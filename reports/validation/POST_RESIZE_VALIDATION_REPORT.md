# Post-Resize Validation Report (Phase 1 Regression + Integrity)

Scope: validate the **3.2 km cropped** S0 testbed only. No LLM, no Experiments
1–4, no new failure scenarios, no research-question redesign.

## Final PASS / FAIL table

| ID | Check | Verdict | Numerical evidence |
|----|-------|---------|--------------------|
| T-R1 | Scene bounds & facility containment | ✅ PASS | 10.24 km²; 8/8 facilities inside bbox |
| T-R2 | CRS round-trip alignment | ✅ PASS | median = **0.000000 m**, max = **0.000000 m** (req <5 / <15 m) |
| T-R3 | SUMO facility snapping sanity | ⚠ WARNING | H1 42.85 m, D1 **58.01 m**, V3 27.48 m, V1/V2/B1 0 m (no >100 m) |
| T-R4 | BlueSky dynamics provenance | ✅ PASS | `bs.traf` authoritative; L-UAV-01 +1358.5 m, EVTOL-01 +3636.8 m, parked M-UAV-02 0.0 m |
| T-R5 | Master clock synchronization | ✅ PASS | 600 steps; max sumo_error = **0**, max bluesky_error = **0** |
| T-R6 | Ground→Air event chain | ✅ PASS | GD1(300) → DISPATCH(300) → MISSION_STARTED(300) → COMPLETED(410) |
| T-R7 | Air→Hub reverse event | ✅ PASS | F-AIR-001(450): BUSY→UNAVAILABLE, EN_ROUTE→NEEDS_REPLAN |
| T-R8 | B1 disruption validity | ✅ PASS | ETA 131.838 → 181.763 s (**+37.87 %**), detour + H1 reachable, interior (860 m margin) |
| T-R9 | Feasibility checker | ✅ PASS | 3 illegal actions all REJECTED (no silent repair) |
| T-R10 | Deterministic replay | ✅ PASS | events/actions/missions/clock_sync **byte-identical** across 2 runs |

**Summary: 9 PASS, 1 WARNING, 0 FAIL.** No blocker for Phase 2.

## Evidence (artifacts + file paths)

| Artifact | Path |
|----------|------|
| Scene audit | `reports/POST_RESIZE_SCENE_AUDIT.md` |
| Detailed alignment CSV / report | `outputs/geographic_alignment_detailed.csv`, `reports/GEOGRAPHIC_ALIGNMENT_DETAILED_REPORT.md` |
| BlueSky provenance CSV / report | `outputs/bluesky_state_provenance.csv`, `reports/BLUESKY_DYNAMICS_VALIDATION.md` |
| Clock sync post-resize CSV | `outputs/clock_sync_post_resize.csv` |
| Post-resize smoke test | `runs/post_resize_cosim_smoke_test/{events,actions,missions,ground_state,air_state,clock_sync}.csv`, `run_config.yaml`, `registry_final.json` |
| B1 validity CSV / report | `outputs/b1_post_resize_validation.csv`, `reports/B1_POST_RESIZE_VALIDATION.md` |
| Reverse air event CSV | `outputs/reverse_air_event.csv` |
| Feasibility violations CSV | `outputs/violations.csv` |
| Replay runs | `runs/replay_post_a/`, `runs/replay_post_b/` |
| Unified scene figure | `outputs/unified_ground_air_scene_post_resize.png` |
| New tests | `tests/test_bluesky_state_provenance.py`, `tests/test_clock_sync_post_resize.py`, `tests/test_feasibility_post_resize.py`, `tests/test_reverse_air_post_resize.py`, `tests/test_deterministic_replay_post_resize.py` |
| New tools | `tools/geo_alignment_detailed.py`, `tools/validate_b1.py`, `tools/run_post_resize_smoke.py` |

## Event schedule (fixed in config)

`config/scenario_config.yaml` → `schedule:` `{duration_s: 600, b1_close_t_s: 300,
reverse_air_event_t_s: 450, seed: 20240601}`. The orchestrator reads these from
config (no hardcoded absolute times).

## Deviation note (unchanged)

The implementation uses 3.2 km / 4 aircraft (per user refinement instruction);
`EXPERIMENT_IMPLEMENTATION_SPEC.md` §7.2 still documents 5 km / 12 aircraft as the
normative reference. Documented in `CHANGELOG.md`, not edited.
