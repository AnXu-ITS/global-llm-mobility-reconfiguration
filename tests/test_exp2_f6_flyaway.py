"""Experiment 2 — F6 (flyaway / uncontrolled trajectory) implementation audit (protocol §10)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from _exp2_audit_common import (final_summary, md5, read_csv, read_json,
                                read_jsonl, record, run_combo)  # noqa: E402

SCENARIO, SEED, MANAGER = "E2_F6_C2", 20240601, "B1"


def main() -> int:
    rd_a, r_a = run_combo(SCENARIO, SEED, MANAGER, "f6_a")
    rd_b, r_b = run_combo(SCENARIO, SEED, MANAGER, "f6_b")
    record("F6-run", r_a.returncode == 0 and r_b.returncode == 0,
           f"runs complete (rc={r_a.returncode},{r_b.returncode})")

    evs = read_csv(rd_a / "events.csv")
    fly_ev = [e for e in evs if e["event_id"] == "FLYAWAY"]
    ok_event = (len(fly_ev) == 1 and int(fly_ev[0]["t"]) == 360
                and json.loads(fly_ev[0]["payload"]).get("aircraft") == "L-UAV-01"
                and json.loads(fly_ev[0]["payload"]).get("trajectory_mode")
                == "UNCONTROLLED_PREDEFINED")
    record("F6-1-event", ok_event, f"FLYAWAY_UNCONTROLLED at t=360 x{len(fly_ev)}")

    tr = read_json(rd_a / "failure_trace.json")
    before, after = tr["state_before"], tr["state_after"]
    l01b, l01a = before["aircraft"]["L-UAV-01"], after["aircraft"]["L-UAV-01"]
    ok_flyaway = (l01b["status"] == "BUSY" and l01a["status"] == "CONTINGENCY"
                  and l01a["commandable"] is False and l01a["reassignable"] is False)
    mb, ma = before["missions"]["M-CRITICAL-001"], after["missions"]["M-CRITICAL-001"]
    ok_mission = mb["status"] == "EN_ROUTE" and ma["status"] == "NEEDS_REPLAN"
    record("F6-2-state", ok_flyaway and ok_mission,
           f"L-UAV-01 {l01b['status']}->{l01a['status']} cmd={l01a['commandable']}; "
           f"critical {mb['status']}->{ma['status']}")

    ok_unaffected = before["aircraft"]["M-UAV-01"] == after["aircraft"]["M-UAV-01"]
    record("F6-3-unaffected", ok_unaffected, "backup M-UAV-01 (outside envelope) unchanged")

    inputs = read_jsonl(rd_a / "manager_inputs.jsonl")
    gs360 = next(x for x in inputs if x["simulation_time"] == 360)
    air360 = {a["id"]: a for a in gs360["air"]}
    zones = gs360["infrastructure"]["failure_zones"]
    visible = (air360["L-UAV-01"]["status"] == "CONTINGENCY"
               and air360["L-UAV-01"]["commandable"] is False
               and any(z["id"] == "ENV-F6-02" and z["state"] == "CLOSED" for z in zones))
    record("F6-4-gs", visible,
           f"GS@360 L-UAV-01={air360['L-UAV-01']['status']}, "
           f"envelope CLOSED={any(z['id']=='ENV-F6-02' and z['state']=='CLOSED' for z in zones)}")

    cands = read_jsonl(rd_a / "candidate_info.jsonl")
    c360 = next(x for x in cands if x["t"] == 360)["candidate_table"]
    hit = [c for c in c360["air"] if c["resource_id"] == "M-UAV-02"]
    backup = [c for c in c360["air"] if c["resource_id"] == "M-UAV-01"]
    ok_cand = (hit and hit[0]["legal"] is False
               and backup and backup[0]["legal"] is True
               and tr["candidate_count_after"] == 1)
    record("F6-5-candidates", ok_cand,
           f"envelope-crossing aircraft illegal ({hit[0]['reject_reason']}); "
           f"backup legal={backup[0]['legal']}, count_after={tr['candidate_count_after']}")

    from failures.e2_failures import point_in_zone
    strip = {"type": "strip", "lat0": 31.3010, "lon0": 120.5970,
             "heading_deg": 20.0, "half_width_m": 200.0, "length_m": 2000.0}
    ok_geom = (point_in_zone(31.3041812, 120.5999046, strip)      # critical aircraft
               and not point_in_zone(31.3108767, 120.6039862, strip))  # backup at V1
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
                           "zones": [strip]})
    r1 = chk.check({"type": "DISPATCH", "aircraft_id": "M-UAV-02",
                    "mission_id": "M-CRITICAL-001", "target_site": "V1"})
    record("F6-6-checker", ok_geom and not r1["valid"] and "RISK_ZONE_VIOLATION" in r1["violations"],
           f"geometry checks={ok_geom}; in-envelope DISPATCH rejected {r1['violations']}")

    clk = read_csv(rd_a / "clock_sync.csv")
    seg = [r for r in clk if 355 <= int(r["t"]) <= 365]
    record("F6-7-clock", all(r["sync_ok"] == "True" for r in seg),
           f"clock sync_ok across t=355..365: {all(r['sync_ok']=='True' for r in seg)}")

    same = {n: md5(rd_a / n) == md5(rd_b / n)
            for n in ("events.csv", "actions.csv", "missions.csv", "clock_sync.csv")}
    record("F6-8-replay", all(same.values()), f"replay byte-identical: {same}")

    return final_summary()


if __name__ == "__main__":
    raise SystemExit(main())
