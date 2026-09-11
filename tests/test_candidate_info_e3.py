"""Pure-Python regression test for the E3 candidate-table extension (2.2.0).

Verifies the multi-mission section emission guard and the leakage contract
without requiring SUMO / BlueSky. The candidate evaluator chain is pure Python.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.candidate_info_e3 import E3CandidateEvaluator  # noqa: E402

FAC = {
    "V1": {"lat": 31.3040, "lon": 120.5985},
    "V2": {"lat": 31.3030, "lon": 120.6000},
    "V3": {"lat": 31.3065, "lon": 120.6027},
}


def _aircraft(acid, status, lat, lon, typ="medical_uav", reassignable=True,
              current_mission=None, mission_priority=None):
    return {
        "id": acid, "type": typ, "status": status,
        "position": {"lat": lat, "lon": lon, "alt_m": 60.0},
        "current_mission": current_mission, "mission_priority": mission_priority,
        "battery_pct": 100.0, "remaining_endurance_s": 1800.0,
        "availability": status, "reassignable": reassignable,
        "commandable": True, "c2_status": "NORMAL", "gnss_status": "NORMAL",
        "landing_compatibility": ["V1", "V2", "V3"],
    }


def _mission(mid, typ, pri, origin, dest, state, deadline_s=480.0,
             ground_fallback=True):
    return {"id": mid, "type": typ, "priority": pri, "origin": origin,
            "destination": dest, "state": state, "deadline_s": deadline_s,
            "ground_fallback": ground_fallback, "assigned_resource": None,
            "mode": None, "delay_cost": 10.0, "cancellation_cost": 100.0}


def _gs(actionable_new, actionable_existing=None):
    air = [
        _aircraft("M-UAV-01", "AVAILABLE", 31.3040, 120.5985),
        _aircraft("M-UAV-02", "AVAILABLE", 31.3030, 120.6000),
        _aircraft("L-UAV-01", "BUSY", 31.3030, 120.6000, typ="logistics_uav",
                  reassignable=False, current_mission="M-L-001",
                  mission_priority="NORMAL"),
        _aircraft("EVTOL-01", "BUSY", 31.3030, 120.6000, typ="passenger_evtol",
                  reassignable=False, current_mission="M-P-001",
                  mission_priority="NORMAL"),
    ]
    existing = list(actionable_existing or [])
    existing += [
        _mission("M-L-001", "logistics", "NORMAL", "V2", "V3", "EN_ROUTE", 1800.0),
        _mission("M-P-001", "passenger_transfer", "NORMAL", "V2", "V1", "EN_ROUTE", 1800.0),
    ]
    gs = {
        "simulation_time": 300,
        "air": air,
        "ground": {"ground_fallback_eta_s": 180.0, "available_ground_fallback": True,
                   "current_d1_h1_eta_s": 180.0},
        "infrastructure": {
            "landing_sites": {"V1": {"state": "AVAILABLE"}, "V2": {"state": "AVAILABLE"},
                              "V3": {"state": "AVAILABLE"}},
            "utm_state": "NOMINAL", "failure_zones": [],
        },
        "missions": {"new": list(actionable_new), "existing": existing},
    }
    return gs


def _no_leakage(table):
    s = str(table)
    for banned in ("objective", "score", "ranking", "recommendation", "best_candidate",
                   "recommended_action", "shadow_price"):
        assert banned not in s.lower(), f"leakage keyword {banned} found"
    return True


def main():
    ev = E3CandidateEvaluator(FAC, dispatch_overhead_s=0.0, contingency_site="V3")

    # 1) single actionable mission -> NO mission_candidates (byte-compat guard)
    crit = _mission("M-CRITICAL-001", "medical_blood", "CRITICAL", "V2", "V1", "WAITING")
    t1 = ev.evaluate(_gs([crit]))
    assert "mission_candidates" not in t1, "single-mission guard failed"
    assert t1["summary"]["candidate_table_version"] == "2.2.0"
    assert t1["summary"]["target_mission_id"] == "M-CRITICAL-001"
    assert _no_leakage(t1)

    # 2) two actionable missions -> mission_candidates with 2 entries
    crit2 = _mission("M-CRITICAL-002", "medical_organ", "HIGH", "V3", "V1", "WAITING",
                     deadline_s=630.0)
    t2 = ev.evaluate(_gs([crit, crit2]))
    assert "mission_candidates" in t2, "multi-mission section missing"
    mc = t2["mission_candidates"]
    assert len(mc) == 2
    ids = [e["mission_id"] for e in mc]
    assert ids == ["M-CRITICAL-001", "M-CRITICAL-002"], ids  # CRITICAL before HIGH
    assert all(set(e) >= {"mission_id", "priority", "origin", "destination",
                          "deadline_s", "state", "air", "ground"} for e in mc)
    assert _no_leakage(t2)

    # 3) an actionable existing mission (NEEDS_REPLAN) is also counted
    replan = _mission("M-L-001", "logistics", "NORMAL", "V2", "V3", "NEEDS_REPLAN", 1800.0)
    t3 = ev.evaluate(_gs([crit], actionable_existing=[replan]))
    assert "mission_candidates" in t3
    assert len(t3["mission_candidates"]) == 2

    print("TEST_CANDIDATE_INFO_E3 PASS")


if __name__ == "__main__":
    main()
