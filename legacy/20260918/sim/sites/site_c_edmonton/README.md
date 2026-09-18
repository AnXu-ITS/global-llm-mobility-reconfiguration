# Site C — Edmonton (sparse suburban / polycentric)

| Field | Value |
|---|---|
| site name | site_c_edmonton |
| city | Edmonton, Alberta, Canada |
| center | (53.4720, -113.4250) |
| bbox | S 53.4576 / N 53.4864 / W -113.4491 / E -113.4009 |
| area | 3.2 x 3.2 km (10.24 km2) |
| morphology | sparse suburban / polycentric (longitudinal + transverse) |
| primary OD | D1 -> H1 (Grey Nuns Community Hospital) |
| auxiliary ODs | OD-C1: C2 -> C3 (west->east, span_x 58%); OD-C2: D2 -> H2 (NW->SE, span_y 77%) |
| primary B1 | edge `471736601#0-AddedOnRampEdge` (closure ETA +34.76%, detour exists) |
| facilities (primary) | H1 Grey Nuns, D1 retail depot (Edge Centre), V1/V2/V3, B1 |
| facilities (auxiliary) | D2 66 Street Plaza (W), H2 Everyday Medical (SE), C2 Kameyosek Shopping Centre (SW), C3 Aspenwood (E), V4/V5 synthetic landing nodes |
| OSM source | Overpass (highways extract + water/bridges/POI queries) |
| SUMO network | `sumo/network.net.xml` |
| BlueSky scene | `bluesky/site_c.scn` |
| figures | `figures/site_c_edmonton_unified_scene_v2.png`, `..._paper.png` |
| validation status | CRS alignment PASS; primary revalidation PASS (eta 230.137 s, B1 +34.76%); transverse routes verified (see `validation/transverse_routes.csv`); B1 validity 4/4 PASS (`validation/B1_VALIDATION.md`); **full-scale Experiment-1 ran** (12 scenarios x 20 seeds x B0/B1/B2/B4b + 60 B4a ablation = 1020 runs -> `runs/experiment1_cross_site/site_c_edmonton`) |

Notes:
- Auxiliary facilities are REAL OSM POIs; V4/V5 are explicitly marked
  `synthetic experimental facility`.
- Both auxiliary ODs have river_dependency = 0 and
  critical_crossing_dependency = False: the transverse structure does NOT
  turn Site C into a bridge-constrained site. (Mill Creek is a culvert-scale
  stream; the auxiliary corridors deliberately stay south of it.)
- Auxiliary ODs are scene/cross-site assets only; NOT part of frozen
  Experiment 1 primary metrics.
