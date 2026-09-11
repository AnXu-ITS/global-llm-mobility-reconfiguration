# Document Sync — Full-Text Consistency Audit

Scope: `ground_air_llm_experiment_plan.md` and
`EXPERIMENT_IMPLEMENTATION_SPEC.md`, synchronized against the frozen Experiment-1
finalization artifacts on this date.

Classification: **A = still valid** · **B = historical reference** ·
**C = outdated and updated**.

## Keyword sweep

| keyword | plan | spec | classification | note |
|---|---|---|---|---|
| `5 km` / `5×5` / `5 × 5` | B | B | B | only in "historical/default design reference" context; NOT current truth |
| `12 aircraft` / `12-aircraft` | B | B | B | only in "historical initial design" context; NOT current truth |
| `B3` (manager) | C | — | C | old "B3 = generic LLM" explicitly marked not-current |
| `B3` (disruption link) | A | A | A | frozen disruption-link id (low impact +7.16 %); distinct from manager naming |
| `B4` (manager "LLM + checker") | C | — | C | old "B4 = LLM + checker" explicitly marked not-current |
| `B4a` / `B4b` | A | A | A | LLM-State / LLM-Candidate, correct |
| `LLM + Feasibility Checker` | — | — | C | removed (0 matches) |
| `nearest available` (B1) | — | — | C | removed (0 matches); B1 = min-completion-time rule |
| `manager_v1` | — | — | C | removed (0 matches); frozen prompt = `manager_v2` |
| `first version` / `第一版` (B2) | — | — | C | removed (0 matches); B2 objective = FROZEN |
| `response caching` | A | — | A | used only in the statistical-independence rule (must NOT count as replicates) |
| `N=20` | A | — | A | valid independent-seed count recommendation (20–30 seeds) |
| `canonical fleet` | A | A | A | now = 4-aircraft frozen fleet |
| `Experiment 1` / `Exp 1` | A | A | A | marked COMPLETED / FROZEN |
| `MVP` | B | B | B | historical record; already completed |
| `S0` | A | A | A | `S0_3p2km_v1` frozen |

## Conclusion

**No remaining "old value still described as current frozen truth".** Every
historical value (5 km, 12-aircraft, B3/B4 manager, "第一版" B2, `manager_v1`) is
either removed or explicitly labelled as historical reference, while the current
frozen truth (3.2 × 3.2 km, 4-aircraft fleet, B4a/B4b, Action Contract v2 +
`manager_action_v1.schema.json`, frozen B2 weights, `manager_v2`) is stated in the
"Current Frozen State" section of both documents.

## One documented naming collision (not a defect to fix)

`B1`/`B2` are simultaneously **manager names** (B1 = Rule-Based, B2 = Frozen
Optimization) and **frozen disruption-link ids** (`scenario_config.yaml`
`disruption_links.B1/B2`, plus `B3` low-impact link). This collision pre-exists in
the codebase and is context-dependent (manager vs ground-disruption link). It is
left as-is per the "do not modify configs" constraint; both documents disambiguate
by context.
