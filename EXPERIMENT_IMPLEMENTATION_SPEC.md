> **2026-09-10状态：四实验完成，进入写作。** 本文保留设计与实现沿革；最终数据、统计口径与论文叙事统一见 `reports/PAPER_STORY_AND_WRITING_GUIDE.md`、`reports/README.md` 和 `outputs/paper_final/results.json`。

# EXPERIMENT_IMPLEMENTATION_SPEC
## Execution Specification for Ground–Low-Altitude Co-Simulation (as-built)

> 本文档定义"如何实现和执行实验"，并已同步为 **as-built execution spec**。
> 不重复 `Research Plan.md` 和 `ground_air_llm_experiment_plan.md` 中的研究背景、
> RQ、实验章节和贡献描述。
>
> **Agent 目标：** 依据本文档与 frozen project artifacts 维护可复现的
> SUMO–BlueSky 联动环境，不自行补充关键实验假设，不重建已冻结组件。

---

# Current Frozen State after Experiment 1 Finalization

> This section reflects the **current validated implementation**. See
> `reports/experiment1_final/` and the frozen configs/schemas for evidence.

- **canonical testbed**: `S0_3p2km_v1`
- **study area**: 3.2 km × 3.2 km, center = **31.30377 N, 120.59981 E**
- **exchange CRS**: EPSG:4326
- **current canonical base fleet**（4 aircraft，`config/scenario_config.yaml` +
  `config/resource_compatibility.yaml`）:
  - `L-UAV-01` — logistics_uav
  - `EVTOL-01` — passenger_evtol
  - `M-UAV-01` — medical_uav
  - `M-UAV-02` — medical_uav
- **SUMO + BlueSky + Python Orchestrator**: validated and frozen
- **master simulation step**: 1 s
- **Global State**: frozen schema `schemas/global_state_v1.schema.json`
  (`schema_version = 1.0.0`)
- **Action Contract**: LLM-facing contract **v2**（prompt `prompts/manager_v2.txt`，
  12 action types incl. REASSIGN preemption）；authoritative structural schema =
  `schemas/manager_action_v1.schema.json`（title `ManagerAction v1`）
- **LLM prompt**: `manager_v2` frozen
- **B2 objective**: frozen before final primary rerun
  (`config/experiment1_b2_weights.yaml`)
- **Candidate Generator**: manager-agnostic
- **Candidate Table**: no B2 objective score / ranking / recommendation leakage
- **Primary managers**: B0, B1, B2, B4b
- **LLM variants**: B4a = LLM-State（no candidate table）; B4b = LLM-Candidate
  （candidate table enabled）— B4b is the primary LLM method
- **Experiment 1 final**: **960** primary runs + **60** B4a ablation runs =
  **1020** total; **0 excluded**; EF-T1…EF-T20 = **20/20 PASS**
- **old pre-fix / v2 datasets**: superseded for primary statistical analysis
- **next stage**: Experiment 2 — Air-Layer Failure Management

> **Historical / default design references (NOT current):** **5 km × 5 km** and
> **12-aircraft S0** are historical/default design references and are **NOT** the
> current frozen base configuration. Current base = 3.2 km × 3.2 km / 4 aircraft.

---

# Source-of-Truth Hierarchy

When this Markdown conflicts with frozen project artifacts:

1. frozen configs / schemas
2. final Experiment-1 reports (`reports/experiment1_final/`)
3. SHA-256 hash manifest (`outputs/file_hashes_final.json`)
4. current code implementation
5. these Markdown documents

Any future change to the frozen protocol requires: (1) CHANGELOG entry, (2) new
version identifier, (3) impact-on-comparability statement, (4) no silent overwrite
of the historical protocol.

---

# 1. Implementation Principles

## 1.1 Simulator roles

- **SUMO**：负责地面交通、道路可达性、道路失效、ground fallback。
- **BlueSky**：负责低空飞行器、低空任务、起降点、航线与空中资源状态。
- **Python Orchestrator / Global State Hub**：唯一的主控层。
- **Manager**（B0/B1/B2/B4a/B4b）：只接收 Global State Hub 输出的抽象状态
  （B4b 额外接收 candidate table），只产生 high-level management actions。
- **Candidate Generator**：manager-agnostic，先于 manager 运行，为所有 manager
  生成同一 factual candidate set。
- **Semantic Validator + Safety / Feasibility Checker**：manager 输出执行前的
  校验与硬约束过滤层。

禁止 SUMO 和 BlueSky 彼此直接耦合业务逻辑。所有跨层通信必须经过 Global State Hub。

---

# 2. Canonical Study Area

## 2.1 Geographic reference

跨模拟器统一采用：

```text
CRS_EXCHANGE = EPSG:4326
Coordinate order = latitude, longitude
```

所有跨层对象必须以 WGS84 经纬度作为唯一地理主键。

SUMO 内部允许继续使用 `(x, y)` 米制投影坐标，但所有与 BlueSky 或 Global State
Hub 交换的数据都必须转换为 `(lat, lon)`。

## 2.2 Default canonical area（current frozen）

> **Historical/default design reference:** 5 km × 5 km（early design default）。
> **Current frozen canonical testbed:** `S0_3p2km_v1`，3.2 km × 3.2 km。

```yaml
scenario_version: S0_3p2km_v1
study_area:
  name: canonical_suzhou_testbed
  center:
    lat: 31.30377
    lon: 120.59981
  width_km: 3.2
  height_km: 3.2
  crs_exchange: EPSG:4326
```

当前正式 Exp 1 / Exp 2 默认必须使用 `S0_3p2km_v1`。只有 scale / geography
sensitivity experiment 才允许另建区域。

## 2.3 Area bounding box

Agent 根据中心点和 3.2 km × 3.2 km 范围计算 bbox（当前 frozen bbox 见
`config/scenario_config.yaml`）：

```yaml
bbox:
  north: <computed>
  south: <computed>
  east: <computed>
  west: <computed>
```

不得手工在 SUMO 和 BlueSky 中分别选择区域。

---

# 3. Shared Geographic Registry

当前实现：

```text
config/scenario_config.yaml
```

包含设施（frozen）：`H1`（hospital）、`D1`（logistics_depot）、`V1`
（hospital_landing_site）、`V2`（logistics_hub_landing_site）、`V3`
（backup_landing_site）、`B1`/`B2`/`B3`（candidate disruption links，互斥）。

要求：

1. `H1` 与 `V1` 应相邻或位于合理步行/短驳距离；
2. `D1` 与 `V2` 作为主要物流源；
3. `V3` 作为备用降落点；
4. `B1` 位于连接 H1 与主要城市区域的重要 SUMO corridor 上；
5. 同一设施不得在 SUMO 和 BlueSky 各维护一份坐标。

---

# 4. SUMO Network Construction

## 4.1 Network source

默认优先：

```text
OpenStreetMap → SUMO network
```

要求：

- 使用与 `scenario_config.yaml` 相同的 bbox；
- 保存原始 OSM 文件；
- 保存 SUMO `.net.xml`；
- 保留 SUMO `<location>` geo-reference 信息。

推荐目录：

```text
sim/sumo/
  area.osm.xml
  network.net.xml
  routes.rou.xml
  additional.add.xml
```

## 4.2 Facility mapping

每个共享设施都必须映射到 SUMO。当前 frozen mapping 在
`config/scenario_config.yaml` 的 `sumo_mapping` 块。

---

# 5. BlueSky Scene Construction

## 5.1 BlueSky scene scope

BlueSky 不需要道路可视化。

BlueSky 中只维护：

- UAV / eVTOL；
- landing sites；
- air routes；
- restricted areas；
- failure zones；
- shared facilities 的 WGS84 点位。

## 5.2 BlueSky shared landmarks

Agent 必须在 BlueSky 中注册 shared landmarks（`H1/V1/V2/V3/D1/B1`）。若 GUI
不便于显示标签，至少必须在内部 registry 中存在。

---

# 6. Geographic Alignment Validation

必须建立：

```text
tests/test_geographic_alignment.py
```

对每个共享 landmark：
1. 从 `scenario_config.yaml` 读取 WGS84；
2. 转换为 SUMO `(x, y)`；
3. 再通过 SUMO geo-conversion 转回 `(lat, lon)`；
4. 与原始 WGS84 计算 Haversine distance。

验收条件：

```text
median alignment error < 5 m
max alignment error < 15 m
```

（当前 frozen：CRS round-trip 0.0000 m；snapping H1 42.85 m / D1 58.01 m
(WARNING，carried over) / V3 27.48 m / V1/V2/B1 0 m。）

---

# 7. Canonical Base Scenario S0

```yaml
scenario_id: S0
scenario_version: S0_3p2km_v1
simulation_duration_s: 1800
simulation_step_s: 1
```

## 7.1 Ground configuration

包含：

- 正常背景地面交通；
- H1 医院；
- D1 物流中心；
- B1/B2/B3 候选 disruption links；
- 从城市主要区域到 H1 的正常地面路径；
- 绕行路径（B1 关闭时 2 条 detour，181.76 s / 191.21 s）；
- ground emergency fallback vehicle 类型。

## 7.2 Air fleet（current frozen = 4 aircraft）

> **Historical initial design:** 12 aircraft（8 logistics UAV + 2 medical UAV +
> 1 inspection UAV + 1 passenger eVTOL）。
> **Current frozen base fleet:** 4 aircraft（from `config/scenario_config.yaml`
> `air_fleet` + `orchestrator/fleet.py` + `config/resource_compatibility.yaml`）：

```text
L-UAV-01  logistics_uav    busy（background logistics V2↔V3）
EVTOL-01  passenger_evtol  busy（background passenger V2↔V1）
M-UAV-01  medical_uav      standby at V1
M-UAV-02  medical_uav      standby at V2
```

> **4-aircraft fleet is the frozen base configuration** for corrected
> Experiment 1 and the initial Experiment 2. Future scale study may expand the
> fleet independently（Experiment 4C），without changing the frozen base fleet.

## 7.3 Initial mission occupancy

目标：天空不是空闲 emergency reserve。

frozen base：2 background services busy + 2 medical standby available（约
50 % occupied）。

---

# 8. Aircraft Registry Schema

当前实现：`state/aircraft_registry.json`（或等价 registry 对象）。

单个对象最少字段：

```json
{
  "aircraft_id": "L-UAV-01",
  "type": "logistics_uav",
  "status": "BUSY",
  "mission_id": "M-L-001",
  "priority": "NORMAL",
  "lat": 31.30377,
  "lon": 120.59981,
  "battery_pct": 82,
  "remaining_endurance_s": 1200,
  "reassignable": true,
  "landing_site_compatibility": ["V2", "V3"],
  "c2_status": "NORMAL",
  "gnss_status": "NORMAL",
  "utm_status": "NORMAL",
  "contingency_mode": "NONE"
}
```

（landing compatibility 具体值以 `config/resource_compatibility.yaml` 为准。）

---

# 9. Air Resource State Machine

允许状态：

```text
AVAILABLE
BUSY
RESERVED
DEGRADED
CONTINGENCY
UNAVAILABLE
RECOVERED
```

允许的核心转换：

```text
AVAILABLE → BUSY
BUSY → AVAILABLE
BUSY → DEGRADED
BUSY → CONTINGENCY
DEGRADED → CONTINGENCY
CONTINGENCY → UNAVAILABLE
CONTINGENCY → RECOVERED
RECOVERED → AVAILABLE
```

禁止通过简单 `delete aircraft` 表示一般 operational failure。只有明确的
terminal-loss scenario 才允许从 registry 中永久移除。

---

# 10. Mission Registry and State Machine

当前实现：`state/mission_registry.json`（或等价 registry 对象）。

单个任务最少字段：

```json
{
  "mission_id": "M-CRITICAL-001",
  "type": "medical_blood",
  "priority": "CRITICAL",
  "origin": "V2",
  "destination": "V1",
  "deadline_s": 480,
  "assigned_resource": null,
  "mode": null,
  "status": "WAITING",
  "ground_fallback": true,
  "delay_cost": 10.0,
  "cancellation_cost": 100.0
}
```

允许状态：

```text
WAITING
ASSIGNED
EN_ROUTE
INTERRUPTED
NEEDS_REPLAN
REASSIGNED
COMPLETED
CANCELLED
FAILED
```

典型转换：

```text
WAITING → ASSIGNED
ASSIGNED → EN_ROUTE
EN_ROUTE → COMPLETED
EN_ROUTE → INTERRUPTED
INTERRUPTED → NEEDS_REPLAN
NEEDS_REPLAN → REASSIGNED
REASSIGNED → EN_ROUTE
NEEDS_REPLAN → CANCELLED
NEEDS_REPLAN → FAILED
```

---

# 11. Priority Policy

默认 mission priority：

```text
CRITICAL
HIGH
NORMAL
LOW
```

frozen canonical ranking：

```text
Blood / organ / life-critical medical
    >
Emergency medicine / emergency equipment
    >
Medical routine / essential passenger
    >
Passenger
    >
Normal logistics
    >
Low-priority logistics / inspection
```

该排序只用于 baseline / checker / scenario definition / consistency validation，
不是 LLM 的最终决策规则。

---

# 12. Ground Disruption Injection Semantics

frozen 实现用 B1/B2/B3 三类候选 disruption link（互斥）。

## 12.1 GD1 — Critical Link Closure

```text
at event time:
SUMO edge(s) corresponding to B1 → blocked / capacity = 0
```

默认：

```yaml
event:
  id: GD1
  start_s: 300      # b1_close_t_s (frozen)
  duration_s: ...
```

Agent 必须记录 before/after ETA to H1、affected OD/missions、rerouting response。

## 12.2 GD2 — Capacity Degradation

```text
selected SUMO edge capacity → 30% of nominal
```

不得实现成完全关闭。

## 12.3 GD3 — Ground Accessibility Trigger

derived event：

```text
if ETA_to_H1 > threshold
→ accessibility_degraded = true
```

默认 threshold：

```text
ETA_now >= 2.0 × ETA_baseline
```

---

# 13. Air Failure Injection Semantics

六类 failure 按 operational abstraction 实现。第一阶段不要求真实通信/GNSS/飞控
物理模型。local safety 始终 L0/L1，不由 LLM 控制。

## 13.1 F1 — C2 Lost Link
```text
aircraft.c2_status = LOST
aircraft.status = CONTINGENCY
aircraft.reassignable = false
current_mission.status = INTERRUPTED
local_contingency = predefined safe action（RETURN → V3）
```

## 13.2 F2 — GNSS / Localization Degradation
```text
GNSS_DEGRADED_ZONE → aircraft.gnss_status = DEGRADED
                    → status = DEGRADED
                    → eligible_for_new_mission = false
```

## 13.3 F3 — UTM / U-space Outage
```text
utm_status = DEGRADED | OUTAGE
DEGRADED: new non-critical air missions prohibited; critical reassignment after feasibility check
OUTAGE:   new air missions prohibited; non-critical → safe termination; critical per predefined safe-policy
```

## 13.4 F4 — Vertiport / Landing Site Failure
```text
Vx.available = false → destination/planned_contingency == Vx → NEEDS_REPLAN
```

## 13.5 F5 — Unknown / Non-Cooperative Aircraft Intrusion
```text
UNKN-01 + temporary_risk_zone
aircraft entering zone cannot receive new assignment; crossing missions → NEEDS_REPLAN/local reroute
```

## 13.6 F6 — Flyaway / Uncontrolled Trajectory
```text
status = CONTINGENCY; commandable = false; trajectory_mode = UNCONTROLLED_PREDEFINED
risk_zone = buffer around uncontrolled trajectory
other missions intersect → NEEDS_REPLAN
```

---

# 14. Global State Schema

每次触发 manager 时，Global State Hub 输出符合
`schemas/global_state_v1.schema.json`（`schema_version = 1.0.0`）的 snapshot。
frozen 顶层结构：

```json
{
  "schema_version": "1.0.0",
  "simulation_time": 620,
  "scenario_id": "S0",
  "scenario_version": "S0_3p2km_v1",
  "ground": {},
  "air": [],
  "infrastructure": {},
  "missions": {},
  "events": [],
  "trend": {}
}
```

要求：

- Agent 不得直接把 raw SUMO / BlueSky logs 喂给 manager；
- 输入必须经过 deterministic abstraction；
- 同一 scenario 和 seed 下，manager 输入内容必须可 replay；
- 每 seed 必须产生 distinct state（seed-independence audit）。

---

# 15. Manager Action Contract（v2）

权威 structural schema 为 `schemas/manager_action_v1.schema.json`（title
`ManagerAction v1`）。LLM-facing contract **v2** 语义（含 REASSIGN preemption）
见 `prompts/manager_v2.txt`。**Action Contract v2 is authoritative.**

允许 action type（12 个，以当前 schema 为准）：

```text
DISPATCH
REASSIGN
REROUTE
DELAY
CANCEL
RESERVE
DIVERT
RETURN
LAND
GROUND_FALLBACK
NO_ACTION
ESCALATE
```

最小 JSON 结构：

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

REASSIGN preemption precondition（v2）：busy aircraft 的当前 mission priority
严格低于新 mission priority，且 aircraft 标记 `reassignable: true`。

---

# 15.5 Normalize-Then-Validate（执行协议）

LLM raw output 的完整链路：

```text
LLM raw output
→ normalization
→ schema validation
→ semantic validation
→ feasibility checker
→ executor
```

**Normalization 只允许**：

- enum case normalization
- known alias normalization
- harmless formatting normalization

**严格禁止 normalization**：

- change aircraft
- change target site
- replace action type based on environment
- choose fallback
- repair an infeasible strategic decision

必须日志保存四段：`raw_action`、`normalized_action`、`validation_result`、
`executed_action`（当前实现写入 `action_pipeline.jsonl`）。被 checker 拒绝的
proposal 不得静默转换成另一个 valid action，也不得计入 issued action。

---

# 16. Manager-Agnostic Candidate Generator Contract

```
Global State
→ Candidate Generator（orchestrator/candidate_info.py）
→ Candidate Set（gs["candidates"]）
→ Manager
```

- **Candidate Generator 不依赖 manager type**，是 Global State 的纯函数。
- 可计算 deterministic operational facts：
  - feasibility（`legal` / `reject_reason`）
  - estimated completion time（`eta_s` / `completion_time_s`）
  - mode（`AIR` / `GROUND`）
  - resource（`resource_id`）
  - infrastructure status（`destination_available`）
  - battery/endurance（`battery_pct` / `endurance_margin_s`）
  - compatibility（`landing_compatible`）
  - interruption / service-loss estimate（`service_loss_estimate`）
  - ground fallback（`ground` candidate）
- **禁止**：B2 weighted objective score、B2 rank、recommended action、selected
  action、optimizer output leakage。
- **B1 / B2 / B4b 使用同一 factual candidate set**（B4a 不渲染 candidate table）。
- `CANDIDATE_TABLE_VERSION = 2.0.0`。详见
  `reports/experiment1_final/CANDIDATE_TABLE_FAIRNESS_AUDIT.md`。

---

# 16.5. Global State → Manager Pipeline（as-built）

```text
Simulator states（SUMO/BlueSky）
→ Global State abstraction（global_state_v1）
→ Candidate Generator（manager-agnostic）
→ Manager Input
   ├─ B4a: Candidate Table DISABLED
   └─ B4b: Candidate Table ENABLED（rendered into prompt）
→ Manager（B0/B1/B2/B4a/B4b）
→ normalize
→ schema validate
→ semantic validate
→ Feasibility Checker
→ Executor
→ SUMO/BlueSky
```

---

# 17. Action → Simulator Mapping

## 17.1 DISPATCH
```text
DISPATCH(aircraft_id, mission_id)  — assign AVAILABLE aircraft to WAITING mission
```

## 17.2 REASSIGN
```text
REASSIGN(aircraft_id, mission_id)
1. detach aircraft from previous interruptible/lower-priority mission
2. update previous mission status
3. assign new mission
4. compute air route
5. send route to BlueSky
6. update aircraft status = BUSY
7. update mission status = ASSIGNED/EN_ROUTE
```

## 17.3 GROUND_FALLBACK
```text
GROUND_FALLBACK(mission_id)
1. create/activate predefined SUMO ground resource
2. assign origin/destination
3. calculate SUMO route
4. update mission.mode = GROUND
5. track ETA and completion
```

## 17.4 DIVERT / CANCEL / RESERVE / RETURN / LAND
按 Action Contract v2 语义执行（feasibility check → executor → simulator）。

---

# 18. Master Clock and Synchronization Protocol

Python Orchestrator 是唯一 master clock。固定 `simulation_step = 1 s`。

每一秒执行顺序（frozen）：

```text
1. apply scheduled events at time t
2. apply queued manager actions scheduled for t
3. step SUMO from t → t+1
4. step BlueSky from t → t+1
5. collect simulator states
6. convert all cross-layer positions to WGS84
7. update mission/resource registries
8. detect new events
9. evaluate manager trigger
10. if trigger:
       build global state
       run candidate generator
       request manager decision
       normalize → schema → semantic → feasibility
       queue valid actions
11. compute online metrics
12. write logs
13. advance t
```

不得交换顺序，除非后续实验明确研究同步机制。

---

# 19. Manager Timing Modes

## 19.1 Mode A — Frozen Simulation Decision（主实验默认）
```text
event detected → capture S_t → obtain manager output → apply at t
```
用于 reproducibility / model comparison / deterministic benchmark。

## 19.2 Mode B — Delayed Execution（latency experiment）
```text
decision based on S_t; apply at S_(t + delay)
```
delay 由实验配置控制。

---

# 20. Event Trigger Policy

立即触发 manager：new CRITICAL mission、major ground disruption、C2 Lost、GNSS
degraded zone、UTM degradation/outage、landing site failure、unknown aircraft、
flyaway、critical resource loss、mission infeasible。

periodic trigger 由实验配置决定（`llm_update_interval_s`）。避免同一 event 每秒
重复触发；每个 event 需 `event_id / first_seen / acknowledged / resolved`。

---

# 21. Canonical MVP Timeline（历史记录）

> 以下为历史 MVP 时间线（Phase 2/3 已实现并验证）。frozen critical mission 在
> t=300 释放（`critical_mission_t_s: 300`），C2 Lost 在 t=360
> （`c2_lost_t_s: 360`）。

```text
t = 0 s      Simulation starts
t = 300 s    GD1: B1 closes; critical mission M-CRITICAL-001 released (V2→V1)
t = 300 s    manager event trigger (compare B0/B1/B2/B4b)
t = 360 s    F1: C2 Lost on assigned aircraft → local contingency RETURN→V3
t = 900 s    Phase-2/3 duration ends (Experiment-1 final runs 900 s)
```

---

# 22. Baseline B1 — Rule-Based Manager（frozen）

Rule baseline definition is frozen from final Experiment 1. B1 决策顺序：

```text
1. process CRITICAL before HIGH before NORMAL before LOW
2. only choose AVAILABLE or explicitly reassignable resources
3. never interrupt a higher-priority mission for a lower-priority mission
4. require feasibility checker pass
5. choose minimum estimated mission completion time
6. if tie: choose highest battery margin
7. if no feasible air resource: choose ground fallback if feasible
8. if neither feasible: delay or cancel according to mission priority
```

frozen implementation 前置：

- candidate generation before ranking（`gs["candidates"]`）；
- unavailable resource filtered；
- unavailable infrastructure filtered（destination availability）；
- battery / endurance margin filtered；
- compatibility filtered（`landing_compatible`）；
- non-commandable resource filtered；
- priority constraints（no equal/higher-priority preemption）；
- feasibility checker pass。

---

# 23. Baseline B2 — Heuristic / Optimization Manager（FROZEN）

**B2 objective and weights are FROZEN.** 权威来源：

- `config/experiment1_b2_weights.yaml`
- `reports/experiment1_final/B2_OBJECTIVE_FREEZE.md`

```text
J = w1 * completion_time_s
  + w_deadline * deadline_violation_s
  + w2[preempted_priority]          (REASSIGN/preemption only)
  + w3 * is_reassignment
  + w_risk * risk_score
```

frozen weights：`w1 = 1.0`，`w_deadline = 10.0`，
`w2 = {LOW: 20, NORMAL: 40, HIGH: 80, CRITICAL: 100000}`，`w3 = 30.0`，
`w_risk = 10.0`，`risk_thresholds_s = [120, 60]`。

**不得**：

- 根据 B4b 结果调权重；
- 在 Experiment 2 中静默改目标函数。

若 Experiment 2 因 failure risk 需要新增 failure-specific hard constraint，
必须记录为 **protocol extension**，而不是 secretly retune weights。B2 从 shared
candidate-table fields 计算 objective（不 re-derive candidate facts privately）。

---

# 23.5. LLM Manager Variants

| variant | name | input |
|---|---|---|
| **B4a** | LLM-State | Global State + Action Contract v2（**no** candidate table） |
| **B4b** | LLM-Candidate | same Global State + same Action Contract v2 + **same manager-agnostic Candidate Set** |

两者使用 frozen prompt `manager_v2`（`prompts/manager_v2.txt`）。**B4b 是当前
primary LLM method**；B4a 是 interface ablation。

---

# 23.6. LLM Configuration（frozen）

| item | value |
|---|---|
| model | `corp-ai/openai/deepseek-v4-pro` |
| endpoint | local compatible API endpoint（OpenAI-compatible；不记录内部凭证） |
| temperature | `0.0` |
| response format | `json_object`（`json_mode: true`） |
| max_tokens | `8192` |
| prompt version | `manager_v2`（frozen） |

凭证/token 不写入任何文档。

---

# 24. Scenario Expansion Matrix（historical reference）

> 以下为历史扩展矩阵；Experiment 1 final 已冻结为 12 scenario classes × 20
> seeds（见 `config/experiment1_final_matrix.yaml`）。Experiment 2 matrix 待设计。

```yaml
scenario_dimensions:
  ground_disruption: [none, link_closure, capacity_degradation]
  air_failure: [none, c2_lost, gnss_degraded, utm_degraded,
                landing_site_failure, unknown_aircraft, flyaway]
  existing_air_workload: [0.25, 0.50, 0.75]
  emergency_priority: [high, critical]
  aircraft_count: [5, 10, 20, 30, 50]
```

---

# 25. Logging Contract

每次 run 独立目录（Experiment-1 final）：

```text
runs/experiment1_final/<scenario>/seed<seed>/<B0|B1|B2|B4b|B4a>/
```

必须输出（final artifact contract）：

```text
run_config.yaml
events.csv
ground_state.csv
air_state.csv
missions.csv
candidate_info.jsonl
manager_inputs.jsonl
manager_outputs.jsonl
feasibility_checks.jsonl
semantic_checks.jsonl
action_pipeline.jsonl
actions.csv
violations.csv
metrics.json
runtime.json
run_meta.json
```

`run_config.yaml` 记录：scenario_id、seed、manager、llm_model、prompt_version、
temperature、simulation_step_s、llm_update_interval_s、failure_config、
baseline_weight_version、（无 git → SHA-256 hash manifest）。

---

# 26. Required Online Metrics

每个 step 或 event 后更新：

```text
critical mission completion status / ETA
normal mission delay
cancelled mission count
reassignment count
ground fallback count
active / available air resources
feasibility violation count
manager call count
manager action count
```

---

# 27. Required End-of-Run Metrics

冻结定义见 `reports/experiment1_final/EXPERIMENT1_FINAL_METRIC_DEFINITIONS.md`
（Critical Mission Completion Time、Deadline Violation、Existing Service Damage、
Air Intervention Rate、Unnecessary Air Intervention Rate（θ=60 s）、Time Saving
vs B0、Reassignment Count、Interrupted Existing Mission Count、Ground Fallback
Rate、Disruption Efficiency）。

---

# 28. Deterministic Replay & Statistical Independence

对每个 scenario：

```text
same scenario_id + same seed + same manager input → replay
```

随机过程必须受统一 seed 控制（Python random / NumPy / SUMO / BlueSky /
scenario generator / seed realization）。

真实 manager output 应保存。replay 允许 `use cached manager output` 用于：

- deterministic replay
- debugging
- simulator isolation

**硬规则**：

- **Cached identical prompts MUST NOT be counted as independent statistical
  replicates.**
- Primary statistical unit = **scenario × genuinely different simulation seed**。
- 每个独立单元必须有：distinct operational state、distinct prompt/state hash、
  seed-independence audit。
- same-prompt × N repeated calls 只用于 stability / backend-cache
  characterization，不能作为 n=N 性能统计。

---

# 29. Acceptance Tests Before Experiment 1（platform regression）

> 以下 T1–T9 是 **platform regression tests**，不是"尚未完成"的 checklist。
> 当前状态：**previously passed / frozen**。Experiment 2 开始前只需 regression
> rerun，不得重新设计这些测试。

## T1 — Geographic alignment
```text
PASS if: median landmark alignment error < 5 m AND max < 15 m
```
（frozen：CRS round-trip 0.0000 m；D1 snap 58.01 m WARNING carried over。）

## T2 — Clock synchronization
```text
SUMO sim time == BlueSky sim time == Orchestrator time（0 step 误差）
```

## T3 — Mission lifecycle
```text
WAITING → ASSIGNED → EN_ROUTE → COMPLETED
```

## T4 — Reassignment lifecycle
```text
EN_ROUTE → INTERRUPTED → NEEDS_REPLAN → REASSIGNED → EN_ROUTE → COMPLETED
```

## T5 — Ground fallback
```text
NEEDS_REPLAN → GROUND_FALLBACK → COMPLETED
```

## T6 — C2 contingency
```text
C2 Lost 后 aircraft 立即 non-commandable；local contingency 不等 LLM；
LLM 只能 reconfigure mission/resources
```

## T7 — Landing-site failure
```text
no new mission may be assigned to failed site
```

## T8 — Invalid manager action rejection
```text
insufficient battery → checker 拒绝并记录
```

## T9 — Deterministic replay
```text
same seed + same scenario → identical event/action timeline（cached manager output）
```

> Experiment 1 final 另有 EF-T1…EF-T20（20/20 PASS，见
> `reports/experiment1_final/EXPERIMENT1_FINAL_ACCEPTANCE_TESTS.md`），是最终
> 数据集的 acceptance，不是 platform regression。

---

# 30. Agent Execution Order

## Historical Build Order

```text
Step 1   Create project directory structure.
Step 2   Build scenario_config.yaml + shared geographic registry.
Step 3   Download/build SUMO OSM network for canonical area.
Step 4   Create BlueSky canonical air scene.
Step 5   Coordinate conversion + alignment tests.
Step 6   Orchestrator master clock.
Step 7   Aircraft + mission registries/state machines.
Step 8   Shared Global State schema.
Step 9   B1 rule manager.
Step 10  Feasibility checker.
Step 11  Experiment 0 / MVP without LLM.
Step 12  Pass T1–T9 acceptance tests.
Step 13  Integrate LLM manager.
Step 14  Freeze prompt version + action schema.
Step 15  Implement B2 optimization manager.
Step 16  Run canonical MVP with B0–B4.
Step 17  Add remaining failure injectors.
Step 18  Run single-failure experiment matrix.
Step 19  Run compound disruption matrix.
Step 20  Run frequency / latency / scale experiments.
```

## Current Execution Status

```text
Platform validation        DONE / FROZEN
Cross-layer interface      DONE / FROZEN
Rule manager (B1)          DONE / FROZEN
LLM integration            DONE / FROZEN
Candidate Generator        DONE / FROZEN
Experiment 1               DONE / FROZEN（960 + 60 = 1020 runs, 0 excluded）
Experiment 2               NEXT
Experiment 3               PENDING
Experiment 4               PENDING
```

> **Agent starting from this document must NOT rebuild Steps 1–16 unless a
> regression failure requires it.**

---

# 31. Recommended Project Structure

```text
project/
├─ config/
│  ├─ scenario_config.yaml
│  ├─ resource_compatibility.yaml
│  ├─ experiment1_b2_weights.yaml
│  ├─ experiment1_final_matrix.yaml
│  ├─ experiment1_final_seeds.yaml
│  └─ phase3_config.yaml
├─ sim/
│  ├─ sumo/
│  └─ bluesky/
├─ orchestrator/
│  ├─ candidate_info.py
│  ├─ phase2_orchestrator.py
│  ├─ phase3_orchestrator.py
│  ├─ experiment1_runner.py
│  └─ ...
├─ state/
├─ managers/
│  ├─ no_cross_layer.py
│  ├─ rule_based.py
│  ├─ optimization.py
│  └─ llm_manager.py
├─ safety/
│  ├─ semantic_validator.py
│  └─ feasibility_checker.py
├─ failures/
├─ schemas/
│  ├─ global_state_v1.schema.json
│  └─ manager_action_v1.schema.json
├─ prompts/
│  └─ manager_v2.txt
├─ tests/
├─ runs/experiment1_final/
└─ analysis/
```

---

# 32. Agent Freedom and Non-Negotiable Constraints

## Agent may choose

- exact SUMO routing helper implementation；
- BlueSky Python/plugin integration method；
- JSON validation library；
- internal class design；
- plotting/reporting library；
- logging implementation；
- minor parameter values not explicitly fixed here。

## Agent must not change without recording

- study-area size（当前 frozen：3.2 × 3.2 km）；
- shared WGS84 reference（EPSG:4326）；
- master-clock ownership；
- 1 s base simulation step；
- canonical S0 fleet composition（当前 frozen：4 aircraft）；
- mission/resource state machines；
- failure operational semantics；
- manager 不控制 L0/L1 safety；
- action schema；
- B2 objective weights（frozen）；
- candidate generator leakage contract；
- statistical independence rule；
- acceptance criteria；
- required logs。

如必须修改：1. CHANGELOG entry；2. 说明 reason；3. 说明 impact on experiment
comparability；4. 不 silent modify。

---

# 33. MVP Completion Definition（历史，已完成）

> 以下为历史 MVP 完成定义，已满足。当前不再作为待办。

```text
[ ] SUMO and BlueSky run under one master clock
[ ] same WGS84 scene validated
[ ] frozen canonical fleet initialized（当前 = 4 aircraft，来自 scenario_config）
[ ] existing air missions are active
[ ] B1 ground disruption injected（frozen: t=300 s）
[ ] critical mission released（frozen: t=300 s）
[ ] manager assigns air or ground support
[ ] C2 Lost injected（frozen: t=360 s）
[ ] local contingency executes without manager
[ ] interrupted mission is reconfigured
[ ] all actions pass through feasibility checker
[ ] mission completes / fails with explicit terminal status
[ ] complete logs are written
[ ] deterministic replay passes
```

---

# 34. Experiment 1 Status（FROZEN）

- **Experiment 1: COMPLETED / FROZEN**
- Primary: **960 runs**（12 scenarios × 20 seeds × 4 managers）
- Ablation: **60 runs**（B4a，6 scenarios × 10 seeds）
- Total: **1020**；**0 excluded**；**EF-T1…EF-T20 = 20/20 PASS**
- 所有旧 Experiment-1 pre-fix dataset：**`superseded_for_primary_analysis = true`**
- **Agent 不得重新运行 Experiment 1，除非用户明确要求。**

---

# 35. Final Implementation Principle

```text
Manager decides system-level strategy.
Traditional simulation/control enforces physical and safety feasibility.
SUMO and BlueSky share geography and time, not internal control logic.
Candidate Generator provides manager-agnostic decision support,
never optimizer-answer leakage.
```

如果 Agent 的实现逐渐变成 "LLM directly flies UAV" 或 "SUMO and BlueSky are two
unrelated demos"，必须立即停止并回到本规格。
