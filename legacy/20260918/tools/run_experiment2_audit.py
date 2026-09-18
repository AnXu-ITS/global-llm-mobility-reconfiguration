"""Experiment-2 audit runner: same as run_experiment2.py but with an explicit
--run-dir (used by the failure audit tests for deterministic replay pairs)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod                  # noqa: E402
from orchestrator.experiment1_runner import make_manager       # noqa: E402
from orchestrator.experiment2_runner import Experiment2Runner  # noqa: E402


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--manager", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--replay-from", default=None,
                    help="directory of the original run whose cached LLM "
                         "decisions are replayed (B4b reproducibility only)")
    args = ap.parse_args(argv)

    cfg = config_mod.load_config()
    with open(ROOT / "config" / "experiment2_matrix.yaml", encoding="utf-8") as f:
        e2 = yaml.safe_load(f)["experiment2"]
    with open(ROOT / "config" / "phase3_config.yaml", encoding="utf-8") as f:
        p3 = yaml.safe_load(f)
    scenario = next(s for s in e2["scenarios"] if s["id"] == args.scenario)

    rd = Path(args.run_dir)
    rd.mkdir(parents=True, exist_ok=True)
    if args.replay_from and args.manager == "B4b":
        from managers.replay_llm import ReplayLLMManager
        manager = ReplayLLMManager(cfg, p3, Path(args.replay_from))
    else:
        manager = make_manager(args.manager, cfg, p3)
    runner = Experiment2Runner(cfg, e2, scenario, manager,
                               ROOT / "sim" / "sumo" / "canonical.sumocfg",
                               rd, args.seed, phase3_config=p3)
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
        "scenario_id": scenario["id"], "seed": args.seed,
        "manager": args.manager,
        "manager_kind": getattr(manager, "manager_kind", args.manager),
        "arm": "audit"}, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    os._exit(main(sys.argv[1:]))
