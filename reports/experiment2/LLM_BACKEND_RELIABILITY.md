# Experiment 2 — LLM Backend Reliability (protocol §23/§30)

Backend behaviour is reported **separately from policy performance**. Every B4b
call is recorded in `manager_outputs.jsonl` (`llm_metadata`) and summarized in
`outputs/experiment2/llm_reliability.json`.

**B4b primary: 320 runs → 694 LLM calls** (event-triggered t=300 + t=360,
periodic re-decisions, structured retries).

| quantity | value |
|---|---|
| LLM calls | 694 |
| successful inferences (VALID_ACTION) | 633 |
| **transport errors** (LLM_TRANSPORT_ERROR) | **61 (8.8 %)** |
| **empty content** (retry-recovered) | **5** |
| structured retries | 5 |
| schema/semantic rejections after retry | 0 |
| unique `response_id` | 629 / 633 responses (4 backend cache replays — see below) |
| latency min / median / mean / max | 0.0 / 22.2 / 33.0 / 241.4 s |
| sub-second completions | 4 (backend cache replays, see below) |
| prompt KV-cache tokens | 1,061,120 (normal) |

## Transport errors (61 — kept in the primary, per the frozen policy)

61 transport errors (`WinError 10060` connection timeouts) are concentrated in
an endpoint-availability window during the tail of the primary run — the
heaviest cells are `E2_F6_C2/seed20240613` (9 consecutive errors; recovered at
t≈660, completed by air at t=690, deadline violated) and several neighbouring
F6_C2/F6_C3 cells (3–5 errors each). Every error follows the frozen recovery
policy: the manager returns **no action** (never a silent B2/B1 substitution),
the orchestrator re-decides on the next 30-s periodic tick, and the run is
**kept in the primary dataset**. These cells are the entire source of the raw
B4b−B2 completion-time divergence in `E2_F6_C2` (+46.9 s) and `E2_F6_C3`
(+19.5 s) — after Holm correction no scenario shows a significant B2–B4b
difference (see `EXPERIMENT2_FINAL_RESULTS.md`). This is an interface/backend
effect, not a policy effect, and is reported as such.

## 4 backend cache replays (design consequence — documented, not an independence violation)

The t=300 Global State of `E2_F4_C1` is **byte-identical** to that of
`E2_F3_C3` for the same seed by scenario construction: the two classes differ
only in the t=360 failure (the ground context and workload are frozen and
identical). For 4 seeds the backend therefore served the cached t=300
completion to the second cell (same `response_id`, 0.06–0.08 s latency). The
t=300 decision content is identical and correct in both cells. Each cell's
t=360 (failure) decision is an independent inference with a unique
`response_id` (verified). The experimental unit remains scenario × seed: the
units diverge at the failure and have genuinely different post-failure
trajectories — the 4 cached cells are **not** same-prompt replicates of a
single scenario and are not excluded. (Same-prompt × N repetition, which the
independence rule forbids, does not occur.)

## Empty-content / no-silent-substitution policy

- 5 empty-content first attempts were recovered by the frozen structured retry
  (recorded `retry_count`, `empty_content_count`); no empty output leaked into
  the dataset.
- On transport error the manager records `LLM_TRANSPORT_ERROR` and returns
  `action=None` — recovery is the orchestrator's periodic re-decision.
- **0 silent substitutions**: for every ISSUED action,
  `normalized_action == executed_action` (verified across all 1280 runs).

## Verdict

The backend completed the primary with **0 crashed B4b runs** and **0
excluded runs**. The 61 transient timeouts (8.8 %) and 5 empty outputs were
recorded, protocol-recovered, and kept — their measurable cost (delayed
recovery, extra deadline violations in the affected F6 cells) is included in
B4b's reported performance and is the documented reason B4b's aggregate
completion time trails B2 by ≈4.5 s with a negligible effect size (d = 0.07).
