# SITE DATA INVENTORY (sim/sites)

Audit of the three canonical sites as consolidated under `sim/sites/`.
All paths below are relative to the project root.

## Site A — site_a_suzhou

| Item | Value |
|---|---|
| bbox | S 31.2893 / N 31.3182 / W 120.5830 / E 120.6166 |
| center | (31.30377, 120.59981) |
| OSM source | Overpass /api/map full extract (frozen); `site_a_suzhou/osm/area.osm.xml` |
| SUMO network | `site_a_suzhou/sumo/network.net.xml` (COPY of frozen `sim/sumo/network.net.xml`) |
| BlueSky scene | `site_a_suzhou/bluesky/canonical_s0.scn` (COPY of frozen `sim/bluesky/canonical_s0.scn`) |
| facility registry | `site_a_suzhou/facilities/registry.json` (derived, read-only) |
| routes | `site_a_suzhou/routes/primary.json` (derived TraCI baseline+detour, read-only) |
| disruption edge | B1 = `148377677#0` (ETA +37.87%) |
| alignment data | `site_a_suzhou/validation/geographic_alignment_detailed.csv` (COPY) |
| morphology data | `comparison/site_morphology_comparison.csv` (row `site_a_suzhou`) |
| figures | `site_a_suzhou/figures/site_a_suzhou_unified_scene_v2.png`, `..._paper.png` |
| configs | `site_a_suzhou/config/scenario_config.yaml` (COPY of frozen `config/scenario_config.yaml`) |
| scripts depending on old path | `orchestrator/*` (frozen Exp-1 replay; READ ONLY, not rewritten), `tools/build_sumo_scene.py`, `tools/build_bluesky_scene.py`, `tools/geo_alignment_detailed.py`, `tools/select_disruptions.py` (all still reference `sim/sumo` / `sim/bluesky` — legacy, kept for Exp-1 replay) |

## Site B — site_b_amsterdam

| Item | Value |
|---|---|
| bbox | S 52.3356 / N 52.3644 / W 4.8885 / E 4.9355 |
| center | (52.3500, 4.9120) |
| OSM source | Overpass QL (highways) + water/bridges/POI queries; `site_b_amsterdam/osm/` |
| SUMO network | `site_b_amsterdam/sumo/network.net.xml` |
| BlueSky scene | `site_b_amsterdam/bluesky/site_b.scn` (regenerated with auxiliary landmarks) |
| facility registry | `site_b_amsterdam/facilities/registry.json` (primary + auxiliary) |
| routes | `site_b_amsterdam/routes/primary.json`, `routes/auxiliary.json` (OD-B1, OD-B2) |
| disruption edge | B1 = `379148751#2` (Berlagebrug; ETA +88.69%, detour) |
| alignment data | `site_b_amsterdam/validation/geographic_alignment.csv` |
| morphology data | `comparison/site_morphology_comparison.csv` (row `site_b_amsterdam`) |
| spatial utilization | `site_b_amsterdam/validation/spatial_utilization.csv` (before/after) |
| figures | `site_b_amsterdam/figures/site_b_amsterdam_unified_scene_v2.png`, `..._paper.png` |
| configs | `site_b_amsterdam/config/site_b_amsterdam_config.yaml` (canonical, incl. `auxiliary:` section; primary identical to legacy `config/site_b_amsterdam_config.yaml`) |
| scripts depending on old path | `tools/cross_site_build.py`, `tools/cross_site_candidates.py` (construction-stage; legacy paths recorded, canonical data in sim/sites) |

## Site C — site_c_edmonton

| Item | Value |
|---|---|
| bbox | S 53.4576 / N 53.4864 / W -113.4491 / E -113.4009 |
| center | (53.4720, -113.4250) |
| OSM source | Overpass QL (highways) + water/bridges/POI queries; `site_c_edmonton/osm/` |
| SUMO network | `site_c_edmonton/sumo/network.net.xml` |
| BlueSky scene | `site_c_edmonton/bluesky/site_c.scn` (regenerated with auxiliary landmarks) |
| facility registry | `site_c_edmonton/facilities/registry.json` (primary + auxiliary) |
| routes | `site_c_edmonton/routes/primary.json`, `routes/auxiliary.json` (OD-C1, OD-C2) |
| disruption edge | B1 = `471736601#0-AddedOnRampEdge` (ETA +34.76%, detour) |
| alignment data | `site_c_edmonton/validation/geographic_alignment.csv` |
| morphology data | `comparison/site_morphology_comparison.csv` (row `site_c_edmonton`) |
| transverse routes | `site_c_edmonton/validation/transverse_routes.csv` |
| spatial utilization | `site_c_edmonton/validation/spatial_utilization.csv` (before/after) |
| figures | `site_c_edmonton/figures/site_c_edmonton_unified_scene_v2.png`, `..._paper.png` |
| configs | `site_c_edmonton/config/site_c_edmonton_config.yaml` (canonical, incl. `auxiliary:` section; primary identical to legacy `config/site_c_edmonton_config.yaml`) |
| scripts depending on old path | `tools/cross_site_build.py`, `tools/cross_site_candidates.py` (construction-stage; legacy paths recorded) |

## comparison/

| Item | Path |
|---|---|
| morphology comparison | `sim/sites/comparison/site_morphology_comparison.csv` |
| unified plotter | `sim/sites/comparison/plot_three_sites.py` |
| three-site figure (debug) | `sim/sites/comparison/three_site_cross_validation_v2.png` |
| three-site figure (paper) | `sim/sites/comparison/three_site_cross_validation_paper.png` / `.pdf` |
| visual QA | `sim/sites/comparison/visual_qa.json`, `plot_qa.json` |
| image acceptance | `sim/sites/comparison/image_acceptance_tests.csv` / `.md` |
| inventory / audit / final report | `SITE_DATA_INVENTORY.md`, `LEGACY_SITE_PATH_AUDIT.md`, `SITE_REFINEMENT_FINAL_REPORT.md` |

## Global manifest

`sim/sites/sites_manifest.yaml` — roles, morphologies, primary/auxiliary ODs,
and per-site config/SUMO/BlueSky/figure paths.
