# HSCC+ICCPS 2027 实验协议 v0.2：六场地接入

日期：2026-09-18。当前主配置为 `config/experiment_protocol.v2.json`，场地注册表为 `config/sites.v1.json`，计划清单位于 `design/generated_v0.2/`。本版新增真实 OSM 的 D/E/F 地图与 R6 面板；正式运行仍关闭。

本版继承 [v0.1](EXPERIMENT_PROTOCOL_v0.1.md) 的共同物理规则、事件顺序、四监督器定义、R0/R1、开发调参、主要指标、失败记账及 Codex 调用契约。下文覆盖其场地身份、随机流、矩阵总数、跨场地分析和场地验收条款。v0.1 文件和既有结果保持为历史版本。

## 1. 六场地及证据状态

| Site | 区域/原型 | 本版职责 | 当前证据 |
|---|---|---|---|
| A | 苏州；Meshed / Flexible | 原 R2、R3(H_A)、R5及R6 | 旧地图保留；新语义正式 fixture 待冻结 |
| B | 阿姆斯特丹；Barrier / Bottleneck | 原 R3(H_B)、R6 | 旧地图保留；新语义正式 fixture 待冻结 |
| C | 埃德蒙顿；Sparse / Long-haul | 原 R4、R6 | 旧地图保留；新语义正式 fixture 待冻结 |
| D | 莱比锡 D_03；Transfer-hub Bottleneck | R6 交接瓶颈 | 真实网络、路线及单载荷闭环已验证；双任务交接位队列待验收 |
| E | 巴塞罗那 E_02；Travel-time Volatile | R6 时间波动 | 真实限速事件改变实际行程；900 s 内期限/负载标定待完成 |
| F | 柏林 F_04；Multi-hub Resource-coupled | R6 资源耦合 | 两个模拟枢纽、兼容矩阵、真实路线及单载荷闭环；多任务资源执行待验收 |

这些是六类运行约束，不是六种城市形态的因果实验。真实 OSM 道路上的 D/H/V 服务设施是明确建模的抽象点，不表示现场医院、起降许可或实际物流运营设施已经核实。

论文按两层组织：**Transport structure** 为A—Meshed flexibility、B—Barrier bottleneck、C—Sparse long-haul；**Execution structure** 为D—Transfer bottleneck、E—Temporal volatility、F—Resource coupling。R6用于检验deadline-aware supervision与cross-stage reservation能否跨这些约束重现。信号系统数量属于统一导入参数下的模拟网络属性，不作现场城市比较；A–F签名须统一生成后才能进入Figure 2热图。

实际筛选及证据见 [场地落地报告](SITES_D_E_F_IMPLEMENTATION_v0.2.md)。作者提及的 `SITES_D_E_F_DESIGN_v0.1.md` 是设计输入，其中 Task 清单属于方案材料；本轮实施范围及未完成项以落地报告为准。交付时文件链接检查未在原路径找到该输入文件，因此不提供失效链接，也不将本轮文档冒充其原件。

## 2. 保留原矩阵，单列 R6

| 组 | 场地与配置 | 计划数 |
|---|---|---:|
| R2_MAIN | A；S0–S3 × 5 延迟 × 四监督器 × 20 seed | 1,600 |
| R2_PHASE | A；S1/S3 × 5 故障相位 × LST/FULL × 20 seed | 400 |
| R2_B2 | A；S0–S3 × B2_FAST × 20 seed | 80 |
| R3_HANDOFF | A/B；H_A/H_B × 5 交接时长 × 四监督器 × 20 seed | 800 |
| R4_SCALE | C；4/8/16 架 × 三负载 × LST/FULL × 10 seed | 180 |
| R5_NATIVE | A；S1/S3 × FIX/LST/FULL × 10 独立 seed | 60 |
| **R6_SITE** | **A–F × SINGLE/COMPETING × LST/FULL × 10 seed；延迟30 s** | **240** |
| R6_B2，可选 | 同六场地、两场景族、10 seed；真实快速计算，无人为30 s延迟 | 120 |

受控/快速基础 **3,300**；原生60；原开发428；R0计划33；基础合计 **3,821** 个运输计划槽位。原可选320 + R6_B2 120 = **440** 个可选槽位。R1 不计运输 run；本轮地图筛选、交通探针和单载荷诊断另立开发账本，不假装已包含在428中。计划槽位不是已执行数或独立样本数。

原 R2_PHASE 的80个零偏移单元仍只在完整签名一致时复用。新 R6 seed 为 **20271201–20271210**，与开发、主实验、原生 seed 不重合；R6 不默认复用 R2 轨迹。原27个 R0 回放证据保留，6个桥接仍待实现。

D 完整交接扫描、F 完整规模扫描、A+D/F 原生扩展是后续候选版本，不暗中替换本版 R3/R4/R5。原生仍为 GPT-6 Astra via Codex / high：60运输 run、400 CLI 启动设计上限，本轮没有新增模型调用。

## 3. R6 任务和公平性

`R6_SINGLE` 有一个受评价紧急任务及一个唯一载荷；360 s 发生共同外生中断，原载具按统一本地策略返航，备用空中或地面载具必须到同一交接设施接货。`R6_COMPETING` 有两个受评价紧急任务和两个独立载荷，其中一个在360 s释放或激活；二者共享至少一个合法优选备用资源，并受到设施容量约束。正式 fixture 必须具体说明该 tick 的释放、装载、故障和等待 episode 的顺序，不能让尚未装载的载荷出现在空中。

F 的三种 OD/task-class 库用于定义兼容性和场地签名，不把第三个任务偷偷加入 R6 主要指标分母。三任务压力、晚到 CRITICAL 与链式预约变体属于开发/后续扩展。每组的有效飞机、车辆、交接位、背景任务和候选图规模随 fixture 留档。

所有方法共享相同物理网络、设施、兼容矩阵、交通/故障事件、载荷初态和参数。D 的预留不得改变运输速度；E 的扰动改变实际 SUMO 世界而非只乘 ETA；F 的兼容性须由执行层拒绝非法指派。FULL 与 LST 仍共用同一 latest-start 内核。

E 的当前开发事件：参考 D1–H1 路径中段一组道路在330–450 s把实际速度上限降到2 m/s，然后恢复。事件文件与网络一起记录 hash。当前探针背景需求是合成设置，未校准真实交通；后续若改变背景或扰动强度，生成新 fixture 版本，并在正式方法比较前冻结。

## 4. Deadline 与时间窗口

期限只来自共同参考阶段图，不读取被比较策略表现或未来交通。装载15 s、交接30 s、卸载15 s是名义设计假设；并行到位取最大值。

- D：`fault_time + tau_ref(return + nominal handoff + onward transport + unload) + 30 s`。
- E：`release + tau_ref(nominal legal ground plan, including load/unload) + 60 s`。以事件前名义状态固定，拥堵后不放宽。
- F：`release_i + tau_ref(individual best legal plan_i) + slack_i`；本版开发初值 loose=90 s、tight=30 s，不以联合最优排程生成期限。

实际交接时长扫描不重算 deadline。当前 `fixtures/development/D|E|F/` 是带数值参考期限和逐任务阶段组成的**开发骨架**，未补齐完整物理初态和正式随机实现；F数值只是一条候选运输链，尚未认证为最优合法参考计划。其 `reference_only` 和未冻结标记不得被正式 runner 忽略。自由流 ETA 与实际含信号等待的行程时长不同，E 当前探针已显示这一差距。

正式 H=900 s 保持不变。若参考期限超过H或名义基线不能按时，记录构造失败并在开发阶段调整OD/负载/统一场景定义，不截断期限，不按 FULL/LST 正式结果筛 seed。本轮交通诊断延长观察至1800 s只是为了观察被截尾车辆到达，不把900 s后到达算作正式及时交付。

## 5. 场地身份、随机流和日志

规划单元必须包含 `site_id, scenario_family, fixture_version`。环境身份包含协议、场地、场景族、seed、网络/设施/兼容性/外生事件/参考期限 hash；不包含 method、执行顺序或模型响应延迟。相同数字 seed 在不同场地不是同一个环境。

随机流派生：`SHA256(protocol_id|site_id|scenario_family|seed|stream_name)` 的前64位。每个方法读取同一预生成外生实现；不按调用次数或本方法结果采样未来事件。

当前生成的是规划身份，统一标 `environment_identity_status=planning_only_formal_fixture_missing`。注册表的 `formal_signature=null`，不能把规划ID当作正式冻结 hash。正式晋级必须补全初态、事件、reference-plan/deadline manifest、控制器和估计器版本后生成完整签名。

日志在 v0.1 字段之外增加：场地和签名版本、网络/设施 hash；每任务参考计划、参考用时和期限生成规则；预约阶段、起止、转换与释放原因；ETA来源、快照时刻、预测/重算/实际用时；共同就绪、bay可用、交接开始/结束/中断原因。

`site_id` 等研究标签用于宿主日志和配对，不把城市、原型名称、未来限速表、事后 latest feasible start 或方法标签送入模型。模型仍只获得当前可见物理事实和共同估计。

## 6. 场地验收及统计

每场地独立报告：OSM下载、建网、路由、地图资产冻结、交通波动观察、单载荷闭环、多任务执行验收、正式fixture冻结。前三张新地图建成不自动使 G-D/G-E/G-F 或原G0–G4通过。

- G-D：真实共同就绪、单bay限制、第二任务排队、唯一保管权及预约不改变物理速度。
- G-E：共同ETA源、不读未来、事件一致，以及**固定的无控制器探针**可暴露预测误差。正式期限/负载还需通过900 s条件；不要求每个 held-out seed 都出现预设坏结果。
- G-F：执行层落实兼容关系、容量、原子分配、lease到期和下游释放；开发构造具备争用与机会成本潜力。净收益为零或负不是拒收地图的理由。

R6 是固定六场地面板。每个seed先计算12个 site×scenario 单元的 FULL−LST 失约比例差，再等权平均；以包含全部12单元和配对方法的完整seed block重采样10,000次，分析seed731605，报告95%区间。另列逐场地诊断，不把六个场地作为随机抽样城市，不与R2主要估计量混池。R6_B2只产生120个唯一快速参考，不因重复画图增加样本数。

## 7. 文档、执行入口与下一阶段

场地入口：[sites/README](../sites/README.md)。复核计划：`python -X utf8 -B research_hscc2027/tools/plan_experiments.py --check`；复核旧设计加 `--protocol v0.1`。场地 hash/图结构/配对检查见 `tools/site_screening/verify_sites.py`。

执行顺序更新为：**完整R1 → D双任务单bay → F多任务资源执行 → E期限/负载标定 → A/B/C统一signature及新语义fixture → R6正式单元冻结**，见 [顺序与机制定位](EXECUTION_PRIORITY_v0.1.md)。前置门未通过时不进入下一项验收。剩余R0桥接与原G0–G4适用门仍是正式运行条件。地图/fixture/控制器的实质改变必须新版本化。
