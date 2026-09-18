# 首轮实现与验证记录 — 2026-09-18

最新R1更新：已修复双载荷共享bay及终态预留缺陷，新增独立状态检查、响应mailbox和条件进展验证；深度12枚举触及100万状态，**完整G1仍未通过**。详见 [R1验收记录](design/R1_ACCEPTANCE_v0.2.md) 与 [严格执行顺序](design/EXECUTION_PRIORITY_v0.1.md)。以下首轮记录保持为历史证据。

后续更新：D/E/F真实OSM地图和逐场地单载荷诊断已经完成，详见 [场地落地报告](design/SITES_D_E_F_IMPLEMENTATION_v0.2.md)；当前规划改用 [协议v0.2](design/EXPERIMENT_PROTOCOL_v0.2.md)。下文保留首轮实现的原始证据与限制。规划校验默认v0.2，复核首轮快照需加 `--protocol v0.1`。

已建立可执行的协议内核，并完成历史回放、协议测试和实际 SUMO/BlueSky 交接仿真。这里记录的是开发阶段证据，不是 R2–R5 正式研究结果。设计 v0.1 及生成计划仍作为原始设计快照；其 `not_implemented` 状态不代表本页的最新实现进度。

## R0：历史行为回放

- 27/27 个历史回放完成，任务完成时长、动作表与完整动作流水线均一致。
- 流水线比对包括原始、规范化和已执行动作、仿真时间、执行结果；仅排除 decision ID。
- B0：D0=182 s，D30=212 s，D60=242 s；故障 359/360/361 s 对照均符合对应历史值。B2=302 s，B1=342 s。
- **6 个 runtime_v2 兼容桥接单元尚未实现，因此不宣称整个 33 单元 R0 门通过。** 这 27 次使用带去重修正的旧执行器及一个旧原版控制，仅验证复制平台和历史基线。
- [结果](runs/regression/r0_20260918_153251_6462ec/report.json)；[完整流水线复核](runs/regression/r0_20260918_153251_6462ec/pipeline_audit.json)。

## R1：协议内核

`runtime_v2/core.py` 实现操作去重、任务/资源版本检查、资源束原子占用、含端点的等待租约、不可向后延长的等待期限、取消语义、终态释放，以及载荷交接的持续条件和保管权转移。写入接口检查世界线程，快照使用独立深拷贝。

- 8 类 × 6 个具名语义变体，共 48 个用例通过；并非同一用例简单平移时间。
- 6 个故意错误实现均被检测：重复请求重置 due、跳过版本、资源冲突、非法货物交接、撤销已执行动作、无限延期。
- 拒绝非世界线程写入，以及 3 种畸形 proposal。
- 两任务争用一个资源的六事件所有排列：720 条调度、52 个观察状态、深度 6，未发现检查器违例。
- **尚未完成计划中的深度 12、两空一地一设施完整状态空间，也未做真实异步适配器的乱序 I/O 验证；不宣称完整 G1 通过。**
- [结果与具名用例表](runs/protocol/r1_20260918_154225_0d33c4/report.json)。同目录保留逐用例事件。

## 最小物理闭环

单个载荷经历装载→空中运输→故障后的本地返航→V3 实地交接→地面运输→V1 卸载。SUMO 与 BlueSky 每秒各推进一步并核对时钟。交接需要飞行器实际位置/高度/速度满足阈值、地面车实际到站且停稳、设施可用并属于当前提交；持续 30 秒后才切换保管权。送达来自 SUMO 的实际 arrival 事件，加 15 秒卸载；不使用 ETA 判定完成。

| 设施额外等待 | 两载具准备好 | 交接开始 | 交接完成 | 地面实际到达 | 卸载后送达 |
|---:|---:|---:|---:|---:|---:|
| 0 s | 415 | 415 | 445 | 610 | 625 |
| 30 s | 415 | 445 | 475 | 610 | 625 |
| 120 s | 415 | 535 | 565 | 700 | 715 |

以上均为仿真绝对秒，任务于 300 s 释放。30 s 延迟改变交接和发车时间，但这次轨迹中的后续行程耗时缩短，最终到达时间相同；这不是对任意延迟都保持送达不变的结论。120 s 延迟使送达推迟 90 s。

在 360 s 请求一个**受控模拟**的慢响应，365 s 执行固定截止的地面兜底，480 s 到达的旧版本响应被丢弃；等待期间飞行器仍有 48 个运动 tick。这里没有启动 LLM 进程，也没有验证原生异步 CLI。截止 365 s 是诊断 fixture 的常量，尚非完整 latest-start 计算。

[三组对照总报告](runs/development/physical_controls_20260918_154631_46df83/report.json)包含轨迹审计和源码 SHA-256；各子运行包含 `fixture.json`、`events.jsonl`、`trajectory.jsonl`、`report.json`。对照目录保存控制台输出。

边界：设施坐标显式对齐 SUMO 车道；四架飞机均用 M600 占位，仅主载具运动。BlueSky 初始化日志提示 legacy 性能回退，实际对象为 `bluesky.traffic.performance.perfbase.PerfBase`。本轮证明运动状态与交接事件相连，**没有证明无人机动力/能耗标定、真实通信故障、完整 S1 背景任务或航空安全**。

## 清理、复用与恢复

- 首先移除 378 个已核对原文件及 ZIP 副本 SHA-256 的非跟踪缓存文件，共 45,177,221 字节；[清单](outputs/bootstrap/cleanup_plan.json)、[执行日志](outputs/bootstrap/cleanup_journal.jsonl)。
- 另清理旧批量数据的 318,948 个工作区副本、6,499,271,306 字节，详见 [冷归档清单](outputs/bootstrap/cold_storage_plan.json) 与执行日志；完整内容仍在独立 ZIP 中。两步合计移除 **319,326 个文件、6,544,448,527 字节（逻辑大小约 6.54 GB）**。旧 `archive/manuscript_workspace` 含目录链接，保留该分支，未沿链接清理外部依赖。
- R0 历史证据 `legacy/20260918/manuscript/source/revision_v3/regression/` 留在原处。旧 tracked 源码、主 Git 历史和旧论文保留；原迁移清单作为历史快照不覆写。
- 新代码复用 240 个源文件和地图资产，复制到 `vendor/legacy_platform/`；来源 SHA-256 见 `PROVENANCE.json`，不导入旧动作/模型缓存。
- 完整 ZIP：`C:/Users/user/research-backups/ground-air-legacy-20260918/legacy_snapshot.zip`。恢复单个文件可用 `tools/restore_legacy_file.py`，恢复到单独目录并验证内容 hash，拒绝覆盖已有文件。
- [清理后审计](outputs/bootstrap/cleanup_verification.json)已通过：904 个旧 tracked 文件内容哈希不变，27 个 R0 来源指标哈希不变，新 Overleaf 仓库无改动；已实际恢复一个旧结果并验证 SHA-256。

## 复现入口

从总工作区根目录执行，使用 [环境清单](outputs/bootstrap/environment_inventory.json) 中记录的 Python 与现有 BlueSky 安装：

```powershell
python -B research_hscc2027/tools/run_r0.py
python -B research_hscc2027/tools/run_r1.py
python -B research_hscc2027/tools/run_physical_controls.py
python -B research_hscc2027/tools/plan_experiments.py --check
```

每次运行写入新的时间戳目录，不覆盖历史证据。`run_r0.py --limit 1` 可做单例诊断。清理脚本是本次迁移工具，**不要当作日常实验入口重新执行**。

下一阶段依赖顺序：完成 6 个 R0 桥接；扩展 R1 状态模型及适配器乱序测试；将诊断控制器拆成可复用载具/设施接口、实现 latest-start 和四种共享内核执行器；冻结 S1–S3 fixture 后进入正式门控。原生 LLM 仍固定为 Codex `gpt-6-astra` / `high`，接入前完成隔离与准入验证。
