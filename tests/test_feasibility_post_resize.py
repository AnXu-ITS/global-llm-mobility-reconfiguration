"""Feasibility-checker regression (post-resize).

Re-validates that the hard-constraint filter REJECTS (never silently repairs)
three infeasible action classes:

  1. assign a BUSY non-reassignable aircraft
  2. assign a mission to an unavailable landing site
  3. assign an aircraft with insufficient battery

Writes outputs/violations.csv.  All three must be REJECTED (valid=False).
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod                      # noqa: E402
from orchestrator.registry import Aircraft, Mission, Registry       # noqa: E402
from safety.feasibility_checker import FeasibilityChecker           # noqa: E402

OUT_CSV = ROOT / "outputs" / "violations.csv"


def _build():
    cfg = config_mod.load_config()
    reg = Registry()
    reg.add_aircraft(Aircraft("L-UAV-01", "logistics_uav", 31.3, 120.6,
                              status="AVAILABLE"))
    # case 1: BUSY, non-reassignable aircraft
    busy = Aircraft("M-UAV-01", "medical_uav", 31.31, 120.60, status="BUSY",
                    mission_id="M-M-001", reassignable=False)
    reg.add_aircraft(busy)
    # case 3: dead-battery aircraft
    dead = Aircraft("L-UAV-09", "logistics_uav", 31.3, 120.6, battery_pct=0)
    reg.add_aircraft(dead)
    reg.add_mission(Mission("M-SUPPORT-001", "medical_resupply", "CRITICAL",
                            "V2", "V1", deadline_s=900))
    reg.add_mission(Mission("M-M-001", "medical_transfer", "HIGH", "V1", "V3",
                            deadline_s=1800, assigned_resource="M-UAV-01",
                            status="EN_ROUTE"))
    # make V3 unavailable to exercise the landing-site availability check
    cfg["facilities"]["V3"]["available"] = False
    return reg, FeasibilityChecker(reg, cfg)


def main() -> int:
    reg, checker = _build()
    cases = [
        ("busy_non_reassignable", {"type": "DISPATCH", "aircraft_id": "M-UAV-01",
                                   "mission_id": "M-SUPPORT-001", "target_site": "V1"}),
        ("unavailable_site", {"type": "DISPATCH", "aircraft_id": "L-UAV-01",
                              "mission_id": "M-SUPPORT-001", "target_site": "V3"}),
        ("insufficient_battery", {"type": "DISPATCH", "aircraft_id": "L-UAV-09",
                                  "mission_id": "M-SUPPORT-001", "target_site": "V1"}),
    ]

    rows = []
    ok = True
    for case_id, action in cases:
        res = checker.check(action)
        rows.append({
            "case_id": case_id,
            "action_type": action["type"],
            "aircraft_id": action["aircraft_id"],
            "mission_id": action["mission_id"],
            "target_site": action["target_site"],
            "valid": res["valid"],
            "violations": ";".join(res["violations"]),
        })
        rejected = (res["valid"] is False)
        ok = ok and rejected
        print(f"{case_id:22s}: valid={res['valid']}  violations={res['violations']}  "
              f"-> {'REJECTED' if rejected else 'NOT REJECTED'}")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\nfeasibility checker (post-resize): {'PASS' if ok else 'FAIL'} "
          f"(all 3 infeasible actions rejected)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
