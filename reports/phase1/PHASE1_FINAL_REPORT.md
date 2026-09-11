# Phase 1 Final Report — Unified Ground–Low-Altitude Testbed (S0)

**Project:** Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions
**Scope:** Phase 0/1 — canonical testbed + geographic alignment + synchronized
SUMO/BlueSky co-simulation + one ground→air cross-layer event. **No LLM.**
**Result:** ALL Phase-1 objectives achieved (6/6 acceptance tests PASS).
**Refined S0:** testbed cropped to 3.2 km, B1/B2/B3 disruption links added, air
network reduced to two sparse background services — all revalidated.

---

## Q1 — Is the environment ready and reusable?

**Yes.** SUMO 1.27.1 (pip, headless + TraCI), BlueSky (in-process, OpenAP), and
pyproj 3.7.2 coexist in the existing BlueSky virtual environment
(`C:\Users\xuan1\.venvs\bluesky`, Python 3.14.7). Only `eclipse-sumo`,
`sumo-data`, and `pyproj` were added; nothing else was reinstalled or broken.

Evidence: `reports/ENVIRONMENT_AUDIT.md`.

## Q2 — Is there a single canonical S0 testbed with one source of truth?

**Yes.** `config/scenario_config.yaml` is the single truth for:

- scenario id `S0`, center (31.30377 N, 120.59981 E — facility centroid), 3.2 km × 3.2 km, EPSG:4326 (cropped from 5 × 5 km);
- bbox computed programmatically (south 31.28934, north 31.31820, west 120.58300, east 120.61662);
- the eight facilities H1 / D1 / V1 / V2 / V3 / B1 / B2 / B3 (WGS84 + SUMO x/y mapping);
- the sparse 4-aircraft fleet (2 busy / 2 available);
- `disruption_links` — the B1/B2/B3 selection evidence (closure-impact ranking).

Both the SUMO scene and the BlueSky scene are *generated* from this config
(`tools/build_sumo_scene.py`, `tools/select_disruptions.py`,
`tools/build_bluesky_scene.py`, `orchestrator/fleet.py`), so the layers cannot
diverge.

## Q3 — Is the SUMO ground scene complete and correct?

**Yes.** Real OSM road network (`sim/sumo/network.net.xml`, 4.05 MB, cropped)
with `routes.rou.xml` (background traffic), `additional.add.xml`, `canonical.sumocfg`.

| Facility | Type | WGS84 | Note |
|----------|------|-------|------|
| H1 | hospital | 31.3108006, 120.6035449 | 苏州慈济门诊部 (real OSM POI) |
| D1 | logistics depot | 31.2966529, 120.5957115 | industrial POI |
| V1 | hospital landing | 31.3108767, 120.6039861 | adjacent to H1 |
| V2 | logistics hub landing | 31.2971715, 120.5956323 | adjacent to D1 |
| V3 | backup landing | 31.3065604, 120.6027607 | mid-area |
| B1 | disruption link (high) | 31.2970766, 120.5985914 | edge `148377677#0` |
| B2 | disruption link (medium) | 31.3084362, 120.6007462 | edge `538444299#2` |
| B3 | disruption link (low) | 31.3018624, 120.6023145 | edge `794857408` |

- D1 → H1 shortest path exists (19 edges, free-flow ETA **131.8 s**).
- B1/B2/B3 are **alternative** candidate disruptions (never simultaneous),
  selected with the *TraCI router itself* (each candidate edge closed, ETA
  impact measured):
  - B1 (high)   +37.87 % → detour ETA 181.76 s
  - B2 (medium) +15.43 % → detour ETA 152.18 s
  - B3 (low)    +7.16 %  → detour ETA 141.28 s
- The crop preserves **2 distinct ground detours** with B1 closed (181.76 s and
  191.21 s).

## Q4 — Is the BlueSky air scene complete and on the same geography?

**Yes.** `sim/bluesky/canonical_s0.scn` (21 commands) defines H1/D1/V1/V2/V3/
B1/B2/B3 as waypoints and creates the sparse 4-aircraft fleet on the same WGS84
frame. The air network holds exactly **two background low-altitude services**
(kept sparse on purpose — no air-congestion study):

1. **logistics service** — L-UAV-01 (Amzn) shuttling V2 ↔ V3;
2. **passenger/eVTOL service** — EVTOL-01 (EC35) shuttling V2 ↔ V1;

plus two medical standby assets (M-UAV-01, M-UAV-02; M600), one of which is the
ground-disruption response resource. Initial occupancy = 2 BUSY / 2 AVAILABLE.

## Q5 — Is geographic alignment proven (not just "two GUIs look alike")?

**Yes.** T1: WGS84 → SUMO x/y → WGS84 Haversine round-trip is exact
(median **0.0000 m**, max **0.0000 m**, thresholds <5 m / <15 m) across the
8 landmarks. Road-snapping displacements are recorded separately (H1 42.9 m,
D1 58.0 m, V3 27.5 m).

Evidence: `outputs/geographic_alignment.csv`,
`reports/GEOGRAPHIC_ALIGNMENT_REPORT.md`, `outputs/unified_ground_air_scene.png`.

## Q6 — Is the master clock synchronized (SUMO == BlueSky == orchestrator)?

**Yes.** A single Python orchestrator drives a 1 s master step; at every logged
timestamp `SUMO time == BlueSky time == orchestrator time`. Over 600 steps the
max clock error was **0.000000 s** (`sync_ok=True` for all rows). T2 PASS.

Evidence: `runs/cosim_smoke_test/clock_sync.csv`.

## Q7 — Does the ground–air co-simulation actually run?

**Yes.** The 600 s smoke test ran end-to-end (SUMO background traffic + D1→H1
route + BlueSky fleet). The two background-service aircraft (L-UAV-01, EVTOL-01)
were continuously moving; M-UAV-02 was dispatched mid-run and flew V2→V1 to
completion. Outputs in `runs/cosim_smoke_test/`:
`ground_state.csv`, `air_state.csv`, `clock_sync.csv`, `events.csv`,
`registry_final.json`, `run_config.yaml`.

## Q8 — Does the cross-layer ground→air event chain work?

**Yes.** At t=300 B1 closes → the hub detects **GROUND_DISRUPTION (GD1)** →
issues a deterministic (non-LLM) **DISPATCH** of the available medical UAV
M-UAV-02 onto a predefined support mission **M-SUPPORT-001 (V2→V1)** → BlueSky
receives the mission change and the UAV flies → **mission COMPLETED at t=410**
(full lifecycle WAITING→ASSIGNED→EN_ROUTE→COMPLETED).

Reverse direction also demonstrated: at t=450 an air-layer failure (F-AIR-001)
marks L-UAV-01 **UNAVAILABLE** and its mission M-L-001 **NEEDS_REPLAN**.

Evidence: `runs/cosim_smoke_test/events.csv`:
```
300  GD1               GROUND_DISRUPTION
300  DISPATCH          ACTION_ISSUED
300  MISSION_STARTED   MISSION
410  MISSION_COMPLETED MISSION
450  F-AIR-001         AIR_EVENT
```

---

## Acceptance summary

| Test | Requirement | Result |
|------|-------------|--------|
| T1 | geographic alignment | PASS |
| T2 | clock sync | PASS |
| T3 | mission lifecycle | PASS |
| T4 | reassignment (optional) | PASS |
| T8 | invalid action rejection | PASS |
| T9 | deterministic replay | PASS |

Full details: `reports/PHASE1_ACCEPTANCE_TESTS.md`.

## STOP condition — confirmed

Reached: **unified testbed + geographic alignment + synchronized SUMO/BlueSky
run + one ground→air cross-layer event.** Deliberately excluded (per scope):
LLM supervision, Experiments 1–4, Monte Carlo, 50-aircraft scale, six-failure
type injection. The testbed is ready to host those next phases.

## Key files

- Config: `config/scenario_config.yaml`
- SUMO: `sim/sumo/` (`network.net.xml`, `routes.rou.xml`, `additional.add.xml`, `canonical.sumocfg`)
- BlueSky: `sim/bluesky/canonical_s0.scn`
- Orchestrator: `orchestrator/` (master clock, adapters, registry, fleet, safety)
- Run artifacts: `runs/cosim_smoke_test/`
- Reports: `reports/` (spec review, environment audit, alignment, acceptance, this report)
