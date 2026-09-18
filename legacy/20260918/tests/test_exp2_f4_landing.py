"""Experiment 2 — F4 (landing-site failure) implementation audit (protocol §10)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from _exp2_audit_common import (final_summary, md5, read_csv, read_json,
                                read_jsonl, record, run_combo)  # noqa: E402

SCENARIO, SEED, MANAGER = "E2_F4_C3", 20240601, "B1"


def main() -> int:
    rd_a, r_a = run_combo(SCENARIO, SEED, MANAGER, "f4_a")
    rd_b, r_b = run_combo(SCENARIO, SEED, MANAGER, "f4_b")
    record("F4-run", r_a.returncode == 0 and r_b.returncode == 0,
           f"runs complete (rc={r_a.returncode},{r_b.returncode})")

    evs = read_csv(rd_a / "events.csv")
    f4_ev = [e for e in evs if e["event_id"] == "LANDING_SITE_FAILURE"]
    ok_event = (len(f4_ev) == 1 and int(f4_ev[0]["t"]) == 360
                and json.loads(f4_ev[0]["payload"]).get("site") == "V1")
    record("F4-1-event", ok_event, f"LANDING_SITE_FAILURE at t=360 x{len(f4_ev)}")

    tr = read_json(rd_a / "failure_trace.json")
    before, after = tr["state_before"], tr["state_after"]
    mb, ma = before["missions"]["M-CRITICAL-001"], after["missions"]["M-CRITICAL-001"]
    ok_mission = (mb["status"] == "EN_ROUTE" and ma["status"] == "NEEDS_REPLAN"
                  and ma["assigned_resource"] is None)
    mpb, mpa = before["missions"]["M-P-001"], after["missions"]["M-P-001"]
    ok_pax = (mpb["status"] == "EN_ROUTE" and mpa["status"] == "NEEDS_REPLAN")
    record("F4-2-state", ok_mission and ok_pax,
           f"critical {mb['status']}->{ma['status']}; M-P-001 {mpb['status']}->{mpa['status']}")

    ok_unaffected = before["missions"]["M-L-001"] == after["missions"]["M-L-001"]
    record("F4-3-unaffected", ok_unaffected, "M-L-001 (dest V2/V3) unchanged")

    inputs = read_jsonl(rd_a / "manager_inputs.jsonl")
    gs360 = next(x for x in inputs if x["simulation_time"] == 360)
    sites = gs360["infrastructure"]["landing_sites"]
    ok_gs = sites["V1"]["state"] == "UNAVAILABLE" and sites["V3"]["state"] == "AVAILABLE"
    record("F4-4-gs", ok_gs,
           f"GS@360 V1={sites['V1']['state']}, V3={sites['V3']['state']}")

    cands = read_jsonl(rd_a / "candidate_info.jsonl")
    c360 = next(x for x in cands if x["t"] == 360)["candidate_table"]
    air_illegal = all(c["legal"] is False for c in c360["air"])
    dest_ok = all(c["destination_available"] is False for c in c360["air"])
    ground_legal = c360["ground"]["legal"] is True
    record("F4-5-candidates",
           air_illegal and dest_ok and ground_legal and tr["candidate_count_after"] == 0,
           f"all air illegal={air_illegal}, destination_available=False={dest_ok}, "
           f"ground legal={ground_legal}, count_after={tr['candidate_count_after']}")

    from orchestrator.registry import Aircraft, Mission, Registry
    from orchestrator import config as config_mod
    from safety.feasibility_checker_e2 import E2FeasibilityChecker
    cfg = config_mod.load_config()
    cfg["facilities"]["V1"]["available"] = False
    reg = Registry()
    reg.add_aircraft(Aircraft("M-UAV-01", "medical_uav", 31.31, 120.6, status="AVAILABLE"))
    reg.add_mission(Mission("M-CRITICAL-001", "medical_blood", "CRITICAL", "V2", "V1",
                            deadline_s=480))
    chk = E2FeasibilityChecker(reg, cfg)
    r1 = chk.check({"type": "DISPATCH", "aircraft_id": "M-UAV-01",
                    "mission_id": "M-CRITICAL-001", "target_site": "V1"})
    r2 = chk.check({"type": "GROUND_FALLBACK", "mission_id": "M-CRITICAL-001"})
    record("F4-6-checker", (not r1["valid"] and "V1_UNAVAILABLE" in r1["violations"]
                            and r2["valid"]),
           f"DISPATCH to V1 rejected {r1['violations']}; GROUND_FALLBACK valid={r2['valid']}")

    clk = read_csv(rd_a / "clock_sync.csv")
    seg = [r for r in clk if 355 <= int(r["t"]) <= 365]
    record("F4-7-clock", all(r["sync_ok"] == "True" for r in seg),
           f"clock sync_ok across t=355..365: {all(r['sync_ok']=='True' for r in seg)}")

    same = {n: md5(rd_a / n) == md5(rd_b / n)
            for n in ("events.csv", "actions.csv", "missions.csv", "clock_sync.csv")}
    record("F4-8-replay", all(same.values()), f"replay byte-identical: {same}")

    return final_summary()


if __name__ == "__main__":
    raise SystemExit(main())
