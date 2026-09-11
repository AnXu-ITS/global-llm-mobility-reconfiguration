# Experiment 2 — Metric Definitions (frozen pre-run, protocol §20)

All metrics are computed per (scenario, seed, manager) run from the run
artifacts (`metrics.json`, `events.csv`, `actions.csv`, `action_pipeline.jsonl`,
`violations.csv`, `failure_trace.json`, `manager_outputs.jsonl`), and are frozen
BEFORE the formal primary runs. Field names below refer to `metrics.json` as
written by `orchestrator/experiment2_runner.py::_metrics`.

Notation: `release_t = 300 s`, `failure_t = 360 s`, `deadline_s = 480 s`
(absolute; release + 180 s frozen CRITICAL slack), `comp_t` = simulation time of
the critical mission's terminal completion event (`MISSION_COMPLETED` /
`GROUND_FALLBACK_COMPLETED` in `events.csv`).

---

## A. Critical mission outcomes (frozen Experiment-1 definitions, unchanged)

- **Critical Mission Completion Rate** — fraction of runs with
  `critical_mission_final_state == "COMPLETED"`.
- **Critical Mission Completion Time** — `critical_mission_completion_time_s =
  comp_t − release_t` (None = horizon-censored, reported separately).
- **Deadline Violation Rate** — fraction of runs with
  `critical_mission_deadline_violation == true`, i.e. `comp_t > deadline_s`.
  (Uncompleted runs are reported as a separate censored count, not as
  violations.)

## B. Mission Recovery Success (protocol §20 B)

`affected_critical` = the critical mission was in `EN_ROUTE`/`ASSIGNED` with
`mode == AIR` at the failure instant and its state became
`NEEDS_REPLAN`/`INTERRUPTED` because of the failure
(`failure_trace.critical_mission_state_before/after`).

`recovery_success` = `affected_critical` AND the mission subsequently regained a
legal, active execution path: an event at t ≥ 360 with
`event_id == MISSION_STARTED` (AIR reassignment executed) **or**
`GROUND_FALLBACK_STARTED`, for the critical mission.
`recovery_mode` ∈ {AIR, GROUND}. `recovered_completed` records, separately,
whether that path reached `COMPLETED` within 900 s (never conflated with
`recovery_success`).

Runs where `affected_critical == false` (C1 scenarios, and all B0 runs — B0's
ground choice is not air-affected) are reported as recovery-N/A and excluded
from recovery-rate denominators.

## C. Failure-to-Replan Latency (protocol §20 C)

`failure_to_replan_latency_s = t(first ISSUED manager action at t ≥ 360) − 360`
(any mission). `critical_first_valid_replan_time_s` = the t of the first ISSUED
action at t ≥ 360 targeting the critical mission (None if never).
Simulation-time operational latency; real LLM wall-clock latency is recorded
separately in `llm_metadata` and never advances the clock (Frozen Simulation
Decision Mode).

## D. Recovery Time (protocol §20 D)

`recovery_time_s = t(regain event) − 360`, where the regain event is the same
`MISSION_STARTED` / `GROUND_FALLBACK_STARTED` event as in B (i.e., the instant
the affected mission re-enters an active execution mode — the subsequent flight
time is NOT included).

## E. Post-Failure Invalid Proposal Rate (protocol §20 E)

From `action_pipeline.jsonl` rows with t ≥ 360 (the orchestrator-level
proposals of every manager, including B0/B1/B2):
`post_failure_proposals` = row count;
`post_failure_rejected` = rows with result ∈ {REJECTED, REJECTED_SEMANTIC};
`post_failure_rejected_failure_related` = rejected rows whose violations (from
`violations.csv` / semantic error types) contain a failure-related code:
`AIRCRAFT_IN_CONTINGENCY`, `AIRCRAFT_NOT_COMMANDABLE`, `AIRCRAFT_UNAVAILABLE`,
`GNSS_DEGRADED_AIRCRAFT`, `AIRCRAFT_DEGRADED`, `UTM_AIR_PROHIBITED`,
`RISK_ZONE_VIOLATION`, `SITE_UNAVAILABLE`, `*_UNAVAILABLE`.
Rate = rejected_failure_related / proposals (per cell and per manager).
Checker rejections are kept, never repaired (frozen contract).

## F. Failed-Resource Reselection Rate (protocol §20 F)

`failed_resource_reselection` = number of post-failure proposals (any result)
whose `aircraft_id` or `target_site` equals the failed resource/site
(`failure_trace.target`). Counted even when rejected downstream — the point is
whether the manager still *proposed* the just-failed resource.

## G. Existing Service Damage (protocol §20 G)

Frozen Experiment-1 M3 definition, unchanged:
`existing_missions_damaged_count = |{ m ∈ missions : m.id ≠ critical_mission_id
∧ status(m) ∈ {INTERRUPTED, NEEDS_REPLAN, CANCELLED, FAILED} }|` (final registry
status at shutdown). Mean per run over seeds = expected damaged missions per
run; the binary "any damage" rate is reported separately, never conflated.

## H. Ground Fallback Rate (protocol §20 H)

`ground_fallback_rate` = fraction of runs with
`critical_mission_final_mode == "GROUND"` (frozen E1 M9 definition: final mode,
not issued actions). `failure_induced_ground_fallback` = a
`GROUND_FALLBACK_STARTED` event for the critical mission at t ≥ 360.

## I. Necessary Ground Fallback (protocol §20 I)

`necessary_ground_fallback` = `affected_critical` AND
`failure_trace.candidate_count_after == 0` (post-failure feasible air = 0).
`necessary_ground_fallback_correct` = necessary AND the critical mission entered
`GROUND_FALLBACK_STARTED` at t ≥ 360. DELAY/CANCEL resolutions and
"air-proposed-then-rejected" sequences are reported separately in the analysis
(never merged into "correct").

## J. Candidate-Set Reduction (protocol §20 J)

`candidate_count_before` = legal air candidates for the critical mission in the
t = 300 decision table (`candidate_info.jsonl`, target = critical mission);
`candidate_count_pre_failure_asif` = legal air candidates evaluated at t = 360
just before the failure (as-if NEEDS_REPLAN evaluation when the mission is not
actionable — labelled `as_if_needs_replan` in `failure_trace.json`);
`candidate_count_after` = legal air candidates at t = 360 after the failure
(real decision table when the critical mission is the target, else the same
as-if evaluation — label recorded);
`candidate_set_reduction_delta = before − after`.
All counts come from the same manager-agnostic candidate evaluator (2.1.0).

## K. Air Resource Availability (protocol §20 K)

Recorded in `failure_trace.state_before/after.air_availability`:
`usable` = aircraft with status ∈ {AVAILABLE, BUSY};
`commandable` = `commandable == true` and `c2_status == NORMAL`;
`compatible` = aircraft whose landing compatibility includes V1 (the critical
destination). Reported before vs after the failure.

## L. Decision Behavior (protocol §20 L)

`post_failure_issued_types` = types of ISSUED actions at t ≥ 360;
`post_failure_proposed_types` = types of proposed actions at t ≥ 360.
Counts of REASSIGN / GROUND_FALLBACK / DIVERT / REROUTE / RETURN / LAND /
DELAY / CANCEL / NO_ACTION / RESERVE / DISPATCH / ESCALATE are tabulated per
(manager, scenario). Proposed vs issued are ALWAYS reported separately
(protocol §21: checker success ≠ manager success).

## Backend observability (protocol §23, frozen E1 policy)

Per LLM call in `llm_metadata`: `response_id`, `input/prompt_tokens`,
`reasoning_tokens`, `output_tokens`, `finish_reason`, `latency_s`, `retry_count`,
`empty_content_count`, `cached_tokens`. Timeouts / empty content are recorded and
kept in the primary dataset — never silently substituted (no B2 fallback).

## Statistical unit (protocol §25/§28)

Independent unit = scenario × simulation seed (n = 20 per scenario); managers
are paired on identical (scenario, seed) realizations. Continuous metrics:
paired t-test + paired Wilcoxon; binary metrics: McNemar; multiple comparisons:
Holm correction; report effect size (Cohen's d), 95 % CI, raw p and adjusted p.
Same-prompt repeats are NOT samples (replay-cached runs are reproducibility
only).

## Implementation note (transparent post-run correction)

The formulas above were frozen before the primary runs. Two implementation
defects in the aggregation step were found and corrected AFTER the runs, with
per-run provenance (`metrics_recomputed.json`, CHANGELOG entry); no simulation
artifact was modified:

1. The recovery-event search required an `aircraft` payload key, so
   GROUND-fallback recoveries were missed (`recovery_success`,
   `recovery_time_s`, `recovery_mode`). Recomputed for all 1280 runs from the
   frozen `events.csv` with exactly the §B/§D formulas.
2. `failed_resource_reselection` counted GROUND_FALLBACK actions whose
   `target_site` equals the failed site (the LLM fills the mission destination
   into the JSON even for ground actions — not a reselection). Recomputed with
   the AIR-actions-only rule of §F.

Both corrections are deterministic functions of the frozen artifacts.

