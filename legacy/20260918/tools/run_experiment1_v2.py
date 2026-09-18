"""Run Experiment 1 v2 Phase 1 — interface/information fairness re-run.

Same 12 frozen scenarios as the archived v1 prototype, but with the v2 fixes:
  - unified action contract (prompts/manager_v2.txt, Fix A)
  - shared candidate table (orchestrator/candidate_info.py, Fix B)
  - scenario_seed vs llm_repeat_id separation + cache/version capture (Fix D)
  - execution-layer fixes (normalize-then-validate, env-computed ETA, Fix G)

Run structure (review §6 / §10):
  - B0 / B1 / B2: ONE deterministic execution per scenario (scenario_seed fixed).
  - B4v2a (prompt-only) and B4v2b (prompt + shared table): N independent
    inference repeats per scenario, each labelled with an llm_repeat_id.

Usage:
    python tools/run_experiment1_v2.py --scenario E1_M_C_high --manager B4v2b --repeat 0..9
    python tools/run_experiment1_v2.py --scenario all --manager all
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod                    # noqa: E402
from orchestrator.experiment1_runner import (Experiment1Runner,  # noqa: E402
                                             make_manager)

DETERMINISTIC_MANAGERS = ("B0", "B1", "B2")
LLM_MANAGERS = ("B4v2a", "B4v2b")
MANAGERS = DETERMINISTIC_MANAGERS + LLM_MANAGERS
SCENARIO_SEED = 20240601           # frozen scenario realization (traffic-free)
DEFAULT_LLM_REPEATS = 10           # independent inference repeats per scenario

RUNS_ROOT = ROOT / "runs" / "experiment1_v2"


def load_e1():
    with open(ROOT / "config" / "experiment1_v2" / "experiment1_matrix.yaml",
              encoding="utf-8") as f:
        return yaml.safe_load(f)["experiment1"]


def load_p3():
    with open(ROOT / "config" / "phase3_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_dir_for(scenario, manager, repeat: int | None) -> Path:
    base = RUNS_ROOT / scenario["id"] / manager
    return base if repeat is None else base / f"repeat{repeat:02d}"


def run_single(scenario, manager_kind, repeat: int | None) -> int:
    cfg = config_mod.load_config()
    e1 = load_e1()
    p3 = load_p3()
    rd = run_dir_for(scenario, manager_kind, repeat)
    manager = make_manager(manager_kind, cfg, p3)
    runner = Experiment1Runner(cfg, e1, scenario, manager,
                               ROOT / "sim" / "sumo" / "canonical.sumocfg",
                               rd, SCENARIO_SEED, phase3_config=p3)
    try:
        runner.setup()
        runner.run()
    finally:
        if getattr(runner, "sumo", None) is not None:
            try:
                runner.sumo.close()
            except Exception:
                pass
    # explicit scenario_seed vs llm_repeat_id (Fix D)
    (rd / "run_meta.json").write_text(json.dumps({
        "scenario_id": scenario["id"],
        "scenario_seed": SCENARIO_SEED,
        "llm_repeat_id": repeat,
        "manager": manager_kind,
        "arm": ("deterministic" if manager_kind in DETERMINISTIC_MANAGERS
                else "v2a_prompt_only" if manager_kind == "B4v2a"
                else "v2b_prompt_plus_shared_table"),
    }, indent=2, sort_keys=True), encoding="utf-8")
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all", help="scenario id or 'all'")
    ap.add_argument("--manager", default="all", help="|".join(MANAGERS) + "|all")
    ap.add_argument("--repeats", default=None,
                    help="comma repeat indices for LLM arms (0-based)")
    ap.add_argument("--force", action="store_true", help="re-run even if metrics.json exists")
    ap.add_argument("--direct", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    e1 = load_e1()
    scenarios = e1["scenarios"]
    if args.scenario != "all":
        scenarios = [s for s in scenarios if s["id"] == args.scenario]
        if not scenarios:
            print(f"unknown scenario {args.scenario}")
            return 2

    managers = list(MANAGERS)
    if args.manager != "all":
        if args.manager not in MANAGERS:
            print(f"unknown manager {args.manager}")
            return 2
        managers = [args.manager]

    repeat_ids = ([int(x) for x in args.repeats.split(",")]
                  if args.repeats else list(range(DEFAULT_LLM_REPEATS)))

    combos = []
    for s in scenarios:
        for m in managers:
            if m in DETERMINISTIC_MANAGERS:
                combos.append((s, m, None))
            else:
                combos.extend((s, m, r) for r in repeat_ids)

    if args.direct:
        if len(combos) != 1:
            print("--direct requires exactly one combo")
            return 2
        s, m, r = combos[0]
        return run_single(s, m, r)

    t0 = time.time()
    n = 0
    failed = []
    for s, m, r in combos:
        rd = run_dir_for(s, m, r)
        if (rd / "metrics.json").exists() and not args.force:
            continue
        label = f"{s['id']}/{m}" + ("" if r is None else f"/repeat{r:02d}")
        print(f"[run] {label}", flush=True)
        cmd = [sys.executable, str(Path(__file__).resolve()),
               "--scenario", s["id"], "--manager", m,
               "--repeats", str(r if r is not None else 0), "--direct"]
        rcode = subprocess.run(cmd, cwd=str(ROOT)).returncode
        if rcode != 0 or not (rd / "metrics.json").exists():
            failed.append(label)
            print(f"[FAIL] {label}", flush=True)
        n += 1
    print(f"\nDone: {n} runs in {time.time() - t0:.1f}s; failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    os._exit(main(sys.argv[1:]))
