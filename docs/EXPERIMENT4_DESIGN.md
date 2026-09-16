# 实验 4 设计：LLM 监督的运行边界（修订版 2，2026-09-09）

> 本文为修订版，落实 `reports/EXPERIMENT4_INDEPENDENT_REVIEW_20260909.md` 的全部 P0/P1
> 整改：4A 改为**三时钟真正信息刷新**，4C 改为**输入规模实验**，并修复进程隔离、
> 时序、pending 队列、触发继承与统计分析。版本号 `experiment4.version = 2`。

## 1. 研究问题

监督式重配置依赖一个 LLM 监督器在运行时感知全局状态并做出调度决策。三个运行参数
决定该监督器的能力边界：

- **4A 信息刷新频率**：监督器多久才获得一次新的全局状态快照？刷新越慢，它对
  新任务与故障的发现越迟（发现延迟 ∝ 刷新间隔），决策输入越陈旧。
- **4B 推理延迟**：从“做出决策”到“决策落地”之间的延迟多长？延迟越大，决策在
  执行时越可能已经失效（`STALE_REJECTED`）。
- **4C 状态规模（输入负担）**：全局状态条目越多，LLM 是否越难在**同一个**决策
  问题上选出与参考一致的最优解（token 与错误随规模如何增长）？

三个子实验共用同一套冻结机制，只改变一个自变量。

## 2. 冻结复用与可追溯

- 冻结测试台 `S0_3p2km_v1`：SUMO 1.27.1 + BlueSky + Python 编排器，3.2 km × 3.2 km
  苏州 OSM 区域，4 机基础机队（L-UAV-01、EVTOL-01、M-UAV-01、M-UAV-02）。
- 管线：Global State v1 → manager → normalize → semantic（`E2SemanticValidator`）→
  feasibility（`E2FeasibilityChecker`）→ executor → SUMO/BlueSky。
- 候选表 2.1.0（E2 `E2CandidateEvaluator`）；B2 权重冻结
  `config/experiment1_b2_weights.yaml`；动作契约 v2；状态机与故障注入器冻结。
- LLM = `corp-ai/openai/deepseek-v4-pro`（`config/phase3_config.yaml`，
  `frozen_simulation_decision_mode: true`）。
- **不修改任何冻结组件**：E4 只新增文件与配置；E4 从 `Experiment2Runner` 继承，但
  把 E3 v2 的“全任务周期触发”修复一并纳入（见 §5.4），避免“复用冻结组件”退化为
  “保留已知缺陷”。

统计单元 = scenario × seed；四个 manager（B0 / B1 / B2 / B4b）在**同一**
(scenario, seed) 上配对，种子为冻结的 20 组 `20240601..20240620`。

## 3. 运行结构（P0 进程隔离 + cohort 分离）

```
runs/experiment4/<cohort>/<sub>/<arm_id>/<scenario>/seed<seed>/<manager>/
    ├─ metrics.json, run_config.yaml, run_meta.json
    ├─ actions.csv, violations.csv, action_pipeline.jsonl
    ├─ manager_inputs.jsonl, manager_outputs.jsonl, candidate_info.jsonl
    ├─ semantic_checks.jsonl, feasibility_checks.jsonl
    └─ run_console.log
```

- **每个运行在独立子进程中执行**（`tools/run_experiment4.py` 的父进程只调度，不再
  在多线程里共享 BlueSky/TraCI 实例；`--direct` 在子进程内跑单个组合）。
- **cohort 分离**：`pilot` 与 `primary` 分目录，重跑一方不会覆盖另一方。
- **完整性校验**：`run_is_current` 在 `run_config.yaml` 中核对 `matrix_version` 与
  `matrix_hash`（冻结矩阵的 SHA-256），不一致则视为过期并重跑。

样本量：4A 5 臂 + 4B 7 臂 + 4C 5 臂 × 4 manager × 20 种子 = **1,360** 个 primary 运行；
pilot = 3 个 pilot 配置 × 3 个 pilot 种子 = 9 运行。

## 4. 4A — 信息刷新频率（三时钟）

### 4.1 三个时钟

| 时钟 | 含义 | 实现 |
|---|---|---|
| 物理事件 | B1 封路 / 应急任务释放 / F1 失联 | 冻结；t=300 释放 + t=371 失联 |
| 观测快照刷新 | 监督器的状态快照多久刷新一次 | 每 `obs_interval_s` 秒，`_refresh_observation_if_due` |
| 管理器决策 | 监督器何时再决策 | 每个观测刷新点 + 每次破坏性事件 |

**监督器永远基于最新观测快照决策，从不读取实时状态**；局部安全层（C2 应急返航
V3）仍即时响应失联，与观测无关。因此：

- 发现延迟 = 下一个观测点 − 故障时刻；
- 调用次数 ∝ 1 / 观测间隔；
- 快照年龄 = 决策时刻 − 快照时刻（写入 `manager_inputs.jsonl` 的
  `observation_snapshot_time` / `observation_snapshot_age_s`）。

### 4.2 臂与故障相位

故障时间取**非对齐**的 `t = 371`（`E4_REFRESH`），使发现延迟随间隔单调：

| 臂 | 观测间隔 | 故障发现时刻 | 发现延迟 |
|---|---|---|---|
| OBS10  | 10 s  | 380 | 9 s |
| OBS30  | 30 s  | 390 | 19 s |
| OBS60  | 60 s  | 420 | 49 s |
| OBS120 | 120 s | 480 | 109 s |
| OBS300 | 300 s | 600 | 229 s |

应急任务 deadline = 480 s（t=300 释放 + 180 s 松弛），因此 OBS120/OBS300 会因发现
过晚而截止违约，形成清晰的单调信号。正式v2采用离散时钟：标记为t的快照在前一物理步结束后生成，
随后才注入t时刻的新事件。因此同秒快照不包含刚注入的任务，snapshot_age=0只表示时间标签一致。
任务在t=300释放后，OBS10/30/60/120/300首次看见任务的时刻分别为310/330/360/360/600。
4A测量的是**完整观察调度机制下，新任务与故障信息可见性的代价**；任务发现、故障发现和重评估次数一起变化。
这是本次正式数据的采样约定，保留该机制和原始运行，未改成事件后即时刷新或补跑其他相位。

### 4.3 指标

`failure_discovery_latency_s`、`snapshot_age_s_max`、`num_manager_decisions`、
`redundant_decision_count`、`decision_switch_count`、`decision_oscillation_count`，以及继承的
`critical_mission_completion_time_s`、`critical_mission_deadline_violation`、
`recovery_success`、`failure_to_replan_latency_s`、`llm_total_*_tokens`。

2026-09-10论文分析口径：`failure_to_replan_latency_s`只计首个ISSUED的关键任务运输/重规划动作，
排除NO_ACTION；`recovery_success`与`recovery_time_s`仅在关键任务确实受影响时有定义；
模式/资源改变计为switch，切换后回到先前模式/资源才计为oscillation（不自动判为不必要）。
由 `tools/paper_metrics.py` 从原始动作日志生成派生指标，原始metrics保持不变。

## 5. 4B — 推理延迟（Mode B 延迟执行）

### 5.1 机制

在 S_t 上决策，在 S_(t+delay) 上重新做 semantic + feasibility 校验后执行；失效即
`STALE_REJECTED`（**从不静默修复**）。`delay_s = 0`（D00）必须与冻结 Mode A 完全一致。

### 5.2 时间片顺序（修复）

每个时间片 `t` 内的固定顺序：

```
物理步进前： 应用 t 时刻全部外生事件（含失联/封路）
           → 执行 t 时刻到期的 pending 动作（在同一 t 的事件之后）
物理步进后： 推进 SUMO/BlueSky → 更新注册表 → 地面兜底 → (4A 观测刷新) → 记账
```

因此同一时间戳的**事件先于** pending 动作，pending 的 checker 复核看到的是事件后的
状态。校验实现于 `Experiment4Runner._step_once`（对 4B/4C 为无操作钩子，行为与冻结
一致）。

### 5.3 pending 队列语义

- **任务版本化**：同一 mission 的新决策把旧 pending 置为 `SUPERSEDED`；
- **幂等去重**：执行前若目标已完成/已取消/已失败，或 GROUND_FALLBACK 的 mission
  已在 `GROUND` 模式，或 DISPATCH/REASSIGN 的目标 mission 已由同一资源
  `ASSIGNED`/`EN_ROUTE`，则置为 `SUPERSEDED` 不重复执行（不重跑地面计时器）；
- **失效**：执行时 semantic/feasibility 复核失败 → `STALE_REJECTED` 并触发一次
  重规划。

### 5.4 全任务周期触发（继承 E3 v2）

`_periodic_due` 对**任一** `WAITING/NEEDS_REPLAN/INTERRUPTED` 的 mission 触发，
而非仅主任务（继承 E3 `experiment3_runner.py` 的修复），保证次级应急与背景
`NEEDS_REPLAN` 任务后续仍有机会被恢复。

### 5.5 指标

`deferred_action_count`、`stale_rejected_count`、`superseded_action_count`、`delay_s`，
以及继承的恢复/截止/振荡/冗余指标。

## 6. 4C — 状态规模（输入负担）

### 6.1 设计

**核心决策问题在全部臂中完全相同**：4 机基础机队 + M-CRITICAL-001 + F1 失联
（t=360，M-UAV-02）+ 参考最优动作。额外 N−4 个条目全部是**惰性干扰项**
（`orchestrator/experiment4_fleet.py: generate_distractors`）：

- 干扰项飞机：`UNAVAILABLE`、`commandable=False`、`reassignable=False`、零续航、
  着陆兼容性只含干扰点（不含 V1/V2/V3）→ 在候选表中永远是 **illegal 行**；
- 干扰项着陆点：`DX1..DX6`（`backup_landing_site`，从不作为任务终点）；
- 干扰项任务：`COMPLETED`（永不 actionable）。

因此 N 只增加输入（GS air / infrastructure / missions 与候选表 illegal 行），
**不改变合法候选集、故障或最优解**。B1/B2 对规模不变（其候选过滤确定性剔除干扰
项），构成参考；B4b 随规模退化即“LLM 上下文边界”。

### 6.2 臂与指标

臂 = 总机数 N ∈ {5, 10, 20, 30, 50}（干扰项数 = N−4 ∈ {1, 6, 16, 26, 46}）。

指标：
- **不变性校验**：同一seed、manager、决策时刻的合法候选资源集合跨臂相等；
  `legal_candidate_count_mean`仅为按实际调用次数加权的描述量，额外重试会改变其均值；
- **选择质量** `legal_selection_count` / `illegal_selection_count` /
  `absent_selection_count`（选中资源是合法候选 / 非法（干扰项）候选 / 表中不存在）；
- 规模代价 `prompt_size_chars_mean`、`llm_total_*_tokens`；
- 约束违约 `constraint_violation_count`、`duplicate_assignment_count`、
  `priority_inversion_count`、`forgotten_aircraft_count`（排除干扰项）。

## 7. 分析计划（`tools/analyze_experiment4.py`）

配对（arm vs 锚点，同 manager 同 seed）：

- 连续指标：**配对 Wilcoxon 符号秩** + 跨臂族 **Holm 校正** + **Cohen's d**（合并
  方差；零方差且均值不等 → 记“未定义”而**不是 0**）+ 配对差 **95% CI** 与 arm-Δ；
- 二元指标（`critical_mission_deadline_violation`、`recovery_success`）：**McNemar**。

锚点：4A=OBS30、4B=D00、4C=N05。输出 `outputs/experiment4_summary.md` + `.json`，
逐臂保留绝对值、有效分母、配对差与CI；比例采用Wilson区间。最终论文统一入口为 `outputs/paper_final/results.json`。

## 8. 放行门槛（运行前）

1. 全部离线验收通过（12 项：配置/种子/干扰项确定性/惰性/计数/构造/触发/4A 观测轮询/
   4B 延迟+版本化+幂等/时序/分析助手）；pytest 不可用时直接调用 `test_*` 函数。
2. 4A 证明自变量确实改变观测与重评估机会（调用数 ∝ 1/间隔、发现延迟 ∝ 间隔）；
   4B 证明量到的是延迟机制（D00 与参考管线逐事件一致）；4C 证明每个 N 的合法候选
   集不变、故障与负载满足设计。
3. 不调用 LLM 的闭环先导先通过，再做小规模 LLM 先导；固定后端错误与重试规则，
   完整保留失败记录。
4. 版本、配置、cohort 与统计方案冻结后，再确定正式样本量与完整矩阵。

## 9. 可比较性说明

- 4A 的观测快照机制只存在于 E4 4A，不影响 4B/4C（`obs_interval_s=0` 时行为与冻结
  Mode A 一致）；4B 的 `_step_once` 钩子在 D00 下为无操作；4C 只追加惰性条目。
- 4B 的 D00 与实验二 F1-C2 冻结结果应逐事件一致，作为回归校验。
- 4C使用同seed、manager、时刻的合法集合校验“输入规模”构念，防止将干扰项误做成可用资源。
