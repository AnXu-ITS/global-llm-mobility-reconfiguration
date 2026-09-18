"""Run the Phase 2 closed loop for one C2 case.

Usage: python tools/run_phase2.py <case> [run_dir]
  case in {C2_A, C2_B, C2_C}
  run_dir defaults to runs/phase2_rule_manager/<case>

Produces the full Phase-2 artifact set (events/ground_state/air_state/missions/
clock_sync/actions/violations CSVs + manager_inputs/outputs/feasibility_checks
JSONL + metrics.json + run_config.yaml + registry_final.json).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod                  # noqa: E402
from orchestrator.phase2_orchestrator import Phase2Orchestrator  # noqa: E402

CASES = ("C2_A", "C2_B", "C2_C")


def main(argv) -> int:
    case = argv[1] if len(argv) > 1 else "C2_B"
    if case not in CASES:
        print(f"unknown case {case}; choose from {CASES}")
        return 2
    run_dir = Path(argv[2]) if len(argv) > 2 else ROOT / "runs" / "phase2_rule_manager" / case
    cfg = config_mod.load_config()
    orch = Phase2Orchestrator(
        cfg=cfg,
        sumo_cfg=ROOT / "sim" / "sumo" / "canonical.sumocfg",
        run_dir=run_dir,
        case=case,
        gui=False,
    )
    orch.setup()
    orch.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
