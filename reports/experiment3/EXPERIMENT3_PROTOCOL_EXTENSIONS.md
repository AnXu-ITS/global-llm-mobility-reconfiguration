# Experiment 3 — Protocol Extensions (frozen pre-run)

Experiment 3 keeps every frozen Experiment-1 and Experiment-2 object
byte-identical (verified by the entry regression against the E2 entry-freeze
manifest). Everything below is an **additive, manager-agnostic extension**
implemented in NEW files, recorded here per protocol §11 / §14 / §32 before any
formal run. No B2 weight, no prompt text, and no B1 rule is changed.

**CHANGELOG entry:** `CHANGELOG.md` → "Experiment 3 protocol extensions (E3-EXT-*)".
**Comparability note:** these extensions are only active under the Experiment-3
runner (`orchestrator/experiment3_runner.py`); Experiment-1 / Experiment-2
artifacts, code paths and hashes are untouched.

---

## E3-EXT-SCHED-1 — multi-event timeline (replaces the single-failure schedule)

Experiment 2 scheduled ONE `AIR_FAILURE` at t = 360. Experiment 3 schedules an
**ordered list of exogenous events** on the canonical timeline, all frozen in
`config/experiment3_matrix.yaml` and fired at their exact times:

```text
t = 0     start (frozen 4-aircraft fleet, W0 or W1 workload)
t = 300   B1 ground disruption + M-CRITICAL-001 released (frozen E1/E2 context)
t = 360   failure-A  (first air-layer failure, frozen family/target/zone)
t = 390   [L3/L4 only] M-CRITICAL-002 released (second emergency, frozen)
t = 420   [L2/L3/L4] failure-B  (second air-layer failure, frozen)
t = 480   [L4 only]   failure-C  (third air-layer failure, frozen)
t = 900   end (L1/L2)  |  t = 1200  end (L3/L4)
```

- Each failure event is injected by the SAME frozen `INJECTORS` from
  `failures/e2_failures.py`; Experiment 3 composes them, it does not rewrite them.
- After each event, the frozen sequence fires: local safety (if applicable) →
  candidate-set update → manager replanning → checker → execution. This is
  identical to the E2 single-failure sequence, just applied per event.
- Events are exogenous: family / target / zone / site / trajectory / time are
  frozen in the matrix and NEVER derived from manager behaviour.

## E3-EXT-EM-1 — second emergency mission (multi-mission support)

`M-CRITICAL-002` (`medical_organ`, **HIGH**, V3→V1, `ground_fallback: true`,
`deadline_s` frozen per scenario) is released at t = 390 in L3/L4 scenarios. It
is a full registry mission (not a placeholder) and competes for the scarce idle
medical asset. The primary "support mission" for the inherited E1/E2 recovery
metrics remains `M-CRITICAL-001`; `M-CRITICAL-002` is tracked as an independent
mission by the new compound metrics (system loss, resource competition). The
primary critical mission's `deadline_s = 480` is unchanged; `M-CRITICAL-002`
uses a frozen HIGH deadline (`deadline_s = 630`, i.e. release 390 + 240 s frozen
HIGH slack — a new frozen constant defined here).

## E3-EXT-CAND-1 — candidate table 2.2.0 (additive multi-mission section)

`orchestrator/candidate_info_e3.py` subclasses the frozen E2 `E2CandidateEvaluator`.
`CANDIDATE_TABLE_VERSION = "2.2.0"` (bump + CHANGELOG + comparability note; the
frozen 2.0.0 / 2.1.0 modules are untouched). The top-level single-target fields
(`summary`, `air`, `ground`) are produced EXACTLY as in 2.1.0 (unchanged, so B1
/B2/B4b ranking behaviour is byte-identical to E2). One additive section:

- `mission_candidates` — a list, one entry per **actionable** mission
  (`WAITING` / `NEEDS_REPLAN` / `INTERRUPTED`) in the Global State, each:
  `{mission_id, priority, origin, destination, deadline_s, air: [...], ground: {...}}`
  computed with the SAME frozen formulas + E2 rules (`evaluate_for`).
- **Emission guard (E3-EXT-CAND-1a):** `mission_candidates` is emitted ONLY when
  there are **≥ 2 actionable missions**. With exactly one actionable mission the
  table renders **byte-identically to 2.1.0** (no extra section), so the L1
  anchor scenarios reproduce the E2 single-failure inputs for B4b exactly. This
  guard is deterministic and manager-agnostic.
- The list is ordered by the frozen priority ordering (CRITICAL > HIGH > NORMAL
  > LOW, then deadline) — this ordering is **factual**, not a recommendation.
- **No B2 score, no ranking, no recommendation, no "best candidate" is added**
  (leakage contract unchanged, extended in
  `CANDIDATE_TABLE_FAIRNESS_AUDIT` for 2.2.0). The multi-mission section exists
  so that resource *competition* is representable to every manager with the same
  factual, structured information.

## E3-EXT-CHECK-1 / E3-EXT-SEM-1 — reuse E2 checker/validator (no new semantics)

The E2 feasibility checker (`safety/feasibility_checker_e2.py`) and semantic
validator (`safety/semantic_validator_e2.py`) already cover F1–F6, UTM, risk
zones and landing sites. Because Experiment 3 composes only frozen families, it
reuses these extensions **unchanged**; the E3 runner swaps them in exactly as the
E2 runner does. No new failure semantics, hence no new checker/semantic code.

## E3-EXT-METRIC-1 — compound metrics (additive, see metric definitions)

`orchestrator/experiment3_runner.py::_metrics` computes, in ADDITION to the
frozen E1/E2 metrics (unchanged formulas):

- `system_weighted_loss` (primary E3 outcome),
- `resource_competition_correct`,
- `spare_medical_assets_at_t420` (second-wave readiness),
- `cascade_recovery` (per-event recovery success/time),
- `decision_oscillation_count`,
- `priority_consistency_violations`.

Full formulas frozen in `EXPERIMENT3_METRIC_DEFINITIONS.md`. No inherited metric
formula is modified (the two documented E2 post-run metric corrections remain in
force and are carried into the E3 metric definitions verbatim).

## E3-EXT-WL-1 — workloads W0 / W1 (reused from E2)

The 4-aircraft fleet is never expanded. W0 (canonical) and W1 (low-redundancy)
are the frozen E2 workloads and are reused unchanged:

- **W0**: `L-UAV-01` busy M-L-001; `EVTOL-01` busy M-P-001; `M-UAV-01` idle at
  V1; `M-UAV-02` idle at V2.
- **W1**: additionally `M-UAV-01` busy M-M-001 (HIGH, non-reassignable), leaving
  `M-UAV-02` as the ONLY idle medical asset — required to realize genuine
  resource competition (L3/L4).

Ground side (B1 closure, primary critical mission, release time, ground fallback
model, deadline) is identical in every scenario.

## E3-EXT-TRG-1 — trigger policy (frozen E1/E2 policy, unchanged)

Event-triggered decisions (each scheduled event) + 30-s periodic re-decisions
**only while the primary critical mission is actionable** (frozen
`_periodic_due`). For L3/L4, `M-CRITICAL-002` remains actionable under its own
frozen deadline; re-decisions continue while **either** the primary critical
mission or `M-CRITICAL-002` is actionable, so the competition window is fully
observed. This is a documented, manager-agnostic change to the *trigger stop
condition* only (it never changes the frozen 30-s cadence or event triggers).

## E3-EXT-GEOM-1 — geometry derivation (pilot step, not hand-authored)

The L2–L4 zone/target geometry (failure-B/C zones, flyaway envelopes, GNSS
zones, recovery-route positions at t = 420 / t = 480) depends on aircraft
positions at those times, which depend on the t = 300–420 evolution. Therefore
geometry is NOT hand-authored: `tools/gen_exp3_geometry.py` derives it from the
frozen sites (V1/V2/V3 coordinates + measured aircraft positions at the failure
instant) and `tools/audit_exp3_scenarios.py` verifies the frozen invariants
(backup outside the zone; recovery leg clear for L2 designs; corridor + recovery
covered for the no-air designs; competition asset is genuinely single). This
mirrors the E2 cross-site geometry procedure exactly.

## Freeze status

All extensions above are frozen **before** the pilot. The scenario matrix is a
**semantic matrix** (classes, motifs, timeline, targets, workloads, emergencies,
failure composition) at this stage; geometry is derived + audited in the pilot
step, after which `config/experiment3_matrix.yaml` is frozen (post-pilot hash),
matching the E2 workflow.
