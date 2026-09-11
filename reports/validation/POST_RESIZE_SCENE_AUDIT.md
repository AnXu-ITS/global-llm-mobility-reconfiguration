# Post-Resize Scene Audit (S0 → 3.2 km crop)

Date: 2024-06-01 (deterministic smoke-test seed) · Scenario `S0`

## 1. Inputs read

- `Research Plan.md` — research boundary unchanged (sparse low-altitude mobility as
  a scarce urban-resilience layer; LLM is a supervisory *manager*, not a pilot).
- `ground_air_llm_experiment_plan.md` — RQ1/RQ2/RQ3; no LLM in this validation phase.
- `EXPERIMENT_IMPLEMENTATION_SPEC.md` — normative reference (still documents the
  pre-crop 5 km × 5 km / 12-aircraft definition; see §7 deviation note below).
- `config/scenario_config.yaml` — single source of truth (current).
- `sim/sumo/canonical.sumocfg` + `sim/bluesky/canonical_s0.scn` — current scenes.
- `CHANGELOG.md` — refinement history.

## 2. Current geometry

| Field | Value |
|-------|-------|
| center (WGS84) | (31.30377 N, 120.59981 E) = facility centroid |
| width × height | 3.2 km × 3.2 km |
| **area** | **10.24 km²** (was 25.0 km²) |
| bbox south / north | 31.2893393 / 31.3182007 |
| bbox west / east | 120.5830033 / 120.6166167 |
| CRS exchange | EPSG:4326 (WGS84, shared ground/air) |

## 3. Facility containment (all must be inside bbox)

| Facility | Lat | Lon | Inside bbox |
|----------|-----|-----|-------------|
| H1 (hospital) | 31.3108006 | 120.6035449 | ✅ PASS |
| D1 (depot) | 31.2966529 | 120.5957115 | ✅ PASS |
| V1 (hospital landing) | 31.3108767 | 120.6039862 | ✅ PASS |
| V2 (logistics hub) | 31.2971716 | 120.5956323 | ✅ PASS |
| V3 (backup landing) | 31.3065604 | 120.6027607 | ✅ PASS |
| B1 (disruption, high) | 31.2970766 | 120.5985915 | ✅ PASS |
| B2 (disruption, medium) | 31.3084362 | 120.6007462 | ✅ PASS |
| B3 (disruption, low) | 31.3018624 | 120.6023145 | ✅ PASS |

**All 8 facilities are inside the cropped bbox.**

## 4. B1 critical ground corridor

- B1 = SUMO edge `148377677#0`, located **on the D1→H1 baseline route**
  (`b1_on_baseline_route = True`, verified with sumolib shortest path).
- B1 is **interior** to the bbox: minimum distance to any bbox side = **860.3 m**
  (no artificial crop-boundary effect).
- B1 is **byte-identical** to the pre-crop 5×5 bottleneck edge (same TraCI corridor).

## 5. BlueSky air routes inside canonical area

| Service | Route | Endpoints inside bbox |
|---------|-------|-----------------------|
| logistics_service (L-UAV-01) | V2 ↔ V3 | ✅ |
| passenger_service (EVTOL-01) | V2 ↔ V1 | ✅ |
| medical standby M-UAV-01 | V1 | ✅ |
| medical standby M-UAV-02 | V2 | ✅ |

All air routes and initial aircraft positions fall inside the cropped bbox.

## 6. Old-coordinate residue check

| Source | Finding |
|--------|---------|
| Active code/config (`config/`, `orchestrator/`, `tools/`, `sim/`) | **No** pre-crop bbox corners (31.27745/31.32255/120.57374/120.62626) or 5 km values |
| `EXPERIMENT_IMPLEMENTATION_SPEC.md` §7.2 | still says 5 km × 5 km, center 31.3000/120.6000, 12 aircraft → **normative doc, NOT active config** (documented deviation) |
| `reports/PHASE1_SPEC_REVIEW.md` | historical spec-review text (not code) |
| `tools/{fetch_osm,build_sumo_scene}.py` | comment `"refined from 5x5 km"` (intentional annotation) |
| `sim/sumo/area.osm.xml`, `osm_pois.json` | raw OSM node coordinates near 31.3 N (real map data, not residue) |
| `runs/*/air_state.csv` | aircraft positions near (31.30, 120.60) are **inside** the new bbox (not residue) |

## 7. Verdict

**PASS** — the cropped SUMO and BlueSky scenes describe the same WGS84 geography;
no active old-coordinate residue; the only pre-crop references live in the
normative spec and historical reports (intentional, documented in CHANGELOG).
