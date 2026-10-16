# Online supplementary material for the ITSAC paper

**A Ground-Low-Altitude Mobility Manager for Service Reconfiguration under Disruptions**  
An Xu, Chengbo Zhang and Yunfei Yin.

## Start here

**[Open the supplementary PDF](ITSAC_Supplement.pdf)**: 20 pages, 20 tables and 9 extended figures.

The conference submission has no separate supplementary-file field. This public, paper-specific directory provides the extended evidence. The revised eight-page main manuscript contains the essential method, experimental definitions, key quantitative results and limitations without requiring the reader to consult this archive.

This paper uses branch `itsac-restored-20261016`, which restores the pre-pivot project at commit `3078ffb60d58952b4c193b2edb1de7d85375bbab`. The repository's `main` branch is a later research direction and is not evidence for this paper.

### Manuscript version

The author-facing revised files are `ITSAC_Final_Academic_Revision.pdf` and `ITSAC_Final_Academic_Revision.docx`, supplied in the revised submission package. The [PDF](../ITSAC_LNEE_8pages.pdf) and [Word file](../ITSAC_LNEE_8pages.docx) already in the repository are the **preceding compression draft**, not this revised main paper. Use the main manuscript submitted through the conference system as authoritative.

The final academic revision retains five main figures: Fig. 1 is the original four-panel overview, Fig. 2 the study networks, Fig. 3 E1 outcomes, Fig. 4 matched policy choices, and Fig. 5 compound service loss. Figure 1 and its caption are unchanged from the supplied original-figure-restored submission package. The supplement PDF and its historical numerical results are unchanged. The [earlier revision notes](REVIEW_REVISION.md) describe a superseded three-figure manuscript; their figure mapping and filenames do not apply to this final version. No new simulation or language-model cohort was executed.

## Where to find the supporting evidence

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
| Reproduction and recovery boundaries | S3, S5-S6; this README and the revision notes |

[Supplement LaTeX source](source/supplement.tex) and [vector figure assets](source/figures/) are available. Final main Fig. 4 uses the decision evidence retained in Fig. S7; supplement numbering has not changed. Main Fig. 1 preserves the original conceptual overview, and its symbols and bars are qualitative.

## Recovered data and code

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

There are **11,140 per-run metric records: 10,960 primary runs and 180 additional ablation runs**. Records are not independent experimental replicates; statistical inference retains fixed-panel seed dependence. Some recorded source paths refer to unavailable historical raw directories.

## Offline numerical verification

From the repository root, with Python, NumPy and SciPy installed:

```bash
python itsac/verify_restored_metrics.py
```

The script recomputes saved-metric means, seed-block intervals and paired comparisons, including the corrected B0 D60 duration of 242 s and retained B4b duration of 302 s. The [verification report](verification/metric_verification.json) records 879 passed numerical checks. The verifier was rerun during the final academic revision on 16 October 2026 and again passed all 879 checks. E2 timely completions conditional on restoration were additionally counted from saved metrics and cross-checked against transfer-margin records: B1/B2 each have 80/200 at Suzhou, 80/200 at Amsterdam and 0/200 at Edmonton; B4b has 75/191, 80/199 and 0/201, respectively. These conditional counts are distinct from all-run deadline-violation rates.

The verifier does not launch SUMO, BlueSky or an LLM/API call. It cannot recreate missing raw trajectories. The [historical reproduction guide](../../manuscript/REPRODUCTION_README.md) requires unavailable original run/output directories for end-to-end postprocessing and is retained for provenance, not as a promise of full replay from this checkout.

To rebuild the unchanged supplementary PDF:

```bash
cd itsac/supplement/source
pdflatex -interaction=nonstopmode -halt-on-error supplement.tex
pdflatex -interaction=nonstopmode -halt-on-error supplement.tex
```

The prior two-figure compression draft can be rebuilt with `python itsac/build_figures.py`; the final five-figure manuscript is supplied as the author-facing Word/PDF pair. The repository manuscript files have not been replaced by this documentation update.

## Interpretation and integrity

Ground fallback uses a corridor-ETA timer rather than independently dispatched road vehicles. Payload custody, loading and physical transfers are absent. Added handling time is an assumed, offline sensitivity with decisions fixed. B0 comparisons include access to a different set of transport modes; B1/B2/B4b compare policies under shared candidate and execution rules. The 5-50-record input study keeps four active aircraft. Backend wall-clock inference is distinct from injected simulation waiting. Site geometry, facilities and fault timing vary together. The authors confirm that the LLM used was DeepSeek V4 Pro; the retained configured identifier is `deepseek-v4-pro`.

Some archived illustrative elements are AI-generated and do not depict observed deployment. Main Fig. 1 preserves the original conceptual artwork, including illustrative elements; it is not deployment evidence. Main Figs. 2–5 show the stated networks and archived numerical evidence. See [recovery provenance](../provenance/recovery.json), [claim-to-evidence map](../provenance/CLAIM_EVIDENCE.md) and [revision notes](REVIEW_REVISION.md).
