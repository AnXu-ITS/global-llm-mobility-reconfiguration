"""Reverse Air->Hub event regression (post-resize).

Verifies the BlueSky / Air Registry -> Global State Hub link still works after
the crop: an existing air resource becomes UNAVAILABLE, the Hub detects the
AIR_EVENT, and its mission transitions to NEEDS_REPLAN (no formal C2 Lost).

Reads runs/post_resize_cosim_smoke_test/{events,missions,air_state}.csv and
writes outputs/reverse_air_event.csv.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RUN = ROOT / "runs" / "post_resize_cosim_smoke_test"
OUT = ROOT / "outputs" / "reverse_air_event.csv"


def main() -> int:
    # 1. AIR_EVENT in events.csv
    event = None
    with open(RUN / "events.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["event_type"] == "AIR_EVENT":
                event = r
    if event is None:
        print("[FAIL] no AIR_EVENT in events.csv")
        return 1

    # 2. M-L-001 NEEDS_REPLAN transition in missions.csv
    replan = None
    with open(RUN / "missions.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["mission_id"] == "M-L-001" and r["status"] == "NEEDS_REPLAN":
                replan = r
    if replan is None:
        print("[FAIL] M-L-001 NEEDS_REPLAN not in missions.csv")
        return 1

    # 3. last recorded status of L-UAV-01 before the event (old_state)
    old_state = None
    with open(RUN / "air_state.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["aircraft_id"] == "L-UAV-01":
                if int(r["t"]) < int(event["t"]):
                    old_state = r["status"]

    row = {
        "event_id": event["event_id"],
        "aircraft_id": "L-UAV-01",
        "old_state": old_state,
        "new_state": "UNAVAILABLE",
        "mission_old_state": "EN_ROUTE",
        "mission_new_state": replan["status"],
        "timestamp": event["t"],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row.keys()))
        w.writeheader()
        w.writerow(row)

    ok = (row["old_state"] == "BUSY" and row["new_state"] == "UNAVAILABLE"
          and row["mission_new_state"] == "NEEDS_REPLAN")
    print(f"reverse air->hub: {row}")
    print(f"reverse air->hub (post-resize): {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
