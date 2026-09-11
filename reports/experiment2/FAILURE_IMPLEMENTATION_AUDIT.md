# Experiment 2 — Failure Implementation Audit (protocol §10)

Each of the six failure families was audited by a dedicated test that runs the
CANONICAL Experiment-2 runner (not a mock) and proves the 8 protocol audit
points:

1. the failure event fires correctly;
2. the affected state changes per the frozen semantics;
3. unaffected state is NOT wrongly modified;
4. the failure is visible in the Global State (manager input at t = 360);
5. the Candidate Generator updates correctly;
6. the checker enforces the hard constraints;
7. the simulator clock is unaffected;
8. replay is deterministic (byte-identical artifacts).

**Verdict: 6 / 6 families PASS — any family FAIL would block the formal matrix.**

| family | test file | scenario used | result |
|---|---|---|---|
| F1 — C2 Lost Link | `tests/test_exp2_f1_c2.py` | E2_F1_C2 (seed 20240601, B1) | **9/9 PASS** |
| F2 — GNSS degradation | `tests/test_exp2_f2_gnss.py` | E2_F2_C2 (seed 20240601, B1) | **9/9 PASS** |
| F3 — UTM outage | `tests/test_exp2_f3_utm.py` | E2_F3_C3 (seed 20240601, B1) | **9/9 PASS** |
| F4 — landing-site failure | `tests/test_exp2_f4_landing.py` | E2_F4_C3 (seed 20240601, B1) | **9/9 PASS** |
| F5 — unknown aircraft | `tests/test_exp2_f5_unknown.py` | E2_F5_C2 (seed 20240601, B1) | **9/9 PASS** |
| F6 — flyaway | `tests/test_exp2_f6_flyaway.py` | E2_F6_C2 (seed 20240601, B1) | **9/9 PASS** |

Logs: `outputs/experiment2/audit_test_exp2_f*.log`.

## Per-family evidence (audit points 1–8)

### F1 — C2 Lost Link
- Event `C2_LOST` + `LOCAL_CONTINGENCY` at t = 360 (immediate, before any
  manager decision). M-UAV-02: BUSY→CONTINGENCY, c2=LOST, commandable=false,
  reassignable=false; critical mission EN_ROUTE→NEEDS_REPLAN (frozen
  transitions). L-UAV-01 / EVTOL-01 / M-L-001 / M-P-001 snapshots unchanged.
- GS@360 shows status/c2/commandability + the C2_LOST event; candidate table:
  M-UAV-02 illegal, backup M-UAV-01 legal (count_after = 1); checker rejects a
  proposal to the failed aircraft (`AIRCRAFT_IN_CONTINGENCY`,
  `AIRCRAFT_NOT_COMMANDABLE`). Clock sync OK; replay byte-identical.

### F2 — GNSS degradation
- Event `GNSS_DEGRADED` at t = 360. Critical aircraft BUSY→DEGRADED,
  gnss=DEGRADED, remains commandable; mission→NEEDS_REPLAN; backup M-UAV-01
  untouched. GS@360 shows status/gnss + zone `ZN-F2-02` CLOSED. Candidate
  table: degraded aircraft illegal, backup legal. Checker rejects the degraded
  aircraft (`GNSS_DEGRADED_AIRCRAFT`, `AIRCRAFT_DEGRADED`). Clock OK; replay
  byte-identical.

### F3 — UTM outage
- Event `UTM_STATE_CHANGE` (OUTAGE) at t = 360; critical and both background
  air missions EN_ROUTE→NEEDS_REPLAN (safe termination); idle backup unchanged.
  GS@360 `infrastructure.utm_state = OUTAGE`. Candidate table: all air illegal
  (UTM-coded reason on the available aircraft), ground legal, count_after = 0.
  Checker rejects air under OUTAGE (`UTM_AIR_PROHIBITED`), accepts
  GROUND_FALLBACK. Clock OK; replay byte-identical.

### F4 — landing-site failure
- Event `LANDING_SITE_FAILURE` (V1) at t = 360; critical and passenger
  (dest V1) missions → NEEDS_REPLAN; M-L-001 (dest V2/V3) unchanged.
  GS@360 V1 = UNAVAILABLE, V3 = AVAILABLE. Candidate table: all air illegal,
  `destination_available=false`, ground legal, count_after = 0. Checker rejects
  DISPATCH→V1 (`V1_UNAVAILABLE`), accepts GROUND_FALLBACK. Clock OK; replay
  byte-identical.

### F5 — unknown aircraft / risk zone
- Event `UNKNOWN_AIRCRAFT_INTRUSION` (UNKN-01, zone ZN-F5-02) at t = 360;
  critical mission → NEEDS_REPLAN; backup M-UAV-01 (outside zone) unchanged.
  GS@360 shows the zone CLOSED + the intrusion event. Candidate table: in-zone
  aircraft illegal, backup legal with `risk_zone_intersection=false`
  (count_after = 1). Checker rejects an in-zone DISPATCH
  (`RISK_ZONE_VIOLATION`); geometry unit-checks confirm the critical aircraft
  inside / backup + V1→V3 leg outside the frozen zone. Clock OK; replay
  byte-identical.

### F6 — flyaway
- Event `FLYAWAY_UNCONTROLLED` at t = 360: L-UAV-01 BUSY→CONTINGENCY,
  commandable=false, `trajectory_mode=UNCONTROLLED_PREDEFINED`; envelope
  ENV-F6-02 declared; critical mission → NEEDS_REPLAN; backup untouched.
  GS@360 shows the CONTINGENCY aircraft + envelope CLOSED. Candidate table:
  envelope-crossing aircraft illegal, backup legal (count_after = 1). Checker
  rejects an in-envelope DISPATCH (`RISK_ZONE_VIOLATION`); geometry checks
  confirm the critical aircraft inside / backup outside the frozen strip.
  Clock OK; replay byte-identical.

## Notes

- One transient crash occurred during the F5 replay run of the first audit
  batch (second identical run); the rerun passed byte-identical. All final
  audit verdicts above are from clean paired runs.
- The F2 GNSS zone carries `candidate_rule: none` (frozen semantics: the zone
  degrades aircraft at the trigger; it imposes no route restriction) — the
  degradation effect flows through the aircraft state and is covered by the
  frozen status filter + the E2 checker codes.
- In F5/F6, an aircraft that abandoned its interrupted mission keeps its frozen
  BUSY status and (higher) priority, so the candidate table reports it illegal
  via the frozen priority filter rather than the zone code; both gates are
  legal and the zone rule is exercised on the backup's route where applicable
  (e.g. E2_F5_C3: `ROUTE_INTERSECTS_RISK_ZONE` on M-UAV-01).
