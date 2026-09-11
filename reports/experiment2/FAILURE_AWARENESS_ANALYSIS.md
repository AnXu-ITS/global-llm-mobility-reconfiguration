# Experiment 2 — Failure Awareness & Safety-Layer Value (protocol §38/§39)

Policy reliability (manager behaviour) is reported separately from system safety (checker interceptions). A checker rejection is recorded, never repaired; a mission that completes AFTER a rejected proposal shows the SAFETY LAYER working — not the manager.

## Per-manager post-failure proposal behaviour (primary runs)

| manager | runs | post-fail proposals | rejected | rejected failure-related | failed-resource reselection | first decision hits failed resource | runs w/ ≥1 interception |
|---|---|---|---|---|---|---|---|
| B0 | 320 | 167 | 0 | 0 | 0 | 0 | 0 |
| B1 | 320 | 267 | 0 | 0 | 0 | 0 | 0 |
| B2 | 320 | 267 | 0 | 0 | 0 | 0 | 0 |
| B4b | 320 | 322 | 1 | 1 | 0 | 0 | 1 |

## No-air condition handling (necessary ground fallback)

| manager | no-air runs | correct ground fallback |
|---|---|---|
| B0 | 0 | 0 |
| B1 | 120 | 120 |
| B2 | 120 | 120 |
| B4b | 115 | 115 |

## By failure family

| family | manager | first decision hits failed resource | no-air correct/total |
|---|---|---|---|
| F1 | B0 | 0 | 0/0 |
| F1 | B1 | 0 | 20/20 |
| F1 | B2 | 0 | 20/20 |
| F1 | B4b | 0 | 20/20 |
| F2 | B0 | 0 | 0/0 |
| F2 | B1 | 0 | 20/20 |
| F2 | B2 | 0 | 20/20 |
| F2 | B4b | 0 | 20/20 |
| F3 | B0 | 0 | 0/0 |
| F3 | B1 | 0 | 20/20 |
| F3 | B2 | 0 | 20/20 |
| F3 | B4b | 0 | 20/20 |
| F4 | B0 | 0 | 0/0 |
| F4 | B1 | 0 | 20/20 |
| F4 | B2 | 0 | 20/20 |
| F4 | B4b | 0 | 20/20 |
| F5 | B0 | 0 | 0/0 |
| F5 | B1 | 0 | 20/20 |
| F5 | B2 | 0 | 20/20 |
| F5 | B4b | 0 | 20/20 |
| F6 | B0 | 0 | 0/0 |
| F6 | B1 | 0 | 20/20 |
| F6 | B2 | 0 | 20/20 |
| F6 | B4b | 0 | 15/15 |

## Interpretation rules

- **System safety** = 0 infeasible EXECUTED actions (every run is verified via action_pipeline.jsonl: raw == normalized == executed).
- **Manager failure-awareness** = proposal-level behaviour above: invalid proposals, reselection of the just-failed resource, and no-air fallback correctness are POLICY properties, credited to the manager — never to the checker.
