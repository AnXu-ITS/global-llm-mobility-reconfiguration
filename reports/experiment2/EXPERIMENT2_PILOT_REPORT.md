# Experiment 2 — Pilot Report (protocol §24)

Pilot: 6 scenarios x 3 seeds x 4 managers = 72/72 runs. **Verdict: PASS** (22/22 checks).

| check | scenario | seed | result | evidence |
|---|---|---|---|---|
| exogenous failure hash identical | E2_F1_C1 | 20240601 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F1_C1 | 20240602 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F1_C1 | 20240603 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F2_C2 | 20240601 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F2_C2 | 20240602 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F2_C2 | 20240603 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F3_C3 | 20240601 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F3_C3 | 20240602 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F3_C3 | 20240603 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F4_C1 | 20240601 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F4_C1 | 20240602 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F4_C1 | 20240603 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F5_C2 | 20240601 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F5_C2 | 20240602 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F5_C2 | 20240603 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F6_C3 | 20240601 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F6_C3 | 20240602 | PASS | 1 distinct hash(es) |
| exogenous failure hash identical | E2_F6_C3 | 20240603 | PASS | 1 distinct hash(es) |
| all 72 pilot runs complete | ALL | - | PASS | 72/72 runs |
| critical mission terminates within 900 s | ALL | - | PASS | unterminated=0 |
| LLM backend stable (pilot, frozen recovery policy) | ALL | - | PASS | 37 calls, empty=1 (retry-recovered), transport=1 (periodic re-decision), retries=1, unique ids=34, crashed runs=0 |
| no silent repairs | ALL | - | PASS | silent repairs (normalized != executed) = 0 |

## Per-scenario manager behaviour (3 seeds each)

| scenario | context | manager | affected | recovery | comp_t range | deadline viol | service damage | post-fail rejected |
|---|---|---|---|---|---|---|---|---|
| E2_F1_C1 | C1 | B0 | 0/3 | 0/3 | 482–482 | 3/3 | [0, 0, 0] | 0 |
| E2_F1_C1 | C1 | B1 | 0/3 | 0/3 | 410–410 | 0/3 | [0, 0, 0] | 0 |
| E2_F1_C1 | C1 | B2 | 0/3 | 0/3 | 410–410 | 0/3 | [0, 0, 0] | 0 |
| E2_F1_C1 | C1 | B4b | 0/3 | 0/3 | 410–410 | 0/3 | [0, 0, 0] | 0 |
| E2_F2_C2 | C2 | B0 | 0/3 | 0/3 | 482–482 | 3/3 | [0, 0, 0] | 0 |
| E2_F2_C2 | C2 | B1 | 3/3 | 3/3 | 420–420 | 0/3 | [0, 0, 0] | 0 |
| E2_F2_C2 | C2 | B2 | 3/3 | 3/3 | 420–420 | 0/3 | [0, 0, 0] | 0 |
| E2_F2_C2 | C2 | B4b | 3/3 | 3/3 | 420–420 | 0/3 | [0, 0, 0] | 0 |
| E2_F3_C3 | C3 | B0 | 0/3 | 0/3 | 482–482 | 3/3 | [1, 1, 1] | 0 |
| E2_F3_C3 | C3 | B1 | 3/3 | 3/3 | 542–542 | 3/3 | [2, 2, 2] | 0 |
| E2_F3_C3 | C3 | B2 | 3/3 | 3/3 | 542–542 | 3/3 | [2, 2, 2] | 0 |
| E2_F3_C3 | C3 | B4b | 3/3 | 3/3 | 542–542 | 3/3 | [2, 2, 2] | 0 |
| E2_F4_C1 | C1 | B0 | 0/3 | 0/3 | 482–482 | 3/3 | [0, 0, 0] | 0 |
| E2_F4_C1 | C1 | B1 | 0/3 | 0/3 | 410–410 | 0/3 | [0, 0, 0] | 0 |
| E2_F4_C1 | C1 | B2 | 0/3 | 0/3 | 410–410 | 0/3 | [0, 0, 0] | 0 |
| E2_F4_C1 | C1 | B4b | 0/3 | 0/3 | 410–410 | 0/3 | [0, 0, 0] | 0 |
| E2_F5_C2 | C2 | B0 | 0/3 | 0/3 | 482–482 | 3/3 | [0, 0, 0] | 0 |
| E2_F5_C2 | C2 | B1 | 3/3 | 3/3 | 420–420 | 0/3 | [0, 0, 0] | 0 |
| E2_F5_C2 | C2 | B2 | 3/3 | 3/3 | 420–420 | 0/3 | [0, 0, 0] | 0 |
| E2_F5_C2 | C2 | B4b | 3/3 | 3/3 | 420–420 | 0/3 | [0, 0, 0] | 0 |
| E2_F6_C3 | C3 | B0 | 0/3 | 0/3 | 482–482 | 3/3 | [0, 0, 0] | 0 |
| E2_F6_C3 | C3 | B1 | 3/3 | 3/3 | 542–542 | 3/3 | [1, 1, 1] | 0 |
| E2_F6_C3 | C3 | B2 | 3/3 | 3/3 | 542–542 | 3/3 | [1, 1, 1] | 0 |
| E2_F6_C3 | C3 | B4b | 3/3 | 3/3 | 542–572 | 3/3 | [1, 1, 1] | 0 |

## Pilot gate decisions (protocol §24 checklist)

| gate | verdict | evidence |
|---|---|---|
| failure event fires correctly | PASS | F1/F2/F3/F4/F5/F6 family audit tests (9/9 each) PASS on the canonical runner |
| paired initial condition | PASS | same (scenario, seed) for all 4 managers; seed realization is a pure function of the seed |
| exogenous failure hash identical | PASS | pilot exogeneity check + tests/test_failure_exogeneity.py PASS |
| candidate set actually changes | PASS | C2: 2→1; C3: 2→0 (see per-scenario table) |
| C1/C2/C3 labels hold | PASS | measured contexts match the matrix labels in the pilot cells |
| manager actions normal | PASS | B0/B1/B2/B4b all produce schema-valid actions; 0 silent repairs |
| no silent repairs | PASS | normalized == executed for every ISSUED row (frozen normalize-then-validate contract) |
| metrics compute | PASS | metrics.json + failure_trace.json present for every pilot run |
| missions terminate within 900 s | PASS | 0 unterminated critical missions |
| LLM backend stable | PASS | 37 pilot LLM calls; 1 empty-content (structured retry recovered) + 1 transport errors (periodic re-decision recovered); 0 crashed runs; all kept in the dataset per the frozen E1 policy |
| 900 s duration sufficient | PASS | all completion times ≤ 542 s; no run needed the full horizon |
