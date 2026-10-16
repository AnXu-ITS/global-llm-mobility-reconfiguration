# 扰动下地面与低空服务重构

[English](README.md) · [论文](itsac/ITSAC_XU_AN.docx) · [补充材料](itsac/supplement/)

本分支提供 ITSAC 论文 *A Ground–Low-Altitude Mobility Manager for Service Reconfiguration under Disruptions* 的代码、配置及保存结果。研究问题是：地面服务受到扰动时，如何利用低空资源按期恢复紧急服务，同时减少对已有任务的影响。

Manager 共享候选信息，比较完成时长与已有服务代价，并在执行前重新检查所选方案。实验使用 SUMO–BlueSky，在苏州、阿姆斯特丹和埃德蒙顿三个道路网络上考察选择性低空支援、故障恢复、复合扰动和观测—执行时效。

## 论文与数据

论文材料位于 `itsac-restored-20261016` 分支；默认 `main` 分支为独立的后续研究。[Word 文件](itsac/ITSAC_XU_AN.docx)为作者提供的最终稿。[补充材料目录](itsac/supplement/)提供扩展图表、来源和数据链接。

归档保留 11,140 条逐运行指标，其中主实验 10,960 条、候选信息消融 180 条，另有 27 次确定性回归运行。保存的指标可用于重新计算统计结果；缺失的完整历史原始轨迹不能从这些指标恢复。

## 离线核验

安装 Python、NumPy 和 SciPy 后，在仓库根目录运行：

```bash
python itsac/verify_restored_metrics.py
```

脚本重新计算均值、按种子分块的区间和配对比较，不启动仿真器或调用模型。[复现说明](manuscript/REPRODUCTION_README.md)列出历史分析流程所需的额外输入及其边界。

## 实验与实现

| 实验 | 研究内容 |
|---|---|
| E1 | 低空支援的收益与已有任务损失 |
| E2 | 替代路径恢复与按时完成之间的区别 |
| E3 | 复合扰动下剩余替代方案的作用 |
| E4 | 观测间隔、执行等待与输入记录数量的影响 |

B0 为纯地面基线，B1 按规则选择空中候选，B2 使用固定目标启发式，B4a/B4b 使用 DeepSeek V4 Pro。B4a 与 B4b 的区别是派生候选信息支持；两者保留共同的原始状态、提示规则及执行检查。

环境配置、目录说明及运行入口见 [英文 README](README.md)。模型提示词、配置和动作 schema 是实验复现材料，分别保存在 `prompts/`、`config/` 和 `schemas/`。

模型采用地面 ETA 计时器，未模拟实际载荷装卸和交接。模型推理的墙钟耗时不推进仿真时间；E4 单独施加执行等待。输入规模实验始终只有四架活跃飞机。结论限于给定的服务级仿真与固定场景面板。
