"""Cross-site Experiment-1 — FULL SCALE (Site B Amsterdam / Site C Edmonton).

Applies the frozen Site-A Experiment-1 pipeline at the SAME scale as Site A
per site:
    primary:  12 scenarios x 20 frozen seeds x 4 managers (B0/B1/B2/B4b) = 960
    ablation: 6 scenarios x 10 seeds x B4a (LLM-State, no candidate table) = 60
    total:    1020 runs per site

Run dirs:
    runs/experiment1_cross_site/<site_id>/<scenario_id>/seed<seed>/<manager>/

Artifact contract: identical to the frozen Experiment-1 final (metrics.json,
candidate_info.jsonl, manager_inputs/outputs, action_pipeline.jsonl,
runtime.json, run_meta.json, ...).

Usage:
    python tools/run_experiment1_cross_site.py --site b --scenario XB_H_C_low --seed 20240601 --manager B1 --direct
    python tools/run_experiment1_cross_site.py --site all                  # 960 primary per site
    python tools/run_experiment1_cross_site.py --site all --ablation       # 60 B4a per site
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
from orchestrator.experiment1_runner import (Experiment1Runner,  # noqa: E402
                                             make_manager)

SITES = {
    "b": {
        "site_id": "site_b_amsterdam",
        "config": ROOT / "sim" / "sites" / "site_b_amsterdam" / "config" /
                  "site_b_amsterdam_config.yaml",
        "sumocfg": ROOT / "sim" / "sites" / "site_b_amsterdam" / "sumo" /
                   "site.sumocfg",
        "matrix": ROOT / "config" / "experiment1_site_b_matrix.yaml",
        "prefix": "XB_",
    },
    "c": {
        "site_id": "site_c_edmonton",
        "config": ROOT / "sim" / "sites" / "site_c_edmonton" / "config" /
                  "site_c_edmonton_config.yaml",
        "sumocfg": ROOT / "sim" / "sites" / "site_c_edmonton" / "sumo" /
                   "site.sumocfg",
        "matrix": ROOT / "config" / "experiment1_site_c_matrix.yaml",
        "prefix": "XC_",
    },
}

PRIMARY_MANAGERS = ("B0", "B1", "B2", "B4b")
ABLATION_MANAGERS = ("B4a",)
ALL_MANAGERS = PRIMARY_MANAGERS + ABLATION_MANAGERS

RUNS_ROOT = ROOT / "runs" / "experiment1_cross_site"
EXCLUDED_CSV = RUNS_ROOT / "excluded_runs.csv"
PHASE3_CONFIG = ROOT / "config" / "phase3_config.yaml"
SEEDS_CONFIG = ROOT / "config" / "experiment1_final_seeds.yaml"

# Frozen §18 ablation scenario selection (Site-A analogs with site prefix).
ABLATION_SUFFIXES = ("H_C_low", "M_C_low",      # clear-air-beneficial
                     "H_C_high", "M_C_high",    # borderline
                     "H_H_high", "L_H_high")    # ground/preemption-unfavorable
ABLATION_SEEDS = [20240601, 20240602, 20240603, 20240604, 20240605,
                  20240606, 20240607, 20240608, 20240609, 20240610]


def load_seeds() -> list:
    with open(SEEDS_CONFIG, encoding="utf-8") as f:
        return list(yaml.safe_load(f)["primary_seeds"])


def run_dir_for(site_key: str, scenario_id: str, seed: int, manager: str) -> Path:
    return RUNS_ROOT / SITES[site_key]["site_id"] / scenario_id / \
        f"seed{seed}" / manager


def run_single(site_key: str, scenario, seed: int, manager_kind: str) -> int:
    site = SITES[site_key]
    cfg = config_mod.load_config(site["config"])
    e1 = yaml.safe_load(site["matrix"].read_text(encoding="utf-8"))["experiment1"]
    p3 = yaml.safe_load(PHASE3_CONFIG.read_text(encoding="utf-8"))
    rd = run_dir_for(site_key, scenario["id"], seed, manager_kind)
    manager = make_manager(manager_kind, cfg, p3)
    runner = Experiment1Runner(cfg, e1, scenario, manager, site["sumocfg"],
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
        "site_role": "cross_site_validation",
        "scenario_id": scenario["id"],
        "scenario_version": cfg.get("scenario_version"),
        "seed": seed,
        "manager": manager_kind,
        "manager_kind": getattr(manager, "manager_kind", manager_kind),
        "arm": ("primary" if manager_kind in PRIMARY_MANAGERS else "ablation_b4a"),
        "include_candidates": None,
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
    seeds = load_seeds()
    out = []
    for site_key in (["b", "c"] if args.site == "all" else [args.site]):
        site = SITES[site_key]
        e1 = yaml.safe_load(site["matrix"].read_text(encoding="utf-8"))["experiment1"]
        scenarios = e1["scenarios"]
        if args.scenario != "all":
            scenarios = [s for s in scenarios if s["id"] == args.scenario]
            if not scenarios:
                raise SystemExit(f"unknown scenario {args.scenario}")
        managers = list(PRIMARY_MANAGERS)
        if args.ablation:
            managers = list(ABLATION_MANAGERS)
        elif args.manager != "all":
            if args.manager not in ALL_MANAGERS:
                raise SystemExit(f"unknown manager {args.manager}")
            managers = [args.manager]
        seeds_use = seeds if args.seed is None else [args.seed]
        if args.ablation or set(managers) <= set(ABLATION_MANAGERS):
            scenarios = [s for s in scenarios
                         if any(s["id"].endswith(suf) for suf in ABLATION_SUFFIXES)]
            if args.seed is None:
                seeds_use = [s for s in seeds if s in ABLATION_SEEDS]
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
    ap.add_argument("--manager", default="all",
                    help="|".join(ALL_MANAGERS) + "|all")
    ap.add_argument("--ablation", action="store_true",
                    help="run the 6x10=60 B4a ablation per site")
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
        ok = (rcode == 0) and (rd / "metrics.json").exists()
        if not ok:
            _record_excluded(k, s["id"], sd, m, f"exit {rcode} / missing metrics.json")
        return label, ok

    todo = [c for c in combos
            if args.force or not (run_dir_for(c[0], c[1]["id"], c[2], c[3]) /
                                  "metrics.json").exists()]
    print(f"{len(combos)} combos; {len(todo)} to run; jobs={args.jobs}", flush=True)

    t0 = time.time()
    n = 0
    failed = []
    if args.jobs <= 1:
        for c in todo:
            label, ok = work(c)
            print(f"[{'ok' if ok else 'FAIL'}] {label}", flush=True)
            n += 1
            if not ok:
                failed.append(label)
    else:
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            futs = {ex.submit(work, c): c for c in todo}
            for fut in as_completed(futs):
                label, ok = fut.result()
                print(f"[{'ok' if ok else 'FAIL'}] {label}", flush=True)
                n += 1
                if not ok:
                    failed.append(label)
    print(f"\nDone: {n} runs in {time.time() - t0:.1f}s; failed: {len(failed)}")
    if failed:
        print("failed:", failed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
