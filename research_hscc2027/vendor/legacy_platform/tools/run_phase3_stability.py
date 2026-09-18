"""Phase 3 decision stability test (section J).

Calls the LLM 10 times on the SAME Global State and quantifies the consistency
of the *actual action* (not the natural-language reason):
    action consistency, selected-resource consistency, fallback consistency.

Outputs:
    runs/phase3_offline_decisions/stability.jsonl
    reports/LLM_DECISION_STABILITY.md
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from managers.llm_manager import LLMManager  # noqa: E402

OUT = ROOT / "runs" / "phase3_offline_decisions"
REPORT = ROOT / "reports" / "LLM_DECISION_STABILITY.md"

REPEATS = 10


def load_state(case: str, idx: int) -> Dict[str, Any]:
    p = ROOT / "runs" / "phase2_rule_manager" / case / "manager_inputs.jsonl"
    lines = [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return json.loads(lines[idx])


def main() -> int:
    cfg = yaml.safe_load((ROOT / "config" / "scenario_config.yaml").read_text(encoding="utf-8"))
    p3 = yaml.safe_load((ROOT / "config" / "phase3_config.yaml").read_text(encoding="utf-8"))
    llm = LLMManager(cfg, p3)
    gs = load_state("C2_B", 0)  # t=300 critical-mission dispatch state

    actions: List[str] = []
    resources: List[str] = []
    records: List[Dict[str, Any]] = []
    OUT.mkdir(parents=True, exist_ok=True)

    with open(OUT / "stability.jsonl", "w", encoding="utf-8") as f:
        for i in range(REPEATS):
            dec = llm.decide(gs)
            act = dec.get("action") or {}
            at = act.get("type", "NONE")
            ar = act.get("aircraft_id") or (act.get("type") if act.get("type") in ("GROUND_FALLBACK",) else None)
            actions.append(at)
            if ar:
                resources.append(ar)
            meta = dec["llm_metadata"]
            rec = {"run": i + 1, "action_type": at, "aircraft_id": act.get("aircraft_id"),
                   "mission_id": act.get("mission_id"), "target_site": act.get("target_site"),
                   "status": meta["validation_status"], "retry": meta["retry_count"],
                   "first_attempt_error": meta.get("first_attempt_error"),
                   "latency_s": meta["latency_s"]}
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False,
                               separators=(",", ":")) + "\n")
            f.flush()
            records.append(rec)
            print(f"run {i+1}: {at:<14} {act.get('aircraft_id') or '-'} "
                  f"status={meta['validation_status']} retry={meta['retry_count']}", flush=True)

    ac = Counter(actions)
    rc = Counter(resources)
    action_consistency = max(ac.values()) / REPEATS
    resource_consistency = max(rc.values()) / REPEATS if resources else 1.0
    fallback_consistency = (ac.get("GROUND_FALLBACK", 0) == REPEATS) if resources else None

    lines = [
        "# LLM Decision Stability (Phase 3)",
        "",
        f"Same Global State (C2_B t=300) queried {REPEATS} times, temperature=0.",
        "",
        "| metric | value |",
        "|--------|-------|",
        f"| action consistency | {action_consistency:.0%} ({ac.most_common(1)[0][0]}) |",
        f"| selected-resource consistency | {resource_consistency:.0%} ({rc.most_common(1)[0][0] if resources else 'n/a'}) |",
        f"| fallback consistency | {fallback_consistency} |",
        f"| retry rate | {sum(1 for r in records if r['retry'] > 0) / REPEATS:.0%} |",
        f"| all VALID_ACTION | {all(r['status'] == 'VALID_ACTION' for r in records)} |",
        "",
        "| run | action | aircraft | status | retry | latency_s |",
        "|-----|--------|----------|--------|-------|-----------|",
    ]
    for r in records:
        lines.append(f"| {r['run']} | {r['action_type']} | {r['aircraft_id'] or '-'} | "
                     f"{r['status']} | {r['retry']} | {r['latency_s']} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {REPORT.name}: action={action_consistency:.0%}, "
          f"resource={resource_consistency:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
