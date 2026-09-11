# Experiment 1 — Final results (paper release 2026-09-10)

Authoritative data: `outputs/paper_final/results.json`. Raw runs retained; tables regenerated offline.

| site | manager | n | completion (s) | deadline rate | service damage | recovered/affected |
|---|---|---|---|---|---|---|
| A | B0 | 240 | 187.667 | 0.333 | 0.000 | N/A |
| A | B1 | 240 | 160.775 | 0.250 | 0.500 | N/A |
| A | B2 | 240 | 147.617 | 0.167 | 0.058 | N/A |
| A | B4b | 240 | 146.633 | 0.167 | 0.133 | N/A |
| B | B0 | 240 | 262.667 | 0.500 | 0.000 | N/A |
| B | B1 | 240 | 47.700 | 0.000 | 0.500 | N/A |
| B | B2 | 240 | 47.700 | 0.000 | 0.500 | N/A |
| B | B4b | 240 | 49.096 | 0.000 | 0.487 | N/A |
| C | B0 | 240 | 323.667 | 0.833 | 0.000 | N/A |
| C | B1 | 240 | 168.275 | 0.100 | 0.500 | N/A |
| C | B2 | 240 | 168.275 | 0.100 | 0.500 | N/A |
| C | B4b | 240 | 168.650 | 0.100 | 0.500 | N/A |

## Finding

Shared candidate information enables selective coordination. On Site A, B4b and B2 have close mean completion times, while their service-preemption choices expose a speed–service trade-off. The paired no-table ablation identifies the role of the interface. Cross-site results evaluate the same architecture under adapted geography.

## Paired candidate-table ablation: B4b minus B4a

| site | metric | n | difference | 95% CI | Holm p |
|---|---|---|---|---|---|
| A | critical_mission_completion_time_s | 60 | -13.567 | [-19.752893400689068, -7.380439932644263] | 4.79e-05 |
| A | existing_missions_damaged_count | 60 | -0.383 | [-0.5099916201168767, -0.25667504654979] | 3.13e-07 |
| A | air_intervention | 60 | -0.383 | [-0.5099916201168767, -0.25667504654979] | 4.77e-07 |
| B | critical_mission_completion_time_s | 60 | 1.450 | [-1.8243287382888205, 4.72432873828882] | 0.964 |
| B | existing_missions_damaged_count | 60 | -0.017 | [-0.050016589634804445, 0.016683256301471116] | 0.964 |
| B | air_intervention | 60 | -0.017 | [-0.050016589634804445, 0.016683256301471116] | 1.000 |
| C | critical_mission_completion_time_s | 60 | 0.000 | [0.0, 0.0] | 1.000 |
| C | existing_missions_damaged_count | 60 | 0.000 | [0.0, 0.0] | 1.000 |
| C | air_intervention | 60 | 0.000 | [0.0, 0.0] | 1.000 |
