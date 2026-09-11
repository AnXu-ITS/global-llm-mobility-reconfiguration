# LLM Decision Stability (Phase 3)

Same Global State (C2_B t=300) queried 10 times, temperature=0.

| metric | value |
|--------|-------|
| action consistency | 100% (DISPATCH) |
| selected-resource consistency | 100% (M-UAV-02) |
| fallback consistency | False |
| retry rate | 0% |
| all VALID_ACTION | True |

| run | action | aircraft | status | retry | latency_s |
|-----|--------|----------|--------|-------|-----------|
| 1 | DISPATCH | M-UAV-02 | VALID_ACTION | 0 | 0.069 |
| 2 | DISPATCH | M-UAV-02 | VALID_ACTION | 0 | 0.029 |
| 3 | DISPATCH | M-UAV-02 | VALID_ACTION | 0 | 0.031 |
| 4 | DISPATCH | M-UAV-02 | VALID_ACTION | 0 | 0.043 |
| 5 | DISPATCH | M-UAV-02 | VALID_ACTION | 0 | 0.032 |
| 6 | DISPATCH | M-UAV-02 | VALID_ACTION | 0 | 0.035 |
| 7 | DISPATCH | M-UAV-02 | VALID_ACTION | 0 | 0.047 |
| 8 | DISPATCH | M-UAV-02 | VALID_ACTION | 0 | 0.04 |
| 9 | DISPATCH | M-UAV-02 | VALID_ACTION | 0 | 0.041 |
| 10 | DISPATCH | M-UAV-02 | VALID_ACTION | 0 | 0.032 |
