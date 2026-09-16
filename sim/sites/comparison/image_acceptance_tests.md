# IMAGE ACCEPTANCE TESTS (IMG-T1 .. IMG-T15)

Summary: **15 PASS / 0 WARNING / 0 FAIL**

Visual QA method: programmatic pixel/geometry analysis (band coverage, color-class pixel counts, renderer-based label bbox overlaps, DPI/file checks) -- see visual_qa.json.

| Test | Description | Status | Evidence |
|---|---|---|---|
| IMG-T1 | Site B spatial utilization improved | **PASS** | hull 2.5% -> 14.7%; envelope 3.5% -> 8.5%; grid 2 -> 4 of 9 |
| IMG-T2 | Site B primary OD remains valid | **PASS** | eta 127.475 s vs config 127.475; B1 closure 88.693% vs config 88.693% |
| IMG-T3 | Site B aux remote assets use real OSM geography | **PASS** | real OSM POIs: ['H2', 'D2', 'C2'] (ids [4763328999, 2818225044, 1260595065]); synthetic landing nodes marked: ['V4', 'V5'] |
| IMG-T4 | Aux routes do not alter frozen primary logic | **PASS** | primary facilities/sumo_mapping/disruption_links identical to legacy config |
| IMG-T5 | Site C contains clear transverse structure | **PASS** | OD-C1 span_x 58.01% (target >50%, floor 40%) |
| IMG-T6 | Site C transverse route uses real SUMO roads | **PASS** | 59 edge refs, 0 missing |
| IMG-T7 | Site C remains sparse/polycentric, not bridge-constrained | **PASS** | OD-C1/OD-C2 river_dependency=0, critical_crossing_dependency=False |
| IMG-T8 | Site A unchanged scientifically | **PASS** | all frozen files byte-identical |
| IMG-T9 | All three figures use same visual grammar | **PASS** | 3 sites recorded with identical STYLE dict |
| IMG-T10 | Primary and auxiliary elements clearly distinguished | **PASS** | primary-red px 1328 vs aux-brown px 272 (ratio 4.88) |
| IMG-T11 | No label/legend major overlap | **PASS** | 0 label bbox overlaps (renderer geometry) |
| IMG-T12 | Paper version legible at publication scale | **PASS** | PNG 3170x1162 px, PDF 512 kB |
| IMG-T13 | All figures saved under new canonical tree | **PASS** | 6/6 present |
| IMG-T14 | A/B/C source data consolidated under sim/sites | **PASS** | 10/10 present |
| IMG-T15 | No Experiment 1 data/results modified | **PASS** | frozen hashes verified (same check as IMG-T8) |
