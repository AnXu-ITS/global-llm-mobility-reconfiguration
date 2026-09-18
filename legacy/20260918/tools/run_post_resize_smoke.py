"""Run the post-resize co-simulation smoke test using the fixed event schedule
from config/scenario_config.yaml (schedule.*).  No LLM; deterministic manager.

Usage: python tools/run_post_resize_smoke.py [run_dir]
  run_dir defaults to runs/post_resize_cosim_smoke_test.

Produces {events,actions,missions,ground_state,air_state,clock_sync}.csv +
registry_final.json + run_config.yaml.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod  # noqa: E402
from orchestrator.orchestrator import Orchestrator  # noqa: E402


def main(argv) -> int:
    cfg = config_mod.load_config()
    sched = cfg["schedule"]
    run_dir = Path(argv[1]) if len(argv) > 1 else ROOT / "runs" / "post_resize_cosim_smoke_test"
    orch = Orchestrator(
        cfg=cfg,
        sumo_cfg=ROOT / "sim" / "sumo" / "canonical.sumocfg",
        run_dir=run_dir,
        duration_s=sched["duration_s"],
        b1_close_t=None,          # -> read from config schedule (fixed in config)
        gui=False,
        seed=sched["seed"],
    )
    orch.setup()
    orch.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
