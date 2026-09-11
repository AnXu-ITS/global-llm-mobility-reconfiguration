# Experiment 3 — Metric Definitions (frozen pre-run, protocol §20)

All metrics are computed per (scenario, seed, manager) run from the run
artifacts (`metrics.json`, `events.csv`, `actions.csv`, `action_pipeline.jsonl`,
`violations.csv`, `failure_trace.json`, `manager_outputs.jsonl`), and are frozen
BEFORE the formal primary runs. Field names below refer to `metrics.json` as
written by `orchestrator/experiment3_runner.py::_metrics`.

**Inheritance rule:** every Experiment-2 metric (§A–§L, including the two
documented post-run corrections) is computed with the SAME frozen formula and
inherited verbatim; Experiment 3 adds the compound metrics below and does NOT
modify any inherited formula.

Notation: `release_t = 300 s`, primary `deadline_s = 480 s` (release + 180 s
frozen CRITICAL slack), `comp_t` = terminal completion time of the relevant
mission. The second emergency `M-CRITICAL-002` uses `release_t2 = 390 s` and
`deadline_s2 = 630 s` (release + 240 s frozen HIGH slack, defined in
`E3-EXT-EM-1`). Priority weight `w(p)` = CRITICAL 4, HIGH 3, NORMAL 2, LOW 1
(the frozen `PRIORITY_ORDER`).

---

## A. System-Weighted Loss (SWL) — PRIMARY Experiment-3 outcome

For every mission `m` in the final registry (all missions, including the primary
critical mission, `M-CRITICAL-002`, and all background services):

```text
L(m) = 0                                        if status(m) == COMPLETED
                                               and no deadline violation
     = delay_cost(m)                             if status(m) == COMPLETED
                                               and deadline violated
     = cancellation_cost(m)                      otherwise
                                               (CANCELLED / FAILED /
                                                INTERRUPTED / NEEDS_REPLAN /
                                                WAITING at shutdown)

SWL = Σ_m  w(priority(m)) · L(m)
```

- `system_weighted_loss` = `SWL`.
- `system_weighted_loss_by_priority` = the SWL contribution split by priority
  class (CRITICAL / HIGH / NORMAL / LOW), reported separately, never conflated.
- `system_weighted_loss_by_mission` = per-mission `w · L` (provenance).
- Missions whose `delay_cost` / `cancellation_cost` are not set in the matrix use
  the frozen defaults (delay 10.0 / cancel 100.0); the primary critical mission
  uses 60.0 / 600.0 (frozen E2 values).

SWL is the metric that makes the E3 trade-off explicit: it rewards completing
high-priority missions on time and penalizes damaging or losing services across
the WHOLE system, not just the single critical mission.

## B. Resource Competition Correctness (RCC) — L3/L4

`competition_instants` = decision instants `t` at which, in the Global State at
`t`, there are ≥ 2 actionable missions and the number of legal idle compatible
medical assets is strictly less than the number of actionable medical missions
(measured from the frozen candidate table / registry). For each such instant,
the frozen priority ordering defines the "correct" top-priority mission.

```text
resource_competition_correct =
  1  if, at EVERY competition instant, the manager's ISSUED action at t
     assigns a scarce asset to the highest-priority actionable mission
     (or correctly withholds it), and never assigns it to a strictly
     lower-priority mission while a higher-priority one remains
     unassigned-and-compatible;
  0  otherwise.
```

Reported per run (binary) and aggregated as a rate. "No competition instant" is
reported separately (competition-N/A), never merged into the rate.

## C. Second-Wave Readiness (redundancy reservation)

`spare_medical_assets_at_t420` = number of aircraft with `status == AVAILABLE`,
`commandable == true`, `c2_status == NORMAL`, and `V1 ∈ landing_site_compatibility`
at the second-failure instant `t = 420` (measured mechanically from the registry,
not from intent). For L2–L4 runs with a second failure; `None` otherwise.

This is the observable of "did the manager burn its last spare on the first wave,
or hold redundancy for the second wave". Lower is not automatically worse — the
trade-off against the primary critical mission's completion is exactly what SWL
is designed to capture; both are reported, never collapsed.

## D. Cascade Resilience (per-event recovery)

For EACH failure event `e` in the run (failure-A at t = 360, failure-B at
t = 420, failure-C at t = 480 for L4), the same §B/§D recovery definitions as
Experiment 2 are computed relative to event `e`:

- `cascade_recovery_success[e]` — the affected mission regained a legal active
  path (MISSION_STARTED / GROUND_FALLBACK_STARTED) at t ≥ t_e.
- `cascade_recovery_time_s[e]` = `t(regain) − t_e`.
- `cascade_recovery_mode[e]` ∈ {AIR, GROUND}.
- `cascade_failure_to_replan_latency_s[e]` = `t(first ISSUED action at t ≥ t_e) − t_e`.

The E2 `recovery_success` / `recovery_time_s` / `failure_to_replan_latency_s`
(for the FIRST event) are still reported unchanged as the inherited fields; the
per-event `cascade_*` fields generalize them to every event.

## E. Decision Oscillation

`decision_oscillation_count` = number of times, across the run, an ISSUED action
changes the mode or assigned resource of a mission in the OPPOSITE direction of
the immediately preceding ISSUED action for that same mission
(e.g. mission X: AIR→GROUND→AIR, or AIR aircraft A→aircraft B→ground→air).
Consecutive identical re-issues are not oscillations. A higher count indicates a
manager thrashing under compound context; it is reported as a behaviour metric,
not as a correctness verdict.

## F. Priority Consistency

`priority_consistency_violations` = number of decision instants at which an
ISSUED action assigns a resource to a mission `m_low` while a strictly
higher-priority actionable mission `m_high` exists that is compatible with that
same resource and was left unassigned at that instant. Violations are counted per
instant; the frozen priority ordering is authoritative. Reported per run and as
a rate over runs.

## G. Inherited Experiment-2 metrics (frozen, unchanged)

All of `EXPERIMENT2_METRIC_DEFINITIONS.md` §A–§L apply verbatim: critical
completion rate/time, deadline violation, recovery success/time, failure-to-replan
latency, post-failure invalid proposal rate, failed-resource reselection,
existing service damage, ground fallback rate, necessary ground fallback,
candidate-set reduction, air resource availability, decision behaviour, backend
observability. The two post-run corrections (GROUND-fallback recovery key;
AIR-actions-only reselection) are carried into the E3 formulas as-is.

## Statistical unit (protocol §25/§28, unchanged)

Independent unit = scenario × simulation seed (n = 20 per scenario); managers
paired on identical (scenario, seed). Continuous: paired t-test + paired
Wilcoxon; binary: McNemar; multiple comparisons: Holm; report Cohen's d, 95 % CI,
raw p and adjusted p. Same-prompt repeats are NOT samples. The primary
statistical comparison for E3 is on `system_weighted_loss` (paired B1/B2/B4b vs
B0 and vs each other), with the inherited critical-mission metrics as secondary.

## Implementation note

The formulas above are frozen before the primary runs. Any post-run aggregation
defect must be corrected by deterministic recomputation from the frozen artifacts
with per-run provenance (as in Experiment 2), never by modifying a simulation
artifact.
