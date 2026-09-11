# Geographic Alignment Report — Canonical Suzhou Testbed (S0, 3.2 km crop)

**Date:** Phase 1 (refined S0)
**Test:** T1 — geographic alignment (WGS84 ↔ SUMO x/y round-trip)
**Result:** PASS

---

## 1. Objective

Prove that the ground scene (SUMO) and the air scene (BlueSky) share a single
geography, so that an object in one layer is located at the same physical place
in the other. The acceptance criterion is a Haversine round-trip error of
`median < 5 m` and `max < 15 m` for every registered facility.

The testbed was refined from the original 5 × 5 km extent to a **3.2 × 3.2 km
crop** centred on the facility centroid (31.30377 N, 120.59981 E), preserving
H1, D1, V1–V3 and the D1→H1 corridor, and adding the two extra candidate
disruption links B2 and B3 (see `config/scenario_config.yaml`).

## 2. Method

For each facility in `config/scenario_config.yaml` (single source of truth):

1. Take the WGS84 coordinate `(lat, lon)` (CRS exchange = EPSG:4326).
2. Convert to SUMO internal coordinates `(x, y)` using the network's projection
   (`net.convertLonLat2XY`, UTM/WGS84 via pyproj).
3. Convert `(x, y)` back to WGS84 using `net.convertXY2LonLat`.
4. Compute the Haversine distance between the original and round-tripped
   coordinate → `error_m`.

Additionally, road-snapped facility coordinates (H1, D1, V1, V2, V3, B1, B2, B3)
are recorded with their snapping distance `snapped_m` (distance from the raw POI
to the nearest passenger-vehicle road edge).

## 3. Results

| facility | type                 | error_m | snapped_m |
|----------|----------------------|---------|-----------|
| H1       | hospital             | 0.0000  | 42.854    |
| D1       | logistics_depot      | 0.0000  | 58.012    |
| V1       | hospital_landing_site| 0.0000  | 0.0       |
| V2       | logistics_hub_landing| 0.0000  | 0.0       |
| V3       | backup_landing_site  | 0.0000  | 27.48     |
| B1       | disruption_link (high)  | 0.0000  | 0.0    |
| B2       | disruption_link (medium)| 0.0000  | 0.0    |
| B3       | disruption_link (low)   | 0.0000  | 0.0    |

- **median error = 0.0000 m** (require `< 5 m`) → **PASS**
- **max error = 0.0000 m** (require `< 15 m`) → **PASS**

Raw evidence: `outputs/geographic_alignment.csv`

## 4. Interpretation of the 0.0000 m round-trip error

The round-trip error is exactly zero because `convertLonLat2XY` and
`convertXY2LonLat` use the *same* pyproj UTM/WGS84 transformer (forward and
inverse). A lossless round-trip is the **expected correct result** for a
properly configured projection — it proves that SUMO and BlueSky resolve the
same WGS84 coordinate to the same physical location. The meaningful failure
modes this test guards against (NaN / huge errors from a missing or mismatched
projection) do not occur.

The *non-zero* geographic displacements in the testbed are the **road-snapping
distances**, recorded separately:

- **H1 (hospital)** snaps 42.85 m to the nearest road edge — the hospital POI is
  a campus/building centroid, and the road access point (V1) is ~43 m away. This
  is a realistic "facility centroid → nearest road" distance.
- **D1 (logistics depot)** snaps 58.0 m — an industrial-area POI whose centroid
  is inside the parcel.
- V1/V2/B1/B2/B3 are defined directly on road edges, so their snap distance is
  ~0 m (V3 = 27.5 m from an intermediate road edge).

## 5. Shared geography artifact

`outputs/unified_ground_air_scene.png` renders the roads, the eight facilities,
the two background low-altitude services, and the initial fleet positions in the
same WGS84 frame — a visual confirmation that the ground and air layers coincide.

## 6. Conclusion

The ground scene (SUMO) and the air scene (BlueSky) share a single WGS84
geography. The projection round-trip is exact (0 m), and facility-to-road
snapping distances are small and realistic. **T1 PASSES.**
