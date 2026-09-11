# LLM Backend Reliability (Finalization §27)

Backend behavior is reported **separately from policy** and from the primary
statistics. Every LLM call is recorded in `manager_outputs.jsonl`
(`llm_metadata`) and summarized in `runtime.json`.

Artifact: `outputs/experiment1_final/llm_reliability.json`
(generator `tools/audit_llm_reliability.py`). Numbers below are for the complete
**B4b primary** (240 runs → 242 calls) and the **B4a ablation** (60 runs, filled
when complete).

## B4b primary (240 runs)

| quantity | value |
|---|---|
| LLM calls | 242 (240 first-decisions + 2 orchestrator re-decisions) |
| unique `response_id` | 240 / 240 |
| repeated `response_id` | 0 |
| **empty content** | **0** |
| **transport errors** | **2** (0.83 %) — `WinError 10060` connection timeout |
| schema/semantic rejections | 0 (all 240 successful calls `VALID_ACTION`) |
| `finish_reason` | `stop` ×240, `None` ×2 (the 2 transport errors) |
| client retries | 0 (recovery is at the orchestrator's periodic re-decision) |
| latency min / median / max | 0.0 s / 21.98 s / 149.61 s |
| **cache-hit completions (sub-second reuse)** | **0** |
| cached *prompt* tokens (KV cache, normal) | 189,184 |

### Cache / independence conclusion

- The ~80 % sub-second cache behavior observed in the *old v2 same-prompt×10*
  design is **absent here**: every B4b prompt is unique (unique seed → unique
  Global State), so **0 cached-completion reuses** and **240/240 unique
  `response_id`s**. Each of the 240 B4b primary observations is an **independent
  inference** over an independent seed. (`cached_tokens` counts only the
  server-side prompt KV-cache, not a response replay.)

### The 2 transport errors (kept, not excluded)

| run | effect |
|---|---|
| `E1_L_H_high / seed20240612 / B4b` | 1st decision timed out; orchestrator re-decided at t+30 s → `GROUND_FALLBACK`; completed on time, no damage. |
| `E1_M_C_high / seed20240607 / B4b` | 1st decision timed out; re-decided at t+30 s → `GROUND_FALLBACK`; the 30 s delay pushed a borderline case (ground ETA 182 s vs CRITICAL slack 180 s) into a **deadline violation** (212 s vs 180 s). |

These runs are **kept in the primary statistics** (Finalization §30: no deleting
LLM bad seeds; exclusions are only simulator crash / corrupted artifact /
protocol violation — a transient, protocol-recovered network timeout is none of
these). They are reported here so the reader can see the backend's honest
contribution to B4b's measured deadline-violation rate.

## Empty-output / no-silent-substitution policy (Finalization §16)

- On empty content, the manager records `empty_content` and does **not**
  substitute a B2/B1 action (verified in `managers/llm_manager.py`: empty →
  no action → orchestrator re-decides on the next periodic tick).
- On transport error, the manager records `LLM_TRANSPORT_ERROR` and returns
  `action=None` (no silent fallback to a heuristic). Recovery is the
  orchestrator's standard periodic re-decision.
- **0 empty-content events** occurred in the primary.

## Verdict

Backend is reliable for the primary: 240/240 unique independent inferences,
0 empty outputs, 0 silent substitutions, 0 response-replay caches; 2 transient
timeouts (0.83 %) recovered by the protocol's own re-decision loop, whose cost
(1 deadline violation in a borderline scenario) is included in B4b's reported
performance.
