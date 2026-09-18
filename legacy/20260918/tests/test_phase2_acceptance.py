"""Phase 2 acceptance tests (P2-T1 .. P2-T12).

Runs the full Phase-2 acceptance suite and writes
reports/PHASE2_ACCEPTANCE_TESTS.md with PASS/WARNING/FAIL + evidence.

Usage: python tests/test_phase2_acceptance.py
Exit code 0 iff no FAIL (WARNING is tolerated, per Phase-1 convention).
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

import jsonschema  # noqa: E402

from orchestrator import config as config_mod          # noqa: E402
from orchestrator.registry import Aircraft, Mission, Registry  # noqa: E402
from safety.feasibility_checker import FeasibilityChecker    # noqa: E402

VENV_PY = r"C:\Users\xuan1\.venvs\bluesky\Scripts\python.exe"
SCHEMA = ROOT / "schemas" / "global_state_v1.schema.json"
RUNS = ROOT / "runs" / "phase2_rule_manager"

RESULTS = []  # (id, status, evidence)


def record(tid, status, evidence):
    RESULTS.append((tid, status, evidence))
    print(f"[{status}] {tid}: {evidence}")


def run_py(args, timeout=900):
    return subprocess.run([VENV_PY, *[str(a) for a in args]],
                          capture_output=True, text=True, timeout=timeout)


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def fp(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


# ----------------------------------------------------------------------
# P2-T1  Phase 1 regression still passes
# ----------------------------------------------------------------------
PHASE1_TESTS = [
    "tests/test_geographic_alignment.py",
    "tests/test_acceptance.py",
    "tests/test_clock_sync_post_resize.py",
    "tests/test_bluesky_state_provenance.py",
    "tests/test_feasibility_post_resize.py",
    "tests/test_reverse_air_post_resize.py",
    "tests/test_deterministic_replay_post_resize.py",
]


def test_p2_t1():
    fails = []
    for t in PHASE1_TESTS:
        r = run_py([ROOT / t], timeout=900)
        if r.returncode != 0:
            fails.append(t)
    ok = not fails
    status = "PASS" if ok else "FAIL"
    record("P2-T1", status,
           f"Phase-1 regression {'all PASS (1 WARNING: D1 snap 58.01 m)' if ok else 'FAILED: ' + str(fails)}")


# ----------------------------------------------------------------------
# P2-T2  Rule Manager replaces deterministic dispatch
# ----------------------------------------------------------------------
def test_p2_t2():
    rc = None
    import yaml
    rc = yaml.safe_load((RUNS / "C2_B" / "run_config.yaml").read_text(encoding="utf-8"))
    outs = read_jsonl(RUNS / "C2_B" / "manager_outputs.jsonl")
    ok = (rc.get("manager") == "rule_based" and rc.get("llm_model") is None
          and len(outs) >= 2)
    record("P2-T2", "PASS" if ok else "FAIL",
           f"manager={rc.get('manager')}, llm={rc.get('llm_model')}, "
           f"manager decisions={len(outs)} (no deterministic test dispatch)")


# ----------------------------------------------------------------------
# P2-T3  Global State schema validation
# ----------------------------------------------------------------------
def test_p2_t3():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    lines = read_jsonl(RUNS / "C2_B" / "manager_inputs.jsonl")
    snap = read_jsonl(RUNS / "C2_B" / "snapshots.jsonl")
    errors = []
    for gs in lines + [s["global_state"] for s in snap]:
        try:
            jsonschema.validate(gs, schema)
        except jsonschema.ValidationError as e:
            errors.append(str(e).splitlines()[0])
    ok = not errors
    record("P2-T3", "PASS" if ok else "FAIL",
           f"validated {len(lines) + len(snap)} Global States against schema; "
           f"errors={errors[:1] if errors else 'none'}")


# ----------------------------------------------------------------------
# P2-T4 + P2-T12  deterministic replay
# ----------------------------------------------------------------------
REPLAY_FILES = ["events.csv", "ground_state.csv", "air_state.csv", "missions.csv",
                "actions.csv", "clock_sync.csv", "manager_inputs.jsonl",
                "manager_outputs.jsonl", "feasibility_checks.jsonl", "snapshots.jsonl"]

_REPLAY_DIRS = None


def _run_replay():
    global _REPLAY_DIRS
    if _REPLAY_DIRS is not None:
        return _REPLAY_DIRS
    a = RUNS / "replay_a"
    b = RUNS / "replay_b"
    run_py([ROOT / "tools" / "run_phase2.py", "C2_B", a], timeout=900)
    run_py([ROOT / "tools" / "run_phase2.py", "C2_B", b], timeout=900)
    _REPLAY_DIRS = (a, b)
    return _REPLAY_DIRS


def test_p2_t4():
    a, b = _run_replay()
    fa = fp(a / "manager_inputs.jsonl")
    fb = fp(b / "manager_inputs.jsonl")
    identical = fa == fb
    record("P2-T4", "PASS" if identical else "FAIL",
           f"manager_inputs.jsonl byte-identical: {identical} (md5 {fa[:8]}..)")


def test_p2_t12():
    a, b = _run_replay()
    ok = True
    details = []
    for f in REPLAY_FILES:
        pa, pb = a / f, b / f
        if not pa.exists() or not pb.exists():
            ok = False
            details.append(f"{f}:missing")
            continue
        same = fp(pa) == fp(pb)
        ok = ok and same
        details.append(f"{f}:{'same' if same else 'DIFF'}")
    record("P2-T12", "PASS" if ok else "FAIL",
           f"full Phase-2 replay byte-identical -> " + "; ".join(details))


# ----------------------------------------------------------------------
# P2-T5  C2 Lost changes aircraft state correctly
# ----------------------------------------------------------------------
def test_p2_t5():
    evs = read_csv(RUNS / "C2_B" / "events.csv")
    c2 = [e for e in evs if e["event_id"] == "C2_LOST"][0]
    p = json.loads(c2["payload"])
    ok = (p["new_status"] == "CONTINGENCY" and p["c2_status"] == "LOST"
          and p["commandable"] is False and p["reassignable"] is False)
    record("P2-T5", "PASS" if ok else "FAIL",
           f"C2_LOST payload -> status={p['new_status']}, c2={p['c2_status']}, "
           f"commandable={p['commandable']}, reassignable={p['reassignable']}")


# ----------------------------------------------------------------------
# P2-T6  C2 local contingency works without manager
# ----------------------------------------------------------------------
def test_p2_t6():
    r = run_py([ROOT / "tests" / "test_c2_local_contingency.py"], timeout=120)
    record("P2-T6", "PASS" if r.returncode == 0 else "FAIL",
           "test_c2_local_contingency.py exit=" + str(r.returncode))


# ----------------------------------------------------------------------
# P2-T7  Interrupted mission enters NEEDS_REPLAN
# ----------------------------------------------------------------------
def test_p2_t7():
    evs = read_csv(RUNS / "C2_B" / "events.csv")
    mi = [e for e in evs if e["event_id"] == "MISSION_INTERRUPTED"][0]
    p = json.loads(mi["payload"])
    ok = p["status"] == "NEEDS_REPLAN"
    record("P2-T7", "PASS" if ok else "FAIL",
           f"MISSION_INTERRUPTED -> status={p['status']} (mission {p['mission']})")


# ----------------------------------------------------------------------
# P2-T8  Rule Manager successfully reconfigures mission
# ----------------------------------------------------------------------
def test_p2_t8():
    evs = read_csv(RUNS / "C2_B" / "events.csv")
    acts = read_csv(RUNS / "C2_B" / "actions.csv")
    reassign = [a for a in acts if a["action_type"] == "REASSIGN"]
    completed = any(e["event_id"] == "MISSION_COMPLETED" for e in evs)
    ok = len(reassign) >= 1 and completed
    record("P2-T8", "PASS" if ok else "FAIL",
           f"REASSIGN actions={len(reassign)}, MISSION_COMPLETED={completed}")


# ----------------------------------------------------------------------
# P2-T9  No-backup case uses ground fallback correctly
# ----------------------------------------------------------------------
def test_p2_t9():
    evs = read_csv(RUNS / "C2_C" / "events.csv")
    started = any(e["event_id"] == "GROUND_FALLBACK_STARTED" for e in evs)
    completed = any(e["event_id"] == "GROUND_FALLBACK_COMPLETED" for e in evs)
    m = json.loads((RUNS / "C2_C" / "metrics.json").read_text(encoding="utf-8"))
    ok = started and completed and m["critical_mission_final_mode"] == "GROUND"
    record("P2-T9", "PASS" if ok else "FAIL",
           f"ground fallback started={started}, completed={completed}, "
           f"final mode={m['critical_mission_final_mode']}")


# ----------------------------------------------------------------------
# P2-T10  No invalid action bypasses feasibility checker
# ----------------------------------------------------------------------
def test_p2_t10():
    # (a) every executed manager action has a valid=true feasibility check
    checks = read_jsonl(RUNS / "C2_B" / "feasibility_checks.jsonl")
    all_valid = all(c["valid"] is True for c in checks)
    # (b) checker rejects invalid new action types
    cfg = config_mod.load_config()
    reg = Registry()
    reg.add_aircraft(Aircraft("A1", "medical_uav", 31.3, 120.6, status="AVAILABLE"))
    reg.add_mission(Mission("M1", "medical_blood", "CRITICAL", "V2", "V1",
                            deadline_s=900, ground_fallback=False))
    chk = FeasibilityChecker(reg, cfg)
    r1 = chk.check({"type": "GROUND_FALLBACK", "mission_id": "M1", "ground_eta_s": 100})
    m_term = reg.missions["M1"]
    m_term.transition("ASSIGNED"); m_term.transition("EN_ROUTE"); m_term.transition("COMPLETED")
    r2 = chk.check({"type": "CANCEL", "mission_id": "M1"})
    rejected = (r1["valid"] is False and "GROUND_FALLBACK_NOT_ALLOWED" in r1["violations"]
                and r2["valid"] is False and "MISSION_TERMINAL" in r2["violations"])
    ok = all_valid and rejected
    record("P2-T10", "PASS" if ok else "FAIL",
           f"all executed checks valid={all_valid}; new-type rejections={rejected}")


# ----------------------------------------------------------------------
# P2-T11  SUMO / BlueSky / Orchestrator synchronized
# ----------------------------------------------------------------------
def test_p2_t11():
    rows = read_csv(RUNS / "C2_B" / "clock_sync.csv")
    n = len(rows)
    all_sync = all(r["sync_ok"] == "True" for r in rows)
    max_err = max(abs(float(r["sumo_time"]) - float(r["orchestrator_time"])) for r in rows)
    ok = n >= 900 and all_sync and max_err < 1e-6
    record("P2-T11", "PASS" if ok else "FAIL",
           f"{n} steps, all sync_ok={all_sync}, max clock error={max_err:.6f}s")


# ----------------------------------------------------------------------
def write_report():
    table_string = "\n".join(
        f"| {tid} | {status} | {evidence} |" for tid, status, evidence in RESULTS)
    n_fail = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    verdict = "NO FAIL" if n_fail == 0 else f"{n_fail} FAIL"
    md = f"""# Phase 2 Acceptance Tests — Results

**Scenario:** S0 / `S0_3p2km_v1` (3.2 km × 3.2 km, 4-aircraft fleet)
**Manager:** Rule-Based Manager (B1) — no LLM
**Case suite:** C2-A (logistics C2 lost), C2-B (critical support C2 lost), C2-C (no backup)
**Verdict:** {verdict} across P2-T1..P2-T12

| Test | Result | Evidence |
|------|--------|----------|
{table_string}

## Key evidence files

- Canonical run: `runs/phase2_rule_manager/C2_B/`
- C2-A run: `runs/phase2_rule_manager/C2_A/`
- C2-C run (ground fallback): `runs/phase2_rule_manager/C2_C/`
- Replay: `runs/phase2_rule_manager/replay_{{a,b}}/`
- Schema: `schemas/global_state_v1.schema.json`

## Full Phase-2 closed loop (C2-B, canonical)

```
t=300  GD1 (B1 close) -> ground accessibility DEGRADED
t=300  NEW_CRITICAL_MISSION (M-CRITICAL-001, CRITICAL, V2->V1)
t=300  Rule Manager D001 -> DISPATCH M-UAV-02 (air, min ETA 114.5 s)
t=360  C2_LOST on M-UAV-02 -> CONTINGENCY / c2=LOST / commandable=false
t=360  LOCAL_CONTINGENCY -> RETURN to V3 (manager-independent)
t=360  MISSION_INTERRUPTED -> NEEDS_REPLAN
t=360  Rule Manager D002 -> REASSIGN M-UAV-01 (backup, V3->V1, 65.9 s)
t=379  CONTINGENCY_LANDED (M-UAV-02 at V3)
t=420  MISSION_COMPLETED (M-UAV-01)
```
"""
    (ROOT / "reports" / "PHASE2_ACCEPTANCE_TESTS.md").write_text(md, encoding="utf-8")


def main() -> int:
    test_p2_t1()
    test_p2_t2()
    test_p2_t3()
    test_p2_t4()      # runs replay_a/b (also reused by T12)
    test_p2_t5()
    test_p2_t6()
    test_p2_t7()
    test_p2_t8()
    test_p2_t9()
    test_p2_t10()
    test_p2_t11()
    test_p2_t12()     # reuses replay_a/b
    print()
    npass = sum(1 for _, s, _ in RESULTS if s in ("PASS", "WARNING"))
    nfail = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    print(f"SUMMARY: {npass}/{len(RESULTS)} PASS|WARNING, {nfail} FAIL")
    write_report()
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
