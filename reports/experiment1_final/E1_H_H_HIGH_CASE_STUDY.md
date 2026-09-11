# E1_H_H_high Deep Case Study (Finalization §25)

`E1_H_H_high` = HIGH ground disruption × HIGH urgency × high workload. This is
the scenario where the (superseded) v2 run observed B4-v2b preempting existing
service for emergency speed. Here it is re-measured on 20 independent seeds with
the corrected (fair, leak-free) candidate table.

Artifact: `outputs/experiment1_final/E1_H_H_high_case_study.csv`
(generator `tools/case_study_e1_h_h_high.py`).

## Setup facts (identical across seeds)

- ground fallback ETA = **228.6 s** (HIGH disruption detour); deadline slack = 300 s
  (HIGH urgency) → ground **meets** the deadline (228.6 < 300), but is slow.
- target mission priority = HIGH; all 4 aircraft are busy (high workload), so air
  support requires a **REASSIGN** (preempt an existing NORMAL-priority service).

## Result (n = 20 seeds)

| manager | action | completion (mean) | existing-service damage | deadline violation |
|---|---|---|---|---|
| B2 | `GROUND_FALLBACK` in **20/20** | 229.0 s | 0.00 | 0/20 |
| B4b | `REASSIGN` in **12/20**, `GROUND_FALLBACK` in 8/20 | **217.1 s** | **0.60** (1 mission per preempt) | 0/20 |

- B2's frozen objective prices the preemption (w2[HIGH]=80 + w3=30) above the
  12 s of ground delay, so B2 never preempts → 229 s, zero damage.
- B4b, given the same facts, preempts a nearby busy aircraft in 12/20 seeds,
  completing at 199–222 s (mean **12 s faster**) but damaging exactly **1 existing
  mission** per preemption (0.60 mean damage).
- B4b never preempts in the other 8/20 seeds (its ground-fallback choice matches
  B2 there), so the divergence is a genuine per-seed decision, not a fixed rule.

## Paired statistics (B2 vs B4b, n = 20)

| contrast | value |
|---|---|
| completion paired t-test p | 0.000175 |
| completion Wilcoxon p | 0.002209 |
| **Holm-corrected p** | **0.0082** (significant) |
| paired effect size (Cohen's d) | **1.04** (large) |
| damage McNemar p | 0.000488 (significant) |

## Interpretation

In the one scenario class where preemption is genuinely on the boundary, B4b
makes a **deliberate, measurable speed↔service-preservation trade-off**: ~12 s
(≈5 %) faster emergency completion at the cost of 0.60 interrupted existing
missions per run. This is NOT a categorical "B4b wins" — it is a **Pareto
operating point**: B2 is the service-preserving operating point, B4b the
speed-favouring one. On all other 11 scenarios B2 and B4b coincide (or differ
only marginally), so the aggregate B2↔B4b gap is ~1 s (see
`EXPERIMENT1_FINAL_RESULTS.md`).
