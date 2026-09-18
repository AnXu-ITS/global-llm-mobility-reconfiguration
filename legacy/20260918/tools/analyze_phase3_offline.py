"""Analyze Phase-3 offline decisions and emit reports/LLM_OFFLINE_SANITY.md."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "runs" / "phase3_offline_decisions"
REPORT = ROOT / "reports" / "LLM_OFFLINE_SANITY.md"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    llm_rows = load_jsonl(OUT / "llm_outputs.jsonl")
    rule_rows = load_jsonl(OUT / "rule_outputs.jsonl")
    feas = load_jsonl(OUT / "feasibility_checks.jsonl")
    states = load_jsonl(OUT / "states.jsonl")

    n = len(llm_rows)
    llm_feas = {f["state_id"]: f for f in feas if f["manager"] == "llm"}
    rule_feas = {f["state_id"]: f for f in feas if f["manager"] == "rule"}

    # --- LLM metrics ---
    statuses = Counter()
    first_errs = Counter()
    action_types = Counter()
    retries = 0
    feasible_llm = 0
    llm_actions = 0
    latencies = []
    ptok = ctok = 0

    for r in llm_rows:
        meta = r["decision"]["llm_metadata"]
        statuses[meta["validation_status"]] += 1
        if meta.get("first_attempt_error"):
            first_errs[meta["first_attempt_error"]] += 1
        if meta["retry_count"] > 0:
            retries += 1
        act = r["decision"].get("action")
        if act:
            action_types[act.get("type")] += 1
            llm_actions += 1
        f = llm_feas.get(r["state_id"], {})
        if f.get("valid", True):
            feasible_llm += 1
        latencies.append(meta.get("latency_s", 0))
        ptok += meta.get("prompt_tokens", 0)
        ctok += meta.get("completion_tokens", 0)

    json_valid = 1.0 - statuses.get("JSON_ERROR", 0) / n
    schema_valid = 1.0 - statuses.get("SCHEMA_ERROR", 0) / n
    feasible_rate = feasible_llm / n
    no_action_rate = action_types.get("NO_ACTION", 0) / n
    retry_rate = retries / n
    unknown_res = first_errs.get("UNKNOWN_RESOURCE", 0) / n
    prio_viol = first_errs.get("PRIORITY_VIOLATION", 0) / n
    dup_assign = first_errs.get("DUPLICATE_ASSIGNMENT", 0) / n

    # --- Rule metrics (comparison) ---
    feasible_rule = sum(1 for r in rule_rows if r.get("feasible", True))
    rule_sem_ok = sum(1 for r in rule_rows if r.get("semantic_valid", True))
    rule_action_types = Counter(
        (r["decision"].get("action") or {}).get("type", "NOOP") for r in rule_rows)

    # --- min-condition gate ---
    gate = {
        "JSON validity = 100% after retry": json_valid == 1.0,
        "Schema validity = 100%": schema_valid == 1.0,
        "Unknown resource = 0 (final)": statuses.get("UNKNOWN_RESOURCE", 0) == 0,
        "Duplicate assignment = 0 (final)": statuses.get("DUPLICATE_ASSIGNMENT", 0) == 0,
        "Feasible action rate >= 95%": feasible_rate >= 0.95,
    }

    # --- per-state table ---
    lines = [
        "# LLM Offline Sanity (Phase 3)",
        "",
        f"**{n} representative Global States** (Phase-2 manager_inputs + audit "
        "snapshots + synthetic mutations), no live simulator.",
        "Model: `corp-ai/openai/deepseek-v4-pro`, prompt `manager_v1`, temperature=0.",
        "",
        "## Metrics",
        "",
        "| metric | value |",
        "|--------|-------|",
        f"| JSON validity rate (after retry) | {json_valid:.0%} ({n - statuses.get('JSON_ERROR', 0)}/{n}) |",
        f"| Schema validity rate | {schema_valid:.0%} |",
        f"| Feasible action rate | {feasible_rate:.0%} ({feasible_llm}/{n}) |",
        f"| Unknown-resource rate (first attempt) | {unknown_res:.0%} |",
        f"| Priority violation rate (first attempt) | {prio_viol:.0%} |",
        f"| Duplicate assignment rate (first attempt) | {dup_assign:.0%} |",
        f"| Retry rate | {retry_rate:.0%} ({retries}/{n}) |",
        f"| No-action rate | {no_action_rate:.0%} |",
        f"| avg latency | {sum(latencies)/len(latencies):.1f} s |",
        f"| tokens (prompt/completion) | {ptok} / {ctok} |",
        "",
        "## Minimum gate for live simulation",
        "",
    ]
    for k, v in gate.items():
        lines.append(f"- [{'PASS' if v else 'FAIL'}] {k}")
    gate_ok = all(gate.values())
    lines += [
        "",
        f"**Gate: {'PASS — proceed to live simulation' if gate_ok else 'FAIL — fix prompt/interface, do not change the simulator'}**",
        "",
        "## Action-type distribution (LLM)",
        "",
    ]
    for at, c in action_types.most_common():
        lines.append(f"- {at}: {c}")
    lines += [
        "",
        "## Rule vs LLM action comparison (sanity only)",
        "",
        "| category | rule action | llm action |",
        "|----------|-------------|------------|",
    ]
    cat_of = {s["state_id"]: s["category"] for s in states}
    for r in llm_rows:
        sid = r["state_id"]
        ra = (rule_rows[int(sid[1:]) - 1]["decision"].get("action") or {}).get("type", "NOOP") \
            if int(sid[1:]) - 1 < len(rule_rows) else "-"
        la = (r["decision"].get("action") or {}).get("type", "NOOP")
        lines.append(f"| {cat_of.get(sid, sid)} | {ra} | {la} |")
    lines += [
        "",
        f"Rule feasible rate: {feasible_rule}/{n}; Rule semantic-valid: {rule_sem_ok}/{n}.",
    ]

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Gate {'PASS' if gate_ok else 'FAIL'}: json={json_valid:.0%} schema={schema_valid:.0%} "
          f"feasible={feasible_rate:.0%} retry={retry_rate:.0%} no_action={no_action_rate:.0%}")
    print(f"first-attempt errors: {dict(first_errs)}")
    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
