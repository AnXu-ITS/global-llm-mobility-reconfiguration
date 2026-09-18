# Site A — Suzhou (frozen primary testbed)

| Field | Value |
|---|---|
| site name | site_a_suzhou |
| city | Suzhou, China |
| center | (31.30377, 120.59981) |
| bbox | S 31.2893 / N 31.3182 / W 120.5830 / E 120.6166 |
| area | 3.2 x 3.2 km (10.24 km2) |
| morphology | meshed / mixed urban |
| primary OD | D1 -> H1 (urgent medical / blood delivery) |
| auxiliary ODs | none |
| primary B1 | edge `148377677#0` (closure ETA +37.87%, detour exists) |
| facilities | H1 苏州慈济门诊部 (hospital), D1 logistics depot, V1/V2/V3 landing sites, B1 disruption |
| OSM source | Overpass /api/map full extract (frozen `area.osm.xml`) |
| SUMO network | `sumo/network.net.xml` (eclipse-sumo 1.27.1, Site A flags) |
| BlueSky scene | `bluesky/canonical_s0.scn` |
| figures | `figures/site_a_suzhou_unified_scene_v2.png`, `..._paper.png` |
| validation status | frozen; byte-identical to canonical source (SHA-256 verified); CRS alignment PASS |

Notes:
- This directory is a COPY of the frozen canonical site
  (`sim/sumo`, `sim/bluesky`, `config/scenario_config.yaml`). The frozen
  originals remain the Experiment-1 sources and were NOT modified.
- `osm/water_osm.json` and `routes/primary.json` are DERIVED read-only
  analyses generated for plotting/validation; the underlying network data is
  untouched.
