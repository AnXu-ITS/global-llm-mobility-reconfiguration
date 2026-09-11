# LLM Input Readiness Assessment (Phase 2)

**Purpose:** Phase 2 does NOT call any LLM API. This report only assesses whether
the Global State snapshots produced as `manager_inputs.jsonl` are already
suitable to be handed to an LLM manager in Phase 3.

**Sampled inputs:** 5 manager inputs drawn across the three C2 cases
(`runs/phase2_rule_manager/{C2_A,C2_B,C2_C}/manager_inputs.jsonl`).

| sample | case | t | size (chars) | ≈ tokens (chars/4) |
|--------|------|---|--------------|--------------------|
| 1 | C2_B | 300 (B1 close + critical mission) | 3 298 | ~824 |
| 2 | C2_B | 360 (after C2 lost) | 3 796 | ~949 |
| 3 | C2_A | 300 | 3 298 | ~824 |
| 4 | C2_C | 300 | 3 548 | ~887 |
| 5 | C2_C | 360 (no-backup reconfiguration) | 4 046 | ~1 011 |

*(Byte counts measured directly from the `manager_inputs.jsonl` files.)*

---

## Q1 — Is the information complete?

**Yes for Phase-2 decisions.** A single snapshot contains, in one structured
document: simulation time + scenario id/version + seed; ground state (B1 state,
current/baseline ETA, ETA increase, accessibility, ground fallback); every
aircraft (status, position, mission, priority, battery/endurance, availability,
reassignable, commandable, C2/GNSS status, landing compatibility);
infrastructure (landing sites + UTM + failure zones); all missions (existing +
new, with priority/deadline/origin/destination/assignment/state/ground fallback +
delay/cancellation cost); the events since the last decision; and the ETA trend.
No decision-relevant field is missing (see
`reports/GLOBAL_STATE_SUFFICIENCY_AUDIT.md`).

## Q2 — Is there simulator-specific noise?

**No.** Positions are rounded to 7 decimals, ETAs to 3, battery to 3, altitude to
1; collections are sorted by stable keys; JSON is `sort_keys` + fixed separators.
There are no raw log lines, no floating-point jitter, no unordered data, no
simulator clock text. The same scenario + seed + time yields byte-identical JSON
(P2-T4 / P2-T12). The only "numbers" an LLM sees are already decision-meaningful.

## Q3 — token / character size

~3 300–4 050 characters per snapshot ≈ **~820–1 010 tokens** for the 4-aircraft
fleet. Well within a single LLM context window, and small enough for batch or
few-shot decision prompting.

## Q4 — Is it readable at 4 aircraft?

**Yes.** The `air[]` array is 4 entries; missions are 2–3 entries; everything is
flat, keyed, and self-describing. A human (or LLM) can scan the whole state in a
few seconds.

## Q5 — Which fields grow the most as aircraft scale?

- `air[]` — **O(N_aircraft)**; the dominant growth term (each entry ~250 chars).
- `missions.existing[]` / `missions.new[]` — O(N_missions).
- `events[]` — O(events per decision window), bounded in practice.
- `ground` / `infrastructure` / `trend` — effectively O(1).
- `air[].landing_compatibility` — small constant list per aircraft.

At 50 aircraft the snapshot would be roughly 50 × ~250 ≈ 12.5 k chars (~3 k
tokens) for `air[]` alone — still tractable, but it is the field to abstract
first.

## Q6 — Is further abstraction needed?

**Not for Phase 3 correctness, yes for scale.** For the 4-aircraft testbed the
raw Global State is the right input (complete, low-noise, small). Before scaling
the fleet, add a summary layer (e.g. counts by availability class, a ranked
candidate shortlist, aggregated ETA deltas) rather than feeding every aircraft to
the LLM. The schema already separates "dynamic" (`air`, `missions`, `ground`,
`trend`) from "static" (`infrastructure`, scenario id), which is the natural seam
for future caching/abstraction.

---

**Recommendation:** the Phase-2 `manager_inputs.jsonl` is **LLM-ready** as-is;
Phase 3 can plug an LLM manager into the identical `Global State → ManagerAction
→ FeasibilityChecker → Executor` contract without schema changes.
