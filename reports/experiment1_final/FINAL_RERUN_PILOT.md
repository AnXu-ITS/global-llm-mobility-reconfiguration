# Final Rerun Mini Pilot (Finalization §21)

Pre-flight smoke of the corrected primary pipeline before the 960-run primary.
3 scenarios × 3 seeds × 4 primary managers = 36 runs, plus the earlier 30-run
seed-independence audit (B1) whose runs are reused (shared run dirs, never
re-run).

Pilot scenarios: `E1_H_C_low` (air clearly useful), `E1_M_C_high` (borderline),
`E1_L_H_high` (ground/preemption preferable). Seeds 20240601–20240603.

## Result

- **36 / 36 pilot runs completed** (every cell has `metrics.json`).
- **0 excluded runs** (`runs/experiment1_final/excluded_runs.csv` absent).
- Every run produced the full artifact contract: `run_config.yaml`, `events.csv`,
  `ground_state.csv`, `air_state.csv`, `missions.csv`, `candidate_info.jsonl`,
  `manager_inputs.jsonl`, `manager_outputs.jsonl`, `feasibility_checks.jsonl`,
  `semantic_checks.jsonl`, `action_pipeline.jsonl`, `actions.csv`, `metrics.json`,
  `runtime.json`, `run_meta.json`.
- LLM arms (9 B4b calls): all `finish_reason=stop`, all `VALID_ACTION`,
  **0 empty content**, **0 retries**, latency ≈ 9.9–23 s (real inference, not
  cache). Unique `response_id` per call.
- Per-seed realization (`runtime.json.seed_realization`) differs across seeds and
  is byte-identical across managers for a shared seed (paired design intact).

## Preliminary (NOT statistical — n = 3 seeds)

| manager | comp mean s | deadline-violation rate | existing-service damage | air rate | unnecessary-air rate |
|---|---|---|---|---|---|
| B0 | 187.7 | 0.667 | 0.000 | 0.000 | 0.000 |
| B1 | 180.8 | 0.303 | 0.697 | 1.000 | 0.394 |
| B2 | 148.0 | 0.333 | 0.000 | 0.333 | 0.000 |
| B4b | 148.0 | 0.333 | 0.000 | 0.333 | 0.000 |

Directionally consistent with the (superseded) v2 finding: B1 is fast-but-damaging
(always air, preempts existing service); B2 is service-preserving (ground when air
is not clearly needed). In these 3 scenarios B4b coincides with B2; whether B4b
differs from B2 (and where) is answered only by the full 20-seed × 12-scenario
primary.

## Decision

Pilot is clean → **proceed to the 960-run primary** (`tools/run_experiment1_final.py`
`--manager all`) and the 60-run B4a ablation (`--ablation`).
