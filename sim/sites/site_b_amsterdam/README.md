# Site B — Amsterdam (water-barrier / bridge-constrained)

| Field | Value |
|---|---|
| site name | site_b_amsterdam |
| city | Amsterdam, Netherlands |
| center | (52.3500, 4.9120) |
| bbox | S 52.3356 / N 52.3644 / W 4.8885 / E 4.9355 |
| area | 3.2 x 3.2 km (10.24 km2) |
| morphology | water-barrier / bridge-constrained urban |
| primary OD | D1 -> H1 (OLVG, locatie Oost) |
| auxiliary ODs | OD-B1: D2 -> H1 ; OD-B2: D1 -> H2 |
| primary B1 | edge `379148751#2` (Berlagebrug over the Amstel; closure ETA +88.69%, detour exists) |
| facilities (primary) | H1 OLVG hospital, D1 municipal industrial facility, V1/V2/V3, B1 |
| facilities (auxiliary) | H2 GZC Amstelkwartier (SE), D2 HEMA Rivierenbuurt (S), C2 Medisch Centrum Oost (NE), V4/V5 synthetic landing nodes |
| OSM source | Overpass (highways extract + water/bridges/POI queries) |
| SUMO network | `sumo/network.net.xml` |
| BlueSky scene | `bluesky/site_b.scn` |
| figures | `figures/site_b_amsterdam_unified_scene_v2.png`, `..._paper.png` |
| validation status | CRS alignment PASS; primary revalidation PASS (eta 127.475 s, B1 +88.69%); spatial utilization improved (hull 2.5% -> 14.7%, grid 2 -> 4 of 9); B1 validity 4/4 PASS (`validation/B1_VALIDATION.md`); **full-scale Experiment-1 ran** (12 scenarios x 20 seeds x B0/B1/B2/B4b + 60 B4a ablation = 1020 runs -> `runs/experiment1_cross_site/site_b_amsterdam`) |

Notes:
- Auxiliary facilities are REAL OSM POIs (ids recorded in
  `config/site_b_amsterdam_config.yaml` under `auxiliary:`); V4/V5 are
  explicitly marked `synthetic experimental facility`.
- Auxiliary ODs are scene/cross-site assets only; they are NOT part of
  frozen Experiment 1 primary metrics.
