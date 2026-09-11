# Experiment 1 Finalization — Final Results

Corrected primary dataset: `runs/experiment1_final/`
(12 scenarios × 20 independent seeds × 4 primary managers = 960 runs, plus the
6-scenario × 10-seed B4a interface ablation = 60 runs). All statistics use the
**independent unit = scenario × seed** (n = 20 per scenario), paired across
managers on identical (scenario, seed) initial state. Same-prompt repeats are
NOT samples.

Machine-readable: `outputs/experiment1_final/primary_analysis.json`,
`ablation_b4a_vs_b4b.json`, `B2_vs_B4b_tradeoff.csv`,
`E1_H_H_high_case_study.csv`, `llm_reliability.json`.

---

## A. Acceptance tests (EF-T1 … EF-T20) — **20 / 20 PASS**

See `EXPERIMENT1_FINAL_ACCEPTANCE_TESTS.md`. Every test is PASS; **no FAIL**.

## B. Leakage / fairness conclusion

**PASS — no optimization-solution leakage.** The shared candidate table
(`CANDIDATE_TABLE_VERSION 2.0.0`) is a pure, deterministic function of the Global
State + fleet constants, generated **without running B2**, containing **no** B2
objective score / ranking / best-candidate. Q1–Q5 = YES / YES / NO / NO / NO.
(Full audit: `CANDIDATE_TABLE_FAIRNESS_AUDIT.md`.)

## C. Primary completion

- Primary: **960 / 960** runs (B0 240, B1 240, B2 240, B4b 240).
- Ablation: **60 / 60** (B4a).
- **0 excluded runs** (`excluded_runs.csv` empty) — no seed pruning, no
  protocol-violation deletions.
- **1020 / 1020** runs satisfy the full artifact contract
  (`tools/verify_artifacts.py`).

## D. Final per-manager metrics (mean [95 % CI], pooled over 240 runs)

| metric | B0 | B1 | B2 | B4b |
|---|---|---|---|---|
| Critical completion (s) | 187.7 [183.6, 191.7] | 160.8 [154.3, 167.3] | 147.6 [142.2, 153.1] | **146.6** [141.4, 151.9] |
| Deadline-violation rate | 0.333 | 0.250 | **0.167** | **0.167** |
| Existing-service damage (mean missions) | 0.000 | 0.500 [0.436, 0.564] | **0.058** [0.028, 0.088] | 0.133 [0.090, 0.177] |
| Air-intervention rate | 0.000 | 1.000 | 0.558 | 0.633 |
| Unnecessary-air rate (θ=60 s) | 0.000 | 0.333 | **0.000** | 0.050 |
| Ground-fallback rate | 1.000 | 0.000 | 0.442 | 0.367 |
| Reassignment count (mean) | 0.000 | 0.500 | 0.058 | 0.133 |
| Time saving vs B0 (s) | 0.0 | 26.9 [19.2, 34.5] | 40.1 [34.4, 45.7] | **41.0** [35.5, 46.6] |
| Disruption efficiency | 0.0 | 32.9 [26.3, 39.4] | 39.4 [33.8, 45.1] | **39.8** [34.2, 45.4] |

Both coordinated managers (B2, B4b) substantially beat the no-coordination (B0)
and air-first (B1) baselines on completion time and deadline violations. B1's
air-first rule achieves speed **only by damaging existing service** (0.50 mean
damage, 33 % unnecessary air).

## E. B2 vs B4b — paired statistics

**Aggregate (n = 240):** B4b ≈ B2 within ~1 s of completion (146.6 vs 147.6 s),
with slightly more existing-service damage (0.133 vs 0.058) and 5 % unnecessary
air (vs 0 %). The two are **Pareto operating points**, not a categorical win.

**Per-scenario (n = 20):** B2 and B4b make **identical** decisions in 8 of 12
scenarios. The only significant divergence is:

| scenario | B2 comp / dmg | B4b comp / dmg | paired t p | **Holm p** | Cohen's d | damage McNemar p |
|---|---|---|---|---|---|---|
| **E1_H_H_high** | 229.0 / 0.00 | **217.1** / **0.60** | 0.000175 | **0.0082** (sig) | 1.04 (large) | 0.00049 (sig) |
| E1_H_C_high | 214.4 / 0.70 | 211.6 / 1.00 | 0.0128 | 0.664 (ns) | 0.615 | 0.031 |
| all others | identical | identical | — | — | — | — |

**Conclusion:** the corrected, leak-free, independent-seed comparison collapses
the earlier v2 "B4b much faster + much more damage" gap to a **single scenario
class** (`E1_H_H_high`): B4b preempts a busy service in 12/20 seeds, gaining ~12 s
(≈5 %) of emergency speed at the cost of 0.60 interrupted existing missions per
run. Elsewhere B4b reproduces B2.

## F. B4a (LLM-State) vs B4b (LLM-Candidate) — interface ablation (n = 60 paired)

| metric | B4a (no candidate table) | B4b (candidate table) | paired p |
|---|---|---|---|
| Air-intervention rate | **1.000** | 0.617 | **< 0.001** (McNemar 0.0) |
| Completion (s) | 177.5 | **163.9** | **4.8e-05** (d = 0.567) |
| Existing-service damage | 0.667 | **0.283** | — |
| Unnecessary-air rate | 0.333 | **0.117** | **0.00024** |
| Deadline-violation rate | 0.333 | 0.333 | 1.0 (ns) |

**Conclusion:** the structured candidate table is the enabler of the LLM's
selective, service-aware behaviour. Without it (B4a), the LLM degenerates to
"always dispatch air" — slower, 2.4× more damage, 2.8× more unnecessary air. The
table's ETA / legality / predicted-deadline-violation / service-loss facts are
what let B4b throttle air and preserve existing service.

## G. E1_H_H_high case study

See `E1_H_H_HIGH_CASE_STUDY.md`. B2 = ground in 20/20 (229 s, 0 damage); B4b =
REASSIGN in 12/20 (217.1 s, 0.60 damage), ground in 8/20. Holm p = 0.0082,
d = 1.04. This is the one genuine, statistically significant speed↔
service-preservation trade-off in the corrected data.

## H. Backend cache / empty-output reliability

See `LLM_BACKEND_RELIABILITY.md`. **240/240 unique `response_id`s, 0 repeated,
0 empty content, 0 cache-completion replays, 0 silent substitutions.** 2 transient
transport timeouts (0.83 %) recovered by the orchestrator's periodic re-decision;
their cost (1 deadline violation in a borderline case) is **included** in B4b's
reported numbers. The old v2 "~80 % sub-second cached same-prompt×10" artefact
does **not** exist here (every prompt is unique per seed).

## I. Final scientific conclusion

1. The **corrected** Experiment-1 primary is internally valid: leak-free shared
   candidate table, genuinely independent simulation seeds, paired design, and
   honest execution-based metrics.
2. **B2 (frozen optimizer) and B4b (LLM-candidate) converge** on completion time
   (147.6 vs 146.6 s) and deadline violations (16.7 % both), and both clearly
   outperform B0 (ground-only) and B1 (air-first). The large B4b edge in the
   superseded v2 data was largely an artefact of candidate-table information
   asymmetry and cached same-prompt repeats.
3. The **remaining, reproducible** contribution of the LLM candidate policy is a
   **controllable speed↔service-preservation operating point**: only in the
   preemption-boundary scenario (`E1_H_H_high`) does B4b trade 0.60 existing
   missions for ~12 s of emergency speed (d = 1.04, Holm p = 0.008).
4. The **candidate-table interface is load-bearing**: the B4a ablation shows that
   without the structured facts the LLM falls back to "always air" and becomes
   the *worst* manager on damage (0.667) and unnecessary air (33 %).
5. Recommendation: the paper's claim should be reframed from "LLM wins" to
   "an LLM candidate policy, given a manager-agnostic structured candidate table,
   matches a frozen optimizer and offers a tunable service-vs-speed trade-off,
   while a prompt-only LLM (no candidate table) degrades to damaging air-first
   behaviour."

## J. Safe to enter Experiment 2?

**Yes** — conditionally. All 20 acceptance tests PASS and the stop condition
(§32) is NOT triggered. The methodology (leak-free shared facts, independent
seeds, paired statistics, execution-based metrics) is now correct and is the
template Experiment 2 must reuse. The one caution: Experiment 2 must **not**
assume B4b categorically beats B2; it should build on the *specific* reproducible
finding above (the B4b speed↔service operating point and the candidate-table
ablation), not on the superseded v2 gap.
