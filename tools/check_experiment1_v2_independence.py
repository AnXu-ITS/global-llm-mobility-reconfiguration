"""Check LLM-call independence for the Experiment-1 v2 re-run (review §6).

For each (scenario, arm) it reads every repeat's manager_outputs.jsonl and
reports, across all decisions:
  - total decisions
  - total unique backend response ids
  - how many response ids repeat (cached-completion signal)
  - min/median/max latency
  - total cached prompt tokens (KV-cache; normal, not a response cache)

A unique response id per decision => independent inference. Repeated ids =>
the backend returned a cached completion, so those repeats are NOT independent
samples and must be reported as such.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "experiment1_v2"
LLM_ARMS = ("B4v2a", "B4v2b")


def collect(run_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    p = run_dir / "manager_outputs.jsonl"
    if not p.exists():
        return rows
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
            rows.append({
                "resp_id": mm.get("response_id"),
                "cached_tokens": int(mm.get("cached_tokens", 0) or 0),
                "latency": mm.get("latency_s"),
                "status": mm.get("validation_status"),
            })
    return rows


def main() -> int:
    scenarios = sorted({p.parent.parent.parent.name
                        for p in RUNS.glob("*/*/repeat*/manager_outputs.jsonl")})
    print("scenario | arm | decisions | unique_ids | repeated_ids | min/med/max lat | cached_prompt_tok | subsec")
    print("---|---|---|---|---|---|---|---")
    grand: Dict[str, Counter] = {}
    for s in scenarios:
        for arm in LLM_ARMS:
            base = RUNS / s / arm
            if not base.exists():
                continue
            rows: List[Dict[str, Any]] = []
            for rp in sorted(base.glob("repeat*/")):
                rows.extend(collect(rp))
            if not rows:
                continue
            ids = [r["resp_id"] for r in rows if r["resp_id"]]
            uniq = set(ids)
            idc = Counter(ids)
            repeated = sum(1 for k, v in idc.items() if v > 1)
            lats = sorted(r["latency"] for r in rows if r["latency"] is not None)
            cached = sum(r["cached_tokens"] for r in rows)
            # sub-second latency => the backend returned a cached completion
            # (real reasoning inference is ~10-60 s on this endpoint).
            subsec = sum(1 for r in rows
                         if r["latency"] is not None and r["latency"] < 1.0)
            med = lats[len(lats) // 2] if lats else 0
            print(f"{s} | {arm} | {len(rows)} | {len(uniq)} | {repeated} "
                  f"| {min(lats) if lats else 0}/{med}/{max(lats) if lats else 0} "
                  f"| {cached} | {subsec} subsec")
            grand.setdefault(arm, Counter())
            grand[arm]["decisions"] += len(rows)
            grand[arm]["unique"] += len(uniq)
            grand[arm]["repeated_ids"] += repeated
            grand[arm]["subsec"] += subsec

    print("\n## totals by arm\n")
    print("arm | decisions | unique_ids | repeated_ids | subsec | unique_fraction")
    print("---|---|---|---|---|---")
    for arm, c in grand.items():
        frac = c["unique"] / c["decisions"] if c["decisions"] else 0
        print(f"{arm} | {c['decisions']} | {c['unique']} | {c['repeated_ids']} "
              f"| {c['subsec']} | {frac:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
