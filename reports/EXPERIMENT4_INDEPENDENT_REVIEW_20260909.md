# 实验 4 独立评审：尚不具备正式批量运行条件

日期：2026-09-09。范围：最新 E4 设计、矩阵、运行器、扩展机队、分析脚本、验收测试及其继承的公共实现；同时核对上次 E2/E3 建议的落实情况。

## 一、结论

**“刷新／延迟／状态规模”三个研究方向值得保留，但当前实现和对照设计还不能可靠识别这三个运行边界。建议先修正，再做小规模先导，不启动计划中的 1,360 次正式运行。**

本次未发现 `runs/experiment4/` 下的结果文件，因此这是运行前评审，不能评价 E4 已有结果或宣布某个延迟／规模阈值。现有 8 个离线验收函数直接执行后 **7 通过、1 失败**；另做了不启动模拟器、不调用 LLM 的状态与函数探针。全部证据见[核查结果](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e4_20260909/checks.json>)。

最优先处理的事项：

| 优先级 | 问题 | 正式运行前的要求 |
|---|---|---|
| P0 | 多线程直接运行共享的 BlueSky/TraCI 实例 | 每个运行独立进程，父进程只调度 |
| P1 | 4A 的即时事件通知绕过“刷新变慢” | 区分状态观测间隔与管理器触发间隔，重新定义对照 |
| P1 | 4B 同时刻故障／延迟动作顺序不一致，队列缺少失效和去重规则 | 固定时间片事件顺序、任务版本与过期取消规则 |
| P1 | E4 没继承 E3 v2 的全任务调度修复 | 次级应急和背景待恢复任务也必须得到后续决策机会 |
| P1 | 4C 增大输入的同时增大运力，且 N05 少一次故障 | 分离输入负担与物理规模，固定／归一化故障暴露 |
| P1 | 质量代理指标与承诺的统计分析未实现完整 | 在运行前完成指标定义、配对分析、校正、阈值判据及测试 |
| P1 | pilot 和 primary 共用目录，重跑可覆盖原记录 | 分 cohort／版本存储，增加完整性及哈希校验 |

这里的 P0 指批量结果可能因运行相互干扰而整体不可用；P1 指会改变研究问题、比较公平性或主要结论的缺陷。

## 二、上次建议的落实情况：已有实质修正，但不是全部完成

已核实的进展：

- E2/E3 分析中的 Holm 累积最大值与 NaN 处理、McNemar 多乘 2 的问题已经修改。
- 公共 E1 指标已把未完成任务记为截止未达标；当前正式任务的截止时间都在运行结束之前。
- E3 v2 的周期调度已经检查所有可调度任务，第二应急任务改为 t=300 注入，恢复模式使用首个恢复事件；条带内部相交检测已有修复。
- 当前 E3 三个场地各有 **960 个运行配置，全部标记 matrix_version=2**，共 2,880 个；旧版归档目录存在。本次核对的是版本和实现，没有重新全面验收这 2,880 条轨迹。

仍未完成或仅部分完成的内容：

- 背景服务仍是无限往返，尚无有限航次完成及资源自然释放；逐任务地面 ETA、载荷交接没有落实。这些在最新 CHANGELOG 中也被列为待做。
- E3 的 `resource_competition_correct`、`priority_consistency_violations` 目前是显式 `None`，不是已经实现的正确率。
- E3 恢复模式已修正，但仍搜索该事件后直到运行结束的主任务恢复，尚未完整加入“该次事件确实影响该任务”和事件归属窗口。
- E3 新 SWL 对所有 EN_ROUTE/ASSIGNED 都计 0，未限定为健康且尚未到截止时间的背景服务。后续应检查未完成且超期的应急运输，不能因仍标作飞行中就免罚。

最关键的继承问题是：**E4 从 Experiment2Runner 继承，E3 v2 的调度修复只写在 Experiment3Runner 中。** E4 又回到了“只要主任务不可调度，就不周期处理其他任务”。实际函数探针：t=450、主任务 COMPLETED、次级任务 WAITING，E4 返回 False，E3 v2 返回 True。

[E4 继承与触发](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment4_runner.py:49>)、[底层主任务触发](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment1_runner.py:308>)、[E3 修复](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment3_runner.py:233>)。

“复用冻结组件”应表示可追溯的统一版本，不应成为保留已知缺陷的理由。建议把需要共享的正确机制抽到公共层，再让 E2/E3/E4 明确选择版本。

## 三、4A：当前测到的主要是失败后的重试节奏，不是信息刷新边界

五个 arm 都在任务释放 t=300 和失联 t=360 **立即获取最新状态并决策**。周期函数又只在主任务 WAITING/NEEDS_REPLAN/INTERRUPTED 时触发。成功派飞或恢复之后任务进入 EN_ROUTE，周期调用就停止。

因此，在两次事件均成功给出运输动作的标准路径上，EV、P10、P30、P60、P120 都可能只有同样的两次调用。离线状态序列探针确认这一条件下五组额外周期调用均为 0。**这不是仿真结果，而是当前触发函数的直接性质。**[触发实现](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment4_runner.py:95>)。

设计文档提出“P120/EV 在 F1 失联后无法及时重规划”，与所有组立即接收失联事件的设定矛盾；“调用次数与间隔倒数成正比”也不是该机制保证的关系。若差异来自 LLM 返回空内容、网络失败或 DELAY，周期参数测到的是后续尝试机会，不能自动解释成状态陈旧。

建议二选一，明确命名：

1. **事件＋周期重评估策略实验：** 保留即时事件，把研究问题改为正常运行与请求失败下的重评估收益、恢复机会及成本；加入预先规定的故障响应失败/等待状态，对 B1/B2 使用一致注入条件。
2. **真正的信息刷新实验：** 将物理事件、观测快照刷新、管理器决策三个时钟分开；监督器按观测间隔接收快照，局部安全层仍立即处理故障。记录每次决策的快照年龄和故障发现延迟。用不同事件相位，避免所有事件恰好落在周期边界。

冗余调用不能仅由重复 issued 运输动作计数：大量 NO_ACTION 重评估或最终无输出同样可能消耗调用；“调用冗余”和“重复执行命令”应分开。

## 四、4B：方向可行，但队列语义和时间边界必须先修正

### 4.1 延迟命令可能先于同时间戳的故障处理

底层 `_step_once` 先处理旧 t 的事件，再推进到 t+1。E4B 在它返回后立刻处理 t+1 到期命令。因此从 359 推进到 360 时，顺序是：

```text
处理 scheduled_events(359)
推进物理状态到 360
执行 pending_actions(360)
下一步才处理 scheduled_events(360)，包括失联
```

离线探针复现了这个调用顺序。D60 在 t=300 产生的动作恰好在 t=360 到期，可能在同时间戳失联标记进入注册表前通过复检。当前文档的“在 S(t+delay) 检查新故障”没有明确这一边界。[延迟处理](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment4_runner.py:313>)、[底层步进](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/phase2_orchestrator.py:242>)。

应规定并测试统一顺序，例如：完成物理步进 → 应用该时刻全部外生事件 → 更新注册表 → 作废过期决策 → 执行到期命令 → 获取新决策。D00 与延迟组必须遵守相同规则；故障时刻前一秒、同秒、后一秒都要有断言。

### 4.2 同一任务可累积多条待执行命令

入队动作没有任务版本、占用标记、最新决策替代规则或去重规则。动作等待执行时任务仍 WAITING/NEEDS_REPLAN，所以周期和事件可以继续产生新命令；旧命令执行后其他队列项不会自动失效。[入队](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment4_runner.py:296>)。

“执行时再检查”不足以解决所有情况。独立探针使用真实地面 checker 和执行方法确认：一个正在地面运输的任务可再次通过 GROUND_FALLBACK 检查，其计时器从 **542 改到 572**，即同一任务被重复启动而额外延迟 30 秒。[地面检查](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/safety/feasibility_checker.py:132>)、[执行计时器](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/phase2_orchestrator.py:473>)。

这项探针证明可发生的实现路径，并不声称已经在 E4 正式运行中观察到该现象。必须先定义：允许多少在途决策、同任务是否只保留最新命令、请求时或执行时是否占用资源、哪些拒绝属于正常 superseded/已满足动作。否则“延迟性能退化”可能主要来自重复启动和反复重规划。

执行复检结果目前也没有写入完整的第二份 semantic/feasibility 日志，只留下 pipeline 和 violation。建议单独记录 capture_t、execute_t、快照版本、检查结果和失效原因，区分真正失效、已被新动作替代、任务已完成、网络无输出。

### 4.3 给定执行延迟与真实推理延迟不是同一实验

当前真实 LLM 调用仍阻塞物理步进，人工 `delay_s` 在返回后施加。这样可以研究**外加执行延迟敏感性**，但还不是仿真时钟持续前进的真实异步推理实验。

在相同延迟扫描下 B4b 和 B2 曲线不同，只说明两条策略在该设置中的响应不同，不能单独证明“LLM 特有的推理延迟惩罚”。应比较各自相对 D00 的变化及其配对差值，并把输入、排队和后端失败因素单独记录。

“第一个 p<0.05 的延迟”随样本量和检验族变化，不是稳定运行阈值。建议预先定义最小有意义的时间损失/按时率下降和置信区间；7 个离散水平只能定位测试网格内的区间，不能宣称获得精确连续临界值。

## 五、4C：输入负担、系统能力和故障暴露混在一起

### 5.1 随 N 增长的不是单纯状态文本

扩展同时增加空闲医疗机、可抢占任务、空间端点和航空候选。当前角色生成按类型成块排列，再把前一半设为 BUSY，所以新增忙碌飞机实际全是物流机，新增医疗机全部空闲：

| 总飞机数 | 空闲医疗机总数 | 新增忙碌物流机 | 实际额外故障数 |
|---:|---:|---:|---:|
| 5 | 2 | 0 | **0** |
| 10 | 3 | 3 | 1 |
| 20 | 5 | 8 | 1 |
| 30 | 7 | 13 | 1 |
| 50 | 11 | 23 | 1 |

这些是种子 20240601 的扩展函数输出；数量由角色和 busy 分配公式决定。任务需求仍只有固定三项应急，规模越大可能越不缺医疗资源。这会掩盖输入变长造成的困难。[角色与忙闲分配](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment4_fleet.py:99>)。

N05 中 `round(1×0.5)=0`，没有繁忙合成飞机，额外 F1 被静默省略；该组新增的一架还被余数分配为 eVTOL。**现有 `test_fleet_expansion_counts` 就在要求额外故障数为 1 的断言处失败。**[故障生成](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment4_fleet.py:161>)、[失败断言](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/tests/test_experiment4_acceptance.py:100>)。

建议拆为：

- **输入规模实验：** 保持核心任务、有效可行动资源、故障与参考最优动作相同，只增加明确无关或不可行动的状态条目；随机化顺序和 ID，记录实际 token 数、遗漏、动作正确率。这回答上下文负担。
- **系统规模实验：** 资源、需求、兼容性及故障暴露按负载比一起设计，分层随机分配各角色忙闲；用同一大实例的嵌套子集或独立随机流保证跨 N 的核心环境可比。它回答系统扩展性，结论与输入规模分开。

如果预算仅支持一种，优先选择与“LLM 状态规模边界”表述直接对应的前一种，保留现有扩展器作为后续系统规模实验基础。

### 5.2 4C 的次级任务仍可能失去后续调度机会

E4C 在 390/420 释放两项额外任务时各触发一次决策，但周期判断只盯主任务。如果首次调用失败、任务选择 DELAY 或背景被抢占，其他任务不会因自己仍待处理而持续获得决策。E4C 还使用单任务候选表 2.1.0，没有 E3 的多任务候选段。[次级任务注入](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment4_runner.py:525>)。

增加任务数并不保证形成有效资源竞争。若要把“忽略任务/资源”归因于 LLM，必须先排除监督器根本没有再次被调用的情况，并输出全部应急任务的按时完成和恢复状态，而不能只看主任务。

### 5.3 质量指标有实质定义偏差

- **forgotten_aircraft_count：** 实现统计运行结束仍 AVAILABLE、从未被 selected/issued 使用的飞机，没有核对首次状态、任务兼容性或是否有必要选择。正确策略本来就应该让多余飞机闲置；该数会随机队增长机械上升，B0 尤其如此。改名为“未使用可用资源数”可以保留作描述，不能用于判断认知遗忘。
- **duplicate_assignment_count：** 文档说检测一架飞机承担两项任务；实际只数已有 `DUPLICATE_ASSIGNMENT` 错误，它检查的是一项任务已有另一架活动飞机。两种约束方向不同，而且合法抢占不能一概视为重复。
- **constraint_violation_count：** 仅统计外层管线拒绝。LLM 内部语义失败、解析失败或重试后修正的动作不会完整进入该计数；因此它不能直接表示所有模型漏约束行为。应同时报告首轮错误、重试后错误、外层拒绝和最终无动作。
- **infeasible_air_action_count：** 仅计 `REJECTED`，漏掉 `REJECTED_SEMANTIC` 的航空动作。
- **decision_oscillation_count：** 仍将单次 AIR→GROUND 或医疗机 A→B 的必要切换当作一次“振荡”，与文档“反复横跳”不符；可以另报切换数，但振荡需定义回到先前选择或不必要反转。

[指标实现](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment4_runner.py:581>)、[切换实现](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/experiment4_runner.py:200>)、[重复分配语义](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/safety/feasibility_checker.py:76>)。写上“代理指标”并不能消除这些构念不匹配。

## 六、运行与统计的阻断问题

### 6.1 并发必须按进程隔离

E4 的 `ThreadPoolExecutor` 直接调用 `run_single`，在一个 Python 进程中构造多个运行器。BlueSkyAdapter 使用导入模块的全局 `bs.sim/bs.traf`；SumoAdapter 使用全局 traci 和固定 `label='cosim'`。因此线程间不具备仿真隔离，可能出现状态互相覆盖、重复连接标签及关闭其他运行连接。[并发入口](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/tools/run_experiment4.py:180>)、[BlueSky 共享对象](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/bluesky_adapter.py:20>)、[TraCI 连接](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/orchestrator/sumo_adapter.py:27>)。

现有 E3 调度器在线程里启动独立子进程，E4 没有保留这一层。应采用同样的进程边界，并验证并行结果和独立串行结果、种子及文件目录相互隔离。仅把 jobs 改成 1 不能替代正式的多运行初始化/清理验证。

### 6.2 pilot、primary 和续跑不可共用无版本输出

pilot 种子是 primary 的前三个；两条路径调用同一 `run_dir_for`，且元数据始终写 `cohort: primary`。正式再跑会打开同名日志并覆盖 pilot；分析器按目录递归读取，也无法区别尚未完成的 pilot 与正式结果。[pilot 调度](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/tools/run_experiment4.py:162>)、[元数据](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/tools/run_experiment4.py:96>)。

当前没有 E3 式 `run_is_current`，没有充分的输入/源代码哈希和完成标识校验。失败后旧 metrics 与新部分日志共存时，分析器还可能把旧指标读进去。应先隔离 cohort 和实验版本，完成后原子写完成标识；续跑只跳过哈希及完整性均匹配的运行。

### 6.3 分析脚本尚未兑现设计承诺

`tools/analyze_experiment4.py` 当前实现了均值表和部分组内原始 Wilcoxon p，但：

- **没有 Holm 校正**；没有设计承诺的 95% CI。
- **没有 arm 相对 P30/D00/N05 的配对变化分析**；只是把 anchor 名称写入结果。
- `sub_json['arms']` 留空，没有形成完整逐 arm 汇总及阈值推断。
- `_cohens_d` 在两组组内方差均为 0 时无条件返回 0。本次用 20 个 110 对 20 个 100 得到 d=0，不能把固定 10 秒差解释为零效应；应报告未定义的标准化效应及原始差。
- 全零差异的 Wilcoxon 在本机 SciPy 返回 NaN，当前代码直接保留；二元逾期数据直接用布尔数组做 Wilcoxon 也不稳妥，应采用明确的二元配对检验及风险差。
- 配对键只用 seed，增加多个场景后会互相覆盖；读取时跳过坏 JSON，未检查预期单元、cohort、版本或排除原因。完成时间只对非空值均值，必须同时报告未完成任务，避免幸存者偏差。

[效应量及检验](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/tools/analyze_experiment4.py:76>)、[结果输出](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/tools/analyze_experiment4.py:166>)。

运行前应预先规定主要结果、最小有意义退化、每个子实验的检验族、配对键、缺失／超期处理和多重校正。单锚定场景加 20 种子可作先导；不能直接支撑不同故障与不同负载下通用的 LLM 运行边界。

## 七、最小修订方案和放行条件

建议保持三个子实验，但暂不保留 1,360 次作为必须完成的固定规模。先做以下工作：

1. **修公共机制和运行器。** 进程隔离；把 E3 的全任务触发修复复用于 E4；明确时间片内事件顺序；实现同任务 pending 版本/失效/幂等；隔离 pilot 和 primary。
2. **改 4A 的自变量。** 选择“重评估节奏”或“观测刷新间隔”，设计至少一个确实产生状态年龄差、且不靠偶发网络失败才有差异的先导。
3. **保留 4B 扫描框架，补队列对照。** 同任务多决策、命令到期与故障同秒、任务已完成、转地面后旧航空命令到期等必须有确定预期。先证明 D00 与参考管线操作一致。
4. **拆解 4C 混杂。** 固定核心决策的输入负担扫描与物理资源扩展分开；修 N05；随机化角色忙闲与 ID；把合法候选集、实际 prompt token 数和所有应急结果记入日志。
5. **先实现分析及构念测试，再跑先导。** 用人工构造的正确闲置、非法重复、合法抢占、必要换机、真正振荡、内部重试、未完成任务验证指标。检测完数据完整性后再作统计。

最低放行门槛：

- 当前 8 个离线验收全部通过，补充时间顺序、pending 去重、次级任务触发和并行隔离测试。
- 4A 证明自变量确实改变观测或重评估机会；4B 证明量到的是预期延迟机制；4C 证明每个 N 的故障和负载满足设计。
- 不调用 LLM 的闭环先导先通过，然后才做小规模 LLM 先导；预先固定后端错误与重试规则，完整保留失败记录。
- 版本、配置、数据 cohort 和统计方案冻结之后，再确定正式样本量与完整矩阵。

本次没有修改 E4 源代码、配置或实验方案，没有启动仿真或实验 LLM。新增文件仅为这份评审和离线证据。

## 八、复核材料与限制

[独立核查脚本](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e4_20260909/check_design.py>)、[机器可读结果及源码哈希](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/reports/independent_e4_20260909/checks.json>)。

环境没有 pytest，因此本次按测试函数签名提供独立 tmp_path，直接执行原文件中的 8 个测试函数；这不是一次 pytest 框架运行。没有调用 setup 或真实 SUMO/BlueSky.step；时间片顺序探针使用假的适配器，仅执行调度方法。E4 的闭环行为、实际 LLM 规模退化及修复后队列性能仍需先导验证。
