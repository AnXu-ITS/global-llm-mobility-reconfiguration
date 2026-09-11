# Phase 2 Entry Baseline — Frozen Phase 1 Testbed

**Date:** Phase 2 entry
**Purpose:** Freeze the passing Phase-1 testbed so any later Phase-2 change can be
checked against it. This file records the exact baseline before Phase 2
implementation begins.

> **VCS note:** the working directory is **not** a git repository, so there is no
> commit hash. The baseline is instead frozen by a SHA-256 manifest of the
> authoritative source files (below). Any Phase-2 change that modifies these
> files must be recorded in `CHANGELOG.md`.

---

## 1. Canonical testbed (current — supersedes old spec)

- **Scenario id / version:** `S0` / **`S0_3p2km_v1`** (frozen in `config/scenario_config.yaml`)
- **Study area:** **3.2 km × 3.2 km** = 10.24 km² (NOT reverted to the old 5 km)
- **Center:** 31.30377 N, 120.59981 E (EPSG:4326)
- **Simulators:** SUMO 1.27.1 (TraCI, headless) + BlueSky (in-process, OpenAP) +
  Python master orchestrator, **1 s master clock**.

## 2. bbox

```
south 31.289339293328542   north 31.31820070667146
west  120.58300330305475   east  120.61661669694526
```

## 3. Facilities (WGS84)

| Facility | Type                   | lat         | lon         | SUMO edge        | snap (m) |
|----------|------------------------|-------------|-------------|------------------|----------|
| H1       | hospital               | 31.3108006  | 120.6035449 | -316161555#1     | 42.854   |
| D1       | logistics_depot        | 31.2966529  | 120.5957115 | 621519959        | **58.012** |
| V1       | hospital_landing_site  | 31.3108767  | 120.6039861 | -316161555#1_0   | 0.0      |
| V2       | logistics_hub_landing  | 31.2971716  | 120.5956323 | 621519959_0      | 0.0      |
| V3       | backup_landing_site    | 31.3065604  | 120.6027607 | 793466819#1_0    | 27.48    |
| B1       | disruption_link (high) | 31.2970766  | 120.5985914 | 148377677#0      | 0.0      |
| B2       | disruption_link (med)  | 31.3084362  | 120.6007462 | 538444299#2      | 0.0      |
| B3       | disruption_link (low)  | 31.3018624  | 120.6023145 | 794857408        | 0.0      |

## 4. B1 disruption (current)

- Edge `148377677#0`, impact **high**.
- Base free-flow D1→H1 ETA: **131.84 s**.
- B1-closed detour ETA: **181.76 s** → **+37.87 %** (a second detour 191.21 s also exists).

## 5. Aircraft fleet (current — NOT restored to 12)

| id        | role             | origin | service              | initial status |
|-----------|------------------|--------|----------------------|----------------|
| L-UAV-01  | logistics_uav    | V2     | V2↔V3 logistics      | BUSY (M-L-001) |
| EVTOL-01  | passenger_evtol  | V2     | V2↔V1 passenger      | BUSY (M-P-001) |
| M-UAV-01  | medical_uav      | V1     | standby              | AVAILABLE      |
| M-UAV-02  | medical_uav      | V2     | standby (dispatched) | AVAILABLE      |

Initial occupancy: **2 BUSY / 2 AVAILABLE**.

## 6. Missions (current)

| mission | type              | priority | route   | aircraft     | status      |
|---------|-------------------|----------|---------|--------------|-------------|
| M-L-001 | logistics         | NORMAL   | V2↔V3   | L-UAV-01     | EN_ROUTE    |
| M-P-001 | passenger_transfer| NORMAL   | V2↔V1   | EVTOL-01     | EN_ROUTE    |
| M-SUPPORT-001 | medical_resupply | CRITICAL | V2→V1 | M-UAV-02 | COMPLETED@t=410 (Phase-1 smoke) |

## 7. Phase 1 acceptance result

**9 PASS / 1 WARNING / 0 FAIL.** Full regression re-run at Phase-2 entry (all
exit code 0):

- `test_geographic_alignment.py` — PASS (median 0.0000 m, max 0.0000 m, 8 landmarks)
- `test_acceptance.py` — 5/5 PASS (T2 clock sync, T3 lifecycle, T4 reassign, T8 reject, T9 replay)
- `test_clock_sync_post_resize.py` — PASS (max error 0 steps)
- `test_bluesky_state_provenance.py` — PASS
- `test_feasibility_post_resize.py` — PASS (3/3 infeasible rejected)
- `test_reverse_air_post_resize.py` — PASS
- `test_deterministic_replay_post_resize.py` — PASS (4 CSVs byte-identical)

## 8. Known WARNING

- **D1 road-snap displacement = 58.01 m** (threshold exceeded; the WARNING).
  Recorded, accepted, unchanged in Phase 2.

## 9. Frozen-file SHA-256 manifest (baseline)

| file | SHA-256 |
|------|---------|
| config/scenario_config.yaml | 7E3282A5123A8B301644052323BD0EDFA87E90E38D0F70D027F28D06CA98BEAD |
| orchestrator/orchestrator.py | EFC0B6A6E478FB354AFE0304456F54B0989C0D8E0A30141D7EAD775E4B1177A8 |
| orchestrator/registry.py | BB64F05A33CD87B034D8834FDA18E282AEA73EB315722AA005A06BFA97C26134 |
| orchestrator/fleet.py | B706CC1B6560A3FB08987F18168667D45ECAEFD70C4182A1641BFCF28DE2D030 |
| orchestrator/config.py | 6F0FEDDDECABB93834805770840FB81312DF2A93A9A7E86BCAE3A580E03CA08A |
| orchestrator/bluesky_adapter.py | DF066D6F5E21A645F633C3B01E0BD499E3D8F03822886F912EB1115D44B18278 |
| orchestrator/sumo_adapter.py | 956B3772DB2F8FC8A8A4DBFA271A1523B29C9CB7FE950068F408B582B1948BFB |
| orchestrator/geo.py | BB554C570A101923B0B1C222B5BA2A4336D7B61CC0CD40C35AB19A2ED99C2502 |
| safety/feasibility_checker.py | BFEA8A6D309AAFB2989EF6A9FBFA545EB028DE49D244EB2B448A0164FB4F24A3 |
| sim/bluesky/canonical_s0.scn | B57DA4038E34A5315A3DBA3B94F4BC2ED2670B616893FE298CC843F6E1B7908C |
| sim/sumo/canonical.sumocfg | 25B62EEBD7E560F9B1B2EAFD1AD75C0E4D22B74F88682E6694BEEB197D6FF032 |
| sim/sumo/routes.rou.xml | BE80DF7B27DA7C42956B7F0ED4A60B43FDE7C9CAE5195731B6945D0474E6199C |

*(`config/scenario_config.yaml` is the frozen post-edit version with
`scenario_version: S0_3p2km_v1` + `phase2:` block.)*

## 10. Phase-1 replay guarantee

The Phase-1 `orchestrator/orchestrator.py` deterministic-dispatch path is left
untouched. Phase 2 adds a separate orchestrator (`orchestrator/phase2_orchestrator.py`)
and only **additively** extends `safety/feasibility_checker.py` with new action
types (`GROUND_FALLBACK` / `DELAY` / `CANCEL`). Phase-1 regression remains green
(§7 above).
