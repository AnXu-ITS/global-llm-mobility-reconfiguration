"""LLM backend reliability audit (Finalization §27) — separate from policy.

Scans every B4a/B4b run's manager_outputs.jsonl (llm_metadata) + runtime.json
and reports: total calls, empty content, finish_reason distribution, retries,
schema/semantic failure rate, latency stats, cache-hit (sub-second) fraction,
cached prompt tokens, and response-id uniqueness.  Backend cache is NEVER
treated as an independent simulation sample.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "experiment1_final"
OUT = ROOT / "outputs" / "experiment1_final"


def collect_llm(run_dir: Path) -> List[Dict[str, Any]]:
    p = run_dir / "manager_outputs.jsonl"
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        mm = d.get("llm_metadata") or {}
        if mm:
            rows.append(mm)
    return rows


def main() -> int:
    arms = ("B4a", "B4b")
    summary: Dict[str, Any] = {}
    all_rows: Dict[str, List[Dict[str, Any]]] = {}
    for arm in arms:
        rows: List[Dict[str, Any]] = []
        for p in sorted(RUNS.glob(f"*/*/{arm}/manager_outputs.jsonl")):
            rows.extend(collect_llm(p.parent))
        all_rows[arm] = rows
        empty = sum(1 for r in rows if r.get("empty_content"))
        finish = {str(k): v for k, v in
                  Counter(r.get("finish_reason") for r in rows).items()}
        status = {str(k): v for k, v in
                  Counter(r.get("validation_status") for r in rows).items()}
        retries = sum(int(r.get("retry_count", 0) or 0) for r in rows)
        lats = sorted(r.get("latency_s") for r in rows if r.get("latency_s") is not None)
        transport_err = sum(1 for r in rows
                            if r.get("validation_status") == "LLM_TRANSPORT_ERROR")
        cache_hit = sum(1 for r in rows
                        if (r.get("latency_s") or 0) < 1.0
                        and r.get("validation_status") == "VALID_ACTION"
                        and not r.get("empty_content"))
        ids = [r.get("response_id") for r in rows if r.get("response_id")]
        cached_tok = sum(int(r.get("cached_tokens", 0) or 0) for r in rows)
        med = lats[len(lats) // 2] if lats else 0.0
        summary[arm] = {
            "calls": len(rows),
            "unique_response_ids": len(set(ids)),
            "repeated_response_ids": len(ids) - len(set(ids)),
            "empty_content": empty,
            "transport_error_calls": transport_err,
            "cache_hit_calls": cache_hit,
            "finish_reason": finish,
            "validation_status": status,
            "retry_total": retries,
            "latency_min_med_max_s": [round(lats[0], 2) if lats else None,
                                      round(med, 2), round(lats[-1], 2) if lats else None],
            "cached_prompt_tokens_total": cached_tok,
        }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "llm_reliability.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\n[saved] {OUT / 'llm_reliability.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
