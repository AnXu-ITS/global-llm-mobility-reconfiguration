# A Ground–Low-Altitude Mobility Manager for Service Reconfiguration under Disruptions

[中文说明](README.zh-CN.md) · [Paper](itsac/ITSAC_XU_AN.docx) · [Supplementary material](itsac/supplement/)

This repository provides the code, configurations and saved results for the ITSAC paper. The study asks how low-altitude resources can restore time-critical ground services under disruptions while preserving existing service commitments.

The manager shares candidate information across replaceable supervisory policies, compares completion estimates and incumbent-service costs, and revalidates selected actions before execution. SUMO–BlueSky simulations examine selective air support, recovery after failures, compound disturbances and observation–execution timing at Suzhou, Amsterdam and Edmonton.

## Paper and data

Use branch `itsac-restored-20261016` for this paper. The default `main` branch contains separate follow-up research. The [Word manuscript](itsac/ITSAC_XU_AN.docx) is the final file supplied by the authors. The [supplement](itsac/supplement/) contains extended tables, figures, sources and data links.

The archive retains **11,140 per-run metric records**: 10,960 primary runs and 180 candidate-information ablation runs. It also retains 27 deterministic regression runs. Complete historical raw trajectories are unavailable; the saved metrics support statistical recomputation, but cannot reconstruct the missing trajectories.

## Verify the numerical results

With Python, NumPy and SciPy installed, run from the repository root:

```bash
python itsac/verify_restored_metrics.py
```

The verifier recomputes means, seed-block intervals and paired comparisons and writes [its report](itsac/supplement/verification/metric_verification.json). It does not launch a simulator or call an LLM. See the [reproduction guide](manuscript/REPRODUCTION_README.md) for the historical analysis pipeline and its additional input requirements.

## Policies and experiments

| Policy | Selection rule |
|---|---|
| B0 | Ground-only service |
| B1 | Rule-based ranking of air candidates |
| B2 | Fixed-objective heuristic balancing completion duration and incumbent commitments |
| B4a | DeepSeek V4 Pro without derived candidate information |
| B4b | DeepSeek V4 Pro with derived candidate information |

B4a and B4b share the raw observations, prompt rules and execution checks. Their difference is access to derived candidate information, including air ETA, legality, deadline consequences and the affected incumbent service.

| Experiment | Question |
|---|---|
| E1 | When does air support improve emergency service, and what incumbent service does it displace? |
| E2 | When does restoring a replacement path also restore timely completion? |
| E3 | Which usable alternatives remain under compound disturbances? |
| E4 | How do observation intervals, execution waiting and input size affect outcomes? |

## Code layout

| Directory | Contents |
|---|---|
| `orchestrator/` | Experiment runners, simulator adapters, state and service registry |
| `managers/` | Supervisory policies and model client |
| `config/` | Site configurations, seeds, experiment matrices and policy settings |
| `prompts/`, `schemas/` | Experimental prompts and structured action contracts |
| `safety/`, `failures/` | Modeled feasibility checks and fault injection |
| `sim/` | SUMO and BlueSky inputs for the three study sites |
| `tools/`, `tests/` | Execution, analysis and acceptance scripts |
| `manuscript/source/revision_v3/` | Saved metrics, analysis scripts and regression records |
| `itsac/supplement/` | Supplementary PDF, sources and numerical verification |

## Simulation setup

The study used Python 3.14, SUMO 1.27.1 and a BlueSky source checkout, with a 1 s step, 900 s horizon and four active aircraft. Install the Python dependencies in [requirements.txt](requirements.txt):

```bash
python -m venv .venv
pip install -r requirements.txt
git clone https://github.com/TUDelft-CNS-ATM/bluesky.git
```

Set `BLUESKY_REPO` to the BlueSky checkout. For B4a/B4b, configure the OpenAI-compatible endpoint in [config/phase3_config.yaml](config/phase3_config.yaml) and provide the key through `CORP_AI_API_KEY`; see [.env.example](.env.example). The study used DeepSeek V4 Pro, recorded as `corp-ai/openai/deepseek-v4-pro`.

The experiment dispatchers expose their options through `--help`, for example:

```bash
python tools/run_experiment1_cross_site.py --help
python tools/run_experiment2_cross_site.py --help
python tools/run_experiment3_cross_site.py --help
python tools/run_experiment4.py --help
```

Fresh B4a/B4b simulation runs call the configured model endpoint. They are separate from offline verification of the published metrics.

## Model scope

This is a service-level simulation. Ground fallback uses an ETA timer; physical payload loading and handoff are not modeled. Feasibility checks implement the stated simulation constraints. Backend inference time does not advance simulation time; E4 injects execution waiting separately. E4C varies input records while keeping four active aircraft. The three sites form a fixed scenario panel rather than a sample of cities.
