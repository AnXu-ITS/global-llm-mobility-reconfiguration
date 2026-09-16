"""Rule-Based Manager (B1) unit tests — no simulator required.

Covers the Phase-2 rule set:
  1. normal dispatch
  2. critical mission prioritisation
  3. busy (non-reassignable) aircraft rejection
  4. insufficient battery rejection
  5. failed / incompatible landing site rejection
  6. no-air-resource -> ground fallback
  7. priority conflict (no preempting a higher-priority mission)
  + rule 5 (min completion time) and rule 6 (tie -> endurance margin)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod            # noqa: E402
from managers.rule_based import RuleBasedManager         # noqa: E402

CFG = config_mod.load_config()
MGR = RuleBasedManager(CFG)
FAC = CFG["facilities"]

RESULTS = []


def record(name, passed, evidence):
    RESULTS.append((name, passed, evidence))
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: {evidence}")


def ac(acid="A1", type_="medical_uav", status="AVAILABLE", site="V2",
       mission=None, priority="NORMAL", battery=100.0, endurance=1800.0,
       reassignable=True, c2="NORMAL", commandable=True, landing=None):
    f = FAC[site]
    return {
        "id": acid, "type": type_, "status": status,
        "position": {"lat": f["lat"], "lon": f["lon"], "alt_m": 100.0},
        "current_mission": mission, "mission_priority": priority,
        "battery_pct": battery, "remaining_endurance_s": endurance,
        "availability": status, "reassignable": reassignable,
        "commandable": commandable, "c2_status": c2, "gnss_status": "NORMAL",
        "landing_compatibility": landing or ["V1", "V2", "V3"],
    }


def mission(mid="M1", priority="NORMAL", origin="V2", dest="V1",
            state="WAITING", ground_fallback=True, deadline=900.0):
    return {"id": mid, "type": "medical_blood", "priority": priority,
            "deadline_s": deadline, "origin": origin, "destination": dest,
            "assigned_resource": None, "mode": None, "state": state,
            "ground_fallback": ground_fallback}


def gs(missions, air, ground_eta=181.76, events=None, t=300):
    return {
        "simulation_time": t,
        "scenario_id": "S0",
        "scenario_version": "S0_3p2km_v1",
        "seed": 20240601,
        "ground": {
            "b1_state": "CLOSED",
            "current_d1_h1_eta_s": ground_eta,
            "baseline_eta_s": 131.84,
            "eta_increase_pct": 37.87,
            "accessibility_status": "DEGRADED",
            "available_ground_fallback": True,
            "ground_fallback_eta_s": ground_eta,
        },
        "air": air,
        "infrastructure": {},
        "missions": {"existing": [], "new": missions},
        "events": events or [],
        "trend": {"previous_eta_s": 131.84, "current_eta_s": ground_eta, "eta_trend": "INCREASING"},
    }


def test_normal_dispatch():
    d = MGR.decide(gs([mission("M1", "NORMAL")], [ac("A1")]))
    ok = (d["selected"]["type"] == "AIR" and d["selected"]["resource"] == "A1"
          and d["action"]["type"] == "DISPATCH")
    record("normal dispatch", ok, f"selected={d['selected']}, action={d['action']}")


def test_critical_mission_priority():
    d = MGR.decide(gs([mission("M-N", "NORMAL"), mission("M-C", "CRITICAL")],
                      [ac("A1")]))
    ok = d["mission_id"] == "M-C"
    record("critical mission prioritised", ok,
           f"target mission={d['mission_id']} (expected M-C)")


def test_busy_aircraft_rejected():
    air = [ac("A1", status="BUSY", mission="M-L", reassignable=False)]
    d = MGR.decide(gs([mission("M1", "CRITICAL")], air))
    cand = d["candidates"][0]
    ok = (cand["feasible"] is False and cand["reject_reason"] == "busy non-reassignable")
    record("busy non-reassignable rejected", ok,
           f"reject_reason={cand['reject_reason']}")


def test_insufficient_battery_rejected():
    air = [ac("A1", battery=0.0)]
    d = MGR.decide(gs([mission("M1", "CRITICAL")], air))
    cand = d["candidates"][0]
    ok = cand["feasible"] is False and cand["reject_reason"] == "insufficient battery"
    record("insufficient battery rejected", ok, f"reject_reason={cand['reject_reason']}")


def test_failed_landing_site_rejected():
    air = [ac("A1", landing=["V2", "V3"])]  # V1 not compatible
    d = MGR.decide(gs([mission("M1", "CRITICAL", dest="V1")], air))
    cand = d["candidates"][0]
    ok = cand["feasible"] is False and "incompatible" in cand["reject_reason"]
    record("failed landing site rejected", ok, f"reject_reason={cand['reject_reason']}")


def test_no_air_fallback():
    air = [ac("A1", status="BUSY", mission="M-L", reassignable=False)]
    d = MGR.decide(gs([mission("M1", "CRITICAL", ground_fallback=True)], air))
    ok = (d["selected"]["type"] == "GROUND" and d["action"]["type"] == "GROUND_FALLBACK")
    record("no-air-resource ground fallback", ok,
           f"selected={d['selected']}, action={d['action']}")


def test_priority_conflict():
    # target NORMAL, current HIGH (reassignable) -> must NOT preempt
    air = [ac("A1", status="BUSY", mission="M-HIGH", priority="HIGH", reassignable=True)]
    d = MGR.decide(gs([mission("M1", "NORMAL")], air))
    cand = d["candidates"][0]
    no_preempt = cand["feasible"] is False and "preempt" in cand["reject_reason"]
    # target CRITICAL, current NORMAL (reassignable) -> preemption allowed
    air2 = [ac("A1", status="BUSY", mission="M-L", priority="NORMAL", reassignable=True)]
    d2 = MGR.decide(gs([mission("M1", "CRITICAL")], air2))
    allowed = d2["candidates"][0]["feasible"] is True
    record("priority conflict (no preempt higher)", no_preempt and allowed,
           f"lower-vs-higher reject={cand['reject_reason']}; higher-vs-lower feasible={allowed}")


def test_min_completion_time():
    air = [ac("A1", site="V2"), ac("A2", site="V3")]
    d = MGR.decide(gs([mission("M1", "CRITICAL", origin="V2", dest="V1")], air))
    etas = {c["resource_id"]: c["eta_s"] for c in d["candidates"]}
    ok = d["selected"]["resource"] == "A1" and etas["A1"] < etas["A2"]
    record("rule5 min completion time", ok, f"etas={ {k: round(v,1) for k,v in etas.items()} }, selected={d['selected']['resource']}")


def test_tie_endurance_margin():
    air = [ac("A1", site="V2", endurance=1200.0), ac("A2", site="V2", endurance=900.0)]
    d = MGR.decide(gs([mission("M1", "CRITICAL", origin="V2", dest="V1")], air))
    ok = d["selected"]["resource"] == "A1"
    record("rule6 tie -> endurance margin", ok, f"selected={d['selected']['resource']}")


def main() -> int:
    test_normal_dispatch()
    test_critical_mission_priority()
    test_busy_aircraft_rejected()
    test_insufficient_battery_rejected()
    test_failed_landing_site_rejected()
    test_no_air_fallback()
    test_priority_conflict()
    test_min_completion_time()
    test_tie_endurance_margin()
    print()
    npass = sum(1 for _, p, _ in RESULTS if p)
    print(f"SUMMARY: {npass}/{len(RESULTS)} passed")
    return 0 if npass == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
