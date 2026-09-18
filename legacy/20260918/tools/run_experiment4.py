"""Run Experiment 4 — LLM Operational Limits (4A / 4B / 4C).

Primary dataset: 4A (5 arms) + 4B (7 arms) + 4C (5 arms) x 4 managers
(B0/B1/B2/B4b) x 20 seeds = 400 + 560 + 400 = 1,360 runs, PAIRED on identical
(scenario, seed) state.

P0 fix (review 20260909): every run executes in its OWN subprocess — the parent
only schedules and never touches a shared BlueSky/TraCI instance.

Cohort separation (review P1): pilot and primary live in separate directories so
a re-run of one never overwrites the other.  `run_is_current` re-checks the
frozen matrix hash before declaring a run complete.

Run structure:
    runs/experiment4/<cohort>/<sub>/<arm_id>/<scenario>/seed<seed>/<manager>/

Usage:
    python tools/run_experiment4.py --sub 4A --arm OBS30 --seed 20240601 --manager B4b --direct
    python tools/run_experiment4.py --pilot --jobs 4
    python tools/run_experiment4.py --sub 4A --manager all --jobs 8    # 400 primary
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod                    # noqa: E402
from orchestrator.experiment1_runner import make_manager         # noqa: E402
from orchestrator.experiment4_runner import (Experiment4BRunner,  # noqa: E402
                                             Experiment4CRunner,
                                             Experiment4Runner)

PRIMARY_MANAGERS = ("B0", "B1", "B2", "B4b")

RUNNER_BY_SUB = {"4A": Experiment4Runner, "4B": Experiment4BRunner,
                 "4C": Experiment4CRunner}

RUNS_ROOT = ROOT / "runs" / "experiment4"


def sha256_hex(obj) -> str:
    import hashlib
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_e4() -> dict:
    with open(ROOT / "config" / "experiment4_matrix.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["experiment4"]


def load_p3() -> dict:
    with open(ROOT / "config" / "phase3_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_seeds() -> list:
    with open(ROOT / "config" / "experiment4_seeds.yaml", encoding="utf-8") as f:
        return list(yaml.safe_load(f)["primary_seeds"])


def load_pilot_seeds() -> list:
    with open(ROOT / "config" / "experiment4_seeds.yaml", encoding="utf-8") as f:
        return list(yaml.safe_load(f)["pilot_seeds"])


def _scenarios_for(e4: dict, sub: str) -> list:
    return [s for s in e4["scenarios"] if s["id"] in e4["exp" + sub.lower()]["scenarios"]]


def _arms_for(e4: dict, sub: str) -> list:
    return list(e4["exp" + sub.lower()]["arms"])


def run_dir_for(sub: str, arm_id: str, scenario_id: str, seed: int,
                manager: str, cohort: str) -> Path:
    return RUNS_ROOT / cohort / sub / arm_id / scenario_id / f"seed{seed}" / manager


def run_single(sub: str, arm: dict, scenario: dict, seed: int,
               manager_kind: str, cohort: str) -> int:
    cfg = config_mod.load_config()
    e4 = load_e4()
    p3 = load_p3()
    rd = run_dir_for(sub, arm["id"], scenario["id"], seed, manager_kind, cohort)
    rd.mkdir(parents=True, exist_ok=True)
    manager = make_manager(manager_kind, cfg, p3)
    runner_cls = RUNNER_BY_SUB[sub]
    runner = runner_cls(cfg, e4, sub, arm, scenario, manager,
                        ROOT / "sim" / "sumo" / "canonical.sumocfg",
                        rd, seed, phase3_config=p3)
    try:
        runner.setup()
        runner.run()
    finally:
        if getattr(runner, "sumo", None) is not None:
            try:
                runner.sumo.close()
            except Exception:
                pass
    (rd / "run_meta.json").write_text(json.dumps({
        "sub_experiment": sub,
        "arm_id": arm["id"],
        "arm_params": arm,
        "scenario_id": scenario["id"],
        "seed": seed,
        "manager": manager_kind,
        "manager_kind": getattr(manager, "manager_kind", manager_kind),
        "cohort": cohort,
        "matrix_version": int(e4.get("version", 1)),
        "matrix_hash": sha256_hex(e4),
    }, indent=2, sort_keys=True), encoding="utf-8")
    return 0


def run_is_current(sub: str, arm_id: str, scenario_id: str, seed: int,
                   manager: str, cohort: str) -> bool:
    """A run is current iff it completed AND its recorded matrix hash matches
    the frozen experiment4 matrix (arms + scenarios + failure schedule)."""
    rd = run_dir_for(sub, arm_id, scenario_id, seed, manager, cohort)
    if not ((rd / "metrics.json").exists() and (rd / "run_config.yaml").exists()):
        return False
    try:
        rc = yaml.safe_load((rd / "run_config.yaml").read_text(encoding="utf-8"))
        e4 = load_e4()
        return (rc.get("matrix_version") == int(e4.get("version", 1))
                and rc.get("matrix_hash") == sha256_hex(e4)
                and rc.get("sub_experiment") == sub
                and rc.get("arm_id") == arm_id)
    except Exception:
        return False


def build_todo(args, e4: dict, seeds: list, pilot_seeds: list) -> list:
    if args.pilot:
        pilots = e4.get("pilots", [])
        if args.sub != "all":
            pilots = [p for p in pilots if p["sub"] == args.sub]
        todo = []
        for p in pilots:
            scen = next(s for s in e4["scenarios"] if s["id"] == p["scenario"])
            arm = next(a for a in _arms_for(e4, p["sub"]) if a["id"] == p["arm"])
            for sd in pilot_seeds:
                todo.append((p["sub"], arm, scen, sd, p["manager"]))
        return todo

    subs = ["4A", "4B", "4C"] if args.sub == "all" else [args.sub]
    for s in subs:
        if s not in RUNNER_BY_SUB:
            raise SystemExit(f"unknown sub-experiment {s}")

    seeds_use = seeds if args.seed is None else [args.seed]
    todo = []
    for sub in subs:
        arms = _arms_for(e4, sub)
        if args.arm != "all":
            arms = [a for a in arms if a["id"] == args.arm]
            if not arms:
                raise SystemExit(f"unknown arm {args.arm} for {sub}")
        managers = list(e4["exp" + sub.lower()].get("managers", list(PRIMARY_MANAGERS)))
        if args.manager != "all":
            if args.manager not in managers:
                raise SystemExit(f"unknown manager {args.manager} for {sub}")
            managers = [args.manager]
        scenarios = _scenarios_for(e4, sub)
        if args.scenario != "all":
            scenarios = [s for s in scenarios if s["id"] == args.scenario]
            if not scenarios:
                raise SystemExit(f"unknown scenario {args.scenario} for {sub}")
        for scen in scenarios:
            for arm in arms:
                for sd in seeds_use:
                    for m in managers:
                        todo.append((sub, arm, scen, sd, m))
    return todo


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", default="all", choices=["all", "4A", "4B", "4C"])
    ap.add_argument("--arm", default="all")
    ap.add_argument("--scenario", default="all")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--manager", default="all", help="|".join(PRIMARY_MANAGERS) + "|all")
    ap.add_argument("--cohort", default="primary", choices=["primary", "pilot"])
    ap.add_argument("--pilot", action="store_true",
                    help="run the pilot matrix (pilots x pilot_seeds)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--jobs", type=int, default=1, help="parallel subprocess workers")
    ap.add_argument("--direct", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    e4 = load_e4()
    seeds = load_seeds()
    pilot_seeds = load_pilot_seeds()
    cohort = "pilot" if args.pilot else args.cohort
    combos = build_todo(args, e4, seeds, pilot_seeds)

    if args.direct:
        if len(combos) != 1:
            print("--direct requires exactly one combo")
            return 2
        sub, arm, scen, sd, m = combos[0]
        return run_single(sub, arm, scen, sd, m, cohort)

    todo = [c for c in combos
            if not run_is_current(c[0], c[1]["id"], c[2]["id"], c[3], c[4], cohort)
            or args.force]
    print(f"{len(combos)} combos; {len(todo)} to run; jobs={args.jobs}", flush=True)

    def work(item):
        sub, arm, scen, sd, m = item
        rd = run_dir_for(sub, arm["id"], scen["id"], sd, m, cohort)
        label = f"{cohort}/{sub}/{arm['id']}/{scen['id']}/seed{sd}/{m}"
        rd.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, str(Path(__file__).resolve()),
               "--sub", sub, "--arm", arm["id"], "--scenario", scen["id"],
               "--seed", str(sd), "--manager", m, "--cohort", cohort, "--direct"]
        logf = rd / "run_console.log"
        try:
            with open(logf, "w", encoding="utf-8") as lf:
                rcode = subprocess.run(cmd, cwd=str(ROOT),
                                       stdout=lf, stderr=subprocess.STDOUT).returncode
        except Exception as e:
            rcode = 99
        ok = (rcode == 0) and (rd / "metrics.json").exists()
        return label, ok

    t0 = time.time()
    failed = []
    if args.jobs <= 1:
        for c in todo:
            label, ok = work(c)
            print(f"[{'ok' if ok else 'FAIL'}] {label}", flush=True)
            if not ok:
                failed.append(label)
    else:
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            futs = {ex.submit(work, c): c for c in todo}
            for fut in as_completed(futs):
                label, ok = fut.result()
                print(f"[{'ok' if ok else 'FAIL'}] {label}", flush=True)
                if not ok:
                    failed.append(label)
    print(f"\nDone: {len(todo)} runs in {time.time() - t0:.1f}s; failed: {len(failed)}")
    if failed:
        print("failed:", failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
