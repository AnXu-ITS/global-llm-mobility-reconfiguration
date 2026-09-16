# A Ground–Low-Altitude Mobility Manager for Service Reconfiguration under Disruptions

[English](README.md) · [中文说明](README.zh-CN.md)

Reference implementation for the paper *"A Ground–Low-Altitude Mobility Manager for
Service Reconfiguration under Disruptions"*. A **candidate generator** converts joint
ground–air observations into a shared **executable candidate interface**; replaceable
**supervisory policies** (heuristic or LLM) select an intervention; an **executor**
checks and applies it while local aircraft contingencies run independently. Four
SUMO–BlueSky experiments are evaluated across **three contrasting transport settings**.

---

## 1. Overview

- **Three study sites**, each 3.2 km × 3.2 km from OpenStreetMap:
  - **A** — Suzhou, China (meshed urban)
  - **B** — Amsterdam, the Netherlands
  - **C** — Edmonton, Canada
- **Co-simulation** — SUMO 1.27.1 (ground) + BlueSky (air), 1 s step, 900 s horizon.
- **Core fleet** — 2 medical UAVs + 1 logistics UAV + 1 passenger eVTOL (4 aircraft).
- **LLM** — OpenAI-compatible chat-completions endpoint
  (`corp-ai/openai/deepseek-v4-pro` by default); stdlib-only client
  (`managers/llm_client.py`), key from `CORP_AI_API_KEY` or `~/.dsh/.credentials.yaml`.

### Supervisory policies (the only thing that changes between runs)

| ID | Policy | Meaning |
|---|---|---|
| `B0` | ground-only | baseline: no air dispatch |
| `B1` | rule-based | hand-coded rules that rank only air candidates |
| `B2` | fixed-objective heuristic | one-step score trading speed vs. incumbent-service preservation |
| `B4a` | LLM (no candidate info) | ablation: LLM without the derived candidate section |
| `B4b` | LLM (candidate info) | main LLM policy with explicit candidate-information support |

### Experiments

| ID | Question | Span |
|---|---|---|
| E1 | Selective air support (baseline vs. coordinated) | 3 sites |
| E2 | Air failures (6 fault families F1–F6) | 3 sites |
| E3 | Compound disturbances (levels L1–L4) | 3 sites |
| E4 | Observation–execution timing (4A refresh · 4B delay · 4C scale) | site A |

**E4 arms** — 4A observation interval `OBS10/30/60/120/300` · 4B execution delay
`D00/01/05/10/20/30/60` · 4C aircraft-record scale `N05/10/20/30/50` (core fleet fixed at 4).

---

## 2. Repository layout

```
├── orchestrator/   experiment runners, SUMO/BlueSky adapters, registry, fleet
├── managers/       B0/B1/B2/B4a/B4b policies + LLM client
├── safety/         feasibility checker + semantic validator (policy-agnostic gates)
├── config/         scenario + experiment matrices (3 sites) + LLM (phase3_config.yaml)
├── prompts/        LLM prompt templates (manager_v1/v2)
├── schemas/        JSON schemas for action validation
├── failures/       E2 fault-injection models (F1–F6)
├── state/          global-state model
├── sim/            SUMO network/routes + BlueSky inputs for site_a/b/c
├── tests/          standalone acceptance tests (no pytest)
├── tools/          run_experiment{1..4}[_cross_site].py + analyze_*.py
├── docs/           design documents
└── manuscript/     paper + reproduction pipeline (see below)
```

`manuscript/` contains the authoritative paper source and its reproduction pipeline:

```
manuscript/
├── overleaf/               main.tex, supplement.tex, references.bib, journal class files
│   ├── figures/            PDF figure assets
│   ├── editable_figures/   PowerPoint figure decks
│   └── reproducibility/    frozen paper reproducibility package (configs, prompts,
│                           schemas, derived data, hashed inventory, queue_fix.py)
├── source/revision_v3/     analysis scripts + derived data + regression runs
├── figure1/                Figure 1 builder and assets
├── reproduce_analysis.ps1  postprocessing/reproduction entry point
└── REPRODUCTION_README.md  full reproduction instructions (see Section 6)
```

Runtime artifacts (`runs/`, `outputs/`) and `archive/` are **git-ignored** (large and
reproducible on demand; `archive/` also holds superseded planning docs and reviews).

---

## 3. Requirements

- **Python 3.14** (virtualenv recommended)
- **SUMO 1.27.1** — via the `eclipse-sumo` pip wheel (no separate install)
- **BlueSky** — a *source checkout* (not pip); see Setup
- Python packages — [`requirements.txt`](requirements.txt)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   POSIX: source .venv/bin/activate
pip install -r requirements.txt
```

---

## 4. Setup

### 4.1 SUMO

`eclipse-sumo` is in `requirements.txt`. At runtime `orchestrator/sumo_env.py` imports
`sumo` to locate `SUMO_HOME` and add `traci`/`sumolib` to the path.

### 4.2 BlueSky

BlueSky is imported **from source** (`orchestrator/bluesky_adapter.py`):

```bash
git clone https://github.com/TUDelft-CNS-ATM/bluesky.git
```

Point the framework at it via `BLUESKY_REPO`:

```bash
# Windows (PowerShell)                    # POSIX
$env:BLUESKY_REPO = "C:\...\bluesky"      export BLUESKY_REPO=/path/to/bluesky
```

### 4.3 LLM endpoint

Edit the `llm:` block of [`config/phase3_config.yaml`](config/phase3_config.yaml):

```yaml
llm:
  model: corp-ai/openai/deepseek-v4-pro
  base_url: http://<your-host>:<port>/v1
  api_key_env: CORP_AI_API_KEY
  max_tokens: 8192
```

Then set the key (`CORP_AI_API_KEY`, or `~/.dsh/.credentials.yaml`). See
[`.env.example`](.env.example) for the environment variables the code reads.

---

## 5. Quick start

```bash
# Single in-process run (E4 4B, arm D10, LLM policy, seed 20240601)
python tools/run_experiment4.py --sub 4B --arm D10 --manager B4b \
    --seed 20240601 --scenario E4_ANCHOR --cohort primary --direct

# Full E4 sweep (parallel workers)
python tools/run_experiment4.py --sub 4A --manager all --jobs 8

# Cross-site experiments (3 sites A/B/C)
python tools/run_experiment1_cross_site.py --help
python tools/run_experiment2_cross_site.py --help
python tools/run_experiment3_cross_site.py --help

# Analyze
python tools/analyze_experiment4.py primary
```

Runs are written under `runs/<experiment>/<cohort>/...`; `--force` re-runs current runs.
`tests/` are standalone scripts (no pytest): `python tests/test_experiment4_acceptance.py`.

---

## 6. Reproducing the paper

1. Install the environment (Section 3) and configure SUMO / BlueSky / LLM (Section 4).
2. Run the framework sweeps with the `tools/run_*.py` dispatchers (Section 5).
3. Follow [`manuscript/REPRODUCTION_README.md`](manuscript/REPRODUCTION_README.md) and
   `manuscript/reproduce_analysis.ps1` to reproduce the numerical analysis and figures
   from the saved run artifacts and the frozen `manuscript/overleaf/reproducibility/`
   package. The postprocessing is LLM-free; `-RunRegression` adds the documented
   deterministic regression runs (requires SUMO/traci).

The LLM endpoint and BlueSky path are the only machine-specific settings.
