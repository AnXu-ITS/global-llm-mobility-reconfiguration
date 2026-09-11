# Experiment 2 — Replay / Reproducibility Audit (protocol §30)

Selected 12 (scenario, seed) pairs — 2 per failure family — replayed for all 4 managers (48 runs).

- B0/B1/B2: deterministic rerun; non-API artifacts must be byte-identical to the primary run.
- B4b: replay of the CACHED primary decisions (no LLM call, marked `replay: true`) — reproducibility ONLY; these runs are NEVER counted as independent samples (frozen rule §28/§30).

| scenario | seed | manager | replay verdict |
|---|---|---|---|
| E2_F1_C3 | 20240609 | B0 | PASS |
| E2_F1_C3 | 20240609 | B1 | PASS |
| E2_F1_C3 | 20240609 | B2 | PASS |
| E2_F1_C3 | 20240609 | B4b | PASS |
| E2_F1_C1 | 20240619 | B0 | PASS |
| E2_F1_C1 | 20240619 | B1 | PASS |
| E2_F1_C1 | 20240619 | B2 | PASS |
| E2_F1_C1 | 20240619 | B4b | PASS |
| E2_F2_C3 | 20240611 | B0 | PASS |
| E2_F2_C3 | 20240611 | B1 | PASS |
| E2_F2_C3 | 20240611 | B2 | PASS |
| E2_F2_C3 | 20240611 | B4b | PASS |
| E2_F2_C2 | 20240604 | B0 | PASS |
| E2_F2_C2 | 20240604 | B1 | PASS |
| E2_F2_C2 | 20240604 | B2 | PASS |
| E2_F2_C2 | 20240604 | B4b | PASS |
| E2_F3_C1 | 20240602 | B0 | PASS |
| E2_F3_C1 | 20240602 | B1 | PASS |
| E2_F3_C1 | 20240602 | B2 | PASS |
| E2_F3_C1 | 20240602 | B4b | PASS |
| E2_F3_C3 | 20240607 | B0 | PASS |
| E2_F3_C3 | 20240607 | B1 | PASS |
| E2_F3_C3 | 20240607 | B2 | PASS |
| E2_F3_C3 | 20240607 | B4b | PASS |
| E2_F4_C1 | 20240602 | B0 | PASS |
| E2_F4_C1 | 20240602 | B1 | PASS |
| E2_F4_C1 | 20240602 | B2 | PASS |
| E2_F4_C1 | 20240602 | B4b | PASS |
| E2_F4_C1 | 20240607 | B0 | PASS |
| E2_F4_C1 | 20240607 | B1 | PASS |
| E2_F4_C1 | 20240607 | B2 | PASS |
| E2_F4_C1 | 20240607 | B4b | PASS |
| E2_F5_C3 | 20240619 | B0 | PASS |
| E2_F5_C3 | 20240619 | B1 | PASS |
| E2_F5_C3 | 20240619 | B2 | PASS |
| E2_F5_C3 | 20240619 | B4b | PASS |
| E2_F5_C1 | 20240607 | B0 | PASS |
| E2_F5_C1 | 20240607 | B1 | PASS |
| E2_F5_C1 | 20240607 | B2 | PASS |
| E2_F5_C1 | 20240607 | B4b | PASS |
| E2_F6_C3 | 20240611 | B0 | PASS |
| E2_F6_C3 | 20240611 | B1 | PASS |
| E2_F6_C3 | 20240611 | B2 | PASS |
| E2_F6_C3 | 20240611 | B4b | PASS |
| E2_F6_C3 | 20240619 | B0 | PASS |
| E2_F6_C3 | 20240619 | B1 | PASS |
| E2_F6_C3 | 20240619 | B2 | PASS |
| E2_F6_C3 | 20240619 | B4b | PASS |

**Verdict: PASS**

Compared artifacts: events.csv / actions.csv / missions.csv / clock_sync.csv (byte-identical) + failure_trace.json deterministic fields (failure_config_hash, state_before, state_after).
