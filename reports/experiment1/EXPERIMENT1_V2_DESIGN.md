# Experiment 1 — v2 Redesign (per the independent review)

This document replaces the archived v1 prototype design
(`archive/experiment1_v1/`). It is written **before** any v2 data collection.
The goal is unchanged — *when ground transport is disrupted, can the LLM
Supervisor selectively call limited low-altitude resources?* — but the design
fixes the validity problems the review identified, so the result can support an
RQ1 claim instead of a bounded prototype observation.

**Guiding rule (review §10):** keep v1 as a labelled prototype; re-run B4 under
the fixed interface/information contract to test *attribution*; only claim
traffic-system effects after the Phase-2 realism work; accept whatever result
(worse, tie, or better) without tuning toward an LLM win.

---

## 1. Fixes and their mapping to the review

| v2 item | review § | status |
|---|---|---|
| Unified action contract (REASSIGN preemption) + prompt v2 | §3 | to implement |
| Shared candidate-information module (ETA/cost/endurance) | §4 | to implement |
| Design realism (real ground task, task recovery, energy, multi-OD) | §5 | Phase 2 |
| `scenario_seed` vs `llm_repeat_id`; cache/version capture | §6 | to implement |
| Execution-based metrics + signed deltas | §7 | **done** (`EXPERIMENT1_V2_CORRECTED_ANALYSIS.md`) |
| Proper statistics (Wilcoxon/Holm/t-CI/B4-vs-B2) | §8 | **done** |
| Execution-layer fixes (normalize-then-validate, env-computed ETA, real tests) | §9 | to implement |
| Two-phase plan | §10 | below |

## 2. Fix A — unified action contract (review §3)

The v1 prompt defined `REASSIGN` only as *re-homing an INTERRUPTED /
NEEDS_REPLAN mission*, but E1 high-workload scenarios require **preempting a
BUSY, reassignable aircraft for a new WAITING mission** — the operation the Rule
manager and Registry already support. The LLM was therefore not told the full
legal action space.

**v2 action contract (frozen before any v2 B4 run):**

| action | precondition | effect |
|---|---|---|
| `DISPATCH` | aircraft `AVAILABLE`, site available, compatible, battery sufficient | assign WAITING mission |
| `REASSIGN` | aircraft `BUSY` **and** `reassignable` **and** its current mission priority < target priority, OR target is INTERRUPTED/NEEDS_REPLAN | detach/interrupt the lower-priority mission, assign target |
| `GROUND_FALLBACK` | `ground_fallback` allowed | schedule ground completion |
| `DELAY` / `CANCEL` | deadline slack / no feasible resource | as Phase-3 semantics |
| `NO_ACTION` / `RESERVE` | — | no-op / reserve |

**Prompt v2** (`prompts/manager_v2.txt`, a new file — never merged with v1):
state these preconditions verbatim, add **one neutral preemption example**
(e.g. "a WAITING CRITICAL mission may REASSIGN a BUSY NORMAL-logistics aircraft
that is marked reassignable"), and describe both air and ground candidates
symmetrically. Temperature 0, `json_object`, `max_tokens=8192` unchanged.

**Ablation arms** (to separate interface error from policy error):
- `v2a` — prompt contract fix only.
- `v2b` — prompt fix **plus** the shared candidate table (§3).

## 3. Fix B — shared candidate information (review §4)

B1/B2 computed air ETA from cruise speed, facility coordinates and dispatch
overhead, and B2 additionally received frozen scalar weights. The v1 Global
State gave the LLM positions/coordinates/endurance but **not** cruise speed,
pickup/drop time, candidate ETA, predicted violation, preempted-loss, or the
candidate action table — so B4 could not reconstruct the 110 s vs 189 s
difference that decides the high-workload cases.

**v2 change:** a shared `CandidateEvaluator` (new module, e.g.
`orchestrator/candidate_info.py`) computes, for the target mission and every
feasible resource (air **and** ground):

- full task ETA (`position → pickup → destination`, cruise speed + dispatch
  overhead + pickup/drop dwell),
- predicted deadline violation (signed seconds),
- preempted-task loss (priority + remaining work of the mission being displaced),
- remaining endurance margin,
- legality (AVAILABLE dispatch vs BUSY-reassignable preempt).

This derived table is exposed to **every** manager identically (B1/B2 keep their
rankers but now consume the same numbers; the LLM prompt embeds the table). The
LLM still *chooses*; only the physical/cost inputs are shared. If the research
question is pure solution ability, the objective is also made public to all; if
it is semantic preference, the objective difference is an explicit factor.

## 4. Fix C — design realism (review §5, Phase 2)

The v1 prototype used a static route-cost ground ETA (no vehicle, no queueing),
background aircraft that never complete or recover, full batteries, and one
fixed OD. For the formal RQ1 traffic claim, v2 Phase 2 will:

1. **Ground task**: insert a real SUMO emergency vehicle and track actual arrival
   (or use an independently calibrated travel-time model); record *predicted*
   ETA and *actual* arrival separately.
2. **Existing tasks**: give background missions remaining work, completion, and
   **post-preemption recovery** (resume/re-dispatch when the aircraft is idle);
   report old-task delay / on-time / cancellation / recovery time.
3. **Energy**: start below full so endurance participates in feasibility.
4. **Variety**: multiple OD pairs / release times and realistic fleet positions.
5. **Parameter sweep** (pilot-then-freeze): ground/air ETA ratio, deadline slack,
   opportunity cost, aircraft distance — no single 2 s cliff (v1 MEDIUM 182 s vs
   CRITICAL 180 s) may carry a conclusion alone.
6. **Multi-task**: if global multi-task reconfiguration is claimed, add a
   rolling-horizon baseline; keep B0 (ground-only) and rename B1 explicitly
   "air-first" and B2 "single-step cost-ranking heuristic".

## 5. Fix D — seeds and repeatability (review §6)

The v1 `seed` field never changed the decision input (all 80 first-round inputs
per scenario were byte-identical), and the LLM call independence was unconfirmed
(201/281 decisions < 1 s; repeated-call token pairs identical — suspected cached
responses).

**v2 change:**

- Fix the seed plumbing so the *scenario* seed actually perturbs relevant inputs
  (SUMO background traffic → ground ETA; aircraft initial positions).
- Separate **`scenario_seed`** (traffic realization) from **`llm_repeat_id`**
  (repeated call on one fixed realization).
- Capture backend **cache-hit / request-id / model-version fingerprint** per call;
  cached output is usable only for deterministic replay, never as an independent
  reasoning sample.
- Report fixed-input stability and traffic-random samples as **separate** results.
- Deterministic managers (B0/B1/B2) need **one** execution per scenario plus an
  offline replay check — not 20 identical re-runs. Sample size for the stochastic
  B4 is set by pilot variance and target CI, not by reaching an arbitrary count.

## 6. Fix E — metrics (review §7) — DONE

See `EXPERIMENT1_V2_CORRECTED_ANALYSIS.md`. Summary of the frozen v2 definitions:

- `air_intervention` = an **issued** air action for the emergency mission
  (execution result), not a proposed one.
- `unnecessary_air` is re-labelled **"air use when ground could meet the
  deadline"** and reported separately from **"harmful preemption"** (air that is
  slower than ground and/or displaces an existing mission).
- **signed** completion difference vs B0 (negative = slower than ground); the
  truncated DE is kept only as a secondary descriptive proxy.
- fix `critical_mission_delay_s` sign and `deadline_violation` for uncompleted
  missions (uncompleted ⇒ violation, not `bool(None)`).
- report: on-time rate, signed completion diff, old-task delay/on-time/cancel,
  recovery time, actual air use, illegal-action rate.

## 7. Fix F — statistics (review §8) — DONE

Implemented in `tools/analyze_experiment1_v2.py`:

- paired t **and** Wilcoxon signed-rank, Holm correction over the pre-registered
  family, t-quantile 95 % CI (n−1 dof), a **direct B4-vs-B2** contrast, and exact
  deterministic deltas with effect size marked *undefined* (no fabricated p=0).

## 8. Fix G — execution-layer correctness (review §9)

Two confirmed-but-untriggered data-integrity holes must be closed before any
site-failure or Phase-2 experiment:

1. **Normalize-then-validate**: the manager's action must be completed/normalized
   *first*, then validated against the authoritative Global State (the v1 code
   validated before `normalize` filled `target_site`/`route`, so an LLM could
   omit the site and still pass, then inherit a closed site).
2. **Environment-computed physical ETA**: the executor must compute the actual
   completion time from the environment — it must never trust a `ground_eta_s` /
   ETA field supplied by the manager (a manager that filled `ground_eta_s=1`
   would be "evaluated" on a 1 s completion).

Acceptance tests must assert real conditions (regression actually passes,
metrics actually correct, statistics actually run), not file existence.

## 9. Two-phase execution plan (review §10)

**Phase 1 — interface & information fairness (re-run, attribution test).**
Keep the 12 frozen v1 scenarios. Implement Fix A (prompt v2), Fix B (shared
candidate table), Fix D (seed/independence), Fix G (execution). Re-run **B4**
under `v2a` and `v2b` with confirmed independent inference; re-run B0/B1/B2
once per scenario (replay-checked, not 20×). Re-apply the corrected metrics and
statistics. This isolates *interface error* from *policy error*.

**Phase 2 — traffic & service realism (formal RQ1).**
Implement Fix C: real ground vehicle / calibrated travel-time, task completion
and post-preemption recovery, energy, multi-OD, and a pilot-driven parameter
sweep (20–30 independent realizations per cell to start, sized by pilot variance
and target CI). Re-run all managers paired under the new simulator.

## 10. v2 file layout

```text
reports/experiment1/            # E1-v2 reports (this doc, corrected analysis, future results)
  EXPERIMENT1_V2_DESIGN.md
  EXPERIMENT1_V2_CORRECTED_ANALYSIS.md
  EXPERIMENT1_V2_CORRECTED_ANALYSIS.json
prompts/manager_v2.txt          # new, versioned (never merged with v1)
config/experiment1_v2/          # v2 matrix / weights / candidate-info config
runs/experiment1_v2/            # v2 runs (Phase 1 & Phase 2)
orchestrator/candidate_info.py  # shared candidate evaluator
archive/experiment1_v1/         # frozen v1 prototype (never overwritten)
```

The archived v1 prompt/config/tools stay byte-identical inside
`archive/experiment1_v1/`; v2 changes are **new files**, so the v1 snapshot and
the v2 re-run are auditable and never conflated.
