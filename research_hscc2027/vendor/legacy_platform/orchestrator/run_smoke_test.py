"""Phase-1 co-simulation smoke test (no LLM).

    duration: 600 s (0-300 warm-up/stable observation, 300 B1 closes,
              300-600 ground->air support mission runs).
    deterministic action: dispatch one AVAILABLE UAV (M-UAV-02) on a
    predefined V2->V1 medical-resupply support mission.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod  # noqa: E402
from orchestrator.orchestrator import Orchestrator  # noqa: E402


def main() -> int:
    cfg = config_mod.load_config()
    run_dir = ROOT / "runs" / "cosim_smoke_test"
    orch = Orchestrator(
        cfg=cfg,
        sumo_cfg=ROOT / "sim" / "sumo" / "canonical.sumocfg",
        run_dir=run_dir,
        duration_s=600,
        b1_close_t=300,
        gui=False,
        seed=20240601,
    )
    orch.setup()
    orch.run()
    print(f"smoke test complete. outputs in {run_dir}")
    print(f"events recorded: {len(orch.events)}")
    for ev in orch.events:
        print(f"  t={ev['t']:4d} {ev['event_type']:28s} {ev['event_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
