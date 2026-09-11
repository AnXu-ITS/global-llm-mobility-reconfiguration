# LLM Counterfactual Sanity (Phase 3)

9 paired states; only ONE variable changes between A and B. The LLM is
required to produce a *directionally correct* decision change, not to match
the Rule Manager.

| pair | variable | A | B | verdict |
|------|----------|---|---|---------|
| P1 | M-UAV-02 C2 status | DISPATCH M-UAV-02 | DISPATCH M-UAV-01 | PASS |
| P2 | V1 landing site | DISPATCH M-UAV-02 | GROUND_FALLBACK | PASS |
| P3 | mission priority | DISPATCH M-UAV-02 | DISPATCH M-UAV-02 | OBSERVED |
| P4 | M-UAV-02 battery | DISPATCH M-UAV-02 | DISPATCH M-UAV-01 | PASS |
| P5 | ground fallback ETA | DISPATCH M-UAV-02 | DISPATCH M-UAV-02 | OBSERVED |
| P6 | backup availability | REASSIGN M-UAV-01 | GROUND_FALLBACK | PASS |
| P7 | M-UAV-02 endurance | DISPATCH M-UAV-02 | DISPATCH M-UAV-01 | PASS |
| P8 | M-UAV-02 reassignability | DISPATCH M-UAV-01 | DISPATCH M-UAV-01 | PASS |
| P9 | M-UAV-02 landing compatibility | DISPATCH M-UAV-02 | DISPATCH M-UAV-01 | PASS |

**Summary:** 7 PASS / 2 OBSERVED / 0 FAIL (total 9).

- **P1** (NORMAL vs LOST): A=DISPATCH M-UAV-02 -> B=DISPATCH M-UAV-01 [PASS]
- **P2** (AVAILABLE vs UNAVAILABLE): A=DISPATCH M-UAV-02 -> B=GROUND_FALLBACK  [PASS]
- **P3** (NORMAL vs CRITICAL): A=DISPATCH M-UAV-02 -> B=DISPATCH M-UAV-02 [OBSERVED]
- **P4** (sufficient vs insufficient): A=DISPATCH M-UAV-02 -> B=DISPATCH M-UAV-01 [PASS]
- **P5** (120 s vs 400 s): A=DISPATCH M-UAV-02 -> B=DISPATCH M-UAV-02 [OBSERVED]
- **P6** (available vs committed): A=REASSIGN M-UAV-01 -> B=GROUND_FALLBACK  [PASS]
- **P7** (sufficient vs insufficient): A=DISPATCH M-UAV-02 -> B=DISPATCH M-UAV-01 [PASS]
- **P8** (non-reassignable vs reassignable(lower prio)): A=DISPATCH M-UAV-01 -> B=DISPATCH M-UAV-01 [PASS]
- **P9** (V1-compatible vs V1-incompatible): A=DISPATCH M-UAV-02 -> B=DISPATCH M-UAV-01 [PASS]
