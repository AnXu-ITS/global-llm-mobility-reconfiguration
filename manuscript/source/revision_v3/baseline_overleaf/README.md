# Transportmetrica B — manager manuscript v2

This folder contains the locally synchronized revision requested on 12 September 2026.

## Compile

Set `main.tex` as the Overleaf main document and select pdfLaTeX. The project includes `interact.cls`, its existing supporting style files, and `tfcad.bst`.

```sh
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

For the separate supplementary PDF, set `supplement.tex` as the main document, or run pdfLaTeX on it twice. The supplementary file has no external bibliography dependency.

## Files

- `main.tex`, `references.bib`: revised manuscript, 22 references.
- `supplement.tex`: nine supplementary tables and implementation/statistical conventions.
- `main.pdf` (25 pages), `supplement.pdf` (6 pages): successfully compiled local previews.
- `figures/fig01.pdf`–`fig08.pdf`: final paper figures. Figure 1 uses independent high-resolution illustrations plus vector text. Figures 2–8 are vector exports.
- `editable_figures/Figure1_hybrid_reference.pptx`: native editable text, routes, nodes and layout; independently embedded illustrations.
- `editable_figures/Figures2_to_8.pptx`: editable diagrams and native charts.
- `REVISION_NOTES.md`: changes, evidence boundaries and integrity results.

All paths used by the LaTeX documents are relative. Figure 1 is placed at 180 mm width; keep its aspect ratio. It is a schematic overview, not measured network data. The artwork provenance is described in Supplementary Section S5.

No experiment, frozen policy, prompt, objective or source dataset was changed. The author, affiliation and contact details retain the original template placeholders and should be filled with the actual information before submission.

The folder is ready for local editing or import into Overleaf. Local synchronization does not indicate a remote Git push or journal submission. Generated auxiliary files and PDFs are ignored by Git; PDFs remain available in this folder.
