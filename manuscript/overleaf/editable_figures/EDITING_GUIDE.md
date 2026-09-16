# 当前人工改图入口

所有图使用 Times New Roman。Figure 1 保留作者的 PowerPoint 修改；正文 Figures 2–6 的当前编辑源为 editorial/output/ 下的 SVG，亦可修改 Python 源后重新生成。最新版本按内容采用不同的开放布局，主文图导出字号为 9.5–12 pt；上一版带框图组与文档保存于 ../archive/figures_boxed_20260914/。

| 论文图号 | 当前编辑源 | LaTeX 图文件 |
|---|---|---|
| Figure 1 | Figure1_revised.pptx | figures/fig01.pdf |
| Figure 2 | editorial/output/Figure2.svg | figures/fig02.pdf |
| Figure 3 | editorial/output/Figure3.svg | figures/fig03.pdf |
| Figure 4 | editorial/output/Figure4.svg | figures/fig04.pdf |
| Figure 5 | editorial/output/Figure5.svg | figures/fig06.pdf |
| Figure 6 | editorial/output/Figure6.svg | figures/fig07.pdf |
| Figure S1 | 归档七页 PPT，第 4 页 | figures/fig05.pdf |
| Figure S2 | 归档七页 PPT，第 7 页 | figures/fig08.pdf |
| Figure S3 | editorial/output/FigureS3.svg | figures/figS03.pdf |

七页 PPT 位于 ../archive/figures_pre_editorial_20260914/Figures2_to_8_revised.pptx。其余旧主文图页仅供历史对照，不再覆盖当前图件。S1 原生图表及 S2 时间线的编辑对象仍完整保留。改动前的文档、图件与源码亦保存在同目录的 ZIP 中。

editorial/source/build_editorial_figures.py 从旁边的原数据快照生成 PDF、SVG 与 300 dpi PNG，执行最终 panel 对齐检查，并输出数值溯源记录。柱、点、区间、热图格和地图路段都是矢量；SVG 文字未转曲，可单独编辑。完整配色、字号和线宽规则见项目根目录 FIGURE_STYLE_GUIDE.md。

重新生成图并编译论文：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build.ps1 -ExportFigures
```

该命令先备份，再从 PPT 导出 Figure 1 和 S1/S2，从 Python 生成正文 Figures 2–6 和 S3，最后编译主文与补充材料。旧七页 PPT 的主文图页不会写回当前图件。

直接修改 SVG 后，请自行将修改同步到对应 PDF，并将相同改动写回 Python 源；否则重新生成会恢复 Python 中的版式。只改论文文字时，运行 scripts/build.ps1，不要加 -ExportFigures。

Figure 5 的原差值面板现为 Figure S3；全部 12 组配对均值和原 95% seed-block 区间均保留。图文件稳定编号与论文图号不同，请按上表维护引用。
