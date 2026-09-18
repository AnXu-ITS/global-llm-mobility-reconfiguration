# HSCC+ICCPS 2027 研究工作区

候选方向：**Deadline-Aware Runtime Supervision for Ground–Air Service Reconfiguration**。

本目录已于 2026-09-18 按新旧方向整理。旧项目有完整独立备份，新论文与新实验使用独立目录；旧批量数据的冗余工作区副本按校验清单清理。

| 入口 | 内容 |
|---|---|
| [转向计划书](HSCC_ICCPS_2027_研究方向转向计划书.md) | 用户提供的完整研究迁移方案，保持原文件 |
| [转向分析与处置矩阵](provenance/hscc2027/MIGRATION_ANALYSIS.md) | 核心贡献判断、本地风险、旧材料如何使用 |
| [新研究工作区](research_hscc2027/README.md) | 新设计、首版运行时、隔离回放与物理仿真 |
| [当前实现和验证](research_hscc2027/IMPLEMENTATION_STATUS.md) | 27 次 R0 回放、48 个 R1 用例、三组物理闭环开发对照及尚未通过的完整门 |
| [具体实验设计 v0.1](research_hscc2027/design/EXPERIMENT_PROTOCOL_v0.1.md) | R0–R5 实验协议、运行矩阵、GPT-6 Astra high 调用与验收 |
| [当前六场地协议 v0.2](research_hscc2027/design/EXPERIMENT_PROTOCOL_v0.2.md) | 新增D/E/F与R6；基础计划3821，可选440 |
| [新增场地落地报告](research_hscc2027/design/SITES_D_E_F_IMPLEMENTATION_v0.2.md) | 莱比锡、巴塞罗那、柏林真实OSM地图、物理诊断与待验收项 |
| [新 Overleaf 仓库](manuscript_hscc2027/) | 已克隆的独立 Git 仓库，当前为 ACM 示例模板 |
| [旧项目档案](legacy/20260918/) | 保留的旧仓库、设计、稿件、R0 证据；旧批量数据可从独立 ZIP 恢复 |
| [迁移校验报告](provenance/hscc2027/migration_verification.json) | 文件集合、内容哈希、修正对应与 Git 状态 |
| [恢复说明](provenance/hscc2027/RESTORE_LEGACY.md) | 独立备份位置、校验和恢复方式 |
| [后续工作](provenance/hscc2027/NEXT_STAGE_PLAN.md) | R0 桥接、异步诊断、物理交接和强基线验证 |

旧缓存与批量结果已完整备份；工作区副本按逐文件 SHA-256 核验后清理，恢复索引与执行日志在 `research_hscc2027/outputs/bootstrap/`。新方向不导入旧动作缓存，也不将旧结果作为新运行时的主要实验结果。

新论文在线项目：<https://www.overleaf.com/project/6aaca76497f5b6e09545fc20>。

本目录现在是资料容器。论文 Git 操作应在 `manuscript_hscc2027/` 执行；旧仓库 Git 操作对应 `legacy/20260918/`。旧 tracked 源码与历史 Git 提交保留；需要旧批量数据的历史脚本应在恢复副本中运行。

现已运行首轮开发仿真，尚未启动正式实验、实验模型调用或推送远程。独立备份在 `C:/Users/xuan1/research-backups/ground-air-legacy-20260918/`；它与本工作区分离，但仍处于同一台机器的 C 盘。
