# Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions

[English](README.md) · [中文说明](README.zh-CN.md)

An LLM acts as a global supervisor that reconfigures a coupled **ground–low-altitude
mobility system** (SUMO road network + BlueSky airspace) when a disruption occurs.
The LLM observes a *global-state snapshot* (ground vehicles + aircraft + missions +
facilities), emits a structured action (`DISPATCH`, `REASSIGN`, `REROUTE`, …), and a
manager-agnostic **feasibility checker + executor** grounds the decision in the
co-simulation. This repository contains the frozen testbed, the experiment framework,
and the analysis tooling used for the paper.

---

## 1. Overview

- **Testbed** `S0_3p2km_v1` — a 3.2 km × 3.2 km canonical Suzhou area
  (center `31.30377, 120.59981`), 1800 s horizon, 1 s step.
- **Co-simulation** — SUMO 1.27.1 (ground) + BlueSky (air), stepped in lock-step.
- **Fleet** — `L-UAV-01` (logistics), `EVTOL-01` (passenger transfer),
  `M-UAV-01`, `M-UAV-02` (medical). A scheduled event closes a ground link and forces
  the supervisor to re-plan.
- **LLM** — an OpenAI-compatible chat-completions endpoint
  (`corp-ai/openai/deepseek-v4-pro` by default); the client is standard-library only
  (`managers/llm_client.py`), key from `CORP_AI_API_KEY` or `~/.dsh/.credentials.yaml`.

### Experiment series

| ID | Question | Arms |
|---|---|---|
| E1 | Baseline vs. method comparison (managers) | `B0/B1/B2/B4b` |
| E2 | Failure awareness | `F1…F6` |
| E3 | Global-state design | — |
| **E4** | **LLM operational limits** | `4A` info-update frequency · `4B` inference latency · `4C` global-state scale |

**E4 arms**

| Sub | Swept parameter | Values |
|---|---|---|
| 4A | observation interval (s) | `OBS10, OBS30, OBS60, OBS120, OBS300` |
| 4B | action latency (s) | `D00, D01, D05, D10, D20, D30, D60` |
| 4C | fleet size (candidate-table scale) | `N05, N10, N20, N30, N50` |

**Managers** (the only thing that changes between runs)

| ID | Manager | Meaning |
|---|---|---|
| `B0` | `NoCrossLayerManager` | ground-only baseline (no air dispatch) |
| `B1` | `RuleBasedManager` | hand-coded cross-layer rules |
| `B2` | weighted rule-based | rule-based with tuned weights |
| `B4b` | `LLMManager` (candidate table) | the LLM supervisor |

---

## 2. Repository layout

```
├── orchestrator/   experiment runners, SUMO/BlueSky adapters, registry, fleet
├── managers/       B0/B1/B2/B4b managers + LLM client
├── safety/         feasibility checker + semantic validator (manager-agnostic gates)
├── config/         scenario + experiment matrices + LLM (phase3_config.yaml)
├── tools/          run_experiment{1..4}.py dispatchers + analyze_*.py
├── sim/            SUMO network/routes + BlueSky scenario inputs
├── tests/          standalone acceptance tests (plain scripts, no pytest)
├── docs/           design documents
├── prompts/        LLM prompt templates
├── schemas/        JSON schemas for LLM action validation
├── failures/       failure-injection models (E2)
├── state/          global-state model
├── reports/        independent reviews / audits
├── 新方向手稿/      manuscript workspace (paper + reproducibility package)
└── archive/        historical versions & old runs  (git-ignored)
```

Runtime outputs (`runs/`, `outputs/`) and `archive/` are **git-ignored** (they are
large and reproducible on demand).

---

## 3. Requirements

- **Python 3.14** (a virtualenv is recommended)
- **SUMO 1.27.1** — installed automatically via the `eclipse-sumo` pip wheel
- **BlueSky** — a *source checkout* (not pip); see Setup
- Python packages — see [`requirements.txt`](requirements.txt)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   POSIX: source .venv/bin/activate
pip install -r requirements.txt
```

---

## 4. Setup

### 4.1 SUMO

`eclipse-sumo` is in `requirements.txt`. At runtime `orchestrator/sumo_env.py`
imports `sumo` to locate `SUMO_HOME` and add `traci`/`sumolib` to the path — no
separate SUMO install is required.

### 4.2 BlueSky

BlueSky is imported **from source** (in-process, `orchestrator/bluesky_adapter.py`).

```bash
git clone https://github.com/TUDelft-CNS-ATM/bluesky.git
```

Point the framework at it via the `BLUESKY_REPO` environment variable:

```bash
# Windows (PowerShell)                    # POSIX
$env:BLUESKY_REPO = "C:\...\bluesky"      export BLUESKY_REPO=/path/to/bluesky
```

The historical checkout used for the paper is commit `dfdff5d`.

### 4.3 LLM endpoint

Edit the `llm:` block of [`config/phase3_config.yaml`](config/phase3_config.yaml):

```yaml
llm:
  model: corp-ai/openai/deepseek-v4-pro
  base_url: http://<your-host>:<port>/v1
  api_key_env: CORP_AI_API_KEY
  max_tokens: 8192
```

Then provide the key:

```bash
# Windows (PowerShell)                    # POSIX
$env:CORP_AI_API_KEY = "sk-..."           export CORP_AI_API_KEY=sk-...
```

(`managers/llm_client.py` also falls back to `~/.dsh/.credentials.yaml`.)

---

## 5. Quick start

```bash
# Single in-process run (E4 4B, arm D10, LLM manager, seed 20240601)
python tools/run_experiment4.py --sub 4B --arm D10 --manager B4b \
    --seed 20240601 --scenario E4_ANCHOR --cohort primary --direct

# Full sweep (parallel subprocess workers)
python tools/run_experiment4.py --sub 4A --manager all --jobs 8

# Analyze results -> outputs/experiment4_summary.md + .json
python tools/analyze_experiment4.py primary
```

Runs are written under `runs/experiment4/<cohort>/<sub>/<arm>/<scenario>/seed<seed>/<manager>/`.
`--force` re-runs existing (current) runs.

### Tests

Tests are standalone scripts (no pytest):

```bash
python tests/test_experiment4_acceptance.py
python tests/test_acceptance.py
```

---

## 6. Reproducing the paper's results

1. Install the environment (Section 3) and configure SUMO / BlueSky / LLM (Section 4).
2. Run the primary sweep for each experiment (e.g. `tools/run_experiment4.py`).
3. Analyze (`tools/analyze_experiment4.py`) and compare against
   `outputs/experiment4_summary.json` / the manuscript's reproducibility package
   (`新方向手稿/overleaf/reproducibility/`).

The E4 primary results (1360 runs) are summarized in `outputs/experiment4_summary.md`
and `.json`. The LLM endpoint and BlueSky path are the only machine-specific settings.
