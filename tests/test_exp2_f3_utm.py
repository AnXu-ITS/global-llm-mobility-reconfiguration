"""Experiment 2 — F3 (UTM/U-space outage) implementation audit (protocol §10)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from _exp2_audit_common import (final_summary, md5, read_csv, read_json,
                                read_jsonl, record, run_combo)  # noqa: E402

SCENARIO, SEED, MANAGER = "E2_F3_C3", 20240601, "B1"


def main() -> int:
    rd_a, r_a = run_combo(SCENARIO, SEED, MANAGER, "f3_a")
    rd_b, r_b = run_combo(SCENARIO, SEED, MANAGER, "f3_b")
    record("F3-run", r_a.returncode == 0 and r_b.returncode == 0,
           f"runs complete (rc={r_a.returncode},{r_b.returncode})")

    evs = read_csv(rd_a / "events.csv")
    utm_ev = [e for e in evs if e["event_id"] == "UTM_STATE_CHANGE"]
    ok_event = (len(utm_ev) == 1 and int(utm_ev[0]["t"]) == 360
                and json.loads(utm_ev[0]["payload"]).get("utm_state") == "OUTAGE")
    record("F3-1-event", ok_event, f"UTM_STATE_CHANGE at t=360 x{len(utm_ev)}")

    tr = read_json(rd_a / "failure_trace.json")
    before, after = tr["state_before"], tr["state_after"]
    mb, ma = before["missions"]["M-CRITICAL-001"], after["missions"]["M-CRITICAL-001"]
    ok_mission = (mb["status"] == "EN_ROUTE" and ma["status"] == "NEEDS_REPLAN"
                  and ma["assigned_resource"] is None)
    mab, maa = before["missions"]["M-L-001"], after["missions"]["M-L-001"]
    ok_bg = mab["status"] == "EN_ROUTE" and maa["status"] == "NEEDS_REPLAN"
    record("F3-2-state", ok_mission and ok_bg,
           f"critical {mb['status']}->{ma['status']}; M-L-001 {mab['status']}->{maa['status']}")

    ok_unaffected = (before["aircraft"]["M-UAV-01"] == after["aircraft"]["M-UAV-01"])
    record("F3-3-unaffected", ok_unaffected, "idle backup M-UAV-01 snapshot unchanged")

    inputs = read_jsonl(rd_a / "manager_inputs.jsonl")
    gs360 = next(x for x in inputs if x["simulation_time"] == 360)
    ok_gs = gs360["infrastructure"]["utm_state"] == "OUTAGE"
    record("F3-4-gs", ok_gs, f"GS@360 utm_state={gs360['infrastructure']['utm_state']}")

    cands = read_jsonl(rd_a / "candidate_info.jsonl")
    c360 = next(x for x in cands if x["t"] == 360)["candidate_table"]
    air_illegal = all(c["legal"] is False for c in c360["air"])
    utm_reasons = [c for c in c360["air"] if "UTM" in str(c["reject_reason"])]
    ground_legal = c360["ground"]["legal"] is True
    record("F3-5-candidates",
           air_illegal and ground_legal and tr["candidate_count_after"] == 0
           and len(utm_reasons) >= 1,
           f"all air illegal under OUTAGE={air_illegal}, UTM-coded reasons="
           f"{len(utm_reasons)}, ground legal={ground_legal}, "
           f"count_after={tr['candidate_count_after']}")

    from orchestrator.registry import Aircraft, Mission, Registry
    from orchestrator import config as config_mod
    from safety.feasibility_checker_e2 import E2FeasibilityChecker
    cfg = config_mod.load_config()
    reg = Registry()
    reg.add_aircraft(Aircraft("M-UAV-01", "medical_uav", 31.31, 120.6, status="AVAILABLE"))
    reg.add_mission(Mission("M-CRITICAL-001", "medical_blood", "CRITICAL", "V2", "V1",
                            deadline_s=480))
    chk = E2FeasibilityChecker(reg, cfg)
    chk.set_failure_state({"utm_state": "OUTAGE", "new_mission_ids": set(),
                           "zones": []})
    r1 = chk.check({"type": "DISPATCH", "aircraft_id": "M-UAV-01",
                    "mission_id": "M-CRITICAL-001", "target_site": "V1"})
    r2 = chk.check({"type": "GROUND_FALLBACK", "mission_id": "M-CRITICAL-001"})
    record("F3-6-checker", (not r1["valid"] and "UTM_AIR_PROHIBITED" in r1["violations"]
                            and r2["valid"]),
           f"air DISPATCH rejected {r1['violations']}; GROUND_FALLBACK valid={r2['valid']}")

    clk = read_csv(rd_a / "clock_sync.csv")
    seg = [r for r in clk if 355 <= int(r["t"]) <= 365]
    record("F3-7-clock", all(r["sync_ok"] == "True" for r in seg),
           f"clock sync_ok across t=355..365: {all(r['sync_ok']=='True' for r in seg)}")

    same = {n: md5(rd_a / n) == md5(rd_b / n)
            for n in ("events.csv", "actions.csv", "missions.csv", "clock_sync.csv")}
    record("F3-8-replay", all(same.values()), f"replay byte-identical: {same}")

    return final_summary()


if __name__ == "__main__":
    raise SystemExit(main())
