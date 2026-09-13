# 新版实验入口（2026-09-09）

后续实验统一使用 `tools/run_revision_v3.py`。新版本保留历史动作候选集，但重新运行同一 seed 的 baseline、A、B、AB；不读取历史单动作指标作为新交互的对照。历史结果只用于另行标注的事后分析。

**当前先做基线验收和诊断，不直接启动 10×50 搜索。** 真实 smoke 中，合成网 seed 701、demand_scale=1.0 的完成率为 82.90%，不满足新配置的 90% 可接受门槛。原因已定位为「输入持续到仿真结束，末端仍有运行和等待插入车辆」——完成率受观测时域影响，不是物理瘫痪。已在开发配置上把需求结束时刻与观测时域解耦（新增 `demand_end_s`，合成网设 1000；`simulation_end_s` 1200→1600），完成率由 82.9% 升至 98.1%，四个站点 baseline 验收均通过。这仍是开发校准，尚未构成论文正式实验计划。

## 已修改的实验契约

| 部分 | 新行为 |
|---|---|
| 合成需求生成 | 每个 OD、时间窗独立且可复现的随机流；增加需求追加车辆，减少需求取固定子集；原有车辆的 ID、出发时间保持不变。OD_ALL 仅作用于干预窗。车辆输入一致不意味着交通轨迹应一致，轨迹变化正是干预结果。 |
| 需求结束与观测时域 | 合成网新增 `demand_end_s`，需求在 `demand_end_s` 结束、观测到 `simulation_end_s`，二者解耦；恢复窗为 `[p_end, demand_end_s]`，之后为纯排空。缺省 `demand_end_s=None` 时退化为旧行为（需求与观测同止于 `sim_duration`）。 |
| 三城需求组合 | 在冻结路由车辆上追加需求，保留原车辆和路线；不同种子的 flow 归属若不一致则拒绝隐式套用。 |
| 队列指标 | 对已有采样时刻补零，时间缺口中断持续时长，按各 lane 长度求和。新版执行器拒绝不完整的队列输出。 |
| 运行与交通状态 | `execution_valid`、`endpoint_valid`、`traffic_outcome`、`single_action_acceptable` 分开保存。工程异常不能产生交通阳性；真实拥堵不会仅因完成率低而被当作进程错误。 |
| 四组交互 | baseline/A/B 均须可接受；四组终点须可测；新增边为 `SAB − S0 − SA − SB`。不合格结果照常保留，不能静默换 seed。 |
| 确认 | 诊断案例与概率确认分开；一次 severe 不再触发概率确认。报告资格率、可测条件下的交互率、四组事件率和二项区间。 |
| 搜索方法 | Random、修复后的 Heuristic、结构特征 LinUCB、无结果反馈 LLM、有结果反馈 LLM 使用相同合法 pair 集与 seed 日程。UCB 只学习本条轨迹；无反馈 LLM 保留动作信息、合法性提示与去重黑名单。LLM（含无反馈）另获得与 heuristic/UCB 相同的信息源头——特征公式（合成网 F1/F2/F3/intensity，三城四个 flag）以及合成网的 junction 图、demand corridor 路径——随 `STRUCTURE` 段进入 prompt，并纳入提案上下文 digest；结构信息变化会令已接受提案的上下文校验失败。 |
| 预算与恢复 | 事件账本只追加。合约失败与网络重试分别限额；401 等永久错误不重试；未知状态的请求/仿真不会自动重发；已保存结果可以恢复缺失的完成事件。 |
| 冻结与缓存 | manifest 保存配置、源代码/输入 SHA-256、候选空间和运行时版本。任何变化都要求新 campaign；缓存仅在同一 campaign、版本和 seed 内复用。 |
| 搜索前置条件 | 搜索前验证全部计划 seed 的 baseline。任一个不合格则停止，尚不发起模型请求或候选搜索；诊断模式仍可运行四组以调查失败原因。 |

主实现位于 `src/experiments/revision_v3/`。Synthetic 的回溢参数仍来自 `configs/failure_definition.yaml`；三城沿用各自冻结的回溢阈值和执行原语，共用新的状态分类与四组判据。这不是“各城市原语、需求压力和阈值完全相同”的实验设计。

## 在当前电脑运行

在 PowerShell 中进入本说明所在目录（`ITSAC_REPRO_BUNDLE`）。使用工作区已有虚拟环境：

```powershell
& ../.venv/Scripts/python.exe tools/preflight.py
& ../.venv/Scripts/python.exe -m unittest discover -s tests -v
```

预检查只读取资产及程序版本，不运行实验、不访问模型。测试包含临时目录中的小型 SUMO/duarouter 检查和模拟的 API 错误，无付费 API 请求。

先冻结合成网开发配置，然后只验收 baseline：

```powershell
& ../.venv/Scripts/python.exe tools/run_revision_v3.py prepare --config configs/revision_v3/synthetic_diagnostic.json
& ../.venv/Scripts/python.exe tools/run_revision_v3.py baseline --config configs/revision_v3/synthetic_diagnostic.json
```

检查 `outputs/revision_v3/synthetic_diagnostic_v3/baseline_acceptance.json` 和对应 `cells/.../result.json`。已完成首次校准：合成网 `demand_end_s=1000`、`simulation_end_s=1600`（需求结束/观测时域解耦），完成率 82.9%→98.1%，四个站点 baseline 均 `all_acceptable=true`。后续若再调参，仍应复制配置并更改 `campaign`，重新 prepare；不要放宽门槛以保留已看到的阳性，也不要根据 LLM 是否赢来选择压力。

三对候选的诊断命令如下。它会保留不合格四组，并明确不给出交互阳性，而不是中途筛掉它们：

```powershell
& ../.venv/Scripts/python.exe tools/run_revision_v3.py confirm --config configs/revision_v3/synthetic_diagnostic.json
```

该配置是 3 对 × 10 个开发 seed，最多 120 个单元；共享 baseline/单动作缓存可减少实际执行数。`confirm` 这个命令名同时用于 `diagnostic` 与 `probability` 两种模式；**当前所有 `*_diagnostic.json` 都只输出 DIAGNOSTIC_ONLY**。三城分别有 `beijing_diagnostic.json`、`shanghai_diagnostic.json`、`taipei_diagnostic.json`，用法相同。候选是开发诊断样例，不是预注册的最终筛选结果；701–710 不宣称全项目从未查看的测试池。

单对工程 smoke（新建独立输出、重跑四组）仍可使用旧快捷入口：

```powershell
& ../.venv/Scripts/python.exe tools/run_one_pair.py --pair A098,A202 --seed 701
```

四场景 smoke 与恢复检查：

```powershell
& ../.venv/Scripts/python.exe tools/smoke_revision_v3.py --tag my_check_01
```

tag 必须选择尚未使用的名字。smoke 成功只表示流程可执行，不表示候选阳性或研究假设得到支持。

## 搜索与模型调用

基线校准完成后，将一致的场景和门槛写入一份新的搜索配置，再 prepare。`synthetic_search.json` 已同步校准值（`demand_end_s=1000`、`simulation_end_s=1600`），提供五方法、每方法 10×50 的开发模板；将在四个站点诊断确认完成后启动。

```powershell
& ../.venv/Scripts/python.exe tools/run_revision_v3.py prepare --config configs/revision_v3/synthetic_search.json
& ../.venv/Scripts/python.exe tools/run_revision_v3.py search --config configs/revision_v3/synthetic_search.json --method random --run 1
& ../.venv/Scripts/python.exe tools/run_revision_v3.py status --config configs/revision_v3/synthetic_search.json
```

方法可选 `random`、`heuristic`、`ucb`、`llm_no_feedback`、`llm`。每个方法/run 单独执行；重复相同命令即恢复。当前 synthetic 模板的 baseline 若未过门槛，search 会按设计拒绝启动。

模型配置保存精确 model、temperature、最大输出 tokens、超时和两类重试限额。凭据放在环境变量或 bundle 的 `.env`（`CORP_AI_API_KEY`）；网关地址通过 `CORP_AI_BASE_URL` 或 `llm.base_url` 显式配置。prepare 和非 LLM 方法不要求密钥。模型后端已做在线验收：`deepseek-v4-pro` 为推理模型（单次 reasoning 实测 2.6k–9.5k token），原 `max_tokens=8192` 会被推理吃满（`finish_reason=length`）导致空 `content` 与连续 `SCHEMA_INVALID`，已把搜索配置的 `max_tokens` 调至 16384、`timeout_seconds` 调至 360；`reasoning_effort` 参数在真实全量 prompt 上无法压低推理量，不作为修复手段。smoke 实测 16384 仍不够：推理模型 completion 随机飙高（成功态 4k–15.5k，但约 45% 首次尝试顶满 16384、`finish_reason=length`、`content` 空；单 call 连续 3 次即 `ProposalStop` 停机），故搜索配置的 `max_tokens` 进一步调至 32768、`max_contract_attempts` 3→5（实测同 prompt 32768/65536 均 `finish=stop` 且 JSON 有效）。另修复 `proposals.py` 传输重试漏捕获 `http.client.RemoteDisconnected`（网关断连会直接冒泡导致整条搜索停机），现与 `ConnectionError`/`http.client.HTTPException` 一并按可重试传输错误处理（计入 `max_transport_errors`）。

每个可评价的候选消耗一次搜索预算，即使单动作不合格或没有交互。执行无效分两级：baseline 单元执行无效（校准/工程问题）仍会停机；候选 A/B/AB 单元执行无效——例如车道关闭时刻目标车道未清空触发的 `Unsafe lane-closure activation` 安全拒绝（sumo_runner 故意 fail-closed，避免人为制造紧急制动/碰撞）——在搜索阶段被记录为不可评估候选（`execution_invalid=true`、`interaction_positive=false`，消耗预算、不自动替换）并继续。诊断/确认阶段保持严格停机（其候选为预选安全对，执行无效即真问题）。共享仿真缓存不会给方法额外公开其他方法的历史结果。10 次搜索共用固定 seed 池，只能研究该池内的搜索变化，不能写成十组独立交通环境。

搜索按用户选择以 5 个独立 campaign 并行执行（`synthetic_search_v4_{random,heuristic,ucb,llm_nofb,llm}`，每方法一个 config 且 `methods` 只含自身；共享相同 seed 日程与合法 pair 集）。结果与单-campaign 串行等价（确定性 seed 日程），仅分散在 5 个根目录，合并分析时按 `(method, run)` 对齐。此并行化偏离冻结的单-campaign 组织，只改变结果存放位置与 wall-clock 耗时，不改变任何候选评估结果。

`search/run_XX/METHOD/state.json` 区分 RUNNING、COMPLETED 和 NEEDS_ATTENTION。未完成 B 次的轨迹不能冒充 Hits@B 完整结果。`events.jsonl` 记录单元执行尝试，`proposal_events.jsonl` 记录提案尝试；原始响应保存 model、usage、response ID。尝试次数不是供应商已核实的计费次数，超时请求也可能已产生费用。当前交付完成执行与诊断管线；正式方法间统计检验、机制去重规则及图表应随正式分析计划另行冻结。

若进程被强制终止，先核对 `.run.lock` 中 PID；只有确认原进程已结束才移除过期锁。存在未完成请求时，检查保存的 prompt/response、账本和提供商记录；存在未完成仿真时检查原始 XML/日志。不要删除 attempt 目录后盲目重试。不确定的失败应保留并标注，必要时建立新 campaign。

## 正式概率确认

复制诊断配置，设置 `mode: "probability"`，固定候选、确实未用于选择的新 seed 集，以及 `confirmation` 中的 `p0`、`alpha`、`family_size`、`min_eligible`。候选家族数必须与候选数一致。程序使用单侧精确二项检验并按候选数做 Bonferroni 校正；资格不足或合格四组中存在终点不可测时输出 INCONCLUSIVE。95% 区间是描述性逐候选区间，不是家族同时置信区间。

正式运行前仍需确定有实际意义的备择概率、样本量/功效、候选筛选和主终点；不要把现在的默认开发 seed 与事后诊断称为完整预注册。条件率以合格且可测四组为分母；四组事件率以全部已评价 seed 为分母，需同时报告缺测和资格率。

## 历史数据与回滚

原始源码备份在工作区 `revision_v3/original_sources.zip`，逐文件哈希在 `original_sources_sha256.json`。旧输出未覆盖。旧 P22 controller 与三城旧执行路径已加迁移提示，避免新生成器与旧对照缓存混用；旧文档和分析结果属于历史协议。需要按旧算法复核时，应把归档源码解压到独立副本，不要覆盖正在使用的新工作区。

只读历史重分析：

```powershell
& ../.venv/Scripts/python.exe tools/reanalyze_legacy_v3.py --output ../revision_v3/legacy_reanalysis_second.json
```

本次已输出 `../revision_v3/legacy_reanalysis.json`：北京旧四组按新状态规则重分类；模型状态计数、保留 attempt metadata、清理日志分列，并保留输入哈希。DeepSeek/GLM 保留 metadata 为 515/523，状态曾记录 266/439，保留的合约失败为 16/24。清理日志另报告 12/16 个被移除目录；因旧清理日志可能被覆盖，报告不把它们包装成精确历史计费总数。重新分类旧结果不能补救旧随机数控制问题，也不能变成新概率确认。

## 本次验收证据

- `../revision_v3/tests_final.log`：48 项测试通过。
- `../revision_v3/preflight_final.log`：8 项预检查通过。
- `outputs/revision_v3/smoke_final_20260909_report.json`：合成网、北京、上海、台北各一对 × 一个 seed × 四组，共 16 个真实单元；恢复后新增执行数为 0。
- `../revision_v3/search_smoke.json`：北京 Random 一次候选搜索完成，4 个真实单元；再次执行无额外仿真。
- 这些是工程小样本；北京 smoke 有一个可接受四组的交互案例，上海/台北样例为阴性，合成样例基线不合格。均不支持概率或方法优劣结论。没有运行付费 LLM 搜索或正式 10×50 批次。

较早调试输出也保留在 `outputs/revision_v3/smoke_acceptance_*`，不要与最终验收混合。正式实验应新建独立 campaign。
