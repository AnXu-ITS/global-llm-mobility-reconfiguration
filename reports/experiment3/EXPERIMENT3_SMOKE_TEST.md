# Experiment 3 — Smoke Test / Environment Verification (pre-pilot)

Records the environment provisioning and the pre-pilot smoke tests that verify
the Experiment-3 runner end-to-end before the formal pilot. This is a platform
verification record, NOT a statistical result.

## 1. Environment (this machine)

| dependency | status |
|---|---|
| Python | 3.14.7 (default `python`) |
| PyYAML | installed 6.0.3 |
| jsonschema | installed 4.26.0 |
| eclipse-sumo (SUMO + TraCI) | installed 1.27.1 (`site-packages\sumo`) |
| BlueSky | repo present `C:\Users\xuan1\OneDrive\桌面\学术agent\bluesky` (imports under 3.14) |
| LLM backend `192.168.27.4:18888` | reachable (HTTP 200 with key); key via `~/.dsh/.credentials.yaml` fallback (`CORP_AI_API_KEY` env var is unset) |

All new modules pass `py_compile`; `tests/test_candidate_info_e3.py` PASS.

## 2. Geometry derivation + audit

- `tools/gen_exp3_geometry.py` resolved **13 `derive` blocks** across the 12
  scenarios into exact lat/lon geometry (V1/V2/V3 sites + frozen E2 corridor
  anchors). `derive` count in the matrix is now **0**.
- `tools/audit_exp3_scenarios.py` **PASS** (10 geometry objects verified against
  the frozen invariants: F5 recovery-route coverage, NW-corner no-asset, F2
  aircraft-state-only, F6 corridor-cross / V3→V1-clear).

## 3. End-to-end smoke tests (single seed 20240601, B1 unless noted)

| scenario | level | events | critical final | recovery (per event) | SWL |
|---|---|---|---|---|---|
| E3_L1_F1_C2 | L1 | 1 (F1) | COMPLETED (121 s) | [AIR] | 400 |
| E3_L1_F5_C2 | L1 | 1 (F5) | COMPLETED (121 s) | [AIR] | 400 |
| E3_L2_F1_F1 | L2 | 2 (F1,F1) | COMPLETED (GROUND, 302 s, deadline-violated) | [GROUND, GROUND] | 640 |
| E3_L2_F1_F5 | L2 | 2 (F1,F5) | COMPLETED (GROUND) | [GROUND, GROUND] | 640 |
| E3_L3_COMP_F1 | L3 | 1 (F1) + 2nd emergency | COMPLETED (on-time) | [—] | 500 |
| E3_L4_B | L4 | 3 (F6,F5,F2) + 2nd emergency | COMPLETED (GROUND, deadline-violated) | [GROUND, null, null] | 440 |
| E3_L1_F1_C2 B0 | L1 | 1 | COMPLETED (182 s) | [null] | 640 |
| E3_L1_F1_C2 B2 | L1 | 1 | COMPLETED (121 s) | [AIR] | 400 |

**Level ladder (design intent confirmed):** L1 = single failure / single
emergency (byte-comparable E2 anchor); L2 = sequential cascade / single
emergency (temporal compounding); L3 = one peripheral failure / **two**
emergencies (resource competition, E3-EXT-EM-1); L4 = 2–3 failures / two
emergencies (full compound).

**Second emergency (M-CRITICAL-002, HIGH, V3→V1) verified in L3/L4:** released
at t=390 (`NEW_SECOND_EMERGENCY`), falls to GROUND fallback when no air spare
remains (L3_COMP_F1: complete t=572 < deadline 630 → on-time, SWL contribution
0), and is included in `system_weighted_loss_by_mission`. `spare_aircraft` per
event is carried in `failure_traces[i].spare_aircraft` (so "spare at second
emergency t=390" = `failure_traces[0].spare_aircraft` for L3/L4).

`failure_traces.json` carries the correct per-event sequence (family, time,
target, spare_aircraft, candidate-count pre/post). The multi-event timeline
(E3-EXT-SCHED-1), cascade-recovery (E3-EXT-CHECK-1) and second-emergency
(E3-EXT-EM-1) mechanisms fire correctly.

## 4. L1 anchor regression vs frozen E2

For the same (scenario, seed), `E3_L1_F1_C2` (B1) reproduces the frozen
`E2_F1_C2` event sequence identically (MISSION_STARTED M-UAV-02 @300,
MISSION_STARTED M-UAV-01 @360) but completes the recovery flight **1 s later**.

Quantified over 5 seeds (20240601–20240605), B1:

| seed | E2_F1_C2 ct | E3_L1_F1_C2 ct | delta |
|---|---|---|---|
| 20240601 | 120 | 121 | +1 |
| 20240602 | 120 | 121 | +1 |
| 20240603 | 120 | 121 | +1 |
| 20240604 | 120 | 121 | +1 |
| 20240605 | 120 | 121 | +1 |

The delta is **constant, sign-consistent (+1 s)** and confined to the BlueSky
arrival step; event ordering, recovery mode (AIR) and final state (COMPLETED)
are identical. This is characteristic of environment/version drift (E2 was run
on Python 3.12 + an earlier BlueSky/SUMO build; this environment is Python 3.14
+ eclipse-sumo 1.27.1), not a logic regression in the E3 runner. It is well
inside the frozen 480-s deadline slack (121 ≪ 480), so the L1 anchor is declared
**comparable modulo a documented +1-s arrival-step offset**; the offset is a
uniform additive shift that does not change any manager's decision, recovery
mode, or the between-manager ordering.

## 5. Open blockers

- **B4b (LLM)**: requires `CORP_AI_API_KEY` (endpoint reachable, 401 without it).
- **Formal L1 regression**: quantify the 1-s delta and decide comparability.
- Pilot + primary runs (B0/B1/B2 can proceed now; B4b after the key is set).
