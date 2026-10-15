# Supplementary material for the ITSAC paper

**A Ground-Low-Altitude Mobility Manager for Service Reconfiguration under Disruptions**

An Xu, Chengbo Zhang and Yunfei Yin.

This is the paper-specific supplement on branch `itsac-restored-20261016`. The branch restores the pre-pivot project at commit `3078ffb60d58952b4c193b2edb1de7d85375bbab` and adds the eight-page Springer LNEE manuscript. The repository's `main` branch remains the later research project. Results from that later direction are not used here.

## Read the paper and extended results

- [Eight-page manuscript PDF](../ITSAC_LNEE_8pages.pdf), including all references.
- [Editable Word manuscript](../ITSAC_LNEE_8pages.docx), following the author-supplied LNEE template, with native Word equations.
- [Supplementary PDF](ITSAC_Supplement.pdf): 20 pages, 20 tables and 9 extended figures.
- [Supplementary LaTeX source](source/supplement.tex) and [original vector figure assets](source/figures/).
- [Compact manuscript figure sources](../figures/) and [manuscript content](../manuscript_source/paper_content.json).

The main paper retains the problem, policy definitions, experimental design, core results, statistical interpretation and limitations. The supplement contains full outcome tables, action and input definitions, fault state machines, statistics, handling-time sensitivity, network descriptors and extended graphical evidence.

## Recovered data and code

| Material | Location | Recovery status |
|---|---|---|
| E1–E3 per-run metrics | [all_metrics.json](../../manuscript/source/revision_v3/all_metrics.json) | 9,780 records, including 180 B4a ablation runs |
| Corrected E4 per-run metrics | [e4_run_metrics_revised.json](../../manuscript/source/revision_v3/e4_run_metrics_revised.json) | 1,360 records; includes the 20 corrected B0 D60 observations |
| Archived numerical summaries | [results_revised.json](../../manuscript/source/revision_v3/results_revised.json) | Preserved without numerical edits |
| Candidate decision summaries | [decision_regimes.json](../../manuscript/source/revision_v3/decision_regimes.json) | Derived decision records, not complete candidate logs |
| Transfer sensitivity | [transfer_margins.json](../../manuscript/source/revision_v3/transfer_margins.json) and [transfer_summary.json](../../manuscript/source/revision_v3/transfer_summary.json) | Archived offline trajectory-fixed sensitivity |
| Experiment configurations | [config/](../../config/) | Restored site, seed, failure and policy configuration files |
| Prompts and schemas | [prompts/](../../prompts/) and [schemas/](../../schemas/) | Restored, including the explicit-candidate prompt |
| Simulation and policy code | [orchestrator/](../../orchestrator/), [managers/](../../managers/), [failures/](../../failures/), [safety/](../../safety/) | Restored pre-pivot implementation |
| Road networks | [sim/sites/](../../sim/sites/) | Three original study sites |
| Queue correction | [queue_fix.py](../../manuscript/source/revision_v3/queue_fix.py) | Retained correction overlay; historical base queue remains distinct |
| Saved deterministic regressions | [regression/](../../manuscript/source/revision_v3/regression/) | 27 archived runs, including 20 corrected B0 D60 seeds |
| Full historical raw logs | Original `runs/` and `outputs/` | **Not recovered**: these directories were excluded from Git |

The recovered dataset contains **11,140 per-run metric records: 10,960 primary runs plus 180 extra ablation runs**. This is not a claim that every raw simulation trace has been recovered. Some recorded `source_run` paths refer to the original, unavailable raw folders.

## Offline verification

From the repository root, with Python, NumPy and SciPy installed:

```powershell
python itsac/verify_restored_metrics.py
```

This command reads the committed metrics and recomputes principal E1–E3 means and seed-block confidence intervals, E1 ablation and scenario contrasts, all E2 comparison endpoints, E3 compound comparisons and E4 completion/deadline summaries. It verifies the corrected B0 D60 result of 242 s separately from the retained B4b result of 302 s. The [verification report](verification/metric_verification.json) records **879 passed numeric checks**, file hashes and comparison details.

The verification does **not** launch SUMO, BlueSky or any LLM/API call. It does not reconstruct metrics from missing raw logs. The historical [full reproduction guide](../../manuscript/REPRODUCTION_README.md) is retained for provenance, but its end-to-end analysis requires the missing original run/output directories and should not be presented as fully executable from this checkout alone. Some legacy summary fields retain older interval conventions; the paper uses the specified seed-block estimates and conditional restored/affected counts.

To rebuild the supplementary PDF:

```powershell
cd itsac/supplement/source
pdflatex -interaction=nonstopmode -halt-on-error supplement.tex
pdflatex -interaction=nonstopmode -halt-on-error supplement.tex
```

The compact figures can be rebuilt from the committed metrics with `python itsac/build_figures.py` (NumPy, SciPy and Matplotlib). The `.docx` is the editable manuscript source. Its original template styles and page geometry are retained; native Word export was used to verify eight-page pagination.

## Interpretation and provenance

- Ground fallback is a SUMO corridor ETA timer, not an individually dispatched ground vehicle.
- Payload custody and physical loading/transfer are absent. Added handling time is an offline assumed sensitivity.
- B0 comparisons include a change in available transport modes. B1/B2/B4b compare policy choice under common candidate and execution rules.
- The 5–50-record input experiment keeps four active aircraft.
- Inference wall-clock time is separate from injected simulation execution waiting.
- The three sites are fixed contexts; morphology, facility geometry and fault placement are not independently randomized.
- The backend string is the recorded configured identifier, not independently verified model-release provenance.
- The supplied ZIP's original diagram includes AI-generated illustrative elements. It is retained as a labeled conceptual supplement figure, not empirical evidence. The new main-paper diagram and chart are deterministic vector figures.

See [recovery provenance](../provenance/recovery.json) and [claim-to-evidence map](../provenance/CLAIM_EVIDENCE.md). The restoration preserves the later public archive's username redactions. Original inputs and historical metric values are otherwise retained.
