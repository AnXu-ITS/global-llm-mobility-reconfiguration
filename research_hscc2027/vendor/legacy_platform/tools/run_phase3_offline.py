"""Phase 3 offline decision test.

Runs the Rule-Based Manager and the LLM Manager over >= 20 representative Global
State snapshots (Phase-2 manager_inputs + audit snapshots + synthetic mutations)
WITHOUT touching the live simulator, and records:

    runs/phase3_offline_decisions/states.jsonl
    runs/phase3_offline_decisions/rule_outputs.jsonl
    runs/phase3_offline_decisions/llm_outputs.jsonl
    runs/phase3_offline_decisions/feasibility_checks.jsonl
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from managers.llm_manager import LLMManager  # noqa: E402
from managers.rule_based import RuleBasedManager  # noqa: E402
from orchestrator.registry import Aircraft, Mission, Registry  # noqa: E402
from safety.feasibility_checker import FeasibilityChecker  # noqa: E402
from safety.semantic_validator import SemanticValidator  # noqa: E402

RUNS = ROOT / "runs" / "phase2_rule_manager"
OUT_DIR = ROOT / "runs" / "phase3_offline_decisions"


def load_gs(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot_states(case: str, times: List[int]) -> List[Dict[str, Any]]:
    p = RUNS / case / "snapshots.jsonl"
    by_t = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        by_t[obj["t"]] = obj["global_state"]
    return [by_t[t] for t in times if t in by_t]


def deep(gs: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(gs)


def synth_insufficient_battery(gs: Dict[str, Any]) -> Dict[str, Any]:
    g = deep(gs)
    for a in g["air"]:
        if a["id"] == "M-UAV-02":
            a["battery_pct"] = 0.0
            a["remaining_endurance_s"] = 0.0
    return g


def synth_insufficient_endurance(gs: Dict[str, Any]) -> Dict[str, Any]:
    g = deep(gs)
    for a in g["air"]:
        if a["id"] == "M-UAV-01":
            a["remaining_endurance_s"] = 0.0
    return g


def synth_site_unavailable(gs: Dict[str, Any]) -> Dict[str, Any]:
    g = deep(gs)
    if "V1" in g["infrastructure"]["landing_sites"]:
        g["infrastructure"]["landing_sites"]["V1"]["state"] = "UNAVAILABLE"
    return g


def synth_busy_resources(gs: Dict[str, Any]) -> Dict[str, Any]:
    g = deep(gs)
    for a in g["air"]:
        if a["id"] in ("M-UAV-01", "M-UAV-02"):
            a["status"] = "BUSY"
            a["availability"] = "BUSY"
            a["reassignable"] = False
            a["current_mission"] = "M-M-BACKUP-001"
            a["mission_priority"] = "HIGH"
    return g


def synth_all_unavailable(gs: Dict[str, Any]) -> Dict[str, Any]:
    g = deep(gs)
    for a in g["air"]:
        if a["id"] in ("M-UAV-01", "M-UAV-02"):
            a["status"] = "UNAVAILABLE"
            a["availability"] = "UNAVAILABLE"
            a["commandable"] = False
    return g


def build_states() -> List[Dict[str, Any]]:
    """Return labeled states with (category, source, t, gs)."""
    states: List[Dict[str, Any]] = []
    add = lambda cat, src, t, gs: states.append(
        {"category": cat, "source": src, "t": t, "gs": gs})

    mi = {case: [json.loads(l) for l in
                 (RUNS / case / "manager_inputs.jsonl").read_text(encoding="utf-8").splitlines()
                 if l.strip()] for case in ("C2_A", "C2_B", "C2_C")}

    # --- manager-input decision moments ---
    add("critical_mission", "C2_B:t300", 300, mi["C2_B"][0])
    add("c2_lost", "C2_B:t360", 360, mi["C2_B"][1])
    add("critical_mission", "C2_A:t300", 300, mi["C2_A"][0])
    add("c2_lost_logistics", "C2_A:t360", 360, mi["C2_A"][1])
    add("critical_mission", "C2_C:t300", 300, mi["C2_C"][0])
    add("ground_fallback", "C2_C:t360", 360, mi["C2_C"][1])

    # --- audit snapshots (non-overlapping times) ---
    for gs in snapshot_states("C2_B", [100, 299, 301, 310, 359, 361, 380, 421, 500]):
        t = gs["simulation_time"]
        cat = {100: "normal", 299: "pre_disruption", 301: "ground_disruption",
               310: "post_dispatch", 359: "pre_c2", 361: "needs_replan",
               380: "contingency_landed", 421: "completed", 500: "post_terminal"}[t]
        add(cat, f"C2_B:t{t}", t, gs)
    for gs in snapshot_states("C2_A", [100, 361]):
        t = gs["simulation_time"]
        cat = {100: "normal", 361: "needs_replan"}[t]
        add(cat, f"C2_A:t{t}", t, gs)
    for gs in snapshot_states("C2_C", [100, 361, 421]):
        t = gs["simulation_time"]
        cat = {100: "normal", 361: "no_backup", 421: "ground_fallback_completed"}[t]
        add(cat, f"C2_C:t{t}", t, gs)

    # --- synthetic mutations (from C2_B t=300 critical-mission state) ---
    base = mi["C2_B"][0]
    add("insufficient_battery", "synth:battery0", 300, synth_insufficient_battery(base))
    add("insufficient_endurance", "synth:endurance0", 300, synth_insufficient_endurance(base))
    add("landing_site_unavailable", "synth:V1_unavailable", 300, synth_site_unavailable(base))
    add("busy_resources", "synth:all_busy", 300, synth_busy_resources(base))
    add("all_unavailable", "synth:all_unavailable", 300, synth_all_unavailable(base))

    return states


def registry_from_gs(gs: Dict[str, Any]) -> Registry:
    reg = Registry()
    for a in gs.get("air", []):
        pos = a.get("position", {})
        ac = Aircraft(a["id"], a["type"], pos.get("lat", 0.0), pos.get("lon", 0.0),
                      status=a.get("status"), mission_id=a.get("current_mission"),
                      priority=a.get("mission_priority"), battery_pct=a.get("battery_pct"),
                      remaining_endurance_s=a.get("remaining_endurance_s"),
                      reassignable=a.get("reassignable"),
                      landing_site_compatibility=a.get("landing_compatibility"),
                      c2_status=a.get("c2_status"), gnss_status=a.get("gnss_status"),
                      commandable=a.get("commandable"))
        reg.add_aircraft(ac)
    for bucket in ("existing", "new"):
        for m in gs.get("missions", {}).get(bucket, []):
            mo = Mission(m["id"], m["type"], m["priority"], m["origin"], m["destination"],
                         deadline_s=m["deadline_s"] if m["deadline_s"] is not None else 1800.0,
                         assigned_resource=m.get("assigned_resource"), mode=m.get("mode"),
                         status=m.get("state"), ground_fallback=m.get("ground_fallback", True),
                         delay_cost=m.get("delay_cost", 10.0),
                         cancellation_cost=m.get("cancellation_cost", 100.0))
            reg.add_mission(mo)
    return reg


def main() -> int:
    cfg = yaml.safe_load((ROOT / "config" / "scenario_config.yaml").read_text(encoding="utf-8"))
    p3 = yaml.safe_load((ROOT / "config" / "phase3_config.yaml").read_text(encoding="utf-8"))

    rule = RuleBasedManager(cfg)
    llm = LLMManager(cfg, p3)
    sem = SemanticValidator(str(ROOT / p3["resource_compatibility"]))
    checker = FeasibilityChecker(None, cfg)  # registry injected per-state

    states = build_states()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    states_f = open(OUT_DIR / "states.jsonl", "w", encoding="utf-8")
    rule_f = open(OUT_DIR / "rule_outputs.jsonl", "w", encoding="utf-8")
    llm_f = open(OUT_DIR / "llm_outputs.jsonl", "w", encoding="utf-8")
    feas_f = open(OUT_DIR / "feasibility_checks.jsonl", "w", encoding="utf-8")

    def wj(fh, obj):
        fh.write(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                            separators=(",", ":")) + "\n")
        fh.flush()

    for i, st in enumerate(states):
        gs = st["gs"]
        sid = f"S{i + 1:02d}"
        reg = registry_from_gs(gs)
        checker.registry = reg

        wj(states_f, {"state_id": sid, "category": st["category"],
                      "source": st["source"], "t": st["t"]})

        # --- Rule Manager ---
        rdec = rule.decide(gs)
        ract = rdec.get("action")
        rsem = sem.validate(ract, gs) if ract else {"valid": True, "error_types": []}
        rchk = checker.check(ract) if ract else {"valid": True, "violations": []}
        wj(rule_f, {"state_id": sid, "category": st["category"], "decision": rdec,
                    "semantic_valid": rsem["valid"],
                    "semantic_errors": rsem["error_types"],
                    "feasible": rchk["valid"], "violations": rchk["violations"]})
        wj(feas_f, {"state_id": sid, "manager": "rule",
                    "decision_id": rdec["decision_id"],
                    "action": ract, "valid": rchk["valid"],
                    "violations": rchk["violations"],
                    "semantic_errors": rsem["error_types"]})

        # --- LLM Manager ---
        ldec = llm.decide(gs)
        lact = ldec.get("action")
        lchk = checker.check(lact) if lact else {"valid": True, "violations": []}
        wj(llm_f, {"state_id": sid, "category": st["category"], "decision": ldec,
                   "feasible": lchk["valid"], "violations": lchk["violations"]})
        wj(feas_f, {"state_id": sid, "manager": "llm",
                    "decision_id": ldec["decision_id"],
                    "action": lact, "valid": lchk["valid"],
                    "violations": lchk["violations"],
                    "llm_metadata": ldec.get("llm_metadata")})

        meta = ldec.get("llm_metadata", {})
        print(f"[{sid}] {st['category']:<22} rule={rdec.get('action',{}).get('type') if ract else 'NOOP':<15}"
              f" llm={(lact or {}).get('type', 'NONE'):<15} "
              f"status={meta.get('validation_status')} retry={meta.get('retry_count')} "
              f"lat={meta.get('latency_s')}s", flush=True)

    for f in (states_f, rule_f, llm_f, feas_f):
        f.close()
    print(f"\nWrote {len(states)} states to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
