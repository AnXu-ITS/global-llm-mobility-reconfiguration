# Editable figure package

- `output/Figure2–Figure6.pdf`: updated main figures (one file per figure).
- `output/Figure2–Figure6.svg`: editable vector sources with live text.
- `output/FigureS3.pdf` and `.svg`: the original Figure 5 paired differences, moved to the supplement.
- `output/*.png`: 300 dpi previews.
- `FIGURE_STYLE_GUIDE.md`: shared palette, font hierarchy, rules and evidence contracts.
- `source/build_editorial_figures.py`: reproducible Python builder; source data are beside it.
- `qa/`: rendered geometry, font-size, collision and source-preservation records.

Run `python source/build_editorial_figures.py` with Python, NumPy and Matplotlib installed. The supplied PDF/SVG files have no raster data panels. Times New Roman must be available to preserve the SVG typography when editing.

The new vector masters replace the old PowerPoint masters for main Figures 2–6. Figure 1 remains unchanged. Old documents and decks are archived in the manuscript repository, and its editing guide identifies the retained sources for supplementary Figures S1–S2.
