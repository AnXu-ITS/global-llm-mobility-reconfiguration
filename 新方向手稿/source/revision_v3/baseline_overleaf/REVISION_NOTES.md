# Transportmetrica B manager manuscript — revision v2

2026-09-12。已按用户要求完成三部分继续修改、Figure 1 混合重绘及本地 Overleaf 同步。原始 v1 和 Figure 1 A/B 均保留。

## 三部分修改

1. **Related work 与交通研究定位**：围绕跨服务扰动传播、动态车队与 ground–air routing、统一约束下的 supervisory selection 重写 Section 2。补充 4 篇已核对的相关工作，承认多模态资源分配、动态路径与重平衡已有基础；gap 收束为可执行候选接口与同约束下的策略比较。
2. **Results 与 Figures 2–8**：按“协调及既有服务代价 → interface ablation → 路径恢复与准时恢复 → compound loss → morphology → timing”组织。Results 从约 3,947 词压缩到 1,913 词（同一统计口径，含图表文字）。正文从约 12,729 词降至 9,646 词。15 个原表的数据块完整保留，正文 6 个、SI 9 个；补充稿约 2,168 词。Figures 2–8 字体和图例统一，10 个原生图表的 202 个缓存数值逐个核对，最大变化为 0。Figure 7 使用直线连接离散实验设置，不再出现自动平滑或自动变色的标记。
3. **Methods 的服务耦合及边界**：Section 4.1 与 5.6 对照既有实现澄清：地面 fallback 使用 SUMO D1–H1 corridor ETA 并以 mission timer 表示；不生成每项任务专用的地面取货/接驳轨迹。registry 表示 mode/resource/status 变更，不表示物理货物交接过程。外部推理调用不推进物理仿真时钟，E4B modeled waiting 与 backend wall latency 分开解释。三个站点是相异网络情境，不是独立识别 morphology 因果效应的设计。

## 稳定术语与论断清单

| 项目 | v2 固定表达/证据边界 |
|---|---|
| 核心贡献 | Ground–Low-Altitude Mobility Manager；shared executable candidate interface |
| B0 | ground-only reference / no coordination |
| B1 | air-first rule |
| B2 | fixed-objective heuristic；fixed-preference structured comparator；Equation (9) 原样保留 |
| B4b | LLM-candidate policy；primary comparison 中的一种实现 |
| B4a | E1 interface ablation；不是第五个 primary manager |
| 聚合结果 | comparable aggregate performance 不等于统计等效，也不等于 LLM 普遍优于其他策略 |
| 不利及空结果 | 保留 E2 Site A 的 B4b 比 B2 慢、E3 配对无显著优势、Site C 多层级无协调增益，以及 E1 速度与服务保留的权衡 |
| interface 效应 | Site A 最明显；其余站点效应较弱或缺失 |
| recovery | executable recovery path 不保证 timely completion |
| 时间 | observation schedule、proposal execution wait、wall-clock inference latency 是不同量 |
| 形态 | 与设施位置、航程和适配故障时间共同变化；不做城市总体或纯形态因果外推 |
| 可行性 | 模型内规则检查；不等于完整航空运行安全认证 |

13 个 Markdown 显示公式原样保留。LaTeX 仅对 Equation (12) 分行，集合和分段损失定义不变。引用的 B2 权重与 prompt 哈希仍为原冻结版本，没有重新标定。

## 表格位置

正文 Table 1–6：interface、policy、morphology、experimental design、E1 interface paired comparison、E2 paired comparison。

| SI 表 | 保留内容 |
|---|---|
| S1 | E1 全策略描述结果 |
| S2 | E2 全策略结果与条件性恢复区间 |
| S3 | E3 各 level 的 SWL |
| S4 | E4A observation |
| S5 | E4B execution waiting |
| S6 | E4C input burden |
| S7 | E3 全场景聚合结果 |
| S8 | notation |
| S9 | action vocabulary |

## 已完成校验

- 正文 **25 页**、补充材料 **6 页**；pdfLaTeX/BibTeX 编译完成，无 undefined citations、LaTeX warnings 或 overfull boxes。
- 22 个参考文献键均解析；正文 8 图、6 表，SI 9 表；全部页面渲染后检查。
- Figure 1 为 C 混合版：85 个原生文字对象、23 处插画摆放；图中文字可编辑。复杂图形与源图风格接近；默认 PDF 已嵌入引言后的主图位置。
- 原始冻结实现、prompt、配置、发布结果及既有 metrics 中 **11,578 个保护文件** SHA-256 未变。
- 本轮没有运行实验、调用决策后端、改动数据或调整 B2 objective。

## 本地交付

`manuscript_tranb_manager_v2.md` 与 `supplement_tranb_manager_v2.md` 是修改执行稿。`overleaf/main.tex`、`supplement.tex`、`references.bib`、`figures/` 与 `editable_figures/` 已同步；编译结果为 `overleaf/main.pdf` 和 `overleaf/supplement.pdf`。这是用户指定路径的本地同步；未进行远端提交。

真实作者、单位与联系方式尚未提供，因此沿用原模板占位信息；正文实验内容没有据此补造。独立插画和字体说明见 Figure 1 README，新增文献核对依据见 `source/revision_v2/reference_verification.md`。

## 可复核文件

`source/revision_v2/text_integrity.json`；`figure_export_integrity.json`；`latex_source_checks.json`；`latex_pdf_qa.json`；`figure1/.build/integrity_result.json`。原 Overleaf 主文件与文献表备份位于 `source/revision_v2/overleaf_*_before.*`。复现图表仅读取既有发布数据。
