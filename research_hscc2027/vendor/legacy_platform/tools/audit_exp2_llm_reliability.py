"""Experiment 2 — LLM Backend Reliability Audit (protocol §23).

Backend behavior reported separately from policy. Reads every B4b run's
manager_outputs.jsonl + runtime.json and summarizes:

  calls, unique response_ids, repeated ids, empty content, transport errors,
  schema/semantic rejections, finish_reason, retries, latency, cached tokens,
  cache-subsecond calls.

Artifact: outputs/experiment2/llm_reliability.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read_jsonl(p: Path):
    out = []
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def main() -> int:
    with open(ROOT / "config" / "experiment2_matrix.yaml", encoding="utf-8") as f:
        e2 = yaml.safe_load(f)["experiment2"]
    with open(ROOT / "config" / "experiment2_seeds.yaml", encoding="utf-8") as f:
        seeds = list(yaml.safe_load(f)["primary_seeds"])

    calls = []
    per_run = []
    n_runs = 0
    for s in e2["scenarios"]:
        for seed in seeds:
            rd = ROOT / "runs" / "experiment2" / s["id"] / f"seed{seed}" / "B4b"
            if not (rd / "metrics.json").exists():
                continue
            n_runs += 1
            decs = read_jsonl(rd / "manager_outputs.jsonl")
            run_calls = [d["llm_metadata"] for d in decs if d.get("llm_metadata")
                         and not d["llm_metadata"].get("replay")]
            per_run.append({"scenario_id": s["id"], "seed": seed,
                            "n_calls": len(run_calls)})
            calls.extend(run_calls)

    ids = [c.get("response_id") for c in calls if c.get("response_id")]
    unique = len(set(ids))
    repeated = len(ids) - unique
    empty = sum(1 for c in calls if c.get("empty_content_count", 0) > 0)
    transport = sum(1 for c in calls if c.get("validation_status") == "LLM_TRANSPORT_ERROR")
    retries = sum(1 for c in calls if c.get("retry_count", 0) > 0)
    lats = [c.get("latency_s", 0.0) for c in calls]
    lats_sorted = sorted(lats)
    cache_subsec = sum(1 for l in lats if l < 1.0)
    finish = {}
    for c in calls:
        fr = c.get("finish_reason")
        finish[fr] = finish.get(fr, 0) + 1
    status = {}
    for c in calls:
        st = c.get("validation_status")
        status[st] = status.get(st, 0) + 1
    tokens = {
        "prompt": sum(c.get("prompt_tokens", 0) for c in calls),
        "completion": sum(c.get("completion_tokens", 0) for c in calls),
        "reasoning": sum(c.get("reasoning_tokens", 0) for c in calls),
        "output": sum(c.get("output_tokens", 0) for c in calls),
        "cached_prompt_tokens": sum(c.get("cached_tokens", 0) for c in calls),
    }
    out = {
        "b4b_runs": n_runs,
        "llm_calls": len(calls),
        "unique_response_ids": unique,
        "repeated_response_ids": repeated,
        "empty_content": empty,
        "transport_errors": transport,
        "schema_semantic_rejections_after_retry": status,
        "retry_count_total": retries,
        "finish_reasons": finish,
        "latency": {
            "min": round(min(lats), 3) if lats else None,
            "median": round(lats_sorted[len(lats_sorted) // 2], 3) if lats else None,
            "mean": round(sum(lats) / len(lats), 3) if lats else None,
            "max": round(max(lats), 3) if lats else None,
        },
        "cache_subsecond_calls": cache_subsec,
        "tokens": tokens,
        "per_run_calls": per_run,
    }
    out_dir = ROOT / "outputs" / "experiment2"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "llm_reliability.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "per_run_calls"},
                     indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
