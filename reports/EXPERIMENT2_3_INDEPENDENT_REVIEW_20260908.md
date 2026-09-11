# 实验 2、3 独立评估：设计、实现、原始结果与重做建议

评估日期：2026 年 9 月 8 日，北京时间。评估对象为执行时的项目文件及三个场地的主实验数据。

## 1. 结论与处置建议

**实验 2：可保留为简化模型下的单故障响应基准；必须重新分析并收缩结论，不必直接丢弃全部 3,840 次运行。** 共享输入、外生故障、统一校验和配对种子设计具有价值。现有数据支持“在指定候选集和故障抽象下，协调策略通常改善主应急任务表现”，没有证明 LLM 优于启发式基线。恢复率分母、候选集收缩解释、统计校正、后台服务损害及网络故障归因需要修正。如果论文要用它证明实际交接时间、拥堵条件下的运输恢复或全系统服务韧性，则应在修正执行模型后补做相关场景。

**实验 3：建议作为正式论文主实验重新设计并重跑；现有 2,880 次运行保留为开发、诊断及旧版本对照数据。** 主要原因不是结果为阴性，而是全系统目标与调度触发机制不一致、背景服务生命周期不合理、L3 未充分形成所声称的竞争，以及跨场地统计和故障归因错误。仅改图表、增加种子或删除失败调用不足以修复。

**立即撤回或改写的表述：**

- “Site B L2 中 LLM 因过度占用第二应急任务资源而显著更差”：L2 没有第二应急任务；主要异常伴随连接失败；按原脚本声明的每场地 12 项检验族，正确 Holm 值约为 **0.21135**，不是 0.036。
- “Site A 三种协调管理器 240/240 决策完全相同”：240/240 的 **SWL 相同**成立；排除理由文本、空字段和地面动作无效字段后，实际运输操作及时间序列仅 **235/240** 相同，5 对主任务完成时间不同。
- “L2 的 +100 SWL 是第二次损失备用医疗飞机造成的”：Site A 两个 F1 开头的 L2 场景没有 SWL 差距；+100 全部来自另外两个场景里未再调度的背景任务。
- “跨场地 B4b 零重试”：原始元数据中 Site B 有 5 次、Site C 有 14 次结构化重试；另外分别有 **143 次、1 次最终传输错误**，它们不能由重试次数代替统计。

## 2. 评估范围与项目理解

项目研究在地面道路中断、低空资源稀缺且已有常规任务的条件下，全局监督器能否调整任务优先级和空地资源，同时维持原有服务。实现是 SUMO 地面路网、BlueSky 航空运动、共享注册表、候选生成器、管理器、语义与可行性检查器组成的闭环；LLM 不直接控制飞行姿态。[研究定位](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/Research Plan.md:26>)、[执行管线](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/phase3_orchestrator.py:53>)。

| 实验 | Site A 苏州 | Site B 阿姆斯特丹 | Site C 埃德蒙顿 | 合计 |
|---|---:|---:|---:|---:|
| E2：16 场景 × 20 种子 × 4 管理器 | 1,280 | 1,280 | 1,280 | 3,840 |
| E3：12 场景 × 20 种子 × 4 管理器 | 960 | 960 | 960 | 2,880 |
| 合计 | 2,240 | 2,240 | 2,240 | **6,720** |

四个管理器为 B0 地面基线、B1 规则、B2 目标函数排序启发式、B4b 候选表输入的 LLM。按矩阵和种子清单枚举，主结果文件齐全，所检查的输入、动作、事件、终态、运行元数据文件均存在。**运行完成及文件齐全不等于运输任务全部完成**：E3 Site B B4b 有 6 个主应急任务未完成。

本次全量读取主运行的指标、管理器输入、动作管线；全量分析 B4b 决策输出；对全部 E3 读取终态、事件和多故障轨迹。未将 pilot、接口回放或旧版本实验混入主样本。没有运行 SUMO、BlueSky 或实验用 LLM，没有修改原代码、配置、日志、已有分析及报告。

已参考更新后的实验 1：正式数据位于 `runs/experiment1_final/`，报告列出 960 个主运行和 60 个接口消融运行。其共享候选信息、真实输入扰动、先规范化再校验、以执行动作计数等修正确实存在于当前代码中；不能沿用旧版 E1 的全部批评。[E1 最新结果](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/experiment1_final/EXPERIMENT1_FINAL_RESULTS.md:1>)。本次未重新审计 E1 的全部 1,020 个运行，因此不为其全部统计结论重新背书。

## 3. 值得保留的设计与实现

1. **初始比较公平。** 全部 1,680 个“实验 × 场地 × 场景 × 种子”配对组，四个管理器首次输入 JSON 完全一致。种子确实改变电量、续航及繁忙飞机初始位置，不再只是相同提示重复采样。[种子实现](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment1_runner.py:197>)。
2. **候选信息无直接优化解泄漏。** B1、B2、B4b 使用同一事实表；候选生成没有调用 B2 生成推荐或最优排名。B2 是单目标任务的启发式候选排序，不应称为全系统最优解。[候选生成](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/candidate_info.py:130>)、[B2 实现](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/managers/optimization.py:45>)。
3. **故障配置外生。** 故障时间、资源、区域或站点由矩阵给定，注入器不按管理器决策主动选择攻击目标。不同策略导致不同暴露和后果，是可以接受的实验机制。F3、F4 没有 C2 单元也被文档明确列为设计限制，不应伪装成完整 6×3 因子设计。
4. **执行边界比旧版可靠。** 规范化动作后再进行共享语义和可行性检查，日志保留原始、规范化、执行动作。地面完成时间优先由环境计算，旧版直接相信管理器 ETA 的问题已有修正。[规范化与校验](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/phase3_orchestrator.py:69>)、[地面执行](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/phase2_orchestrator.py:473>)。
5. **保留后台失败运行是正确方向。** 不能只删除不利的网络故障样本。当前数据可以作为当时整套“管理器＋接口＋调度机制”的运行记录；但不能在没有隔离设计的情况下把全部差距归因于模型策略。

## 4. 实验 3 的主要问题

### P0-1：全系统损失与背景任务生命周期不一致

背景服务在初始化时被设为 `EN_ROUTE`，截止时间固定为 1800 秒，并通过 `shuttle_pairs` 往返飞行；正常到站不会将这类任务标记为完成。[背景初始化](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment1_runner.py:157>)、[往返逻辑](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/phase2_orchestrator.py:543>)。

E3 的 SWL 对所有未完成任务收取取消成本，包括仍正常 `EN_ROUTE` 的任务；但 E3 仿真在 900 或 1200 秒结束，早于这些背景服务的截止时间。[SWL 计算](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment3_runner.py:268>)。

全量终态核查：**2,864/2,880** 个 E3 运行中，至少一个“仍 EN_ROUTE、截止时间在仿真结束之后”的背景任务被计入损失。正常持续服务被按取消计费，而被故障中断后转地面、在结束前完成的相同服务反而可以获得零损失。这使跨复杂度、跨场地的 SWL 水平缺乏清晰的服务效用含义。

例如 Site A `E3_L2_F1_F1/seed20240601/B1` 的 SWL=640，其中主任务逾期罚 240，正常物流和客运背景任务各罚 200。两个背景任务都仍在飞行，截止时间都是 1800。[逐任务指标](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/runs/experiment3/E3_L2_F1_F1/seed20240601/B1/metrics.json>)、[终态](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/runs/experiment3/E3_L2_F1_F1/seed20240601/B1/registry_final.json>)。

为检验影响，本次只从 SWL 中扣除这些“未到截止时间的 EN_ROUTE 背景任务”费用，进行了离线敏感性分析：

| Site A | 原 SWL：B0 / B2 | 扣除上述费用：B0 / B2 | 差值 B2−B0 |
|---|---:|---:|---:|
| L1 | 640 / 400 | 240 / 0 | −240 |
| L2 | 540 / 640 | 240 / 340 | +100 |
| L3 | 840 / 600 | 245 / 5 | −240 |
| L4 | 490 / 370 | 240 / 120 | −120 |

**重要限制：这项敏感性分析没有消除 Site A 的 L2 差距，也不是修复后的正式指标。** 它证明损失水平包含大额终止时点费用；L2 的 +100 还需要下一项机制解释。正确修复应给背景服务定义可完成的航次及续接需求，或按交付量、服务中断时长计费，并明确截尾处理，之后重新运行受到资源释放变化影响的场景。

### P0-2：只触发应急任务的调度，制造了背景任务长期无人处理

E3 `_periodic_due` 只检查两个应急任务是否可调度；两者一旦进入 `EN_ROUTE` 或完成，其他 `NEEDS_REPLAN` 背景任务不再触发周期决策。每个事件只执行一个管理器动作，所以优先处理主应急任务后，剩余服务可能一直停到仿真结束。[触发条件](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment3_runner.py:225>)、[单动作管线](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/phase3_orchestrator.py:58>)。

**直接证据：** `E3_L2_F2_F4/seed20240601` 在 t=420 关闭 V1 后：

- B2 同时面对主应急任务和客运任务中断，先给主应急任务安排地面运输，t=602 完成；客运任务一直留在 `NEEDS_REPLAN`，没有后续决策处理。
- B0 的主任务早已在地面运输，因此 t=420 的唯一决策用来恢复客运，客运也在 t=602 完成。

两者主应急任务在 SWL 中都只罚 240；额外 200 完全来自客运任务。另一个 `E3_L2_F6_F5` 同理，额外 200 来自物流任务。四个 L2 场景等权平均后，正好得到 +100。

| Site A L2 场景 | 主应急损失 B0 / B2 | 背景损失 B0 / B2 | SWL 差值 |
|---|---:|---:|---:|
| F1→F1 | 240 / 240 | 400 / 400 | 0 |
| F1→F5 | 240 / 240 | 400 / 400 | 0 |
| F2→F4 | 240 / 240 | 200 / 400 | +200 |
| F6→F5 | 240 / 240 | 200 / 400 | +200 |

[B2 事件](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/runs/experiment3/E3_L2_F2_F4/seed20240601/B2/events.csv>)、[B0 事件](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/runs/experiment3/E3_L2_F2_F4/seed20240601/B0/events.csv>)、[B2 终态](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/runs/experiment3/E3_L2_F2_F4/seed20240601/B2/registry_final.json>)。

独立纯函数探针也复现：t=450、主应急任务 `EN_ROUTE`、客运任务 `NEEDS_REPLAN` 时，当前触发函数返回 False。因此，**可以报告旧调度机制留下未恢复服务，不能据此宣布备用资源耗尽是 +100 SWL 的已验证原因。** 触发策略一旦修复，会产生原日志中不存在的新动作；不能靠修改指标复原完整反事实，相关 L2/L4 必须重跑。

### P0-3：L3 没有充分检验多应急任务争夺资源

Site A L3 的主任务 t=300 已派出，第二任务 t=390 才释放。此时一架医疗机忙于主任务，另一架长期执行不可抢占的背景医疗服务，第二任务通常只有立即地面运输这一现成选项。

全量管理器输入显示，Site A、B **均没有两个应急任务同时处于可调度状态的决策时刻**；Site C 仅 B4b 有 2 个这样的时刻。对于 L3 的 80 个第二应急任务/管理器，A 全部地面、B 的 B1/B2/B4b 全部空中、C 全部地面。资源忙闲确实影响可行性，但这些多数是按先后顺序独立分配的任务，不能充分检验全局竞争、留备与跨任务规划。

同时，报告声称 `mission_candidates` “只在 L4_B 发出”不符合全量输入。Site A B2 在 L2_F2_F4 有 20 次、L2_F6_F5 有 40 次、L3_COMP_F2 有 4 次、L4_B 有 60 次多任务候选表；大多是背景任务中断产生的多任务状态，而非两个应急任务直接竞争。[多任务表生成](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/candidate_info_e3.py:42>)。

B1/B2 只对最高优先级任务读取顶层 `air/ground` 表，没有执行跨任务联合分配或未来资源预留优化。[B1](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/managers/rule_based.py:65>)、[B2](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/managers/optimization.py:65>)。因此“LLM 与基线相同，所以全局推理没有价值”超出了当前策略空间。

重做 L3 应先验设置同时待决任务、重叠需求窗口、有限资源释放时间、不同优先级与截止期之间的真实取舍；保证先导检查中这些状态实际出现。不要为了让 LLM 赢而选参数；应让提前等待、直接地面、立即派飞、留备等策略都有可辨别的结果。

### P0-4：跨场地报告把网络故障当成策略劣势，并错误计算显著性

E3 Site B B4b 的原始输出共有 861 次决策：718 次最终有效输出、**143 次最终传输错误，涉及 17 个运行**。其中 6 个主应急任务直到结束都未完成。Site C 为 759 次有效输出、1 次传输错误，另有 14 次结构化重试。

例：`E3XB_L2_F2_F4/seed20240602/B4b` 只在 t=300 成功派飞；从 t=322 起持续出现连接重置或远端关闭，22 次最终传输失败，主任务无恢复动作。该运行 `retry_count=0`，是因为传输异常直接返回、不进入解析重试分支。**零重试绝不等于调用成功。**[原始输出](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/runs/experiment3_cross_site/site_b_amsterdam/E3XB_L2_F2_F4/seed20240602/B4b/manager_outputs.jsonl>)、[事件](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/runs/experiment3_cross_site/site_b_amsterdam/E3XB_L2_F2_F4/seed20240602/B4b/events.csv>)、[异常分支](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/managers/llm_manager.py:135>)。

Site B L2 的 SWL 差距由 9 对不同结果形成：6 个未完成主任务分别增加 2400 或 2160 损失，两个主任务结果改善，另有背景恢复差异。该层只有一个应急任务，原报告“第二应急任务占用航空资源”的机制不存在。

按原脚本声明的每场地 12 项比较族（B4b 对 B1/B2 × L2/L3/L4 × SWL/CRITICAL+HIGH），本次对全零差异设 p=1，并实施累积最大值形式的 Holm 校正：

| E3 比较 | 样本对数 | 平均差 B4b−B2 | 原始配对 t p | 正确 Holm p |
|---|---:|---:|---:|---:|
| Site A，各层 SWL | 40 或 80 | 0 | 全零差异 | 1 |
| Site B，L2 SWL | 80 | +159 | 0.0179675 | **0.211348** |
| Site B，L2 CRITICAL+HIGH | 80 | +159 | 0.0176123 | **0.211348** |
| Site C，L4 SWL | 40 | +5 | 0.323475 | 1 |

Site B L2 的未校正差值 95% CI 为 [28.04, 289.96]，Wilcoxon p=0.03481；这些不能替代预先声明的多重检验。不能把“不显著”解释成等效，也不能保留“Holm 后显著更差”。[原统计脚本](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/tools/test_exp3_cross_site_hypotheses.py:86>)。

### P0-5：未完成任务被标成“不违反截止时间”

继承自 E1 的字段使用 `bool(comp_t and crit and comp_t > crit.deadline_s)`。当 `comp_t=None` 时返回 False，把仿真结束仍未完成、且早已超过截止时间的任务统计成没有逾期。[代码](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment1_runner.py:361>)。

E3 Site B 的 6 个未完成主任务全部触发这个问题。因此，报告中的 B4b 逾期率 **53/240=22.08%** 不能当作任务按时可靠性；按“截止时间前未完成即未达标”统计，应为 **59/240=24.58%**，B2 为 **60/240=25.00%**。应同时报告完成率、按时完成率、完成任务条件下的时间、未完成数量，避免条件均值产生幸存者偏差。

E2 当前主样本全部完成，本缺陷没有改变它的逾期率；但代码必须在新的正式实验前修复。

### P1-1：复合指标未实现或不符合文字定义

- `resource_competition_correct` 与 `priority_consistency_violations` 在 **全部 2,880 个 E3 metrics.json 中缺失**。不能凭 SWL 相同宣布高优先级一致性已通过验证。
- 文档中的 `spare_medical_assets_at_t420` 未输出。现有 `spare_aircraft_at_second_failure` 是注入第二故障后采样的可用飞机 ID 列表；没有完整实现文档的医疗兼容性口径。应区分故障前预留量和故障后剩余量。
- `cascade_recovery` 对每个故障搜索直到运行结束的主任务恢复事件，并以“以后是否出现过地面恢复”决定该次恢复模式，造成先空中恢复、随后地面恢复的事件被回填为 GROUND。本次发现 **591 个事件**的模式与首个实际恢复事件不符（A 240、B 112、C 239），以及 **67 个未影响主任务的事件**被记为主任务恢复成功。
- `decision_oscillation_count` 数所有模式/资源变更，AIR A→AIR B→GROUND 也算 2 次。应称为“切换次数”；若要解释成来回振荡，需要另行识别反向返回。

[指标定义](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/experiment3/EXPERIMENT3_METRIC_DEFINITIONS.md:53>)、[实际输出字段](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment3_runner.py:241>)、[恢复与切换实现](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment3_runner.py:286>)。

这些字段可以优先从现有事件与状态离线重算；缺失相应竞争时刻时必须标 N/A，不能补成“正确”。现有验收测试主要检查字段存在、列表长度、分项求和等，并不能验证上述机制。[验收范围](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/tests/test_exp3_acceptance.py:78>)。

## 5. 实验 2 的结果、指标和统计

### 5.1 可保留的描述性结果

| 场地 | B0 主任务完成时间 | B2 | B4b | B2 / B4b 逾期率 |
|---|---:|---:|---:|---:|
| A | 182.000 s | 162.000 s | 166.525 s | 37.50% / 39.06% |
| B | 241.000 s | 153.875 s | 154.050 s | 37.50% / 37.50% |
| C | 310.000 s | 278.000 s | 278.922 s | 62.50% / 62.81% |

这是当前运行日志中的结果，适用范围是固定地面中断、一个主应急任务、指定四机资源及六种抽象故障。B0 的主任务全部走地面，天然不受后续空中故障中断；它适合作为“不采用跨层恢复”的参照，不能将其 recovery=0 与空中受损后的恢复失败混为一谈。

B1/B2 的主要绩效相同是实测事实，但两者都在很窄的候选空间内工作。当前结果没有提供 LLM 超越强全局调度器的证据。

### 5.2 恢复率与恢复时间需要统一分母

| 场地 | B2：受影响后恢复数 / 受影响数 | B4b：受影响后恢复数 / 受影响数 |
|---|---:|---:|
| A | 200/200 | 191/191 |
| B | 200/200 | 199/199 |
| C | 200/200 | 201/201 |

跨场地表中的 0.625、0.621875、0.628125 实际使用全体 320 个运行作分母，不能标作“受影响运行恢复率”。A 中有 9 个 B4b 运行在故障发生前尚未成功派出航空任务，因此未形成可被中断的航空主任务；它们不能既在条件恢复率中被排除，又在 McNemar 中当成同一种“恢复失败”。

原 A 聚合恢复时间比较使用 200 对，但其中仅 **191 对同时满足两个管理器主任务均受影响**。在这 191 对中平均恢复时间差为 **3.9267 秒**，并非 200 对的 4.5 秒。应将主任务按时完成的无条件指标作为端到端主要结果；条件恢复指标用于机制分析，并明确条件选择受策略影响。

[恢复实现](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment2_runner.py:332>)、[规定分母](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/experiment2/EXPERIMENT2_METRIC_DEFINITIONS.md:40>)。

### 5.3 候选收缩混入了派飞占用变化

当前 `candidate_set_reduction_delta` 是 t=300 初始派飞前候选数减去 t=360 故障后候选数，并非同一时刻仅改变故障条件的因果差值。

例如 `E2_F1_C1/seed20240601/B2`：初始 2 个可派医疗资源；t=360 故障前 as-if 候选为 1，故障后仍为 1。报告展示的 2→1 包含主任务已经占用一架医疗机的变化，不能解释成外围物流失联减少了一个可用医疗选项。[轨迹](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/runs/experiment2/E2_F1_C1/seed20240601/B2/failure_trace.json>)、[计数实现](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment2_runner.py:200>)。

需要同时报告“当前执行路径是否失效”和“重规划备选集合”；用相同任务位置、可操作状态及资源占用口径比较故障前后。已有 as-if 统计可辅助核查，但也不能把不同状态下的集合直接当作因果反事实。依赖“收缩程度越大，LLM 相对表现如何”的结论需要重新分析。

### 5.4 统计实现必须修正，逐场景和总体比较不能混用

E2/E3 的 `holm` 只计算 `p × 剩余检验数`，缺少排序后的累积最大值，且未正确处理全零差异形成的 NaN；结果可能违反 Holm 的单调性。McNemar 调用 `binomtest` 默认双侧 p 后又乘 2，重复翻倍。[E2 统计代码](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/tools/analyze_experiment2.py:116>)、[E3 统计代码](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/tools/analyze_experiment3.py:119>)。

正确排序后调整值为：`p_adj(i) = min(1, max_{j≤i} [(m-j+1) p_(j)])`，再还原顺序。SciPy 的 `binomtest` 默认已经是双侧检验；Holm 属于逐步 Bonferroni 校正。[SciPy 官方说明](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html)、[statsmodels 官方说明](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html)。

独立重算结果：

- E2 每场地所有逐场景比较校正后，仍没有显著 B2–B4b 差异；这部分描述可以保留。
- E2 A 的总体完成时间差为 **+4.525 秒**，未校正 95% CI **[1.917, 7.133]**，原始 t p=0.000723。若将原分析列出的 5 个连续指标和 7 个二元指标作为一个明确的总体检验族，正确 Holm p=**0.008678**。因此不能用“逐场景均不显著”推出“总体也没有差异”。
- 二元逾期对的 5:0 不一致数，正确精确 McNemar p=**0.0625**，不是 0.125；9:0 为 **0.00390625**，不是 0.0078125。不过恢复成功字段的上述条件选择问题先于统计显著性，不能仅靠更正 p 值宣称恢复能力不同。
- 在同样的总体 12 项口径下，B、C 完成时间的 Holm p 分别约为 **0.09395、1.0**。

总体差距可以是接口可靠性的系统表现，不等于模型决策能力差距。E2 A 全量原始决策有 61 次最终传输错误，涉及 25 个运行；不能把“9 个故障前尚未派飞的运行”误当成“只有 9 个运行遇到错误”。

上述总体检验族是本次明确说明的重分析口径，不能冒称它已在原实验中预注册。不同场景共用种子、共享初始态且故障窗口具有时间相关性；正式分析还应按场景和种子成组报告或做分层/成组敏感性分析，避免把固定场景数包装成随机城市样本。相同均值或未拒绝零假设都不等于等效性证明。

## 6. 共同的模型适用边界及潜在代码问题

### 6.1 地面 ETA 是自由流路径代理，且没有按任务起终点计算

`SumoAdapter.get_route_eta` 使用路径边长/最高速度求和，明确没有采用动态行程时间。地面执行器也没有加入真实运输车辆，而是设置完成计时器。[ETA 实现](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/sumo_adapter.py:98>)、[计时器](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/phase2_orchestrator.py:473>)。

所有任务地面退路都使用同一个 D1→H1 ETA；E3 第二任务实际是 V3→V1，背景任务也有其他起终点，当前实现没有反映这些差异。这样可以研究拓扑中断下的抽象选项切换，不能直接报告真实拥堵、接驳和服务交付时间。模型更改会改变空地排序及任务完成时间，需要新实验。

### 6.2 恢复路径默认从 V3 交接，货物状态与准备时间不足

中断任务的航空候选及默认重分配路线转为 V3→目的地；代码未显式表示载荷在失联飞机上的位置、何时到达交接点、取卸货时间、是否允许备用货源。[恢复路线](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/candidate_info.py:238>)、[规范化动作](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/phase3_orchestrator.py:136>)。

本次未据此断言每条已记录路线都发生了提前取货；部分备用飞机到 V3 时原机可能已经返回。但失控飞走与可安全返回场景的载荷可恢复性不能自动等同。若保持该抽象，应明确“任务可从 V3 重新发起”的前提；若要推导现实运输恢复效果，需要补充载荷守恒和交接等待并重跑。

### 6.3 故障是可审计的状态机简化，不是完整物理安全模型

F2 只在注入瞬间把区域内飞机降级；后续进入该区域的飞机不会自动遭遇同样故障。F5/F6 对当时在区域内的执行任务施加局部处置，并通过候选和动作检查约束新路线。它们适合作为故障通知/重规划测试，不能据此声称验证了连续 GNSS 误差或完整入侵避碰安全。

另有明确的几何缺陷：条带与路线最短距离只检查两线段端点到对方线段的距离，没有检测线段内部相交。正交穿越条带中部时，旧函数返回“不相交”，独立探针得到真实相交。[问题函数](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/failures/e2_failures.py:63>)。

**实际影响边界：** 对全部 E2/E3、三个场地、活动 F6 条带下记录的 1,389 个合法候选记录和 501 条已执行航空路线作对照，本次未发现该遗漏改变已记录合法候选或执行动作。候选记录可能包含顶层与多任务表重复。它是新场景前应修复的潜在缺陷，不能据此把现有全部 F6 运行判为无效，也不代表其他物理风险已经排除。[几何结果](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e23_20260908/geometry_results.json>)。

### 6.4 仿真时钟冻结与接口日志的双重限制

真实 LLM 等待时间不推进仿真时钟，报告中的 0 秒重规划是“仿真决策时间”而非实际响应时延。传输异常又没有把异常等待耗时计入 `latency_s`，并被 `cache_subsecond_calls` 的小于 1 秒规则当作缓存候选。例如 E3 B 的 151 次该字段计数中有 143 次实际是传输错误。[异常处理](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/managers/llm_manager.py:135>)、[缓存计数](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment2_runner.py:518>)。

不能用这些数证明亚秒推理或实时时限。应记录请求开始/结束、异常耗时、响应 ID 和缓存令牌；区分成功响应、解析重试、传输失败和下一仿真时刻重新决策。当前 B4b 有重复响应 ID，需要在延迟与推理重复性分析中说明；不能因为输入缓存命中就把场景结果一概视为无效重复。

### 6.5 跨场地只能支持适配复现，不能单独识别城市形态因果作用

跨场地同时改变路网/航空距离、故障注入时刻（A 360、B 322、C 383）、空间区域和第二波相对任务进度。Site B/ C 又经历不同的 LLM 连接故障窗口。因此可以说“这些适配设置得到不同结果”，不能从三个场地直接宣布效益完全由城市形态决定或存在不可突破的逾期率下限。

Site A L1 相对 E2 有记录的 +1 秒完成偏移；而 L2 第二事件恰在 420，恢复完成可能在 421。对此不能仅以“L1 尚有截止裕量”推断 L2 不敏感。需固定运行环境，并对第二波事件相对到达时刻做预先规定的时间偏移检查。

跨场地过程还补充了 `medical_organ` 兼容性并重新固定共享哈希。补全能力配置是合理修复，E1/E2 无该任务类型；但新的哈希只能证明当前版本一致，不能证明 Site A 运行时配置原本就相同。Site A 未选择航空第二任务可以解释现有执行轨迹为何不变，不能证明等待后派飞等未观察策略从未被旧兼容性限制。[变更说明](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/experiment3/E3_CROSS_SITE_FINAL_RESULTS.md:12>)。

## 7. 具体重分析与重做清单

| 对象 | 处置 | 理由及最小工作 |
|---|---|---|
| 原始 E2/E3 运行与日志 | 全部保留、注明版本 | 不删除网络失败或不利种子；可用于复核和旧版本对照 |
| E2 主任务时间及状态描述 | 在简化模型范围内保留 | 全量文件齐全且任务已完成，配对输入一致 |
| E2 恢复、候选收缩、统计、损害归因 | 重新分析 | 明确条件分母、正常执行选项与备选集合；修正 Holm/McNemar；区分策略与接口影响 |
| E2 系统服务/现实运输结论 | 收缩或补做 | 若要求真实服务生命周期、载荷交接和任务专属地面 ETA，则运行轨迹将改变 |
| E3 L1 | 留作旧环境回归锚点；新版再验证 | 可验证单故障路径，但不直接证明复合竞争能力 |
| E3 L2 | 修复调度和生命周期后重做 | +100 归因涉及未处理背景任务；新动作不在旧日志中 |
| E3 L3 | 重新设计并重做 | 应覆盖实际同时待决、资源不足和等待/预留的可辨别权衡 |
| E3 L4 | 随统一执行语义重做 | 叠加了触发、背景任务、第二任务和多事件指标问题 |
| E3 跨场地 L2 “LLM 显著劣势” | 撤回当前机制及显著性表述 | 正确校正不显著，主要异常伴随连接失败，且没有第二应急任务 |
| E3 恢复/一致性/切换指标 | 先离线重算，缺证据标 N/A | 事件模式与影响归属有错，两个规定指标没有实现 |
| 新版 E1 的统计与公共代码 | 同步复核，不直接全量重跑 | E1 分析脚本也出现相同的 Holm 简化；本次没有重算其完整检验族 |

建议按以下顺序开展下一版，避免先花费 LLM 调用再发现设计没有产生目标状态：

1. **先修共有执行与统计。** 对所有可调度任务维持调度；一次事件后允许明确的队列排空或固定处理预算；建立有限航次/服务中断成本；完成和逾期分开；任务专属地面路线；载荷交接；修复几何。保留新的版本号和执行前哈希，禁止更新哈希后冒称旧运行使用了新配置。
2. **再做不调用 LLM 的设计先导。** 验证正常背景任务可完成、任务完成会释放资源、两个应急任务确实争夺同一资源、单次故障和复合故障作用可区分。设置无故障、仅 A、仅 B、A+B 的匹配对照，避免把任务数、负载、时间窗口同时变化全部归于“复杂度”。
3. **提升比较对象而非给 LLM 喂答案。** 保留 B1/B2 便于前后对比，加入同样信息、同样运行时间预算下的多任务启发式或滚动规划基线；共同候选表不附优化答案。把单任务排序能力与全局资源配置能力分开评价。
4. **冻结协议后开展正式配对实验。** 预先规定主要指标、检验族、场景权重、故障暴露和网络异常处理；按场景/种子随机交错调用次序，避免某类场景集中撞上一次网络故障窗口。正式保留端到端失败；另做接口可靠性分层或统一降级策略消融，不能只重跑坏种子后覆盖原样本。
5. **最后做跨场地复现与时序敏感性。** 使用统一软件和兼容性版本；说明绝对时间、相对航程阶段分别如何保持可比；报告任务按时完成、实际服务中断、资源占用和完整调用可靠性。样本量依据场景内差异和最小有意义效应确定，增加种子不替代有效场景设计。

本次没有自动实施上述实验变更或补跑。

## 8. 独立证据与复核方式

所有新增材料位于 `reports/independent_e23_20260908/`，输出与原实验目录分离：

- [全量指标与正确统计](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e23_20260908/audit_results.json>)、[逐运行摘要](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e23_20260908/run_summary.csv>)。
- [后台可靠性、动作差异与恢复事件核查](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e23_20260908/diagnostic_results.json>)。
- [几何探针与已记录动作核查](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e23_20260908/geometry_results.json>)、[独立统计及调度触发探针](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e23_20260908/probe_results.json>)。
- [首次读取 SHA-256 清单](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e23_20260908/source_sha256.json>)、[诊断读取 SHA-256 清单](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e23_20260908/diagnostic_sha256.json>)。两次扫描共有 13,440 个文件，未发现内容变化。
- 可复现脚本：[audit.py](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e23_20260908/audit.py>)、[diagnostics.py](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e23_20260908/diagnostics.py>)、[geometry_audit.py](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e23_20260908/geometry_audit.py>)、[probes.py](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e23_20260908/probes.py>)。这些脚本只读原实验文件，并把输出写入本独立目录；没有模拟器/实验 LLM 调用。

复核环境使用现有 Python 3.14.7、NumPy 2.3.5、SciPy 1.18.1。本次重新计算的是已发生轨迹的统计与诊断，没有把离线指标敏感性分析冒充修复后的仿真。对实际载荷交接、持续空间故障、修复后服务恢复和更强规划基线的效果，仍需新实验验证。
