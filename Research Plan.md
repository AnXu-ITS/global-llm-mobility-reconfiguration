# Research Plan  
## Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions

### 1. Core Idea

本研究不把低空交通假设成一个已经高度普及、具有大规模空中拥堵的成熟交通系统。

相反，我们采用一个更现实的假设：

> **低空交通在近期更可能是一层稀缺、异质、成本较高但响应迅速的城市韧性资源，用于物流、医疗、巡检、应急和少量载人出行。**

城市中原本已经存在一定数量的低空飞行器，例如：

- 物流 UAV
- 医疗 UAV
- 巡检 UAV
- 警务/应急 UAV
- 少量载人 eVTOL

这些飞行器平时已经承担自己的任务，并不是闲置的应急储备。

当地面交通系统出现事故、道路阻断、桥梁关闭、公共交通中断或其他重大扰动时，低空交通可以作为补充运输能力。

核心问题是：

> **一个掌握全局状态的 LLM Supervisory Manager，能否在不破坏原有低空交通运行的前提下，合理重构空地交通资源，并在低空系统自身发生故障时继续维持整体系统的韧性？**

---

# 2. Research Positioning

本研究不研究：

- LLM直接控制无人机姿态
- LLM进行秒级避碰
- 高密度天空交通拥堵
- 数百上千架 UAV 的未来城市空中交通流
- 纯粹的 UAV path planning
- 单纯的 truck–drone routing

本研究关注：

\[
\boxed{
Global\ Resource\ Allocation
+
Mission\ Reprioritization
+
Failure\ Management
+
Ground-Air\ Coordination
}
\]

LLM的角色不是飞行员，而是：

# LLM Supervisory Ground–Air Mobility Manager

---

# 3. Overall System

整个系统由三部分组成。

## Ground Layer

使用 SUMO 模拟：

- 城市道路交通
- 道路事故
- 桥梁/道路关闭
- 拥堵
- 紧急任务
- 医院、物流节点等关键设施可达性

---

## Low-Altitude Layer

使用 BlueSky 模拟：

- 已有低空飞行任务
- UAV / eVTOL
- 起降点
- 航线
- 飞行器状态
- 通信/导航状态
- 低空基础设施状态
- 异常和失效

低空规模保持相对稀疏，例如：

\[
5\sim30
\]

或最多几十架飞行器。

研究重点不是 air congestion，而是：

\[
Availability
+
Reliability
+
Allocation
\]

---

## Global LLM Manager

LLM获取整个城市的抽象化全局状态：

\[
S_t=
\{
G_t,A_t,M_t,F_t
\}
\]

其中：

- \(G_t\)：地面交通状态
- \(A_t\)：现有低空飞行器与任务状态
- \(M_t\)：新增任务和应急需求
- \(F_t\)：故障、异常和不确定性

LLM输出高层调度决策，例如：

\[
A_t^{manager}=
\{
dispatch,
reassign,
reroute,
delay,
cancel,
reserve,
divert,
land,
return,
ground\ fallback,
escalate
\}
\]

LLM不输出：

- pitch
- roll
- yaw
- thrust
- 秒级避碰动作

---

# 4. Main Research Question

核心研究问题可以表述为：

> **Can an LLM globally reconfigure a sparse, heterogeneous and failure-prone low-altitude mobility system to support disrupted ground transportation while preserving existing aerial operations?**

中文：

> **当地面交通发生扰动时，LLM能否在全局考虑原有低空任务、现有飞行器状态、应急需求和低空系统风险的情况下，合理重新配置有限的低空交通资源？**

---

# 5. Two Main Research Tasks

## RQ1 — Ground Failure → Air Support

研究地面交通发生问题时，低空资源是否应该被调动。

例如：

\[
Road\ disruption
\rightarrow
LLM
\rightarrow
Selective\ Air\ Support
\]

典型场景：

- 重大道路事故
- 桥梁关闭
- 医院道路受阻
- 公共交通中断
- 灾害导致局部道路不可达
- 大型事件导致关键道路失效

LLM不能简单地把所有需求转移到低空。

它需要判断：

> 哪些任务值得使用稀缺低空资源？

例如：

\[
Blood
>
Emergency\ Medicine
>
Medical\ Equipment
>
Passenger
>
Normal\ Logistics
\]

同时考虑：

- 任务紧急程度
- deadline
- 可用飞行器
- 飞行器当前任务
- 电量
- 距离
- 起降点
- 风险
- 对原有任务的影响

核心问题是：

# Selective Emergency Resource Allocation

---

# 6. Existing Air Traffic Must Be Preserved

研究环境开始时，低空不是空的。

例如：

- UAV-01：物流配送
- UAV-02：医疗任务
- UAV-03：巡检
- UAV-04：物流配送
- eVTOL-01：载人任务

当地面发生事故以后，LLM必须判断：

> 是否应该中断已有任务来支援新任务？

例如：

\[
Normal\ logistics
\rightarrow cancelled
\]

然后：

\[
UAV
\rightarrow emergency\ mission
\]

但同时必须衡量机会成本。

因此不能只测：

\[
Emergency\ Mission\ Success
\]

还要测：

\[
Damage\ to\ Existing\ Services
\]

---

# 7. RQ2 — Failure inside the Low-Altitude Layer

低空系统自身也可能发生异常。

重点考虑以下失效场景：

### 1. C2 Lost Link

飞行器与 operator / UTM 失去通信。

LLM需要决定：

- 是否重新分配任务
- 是否调用备用飞行器
- 是否取消任务
- 是否切换起降点

飞行器本身立即执行预定义安全 contingency procedure，不等待 LLM。

---

### 2. GNSS / Localization Degradation

定位精度下降。

可能导致：

- 飞行器不可继续承担某些任务
- 安全约束增加
- 特定区域暂时不可使用

LLM需要重新配置任务。

---

### 3. UTM / U-space Service Outage

低空数字交通管理服务失效或降级。

LLM需要决定：

- 哪些任务继续
- 哪些任务停止
- 是否停止接受新任务
- 是否让已有航空器返航/降落

---

### 4. Vertiport / Landing Site Failure

起降点不可用。

LLM需要：

- divert
- 改变目的地
- 延迟任务
- 重分配其他飞行器
- 必要时退回地面交通

---

### 5. Unknown / Non-Cooperative Aircraft Intrusion

未知或非合作飞行器进入运行区域。

LLM负责：

- 全局任务调整
- 区域限制
- 任务暂停
- 资源重新配置

局部避碰仍由传统安全算法完成。

---

### 6. Flyaway / Uncontrolled Trajectory

某架飞行器进入不可预测状态。

LLM负责：

- 将相关区域视为高风险
- 调整其他任务
- 释放/关闭部分资源
- 重新安排原任务

---

# 8. Compound Failure

真正体现 LLM价值的场景不是单一故障，而是多个事件叠加。

例如：

\[
Bridge\ Closure
+
Medical\ Mission
+
GNSS\ Degradation
+
C2\ Lost
\]

LLM需要同时考虑：

- 地面交通正在恶化
- 原有低空任务
- 新的紧急任务
- 一架支援 UAV失效
- 另一区域导航退化
- 当前剩余资源

因此研究：

\[
Context
+
Priority
+
Resource
+
Risk
+
Failure
\rightarrow Decision
\]

---

# 9. Multi-Time-Scale Architecture

LLM不能承担实时安全控制。

整个系统按照不同时间尺度分层。

## L0 — Flight Safety

时间尺度：

\[
ms\sim sub-second
\]

负责：

- 飞控
- 姿态
- stabilization
- emergency control

LLM：

\[
\boxed{No}
\]

---

## L1 — Tactical Safety

时间尺度：

\[
seconds
\]

负责：

- separation
- collision avoidance
- local contingency
- lost-link safe procedure

LLM：

\[
\boxed{No}
\]

---

## L2 — Global Mobility Management

时间尺度：

\[
tens\ of\ seconds\sim minutes
\]

负责：

- dispatch
- mission reassignment
- priority
- resource allocation
- cross-layer response
- failure reconfiguration

LLM：

\[
\boxed{Yes}
\]

---

# 10. Information Exchange Strategy

LLM不需要每秒重新读取全局状态。

采用：

# Periodic + Event-Triggered

正常运行时：

\[
\Delta t_{LLM}
\approx
30\sim60s
\]

作为初始实验设置。

同时测试：

\[
10,\ 30,\ 60,\ 120s
\]

---

发生关键事件时立即触发新的全局决策，例如：

- road failure
- critical mission
- C2 lost
- GNSS degradation
- UTM outage
- landing-site failure
- unknown aircraft
- flyaway

即：

\[
Event
\rightarrow
LLM\ Replanning
\]

---

# 11. LLM Inference Delay

LLM计算时间不能忽略。

因此直接将 latency 作为实验变量：

\[
T_{LLM}
=
\{1,5,10,20,30,60\}s
\]

研究：

> 多大的推理延迟之后，LLM manager开始无法提供有效的系统级收益？

因此可以形成一个重要研究问题：

\[
\boxed{
What\ is\ the\ effective\ supervisory\ decision\ horizon?
}
\]

---

# 12. Global State Representation

不建议直接给 LLM raw simulation state。

使用 State Abstraction Layer。

输入应该包含：

## Ground

- road failure
- congestion
- critical accessibility
- travel-time increase
- affected facilities

## Aircraft

- ID
- type
- mission
- priority
- position
- battery
- availability
- failure state

## Infrastructure

- landing-site availability
- UTM status
- GNSS status
- weather restrictions

## Missions

- existing missions
- new requests
- deadline
- priority
- payload/passenger type

同时提供趋势：

\[
S_{t-k}, S_t,\Delta S
\]

例如：

> Ground delay: 7 → 12 → 18 min, rapidly increasing.

而不仅是单个 snapshot。

---

# 13. Safety and Feasibility Layer

LLM不直接拥有最终执行权。

架构：

\[
SUMO+BlueSky
\]

↓

State Abstraction

↓

Event / Change Detection

↓

LLM Global Manager

↓

Candidate Strategy

↓

Safety / Feasibility Checker

↓

Execution

传统算法负责判断：

- 飞行器是否有足够电量
- route 是否可行
- separation 是否满足
- landing site 是否真的可用
- 飞行轨迹是否安全

LLM负责：

> **What should be done?**

传统系统负责：

> **Can it safely be done?**

---

# 14. Experimental Baselines

至少比较：

### B0 — No Cross-Layer Coordination

地面和低空各自运行。

### B1 — Rule-Based Manager

固定规则：

> critical mission → nearest available UAV

### B2 — Optimization / Heuristic Manager

传统优化或调度算法。

### B3 — LLM Global Manager

根据全局上下文进行决策。

可以进一步：

### B4 — LLM + Safety/Optimization Checker

LLM提出战略，传统算法验证并执行。

---

# 15. Main Evaluation Metrics

不能只评价 emergency mission success。

需要同时衡量：

## Critical mission performance

\[
Critical\ Mission\ Success
\]

\[
Critical\ Mission\ Delay
\]

---

## Existing service damage

\[
Normal\ Mission\ Delay
\]

\[
Cancelled\ Missions
\]

\[
Reassignment\ Ratio
\]

---

## Fleet performance

\[
Fleet\ Availability
\]

\[
Resource\ Utilization
\]

---

## System recovery

\[
Recovery\ Time
\]

\[
Ground\ Accessibility
\]

\[
System\ Loss
\]

---

## LLM management quality

可以考虑：

\[
Disruption\ Efficiency
=
\frac{Critical\ Benefit}
{Normal\ Service\ Loss}
\]

核心问题：

> LLM是否为了救一个紧急任务，过度破坏正常低空交通？

---

# 16. Three Important LLM-Specific Experiments

### Experiment A — Global State Scale

逐渐增加：

- 飞行器数量
- 任务数量
- landing sites
- simultaneous events

研究：

> LLM看到多大的全局状态后开始出现调度能力下降？

---

### Experiment B — Update Frequency

比较：

\[
10s,\ 30s,\ 60s,\ 120s,\ Event-only
\]

以及：

\[
30s+Event
\]

研究信息交换频率。

---

### Experiment C — Inference Latency

人为加入不同 LLM latency。

研究：

\[
Latency
\rightarrow Management\ Performance
\]

---

# 17. Main Scientific Contribution

本研究不是证明：

> LLM能够控制无人机。

而是研究：

> **LLM能否作为全局交通系统监督层，在一个低密度、异质、已有正常任务且自身可能发生故障的低空交通生态中，根据地面扰动动态重新配置有限的航空资源。**

核心概念是：

\[
\boxed{
Low\text{-}Altitude\ Mobility
=
Urban\ Resilience\ Layer
}
\]

而不是：

\[
Low\text{-}Altitude
=
Future\ Congested\ Sky
\]

---

# 18. Candidate Paper Title

首选：

**Global LLM-Supervised Reconfiguration of Heterogeneous Ground–Low-Altitude Mobility under Cross-Layer Disruptions**

更有故事性的版本：

**When Roads Fail, Can the Sky Adapt? Global LLM-Supervised Management of Ground–Low-Altitude Mobility under Disruptions**

---

# 19. One-Sentence Research Thesis

> **Low-altitude mobility should be treated not as a mature high-capacity urban transport network, but as a sparse and failure-prone resilience layer whose limited resources must be globally reconfigured alongside existing missions when ground transportation is disrupted.**

LLM的价值就在于：

\[
\boxed{
Global\ Context
+
Semantic\ Priority
+
Dynamic\ Failure
+
Resource\ Tradeoff
\rightarrow
System\ Reconfiguration
}
\]

而不是实时飞行控制。