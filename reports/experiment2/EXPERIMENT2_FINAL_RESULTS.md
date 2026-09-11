# Experiment 2 — Final results (paper release 2026-09-10)

Authoritative data: `outputs/paper_final/results.json`. Raw runs retained; tables regenerated offline.

| site | manager | n | completion (s) | deadline rate | service damage | recovered/affected |
|---|---|---|---|---|---|---|
| A | B0 | 320 | 182.000 | 1.000 | 0.081 | N/A |
| A | B1 | 320 | 162.000 | 0.375 | 0.394 | 200/200 |
| A | B2 | 320 | 162.000 | 0.375 | 0.394 | 200/200 |
| A | B4b | 320 | 166.525 | 0.391 | 0.397 | 191/191 |
| B | B0 | 320 | 241.000 | 1.000 | 0.125 | N/A |
| B | B1 | 320 | 153.875 | 0.375 | 0.403 | 200/200 |
| B | B2 | 320 | 153.875 | 0.375 | 0.403 | 200/200 |
| B | B4b | 320 | 154.050 | 0.375 | 0.403 | 199/199 |
| C | B0 | 320 | 310.000 | 1.000 | 0.131 | N/A |
| C | B1 | 320 | 278.000 | 0.625 | 0.444 | 200/200 |
| C | B2 | 320 | 278.000 | 0.625 | 0.444 | 200/200 |
| C | B4b | 320 | 278.922 | 0.628 | 0.444 | 201/201 |

## Finding

The shared execution layer restores an executable path after isolated air-layer failures. Report end-to-end completion/deadline results for all runs; recovery is conditional on an affected critical chain. Observed backend failures remain in the end-to-end comparison.

## B4b minus B2: corrected paired family

| site | metric | paired n | difference | 95% CI | Holm p |
|---|---|---|---|---|---|
| A | critical_mission_completion_time_s | 320 | 4.525 | [1.9172149794826456, 7.132785020517355] | 0.009 |
| A | recovery_time_s | 191 | 3.927 | [0.7326238481732794, 7.120779293187977] | 0.162 |
| B | critical_mission_completion_time_s | 320 | 0.175 | [0.046096476346751736, 0.30390352365324824] | 0.094 |
| B | recovery_time_s | 199 | 0.281 | [0.07486202403544845, 0.48795204631631034] | 0.094 |
| C | critical_mission_completion_time_s | 320 | 0.922 | [-0.16181869183223818, 2.005568691832238] | 1.000 |
| C | recovery_time_s | 200 | 0.255 | [-0.12190965339042109, 0.6319096533904212] | 1.000 |

Recovery-time pairs require both managers to be affected. The 12-item per-site family is retained for continuity, with conditional denominators corrected. Candidate-count reduction remains descriptive because aircraft occupancy also changes the count.
