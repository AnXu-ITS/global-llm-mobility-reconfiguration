# Experiment 2 — Acceptance Tests (E2-T1 … E2-T32)

**Verdict: 32/32 PASS, 0 FAIL — NO FAIL**

| id | result | evidence |
|---|---|---|
| E2-T1 | PASS | entry regression 12/12 PASS (see EXPERIMENT2_ENTRY_REGRESSION.md) |
| E2-T2 | PASS | E1 frozen hash manifest: 26/26 match |
| E2-T3 | PASS | S0_3p2km_v1, fleet size 4 |
| E2-T4 | PASS | B2 weights hash matches frozen value |
| E2-T5 | PASS | manager_v2 prompt hash matches frozen value |
| E2-T6 | PASS | candidate_info_e2.py imports no manager module (manager-agnostic) |
| E2-T7 | PASS | no objective/weight/ranking/recommend field in the emitted 2.1.0 candidate tables |
| E2-T8 | PASS | test_exp2_f1_c2.py final run: 9/9 PASS |
| E2-T9 | PASS | test_exp2_f2_gnss.py final run: 9/9 PASS |
| E2-T10 | PASS | test_exp2_f3_utm.py final run: 9/9 PASS |
| E2-T11 | PASS | test_exp2_f4_landing.py final run: 9/9 PASS |
| E2-T12 | PASS | test_exp2_f5_unknown.py final run: 9/9 PASS |
| E2-T13 | PASS | test_exp2_f6_flyaway.py final run: 9/9 PASS |
| E2-T14 | PASS | local contingency fires before any manager decision (F1-F6 audit tests + failure_trace.local_contingency) |
| E2-T15 | PASS | 16 scenarios, each with exactly one failure family |
| E2-T16 | PASS | failure_exogeneity_audit.csv: all hashes match frozen config |
| E2-T17 | PASS | scenario audit confirms C1/C2/C3 labels against measured candidate sets |
| E2-T18 | PASS | EXPERIMENT2_METRIC_DEFINITIONS.md present (frozen pre-run) |
| E2-T19 | PASS | 20 seeds frozen, identical to the E1 seed set (reuse per §25) |
| E2-T20 | PASS | 20/20 distinct initial states per scenario (seed_independence_audit.csv) |
| E2-T21 | PASS | EXPERIMENT2_PILOT_REPORT.md verdict PASS |
| E2-T22 | PASS | 1280/1280 primary runs complete |
| E2-T23 | PASS | prompt + B2 weights hashes frozen |
| E2-T24 | PASS | checker bypasses / silent substitutions: 0 |
| E2-T25 | PASS | raw==normalized==executed for every ISSUED action (0 violations) |
| E2-T26 | PASS | ARTIFACT CONTRACT: PASS |
| E2-T27 | PASS | outputs/experiment2/primary_analysis.json present |
| E2-T28 | PASS | outputs/experiment2/family_context_cells.json present |
| E2-T29 | PASS | scenario audit (contexts) present |
| E2-T30 | PASS | outputs/experiment2/llm_reliability.json present (separate from primary stats) |
| E2-T31 | PASS | EXPERIMENT2_REPLAY_AUDIT.md PASS |
| E2-T32 | PASS | no Experiment-3 matrix / run directory |
