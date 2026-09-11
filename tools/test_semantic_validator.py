"""Quick unit test for the SemanticValidator + resource compatibility."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from safety.semantic_validator import SemanticValidator  # noqa: E402

sv = SemanticValidator(str(ROOT / "config" / "resource_compatibility.yaml"))

gs = {
    "simulation_time": 300,
    "scenario_id": "S0",
    "air": [
        {"id": "M-UAV-01", "type": "medical_uav", "status": "AVAILABLE",
         "current_mission": None, "mission_priority": "NORMAL", "reassignable": True,
         "commandable": True, "c2_status": "NORMAL"},
        {"id": "M-UAV-02", "type": "medical_uav", "status": "AVAILABLE",
         "current_mission": None, "mission_priority": "NORMAL", "reassignable": True,
         "commandable": True, "c2_status": "NORMAL"},
        {"id": "L-UAV-01", "type": "logistics_uav", "status": "BUSY",
         "current_mission": "M-L-001", "mission_priority": "NORMAL", "reassignable": False,
         "commandable": True, "c2_status": "NORMAL"},
    ],
    "missions": {
        "new": [
            {"id": "M-CRITICAL-001", "type": "medical_blood", "priority": "CRITICAL",
             "state": "WAITING", "assigned_resource": None, "origin": "V2", "destination": "V1"},
        ],
        "existing": [
            {"id": "M-P-001", "type": "passenger_transfer", "priority": "NORMAL",
             "state": "WAITING", "assigned_resource": None, "origin": "V2", "destination": "V1"},
        ],
    },
    "infrastructure": {"landing_sites": {"V1": {"state": "AVAILABLE"}, "V2": {"state": "AVAILABLE"}}},
}


def check(name, action, g, expect_valid):
    r = sv.validate(action, g)
    ok = r["valid"] == expect_valid
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: valid={r['valid']} errors={r['error_types']}")
    return ok


results = []
# 1. medical_uav -> medical_blood (allowed)
results.append(check("medical->blood allowed",
                     {"type": "DISPATCH", "aircraft_id": "M-UAV-01",
                      "mission_id": "M-CRITICAL-001", "target_site": "V1"}, gs, True))
# 2. medical_uav -> passenger_transfer (denied)
results.append(check("medical->passenger denied",
                     {"type": "DISPATCH", "aircraft_id": "M-UAV-01",
                      "mission_id": "M-P-001", "target_site": "V1"}, gs, False))
# 3. unknown resource
results.append(check("unknown resource",
                     {"type": "DISPATCH", "aircraft_id": "GHOST",
                      "mission_id": "M-CRITICAL-001", "target_site": "V1"}, gs, False))
# 4. unknown mission
results.append(check("unknown mission",
                     {"type": "DISPATCH", "aircraft_id": "M-UAV-01",
                      "mission_id": "GHOST", "target_site": "V1"}, gs, False))
# 5. duplicate assignment (mission already held by an active aircraft)
g5 = json.loads(json.dumps(gs))
g5["missions"]["new"][0]["assigned_resource"] = "M-UAV-02"
g5["missions"]["new"][0]["state"] = "EN_ROUTE"
results.append(check("duplicate assignment",
                     {"type": "REASSIGN", "aircraft_id": "M-UAV-01",
                      "mission_id": "M-CRITICAL-001", "target_site": "V1"}, g5, False))
# 6. medical_uav -> logistics with a pending HIGH medical mission (strategic reserve -> denied)
g6 = json.loads(json.dumps(gs))
g6["missions"]["new"][0]["state"] = "NEEDS_REPLAN"  # pending critical medical mission
g6["missions"]["existing"].append(
    {"id": "M-L-EXTRA", "type": "logistics", "priority": "NORMAL",
     "state": "WAITING", "assigned_resource": None, "origin": "V2", "destination": "V3"})
results.append(check("medical->logistics w/ pending medical (denied)",
                     {"type": "DISPATCH", "aircraft_id": "M-UAV-01",
                      "mission_id": "M-L-EXTRA", "target_site": "V3"}, g6, False))
# 7. logistics_uav -> medical when a medical UAV is available (conditional -> denied)
results.append(check("logistics->medical w/ available medical (denied)",
                     {"type": "DISPATCH", "aircraft_id": "L-UAV-01",
                      "mission_id": "M-CRITICAL-001", "target_site": "V1"}, gs, False))

print(f"\n{sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
