# LEGACY SITE PATH AUDIT

Old project paths vs the canonical sim/sites tree.

| OLD PATH | NEW CANONICAL PATH | STATUS |
|---|---|---|
| config\scenario_config.yaml | sim\sites\site_a_suzhou\config\scenario_config.yaml | COPY (frozen content) |
| sim\sumo\area.osm.xml | sim\sites\site_a_suzhou\osm\area.osm.xml | COPY |
| sim\sumo\osm_pois.json | sim\sites\site_a_suzhou\osm\osm_pois.json | COPY |
| sim\sumo\network.net.xml | sim\sites\site_a_suzhou\sumo\network.net.xml | COPY |
| sim\sumo\routes.rou.xml | sim\sites\site_a_suzhou\sumo\routes.rou.xml | COPY |
| sim\sumo\additional.add.xml | sim\sites\site_a_suzhou\sumo\additional.add.xml | COPY |
| sim\sumo\canonical.sumocfg | sim\sites\site_a_suzhou\sumo\canonical.sumocfg | COPY |
| sim\bluesky\canonical_s0.scn | sim\sites\site_a_suzhou\bluesky\canonical_s0.scn | COPY |
| outputs\geographic_alignment_detailed.csv | sim\sites\site_a_suzhou\validation\geographic_alignment_detailed.csv | COPY |
| outputs\geographic_alignment_detailed.csv | sim\sites\site_a_suzhou\validation\geographic_alignment_detailed.csv | COPY |
| reports\validation\B1_POST_RESIZE_VALIDATION.md | sim\sites\site_a_suzhou\validation\B1_POST_RESIZE_VALIDATION.md | COPY |
| sim\sites\site_b_amsterdam\sumo\area.osm.xml | sim\sites\site_b_amsterdam\osm\area.osm.xml | MOVED (canonical) |
| sim\sites\site_b_amsterdam\sumo\osm_pois.json | sim\sites\site_b_amsterdam\osm\osm_pois.json | MOVED (canonical) |
| sim\sites\site_b_amsterdam\sumo\water_osm.json | sim\sites\site_b_amsterdam\osm\water_osm.json | MOVED (canonical) |
| sim\sites\site_b_amsterdam\sumo\bridges_osm.json | sim\sites\site_b_amsterdam\osm\bridges_osm.json | MOVED (canonical) |
| sim/sites/site_b_amsterdam/sumo/network.net.xml | sim/sites/site_b_amsterdam/sumo/network.net.xml | KEPT (canonical) |
| sim/sites/site_b_amsterdam/sumo/routes.rou.xml | sim/sites/site_b_amsterdam/sumo/routes.rou.xml | KEPT (canonical) |
| sim/sites/site_b_amsterdam/sumo/site.sumocfg | sim/sites/site_b_amsterdam/sumo/site.sumocfg | KEPT (canonical) |
| config/site_b_amsterdam_config.yaml | sim/sites/site_b_amsterdam/config/site_b_amsterdam_config.yaml | COPY + auxiliary extension (primary identical) |
| sim/sites/site_b_amsterdam/sumo/additional.add.xml (old) | sim/sites/site_b_amsterdam/sumo/additional.add.xml | REGENERATED with auxiliary POIs (primary POIs identical) |
| sim/sites/site_b_amsterdam/bluesky/site_b.scn (old) | sim/sites/site_b_amsterdam/bluesky/site_b.scn | REGENERATED with auxiliary landmarks (primary fleet identical) |
| outputs\cross_site\refinement\site_b_amsterdam\spatial_utilization.csv | sim\sites\site_b_amsterdam\validation\spatial_utilization.csv | COPY (refinement) |
| outputs\cross_site\refinement\site_b_amsterdam\od_routes.csv | sim\sites\site_b_amsterdam\validation\od_routes.csv | COPY (refinement) |
| outputs\cross_site\b_geographic_alignment.csv | sim\sites\site_b_amsterdam\validation\geographic_alignment.csv | COPY |
| sim\sites\site_c_edmonton\sumo\area.osm.xml | sim\sites\site_c_edmonton\osm\area.osm.xml | MOVED (canonical) |
| sim\sites\site_c_edmonton\sumo\osm_pois.json | sim\sites\site_c_edmonton\osm\osm_pois.json | MOVED (canonical) |
| sim\sites\site_c_edmonton\sumo\water_osm.json | sim\sites\site_c_edmonton\osm\water_osm.json | MOVED (canonical) |
| sim\sites\site_c_edmonton\sumo\bridges_osm.json | sim\sites\site_c_edmonton\osm\bridges_osm.json | MOVED (canonical) |
| sim/sites/site_c_edmonton/sumo/network.net.xml | sim/sites/site_c_edmonton/sumo/network.net.xml | KEPT (canonical) |
| sim/sites/site_c_edmonton/sumo/routes.rou.xml | sim/sites/site_c_edmonton/sumo/routes.rou.xml | KEPT (canonical) |
| sim/sites/site_c_edmonton/sumo/site.sumocfg | sim/sites/site_c_edmonton/sumo/site.sumocfg | KEPT (canonical) |
| config/site_c_edmonton_config.yaml | sim/sites/site_c_edmonton/config/site_c_edmonton_config.yaml | COPY + auxiliary extension (primary identical) |
| sim/sites/site_c_edmonton/sumo/additional.add.xml (old) | sim/sites/site_c_edmonton/sumo/additional.add.xml | REGENERATED with auxiliary POIs (primary POIs identical) |
| sim/sites/site_c_edmonton/bluesky/site_c.scn (old) | sim/sites/site_c_edmonton/bluesky/site_c.scn | REGENERATED with auxiliary landmarks (primary fleet identical) |
| outputs\cross_site\refinement\site_c_edmonton\spatial_utilization.csv | sim\sites\site_c_edmonton\validation\spatial_utilization.csv | COPY (refinement) |
| outputs\cross_site\refinement\site_c_edmonton\transverse_routes.csv | sim\sites\site_c_edmonton\validation\transverse_routes.csv | COPY (refinement) |
| outputs\cross_site\c_geographic_alignment.csv | sim\sites\site_c_edmonton\validation\geographic_alignment.csv | COPY |
| outputs\cross_site\site_morphology_comparison.csv | sim\sites\comparison\site_morphology_comparison.csv | COPY |

Notes:
- Site A frozen files were COPIED (originals remain the frozen
  experiment-1 sources); SHA-256 verified.
- outputs/cross_site/ remains as the construction-stage work area
  (legacy); canonical scene data lives under sim/sites/.
- Frozen Exp-1 replay paths (sim/sumo, sim/bluesky,
  config/scenario_config.yaml) are untouched.
