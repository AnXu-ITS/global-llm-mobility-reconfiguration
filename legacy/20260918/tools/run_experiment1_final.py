"""Run Experiment 1 Finalization — independent-seed primary rerun.

Primary dataset (Finalization §13):
    12 scenarios x 20 independent simulation seeds x 4 primary managers
    (B0, B1, B2, B4b) = 960 runs, PAIRED on identical (scenario, seed) state.

Interface ablation (Finalization §18): B4a (LLM-State, no candidate table)
over 6 representative scenarios x 10 seeds = 60 runs.

Run structure (Finalization §20):
    runs/experiment1_final/<scenario>/seed<seed>/<B0|B1|B2|B4b|B4a>/

Every run records run_config.yaml, events.csv, ground_state.csv, air_state.csv,
missions.csv, candidate_info.jsonl, manager_inputs.jsonl, manager_outputs.jsonl,
feasibility_checks.jsonl, semantic_checks.jsonl, action_pipeline.jsonl,
actions.csv, metrics.json, runtime.json.

Usage:
    python tools/run_experiment1_final.py --scenario E1_H_C_low --seed 20240601 --manager B1 --direct
    python tools/run_experiment1_final.py --manager all           # full 960 primary
    python tools/run_experiment1_final.py --ablation              # B4a 60-run ablation
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
from orchestrator.experiment1_runner import (Experiment1Runner,  # noqa: E402
                                             make_manager)

PRIMARY_MANAGERS = ("B0", "B1", "B2", "B4b")
ABLATION_MANAGERS = ("B4a",)
ALL_MANAGERS = PRIMARY_MANAGERS + ABLATION_MANAGERS

RUNS_ROOT = ROOT / "runs" / "experiment1_final"
EXCLUDED_CSV = RUNS_ROOT / "excluded_runs.csv"

# Finalization §18: 2 clear-air-beneficial, 2 borderline, 2 ground-unfavorable.
ABLATION_SCENARIOS = ("E1_H_C_low", "E1_M_C_low",      # clear-air-beneficial
                      "E1_H_C_high", "E1_M_C_high",    # borderline
                      "E1_H_H_high", "E1_L_H_high")    # ground/preemption-unfavorable
ABLATION_SEEDS = [20240601, 20240602, 20240603, 20240604, 20240605,
                  20240606, 20240607, 20240608, 20240609, 20240610]

# Finalization §21 mini pilot: 3 scenarios x 3 seeds x 4 primary managers = 36.
PILOT_SCENARIOS = ("E1_H_C_low", "E1_M_C_high", "E1_L_H_high")
PILOT_SEEDS = [20240601, 20240602, 20240603]


def load_e1() -> dict:
    with open(ROOT / "config" / "experiment1_final_matrix.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["experiment1"]


def load_p3() -> dict:
    with open(ROOT / "config" / "phase3_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_seeds() -> list:
    with open(ROOT / "config" / "experiment1_final_seeds.yaml", encoding="utf-8") as f:
        return list(yaml.safe_load(f)["primary_seeds"])


def run_dir_for(scenario_id: str, seed: int, manager: str) -> Path:
    return RUNS_ROOT / scenario_id / f"seed{seed}" / manager


def run_single(scenario, seed: int, manager_kind: str) -> int:
    cfg = config_mod.load_config()
    e1 = load_e1()
    p3 = load_p3()
    rd = run_dir_for(scenario["id"], seed, manager_kind)
    manager = make_manager(manager_kind, cfg, p3)
    runner = Experiment1Runner(cfg, e1, scenario, manager,
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
        "seed": seed,
        "manager": manager_kind,
        "manager_kind": getattr(manager, "manager_kind", manager_kind),
        "arm": ("primary" if manager_kind in PRIMARY_MANAGERS else "ablation_b4a"),
        "include_candidates": bool(p3.get("include_candidates", False)) if manager_kind in ALL_MANAGERS and manager_kind.startswith("B4") else None,
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


def combos_for(args, e1, seeds):
    scenarios = e1["scenarios"]
    if args.pilot:
        scenarios = [s for s in scenarios if s["id"] in PILOT_SCENARIOS]
        seeds_use = [s for s in seeds if s in PILOT_SEEDS]
        managers = list(PRIMARY_MANAGERS)
        return [(s, sd, m) for s in scenarios for sd in seeds_use for m in managers]

    if args.scenario != "all":
        scenarios = [s for s in scenarios if s["id"] == args.scenario]
        if not scenarios:
            raise SystemExit(f"unknown scenario {args.scenario}")

    managers = list(PRIMARY_MANAGERS)
    if args.manager == "ablation":
        managers = list(ABLATION_MANAGERS)
    elif args.manager != "all":
        if args.manager not in ALL_MANAGERS:
            raise SystemExit(f"unknown manager {args.manager}")
        managers = [args.manager]

    seeds_use = seeds if args.seed is None else [args.seed]

    # restrict scenarios for the ablation arm
    if args.manager == "ablation" or set(managers) <= set(ABLATION_MANAGERS):
        scenarios = [s for s in scenarios if s["id"] in ABLATION_SCENARIOS]
        if args.seed is None:
            seeds_use = [s for s in seeds if s in ABLATION_SEEDS]

    out = []
    for s in scenarios:
        for sd in seeds_use:
            for m in managers:
                out.append((s, sd, m))
    return out


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--manager", default="all",
                    help="|".join(ALL_MANAGERS) + "|all|ablation")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--pilot", action="store_true",
                    help="run the 3x3x4=36-run mini pilot")
    ap.add_argument("--jobs", type=int, default=1,
                    help="parallel subprocess workers")
    ap.add_argument("--direct", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    e1 = load_e1()
    seeds = load_seeds()
    combos = combos_for(args, e1, seeds)

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
        ok = (rcode == 0) and (rd / "metrics.json").exists()
        if not ok:
            _record_excluded(s["id"], sd, m, f"exit {rcode} / missing metrics.json")
        return label, ok

    todo = [c for c in combos if not (run_dir_for(c[0]["id"], c[1], c[2]) / "metrics.json").exists() or args.force]
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
    os._exit(main(sys.argv[1:]))
