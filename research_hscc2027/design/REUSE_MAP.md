# 可复用资产索引

2026-09-18更新：240个源文件和地图已复制到 `vendor/legacy_platform/` 并保留PROVENANCE哈希。A/B/C沿用这些几何资产；D/E/F为重新下载OSM构建，来源位于 `sites/sources/`、选择依据位于 `sites/selection_rule.json`、入选资产位于 `sites/frozen/`。不修改vendor旧地图来冒充新场地。

新场地复用的是SUMO/BlueSky适配器和协议内核，设施/兼容矩阵/道路事件为新设计。A/B/C旧形态指标与D/E/F新signature不直接混用，须按统一算法重算。完整接入约束见 [实验协议v0.2](EXPERIMENT_PROTOCOL_v0.2.md)。

以下路径相对于 `legacy/20260918/`。列出的是候选复用来源，不代表已迁移或已通过新语义回归。

| 来源 | 复用内容 | 复用前的检查 |
|---|---|---|
| `sim/`、`config/` | A/B/C 路网、设施、场景构件 | 路由可达性、版本与坐标一致性 |
| `failures/` | F1–F6 故障注入 | 拆出事件源，避免同步推理重入 |
| `managers/` | B0/B1/B2 和提案接口 | 共同观测权限、真实计算耗时 |
| `safety/`、`schemas/` | 基础校验及动作接口 | 新任务/资源/载荷前置条件 |
| `orchestrator/sumo_adapter.py` | 地面车辆/路由接口 | 任务由真实抵达事件完成 |
| `orchestrator/bluesky_adapter.py` | 飞机和仿真接口 | 下发与物理生效日志分开 |
| `orchestrator/candidate_info_e3.py` | 多任务候选派生 | 新 ETA、交接与资源依赖 |
| `manuscript/source/revision_v3/queue_fix.py` | 修正版命令去重 | 作为 R0 来源，保留原语义锚点 |

旧 `runs/`、`outputs/`、缓存和旧论文主文不复制为新实验的默认输入/输出。需要历史诊断时使用明确路径及对应文件哈希。
