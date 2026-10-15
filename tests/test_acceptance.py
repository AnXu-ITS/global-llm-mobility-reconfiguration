"""Phase-1 acceptance tests (T1 is in test_geographic_alignment.py).

T2  clock synchronisation (SUMO == BlueSky == orchestrator)
T3  mission lifecycle (WAITING -> ASSIGNED -> EN_ROUTE -> COMPLETED)
T4  reassignment action (optional)
T8  invalid action rejection (safety checker)
T9  deterministic replay (same seed -> identical outputs)

Each test prints PASS/FAIL with evidence. Exit code 0 iff all pass.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod  # noqa: E402
from orchestrator.registry import Aircraft, Mission, Registry  # noqa: E402
from safety.feasibility_checker import FeasibilityChecker  # noqa: E402

RUN = ROOT / "runs" / "cosim_smoke_test"
VENV_PY = r"C:\Users\user\.venvs\bluesky\Scripts\python.exe"

RESULTS = []


def record(name, passed, evidence):
    RESULTS.append((name, passed, evidence))
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: {evidence}")


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _build_registry():
    """Small standalone registry + checker for T4/T8 (no sim needed)."""
    reg = Registry()
    for i in range(1, 4):
        reg.add_aircraft(Aircraft(f"L-UAV-0{i}", "logistics_uav", 31.3, 120.6,
                                  status="AVAILABLE"))
    # one busy aircraft
    busy = Aircraft("M-UAV-01", "medical_uav", 31.31, 120.60, status="BUSY",
                    mission_id="M-M-001")
    reg.add_aircraft(busy)
    reg.add_mission(Mission("M-SUPPORT-001", "medical_resupply", "CRITICAL",
                            "V2", "V1", deadline_s=900))
    reg.add_mission(Mission("M-M-001", "medical_transfer", "HIGH", "V1", "V3",
                            deadline_s=1800, assigned_resource="M-UAV-01",
                            status="EN_ROUTE"))
    cfg = config_mod.load_config()
    return reg, FeasibilityChecker(reg, cfg)


def test_t2():
    try:
        rows = read_csv(RUN / "clock_sync.csv")
        n = len(rows)
        all_sync = all(r["sync_ok"] == "True" for r in rows)
        max_err = max(abs(float(r["sumo_time"]) - float(r["orchestrator_time"]))
                      for r in rows)
        ok = n >= 600 and all_sync and max_err < 1e-6
        record("T2", ok, f"{n} steps, all sync_ok={all_sync}, max clock error={max_err:.6f}s")
    except Exception as e:
        record("T2", False, f"error: {e}")


def test_t3():
    try:
        reg = json.loads((RUN / "registry_final.json").read_text(encoding="utf-8"))
        m = {x["mission_id"]: x for x in reg["missions"]}.get("M-SUPPORT-001")
        a = {x["aircraft_id"]: x for x in reg["aircraft"]}.get("M-UAV-02")
        events = read_csv(RUN / "events.csv")
        started = any("MISSION_STARTED" in e["event_id"] for e in events)
        completed = any("MISSION_COMPLETED" in e["event_id"] for e in events)
        ok = (m is not None and m["status"] == "COMPLETED"
              and m["assigned_resource"] == "M-UAV-02"
              and a is not None and a["status"] == "AVAILABLE"
              and started and completed)
        record("T3", ok, f"M-SUPPORT-001 status={m['status'] if m else None}, "
              f"M-UAV-02 status={a['status'] if a else None}, "
              f"started={started}, completed={completed}")
    except Exception as e:
        record("T3", False, f"error: {e}")


def test_t4():
    """T4 (optional): REASSIGN a NEEDS_REPLAN mission to an available UAV."""
    try:
        reg, checker = _build_registry()
        # the current holder (M-UAV-01) is lost: BUSY -> CONTINGENCY -> UNAVAILABLE
        reg.aircraft["M-UAV-01"].transition("CONTINGENCY")
        reg.aircraft["M-UAV-01"].transition("UNAVAILABLE")
        # its mission goes EN_ROUTE -> NEEDS_REPLAN
        reg.missions["M-M-001"].transition("NEEDS_REPLAN")
        action = {"type": "REASSIGN", "aircraft_id": "L-UAV-01",
                  "mission_id": "M-M-001", "target_site": "V3"}
        result = checker.check(action)
        if result["valid"]:
            reg.missions["M-M-001"].assigned_resource = "L-UAV-01"
            reg.aircraft["L-UAV-01"].transition("BUSY")
            reg.aircraft["L-UAV-01"].mission_id = "M-M-001"
            reg.missions["M-M-001"].transition("REASSIGNED")
            reg.missions["M-M-001"].transition("EN_ROUTE")
        ok = result["valid"] and reg.missions["M-M-001"].status == "EN_ROUTE"
        record("T4", ok, f"REASSIGN valid={result['valid']}, "
              f"violations={result['violations']}, final status={reg.missions['M-M-001'].status}")
    except Exception as e:
        record("T4", False, f"error: {e}")


def test_t8():
    """T8: safety checker must reject infeasible actions."""
    try:
        reg, checker = _build_registry()
        # (a) dispatch a BUSY aircraft -> infeasible (already busy; also duplicate assignment)
        a1 = {"type": "DISPATCH", "aircraft_id": "M-UAV-01",
              "mission_id": "M-SUPPORT-001", "target_site": "V1"}
        r1 = checker.check(a1)
        # (b) dispatch to an incompatible/unknown site
        a2 = {"type": "DISPATCH", "aircraft_id": "L-UAV-01",
              "mission_id": "M-SUPPORT-001", "target_site": "NOPE"}
        r2 = checker.check(a2)
        # (c) dispatch an aircraft with zero battery
        dead = Aircraft("L-UAV-09", "logistics_uav", 31.3, 120.6, battery_pct=0)
        reg.add_aircraft(dead)
        a3 = {"type": "DISPATCH", "aircraft_id": "L-UAV-09",
              "mission_id": "M-SUPPORT-001", "target_site": "V1"}
        r3 = checker.check(a3)
        ok = (r1["valid"] is False and r2["valid"] is False and r3["valid"] is False)
        record("T8", ok, f"busy-dispatch valid={r1['valid']} {r1['violations']}; "
              f"bad-site valid={r2['valid']} {r2['violations']}; "
              f"dead-battery valid={r3['valid']} {r3['violations']}")
    except Exception as e:
        record("T8", False, f"error: {e}")


def _run_scenario(run_dir: Path, duration: int, b1_close_t: int, seed: int):
    cmd = [VENV_PY, str(ROOT / "tools" / "run_scenario.py"),
           str(run_dir), str(duration), str(b1_close_t), str(seed)]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


def _file_fp(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def test_t9():
    """T9: deterministic replay -- same seed, identical events + trajectories."""
    try:
        d1 = ROOT / "runs" / "replay_a"
        d2 = ROOT / "runs" / "replay_b"
        r1 = _run_scenario(d1, 40, 20, 424242)
        r2 = _run_scenario(d2, 40, 20, 424242)
        if r1.returncode != 0 or r2.returncode != 0:
            record("T9", False, f"scenario run failed (rc={r1.returncode},{r2.returncode})")
            return
        same_events = _file_fp(d1 / "events.csv") == _file_fp(d2 / "events.csv")
        same_ground = _file_fp(d1 / "ground_state.csv") == _file_fp(d2 / "ground_state.csv")
        same_air = _file_fp(d1 / "air_state.csv") == _file_fp(d2 / "air_state.csv")
        same_clock = _file_fp(d1 / "clock_sync.csv") == _file_fp(d2 / "clock_sync.csv")
        ok = same_events and same_ground and same_air and same_clock
        record("T9", ok, f"events={same_events}, ground={same_ground}, "
              f"air={same_air}, clock={same_clock}")
    except Exception as e:
        record("T9", False, f"error: {e}")


def main() -> int:
    test_t2()
    test_t3()
    test_t4()
    test_t8()
    test_t9()
    print()
    npass = sum(1 for _, p, _ in RESULTS if p)
    print(f"SUMMARY: {npass}/{len(RESULTS)} passed")
    return 0 if npass == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
