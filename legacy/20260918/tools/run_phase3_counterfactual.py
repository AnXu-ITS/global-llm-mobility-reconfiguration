"""Phase 3 counterfactual sanity tests (section I).

For each pair, ONLY one variable changes between A and B. We do NOT require the
LLM to match the Rule Manager; we require the LLM's decision to change in the
directionally-correct way under the causal state change.

Outputs:
    runs/phase3_offline_decisions/counterfactual.jsonl
    reports/LLM_COUNTERFACTUAL_SANITY.md
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from managers.llm_manager import LLMManager  # noqa: E402

OUT = ROOT / "runs" / "phase3_offline_decisions"
REPORT = ROOT / "reports" / "LLM_COUNTERFACTUAL_SANITY.md"


def load_gs(case: str, idx: int) -> Dict[str, Any]:
    p = ROOT / "runs" / "phase2_rule_manager" / case / "manager_inputs.jsonl"
    lines = [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return json.loads(lines[idx])


def deep(gs: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(gs)


def set_air(gs: Dict[str, Any], acid: str, **kw) -> Dict[str, Any]:
    for a in gs["air"]:
        if a["id"] == acid:
            for k, v in kw.items():
                a[k] = v
    return gs


def set_site(gs: Dict[str, Any], site: str, state: str) -> Dict[str, Any]:
    if site in gs["infrastructure"]["landing_sites"]:
        gs["infrastructure"]["landing_sites"][site]["state"] = state
    return gs


def set_ground_eta(gs: Dict[str, Any], eta: float) -> Dict[str, Any]:
    gs["ground"]["ground_fallback_eta_s"] = eta
    gs["ground"]["current_d1_h1_eta_s"] = eta
    return gs


def mission(gs: Dict[str, Any], mid: str) -> Dict[str, Any]:
    for bucket in ("new", "existing"):
        for m in gs["missions"][bucket]:
            if m["id"] == mid:
                return m
    raise KeyError(mid)


def set_mission(gs: Dict[str, Any], mid: str, **kw) -> Dict[str, Any]:
    m = mission(gs, mid)
    for k, v in kw.items():
        m[k] = v
    return gs


BASE = load_gs("C2_B", 0)   # t=300 critical mission dispatch
BASE_C2 = load_gs("C2_B", 1)  # t=360 after C2 lost


def build_pairs() -> List[Dict[str, Any]]:
    pairs: List[Dict[str, Any]] = []

    # Pair 1: C2 NORMAL vs LOST on M-UAV-02
    a = deep(BASE)
    b = set_air(deep(BASE), "M-UAV-02", c2_status="LOST", commandable=False,
                status="CONTINGENCY", availability="UNAVAILABLE")
    pairs.append({"id": "P1", "variable": "M-UAV-02 C2 status",
                  "desc": "NORMAL vs LOST",
                  "expect": "LOST aircraft must not be selected",
                  "a": a, "b": b})

    # Pair 2: V1 AVAILABLE vs UNAVAILABLE
    a = deep(BASE)
    b = set_site(deep(BASE), "V1", "UNAVAILABLE")
    pairs.append({"id": "P2", "variable": "V1 landing site",
                  "desc": "AVAILABLE vs UNAVAILABLE",
                  "expect": "must not dispatch to V1 when UNAVAILABLE",
                  "a": a, "b": b})

    # Pair 3: critical mission NORMAL vs CRITICAL
    a = set_mission(deep(BASE), "M-CRITICAL-001", priority="NORMAL")
    b = set_mission(deep(BASE), "M-CRITICAL-001", priority="CRITICAL")
    pairs.append({"id": "P3", "variable": "mission priority",
                  "desc": "NORMAL vs CRITICAL",
                  "expect": "observe whether resource choice changes with priority",
                  "a": a, "b": b})

    # Pair 4: battery sufficient vs insufficient on M-UAV-02
    a = deep(BASE)
    b = set_air(deep(BASE), "M-UAV-02", battery_pct=0.0, remaining_endurance_s=0.0)
    pairs.append({"id": "P4", "variable": "M-UAV-02 battery",
                  "desc": "sufficient vs insufficient",
                  "expect": "insufficient-battery aircraft must not be selected",
                  "a": a, "b": b})

    # Pair 5: ground ETA 120 vs 400 (observe air-vs-ground preference)
    a = set_ground_eta(deep(BASE), 120.0)
    b = set_ground_eta(deep(BASE), 400.0)
    pairs.append({"id": "P5", "variable": "ground fallback ETA",
                  "desc": "120 s vs 400 s",
                  "expect": "observe whether longer ground ETA increases air preference",
                  "a": a, "b": b})

    # Pair 6: backup available vs no backup (after C2)
    a = deep(BASE_C2)  # M-UAV-01 AVAILABLE
    b = set_air(deep(BASE_C2), "M-UAV-01", status="BUSY", availability="BUSY",
                reassignable=False, current_mission="M-M-BACKUP-001",
                mission_priority="HIGH")
    pairs.append({"id": "P6", "variable": "backup availability",
                  "desc": "available vs committed",
                  "expect": "no backup -> ground fallback / delay / cancel (not the busy aircraft)",
                  "a": a, "b": b})

    # Pair 7: endurance sufficient vs insufficient on M-UAV-02
    a = deep(BASE)
    b = set_air(deep(BASE), "M-UAV-02", remaining_endurance_s=0.0)
    pairs.append({"id": "P7", "variable": "M-UAV-02 endurance",
                  "desc": "sufficient vs insufficient",
                  "expect": "insufficient-endurance aircraft must not be selected",
                  "a": a, "b": b})

    # Pair 8: busy M-UAV-02 non-reassignable vs reassignable-lower-priority
    a = set_air(deep(BASE), "M-UAV-02", status="BUSY", availability="BUSY",
                reassignable=False, current_mission="M-M-HOLD-001", mission_priority="HIGH")
    b = set_air(deep(BASE), "M-UAV-02", status="BUSY", availability="REASSIGNABLE",
                reassignable=True, current_mission="M-L-HOLD-001", mission_priority="NORMAL")
    pairs.append({"id": "P8", "variable": "M-UAV-02 reassignability",
                  "desc": "non-reassignable vs reassignable(lower prio)",
                  "expect": "only the reassignable lower-priority aircraft may be preempted",
                  "a": a, "b": b})

    # Pair 9: M-UAV-02 landing compatibility includes/excludes V1
    a = deep(BASE)
    b = set_air(deep(BASE), "M-UAV-02", landing_compatibility=["V2", "V3"])
    pairs.append({"id": "P9", "variable": "M-UAV-02 landing compatibility",
                  "desc": "V1-compatible vs V1-incompatible",
                  "expect": "V1-incompatible aircraft must not be sent to V1",
                  "a": a, "b": b})

    return pairs


def action_of(dec: Dict[str, Any]) -> Dict[str, Any]:
    return dec.get("action") or {}


def verdict(pair_id: str, a: Dict[str, Any], b: Dict[str, Any]) -> str:
    """Directional sanity verdict for a pair (per-pair, explicit)."""
    ra, rb = a.get("aircraft_id"), b.get("aircraft_id")
    ta, tb = a.get("type"), b.get("type")
    if pair_id == "P1":   # C2 LOST on M-UAV-02 -> must not select it
        return "PASS" if rb != "M-UAV-02" else "FAIL"
    if pair_id == "P2":   # V1 UNAVAILABLE -> must not dispatch to V1
        return "PASS" if (tb != "DISPATCH" or b.get("target_site") != "V1") else "FAIL"
    if pair_id == "P3":   # priority NORMAL vs CRITICAL -> observational
        return "OBSERVED"
    if pair_id == "P4":   # battery insufficient -> must not select M-UAV-02
        return "PASS" if rb != "M-UAV-02" else "FAIL"
    if pair_id == "P5":   # ground ETA 120 vs 400 -> observational
        return "OBSERVED"
    if pair_id == "P6":   # no backup -> ground fallback / delay / cancel
        return "PASS" if tb in ("GROUND_FALLBACK", "DELAY", "CANCEL", "ESCALATE", "NO_ACTION") else "FAIL"
    if pair_id == "P7":   # endurance insufficient -> must not select M-UAV-02
        return "PASS" if rb != "M-UAV-02" else "FAIL"
    if pair_id == "P8":   # non-reassignable M-UAV-02 must not be preempted in A
        return "PASS" if ra != "M-UAV-02" else "FAIL"
    if pair_id == "P9":   # V1-incompatible M-UAV-02 -> must not select it
        return "PASS" if rb != "M-UAV-02" else "FAIL"
    return "OBSERVED"


def main() -> int:
    cfg = yaml.safe_load((ROOT / "config" / "scenario_config.yaml").read_text(encoding="utf-8"))
    p3 = yaml.safe_load((ROOT / "config" / "phase3_config.yaml").read_text(encoding="utf-8"))
    llm = LLMManager(cfg, p3)
    pairs = build_pairs()
    OUT.mkdir(parents=True, exist_ok=True)

    rows = []
    with open(OUT / "counterfactual.jsonl", "w", encoding="utf-8") as f:
        for p in pairs:
            da = llm.decide(p["a"])
            db = llm.decide(p["b"])
            aa, ab = action_of(da), action_of(db)
            v = verdict(p["id"], aa, ab)
            rec = {
                "pair_id": p["id"], "variable": p["variable"], "desc": p["desc"],
                "expect": p["expect"],
                "A": {"action": aa, "status": da["llm_metadata"]["validation_status"],
                      "retry": da["llm_metadata"]["retry_count"]},
                "B": {"action": ab, "status": db["llm_metadata"]["validation_status"],
                      "retry": db["llm_metadata"]["retry_count"]},
                "verdict": v,
            }
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False,
                               separators=(",", ":")) + "\n")
            f.flush()
            rows.append(rec)
            print(f"{p['id']} {p['desc']:<40} A={aa.get('type'):<14} {aa.get('aircraft_id') or '-'}"
                  f"  B={ab.get('type'):<14} {ab.get('aircraft_id') or '-'}  -> {v}", flush=True)

    write_report(rows)
    print(f"\nWrote counterfactual results + {REPORT.name}")
    return 0


def write_report(rows: List[Dict[str, Any]]) -> None:
    n_pass = sum(1 for r in rows if r["verdict"] == "PASS")
    n_obs = sum(1 for r in rows if r["verdict"] == "OBSERVED")
    n_check = sum(1 for r in rows if r["verdict"] == "CHECK")
    n_fail = sum(1 for r in rows if r["verdict"] == "FAIL")
    lines = [
        "# LLM Counterfactual Sanity (Phase 3)",
        "",
        "9 paired states; only ONE variable changes between A and B. The LLM is",
        "required to produce a *directionally correct* decision change, not to match",
        "the Rule Manager.",
        "",
        "| pair | variable | A | B | verdict |",
        "|------|----------|---|---|---------|",
    ]
    for r in rows:
        aa, ab = r["A"]["action"], r["B"]["action"]
        a_txt = f"{aa.get('type')} {aa.get('aircraft_id') or ''}".strip()
        b_txt = f"{ab.get('type')} {ab.get('aircraft_id') or ''}".strip()
        lines.append(f"| {r['pair_id']} | {r['variable']} | {a_txt} | {b_txt} | {r['verdict']} |")
    lines += [
        "",
        f"**Summary:** {n_pass} PASS / {n_obs} OBSERVED / {n_check} CHECK / {n_fail} FAIL "
        f"(total {len(rows)}).",
        "",
        "A PASS means the causal change produced the required directional change;",
        "OBSERVED is for observational pairs (priority / ground-ETA) where the",
        "behaviour is recorded without a pass/fail gate.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
