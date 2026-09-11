# Experiment 1 Finalization — Acceptance Tests (EF-T1 … EF-T20)

Protocol §31: every test must be **NO FAIL** before entering Experiment 2.

**Final status: 20 / 20 PASS — no FAIL.**

| id | test | required | status | evidence |
|---|---|---|---|---|
| EF-T1 | Code state frozen + hashes recorded (no git → SHA-256) | no unrecorded code drift | PASS | `EXPERIMENT1_FINAL_ENTRY_FREEZE.md`, `outputs/file_hashes_pre_fix.json`, `outputs/file_hashes_final.json` |
| EF-T2 | Leakage Q1 — table generable WITHOUT running B2 | YES | PASS | `CANDIDATE_TABLE_FAIRNESS_AUDIT.md` §4; generator imports no optimizer |
| EF-T3 | Leakage Q2 — table = environment/deterministic facts only | YES | PASS | field inventory §2 |
| EF-T4 | Leakage Q3 — LLM does NOT see B2 final selection | NO | PASS | B2 output written only to B2 run's `manager_outputs.jsonl` |
| EF-T5 | Leakage Q4 — LLM does NOT see a candidate ranking | NO | PASS | `air[]` in GS order, no rank field |
| EF-T6 | Leakage Q5 — LLM does NOT see B2-weight scalar | NO | PASS | no J/utility field in candidate table |
| EF-T7 | Manager naming frozen (B4a = LLM-State, B4b = LLM-Candidate) | — | PASS | `EXPERIMENT1_FINAL_ENTRY_FREEZE.md` §0.5; `make_manager` aliases |
| EF-T8 | Prompt frozen (`manager_v2.txt` hash) and unchanged | — | PASS | `PROMPT_FREEZE.md` (SHA-256 `cf3a5507…`) |
| EF-T9 | B2 objective weights frozen and unchanged | — | PASS | `B2_OBJECTIVE_FREEZE.md`; `config/experiment1_b2_weights.yaml` hash |
| EF-T10 | Metric definitions frozen pre-run (esp. Existing-Service-Damage + Unnecessary-Air predicate + θ_time) | — | PASS | `EXPERIMENT1_FINAL_METRIC_DEFINITIONS.md` |
| EF-T11 | Seed independence — distinct Global State across seeds | ≥1 state aspect varies | PASS | `SEED_INDEPENDENCE_AUDIT.md` (10/10 distinct hashes, 3 scenarios) |
| EF-T12 | Primary 960 runs complete (12×20×4, no missing cells) | 960 | PASS | `tools/verify_artifacts.py`: B0/B1/B2/B4b = 240/240 each |
| EF-T13 | B4a ablation 60 runs complete (6×10) | 60 | PASS | `tools/verify_artifacts.py`: B4a = 60/60 |
| EF-T14 | Paired design — identical per-seed realization across managers | — | PASS | pilot: `runtime.json.seed_realization` identical across B0/B1/B2/B4b per seed |
| EF-T15 | No performance-based seed pruning; exclusions only crash/corrupt/protocol | 0 unjustified exclusions | PASS | `runs/experiment1_final/excluded_runs.csv` empty (0 excluded) |
| EF-T16 | LLM empty-output policy — record, never silently substitute B2/B1 | — | PASS | code records `empty_content`; no substitution path |
| EF-T17 | Cache responses NOT counted as independent samples | — | PASS | `LLM_BACKEND_RELIABILITY.md`: 240/240 unique ids, 0 cache replays, 0 sub-second successful reuses |
| EF-T18 | B2 objective computed FROM shared table (no private re-derivation in primary path) | — | PASS | `managers/optimization.py::_decide_from_shared` |
| EF-T19 | Paired statistics + Holm correction + effect sizes | — | PASS | `outputs/experiment1_final/primary_analysis.json` (t, Wilcoxon, Holm, Cohen's d per scenario) |
| EF-T20 | No forbidden behavior (no prompt tuning to win; no post-hoc B2 re-weight; no added failure; no scenario edits to favor B4b; no same-prompt×10 as stats) | — | PASS | prompt hash frozen; B2 weights frozen; scenarios/matrix unchanged; n=seed |

## Forbidden-behavior checklist (Finalization §30)

- [x] Did NOT enter Experiment 2.
- [x] Did NOT change the research question.
- [x] Did NOT tune the prompt to make the LLM win (prompt hash unchanged).
- [x] Did NOT change B2 weights after seeing results.
- [x] Did NOT add new failure modes.
- [x] Did NOT delete LLM bad seeds.
- [x] Did NOT repeat the same prompt until a liked response (each B4 call = unique seed → unique prompt).
- [x] Did NOT modify scenarios to make B4b win.
- [x] Did NOT inject B2's best answer into the candidate table.
- [x] Did NOT silently convert a checker rejection into another valid action (executor logs raw → normalized → executed).
- [x] Did NOT count cached completions as independent samples.
