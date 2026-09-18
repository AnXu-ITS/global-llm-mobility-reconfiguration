"""Run Experiment 3 — Compound Disruption Stress Test.

Primary dataset (protocol): 12 scenario classes (L1-L4) x 20 independent seeds
x 4 primary managers (B0/B1/B2/B4b) = 960 runs, PAIRED on identical
(scenario, seed) state.

Pilot (protocol §24): 6 scenarios x 3 seeds x 4 managers = 72 runs.

Run structure:
    runs/experiment3/<scenario>/seed<seed>/<B0|B1|B2|B4b>/

Usage:
    python tools/run_experiment3.py --scenario E3_L1_F1_C2 --seed 20240601 --manager B1 --direct
    python tools/run_experiment3.py --pilot --jobs 4
    python tools/run_experiment3.py --manager all --jobs 8     # full 960 primary
"""
from __future__ import annotations

import argparse
import csv
import json
import os
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
from orchestrator.experiment3_runner import Experiment3Runner    # noqa: E402

PRIMARY_MANAGERS = ("B0", "B1", "B2", "B4b")

RUNS_ROOT = ROOT / "runs" / "experiment3"
EXCLUDED_CSV = RUNS_ROOT / "excluded_runs.csv"


def sha256_hex(obj) -> str:
    import hashlib
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_e3() -> dict:
    with open(ROOT / "config" / "experiment3_matrix.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["experiment3"]


def load_p3() -> dict:
    with open(ROOT / "config" / "phase3_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_seeds() -> list:
    with open(ROOT / "config" / "experiment3_seeds.yaml", encoding="utf-8") as f:
        return list(yaml.safe_load(f)["primary_seeds"])


def load_pilot_seeds() -> list:
    with open(ROOT / "config" / "experiment3_seeds.yaml", encoding="utf-8") as f:
        return list(yaml.safe_load(f)["pilot_seeds"])


def run_dir_for(scenario_id: str, seed: int, manager: str) -> Path:
    return RUNS_ROOT / scenario_id / f"seed{seed}" / manager


def run_single(scenario, seed: int, manager_kind: str) -> int:
    cfg = config_mod.load_config()
    e3 = load_e3()
    p3 = load_p3()
    rd = run_dir_for(scenario["id"], seed, manager_kind)
    rd.mkdir(parents=True, exist_ok=True)
    manager = make_manager(manager_kind, cfg, p3)
    runner = Experiment3Runner(cfg, e3, scenario, manager,
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
        "scenario_id": scenario["id"],
        "level": scenario.get("level"),
        "motif": scenario.get("motif"),
        "seed": seed,
        "manager": manager_kind,
        "manager_kind": getattr(manager, "manager_kind", manager_kind),
        "arm": "primary",
    }, indent=2, sort_keys=True), encoding="utf-8")
    return 0


def _record_excluded(scenario_id: str, seed: int, manager: str, reason: str) -> None:
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    new = not EXCLUDED_CSV.exists()
    with open(EXCLUDED_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["scenario_id", "seed", "manager", "reason", "recorded_at"])
        w.writerow([scenario_id, seed, manager, reason,
                    time.strftime("%Y-%m-%dT%H:%M:%S")])


def run_is_current(scenario_id: str, seed: int, manager: str) -> bool:
    """A run is current iff its recorded failure_schedule_hash matches the
    frozen matrix scenario's failure schedule."""
    rd = run_dir_for(scenario_id, seed, manager)
    if not ((rd / "metrics.json").exists() and (rd / "failure_traces.json").exists()
            and (rd / "run_config.yaml").exists()):
        return False
    try:
        e3 = load_e3()
        scen = next(s for s in e3["scenarios"] if s["id"] == scenario_id)
        rc = yaml.safe_load((rd / "run_config.yaml").read_text(encoding="utf-8"))
        return (rc.get("failure_schedule_hash") == sha256_hex(scen["failure_schedule"])
                and rc.get("matrix_version") == e3.get("version"))
    except Exception:
        return False


def combos_for(args, e3, seeds):
    scenarios = e3["scenarios"]
    if args.pilot:
        pilot_ids = [p["scenario"] for p in e3["pilots"]]
        scenarios = [s for s in scenarios if s["id"] in pilot_ids]
        seeds_use = [s for s in seeds if s in load_pilot_seeds()]
        managers = list(PRIMARY_MANAGERS)
        if args.manager != "all":
            if args.manager not in PRIMARY_MANAGERS:
                raise SystemExit(f"unknown manager {args.manager}")
            managers = [args.manager]
        return [(s, sd, m) for s in scenarios for sd in seeds_use for m in managers]

    if args.scenario != "all":
        scenarios = [s for s in scenarios if s["id"] == args.scenario]
        if not scenarios:
            raise SystemExit(f"unknown scenario {args.scenario}")

    managers = list(PRIMARY_MANAGERS)
    if args.manager != "all":
        if args.manager not in PRIMARY_MANAGERS:
            raise SystemExit(f"unknown manager {args.manager}")
        managers = [args.manager]

    seeds_use = seeds if args.seed is None else [args.seed]
    return [(s, sd, m) for s in scenarios for sd in seeds_use for m in managers]


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--manager", default="all", help="|".join(PRIMARY_MANAGERS) + "|all")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--pilot", action="store_true",
                    help="run the 6x3x4=72-run pilot")
    ap.add_argument("--jobs", type=int, default=1, help="parallel subprocess workers")
    ap.add_argument("--direct", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    e3 = load_e3()
    seeds = load_seeds()
    combos = combos_for(args, e3, seeds)

    if args.direct:
        if len(combos) != 1:
            print("--direct requires exactly one combo")
            return 2
        s, sd, m = combos[0]
        return run_single(s, sd, m)

    def work(item):
        s, sd, m = item
        rd = run_dir_for(s["id"], sd, m)
        label = f"{s['id']}/seed{sd}/{m}"
        rd.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, str(Path(__file__).resolve()),
               "--scenario", s["id"], "--seed", str(sd), "--manager", m, "--direct"]
        logf = rd / "run_console.log"
        try:
            with open(logf, "w", encoding="utf-8") as lf:
                rcode = subprocess.run(cmd, cwd=str(ROOT),
                                       stdout=lf, stderr=subprocess.STDOUT).returncode
        except Exception as e:
            rcode = 99
            _record_excluded(s["id"], sd, m, f"subprocess exception: {e}")
        ok = (rcode == 0) and (rd / "metrics.json").exists() \
            and (rd / "failure_traces.json").exists()
        if not ok:
            _record_excluded(s["id"], sd, m,
                             f"exit {rcode} / missing metrics.json or failure_traces.json")
        return label, ok

    todo = [c for c in combos
            if not run_is_current(c[0]["id"], c[1], c[2]) or args.force]
    print(f"{len(combos)} combos; {len(todo)} to run; jobs={args.jobs}", flush=True)

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
    os._exit(main(sys.argv[1:]))
