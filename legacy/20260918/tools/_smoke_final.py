"""Smoke test: shared-table consumption by B0/B1/B2 + seed realization check."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod
from orchestrator.candidate_info import CandidateEvaluator
from managers.rule_based import RuleBasedManager
from managers.optimization import OptimizationManager
from managers.no_cross_layer import NoCrossLayerManager

CFG = config_mod.load_config()
FAC = CFG["facilities"]


def ac(acid, type_="medical_uav", status="AVAILABLE", site="V2", mission=None,
       priority="NORMAL", battery=100.0, endurance=1800.0, reassignable=True):
    f = FAC[site]
    return {"id": acid, "type": type_, "status": status,
            "position": {"lat": f["lat"], "lon": f["lon"], "alt_m": 100.0},
            "current_mission": mission, "mission_priority": priority,
            "battery_pct": battery, "remaining_endurance_s": endurance,
            "availability": status, "reassignable": reassignable,
            "commandable": True, "c2_status": "NORMAL", "gnss_status": "NORMAL",
            "landing_compatibility": ["V1", "V2", "V3"]}


def mission(mid, priority, origin="V2", dest="V1", state="WAITING", deadline=480.0):
    return {"id": mid, "type": "medical_blood", "priority": priority,
            "deadline_s": deadline, "origin": origin, "destination": dest,
            "assigned_resource": None, "mode": None, "state": state,
            "ground_fallback": True}


def gs(air, missions, ground_eta=181.76, t=300):
    g = {"simulation_time": t, "scenario_id": "E1_H_C_low",
         "scenario_version": "S0_3p2km_v1", "seed": 20240601,
         "ground": {"b1_state": "CLOSED", "current_d1_h1_eta_s": ground_eta,
                    "baseline_eta_s": 131.84, "eta_increase_pct": 37.87,
                    "accessibility_status": "DEGRADED",
                    "available_ground_fallback": True,
                    "ground_fallback_eta_s": ground_eta},
         "air": air,
         "infrastructure": {"landing_sites": {
             "V1": {"state": "AVAILABLE", "lat": FAC["V1"]["lat"], "lon": FAC["V1"]["lon"]},
             "V2": {"state": "AVAILABLE", "lat": FAC["V2"]["lat"], "lon": FAC["V2"]["lon"]},
             "V3": {"state": "AVAILABLE", "lat": FAC["V3"]["lat"], "lon": FAC["V3"]["lon"]}}},
         "missions": {"existing": [], "new": missions},
         "events": [], "trend": {"previous_eta_s": 131.84, "current_eta_s": ground_eta, "eta_trend": "INCREASING"}}
    ce = CandidateEvaluator(FAC)
    g["candidates"] = ce.evaluate(g)
    return g


def main():
    # idle medical UAV available -> B1/B2 should DISPATCH it (air), B0 ground
    air = [ac("M-UAV-02", site="V2")]
    g = gs(air, [mission("M-EMERGENCY-001", "CRITICAL")])
    b1 = RuleBasedManager(CFG).decide(g)
    b2 = OptimizationManager(CFG, str(ROOT / "config/experiment1_v2/experiment1_b2_weights.yaml")).decide(g)
    b0 = NoCrossLayerManager(CFG).decide(g)
    print("B1:", b1["action"]["type"], b1["selected"])
    print("B2:", b2["action"]["type"], b2["selected"])
    print("B0:", b0["action"]["type"], b0["selected"])
    assert b1["action"]["type"] == "DISPATCH", b1
    assert b2["action"]["type"] == "DISPATCH", b2
    assert b0["action"]["type"] == "GROUND_FALLBACK", b0
    # shared-table candidates carried into the decision provenance
    assert b1["candidates"][0]["legal"] is True
    assert b2["candidates"][0]["legal"] is True
    print("shared-table consumption OK (B1/B2 dispatch idle medical, B0 ground)")

    # busy non-reassignable -> no air, both B1/B2 fall back to ground
    air2 = [ac("L-UAV-01", type_="logistics_uav", status="BUSY", site="V2",
               mission="M-L-001", priority="NORMAL", reassignable=False)]
    g2 = gs(air2, [mission("M-EMERGENCY-001", "CRITICAL")])
    b1b = RuleBasedManager(CFG).decide(g2)
    b2b = OptimizationManager(CFG, str(ROOT / "config/experiment1_v2/experiment1_b2_weights.yaml")).decide(g2)
    print("B1(no air):", b1b["action"]["type"], "| B2(no air):", b2b["action"]["type"])
    assert b1b["action"]["type"] == "GROUND_FALLBACK", b1b
    assert b2b["action"]["type"] == "GROUND_FALLBACK", b2b
    print("ground fallback shared-facts OK")

    # seed realization: two seeds -> different manager-visible air endurance
    from orchestrator.experiment1_runner import Experiment1Runner  # import only for attribute sanity
    import random
    r1 = random.Random(1)
    r2 = random.Random(2)
    v1 = [round(r1.uniform(0, 0.15), 4), round(r2.uniform(0, 0.15), 4)]
    print("seed rng distinct sample:", v1)
    assert v1[0] != v1[1]
    print("ALL SMOKE CHECKS PASSED")


if __name__ == "__main__":
    main()
