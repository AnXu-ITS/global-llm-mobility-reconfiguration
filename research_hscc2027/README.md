# HSCC+ICCPS 2027 新方向工作区

候选题目：**Deadline-Aware Runtime Supervision for Ground–Air Service Reconfiguration**。

当前状态：已实现首版协议内核，27 次历史回放、48 个协议用例和三组 SUMO/BlueSky 物理闭环开发对照已通过。完整 R0/R1 门尚未完成，尚无正式 R2–R5 结果。详情与限制见 [实现和验证记录](IMPLEMENTATION_STATUS.md)。新实验的 LLM 固定为 **本机 Codex / GPT-6 Astra / high**；本轮没有实验模型调用。

最新场地扩展：D/E/F 真实 OSM 地图已落地（莱比锡/巴塞罗那/柏林），各自单载荷闭环通过；正式场地验收仍待完成。当前采用 [六场地协议 v0.2](design/EXPERIMENT_PROTOCOL_v0.2.md)、[场地注册表](config/sites.v1.json)和[落地报告](design/SITES_D_E_F_IMPLEMENTATION_v0.2.md)。

最新优先级：完整R1 → D → F → E → A/B/C统一签名和fixture → R6冻结。R1已增加状态检查和真实队列测试，但显式枚举触及100万状态，G1仍关闭；见 [验收证据与限制](design/R1_ACCEPTANCE_v0.2.md)及[执行顺序/论文两层结构](design/EXECUTION_PRIORITY_v0.1.md)。门检查入口为 `tools/check_execution_gates.py`，完整R1入口为 `tools/run_r1_full.py`。

- [当前实验协议 v0.2](design/EXPERIMENT_PROTOCOL_v0.2.md)：继承v0.1共同规则，新增六场地身份、R6及验收；[v0.1](design/EXPERIMENT_PROTOCOL_v0.1.md)为历史设计。
- [模型调用契约](design/MODEL_INTERFACE_CODEX_ASTRA.md)：本机 ChatGPT 登录、独立请求、模型/档位、计时及准入。
- [当前机器配置](config/experiment_protocol.v2.json) 与 [Astra high 配置](config/llm_codex_astra_high.json)。
- [当前计划总表](design/generated_v0.2/plan_summary.json)、[逐单元计划](design/generated_v0.2/run_plan.csv)、[R0 来源与预期](design/generated_v0.2/r0_plan.csv)。原 `design/generated/` 保留v0.1。

基础计划槽位：3,300 个受控/快速参考（含R6的240）、60 个原生、428 个原开发、33 个 R0，共 **3,821**；可选扩展 **440** 单列（含R6_B2的120）。地图筛选和物理探针另立开发账本。相位零偏移的80个锚点可按完整签名复用，不增加独立样本。计划清单不是运行日志。

从总工作区根目录执行 `python -X utf8 -B research_hscc2027/tools/plan_experiments.py --check` 校验当前v0.2；加 `--protocol v0.1` 校验保留的原始设计。该工具不运行模拟器、不调用LLM；最新实现进度与规划状态分别记录。

| 目录 | 用途 |
|---|---|
| `design/` | 新运行时、时间/资源/载荷模型与接口设计 |
| `sites/` | 真实OSM来源、15个候选、D/E/F入选地图、签名、诊断及图件 |
| `fixtures/development/` | 新场地开发骨架；禁止冒充正式冻结fixture |
| `config/` | 开发/正式实验配置与版本标记 |
| `analysis/` | 新统计与图表生成代码 |
| `runtime_v2/` | 首版协议内核；与仿真、LLM 解耦 |
| `vendor/legacy_platform/` | 带来源哈希的旧平台源代码和地图复用副本 |
| `runs/regression/` | 隔离 R0 回放及历史动作流水线对照 |
| `runs/protocol/` | R1 用例、故障注入与有限调度探索 |
| `runs/development/` | 新开发运行，每次 attempt 使用新目录 |
| `runs/primary/` | 冻结正式运行，追加式保存 |
| `outputs/` | 新方向派生图表与数据 |

旧平台位于 `../legacy/20260918/`，复用模块前从该目录复制所需源文件到新代码仓库并记录来源 SHA。不要把旧稿的重写/清理脚本接入新论文构建。

论文仓库为 `../manuscript_hscc2027/`，完整方案仍在根目录的转向计划书中。分析与归档证据在 `../provenance/hscc2027/`。
