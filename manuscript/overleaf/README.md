# 当前论文工作库

当前版本包含英文语言编辑、服务链时间裕度表述与 2026-09-14 图组设计更新。正文保留 Figures 1–6；补充材料包含 Figures S1–S3。Figure 1 保留作者修改，Figures 2–6 使用同源的低饱和度配色与 Times New Roman 字体。最新图组采用按内容变化的开放版式，并将主文图的最小导出字号提高至 9.5 pt。

- main.tex、references.bib：主文和参考文献。
- supplement.tex：补充材料。
- main_revised.pdf、supplement_revised.pdf：当前编译预览。
- editable_figures/Figure1_revised.pptx：Figure 1 的原有编辑入口。
- editable_figures/editorial/output/：Figures 2–6、S3 的可编辑 SVG、矢量 PDF 和 PNG 预览。
- editable_figures/editorial/source/：Python 生成脚本及原数据快照。
- editable_figures/EDITING_GUIDE.md：当前论文图号、源文件和导出文件的对应表。
- FIGURE_STYLE_GUIDE.md：颜色、字号、线宽、panel 与图例规则。
- reproducibility/：参数、prompt、派生结果和局部修正代码。
- archive/：修改前文档及旧图件归档，包含作者的远端修改。

## 编译与改图

只改文字时运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

从当前编辑源重新生成图并编译时加 -ExportFigures。该命令先备份图件，再从 Figure 1 PPT 和归档七页 PPT 的 S1/S2 页导出相应图；其余图从 Python 源生成。需要 Windows PowerPoint、Python/NumPy/Matplotlib/PyMuPDF 与 pdfLaTeX/BibTeX。编辑 SVG 后若要保留手工调整，须同步生成脚本；直接运行重新生成会以脚本内容为准。

旧七页 PPT 和旧合并图集已移至 archive/figures_pre_editorial_20260914/。上一版带框图组及对应文档另存于 archive/figures_boxed_20260914/。它们的主文图页不再是当前编辑源。不要用旧生成器覆盖新的 SVG/PDF。

Overleaf 在线主文件选择 main.tex，编译器为 pdfLaTeX；补充材料单独选择 supplement.tex。远程 origin 指向现有 Overleaf 项目。同步前先获取远端修改，使用正常 Git 合并或快进，保留作者内容。
