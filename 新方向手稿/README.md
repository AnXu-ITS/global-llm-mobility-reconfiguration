# Transportmetrica B 论文初稿

当前英文初稿以 **Ground–Low-Altitude Mobility Manager** 为主线，按写作蓝图展开。LLM 是监督策略的一种实现；文稿同时报告简单策略收敛、跨场地差异和恢复路径与按时恢复之间的区别。

- [论文初稿](FIRST_DRAFT_TRANSPORTMETRICA_B.md)：完整英文正文、13 张表、8 幅图、18 篇参考文献及附录。
- [PowerPoint 矢量图源文件](figures/MANUSCRIPT_FIGURES.pptx)：每页对应一幅论文图。
- [写作蓝图](WRITING_BLUEPRINT_TRANSPORTMETRICA_B.md)：本次初稿的叙事与证据依据。

## 图片对应关系

| PPT 页码 | 论文图片 | 内容 |
|---|---|---|
| 1 | Figure 1 | 统一监督管理架构 |
| 2 | Figure 2 | Suzhou、Amsterdam、Edmonton 的路网、设施及地空连接 |
| 3 | Figure 3 | E1：完成时间、超时率与现有服务损伤 |
| 4 | Figure 4 | E1：候选接口消融及配对置信区间 |
| 5 | Figure 5 | E2：条件恢复率与全样本超时率 |
| 6 | Figure 6 | E3：分场地、分层级的加权服务损失 |
| 7 | Figure 7 | E4：观测间隔、执行延迟、输入负担 |
| 8 | Figure 8 | 60 秒执行延迟下的命令替换与完成时序 |

PPT 使用可编辑形状、连接线、矢量路径和原生图表；统计图的数值系列保留在内嵌工作簿中。Markdown 显示同源 PNG 预览。三站点图补回原有辅助地面 OD、辅助设施、背景低空服务和辅助低空连接；图注明确它们的场地背景作用，不将其表述为新增冻结主实验任务。没有为填满地图而虚构线路。

## 数据与版本

数值来源为 `../outputs/paper_final/results.json` 的 `paper_final_20260910` 冻结发布：10,960 个主实验运行和 180 个附加 B4a 消融运行。路网形态表来自已有 morphology CSV；图中道路和辅助线路读取 `../sim/sites/` 的现存几何与路线档案。

本次仅生成手稿与绘图产物，没有重新运行实验，没有改动原始数据、冻结 manager、prompt 或 B2 objective。统计检验直接引用冻结输出，未另设检验家族重新计算。

## 可维护源文件

- `source/manuscript.template.md`：正文与图注源文件。
- `source/build_manuscript.py`：读取冻结结果并填充表格和图片引用。
- `source/references.md`：参考文献列表。
- `source/extract_geometry.py`：只读提取已有道路、水体、设施及路线，不启动仿真。
- `source/build_figures.mjs`：生成 PowerPoint 图形和 PNG 预览，使用本机 bundled artifact-tool。
- `.build/`：中间文件、构建检查及早期图形版本，不属于论文提交材料。

若继续编辑，建议修改正文模板后重新生成 MD，避免后续构建覆盖直接写入最终 MD 的改动。图形构建默认保护已有 PPT；制作新版本时可设置 `FIGURE_PPTX_NAME` 为新文件名。

当前交付为供学术修改的第一稿。作者、机构、基金与最终公开数据地址需在投稿信息确定后补入。PPT 已通过包结构、页面边界、字体声明及原生图表检查，并逐图检查导出的预览；未声称已经在桌面 PowerPoint 中人工打开验证。
