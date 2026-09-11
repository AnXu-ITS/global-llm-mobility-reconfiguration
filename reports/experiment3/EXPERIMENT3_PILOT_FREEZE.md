# Experiment 3 — Pilot Results + Post-Pilot Matrix Freeze

Pilot (protocol §24): 6 scenarios × 3 pilot seeds × 4 managers. The B0/B1/B2
arms ran now; the B4b (LLM) arm is deferred pending `CORP_AI_API_KEY`
(backend `192.168.27.4:18888` reachable but returns 401 without the key).

## 1. Pilot completeness (B0/B1/B2)

- **54/54 runs present**, 0 missing, **0 excluded** (`excluded_runs.csv` absent).
- Metrics audit over all 54 `metrics.json`: **0 anomalies** — no NaN, no
  negative SWL, correct `num_failure_events` per level (L1=1, L2=2, L3=1,
  L4=2/3), correct `experiment` tag.

## 2. SWL by level × manager (pilot, n small — verification only, NOT analysis)

| level | B0 | B1 | B2 |
|---|---|---|---|
| L1 (n=6) | 640 | 400 | 400 |
| L2 (n=6) | 540 | 640 | 640 |
| L3 (n=3) | 740 | 500 | 500 |
| L4 (n=3) | 440 | 440 | 440 |

The managers diverge where the compound stress creates genuine trade-offs
(L1/L2/L3: B0 ≠ B1 ≡ B2), which is the point of Experiment 3. Full
between-manager inference is deferred to the 20-seed primary + Holm correction.

## 3. Matrix freeze (post-pilot)

The matrix is **frozen** as of this pilot. Frozen hashes in
`outputs/experiment3/freeze_hashes.json`:

- matrix `sha256` = `e8fd26b93bf00e26…`
- per-scenario `failure_schedule` hashes (see the JSON).

`tools/run_experiment3.py` treats a run as current iff its recorded
`failure_schedule_hash` matches the frozen matrix, so any future matrix edit
automatically invalidates affected runs (hash guard), mirroring E2.

## 4. Decision

**Proceed to primary** (12 scenarios × 20 seeds × 4 managers = 960 runs).
B0/B1/B2 (720 runs) launch now; B4b (240 runs) will be appended when the API
key is set, reusing the same frozen matrix + hash guard.
