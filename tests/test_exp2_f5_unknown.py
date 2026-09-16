"""Experiment 2 — F5 (unknown aircraft / risk zone) implementation audit (protocol §10)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from _exp2_audit_common import (final_summary, md5, read_csv, read_json,
                                read_jsonl, record, run_combo)  # noqa: E402

SCENARIO, SEED, MANAGER = "E2_F5_C2", 20240601, "B1"


def main() -> int:
    rd_a, r_a = run_combo(SCENARIO, SEED, MANAGER, "f5_a")
    rd_b, r_b = run_combo(SCENARIO, SEED, MANAGER, "f5_b")
    record("F5-run", r_a.returncode == 0 and r_b.returncode == 0,
           f"runs complete (rc={r_a.returncode},{r_b.returncode})")

    evs = read_csv(rd_a / "events.csv")
    unk_ev = [e for e in evs if e["event_id"] == "UNKNOWN_AIRCRAFT"]
    ok_event = (len(unk_ev) == 1 and int(unk_ev[0]["t"]) == 360
                and json.loads(unk_ev[0]["payload"]).get("aircraft") == "UNKN-01")
    record("F5-1-event", ok_event, f"UNKNOWN_AIRCRAFT_INTRUSION at t=360 x{len(unk_ev)}")

    tr = read_json(rd_a / "failure_trace.json")
    before, after = tr["state_before"], tr["state_after"]
    mb, ma = before["missions"]["M-CRITICAL-001"], after["missions"]["M-CRITICAL-001"]
    ok_mission = (mb["status"] == "EN_ROUTE" and ma["status"] == "NEEDS_REPLAN"
                  and ma["assigned_resource"] is None)
    record("F5-2-state", ok_mission, f"critical {mb['status']}->{ma['status']}")

    ok_unaffected = before["aircraft"]["M-UAV-01"] == after["aircraft"]["M-UAV-01"]
    record("F5-3-unaffected", ok_unaffected, "backup M-UAV-01 (outside zone) unchanged")

    inputs = read_jsonl(rd_a / "manager_inputs.jsonl")
    gs360 = next(x for x in inputs if x["simulation_time"] == 360)
    zones = gs360["infrastructure"]["failure_zones"]
    zone_vis = any(z["id"] == "ZN-F5-02" and z["state"] == "CLOSED" for z in zones)
    event_vis = any(e.get("event_type") == "UNKNOWN_AIRCRAFT_INTRUSION" for e in gs360["events"])
    record("F5-4-gs", zone_vis and event_vis,
           f"GS@360 zone CLOSED={zone_vis}, intrusion event visible={event_vis}")

    cands = read_jsonl(rd_a / "candidate_info.jsonl")
    c360 = next(x for x in cands if x["t"] == 360)["candidate_table"]
    hit = [c for c in c360["air"] if c["resource_id"] == "M-UAV-02"]
    backup = [c for c in c360["air"] if c["resource_id"] == "M-UAV-01"]
    # the in-zone aircraft is illegal via the frozen priority filter (it keeps
    # its abandoned CRITICAL priority) and/or the zone rule — both are legal
    # gates; the zone rule itself is proven in F5-6 and on the backup route.
    ok_cand = (hit and hit[0]["legal"] is False
               and backup and backup[0]["legal"] is True
               and backup[0]["risk_zone_intersection"] is False
               and tr["candidate_count_after"] == 1)
    record("F5-5-candidates", ok_cand,
           f"in-zone aircraft illegal ({hit[0]['reject_reason']}); backup legal="
           f"{backup[0]['legal']} intersect={backup[0]['risk_zone_intersection']}")

    from failures.e2_failures import point_in_zone, route_intersects_zone
    zone = {"type": "circle", "lat": 31.304024142602, "lon": 120.59980924131,
            "radius_m": 100.0}
    ok_geom = (point_in_zone(31.3041812, 120.5999046, zone)      # critical aircraft
               and not point_in_zone(31.3108767, 120.6039862, zone)  # backup at V1
               and not route_intersects_zone(
                   [(31.3108767, 120.6039862), (31.3065604, 120.6027607)],
                   zone))  # V1->V3 leg stays clear
    from orchestrator.registry import Aircraft, Mission, Registry
    from orchestrator import config as config_mod
    from safety.feasibility_checker_e2 import E2FeasibilityChecker
    cfg = config_mod.load_config()
    reg = Registry()
    reg.add_aircraft(Aircraft("M-UAV-02", "medical_uav", 31.30418, 120.59990,
                              status="AVAILABLE"))
    reg.add_mission(Mission("M-CRITICAL-001", "medical_blood", "CRITICAL", "V2", "V1",
                            deadline_s=480))
    chk = E2FeasibilityChecker(reg, cfg)
    chk.set_failure_state({"utm_state": "NOMINAL", "new_mission_ids": set(),
                           "zones": [zone]})
    r1 = chk.check({"type": "DISPATCH", "aircraft_id": "M-UAV-02",
                    "mission_id": "M-CRITICAL-001", "target_site": "V1"})
    record("F5-6-checker", ok_geom and not r1["valid"] and "RISK_ZONE_VIOLATION" in r1["violations"],
           f"geometry checks={ok_geom}; in-zone DISPATCH rejected {r1['violations']}")

    clk = read_csv(rd_a / "clock_sync.csv")
    seg = [r for r in clk if 355 <= int(r["t"]) <= 365]
    record("F5-7-clock", all(r["sync_ok"] == "True" for r in seg),
           f"clock sync_ok across t=355..365: {all(r['sync_ok']=='True' for r in seg)}")

    same = {n: md5(rd_a / n) == md5(rd_b / n)
            for n in ("events.csv", "actions.csv", "missions.csv", "clock_sync.csv")}
    record("F5-8-replay", all(same.values()), f"replay byte-identical: {same}")

    return final_summary()


if __name__ == "__main__":
    raise SystemExit(main())
