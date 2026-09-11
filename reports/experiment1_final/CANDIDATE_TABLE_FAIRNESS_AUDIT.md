# Candidate-Table Fairness & Optimization-Leakage Audit

Protocol §1 / §2. Audits `orchestrator/candidate_info.py` (Candidate Generator,
`CANDIDATE_TABLE_VERSION = 2.0.0`) and every path that produces or consumes the
candidate table. The candidate table is the *only* derived candidate information
any manager receives; it is produced by `CandidateEvaluator.evaluate(gs)` and
injected as `gs["candidates"]` in `Phase2Orchestrator._build_gs` **before any
manager runs**.

## 1. Architecture (Finalization §3)

```
SUMO + BlueSky
  → Global State (state/global_state.py, deterministic)
  → Candidate Generator (orchestrator/candidate_info.py)  ← manager-agnostic
  → Candidate Set  (gs["candidates"])
  → Manager (B0 / B1 / B2 / B4a / B4b)   ← decision POLICY only
  → SemanticValidator → FeasibilityChecker → Executor
```

- **B1, B2, B4b all access the SAME candidate set** (`gs["candidates"]`). B1 ranks
  by min completion time (tie: endurance); B2 ranks by its frozen scalar objective
  computed **from the candidate fields**; B4b renders the candidate table into its
  prompt for semantic/contextual selection. B4a withholds it (interface ablation).
- The Candidate Generator **never runs B2**, never imports the Optimization manager,
  and never receives any objective weight. It is a pure function of
  `(facilities, dispatch_overhead_s, contingency_site, Global State)`.

## 2. Complete field inventory (every field a manager can see)

### 2.1 `summary`

| field | type | source | B2-dependent? |
|---|---|---|---|
| `candidate_table_version` | str | constant `2.0.0` | no |
| `simulation_time` | int | GS `simulation_time` | no |
| `target_mission_id` | str/null | highest-priority actionable mission | no |
| `target_mission_priority` | str/null | mission priority | no |
| `target_mission_origin` | str/null | mission origin | no |
| `target_mission_destination` | str/null | mission destination | no |
| `deadline_slack_s` | float/null | `deadline_s − simulation_time` (environment) | no |
| `cruise_speed_ms` | dict | `ROLE_CRUISE_MS` (fleet constants) | no |
| `dispatch_overhead_s` | float | scenario manager config | no |
| `endurance_margin_s` | float | safety constant `60.0` | no |

### 2.2 `air[]` (one entry per aircraft, in Global-State order — never re-ranked)

| field | type | meaning | B2-dependent? |
|---|---|---|---|
| `resource_id` | str | aircraft id | no |
| `mode` | "AIR" | transport mode | no |
| `type` | "AIR" | legacy alias of mode | no |
| `action_type` | "DISPATCH"/"REASSIGN"/null | legal action implied by the candidate | no |
| `legal` | bool | legality after the deterministic filter | no |
| `reject_reason` | str/null | why filtered (C2/commandability/status/reassignability/priority/battery/endurance/destination/compatibility) | no |
| `eta_s` | float/null | remaining duration (s) now→completion (haversine + cruise speed + overhead) | no |
| `completion_time_s` | float/null | absolute `simulation_time + eta_s` | no |
| `route` | list/null | ordered landing-site waypoints | no |
| `predicted_deadline_violation_s` | float/null | signed `eta_s − deadline_slack_s` (negative = meets) | no |
| `preempted_mission_id` | str/null | current mission of a BUSY/RESERVED aircraft | no |
| `preempted_mission_priority` | str/null | that mission's priority | no |
| `battery_pct` | float/null | aircraft battery level | no |
| `endurance_margin_s` | float/null | aircraft remaining endurance (s) | no |
| `destination_available` | bool/null | destination landing site `state == AVAILABLE` | no |
| `landing_compatible` | bool | destination ∈ aircraft `landing_compatibility` | no |
| `service_loss_estimate` | object | deterministic interruption estimate (see 2.4) | no |

### 2.3 `ground` (single ground-fallback candidate)

Same shape as `air[]` with `resource_id="GROUND"`, `mode="GROUND"`,
`action_type="GROUND_FALLBACK"`, `eta_s` = ground fallback ETA (from
`ground_fallback_eta_s` or `current_d1_h1_eta_s`), `legal` = mission
`ground_fallback` allowed AND ETA present. `battery_pct`/`endurance_margin_s`/
`destination_available`/`landing_compatible` are `null` (not applicable).

### 2.4 `service_loss_estimate` (the interruption / service-loss estimate)

```
{ "interrupts_existing_mission": bool,
  "interrupted_mission_id": str|null,
  "interrupted_mission_priority": str|null }
```

`interrupts_existing_mission` is `true` iff the candidate is a REASSIGN that
preempts a BUSY/RESERVED aircraft; then the interrupted mission id/priority are
copied from the aircraft's `current_mission` / `mission_priority`. This is a
deterministic structural fact (does this candidate interrupt a running service?),
**not** a cost/score and not a B2-weighted quantity.

## 3. Protocol-required field coverage (§1 checklist)

| required check | present | where |
|---|---|---|
| candidate resource ID | ✅ | `resource_id` |
| mode | ✅ | `mode` (alias `type`) |
| feasibility | ✅ | `legal` (+ `reject_reason`) |
| estimated completion time | ✅ | `completion_time_s` (absolute) + `eta_s` (duration) |
| ETA | ✅ | `eta_s` |
| battery/endurance margin | ✅ | `battery_pct` + `endurance_margin_s` |
| current mission | ✅ | `preempted_mission_id` |
| current mission priority | ✅ | `preempted_mission_priority` |
| interruption / service-loss estimate | ✅ | `service_loss_estimate` |
| destination availability | ✅ | `destination_available` |
| compatibility | ✅ | `landing_compatible` |
| ground fallback candidate | ✅ | `ground` |

## 4. Leakage audit (Finalization §2) — required verdicts

The candidate table contains **none** of the forbidden fields:
B2 objective score, weighted cost J, B2 ranking, "best candidate",
"recommended action", optimizer-selected candidate, optimizer shadow price,
optimizer internal utility, hidden rank, or any field depending on B2 weights.

| question | required | verdict | evidence |
|---|---|---|---|
| Q1. Can the table be generated **without running B2**? | YES | **YES** | `CandidateEvaluator.evaluate` imports only `orchestrator.fleet` + `orchestrator.geo`; no optimizer import. |
| Q2. Table contains **only environment / deterministic candidate evaluation**? | YES | **YES** | every field derives from GS + fleet constants + haversine; see §2. |
| Q3. Does the LLM see B2's **final selection**? | NO | **NO** | LLM prompt = Global State (+ candidate table for B4b); B2's `objective_meta`/`selected` are written only to `manager_outputs.jsonl` of the B2 run, never fed to any other manager. |
| Q4. Does the LLM see a **candidate ranking**? | NO | **NO** | `air[]` is emitted in Global-State (aircraft) order, never sorted; no rank field. |
| Q5. Does the LLM see any **scalar score synthesized from B2 weights**? | NO | **NO** | the only scalar derivatives (`eta_s`, `predicted_deadline_violation_s`, `endurance_margin_s`) are weight-free environment quantities. |

**Leakage verdict: PASS — no optimization-solution leakage.**

## 5. Manager-agnostic generation (§3) — verified

- `CandidateGenerator` is `CandidateEvaluator`; it is constructed once in
  `Phase2Orchestrator.__init__` with only `(facilities, dispatch_overhead_s,
  contingency_site)`. It has no reference to any manager.
- `B2` does **not** secretly run inside the generator, and its result is **not**
  given to the LLM. B2's `decide` consumes `gs["candidates"]` (facts) and computes
  its own objective locally; B4b consumes the same `gs["candidates"]` for semantic
  selection. Different managers = different decision *policy* over the *same* facts.

## 6. Shared-facts consistency (Finalization §17)

`CandidateEvaluator._reject_air`, `_air_route`, `_air_eta`, and the ground
candidate are the SAME formulas as `RuleBasedManager._reject_air` / `_air_route` /
`_air_eta` / `_evaluate_ground` (the only difference: the table rounds `eta_s` to 3
decimals). Since B1/B2 now rank over the shared table directly, all managers use
**the same computation pipeline** for completion estimate, feasibility,
infrastructure availability, aircraft compatibility, battery/endurance, and
existing-mission state. No manager holds a more precise or a text-paraphrased ETA.
