# Reproduction and data

## Saved-metric verification

The [ITSAC branch](https://github.com/AnXu-ITS/global-llm-mobility-reconfiguration/tree/itsac-restored-20261016) includes an offline verifier. From that branch's repository root:

```bash
python itsac/verify_restored_metrics.py
```

Python, NumPy and SciPy are required. The verifier uses the saved per-run metrics to recompute means, seed-block intervals and paired comparisons. It does not require SUMO, BlueSky or a model endpoint.

The archive contains 11,140 per-run metric records and 27 deterministic regression runs. Complete historical `runs/` and `outputs/` directories are unavailable. Saved metrics support statistical recomputation; they cannot reconstruct the missing full trajectories.

## Historical postprocessing

From `manuscript/`, `./reproduce_analysis.ps1` runs the following sequence:

```text
inspect_evidence.py -> morphology_boundary.py -> verify_details.py
    -> analyze_revision.py -> finalize_data.py
```

This pipeline requires the original run/output directories, plus NumPy, SciPy, pandas, Shapely, sumolib and NetworkX. It cannot run end to end from this checkout alone. `-RunRegression` also executes the deterministic regression set and requires SUMO, TraCI and the simulation dependencies. It makes no LLM calls. `finalize_data.py` inserts the corrected B0 D60 cell after the general analysis.

The original inputs are `outputs/paper_final/results.json`, the E2 and E4 per-run metric files, and the experiment run directories identified in the analysis scripts. Historical source paths remain in the saved records for traceability.

## Numerical conventions

The scenario panel retains its original weights. Uncertainty and paired comparisons use seed blocks; the number of runs is not the number of independent sampling units. Transfer sensitivity adds assumed handling durations to fixed recorded trajectories and does not reschedule the system.

The queue correction in `source/revision_v3/queue_fix.py` preserves the due time of an identical pending command. `regression/D60_F360/` contains 20 corrected B0 runs; the other regression directories contain controls. The corrected B0 D60 completion duration is 242 s. The retained B4b value is 302 s because its command changes. B1 control reruns take 342 s in the later runtime, compared with the archived 341 s; patched and unpatched controls share this difference, so the archived B1 analysis is retained.

`details_verified.json` records historical state and queue checks. Its simple interruption-duration field is not a cumulative service-cost measure. `persistent_interruption_duration.json` instead measures the exposure of services still interrupted at the observation horizon.

## Historical manuscript and figures

The LaTeX source in `overleaf/` predates the conference manuscript. Build it with pdfLaTeX, BibTeX, and two further pdfLaTeX passes; compile `supplement.tex` twice separately. The saved figure PDFs and editable PowerPoint files remain available. Some historical builders require `@oai/artifact-tool`, presentation utilities and local assets that are not bundled here.

The conceptual overview includes AI-generated illustration assets. These are schematic artwork, not observations of a deployed system. Numerical figures use the archived simulation data.
