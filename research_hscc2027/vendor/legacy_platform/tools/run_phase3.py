"""Run the Phase 3 live closed loop with the LLM Manager.

Usage: python tools/run_phase3.py <SMOKE|C2_B|C2_C> [run_dir]

  SMOKE  B1 closure -> critical mission -> LLM dispatch -> terminal (no C2)
  C2_B   canonical C2 on the support aircraft -> LLM reconfiguration
  C2_C   no backup -> LLM ground fallback / delay / cancel

Produces the Phase-3 artifact set (Phase-2 artifacts + semantic_checks.jsonl +
llm_metadata in manager_outputs / metrics).
"""
import copy
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from managers.llm_manager import LLMManager            # noqa: E402
from orchestrator import config as config_mod          # noqa: E402
from orchestrator.phase3_orchestrator import Phase3Orchestrator  # noqa: E402

CASES = ("SMOKE", "C2_B", "C2_C")
DEFAULT_DIRS = {
    "SMOKE": "runs/phase3_live_smoke",
    "C2_B": "runs/phase3_live_c2",
    "C2_C": "runs/phase3_no_backup",
}


def main(argv) -> int:
    case = argv[1] if len(argv) > 1 else "C2_B"
    if case not in CASES:
        print(f"unknown case {case}; choose from {CASES}")
        return 2
    run_dir = Path(argv[2]) if len(argv) > 2 else ROOT / DEFAULT_DIRS[case]

    cfg = config_mod.load_config()
    if case == "SMOKE":
        cfg = copy.deepcopy(cfg)
        cfg["phase2"]["schedule"]["c2_lost_t_s"] = None

    p3 = yaml.safe_load((ROOT / "config" / "phase3_config.yaml").read_text(encoding="utf-8"))
    manager = LLMManager(cfg, p3)

    orch = Phase3Orchestrator(
        cfg=cfg,
        sumo_cfg=ROOT / "sim" / "sumo" / "canonical.sumocfg",
        run_dir=run_dir,
        case=case,
        gui=False,
        manager=manager,
        phase3_config=p3,
    )
    orch.setup()
    orch.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
