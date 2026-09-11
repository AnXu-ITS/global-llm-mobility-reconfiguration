# Global State Sufficiency Audit (Phase 2)

**Schema:** `schemas/global_state_v1.schema.json` (Global State v1)
**Builder:** `state/global_state.py` (deterministic; sorted keys, fixed float precision)
**Source run:** `runs/phase2_rule_manager/C2_B/snapshots.jsonl` (10 key moments) +
`manager_inputs.jsonl` (the 2 manager-decision moments)

## 1. The 10 key moments

| # | t | moment | b1 / ETA | air snapshot |
|---|----|--------|----------|--------------|
| 1 | 100 | normal operation (warm-up) | OPEN / 131.84 s | L-UAV-01, EVTOL-01 BUSY; M-UAV-01, M-UAV-02 AVAILABLE |
| 2 | 299 | just before B1 closure | OPEN / 131.84 s | same as #1 |
| 3 | 301 | after B1 closure + critical mission dispatched | CLOSED / 181.76 s (+37.87 %) | M-UAV-02 BUSY on M-CRITICAL-001 |
| 4 | 310 | support aircraft en route | CLOSED / 181.76 s | M-UAV-02 en route |
| 5 | 359 | immediately before C2 failure | CLOSED / 181.76 s | M-UAV-02 en route |
| 6 | 361 | immediately after C2 failure + reassignment | CLOSED / 181.76 s | M-UAV-02 CONTINGENCY (c2 LOST); M-UAV-01 BUSY on critical |
| 7 | 370 | backup aircraft en route | CLOSED / 181.76 s | same as #6 |
| 8 | 380 | lost aircraft contingency landed | CLOSED / 181.76 s | M-UAV-02 CONTINGENCY at V3 |
| 9 | 421 | mission completed | CLOSED / 181.76 s | M-UAV-01 AVAILABLE (completed); M-UAV-02 CONTINGENCY |
| 10 | 500 | post-terminal steady state | CLOSED / 181.76 s | same as #9 |

Each snapshot carries the full structured state (ground, per-aircraft, per-mission,
infrastructure, events, trend). Byte-identical across replays (P2-T4 / P2-T12).

---

## 2. Sufficiency questions — itemised answers

**Q1. Does the manager know WHY the ground degraded?**
Yes. `ground.b1_state = CLOSED`, `ground.eta_increase_pct = 37.868`,
`infrastructure.failure_zones[0] = {id: B1, edge_id: 148377677#0, impact_level: high, state: CLOSED}`,
plus the `events` list contains the `GD1` GROUND_DISRUPTION event with the closed edge.

**Q2. Does the manager know whether every air resource is currently busy?**
Yes. Each `air[]` entry has `status` (AVAILABLE/BUSY/CONTINGENCY/…) and a derived
`availability` (AVAILABLE / REASSIGNABLE / BUSY / UNAVAILABLE), plus
`current_mission` and `reassignable`. The manager's rule 2 reads exactly these.

**Q3. Does the manager know the opportunity cost of interrupting a task?**
Yes. Two levels: (a) `air[].current_mission` + `air[].mission_priority` tells the
manager *which* mission it would preempt and its priority (rule 3); (b) every
mission now exposes `delay_cost` and `cancellation_cost` (added during the audit —
they existed in the mission model but were missing from Global State v1; the
schema was fixed). No implicit prompt fill-in.

**Q4. Does the manager know battery / endurance?**
Yes. `air[].battery_pct` and `air[].remaining_endurance_s` are present; the
manager rejects `battery_pct <= 0`, `remaining_endurance_s <= 0`, and requires
`remaining_endurance_s >= ETA + 60 s` headroom (rule 4). *(Known simulator
limitation, not a schema gap: endurance is a static model attribute, not
dynamically drained by BlueSky in Phase 2.)*

**Q5. Does the manager know whether a landing site is available?**
Yes. `infrastructure.landing_sites[].state` (AVAILABLE/UNAVAILABLE) and each
aircraft's `landing_compatibility` list. The checker also enforces site
availability and aircraft–site compatibility.

**Q6. Does the manager know ground fallback?**
Yes. `ground.available_ground_fallback`, `ground.ground_fallback_eta_s`
(181.76 s detour), and per-mission `ground_fallback` flag. Rule 7 uses these.

**Q7. Does the manager know mission deadline?**
Yes. Each mission carries `deadline_s`; rule 8 (DELAY vs CANCEL) uses
`deadline_s` vs `simulation_time`, together with `delay_cost`/`cancellation_cost`.

**Q8. Can the manager decide "keep current mission" vs "preempt a resource"?**
Yes. `air[].status` + `reassignable` + `current_mission` + `mission_priority`
give the preemption decision (rule 3: only preempt a strictly lower-priority
mission), and the candidate ranking (rules 5–6) decides whether preemption is
worth it. `delay_cost`/`cancellation_cost` quantify the alternative.

**Q9. Is there important information only the simulator knows that the manager cannot see?**
No decision-relevant information is hidden. The one abstraction is the ground
ETA: the manager sees the TraCI-router **free-flow** detour ETA (181.76 s), not
per-vehicle dynamic travel time. This is deliberate (Phase-1 decision): the
free-flow route ETA captures the disruption's routing impact while excluding
stuck-vehicle spikes — the correct decision abstraction for reconfiguration.
Lost-link aircraft real-time position is also visible (`air[].position` +
`status=CONTINGENCY`), even though the manager does not control it.

**Q10. Is there unnecessary raw simulation noise?**
No. Global State is fully structured and deterministic: floats are rounded to
fixed precision (lat/lon 7 dp, ETA 3 dp, battery 3 dp, alt 1 dp), collections
are sorted by stable keys, and serialisation is `sort_keys` + fixed separators.
There are no raw timestamps, no unordered logs, no floating-point jitter in the
JSON (byte-identical replay confirmed by P2-T4 / P2-T12).

---

## 3. Conclusion

Global State v1 is **sufficient** for the Rule-Based Manager to make every
Phase-2 decision (B1 closure, critical-mission dispatch, C2-lost reconfiguration,
backup vs ground fallback). One schema gap found and fixed during the audit:
`delay_cost` / `cancellation_cost` were exposed on missions (Q3). No information
is supplied implicitly through natural language.
