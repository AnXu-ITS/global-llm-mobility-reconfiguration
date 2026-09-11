# Experiment 3 — Entry Baseline

Protocol §2. Records the exact state of every object Experiment 3 inherits from
the frozen Experiment-1 / Experiment-2 platform, and the user-approved scoping
decisions. **After the formal primary run starts, none of the inherited objects
may be modified.** All Experiment-3 additions live in NEW files / new config
blocks and are separately frozen in `EXPERIMENT3_PROTOCOL_EXTENSIONS.md` and
`config/experiment3_matrix.yaml`.

**Full hash manifest:** `outputs/experiment3_entry_freeze_hashes.json` (produced
at pilot freeze; identical to the E2 entry-freeze manifest for all inherited
objects, re-verified by the entry regression).

---

## 0. User-approved scoping decisions (2026-09, Experiment 3 kickoff)

| decision | choice |
|---|---|
| Scope | **Site A canonical first**; cross-site (Site B/C) deferred until Site A primary is frozen and reviewed |
| B2 handling | **Keep frozen B2 unchanged** (single-objective, `config/experiment1_b2_weights.yaml`); any B2 degradation under compound is a legitimate finding, not a bug |
| Seeds | **n = 20 per scenario class** for the entire primary matrix (L1–L4) |
| Managers | **B0 / B1 / B2 / B4b** (primary). B4a is NOT an Experiment-3 arm |

## 1. Frozen identifiers (inherited, unchanged)

| component | identifier / value |
|---|---|
| canonical testbed | `S0_3p2km_v1` |
| study area | 3.2 km × 3.2 km, center 31.30377 N / 120.59981 E, EPSG:4326 |
| fleet | frozen 4 aircraft (`L-UAV-01`, `EVTOL-01`, `M-UAV-01`, `M-UAV-02`) — NOT expanded |
| simulation step | 1 s |
| Global State | v1 (`schema_version` 1.0.0) |
| Action Contract | v2 (`ManagerAction v1` schema; LLM-facing `prompts/manager_v2.txt`) |
| Candidate Table | v2.1.0 inherited from E2; Experiment 3 adds an additive 2.2.0 multi-mission section (see protocol extensions) |
| Prompt | `manager_v2` (unchanged; multi-mission is rendered into the existing state, not into a new prompt) |
| B2 objective | frozen (`config/experiment1_b2_weights.yaml`) — **no re-tuning for Experiment 3** |
| Managers | B0, B1, B2, B4b |

## 2. Inherited frozen protocol constants (not re-defined by Experiment 3)

- Ground disruption family used by Experiment 3 = **B1 critical-link closure**
  (E1 `MEDIUM` severity): D1→H1 ETA 131.838 s → 181.763 s, **+37.87 %**.
- Primary critical mission = `M-CRITICAL-001`, `medical_blood`, **CRITICAL**,
  V2→V1, released at t = 300 s, `ground_fallback: true`, `deadline_s = 480`.
- B1 link closure at t = 300 s; 1 s step; periodic re-decision 30 s.
- Failure families F1–F6 (frozen E2 semantics + injectors
  `failures/e2_failures.py`) are REUSED verbatim; Experiment 3 introduces NO new
  failure family — "compound" = composition of frozen families on one timeline.
- LLM: `corp-ai/openai/deepseek-v4-pro`, temperature 0, `json_object`,
  max_tokens 8192, prompt `manager_v2`. Real API latency recorded, never
  injected into simulation time (Frozen Simulation Decision Mode).
- 20-seed set: reuse the frozen E2 20 seeds (`config/experiment2_seeds.yaml`),
  subject to a seed-independence audit under the Experiment-3 scenarios.

## 3. Experiment-3 additions (new files only — frozen objects untouched)

| new object | purpose |
|---|---|
| `config/experiment3_matrix.yaml` | L1–L4 compound scenario matrix (multi-event schedule) |
| `config/experiment3_seeds.yaml` | frozen 20-seed list (copy of E2 seeds, re-hashed) |
| `failures/e3_compound.py` | multi-event failure scheduler (composes frozen F1–F6 injectors) |
| `orchestrator/candidate_info_e3.py` | candidate table 2.2.0 (additive per-actionable-mission section) |
| `orchestrator/experiment3_runner.py` | Experiment-3 runner (reuses E2 machinery, adds multi-event timeline + second emergency) |
| `tools/gen_exp3_geometry.py` | derive + audit L2–L4 zone/target geometry from the frozen sites (pilot step) |
| `tools/run_experiment3.py` + analysis/audit tools | harness, audits, statistics, figures |

All extensions are documented in `EXPERIMENT3_PROTOCOL_EXTENSIONS.md` with
CHANGELOG entries and comparability notes before any formal run.

## 4. Experiment-3 scientific context (why this experiment exists)

Experiment 2 closed with **no statistically supported B2–B4b divergence** and
with **B1 ≡ B2** (the frozen optimizer's min-ETA choice always coincides with
the rule baseline). The E2 final report attributes this to the scenario space:
a single critical mission + a single failure means the answer is always
"min-ETA air vs ground" and no beneficial preemption exists. Experiment 3 is
the test of whether that comparability is a *property of the policies* or an
*artifact of a too-simple scenario space*. It does so by constructing compound
scenarios with genuine multi-objective trade-offs:

1. **Resource competition** — two emergencies, fewer idle compatible assets.
2. **Sequential cascade** — a second failure after the first response, so the
   first response's robustness matters (redundancy reservation).
3. **Multi-objective divergence** — scenarios where the greedy min-ETA choice
   and the globally-priority-consistent choice can genuinely differ.

All three are implemented as **exogenous, frozen** events (never derived from
manager behaviour). The hypothesis that the LLM's contextual prioritization
helps as complexity grows is **to be tested, not assumed**; a null result
(all managers degrade identically) is an equally valid finding.
