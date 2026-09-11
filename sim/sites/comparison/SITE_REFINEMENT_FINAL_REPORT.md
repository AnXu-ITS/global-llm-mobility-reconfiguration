# SITE REFINEMENT FINAL REPORT

Three-site scene refinement + directory consolidation.
Frozen Experiment 1 (Site A, managers, prompt, B2, candidate generator)
untouched — verified by SHA-256.

## 1. Site B new remote facilities

| Key | Facility | OSM id | Location | Snap |
|---|---|---|---|---|
| H2 | GZC Amstelkwartier (health centre) | 4763328999 | south-east quadrant | 17.1 m |
| D2 | HEMA (retail, Rivierenbuurt) | 2818225044 | south, west bank | 14.9 m |
| C2 | Medisch Centrum Oost | 1260595065 | north-east quadrant | 17.9 m |
| V4 | synthetic landing node near H2 | — | snapped to H2 access edge | 0 m |
| V5 | synthetic landing node near D2 | — | snapped to D2 access edge | 0 m |

All POIs are REAL OSM elements inside the bbox; V4/V5 are explicitly marked
`synthetic experimental facility` in the canonical config.

## 2. Site B spatial utilization BEFORE vs AFTER

| Metric | BEFORE (primary only) | AFTER (+auxiliary) |
|---|---|---|
| facility convex-hull area | 2.47% of site | 14.69% |
| facility bbox area | 5.15% | 19.40% |
| facility E-W span | 15.0% of width | 31.7% |
| facility N-S span | 34.2% of height | 61.2% |
| route envelope area (100 m buffer) | 3.53% | 8.53% |
| 3x3 grid cells covered | 2 / 9 | 4 / 9 |

Pixel-level note: raw per-band ink is dominated by the road layer, which was
already drawn across the whole bbox in v1 (band coverage 0.22/0.18/0.18 ->
0.21/0.18/0.18); the spatial-utilization improvement is therefore measured on
facility/route GEOMETRY (hull, spans, envelope, grid), which is the
scientifically meaningful quantity and improved substantially.

## 3. Site B auxiliary ODs

| OD | Route | Network | Euclidean | Circuity | ETA | Turns | SpanX/SpanY |
|---|---|---|---|---|---|---|---|
| OD-B1 | D2 -> H1 | 2451 m | 1585 m | 1.55 | 240 s | 7 | 24% / 43% |
| OD-B2 | D1 -> H2 | 2695 m | 2526 m | 1.07 | 255 s | 6 | 29% / 65% |

Both cross the Amstel on real SUMO edges. OD-B2 crosses 5 water bodies; its
crossing-closure sensitivity: +16.9% / +16.9% / +73.9% (Berlagebrug) /
+45.1% / +75.9% — every closure keeps a detour.

## 4. Site B primary B1 / OD unchanged?

**YES.** Revalidation on the canonical net: D1->H1 eta 127.475 s (config
127.475), B1 `379148751#2` closure +88.693% (config 88.693), detour exists.
The canonical config's `facilities` / `sumo_mapping` / `disruption_links`
primary sections are asserted byte-identical to the legacy config.

## 5. Site C new transverse facilities

| Key | Facility | OSM id | Location | Snap |
|---|---|---|---|---|
| D2 | 66 Street Plaza (retail) | 295699431 | west side | 70.0 m (WARNING, <100) |
| H2 | Everyday Medical (clinic) | 2955340269 | south-east | 22.0 m |
| C2 | Kameyosek Shopping Centre | 574145086 | south-west | 59.1 m (WARNING, <100) |
| C3 | Aspenwood (retail) | 556875401 | east side | 38.9 m |
| V4/V5 | synthetic landing nodes | — | near H2 / D2 | 0 m |

## 6. Site C east-west OD length / circuity

| OD | Route | Network | Euclidean | Circuity | ETA | SpanX | SpanY |
|---|---|---|---|---|---|---|---|
| OD-C1 | C2 -> C3 (west->east) | 3322 m | 2632 m | 1.26 | 224 s | **58.0%** | 22% |
| OD-C2 | D2 -> H2 (NW->SE) | 3818 m | 3029 m | 1.26 | 237 s | 36% | 77% |

OD-C1 east-west span = 58.0% of the site width (target >50%, floor 40%).

## 7. Site C still non-bridge-dominated?

**YES.** OD-C1 and OD-C2 have river_dependency = 0 and
critical_crossing_dependency = False (59 real SUMO edge refs, 0 missing).
Mill Creek is a culvert-scale stream whose only in-box road crossing sits on
the primary corridor; both auxiliary corridors deliberately stay south of it,
so no auxiliary OD depends on any water crossing. Primary B1 remains a plain
road link (not a bridge).

## 8. Site A scientific definition unchanged?

**YES.** All 8 frozen files remain SHA-256 byte-identical; the canonical
`sim/sites/site_a_suzhou/` tree contains byte-identical COPIES plus clearly
marked DERIVED read-only files (water_osm.json, registry.json,
routes/primary.json).

## 9. Canonical data paths

```
sim/sites/
├─ site_a_suzhou/{config,osm,sumo,bluesky,facilities,routes,validation,figures,metadata}
├─ site_b_amsterdam/{...}
├─ site_c_edmonton/{...}
├─ comparison/
└─ sites_manifest.yaml
```

Legacy paths recorded in `sim/sites/comparison/LEGACY_SITE_PATH_AUDIT.md`
(38 entries). Frozen Exp-1 replay paths (`sim/sumo`, `sim/bluesky`,
`config/scenario_config.yaml`) untouched.

## 10. Final figure paths

- `sim/sites/site_a_suzhou/figures/site_a_suzhou_unified_scene_v2.png` (+ `_paper.png`)
- `sim/sites/site_b_amsterdam/figures/site_b_amsterdam_unified_scene_v2.png` (+ `_paper.png`)
- `sim/sites/site_c_edmonton/figures/site_c_edmonton_unified_scene_v2.png` (+ `_paper.png`)
- `sim/sites/comparison/three_site_cross_validation_v2.png`
- `sim/sites/comparison/three_site_cross_validation_paper.png` (300 DPI, 3170x1162 px)
- `sim/sites/comparison/three_site_cross_validation_paper.pdf` (vector, 512 kB)

## 11. Visual QA

QA method: programmatic pixel/geometry analysis (this runtime cannot perform
human-eye review; the method is recorded in `comparison/visual_qa.json`):
- renderer-based label bbox overlap check: **0 overlaps**;
- color-class dominance: primary-red 1328 px vs auxiliary-brown 272 px
  (ratio 4.88 — primary visually dominant);
- paper version: 3170x1162 px @ 300 DPI + vector PDF, fonts >= 6.5 pt;
- band coverage recorded for v1/v2 (see section 2 note).

## 12. IMG-T1 .. IMG-T15

**15 PASS / 0 WARNING / 0 FAIL** — full table in
`sim/sites/comparison/image_acceptance_tests.md` and
`image_acceptance_tests.csv`.
