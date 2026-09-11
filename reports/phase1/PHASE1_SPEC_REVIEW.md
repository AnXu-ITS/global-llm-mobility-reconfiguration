# PHASE 1 SPEC REVIEW

> 项目：Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions
> 阶段：Phase 0 / Phase 1（研究规范审查 + 试验场地构建 + SUMO–BlueSky 协同仿真 smoke test）
> 审查对象：
> 1. `Research Plan.md`（888 行）
> 2. `ground_air_llm_experiment_plan.md`（934 行）
> 3. `EXPERIMENT_IMPLEMENTATION_SPEC.md`（1745 行）

---

## 0. 文档优先级与执行规则

按本阶段用户指令确立的优先级：

1. **执行层最高优先级** = `EXPERIMENT_IMPLEMENTATION_SPEC.md`（定义“如何实现和执行”）。
2. 其次 = 本阶段用户逐条指令（在 spec 未覆盖或留白的细节上，用户指令为直接执行依据）。
3. 再其次 = `ground_air_llm_experiment_plan.md`（实验矩阵/RQ 细化）。
4. 最后 = `Research Plan.md`（研究边界与定位，**不可擅自修改**）。

铁律：
- 不改研究边界；不改 research question 语义。
- 不把项目变成 UAV path planning / 飞控 / 高密度空中拥堵研究。
- 不因实现方便删除 shared geography 或 master clock。
- 任何对 spec 细节的偏离必须进入 CHANGELOG 并在最终报告说明影响。

---

## 1. 研究真正要回答的问题

核心一句话（`Research Plan.md` §4 / §17 / §19）：

> **当地面交通发生扰动时，一个掌握全局状态的 LLM Supervisory Manager 能否在不破坏原有低空交通运行的前提下，合理重构空地交通资源；并在低空系统自身发生故障时继续维持整体系统韧性？**

英文表述（§4）：
> Can an LLM globally reconfigure a sparse, heterogeneous and failure-prone low-altitude mobility system to support disrupted ground transportation while preserving existing aerial operations?

研究把低空交通建模为**稀疏、异质、昂贵但响应迅速的城市韧性资源层**（`Low-Altitude Mobility = Urban Resilience Layer`），而不是“未来高密度拥堵天空”。四份结构化的研究子问题：

- **RQ1** Ground Disruption → Air Support：地面失效时是否应选择性调用低空资源，而不是把所有需求都丢给低空。
- **RQ2** Air-Layer Failure Reconfiguration：低空自身失效（C2 lost / GNSS / UTM / landing-site / intrusion / flyaway）后 LLM 能否及时重构任务与资源。
- **RQ3** Compound Disruptions：多事件叠加时 LLM 是否比规则/启发式有更强的全局适应能力。
- **RQ4** Operational Viability：在何种信息刷新频率、推理延迟、系统规模下 LLM supervision 仍然有效。

LLM 的价值命题是 `Global Context + Semantic Priority + Dynamic Failure + Resource Tradeoff → System Reconfiguration`，而不是实时飞行控制。

---

## 2. 本研究明确不研究什么

`Research Plan.md` §2 明确排除：

- LLM 直接控制无人机姿态（pitch/roll/yaw/thrust）。
- LLM 进行秒级避碰（L0/L1 安全）。
- 高密度天空交通拥堵。
- 数百上千架 UAV 的未来城市空中交通流。
- 纯粹的 UAV path planning。
- 单纯的 truck–drone routing。

对应地，本研究只关注：**Global Resource Allocation + Mission Reprioritization + Failure Management + Ground–Air Coordination**。

> 因此任何实现都必须把 LLM 限制在 L2 层（tens of seconds ~ minutes 的全局机动管理），绝不输出飞控/避碰指令。

---

## 3. 三个组件各自负责什么

| 组件 | 职责 | 边界 |
|---|---|---|
| **SUMO**（Ground） | 城市道路网、背景地面交通、道路事故、桥梁/关键路段关闭、拥堵、医院等关键设施可达性、ground fallback 车辆 | 只负责地面；不持有低空对象坐标真值 |
| **BlueSky**（Air） | 既有 UAV/eVTOL、航空器位置与任务、低空起降点、航线、航空器可用性、C2/GNSS/UTM 状态抽象、失效与 contingency、landing-site 可用性 | 只负责低空；不做道路可视化 |
| **Python Global State Hub / Orchestrator** | 唯一 master clock；同步 SUMO 与 BlueSky；每步采集 ground/air 状态；raw→抽象全局状态；事件检测；触发/下发合法动作；写全部日志 | 所有跨层通信唯一通道 |
| **LLM Supervisory Manager** | 只读抽象状态，只产 high-level actions（dispatch/reassign/reroute/delay/cancel/reserve/divert/land/return/ground_fallback/escalate） | 不直接控制飞控；输出必须过 checker |
| **Safety / Feasibility Checker** | LLM 输出执行前的硬约束过滤（电量/路由/起降点/机型适配/deadline/限制区/UTM 规则） | LLM 答“做什么”，checker 答“能否安全做” |

**关键架构约束**：SUMO 与 BlueSky 不得彼此直接耦合业务逻辑；所有跨层通信必须经过 Global State Hub（`EXPERIMENT_IMPLEMENTATION_SPEC.md` §1.1）。

---

## 4. LLM 位于哪个时间尺度

`Research Plan.md` §9 / `experiment_plan` §4：

| 层级 | 功能 | 时间尺度 | LLM |
|---|---:|---:|
| L0 | flight control / stabilization | ms–sub-second | 否 |
| L1 | tactical avoidance / local contingency | 秒级 | 否 |
| L2 | global mobility reconfiguration | 10s–minutes | **是** |
| L3 | long-horizon planning | minutes–hours | 可选 |

- LLM 信息交换策略 = **Periodic + Event-Triggered**。正常周期初始 `Δt_LLM ≈ 30–60s`（spec 默认 `llm_update_interval_s: 30`）。
- 关键事件立即触发（road failure / new critical mission / C2 lost / GNSS degraded / UTM outage / landing-site failure / unknown aircraft / flyaway / mission infeasible / critical battery）。
- LLM 推理延迟作为实验变量：`T_LLM = {1,5,10,20,30,60}s`，用 Mode A（frozen decision）/ Mode B（delayed execution）两种 timing 模式实现。

> **本阶段（Phase 1）完全不接 LLM**，只用 deterministic test action 验证链路。LLM 触发逻辑只预留接口。

---

## 5. 为什么不研究高密度天空拥堵

`Research Plan.md` §1/§17 的核心假设：

- 近期低空交通更现实地是一层**稀缺、异质、成本较高但响应迅速的城市韧性资源**，规模 `5~30` 架（后续 scale 实验到 50），不是成熟的高容量网络。
- 研究焦点是 `Availability + Reliability + Allocation`，而不是 air congestion。
- 若建模成高密度拥堵天空，会把研究目标偷换成“未来大规模城市空中交通流”，偏离本研究的核心贡献（LLM 作为稀疏韧性层的全局监督重构）。

因此 spec §7.2 固定 canonical S0 为 12 架飞机，且 §24 scale 上限 50，明确禁止本阶段做 50-aircraft scale test。

---

## 6. 既有低空飞行器为什么必须已经承担任务

`Research Plan.md` §6 / `experiment_plan` §10：

- 低空不是空的应急储备。环境开始时物流/医疗/巡检 UAV、eVTOL 已经在执行各自任务。
- 只有“已有任务”成立，LLM 才必须面对**机会成本**：调动一架 UAV 支援紧急任务 = 打断它的原有任务。
- 因此不能只测 `Emergency Mission Success`，必须同时测 `Damage to Existing Services`（Normal Mission Delay / Cancelled Missions / Reassignment Ratio）。

spec §7.3 把它量化：canonical S0 初始负荷约 **75% occupied / 25% available**（至少 6 物流 + 1 医疗 + 1 巡检 + 1 eVTOL active，至少 2 架可再分配但不能全部闲置）。

---

## 7. SUMO 与 BlueSky 如何共享地理环境

`EXPERIMENT_IMPLEMENTATION_SPEC.md` §2/§3：

- 统一 CRS：**EPSG:4326 / WGS84**，坐标顺序 `(lat, lon)`。WGS84 经纬度是唯一地理主键。
- 唯一真值源：`config/scenario_config.yaml`（shared geographic registry）。同一设施**不得**在 SUMO 和 BlueSky 各维护一份坐标。
- SUMO 内部可用 `(x, y)` 米制投影坐标，但所有与 BlueSky / Hub 交换的数据必须转回 `(lat, lon)`。
- 禁止“SUMO 里选一个地方，BlueSky 再凭视觉选一个相似地方”。

设施（§3）：
- `H1` hospital（与 `V1` 相邻/短驳距离内）
- `V1` hospital landing site
- `V2` logistics hub landing site（与 `D1` 配对为主要物流源）
- `V3` backup landing site
- `D1` logistics depot
- `B1` critical bridge / road link（必须位于连接 H1 与主要城市区域的重要 SUMO corridor 上）

---

## 8. simulation-time co-simulation 的要求

`experiment_plan` §5.1 / spec §18：

- 基础仿真步长 `Δt_sim = 1s`。
- **Python Orchestrator 是唯一 master clock**，不得让两个模拟器自由运行后再对齐。
- 每步固定执行顺序（spec §18，本阶段去掉 LLM 触发后为）：
  1. apply scheduled events at t
  2. apply queued manager actions at t
  3. SUMO step t→t+1
  4. BlueSky step t→t+1
  5. collect SUMO state
  6. collect BlueSky state
  7. convert cross-layer coordinates to WGS84
  8. update shared state / registries
  9. detect events
  10. log timestamp
  11. advance t
- 不变量：`SUMO time == BlueSky time == Orchestrator time`（T2 允许误差 = 0 steps）。

---

## 9. Canonical 关键对象一览

### 9.1 Canonical study area（spec §2.2）
```yaml
study_area:
  name: canonical_suzhou_testbed
  center: { lat: 31.3000, lon: 120.6000 }
  width_km: 5.0
  height_km: 5.0
  crs_exchange: EPSG:4326
```
- 该区域仅作为**默认可复现实验区域**，不是对苏州运营现实性的 claim。
- bbox 由程序按中心点 + 5km×5km 计算（§2.3），不得手工在 SUMO/BlueSky 分别选。

### 9.2 Shared geographic registry（spec §3）
见 §7；唯一文件 `config/scenario_config.yaml`，含 `facilities`（H1/V1/V2/V3/D1/B1）+ bbox + CRS。

### 9.3 Geographic alignment validation（spec §6）
- 流程：`scenario_config WGS84 → SUMO (x,y) → SUMO geo-conversion → WGS84 → Haversine error`。
- 验收：**median < 5 m，max < 15 m**。
- road snapping 必须记录 original / snapped / snapping distance。
- 用 `tests/test_geographic_alignment.py` + `outputs/geographic_alignment.csv` + `reports/GEOGRAPHIC_ALIGNMENT_REPORT.md` + `outputs/unified_ground_air_scene.png` 证明（不接受两张 GUI 截图）。

### 9.4 Canonical S0（spec §7）
```yaml
scenario_id: S0
simulation_duration_s: 1800
simulation_step_s: 1
```
机队（12 架）：
```
L-UAV-01..08   (logistics UAV)     × 8
M-UAV-01..02   (medical UAV)       × 2
I-UAV-01       (inspection UAV)    × 1
EVTOL-01       (passenger eVTOL)   × 1
```

### 9.5 Master clock（spec §18）
见 §8。固定 1s，Orchestrator 独占，禁止交换执行顺序。

### 9.6 Acceptance tests（spec §29）
本阶段必须通过：**T1**（geographic alignment）、**T2**（clock sync，1800 steps 0 误差）、**T3**（mission lifecycle WAITING→ASSIGNED→EN_ROUTE→COMPLETED）、**T8**（invalid action 拒绝）、**T9**（deterministic replay）。易实现则加 **T4**（reassignment lifecycle）。每个测试给 PASS/FAIL + 实际证据，不伪造 PASS。

---

## 10. 三份文件之间的矛盾分析

结论：**三份文件在研究语义层面无实质矛盾；仅存在 2 处细节不一致 + 若干粒度差异，均已定位并给出执行裁决。**

### 10.1 文件名差异（非内容冲突）
- 用户指令写 `ground_air_llm_experiment_plan(1).md`，磁盘实际文件为 `ground_air_llm_experiment_plan.md`（无 `(1)` 后缀）。已按实际文件名读取，内容即 experiment plan。

### 10.2 RQ 结构粒度差异（非冲突）
- `Research Plan.md` 用 RQ1（ground→air）+ RQ2（air failure）两章，另设 §8 Compound Failure、§16 LLM-specific 实验。
- `experiment_plan` 形式化为 RQ1/RQ2/RQ3(compound)/RQ4(operational viability)。
- 判定：后者是前者的展开与编号化，语义一致，不冲突。执行按 experiment plan 的 RQ1–RQ4 编号。

### 10.3 GD1 注入时刻不一致（**需裁决的细节冲突**）
- spec §12.1 / §21 canonical MVP timeline：`GD1 B1 close at t=600s`（`start_s: 600`），M-CRIT-001 在 t=620s，F1 在 t=760s。
- 本阶段用户指令（第 9 步）：“例如 t = 300 s B1 closes in SUMO”，且 smoke test 时长 300–600s。
- **裁决**：spec 的 t=600s 是 **full MVP / Experiment 0**（spec Step 11–12 之后）的 canonical 时间线；本阶段做的是更早的 **co-simulation smoke test**，用户明确指定 t=300s 作为“最简单跨层事件”。因此：
  - smoke test 采用 **t=300s** 关闭 B1（时长 600s：0–300 warm-up/稳定观察，300 关闭，300–600 验证 ground→air 链路）。
  - canonical MVP 的 `GD1 start_s=600` 保持不变，留给后续 Phase 2 执行。
  - 研究语义（ground disruption → hub → air action）完全不变，仅事件注入时刻不同。
  - 记入 CHANGELOG。

### 10.4 优先级排序的粒度差异（非冲突）
- `Research Plan.md` §5：Blood > Emergency Medicine > Medical Equipment > Passenger > Normal Logistics。
- spec §11：Blood/organ/life-critical > Emergency medicine/equipment > Medical routine/essential passenger > Passenger > Normal logistics > Low-priority logistics/inspection。
- 判定：spec 是前者的超集/细化（补了 routine medical、inspection 两类），无矛盾；执行采用 spec §11 排序，且**只用于 baseline/checker/scenario 定义，不当作 LLM 的最终决策规则**。

### 10.5 其它确认一致的项
- 机队规模 12（5–30 范围内）、initial occupancy 75%/25%、1s 步长、WGS84、master clock 归属、action schema、六类 air failure 语义、B0–B4 baseline 列表、acceptance criteria、required logs —— 三份文件 + 用户指令一致。

---

## 11. Mandatory 要求清单（不可自行更改）

**地理/场景**
- M1 唯一真值源 `config/scenario_config.yaml`，CRS EPSG:4326，坐标序 (lat,lon)。
- M2 中心 (31.3000, 120.6000)，5km×5km，bbox 程序计算。
- M3 设施 H1/V1/V2/V3/D1/B1 齐全，语义关系满足（H1~V1 相邻、D1~V2 物流源、V3 备用、B1 在 H1 关键走廊上）。
- M4 同一设施不双份坐标。
- M5 地理对齐：median<5m，max<15m；snapping 记录；`unified_ground_air_scene.png` 用 Python/GIS 绘制（不依赖 BlueSky GUI）。

**SUMO**
- M6 用与 scenario_config 相同的 bbox 的真实 OSM 路网；保留原始 OSM、`network.net.xml`、`routes.rou.xml`、`additional.add.xml`、SUMO config；保留 `<location>` geo-reference。
- M7 每个设施映射到 SUMO edge（含 snapped_distance_m）。
- M8 B1 满足：D1→H1 有正常路径；B1 在关键通道；B1 关闭后有绕行路径；B1 关闭后 H1 地面可达性明显下降。
- M9 若无理想真实 bridge，允许把 B1 定义为 critical road link / bottleneck corridor，但必须解释原因。

**BlueSky**
- M10 用同一 WGS84 场景；注册/显示 H1/V1/V2/V3/D1/B1；建立小范围低空 route system。
- M11 canonical S0 机队 12 架、ID 命名固定、初始 75% busy / 25% available、不能全闲置。

**Orchestrator / 时钟**
- M12 Python Orchestrator 是唯一 master clock，step=1s，执行顺序固定，`SUMO time==BlueSky time==orchestrator time`，禁止自由运行后再对齐。
- M13 本阶段不接 LLM；smoke test 300–600s。

**事件链路**
- M14 ground event → hub detects GROUND_DISRUPTION → shared state 更新 → BlueSky 收到 mission 变更 → UAV 开始 support mission（deterministic action，不用 LLM）。
- M15（易实现则做）反向：BlueSky aircraft unavailable → hub detects AIR EVENT → shared mission NEEDS_REPLAN。

**验收/日志/交付**
- M16 通过 T1/T2/T3/T8/T9（易做加 T4），每项 PASS/FAIL + 证据。
- M17 smoke test 输出 `ground_state.csv / air_state.csv / clock_sync.csv / events.csv / run_config.yaml`。
- M18 完整交付物清单（12 项，见最终报告章节）。

---

## 12. 允许自行决定的参数/实现

spec §32 “Agent may choose” + 用户指令授权，可自行决定：
- SUMO routing helper 具体实现；TraCI（socket 子进程）还是 libsumo（本方案选 **TraCI 子进程**，理由见 §13）。
- BlueSky 具体 Python/plugin/API 接法（本方案选 **同进程嵌入 `import bluesky as bs`**，理由见 §13）。
- JSON 校验库、内部类设计、绘图库、日志实现、优化求解器（后续阶段）。
- 未显式固定的次要参数。
- 设施 V1/V2/V3 的具体 WGS84 坐标（在语义约束内由程序基于 H1/D1 与路网计算）。
- 背景交通车辆数、路线细节（满足“有背景车辆、D1→H1 有效路线”即可）。
- BlueSky 内部 simdt 的处理方式（保持 master 1s 不变，见 §13.3）。

---

## 13. 我准备如何实现 SUMO–BlueSky 协同

### 13.1 单进程 + 双接口
一个 Orchestrator 进程（用 BlueSky venv + 已安装的 eclipse-sumo），同时控制两个模拟器，从根上保证时钟不漂移。

### 13.2 SUMO：TraCI 子进程模式
- `traci.start(["sumo-gui"|"sumo", "-c", "sim/sumo/canonical.sumocfg", "--step-length", "1", ...])` 拉起 `sumo.exe` 子进程，通过本地 TCP socket 通信。
- `traci.simulationStep()` 每次恰好推进 1s（`--step-length 1`），天然满足 `SUMO time == master time`。
- 选 TraCI 而非 libsumo 的原因：TraCI 是纯 Python（对 Python 3.14 无 ABI 要求）、子进程隔离更稳、且 spec 允许二者任一。
- 坐标：`traci.simulation.convertGeo(lon, lat)` / `convertGeo(x, y, fromGeo=False)` 做 WGS84↔(x,y) 双向转换；离线对齐测试用 `sumolib` 读 `.net.xml` 的 `<location>` 投影参数。

### 13.3 BlueSky：同进程嵌入 + 1s 对齐步进
- 把仓库根 `C:\Users\xuan1\OneDrive\桌面\学术agent\bluesky` 加入 `sys.path`，`import bluesky as bs`，`bs.init('sim')` 无 GUI。
- 场景文件放在 `sim/bluesky/canonical_s0.scn`（landmark、route、12 架机、初始任务），由 Orchestrator 加载。
- 时钟对齐：BlueSky 内部默认 `simdt=0.05s`。为保证 `BlueSky time == master time`，每 master 步让 BlueSky 推进精确 1s —— 采用“按 master 步长调用 BlueSky 的 simulation event loop，累计推进 1s”的方式（20×0.05s 或按需调整），并在每步校验 `bs.sim.simt` 与 master time 相等。
- 航点：本地自定义 WGS84 waypoint（V1/V2/V3/D1/H1/B1）作为 fix 点，避免依赖全局 navaid 库（其以欧美数据为主）。
- 状态读取：`bs.traf`（id/lat/lon/alt/tas/trk/ap/status）→ 统一转 WGS84 写入 shared state。
- 动作下发：DISPATCH/REASSIGN 通过设置目标航点/航线 + 状态机标记，只产生高层指令，不生成飞控量。

### 13.4 共享真值与对齐
- `config/scenario_config.yaml` 是唯一真值；SUMO 与 BlueSky 各自从它生成，绝不各自维护坐标。
- 跨层统一 WGS84；Haversine 校验；`unified_ground_air_scene.png` 用 matplotlib（Python 本地 CRS 绘制，SUMO x/y 投影 + 叠加 WGS84 航线），不依赖 BlueSky GUI。

### 13.5 本阶段事件链路（无 LLM）
```
t=300:  B1 close (traci set edge disallowed)
  → Hub 检测 D1→H1 ETA 显著上升 → GROUND_DISRUPTION 事件
  → deterministic action: DISPATCH 一架 AVAILABLE UAV → predefined support mission (V2→V1/H1)
  → BlueSky 收到 mission 变更 → UAV 起飞/改航执行
（反向，易做则加）BlueSky aircraft unavailable → AIR EVENT → shared mission NEEDS_REPLAN
```

---

## 14. 当前机器环境（初探，详见 ENVIRONMENT_AUDIT.md）

| 项 | 状态 |
|---|---|
| Python | 默认 3.14.7（另有 uv 提供的 3.11.16 / 3.12.14） |
| SUMO | **初始未安装**（无 sumo/netconvert/traci/libsumo，SUMO_HOME 空）；正在通过 `pip install eclipse-sumo==1.27.1`（py3-none-win_amd64，仅依赖 sumo-data，无 numpy 冲突）装入 BlueSky venv |
| BlueSky | 已安装可用：源码仓库 `C:\Users\xuan1\OneDrive\桌面\学术agent\bluesky`（commit dfdff5d），venv `C:\Users\xuan1\.venvs\bluesky`（Py3.14.7，含 numpy/scipy/matplotlib/pandas/msgpack/pyzmq/openap/bluesky-navdata/PyYAML）；`import bluesky` ✅，headless 冒烟 ✅ |
| 关键库 | 默认 python：有 numpy/pandas/matplotlib/requests/scipy；**缺** PyYAML/lxml/shapely/pyproj/networkx（Orchestrator 用 BlueSky venv 已含 PyYAML） |
| 网络 | PyPI 200 ✅，sumo.dlr.de 200 ✅（可下载 OSM/SUMO） |
| 磁盘 | C: 余约 109 GB ✅ |

---

## 15. 可能阻止实验落地的问题（blocker 预判）

1. **SUMO 在 Python 3.14 的可用性**（已缓解）：`eclipse-sumo` 轮子为 `py3-none-win_amd64`（与 Python 版本无关），预期可装。若 `libsumo` 编译绑定在 3.14 不可用，**不影响**——本方案用 TraCI（纯 Python socket）而非 libsumo。待安装完成后实测确认。
2. **BlueSky 与 1s master clock 的步进对齐**：BlueSky 内部 `simdt=0.05s`，需精确实现“每 master 步累计推进 1s”并校验 `simt` 单调、无累积误差。这是实现要点而非硬阻塞，但若 BlueSky 在非 GUI 步进模式下行为异常需降级到“子进程 + 网络命令”接法。
3. **真实 OSM 数据可用性**：Suzhou（31.30, 120.60）OSM 覆盖与医院 POI 是否落在 5km×5km bbox 内需实测。若无医院 POI，按 spec §4.2 语义在 bbox 内取最近/最合理医疗类 POI，并记录理由；**不**修改研究问题、不修改中心点。
4. **netconvert 对中文路网的 typemap 处理**：可能需要调整 `--osm.elevation` / 过滤不合理边；属于常规处理，非阻塞。
5. **B1 桥/瓶颈走廊的真实性**：若 bbox 内无理想真实桥，按 spec 授权把 B1 定义为 critical road link / bottleneck corridor 并解释（M9）。
6. **OneDrive 路径**：BlueSky 仓库位于 OneDrive 同步目录下，文件同步 churn 可能影响运行稳定性；已把 venv 放在 OneDrive 之外，运行时注意。SUMO/OSM 产物写入本项目目录（亦在 OneDrive 下），若遇同步锁问题，运行/构建文件可临时放到非 OneDrive 工作区，最终产物拷回。
7. **1800-step T2 耗时**：无 GUI 下 SUMO+BlueSky 步进应可控；若单步过慢导致 1800s 模拟超时，会先做 600s 完整 smoke test + 说明 T2 用 1800-step 独立运行结果（不降标准，只调整运行方式）。

---

## 16. 本阶段执行顺序确认

按用户指令：先 spec review（本文件）→ 环境审计 → 场景构建（config→SUMO→BlueSky）→ 地理对齐证明 → Orchestrator → smoke test → 跨层事件 → acceptance tests → 最终报告。全程不接 LLM、不跑 Exp 1–4、不做 Monte Carlo / 50-aircraft / 六类 failure。
