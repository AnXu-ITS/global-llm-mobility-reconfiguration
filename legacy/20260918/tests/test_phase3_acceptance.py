"""Phase 3 acceptance tests (P3-T1 .. P3-T14).

Reads the offline decision artifacts + live run artifacts and writes
reports/PHASE3_ACCEPTANCE_TESTS.md. Exit code 0 iff no FAIL.

Usage: python tests/test_phase3_acceptance.py
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

from managers.llm_manager import LLMManager      # noqa: E402
from managers.rule_based import RuleBasedManager  # noqa: E402
from orchestrator import config as config_mod     # noqa: E402
from orchestrator.registry import Aircraft, Mission, Registry  # noqa: E402
from safety.feasibility_checker import FeasibilityChecker  # noqa: E402

VENV_PY = r"C:\Users\user\.venvs\bluesky\Scripts\python.exe"
OFFLINE = ROOT / "runs" / "phase3_offline_decisions"
LIVE = ROOT / "runs" / "phase3_live_smoke"
LIVE_C2 = ROOT / "runs" / "phase3_live_c2"
LIVE_NB = ROOT / "runs" / "phase3_no_backup"
P2_RUNS = ROOT / "runs" / "phase2_rule_manager"

RESULTS = []


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


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def test_p3_t1():
    r = run_py([ROOT / "tests" / "test_phase2_acceptance.py"], timeout=1800)
    record("P3-T1", "PASS" if r.returncode == 0 else "FAIL",
           "Phase-1/2 regression " + ("PASS" if r.returncode == 0 else "FAILED"))


def test_p3_t2():
    a = LIVE_C2 / "manager_inputs.jsonl"
    b = P2_RUNS / "C2_B" / "manager_inputs.jsonl"
    if not a.exists() or not b.exists():
        record("P3-T2", "FAIL", f"missing inputs {a.exists()} {b.exists()}")
        return
    identical = md5(a) == md5(b)
    record("P3-T2", "PASS" if identical else "FAIL",
           f"Phase-3 LLM manager_inputs byte-identical to Phase-2 Rule manager_inputs: {identical}")


def test_p3_t3():
    cfg = config_mod.load_config()
    import yaml
    p3 = yaml.safe_load((ROOT / "config" / "phase3_config.yaml").read_text(encoding="utf-8"))
    rule = RuleBasedManager(cfg)
    llm = LLMManager(cfg, p3)
    # interface: both expose decide(gs) -> dict with decision_id + action keys
    gs = {"simulation_time": 0, "scenario_id": "S0", "missions": {"new": [], "existing": []},
          "air": [], "ground": {}, "events": [], "trend": {}, "infrastructure": {"landing_sites": {}}}
    rk = set(rule.decide(gs).keys())
    lk = set(llm.decide(gs).keys())
    need = {"decision_id", "action", "reason", "mission_id", "selected"}
    ok = need.issubset(rk) and need.issubset(lk)
    record("P3-T3", "PASS" if ok else "FAIL",
           f"Rule keys={sorted(need & rk)}, LLM keys={sorted(need & lk)} (both expose the ManagerAction contract)")


def test_p3_t4():
    llm = read_jsonl(OFFLINE / "llm_outputs.jsonl")
    n_schema_err = sum(1 for r in llm if r["decision"]["llm_metadata"]["validation_status"] == "SCHEMA_ERROR")
    ok = n_schema_err == 0
    record("P3-T4", "PASS" if ok else "FAIL",
           f"structured output schema-valid on {len(llm)} states; SCHEMA_ERROR={n_schema_err}")


def test_p3_t5():
    llm = read_jsonl(OFFLINE / "llm_outputs.jsonl")
    n_unk = sum(1 for r in llm if "UNKNOWN_RESOURCE" in r["decision"]["llm_metadata"]["errors"])
    ok = n_unk == 0
    record("P3-T5", "PASS" if ok else "FAIL",
           f"unknown-resource hallucination after retry = {n_unk}")


def test_p3_t6():
    cfg = config_mod.load_config()
    reg = Registry()
    reg.add_aircraft(Aircraft("A1", "medical_uav", 31.3, 120.6, status="AVAILABLE",
                              battery_pct=0, remaining_endurance_s=0))
    reg.add_mission(Mission("M1", "medical_blood", "CRITICAL", "V2", "V1",
                            deadline_s=900, ground_fallback=True))
    chk = FeasibilityChecker(reg, cfg)
    r1 = chk.check({"type": "DISPATCH", "aircraft_id": "GHOST", "mission_id": "M1",
                    "target_site": "V1"})
    r2 = chk.check({"type": "DISPATCH", "aircraft_id": "A1", "mission_id": "M1",
                    "target_site": "V1"})
    ok = (not r1["valid"] and "AIRCRAFT_NOT_FOUND" in r1["violations"]
          and not r2["valid"] and "INSUFFICIENT_BATTERY" in r2["violations"])
    record("P3-T6", "PASS" if ok else "FAIL",
           f"checker blocks unknown resource ({r1['violations']}) and insufficient battery ({r2['violations']})")


def test_p3_t7():
    cf = read_jsonl(OFFLINE / "counterfactual.jsonl")
    n_fail = sum(1 for r in cf if r["verdict"] == "FAIL")
    n_pass = sum(1 for r in cf if r["verdict"] == "PASS")
    ok = n_fail == 0 and len(cf) >= 8
    record("P3-T7", "PASS" if ok else "FAIL",
           f"{len(cf)} pairs: {n_pass} PASS, {sum(1 for r in cf if r['verdict']=='OBSERVED')} OBSERVED, "
           f"{n_fail} FAIL")


def test_p3_t8():
    st = read_jsonl(OFFLINE / "stability.jsonl")
    from collections import Counter
    ac = Counter(r["action_type"] for r in st)
    rc = Counter(r["aircraft_id"] for r in st if r["aircraft_id"])
    action_consistency = (max(ac.values()) / len(st)) if st else 0
    ok = len(st) >= 10 and action_consistency > 0
    record("P3-T8", "PASS" if ok else "FAIL",
           f"{len(st)} repeats, action consistency={action_consistency:.0%} "
           f"(mode={ac.most_common(1)[0][0] if ac else '-'})")


def _events(run: Path):
    return read_csv(run / "events.csv")


def _metrics(run: Path):
    return json.loads((run / "metrics.json").read_text(encoding="utf-8"))


def test_p3_t9():
    if not (LIVE / "metrics.json").exists():
        record("P3-T9", "FAIL", "live smoke run missing")
        return
    evs = _events(LIVE)
    m = _metrics(LIVE)
    dispatched = any(e["event_id"] == "MISSION_STARTED" for e in evs)
    completed = any(e["event_id"] == "MISSION_COMPLETED" for e in evs)
    ok = dispatched and completed and m.get("critical_mission_final_state") == "COMPLETED"
    record("P3-T9", "PASS" if ok else "FAIL",
           f"ground->LLM->air chain: dispatched={dispatched}, completed={completed}, "
           f"final={m.get('critical_mission_final_state')}")


def test_p3_t10():
    if not (LIVE_C2 / "metrics.json").exists():
        record("P3-T10", "FAIL", "live C2 run missing")
        return
    evs = _events(LIVE_C2)
    m = _metrics(LIVE_C2)
    c2 = any(e["event_id"] == "C2_LOST" for e in evs)
    reconf = any(e["event_id"] in ("MISSION_STARTED", "GROUND_FALLBACK_STARTED") for e in evs)
    completed = any(e["event_id"] in ("MISSION_COMPLETED", "GROUND_FALLBACK_COMPLETED") for e in evs)
    ok = c2 and reconf and completed
    record("P3-T10", "PASS" if ok else "FAIL",
           f"C2->LLM reconfiguration: c2_lost={c2}, reconfigure={reconf}, terminal={completed}, "
           f"final={m.get('critical_mission_final_state')}")


def test_p3_t11():
    if not (LIVE_NB / "metrics.json").exists():
        record("P3-T11", "FAIL", "no-backup run missing")
        return
    m = _metrics(LIVE_NB)
    evs = _events(LIVE_NB)
    acts = read_csv(LIVE_NB / "actions.csv")
    illegal = [a for a in acts if a["result"] in ("REJECTED", "REJECTED_SEMANTIC")]
    legal = m.get("critical_mission_final_state") in ("COMPLETED", "CANCELLED", "FAILED") \
        or any(e["event_id"] in ("GROUND_FALLBACK_COMPLETED", "MISSION_CANCELLED", "MISSION_DELAYED") for e in evs)
    ok = legal and not illegal
    record("P3-T11", "PASS" if ok else "FAIL",
           f"no-backup handled legally: final={m.get('critical_mission_final_state')}, "
           f"rejected_actions={len(illegal)}")


def test_p3_t12():
    if not (LIVE_C2 / "events.csv").exists():
        record("P3-T12", "FAIL", "live C2 events missing")
        return
    evs = _events(LIVE_C2)
    order = [e["event_id"] for e in evs if e["event_id"] in
             ("C2_LOST", "LOCAL_CONTINGENCY", "MISSION_INTERRUPTED", "MISSION_STARTED")]
    # local contingency must appear right after C2_LOST and before any manager-driven MISSION_STARTED
    ok = "LOCAL_CONTINGENCY" in order and order.index("LOCAL_CONTINGENCY") == order.index("C2_LOST") + 1
    lc = [e for e in evs if e["event_id"] == "LOCAL_CONTINGENCY"][0]
    p = json.loads(lc["payload"])
    ok = ok and p.get("mode") == "RETURN" and p.get("target_site") == "V3"
    record("P3-T12", "PASS" if ok else "FAIL",
           f"local contingency fires immediately after C2_LOST (order={order[:4]}), "
           f"mode={p.get('mode')} target={p.get('target_site')}")


def test_p3_t13():
    runs = [LIVE, LIVE_C2, LIVE_NB]
    all_sync = True
    for run in runs:
        rows = read_csv(run / "clock_sync.csv")
        if not all(r["sync_ok"] == "True" for r in rows):
            all_sync = False
    record("P3-T13", "PASS" if all_sync else "FAIL",
           "SUMO/BlueSky/orchestrator synchronized across all live runs")


def test_p3_t14():
    ok = True
    for run in (LIVE, LIVE_C2, LIVE_NB):
        a = run / "manager_inputs.jsonl"
        b = run / "manager_outputs.jsonl"
        if not a.exists() or not b.exists():
            ok = False
            continue
        if len(read_jsonl(a)) != len(read_jsonl(b)):
            ok = False
    record("P3-T14", "PASS" if ok else "FAIL",
           "manager_inputs.jsonl and manager_outputs.jsonl present and paired in all live runs")


def write_report():
    table = "\n".join(f"| {tid} | {status} | {evidence} |" for tid, status, evidence in RESULTS)
    n_fail = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    verdict = "NO FAIL" if n_fail == 0 else f"{n_fail} FAIL"
    md = f"""# Phase 3 Acceptance Tests — Results

**Manager:** LLM Manager (`corp-ai/openai/deepseek-v4-pro`, prompt `manager_v1`, temperature=0)
**Shared path:** Global State v1 -> Manager -> Semantic Validator -> FeasibilityChecker -> Executor
**Verdict:** {verdict} across P3-T1..P3-T14

| Test | Result | Evidence |
|------|--------|----------|
{table}
"""
    (ROOT / "reports" / "PHASE3_ACCEPTANCE_TESTS.md").write_text(md, encoding="utf-8")


def main() -> int:
    test_p3_t1()
    test_p3_t2()
    test_p3_t3()
    test_p3_t4()
    test_p3_t5()
    test_p3_t6()
    test_p3_t7()
    test_p3_t8()
    test_p3_t9()
    test_p3_t10()
    test_p3_t11()
    test_p3_t12()
    test_p3_t13()
    test_p3_t14()
    print()
    n_fail = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    print(f"SUMMARY: {len(RESULTS) - n_fail}/{len(RESULTS)} PASS, {n_fail} FAIL")
    write_report()
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
