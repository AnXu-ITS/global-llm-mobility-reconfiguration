# 新方向手稿：从这里开始

## 日常工作

1. **读稿、改论文**：打开 `overleaf/`。当前文件为 main_revised.pdf、supplement_revised.pdf、main.tex、supplement.tex。
2. **人工改图**：打开 `人工改图入口/`，双击 Figure 1 或 Figures 2–8 快捷方式。两者直接打开 overleaf 本地库中的当前 PPT。
3. **改图后更新论文**：保存并关闭 PPT，运行 `人工改图入口/改图后更新论文.cmd`，会备份图件、导出并编译。仅改文字可运行 overleaf/scripts/build.ps1。

## 目录用途

- `overleaf/`：唯一当前论文交付与 Git 本地库。
- `人工改图入口/`：PPT 快捷方式与更新按钮，无重复 PPT。
- `source/`、`figure1/`、`figures_revised/`、`.build/`：复现与自动生成依赖，保留原路径；不是日常人工编辑入口。
- `archive/`：旧稿、旧图、历史打包件、编译与 QA 中间文件；保留归档索引，没有删除原始内容。
- `REVISION_SUMMARY.md`：实质修订说明。
- `REPRODUCTION_README.md`、`reproduce_analysis.ps1`：分析复现入口。

注意：自动生成图件脚本可能覆盖人工编辑，因此人工改图后使用 overleaf/scripts/build.ps1 -ExportFigures，同步以 editable_figures 中的 PPT 为准。当前主文 25 页、6 张图；补充材料 12 页，含 Figures S1–S2。PPT 页序与新图号见 overleaf/editable_figures/EDITING_GUIDE.md。
