# Phase 1 Acceptance Tests — Results

**Testbed:** canonical_suzhou_testbed (S0, 3.2 km crop)
**Run:** `python tests/test_geographic_alignment.py` (T1) + `python tests/test_acceptance.py` (T2/T3/T4/T8/T9)
**Result:** 6 / 6 PASS (re-run after the S0 refinement: crop, B1–B3, sparse air fleet)

---

## T1 — Geographic alignment

- **Criterion:** WGS84 → SUMO x/y → WGS84 Haversine round-trip error `median < 5 m`, `max < 15 m`.
- **Result:** median **0.0000 m**, max **0.0000 m** across **8 landmarks**
  (H1, D1, V1, V2, V3, B1, B2, B3) → **PASS**.
- **Evidence:** `outputs/geographic_alignment.csv`; `reports/GEOGRAPHIC_ALIGNMENT_REPORT.md`.
- **Note:** the round-trip is exact (same pyproj UTM transformer forward+inverse);
  the real geographic displacement is the recorded road-snapping distance
  (H1 42.9 m, D1 58.0 m, V3 27.5 m).

## T2 — Clock synchronisation

- **Criterion:** `SUMO time == BlueSky time == orchestrator time` at every step.
- **Result:** 600 logged steps, `sync_ok=True` for **all** rows, max clock error
  **0.000000 s** → **PASS**.
- **Evidence:** `runs/cosim_smoke_test/clock_sync.csv` (600 rows).
- **Implementation note:** BlueSky is put into OPERATE state at init
  (`bs.sim.op()`) so its first `step()` advances the clock in lockstep with
  SUMO, avoiding a one-step INIT lag.

## T3 — Mission lifecycle

- **Criterion:** support mission traverses `WAITING → ASSIGNED → EN_ROUTE → COMPLETED`.
- **Result:** `M-SUPPORT-001` (medical resupply, CRITICAL, V2→V1) created at
  t=300 (WAITING), dispatched to M-UAV-02 (ASSIGNED→EN_ROUTE), and
  **COMPLETED** at t=410; M-UAV-02 returned to **AVAILABLE** → **PASS**.
- **Evidence:** `runs/cosim_smoke_test/events.csv` (MISSION_STARTED@300,
  MISSION_COMPLETED@410); `runs/cosim_smoke_test/registry_final.json`.

## T4 — Reassignment action (optional)

- **Criterion:** a `NEEDS_REPLAN` mission can be reassigned to an available UAV.
- **Result:** REASSIGN `M-M-001` (holder M-UAV-01 lost) → L-UAV-01 is feasible
  and completes the `REASSIGNED → EN_ROUTE` transition → **PASS**.
- **Note:** checker correctly allows reassignment when the prior holder is
  `UNAVAILABLE` (no spurious `DUPLICATE_ASSIGNMENT`).

## T8 — Invalid action rejection

- **Criterion:** the safety/feasibility checker rejects infeasible actions.
- **Result:** three invalid actions rejected:
  1. DISPATCH a **BUSY** aircraft → `AIRCRAFT_NOT_AVAILABLE_BUSY` (rejected)
  2. DISPATCH to a **non-existent site** → `SITE_NOT_FOUND` (rejected)
  3. DISPATCH an aircraft with **zero battery** → `INSUFFICIENT_BATTERY` (rejected)
  → **PASS**.
- **Evidence:** checker unit test in `tests/test_acceptance.py`.

## T9 — Deterministic replay

- **Criterion:** same seed + same scenario ⇒ byte-identical outputs.
- **Result:** two independent 40 s runs (seed 424242, B1 close at t=20) produce
  **identical** `events.csv`, `ground_state.csv`, `air_state.csv`,
  `clock_sync.csv` (MD5 equal) → **PASS**.
- **Evidence:** `runs/replay_a`, `runs/replay_b`; `tests/test_acceptance.py`.

---

## Refined S0 — what changed and why the tests still hold

- **Crop 5 × 5 km → 3.2 × 3.2 km** (centred on the facility centroid). The
  D1→H1 corridor is preserved exactly (base ETA 131.84 s unchanged) and the
  crop retains **2 distinct ground detours** with B1 closed.
- **B1/B2/B3** candidate disruption links (low/medium/high accessibility
  impact, +7.16 % / +15.43 % / +37.87 %), stored in `disruption_links` and
  selected by `tools/select_disruptions.py`. They are alternatives, not
  simultaneous closures.
- **Sparse air fleet (4 aircraft)**: two background low-altitude services
  (logistics V2↔V3 on L-UAV-01; passenger/eVTOL V2↔V1 on EVTOL-01) plus two
  medical standby assets (M-UAV-01, M-UAV-02). The ground→air response
  (M-UAV-02 dispatch on B1 closure) and the reverse air event (L-UAV-01 →
  UNAVAILABLE at t=450) both still execute, so T2/T3/T9 remain valid.

## Summary

| Test | Requirement | Result |
|------|-------------|--------|
| T1 | geographic alignment | PASS |
| T2 | clock sync | PASS |
| T3 | mission lifecycle | PASS |
| T4 | reassignment (optional) | PASS |
| T8 | invalid action rejection | PASS |
| T9 | deterministic replay | PASS |

All Phase-1 acceptance criteria are satisfied.
