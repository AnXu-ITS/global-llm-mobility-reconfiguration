# CROSS-SITE TESTBED FINAL REPORT

Cross-Site Testbed Construction: Site B (Amsterdam) + Site C (Edmonton).
Frozen Site A (Suzhou, S0_3p2km_v1) untouched -- verified byte-identical
(CS-T1, SHA-256 snapshot in `outputs/cross_site/site_a_freeze_hashes.json`).

---

## 1. Amsterdam final 3.2 x 3.2 km bbox

Candidate **ams_olvg_amstel** (selected; score 105/110):

- center: (52.3500, 4.9120)
- bbox: south=52.3356, north=52.3644, west=4.8885, east=4.9355
- area: 3200.0 m x 3200.0 m (CS-T2 PASS)
- chosen from **11 scored candidates** (outputs/cross_site/amsterdam_candidate_bboxes.csv)

## 2. Why it represents water-barrier / bridge-constrained

The box spans the AMSTEL river between De Pijp (west bank) and OLVG Oost /
Weesperzijde (east bank). Evidence:

- in-area water: 1.05 km2 (Amstel + canal grid); the Amstel polygon does not
  touch the bbox edge (no clipping artifact);
- only **4 usable road crossings of the main barrier** in the whole box,
  versus 73 water-crossing edges overall (the canal grid is dense; the RIVER
  crossings are the scarce resource);
- the selected D1->H1 corridor uses exactly one of them (the Berlagebrug),
  so the network is genuinely crossing-constrained.

## 3. Best crossing disruption (B1_B) ETA increase

- B1_B = SUMO edge `379148751#2` (Berlagebrug deck across the Amstel; OSM
  tags it as embankment, i.e. a real river crossing).
- baseline ETA: 127.48 s (distance 1.12 km)
- after closure: 240.54 s (distance 2.02 km)
- **ETA increase: +88.69%** -> high-severity case (>=40%, approaching 2.0x)
- destination remains reachable; detour exists.

## 4. Detours / alternate crossings after closure

- crossings in box before closure: 4 across the main barrier
- alternative crossings remaining after closing B1_B: 3
- the computed detour reroutes via the next Amstel bridge (25 edges,
  2.02 km); detour boundary share = 0.000 (none of it hugs the bbox edge).

## 5. Edmonton final bbox

Candidate **edm_grey_nuns** (selected; score 68/100; the only candidate whose
H1 is a real acute-care hospital -- the 76-87 point alternatives used
pharmacies / chiropractors / denture clinics as H1):

- center: (53.4720, -113.4250)
- bbox: south=53.4576, north=53.4864, west=-113.4491, east=-113.4009
- area: 3200.0 m x 3200.0 m (CS-T3 PASS)
- chosen from **10 scored candidates** (outputs/cross_site/edmonton_candidate_bboxes.csv)

## 6. Why it represents sparse suburban / polycentric

- H1 = Grey Nuns Community Hospital (real acute-care hospital, OSM way
  427630969; access point on its official address street Youville Drive West
  NW; building centroid 150 m inside the campus -- recorded as
  campus_centroid_offset_m, not a snapping failure);
- D1 = real retail/commercial depot (OSM way 222679705, Edge Centre area,
  46.5 m snap);
- low-degree crescent network: mean degree 2.42 (Site A 2.83), dead-end
  ratio 0.288 (Site A 0.185), road spacing 81 m (Site A 60 m);
- 16 activity POI clusters -> polycentric structure (facility dispersion
  proxy 1.16-1.72 km);
- zero water crossings; B1_C is a plain road link -- the weakness is
  dispersion, not a water bottleneck.

## 7. Site C density vs Site A

| Metric | Site A | Site C | Delta |
|---|---|---|---|
| road density (km/km2) | 19.55 | 18.44 | -5.7% |
| intersection density, >=3-way (/km2) | 38.77 | 40.92 | +5.5% (reported; crescent loops create many 3-way junctions) |
| 4-way intersection density (/km2) | 10.7 | 9.8 | -8.4% |
| dead-end ratio | 0.185 | 0.288 | +56% |
| mean OD circuity | 1.197 | 1.472 | +23% |
| route-redundancy proxy | 0.28 | 0.07 | -75% |
| mean shortest path (km) | 2.09 | 2.26 | +8% |

Overall morphology: clearly more dispersed (5/5 dispersion axes PASS,
CS-T10).

## 8. Site C D1 -> H1 distances

- network distance: **3.43 km** (vs 2.92 km on Site A, +17%)
- euclidean distance: **2.53 km** (vs 1.74 km on Site A, +45%)
- D1->H1 circuity: 1.36

## 9. Three-site morphology metrics

See `outputs/cross_site/site_morphology_comparison.csv` and
`reports/cross_site/NETWORK_MORPHOLOGY_VALIDATION.md` (full table). Summary:

| | Site A Suzhou | Site B Amsterdam | Site C Edmonton |
|---|---|---|---|
| label | meshed / mixed urban | water-barrier / bridge-constrained | sparse suburban / polycentric |
| road density km/km2 | 19.55 | 23.37 | 18.44 |
| intersection density /km2 | 38.77 | 101.76 | 40.92 |
| mean degree | 2.83 | 2.66 | 2.42 |
| dead-end ratio | 0.185 | 0.119 | 0.288 |
| mean OD circuity | 1.197 | 1.141 | 1.472 |
| redundancy proxy | 0.28 | 0.13 | 0.07 |
| D1->H1 net km | 2.92 | 1.12 | 3.43 |
| major barrier | none | Amstel river | none |
| main-barrier crossings | - | 4 | 0 |
| critical-link ETA increase | +37.87% | +88.69% | +34.76% |

## 10. SUMO-BlueSky co-simulation status

Both new sites ran the identical 600-step (1 s master clock) co-simulation
smoke test (no manager, no LLM):

- Site B: runs/site_b_cosim_smoke -- 600 clock rows, **0 sync violations**,
  SUMO ran 45 background vehicles, BlueSky flew the fleet (mission completed
  at t=340).
- Site C: runs/site_c_cosim_smoke -- 600 clock rows, **0 sync violations**,
  mission completed at t=461.
- both runs: 3+ moving aircraft with BlueSky-driven dynamics (CS-T17 PASS).

## 11. Snapping failures (>100 m)?

**None.** Access-point snap distances:

- Site B: H1 (OLVG POI node) 49.9 m, D1 18.2 m
- Site C: H1 (address-street access point) 0.0 m, D1 46.5 m

Note: Grey Nuns' BUILDING CENTROID lies 150 m inside its campus (recorded as
campus_centroid_offset_m=150.0); the facility's routing point is its real
address-street access point, so no snapping failure exists.

## 12. Boundary artifacts?

**None detected.** B1_B crossing margin = 669.7 m (>=300 required); detour
boundary share = 0.000 (<=0.30 required); the Amstel polygon does not touch
the bbox edge. (Other Amsterdam candidates DID show boundary issues --
IJmeer-clipped boxes were penalized/not selected.)

## 13. Are these two sites sufficient for cross-site validation?

**Yes.** The three sites instantiate three quantitatively distinct mechanisms
at identical scale/stack/mission semantics:
- Site A: single-link bottleneck (+37.9%), no water role;
- Site B: river-crossing bottleneck (+88.7%) with forced bridge detour;
- Site C: dispersion penalty (lowest redundancy 0.07, longest OD 3.43 km,
  zero water crossings).
CS-T1..CS-T20: 20 PASS / 0 WARNING / 0 FAIL.

## 14. Best scenarios for reproducing Experiment 1

- Site B: the standard Exp-1 schedule with **B1_B (Berlagebrug) as GD1**
  (t=300 closure) -- same fleet, same 600 s schedule, same deterministic
  smoke action; the +88.7% ground ETA degradation gives the air intervention
  maximal room to matter.
- Site C: the standard Exp-1 schedule with **B1_C as GD1** (+34.8%) -- a
  milder ground-disruption case that stresses whether air reconfiguration
  still pays off under weaker ground degradation.

## 15. Best compound scenarios for limited Exp-3 external validation

- Site B compound: **GD1 (B1_B closure at t=300) + reverse air event
  (t=450)** -- the same compound as Site A, now with the strongest ground
  disruption across all sites.
- Site C compound: **GD1 (B1_C closure) + reverse air event** -- tests the
  compound behavior where the ground penalty comes from dispersion rather
  than a barrier.

## Operational-realism statement

Amsterdam / Edmonton real OSM networks are used as geographic network
substrates. UAV routes, landing sites, the emergency mission and failure
injection are experimental / synthetic operational scenarios. This work does
NOT claim that Amsterdam or Edmonton currently operates such a UAV network
or low-altitude service.

## Artifacts

- SUMO scenes: sim/sites/site_b_amsterdam/sumo/, sim/sites/site_c_edmonton/sumo/
  (area.osm.xml, network.net.xml, routes.rou.xml, additional.add.xml, site.sumocfg)
- BlueSky scenes: sim/sites/site_b_amsterdam/bluesky/site_b.scn,
  sim/sites/site_c_edmonton/bluesky/site_c.scn
- site configs: config/site_b_amsterdam_config.yaml, config/site_c_edmonton_config.yaml
- candidate scores: outputs/cross_site/amsterdam_candidate_bboxes.csv (11),
  outputs/cross_site/edmonton_candidate_bboxes.csv (10)
- alignment: outputs/cross_site/b_geographic_alignment.csv,
  c_geographic_alignment.csv
- morphology: outputs/cross_site/site_morphology_comparison.csv
- figures: outputs/cross_site/site_b_amsterdam_unified_scene.png,
  site_c_edmonton_unified_scene.png, three_site_morphology_comparison.png
- acceptance: outputs/cross_site/acceptance_tests.csv,
  reports/cross_site/CROSS_SITE_ACCEPTANCE_TESTS.md
- run dirs: runs/site_b_cosim_smoke/, runs/site_c_cosim_smoke/
