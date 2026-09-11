# Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions

## Abstract

Low-altitude transport can preserve urgent mobility when ground routes are disrupted, but its value depends on whether scarce aircraft can be reassigned without excessive disruption to existing services. Aircraft, navigation, communications, and landing infrastructure can also fail, making coordination a continuing supervisory task. This paper develops a closed-loop architecture that combines ground and air states, exposes comparable executable candidates to a global supervisor, and validates selected actions before execution. A large language model (LLM) is evaluated alongside a ground-only manager, an air-first rule, and a fixed-objective heuristic using coupled SUMO–BlueSky simulation on road networks from Suzhou, Amsterdam, and Edmonton. Four experiments comprise 10,960 primary runs and 180 candidate-interface ablations. In the Suzhou ground-disruption panel, the LLM reduces mean emergency completion time by 21.9% relative to ground-only operation. Providing the candidate table reduces completion time by 13.57 s and existing-service damage by 0.383 services per run relative to the same LLM without the table. Under single air failures, all affected LLM runs recover an executable transport path, although recovery does not ensure timely completion. Under compound disturbances, the LLM reduces aggregate priority-weighted loss by 57.4% at Suzhou relative to ground-only operation, while showing no significant loss advantage over the coordinated rule and heuristic. Operational sensitivity experiments reveal a clear observation-frequency–call-cost trade-off, an execution-delay-induced change of transport mode, and rising token demand when the input expands to 50 aircraft records around a fixed four-aircraft fleet. These results identify comparable candidate information, surviving transport options, and timely observation and execution as the main conditions for effective global supervision.

**Keywords:** ground–air coordination; low-altitude mobility; disruption management; large language models; supervisory control; transport resilience; co-simulation.

<a id="sec-1"></a>
## 1. Introduction

Transport disruption management requires more than restoring individual links. An urgent mission may retain a feasible route while losing enough time to miss its deadline; alternatively, moving that mission to another resource may interrupt a service already in progress. Transport resilience therefore involves the performance of the connected service system as well as the availability of its physical components. This distinction is consistent with the network and system perspectives synthesized by Mattsson and Jenelius. [[1]](https://doi.org/10.1016/j.tra.2015.06.002)

Ground and low-altitude transport offer a useful setting in which to study these interactions. An aircraft can bypass a road detour, but a small fleet cannot support every delayed journey simultaneously. Medical, logistics, and passenger services may compete for vehicles with different capabilities and operating constraints. Coordinated truck–drone routing already demonstrates the importance of explicitly linking the two modes, while urban air mobility concepts place aircraft operations within a wider infrastructure and service environment. [[2]](https://doi.org/10.1016/j.trc.2015.03.005), [[3]](https://www.faa.gov/sites/faa.gov/files/Urban-Air-Mobility-Concept-of-Operations-2.0.pdf) During a disruption, these links become dynamic: the road alternative changes, aircraft become unavailable, landing sites close, and a previously appropriate assignment can cease to be executable.

A global supervisor must consequently answer three connected questions. Should an urgent ground task use a scarce aircraft? If the selected air service fails, which remaining transport path should replace it? How much of the expected benefit survives delayed information or delayed execution? Answering these questions requires a common view of mission urgency, resource compatibility, completion estimates, and the effects of reassignment on existing services.

LLMs provide a potential interface for this supervisory reasoning because they can consume heterogeneous descriptions and return structured decisions. Work on grounded robotic action and reasoning–action interaction motivates a separation between high-level language-based choice and executable capabilities. [[4]](https://proceedings.mlr.press/v205/ichter23a.html), [[5]](https://arxiv.org/abs/2210.03629) In a transport system, however, access to a detailed state description is only one part of that separation. The supervisor also needs comparable alternatives and an execution layer that interprets the selected action consistently. The central proposition examined here is that **global state becomes useful for reconfiguration when it is organized into comparable, executable, and timely decision information**.

This paper develops and evaluates that proposition through a common supervisory architecture. Ground and air simulation states are merged into a time-stamped snapshot. A deterministic candidate builder translates the snapshot into feasible transport alternatives without prescribing a manager-specific ranking. Four supervisory managers receive this interface, and their actions pass through the same deterministic validation and execution layer. Local aircraft contingency responses remain active throughout. Here, *global* means the combined state of one modeled ground–air service system; each study site is evaluated separately.

The paper makes three contributions:

1. It specifies a closed-loop ground–air supervisory architecture in which shared candidate information connects heterogeneous global state, high-level action selection, and deterministic execution constraints.
2. It evaluates that architecture through a three-site sequence of ground disruptions, individual air failures, and compound disturbances, including a matched LLM interface ablation that isolates the effect of presenting an explicit candidate table.
3. It characterizes observation timing, action execution delay, and input burden on a fixed core task, relating transport outcomes to supervisory call demand and prompt-token cost.

The experiments show both where coordinated supervision helps and what determines its benefit. The candidate table substantially improves the LLM's speed–service trade-off in the most discriminating site. Recovery mechanisms restore executable transport paths after air failures, but deadlines and surviving capacity determine whether service losses are avoided. Under shared information and constraints, the LLM frequently approaches the behavior of the coordinated baselines. This makes the information interface and the operating conditions central to the interpretation of the results.

<a id="sec-2"></a>
## 2. Related work

<a id="sec-2-1"></a>
### 2.1. Transport resilience and ground–air coordination

Transport vulnerability and resilience research distinguishes structural exposure from the consequences of disruption for system performance. A disrupted component may be important because of the services that depend on it, and recovery can involve rerouting or reallocating demand as well as repairing the component. [[1]](https://doi.org/10.1016/j.tra.2015.06.002) This paper adopts a service-oriented perspective: completion time, deadline compliance, interruption of existing missions, and priority-weighted loss are measured together.

Ground–air coordination also has a substantial operational precedent in drone-assisted delivery. The flying sidekick traveling salesman problem explicitly couples truck and drone movements to improve a delivery operation. [[2]](https://doi.org/10.1016/j.trc.2015.03.005) The present problem concerns a different decision scale. It considers a small heterogeneous fleet, urgent arrivals, reassignment of ongoing services, and changes in feasibility after disturbances. The supervisor repeatedly selects one executable intervention from the current state instead of solving a complete delivery tour. The broader infrastructure setting is motivated by urban air mobility concepts that describe interactions among vehicles, operating locations, and supporting services. [[3]](https://www.faa.gov/sites/faa.gov/files/Urban-Air-Mobility-Concept-of-Operations-2.0.pdf)

<a id="sec-2-2"></a>
### 2.2. Language models as grounded decision agents

SayCan combines language-based high-level selection with estimates of executable robotic capabilities. [[4]](https://proceedings.mlr.press/v205/ichter23a.html) ReAct interleaves reasoning and action so that an agent can use observations to guide subsequent decisions. [[5]](https://arxiv.org/abs/2210.03629) These studies motivate two design choices here: the supervisory decision is grounded in explicit candidates, and each executed intervention is followed by another observation of the environment. The candidate builder and action checker implement the grounding at the transport-system interface.

LLMLight investigates LLMs as traffic signal control agents, showing how a transport state can be represented as an input to language-based control. [[6]](https://arxiv.org/abs/2312.16044) The present work extends the evaluation question to heterogeneous ground–air resources whose feasibility can change during a mission. It also compares the LLM with managers that receive the same candidate information, allowing the interface contribution to be distinguished from the choice of decision policy.

The amount of available context is another relevant issue. Long-context language-model research shows that access to more information does not automatically imply reliable use of that information. [[7]](https://aclanthology.org/2024.tacl-1.9/) We therefore vary the number of records surrounding a fixed transport decision and measure both action validity and token demand. This experiment addresses input burden; it does not increase the number of active transport resources or the number of simultaneous urgent requests.

<a id="sec-2-3"></a>
### 2.3. Position of the present study

The study connects three usually separate concerns: the transport value of cross-modal reassignment, the grounding of an LLM supervisor in executable alternatives, and the timing conditions under which that supervisor operates. Its main empirical comparison is between decision policies inside a shared architecture. Its interface ablation asks whether an explicit candidate representation improves the same LLM's decisions. Its disturbance sequence then asks whether those decisions continue to provide useful service recovery when the low-altitude support system is itself disrupted.

<a id="sec-3"></a>
## 3. Problem formulation

<a id="sec-3-1"></a>
### 3.1. State, missions, and disturbances

Let time advance in discrete simulation steps. The ground network is a directed graph, and the air layer contains aircraft, operating sites, mission assignments, and active operating restrictions. At decision time $t$, the combined state is represented by

<a id="eq-1"></a>
$$
S_t = \left(G_t, A_t, I_t, M_t, E_t\right),
\tag{1}
$$

where $G_t$ describes ground connectivity and travel-time estimates, $A_t$ describes aircraft states, $I_t$ describes landing-site and airspace conditions, $M_t$ contains missions, and $E_t$ contains currently observed disturbances and recent events. The supervisor receives an observation $\widehat S_t=S_{\tau(t)}$ with timestamp $\tau(t)\leq t$. Information age is $t-\tau(t)$, although the ordering of events within a simulation step can also affect what a same-time snapshot contains.

Each mission $m$ has a release time $r_m$, a deadline $d_m$, origin and destination, a service type, a priority $p_m$, and configured delay and cancellation penalties. Aircraft have service compatibility, assignment status, position, commandability, and remaining endurance. Disturbances can change ground travel time, disable an aircraft capability, restrict airspace, or remove a landing option. A disturbance may leave the current mission unaffected, interrupt its selected air chain while preserving another air option, or leave ground transport as the remaining feasible alternative.

<a id="sec-3-2"></a>
### 3.2. Executable candidates and supervisory actions

For a target mission, the candidate builder constructs

<a id="eq-2"></a>
$$
\mathcal C_m(\widehat S_t)
=\left\{c:\;\operatorname{available}(c)\land
\operatorname{compatible}(c,m)\land
\operatorname{operable}(c,\widehat S_t)\right\}.
\tag{2}
$$

An air candidate identifies the aircraft, destination, assignment or reassignment action, estimated time to completion, endurance margin, and any existing mission that would be displaced. Feasibility includes commandability, battery and endurance requirements, landing-site compatibility and availability, and the modeled airspace restrictions. An occupied aircraft can be reassigned only when its existing mission is explicitly reassignable and has strictly lower priority than the target. A ground-fallback candidate is included when ground service is permitted and an estimate is available.

The supervisory policy selects one structured action per decision epoch:

<a id="eq-3"></a>
$$
a_t=\pi\!\left(\widehat S_t,\{\mathcal C_m(\widehat S_t)\}_{m\in M_t}\right),
\qquad
S_{t+1}=F\!\left(S_t,\operatorname{Execute}(a_t,S_t),e_t\right).
\tag{3}
$$

Here, $F$ includes simulator evolution and local contingency responses, and $e_t$ denotes exogenous events at the step. The action vocabulary is listed in Appendix [A](#app-a). An action selected from a past observation is checked against the state at execution; the executor obtains operational quantities from the environment rather than accepting an LLM's asserted feasibility or travel time.

<a id="sec-3-3"></a>
### 3.3. Coordination objectives

The transport problem has several objectives: completing the new mission quickly, meeting its deadline, preserving existing services, and retaining executable alternatives as the environment changes. These objectives can conflict. For example, diverting an occupied aircraft can shorten an emergency trip that already meets its deadline by road, while damaging another service. The evaluation therefore reports multiple outcomes instead of treating completion time alone as the measure of coordination quality.

For the fixed-objective baseline, these considerations are represented by the following ranking score over feasible air and ground candidates:

<a id="eq-4"></a>
$$
J_t(c)=\eta_c+10\max(0,t+\eta_c-d_m)
+\mathbf 1_{\mathrm{preempt}}(c)\left(\kappa_{p(c)}+30\right)
+10\rho_c,
\tag{4}
$$

where $\eta_c$ is the candidate's remaining completion estimate in seconds, $\kappa_{p(c)}$ is the penalty for displacing the incumbent mission, and $\rho_c$ is an endurance-margin score. The frozen values of $\kappa$ are 20, 40, and 80 for LOW, NORMAL, and HIGH incumbent priorities. CRITICAL is assigned 100,000, although equal- or higher-priority preemption is already excluded by the feasibility filter. For an air candidate with endurance margin $b_c$ in seconds, $\rho_c=\mathbf 1[b_c<120]+\mathbf 1[b_c<60]$; ground candidates incur neither preemption nor endurance penalties. This is a one-step heuristic ranking, not a solution to a full-horizon scheduling problem.

<a id="sec-4"></a>
## 4. Global supervisory framework

<a id="fig-1"></a>
![Closed-loop ground–air supervisory architecture](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/manuscript/figures/fig01_architecture.png>)

**Figure 1.** Closed-loop architecture. The environment supplies a global snapshot and a shared candidate table. A supervisor selects a structured action, which is validated and executed deterministically. Local contingency responses operate independently of supervisory inference, and subsequent observations close the loop.

<a id="sec-4-1"></a>
### 4.1. Coupled simulation and global state construction

The ground layer uses SUMO, a microscopic traffic simulation platform supporting intermodal and coupled simulation applications. [[8]](https://doi.org/10.1109/ITSC.2018.8569938) The air layer uses BlueSky, an open-source air traffic simulation environment. [[9]](https://resolver.tudelft.nl/uuid:d1131a90-f0ea-4489-a217-ad29987689a1) A master orchestrator advances the system with a 1 s step and maintains a common mission registry. It applies disturbances, updates resource and mission states, invokes the supervisor, validates actions, and records execution events.

The global snapshot contains current and baseline ground estimates, closed links, aircraft identity and role, position, assignment, remaining endurance, and commandability. It also contains operating-site availability, modeled navigation or airspace restrictions, task priorities and deadlines, and event information. The ground fallback is represented by a road-routing travel-time proxy. The air and ground components therefore share a service-level abstraction even though their underlying simulators represent different physical processes.

Newly released or interrupted missions can trigger supervisory decisions. Outside the observation-interval experiment, periodic decisions are also enabled every 30 s while a mission is waiting, requires replanning, or is interrupted. In the multi-mission experiment this condition covers the mission registry, including background services. After an accepted intervention, the system continues to evolve and may require another decision.

<a id="sec-4-2"></a>
### 4.2. Shared candidate interface

The candidate table is generated from the state using deterministic feasibility logic. It exposes the alternatives and the attributes needed to compare them, but does not include the heuristic baseline's objective value, an optimum label, or a recommended action. The primary managers receive the same information contract. Candidate-table versions extend the contract from ground disruption to air failure and then to multiple missions while preserving that separation between feasibility and preference.

This interface serves two purposes. First, it makes the effect of a policy interpretable: the manager is choosing among explicit alternatives with visible costs and constraints. Second, it prevents each manager from receiving a different implicit transport model. The rule and heuristic still implement their own ranking, and the LLM still decides how to weigh urgency and service disruption. The no-table LLM ablation retains the global snapshot and deterministic action checker but removes the explicit candidate table from the prompt.

<a id="sec-4-3"></a>
### 4.3. Supervisory managers

<a id="tab-1"></a>
**Table 1.** Supervisory policies. B4a is used only in the matched interface ablation; the four primary managers are B0, B1, B2, and B4b.

| Manager | Decision policy | Candidate information and execution |
| --- | --- | --- |
| B0: ground-only | Uses ground service for the emergency when available; does not divert air resources for cross-modal support | Shared state and validation; no supervisory air intervention |
| B1: air-first rule | Selects the legal air candidate with the lowest ETA, breaking ties by greater endurance; uses ground fallback when no legal air option remains | Shared candidate table and checker |
| B2: fixed-objective heuristic | Selects the feasible candidate with the lowest score in Equation [4](#eq-4) | Same candidates and checker as B1; frozen ranking weights |
| B4b: LLM with table | Selects a structured action from global state and explicit candidates, guided by urgency, existing-service preservation, and fault awareness | Shared candidate table and checker |
| B4a: LLM without table | Same LLM and decision prompt with the explicit candidate table removed | Global snapshot retained; same checker |

The recorded LLM backend identifier is `corp-ai/openai/deepseek-v4-pro`. Requests use temperature 0, a maximum output budget of 8,192 tokens, JSON-object output, a 180 s timeout, and at most one structured-output retry. The prompt prioritizes life-critical missions, respects higher-priority incumbent services, seeks limited disruption to existing operations, and asks for selective use of low-altitude support under faults. The model observes the current snapshot and event information; future failure schedules are not supplied to it. The recorded identifier specifies the backend used in these experiments without assuming access to its model weights or training data.

All managers act through the same action contract. B1 and B2 select eligible target missions by priority before choosing a resource. The LLM can use the combined state to select a structured intervention, but the checker still enforces compatibility and priority constraints. Neither temperature 0 nor a valid JSON object guarantees repeatable end-to-end behavior, so backend errors and retries are retained in the outcome analysis.

<a id="sec-4-4"></a>
### 4.4. Validation, execution, and local response

The deterministic checker verifies identifiers, resource status, mission compatibility, commandability, destination availability, and the relevant operational constraints. Accepted actions are translated into simulator and registry updates. Delayed actions can enter a pending queue, and subsequent events can supersede a pending command. Logged proposals, issued actions, and completed transport events are therefore distinct records.

Local contingency behavior does not wait for LLM reasoning. In the modeled command-link-loss case, for example, the affected aircraft becomes unavailable for supervisory commands and follows a local return procedure. The supervisor then selects a replacement air resource or ground fallback for the interrupted service. This division allows the experiments to evaluate service reconfiguration while preserving a consistent local response across managers.

<a id="sec-5"></a>
## 5. Experimental design and evaluation

<a id="sec-5-1"></a>
### 5.1. Study sites and resources

Three 3.2 km × 3.2 km study areas are constructed from OpenStreetMap road data: Suzhou, China (Site A); Amsterdam, the Netherlands (Site B); and Edmonton, Canada (Site C). OpenStreetMap provides the geographical road substrate. [[10]](https://discovery.ucl.ac.uk/id/eprint/13849/) Facilities, missions, aircraft operations, and disturbance schedules are scenario constructs. The sites provide contrasting road layouts and ground alternatives within a common experimental architecture.

<a id="fig-2"></a>
![Three study sites and representative ground and low-altitude connections](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/manuscript/figures/fig02_sites.png>)

**Figure 2.** Study-site road substrates and representative service connections. The red route and dashed pink detour illustrate the ground alternative around the marked road disruption; dotted green connections illustrate low-altitude support. D and H labels denote scenario ground facilities and the green site markers indicate the associated service locations. The map label B1 denotes a disrupted road link, distinct from supervisor B1. Map data: © OpenStreetMap contributors. Facilities and routes are modeled study elements.

<a id="tab-2"></a>
**Table 2.** Study-site characteristics. Road-network lengths and densities describe the imported study networks. The D1–H1 pair is the ground service reference used in the scenarios.

| Characteristic | Site A: Suzhou | Site B: Amsterdam | Site C: Edmonton |
| --- | --- | --- | --- |
| Area (km²) | 10.24 | 10.24 | 10.24 |
| Road length (km) | 200.165 | 239.265 | 188.817 |
| Road density (km/km²) | 19.547 | 23.366 | 18.439 |
| Network nodes / edges | 542 / 1,286 | 1,877 / 3,514 | 791 / 1,681 |
| Mean sampled OD circuity | 1.197 | 1.141 | 1.472 |
| D1–H1 network distance (km) | 2.922 | 1.119 | 3.430 |
| D1–H1 straight-line distance (km) | 1.740 | 0.725 | 2.529 |
| Reference critical-link ETA increase (%) | 37.87 | 88.69 | 34.76 |

Each site uses a four-aircraft core fleet: two medical UAVs, one logistics UAV, and one passenger eVTOL. Role and mission compatibility restrict which vehicles can serve each task. Low workload leaves both medical UAVs idle. High workload places them on existing missions, with reassignment available only for an explicitly reassignable lower-priority service. Geography, affected routes, and failure locations are adapted to each site; the policy definitions and experimental questions remain common.

<a id="sec-5-2"></a>
### 5.2. Four-experiment sequence

<a id="tab-3"></a>
**Table 3.** Experimental design and run counts. Each primary cell uses 20 paired seeds and four managers. Interface-ablation runs are additional B4a runs matched to the corresponding B4b subset.

| Experiment | Main factors | Sites | Primary runs | Additional ablation runs |
| --- | --- | --- | --- | --- |
| E1: selective coordination | 3 ground disruption levels × 2 urgency levels × 2 workloads | A, B, C | 12 × 20 × 4 × 3 = 2,880 | 6 scenarios × 10 seeds × 3 sites = 180 |
| E2: single air failure | 16 feasible failure-family/context combinations | A, B, C | 16 × 20 × 4 × 3 = 3,840 | 0 |
| E3: compound disturbance | 12 scenarios across four complexity levels | A, B, C | 12 × 20 × 4 × 3 = 2,880 | 0 |
| E4A: observation interval | 10, 30, 60, 120, 300 s | A | 5 × 20 × 4 = 400 | 0 |
| E4B: execution delay | 0, 1, 5, 10, 20, 30, 60 s | A | 7 × 20 × 4 = 560 | 0 |
| E4C: input burden | 5, 10, 20, 30, 50 aircraft records | A | 5 × 20 × 4 = 400 | 0 |
| **Total** | | | **10,960** | **180** |

**E1: when to use air support.** A new blood-transport mission and a ground disruption occur at $t=300$ s. Ground disruption has three levels, mission urgency has two levels, and air workload has two levels, giving 12 scenarios per site. HIGH urgency allows 300 s from release to deadline, whereas CRITICAL urgency allows 180 s. Low and high workload distinguish available medical aircraft from a fleet already serving other tasks. Six scenarios per site form the matched no-table ablation, using ten seeds each. All primary E1 runs last 900 s.

**E2: when air support fails.** The primary emergency is CRITICAL, with release at 300 s and deadline at 480 s. Six modeled failure families cover command-and-control link loss (F1), degraded satellite navigation (F2), UTM service outage or degradation (F3), landing-site failure (F4), unknown-aircraft intrusion (F5), and flyaway behavior with a moving risk envelope (F6). Three contexts distinguish a peripheral effect (C1), interruption of the emergency chain with another air option available (C2), and removal of the relevant air alternatives (C3). F3–C2 and F4–C2 are not instantiated because the configured single-event mechanisms cannot produce the intended interruption while preserving the required alternative. The resulting matrix has 16 scenario types; these two combinations are design exclusions rather than failed runs. Failure timing is adapted to intercept the site's air operation: 360 s at A, 322 s at B, and 383 s at C.

**E3: when disturbances and mission demands compound.** Twelve scenarios form four levels. L1 contains two single-failure, single-emergency anchors. L2 contains four two-failure, single-emergency cascades. L3 contains four single-failure scenarios with two simultaneous emergency missions and tighter medical-resource availability. L4 contains two scenarios combining multiple emergencies with two or three failures. In the two-emergency scenarios, a second medical mission is released at 300 s with HIGH priority and 240 s of deadline slack. The primary CRITICAL and secondary HIGH missions have delay penalties of 60 and 45 and cancellation penalties of 600 and 450, respectively. Scenario horizons are 900 or 1,200 s. Event locations and multi-event timing are adapted consistently to each site's geometry. The complete scenario manifests accompany the data release.

**E4: when operating conditions change.** Three controlled studies retain Site A's core transport task. E4A changes the observation interval, with a fault at 371 s. Its scheduled polling continues through the observation experiment's horizon, so call counts include observations after transport decisions have already been resolved. E4B injects a delay between decision and action execution for every manager, with a fault at 360 s. E4C expands the supervisor input around the four-aircraft physical fleet using unavailable, non-commandable aircraft records with zero endurance and incompatible landing capabilities, together with inert site and completed-mission records. These added records do not create usable transport capacity. Candidate invariance is checked at matched decision stages across the tested arms.

<a id="sec-5-3"></a>
### 5.3. Pairing and recorded outcomes

The primary seeds are the 20 integers from 20240601 to 20240620. Each seed controls the SUMO random seed and a common initial-state realization, including aircraft progress and battery/endurance perturbations. Busy-aircraft progress is sampled along its route, and remaining endurance is reduced by a seed-dependent amount of up to 15%. Managers are paired by scenario and seed, so each comparison uses the same exogenous realization. Some outcome cells are constant because these perturbations do not change the selected action or its resulting completion time.

The experimental unit is a scenario–seed run, not a repeated prompt. Summaries weight the included scenario–seed runs equally. Consequently, E3 aggregate results reflect the number of scenarios within each level: 40, 80, 80, and 40 runs per manager for L1–L4. Statistical intervals describe the fixed scenario panel under the tested seed variation; the three sites are not treated as a random sample of cities. Backend errors and structured retries remain in the analyzed runs.

<a id="sec-5-4"></a>
### 5.4. Metrics

For a completed emergency mission, completion duration and deadline violation are

<a id="eq-5"></a>
$$
T_m=c_m-r_m,\qquad V_m=\mathbf 1[c_m>d_m],
\tag{5}
$$

where $c_m$ is the observed completion time. Thus, exactly meeting the deadline is counted as on time. The primary mission field in the data retains the name `critical_mission_completion_time_s`, including the HIGH-urgency cells of E1. We call it *emergency completion time* when describing that experiment.

Existing-service damage counts non-primary missions whose final state is INTERRUPTED, NEEDS_REPLAN, CANCELLED, or FAILED. It is a service-state outcome at the horizon, not a cumulative count of every interruption and not a measurement of physical damage. Air intervention is determined from issued actions; a rejected proposal is not counted as an executed intervention.

For single-failure recovery, let $A_i=1$ when the run's critical air chain is actually affected. Let $R_i=1$ when an executable replacement service is established after that interruption. The reported conditional recovery rate is

<a id="eq-6"></a>
$$
\widehat P_{\mathrm{rec}}=
\frac{\sum_i A_iR_i}{\sum_i A_i}.
\tag{6}
$$

Unaffected runs have no recovery outcome and are reported as N/A. Recovery time measures the interval from the fault to the recorded resumption of a transport path. Failure-to-replan latency uses the first issued mission-specific DISPATCH, REASSIGN, DIVERT, REROUTE, or GROUND_FALLBACK action after the fault; NO_ACTION is excluded. Because different policies can expose the mission to different failures, pairwise recovery-time comparisons include only scenario–seed pairs in which both managers are affected. Completion and deadline results use all matched runs.

E3 measures priority-weighted system loss at the run horizon $H$:

<a id="eq-7"></a>
$$
L_H=\sum_{m\in M_H}w_{p_m}\ell_m(H),
\qquad
w_{\mathrm{CRITICAL,HIGH,NORMAL,LOW}}=(4,3,2,1),
\tag{7}
$$

with the implemented mission penalty

<a id="eq-8"></a>
$$
\ell_m(H)=
\begin{cases}
q_m^{\mathrm{delay}}, & m\text{ completed and }c_m>d_m,\\
q_m^{\mathrm{cancel}}, & \operatorname{status}_m(H)\in\mathcal U,\\
0, & \text{otherwise},
\end{cases}
\quad
\mathcal U=\{\text{CANCELLED, FAILED, INTERRUPTED, NEEDS\_REPLAN, WAITING}\}.
\tag{8}
$$

The delay charge is a fixed penalty for a late completed mission, not a penalty multiplied by seconds of lateness. Normal EN_ROUTE and ASSIGNED services incur no charge at the horizon. The resulting system weighted loss (SWL) is expressed in configured loss units. For example, a late completed primary CRITICAL mission contributes $4\times60=240$ units, and a late completed secondary HIGH mission contributes $3\times45=135$ units. We also examine the contribution from CRITICAL and HIGH missions. This definition makes the service-priority interpretation explicit while avoiding an interpretation of SWL as monetary cost or a comprehensive welfare measure.

E4 additionally reports the time of first fault visibility, decision-call count, prompt-token demand, and action validity. A resource/mode switch is a change between aircraft or between air and ground. An oscillation is a subsequent return to a previously used resource or mode; the count alone does not establish that the return was unnecessary. Prompt tokens per logged call include retained calls with a transport error and zero recorded token usage.

<a id="sec-5-5"></a>
### 5.5. Statistical analysis

For matched outcomes $Y_i^{(u)}$ and $Y_i^{(v)}$, the paired effect is

<a id="eq-9"></a>
$$
D_i=Y_i^{(u)}-Y_i^{(v)},\qquad
\overline D=\frac{1}{n}\sum_{i=1}^{n}D_i,\qquad
\mathrm{CI}_{95\%}=\overline D\pm t_{0.975,n-1}\frac{s_D}{\sqrt n}.
\tag{9}
$$

Continuous comparisons report raw paired differences and 95% paired $t$ intervals, with paired $t$ and Wilcoxon signed-rank results retained in the release. [[11]](https://www.jstor.org/stable/3001968) If every difference is zero, the test is assigned $p=1$. If a constant nonzero difference makes the paired $t$ statistic undefined, the finite signed-rank result is used for adjustment. E4 uses signed-rank tests for non-anchor arms against the designated anchor. These conventions prevent deterministic cells from producing undefined headline significance values.

Binary paired comparisons use exact McNemar tests, and absolute proportions use Wilson 95% intervals. [[12]](https://doi.org/10.1007/BF02295996), [[13]](https://doi.org/10.1080/01621459.1927.10502953) Paired risk-difference $t$ intervals are descriptive; inference for those endpoints uses the exact paired binary test. Holm adjustment controls each explicitly defined comparison family. [[14]](https://www.jstor.org/stable/4615733) For ordered raw values $p_{(1)}\leq\cdots\leq p_{(K)}$, the adjusted values are

<a id="eq-10"></a>
$$
p^{\mathrm{Holm}}_{(j)}=
\min\!\left[1,\max_{1\leq k\leq j}\{(K-k+1)p_{(k)}\}\right].
\tag{10}
$$

The E1 ablation family contains three endpoints per site. Scenario-specific E1 completion comparisons contain 12 tests per site. The E2 B4b–B2 family contains 12 endpoints per site, with conditional recovery denominators applied before testing. E3 uses 12 comparisons per site: two coordinated baselines, three compound levels, and two loss endpoints. E4 uses separate per-manager, per-metric families of four, six, and four non-anchor arms for observation, delay, and input burden. Appendix [C](#app-c) records the endpoint and data conventions. Statistical significance is assessed at adjusted $p<0.05$; performance interpretation also considers effect size, deadline outcomes, and the execution sequence.

<a id="sec-6"></a>
## 6. Results

<a id="sec-6-1"></a>
### 6.1. E1: selective low-altitude support under ground disruption

The first experiment shows that coordination can substantially shorten the emergency trip, but policies differ in how they use occupied aircraft. At Site A, mean completion times are 187.67, 160.78, 147.62, and 146.63 s for B0, B1, B2, and B4b, respectively (Table [4](#tab-4)). B4b saves 41.03 s, or 21.9%, relative to ground-only operation. B2 and B4b both reduce the deadline-violation rate from 33.33% to 16.67%. Their speed improvement is accompanied by different existing-service outcomes: B2 incurs 0.058 damaged services per run, compared with 0.133 for B4b and 0.500 for the air-first rule.

<a id="tab-4"></a>
**Table 4.** E1 emergency transport outcomes. Each site–manager entry contains 240 runs. Completion is measured from mission release; service damage is the mean number of non-primary missions in a damaged final service state.

| Site | Manager | Completion (s) | Deadline violations (%) | Service damage/run |
| --- | --- | --- | --- | --- |
| A | B0 | 187.67 | 33.33 | 0.000 |
| A | B1 | 160.78 | 25.00 | 0.500 |
| A | B2 | 147.62 | 16.67 | 0.058 |
| A | B4b | 146.63 | 16.67 | 0.133 |
| B | B0 | 262.67 | 50.00 | 0.000 |
| B | B1 | 47.70 | 0.00 | 0.500 |
| B | B2 | 47.70 | 0.00 | 0.500 |
| B | B4b | 49.10 | 0.00 | 0.487 |
| C | B0 | 323.67 | 83.33 | 0.000 |
| C | B1 | 168.28 | 10.00 | 0.500 |
| C | B2 | 168.28 | 10.00 | 0.500 |
| C | B4b | 168.65 | 10.00 | 0.500 |

The sub-second aggregate completion difference between B4b and B2 does not capture the most informative result. The matched interface ablation does: at Site A, adding the candidate table to the same LLM reduces completion time by 13.57 s (95% CI −19.75 to −7.38 s; Holm-adjusted $p=4.79\times10^{-5}$), service damage by 0.383 per run, and air intervention by 38.33 percentage points (Table [5](#tab-5)). The latter two changes show that the interface improves selectivity. Faster emergency service is achieved alongside fewer damaged existing services and less frequent use of air support.

<a id="fig-3"></a>
![E1 performance, existing-service damage, and candidate-table ablation](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/manuscript/figures/fig03_e1_coordination.png>)

**Figure 3.** E1 coordination and interface effects. Panels (a) and (b) show Site A means with 95% intervals for 240 runs per manager. Panel (c) shows paired completion differences for 60 matched B4b–B4a runs per site; negative values favor the candidate-table interface. The substantial interface effect at Site A accompanies a reduction in existing-service damage.

<a id="tab-5"></a>
**Table 5.** Candidate-table ablation, B4b minus B4a, with 60 matched runs per site. Negative values indicate lower completion time, fewer damaged services, or less frequent air intervention. “pp” denotes percentage points. Air-intervention intervals are descriptive paired risk-difference intervals; the adjusted test uses exact McNemar inference.

| Site | Endpoint | Paired difference | 95% CI | Holm-adjusted p |
| --- | --- | --- | --- | --- |
| A | Completion (s) | -13.567 | [-19.753, -7.380] | 4.79e-05 |
| A | Service damage/run | -0.383 | [-0.510, -0.257] | 3.13e-07 |
| A | Air intervention (pp) | -38.333 | [-50.999, -25.668] | 4.77e-07 |
| B | Completion (s) | 1.450 | [-1.824, 4.724] | 0.964 |
| B | Service damage/run | -0.017 | [-0.050, 0.017] | 0.964 |
| B | Air intervention (pp) | -1.667 | [-5.002, 1.668] | 1.000 |
| C | Completion (s) | 0.000 | [0.000, 0.000] | 1.000 |
| C | Service damage/run | 0.000 | [0.000, 0.000] | 1.000 |
| C | Air intervention (pp) | 0.000 | [0.000, 0.000] | 1.000 |

A high-disruption, HIGH-urgency, high-workload scenario illustrates the remaining speed–service trade-off. At Site A, road transport still meets the 300 s deadline slack. B2 uses ground fallback in all 20 runs. B4b reassigns an occupied aircraft in 12 runs, reducing mean completion time by 11.95 s (95% CI −17.33 to −6.57 s; Holm-adjusted $p=0.00210$ across the 12 scenario comparisons), while adding 0.600 damaged services per run. Both policies meet the emergency deadline. The LLM's faster result in this case represents a different service trade-off, rather than an unqualified improvement in coordination.

The cross-site results reinforce the role of the feasible alternatives. At Site B, mean completion falls from 262.67 s with B0 to 47.70 s with B1/B2 and 49.10 s with B4b; all coordinated managers meet the deadline in every run. At Site C, B1/B2 and B4b also have closely aligned mean completion times and deadline rates. The table ablation has no clear effect at B and exactly zero observed effect at C. Thus, the interface benefit is strongest where the scenario panel presents consequential choices between air intervention, ground completion, and preservation of an incumbent service.

<a id="sec-6-2"></a>
### 6.2. E2: restoring transport after air-system failures

All affected runs of B1, B2, and B4b establish a replacement transport path in the single-failure panel (Table [6](#tab-6)). For B4b, the affected/recovered counts are 191/191 at Site A, 199/199 at B, and 201/201 at C. These denominators differ because prior policy decisions determine whether the critical mission uses the resource or path subsequently affected by the fault. B0 has no affected critical air chain and therefore no conditional recovery denominator.

Recovery and timeliness separate clearly. Although every affected B4b run recovers a path, its all-run deadline-violation rates remain 39.06%, 37.50%, and 62.81% at A, B, and C. Some replacement routes are executable but cannot complete the mission within the remaining time. Figure [4](#fig-4) places deadline outcomes beside the paired completion differences so that restoration of service is interpreted together with its transport consequence.

<a id="tab-6"></a>
**Table 6.** E2 completion, deadline compliance, and conditional recovery. Each site–manager entry contains 320 runs. Recovery intervals are Wilson intervals on the affected subset. N/A indicates that the primary air chain was not affected, rather than a failed recovery.

| Site | Manager | Completion (s) | Deadline violations (%) | Recovered/affected | Recovery rate, 95% CI (%) |
| --- | --- | --- | --- | --- | --- |
| A | B0 | 182.00 | 100.00 | N/A | N/A |
| A | B1 | 162.00 | 37.50 | 200/200 | 100 [98.1, 100.0] |
| A | B2 | 162.00 | 37.50 | 200/200 | 100 [98.1, 100.0] |
| A | B4b | 166.53 | 39.06 | 191/191 | 100 [98.0, 100.0] |
| B | B0 | 241.00 | 100.00 | N/A | N/A |
| B | B1 | 153.88 | 37.50 | 200/200 | 100 [98.1, 100.0] |
| B | B2 | 153.88 | 37.50 | 200/200 | 100 [98.1, 100.0] |
| B | B4b | 154.05 | 37.50 | 199/199 | 100 [98.1, 100.0] |
| C | B0 | 310.00 | 100.00 | N/A | N/A |
| C | B1 | 278.00 | 62.50 | 200/200 | 100 [98.1, 100.0] |
| C | B2 | 278.00 | 62.50 | 200/200 | 100 [98.1, 100.0] |
| C | B4b | 278.92 | 62.81 | 201/201 | 100 [98.1, 100.0] |

<a id="fig-4"></a>
![Deadline outcomes and paired completion differences after single air failures](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/manuscript/figures/fig04_e2_recovery.png>)

**Figure 4.** E2 service outcomes. Panel (a) shows all-run deadline violations for 320 runs per site and manager. Panel (b) shows B4b–B2 paired mean completion differences with 95% intervals. These all-run results complement the conditional recovery rates in Table [6](#tab-6).

At Site A, B4b is 4.525 s slower than B2 on average (95% CI 1.917–7.133 s; Holm-adjusted $p=0.00868$). The conditional recovery-time difference is 3.927 s over 191 jointly affected pairs, with an adjusted $p=0.162$ (Table [7](#tab-7)). The completion difference is therefore a supported end-to-end performance difference, while the recovery-time comparison does not pass the specified multiplicity correction. At B and C, the mean completion differences are smaller, and neither is significant after adjustment.

<a id="tab-7"></a>
**Table 7.** Selected E2 paired comparisons, B4b minus B2. Completion uses all 320 matched pairs per site. Recovery time uses pairs in which both managers' critical chains are affected. Reported adjusted values belong to the full 12-endpoint per-site family.

| Site | Endpoint | Matched n | B4b − B2 (s) | 95% CI (s) | Holm-adjusted p |
| --- | --- | --- | --- | --- | --- |
| A | Completion | 320 | 4.525 | [1.917, 7.133] | 0.009 |
| A | Conditional recovery | 191 | 3.927 | [0.733, 7.121] | 0.162 |
| B | Completion | 320 | 0.175 | [0.046, 0.304] | 0.094 |
| B | Conditional recovery | 199 | 0.281 | [0.075, 0.488] | 0.094 |
| C | Completion | 320 | 0.922 | [-0.162, 2.006] | 1.000 |
| C | Conditional recovery | 200 | 0.255 | [-0.122, 0.632] | 1.000 |

The execution records show why the closed-loop distinction matters. A failed aircraft can begin a local contingency response while the supervisor selects another aircraft or ground service. That replacement can be established at the same simulation time as the fault for a deterministic manager, producing a zero simulated recovery interval. LLM backend failures and retries can defer the effective intervention until another decision opportunity; these runs remain in the reported results. Accordingly, the measured behavior belongs to the complete observation–decision–execution chain.

<a id="sec-6-3"></a>
### 6.3. E3: compound loss depends on surviving options and deadlines

The compound experiment tests whether coordinated intervention continues to protect priority-weighted service outcomes as failures and mission demands accumulate. At Site A, aggregate SWL is 240.000 for B0, 100.000 for B1 and B2, and 102.125 for B4b. The LLM reduces loss by 57.4% relative to ground-only operation. At Sites B and C, B4b aggregate SWL is 127.500 and 227.500, compared with 307.500 for B0 at each site, corresponding to reductions of 58.5% and 26.0%.

The level-by-site pattern explains these aggregate values (Table [8](#tab-8) and Figure [5](#fig-5)). Site A's L1 and L3 scenarios generally retain useful alternatives, and coordination removes most of the loss incurred by B0. Its L2 cascade scenarios yield SWL 240 for every manager: reconfiguration does not recover enough timely service to avoid the configured penalty. L4 retains partial coordination value, with B1/B2 at 120 and B4b at 123.375. The result is a pattern of available or exhausted recovery opportunities across the scenario panel, rather than a monotonic relationship between a complexity label and performance.

<a id="tab-8"></a>
**Table 8.** E3 mean system weighted loss by site and complexity level, in configured loss units. The number of runs is per manager. The aggregate values in the text weight all 240 runs per site and manager equally.

| Site | Level | n/manager | B0 | B1 | B2 | B4b |
| --- | --- | --- | --- | --- | --- | --- |
| A | L1 | 40 | 240.000 | 0.000 | 0.000 | 6.000 |
| A | L2 | 80 | 240.000 | 240.000 | 240.000 | 240.000 |
| A | L3 | 80 | 240.000 | 0.000 | 0.000 | 1.688 |
| A | L4 | 40 | 240.000 | 120.000 | 120.000 | 123.375 |
| B | L1 | 40 | 240.000 | 0.000 | 0.000 | 0.000 |
| B | L2 | 80 | 240.000 | 120.000 | 120.000 | 120.000 |
| B | L3 | 80 | 375.000 | 135.000 | 135.000 | 135.000 |
| B | L4 | 40 | 375.000 | 255.000 | 255.000 | 255.000 |
| C | L1 | 40 | 240.000 | 240.000 | 240.000 | 240.000 |
| C | L2 | 80 | 240.000 | 240.000 | 240.000 | 240.000 |
| C | L3 | 80 | 375.000 | 135.000 | 135.000 | 135.000 |
| C | L4 | 40 | 375.000 | 375.000 | 375.000 | 375.000 |

<a id="fig-5"></a>
![Priority-weighted system loss under compound disturbances across sites](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/manuscript/figures/fig05_e3_compound_loss.png>)

**Figure 5.** E3 mean SWL by site, level, and supervisor. Each cell contains 40 runs for L1/L4 or 80 runs for L2/L3. Lower values indicate fewer configured priority-weighted losses. The same supervisory policy produces different benefits as site-adapted travel times, failures, and remaining alternatives change.

At Site B, coordination removes L1 loss, halves L2 loss, and reduces L3 and L4 loss to 135 and 255, respectively. At Site C, all managers incur 240 units in L1/L2 and 375 units in L4, while the coordinated managers reduce L3 to 135. The late-primary penalty of 240 and the secondary HIGH penalty of 135 provide interpretable reference values for these outcomes. The cross-site contrast is consistent with the combination of feasible resources and deadline slack determining whether an executable alternative also prevents a loss.

B4b does not significantly reduce SWL relative to B1 or B2 in any of the three-site compound comparison families. At Site A, its SWL difference against either baseline is 0 in L2, +1.688 in L3 (95% CI −1.671 to 5.046), and +3.375 in L4 (95% CI −3.452 to 10.202); all corresponding Holm-adjusted values are 1. At Sites B and C, these compound-level SWL differences are exactly zero. The evaluated CRITICAL+HIGH loss endpoint leads to the same absence of a significant LLM advantage.

Completion duration and weighted loss can also move differently. At Site A, B0 completes the primary task in 182.00 s on average, compared with 187.25 s for B1/B2 and 188.80 s for B4b in E3, even though the coordinated policies substantially reduce SWL. Some scenarios gain timely service while others incur longer completion durations after reconfiguration; their loss penalties depend on deadlines and priorities rather than only on seconds. Appendix [B](#app-b) reports the complete aggregate completion and deadline results alongside SWL.

<a id="sec-6-4"></a>
### 6.4. E4: observation, execution, and input burden

<a id="sec-6-4-1"></a>
#### 6.4.1. Observation scheduling trades timeliness for call demand

Increasing the observation interval progressively delays visibility of both the new task and the subsequent fault. With intervals of 10, 30, 60, 120, and 300 s, B4b's mean completion durations are 140, 150, 180, 240, and 482 s. The first three arms meet the 180 s deadline slack, whereas the last two miss it in every run. B2 has the same completion outcomes in these arms, showing that the observation schedule can determine performance before differences between supervisory policies become decisive.

<a id="tab-9"></a>
**Table 9.** E4A observation scheduling and B4b performance, with 20 runs per arm. Visibility times are absolute simulation times; completion is duration from the task release at 300 s. The fault occurs at 371 s. Prompt demand is the mean sum of recorded prompt tokens per run.

| Interval (s) | Task first visible (s) | Fault first visible (s) | Completion (s) | Deadline violations (%) | Calls/run | Prompt tokens/run |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | 310 | 380 | 140 | 0 | 62 | 172849 |
| 30 | 330 | 390 | 150 | 0 | 22 | 62308 |
| 60 | 360 | 420 | 180 | 0 | 12 | 35017 |
| 120 | 360 | 480 | 240 | 100 | 7 | 21348 |
| 300 | 600 | 600 | 482 | 100 | 4 | 11708 |

Same-step ordering is important for interpreting Table [9](#tab-9). A snapshot bearing time 300 s is constructed before the new task event at that step and does not yet include that task. Its first visibility is therefore 310, 330, 360, 360, or 600 s across the five schedules. The corresponding fault-discovery delays are 9, 19, 49, 109, and 229 s. In OBS300, no critical air dispatch occurs before the fault, so conditional recovery is N/A. In OBS120, all 20 affected missions recover, but all complete late.

The slower schedules reduce supervisory call demand from 62 to 4 calls per run. Mean recorded prompt demand falls from approximately 172,849 to 11,708 tokens per run. Thus, observation frequency controls both responsiveness and cumulative inference demand. The call counts belong to the tested full-horizon polling policy; a policy that stops polling or changes frequency after resolution would have a different cost profile.

<a id="sec-6-4-2"></a>
#### 6.4.2. Execution delay can change the selected transport sequence

Execution delay initially consumes task slack almost one-for-one. For injected delays of 0, 1, 5, 10, 20, and 30 s, B4b completes the mission in 120, 121, 125, 130, 140, and 150 s, respectively. At a delay of 60 s, completion rises to 302 s and all runs miss the deadline. The tested zero-to-30-second arms remain on time.

The 60 s result has an identifiable event sequence. The initial dispatch selected at 300 s is pending until 360 s, when the fault occurs. The new ground-fallback decision supersedes that pending dispatch; the ground action executes at 420 s and completes at 602 s, giving 302 s from release. This transition is recorded as supersession, rather than rejection of a stale command. The change in outcome therefore reflects both the passage of time and a change in the executed transport sequence. The sampled arms locate an observed transition but do not establish a continuous delay threshold between them.

<a id="fig-6"></a>
![Operational sensitivity to observation intervals, execution delays, and input burden](<C:/Users/xuan1/OneDrive/桌面/PhD论文/Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions/manuscript/figures/fig06_e4_operational_conditions.png>)

**Figure 6.** E4 operational conditions for B4b. Panels show the tested observation intervals, injected execution delays, and input-record counts. Each arm contains 20 runs. Completion outcomes are constant within the tested cells in the first two panels. The input panel reports mean prompt tokens over logged calls, including retained transport-error calls with zero recorded tokens. Connecting lines guide the eye between discrete tested arms.

<a id="sec-6-4-3"></a>
#### 6.4.3. Input growth increases token demand before degrading the tested choices

Expanding the input from 5 to 50 aircraft records increases mean recorded prompt tokens per call from 3,982.1 to 20,593.5, a factor of approximately 5.17. The physical fleet remains four aircraft, and all added aircraft records are non-operational. Checks at 640 matched decision stages across the managers, seeds, and expanded arms confirm that the legal candidate set remains unchanged.

<a id="tab-10"></a>
**Table 10.** E4C input burden and B4b outcomes. Each arm contains 20 runs. Added records do not enlarge the physical fleet or feasible transport set. Logged calls include a retained transport error in N05, which produces one additional decision opportunity and a slightly higher mean completion time.

| Aircraft records | Physical fleet | Mean completion (s) | On-time runs | Logged calls | Mean prompt tokens/call |
| --- | --- | --- | --- | --- | --- |
| 5 | 4 | 121.5 | 20/20 | 41 | 3982.1 |
| 10 | 4 | 120.0 | 20/20 | 40 | 5920.6 |
| 20 | 4 | 120.0 | 20/20 | 40 | 9588.7 |
| 30 | 4 | 120.0 | 20/20 | 40 | 13256.7 |
| 50 | 4 | 120.0 | 20/20 | 40 | 20593.5 |

All 100 B4b runs in this experiment complete on time, with no observed selection of an illegal or nonexistent resource. Mean completion is 120 s in N10–N50 and 121.5 s in N05. The N05 difference corresponds to one retained backend transport error. These results show maintained selection quality over the tested input range and a substantial increase in token demand. They establish the cost of a larger surrounding state description for this fixed decision, rather than a capacity limit for coordinating 50 operational aircraft.

Across all E4 B4b runs, four transport-error calls and four structured retries are recorded. Reporting these events alongside the task outcomes preserves the operational meaning of the experiment: the supervision interface, backend response, and next decision opportunity together determine the realized action.

<a id="sec-7"></a>
## 7. Discussion

<a id="sec-7-1"></a>
### 7.1. The candidate interface carries a measurable part of coordination value

The Site A ablation provides direct evidence that presentation of executable alternatives changes supervisory behavior. The same LLM becomes faster on the emergency task while using air support less often and damaging fewer existing services. This combination is more informative than a small completion-time advantage over another manager. It suggests that explicit alternatives help the supervisor distinguish situations in which air support is necessary from situations in which a viable ground path already protects the task deadline.

The architecture deliberately makes that information available to the coordinated baselines as well. Their close performance is therefore useful evidence about what the common interface enables. In several panels, a simple policy can select the same practical option as the LLM because there are few feasible alternatives or one option clearly dominates. In the more discriminating E1 trade-off, the LLM sometimes accepts an incumbent-service loss to gain emergency speed. A deployment-oriented objective must decide how to value that exchange. The experiment exposes the exchange rather than treating a faster mission as sufficient proof of a better system decision.

<a id="sec-7-2"></a>
### 7.2. Feasibility and remaining time jointly determine recovery value

The transition from E2 to E3 separates three stages of recovery: identifying an available option, establishing a replacement service, and completing it before its deadline. The first two stages can succeed while the third fails. E2's uniformly successful conditional path restoration and substantial residual deadline violations make this distinction explicit. E3 then shows that additional disturbances can exhaust timely alternatives even when supervisors continue to issue valid actions.

A useful interpretation is the remaining temporal margin of an executable candidate:

<a id="eq-11"></a>
$$
\sigma_m(c,t)=d_m-t-\delta_{\mathrm{exec}}-\eta_c.
\tag{11}
$$

This diagnostic expression is not an additional fitted model. It states that, at decision time $t$, a candidate with estimate $\eta_c$ can meet the deadline only if the remaining slack accommodates execution delay $\delta_{\mathrm{exec}}$ and travel. Delayed observation increases the time at which a useful decision can be made; another failure can remove the candidate entirely. E4's observation and execution studies make both mechanisms visible. Its D60 sequence additionally shows that timing can change which command survives to execution.

The cross-site results indicate why physical context should be part of the evaluation rather than treated as a display background. Different road alternatives, air travel times, and site-adapted failures change the opportunities available to every supervisor. The present comparisons reproduce the architecture across these contexts while preserving their distinct opportunity sets. They do not attribute the entire performance difference to a single morphological characteristic.

<a id="sec-7-3"></a>
### 7.3. Supervisory deployment should manage information and inference demand together

E4 identifies two different sources of computational demand. Frequent observation increases the number of calls, while a larger state description increases prompt tokens per call. Reducing one does not necessarily reduce the other. The observation experiment suggests that a practical supervisor should make update frequency sensitive to unresolved missions, recent faults, and deadline slack. The input-burden experiment suggests that feasible candidates can remain a compact decision interface even when the surrounding state contains many irrelevant records. Adaptive observation scheduling and task-relevant state compression are therefore natural extensions of the demonstrated architecture.

The deterministic executor also has a continuing role after a valid decision has been produced. A command can wait in a queue while its assumptions change, so the system must retain the distinction between selection, acceptance, execution, and supersession. In parallel, local responses should remain independent of supervisory inference. These are concrete consequences of the observed event sequences, especially where an aircraft fault coincides with a delayed dispatch.

<a id="sec-7-4"></a>
### 7.4. Scope and further development

The experiments evaluate high-level service reconfiguration in a coupled simulation. They use simplified air-failure state machines, a shared ground travel-time proxy based on the reference service pair, and deterministic checks for modeled constraints. Physical payload transfer, mission-specific ground–air handoff, detailed passenger processes, and complete aircraft dynamics for each operational vehicle class are outside the current service model. SWL charges the specified terminal service states and late completions; normally ongoing EN_ROUTE or ASSIGNED background services are not assigned a horizon penalty. These choices define the meaning of the reported loss reductions.

The statistical evidence concerns fixed scenario panels with 20 seed realizations per cell. The cross-site studies use adapted geometry and failure timing. The LLM evaluation uses one recorded backend and prompt family, and the strongest candidate-table ablation effect occurs at one site. E4C increases input records around a fixed four-aircraft decision problem. Extending the work to several LLM backends, denser sets of feasible alternatives, larger active fleets, and independent cities would test how far the observed interface effect generalizes.

Finally, the simulator does not advance physical time during an external inference call. E4B injects execution delays to study temporal sensitivity, while logged backend latency and errors characterize the external service. A real-time implementation would need to couple those wall-clock processes directly to the evolving transport state. Such an implementation, together with realistic transfer processes and adaptive information updates, is the next step toward evaluating the architecture in operational conditions.

<a id="sec-8"></a>
## 8. Conclusion

This paper develops a global supervisory architecture for reconfiguring ground–low-altitude transport under disruptions and evaluates it through four experiments comprising 10,960 primary runs and 180 interface ablations. The architecture combines global state, shared executable candidates, structured supervisory actions, deterministic execution checks, and independent local contingency responses.

The central result is that the usefulness of global supervision depends on how information and action are connected. At Site A, an explicit candidate table improves the LLM's emergency completion time by 13.57 s while reducing damage to existing services. Coordinated supervision restores executable paths after single air failures and reduces priority-weighted loss in many compound scenarios. The resulting LLM behavior is often close to that of the coordinated rule and heuristic, and its benefit over ground-only operation varies with the surviving resources and mission deadlines. Observation and execution timing can remove that benefit, while larger inputs increase token demand even when the tested choices remain valid.

The study supports LLMs as a viable supervisory component within this structured architecture. Its broader transportation implication is that resilience-oriented ground–air coordination requires comparable alternatives, explicit service trade-offs, and enough remaining time to execute a useful decision. These conditions provide a practical basis for extending the framework to richer operating models and larger coordinated service systems.

<a id="data-availability"></a>
## Data and code availability

The accompanying project contains the analyzed run artifacts, scenario configurations, analysis scripts, and a frozen paper release identified as `paper_final_20260910`. The release includes the authoritative `results.json`, the summary table `main_results.csv`, execution-derived recovery metrics, SHA-256 input manifests, a source snapshot, and verification records. The manuscript package includes a table-and-figure build script and a BibTeX database. Appendix [C](#app-c) describes the regeneration procedure. This availability statement refers to the accompanying research package; no public repository identifier is assigned in this manuscript.

<a id="references"></a>
## References

<a id="ref-1"></a>
[1] Mattsson, L.-G., and Jenelius, E. (2015). Vulnerability and resilience of transport systems—A discussion of recent research. *Transportation Research Part A: Policy and Practice*, 81, 16–34. [doi:10.1016/j.tra.2015.06.002](https://doi.org/10.1016/j.tra.2015.06.002).

<a id="ref-2"></a>
[2] Murray, C. C., and Chu, A. G. (2015). The flying sidekick traveling salesman problem: Optimization of drone-assisted parcel delivery. *Transportation Research Part C: Emerging Technologies*, 54, 86–109. [doi:10.1016/j.trc.2015.03.005](https://doi.org/10.1016/j.trc.2015.03.005).

<a id="ref-3"></a>
[3] Federal Aviation Administration. (2023). *Urban Air Mobility Concept of Operations, Version 2.0*. [Official report](https://www.faa.gov/sites/faa.gov/files/Urban-Air-Mobility-Concept-of-Operations-2.0.pdf).

<a id="ref-4"></a>
[4] Ichter, B., Brohan, A., Chebotar, Y., et al. (2023). Do As I Can, Not As I Say: Grounding Language in Robotic Affordances. *Proceedings of the 6th Conference on Robot Learning*, Proceedings of Machine Learning Research, 205, 287–318. [Publisher record](https://proceedings.mlr.press/v205/ichter23a.html).

<a id="ref-5"></a>
[5] Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., and Cao, Y. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *International Conference on Learning Representations*. [Author manuscript, arXiv:2210.03629](https://arxiv.org/abs/2210.03629).

<a id="ref-6"></a>
[6] Lai, S., Xu, Z., Zhang, W., Liu, H., and Xiong, H. (2024). LLMLight: Large Language Models as Traffic Signal Control Agents. *arXiv preprint*, arXiv:2312.16044, version 5. [Author manuscript](https://arxiv.org/abs/2312.16044v5).

<a id="ref-7"></a>
[7] Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., and Liang, P. (2024). Lost in the Middle: How Language Models Use Long Contexts. *Transactions of the Association for Computational Linguistics*, 12, 157–173. [doi:10.1162/tacl_a_00638](https://doi.org/10.1162/tacl_a_00638).

<a id="ref-8"></a>
[8] Alvarez Lopez, P., Behrisch, M., Bieker-Walz, L., Erdmann, J., Flötteröd, Y.-P., Hilbrich, R., Lücken, L., Rummel, J., Wagner, P., and Wießner, E. (2018). Microscopic Traffic Simulation using SUMO. *21st IEEE International Conference on Intelligent Transportation Systems*, 2575–2582. [doi:10.1109/ITSC.2018.8569938](https://doi.org/10.1109/ITSC.2018.8569938).

<a id="ref-9"></a>
[9] Hoekstra, J. M., and Ellerbroek, J. (2016). BlueSky ATC Simulator Project: An Open Data and Open Source Approach. *7th International Conference on Research in Air Transportation*. [TU Delft repository record](https://resolver.tudelft.nl/uuid:d1131a90-f0ea-4489-a217-ad29987689a1).

<a id="ref-10"></a>
[10] Haklay, M., and Weber, P. (2008). OpenStreetMap: User-Generated Street Maps. *IEEE Pervasive Computing*, 7(4), 12–18. [UCL repository record](https://discovery.ucl.ac.uk/id/eprint/13849/).

<a id="ref-11"></a>
[11] Wilcoxon, F. (1945). Individual Comparisons by Ranking Methods. *Biometrics Bulletin*, 1(6), 80–83. [doi:10.2307/3001968](https://doi.org/10.2307/3001968).

<a id="ref-12"></a>
[12] McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. *Psychometrika*, 12(2), 153–157. [doi:10.1007/BF02295996](https://doi.org/10.1007/BF02295996).

<a id="ref-13"></a>
[13] Wilson, E. B. (1927). Probable Inference, the Law of Succession, and Statistical Inference. *Journal of the American Statistical Association*, 22(158), 209–212. [doi:10.1080/01621459.1927.10502953](https://doi.org/10.1080/01621459.1927.10502953).

<a id="ref-14"></a>
[14] Holm, S. (1979). A Simple Sequentially Rejective Multiple Test Procedure. *Scandinavian Journal of Statistics*, 6(2), 65–70. [Original article](https://www.jstor.org/stable/4615733).

<a id="app-a"></a>
## Appendix A. Interface and notation

<a id="tab-11"></a>
**Table 11.** Principal notation and units.

| Symbol | Meaning | Unit |
| --- | --- | --- |
| $t$, $\tau(t)$, $H$ | Decision time, observation timestamp, horizon | s |
| $S_t$, $\widehat S_t$ | Current state and supervisor observation | — |
| $r_m$, $d_m$, $c_m$ | Mission release, deadline, completion time | s |
| $T_m$, $V_m$ | Completion duration and deadline-violation indicator | s; binary |
| $\mathcal C_m$ | Feasible candidate set for mission $m$ | — |
| $\eta_c$, $b_c$ | Remaining completion estimate and endurance margin | s |
| $J_t(c)$ | Frozen heuristic candidate score | configured score units |
| $A_i$, $R_i$ | Affected-chain and recovered-path indicators | binary |
| $w_{p_m}$ | Priority weight | dimensionless |
| $q_m^{\mathrm{delay}}$, $q_m^{\mathrm{cancel}}$ | Flat delay and cancellation penalties | configured loss units |
| $L_H$ | Priority-weighted system loss | configured loss units |
| $\delta_{\mathrm{exec}}$, $\sigma_m$ | Injected execution delay and temporal margin | s |

<a id="tab-12"></a>
**Table 12.** Structured supervisory action vocabulary. The checker applies action-specific requirements; the vocabulary is larger than the set needed in every scenario.

| Action | Supervisory meaning |
| --- | --- |
| DISPATCH | Assign an available aircraft to a mission |
| REASSIGN | Transfer an eligible occupied aircraft to another mission |
| REROUTE | Change the route of an ongoing operation |
| DELAY | Postpone an operation |
| CANCEL | Cancel the specified operation |
| RESERVE | Reserve a resource for a mission |
| DIVERT | Change the destination or continuation of an air operation |
| RETURN | Request an eligible aircraft's return |
| LAND | Request landing under the modeled conditions |
| GROUND_FALLBACK | Establish ground service for an eligible mission |
| NO_ACTION | Make no operational change at the decision epoch |
| ESCALATE | Report the need for intervention beyond the current action choice |

The candidate table carries resource and mission identifiers, feasibility information, remaining completion estimates, endurance margins, and incumbent-service consequences. Version 2.0 supports E1; version 2.1 adds the single-failure interface used in E2/E4; version 2.2 supports E3's multi-mission representation. The no-table ablation removes this explicit table while retaining the underlying snapshot. The exact prompt construction and request settings are preserved in the accompanying source snapshot, allowing the interface to be reproduced without relying on an abbreviated prompt quoted in the paper.

<a id="app-b"></a>
## Appendix B. Complete aggregate outcomes and delay arms

<a id="tab-13"></a>
**Table 13.** Aggregate outcomes for the three-site experiments. Completion intervals are mean $t$ intervals; deadline intervals are Wilson intervals. SWL is defined for E3. The intervals summarize the fixed scenario panel and seed realizations, not a population of cities. Lower bounds from mean intervals are not truncated to impose non-negativity.

| Experiment | Site | Manager | n | Completion: mean [95% CI] (s) | Deadline violations: % [95% CI] | SWL: mean [95% CI] |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | A | B0 | 240 | 187.67 [183.63, 191.70] | 33.33 [27.67, 39.52] | N/A |
| E1 | A | B1 | 240 | 160.78 [154.28, 167.27] | 25.00 [19.94, 30.84] | N/A |
| E1 | A | B2 | 240 | 147.62 [142.15, 153.08] | 16.67 [12.48, 21.90] | N/A |
| E1 | A | B4b | 240 | 146.63 [141.41, 151.86] | 16.67 [12.48, 21.90] | N/A |
| E1 | B | B0 | 240 | 262.67 [249.67, 275.66] | 50.00 [43.72, 56.28] | N/A |
| E1 | B | B1 | 240 | 47.70 [46.62, 48.78] | 0.00 [0.00, 1.58] | N/A |
| E1 | B | B2 | 240 | 47.70 [46.62, 48.78] | 0.00 [0.00, 1.58] | N/A |
| E1 | B | B4b | 240 | 49.10 [47.24, 50.95] | 0.00 [0.00, 1.58] | N/A |
| E1 | C | B0 | 240 | 323.67 [318.37, 328.96] | 83.33 [78.10, 87.52] | N/A |
| E1 | C | B1 | 240 | 168.28 [166.83, 169.72] | 10.00 [6.81, 14.45] | N/A |
| E1 | C | B2 | 240 | 168.28 [166.83, 169.72] | 10.00 [6.81, 14.45] | N/A |
| E1 | C | B4b | 240 | 168.65 [167.07, 170.23] | 10.00 [6.81, 14.45] | N/A |
| E2 | A | B0 | 320 | 182.00 [182.00, 182.00] | 100.00 [98.81, 100.00] | N/A |
| E2 | A | B1 | 320 | 162.00 [155.16, 168.84] | 37.50 [32.37, 42.92] | N/A |
| E2 | A | B2 | 320 | 162.00 [155.16, 168.84] | 37.50 [32.37, 42.92] | N/A |
| E2 | A | B4b | 320 | 166.53 [159.24, 173.81] | 39.06 [33.88, 44.51] | N/A |
| E2 | B | B0 | 320 | 241.00 [241.00, 241.00] | 100.00 [98.81, 100.00] | N/A |
| E2 | B | B1 | 320 | 153.88 [143.23, 164.52] | 37.50 [32.37, 42.92] | N/A |
| E2 | B | B2 | 320 | 153.88 [143.23, 164.52] | 37.50 [32.37, 42.92] | N/A |
| E2 | B | B4b | 320 | 154.05 [143.38, 164.72] | 37.50 [32.37, 42.92] | N/A |
| E2 | C | B0 | 320 | 310.00 [310.00, 310.00] | 100.00 [98.81, 100.00] | N/A |
| E2 | C | B1 | 320 | 278.00 [266.93, 289.07] | 62.50 [57.08, 67.63] | N/A |
| E2 | C | B2 | 320 | 278.00 [266.93, 289.07] | 62.50 [57.08, 67.63] | N/A |
| E2 | C | B4b | 320 | 278.92 [267.83, 290.02] | 62.81 [57.39, 67.93] | N/A |
| E3 | A | B0 | 240 | 182.00 [182.00, 182.00] | 100.00 [98.42, 100.00] | 240.00 [240.00, 240.00] |
| E3 | A | B1 | 240 | 187.25 [176.00, 198.50] | 41.67 [35.61, 47.99] | 100.00 [84.92, 115.08] |
| E3 | A | B2 | 240 | 187.25 [176.00, 198.50] | 41.67 [35.61, 47.99] | 100.00 [84.92, 115.08] |
| E3 | A | B4b | 240 | 188.80 [177.39, 200.21] | 42.08 [36.01, 48.41] | 102.12 [86.92, 117.33] |
| E3 | B | B0 | 240 | 241.00 [241.00, 241.00] | 100.00 [98.42, 100.00] | 307.50 [298.90, 316.10] |
| E3 | B | B1 | 240 | 146.83 [133.44, 160.22] | 25.00 [19.94, 30.84] | 127.50 [113.16, 141.84] |
| E3 | B | B2 | 240 | 146.83 [133.44, 160.22] | 25.00 [19.94, 30.84] | 127.50 [113.16, 141.84] |
| E3 | B | B4b | 240 | 147.05 [133.67, 160.43] | 25.00 [19.94, 30.84] | 127.50 [113.16, 141.84] |
| E3 | C | B0 | 240 | 310.00 [310.00, 310.00] | 100.00 [98.42, 100.00] | 307.50 [298.90, 316.10] |
| E3 | C | B1 | 240 | 322.67 [306.37, 338.96] | 66.67 [60.48, 72.33] | 227.50 [217.18, 237.82] |
| E3 | C | B2 | 240 | 322.67 [306.37, 338.96] | 66.67 [60.48, 72.33] | 227.50 [217.18, 237.82] |
| E3 | C | B4b | 240 | 323.82 [307.38, 340.27] | 66.67 [60.48, 72.33] | 227.50 [217.18, 237.82] |

<a id="tab-14"></a>
**Table 14.** E4B B4b execution-delay outcomes, 20 runs per arm. Every completion-time cell is constant across its 20 tested seeds. Zero observed deadline violations have a Wilson 95% interval of 0–16.11%; 20/20 violations have an interval of 83.89–100%.

| Delay (s) | Mean completion (s) | Deadline violations (%) |
| --- | --- | --- |
| 0 | 120 | 0 |
| 1 | 121 | 0 |
| 5 | 125 | 0 |
| 10 | 130 | 0 |
| 20 | 140 | 0 |
| 30 | 150 | 0 |
| 60 | 302 | 100 |

The zero-delay E4B anchor matches the corresponding E2 scenario's transport outcomes for all 80 manager–seed runs. Nineteen of the 20 B4b action logs also match; the remaining log includes a retained backend transport error. In E4A, OBS10–OBS120 each have 20 affected and recovered B4b runs, while OBS300 has no affected critical air chain. These distinctions explain why conditional recovery should not be averaged across unaffected arms.

<a id="app-c"></a>
## Appendix C. Statistical families and reproducibility

### C.1. Comparison families and missing values

E1 uses three candidate-table-ablation endpoints per site: emergency completion time, existing-service damage, and air intervention. Scenario-specific B4b–B2 completion comparisons form a separate 12-test family per site. The main-text scenario example belongs to that family.

The E2 B4b–B2 family contains completion time, recovery time, failure-to-replan latency, existing-service damage, candidate-set reduction, deadline violation, recovery success, recovered-and-completed status, ground fallback, failure-induced ground fallback, necessary-ground-fallback correctness, and air intervention. Recovery endpoints require both policies to be affected. The candidate-count endpoint mixes availability and occupancy changes and is retained as a descriptive result; it is not interpreted as an isolated causal effect of the fault.

E3's compound family compares B4b with B1 and B2 at L2–L4 for SWL and the combined CRITICAL+HIGH loss contribution. Action-level fields for priority-consistency violations and resource-competition correctness are unimplemented in this release and are not analyzed as observed zero outcomes. E4 comparisons use OBS30, D00, and N05 as the respective anchors, with Holm adjustment separately for each manager and endpoint across the non-anchor arms. Undefined or unavailable tests are retained conservatively in the declared adjustment family, with the observed result still reported as unavailable rather than as an estimated effect.

### C.2. Data provenance and regeneration

The authoritative numerical release is `outputs/paper_final/results.json`. It contains 10,960 primary runs plus 180 E1 ablation runs. The release retains original run artifacts and supplies execution-derived analysis fields separately. Metric-input hashes cover 11,140 runs; additional manifests cover the action and decision-output inputs used for recovery and reliability analysis. The source snapshot and environment record identify the analysis implementation, while individual run configurations retain their original run provenance.

The final analysis environment records Python 3.14.7, NumPy 2.5.2, SciPy 1.18.0, pandas 3.0.5, Matplotlib 3.11.1, PyYAML 6.0.3, and the SUMO 1.27.1 package on Windows. This is an analysis-time record, not a claim that every historical simulation was executed in that same environment. BlueSky source is retained in the project provenance. Connection configuration is represented by a hash rather than reproduced with credentials.

The release README provides the complete offline regeneration sequence. The central commands rebuild statistics, hypothesis summaries, figures, and verification records from existing runs; they do not launch additional simulator experiments or LLM calls. The manuscript tables are generated directly from the authoritative JSON by `manuscript/build_manuscript.py`, and the same script copies or regenerates the six figures and checks internal references. The accompanying `references.bib` preserves stable citation keys for conversion to a journal or conference LaTeX class.

### C.3. Interpretation of operational timing

Observation time, decision time, action issue time, action execution time, and transport completion time are separate quantities in the records. A NO_ACTION response does not establish mission replanning. A pending action replaced by a later decision is classified as superseded, and a return to a previously used aircraft or mode is classified as an oscillation without assigning a judgment about its necessity. These definitions ensure that the timing results correspond to the actual modeled transport sequence.

The E4C prompt-token mean divides total recorded prompt tokens by logged calls, including transport-error calls with zero recorded tokens. It is an observed logging measure and is not a billing estimate. Likewise, injected simulation-time execution delay and measured wall-clock inference latency describe different processes. Maintaining these distinctions allows the operational results to be reused when the architecture is extended to real-time execution.
