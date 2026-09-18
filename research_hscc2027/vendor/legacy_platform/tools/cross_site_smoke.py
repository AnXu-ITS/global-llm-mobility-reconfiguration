"""Cross-site co-simulation smoke test (Site B / Site C, NO manager, NO LLM).

   duration: 600 s, 1 s master clock
   schedule : 0-300 warm-up, 300 B1 closes, 300-600 deterministic support
              mission dispatch (same deterministic smoke action as Site A).
   fleet    : identical to Site A (L-UAV-01, EVTOL-01 busy shuttles;
              M-UAV-01/M-UAV-02 standby; M-UAV-02 dispatched at t=300).

Outputs in runs/site_b_cosim_smoke / runs/site_c_cosim_smoke:
   ground_state.csv air_state.csv clock_sync.csv events.csv
   actions.csv missions.csv registry_final.json run_config.yaml

Usage: python tools/cross_site_smoke.py --site b|c
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod  # noqa: E402
from orchestrator.orchestrator import Orchestrator  # noqa: E402

SITES = {
    "b": {"site_id": "site_b_amsterdam", "run_dir": "site_b_cosim_smoke"},
    "c": {"site_id": "site_c_edmonton", "run_dir": "site_c_cosim_smoke"},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, choices=["b", "c"])
    ap.add_argument("--config", default=None,
                    help="override config path (default: config/site_<id>_config.yaml)")
    ap.add_argument("--run-dir", default=None,
                    help="override run directory")
    args = ap.parse_args()
    meta = SITES[args.site]
    site_id = meta["site_id"]
    cfg_path = Path(args.config) if args.config else \
        ROOT / "config" / f"{site_id}_config.yaml"
    cfg = config_mod.load_config(cfg_path)
    run_dir = Path(args.run_dir) if args.run_dir else ROOT / "runs" / meta["run_dir"]
    orch = Orchestrator(
        cfg=cfg,
        sumo_cfg=ROOT / "sim" / "sites" / site_id / "sumo" / "site.sumocfg",
        run_dir=run_dir,
        duration_s=600,
        b1_close_t=300,
        gui=False,
        seed=20240601,
    )
    orch.setup()
    orch.run()
    print(f"[{site_id}] smoke test complete. outputs in {run_dir}")
    print(f"events recorded: {len(orch.events)}")
    for ev in orch.events:
        print(f"  t={ev['t']:4d} {ev['event_type']:28s} {ev['event_id']}")
    # clock-sync summary
    import csv as _csv
    with open(run_dir / "clock_sync.csv", newline="", encoding="utf-8") as fh:
        reader = _csv.DictReader(fh)
        rows = list(reader)
    bad = [r for r in rows if r["sync_ok"] != "True"]
    print(f"clock rows={len(rows)} sync_violations={len(bad)}")
    if bad:
        for r in bad[:5]:
            print("  VIOLATION:", r)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
