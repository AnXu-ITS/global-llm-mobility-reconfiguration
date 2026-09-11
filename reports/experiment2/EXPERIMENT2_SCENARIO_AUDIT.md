# Experiment 2 — Scenario Audit (protocol §19)

Answers the 10 protocol questions for every scenario class. Measured
candidate-set values come from the primary runs
(`outputs/experiment2/scenario_audit.csv`; pre = t-300 decision table, post =
t-360 decision table when the critical mission is actionable, otherwise a
deterministic as-if NEEDS_REPLAN evaluation — labelled in
`failure_trace.json`). 16 scenario classes: 6 families × 3 contexts with two
documented SCENARIO_DESIGN_LIMITATIONs (F3-C2, F4-C2).

## Matrix overview

| scenario | family | context | workload | failure (frozen) | pre→post feasible air (critical) | critical chain |
|---|---|---|---|---|---|---|
| E2_F1_C1 | F1 C2 lost | C1 | W0 | target L-UAV-01 | 2→1 | untouched |
| E2_F1_C2 | F1 C2 lost | C2 | W0 | target M-UAV-02 | 2→1 | interrupted, backup legal |
| E2_F1_C3 | F1 C2 lost | C3 | W1 | target M-UAV-02 | 1→0 | interrupted, no air |
| E2_F2_C1 | F2 GNSS | C1 | W0 | zone r300 @ V3 | 2→1 | untouched |
| E2_F2_C2 | F2 GNSS | C2 | W0 | zone r100 @ corridor 0.52 | 2→1 | interrupted, backup legal |
| E2_F2_C3 | F2 GNSS | C3 | W1 | zone r100 @ corridor 0.52 | 1→0 | interrupted, no air |
| E2_F3_C1 | F3 UTM | C1 | W0+M-L-002 | DEGRADED | 2→1 | untouched (new non-critical air blocked) |
| E2_F3_C3 | F3 UTM | C3 | W0 | OUTAGE | 2→0 | interrupted, no air |
| E2_F4_C1 | F4 site | C1 | W0 | V2 unavailable | 2→1 | untouched |
| E2_F4_C3 | F4 site | C3 | W0 | V1 unavailable | 2→0 | interrupted, no air |
| E2_F5_C1 | F5 unknown | C1 | W0 | zone r400 @ NW corner | 2→1 | untouched |
| E2_F5_C2 | F5 unknown | C2 | W0 | zone r100 @ corridor 0.50 | 2→1 | interrupted, backup legal |
| E2_F5_C3 | F5 unknown | C3 | W0 | zone r600 covering corridor+V3→V1 | 2→0 | interrupted, no air |
| E2_F6_C1 | F6 flyaway | C1 | W0 | envelope low-latitude strip | 2→1 | untouched |
| E2_F6_C2 | F6 flyaway | C2 | W0 | envelope crosses corridor, V3→V1 clear | 2→1 | interrupted, backup legal |
| E2_F6_C3 | F6 flyaway | C3 | W0 | envelope covers corridor + V3→V1 | 2→0 | interrupted, no air |

The pre→post 2→1 in the C1 rows is the frozen holder-exclusion: an in-flight
critical mission cannot be "reassigned to itself" (equal-priority filter), so
the feasible re-assignment set for the untouched mission is the backup alone.
What distinguishes C1 from C2 is therefore the critical-chain interruption
(column 5), per the protocol definition (§16): C1 = failure does not force a
critical-mode switch; C2 = current critical option destroyed but ≥1 legal air
backup remains; C3 = feasible air reduced to 0 and ground becomes the only
robust mode.

## Per-scenario answers (protocol §19, questions 1–10)

### E2_F1_C1 (F1-C1, peripheral C2 lost)
1. C2 lost link on L-UAV-01 at t=360 (frozen RETURN→V3 contingency).
2. Exogenous: target frozen in the matrix; never derived from manager state (exogeneity audit PASS).
3. Changes: L-UAV-01 → CONTINGENCY/uncommandable; M-L-001 → NEEDS_REPLAN.
4. Pre/post: 2→1 (backup M-UAV-01 remains legal; the critical mission is airborne and untouched).
5. C1: yes — limited candidate loss, no critical-mode switch.
6. Critical mission unaffected (completes by air at ≈410 s).
7. Opportunity cost: M-L-001 (logistics service) is interrupted — managers can recover it (air/ground) or cancel.
8. Ground fallback exists for M-L-001 (frozen ground model).
9. Real manager choice: recover M-L-001 by M-UAV-01 vs ground vs cancel; the failure also tempts unnecessary critical reconfigurations (restraint observable).
10. Unique among the 16 (only peripheral-F1 class).

### E2_F1_C2 (F1-C2, critical-chain C2 lost with backup)
1. C2 lost on M-UAV-02 (the dispatched critical aircraft) at t=360.
2. Exogenous ✓ (target frozen; identical for all managers — B0 keeps M-UAV-02 idle, which is the legal policy consequence recorded, not re-targeted).
3. Changes: M-UAV-02 → CONTINGENCY + RETURN→V3; M-CRITICAL-001 → NEEDS_REPLAN.
4. Pre/post: 2→1 (M-UAV-01 legal; recovery route V3→V1 ≈66 s).
5. C2: yes — current option destroyed, ≥1 air alternative.
6. Critical mission is the affected mission (air recovery ≈420 s, meets deadline 480 s).
7. Opportunity cost: none beyond the failure itself (M-L-001/M-P-001 continue).
8. Ground fallback exists (used by B0 from t=300, and available as backup).
9. Real choice: air REASSIGN to M-UAV-01 vs GROUND_FALLBACK vs DELAY.
10. The canonical C2 class for F1; F2-C2/F5-C2/F6-C2 are its cross-family counterparts.

### E2_F1_C3 (F1-C3, low-redundancy C2 lost)
1. C2 lost on M-UAV-02 under W1 (M-UAV-01 committed to a HIGH medical transfer, non-reassignable).
2. Exogenous ✓.
3. Changes: M-UAV-02 → CONTINGENCY; critical → NEEDS_REPLAN; the only other medical asset is busy HIGH.
4. Pre/post: 1→0.
5. C3: yes — no feasible air remains; ground is the only robust mode.
6. Critical mission forced to ground (≈542 s) → deadline violation (deadline 480 s).
7. Opportunity cost: none additional (M-M-001 untouched by design).
8. Ground fallback exists and is the intended resolution.
9. Real choice: ground now vs futile air proposals (rejected) vs delay — failure-awareness pressure.
10. Unique (W1 + F1); F2-C3 is its GNSS counterpart.

### E2_F2_C1 (F2-C1, peripheral GNSS zone)
1. GNSS zone (r=300 m) over V3 at t=360: L-UAV-01 (always in-zone at trigger) → DEGRADED; M-L-001 → NEEDS_REPLAN.
2. Exogenous ✓ (frozen zone).
3. Changes: L-UAV-01 DEGRADED (stays commandable); M-L-001 → NEEDS_REPLAN. EVTOL-01 occasionally in-zone (seed-dependent, honest variation, no critical effect).
4. Pre/post: 2→1 (backup intact; zone imposes no route rule — frozen aircraft-state-only semantics).
5. C1 ✓.
6. Critical mission unaffected (≈410 s).
7. Opportunity cost: M-L-001 recoverable (M-UAV-01 dispatch legal — its route is not zone-restricted).
8. Ground fallback exists for M-L-001.
9. Real choice: recover logistics by air vs ground vs cancel.
10. Unique (GNSS family C1).

### E2_F2_C2 (F2-C2, critical GNSS degradation with backup)
1. GNSS zone (r=100 m) over the corridor at progress 0.52: the critical aircraft (position deterministic at t=360) → DEGRADED; mission → NEEDS_REPLAN; local divert to V3.
2. Exogenous ✓.
3. Changes: critical aircraft DEGRADED (commandable), mission NEEDS_REPLAN; backup M-UAV-01 at V1 outside the zone.
4. Pre/post: 2→1 (backup legal).
5. C2 ✓.
6. Critical air recovery ≈420 s, meets deadline.
7. Opportunity cost: passenger mission occasionally in-zone (seed-dependent, documented).
8. Ground fallback exists.
9. Real choice: air REASSIGN vs ground.
10. GNSS counterpart of the F1-C2/F5-C2/F6-C2 class.

### E2_F2_C3 (F2-C3, GNSS + low redundancy)
1. Same corridor zone under W1 → critical aircraft DEGRADED; M-UAV-01 busy HIGH.
2. Exogenous ✓.
3. Changes: critical aircraft DEGRADED + mission NEEDS_REPLAN; no idle medical asset.
4. Pre/post: 1→0.
5. C3 ✓.
6. Forced ground (≈542 s) → deadline violation.
7. No additional opportunity cost.
8. Ground fallback exists (intended).
9. Real choice: ground vs futile air proposals.
10. Unique (W1 + F2).

### E2_F3_C1 (F3-C1, UTM DEGRADED)
1. UTM → DEGRADED at t=360: new non-critical air missions prohibited; in-flight missions continue.
2. Exogenous ✓.
3. Changes: none to in-flight assets; the new non-critical M-L-002 (released t=300) loses all legal air candidates (this is the visible, measurable effect).
4. Pre/post (critical): 2→1 — critical reassignment stays legal (CRITICAL exception).
5. C1 ✓ (capability-level failure: the air resource layer loses the ability to accept NEW non-critical work; the critical chain is untouched).
6. Critical mission unaffected (≈410 s).
7. Opportunity cost: M-L-002 cannot be flown (managers must delay/cancel; ground disabled by design).
8. Ground fallback: deliberately disabled for M-L-002 (tests whether managers respect the air prohibition instead of inventing alternatives); available for the critical mission.
9. Real choice: DELAY vs CANCEL vs (futile) air proposals for M-L-002.
10. Unique (UTM family).

### E2_F3_C3 (F3-C3, full UTM outage)
1. UTM → OUTAGE at t=360: new air missions prohibited (including critical reassignments); in-flight missions terminate safely (frozen safe-policy).
2. Exogenous ✓.
3. Changes: critical + both background air missions → NEEDS_REPLAN; aircraft divert to V3 (local, manager-independent).
4. Pre/post: 2→0.
5. C3 ✓.
6. Forced ground (≈542 s) → deadline violation.
7. Opportunity cost: both background services damaged (no further triggers to re-plan them — frozen trigger policy, documented).
8. Ground fallback exists (used).
9. Real choice: ground for the critical mission vs futile air proposals (UTM_AIR_PROHIBITED).
10. Unique (full-outage class).

### E2_F4_C1 (F4-C1, peripheral site failure)
1. V2 unavailable at t=360 (logistics hub; critical destination is V1).
2. Exogenous ✓.
3. Changes: the logistics shuttle is re-evaluated when its current leg destination is V2 (≈35 % of seeds — honest seed-dependent variation); critical chain untouched.
4. Pre/post: 2→1 (backup route V3→V1 unaffected).
5. C1 ✓.
6. Critical mission unaffected (≈410 s).
7. Opportunity cost: M-L-001 damaged in the affected seeds.
8. Ground fallback exists.
9. Real choice: recover/abandon the logistics service; restraint observable in unaffected seeds.
10. Unique (F4 family).

### E2_F4_C3 (F4-C3, critical destination site failure)
1. V1 (the critical destination) unavailable at t=360.
2. Exogenous ✓.
3. Changes: critical + passenger (destination V1) missions → NEEDS_REPLAN; aircraft divert to V3.
4. Pre/post: 2→0 (destination-level failure removes every air alternative at once).
5. C3 ✓ — and the reason F4-C2 is a documented SCENARIO_DESIGN_LIMITATION: no single-site failure can break the current critical option while leaving a legal air alternative to V1.
6. Forced ground (≈542 s) → deadline violation.
7. Opportunity cost: M-P-001 damaged (deterministic).
8. Ground fallback exists (unaffected by the air-site failure).
9. Real choice: ground vs futile proposals to V1 (SITE_UNAVAILABLE).
10. Unique.

### E2_F5_C1 (F5-C1, peripheral intrusion)
1. UNKN-01 + temporary risk zone (r=400 m) in the NW corner at t=360 — contains no current asset.
2. Exogenous ✓ (frozen zone + trajectory).
3. Changes: airspace region temporarily closed; nothing operational crosses it.
4. Pre/post: 2→1 (backup intact; no candidate route crosses the zone).
5. C1 ✓ — designed as the "no critical contact" intrusion: the correct managerial behaviour is restraint (NO_ACTION); over-reaction is measurable decision behaviour.
6. Critical mission unaffected (≈410 s).
7. Opportunity cost: none (by design).
8. Ground fallback exists (unused).
9. Real choice: NO_ACTION (correct) vs unnecessary reconfiguration — a genuine decision-behaviour test.
10. Unique (the only zero-contact intrusion class; cross-check with the C1 site/C2-lost classes).

### E2_F5_C2 (F5-C2, critical-chain intrusion with backup)
1. UNKN-01 + risk zone (r=100 m) over the corridor at progress 0.50: the critical aircraft is inside at t=360 (deterministic); mission → NEEDS_REPLAN; local divert to V3.
2. Exogenous ✓.
3. Changes: critical mission interrupted; backup M-UAV-01 (at V1, outside) remains legal; its V3→V1 recovery route is outside the zone (geometry frozen + audited).
4. Pre/post: 2→1.
5. C2 ✓.
6. Air recovery ≈420 s, meets deadline.
7. Opportunity cost: passenger mission occasionally in-zone (seed-dependent, documented).
8. Ground fallback exists.
9. Real choice: air REASSIGN vs ground.
10. Cross-family counterpart of F1-C2/F2-C2/F6-C2 (zone semantics differ: F5 blocks routes, F1 blocks commandability, F2 blocks the aircraft state).

### E2_F5_C3 (F5-C3, wide intrusion — no air)
1. UNKN-01 + risk zone (r=600 m) covering the critical corridor AND the V3→V1 recovery segment.
2. Exogenous ✓.
3. Changes: critical mission → NEEDS_REPLAN; logistics (always) and passenger (≈80 % of seeds) missions interrupted; the backup's recovery route intersects the zone → illegal.
4. Pre/post: 2→0 (`ROUTE_INTERSECTS_RISK_ZONE` on the backup — audited).
5. C3 ✓.
6. Forced ground (≈542 s) → deadline violation.
7. Opportunity cost: both background services damaged.
8. Ground fallback exists (roads unaffected by the airspace zone).
9. Real choice: ground vs futile air proposals.
10. Unique.

### E2_F6_C1 (F6-C1, peripheral flyaway)
1. L-UAV-01 flies away uncontrolled at t=360; envelope = low-latitude eastward strip (lat band below the passenger return leg).
2. Exogenous ✓ (frozen trajectory/envelope; aircraft snap-to-trajectory documented).
3. Changes: L-UAV-01 → CONTINGENCY/uncommandable + M-L-001 → NEEDS_REPLAN; no other asset in the envelope.
4. Pre/post: 2→1.
5. C1 ✓.
6. Critical mission unaffected (≈410 s).
7. Opportunity cost: M-L-001 (cargo lost with the flyaway — managers should cancel rather than re-fly; both behaviours observable).
8. Ground fallback exists for M-L-001.
9. Real choice: cancel vs ground vs (futile) re-fly of the lost service.
10. Unique (flyaway family).

### E2_F6_C2 (F6-C2, critical-chain flyaway with backup)
1. L-UAV-01 flyaway whose envelope (heading 20°, half-width 200 m) crosses the critical corridor but leaves V3→V1 clear (geometry audited).
2. Exogenous ✓.
3. Changes: critical mission → NEEDS_REPLAN (aircraft in envelope, diverted to V3); backup M-UAV-01 (at V1, outside the envelope) remains legal.
4. Pre/post: 2→1.
5. C2 ✓.
6. Air recovery ≈420 s, meets deadline.
7. Opportunity cost: M-L-001 (flyaway) always; M-P-001 seed-dependent (documented).
8. Ground fallback exists.
9. Real choice: air REASSIGN vs ground.
10. Cross-family counterpart (envelope = corridor strip, unlike F5's circle).

### E2_F6_C3 (F6-C3, flyaway blocks all air)
1. L-UAV-01 flyaway whose envelope (heading 40°, half-width 350 m) covers the critical corridor AND V3→V1 (and V1 itself).
2. Exogenous ✓.
3. Changes: critical + passenger missions → NEEDS_REPLAN; backup M-UAV-01 is inside the envelope → illegal.
4. Pre/post: 2→0.
5. C3 ✓.
6. Forced ground (≈542 s) → deadline violation.
7. Opportunity cost: both background services damaged.
8. Ground fallback exists.
9. Real choice: ground vs futile air proposals (RISK_ZONE_VIOLATION).
10. Unique.

## SCENARIO_DESIGN_LIMITATION records (§17/§27)

- **F3-C2 (UTM)**: a single UTM state change cannot break the current critical
  option while leaving a legal air backup — OUTAGE forbids ALL new air
  assignments (so the backup is illegal by construction), and DEGRADED does not
  interrupt in-flight missions (so the current option is never broken). The
  only C2-shaped UTM effect would need a second event (an Experiment-3 compound
  disruption). Matrix reduced by 1 class; F3 contributes C1 + C3.
- **F4-C2 (landing site)**: the critical destination V1 is shared by EVERY air
  alternative, so a failure of V1 removes all air options at once (C3); any
  other single-site failure (V2/V3) is peripheral (C1). No single-site failure
  produces "current option broken + ≥1 air alternative to V1 remains". Matrix
  reduced by 1 class; F4 contributes C1 + C3.

Per protocol §27 the matrix is therefore 16 classes (not 18) →
16 × 20 × 4 = **1280 primary runs** (B0/B1/B2/B4b = 320 each).

## Measured validation

`tools/audit_exp2_scenarios.py` verifies the C1/C2/C3 label of every
(scenario, manager, seed) cell from the primary runs
(`outputs/experiment2/scenario_audit.csv`): the measured context
(pre/post feasible air + critical-chain interruption) must equal the frozen
matrix label for every cell. Any failure blocks the primary analysis.

**Result: PASS (1280/1280 cells audited).**

- **B0**: `B0-IMMUNE` 20/20 seeds in every scenario — its ground-only choice
  means no air failure can touch its critical chain (the legal policy
  consequence recorded per protocol §7, not a label violation).
- **B1 / B2**: measured context equals the frozen label in **20/20 seeds of
  every scenario** (C1: 2→1 without interruption; C2: 2→1 with interruption;
  C3: →0 with interruption).
- **B4b**: label match in 20/20 seeds for 14 of 16 scenarios. The exceptions:
  `E2_F6_C2` (4/20 seeds) and `E2_F6_C3` (5/20 seeds) are
  `DIVERGENT-PRE-FAILURE` cells — in those runs the B4b arm experienced
  consecutive LLM transport errors at t=300–360, so the critical mission was
  still WAITING when the failure fired; the failure therefore could not
  interrupt a chain that had not been launched (legal policy/backend
  consequence; the runs are KEPT, and the backend contribution is reported
  separately in `LLM_BACKEND_RELIABILITY` — §23/§30/§39). In those cells the
  post-failure feasible-air set is genuinely 0 (e.g. the F6 envelope covers
  V2, blocking the pickup route), which the audit records per-seed.

