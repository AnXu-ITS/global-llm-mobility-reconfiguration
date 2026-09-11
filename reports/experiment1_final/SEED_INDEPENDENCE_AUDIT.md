# Seed Independence Audit (Finalization §9)

Verifies that the 20 frozen seeds genuinely change the manager-visible Global
State (and are not merely an unused random number). Method: run the deterministic
B1 manager once per (scenario, seed) — the manager **input** is the shared Global
State, identical across managers for a given seed — and hash the first manager
input (the t = 300 s decision snapshot).

Artifact: `outputs/experiment1_final/seed_independence_audit.csv`.
Generator: `tools/audit_seed_independence.py`.

## Result

| scenario | n seeds | distinct `global_state_hash` | distinct `aircraft_state_hash` | distinct `mission_state_hash` |
|---|---|---|---|---|
| E1_H_C_low | 10 | **10** | **10** | 1 |
| E1_H_H_high | 10 | **10** | **10** | 1 |
| E1_M_C_high | 10 | **10** | **10** | 1 |

- **`global_state_hash` distinct = 10/10 for every scenario** → PASS (§9:
  "不同 seed 的 Global State 不能全部相同").
- `aircraft_state_hash` distinct = 10/10 — driven by the per-seed initial-state
  realization (busy-aircraft progress along the origin→dest leg + battery/endurance
  reduction). This changes the manager-visible **aircraft position**, **remaining
  endurance**, and **battery %** (§8 allows "aircraft progress/position" and
  "battery/endurance").
- `mission_state_hash` distinct = 1 — **expected**: the mission list is defined by
  the frozen scenario (workload/urgency/disruption), not by the seed. Mission
  *timing* is identical because the emergency release time (t = 300 s) is frozen.
- `ground_eta` is seed-invariant (free-flow static route ETA): expected and
  acceptable — §8 requires the seed to change **at least one** of the listed
  state aspects, and it changes aircraft progress/position + battery/endurance.

## Seed mechanism (frozen)

In `orchestrator/experiment1_runner.py::_apply_seed_realization`, a
`random.Random(seed)` RNG drives, for every run:

1. **battery/endurance** — each aircraft's `remaining_endurance_s` and
   `battery_pct` are multiplied by `(1 − U(0, 0.15))` (0..15 % reduction).
2. **busy-aircraft progress** — each busy aircraft's initial position is advanced
   along its origin→destination leg by `U(0.05, 0.40)`.

The same seed yields a byte-identical realization for every manager, so the
B0/B1/B2/B4b **paired design** sees identical initial states per (scenario, seed).
Scenario definitions (workload/disruption/urgency/emergency release) are untouched.

## CSV fields

`scenario_id, seed, global_state_hash, prompt_hash, ground_eta,
aircraft_state_hash, mission_state_hash, cache_hit, backend_latency`

(`prompt_hash`/`cache_hit`/`backend_latency` are `n/a` because B1 is deterministic
and issues no LLM call; the LLM-call independence is audited separately in
`LLM_BACKEND_RELIABILITY.md`.)
