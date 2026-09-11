# Experiment 2 — Entry Regression

Protocol §1: rerun ONLY the existing (frozen) Phase-1 / Phase-2 / Phase-3 /
Experiment-1 platform regression tests before entering Experiment 2. No new
tests were designed for this gate.

**Date:** 2026-09-05
**Runner:** `tools/run_entry_regression.py` (thin subprocess wrapper over the
existing test files — the tests themselves were not modified)
**Machine-readable:** `outputs/experiment2/entry_regression.json`

## Verdict: 12 / 12 PASS — no new FAIL. Entry gate CLEARED.

| # | item | result | evidence |
|---|---|---|---|
| 0 | Experiment-1 frozen artifact hash check (`outputs/file_hashes_final.json`) | **PASS** | 26/26 SHA-256 matches, 0 mismatches — no Experiment-1 frozen file was modified |
| 1 | `tests/test_geographic_alignment.py` | **PASS** | median 0.0000 m (< 5 m), max 0.0000 m (< 15 m); D1 snap 58.012 m WARNING carried over as frozen |
| 2 | `tests/test_bluesky_state_provenance.py` | **PASS** | positions read from `bs.traf`; L-UAV-01 1358.5 m / EVTOL-01 3636.8 m / parked M-UAV-02 0.0 m |
| 3 | `tests/test_clock_sync_post_resize.py` | **PASS** | max SUMO/BlueSky clock error = 0.000000 steps |
| 4 | `tests/test_acceptance.py` (T2/T3/T4/T8/T9) | **PASS** | T2 sync 600/600; T3 lifecycle COMPLETED; T4 REASSIGN valid; T8 3/3 infeasible rejected; T9 replay byte-identical |
| 5 | `tests/test_rule_based_manager.py` | **PASS** | 9/9 (rule 1–6 + ground fallback + priority conflict) |
| 6 | `tests/test_c2_local_contingency.py` | **PASS** | 4/4 — C2 LOST → CONTINGENCY / commandable=false / NEEDS_REPLAN; local contingency RETURN→V3 independent of manager |
| 7 | `tests/test_phase2_acceptance.py` | **PASS** | 12/12 — Global State schema validation, Ground→Air chain, C2 reconfiguration, deterministic replay |
| 8 | `tests/test_reverse_air_post_resize.py` | **PASS** | Air→Hub event F-AIR-001 → BUSY→UNAVAILABLE, EN_ROUTE→NEEDS_REPLAN |
| 9 | `tests/test_feasibility_post_resize.py` | **PASS** | 3/3 infeasible actions rejected (busy non-reassignable / unavailable site / insufficient battery) |
| 10 | `tests/test_deterministic_replay_post_resize.py` | **PASS** | events/actions/missions/clock_sync byte-identical |
| 11 | `tests/test_phase3_acceptance.py` | **PASS** | 14/14 — LLM pipeline, semantic validator, normalize-then-validate chain, C2→LLM reconfiguration |

## Gate items from protocol §1 — explicit confirmation

- geographic alignment PASS (median 0.0 m; D1 snap 58.01 m WARNING carried over) ✅
- BlueSky state provenance PASS ✅
- master clock sync PASS (0-step error) ✅
- Ground→Air chain PASS ✅
- Air→Hub event PASS ✅
- feasibility checker PASS ✅
- deterministic replay PASS ✅
- Rule Manager PASS ✅
- C2 local contingency PASS ✅
- Global State schema PASS ✅
- Candidate Generator fairness PASS (hash `4ebef494…a7adc2` unchanged = frozen 2.0.0 table) ✅
- normalize-then-validate PASS ✅

## Total wall time

129.3 s (all tests). No test was re-designed; no frozen component was rebuilt.
