# CROSS-SITE CONTROL VARIABLES

Cross-site validation design: what is held fixed vs. what varies across
Site A (Suzhou), Site B (Amsterdam), Site C (Edmonton).

## FIXED (cross-site scientific controls)

| # | Control | Value | Notes |
|---|---------|-------|-------|
| 1 | Study-area extent | 3.2 x 3.2 km (10.24 km2) | identical bbox geometry on all three sites |
| 2 | Ground simulator | SUMO (eclipse-sumo 1.27.1) | same version, same netconvert flags |
| 3 | netconvert pipeline | `--geometry.remove --roundabouts.guess --ramps.guess --junctions.join --tls.guess-signals true --keep-edges.by-vclass passenger --remove-edges.isolated true` | byte-comparable treatment of OSM data |
| 4 | Air simulator | BlueSky (TUDelft) | same repo, same performance models (OpenAP + legacy) |
| 5 | Python Orchestrator | `orchestrator/orchestrator.py` | same master loop, same 1 s master clock |
| 6 | Master step | 1 s | SUMO step == BlueSky step == orchestrator time |
| 7 | Mission semantics | urgent medical / blood delivery, D1 -> H1 | identical across sites |
| 8 | Fleet | L-UAV-01, EVTOL-01 (busy shuttles), M-UAV-01, M-UAV-02 (standby) | identical composition and roles |
| 9 | Facility semantics | H1 hospital/medical, D1 logistics depot, V1/V2 landing sites, V3 backup landing, B1 critical ground disruption | identical registry keys |
| 10 | Disruption schedule | B1 closes at t=300 s, run length 600 s (smoke) | identical timing |
| 11 | Manager versions | frozen (not invoked in this phase) | no manager runs in cross-site construction |
| 12 | Prompt | prompt v2 frozen | untouched |
| 13 | Action Contract | v2 frozen | untouched |
| 14 | Candidate generator | frozen | untouched |
| 15 | B2 objective | frozen | untouched |
| 16 | Metrics | same definitions on all sites (see `cross_site_lib` docstring) | computed by one code path |
| 17 | Fleet size for future validation | identical to Site A unless the user asks otherwise | documented constraint |
| 18 | Site A files | byte-frozen (SHA-256 snapshot in `outputs/cross_site/site_a_freeze_hashes.json`) | verified by CS-T1 |

## VARIABLE (the morphology mechanisms under study)

| # | Variable | Site A | Site B | Site C |
|---|----------|--------|--------|--------|
| 1 | Road-network morphology | meshed / mixed urban | water-barrier constrained | sparse suburban / polycentric |
| 2 | Water barrier | minor canals | major water body (see site config) | none |
| 3 | Facility geometry | compact | separated by barrier | dispersed |
| 4 | Route redundancy | high | low across the barrier | medium-low via dispersion |
| 5 | Path circuity | low | elevated across barrier | elevated via dispersion |
| 6 | Failure mechanism of B1 | single-link bottleneck | water crossing closure | sparse-network bottleneck |

## Operational-scenario realism statement

Amsterdam / Edmonton real OSM networks are used as geographic network
substrates. UAV routes, landing sites, the emergency mission, and failure
injection are experimental / synthetic operational scenarios. This work does
NOT claim that Amsterdam or Edmonton currently operates such a UAV network or
low-altitude service.
