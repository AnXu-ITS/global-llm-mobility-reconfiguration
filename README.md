# Deadline-Aware Runtime Supervision for Ground–Air Service Reconfiguration

Research code and experiment workspace targeting **HSCC + ICCPS 2027**. · [中文说明 →](README.zh-CN.md)

> **In one sentence.** When a *slow* decision-maker — an LLM — proposes service reconfigurations from observations that are already stale, while traffic, failures, and service deadlines keep evolving, how should the execution layer avoid spending still-valid recovery opportunities on waiting, outdated proposals, resource conflicts, and incomplete handoffs?

This repository implements a **deadline- and resource-aware asynchronous runtime supervisor** for ground–air mobility services, simulated with SUMO (ground) and BlueSky (air). The LLM is treated as a *replaceable slow proposer*; the intended scientific contribution is the execution machinery, not the model.

---

## Status at a glance

| Component | Status | What exists |
|---|:---:|---|
| **R0** · corrected-baseline bridging | 🟡 | 27/27 historical replays reproduced; 6 `runtime_v2` bridge units pending |
| **R1** · protocol kernel (consistency & progress) | 🟡 | 48 named cases + 6 fault-injection variants pass; depth-12 full state space (gate G1) pending |
| **Minimal physical closed-loop** | ✅ | 3 handoff-delay controls (0 / 30 / 120 s) pass in SUMO + BlueSky |
| **Sites D/E/F** (real OSM) | ✅ | Leipzig / Barcelona / Berlin single-payload closed-loop landed |
| **R2–R6** formal experiments | ⬜ | Designed, not yet run |

> No formal experiment, LLM call, or paper result has been produced yet. The evidence above is development-stage verification, not the submission's main results.

## Background and motivation

The earlier version of this project compared *which supervision policy* (heuristic vs. LLM-proposed) best reconfigures a ground–air mobility system under disruptions. The follow-up work pivots to a sharper question: once a slow proposer is in the loop, **losses come less from "which plan" than from what the executor does while that plan is being computed** — waiting, applying outdated proposals, double-booking a shared resource, or completing a handoff that never actually finished.

The LLM is therefore no longer asked to "beat the heuristics". It stays a slow, structured proposal source, and the novelty shifts to:

1. an **asynchronous service-execution model with physical preconditions** — request / version / operation / payload states, traced end-to-end;
2. a **supervision mechanism that jointly manages time budget and resource / handoff commitments**;
3. a **two-level verification system** — protocol-level (R1) plus closed-loop physical (R3/R4) evidence.

## Research questions

- **RQ1 · Execution consistency** — under duplicates, reordering, latency, timeouts, and multi-task contention, can the system keep task versions, resource ownership, and payload phase consistent, without infinite rejection or waiting?
- **RQ2 · Opportunity preservation** — relative to a tuned fixed timeout and a latest-start rule, does joint time-and-resource management reduce avoidable missed deadlines, and does the benefit appear only under resource-conflict / handoff-unready / phase-sensitive conditions?
- **RQ3 · System cost & scope** — at what execution overhead, resource idling, or incumbent-service loss do these mechanisms come, under real async calls, explicit ground/handoff models, and larger effective payload?

## Approach

Only one simulation owner mutates world state; a proposal worker reads immutable snapshots and returns structured proposals.

```
world / failures / tasks
        │
   fast supervisor ── immutable snapshot ──► slow proposer (LLM) worker
        │                                        │ structured proposal
        ▼                                        ▼
  admission · version & resource check · bounded reservation · issue · confirmation
        │
        ▼
   SUMO (ground) + BlueSky (air) + task/payload registry
```

A task's waiting budget is predicted from the remaining slack of its currently-feasible fallback plan,

```
B_m(t) = d_m − t − T_fallback(m, t) − T_monitor+issue − ε
```

rather than a single global timeout. Four executor variants isolate the mechanism:

| Variant | Waiting rule | Cross-stage resource planning |
|---|---|---|
| `X_FIX` | dev-tuned fixed timeout | current-state checks only |
| `X_LST` | latest-start / remaining-slack rule | current-state checks only |
| `X_TX` | fixed timeout (as `X_FIX`) | reservations + handoff-phase planning |
| `X_FULL` | dynamic time budget | joint time + resource/handoff management |

The primary pre-registered comparison is `X_FULL − X_LST` under identical physics and information.

## What is implemented so far

- **R0** — 27/27 historical replays reproduce task durations, action tables, and the full action pipeline (only decision IDs excluded). Anchors: B0 D0/D30/D60 = 182/212/242 s, B1 = 342 s, B2 = 302 s.
- **R1** — `runtime_v2/core.py` implements operation dedup, task/resource versioning, atomic resource bundles, bounded wait leases, non-postponable due-times, cancel semantics, terminal release, and payload-custody preconditions. 8 families × 6 named variants = 48 cases; 6 deliberately-broken variants are all caught; a 720-schedule enumeration (two tasks, one resource, depth 6) finds no checker violation.
- **Minimal physical closed-loop** — one payload: load → air transport → failure → local return → V3 handoff → ground transport → unload. Handoff requires the physical co-arrival of carrier, ground vehicle, and facility for 30 s; delivery uses SUMO's real arrival event + 15 s unload, never an ETA timer. Three facility-wait controls (0 / 30 / 120 s) pass.
- **Sites D/E/F** — Leipzig, Barcelona, Berlin imported from real OSM with per-site single-payload closed-loop diagnostics; formal site acceptance pending.

Full detail and explicit limits: [`research_hscc2027/IMPLEMENTATION_STATUS.md`](research_hscc2027/IMPLEMENTATION_STATUS.md).

## Repository layout

| Path | Contents |
|---|---|
| [`research_hscc2027/`](research_hscc2027/) | New direction: runtime kernel, design, configs, schemas, tools, site data |
| [`research_hscc2027/runtime_v2/`](research_hscc2027/runtime_v2/) | Protocol kernel (dedup, versioning, reservation, custody, event log) |
| [`research_hscc2027/design/`](research_hscc2027/design/) | Experiment protocols (v0.1 / v0.2), R1 acceptance, execution priority |
| [`research_hscc2027/sites/`](research_hscc2027/sites/) | Real-OSM site sources, candidates, frozen D/E/F fixtures, figures |
| [`manuscript_hscc2027/`](manuscript_hscc2027/) | Paper source (private Overleaf workspace; ACM template for now) |
| [`provenance/hscc2027/`](provenance/hscc2027/) | Migration analysis, freeze manifests, restore / audit records |
| [`legacy/20260918/`](legacy/20260918/) | Archived prior project (old framework, manuscript, R0 evidence) |
| [`HSCC_ICCPS_2027_研究方向转向计划书.md`](HSCC_ICCPS_2027_研究方向转向计划书.md) | Full research-pivot plan (Chinese) |

## Reproducing the current results

Deterministic replays and protocol checks run from the repository root (Python 3, SUMO, BlueSky; exact environment recorded in `research_hscc2027/outputs/bootstrap/`):

```powershell
python -B research_hscc2027/tools/run_r0.py              # historical replay
python -B research_hscc2027/tools/run_r1.py              # protocol kernel cases
python -B research_hscc2027/tools/run_physical_controls.py
python -B research_hscc2027/tools/plan_experiments.py --check
```

Generated runs/outputs are kept out of Git (see `.gitignore`) and are backed up externally with an index; raw road-network maps are regenerated from OSM.

## Roadmap

`R0` corrected-baseline bridge → `R1` protocol & conditional progress → `R2` async time management (main) → `R3` explicit handoff & ground transport → `R4` effective scale & overhead → `R6` fixed six-site panel (A Suzhou · B Amsterdam · C Edmonton · D Leipzig · E Barcelona · F Berlin). See [`EXPERIMENT_PROTOCOL_v0.2.md`](research_hscc2027/design/EXPERIMENT_PROTOCOL_v0.2.md).

## Code availability, citation, license

- **Code availability** — this repository is the primary artifact; a versioned snapshot (e.g. Zenodo DOI) will be minted on acceptance for a permanent identifier.
- **Citation** — preprint in preparation; please cite the upcoming paper once available.
- **License** — to be added; contact the authors before reuse in the meantime.
- **Contact** — open an [issue](../../issues).
