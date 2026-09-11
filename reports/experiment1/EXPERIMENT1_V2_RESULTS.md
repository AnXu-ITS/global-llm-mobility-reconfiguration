> **历史中间版本，非当前论文结果。** 当前独立种子final结果见 [EXPERIMENT1_FINAL_RESULTS.md](EXPERIMENT1_FINAL_RESULTS.md) 和 `outputs/paper_final/results.json`。

# Experiment 1 — v2 Phase-1 Results (interface & information fairness)

This reports the re-run specified in `EXPERIMENT1_V2_DESIGN.md`. It keeps the
12 frozen scenarios, fixes the interface/information deficits the independent
review identified, and re-runs the LLM under two ablation arms. **Nothing was
tuned to make the LLM win**; the result below is what the fixed interface
produces.

## What was changed (implemented)

| fix | review § | implementation |
|---|---|---|
| unified action contract (REASSIGN preemption) | §3 | `prompts/manager_v2.txt` (new, versioned) |
| shared candidate table (ETA / violation / preempt-loss / endurance) | §4 | `orchestrator/candidate_info.py` injected into every Global State |
| `scenario_seed` vs `llm_repeat_id` + cache/version capture | §6 | `tools/run_experiment1_v2.py`, `run_meta.json`, `response_id`/`cached_tokens`/`created` in LLM metadata |
| execution-based metrics | §7 | `air_intervention` from `actions.csv result=ISSUED` (+ flush fix) |
| normalize-then-validate, env-computed ETA | §9 | `phase3_orchestrator`, `phase2_orchestrator` |

**Ablation arms** (both use prompt v2; only the candidate table differs):

- `B4v2a` — prompt fix **only** (no candidate table shown to the LLM).
- `B4v2b` — prompt fix **plus** the shared candidate table.

B0/B1/B2 were re-run once per scenario (deterministic); B4v2a/B4v2b were run
with 10 labelled repeats per scenario. 276 runs total, all completed.

## Corrected per-manager summary (12 scenarios, equal weight)

| manager | mean comp (s) | deadline viol. | damage/run | air rate | unnecessary-air | signed saved (s) |
|---|---|---|---|---|---|---|
| B0 (no cross-layer) | 187.67 | 33.33 % | 0 | 0 % | 0 % | — |
| B1 (rule, air-first) | 149.50 | 25.00 % | 0.500 | 100 % | 66.67 % | +38.17 |
| B2 (optimization) | 145.50 | 16.67 % | **0.083** | **58.33 %** | **33.33 %** | +42.17 |
| B4-v2a (LLM, prompt-only) | 149.75 | 25.00 % | 0.500 | 100 % | 66.67 % | +37.92 |
| **B4-v2b (LLM + shared table)** | **142.28** | **16.67 %** | 0.183 | 68.33 % | 43.33 % | **+45.38** |

(v1, archived, for reference — B4 was 157.69 s / 22.92 % / 0.225 / 72.50 % /
49.17 % / +29.97 s.)

## Interpretation of the ablation

1. **Prompt fix alone (v2a) reproduces the air-first rule.** With the corrected
   action contract (preemption now described), the LLM preempts the busy
   reassignable aircraft whenever it is legal — the same policy as B1
   (comp 149.75 vs 149.50, air 100 %, damage 0.500). This isolates the §3
   interface error: the v1 prompt simply never told the LLM it *could* preempt.

2. **Adding the shared candidate table (v2b) makes the LLM selective.** In the
   four "ground-preferable / borderline" high-workload scenarios
   (`E1_L_C_high`, `E1_L_H_high`, `E1_M_C_high`, `E1_M_H_high`) v2a still
   preempts (like B1, net *negative* saved time), whereas v2b switches to ground
   (net zero, zero damage) — exactly the behaviour the review said B2 has but
   the LLM could not reconstruct from the v1 Global State:

   | scenario | B4-v2a | B4-v2b |
   |---|---|---|
   | E1_L_C_high | air, −37.0 s, damage 1.0 | **ground, 0 s, damage 0** |
   | E1_L_H_high | air, −37.0 s, damage 1.0 | **ground, 0 s, damage 0** |
   | E1_M_C_high | air, −7.0 s, damage 1.0 | **ground, 0 s, damage 0** |
   | E1_M_H_high | air, −7.0 s, damage 1.0 | ground/mixed, −1.4 s, damage 0.2 |

3. **Net effect of v2b.** The LLM with the shared table matches B2 on deadline
   violation (16.67 %) and is **slightly faster** (142.28 s vs 145.50 s; signed
   saved +45.38 s vs +42.17 s). It still has a higher damage rate (0.183 vs
   0.083) and unnecessary-air rate (0.433 vs 0.333), driven by `E1_H_H_high`,
   where v2b preempts a NORMAL logistics mission for a HIGH medical mission even
   though ground (229 s) already meets the 300 s deadline. B2's frozen weights
   price that preemption (w2+w3 = 70) above the 40 s speed gain, so B2 declines.
   **This is a preference gap (speed vs service preservation), not an
   information deficit** — the candidate table was provided and the LLM chose
   speed.

## Attribution conclusion (RQ1, Phase 1)

The v1 negative/limited LLM result was **not** evidence that the LLM cannot do
selective ground–air reconfiguration. Once (a) the legal action space is stated
correctly and (b) the same physical/cost features B1/B2 receive are given to the
LLM, the LLM (B4-v2b) matches or slightly exceeds the frozen optimisation
baseline B2 on the primary objectives (completion time, deadline violation) and
only differs on the secondary speed-vs-disruption trade-off.

## LLM-call independence (review §6) — important caveat

The backend **caches identical prompts**: across the 10 repeats per cell,
~80 % of calls returned in under 1 s (cached completion), and only ~20 % were
real inference (unique `response_id`, seconds-to-tens-of-seconds latency).

| arm | decisions | unique response ids | sub-second (cached) | unique fraction |
|---|---|---|---|---|
| B4v2a | 121 | 24 | 94 | 0.198 |
| B4v2b | 120 | 21 | 97 | 0.175 |

Consequences, reported honestly:

- The 10 repeats per (scenario, arm) are **not independent samples**; they are
  ~2 effective unique inferences plus cached duplicates. Per-cell rates such as
  "damage 0.2" (E1_M_H_high v2b) mean *one of ~two distinct responses
  preempted*, not a 20 % probability.
- The **v2a vs v2b contrast is valid**: the two arms use different prompts
  (different cache keys), so their first inferences are independent, and the
  policy difference is driven by the candidate table, not by noise.
- No p-values/CIs are reported on the LLM cells because the repeat count is not
  a valid sample size under caching. The comparison above is a **deterministic
  policy difference** on a frozen scenario, not a stochastic claim.

## Remaining limitations (→ Phase 2)

- Ground task is still a static ETA, existing missions never complete/recover,
  battery is full, one OD/release (review §5). These need the Phase-2 traffic
  realism before a traffic-system claim.
- The LLM's speed-vs-disruption preference differs from B2's frozen weights; a
  future arm can state the objective explicitly to test whether the gap is
  preference or reasoning.

## Files

- results: `runs/experiment1_v2/` (276 runs) + `runs/experiment1_v2/experiment1_v2_analysis.json`
- analysis: `tools/analyze_experiment1_v2_rerun.py`, `tools/check_experiment1_v2_independence.py`
- runner: `tools/run_experiment1_v2.py`
- prompt: `prompts/manager_v2.txt` · shared evaluator: `orchestrator/candidate_info.py`
