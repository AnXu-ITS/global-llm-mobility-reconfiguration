# Reproduction and source guide — revised manuscript

Run from the manuscript directory (`manuscript/`). Parent-project code and run logs are inputs only. All revision outputs are under `source/revision_v3`; the original 25/6-page source package is retained in `source/revision_v3/baseline_overleaf`. The current authoritative sources are `overleaf/main.tex` and `overleaf/supplement.tex`; their revised PDFs use separate job names. Do not run a legacy manuscript builder over these files.

## Build PDFs (requires MiKTeX/TeX Live and BibTeX)

```powershell
Set-Location overleaf
pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_revised main.tex
bibtex main_revised
pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_revised main.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_revised main.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=supplement_revised supplement.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=supplement_revised supplement.tex
```

## Reproduce analysis

`./reproduce_analysis.ps1` performs postprocessing only, using saved regression outputs. Python needs numpy, scipy, pandas, shapely, sumolib and networkx; the parent project's tool imports must remain available. `-RunRegression` explicitly adds the documented 27 deterministic runs, requiring SUMO, traci and the parent's simulation dependencies. It does not call an LLM. No full experiment matrix is launched.

Processing order: inspect_evidence.py → morphology_boundary.py → verify_details.py → optional run_regression.py → analyze_revision.py → finalize_data.py. `finalize_data.py` must follow the general analysis to insert the corrected B0 cell and rebuild E4 comparisons. `rewrite_manuscript.py` then `refine_text.py` regenerate text/tables from the archived baseline and data; these are deliberate source regeneration steps and should not be run after manual prose edits without reviewing the diff.

Original inputs: parent `outputs/paper_final/results.json`, `e2_[a,b,c]_run_metrics.json`, `e4_run_metrics.json`; parent `runs/experiment1_final`, `runs/experiment1_cross_site`, `runs/experiment2`, `runs/experiment2_cross_site`, `runs/experiment3`, `runs/experiment3_cross_site`, and `runs/experiment4/primary`. Actual run-relative paths are preserved in all_metrics.json, decision_regimes.json and transfer_margins.json. Raw logs are not duplicated into the submission ZIP; reproduction of simulations requires the parent project. Derived observations, numerical results, copied parameter/prompt/schema files and inventory are included in `overleaf/reproducibility`.

The queue correction is a local subclass in `source/revision_v3/queue_fix.py`; parent code is unchanged. `regression/D60_F360` contains the 20 corrected B0 runs; other subdirectories contain controls. `details_verified.json` contains initial-state/queue evidence; do not interpret its naive missions.csv interruption-duration field as full cumulative cost. The defensible complementary measure is `persistent_interruption_duration.json`.

## Editable figures

Current deliverable decks: `overleaf/editable_figures/Figure1_revised.pptx` and `Figures2_to_8_revised.pptx`. PDF figure assets in `overleaf/figures/fig01.pdf` through `fig08.pdf` are vector PowerPoint exports. Figure 1 uses separate illustration assets; the whole figure is not flattened. Source builders are `figure1/.build/build_figure1_revised.mjs` and `source/build_figures_v3.mjs`; `prepare_figures.py` creates these from the retained prior builders. They require @oai/artifact-tool and the locally configured presentation finalization utilities. Map geometry is `.build/geometry.json`; Figure 1 asset paths are defined in its builder. Choose unused HYBRID_STEM / FIGURE_PPTX_NAME environment values to avoid overwriting a finalized deck. PowerPoint export uses `figure1/.build/export_revision_powerpoint.ps1`; `export_and_render.py --figures` copies/scales the selected native PDFs, and without arguments renders manuscript QA pages using pymupdf/Pillow.

Statistical scope is the fixed scenario panel with equal original scenario/run weights and paired seed blocks. Do not treat run count as the count of independent sampling units. Transfer sensitivity is an offline assumed additional-time analysis, not closed-loop scheduling. Files contain local source paths for traceability; no public repository URL has been assigned.
