# LLM Offline Sanity (Phase 3)

**25 representative Global States** (Phase-2 manager_inputs + audit snapshots + synthetic mutations), no live simulator.
Model: `corp-ai/openai/deepseek-v4-pro`, prompt `manager_v1`, temperature=0.

## Metrics

| metric | value |
|--------|-------|
| JSON validity rate (after retry) | 100% (25/25) |
| Schema validity rate | 100% |
| Feasible action rate | 100% (25/25) |
| Unknown-resource rate (first attempt) | 0% |
| Priority violation rate (first attempt) | 0% |
| Duplicate assignment rate (first attempt) | 0% |
| Retry rate | 0% (0/25) |
| No-action rate | 52% |
| avg latency | 24.8 s |
| tokens (prompt/completion) | 54790 / 39403 |

## Minimum gate for live simulation

- [PASS] JSON validity = 100% after retry
- [PASS] Schema validity = 100%
- [PASS] Unknown resource = 0 (final)
- [PASS] Duplicate assignment = 0 (final)
- [PASS] Feasible action rate >= 95%

**Gate: PASS — proceed to live simulation**

## Action-type distribution (LLM)

- NO_ACTION: 13
- GROUND_FALLBACK: 6
- DISPATCH: 5
- REASSIGN: 1

## Rule vs LLM action comparison (sanity only)

| category | rule action | llm action |
|----------|-------------|------------|
| critical_mission | DISPATCH | DISPATCH |
| c2_lost | REASSIGN | REASSIGN |
| critical_mission | DISPATCH | DISPATCH |
| c2_lost_logistics | REASSIGN | GROUND_FALLBACK |
| critical_mission | DISPATCH | DISPATCH |
| ground_fallback | GROUND_FALLBACK | GROUND_FALLBACK |
| normal | NOOP | NO_ACTION |
| pre_disruption | NOOP | NO_ACTION |
| ground_disruption | NOOP | NO_ACTION |
| post_dispatch | NOOP | NO_ACTION |
| pre_c2 | NOOP | NO_ACTION |
| needs_replan | NOOP | NO_ACTION |
| contingency_landed | NOOP | NO_ACTION |
| completed | NOOP | NO_ACTION |
| post_terminal | NOOP | NO_ACTION |
| normal | NOOP | NO_ACTION |
| needs_replan | NOOP | GROUND_FALLBACK |
| normal | NOOP | NO_ACTION |
| no_backup | NOOP | NO_ACTION |
| ground_fallback_completed | NOOP | NO_ACTION |
| insufficient_battery | DISPATCH | DISPATCH |
| insufficient_endurance | DISPATCH | DISPATCH |
| landing_site_unavailable | DISPATCH | GROUND_FALLBACK |
| busy_resources | GROUND_FALLBACK | GROUND_FALLBACK |
| all_unavailable | GROUND_FALLBACK | GROUND_FALLBACK |

Rule feasible rate: 25/25; Rule semantic-valid: 24/25.
