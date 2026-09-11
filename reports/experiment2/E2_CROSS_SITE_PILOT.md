# Experiment 2 — Cross-Site Pilot Report (Site B / Site C)

Per-site pilots: 6 scenarios x 3 seeds x 4 managers = 72 runs per site (144/144 cells collected). Site-adapted timelines (Site B t_failure=322 s, Site C t_failure=383 s) and the re-derived F2/F5/F6 geometry are in effect. **Verdict: PASS** (722/722 checks).

## Per-scenario behaviour (3 seeds each)

| site | scenario | ctx | manager | affected | recovery | comp range | viol | dmg |
|---|---|---|---|---|---|---|---|---|
| site_b_amsterdam | E2XB_F1_C1 | C1 | B0 | 0/3 | 0/3 | 541-541 | 3/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F1_C1 | C1 | B1 | 0/3 | 0/3 | 340-340 | 0/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F1_C1 | C1 | B2 | 0/3 | 0/3 | 340-340 | 0/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F1_C1 | C1 | B4b | 0/3 | 0/3 | 340-340 | 0/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F4_C1 | C1 | B0 | 0/3 | 0/3 | 541-541 | 3/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F4_C1 | C1 | B1 | 0/3 | 0/3 | 340-340 | 0/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F4_C1 | C1 | B2 | 0/3 | 0/3 | 340-340 | 0/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F4_C1 | C1 | B4b | 0/3 | 0/3 | 340-340 | 0/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F2_C2 | C2 | B0 | 0/3 | 0/3 | 541-541 | 3/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F2_C2 | C2 | B1 | 3/3 | 3/3 | 461-461 | 0/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F2_C2 | C2 | B2 | 3/3 | 3/3 | 461-461 | 0/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F2_C2 | C2 | B4b | 3/3 | 3/3 | 461-461 | 0/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F5_C2 | C2 | B0 | 0/3 | 0/3 | 541-541 | 3/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F5_C2 | C2 | B1 | 3/3 | 3/3 | 461-461 | 0/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F5_C2 | C2 | B2 | 3/3 | 3/3 | 461-461 | 0/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F5_C2 | C2 | B4b | 3/3 | 3/3 | 461-461 | 0/3 | [0, 0, 0] |
| site_b_amsterdam | E2XB_F3_C3 | C3 | B0 | 0/3 | 0/3 | 541-541 | 3/3 | [1, 1, 1] |
| site_b_amsterdam | E2XB_F3_C3 | C3 | B1 | 3/3 | 3/3 | 563-563 | 3/3 | [2, 2, 2] |
| site_b_amsterdam | E2XB_F3_C3 | C3 | B2 | 3/3 | 3/3 | 563-563 | 3/3 | [2, 2, 2] |
| site_b_amsterdam | E2XB_F3_C3 | C3 | B4b | 3/3 | 3/3 | 563-563 | 3/3 | [2, 2, 2] |
| site_b_amsterdam | E2XB_F6_C3 | C3 | B0 | 0/3 | 0/3 | 541-541 | 3/3 | [1, 1, 1] |
| site_b_amsterdam | E2XB_F6_C3 | C3 | B1 | 3/3 | 3/3 | 563-563 | 3/3 | [2, 2, 2] |
| site_b_amsterdam | E2XB_F6_C3 | C3 | B2 | 3/3 | 3/3 | 563-563 | 3/3 | [2, 2, 2] |
| site_b_amsterdam | E2XB_F6_C3 | C3 | B4b | 3/3 | 3/3 | 563-563 | 3/3 | [2, 2, 2] |
| site_c_edmonton | E2XC_F1_C1 | C1 | B0 | 0/3 | 0/3 | 610-610 | 3/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F1_C1 | C1 | B1 | 0/3 | 0/3 | 461-461 | 0/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F1_C1 | C1 | B2 | 0/3 | 0/3 | 461-461 | 0/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F1_C1 | C1 | B4b | 0/3 | 0/3 | 461-461 | 0/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F4_C1 | C1 | B0 | 0/3 | 0/3 | 610-610 | 3/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F4_C1 | C1 | B1 | 0/3 | 0/3 | 461-461 | 0/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F4_C1 | C1 | B2 | 0/3 | 0/3 | 461-461 | 0/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F4_C1 | C1 | B4b | 0/3 | 0/3 | 461-461 | 0/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F2_C2 | C2 | B0 | 0/3 | 0/3 | 610-610 | 3/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F2_C2 | C2 | B1 | 3/3 | 3/3 | 581-581 | 3/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F2_C2 | C2 | B2 | 3/3 | 3/3 | 581-581 | 3/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F2_C2 | C2 | B4b | 3/3 | 3/3 | 581-581 | 3/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F5_C2 | C2 | B0 | 0/3 | 0/3 | 610-610 | 3/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F5_C2 | C2 | B1 | 3/3 | 3/3 | 581-581 | 3/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F5_C2 | C2 | B2 | 3/3 | 3/3 | 581-581 | 3/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F5_C2 | C2 | B4b | 3/3 | 3/3 | 581-581 | 3/3 | [0, 0, 0] |
| site_c_edmonton | E2XC_F3_C3 | C3 | B0 | 0/3 | 0/3 | 610-610 | 3/3 | [1, 1, 1] |
| site_c_edmonton | E2XC_F3_C3 | C3 | B1 | 3/3 | 3/3 | 693-693 | 3/3 | [2, 2, 2] |
| site_c_edmonton | E2XC_F3_C3 | C3 | B2 | 3/3 | 3/3 | 693-693 | 3/3 | [2, 2, 2] |
| site_c_edmonton | E2XC_F3_C3 | C3 | B4b | 3/3 | 3/3 | 693-693 | 3/3 | [2, 2, 2] |
| site_c_edmonton | E2XC_F6_C3 | C3 | B0 | 0/3 | 0/3 | 610-610 | 3/3 | [1, 0, 1] |
| site_c_edmonton | E2XC_F6_C3 | C3 | B1 | 3/3 | 3/3 | 693-693 | 3/3 | [2, 1, 2] |
| site_c_edmonton | E2XC_F6_C3 | C3 | B2 | 3/3 | 3/3 | 693-693 | 3/3 | [2, 1, 2] |
| site_c_edmonton | E2XC_F6_C3 | C3 | B4b | 3/3 | 3/3 | 693-693 | 3/3 | [2, 1, 2] |

## Gate decisions

| gate | verdict | evidence |
|---|---|---|
| exogenous failure hash identical per (scenario, seed) | PASS | failure config frozen per site matrix; hash guard active |
| failure event fires at the site-adapted time | PASS | t=322 (Site B) / t=383 (Site C) |
| C2/C3 candidate-set effect measured | PASS | post < pre for affected managers in every C2/C3 cell |
| managers act through the checker (no silent substitution) | PASS | normalized == executed everywhere |
| missions terminate within 900 s | PASS | 0 unterminated critical missions |
| clock sync unaffected | PASS | sync_ok across all pilot cells |
| LLM backend stable (frozen recovery policy) | PASS | 72 calls, 0 empty, 0 transport, 0 crashed |
