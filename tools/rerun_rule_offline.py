"""Regenerate the RULE offline outputs after the Rule-Manager destination-filter fix.

Reuses the exact 25 states from tools/run_phase3_offline.build_states(), runs ONLY
the Rule Manager (no LLM calls), and rewrites rule_outputs.jsonl plus the `rule`
rows of feasibility_checks.jsonl. The LLM rows/files are left untouched.
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from managers.rule_based import RuleBasedManager  # noqa: E402
from safety.feasibility_checker import FeasibilityChecker  # noqa: E402
from safety.semantic_validator import SemanticValidator  # noqa: E402
from tools.run_phase3_offline import build_states, registry_from_gs  # noqa: E402

OUT = ROOT / "runs" / "phase3_offline_decisions"


def main() -> int:
    cfg = yaml.safe_load((ROOT / "config" / "scenario_config.yaml").read_text(encoding="utf-8"))
    p3 = yaml.safe_load((ROOT / "config" / "phase3_config.yaml").read_text(encoding="utf-8"))
    rule = RuleBasedManager(cfg)
    sem = SemanticValidator(str(ROOT / p3["resource_compatibility"]))
    checker = FeasibilityChecker(None, cfg)

    # preserve existing LLM rows in feasibility_checks.jsonl
    feas_rows = [json.loads(l) for l in (OUT / "feasibility_checks.jsonl").read_text(encoding="utf-8").splitlines()]
    llm_rows = [r for r in feas_rows if r.get("manager") == "llm"]

    states = build_states()
    rule_f = open(OUT / "rule_outputs.jsonl", "w", encoding="utf-8")
    new_rule_rows = []

    def wj(fh, obj):
        fh.write(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")

    for i, st in enumerate(states):
        gs, sid = st["gs"], f"S{i + 1:02d}"
        reg = registry_from_gs(gs)
        checker.registry = reg
        rdec = rule.decide(gs)
        ract = rdec.get("action")
        rsem = sem.validate(ract, gs) if ract else {"valid": True, "error_types": []}
        rchk = checker.check(ract) if ract else {"valid": True, "violations": []}
        wj(rule_f, {"state_id": sid, "category": st["category"], "decision": rdec,
                    "semantic_valid": rsem["valid"], "semantic_errors": rsem["error_types"],
                    "feasible": rchk["valid"], "violations": rchk["violations"]})
        new_rule_rows.append({"state_id": sid, "manager": "rule",
                              "decision_id": rdec["decision_id"], "action": ract,
                              "valid": rchk["valid"], "violations": rchk["violations"],
                              "semantic_errors": rsem["error_types"]})
        at = (ract or {}).get("type", "NOOP")
        print(f"[{sid}] {st['category']:<22} rule={at:<15} semantic_ok={rsem['valid']} feasible={rchk['valid']}", flush=True)

    rule_f.close()
    # rewrite feasibility_checks.jsonl = new rule rows + preserved LLM rows (stable order)
    with open(OUT / "feasibility_checks.jsonl", "w", encoding="utf-8") as f:
        for r in new_rule_rows + llm_rows:
            f.write(json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")

    # quick report: any rule action still infeasible / semantic-invalid?
    bad = [r for r in new_rule_rows if not r["valid"] or r["semantic_errors"]]
    print(f"\n{len(new_rule_rows)} rule states; {len(bad)} with checker/semantic rejection:")
    for r in bad:
        print(f"  {r['state_id']} action={ (r['action'] or {}).get('type') } "
              f"violations={r['violations']} semantic={r['semantic_errors']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
