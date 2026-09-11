# Experiment 3 v2 — Final results (paper release 2026-09-10)

Three sites, 2,880 primary runs. This replaces v1 final-result claims. Primary outcome: system-weighted loss (SWL).

| site | level | B0 | B1 | B2 | B4b |
|---|---|---|---|---|---|
| A | L1 | 240.000 | 0.000 | 0.000 | 6.000 |
| A | L2 | 240.000 | 240.000 | 240.000 | 240.000 |
| A | L3 | 240.000 | 0.000 | 0.000 | 1.688 |
| A | L4 | 240.000 | 120.000 | 120.000 | 123.375 |
| B | L1 | 240.000 | 0.000 | 0.000 | 0.000 |
| B | L2 | 240.000 | 120.000 | 120.000 | 120.000 |
| B | L3 | 375.000 | 135.000 | 135.000 | 135.000 |
| B | L4 | 375.000 | 255.000 | 255.000 | 255.000 |
| C | L1 | 240.000 | 240.000 | 240.000 | 240.000 |
| C | L2 | 240.000 | 240.000 | 240.000 | 240.000 |
| C | L3 | 375.000 | 135.000 | 135.000 | 135.000 |
| C | L4 | 375.000 | 375.000 | 375.000 | 375.000 |

## Finding

Coordination reduces loss where remaining transport options can preserve task deadlines. It offers no SWL gain in some exhausted/slack-limited cells. On Site A L2 all managers score 240; the old +100 cascade-backfire effect disappears after the lifecycle/scheduling correction. B4b does not show a significant SWL advantage over B1/B2 in the corrected compound comparisons.

B1 and B2 share the same SWL outcomes in these scenarios. B4b has small Site-A deviations; identical decisions are not claimed. CRITICAL+HIGH loss measures priority-weighted outcomes. Unimplemented action-level priority/competition fields are not used as findings.

## Corrected compound comparisons

| site | baseline | level | metric | n | difference | 95% CI | Holm p |
|---|---|---|---|---|---|---|---|
| A | B1 | L2 | system_weighted_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| A | B1 | L2 | _critical_high_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| A | B1 | L3 | system_weighted_loss | 80 | 1.688 | [-1.6713847297633415, 5.046384729763341] | 1.000 |
| A | B1 | L3 | _critical_high_loss | 80 | 1.688 | [-1.6713847297633415, 5.046384729763341] | 1.000 |
| A | B1 | L4 | system_weighted_loss | 40 | 3.375 | [-3.4515818551240676, 10.201581855124068] | 1.000 |
| A | B1 | L4 | _critical_high_loss | 40 | 3.375 | [-3.4515818551240676, 10.201581855124068] | 1.000 |
| A | B2 | L2 | system_weighted_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| A | B2 | L2 | _critical_high_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| A | B2 | L3 | system_weighted_loss | 80 | 1.688 | [-1.6713847297633415, 5.046384729763341] | 1.000 |
| A | B2 | L3 | _critical_high_loss | 80 | 1.688 | [-1.6713847297633415, 5.046384729763341] | 1.000 |
| A | B2 | L4 | system_weighted_loss | 40 | 3.375 | [-3.4515818551240676, 10.201581855124068] | 1.000 |
| A | B2 | L4 | _critical_high_loss | 40 | 3.375 | [-3.4515818551240676, 10.201581855124068] | 1.000 |
| B | B1 | L2 | system_weighted_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| B | B1 | L2 | _critical_high_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| B | B1 | L3 | system_weighted_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| B | B1 | L3 | _critical_high_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| B | B1 | L4 | system_weighted_loss | 40 | 0.000 | [0.0, 0.0] | 1.000 |
| B | B1 | L4 | _critical_high_loss | 40 | 0.000 | [0.0, 0.0] | 1.000 |
| B | B2 | L2 | system_weighted_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| B | B2 | L2 | _critical_high_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| B | B2 | L3 | system_weighted_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| B | B2 | L3 | _critical_high_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| B | B2 | L4 | system_weighted_loss | 40 | 0.000 | [0.0, 0.0] | 1.000 |
| B | B2 | L4 | _critical_high_loss | 40 | 0.000 | [0.0, 0.0] | 1.000 |
| C | B1 | L2 | system_weighted_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| C | B1 | L2 | _critical_high_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| C | B1 | L3 | system_weighted_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| C | B1 | L3 | _critical_high_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| C | B1 | L4 | system_weighted_loss | 40 | 0.000 | [0.0, 0.0] | 1.000 |
| C | B1 | L4 | _critical_high_loss | 40 | 0.000 | [0.0, 0.0] | 1.000 |
| C | B2 | L2 | system_weighted_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| C | B2 | L2 | _critical_high_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| C | B2 | L3 | system_weighted_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| C | B2 | L3 | _critical_high_loss | 80 | 0.000 | [0.0, 0.0] | 1.000 |
| C | B2 | L4 | system_weighted_loss | 40 | 0.000 | [0.0, 0.0] | 1.000 |
| C | B2 | L4 | _critical_high_loss | 40 | 0.000 | [0.0, 0.0] | 1.000 |

Sources: `outputs/paper_final/results.json`; per-run data `runs/experiment3` and `runs/experiment3_cross_site`, matrix version 2.
