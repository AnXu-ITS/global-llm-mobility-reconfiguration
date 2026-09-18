"""Experiment 2 — F2 (GNSS degradation) implementation audit (protocol §10)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from _exp2_audit_common import (final_summary, md5, read_csv, read_json,
                                read_jsonl, record, run_combo)  # noqa: E402

SCENARIO, SEED, MANAGER = "E2_F2_C2", 20240601, "B1"
RESULTS = []


def main() -> int:
    rd_a, r_a = run_combo(SCENARIO, SEED, MANAGER, "f2_a")
    rd_b, r_b = run_combo(SCENARIO, SEED, MANAGER, "f2_b")
    record("F2-run", r_a.returncode == 0 and r_b.returncode == 0,
           f"runs complete (rc={r_a.returncode},{r_b.returncode})")

    evs = read_csv(rd_a / "events.csv")
    gnss_ev = [e for e in evs if e["event_id"] == "GNSS_DEGRADED"]
    record("F2-1-event", len(gnss_ev) == 1 and int(gnss_ev[0]["t"]) == 360,
           f"GNSS_DEGRADED at t=360 x{len(gnss_ev)}")

    tr = read_json(rd_a / "failure_trace.json")
    before, after = tr["state_before"], tr["state_after"]
    m02b, m02a = before["aircraft"]["M-UAV-02"], after["aircraft"]["M-UAV-02"]
    ok_state = (m02b["status"] == "BUSY" and m02a["status"] == "DEGRADED"
                and m02a["gnss_status"] == "DEGRADED" and m02a["commandable"] is True)
    mb, ma = before["missions"]["M-CRITICAL-001"], after["missions"]["M-CRITICAL-001"]
    ok_mission = (mb["status"] == "EN_ROUTE" and ma["status"] == "NEEDS_REPLAN"
                  and ma["assigned_resource"] is None)
    record("F2-2-state", ok_state and ok_mission,
           f"M-UAV-02 {m02b['status']}->{m02a['status']} gnss={m02a['gnss_status']} "
           f"cmd={m02a['commandable']}; critical {mb['status']}->{ma['status']}")

    ok_unaffected = (before["aircraft"]["M-UAV-01"] == after["aircraft"]["M-UAV-01"]
                     and before["missions"]["M-L-001"] == after["missions"]["M-L-001"])
    record("F2-3-unaffected", ok_unaffected,
           "backup M-UAV-01 and logistics mission snapshots unchanged")

    inputs = read_jsonl(rd_a / "manager_inputs.jsonl")
    gs360 = next(x for x in inputs if x["simulation_time"] == 360)
    air360 = {a["id"]: a for a in gs360["air"]}
    zones = gs360["infrastructure"]["failure_zones"]
    visible = (air360["M-UAV-02"]["status"] == "DEGRADED"
               and air360["M-UAV-02"]["gnss_status"] == "DEGRADED"
               and any(z["id"] == "ZN-F2-02" and z["state"] == "CLOSED" for z in zones))
    record("F2-4-gs", visible,
           f"GS@360: M-UAV-02 status={air360['M-UAV-02']['status']}, "
           f"zone ZN-F2-02 CLOSED={any(z['id']=='ZN-F2-02' and z['state']=='CLOSED' for z in zones)}")

    cands = read_jsonl(rd_a / "candidate_info.jsonl")
    c360 = next(x for x in cands if x["t"] == 360)["candidate_table"]
    failed = [c for c in c360["air"] if c["resource_id"] == "M-UAV-02"]
    backup = [c for c in c360["air"] if c["resource_id"] == "M-UAV-01"]
    ok_cand = (failed and failed[0]["legal"] is False
               and "DEGRADED" in str(failed[0]["reject_reason"])
               and backup and backup[0]["legal"] is True
               and tr["candidate_count_after"] == 1)
    record("F2-5-candidates", ok_cand,
           f"M-UAV-02 legal={failed[0]['legal']} ({failed[0]['reject_reason']}), "
           f"M-UAV-01 legal={backup[0]['legal']}, count_after={tr['candidate_count_after']}")

    from orchestrator.registry import Aircraft, Mission, Registry
    from orchestrator import config as config_mod
    from safety.feasibility_checker_e2 import E2FeasibilityChecker
    cfg = config_mod.load_config()
    reg = Registry()
    reg.add_aircraft(Aircraft("M-UAV-02", "medical_uav", 31.3, 120.6, status="DEGRADED",
                              gnss_status="DEGRADED"))
    reg.add_aircraft(Aircraft("M-UAV-01", "medical_uav", 31.31, 120.6, status="AVAILABLE"))
    reg.add_mission(Mission("M-CRITICAL-001", "medical_blood", "CRITICAL", "V2", "V1",
                            deadline_s=480))
    chk = E2FeasibilityChecker(reg, cfg)
    r1 = chk.check({"type": "REASSIGN", "aircraft_id": "M-UAV-02",
                    "mission_id": "M-CRITICAL-001", "target_site": "V1"})
    r2 = chk.check({"type": "REASSIGN", "aircraft_id": "M-UAV-01",
                    "mission_id": "M-CRITICAL-001", "target_site": "V1"})
    record("F2-6-checker", (not r1["valid"] and "GNSS_DEGRADED_AIRCRAFT" in r1["violations"]
                            and r2["valid"]),
           f"degraded-aircraft REASSIGN rejected {r1['violations']}; backup valid={r2['valid']}")

    clk = read_csv(rd_a / "clock_sync.csv")
    seg = [r for r in clk if 355 <= int(r["t"]) <= 365]
    record("F2-7-clock", all(r["sync_ok"] == "True" for r in seg),
           f"clock sync_ok across t=355..365: {all(r['sync_ok']=='True' for r in seg)}")

    same = {n: md5(rd_a / n) == md5(rd_b / n)
            for n in ("events.csv", "actions.csv", "missions.csv", "clock_sync.csv")}
    record("F2-8-replay", all(same.values()), f"replay byte-identical: {same}")

    return final_summary()


if __name__ == "__main__":
    raise SystemExit(main())
