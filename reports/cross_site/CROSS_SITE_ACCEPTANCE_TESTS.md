# CROSS-SITE ACCEPTANCE TESTS (CS-T1 .. CS-T20)

Summary: **20 PASS / 0 WARNING / 0 FAIL**

| Test | Description | Status | Evidence |
|---|---|---|---|
| CS-T1 | Site A unchanged (8 frozen files byte-identical) | **PASS** | all 8 frozen Site A files byte-identical |
| CS-T2 | Site B = 3.2 x 3.2 km | **PASS** | 3200.0 m x 3200.0 m |
| CS-T3 | Site C = 3.2 x 3.2 km | **PASS** | 3200.0 m x 3200.0 m |
| CS-T4 | Amsterdam bbox selected from >=5 candidates | **PASS** | 11 candidates |
| CS-T5 | Edmonton bbox selected from >=5 candidates | **PASS** | 10 candidates |
| CS-T6 | Site B has genuine water/crossing constraint | **PASS** | B1=379148751#2 kind=embankment water=1.05 km2 main_crossings=4 |
| CS-T7 | Site B critical crossing closure has detour | **PASS** | detour=True (25 edges) |
| CS-T8 | Site B ETA increase >=25% | **PASS** | 88.69% (>=40% preferred) |
| CS-T9 | Site B not bbox-boundary artifact | **PASS** | margin=670 m detour_boundary_share=0.000 |
| CS-T10 | Site C lower-density / more dispersed than Site A | **PASS** | road 18.439 vs 19.547 km/km2; intersections 40.918 vs 38.77 /km2 (reported); dead-ends 0.2882 vs 0.1845; circuity 1.4721 vs 1.1969; D1->H1 3.4296 vs 2.9222 km (5/5 dispersion axes) |
| CS-T11 | Site C not dominated by river/bridge dependency | **PASS** | B1 crossing=False baseline crossings=0 |
| CS-T12 | Facilities geographically valid (real POI, snap<=100m) | **PASS** | B: H1=OLVG, locatie Oost snap=49.918m, D1=222679705 snap=46.503m |
| CS-T13 | CRS alignment PASS for Site B | **PASS** | median=0.000 m max=0.000 m |
| CS-T14 | CRS alignment PASS for Site C | **PASS** | median=0.000 m max=0.000 m |
| CS-T15 | SUMO/BlueSky clocks sync for Site B (600 steps, 0 errors) | **PASS** | 600 rows, 0 violations |
| CS-T16 | SUMO/BlueSky clocks sync for Site C (600 steps, 0 errors) | **PASS** | 600 rows, 0 violations |
| CS-T17 | BlueSky dynamics provenance confirmed in Site B/C | **PASS** | B: 3 moving aircraft, C: 3 moving aircraft |
| CS-T18 | Three-site morphology metrics generated | **PASS** | 3 sites, 20 columns |
| CS-T19 | Site type labels supported by quantitative evidence | **PASS** | B=water-constrained (crossings>=2, B1=crossing); C=sparse (no crossing B1, density<Site A) |
| CS-T20 | No manager experiments run (deterministic smoke only) | **PASS** | B manager=deterministic_smoke_test_action llm=None manager_files=0; C manager=deterministic_smoke_test_action llm=None manager_files=0 |

Notes:
- CS-T1 compares SHA-256 hashes of the 8 frozen Site A files against the
  snapshot recorded at the start of the cross-site phase.
- CS-T9 boundary-artifact rule: the closed crossing must sit >=300 m from
  the bbox edge AND the detour must keep <=30% of its length inside the
  150 m boundary band.
- CS-T17: an aircraft counts as moving when its WGS84 position changes by
  >0.001 deg (~100 m) between t=0 and t=600.
- CS-T20: manager field in run_config.yaml is the deterministic smoke-test
  action; no LLM model configured; no manager/LLM artifacts in run dirs.
