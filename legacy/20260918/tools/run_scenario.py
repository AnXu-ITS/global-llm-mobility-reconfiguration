"""Generic scenario runner for Phase-1 acceptance tests (esp. T9 replay).

Usage: python tools/run_scenario.py <run_dir> <duration_s> <b1_close_t> <seed>
Writes ground_state.csv / air_state.csv / clock_sync.csv / events.csv /
registry_final.json / run_config.yaml into <run_dir>.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod  # noqa: E402
from orchestrator.orchestrator import Orchestrator  # noqa: E402


def main() -> int:
    run_dir = Path(sys.argv[1])
    duration_s = int(sys.argv[2])
    b1_close_t = int(sys.argv[3])
    seed = int(sys.argv[4])
    cfg = config_mod.load_config()
    orch = Orchestrator(
        cfg=cfg,
        sumo_cfg=ROOT / "sim" / "sumo" / "canonical.sumocfg",
        run_dir=run_dir,
        duration_s=duration_s,
        b1_close_t=b1_close_t,
        gui=False,
        seed=seed,
    )
    orch.setup()
    orch.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
