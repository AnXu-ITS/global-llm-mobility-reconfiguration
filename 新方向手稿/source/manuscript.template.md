# A Ground–Low-Altitude Mobility Manager for Service Reconfiguration under Disruptions

## Abstract

Low-altitude transport offers an alternative when ground services are disrupted, but its contribution depends on scarce resources, competing missions and the time available for intervention. This paper proposes a Ground–Low-Altitude Mobility Manager that connects a global state representation to a manager-agnostic executable candidate interface, a supervisory policy, deterministic feasibility checking and execution in a coupled SUMO–BlueSky environment. Ground-only operation, an air-first rule, a fixed-objective heuristic and an LLM-based policy are compared under shared information and execution contracts. Four experiments use road networks from Suzhou, Amsterdam and Edmonton, comprising 10,960 primary runs and 180 additional interface-ablation runs. Coordination improves emergency transport or priority-weighted service outcomes in many tested conditions, but its benefit varies across network contexts and can involve disruption to existing services. Under compound disturbances at Suzhou, mean weighted loss decreases from 240 with ground-only operation to 100 with either deterministic coordinated policy and 102.125 with the LLM. All affected coordinated runs in the single-failure experiment restore a transport path, although substantial deadline violations remain. The explicit candidate interface improves the tested LLM's speed–service trade-off at Suzhou, with weaker or absent effects elsewhere. Observation scheduling and execution delay can exhaust temporal margins and change the executed transport sequence. These findings support a common architecture for studying supervisory policies and show that useful reconfiguration depends on surviving transport alternatives, service preferences and timely execution, without establishing a general advantage of LLM supervision.

**Keywords:** ground–low-altitude mobility; service reconfiguration; disruption management; supervisory control; transport resilience; network morphology.

## 1. Introduction

Transport disruption management concerns the continuation of services as network conditions change. A route may remain connected while taking too long to meet an urgent task's deadline. Conversely, restoring the urgent task by diverting a vehicle may interrupt another service that was already under way. Evaluating the response therefore requires attention to service outcomes as well as infrastructure availability. Transport vulnerability and resilience research provides a basis for connecting disruptions to changes in system performance, including consequences that extend beyond the initially affected component. [[1]](https://doi.org/10.1016/j.tra.2015.06.002)

Ground and low-altitude transport provide a setting in which these interactions are particularly explicit. An aircraft can avoid a road detour, but a small heterogeneous fleet cannot serve every delayed task. Aircraft assignments must respect service compatibility, remaining endurance, landing-site availability and the priority of incumbent missions. Moreover, the supporting air system can itself become disrupted. Communication loss, navigation degradation or the closure of a landing site may invalidate a previously appropriate allocation. The supervisory problem consequently continues after the initial decision to use air support.

The relevant decision scale in this study is service reconfiguration. A supervisor observes the combined ground–air system and chooses an intervention, such as assigning a spare aircraft, reassigning an eligible occupied aircraft, changing an ongoing operation or establishing ground fallback. Local aircraft responses remain responsible for their modeled contingency behavior. This separation allows the supervisor to focus on which service should use which surviving transport option, while a common execution layer determines whether the intervention can proceed. It also exposes a temporal distinction: selecting a feasible alternative does not ensure that the service will resume soon enough to meet its deadline.

Dynamic routing and disruption-management methods already address decisions made as new information arrives. Reviews of dynamic vehicle routing and work on real-time public transit rescheduling demonstrate the importance of updating operational decisions during service provision. [[4]](https://doi.org/10.1016/j.ejor.2012.08.015), [[5]](https://doi.org/10.1080/21680566.2017.1358678) In a ground–low-altitude system, policy comparison additionally requires consistent treatment of heterogeneous transport alternatives. If one policy receives a derived travel-time estimate while another must infer that quantity from raw descriptions, the comparison mixes the information interface with the selection policy. Similarly, different execution constraints can make apparently identical decisions operationally incomparable.

We propose a Ground–Low-Altitude Mobility Manager that separates these concerns. Its architecture follows the sequence **Global State → Manager-Agnostic Executable Candidate Interface → Supervisory Policy → Deterministic Safety/Feasibility Checker → Executor → SUMO–BlueSky closed loop**. The candidate interface exposes feasibility, estimated completion time and consequences for existing services without transmitting a policy-specific score or recommendation. Four policy implementations use this architecture: a ground-only reference, an air-first rule, a fixed-objective heuristic and a large language model (LLM). The LLM is one implementation of the supervisory policy. Here, *global* refers to the joint state of a single modeled study area; the three areas are evaluated separately.

The evaluation addresses four questions. When does low-altitude intervention improve emergency transport sufficiently to justify its effects on existing services? After an air-system failure, does restoring an executable path also restore timely service? How do coordination benefits and policy differences vary across contrasting network contexts? Finally, how do observation scheduling, execution delay and input burden affect the realized intervention? Four experiments address these questions using three road-network substrates and a common small-fleet service model. The comparisons include convergence between simple and LLM policies, rather than requiring one implementation to dominate for the architecture to be informative.

The paper makes three contributions. First, it specifies and implements a supervisory architecture in which executable candidate information connects heterogeneous transport states, policy preferences and common execution constraints. Second, it provides a controlled comparison of service reconfiguration under ground disruptions, individual air failures and compound disturbances across three network contexts, including a matched LLM candidate-interface ablation. Third, it characterizes the consequences of observation scheduling and action execution delay for transport outcomes, while separately measuring the input burden of the LLM implementation. Together, these contributions identify conditions under which supervisory reconfiguration produces useful service recovery and conditions under which additional policy complexity yields little observed benefit.

## 2. Related work

### 2.1. Transport disruption, vulnerability and service resilience

Transport resilience concerns how a system sustains or regains useful performance following disruption. Mattsson and Jenelius distinguish related vulnerability and resilience perspectives and discuss the importance of the system boundary used in evaluation. [[1]](https://doi.org/10.1016/j.tra.2015.06.002) Jenelius and Mattsson further connect conceptual vulnerability measures to implementable indicators and network case studies. [[2]](https://doi.org/10.1016/j.compenvurbsys.2014.02.003) These perspectives motivate the distinction used here between the existence of an alternative path and the service outcome achieved through that path.

Complete component failure is only one form of disruption. Cats and Jenelius examine how partial capacity degradation affects public transport network performance, illustrating why a binary representation of network availability can miss operational consequences. [[3]](https://doi.org/10.1080/21680566.2016.1267596) The present study likewise evaluates more than connectivity, using completion duration, deadline compliance, incumbent-service damage and priority-weighted loss. Its response mechanism is resource and service reconfiguration. It does not model the repair of damaged infrastructure or measure the time required for an entire network to return to its pre-disruption state.

### 2.2. Dynamic fleet management and ground–air coordination

Dynamic vehicle routing research addresses information that becomes available during operations and the corresponding need to update routing and assignment decisions. Pillac et al. organize this literature around the characteristics of dynamic information and associated solution approaches. [[4]](https://doi.org/10.1016/j.ejor.2012.08.015) In public transport, Lai and Leung study the use of real-time and historical information for operational routing and scheduling decisions in disruption management. [[5]](https://doi.org/10.1080/21680566.2017.1358678) These studies establish that dynamic adaptation is a transportation-management problem with a substantial methodological foundation.

Ground–air coordination adds relationships between modes and their resources. The flying sidekick traveling salesman problem explicitly coordinates truck and drone movements for parcel delivery. [[6]](https://doi.org/10.1016/j.trc.2015.03.005) Urban air mobility concepts place aviation operations within a broader environment of operating locations, supporting services and management responsibilities. [[7]](https://www.faa.gov/sites/faa.gov/files/Urban-Air-Mobility-Concept-of-Operations-2.0.pdf) The problem considered here differs from complete tour construction: a supervisor repeatedly chooses a service intervention for a small heterogeneous fleet while tasks, assignments and feasibility change. The ground component supplies a shared travel-time alternative, and the air component supplies compatible resources whose reassignment may affect incumbent services. Physical payload transfer and detailed intermodal access processes remain outside the current abstraction.

### 2.3. Supervisory architectures and constrained execution

Separating action proposals from constraint enforcement is an established control-system design principle. For example, the predictive safety filter of Wabersich and Zeilinger evaluates a proposed control input against a model-based safety mechanism for constrained nonlinear systems. [[8]](https://doi.org/10.1016/j.automatica.2021.109597) This provides a useful architectural precedent for keeping a decision policy distinct from the layer that permits its execution. The guarantees in that work depend on its predictive-control formulation and assumptions. The checker in the present study instead enforces the modeled service and operational rules deterministically; it does not establish invariant-set safety, recursive feasibility or certified aircraft separation.

At the transportation-service level, an additional requirement is that policies compare the same alternatives. Our candidate interface therefore exposes common environmental facts before policy selection, while execution-time checks use the current state after any waiting period. The contribution lies in specifying this interface for the ground–low-altitude reconfiguration problem and evaluating its consequences together with service dynamics, rather than in claiming a new general principle of hierarchical control.

### 2.4. Language models as supervisory policies and study positioning

Language-based decision systems motivate explicit connections between high-level selection and executable capabilities. SayCan grounds language-based choices in robotic capabilities, separating a plausible instruction from an action that the system can perform. [[9]](https://proceedings.mlr.press/v205/ichter23a.html) LLMLight studies LLMs as traffic signal control agents, providing a transport application of language-based decisions over a represented state. [[10]](https://arxiv.org/abs/2312.16044v5) These studies motivate the inclusion of an LLM policy, while leaving the transport value of that policy to empirical comparison.

The way information is represented also matters. Research on long-context language models shows that the presence of information in a context does not guarantee that it is used reliably. [[11]](https://aclanthology.org/2024.tacl-1.9/) We examine an explicit candidate-table ablation and input growth around a fixed decision problem. The former changes the representation available to the same LLM; the latter increases surrounding records without adding operational aircraft. Neither experiment is a test of all possible language models or a general demonstration of large-fleet coordination.

The study thus brings together a particular combination of concerns: cross-modal service reassignment, disruption-dependent feasibility, policy comparison under a shared information contract, and observation–execution timing. Its empirical focus is the behavior of complete supervisory implementations within one architecture. It does not compare the LLM with the strongest possible routing or optimization method, and it does not require an LLM advantage to establish where the architecture enables useful reconfiguration.

## 3. Problem formulation

### 3.1. Ground–low-altitude service system

Let the ground network be a directed graph $G^g=(V^g,E^g)$. The low-altitude layer contains aircraft, operating sites, assignments, routes and active restrictions. Time advances in discrete simulation steps. At time $t$, the combined service state is

$$
S_t=(G_t,A_t,I_t,M_t,E_t), \tag{1}
$$

where $G_t$ contains ground connectivity and travel-time estimates, $A_t$ contains aircraft states, $I_t$ describes landing infrastructure and operating restrictions, $M_t$ is the mission registry, and $E_t$ records currently represented disturbances and recent events. A mission $m$ has a release time $r_m$, absolute deadline $d_m$, origin, destination, service type, priority $p_m$, state and configured penalties. An aircraft has a role, assignment status, position, remaining endurance, landing compatibility and commandability.

A disruption can alter ground travel time, interrupt a selected air chain, remove an aircraft from supervisory control or eliminate a landing option. The same external event can affect different policies differently because their earlier assignments determine the mission's exposure. Cross-modal reconfiguration changes a task's assigned resource or transport mode, or changes the continuation of an existing operation. It can improve an emergency's outcome while changing the service state of an incumbent mission.

The supervisor receives an observation

$$
\widehat S_t=\mathcal O_t(S_{0:t}),\qquad \tau(t)\le t, \tag{2}
$$

where $\mathcal O_t$ incorporates snapshot sampling and event ordering and $\tau(t)$ is the snapshot timestamp. The age $t-\tau(t)$ is useful but does not completely describe visibility: an event injected after a snapshot at the same simulation second is absent from that snapshot. This distinction becomes operationally important in the observation-scheduling experiment.

### 3.2. Candidate information and feasible alternatives

A deterministic mapping $\Phi$ constructs the candidate information interface,

$$
\mathcal I_t=\Phi(\widehat S_t),\qquad
\mathcal C_{m,t}=\{c\in\mathcal I_{m,t}:\operatorname{legal}(c\mid\widehat S_t)=1\}. \tag{3}
$$

$\mathcal I_{m,t}$ contains the records associated with mission $m$, whereas $\mathcal C_{m,t}$ denotes the subset marked legal. The distinction is necessary because the interface retains rejected resource records and their rejection reasons. A candidate record identifies the mission and resource, transport mode, implied action, estimated remaining completion duration $\widehat\eta_c$, feasibility status, endurance information, destination conditions and any incumbent service that would be displaced.

Air feasibility depends on availability, mission compatibility, commandability, battery/endurance conditions, landing-site compatibility and modeled restrictions. Reassignment of an occupied aircraft requires an explicitly reassignable incumbent mission with strictly lower priority than the target. A ground candidate is available when the mission permits ground fallback and a travel-time estimate is present. These candidates represent the alternatives generated by the implemented service model; they do not enumerate every possible route or future schedule.

The interface contains no B2 objective score, optimizer selection or manager-specific recommended action. Nevertheless, it embodies shared modeling choices, including priority constraints, travel-time approximations and the organization of multi-mission records. Manager-agnostic therefore means that policies share the same generation rules and facts at a given state, rather than that the representation is free of operational assumptions. Once policies take different actions, their subsequent states and candidate sets can legitimately differ.

### 3.3. Supervisory actions and execution-time constraints

At a decision epoch, policy $k$ proposes one structured intervention:

$$
a_t^{\mathrm{prop}}=\pi_k(\widehat S_t,\mathcal I_t),\qquad
k\in\{\mathrm{B0,B1,B2,B4b}\}. \tag{4}
$$

The action contract includes assignment and reassignment actions, route or destination changes, ground fallback, and management responses such as delay or no action. A proposal need not correspond to selecting an aircraft. In particular, B0 restricts cross-modal emergency support to the ground alternative.

Let $t_e=t+\delta_{\mathrm{exec}}$ be a proposal's scheduled execution time. Let $Q(a,t_e)$ indicate that the proposal remains the active command version for the relevant task, and let $\Gamma(a,S_{t_e})$ denote the semantic and feasibility check using the current execution state. Abstracting the action-specific normalization performed by the implementation, the executed intervention is

$$
u_{t_e}=\begin{cases}
\operatorname{Executor}(a_t^{\mathrm{prop}},S_{t_e}),
&Q(a_t^{\mathrm{prop}},t_e)=1\land\Gamma(a_t^{\mathrm{prop}},S_{t_e})=1,\\
\varnothing,&\text{otherwise}.
\end{cases} \tag{5}
$$

A proposal replaced by a newer command is superseded; a proposal that fails the current checks is rejected. Neither event is equivalent to completed transport. The subsequent state follows

$$
S_{t+1}=F(S_t,u_t,e_t,\ell_t), \tag{6}
$$

where $e_t$ represents exogenous events and $\ell_t$ represents local contingency responses. This notation describes the implemented supervisory interface and event-driven simulator evolution. It is not a fitted transition model or a proof of closed-loop stability.

### 3.4. Service outcomes and temporal feasibility

For a completed mission, completion duration and deadline violation are

$$
T_m=c_m-r_m,\qquad V_m=\mathbf1[c_m>d_m], \tag{7}
$$

where $c_m$ is the absolute completion time. Completion exactly at the deadline is on time. A useful diagnostic for a candidate at decision time $t$ is its estimated temporal margin,

$$
\sigma_m(c,t)=d_m-t-\delta_{\mathrm{exec}}-\widehat\eta_c,\qquad
\mathcal C^{\mathrm{timely}}_{m,t}=\{c\in\mathcal C_{m,t}:\sigma_m(c,t)\ge0\}. \tag{8}
$$

A nonempty feasible set does not ensure a nonempty set of alternatives predicted to finish on time. Even a nonnegative estimated margin does not guarantee on-time completion, because subsequent failures, queue changes and estimation error can alter the outcome. Equation (8) organizes the interpretation of the experiments; it does not introduce a newly measured candidate-count endpoint or a continuous delay threshold.

We evaluate service resilience through path restoration, deadline compliance, incumbent-service preservation and priority-weighted loss. These outcomes describe complementary aspects of supervisory recovery. They do not measure infrastructure repair or imply that all parts of the transport system have returned to their original operating conditions.

## 4. Ground–Low-Altitude Mobility Manager

### 4.1. Global state and closed-loop environment

The framework couples SUMO for ground traffic with BlueSky for the air environment. SUMO provides a microscopic traffic simulation platform with interfaces for coupled applications, while BlueSky provides an open air traffic simulation environment. [[12]](https://doi.org/10.1109/ITSC.2018.8569938), [[13]](https://resolver.tudelft.nl/uuid:d1131a90-f0ea-4489-a217-ad29987689a1) A master orchestrator advances both layers on a 1 s simulation step, maintains the service registry, applies events, invokes the selected policy and records action outcomes.

@@FIG1@@

**Figure 1.** Ground–Low-Altitude Mobility Manager. Candidate generation, policy choice, constraint checking and execution have separate responsibilities. The policy block contains four alternative implementations. Local contingency responses operate independently of supervisory inference. The checker enforces modeled operational constraints and does not constitute formal safety certification.

The global snapshot combines current and reference ground estimates, closed links, aircraft positions and assignments, endurance, commandability, landing-site availability, task priorities and deadlines, and represented failure conditions. Ground fallback uses a road-routing travel-time proxy associated with the reference service pair. The resulting coupling is a service-level model: it connects task status and resource allocation across modes while abstracting detailed pickup, transfer and passenger processes.

### 4.2. Manager-agnostic executable candidate interface

The candidate builder exposes facts needed to compare air and ground alternatives. Remaining completion estimates use a common duration convention. Air estimates combine the modeled route geometry, role-specific cruise speeds and dispatch overhead. The interface also reports absolute estimated completion time, the remaining deadline margin and structural consequences of preemption. Ground uses the common fallback estimate. These estimates support supervisory choice; the executor obtains operational quantities from the environment rather than accepting an LLM's asserted travel time or feasibility.

**Table 1.** Main information groups in the executable candidate interface.

| Group | Information supplied | Supervisory role |
|---|---|---|
| Target mission | Identifier, priority, origin, destination, deadline and state | Establish task requirements and urgency |
| Resource and action | Aircraft or ground identifier, mode, dispatch/reassignment/fallback action | Connect the alternative to the execution contract |
| Feasibility | Legal flag, rejection reason, compatibility, commandability and destination state | Distinguish available interventions from rejected alternatives |
| Completion and time | Remaining ETA, estimated absolute completion, deadline comparison | Compare transport duration and remaining margin |
| Existing service | Preempted mission identifier and priority, interruption indicator | Make the consequence of reassignment visible |
| Air operating state | Battery/endurance information and failure-related restrictions | Represent the modeled operating conditions |

The generator does not run B2 or receive its preference weights. B1 and B2 calculate their own selections from the shared table, while B4b receives the same table within the prompt. A structural interruption indicator identifies whether reassignment displaces an existing service; it is not a learned welfare estimate or a B2-weighted cost.

The contract develops through additive versions. Version 2.0 supports E1, version 2.1 adds single-failure information for E2 and E4, and version 2.2 supports the multi-mission representation used in E3. Multi-mission entries are organized by priority and deadline. These are common organizational rules rather than optimizer recommendations. The policy comparison is controlled within each experiment and interface version; the full experiment sequence is not represented as having byte-identical inputs.

### 4.3. Supervisory policies

The four primary policies are summarized in Table 2. All use the common action contract and execution constraints. B0 provides a reference for emergency transport without supervisory air support, while B1, B2 and B4b compare alternative coordinated policies. Background air services remain present under B0.

**Table 2.** Supervisory policies and their comparison roles.

| Policy | Selection rule | Interpretation |
|---|---|---|
| B0: ground-only | Serves the eligible target by ground fallback, without retasking an air asset for cross-modal support | Reference for the total effect of enabling coordination |
| B1: air-first rule | Chooses the legal air candidate with minimum ETA, using endurance to break ties; considers ground when no legal air option remains | Simple deterministic coordination |
| B2: fixed-objective heuristic | Selects a target under the frozen priority rule and minimizes a fixed scalar score over legal air and ground candidates | One-step completion–service–risk trade-off |
| B4b: LLM-based policy | Reads the shared state and explicit candidate table and returns a structured intervention | Language-based implementation of the policy layer |
| B4a: no-table LLM | Uses the same prompt template and checker as B4b with the explicit candidate section removed | Additional E1 interface ablation only |

B1's air-first ordering is important: it minimizes ETA among legal air candidates, rather than minimizing travel time over both modes. B2 compares air and ground using the frozen score

$$
J_t(c)=\widehat\eta_c+10\max(0,t+\widehat\eta_c-d_m)
+\mathbf1_{\mathrm{preempt}}(c)(\kappa_{p(c)}+30)+10\rho_c, \tag{9}
$$

where $\kappa_{\mathrm{LOW,NORMAL,HIGH,CRITICAL}}=(20,40,80,100000)$ and $\rho_c=\mathbf1[b_c<120]+\mathbf1[b_c<60]$ for endurance margin $b_c$ in seconds. Ground candidates incur neither preemption nor endurance penalties. The score uses configured seconds-equivalent trade-offs and contains no separate ground-delay term. Equal- or higher-priority preemption is already excluded by the feasibility rules. B2 is a one-step candidate-ranking heuristic, not a full-horizon scheduling optimizer or model predictive controller.

B4b uses the frozen prompt template with temperature 0, JSON output mode and an output-token budget of 8192. The recorded backend identifier is `corp-ai/openai/deepseek-v4-pro`; this is the configured service identifier and does not independently certify the provider's underlying model version. The no-table ablation changes only the explicit candidate section of the prompt template, while retaining the global snapshot and checker. Neither deterministic decoding settings nor valid JSON guarantee repeatable end-to-end operation, so transport errors and structured retries remain in the analyzed cohort.

### 4.4. Deterministic checking

The validation pipeline checks action structure, identifiers, mission and aircraft status, commandability, compatibility, destination availability, priority restrictions and the relevant modeled operating constraints. The distinction between preselection filtering and action checking is deliberate. Candidate legality describes the observed state; execution checks address whether the selected intervention can be applied to the state that exists when it is due.

Rejected proposals are logged rather than silently converted into a preferred action. An accepted assignment changes the registry and simulator commands through deterministic execution rules. These rules apply to every supervisory implementation. Consequently, a valid LLM proposal cannot be interpreted as evidence that the model itself supplied the safety mechanism, and a high task completion rate does not certify physical safety beyond the modeled constraints.

### 4.5. Execution, pending actions and local contingencies

The executor maintains the distinction between proposal, issue, execution and transport completion. In the execution-delay experiment, accepted proposals enter a pending queue. Task-specific versioning allows a newer command to supersede an earlier pending command, and the execution pipeline revalidates the current action before application. A change in the environment can therefore alter both when a command executes and which command ultimately survives.

Local aircraft contingency behavior continues independently of supervisory decisions. In the modeled command-link-loss case, for example, an affected aircraft becomes unavailable for further supervisory commands and follows its local return procedure. The manager can then select another air resource or ground fallback for the interrupted service. Service recovery thus combines a common local response with a potentially policy-dependent replacement decision.

### 4.6. Decision opportunities and observation scheduling

New or interrupted missions can trigger supervisory decisions. Outside the observation-interval experiment, periodic decisions are also enabled every 30 s while a task is waiting, requires replanning or is interrupted. In E3, the condition covers actionable missions in the registry, including background services. Each accepted intervention is followed by continued simulator evolution and subsequent observations.

E4A replaces this ordinary observation arrangement with controlled snapshot refresh and polling schedules. The policy uses the latest observed snapshot rather than an unrestricted view of current state. E4B instead introduces controlled execution waiting, and E4C adds inert input records around the unchanged core service problem. These experiments isolate different implementation conditions while preserving the respective frozen policy definitions.

## 5. Experimental design

### 5.1. Study sites and modeled services

The three study areas are based on OpenStreetMap road data from Suzhou, China (A), Amsterdam, the Netherlands (B), and Edmonton, Canada (C). OpenStreetMap supplies the geographic network substrate. [[14]](https://discovery.ucl.ac.uk/id/eprint/13849/) The configured study-area extent is 3.2 km × 3.2 km at each site. Figure 2 shows the imported road substrates and representative service connections. Network conversion can retain geometry beyond the nominal area, so the figure uses a common projected scale and shows the full imported substrates rather than presenting their outlines as identical nominal-area boundaries.

@@FIG2@@

**Figure 2.** Three network contexts and representative ground and air alternatives, drawn from existing projected network geometry as editable PowerPoint paths. Red indicates the primary ground route, purple the road detour and green the primary low-altitude connection. Brown lines restore the archived auxiliary road ODs at B and C; blue dashed lines show background air-service connections and the auxiliary V5–V4 connection where present. D1/H1 identify the reference service endpoints, V3 the backup landing site, and D2/H2/C2/C3 auxiliary facilities. Co-located landing nodes are not labeled separately. “Closure” marks the reference disrupted road link and is distinct from policy B1. Auxiliary routes describe the broader site geometry and are not additional missions in the frozen E1 primary cohort. Scale bars are 500 m. Water and road data: © OpenStreetMap contributors. Facilities, air operations and disturbance scenarios are modeled service elements.

@@TABLE_SITE@@

Road length and density sum directional passenger-edge lengths, counting two directions separately. Intersection density counts junctions with at least three distinct neighbors. Mean OD circuity uses the project's fixed sample of 200 OD pairs, whereas D1–H1 circuity describes the particular reference service pair. The reference closure ETA increases are network-validation quantities, not substitutes for the full E1 disturbance matrix.

The sites offer contrasting operating contexts. Site A has a meshed urban network with meaningful choices between continued ground service and occupied air resources. Site B combines the highest road density with water-barrier constraints on the reference ground corridor. Site C has a higher dead-end ratio and mean sampled OD circuity, with a longer reference service distance. These characteristics motivate contextual comparisons; they do not constitute a controlled experiment in which a single morphological variable changes.

Every site uses a four-aircraft core fleet: two medical UAVs, one logistics UAV and one passenger eVTOL. Compatibility restricts which aircraft can serve a given mission. Low medical workload leaves the medical aircraft idle, whereas high workload assigns them to existing services. Facilities, aircraft operations, landing sites and failures are scenario constructs. The experiments do not claim that the modeled low-altitude service systems operate in the three cities.

### 5.2. Shared controls and site adaptations

Policies share mission semantics, the action contract, candidate-generation rules and deterministic execution constraints within an experiment. The prompt and B2 objective remain frozen. Geographic coordinates, road alternatives, aircraft travel distances and failure placement vary across sites. Failure times are adapted to intercept the modeled air operation, rather than applying an identical time that would affect different flight phases. Thus, the cross-site evaluation tests the same supervisory architecture in different network and service contexts.

Two comparisons must be distinguished. B0 versus a coordinated policy measures the total difference associated with allowing cross-modal support, including a difference in available transport modes. B1 versus B2 versus B4b compares supervisory implementations under common information and action constraints. In contrast, B4a versus B4b tests explicit candidate presentation within the same LLM implementation. These comparisons answer different questions and are not combined into one ranking of algorithmic intelligence.

### 5.3. Disturbance experiments

**Table 4.** Experiment design and sample sizes. Each primary scenario–arm–policy cell contains 20 paired seeds.

| Experiment | Factors | Sites | Primary runs | Additional B4a runs |
|---|---|---|---:|---:|
| E1 | 3 ground disruption levels × 2 urgency levels × 2 workloads | A, B, C | 2,880 | 180 |
| E2 | 16 feasible failure-family/context combinations | A, B, C | 3,840 | 0 |
| E3 v2 | 12 scenarios across four disturbance/task levels | A, B, C | 2,880 | 0 |
| E4A | Observation intervals of 10, 30, 60, 120, 300 s | A | 400 | 0 |
| E4B | Execution delays of 0, 1, 5, 10, 20, 30, 60 s | A | 560 | 0 |
| E4C | Total aircraft records of 5, 10, 20, 30, 50 | A | 400 | 0 |
| **Total** | | | **10,960** | **180** |

**E1: ground disruption and selective support.** A new blood-transport mission and a ground disruption occur at 300 s. Ground disruption has three levels, urgency has HIGH and CRITICAL levels, and medical workload is low or high. HIGH urgency has 300 s of deadline slack and CRITICAL urgency has 180 s. The resulting 12 scenarios run for 900 s. Six scenarios per site provide the interface ablation, with ten matched seeds each. The 180 extra runs are B4a runs; their B4b counterparts belong to the primary cohort.

**E2: individual air-system failures.** The primary CRITICAL mission is released at 300 s and has deadline 480 s. Six failure families model command-and-control link loss, GNSS degradation, UTM degradation/outage, landing-site failure, unknown-aircraft intrusion and flyaway behavior with a moving risk envelope. Context C1 affects a peripheral part of the operation, C2 interrupts the primary service chain while retaining another air option, and C3 removes the relevant air alternatives. F3–C2 and F4–C2 are excluded because the specified mechanisms cannot create the intended combination of interruption and surviving air alternative. The resulting 16 scenarios use fault times of 360, 322 and 383 s at A, B and C, respectively.

**E3: compound disturbance and competing services.** Twelve scenarios form four levels. L1 comprises two single-failure, single-emergency anchors. L2 comprises four two-failure, single-emergency cascades. L3 comprises four single-failure scenarios with two simultaneous emergency missions and tighter medical-resource availability. L4 comprises two scenarios with multiple emergencies and two or three failures. In the two-emergency scenarios, the second medical mission is released at 300 s with HIGH priority and 240 s of deadline slack. The primary CRITICAL and secondary HIGH missions have delay penalties of 60 and 45 and cancellation penalties of 600 and 450, respectively. Horizons are 900 or 1,200 s. These levels change both disturbance structure and task demand and are not a one-dimensional ladder of difficulty.

### 5.4. Observation, execution delay and input burden

E4 retains Site A's core task and separates three operational changes. E4A varies the snapshot observation interval, with a fault at 371 s. Scheduled polling continues over the observation experiment's horizon, including after some transport decisions have resolved. E4B introduces the same specified decision-to-execution delay for every policy, with a fault at 360 s. E4C enlarges the surrounding input using unavailable, non-commandable aircraft records with zero endurance and incompatible landing capabilities, together with inert facility and completed-mission records.

E4C does not add usable transport capacity. Its core fleet remains four aircraft, and candidate invariance is checked at matched decision stages. The experiment therefore tests input burden and selection quality for a fixed transport decision. It does not test scheduling fifty operational aircraft or serving a proportionally larger set of urgent missions.

### 5.5. Outcomes, pairing and statistical interpretation

The primary seeds are 20240601–20240620. Each controls the SUMO random seed and a common initial-state realization, including progress and endurance perturbations for aircraft. Busy-aircraft progress is sampled along its route, and remaining endurance receives a seed-dependent reduction of up to 15%. Comparisons pair policies by scenario and seed. Some outcomes are constant within a cell because the perturbations do not change the executed action or resulting completion time.

Emergency completion and deadline violation follow Equation (7). Existing-service damage counts non-primary missions whose horizon state is INTERRUPTED, NEEDS_REPLAN, CANCELLED or FAILED. It measures final service status rather than cumulative historical interruptions or physical damage. Issued actions identify air intervention; rejected proposals do not count as interventions.

For recovery, let $A_i=1$ if a run's primary air chain is actually affected and $R_i=1$ if an executable replacement service is established. Conditional path restoration is

$$
\widehat P_{\mathrm{rec}}=\frac{\sum_i A_iR_i}{\sum_i A_i}. \tag{10}
$$

When no run is affected, the result is N/A. Pairwise recovery-time comparisons include only pairs in which both policies are affected. Completion and deadline comparisons retain all matched runs. Failure-to-replan latency uses the first issued mission-specific DISPATCH, REASSIGN, DIVERT, REROUTE or GROUND_FALLBACK action after the fault, excluding NO_ACTION. Path restoration and completed transport are separate events.

E3's system weighted loss (SWL) is

$$
L_H=\sum_{m\in M_H}w_{p_m}\ell_m(H),\qquad
w_{\mathrm{CRITICAL,HIGH,NORMAL,LOW}}=(4,3,2,1), \tag{11}
$$

with

$$
\ell_m(H)=\begin{cases}
q_m^{\mathrm{delay}},&m\text{ completed and }c_m>d_m,\\
q_m^{\mathrm{cancel}},&\operatorname{state}_m(H)\in\mathcal U,\\
0,&\text{otherwise},
\end{cases}
\quad\mathcal U=\{\mathrm{CANCELLED,FAILED,INTERRUPTED,NEEDS\_REPLAN,WAITING}\}. \tag{12}
$$

Late completion incurs a fixed penalty, not a charge per second late. Normally ongoing EN_ROUTE and ASSIGNED services incur no horizon penalty. A late primary CRITICAL mission therefore contributes 240 units and a late secondary HIGH mission contributes 135 units. SWL is expressed in configured loss units, not monetary welfare. We also report the CRITICAL+HIGH component when comparing compound-level policies.

For continuous endpoints, the paired difference and its interval are

$$
D_i=Y_i^{(u)}-Y_i^{(v)},\qquad
\overline D=\frac1n\sum_iD_i,\qquad
\mathrm{CI}_{95\%}=\overline D\pm t_{0.975,n-1}\frac{s_D}{\sqrt n}. \tag{13}
$$

The release retains paired t and Wilcoxon signed-rank results, as well as pooled-SD effect sizes. [[15]](https://doi.org/10.2307/3001968) Identical pairs receive $p=1$. For a constant nonzero paired difference, the t statistic is undefined and the finite signed-rank result is used for adjustment. Binary comparisons use exact McNemar tests, while absolute proportions use Wilson intervals. [[16]](https://doi.org/10.1007/BF02295996), [[17]](https://doi.org/10.1080/01621459.1927.10502953) Paired risk-difference t intervals are descriptive. Holm adjustment applies to the recorded comparison families, with adjusted $p<0.05$ as the significance criterion. [[18]](https://www.jstor.org/stable/4615733)

E1 ablation families contain three endpoints per site; scenario-specific completion comparisons contain 12 tests per site. E2 uses a 12-endpoint B4b–B2 family per site. E3 uses 12 comparisons per site: two coordinated baselines, three compound levels and two loss endpoints. E4 compares non-anchor arms with OBS30, D00 and N05, using separate per-policy, per-metric families. Appendix B records interpretation details. A nonsignificant comparison is not treated as statistical equivalence.

Summaries weight scenario–seed runs equally. E3 therefore has 40, 80, 80 and 40 runs per policy at L1–L4, rather than equal level weights. Intervals describe the tested fixed scenario panels and seed perturbations. The three sites are not a random sample of cities, and the total run count does not establish city-population inference.

### 5.6. Provenance and model scope

The analysis uses the frozen release `paper_final_20260910`: E1-final, corrected E2, E3-v2 and E4-v2. Original run artifacts remain separate from corrected derived metrics. The release includes metric-input hashes, execution-derived inputs, analysis code, a source/environment snapshot and verification records. Its analysis-time snapshot is distinct from original run-time provenance.

The model evaluates high-level service reconfiguration with simplified failure state machines, a shared reference-pair ground ETA proxy and deterministic checks of modeled constraints. It does not explicitly conserve physical payload through every transfer or calculate a separate ground access/egress trajectory for every task. External inference calls do not advance the physical simulation clock. Injected execution delays and recorded wall-clock inference latency are consequently different quantities. These boundaries determine the transport claims supported by the experiments.

## 6. Results

### 6.1. Selective coordination under ground disruption

E1 shows that enabling air support can substantially improve emergency transport, while the choice of coordination policy affects incumbent services. At Site A, mean emergency completion is 187.67 s for B0, 160.78 s for B1, 147.62 s for B2 and 146.63 s for B4b. B2 and B4b both reduce deadline violations from 33.33% under B0 to 16.67%. Their service consequences differ: mean existing-service damage is 0.058 per run for B2, 0.133 for B4b and 0.500 for B1. Figure 3 and Table 5 place these outcomes alongside one another.

@@FIG3@@

**Figure 3.** E1 mean emergency completion, deadline violation and existing-service damage across the three sites. Each site–policy cell contains 240 runs. The plots show descriptive means; Table 6 and the scenario comparison below report paired inference for the corresponding comparisons. Policy colors are consistent across all result figures.

@@TABLE_E1@@

The high-disruption, HIGH-urgency, high-workload case at Site A illustrates the policy trade-off. Ground fallback has an estimate of approximately 228.617 s and can meet the 300 s deadline slack. B2 chooses ground in all 20 runs. B4b reassigns an occupied aircraft in 12 runs and uses ground in eight. Its completion time is lower by 11.95 s on average (95% CI −17.330 to −6.570 s; Holm-adjusted $p=0.002100$ across the 12 scenario comparisons), while damage increases by 0.600 services per run. Both policies meet the emergency deadline in all runs. Faster transport in this case reflects a different choice about preserving an existing service, rather than an improvement on every outcome.

The cross-site patterns show why the ground-only comparison must be separated from the policy comparison. At Site B, completion falls from 262.67 s with B0 to 47.70 s with B1/B2 and 49.10 s with B4b, and all coordinated policies meet all tested emergency deadlines. At Site C, completion falls from 323.67 s to approximately 168 s under coordination, with a common 10% deadline-violation rate. The large gains associated with enabling air support coexist with small differences among the coordinated implementations. They should not be attributed solely to the sophistication of any one policy.

### 6.2. Executable candidate representation and policy behavior

The matched interface ablation provides evidence about the explicit candidate representation within the LLM implementation. At Site A, B4b minus B4a is −13.567 s for emergency completion (95% CI −19.753 to −7.380; Holm-adjusted $p=4.794\times10^{-5}$). It is also −0.383 damaged services per run and −38.333 percentage points for air intervention. The combination matters: the candidate-table policy completes the emergency more quickly while intervening less frequently and preserving more incumbent services.

@@FIG4@@

**Figure 4.** Paired differences for the explicit candidate-table LLM (B4b) relative to the no-table LLM (B4a), with 60 matched runs per site. Negative values indicate lower completion duration, fewer damaged services or lower air-intervention frequency. Bars denote 95% paired intervals. Air-intervention risk-difference intervals are descriptive; inference uses exact McNemar tests.

@@TABLE_ABLATION@@

The effect does not recur uniformly across sites. At B, the mean completion difference is +1.450 s and the adjusted $p$ is 0.964. At C, the three reported ablation endpoints have exactly zero observed difference. These results are consistent with the interface being most consequential where the represented alternatives expose a meaningful choice between ground completion, air intervention and preservation of an incumbent service. They do not establish that all policies require an explicit table to perform well, nor that this representation is universally optimal.

The architecture nevertheless gives the representation a role beyond its appearance in a prompt. It ensures that B1, B2 and B4b access comparable derived facts and that chosen resources can be traced into execution. The ablation identifies an effect of making these facts explicit to one policy implementation. The common contract, rather than an LLM-only prompt format, is the basis for the primary policy comparison.

### 6.3. Path restoration versus timely service recovery

All affected B1, B2 and B4b runs restore an executable replacement transport path in E2. B4b restores 191/191 affected runs at A, 199/199 at B and 201/201 at C. B1 and B2 each restore 200/200 at every site. These denominators differ because earlier policy decisions determine whether the emergency uses the subsequently affected resource or route. B0 has no affected primary air chain, so its conditional recovery outcome is N/A.

@@FIG5@@

**Figure 5.** E2 all-run deadline violations and conditional path-restoration counts. Deadline results use 320 runs per site and policy. Recovery counts include only affected primary air chains. Restoring every affected path does not imply that all missions meet their deadlines; B0 has no conditional air-chain recovery denominator.

@@TABLE_E2@@

Path restoration and timely recovery separate sharply. B4b's all-run deadline-violation rates remain 39.06%, 37.50% and 62.81% at A, B and C. B1/B2 have corresponding rates of 37.50%, 37.50% and 62.50%. A replacement route can satisfy operational constraints yet require more time than remains before the deadline. The high restoration counts therefore demonstrate the availability and use of replacement service mechanisms within this panel, while the deadline results reveal their transport limitations.

At Site A, B4b completes the emergency 4.525 s later than B2 on average (95% CI 1.917–7.133 s; Holm-adjusted $p=0.008678$). The conditional recovery-time difference is +3.927 s over 191 jointly affected pairs, with adjusted $p=0.162454$. Thus, the all-run completion comparison identifies a disadvantage for the tested LLM implementation, whereas the conditional recovery-time endpoint does not pass the specified correction. At B and C, completion differences are smaller and do not pass Holm adjustment. Table 8 preserves the different paired denominators.

@@TABLE_E2_PAIRS@@

A local aircraft response and a supervisory replacement decision can occur within the same simulation second, giving deterministic policies a zero simulated recovery interval in some conditions. Backend transport errors and retries can postpone the effective supervisory intervention until another decision opportunity. The reported outcomes retain those runs and describe the complete implementation, rather than an idealized policy with backend failures removed.

### 6.4. Compound disruptions and priority-weighted service loss

E3 tests whether useful service outcomes persist as faults and mission demand accumulate. At A, aggregate SWL decreases from 240 under B0 to 100 under B1/B2 and 102.125 under B4b. At B, the corresponding values are 307.5 and 127.5 for all three coordinated policies. At C, they are 307.5 and 227.5. These reductions reflect the configured service penalties avoided by coordination, and their magnitude differs across sites.

@@FIG6@@

**Figure 6.** E3 mean priority-weighted service loss by site, scenario level and policy. L1/L4 contain 40 runs per policy and L2/L3 contain 80. The common vertical scale preserves comparisons across sites. L1–L4 vary in both disturbance structure and mission demand; the sequence does not imply monotonically increasing difficulty.

@@TABLE_E3@@

The level-specific results clarify where these averages arise. At A, B1/B2 eliminate L1 and L3 loss, while B4b has residual means of 6 and 1.6875. All policies have SWL 240 in L2. In L4, the deterministic coordinated policies have mean 120 and B4b has 123.375, compared with 240 for B0. Thus, additional feasible interventions do not necessarily remove the late-primary penalty in the cascade scenarios, while other scenarios retain useful opportunities to protect service.

At B, coordinated policies eliminate L1 loss, reduce L2 from 240 to 120, and reduce L3 and L4 from 375 to 135 and 255. At C, all policies have loss 240 in L1/L2 and 375 in L4; coordination reduces L3 from 375 to 135. The configured late-primary penalty of 240 and late-secondary penalty of 135 provide reference values for interpreting these patterns, although a cell mean does not uniquely identify every run's service trajectory.

B4b does not significantly reduce SWL relative to B1 or B2 in any of the three-site compound comparison families. At A, its differences from either policy are 0 in L2, +1.6875 in L3 (95% CI −1.671 to 5.046) and +3.375 in L4 (95% CI −3.452 to 10.202), with adjusted $p=1$ for these comparisons. At B and C, the corresponding compound-level SWL differences are zero. The CRITICAL+HIGH loss endpoint likewise provides no significant LLM advantage. These outcome similarities do not establish statistical equivalence or prove that every action sequence is identical.

Weighted service loss and primary completion time can move in different directions. At A, B0 completes the primary task in 182.00 s on average, compared with 187.25 s for B1/B2 and 188.80 s for B4b, despite the lower SWL under coordination. The loss function depends on which services meet their deadlines and their priorities, rather than only on average seconds to primary completion. This is an additional reason to avoid interpreting a single speed metric as system-wide coordination quality.

### 6.5. Cross-site synthesis: network context and policy convergence

The cross-site results reveal differences in both coordination opportunity and policy sensitivity. Site A's E1 panel contains decisions in which ground can still meet the deadline while aircraft reassignment offers a smaller speed benefit at an incumbent-service cost. This setting exposes differences between the frozen B2 trade-off and the LLM's choices and produces the strongest candidate-interface ablation effect. In B and C, the primary E1 outcomes are much more similar across coordinated policies even though their gains over ground-only transport are large.

The network evidence helps interpret these contexts without isolating a single causal factor. B has the highest directional road density, yet its reference disruption removes a water-crossing option and increases reference ETA by 88.69%. Density alone is therefore an incomplete description of its ground alternatives. C has the highest sampled mean OD circuity and dead-end ratio and the longest reference network distance. Its D1–H1 circuity, however, is lower than the same ratio at A and B. The overall network statistic and the particular task geometry must be kept distinct.

The compound panel shows why ground vulnerability does not automatically imply a large recoverable benefit from air support. C has substantial E1 gains but no SWL improvement at L1, L2 or L4 in E3. The capacity to avoid loss depends on the surviving service alternatives after the specified faults and on the time left to complete the relevant tasks. Conversely, a context with a large air-versus-ground advantage can yield very little separation among policies when they exploit similar alternatives.

These findings support reproduction of the supervisory architecture across contrasting network contexts. Geography, facility placement, aircraft travel times and fault timing change together, so the comparisons do not identify an independent effect of density, circuity or route redundancy. The interpretation is conditional on the site-adapted scenarios and common service model.

### 6.6. Operational timing and input burden

#### 6.6.1. Observation scheduling and call demand

Observation scheduling affects both the discovery of a new task and the later fault. Under OBS10, OBS30, OBS60, OBS120 and OBS300, B2 and B4b have identical mean completion durations of 140, 150, 180, 240 and 482 s. B1 shares the first four values but completes in 521 s under OBS300. B0 completes in 192, 212, 253, 253 and 482 s. Thus, timing often dominates differences between coordinated policies, while the longest interval still exposes a difference for the air-first rule.

@@FIG7@@

**Figure 7.** Operational sensitivity at Site A. Panels (a) and (b) show all four policies under the tested observation intervals and injected execution delays; B2 and B4b overlap. Panel (c) shows B4b prompt tokens per logged call as total aircraft records increase around the fixed four-aircraft fleet. Each arm–policy cell contains 20 runs. Lines connect discrete tested arms for readability and do not identify continuous thresholds. Token means include retained transport-error calls with zero recorded tokens.

@@TABLE_E4A@@

At time 300 s, the snapshot is constructed before the same-second task event becomes visible. The new task first appears at 310, 330, 360, 360 or 600 s across the observation schedules. The fault at 371 s first appears at 380, 390, 420, 480 or 600 s. A zero-age timestamp consequently does not ensure inclusion of all same-second events. E4A measures the combined observation-scheduling mechanism, rather than an isolated effect of stale fault information.

B4b meets the deadline in all OBS10–OBS60 runs, with OBS60 finishing exactly at the deadline. All OBS120 and OBS300 runs finish late. The OBS120 runs restore the affected path but cannot recover timely completion. In OBS300, the critical air chain has not been dispatched when the fault occurs, so conditional recovery is N/A. Counting these runs as recovery failures would conflate absence of exposure with failure to restore service.

The scheduling change also reduces B4b call demand from 62 to four calls per run. Mean recorded prompt demand falls from approximately 172,849 to 11,708 tokens per run. These totals belong to the fixed full-horizon polling protocol. They do not estimate the cost of an adaptive policy that stops or changes observation frequency after the service has resolved.

#### 6.6.2. Execution delay and the executed service sequence

For injected delays of 0, 1, 5, 10, 20 and 30 s, B1, B2 and B4b complete in 120, 121, 125, 130, 140 and 150 s, respectively. At 60 s delay, B2 and B4b complete in 302 s and B1 in 341 s. B0 changes from 182 s at zero delay to 302 s at 60 s. In the tested B4b cells, delays through 30 s retain on-time completion, whereas all D60 runs are late.

@@TABLE_E4B@@

The D60 B4b event sequence explains why the final difference is not simply an additional 60 s of travel (Figure 8). The initial dispatch proposal at 300 s is scheduled for execution at 360 s. The fault occurs at that time, and a newer ground-fallback decision supersedes the pending dispatch. Ground service executes at 420 s and completes at 602 s, yielding a duration of 302 s from release. This record is a command supersession, rather than rejection of a stale command by the checker.

@@FIG8@@

**Figure 8.** B4b execution sequence in E4B D60. The air dispatch waits from 300 to 360 s and is superseded when the fault and new ground decision occur. Ground fallback waits until 420 s and completes at 602 s, after the deadline at 480 s. Timing changes which intervention reaches execution as well as when transport completes.

The zero-delay E4B anchor matches the corresponding E2 transport outcomes for all 80 policy–seed runs. B0/B1/B2 action logs match in 20/20 cases and B4b in 19/20, with the remaining B4b log containing an additional retained transport error. The observed transition at D60 belongs to this event timing and queue logic. The discrete arms do not establish a general maximum tolerable inference delay, nor do they show that real wall-clock inference latency was coupled to a continuously evolving simulation.

#### 6.6.3. Input burden with a fixed active fleet

Increasing total aircraft records from five to fifty raises B4b's mean recorded prompt tokens per call from 3,982.1 to 20,593.5, approximately 5.17-fold. The core physical fleet remains four aircraft. The release's 640 comparisons at matched decision stages confirm that the legal candidate set remains unchanged under the input expansion.

@@TABLE_E4C@@

All 100 B4b runs in E4C complete on time, with no observed selection of an illegal or nonexistent resource. Completion is 120 s in N10–N50 and 121.5 s in N05. The N05 difference accompanies one retained transport error and an additional decision opportunity. It does not indicate that smaller inputs are intrinsically harder. The result establishes rising input burden with maintained selection quality over the tested range, rather than coordination capacity for fifty operational aircraft.

Across E4, B4b records four final transport-error calls and four structured retries. Those events remain in the results. Switching between resources or modes is also distinguished from returning to a previously used choice; a necessary replacement aircraft is not, by itself, evidence of decision oscillation. Together, these records connect the external decision service to the operational sequence that determines completion.

## 7. Discussion

### 7.1. Candidate interfaces as a transport-management design choice

The proposed interface makes the transportation meaning of a supervisory choice explicit. An aircraft identifier alone does not describe a useful alternative: the supervisor also needs to know whether that aircraft can serve the task, the expected time to completion and what happens to its incumbent service. Ground must be represented on a comparable completion-time basis. By generating these attributes through one deterministic mapping, the architecture permits policy differences to be interpreted against a shared representation of the transport problem.

The Site A ablation shows that explicit candidate presentation can materially change the tested LLM's behavior. Emergency duration, damage and air intervention all decrease relative to the no-table condition. This supports the value of explicit alternatives in that setting, but it does not identify a universal best representation. At B and C, the reported interface effect is weak or absent. A broader interpretation is therefore that the interface provides a common decision contract whose empirical effect depends on the policy and the choices present in the scenario.

That contract is also a modeling boundary. It determines which alternatives are exposed, how travel time is approximated and which priority restrictions apply. A more elaborate policy cannot recover an alternative excluded or inaccurately represented by this layer. Conversely, the candidate generator should not contain a hidden preference score that predetermines the nominal policy comparison. Transparency about both facts and assumptions is consequently part of the architecture's contribution.

### 7.2. Policy convergence and speed–service trade-offs

The close performance of simple and LLM policies is a substantive result. Under several tested conditions, a small number of useful alternatives leads the implementations to similar service outcomes. E3's coordinated SWL values are identical at B and C, and B2/B4b completion coincides across the E4 timing arms. These results do not establish equivalent general capabilities, but they show that greater policy complexity need not translate into a measurable transport benefit in a constrained decision setting.

Where policies differ, the difference can concern service preferences rather than feasibility. The E1 high-workload case demonstrates that a policy can accelerate an emergency already expected to meet its deadline by interrupting an incumbent mission. B2's frozen objective favors preservation in that case, while B4b sometimes favors speed. Without an agreed valuation of that exchange, the faster outcome cannot be labeled universally better. The explicit candidate interface makes the exchange visible rather than resolving it on behalf of every implementation.

Policy selection for an application would also involve reliability, explainability and processing demand. The observed backend errors belong to the LLM implementation's realized performance, and its token demand increases with input records. The experiments do not measure a complete lifecycle cost for all policies, so they do not establish a cost-optimal deployment choice. They do provide a reason to retain transparent deterministic policies as serious supervisory alternatives.

### 7.3. Surviving alternatives, network context and timely recovery

Recovery has at least three relevant stages in this system: an alternative satisfies the current constraints, an executed intervention establishes replacement service, and the service completes before its deadline. E2 shows that the second stage can succeed in every affected coordinated run while the third fails frequently. E3 shows that the benefits of coordination remain conditional as faults and task demands compound. Equation (8) expresses the temporal distinction, while the results reveal that subsequent events can further change the candidate or its command status.

The cross-site evidence suggests that transportation context influences both the size of the coordination opportunity and the importance of policy preferences. A large ground detour can make air support valuable across several policies. A viable ground path with adequate slack can instead expose a trade-off between marginal speed and service preservation. Following an air failure, a long ground alternative may restore completion but fail to prevent a late-service penalty. These mechanisms are consistent with the observed patterns without requiring a general ranking of the three city networks.

Morphology should therefore enter the interpretation through measured route and service conditions. Road density does not by itself describe a water-barrier corridor, and sampled network circuity does not uniquely describe the task's OD pair. Because geometry, facility locations, flight durations and fault phases vary together here, identifying their independent effects would require a different controlled design. The present evidence supports conditional cross-site reproduction of the manager architecture.

### 7.4. Operational timing, applicability and limitations

Observation and execution form part of the supervisory policy's operating conditions. Slower observation reduces calls but can delay both task discovery and recognition of a failed transport chain. Execution waiting consumes deadline margin and can expose a pending command to an event that changes its continuation. The D60 sequence shows that the eventual mode choice can change during this interval. Assessing the architecture solely from the instant when a valid proposal is produced would miss these effects.

These findings motivate deadline-aware observation schedules and explicit management of pending actions. Task-relevant state compression could also reduce input burden when irrelevant records accumulate. Such changes are design implications for future work, not improvements validated by the current experiment. In particular, adaptive polling and compression would require evaluation against the frozen reference conditions, rather than being assumed to preserve the reported outcomes.

The principal limitations concern service realism, decision-space coverage and external validity. The coupling abstracts physical payload transfer, mission-specific ground access and egress, detailed passenger processes and full dynamics for every aircraft class. The four-aircraft fleet and tested scenarios provide limited feasible decision diversity in several cells. B2 represents a transparent fixed-objective heuristic, rather than a strong full-horizon optimizer. SWL uses configured flat penalties and does not penalize normally ongoing services at the horizon. Consequently, its reductions should be interpreted together with deadline and completion results, rather than as comprehensive welfare gains.

The LLM evidence concerns one recorded backend and prompt family. Twenty seed realizations per primary cell provide paired comparisons over fixed scenario panels, not unrestricted sampling of operational uncertainty or cities. The inference service does not advance physical simulation time while responding; real-time wall-clock coupling remains untested. Larger active fleets, more simultaneous demands, explicit transfer processes, stronger optimization baselines and systematically controlled network changes would extend the claims. None is required to reinterpret the current results as a common supervisory architecture with conditional transport benefits.

## 8. Conclusions

This paper proposes a Ground–Low-Altitude Mobility Manager that connects a joint transport state, a manager-agnostic executable candidate interface, alternative supervisory policies, deterministic checking and execution in a SUMO–BlueSky closed loop. Its evaluation comprises 10,960 primary runs and 180 additional interface-ablation runs across ground disruptions, single air-system failures, compound disturbances and operational sensitivities.

The results show that coordination can improve emergency transport and protect priority-weighted services, while the size and form of those benefits depend on the modeled operating context. Simple coordinated policies often approach or match the LLM's outcomes. Where policies differ, faster emergency completion can involve greater damage to incumbent services. Explicit candidate presentation improves the tested LLM's decisions most clearly at one site, while supplying a common information contract for the broader policy comparison.

An executable recovery path does not ensure timely recovery. Fault exposure, surviving resources and remaining task slack determine whether reconfiguration can avert a service penalty. Observation scheduling and execution waiting can remove temporal margin or change which command reaches execution. Effective ground–low-altitude supervision therefore requires comparable transport alternatives and attention to the full observation–decision–execution sequence. The architecture provides a reproducible basis for investigating those conditions without making LLM superiority the premise of the transportation contribution.

## Data and code availability

The accompanying research package contains the original run artifacts and the frozen numerical release `paper_final_20260910`, including the authoritative results JSON, summary CSV, derived execution metrics, source/environment records and input hashes. The present manuscript and PowerPoint figures use that release without changing the raw runs, frozen policies, prompt or B2 weights. No public repository identifier is assigned in this draft. The availability statement refers to the accompanying project files rather than to an already public archive.

## References

@@REFERENCES@@

## Appendix A. Interface and implementation details

### A.1. Principal notation

| Symbol | Meaning | Unit |
|---|---|---|
| $t,\tau(t),t_e,H$ | Decision time, observation timestamp, scheduled execution and horizon | s |
| $S_t,\widehat S_t$ | Current joint state and observed state | — |
| $r_m,d_m,c_m$ | Mission release, deadline and completion | s |
| $\mathcal I_t,\mathcal C_{m,t}$ | Candidate information and legal subset | — |
| $\widehat\eta_c,\delta_{\mathrm{exec}},\sigma_m$ | Remaining completion estimate, execution delay, estimated temporal margin | s |
| $a^{\mathrm{prop}},u,Q,\Gamma$ | Proposal, executed intervention, current-version indicator, current-state checker | — |
| $J_t(c)$ | Frozen one-step heuristic score | Configured seconds-equivalent units |
| $A_i,R_i$ | Affected-chain and recovered-path indicators | Binary |
| $T_m,V_m,L_H$ | Completion duration, deadline violation, weighted service loss | s; binary; loss units |

### A.2. Structured action vocabulary

| Action | Meaning |
|---|---|
| DISPATCH | Assign an available compatible aircraft |
| REASSIGN | Transfer an eligible occupied aircraft to another mission |
| REROUTE | Change an ongoing operation's route |
| DIVERT | Change an air operation's destination or continuation |
| DELAY | Postpone an operation |
| CANCEL | Cancel a specified operation |
| RESERVE | Reserve a resource for a mission |
| RETURN | Request return by an eligible aircraft |
| LAND | Request landing under modeled constraints |
| GROUND_FALLBACK | Establish ground service for an eligible mission |
| NO_ACTION | Make no operational change at the decision epoch |
| ESCALATE | Report a need beyond the current action choice |

The vocabulary is larger than the set exercised by any single scenario. Supporting an action type in the contract does not imply that the experiments independently validate every possible use of that action. The candidate interface retains legal flags and rejection reasons, while the checker applies action-specific conditions.

### A.3. Frozen policy details

The prompt template is `manager_v2.txt`, SHA-256 `cf3a550761718d4b5ba53cd004980d795cc8e0ac9708f4284fe0f22be94f279c`. B4a and B4b use the same template, with only the candidate section withheld in B4a. B2's weight file has SHA-256 `a6e880f3c8e7398bcc2c25568141bd141be24d04eab7a8d0989cc72cacc673f6`. Its preemption penalty depends on the incumbent mission's priority. These values were not retuned for this manuscript. The backend identifier reported in Section 4.3 is preserved as provenance, not interpreted as an independently verified model-release label.

## Appendix B. Statistical and outcome conventions

### B.1. Conditional populations

Recovery outcomes apply only after the primary service chain is affected. At Site C in E2, B4b has 201 affected runs, but the B4b–B2 recovery-time comparison contains 200 jointly affected pairs. All-run completion and deadline comparisons contain 320 pairs per site. E4A OBS300 is unexposed at the time of failure and has no conditional recovery denominator. Its late completions remain in the all-run outcome analysis.

### B.2. Comparison families and missing fields

The E2 B4b–B2 family contains completion time, recovery time, failure-to-replan latency, existing-service damage, candidate-set reduction, deadline violation, recovery success, recovered-and-completed status, ground fallback, failure-induced ground fallback, necessary-ground-fallback correctness and air intervention. The candidate-count endpoint mixes occupancy and availability changes and is not used as a clean causal estimate of failure-induced candidate loss. Undefined or unavailable tests remain conservatively represented in the recorded adjustment family without turning missing effects into estimated zero effects.

E3 compound comparisons cover L2–L4, B1 and B2 as comparators, and SWL and CRITICAL+HIGH loss as endpoints. Action-level priority-consistency and resource-competition fields are unimplemented and are not analyzed as zero violations or perfect correctness. The manuscript uses observed priority-weighted outcomes instead. E4 uses separate families for each policy, metric and subexperiment, retaining the original anchors.

### B.3. Aggregate compound outcomes

@@TABLE_E3_AGG@@

These aggregate values weight scenario–seed runs equally. Because L2 and L3 each contain twice as many scenarios as L1 and L4, they contribute twice as many runs to a policy's aggregate mean. Changing to equal level weights would define a different summary and is not done here.

## Appendix C. Figure sources and reproducibility

Each of the eight figures has an editable source slide in the accompanying [PowerPoint figure file](figures/MANUSCRIPT_FIGURES.pptx). Architecture and timeline elements use native shapes and connectors, the road substrates use native vector paths derived from existing geometry, and standard result charts retain numerical series in embedded workbooks. Plotted series are rounded to eight decimal places for workbook portability; manuscript tables and inference use the frozen source values. The ablation figure uses editable points and interval segments for the frozen paired intervals. Markdown embeds PNG previews exported from these figures; the PowerPoint file preserves the vector editing source.

The figure and manuscript build files read the frozen results and site geometry. They generate document tables and presentation artifacts without invoking the managers, starting SUMO/BlueSky experiments or querying an LLM decision backend. Source citations accompany the relevant figure notes. Statistical tests are reproduced from the release outputs rather than recalculated under a new family in this draft.

The final release records an analysis environment separately from individual run configurations. Its source snapshot and SHA-256 manifests support traceability, but do not retroactively prove that every historical run used the same analysis-time environment. This distinction is retained when interpreting implementation changes and corrected derived fields.
