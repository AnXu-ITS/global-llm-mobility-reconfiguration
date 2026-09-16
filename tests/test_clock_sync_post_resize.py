"""Master-clock regression (post-resize): 600 simulation steps, step-aligned
SUMO/BlueSky/Orchestrator clocks.

Reads runs/post_resize_cosim_smoke_test/clock_sync.csv (written by the
orchestrator each step) and derives per-step errors:

  sumo_error    = |sumo_time    - orchestrator_time|
  bluesky_error = |bluesky_time - orchestrator_time|

Writes outputs/clock_sync_post_resize.csv.  Acceptance: max error = 0 steps
(i.e. step indices are exactly identical for all three clocks).
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SRC = ROOT / "runs" / "post_resize_cosim_smoke_test" / "clock_sync.csv"
OUT = ROOT / "outputs" / "clock_sync_post_resize.csv"


def main() -> int:
    rows = []
    max_s, max_b = 0.0, 0.0
    with open(SRC, newline="") as fh:
        r = csv.DictReader(fh)
        for line in r:
            step = int(line["t"])
            ot = float(line["orchestrator_time"])
            st = float(line["sumo_time"])
            bt = float(line["bluesky_time"])
            se = abs(st - ot)
            be = abs(bt - ot)
            max_s = max(max_s, se)
            max_b = max(max_b, be)
            rows.append({
                "step": step,
                "orchestrator_time": ot,
                "sumo_time": st,
                "bluesky_time": bt,
                "sumo_error": round(se, 6),
                "bluesky_error": round(be, 6),
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"steps: {len(rows)}")
    print(f"max sumo_error   = {max_s:.6f} steps")
    print(f"max bluesky_error = {max_b:.6f} steps")
    ok = (max_s < 1e-9) and (max_b < 1e-9) and len(rows) >= 600
    print(f"clock sync (post-resize): {'PASS' if ok else 'FAIL'} "
          f"(max error = 0 simulation step)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
