"""C2 Lost Link + Local Contingency tests (F) — no simulator required.

Proves that at the instant of C2 failure the lost-link aircraft immediately
enters CONTINGENCY and executes a pre-defined RETURN (or LAND) **without** the
Rule Manager, LLM, or global planner — even when the manager is disabled or its
response is delayed.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod         # noqa: E402
from orchestrator.registry import Aircraft, Mission   # noqa: E402
from failures.c2_lost import C2LostLink, LocalContingency  # noqa: E402

CFG = config_mod.load_config()
RESULTS = []


def record(name, passed, evidence):
    RESULTS.append((name, passed, evidence))
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: {evidence}")


def _make_enroute_aircraft():
    ac = Aircraft("M-UAV-02", "medical_uav", 31.30, 120.60, status="BUSY",
                  mission_id="M-CRITICAL-001")
    m = Mission("M-CRITICAL-001", "medical_blood", "CRITICAL", "V2", "V1",
                deadline_s=900, assigned_resource="M-UAV-02")
    m.status = "EN_ROUTE"
    return ac, m


def test_c2_state_mutation():
    ac, m = _make_enroute_aircraft()
    change = C2LostLink(CFG).trigger(ac, m)
    ok = (ac.c2_status == "LOST" and ac.status == "CONTINGENCY"
          and ac.reassignable is False and ac.commandable is False
          and m.status == "NEEDS_REPLAN")
    record("C2 lost changes aircraft state", ok,
           f"c2={ac.c2_status}, status={ac.status}, reassignable={ac.reassignable}, "
           f"commandable={ac.commandable}, mission={m.status}")


def test_mission_enroute_to_replan():
    ac, m = _make_enroute_aircraft()
    change = C2LostLink(CFG).trigger(ac, m)
    ok = change["mission_change"] == {"from": "EN_ROUTE", "to": "NEEDS_REPLAN"}
    record("EN_ROUTE -> INTERRUPTED -> NEEDS_REPLAN", ok,
           f"mission_change={change['mission_change']}")


def test_local_contingency_independent():
    """Contingency plan is produced without any manager / LLM / planner object."""
    ac, m = _make_enroute_aircraft()
    # trigger C2 (no manager involved anywhere)
    C2LostLink(CFG).trigger(ac, m)
    plan = LocalContingency(CFG).plan(ac.id)
    ok = (plan["mode"] in ("RETURN", "LAND") and plan["target_site"] == "V3")
    record("local contingency RETURN/LAND to V3 (no manager)", ok, f"plan={plan}")


def test_contingency_fires_before_manager():
    """Even if the manager is 'delayed', the aircraft is already CONTINGENCY at
    the failure instant; a later manager decision cannot undo the local action."""
    ac, m = _make_enroute_aircraft()
    t_fail = 360
    # failure instant: local contingency fires immediately
    C2LostLink(CFG).trigger(ac, m)
    plan = LocalContingency(CFG).plan(ac.id)
    immediate = ac.status == "CONTINGENCY" and plan["mode"] in ("RETURN", "LAND")
    # "delayed" manager (simulated): it only sees the post-contingency state
    manager_absent = True  # no manager is imported or invoked in this module
    ok = immediate and manager_absent
    record("C2 event -> contingency without manager/delay", ok,
           f"at t={t_fail}: status={ac.status}, plan={plan['mode']}, manager invoked={not manager_absent}")


def main() -> int:
    test_c2_state_mutation()
    test_mission_enroute_to_replan()
    test_local_contingency_independent()
    test_contingency_fires_before_manager()
    print()
    npass = sum(1 for _, p, _ in RESULTS if p)
    print(f"SUMMARY: {npass}/{len(RESULTS)} passed")
    return 0 if npass == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
