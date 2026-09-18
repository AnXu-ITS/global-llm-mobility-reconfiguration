"""Experiment 2 cross-site runner — SMOKE STAGE (Site B Amsterdam / Site C Edmonton).

Applies the frozen Site-A Experiment-2 pipeline (failure injection F1-F6,
candidate table 2.1.0, E2 checker/semantic extensions, failure_trace.json,
E2 metrics) to the cross-site testbeds using the site-specific smoke matrices
(config/experiment2_site_b_matrix.yaml / config/experiment2_site_c_matrix.yaml).

SMOKE SCOPE (this stage): 6 scenarios (one per failure family) x 1 seed x
4 managers per site = 48 runs. NOT a primary dataset and NOT part of the
frozen canonical Experiment-2 dataset (runs/experiment2/ is untouched).

Run dirs: runs/experiment2_cross_site/<site_id>/<scenario_id>/seed<seed>/<manager>/

Usage:
    python tools/run_experiment2_cross_site.py --site b --scenario E2XB_F1_C1 --seed 20240601 --manager B1 --direct
    python tools/run_experiment2_cross_site.py --site all --smoke --jobs 6
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod                  # noqa: E402
from orchestrator.experiment1_runner import make_manager       # noqa: E402
from orchestrator.experiment2_runner import Experiment2Runner  # noqa: E402

SITES = {
    "b": {
        "site_id": "site_b_amsterdam",
        "city": "Amsterdam, NL",
        "config": ROOT / "sim" / "sites" / "site_b_amsterdam" / "config" /
                  "site_b_amsterdam_config.yaml",
        "sumocfg": ROOT / "sim" / "sites" / "site_b_amsterdam" / "sumo" /
                   "site.sumocfg",
        "matrix": ROOT / "config" / "experiment2_site_b_matrix.yaml",
    },
    "c": {
        "site_id": "site_c_edmonton",
        "city": "Edmonton, CA",
        "config": ROOT / "sim" / "sites" / "site_c_edmonton" / "config" /
                  "site_c_edmonton_config.yaml",
        "sumocfg": ROOT / "sim" / "sites" / "site_c_edmonton" / "sumo" /
                   "site.sumocfg",
        "matrix": ROOT / "config" / "experiment2_site_c_matrix.yaml",
    },
}

PRIMARY_MANAGERS = ("B0", "B1", "B2", "B4b")
RUNS_ROOT = ROOT / "runs" / "experiment2_cross_site"
EXCLUDED_CSV = RUNS_ROOT / "excluded_runs.csv"
PHASE3_CONFIG = ROOT / "config" / "phase3_config.yaml"
SMOKE_SEEDS = [20240601]
PILOT_SEEDS = [20240601, 20240602, 20240603]


def load_primary_seeds() -> list:
    with open(ROOT / "config" / "experiment2_seeds.yaml", encoding="utf-8") as f:
        return list(yaml.safe_load(f)["primary_seeds"])


def sha256_hex(obj) -> str:
    import hashlib
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def run_is_current(site_key: str, scenario_id: str, seed: int, manager: str) -> bool:
    """A cross-site cell is current iff its failure trace matches the site
    matrix's frozen failure config (guards stale pre-adaptation cells)."""
    rd = run_dir_for(site_key, scenario_id, seed, manager)
    if not ((rd / "metrics.json").exists() and (rd / "failure_trace.json").exists()):
        return False
    try:
        e2 = yaml.safe_load(SITES[site_key]["matrix"].read_text(encoding="utf-8"))["experiment2"]
        scen = next(s for s in e2["scenarios"] if s["id"] == scenario_id)
        tr = json.loads((rd / "failure_trace.json").read_text(encoding="utf-8"))
        return tr.get("failure_config_hash") == sha256_hex(scen["failure"])
    except Exception:
        return False


def run_dir_for(site_key: str, scenario_id: str, seed: int, manager: str) -> Path:
    return RUNS_ROOT / SITES[site_key]["site_id"] / scenario_id / \
        f"seed{seed}" / manager


def run_single(site_key: str, scenario, seed: int, manager_kind: str) -> int:
    site = SITES[site_key]
    cfg = config_mod.load_config(site["config"])
    e2 = yaml.safe_load(site["matrix"].read_text(encoding="utf-8"))["experiment2"]
    p3 = yaml.safe_load(PHASE3_CONFIG.read_text(encoding="utf-8"))
    rd = run_dir_for(site_key, scenario["id"], seed, manager_kind)
    rd.mkdir(parents=True, exist_ok=True)
    manager = make_manager(manager_kind, cfg, p3)
    runner = Experiment2Runner(cfg, e2, scenario, manager, site["sumocfg"],
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
        "site_id": site["site_id"],
        "site_role": "experiment2_cross_site_smoke",
        "scenario_id": scenario["id"],
        "scenario_version": cfg.get("scenario_version"),
        "failure_family": scenario.get("failure_family"),
        "impact_context": scenario.get("impact_context"),
        "seed": seed,
        "manager": manager_kind,
        "manager_kind": getattr(manager, "manager_kind", manager_kind),
        "arm": "cross_site_smoke",
    }, indent=2, sort_keys=True), encoding="utf-8")
    return 0


def _record_excluded(site_key: str, scenario_id: str, seed: int,
                     manager: str, reason: str) -> None:
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    new = not EXCLUDED_CSV.exists()
    with open(EXCLUDED_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["site_id", "scenario_id", "seed", "manager",
                        "reason", "recorded_at"])
        w.writerow([SITES[site_key]["site_id"], scenario_id, seed, manager,
                    reason, time.strftime("%Y-%m-%dT%H:%M:%S")])


def combos_for(args):
    out = []
    for site_key in (["b", "c"] if args.site == "all" else [args.site]):
        site = SITES[site_key]
        e2 = yaml.safe_load(site["matrix"].read_text(encoding="utf-8"))["experiment2"]
        scenarios = e2["scenarios"]
        if args.smoke:
            smoke_ids = set(e2.get("smoke", []))
            scenarios = [s for s in scenarios if s["id"] in smoke_ids]
        elif args.pilot:
            pilot_ids = [p["scenario"] for p in e2.get("pilots", [])]
            scenarios = [s for s in scenarios if s["id"] in pilot_ids]
        elif args.scenario != "all":
            scenarios = [s for s in scenarios if s["id"] == args.scenario]
            if not scenarios:
                raise SystemExit(f"unknown scenario {args.scenario}")
        managers = list(PRIMARY_MANAGERS)
        if args.manager != "all":
            if args.manager not in PRIMARY_MANAGERS:
                raise SystemExit(f"unknown manager {args.manager}")
            managers = [args.manager]
        if args.smoke:
            seeds_use = SMOKE_SEEDS
        elif args.pilot:
            seeds_use = PILOT_SEEDS
        elif args.seed is not None:
            seeds_use = [args.seed]
        else:
            seeds_use = load_primary_seeds()
        for s in scenarios:
            for sd in seeds_use:
                for m in managers:
                    out.append((site_key, s, sd, m))
    return out


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="all", choices=["b", "c", "all"])
    ap.add_argument("--scenario", default="all")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--manager", default="all", help="|".join(PRIMARY_MANAGERS) + "|all")
    ap.add_argument("--smoke", action="store_true",
                    help="run the smoke set (6 scenarios x 1 seed x 4 managers per site)")
    ap.add_argument("--pilot", action="store_true",
                    help="run the pilot set (6 scenarios x 3 seeds x 4 managers per site)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--direct", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    combos = combos_for(args)

    if args.direct:
        if len(combos) != 1:
            print("--direct requires exactly one combo")
            return 2
        k, s, sd, m = combos[0]
        return run_single(k, s, sd, m)

    def work(item):
        k, s, sd, m = item
        rd = run_dir_for(k, s["id"], sd, m)
        label = f"{SITES[k]['site_id']}/{s['id']}/seed{sd}/{m}"
        rd.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, str(Path(__file__).resolve()),
               "--site", k, "--scenario", s["id"], "--seed", str(sd),
               "--manager", m, "--direct"]
        logf = rd / "run_console.log"
        try:
            with open(logf, "w", encoding="utf-8") as lf:
                rcode = subprocess.run(cmd, cwd=str(ROOT),
                                       stdout=lf, stderr=subprocess.STDOUT).returncode
        except Exception as e:
            rcode = 99
            _record_excluded(k, s["id"], sd, m, f"subprocess exception: {e}")
        ok = (rcode == 0) and (rd / "metrics.json").exists() \
            and (rd / "failure_trace.json").exists()
        if not ok:
            _record_excluded(k, s["id"], sd, m,
                             f"exit {rcode} / missing metrics or failure_trace")
        return label, ok

    todo = [c for c in combos
            if args.force or not run_is_current(c[0], c[1]["id"], c[2], c[3])]
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
    sys.exit(main(sys.argv[1:]))
