# NETWORK MORPHOLOGY VALIDATION (Cross-Site)

Quantitative evidence that Site A / B / C instantiate three DIFFERENT network
morphology mechanisms. All metrics below come from a single code path
(`tools/cross_site_lib.py::metrics_from_net`, definitions in its docstring).

## Metric definitions

| Metric | Definition |
|--------|-----------|
| road_length_km | sum of directional passenger-edge lengths (a two-way road counts twice) |
| road_density_km_per_km2 | road_length_km / 10.24 |
| node_count / edge_count | SUMO junctions / directional passenger edges |
| intersection_density | junctions with >=3 distinct neighbours per km2 |
| mean_node_degree | mean number of distinct neighbouring junctions |
| dead_end_ratio | junctions with exactly 1 neighbour / all junctions |
| mean/median shortest path | 200 deterministic OD pairs (largest component, euclid >=200 m), length-weighted |
| mean_od_circuity | mean(network_km / euclidean_km) over the sampled pairs |
| route redundancy proxy | over 60 pairs: fraction where EVERY single-edge closure of the baseline path still admits a detour within 1.5x baseline length |
| road_spacing_proxy_m | median nearest-neighbour distance between intersections |
| usable_crossing_count | passenger edges whose geometry crosses an in-area water body (OSM bridge/tunnel/embankment tag kept as metadata) |
| boundary-artifact rule | closed crossing must sit >=300 m from the bbox edge AND the detour must keep <=30% of its length inside the 150 m boundary band; the main water body must not touch the bbox edge |

## Three-site comparison (outputs/cross_site/site_morphology_comparison.csv)

| Metric | Site A (Suzhou) | Site B (Amsterdam) | Site C (Edmonton) |
|---|---|---|---|
| area_km2 | 10.24 | 10.24 | 10.24 |
| road_density_km_per_km2 | 19.55 | 23.37 | 18.44 |
| intersection_density (>=3-way) /km2 | 38.77 | 101.76 | 40.92 |
| 4-way intersection density /km2 | 10.7 | (high, dense grid) | 9.8 |
| mean_node_degree | 2.83 | 2.66 | 2.42 |
| dead_end_ratio | 0.185 | 0.119 | 0.288 |
| mean_shortest_path_km | 2.09 | 1.69 | 2.26 |
| mean_od_circuity | 1.197 | 1.141 | 1.472 |
| route_redundancy_proxy | 0.28 | 0.13 | 0.07 |
| road_spacing_proxy_m | 60.5 | (dense) | 81 |
| D1->H1 network km | 2.92 | 1.12 | 3.43 |
| D1->H1 euclidean km | 1.74 | 0.72 | 2.53 |
| D1->H1 circuity | 1.68 | 1.54 | 1.36 |
| major_barrier_type | none | water (Amstel river) | none |
| usable_crossing_count (all water) | 0 | 73 (4 across main barrier) | 0 |
| critical-link ETA increase | +37.87% (B1) | +88.69% (B1_B) | +34.76% (B1_C) |
| detour_exists | true | true | true |

## Why Site B is NOT just another dense urban site

Site B (Amsterdam, OLVG/Amstel box) is, by raw density (road 23.4 km/km2,
intersections 101.8/km2), the DENSEST of the three sites. Yet its
failure mechanism is not density:

1. **A real river barrier**: the Amstel crosses the box north-south; 1.05 km2
   of in-area water; the barrier polygon does NOT touch the bbox edge.
2. **Limited crossings**: only 4 usable road crossings of the main barrier in
   the whole 3.2x3.2 km box (Berlagebrug, Nieuwe Amstelbrug, Torontobrug and
   one more), versus 73 total water crossings once the canal grid is included
   -- the AMSTEL is the scarce resource, not the canals.
3. **Crossing dependency**: B1_B = the Berlagebrug deck edge (OSM way
   379148751, tagged as embankment in OSM but a genuine river crossing). Its
   closure removes the only crossing on the D1->H1 corridor and the ETA jumps
   from 127.5 s to 240.5 s (+88.69%), while the destination stays reachable
   via the next bridge downstream (detour 2.02 km, 25 edges).
4. **No boundary artifact**: the closed crossing sits 670 m from the bbox
   edge; 0% of the detour runs inside the 150 m boundary band.
5. **Real facilities on both banks**: H1 = OLVG, locatie Oost (acute-care
   hospital, OSM node 26989989) on the east bank; D1 = a real landuse-
   industrial facility (OSM way 268998855) on the west bank.

Density in Site B is therefore a CONTEXT property (inner-city canal grid),
while the identified disruption mechanism is the river-barrier crossing --
quantitatively distinct from Site A (+37.9%) and from any "dense urban"
reading.

## Why Site C is NOT another bridge-constrained site

Site C (Edmonton, Grey Nuns/Mill Woods box) has:

1. **No water bottleneck**: 0.05 km2 of in-area water (small ponds), ZERO
   usable road-water crossings, and the D1->H1 baseline route crosses NO
   water at all.
2. **B1_C is a plain road link** (collector/ramp connection edge
   471736601#0-AddedOnRampEdge), not a bridge: `is_water_crossing = False`.
3. **The failure mechanism is dispersion**: the closure of a single ordinary
   link raises the ETA from 230.1 s to 310.1 s (+34.76%) because the
   alternatives are long, low-redundancy collectors -- the route-redundancy
   proxy is 0.07 (Site A: 0.28), the dead-end ratio is 0.288 (Site A:
   0.185), and mean OD circuity is 1.47 (Site A: 1.20).

## Why A / B / C represent three different morphology mechanisms

| Site | Label | Mechanism |
|---|---|---|
| A (Suzhou) | Meshed / Mixed Urban | moderate density, mixed grid, one mid-impact single-link bottleneck (+37.9%), no water role |
| B (Amsterdam) | Water-Barrier / Bridge-Constrained | dense canal city where the AMSTEL's 4 crossings gate east-west ground access; one crossing closure = +88.7% ETA with a forced river detour |
| C (Edmonton) | Sparse Suburban / Polycentric | low-degree crescent network, 28.8% dead ends, lowest redundancy (0.07), longest dispersed OD (3.43 km), zero water crossings |

The three mechanisms are distinguished by WHERE the ground-network weakness
comes from: a single link (A), a water crossing (B), or spatial dispersion
(C) -- verified quantitatively, not by city name.
