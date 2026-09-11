## 2026-09-10 — Paper finalization and writing release

- Added `outputs/paper_final/results.json` as the authoritative E1-final/E2-corrected/E3-v2/E4-v2 release (10,960 primary + 180 ablation runs).
- Unified paired statistics/Holm, refreshed E3 hypothesis outputs, corrected E2 recovery to 191 jointly affected Site-A pairs, and retained endpoint backend failures.
- Corrected E4 executed replan latency, conditional recovery denominators, switch/return metrics; added absolute arm tables, CIs and logged-call reliability.
- Documented 4A's actual observation ordering and 4C input burden; retained the original simulation design and raw results.
- Updated final reports, progress/index and `PAPER_STORY_AND_WRITING_GUIDE.md`; archived superseded reports. Added E3/E4 PNG and SVG figures.
- Verified 25 paper/E4 checks, E3 9/9 and cross-site 7/7. Historical runner mismatch is explained by an exactly reconstructible deadline-metric patch. All 10,960 primary metric hashes unchanged.

# Changelog — Phase 0/1/2/3 + Experiments 1/2/3

## 2026-09-08 — Experiment 3 v2: review-driven redesign + re-run (COMPLETE)

Following the independent review (`reports/EXPERIMENT2_3_INDEPENDENT_REVIEW_20260908.md`),
Experiment 3 was archived and re-designed; the corrected matrix (v2) is re-running.

- **Archived** old E3 data → `archive/experiment3_v1/` (runs/experiment3,
  runs/experiment3_cross_site, config, reports/experiment3, E3 code snapshots;
  63,363 files). Old runs kept as development/diagnostic/old-version comparison.
- **`orchestrator/experiment3_runner.py`**:
  - `_system_weighted_loss` (P0-1): only CANCELLED/FAILED/INTERRUPTED/
    NEEDS_REPLAN/WAITING charge cancellation; normal ongoing EN_ROUTE/ASSIGNED
    services now score 0 (was: `else: cancellation_cost` for every non-COMPLETED).
  - `_periodic_due` (P0-2): triggers on ANY actionable mission, not just the
    emergency set (background NEEDS_REPLAN services are now recoverable).
  - `_cascade_recovery` (P1-1): mode derived from the FIRST recovery event
    (MISSION_STARTED=>AIR / GROUND_FALLBACK_STARTED=>GROUND), not backfilled by
    any later ground recovery.
  - `_on_critical_mission` override + `_on_second_emergency(run_manager=)` +
    `setup()` (P0-3): when `second_emergency_t_s == critical_t`, BOTH emergencies
    are injected before the single manager decision → genuine simultaneous
    resource competition (previously the 2nd emergency released at t=390, after
    the 1st was already dispatched).
  - `resource_competition_correct` / `priority_consistency_violations` emitted as
    explicit `null` (N/A) pending a per-decision competition-instant detector
    (review permits N/A).
  - `run_config.yaml` now records `matrix_version`.
- **`failures/e2_failures.py`** (§6.3): `_segment_segment_distance_m` now detects
  proper segment-segment intersection (orientation test) instead of sampling only
  the four endpoints (orthogonal crossings were previously missed).
- **`orchestrator/experiment1_runner.py`** (P0-5, shared): deadline violation now
  marks unfinished-past-deadline as violation (already fixed in the prior entry).
- **`config/experiment3_{matrix,site_b,site_c}.yaml`**: version 1→2;
  `second_emergency_t_s` 390/352/413 → 300 (simultaneous competition on all sites).
- **Freeze hash** regenerated: `outputs/experiment3/freeze_hashes.json`
  `matrix_sha256` = `d441240a7ef5c2643af84a507ec1d997c721c0a0a824fae16ce212e77f5d8e8b`.
- **`tools/run_experiment3.py`**: `run_is_current` also verifies `matrix_version`.
- **Smoke (v2)**: 24/24 B0/B1 across all 12 scenarios; B4b L3 competition decision
  identical to B1 (DISPATCH CRITICAL → M-UAV-02, HIGH → GROUND_FALLBACK), SWL=0.
- **Re-run (v2)**: `python tools/run_experiment3.py --manager all --jobs 8`
  (Site A canonical 960 runs) + `tools/run_experiment3_cross_site.py --site all
  --manager all --jobs 12` (cross-site 1920 runs). Both completed, **0 failures**.
- **Finalization** (`tools/finalize_e3_v2.py`): completeness 960/960 + 1920/1920,
  `matrix_version` == 2 on all runs, **0** background missions charged non-zero
  SWL (P0-1 confirmed). Site A v1→v2 mean SWL dropped across all scenarios
  (e.g. L2 640→240; L3 COMP_F4/F5 760→60; L4_A 360→60).
- **Site A statistics** (`tools/analyze_experiment3.py`): B1/B2/B4b significantly
  beat B0 in L1/L3/L4 (Holm p<0.001); **L2 diff=0, Holm=1.0** — the spurious
  "+200 background gap" is gone (all managers 240).
- **Cross-site analysis** (`tools/analyze_experiment3_cross_site.py`,
  `tools/test_exp3_cross_site_hypotheses.py`): three-site SWL reproduced; B1/B2/B4b
  beat B0 at Sites A/B (L1/L3/L4) and Site C (L3). **H3a null at all sites** —
  B4b is statistically indistinguishable from B1/B2 (Site A +1.7/+3.4 SWL,
  p≈0.32), i.e. the earlier "B4b worse" was a false background-charging artifact
  and B4b shows parity, not superiority.

Not yet done: finite-trip background lifecycle / cargo handover / per-task ground
ETA (review §6 model-boundary items — external validity, require further design);
`resource_competition_correct` + `priority_consistency_violations` full
implementation (currently N/A).

## 2026-09-08 — Independent-review fixes to E2/E3 statistics & metrics

External independent review (`reports/EXPERIMENT2_3_INDEPENDENT_REVIEW_20260908.md`)
found substantive issues in E2/E3. This entry records the code fixes and the
offline recomputation (no simulation/LLM re-runs; frozen `runs/` untouched).

- **`tools/analyze_experiment2.py` / `tools/analyze_experiment3.py`**:
  - `holm()` now applies the cumulative-max step-down and treats undefined
    (all-identical) p as 1.0 (was: `p*(m-k)` only, no monotonicity, NaN-unsafe).
  - `mcnemar()` removed the extra `* 2` (scipy `binomtest` is already two-sided).
- **`orchestrator/experiment1_runner.py`**: `critical_mission_deadline_violation`
  now marks an unfinished mission past its deadline as a violation (was:
  `bool(comp_t and crit and comp_t > deadline)` → False when `comp_t is None`).
- **`tools/recompute_corrected_stats.py`** (new): read-only offline recomputation
  over all 6,720 E2/E3 runs (3 sites), writing `outputs/corrected_20260908/`
  (never overwrites frozen `outputs/experiment{2,3}/`).
- **Verified against the independent review (exact match)**:
  - E2 Site A aggregate completion-time diff Holm p = **0.008678** (12-item family);
    McNemar exact 5:0 → 0.0625, 9:0 → 0.00390625.
  - E3 Site B L2 SWL Holm = **0.211348** (not 0.036; not significant).
  - E3 Site B B4b deadline-violation rate = **59/240 = 24.58%** (was 53/240 = 22.08%);
    B2 = 60/240 = 25.00% (unchanged).
- **Analysis docs**: `reports/REVIEW_20260908_ANALYSIS.md` (analysis & disposition);
  `PROGRESS_REPORT.md` updated with the audit corrections (§11 summary + inline 🔍 marks).

Not yet done (per review §7): E3 scheduler trigger, background-mission lifecycle,
SWL accounting, L3 competition design, geometry fix — these require re-runs, not
offline recomputation.

## Experiment 3 — Compound Disruption Stress Test (COMPLETE, 4 managers)

User-approved scoping: Site A canonical first (cross-site deferred), B2 kept
frozen (no re-tuning), n = 20 seeds across the whole L1–L4 matrix. All
Experiment-3 additions are **additive, manager-agnostic, NEW files**; no frozen
E1/E2 object is modified.

- **Frozen design documents** (`reports/experiment3/`):
  `EXPERIMENT3_ENTRY_BASELINE.md` (inherited frozen identifiers + scoping
  decisions), `EXPERIMENT3_PROTOCOL_EXTENSIONS.md` (E3-EXT-SCHED-1 multi-event
  timeline, E3-EXT-EM-1 second emergency, E3-EXT-CAND-1/1a candidate table 2.2.0
  with the single-mission emission guard, E3-EXT-TRG-1 extended periodic
  trigger, E3-EXT-GEOM-1 geometry derivation), `EXPERIMENT3_METRIC_DEFINITIONS.md`
  (system-weighted loss as primary, resource competition, second-wave readiness,
  cascade recovery, decision oscillation, priority consistency).
- **Scenario matrix** `config/experiment3_matrix.yaml` — 12 classes (2 L1 anchor
  + 4 L2 cascade + 4 L3 competition + 2 L4 full-compound), multi-event failure
  schedule; F2/F5/F6 t=420/t=480 geometry declared via `derive.invariant` and
  derived + audited in the pilot step. L1 anchor F5 uses the exact frozen
  E2_F5_C2 geometry.
- **Code** (new files): `orchestrator/candidate_info_e3.py` (2.2.0),
  `failures/e3_compound.py`, `orchestrator/experiment3_runner.py`,
  `tools/run_experiment3.py`, `config/experiment3_seeds.yaml` (reuses frozen
  E2 20 seeds).
- **Environment provisioned**: PyYAML 6.0.3, jsonschema 4.26.0, eclipse-sumo
  1.27.1 (random-free-port TraCI → parallel-safe), BlueSky repo importable
  under Python 3.14.7.
- **Geometry**: `tools/gen_exp3_geometry.py` resolved 13 `derive` blocks (V1/V2/V3
  sites + frozen E2 corridor anchors); `tools/audit_exp3_scenarios.py` PASS
  (F5 recovery-route coverage, NW-corner no-asset, F2 aircraft-state-only,
  F6 corridor-cross / V3→V1-clear). Matrix carries 0 `derive` residues.
- **End-to-end smoke** (`reports/experiment3/EXPERIMENT3_SMOKE_TEST.md`): all 4
  levels smoke-tested with B1 — L1 (F1/F5), L2 (F1+F1, F1+F5 cascade),
  L3 (COMP_F1 competition + M-CRITICAL-002 second emergency released @390),
  L4 (B triple-zone + second emergency). B0/B2 verified on L1. Multi-event
  timeline, cascade-recovery, second-emergency and SWL metrics all fire
  correctly.
- **L1 anchor regression**: constant **+1 s** BlueSky arrival offset vs frozen
  E2 (5 seeds, all 121 vs 120) — uniform, sign-consistent, within the 480-s
  slack, no behavioural change → declared comparable modulo a documented
  +1-s offset (environment/version drift: E2 was Python 3.12, now 3.14 +
  eclipse-sumo 1.27.1).
- **Pilot**: 6 scenarios × 3 seeds × B0/B1/B2 = **54/54 PASS, 0 excluded**
  (`reports/experiment3/EXPERIMENT3_PILOT_FREEZE.md`); matrix frozen
  `outputs/experiment3/freeze_hashes.json` (`e8fd26b9…`).
- **Primary (4 managers)**: 12 scenarios × 20 seeds × 4 managers = **960 runs,
  0 excluded, 0 missing**. Analysis `tools/analyze_experiment3.py` →
  `outputs/experiment3/primary_analysis.json`; hypotheses `tools/test_exp3_hypotheses.py`
  → `outputs/experiment3/hypothesis_tests.json`. Results in
  `reports/experiment3/EXPERIMENT3_FINAL_RESULTS.md`:
  - SWL by level: L1 640/400/400/400, L2 540/640/640/640, L3 840/600/600/600,
    L4 490/370/370/370 (B0/B1/B2/B4b).
  - **L2 cascade backfires on air recovery**: cross-layer managers reassign the
    backup after failure-A, failure-B destroys it → +100 SWL vs ground-only B0
    (Holm p<0.001, d=1.405); structural (exogenous frozen schedule).
  - Air recovery helps elsewhere (L1 −240, L3 −240, L4 −120; B0 viol=1.0 at
    every level).
  - **B1 ≡ B2 ≡ B4b exactly (240/240 identical SWL)** → **H3a/H3b null**: the
    LLM supervisor does not lower SWL nor improve CRITICAL/HIGH consistency
    under compound stress. Informative null (deterministic frozen candidate
    set + priority weights leave no decision signal for contextual reasoning).
  - B4b reliability: 7/240 runs needed 1 LLM retry (L4_B multi-mission load;
    max 404 s), all recovered, 0 excluded.
- **LLM key** sourced from `~/.dsh/.credentials.yaml` fallback (env var unset).
- **Acceptance tests**: `tests/test_exp3_acceptance.py` 9/9 PASS;
  `tests/test_candidate_info_e3.py` PASS.

## Experiment 2 — cross-site site-adaptation + per-site pilot (Site B / Site C)

- **Site-adaptation implemented (user-approved) and verified:** the canonical
  t=360 failure time assumed a critical flight longer than 60 s, which fails on
  Site B (~44 s flight). Frozen site rule `E2-EXT-XSITE-1`:
  `t_failure = 300 + floor(air_eta/2)` → Site B 322 s, Site C 383 s (Site A's
  canonical 360 s stays frozen; the rule's Site-A value would be 357 s —
  documented). F2/F5/F6 zone/envelope geometry is re-derived per site from the
  site's own V1/V2/V3 + the t_failure aircraft position and audited against
  frozen invariants (backup outside the zone; V3→V1 recovery leg clear for
  C2 designs; corridor+recovery covered for C3 designs) —
  `tools/gen_exp2_site_matrices.py`,
  `outputs/experiment2/cross_site_geometry_audit.json`. Site-C-specific
  findings: F5-C2 radius 80 m and F6-C2 half-width 88 m (the recovery leg runs
  close to the corridor there); Site-C C2 air recovery (~198 s) exceeds the
  180-s slack → recovery success WITH deadline violation (measured, honest).
- **Modified smoke: 48/48 PASS** (`reports/experiment2/E2_CROSS_SITE_SMOKE.md`):
  the adapted timeline now interrupts the AIRBORNE critical chain on Site B in
  every C2/C3 family (F1/F2/F5/F6-C2 complete at 461 s, meet the deadline).
- **Per-site pilots: 72 runs per site, 722/722 checks PASS**
  (`reports/experiment2/E2_CROSS_SITE_PILOT.md`). Site matrices frozen
  post-pilot (`outputs/experiment2/cross_site_freeze_hashes.json`);
  seeds = the frozen E2 20-seed set.
- **Per-site primaries: 1280 runs per site (2560 total), 0 excluded**
  (`reports/experiment2/E2_CROSS_SITE_FINAL_RESULTS.md`). Post-primary fix:
  the Site-C F6-C1 envelope (old rule "V3 lat − 0.0025") sat too close to the
  corridor and caught the critical aircraft; corrected to
  "min(V3/V1/pos_tf lat) − 0.0030" + an added invariant audit; the 160 F6-C1
  cells were re-run (frozen-config hash guard) and the matrices re-frozen
  (site_b `8edc667f…`, site_c `7bbb8188…`). Per-site verification PASS:
  0 exogeneity / 0 contract / 0 scenario-audit violations, 1 documented
  divergent cell per site (backend policy consequences, kept). Result: the E2
  headline (comparable B2–B4b, no significant difference after Holm,
  100 % recovery success) replicates on both sites with site-adapted
  timelines/geometry, while operating points shift with corridor geometry
  (Site C violation rate 62.5 %).
- Frozen canonical datasets untouched (`runs/experiment2/`, Site-A matrix).

## Experiment 2 — cross-site smoke (Site B Amsterdam / Site C Edmonton) + E1 analysis-tool re-freeze

- **Cross-site E2 smoke (platform verification, 48/48 PASS):** the frozen E2
  pipeline (F1-F6 injectors, candidate table 2.1.0, E2 checker/semantic
  extensions, failure_trace, E2 metrics) runs on `site_b_amsterdam` and
  `site_c_edmonton` via `tools/run_experiment2_cross_site.py` with the smoke
  matrices `config/experiment2_site_b_matrix.yaml` /
  `config/experiment2_site_c_matrix.yaml` (one scenario per family, site-derived
  F2/F5/F6 geometry). Findings in `reports/experiment2/E2_CROSS_SITE_SMOKE.md`:
  (1) Site B's ~44 s critical flight completes before the canonical t=360
  failure — the C2/C3 critical-chain designs need a site-adapted failure time or
  documented C1-only treatment; (2) Site-C zone geometry cannot be copied from
  Site A (the F2-C1 V3 zone contains Site-C's critical aircraft at t=360);
  (3) 1 transient LLM transport error kept per the frozen policy. The frozen
  canonical dataset `runs/experiment2/` is untouched.
- **E1 analysis-tool re-freeze (user-approved):** `tools/analyze_ablation.py`
  and `tools/analyze_experiment1_final.py` were refactored externally on
  2026-09-06 (loader reuse) and no longer matched `outputs/file_hashes_final.json`.
  The refactor is accepted as an intentional post-E1 change; the freeze manifest
  was updated to the new hashes (`5f96ad3f…` / `32a13d81…`). Impact on
  comparability: none for the frozen Experiment-1 DATASET (runs + analysis
  outputs are unchanged; only the two post-hoc analysis tools were refactored).

## Experiment 2 — Air-Layer Failure Management (protocol extensions)

**Metric fix (transparent, artifacts untouched):** the runner's recovery-metric
aggregation required an `aircraft` payload key, so GROUND fallback recoveries
were missed (`recovery_success` / `recovery_mode` / `recovery_time_s`). The
runner is fixed and the three derived fields were recomputed for all 1280
primary runs from the frozen `events.csv` with the frozen §B/§D formulas
(`tools/fix_exp2_metrics.py`, per-run provenance `metrics_recomputed.json`).
No simulation artifact was modified.

Experiment 2 (failure-induced feasible-set reconfiguration) is implemented as
**additive, manager-agnostic extensions in NEW files**; all frozen Experiment-1
objects are untouched (entry regression: 26/26 hash matches, 12/12 PASS).
Extensions frozen pre-pilot — see `reports/experiment2/EXPERIMENT2_PROTOCOL_EXTENSIONS.md`:

- `E2-EXT-STATE-1` — additive aircraft transitions AVAILABLE→DEGRADED /
  AVAILABLE→CONTINGENCY (`failures/state_ext.py`); `orchestrator/registry.py`
  unchanged.
- `E2-EXT-CAND-1` — candidate table **2.1.0** (`orchestrator/candidate_info_e2.py`,
  subclass of the frozen 2.0.0 evaluator): additive factual fields
  (`failure_reason`, `risk_zone_intersection`, `utm_eligible`) + failure-aware
  legality (UTM DEGRADED/OUTAGE, air risk zones). No scoring/ranking added.
- `E2-EXT-CHECK-1` / `E2-EXT-SEM-1` — checker/semantic extensions
  (`safety/feasibility_checker_e2.py`, `safety/semantic_validator_e2.py`):
  `UTM_AIR_PROHIBITED`, `GNSS_DEGRADED_AIRCRAFT`, `RISK_ZONE_VIOLATION`.
- `E2-EXT-F1..F6` — six failure injectors with frozen semantics
  (`failures/e2_failures.py`); `E2-EXT-GS-1` — failure visibility through the
  frozen global_state_v1 schema (utm_state + failure_zones).
- `orchestrator/experiment2_runner.py` — Experiment-2 runner reusing the frozen
  Phase-2/3 machinery; fixed ground context (B1 closure, M-CRITICAL-001,
  release 300 s, deadline 480 s, duration 900 s); ONE air failure per run,
  exogenous (frozen in `config/experiment2_matrix.yaml`).
- Impact on comparability: none for Experiment 1 (its code paths and artifacts
  are byte-identical); Experiment-2 metrics/statistics are new (frozen in
  `EXPERIMENT2_METRIC_DEFINITIONS.md`).

## Cross-Site Experiment-1 — FULL SCALE (Site B Amsterdam / Site C Edmonton)

Frozen Site-A Experiment-1 pipeline applied to the two cross-site testbeds at
the SAME experimental scale as the frozen primary (user request: "把 bc 的实验
规模补成和 a 一模一样"). Frozen Site A files untouched (CS-T1 byte-identical
re-verified; CS-T1..T20 still 20/20 PASS).

- **B2 disruption links selected per site** by TraCI closure ranking (Site-A
  `select_disruptions` method; `tools/cross_site_select_disruptions.py`,
  `outputs/cross_site/site_{b,c}_disruption_ranking.csv`): Site B `7370322`
  (+17.78 %), Site C `1427039799` (+22.14 %); added to the four site configs
  (facilities + sumo_mapping + disruption_links.links.B2).
- **Matrices upgraded to the full frozen structure** (`config/experiment1_site_b_matrix.yaml`,
  `experiment1_site_c_matrix.yaml`): LOW=[B2], MEDIUM=[B1], HIGH=[B1,B2]+degrade
  0.5; 12 scenarios (`XB_*` / `XC_*`), 3 pilots; urgencies/workloads verbatim
  from the frozen primary matrix. Severity magnitudes are site-specific
  (Site B MEDIUM +88.69 % vs Site A +37.87 %); the factor STRUCTURE is identical.
- **Runs: 12 x 20 seeds x {B0,B1,B2,B4b} = 960 + 60 B4a ablation per site =
  1020 per site, 2040 total, 0 excluded.** Run dirs
  `runs/experiment1_cross_site/<site_id>/<scenario>/seed<seed>/<manager>/`;
  the earlier 8 single-seed smoke runs preserved (superseded) in
  `runs/experiment1_cross_site_legacy_smoke/`.
- Per-site analyses (n=240/manager): `outputs/site_b_amsterdam/`,
  `outputs/site_c_edmonton/` (primary_analysis.json + B2_vs_B4b_tradeoff.csv +
  ablation_b4a_vs_b4b.json); three-site comparison
  `outputs/cross_site/three_site_comparison.csv` +
  `reports/cross_site/THREE_SITE_COMPARISON.md` (tool
  `tools/analyze_three_sites.py`).
- Full report: `reports/cross_site/CROSS_SITE_EXPERIMENT1_REPRODUCTION.md`.

### Results (n = 240 per manager; mean [95 % CI])

| site | B0 | B1 | B2 | B4b |
|---|---|---|---|---|
| site_b_amsterdam | 262.7 s, 50 % viol | 47.7 s, 0 % viol, 0.500 dmg | 47.7 s, 0 % viol, 0.500 dmg | 49.1 s, 0 % viol, 0.487 dmg |
| site_c_edmonton | 323.7 s, 83 % viol | 168.3 s, 10 % viol, 0.500 dmg | 168.3 s, 10 % viol, 0.500 dmg | 168.7 s, 10 % viol, 0.500 dmg |

**No significant B2↔B4b divergence on either site** (all Holm p >= 0.33) and
the B4a ablation is behaviourally inert there (B4a ≈ B4b): on Sites B/C air
dominates ground so strongly that B1 ≡ B2 ≡ B4b (air-first everywhere). The
Site-A trade-off region (ground≈air, E1_H_H_high divergence, candidate table
load-bearing) does NOT replicate on B/C — the three sites instantiate three
regions of the speed↔service-preservation space (see
`CROSS_SITE_EXPERIMENT1_REPRODUCTION.md`).

## Phase 3 — LLM Manager Integration & Decision Sanity Validation

Phase 3 swaps the Rule Manager for an LLM Manager while freezing Phase 2 (Global State v1,
ManagerAction schema, FeasibilityChecker, executor, 3.2 km / 4-aircraft testbed, event
schedules, Rule Manager, C2 local contingency). Question: can the LLM stably, legally, and
executably participate in the *same* closed loop? **Yes — P3-T1..T14: 14/14 PASS / 0 FAIL.**

- LLM = `corp-ai/openai/deepseek-v4-pro` (local corp-ai endpoint), prompt `manager_v1`,
  `temperature=0`, `response_format=json_object`, `max_tokens=8192` (≤2048 exhausts the budget
  on reasoning tokens → empty content; 8192 → 100 % JSON validity).

### Added (Phase 3)
- `config/resource_compatibility.yaml` — aircraft-type × mission-type matrix (allowed/conditional/
  denied) + strategic reserve (≥1 medical UAV kept while HIGH/CRITICAL medical mission pending).
- `schemas/manager_action_v1.schema.json` — frozen ManagerAction contract (12 action types).
- `prompts/manager_v1.txt` — frozen supervisory-manager prompt (8 objectives; decide from supplied
  Global State only; JSON only; short reason; no chain-of-thought).
- `managers/llm_client.py` + `managers/llm_manager.py` — LLM Manager, interface ≡ RuleBasedManager;
  pipeline JSON→schema→semantic→feasibility→executor; one structured retry; no silent repair.
- `safety/semantic_validator.py` — shared semantic gate (UNKNOWN_RESOURCE/UNKNOWN_MISSION/
  RESOURCE_INCOMPATIBLE/DUPLICATE_ASSIGNMENT/PRIORITY_VIOLATION/SITE_UNAVAILABLE).
- `safety/feasibility_checker.py` — additive only: REROUTE→air-mission, RETURN/LAND→aircraft-only,
  RESERVE kept (`_check_reserve`); Phase-1/2 gates unchanged.
- `orchestrator/phase3_orchestrator.py` — Phase-3 loop (semantic + checker + executor), additive
  action executor (REROUTE/DIVERT/RESERVE/RETURN/LAND/NO_ACTION/ESCALATE), `_normalize_action`
  (fills route/target from mission using the Rule Manager's identical route semantics), latency
  logged but never advances sim time (frozen simulation decision mode).
- `tools/run_phase3.py` (SMOKE/C2_B/C2_C), `tools/run_phase3_offline.py` (25 states),
  `tools/run_phase3_counterfactual.py` (9 pairs), `tools/run_phase3_stability.py` (10 repeats),
  `tools/analyze_phase3_offline.py`, `tools/test_semantic_validator.py`.
- `tests/test_phase3_acceptance.py` — P3-T1..T14.
- Reports: `PHASE3_ENTRY_BASELINE.md`, `LLM_OFFLINE_SANITY.md`, `LLM_COUNTERFACTUAL_SANITY.md`,
  `LLM_DECISION_STABILITY.md`, `PHASE3_ACCEPTANCE_TESTS.md`, `PHASE3_FINAL_REPORT.md`.
- Artifacts: `runs/phase3_offline_decisions/` (states + rule/llm outputs + feasibility +
  counterfactual + stability), `runs/phase3_live_{smoke,c2}/`, `runs/phase3_no_backup/`.

### Results (Phase 3)
- Offline gate: JSON 100 %, schema 100 %, feasible 100 %, unknown-resource 0, duplicate 0,
  retry 0 %, no-action 52 %.
- Counterfactual: 7 PASS / 2 OBSERVED / 0 FAIL. Stability: 10/10 identical (DISPATCH M-UAV-02).
- Live: SMOKE DISPATCH M-UAV-02 → COMPLETED (AIR); C2-B DISPATCH M-UAV-02 → C2_LOST →
  local contingency RETURN→V3 → REASSIGN M-UAV-01 → COMPLETED (AIR); C2-C DISPATCH M-UAV-02 →
  GROUND_FALLBACK → COMPLETED (GROUND). All three match the Phase-2 Rule-Manager sequence.
- Rule vs LLM (25 states): 22 equivalent, 2 different-but-feasible (LLM more conservative on the
  medical reserve), 1 different-and-better (LLM avoids the Rule's infeasible DISPATCH to UNAVAILABLE
  V1), 0 worse, 0 invalid. No "LLM outperforms Rule" claim.
- STOP: P3-T1..T14 no FAIL → did **not** auto-enter Experiments 1–4.

## Phase 2 — Manager Layer Validation (canonical testbed frozen)

Phase 2 canonical testbed = **3.2 km × 3.2 km / current 4-aircraft fleet**
(2 background services + 2 medical standby). The old 5 km / 12-aircraft
normative reference from the implementation spec is superseded; the testbed is
NOT reverted to 5 km and the fleet is NOT restored to 12 aircraft.

- `config/scenario_config.yaml` — `scenario_version: S0_3p2km_v1` frozen; new
  `phase2:` block (schedule, critical mission, manager params, C2-lost local
  contingency, and C2-A/C2-B/C2-C case definitions).
- Phase 2 scope: formal Rule-Based Manager B1, final Global State v1 schema,
  C2 Lost Link failure (F1 only) with manager-independent local contingency,
  full closed loop + deterministic replay. **No LLM integration.**

### Added (Phase 2)
- `managers/rule_based.py` — Rule-Based Manager B1 (pure `Global State -> ManagerAction`,
  rules 1–8: priority, availability/reassignability, no higher-priority preemption,
  feasibility, min completion time, endurance tie-break, ground fallback, DELAY/CANCEL).
- `state/global_state.py` + `schemas/global_state_v1.schema.json` — deterministic
  Global State v1 (sorted keys, fixed float precision, byte-identical replay).
- `failures/c2_lost.py` — C2 Lost Link (F1) mutation + manager-independent local
  contingency (RETURN to V3; reason recorded).
- `orchestrator/phase2_orchestrator.py` — Phase-2 closed loop:
  `Global State -> Rule-Based Manager -> FeasibilityChecker -> Executor -> Simulator`.
- `tools/run_phase2.py` — case runner (C2-A/C2-B/C2-C); `tools/dump_snapshots.py`.
- `safety/feasibility_checker.py` — additive new action gates: `GROUND_FALLBACK`,
  `DELAY`, `CANCEL` (existing DISPATCH/REASSIGN unchanged).
- `orchestrator/registry.py` — additive `reassign` / `ground_fallback` /
  `complete_ground_mission`; aircraft priority updated on assignment.
- Tests: `test_rule_based_manager.py` (9/9), `test_c2_local_contingency.py` (4/4),
  `test_phase2_acceptance.py` (P2-T1..T12).
- Reports: `PHASE2_ENTRY_BASELINE.md`, `GLOBAL_STATE_SUFFICIENCY_AUDIT.md`,
  `RULE_MANAGER_DECISION_TRACE.md`, `PHASE2_ACCEPTANCE_TESTS.md`, `LLM_INPUT_READINESS.md`.
- Run artifacts: `runs/phase2_rule_manager/{C2_A,C2_B,C2_C,replay_a,replay_b}/`
  (events/ground/air/missions/actions/clock/violations CSVs + manager_inputs /
  manager_outputs / feasibility_checks / snapshots JSONL + metrics.json +
  run_config.yaml).

### Results (Phase 2)
- **P2-T1..T12: 12/12 PASS / 0 FAIL** (1 Phase-1 WARNING: D1 snap 58.01 m, carried over).
- Canonical C2-B loop: B1 close (t=300) → critical mission → D001 dispatch
  M-UAV-02 (114.5 s) → C2 lost on M-UAV-02 (t=360) → local contingency RETURN→V3 →
  mission NEEDS_REPLAN → D002 reassign M-UAV-01 (65.9 s) → COMPLETED (t=420).
- C2-A (logistics C2 lost): logistics mission reassigned; critical mission unaffected.
- C2-C (no backup): ground fallback selected, completed t=542.
- Deterministic replay: 10 artifacts byte-identical across 2 runs (P2-T4/T12).
- Global State: 12 snapshots schema-validated; ~3.3–4.0 k chars per manager input.

## 2026 — Post-Resize Phase-1 Regression + Integrity Validation

Scope: re-validate the 3.2 km cropped testbed only (no LLM, no Exp 1–4, no new
failure scenarios). Verdict: **9 PASS / 1 WARNING / 0 FAIL**.

### Changed
- `orchestrator/orchestrator.py` — event schedule now config-driven
  (`schedule.{b1_close_t_s,reverse_air_event_t_s}` from `scenario_config.yaml`);
  added `actions.csv` and `missions.csv` logging (mission lifecycle + issued
  actions); `_record_mission`/`_record_action` helpers; shutdown closes the new
  writers and records `reverse_air_event_t_s` in `run_config.yaml`.
- `config/scenario_config.yaml` (+ `tools/build_sumo_scene.py`) — new `schedule:`
  block `{duration_s:600, b1_close_t_s:300, reverse_air_event_t_s:450, seed:20240601}`.
- `orchestrator/fleet.py` — passenger/eVTOL service moved to **V2↔V1** (1.7 km),
  fixing an EC35 waypoint-overshoot drift that occurred on the 494 m V3↔V1 leg.
- `tools/plot_unified_scene.py` — also writes `unified_ground_air_scene_post_resize.png`.

### Added
- `tools/run_post_resize_smoke.py` — post-resize smoke test runner (config-driven schedule).
- `tools/geo_alignment_detailed.py` — splits alignment into CRS round-trip + snapping.
- `tools/validate_b1.py` — B1 post-resize validity (detour/reachability/interior).
- Tests: `test_bluesky_state_provenance.py`, `test_clock_sync_post_resize.py`,
  `test_feasibility_post_resize.py`, `test_reverse_air_post_resize.py`,
  `test_deterministic_replay_post_resize.py`.
- Outputs: `geographic_alignment_detailed.csv`, `bluesky_state_provenance.csv`,
  `clock_sync_post_resize.csv`, `b1_post_resize_validation.csv`,
  `reverse_air_event.csv`, `violations.csv`.
- Reports: `POST_RESIZE_SCENE_AUDIT.md`, `GEOGRAPHIC_ALIGNMENT_DETAILED_REPORT.md`,
  `BLUESKY_DYNAMICS_VALIDATION.md`, `B1_POST_RESIZE_VALIDATION.md`,
  `POST_RESIZE_VALIDATION_REPORT.md`.
- Run: `runs/post_resize_cosim_smoke_test/` (with actions/missions CSVs) + replay
  `runs/replay_post_{a,b}/`.

### Results (key numbers)
- bbox/area: 3.2 × 3.2 km = **10.24 km²**, centre (31.30377 N, 120.59981 E).
- CRS round-trip: median **0.000000 m**, max **0.000000 m**.
- Snapping: H1 42.85 m, D1 **58.01 m (WARNING)**, V3 27.48 m, V1/V2/B1 0 m.
- Clock: 600 steps, max error **0 steps** (SUMO == BlueSky == orchestrator).
- B1: ETA 131.838 → 181.763 s (**+37.87 %**), detour + H1 reachable, interior.
- Ground→air chain: GD1(300)→DISPATCH→STARTED(300)→COMPLETED(410).
- Air→hub: F-AIR-001(450) BUSY→UNAVAILABLE, EN_ROUTE→NEEDS_REPLAN.
- Deterministic replay: 4 CSVs byte-identical across 2 full runs.

## 2026 — Refined S0 (crop + sparse air + B1–B3)

### Changed
- **Cropped the testbed** from 5 × 5 km to **3.2 × 3.2 km**, re-centred on the
  facility centroid (31.30377 N, 120.59981 E). Re-downloaded OSM and rebuilt
  `network.net.xml` (4.05 MB) for the smaller extent. The D1→H1 corridor is
  preserved exactly (base free-flow ETA 131.84 s unchanged), and the crop
  retains **2 distinct ground detours** when B1 is closed (181.76 s and
  191.21 s, verified via the TraCI router).
- **B1/B2/B3 candidate disruption links** (alternative, never simultaneous),
  selected by the TraCI router as low/medium/high D1→H1 accessibility impacts:
  - B1 `148377677#0` — high   +37.87 % (same bottleneck as before)
  - B2 `538444299#2` — medium +15.43 %
  - B3 `794857408`   — low    +7.16 %
  Config now carries `disruption_links` (with `closure_impact` ranking) instead
  of the single `b1_selection` block.
- **Sparse air network**: the 12-aircraft fleet was reduced to **4 aircraft** —
  exactly two background low-altitude services (`logistics_service` V2↔V3 on
  L-UAV-01, `passenger_service` V2↔V1 on EVTOL-01) plus two medical standby
  assets (M-UAV-01, M-UAV-02). No inspection patrol; air layer kept sparse
  (no air-congestion study).
- Reverse air event (F-AIR-001, t=450) now targets L-UAV-01 (mission M-L-001 →
  NEEDS_REPLAN) instead of the removed L-UAV-05.
- `plot_unified_scene.py` now renders B1/B2/B3 with high/medium/low colour
  coding and the two background air services.

### Added
- `tools/select_disruptions.py` — TraCI-router B1/B2/B3 selector + ≥2-detour
  verification for the cropped net.

### Revalidated
- T1 geographic alignment: 0.0000 m for all 8 landmarks (H1/D1/V1/V2/V3/B1/B2/B3).
- T2/T3/T4/T8/T9 acceptance: 5/5 PASS after the crop and fleet change.

## 2026 — Phase 1 (testbed + co-simulation)

### Added
- `config/scenario_config.yaml` — single source of truth for canonical S0.
- `sim/sumo/` — real-OSM road network (`network.net.xml`), `routes.rou.xml`
  (background traffic), `additional.add.xml`, `canonical.sumocfg`.
- `sim/bluesky/canonical_s0.scn` — 12-aircraft low-altitude scene (shared WGS84).
- `orchestrator/` — master-clock orchestrator (`orchestrator.py`), SUMO adapter,
  BlueSky adapter, geo/CRS helpers, registry (aircraft/mission state machines),
  fleet definition, config loader.
- `safety/feasibility_checker.py` — hard-constraint filter for manager actions.
- `tools/` — `fetch_osm.py`, `build_sumo_scene.py`, `select_b1.py`,
  `build_bluesky_scene.py`, `plot_unified_scene.py`, `run_scenario.py`.
- `tests/test_geographic_alignment.py` (T1), `tests/test_acceptance.py`
  (T2/T3/T4/T8/T9).
- `reports/` — spec review, environment audit, geographic alignment, acceptance
  tests, final report.
- `outputs/geographic_alignment.csv`, `outputs/unified_ground_air_scene.png`.
- `runs/cosim_smoke_test/` — 600 s co-sim outputs (ground/air/clock/events/
  registry/run config).

### Fixed
- SUMO `traci`/`sumolib` import path (pip wheel: `import sumo` then add `tools/`).
- Circular import shadowing in `tools/*` (`from orchestrator.geo import ...`).
- Overpass POI way `center` vs node `lat/lon` handling (`el_latlon`).
- `pyproj` added for `net.convertLonLat2XY/convertXY2LonLat`.
- `net.getNearestEdges` absent → manual nearest-edge snapping.
- `getDistanceRoad` returns a float (not tuple) in SUMO 1.27 → route ETA via
  `findRoute` + lane length/maxSpeed (free-flow, stable).
- TraCI needs full `sumo.exe` path (`sumo_env.binary`).
- BlueSky clock lag: enter OPERATE state at init (`bs.sim.op()`) so the first
  `step()` advances the clock in lockstep with SUMO.
- Parked aircraft kept `SPD 0` after dispatch → `fly_to` now restores cruise speed.
- `Aircraft.__init__` ignored `status` kwarg → now honored.
- Feasibility checker: reject assigning a non-AVAILABLE aircraft; allow
  reassignment when the prior holder is UNAVAILABLE (no false DUPLICATE_ASSIGNMENT).

### Notes
- B1 is a TraCI-router-selected bottleneck corridor (edge `148377677#0`,
  +37.9 % ETA, detour exists); no OSM bridge lay on the D1→H1 shortest path.
- GD3 (`ETA >= 2.0 × baseline`) intentionally not triggered by the +37.9 %
  detour; GROUND_DISRUPTION is driven by the GD1 closure event per spec §12.
