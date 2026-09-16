"""Experiment 2 — F1 (C2 Lost Link) implementation audit (protocol §10).

Proves the 8 audit points for the F1 family using the canonical runner
(E2_F1_C2, seed 20240601, B1) plus in-process checker assertions.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from _exp2_audit_common import (final_summary, md5, read_csv, read_json,
                                read_jsonl, record, run_combo)  # noqa: E402

SCENARIO, SEED, MANAGER = "E2_F1_C2", 20240601, "B1"
RESULTS = []


def main() -> int:
    # two identical runs for the replay point
    rd_a, r_a = run_combo(SCENARIO, SEED, MANAGER, "f1_a")
    rd_b, r_b = run_combo(SCENARIO, SEED, MANAGER, "f1_b")
    record("F1-run", r_a.returncode == 0 and r_b.returncode == 0,
           f"runs complete (rc={r_a.returncode},{r_b.returncode})")

    # 1. failure event fires
    evs = read_csv(rd_a / "events.csv")
    c2_ev = [e for e in evs if e["event_id"] == "C2_LOST"]
    lc_ev = [e for e in evs if e["event_id"] == "LOCAL_CONTINGENCY"]
    record("F1-1-event", len(c2_ev) == 1 and int(c2_ev[0]["t"]) == 360
           and len(lc_ev) == 1 and int(lc_ev[0]["t"]) == 360,
           f"C2_LOST at t=360 x{len(c2_ev)}, LOCAL_CONTINGENCY x{len(lc_ev)}")

    # 2. affected state changes per the frozen F1 semantics
    tr = read_json(rd_a / "failure_trace.json")
    before, after = tr["state_before"], tr["state_after"]
    m02b, m02a = before["aircraft"]["M-UAV-02"], after["aircraft"]["M-UAV-02"]
    ok_state = (m02b["status"] == "BUSY" and m02a["status"] == "CONTINGENCY"
                and m02a["c2_status"] == "LOST" and m02a["commandable"] is False
                and m02a["reassignable"] is False)
    mb, ma = before["missions"]["M-CRITICAL-001"], after["missions"]["M-CRITICAL-001"]
    ok_mission = (mb["status"] == "EN_ROUTE" and ma["status"] == "NEEDS_REPLAN"
                  and ma["assigned_resource"] is None)
    record("F1-2-state", ok_state and ok_mission,
           f"M-UAV-02 {m02b['status']}->{m02a['status']} c2={m02a['c2_status']} "
           f"cmd={m02a['commandable']}; critical {mb['status']}->{ma['status']}")

    # 3. unaffected state unchanged
    ok_unaffected = (before["aircraft"]["L-UAV-01"] == after["aircraft"]["L-UAV-01"]
                     and before["aircraft"]["EVTOL-01"] == after["aircraft"]["EVTOL-01"]
                     and before["missions"]["M-L-001"] == after["missions"]["M-L-001"]
                     and before["missions"]["M-P-001"] == after["missions"]["M-P-001"])
    record("F1-3-unaffected", ok_unaffected,
           "L-UAV-01 / EVTOL-01 / M-L-001 / M-P-001 snapshots unchanged")

    # 4. failure visible in the Global State (t=360 decision input)
    inputs = read_jsonl(rd_a / "manager_inputs.jsonl")
    gs360 = next(x for x in inputs if x["simulation_time"] == 360)
    air360 = {a["id"]: a for a in gs360["air"]}
    visible = (air360["M-UAV-02"]["status"] == "CONTINGENCY"
               and air360["M-UAV-02"]["c2_status"] == "LOST"
               and air360["M-UAV-02"]["commandable"] is False
               and any(e.get("event_type") == "C2_LOST" for e in gs360["events"]))
    record("F1-4-gs", visible,
           f"GS@360: M-UAV-02 status={air360['M-UAV-02']['status']}, "
           f"c2={air360['M-UAV-02']['c2_status']}, events include C2_LOST={visible}")

    # 5. candidate generator updates
    cands = read_jsonl(rd_a / "candidate_info.jsonl")
    c360 = next(x for x in cands if x["t"] == 360)["candidate_table"]
    failed = [c for c in c360["air"] if c["resource_id"] == "M-UAV-02"]
    backup = [c for c in c360["air"] if c["resource_id"] == "M-UAV-01"]
    ok_cand = (failed and failed[0]["legal"] is False
               and ("CONTINGENCY" in str(failed[0]["reject_reason"])
                    or "C2 status" in str(failed[0]["reject_reason"]))
               and backup and backup[0]["legal"] is True
               and tr["candidate_count_after"] == 1)
    record("F1-5-candidates", ok_cand,
           f"M-UAV-02 legal={failed[0]['legal']} ({failed[0]['reject_reason']}), "
           f"M-UAV-01 legal={backup[0]['legal']}, count_after={tr['candidate_count_after']}")

    # 6. checker enforces the hard constraint (in-process)
    from orchestrator.registry import Aircraft, Mission, Registry
    from orchestrator import config as config_mod
    from safety.feasibility_checker_e2 import E2FeasibilityChecker
    cfg = config_mod.load_config()
    reg = Registry()
    reg.add_aircraft(Aircraft("M-UAV-02", "medical_uav", 31.3, 120.6, status="CONTINGENCY",
                              commandable=False, c2_status="LOST"))
    reg.add_aircraft(Aircraft("M-UAV-01", "medical_uav", 31.31, 120.6, status="AVAILABLE"))
    reg.add_mission(Mission("M-CRITICAL-001", "medical_blood", "CRITICAL", "V2", "V1",
                            deadline_s=480))
    chk = E2FeasibilityChecker(reg, cfg)
    r1 = chk.check({"type": "REASSIGN", "aircraft_id": "M-UAV-02",
                    "mission_id": "M-CRITICAL-001", "target_site": "V1"})
    r2 = chk.check({"type": "REASSIGN", "aircraft_id": "M-UAV-01",
                    "mission_id": "M-CRITICAL-001", "target_site": "V1"})
    record("F1-6-checker", (not r1["valid"] and "AIRCRAFT_IN_CONTINGENCY" in r1["violations"]
                            and "AIRCRAFT_NOT_COMMANDABLE" in r1["violations"]
                            and r2["valid"]),
           f"failed-aircraft REASSIGN rejected {r1['violations']}; healthy backup valid={r2['valid']}")

    # 7. clock unaffected around the failure
    clk = read_csv(rd_a / "clock_sync.csv")
    seg = [r for r in clk if 355 <= int(r["t"]) <= 365]
    ok_clk = all(r["sync_ok"] == "True" for r in seg)
    record("F1-7-clock", ok_clk, f"clock sync_ok across t=355..365: {ok_clk}")

    # 8. deterministic replay
    same = {n: md5(rd_a / n) == md5(rd_b / n)
            for n in ("events.csv", "actions.csv", "missions.csv", "clock_sync.csv")}
    record("F1-8-replay", all(same.values()), f"replay byte-identical: {same}")

    return final_summary()


if __name__ == "__main__":
    raise SystemExit(main())
