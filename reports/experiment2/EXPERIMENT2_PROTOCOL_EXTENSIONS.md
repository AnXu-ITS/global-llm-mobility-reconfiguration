# Experiment 2 — Protocol Extensions (frozen pre-run)

Experiment 2 keeps every frozen Experiment-1 object byte-identical (verified by
the entry regression: 26/26 hash matches). Everything below is an **additive,
manager-agnostic extension** implemented in NEW files, recorded here per
protocol §11 / §14 / §32 before any formal run. No B2 preference weight, no
prompt text, and no B1 rule was changed.

**CHANGELOG entry:** `CHANGELOG.md` → "Experiment 2 protocol extensions (E2-EXT-*)".
**Comparability note:** these extensions are only active under the Experiment-2
runner (`orchestrator/experiment2_runner.py`); Experiment-1 artifacts, code paths
and hashes are untouched, so Experiment-1 comparability is unaffected.

---

## E2-EXT-CLOCK-1 — canonical Experiment-2 timeline (fixed)

- t = 0: simulation starts (4-aircraft frozen fleet, 2 background services busy).
- t = 300: **B1 ground disruption** (critical-link closure, +37.87 %) AND
  **M-CRITICAL-001 released** (medical_blood, CRITICAL, V2→V1) → manager decision.
- t = 360: **ONE air-layer failure** injected (family/target/zone frozen in the
  scenario config) → local safety if applicable → candidate-set update →
  manager replanning → checker → execution.
- t = 900: simulation end (verified in pilot that all metrics terminate ≤ 900 s).
- Duration 900 s for **every** manager of every scenario (no per-manager durations).
- **Deadline:** `deadline_s = 480` (absolute) = release 300 s + 180 s CRITICAL
  slack. The 180-s slack is the frozen Experiment-1 CRITICAL urgency value; with
  the frozen ground context (post-B1-closure ground ETA 181.76 s) ground-only
  resolution marginally misses the deadline while air meets it — this is the
  fixed ground-side trade-off all failure effects are measured against. The
  deadline is identical for all managers and all scenarios (frozen).

## E2-EXT-STATE-1 — additive aircraft state transitions

The frozen registry (`orchestrator/registry.py`, unchanged) has no
AVAILABLE→DEGRADED / AVAILABLE→CONTINGENCY transition, but F1/F2 can hit an
idle aircraft (e.g. B0 never dispatched M-UAV-02). `failures/state_ext.py`
implements the additive transitions

```
AVAILABLE → DEGRADED      (F2 GNSS degradation of an idle aircraft)
AVAILABLE → CONTINGENCY   (F1 C2 lost on an idle aircraft)
```

applied by the failure injectors only, with an explicit `E2-EXT-STATE-1` marker
in the failure trace. Manager-agnostic; no frozen state machine is modified; no
Experiment-1 code path uses these transitions.

## E2-EXT-GS-1 — Global State failure visibility

The frozen `global_state_v1` schema is reused without modification:
- `infrastructure.utm_state` carries `NOMINAL` / `DEGRADED` / `OUTAGE`
  (the field is a free string in the frozen schema). The Experiment-2 runner
  patches this field deterministically from the frozen scenario config (before
  the failure it is `NOMINAL`).
- air risk zones appear in `infrastructure.failure_zones` (frozen shape:
  `{id, edge_id, impact_level, state}`) with `id` like `ZN-F5-UNKN-01` /
  `ENV-F6-FLYAWAY`, `edge_id: ""`, `impact_level: high`, `state: CLOSED` while
  active. Ground B1/B2/B3 links keep their existing zone entries.
- aircraft `gnss_status` / `c2_status` / `status` / `commandable` fields already
  exist in the frozen schema and are set by the injectors.
No schema file is modified (hash unchanged).

## E2-EXT-CAND-1 — candidate table 2.1.0 (additive, manager-agnostic)

`orchestrator/candidate_info_e2.py` subclasses the frozen `CandidateEvaluator`.
`CANDIDATE_TABLE_VERSION = "2.1.0"` (bump + CHANGELOG + this comparability
note; the frozen 2.0.0 module is untouched). All frozen fields are inherited;
B1/B2/B4b consume the **same** table. Additions:

1. **New factual fields per air candidate** (no scoring, no ranking):
   - `failure_reason` — str|null: which failure-state makes the candidate
     illegal (only when a failure-aware rule rejected it; frozen reject reasons
     keep their original `reject_reason` text);
   - `risk_zone_intersection` — bool: candidate route/aircraft intersects an
     active air risk zone;
   - `utm_eligible` — bool|null: whether UTM state currently permits a NEW air
     assignment for this candidate's mission.
2. **New failure-aware legality rules** (applied AFTER the frozen filters, so
   frozen reject reasons are preserved verbatim):
   - **UTM (F3).** `utm_state == DEGRADED`: a *new* non-CRITICAL mission
     (mission in the `new` bucket, priority ≠ CRITICAL) has all air candidates
     illegal (`UTM_DEGRADED_NEW_NONCRITICAL_AIR_PROHIBITED`); CRITICAL missions
     keep normal feasibility rules. `utm_state == OUTAGE`: every mission that
     requires a NEW air assignment (WAITING / NEEDS_REPLAN / INTERRUPTED) has
     all air candidates illegal (`UTM_OUTAGE_NEW_AIR_PROHIBITED`). Ground
     candidate unaffected.
   - **Risk zones (F5/F6).** An air candidate is illegal when (a) the aircraft's
     current position lies inside an active air risk zone
     (`AIRCRAFT_IN_RISK_ZONE`), or (b) any leg of its route (aircraft position →
     first waypoint → … → destination) intersects an active air risk zone
     (`ROUTE_INTERSECTS_RISK_ZONE`). Geometry: F5 = circle (center, radius);
     F6 = corridor strip (start, heading, half-width, length) around the frozen
     flyaway trajectory. Intersection = great-circle point/segment distance ≤
     radius / half-width (deterministic haversine). Zone config carries a
     `candidate_rule` key: `full` (F5/F6 — position + route rules) vs `none`
     (F2 — the zone appears in the Global State for awareness but imposes no
     candidate rule; its effect flows through the aircraft state, see
     E2-EXT-F2-1).
   - **GNSS (F2).** Degraded aircraft are already rejected by the frozen
     `status == DEGRADED` filter; no extra rule is needed. The GNSS zone itself
     imposes no route restriction on other aircraft (frozen minimal semantics).
3. The manager-agnostic contract is unchanged: no B2 score, no ranking, no
   recommendation. B1/B2 rank over `legal` exactly as before; B4b renders the
   same table (new fields visible, factual only).

## E2-EXT-CHECK-1 — feasibility checker extension (hard constraints)

`safety/feasibility_checker_e2.py` subclasses the frozen `FeasibilityChecker`
(new file; frozen checker untouched). After the frozen checks pass, it adds
manager-agnostic hard constraints:
- `UTM_AIR_PROHIBITED` — air mission action while UTM rules prohibit it
  (same predicates as E2-EXT-CAND-1);
- `GNSS_DEGRADED_AIRCRAFT` — action on an aircraft with
  `gnss_status == DEGRADED` (and `status == DEGRADED`);
- `RISK_ZONE_VIOLATION` — aircraft position or route intersects an active air
  risk zone;
- failed landing site / lost-link / contingency aircraft remain covered by the
  frozen checker codes (`V1_UNAVAILABLE`, `AIRCRAFT_NOT_COMMANDABLE`,
  `AIRCRAFT_IN_CONTINGENCY`, …).

Rejections are recorded as violations and in `action_pipeline.jsonl`; nothing is
silently repaired (normalize-then-validate contract unchanged).

## E2-EXT-SEM-1 — semantic validator extension (GS-based)

`safety/semantic_validator_e2.py` subclasses the frozen `SemanticValidator`
(new file). Adds GS-based error types mirroring E2-EXT-CHECK-1:
`UTM_AIR_PROHIBITED`, `GNSS_DEGRADED_AIRCRAFT`, `RISK_ZONE_VIOLATION`,
plus the frozen `SITE_UNAVAILABLE` (already covers F4 in the frozen validator).
The LLM manager's INTERNAL validation/retry still uses the frozen validator
(unchanged); the Experiment-2 gates run in the orchestrator pipeline for every
manager, so a proposal violating only E2 constraints is rejected and recorded
(and counted in the post-failure invalid-proposal metrics).

## E2-EXT-F1-1 — F1 C2 Lost Link (reuses frozen semantics)

Frozen `failures/c2_lost.py` semantics verbatim:
`c2_status=LOST`, `status=CONTINGENCY`, `reassignable=false`,
`commandable=false`, affected mission `INTERRUPTED → NEEDS_REPLAN`, local
contingency `RETURN → V3` fires immediately and never waits for the manager.
Extension only: the injector may target an idle aircraft (E2-EXT-STATE-1) and
the failure target is frozen in the scenario config (exogenous).

## E2-EXT-F2-1 — F2 GNSS degradation (frozen safe-policy)

- A frozen `GNSS_DEGRADED_ZONE` (circle) is declared at t = 360. Every aircraft
  whose position lies inside the zone **at the trigger instant** becomes
  `gnss_status = DEGRADED`, `status = DEGRADED` (one-shot; no new physical
  error model, per protocol §9).
- A DEGRADED aircraft may not take any NEW task (frozen status filter + E2
  checker). If it is BUSY en route to a precision landing site, its current
  mission is `INTERRUPTED → NEEDS_REPLAN` (it can no longer guarantee the
  precision approach) and the aircraft executes the local safe action
  **divert to V3** (manager-independent; the aircraft remains commandable and
  DEGRADED for the rest of the run).
- Zone membership is evaluated only at the trigger; the zone persists in the
  Global State for manager awareness for the rest of the run.

## E2-EXT-F3-1 — F3 UTM outage (frozen semantics)

- `DEGRADED`: new non-critical air missions prohibited; in-flight missions
  continue; critical reassignment subject to the existing feasibility rules.
- `OUTAGE`: new air missions prohibited (including critical reassignments);
  in-flight missions follow the frozen safe-policy **safe termination**:
  critical and non-critical in-flight missions are `INTERRUPTED →
  NEEDS_REPLAN` and their aircraft divert to V3 (local, manager-independent).
- The LLM never performs tactical safety (L0/L1 unchanged).

## E2-EXT-F4-1 — F4 landing-site failure

`Vx.available = false` at t = 360. Every mission with `destination == Vx` is
re-evaluated → `NEEDS_REPLAN`; the affected aircraft diverts to V3 (local).
All air candidates whose destination is Vx are illegal (frozen destination
filter + `SITE_UNAVAILABLE` / `Vx_UNAVAILABLE` gates). Route-waypoint
availability is NOT additionally checked (frozen destination-based semantics
preserved; recorded as an abstraction limitation). Ground fallback is unaffected.

## E2-EXT-F5-1 — F5 unknown / non-cooperative aircraft

At t = 360 an unknown aircraft `UNKN-01` (never in the registry, never a
candidate) appears in BlueSky on a frozen trajectory and a **temporary risk
zone** (frozen circle) is declared for [360, 480] s. Semantics:
- an aircraft inside the zone at a decision instant cannot receive a new
  assignment;
- a mission whose aircraft position or route intersects the zone at the trigger
  instant is `INTERRUPTED → NEEDS_REPLAN`; the affected (commandable) aircraft
  diverts to V3 (local collision avoidance / staging, manager-independent —
  tactical avoidance remains outside the manager);
- the zone dissolves at t = 480 (recorded in `failure_zones` state).

## E2-EXT-F6-1 — F6 flyaway / uncontrolled trajectory

At t = 360 the frozen target aircraft becomes `status = CONTINGENCY`,
`commandable = false`, `trajectory_mode = UNCONTROLLED_PREDEFINED` (dynamic
attribute + `contingency_mode` marker; registry class untouched), abandons its
current mission (`INTERRUPTED → NEEDS_REPLAN`), snaps to the frozen trajectory
origin (the point where control was lost) and follows the frozen trajectory in
BlueSky for the rest of the run. A frozen envelope (corridor strip around the
trajectory) is declared for [360, 900]. Missions whose aircraft/route
intersects the envelope at the trigger are `INTERRUPTED → NEEDS_REPLAN`; the
affected commandable aircraft diverts to V3 (local). Air candidates
intersecting the envelope are illegal (E2-EXT-CAND-1).

## E2-EXT-WL-1 — workloads W0 / W1 (scenario-frozen)

The 4-aircraft fleet is never expanded. Two scenario-frozen workloads realize
the three impact contexts:

- **W0** (canonical): `L-UAV-01` busy M-L-001 (NORMAL, V2↔V3, non-reassignable);
  `EVTOL-01` busy M-P-001 (NORMAL, V2→V1, non-reassignable);
  `M-UAV-01` AVAILABLE at V1; `M-UAV-02` AVAILABLE at V2.
- **W1** (low-redundancy): additionally `M-UAV-01` busy M-M-001 (HIGH,
  V1↔V3, non-reassignable) and `M-UAV-02` AVAILABLE — so the critical mission
  has exactly ONE feasible air option pre-failure (needed for F1-C3 / F2-C3).

The ground side (B1 closure, critical mission, release time, ground fallback
model, deadline) is identical in every scenario — workload variation is only
ever used to realize the C1/C2/C3 feasible-set differences required by
protocol §16/§17 and is frozen per scenario in `config/experiment2_matrix.yaml`.
No scenario sweeps the ground-severity or urgency dimensions (protocol §4).

## E2-EXT-F3-ML2 — M-L-002 (F3-C1 only)

`E2_F3_C1` adds one new non-critical mission `M-L-002` (logistics, NORMAL,
V2→V3, `ground_fallback: false`, deadline 900 s, released t = 300). Purpose:
UTM DEGRADED's "new non-critical air missions prohibited" has no visible
effect in the otherwise fully-in-flight testbed; M-L-002 gives it a real,
measurable decision (the t = 360 failure-triggered decision targets M-L-002,
whose air candidates are UTM-illegal). M-L-002 is absent from all other
scenarios. Its final `WAITING` state is not service damage under the frozen
M3 definition (noted in the scenario audit).

## E2-EXT-TRG-1 — trigger policy (frozen E1 policy, unchanged)

Event-triggered decisions (t = 300 release, t = 360 failure) + 30-s periodic
re-decisions **only while the critical mission is actionable** (frozen E1
`_periodic_due`). Consequence (documented): after the critical mission is
resolved, lower-priority background missions left `NEEDS_REPLAN` by a failure
receive no further manager decisions; they remain damaged per the frozen M3
definition. This is identical for all managers (fairness preserved).

## Freeze status

All extensions above are frozen **before** the pilot. `EXPERIMENT2_SCENARIO_AUDIT.md`
validates the resulting C1/C2/C3 candidate-set effects, and
`EXPERIMENT2_METRIC_DEFINITIONS.md` freezes the metric formulas before the
formal primary runs.
