# Supplementary material

**A Ground-Low-Altitude Mobility Manager for Service Reconfiguration under Disruptions**  
An Xu, Chengbo Zhang and Yunfei Yin.

[Main manuscript](../ITSAC_XU_AN.docx) · [Supplementary PDF](ITSAC_Supplement.pdf) · [LaTeX source](source/supplement.tex)

This directory contains the extended results for the ITSAC paper: 20 tables and nine supplementary figures. Use the `itsac-restored-20261016` branch for this study; `main` contains separate follow-up research.

## Contents

| Main-paper topic | Supplement locations |
|---|---|
| Shared candidate interface, action vocabulary and operational parameters | S2; Tables S8-S11; archived overview in Fig. S4 |
| E1 service performance and incumbent commitments | Table S1; Figs. S6-S7; candidate-information ablation in Table S19 |
| Final main Fig. 4: matched policy choices | Fig. S7 and archived `decision_regimes.json` |
| E2 restoration versus timely completion | Table S2; Fig. S1; paired tests in Tables S12-S14 and S20 |
| Omitted physical transfer and added-time sensitivity | S4.2; Table S16 |
| Compound service loss | Tables S3, S7 and S15; Figs. S3 and S8 |
| Observation and execution timing | Tables S4-S5; Figs. S2 and S9; command correction in S4.1 |
| Input burden with four active aircraft | Table S6; Fig. S9 |
| Study networks and model scope | Table S18; Fig. S5; S4.3-S4.4 |
| Reproduction and recovery boundaries | S3, S5-S6 and this README |

The main manuscript has five figures: the manager overview, study networks, E1 outcomes, matched policy choices and compound service loss. Supplementary figures retain numbering S1–S9. Main Figure 1 is a conceptual overview; its symbols and bars are qualitative.

## Data and implementation

| Material | Location | Recovery status |
|---|---|---|
| E1-E3 per-run metrics | [all_metrics.json](../../manuscript/source/revision_v3/all_metrics.json) | 9,780 records, including 180 B4a ablation runs |
| Corrected E4 per-run metrics | [e4_run_metrics_revised.json](../../manuscript/source/revision_v3/e4_run_metrics_revised.json) | 1,360 records, including 20 corrected B0 D60 observations |
| Archived numerical summaries | [results_revised.json](../../manuscript/source/revision_v3/results_revised.json) | Historical results retained |
| Candidate decision summaries | [decision_regimes.json](../../manuscript/source/revision_v3/decision_regimes.json) | Derived decision records, not complete candidate logs |
| Transfer sensitivity | [transfer_margins.json](../../manuscript/source/revision_v3/transfer_margins.json), [transfer_summary.json](../../manuscript/source/revision_v3/transfer_summary.json) | Archived offline trajectory-fixed sensitivity |
| Experiment settings | [config/](../../config/) | Restored site, seed, failure and policy configurations |
| Prompts and schemas | [prompts/](../../prompts/), [schemas/](../../schemas/) | Restored inputs and action contract |
| Simulation and policies | [orchestrator/](../../orchestrator/), [managers/](../../managers/), [failures/](../../failures/), [safety/](../../safety/) | Restored pre-pivot implementation |
| Road networks | [sim/sites/](../../sim/sites/) | Three original study sites |
| Queue correction | [queue_fix.py](../../manuscript/source/revision_v3/queue_fix.py) | Correction overlay retained separately |
| Deterministic regressions | [regression/](../../manuscript/source/revision_v3/regression/) | 27 saved regression runs |
| Full historical raw logs | Original `runs/` and `outputs/` | **Not recovered**; excluded from Git |

The saved metrics contain **11,140 records: 10,960 primary runs and 180 additional ablation runs**. Statistical inference retains fixed-panel seed dependence. Recorded paths may refer to historical raw directories that are no longer available. Saved metrics permit statistical recomputation; they cannot recover missing complete trajectories.

## Numerical verification

From the repository root, with Python, NumPy and SciPy installed:

```bash
python itsac/verify_restored_metrics.py
```

The [verification report](verification/metric_verification.json) covers 879 numerical checks, including saved-metric means, seed-block intervals and paired comparisons. The corrected B0 D60 duration is 242 s; B4b remains at 302 s. This command does not launch SUMO, BlueSky or a model endpoint.

For E2, timely completions among restored chains are:

| Site | B1 | B2 | B4b |
|---|---|---|---|
| Suzhou | 80/200 | 80/200 | 75/191 |
| Amsterdam | 80/200 | 80/200 | 80/199 |
| Edmonton | 0/200 | 0/200 | 0/201 |

These conditional counts use restored chains as the denominator. All-run deadline-violation rates use 320 runs per site and policy.

The [reproduction guide](../../manuscript/REPRODUCTION_README.md) describes the historical analysis pipeline and its missing-input requirements. The [results-to-data map](../provenance/CLAIM_EVIDENCE.md) identifies the supporting records.

To rebuild the supplementary PDF:

```bash
cd itsac/supplement/source
pdflatex -interaction=nonstopmode -halt-on-error supplement.tex
pdflatex -interaction=nonstopmode -halt-on-error supplement.tex
```

## Model scope and provenance

Ground fallback uses a corridor-ETA timer. Payload custody, loading and physical transfers are not modeled. Added handling time is an offline sensitivity with decisions fixed. B0 differs in transport-mode availability; B1, B2 and B4b compare policies with shared candidate and execution rules. E4C varies input records while retaining four active aircraft. Backend inference time is distinct from injected simulation waiting. Site geometry, facilities and fault timing vary together.

The LLM used was DeepSeek V4 Pro; the retained configured identifier is `deepseek-v4-pro`. Some conceptual illustration assets are AI-generated and do not depict observed deployment. Numerical figures use the archived simulation evidence. Source commits and archive hashes are recorded in [recovery.json](../provenance/recovery.json).
