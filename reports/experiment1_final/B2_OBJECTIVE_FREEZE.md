# B2 Objective Freeze (Finalization §6)

Frozen before the corrected primary rerun. Values are in
`config/experiment1_b2_weights.yaml` (SHA-256 `a6e880f3c8e7398bcc2c25568141bd141be24d04eab7a8d0989cc72cacc673f6`).
A byte-identical copy is `config/experiment1_v2/experiment1_b2_weights.yaml`.

## Objective (as actually implemented in `managers/optimization.py`)

B2 minimizes the scalar objective `J` over the feasible candidate set
(feasible air candidates + the ground-fallback candidate), where each candidate's
facts are read from the shared candidate table (`gs["candidates"]`).

```
J = w1 * completion_time_s
  + w_deadline * deadline_violation_s
  + w2[preempted_priority]          (REASSIGN/preemption only)
  + w3 * is_reassignment
  + w_risk * risk_score
```

### Term definitions (frozen)

| term | definition | value source |
|---|---|---|
| `completion_time_s` | candidate duration to completion (`eta_s`): air haversine ETA, or ground fallback ETA | shared candidate table `eta_s` |
| `deadline_violation_s` | `max(0, simulation_time + completion_time_s − deadline_s)` | candidate `eta_s` + mission `deadline_s` |
| `w2[preempted_priority]` | disruption penalty of preempting an existing mission of that priority (`LOW/NORMAL/HIGH/CRITICAL`) | shared candidate table `preempted_mission_priority` |
| `is_reassignment` | `1` iff the candidate is a REASSIGN that preempts a busy aircraft, else `0` | shared candidate table `action_type`/`preempted_mission_id` |
| `risk_score` | endurance risk points: `>=120 s → 0`, `60–120 s → 1`, `<60 s → 2` | shared candidate table `endurance_margin_s` |

### Weights (frozen — must not change after the rerun starts)

| weight | value | note |
|---|---|---|
| `w1_completion_time` | `1.0` | seconds of completion time per unit |
| `w_deadline` | `10.0` | seconds of deadline violation per unit (strong) |
| `w2_existing_disruption` | `LOW 20.0 / NORMAL 40.0 / HIGH 80.0 / CRITICAL 100000.0` | preempted-priority penalty (CRITICAL effectively forbidden; already filtered by rule 3) |
| `w3_reassignment` | `30.0` | fixed cost per preemption |
| `w_risk` | `10.0` | per risk point |
| `risk_thresholds_s` | `[120.0, 60.0]` | risk point binning |

### Normalization (frozen)

- All quantities are in **seconds-equivalent** units (completion time, violation,
  disruption penalty, reassignment fixed cost, risk penalty are all added on the
  same second-equivalent scale). No min-max re-scaling is applied; the objective
  is a homogeneous linear combination of second-equivalent terms.
- `deadline_violation_s` is clamped at `0` (no reward for early completion via
  this term; speed is captured by `w1 * completion_time_s`).
- `risk_score` is an integer count of thresholds violated (0/1/2).

## Freeze contract

1. **No weight may change after the corrected primary rerun begins.**
2. **No B2 re-tuning after seeing B4b results.** (Explicitly forbidden.)
3. B2's hard constraints (availability, battery/endurance, compatibility,
   landing-site availability, no equal/higher-priority preemption) are the SAME
   candidate filter as B1 — B2 changes only the RANKING, never the safety envelope.
4. The B2 objective is computed **from the shared candidate-table fields**
   (Finalization §3/§17) — it does not receive any LLM-selected information.

## Mapping to the protocol's five-term description (§6)

The protocol describes J as
`w1·completion/deadline + w2·existing-service-disruption + w3·reassignment-cost
+ w4·ground-delay + w5·operational-risk`. The implemented (and frozen) objective
maps to it as follows: the "completion/deadline" term is split into
`w1·completion_time_s + w_deadline·deadline_violation_s`; "existing-service
disruption" = `w2[preempted_priority]`; "reassignment cost" = `w3`; "operational
risk" = `w_risk·risk_score`; and "ground delay" is **not** a separate term —
ground is scored by the SAME `completion_time_s`/`deadline_violation_s` terms as
air (so air vs ground is compared on a common completion-time scale, not via a
ground-specific weight). This is the faithful frozen form; it is recorded here so
the implemented objective, not an idealized description, is what is frozen.
