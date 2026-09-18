# 论文与复现：从这里开始

## 目录用途

- `overleaf/`：当前论文交付（`main.tex`、`supplement.tex`、`references.bib`、`figures/`、
  `editable_figures/`、`reproducibility/`）。修订版 PDF 为 `main_revised.pdf` 与
  `supplement_revised.pdf`。
- `source/revision_v3/`：数值分析脚本与派生数据（含 `queue_fix.py` 修正覆盖层、
  `regression/` 回归运行、`baseline_overleaf/` 原始 25/6 页源包）。
- `figure1/`：Figure 1 构建器与素材。
- `REPRODUCTION_README.md` + `reproduce_analysis.ps1`：分析/图件复现入口。
- `REVISION_SUMMARY.md`：实质修订说明。

已归档到仓库根目录 `archive/manuscript_workspace/`（git 忽略）的迭代与过程目录不再出现在
本仓库中：`人工改图入口/`、`figures_revised/`、`figure_design_*/`、`language_edit_*/`、
`scientific_clarity_*/`、`source/figure_redesign/`、`source/figure_typography/`、`.build/`
等。

## 编译 PDF（需 MiKTeX/TeX Live + BibTeX）

```powershell
Set-Location overleaf
pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_revised main.tex
bibtex main_revised
pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_revised main.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_revised main.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=supplement_revised supplement.tex
```

图件编辑与自动生成以 `overleaf/editable_figures/` 中的 PPT 为准；细节见
`overleaf/editable_figures/EDITING_GUIDE.md` 与 `REPRODUCTION_README.md`。
