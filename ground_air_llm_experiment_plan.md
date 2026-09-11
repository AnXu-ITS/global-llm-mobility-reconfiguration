> **2026-09-10状态：四实验完成，进入写作。** 本文保留设计与实现沿革；最终数据、统计口径与论文叙事统一见 `reports/PAPER_STORY_AND_WRITING_GUIDE.md`、`reports/README.md` 和 `outputs/paper_final/results.json`。

# 实验计划书
## Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Cross-Layer Disruptions

---

# Current Frozen State after Experiment 1 Finalization

> This section reflects the **current validated implementation**, not the
> original design intent. It is maintained in lock-step with
> `reports/experiment1_final/` and the frozen configs/schemas.

- **canonical testbed**: `S0_3p2km_v1`
- **study area**: 3.2 km × 3.2 km, center = **31.30377 N, 120.59981 E**
- **exchange CRS**: EPSG:4326
- **current canonical base fleet** (4 aircraft, from `config/scenario_config.yaml`
  and `config/resource_compatibility.yaml`):
  - `L-UAV-01` — logistics_uav
  - `EVTOL-01` — passenger_evtol
  - `M-UAV-01` — medical_uav
  - `M-UAV-02` — medical_uav
- **SUMO + BlueSky + Python Orchestrator**: validated and frozen
- **master simulation step**: 1 s
- **Global State**: frozen schema `schemas/global_state_v1.schema.json`
  (`schema_version = 1.0.0`)
- **Action Contract**: LLM-facing contract **v2** (prompt `prompts/manager_v2.txt`,
  12 action types incl. the REASSIGN preemption rule); authoritative structural
  schema = `schemas/manager_action_v1.schema.json` (title `ManagerAction v1`)
- **LLM prompt**: `manager_v2` frozen
- **B2 objective**: frozen before final primary rerun
  (`config/experiment1_b2_weights.yaml`)
- **Candidate Generator**: manager-agnostic
- **Candidate Table**: contains **no** B2 objective score / ranking /
  recommendation leakage
- **Primary managers**: B0, B1, B2, B4b
- **LLM variants**: B4a = LLM-State (prompt-only, no candidate table);
  B4b = LLM-Candidate (candidate table rendered into prompt) — B4b is the
  primary LLM method
- **Experiment 1 final primary dataset**: **960 runs** =
  12 scenarios × 20 independent seeds × 4 primary managers
- **B4a ablation**: **60** independent-seed runs
- **total final Experiment-1 runs**: **1020**
- **excluded runs**: **0**
- **acceptance**: EF-T1 … EF-T20 = **20/20 PASS**
- **old pre-fix / v2 Experiment-1 datasets**: superseded for primary statistical
  analysis; preserved only for provenance/debugging
- **next research stage**: Experiment 2 — Air-Layer Failure Management

> **Historical / default design references (NOT current):** earlier values such as
> **5 km × 5 km** and **12-aircraft S0** are historical/default design references
> and are **NOT** the current frozen Experiment-1 / Experiment-2 base
> configuration. The current base is 3.2 km × 3.2 km with 4 aircraft.

---

# Source-of-Truth Hierarchy

When this Markdown conflicts with frozen project artifacts, the following order
wins:

1. frozen configs / schemas
2. final Experiment-1 reports (`reports/experiment1_final/`)
3. SHA-256 hash manifest (`outputs/file_hashes_final.json`)
4. current code implementation
5. these Markdown documents

This revision aims to eliminate such conflicts. Any future change to the frozen
protocol requires: (1) a CHANGELOG entry, (2) a new version identifier, (3) an
impact-on-comparability statement, and (4) no silent overwrite of the historical
protocol.

---

## 1. 项目目标

本研究构建一个由 **SUMO + BlueSky + Python Global State Hub + LLM Supervisory
Manager** 组成的空地协同交通仿真平台，研究在地面交通受扰、低空交通自身存在
既有任务且可能进一步发生失效的情况下，不同 supervisory decision policies 如何
对有限低空资源进行选择性的重构与调度。LLM 是其中的一个 candidate supervisory
policy，本研究不以"证明 LLM 优于 baseline"为预设目标。

本研究不假设近期存在大规模、高密度、类似道路拥堵的城市低空交通。相反，低空
交通被建模为：

> **一个稀疏、异质、昂贵但响应迅速的城市韧性资源层。**

环境中原本已经存在少量低空交通，包括物流 UAV、医疗 UAV、巡检 UAV、警务/应急
UAV，以及少量载人 eVTOL。这些航空器本身已有任务，并非闲置的应急储备。

当地面交通出现重大扰动时，supervisory manager 需要判断：

1. 是否需要调用低空资源；
2. 应调用哪些航空器；
3. 是否应中断或延迟原有低空任务；
4. 如何在任务优先级、系统风险与资源约束之间做全局权衡；
5. 当低空支援层进一步发生通信、定位、基础设施或飞行器失效时，如何重新配置系统。

---

## 2. 核心研究问题

### RQ1 — Selective Ground-to-Air Support

**Can different supervisory decision policies selectively mobilize sparse
low-altitude resources under ground disruption while limiting damage to existing
air services?**

重点研究：
- 哪些地面任务值得转移到低空；
- 哪些现有低空任务可以被中断；
- 如何权衡紧急收益与正常服务损失；
- 是否能够保留低空系统必要的安全与冗余资源。

> Experiment 1 **不以"证明 LLM 优于 baseline"为目标**，而是刻画不同
> supervisory policies（无协同、规则/air-first、冻结优化、候选信息增强的 LLM）
> 在同一结构化 ground-disruption allocation 任务上的行为与权衡。

### RQ2 — Air-Layer Failure Reconfiguration

**Does the comparable aggregate performance of the frozen optimizer and the
candidate-informed LLM persist when the aerial resource layer itself becomes
unreliable?**

中文说明：Experiment 1 已表明，在**无 air-layer failure** 的结构化
ground-disruption allocation 中，B2（冻结优化）与 B4b（候选信息增强 LLM）的
aggregate critical-mission performance 接近，但 service–speed operating point
不同。Experiment 2 因此研究：**当 feasible candidate set 因 air-layer failure
动态改变时，这种接近是否仍然存在？** Experiment 2 不预设 B4b 会赢。

重点失效场景：
1. C2 Lost Link
2. GNSS / Localization Degradation
3. UTM / U-space Service Outage
4. Vertiport / Landing Site Failure
5. Unknown / Non-Cooperative Aircraft Intrusion
6. Flyaway / Uncontrolled Trajectory

### RQ3 — Compound Disruptions

**当多个地面与低空事件同时发生时，不同 supervisory policies 的性能和行为如何
分化？**

研究重点：

\[
Ground\ disruption
+
Existing\ air\ missions
+
Emergency\ request
+
Air\ failure
\]

### RQ4 — Operational Viability of LLM Supervision

**在什么信息更新频率、推理延迟和系统规模下，LLM supervisory management 仍然
有效？**

重点研究：
- 信息刷新频率；
- Event-triggered 调度；
- LLM inference latency；
- Global-state scale；
- 状态输入长度与约束遗漏；
- 决策稳定性。

---

## 3. 总体仿真架构

```text
                     ┌─────────────────────────┐
                     │ Global LLM Manager      │
                     │ supervisory decisions   │
                     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │ Python Global State Hub │
                     │ state abstraction       │
                     │ candidate generation    │
                     │ event detection         │
                     │ action execution        │
                     └───────────┬─────────────┘
                            ┌────┴────┐
                            │         │
                            ▼         ▼
                       ┌────────┐ ┌──────────┐
                       │  SUMO  │ │ BlueSky  │
                       │ Ground │ │   Air    │
                       └────────┘ └──────────┘
```

### 3.1 SUMO

负责模拟：
- 城市道路网络；
- 正常地面交通；
- 道路事故；
- 桥梁 / 关键路段关闭；
- 医院等关键设施可达性；
- 地面紧急任务；
- ground fallback；
- 信号控制 / emergency routing（如后续需要）。

### 3.2 BlueSky

负责模拟：
- 已有 UAV / eVTOL；
- 航空器位置与任务；
- 低空起降点；
- 航空器可用性；
- 路线与任务状态；
- C2 / GNSS / UTM 等状态抽象；
- 航空器失效与 contingency 状态；
- landing site availability。

第一阶段不重点研究高密度 air congestion。

当前 frozen base fleet 为 4 架（见页首 "Current Frozen State"）。scale
sensitivity（Experiment 4C）可在不改变 base fleet 的前提下独立扩展机队规模：

\[
N_{air}=5\sim30
\]

后续扩展至：

\[
N_{air}=50
\]

### 3.3 Python Global State Hub

负责：
1. 同步 SUMO 与 BlueSky 仿真时钟；
2. 每个仿真步收集 ground / air 状态；
3. 将 raw state 压缩为 LLM 可读的 structured global state；
4. 运行 manager-agnostic candidate generator，生成 shared candidate set；
5. 识别关键事件；
6. 决定是否触发 manager；
7. 检查 manager 输出格式；
8. 调用 semantic validator + safety / feasibility checker；
9. 将合法动作分别下发至 SUMO 与 BlueSky；
10. 记录所有系统状态、事件、决策和结果。

---

## 4. 时间尺度设计

| 层级 | 功能 | 时间尺度 | 是否由 LLM 控制 |
|---|---:|---:|
| L0 | flight control / stabilization | ms–sub-second | 否 |
| L1 | tactical avoidance / local contingency | 秒级 | 否 |
| L2 | global mobility reconfiguration | 10s–minutes | 是 |
| L3 | long-horizon planning | minutes–hours | 可选 |

LLM 不承担任何必须亚秒级响应的安全动作。

例如 C2 Lost Link：

\[
C2\ Lost
\rightarrow
Local\ Contingency\ Procedure
\]

立即执行。

随后才：

\[
Failure\ Event
\rightarrow
Manager\ Global\ Reconfiguration
\]

---

## 5. 信息交换方式

### 5.1 SUMO–BlueSky

使用 simulation-time co-simulation。

基础仿真步长：

\[
\Delta t_{sim}=1s
\]

每个仿真步：
1. SUMO step；
2. BlueSky step；
3. 收集状态；
4. 更新 global state；
5. 检查是否触发 manager。

### 5.2 Manager 更新策略

采用：

\[
Periodic + Event\text{-}Triggered
\]

正常周期初始设置：

\[
\Delta t_{manager}=30\sim60s
\]

以下情况立即请求重新调度：
- major road disruption；
- new critical mission；
- C2 Lost Link；
- GNSS degradation；
- UTM outage；
- landing-site failure；
- unknown aircraft intrusion；
- flyaway；
- mission infeasibility；
- critical battery / resource loss；
- system state crosses risk threshold。

---

## 6. Global State 输入设计

Manager 不直接读取 raw simulator logs，而是读取抽象后的状态。当前 frozen schema
为 `schemas/global_state_v1.schema.json`（`schema_version = 1.0.0`）。

### Ground State
- 当前事故 / 路段关闭；
- 受影响区域；
- 关键设施可达性；
- emergency mission；
- 当前地面 ETA；
- ground fallback 可行性；
- ground delay trend。

### Air Fleet State
每个航空器至少包含：
- ID
- Type
- Current mission
- Mission priority
- Availability
- Battery / remaining endurance
- Location
- Destination
- Landing-site compatibility
- Current failure state
- Reassignable or not

### Air Infrastructure State
- landing-site availability；
- UTM status；
- GNSS status；
- weather restriction；
- temporary restricted area；
- unknown aircraft alert。

### Mission State
- mission ID；
- type；
- urgency；
- deadline；
- origin；
- destination；
- payload / passenger class；
- whether ground fallback exists；
- cost of delay；
- cost of cancellation。

### Temporal Trend

不仅给单个 snapshot，还提供：

\[
S_{t-k},S_t,\Delta S
\]

例如：

```text
Hospital H2 ground ETA:
7 min -> 12 min -> 18 min
Trend: rapidly worsening
```

---

## 7. Manager Action Space

Manager 仅输出 high-level actions。权威 action contract 为
`schemas/manager_action_v1.schema.json`（title `ManagerAction v1`，12 个 action
type），LLM-facing contract v2 语义见 `prompts/manager_v2.txt`（含 REASSIGN
preemption 规则）：

\[
A=
\{
DISPATCH,
REASSIGN,
REROUTE,
DELAY,
CANCEL,
RESERVE,
DIVERT,
RETURN,
LAND,
GROUND\_FALLBACK,
NO\_ACTION,
ESCALATE
\}
\]

禁止直接输出：
- pitch
- roll
- yaw
- thrust
- 秒级避碰动作

---

## 8. Safety / Feasibility Checker

Manager 输出不得直接执行。

必须经过传统 checker 检查：
- battery 是否足够；
- route 是否可行；
- landing site 是否可用；
- aircraft type 是否适配；
- mission deadline 是否可能满足；
- safety constraint 是否满足；
- local contingency 是否冲突；
- 是否违反硬约束。

若不可行：
1. 拒绝该动作；
2. 记录 infeasible decision；
3. 可选择调用 fallback rule 或再次请求 manager 重新规划。

当前实现还包含 shared Semantic Validator（`safety/semantic_validator.py`），在
Feasibility Checker 之前做 schema + semantic 校验。normalize-then-validate
契约见 `EXPERIMENT_IMPLEMENTATION_SPEC.md`。

---

# 9. Experiment 0 — Co-Simulation Validation

## Status: COMPLETED

SUMO–BlueSky–Python Hub 的基础闭环已建立并通过验收（Phase 1/2/3）。

## 最小场景

1. SUMO 正常运行；
2. BlueSky 中存在若干正常低空任务；
3. SUMO 某关键道路关闭；
4. Python Hub 产生 GroundDisruptionEvent；
5. 某低空任务被重新分配；
6. BlueSky 中支援 UAV 执行任务；
7. UAV 发生模拟故障；
8. Python Hub 触发 fallback；
9. ground 或其他 air resource 接管任务。

## 验证内容
- simulation clock synchronization；
- event timestamp consistency；
- state transfer；
- mission assignment；
- action execution；
- log reproducibility；
- deterministic replay。

## 成功条件

所有事件能在统一时间轴上复现，且跨层命令能够正确执行。已达成。

---

# 10. Experiment 1 — Ground Disruption and Selective Air Support

## Status: COMPLETED AND FROZEN

冻结证据与最终数值见 `reports/experiment1_final/EXPERIMENT1_FINAL_RESULTS.md`
及同目录其他报告。本节只记录 final protocol 与 headline results。

## Primary managers

| manager | 含义 |
|---|---|
| **B0** | No Cross-Layer Coordination（ground-only） |
| **B1** | Rule-Based / Air-First baseline |
| **B2** | Frozen Optimization（heuristic objective ranking） |
| **B4b** | LLM-Candidate（primary LLM method） |

## Interface ablation

| arm | 含义 | input |
|---|---|---|
| **B4a** | LLM-State | Global State + Action Contract v2（**no** candidate table） |
| **B4b** | LLM-Candidate | Global State + **manager-agnostic structured Candidate Table** + Action Contract v2 |

> 不再使用旧的 "B3 = generic LLM" / "B4 = LLM + checker" 作为正式当前命名。
> 当前正式 LLM 命名只有 B4a（LLM-State，interface ablation）与 B4b
> （LLM-Candidate，primary method）。

## 初始环境

低空环境原本存在（4-aircraft frozen fleet）：
- 1 × logistics UAV（L-UAV-01，busy）；
- 2 × medical UAV（M-UAV-01 / M-UAV-02，standby）；
- 1 × passenger eVTOL（EVTOL-01，busy）；
- 原有 mission schedule（2 background services）。

不是空载等待状态。

## Ground Disruption Families（frozen 实现为 B1/B2/B3 三类 disruption link）

- **B1**（high impact）：D1→H1 ETA +37.87 %；
- **B2**（medium impact）：+15.43 %；
- **B3**（low impact）：+7.16 %。

原始 G1–G4 描述保留为历史设计参考；当前 frozen 实现用 3 类候选 disruption
link（互斥，不同时发生）+ critical mission（medical_blood，V2→V1）。

## Final dataset（Finalization §13）

- 12 scenario classes
- × 20 genuinely different simulation seeds
- × 4 primary managers（B0 / B1 / B2 / B4b）
- = **960 primary runs**

plus:

- 60 B4a independent-seed ablation runs（6 scenarios × 10 seeds）

**Total: 1020 runs. 0 excluded.**

- same-prompt repeated calls are **NOT** statistical replicates.
- independent experimental unit = **scenario × simulation seed**.

## Final headline results（从 `EXPERIMENT1_FINAL_RESULTS.md` 抄录）

| manager | completion (s) [95 % CI] | deadline violation | service damage | unnecessary air |
|---|---|---|---|---|
| B0 | 187.7 [183.6, 191.7] | 33.3 % | 0.000 | 0 % |
| B1 | 160.8 [154.3, 167.3] | 25.0 % | 0.500 | 33.3 % |
| B2 | 147.6 [142.2, 153.1] | 16.7 % | 0.058 | 0 % |
| B4b | 146.6 [141.4, 151.9] | 16.7 % | 0.133 | 5 % |

B4a vs B4b ablation（n = 60 paired）：B4a（无候选表）air-intervention 100 %、
completion 177.5 s、damage 0.667、unnecessary-air 33.3 %；B4b（有候选表）air
61.7 %、completion 163.9 s、damage 0.283、unnecessary-air 11.7 %。

## Frozen scientific conclusions

1. Selective low-altitude support improves disrupted critical-mission performance
   relative to no coordination.
2. Air-first intervention is not selective and causes excessive damage to existing
   services.
3. B2 and B4b achieve comparable aggregate critical-mission performance on the
   frozen Experiment-1 testbed.
4. B2 preserves existing service more strongly.
5. B4b occupies a somewhat different speed–service-preservation operating point.
6. Structured manager-agnostic candidate information materially changes LLM
   supervisory behavior.
7. B4a without candidate information degrades toward an air-first policy.
8. The candidate table is operational decision support, not optimizer-answer
   leakage.

> 不写 "LLM outperforms optimizer"；也不写 "LLM matches optimizer"（尚无
> equivalence / non-inferiority test）。B2 与 B4b 的 aggregate 性能"comparable"，
> 服务-速度 operating point 不同（唯一显著差异集中在 E1_H_H_high：B4b 比 B2 快
> ~12 s 但多损伤 0.60 现有任务；Holm p = 0.0082，d = 1.04）。

## Candidate Representation（方法学发现）

```
Global State
→ Manager-Agnostic Candidate Generator
→ Candidate Set
→ Manager
→ Feasibility Checker
→ Executor
```

Candidate facts 可包含（当前实现 `orchestrator/candidate_info.py`，
`CANDIDATE_TABLE_VERSION = 2.0.0`）：

- resource
- mode（AIR / GROUND）
- estimated completion time（`eta_s` / `completion_time_s`）
- feasibility（`legal` / `reject_reason`）
- battery / endurance margin
- existing mission status（`preempted_mission_id` / `preempted_mission_priority`）
- service-disruption estimate（`service_loss_estimate`）
- infrastructure availability（`destination_available`）
- compatibility（`landing_compatible`）
- ground fallback（`ground` candidate）

但**不得包含**：

- B2 objective score
- B2 ranking
- recommended action
- best candidate
- optimizer answer

> candidate representation 是 supervisory interface 的一部分，**不是 B2 的一部分**。
> B1 / B2 / B4b 使用同一 factual candidate set（见
> `reports/experiment1_final/CANDIDATE_TABLE_FAIRNESS_AUDIT.md`）。

---

# 11. Experiment 2 — Air-Layer Failure Management

## Status: NEXT（未开始）

## 主目标（updated）

**Failure-induced feasible-set reconfiguration.** Experiment 1 已表明：在无
air-layer failure 的结构化 ground-disruption allocation 中，B2 与 B4b 的
aggregate performance 接近但 service–speed operating point 不同。Experiment 2
的 next question：

> **Does the B2–B4b comparable aggregate performance observed in Experiment 1
> persist when air-layer failures dynamically alter the feasible resource set?**

## Failure Families（沿用当前 operational abstraction）

### F1 — C2 Lost Link
航空器进入 local contingency。Manager 负责 mission reassignment、backup aircraft
dispatch、ground fallback、delay / cancel。

### F2 — GNSS / Localization Degradation
模拟 aircraft unavailable、selected zone degraded 或 restricted operation。

### F3 — UTM / U-space Outage
模拟 partial outage、complete outage、new mission acceptance stopped，以及
current critical missions selectively continued。

### F4 — Vertiport / Landing Site Failure

\[
LandingSite_i: Available\rightarrow Unavailable
\]

### F5 — Unknown / Non-Cooperative Aircraft
触发 temporary restricted area、mission rerouting、selective suspension。

### F6 — Flyaway / Uncontrolled Trajectory
触发 risk region、flight-resource withdrawal、task reassignment、ground fallback。

Local safety remains L0/L1 and outside LLM control。

## 重点指标（建议，非冻结）

- Mission Recovery Success
- Mission Recovery Time
- Failure-to-Replan Latency
- Failure-Aware Reassignment Accuracy
- Invalid Post-Failure Action Rate
- Unnecessary Existing-Service Disruption
- Ground Fallback Appropriateness
- Critical Mission Completion / Deadline Violation
- Candidate-Set Reduction / Resource Availability

六种 failure 的最终 scenario matrix 留待 Experiment 2 设计时冻结，本文档不提前
生成。

---

# 12. Experiment 3 — Compound Disruption Stress Test

## Status: PENDING

## 目标

**检验随着 compound-disruption complexity 增加，不同 supervisory policies 的性能
和行为如何分化。**

## Complexity Levels

### C1
单一事件，例如 Bridge Closure。

### C2

\[
Bridge\ Closure+C2\ Lost
\]

### C3

\[
Bridge\ Closure
+
Medical\ Request
+
GNSS\ Degradation
\]

### C4

\[
Road\ Disruption
+
Existing\ Air\ Workload
+
Emergency\ Request
+
C2\ Lost
+
Landing\ Site\ Failure
\]

## 核心假设

Rule-based manager 在低复杂度场景下可以表现良好。

随着：

\[
Context\ Complexity\uparrow
\]

LLM may exhibit contextual prioritization —— **这是一个 hypothesis，不是 assumed
outcome**，必须由实验验证。负面结果（LLM 无优势）同样有价值。

---

# 13. Experiment 4 — LLM Operational Limits

## Status: PENDING

该实验专门研究 LLM 是否真的适合作为 supervisory manager。

## 13.1 Experiment 4A — Information Update Frequency

测试：

\[
\Delta t_{manager}
=
\{10,30,60,120\}s
\]

以及：
- Event-only；
- 30s + Event；
- 60s + Event。

关注：
- stale decision；
- decision oscillation；
- number of LLM calls；
- redundant decision count；
- computational cost。

## 13.2 Experiment 4B — Inference Latency

人为控制：

\[
T_{delay}
=
\{1,5,10,20,30,60\}s
\]

Manager 决策基于 \(S_t\)，但执行于 \(S_{t+T_{delay}}\)。

目标是寻找：

\[
T_{critical}^{manager}
\]

即有效 supervisory decision horizon。

## 13.3 Experiment 4C — Global State Scale

逐渐增加：

\[
N_{air}=\{5,10,20,30,50\}
\]

同时增加：
- simultaneous missions；
- failure count；
- landing sites；
- active constraints。

关注：
- missed constraints；
- forgotten aircraft；
- duplicated assignments；
- infeasible action；
- inconsistent prioritization；
- decision quality degradation。

---

# 14. Prompt / Output Standardization

LLM 输入使用结构化 Global State JSON（`global_state_v1.schema.json`）；B4b 额外
获得 candidate-table section。

输出必须通过 `manager_action_v1.schema.json` 校验，JSON 单对象，无 markdown
fence，无 prose：

```json
{
  "type": "DISPATCH",
  "aircraft_id": "M-UAV-02",
  "mission_id": "M-CRITICAL-001",
  "target_site": "V1",
  "route": ["V2", "V1"],
  "ground_eta_s": null,
  "reason": "short justification"
}
```

避免完全自由文本。

---

# 15. Scenario Generation

建议采用：

\[
Base\ Scenario
\times
Ground\ Disruption
\times
Air\ Failure
\times
Fleet\ State
\times
Mission\ Priority
\]

生成 scenario matrix。

优先：
1. deterministic core scenarios；
2. controlled parameter sweeps；
3. random-seed replication（每 seed 必须 genuinely different）；
4. 后期再加入 stochastic stress testing。

---

# 16. Replication Strategy

每个 stochastic scenario 使用 genuinely different simulation seeds：

\[
N=20\sim30
\]

个独立种子（Experiment 1 已冻结 20 seeds）。

核心 benchmark 场景可采用：

\[
N=30\sim50
\]

独立种子。

> **Statistical independence rule:** same-prompt repeated calls（response
> caching / 同一状态反复调用）**不得**作为 independent statistical replicates。
> 它们只用于 stability / backend-cache characterization。independent unit =
> scenario × simulation seed，且要求每 seed 有 distinct operational state /
> state hash。

---

# 17. Statistical Analysis

建议报告：
- mean；
- median；
- standard deviation；
- confidence interval；
- effect size；
- paired comparisons when possible（paired across managers on identical
  scenario × seed）。

如进行多模型 / 多 baseline 比较，可使用：
- paired t-test；
- paired Wilcoxon；
- McNemar（binary outcomes）；
- multiple-comparison correction（Holm）。

Experiment 1 final 已按此执行（paired + Holm + effect size；见
`reports/experiment1_final/EXPERIMENT1_FINAL_RESULTS.md`）。

重点不是只报告：

> LLM 比 baseline 高 X%。

而是报告：

> 在哪些场景、复杂度和延迟条件下优势存在或消失。

---

# 18. Ablation Studies

Experiment 1 final 已完成 B4a vs B4b 的 candidate-table interface ablation（60
independent-seed runs）。后续（Experiment 2/3/4）可继续：

### A1 — No Trend Information
仅给 \(S_t\) vs. \(S_{t-k}+S_t+\Delta S\)。

### A2 — No Existing-Air Mission Context
测试如果 manager 看不到原有低空任务，会不会过度抢占资源。

### A3 — No Failure Information
验证 failure awareness 的作用。

### A4 — No Feasibility Checker
比较 manager 有无 checker 下的 infeasible actions（历史设计参考）。

### A5 — Periodic Only vs Event-Triggered
检验 event trigger 的实际价值。

---

# 19. Negative Results / Failure Criteria

以下结果都应视为有价值：

- LLM 不如优化算法：说明该问题可能不需要 LLM；
- LLM 仅在 compound disruptions 下有优势：这是重要边界；
- LLM latency 超过某阈值后失效：形成 operational boundary；
- LLM 在较大系统规模下遗漏约束：形成 scale boundary；
- Rule-based 在简单场景更好：完全合理。

论文不需要证明 LLM 在所有情况下都优于 baseline。

---

# 20. 实施顺序（Current Status）

> Agent starting from this document must **NOT** rebuild the Experiment-1
> platform from scratch unless a regression failure requires it.

| phase | 内容 | status |
|---|---|---|
| Phase 1 | SUMO + BlueSky platform + master clock | DONE / FROZEN |
| Phase 2 | Cross-layer mission interface + Global State + B1 | DONE / FROZEN |
| Phase 3 | LLM integration + semantic/feasibility checker | DONE / FROZEN |
| Experiment 0 | Co-simulation validation | DONE / FROZEN |
| Experiment 1 | Ground disruption + selective air support | **DONE / FROZEN**（960 + 60 = 1020 runs） |
| Experiment 2 | Air-layer failure management | **NEXT** |
| Experiment 3 | Compound disruption stress test | PENDING |
| Experiment 4 | LLM operational limits | PENDING |

---

# 21. 最小可行实验 MVP（历史记录）

> 以下 MVP 描述为历史设计参考，已完成；不再是待办。

### Ground
- one critical road closure

### Air
- 5–10 UAV（历史规模）；
- existing logistics missions；
- one medical UAV；
- 2 landing sites。

### New Event
- one urgent medical mission

### Air Failure
- C2 Lost Link

### Managers
- no coordination；
- rule-based；
- one LLM manager。

完整链路：

\[
Road\ Closure
\rightarrow
Emergency\ Mission
\rightarrow
Air\ Reassignment
\rightarrow
C2\ Lost
\rightarrow
Global\ Reconfiguration
\rightarrow
Ground/Air\ Fallback
\]

该闭环已在 Phase 2/3 完成并验证。

---

# 22. 论文核心贡献预期

最终论文不应宣称：

> LLM can control low-altitude aircraft.

而应围绕以下贡献：

1. 一个同步的 SUMO + BlueSky ground–low-altitude co-simulation framework；
2. 将低空交通建模为 Sparse Urban Resilience Layer，而不是成熟高密度空中交通；
3. **shared structured candidate representation**（manager-agnostic candidate
   table）作为 supervisory interface 的方法学贡献；
4. **comparative supervisory-policy evaluation**（B0/B1/B2/B4b + B4a ablation），
   而非单纯"提出一个 LLM manager"；
5. 系统测试 ground disruptions、air-layer failures 和 compound failures 的
   reconfiguration；
6. 给出 LLM supervisory management 的 operational boundary（update-frequency、
   inference-latency、global-state-scale）。

---

# 23. 推荐论文标题

首选：

**Global LLM-Supervised Reconfiguration of Heterogeneous Ground–Low-Altitude Mobility under Cross-Layer Disruptions**

更具叙事性的版本：

**When Roads Fail, Can the Sky Adapt? LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions**

---

# 24. 一句话总结

> **本研究不是让 LLM 实时控制无人机，而是研究当城市地面交通失效、有限低空资源
> 需要介入且低空系统本身也可能发生异常时，不同的 supervisory decision policies
> ——尤其是由一个掌握全局状态的 LLM supervisory manager 在共享结构化 candidate
> representation 的辅助下——能否在安全约束下完成合理的跨层资源重构。**
