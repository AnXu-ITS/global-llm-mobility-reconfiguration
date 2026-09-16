# Figures 2–6: flexible composition and larger text

This revision replaces the repeated boxed layouts with different compositions suited to maps, comparisons, decision behavior, heatmaps and timing. It retains the Figure 1 font and palette, all original quantitative values, and the existing main/supplement placement.

- `output/Figure2.pdf` through `Figure6.pdf`: updated manuscript figures.
- `output/Figure2.svg` through `Figure6.svg`: editable vectors with live text.
- `output/*.png`: 300 dpi previews.
- `output/FigureS3.*`: retained supplementary paired contrasts.
- `FIGURE_SET_PREVIEW.png`: overview, including the unchanged Figure 1 reference.
- `FIGURE_STYLE_GUIDE.md`: palette, enlarged type hierarchy, flexible layouts, line and legend rules.
- `source/`: Python builder, unchanged data snapshot and alignment helper.
- `qa/`: source preservation, font, alignment and rendered collision checks.
- The compiled main manuscript and supplement are at the Overleaf project root.

Run `python source/build_editorial_figures.py` with NumPy, Matplotlib and PyMuPDF. Times New Roman must be installed for matching typography. Every data panel remains vector based; no screenshot is used as an editable substitute. Direct SVG changes should also be transferred to the builder before regenerating.

Main figure text is 9.5–12 pt at the 510 pt export width; most labels are approximately 8–9 pt at the current manuscript width. Figure 6 uses a wider lower panel, so larger type does not squeeze three different questions into identical narrow plots.

The Overleaf editing guide maps manuscript figure numbers to the stable `figures/fig*.pdf` names. Figure 1 and supplementary S1/S2 retain their earlier editable sources. The preceding boxed figures and documents are preserved in `archive/figures_boxed_20260914/before_flexible_layout.zip`.
