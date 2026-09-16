"""Rebuild the revision from the preserved current LaTeX and verified data."""
from pathlib import Path
import json,re,shutil
W=Path(__file__).resolve().parents[2];O=W/'source/revision_v3';R=W.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
D=read(O/'results_revised.json');G=read(O/'morphology_boundary.json')
main=(O/'baseline_overleaf/main.tex').read_text(encoding='utf-8')
si=(O/'baseline_overleaf/supplement.tex').read_text(encoding='utf-8')
def section(text,title,new,kind='subsection'):
    pattern=r'\\'+kind+r'\{'+re.escape(title)+r'\}\n.*?(?=\\(?:'+kind+r'|section)\{|\\section\*\{|\Z)'
    out,n=re.subn(pattern,lambda m:'\\'+kind+'{'+title+'}\n\n'+new.strip()+'\n\n',text,flags=re.S)
    assert n==1,(title,n);return out
def f(v,d=3):return f'{v:.{d}f}'
def pval(v):return f'{v:.2e}' if 0<v<.001 else f'{v:.6f}' if v<1 else '1.000'
def interval(s,d=3,mul=1):return '['+', '.join(f(x*mul,d) for x in s['ci95'])+']'
def mci(s,d=3,mul=1):return f(s['mean']*mul,d)+' '+interval(s,d,mul)
def table_rows(tex,label,rows):
    start=tex.index(r'\label{'+label+'}');a=tex.index(r'\midrule',start)+len(r'\midrule');b=tex.index(r'\bottomrule',a)
    return tex[:a]+'\n'+'\n'.join(' & '.join(map(str,row))+r' \\' for row in rows)+'\n'+tex[b:]

a=D['E1']['A']['summary']; e2=D['E2']['A']['summary']['B4b']
abstract=rf'''Low-altitude capacity alone does not ensure service resilience: an intervention must preserve useful service before its deadline margin is exhausted. We propose a Ground--Low-Altitude Mobility Manager that organizes joint ground--air states into a shared executable candidate interface. Replaceable supervisory policies select interventions using common feasibility, completion-time and incumbent-service facts, while execution checks and independent local contingencies govern their application. Four SUMO--BlueSky experiments across three contrasting transport settings examine selective air support, air failures, compound disturbances and observation--execution timing. At the meshed urban site, the fixed-objective heuristic and LLM-candidate policy both reduce emergency deadline violations from {a['B0']['critical_mission_deadline_violation']['mean']*100:.2f}\% to {a['B2']['critical_mission_deadline_violation']['mean']*100:.2f}\%, but leave {a['B2']['existing_missions_damaged_count']['mean']:.3f} and {a['B4b']['existing_missions_damaged_count']['mean']:.3f} damaged incumbent services per run, respectively. Explicit candidate-information support changes choices when faster air service competes with service preservation. Every affected coordinated run restores a path after a single air failure, yet {e2['critical_mission_deadline_violation']['mean']*100:.2f}\% of all LLM-policy runs at that site remain late. Delayed observation consumes the remaining margin, and execution waiting can change the intervention itself through command replacement. The study establishes an executable architecture for comparative service management and identifies surviving alternatives, incumbent-service costs and intervention timing as the mechanisms governing realized resilience. The management implication is to secure timely, useful reconfiguration, rather than equating available air capacity or a restored path with recovered service.'''
main=re.sub(r'\\begin\{abstract\}.*?\\end\{abstract\}',lambda m:r'\begin{abstract}'+'\n'+abstract+'\n'+r'\end{abstract}',main,flags=re.S)
intro=r'''Restoring network connectivity does not necessarily restore transport service. An urgent mission may retain a road route but lose enough time to miss its deadline. A useful response must therefore preserve completion within the remaining service margin. Reassigning a vehicle can rescue that mission while interrupting another service. This links disruption management to both deadline compliance and the distribution of service losses, consistent with performance-based transport resilience assessment. \citep{ref1}

Low-altitude resources offer a way around disrupted ground links. Their value depends on where they are, which tasks they can serve and whether they are already occupied. A faster aircraft may require preempting an incumbent service even when continued ground transport would remain timely. Communication loss, degraded navigation and unavailable landing sites can also remove the air alternative after dispatch. The relevant management problem is thus to select and execute useful cross-modal interventions as resources and deadlines evolve.

Multimodal recovery and Resilience as a Service already coordinate heterogeneous replacement services, while dynamic fleet management and truck--drone routing address evolving assignments and synchronization. \citep{ref4,ref19,ref20,ref21,ref22} Constrained-execution architectures further distinguish a proposed action from permission to apply it. \citep{ref8} We connect these ideas at the level of supervisory service reconfiguration: a failure-prone air layer supports disrupted ground services through a common interface that exposes feasible interventions and their consequences. This creates a controlled basis for comparing selection policies and tracing why an admissible replacement sometimes arrives too late.

We propose the \textbf{Ground--Low-Altitude Mobility Manager} to connect joint state observations, deterministic candidate generation, replaceable supervisory selection and common execution checks. Its \textbf{shared executable candidate interface} reports resource compatibility, legality, estimated completion and the incumbent service displaced by each option. The policy selects one intervention; the executor normalizes and validates it, then issues it or queues it for revalidation. Local contingencies operate independently. Here, global state denotes the joint state of one modeled study area. Ground service uses a SUMO corridor ETA timer; air transport evolves in BlueSky.

We make three contributions. First, we develop a ground--air supervisory service-reconfiguration architecture with explicit observation, selection and execution semantics. Second, we provide a shared executable candidate interface and comparative evidence from ground-only, air-first, fixed-objective heuristic and LLM-candidate policies. Third, we quantify transport mechanisms linking surviving alternatives, service trade-offs and observation--execution timing. Selective air support reduces missed deadlines but can displace incumbent services; restored paths can remain late; delayed execution can replace the originally selected action. Figure 1 connects these findings to E1 selective support, E2 single air failure, E3 compound disturbance and E4 timing and input burden.'''
start=main.index(r'\section{Introduction}');end=main.index(r'\begin{figure}',start)
main=main[:start]+r'\section{Introduction}'+'\n\n'+intro+'\n\n'+main[end:]
main=main.replace('Its scale is illustrative; map B1 is distinct from policy B1.','The schematic map is not to scale; map B1 is distinct from policy B1.')
main=main.replace('E1 examines air support during ground disruption','E1 examines selective air support').replace('E4 observation sensitivity with execution/input studies','E4 observation, execution and input burden')
main=main.replace('The claimed contribution is this specific architecture and its disruption evidence, rather than the general idea of multimodal recovery.','The common interface allows this failure-prone support layer to be studied through interchangeable selection policies and their executed service consequences.')
main=main.replace('Accordingly, B2 is one fixed-preference structured comparator, not a proxy for the strongest routing or scheduling optimizer.','B2 operationalizes one explicit speed--service-preservation preference through one-step candidate ranking.')
main=main.replace("Its formal guarantees do not transfer to the deterministic rule checks used here.","We adopt the proposal--execution separation and implement transport-specific deterministic rule checks.")
main=section(main,'Language models and the comparison addressed here',r'''SayCan connects language-based choices to executable robotic capabilities, while LLMLight applies language-based decisions to traffic signal control. \citep{ref9,ref10} These studies motivate an LLM as one implementation of the supervisory policy. Long-context research also distinguishes information availability from effective use. \citep{ref11}

Our comparison asks how policies use a common service-management contract and when their executed interventions protect service. B4a--B4b separately tests explicit candidate-information support within the same LLM implementation. It removes derived per-candidate facts along with their presentation, so its effect concerns information support rather than table formatting alone.''')

old='Coupling therefore occurs through task status and resource assignment.'
st=main.index(old);en=main.index(r'\subsection{',st)
main=main[:st]+r'''Coupling occurs through task status and resource assignment. A new air assignment follows the resource's current position to the mission origin and destination; an interrupted-mission candidate uses the contingency site V3 before the destination. Preemption detaches the incumbent mission and changes the resource's assignment. Local return or diversion evolves separately, but replacement dispatch is not gated by verified arrival of the original payload at V3. The registry has no payload-custody, unloading, reloading or re-shipment process. Ground fallback changes mode and schedules completion from the live corridor ETA, with the proposal ETA used only if that query is unavailable. These semantics represent service replacement, with physical transfer time examined separately through an offline margin sensitivity in Supplementary Section S4.

\begin{center}
\begin{minipage}{0.96\textwidth}
\hrule\vspace{5pt}
\textbf{Algorithm 1. Ground--air supervisory service reconfiguration}
\begin{enumerate}\setlength{\itemsep}{1pt}\setlength{\parskip}{0pt}
\item Initialize both simulators, the mission/resource registry and the observation and pending-command stores.
\item At each simulation step, apply scheduled events. Their local contingency responses run independently of supervisory inference.
\item At an event or periodic decision opportunity, observe the joint state (the latest stored snapshot in E4A); build candidate facts for the actionable mission(s).
\item Select one supervisory intervention using policy $\pi$; normalize missing route/target fields and validate its structure, semantics and modeled feasibility. Log rejected proposals.
\item Issue an accepted intervention immediately, or queue it for $t+\delta_{\rm exec}$. Keep the original due time for an identical pending command; a changed command supersedes the previous one for that mission.
\item After same-time events and their decisions, process due commands: normalize again, refresh state and revalidate. Skip completed effects; on stale rejection request a new decision; otherwise execute.
\item Advance SUMO and BlueSky by 1 s; update mission/resource states, ground completion timers and scheduled observations. Repeat until the horizon.
\end{enumerate}
\vspace{3pt}\hrule
\end{minipage}
\end{center}

Algorithm 1 follows the implemented event-before-pending order. Ordinary periodic decisions are suppressed while an actionable mission already has a pending command; E4A instead follows its scheduled polling protocol. The identical-command rule is the queue correction evaluated in Section 6.6.2; independent local contingencies do not wait for that queue.

'''+main[en:]
main=main.replace('The contract develops through additive versions. Version 2.0 supports E1, version 2.1 adds single-failure information for E2 and E4, and version 2.2 supports the multi-mission representation used in E3. Multi-mission entries are organized by priority and deadline. These are common organizational rules rather than optimizer recommendations. The policy comparison is controlled within each experiment and interface version; the full experiment sequence is not represented as having byte-identical inputs.','E2 and E4 add failure and risk-zone facts to the E1 interface. E3 extends it to multiple actionable missions organized by priority and deadline. Information derivation and execution semantics are shared across policies within each experiment.')
example=r'''\paragraph{A decision with service-preservation pressure.} At Site A, high disruption and high medical workload leave a timely ground route and one faster, preemptive air option. At 300 s in seed 20240601, the HIGH-priority emergency is due at 600 s. The logged candidates are:

\begin{center}\small
\begin{tabularx}{\textwidth}{@{}YrrYYY@{}}\toprule
Resource/mode & ETA (s) & Margin (s) & Legality & Incumbent & Preemption consequence \\\midrule
GROUND / ground & 228.617 & 71.383 & Legal & None & None \\
M-UAV-02 / air & 212.823 & 87.177 & Legal & M-L-002, NORMAL & Interrupt incumbent service \\
EVTOL-01, L-UAV-01, M-UAV-01 / air & --- & --- & Illegal & Occupied & Non-reassignable \\\bottomrule
\end{tabularx}
\end{center}

B2 selected ground and completed in 229 s; B4b reassigned M-UAV-02 and completed in 212 s, leaving one damaged incumbent service. B1 also selects the legal air option under its air-first rule. The same candidate facts support all three policies. The estimated 15.794 s air advantage improves speed, but both alternatives meet the emergency deadline and only air displaces an incumbent. Thus the fastest option can have the larger system service cost. Candidate ETA is an estimate; realized air completion also reflects simulator motion and the arrival radius.

'''
main=main.replace(r'\subsection{Supervisory policies}',example+r'\subsection{Supervisory policies}',1)
main=main.replace('under the frozen priority rule','under the priority rule').replace('Fixed-preference structured comparator','Transparent speed--service trade-off')
main=main.replace('B2 compares air and ground using the frozen score','B2 is a fixed-objective heuristic that ranks legal air and ground candidates for the priority-selected actionable mission using')
st=main.index('B2 is a fixed-preference structured comparator implemented');en=main.index(r'\subsection{Deterministic checking}',st)
main=main[:st]+r'''The weights define a fixed speed--service-preservation preference and remain unchanged across comparisons.

B4b uses the common prompt template with temperature 0, JSON output mode and an output-token budget of 8192. The recorded backend identifier is \nolinkurl{corp-ai/openai/deepseek-v4-pro}; it identifies the configured service, with the underlying release unverified. B4a retains the same snapshot, prompt rules and checker but removes the candidate section. This removes per-resource air ETA, explicit legal/rejection flags, deadline consequences and the mapped preempted-service consequence. Raw assignments, priorities, positions and ground ETA remain available. We therefore define the ablation as \emph{explicit candidate-information support}. Supplementary Section S2 supplies the field comparison and full prompt file. Recorded errors and structured retries remain in the analyzed cohort.

'''+main[en:]
main=main.replace('Consequently, a valid LLM proposal cannot be interpreted as evidence that the model itself supplied the safety mechanism, and a high task completion rate does not certify physical safety beyond the modeled constraints.','The execution layer supplies modeled feasibility enforcement for every policy; operational aviation certification lies outside this service model.')
main=main.replace('Task-specific versioning allows a newer command to supersede an earlier pending command,','Task-specific versioning allows a changed command to supersede an earlier pending command; an identical normalized command retains the original due time,')
main=main.replace('respective frozen policy definitions','respective policy definitions')

rows=[['Statistical polygon area (km$^2$)']+[f(G[s]['polygon_area_km2'],4) for s in 'ABC'],['Within-boundary road length (km)']+[f(G[s]['clipped_directional_km']) for s in 'ABC'],['Within-boundary road density (km/km$^2$)']+[f(G[s]['clipped_density']) for s in 'ABC'],['Within-boundary intersection density (km$^{-2}$)']+[f(G[s]['intersection_density']) for s in 'ABC'],['Full routing-network nodes',542,1877,791],['Full directional passenger edges',1286,3514,1681],['Full-network mean node degree','2.830','2.663','2.420'],['Full-network dead-end ratio','.1845','.1193','.2882'],['Full-network sampled OD circuity','1.1969','1.1409','1.4721'],['D1--H1 network distance (km)','2.9222','1.1192','3.4296'],['D1--H1 Euclidean distance (km)','1.7403','.7246','2.5285'],['D1--H1 circuity','1.6791','1.5446','1.3564'],['Reference closure ETA increase (\%)','37.87','88.69','34.76']]
main=table_rows(main,'tab:table3',rows)
st=main.index('Source: archived site-morphology');en=main.index('The sites offer',st)
main=main[:st]+r'''Road length is the sum of directional passenger-edge lengths apportioned by the fraction of each polyline inside the configured study polygon. Both density denominators use that polygon's projected area, approximately 10.24 km$^2$. Intersection counts include only nodes inside it, with at least three distinct neighbors in the full graph. The full routing network retains outside roads; its topology and fixed 200-pair OD sample are explicitly labeled separately. D1--H1 quantities describe the reference service pair. Supplementary Section S4 gives the boundary correction.

'''+main[en:]
main=main.replace('Site B combines the highest road density','Site B combines the highest within-boundary road density')
main=main.replace('These characteristics motivate contextual comparisons; they do not constitute a controlled experiment in which a single morphological variable changes.','These characteristics supply contrasting transport alternatives; their causal separation is discussed in Section 7.')
main=main.replace('The experiments do not claim that the modeled low-altitude service systems operate in the three cities.','These are modeled services on real road substrates.')
main=main.replace('Normally ongoing EN\_ROUTE and ASSIGNED services incur no horizon penalty.','EN\_ROUTE and ASSIGNED services incur no horizon penalty. A terminal-registry audit found all 4,320 E3 task instances with deadlines at or before the horizon completed; none were omitted as overdue ongoing tasks.')
st=main.index('For continuous endpoints, the paired difference');en=main.index(r'\subsection{Provenance and model scope}',st)
main=main[:st]+r'''The fixed scenario panel defines the estimand. Equal weights are assigned to scenario--seed runs, preserving the E3 level sample sizes of 40, 80, 80 and 40 per policy. The initialization code restarts \nolinkurl{random.Random(seed)} in each scenario, traverses aircraft in sorted order and also passes that seed to SUMO. Scenario workloads can change the number of draws, but do not establish independent streams. We therefore group the complete fixed panel by seed before estimating uncertainty and pair policies within each scenario and seed.

For a complete panel with $J$ scenarios and $K$ seeds, define
\begin{equation*}
D_s=\frac{1}{J}\sum_{j=1}^J(Y^{(u)}_{js}-Y^{(v)}_{js}),\qquad
\overline D=\frac1K\sum_sD_s,\qquad
\mathrm{CI}_{95\%}=\overline D\pm t_{0.975,K-1}\frac{s_D}{\sqrt K}.\tag{13}
\end{equation*}

Primary panels use $K=20$; the six-scenario E1 ablation uses $K=10$. Means and scenario weights are unchanged by blocking. Continuous comparisons use a paired t test on seed aggregates, with the previously specified signed-rank fallback for constant nonzero differences. Identical differences receive $p=1$. Binary comparisons swap policy labels for entire seed blocks in an exact paired randomization test, preserving within-seed dependence. This replaces run-independent McNemar inference for multi-scenario panels. Unadjusted intervals describe fixed-panel seed uncertainty; a zero-width interval means no variation across these seed aggregates. Supplementary Section S3 specifies the conditional-denominator calculation and provides the complete revised tests.

Holm adjustment retains the original comparison families: three E1 ablation endpoints per site; 12 scenario-specific E1 completion tests; 12 E2 endpoints per site; and 12 E3 compound comparisons per site. E4 retains separate per-policy, per-metric non-anchor comparisons with OBS30, D00 and N05. Adjusted $p<0.05$ is the decision criterion. \citep{ref18} The sites form separate fixed transport contexts, and nonsignificance is not statistical equivalence.

'''+main[en:]
main=section(main,'Provenance and model scope',r'''Experiments evaluate supervisory service replacement with four core aircraft, specified fault state machines and the ground timer abstraction described in Section 4.1. External inference calls do not advance physical simulation time. E4A changes observed information and E4B inserts a controlled execution wait; wall-clock backend latency is recorded separately. The numerical revision preserves original runs, corrects the B0 D60 duplicate-command cell through a local implementation overlay, and recalculates fixed-panel statistics. Supplementary materials provide parameters, prompts, analysis scripts and revision provenance.''')

main=main.replace(r'\subsection{Coordination benefit and service preservation}',r'\subsection{Selective air support and incumbent-service cost}')
main=main.replace('Their mean completion durations were comparable, but','Their mean completion durations were 147.62 and 146.63 s, respectively, but')
main=main.replace('The speed gain therefore came with a different service-preservation choice.','The speed gain therefore came from preempting a service even though ground retained a positive deadline margin. A manager must price that displacement alongside emergency speed.')
# Replace repetitive ablation plot by logged decision regimes, keeping its figure number.
fig4=r'''\begin{figure}[!htbp]
\centering
\includegraphics[width=\textwidth]{figures/fig04.pdf}
\caption{Supervisory decision regimes from E1 first-decision logs. (a) Site A candidate geometry relates the air ETA advantage to the best remaining deadline margin; symbols distinguish preemption. Repeated locations represent multiple matched states. (b) Air selections when faster air requires preemption and ground remains timely, with 20, 60 and 20 states at A, B and C. (c) Observed deadline violations among states with no candidate predicted timely: 40 at A and 27 at C per policy; B has none. First candidate snapshots match across B1, B2 and B4b in all 720 scenario--seed states. Subsequent actions and trajectories may differ. ETA-based groups are descriptive, not a new policy score.}
\label{fig:fig04}
\end{figure}'''
st=main.index(r'\begin{figure}',main.index(r'\subsection{The candidate interface'));en=main.index(r'\end{figure}',st)+len(r'\end{figure}')
main=main[:st]+fig4+main[en:]
main=main.replace('At A, explicit candidate presentation changed the tested LLM\'s behavior (Figure 4; Table 5).','Explicit candidate-information support improved both speed and service preservation at A (Table 5).')
main=main.replace('The jointly favorable changes show that faster emergency service did not require more frequent preemption in this ablation.','Completion decreased by 13.567 s, damage by 0.383 services per run and air intervention by 38.333 percentage points. These jointly favorable changes indicate more selective use of the same transport resources.')
rows=[]
for s in 'ABC':
 for z,name,mul in zip(D['E1'][s]['ablation'],['Completion (s)','Damaged services/run','Air intervention (pp)'],[1,1,100]):rows.append([s,name,z['n'],f(z['diff_mean']*mul),interval(z,3,mul),pval(z['p_holm'])])
main=table_rows(main,'tab:table5',rows)
main=main.replace('The three endpoints form one adjustment family per site. Air intervention is a paired risk difference in percentage points (pp); its interval is descriptive and its test is exact McNemar.','Each site retains a three-endpoint adjustment family. Intervals use ten seed blocks; air intervention is a risk difference in percentage points (pp) with exact whole-block label-swap inference.')
main=main.replace('The result supports a material interface effect where competing alternatives mattered in this tested LLM implementation. It does not establish a universally optimal representation or replace the primary comparison among B1, B2 and B4b.','Figure 4 explains the decision conditions. At A, 20 states offer faster preemptive air and timely ground: B1, B2 and B4b choose air in 20, zero and 12 cases. At B and C, the corresponding counts are 60/60/57 and 20/20/20, showing that a speed--service conflict does not inevitably produce policy divergence. When A has no predicted timely candidate, all 40 runs per coordinated policy are late despite different mode choices. At C, 24 of 27 such cases are late; the remaining three expose the approximation in candidate ETA. These observations connect explicit information support to decisions without equating predicted margins with guaranteed completion.')
rows=[]
for s in 'ABC':
 for z,name in zip(D['E2'][s]['b4b_vs_b2_family'][:2],['Completion (s)','Recovery time (s)']):rows.append([s,name,z['n'],f(z['diff_mean']),interval(z),pval(z['p_holm'])])
main=table_rows(main,'tab:table6',rows)
main=main.replace('95\% paired interval','95\% seed-block interval')
main=main.replace('These results retain an adverse comparison for the LLM policy while distinguishing all-run transport from conditional replacement latency.','Rapidly establishing replacement service does not remove the travel time that remains after the fault; dispatch latency and deadline performance therefore answer different operational questions.')
z3=next(z for z in D['E3']['A']['hypotheses'] if z['baseline']=='B2' and z['level']=='L3' and z['metric']=='system_weighted_loss');z4=next(z for z in D['E3']['A']['hypotheses'] if z['baseline']=='B2' and z['level']=='L4' and z['metric']=='system_weighted_loss')
main=main.replace('+1.6875 (95\% CI -1.671 to 5.046) and +3.375 (-3.452 to 10.202)',f"+1.6875 (95\\% CI {interval(z3)}) and +3.375 ({interval(z4)})")
main=main.replace('This supports comparable aggregate performance in these panels without establishing statistical equivalence or identical action sequences.','The transport benefit follows the surviving deadline-compatible alternatives, while policy differences contribute little additional protection in these panels.')
main=main.replace('The result belongs to the tested event order and queue rules, rather than a universal delay threshold.','After correcting identical-command replacement, B0 instead executes its ground command at 360 s and completes at 542 s: 242 s from release. Its original 302 s duration included an unintended second 60 s wait. All 20 B0 D60 runs reproduce the correction; D00 and D30 controls retain 182 and 212 s, and neighboring fault times retain 242 s. Figure 8 distinguishes this corrected ground-only sequence from B4b\'s genuine air-to-ground replacement. These are effects of the specified event order and command semantics.')
main=main.replace('E4B D60 command sequence for B4b.','E4B D60 command sequences after identical-command deduplication.')
main=main.replace('The transition changes the executed mode as well as completion time.','Dashed lines denote pending commands and solid lines actual transport. Corrected B0 ground service executes at 360 s and completes at 542 s; B4b changes mode and completes at 602 s.')
main=main.replace('This is not evidence that smaller inputs are inherently harder.','The difference follows a retained transport error and subsequent decision opportunity.')

discussion=r'''\subsection{An executable service-management architecture}

We develop the Manager as a transport method whose decision object is a service intervention. Joint state becomes useful only when linked to a compatible resource, an executable action and a completion estimate. The candidate interface makes that link explicit and carries incumbent-service consequences into selection. Common checking and execution let researchers compare policy preferences without changing the underlying transport contract. This extends multimodal recovery and dynamic fleet management to a failure-prone ground--air service system. \citep{ref4,ref20,ref22}

The comparison shows why a replaceable policy layer is useful. Deterministic and LLM policies often obtain similar outcomes because the surviving alternatives strongly constrain what can be achieved. Where timely ground competes with faster preemptive air, policies can express different service preferences. B2 makes its valuation explicit through fixed weights; B4b sometimes exchanges incumbent preservation for additional emergency speed. The Manager exposes that exchange so an operator can evaluate it against service obligations.

\subsection{Useful alternatives and the remaining service margin}

Low-altitude capacity yields resilience when it supplies a useful alternative that can be executed in time. E1 demonstrates the bypass benefit and the cost of reallocating occupied aircraft. E2 separates successful path restoration from timely completion. E3 shows how surviving options protect priority-weighted services, while exhausted alternatives leave the same loss across policies. Together these findings connect network recovery to the service outcomes that motivate intervention. \citep{ref1,ref3}

The decision-log analysis identifies contrasting operating conditions. Clear speed and service-preservation advantages tend to align choices; smaller speed gains with preemption expose preferences; negative predicted margins identify services that are difficult to rescue. Predictions remain approximate, as Site C's few timely completions despite negative candidate margins illustrate. The interface must therefore expose the provenance of ETA and service consequences, and timing estimates must be interpreted together with realized trajectories.

Transfer sensitivity reinforces this mechanism. In the offline replacement analysis, Site B's timely affected services retain only 19 s of margin. A 30 s handover assumption makes 80 previously timely services per coordinated policy late. Site A's deterministic replacements retain 60 s, while a small number of LLM trajectories are closer to the deadline. This does not alter the observed path-restoration result, but it makes physical transfer timing central to deploying the architecture.

\subsection{Observation and execution are management decisions}

Observation scheduling determines when a mission or fault enters the decision state. Pending-command semantics determine whether an accepted intervention reaches execution before circumstances change. E4 demonstrates both mechanisms: sparse observation can exhaust the deadline, and waiting can allow a fault to replace an air command with ground service. The B0 duplicate-command correction removes an implementation-induced delay and leaves the substantive air-to-ground replacement mechanism intact. A practical Manager needs deadline-aware observation and idempotent handling of repeated commands, in addition to a capable selection policy.

Explicit candidate information also imposes computational input demand. B4a--B4b measures the support supplied by derived candidate facts, while E4C measures input burden around a fixed active fleet. These results guide interface design and policy selection together: the available facts should make consequential choices comparable without obscuring them in unnecessary records.

\subsection{Scope and next steps}

The evidence concerns fixed, site-adapted scenario panels and a four-aircraft core fleet. Road morphology varies together with facility placement, flight distance and fault timing. Ground service uses a corridor ETA timer, and the registry abstracts payload custody and transfer synchronization; offline added-time sensitivity does not re-optimize a closed loop. Faults and feasibility checks implement specified service-level rules. SWL uses configured flat penalties, and incumbent damage is a final-state count. The tested LLM is one recorded backend and prompt family, with wall-clock inference decoupled from simulated transport. Next steps are task-specific ground and payload-transfer models, closed-loop transfer-delay experiments, larger active fleets and controlled variation of transport geometry. These extensions would test operational generalization of the mechanisms established here.'''
st=main.index(r'\section{Discussion}');en=main.index(r'\section{Conclusions}',st)
main=main[:st]+r'\section{Discussion}'+'\n\n'+discussion+'\n\n'+main[en:]
main=section(main,'Conclusions',r'''We propose a Ground--Low-Altitude Mobility Manager that connects joint transport observations to executable service reconfiguration. Its shared candidate interface makes feasibility, remaining time and incumbent-service consequences comparable across replaceable supervisory policies. The closed-loop experiments demonstrate selective air-support benefits, expose speed--service-preservation trade-offs and distinguish path restoration from timely service recovery.

Low-altitude capacity alone does not ensure resilience. Its value depends on selecting and executing useful cross-modal interventions before the remaining service margin is exhausted. Surviving alternatives define what can be rescued, service preferences determine which trade-offs are accepted, and observation--execution timing determines whether the selected intervention takes effect. The Manager provides a concrete architecture and comparative evidence for managing these dependencies.''',kind='section')
st=main.index(r'\section*{Data and code availability}');en=main.index(r'\bibliographystyle',st)
main=main[:st]+r'''\section*{Data and code availability}

The accompanying local research package contains run artifacts, experiment configurations, prompt files, analysis scripts, revised figure data and an executable queue-correction overlay. Supplementary Section S6 identifies the files and reproduction commands. Original data and the previous manuscript version are retained separately. A public repository identifier has not yet been assigned.

'''+main[en:]
main=main.replace('frozen','specified').replace('Frozen','Specified')

# Supplement tables use revised seed-block intervals; conditional counts stay exact.
rows=[]
for s in 'ABC':
 for m,z in D['E1'][s]['summary'].items():rows.append([s,m,z['n'],mci(z['critical_mission_completion_time_s'],2),mci(z['critical_mission_deadline_violation'],2,100),mci(z['existing_missions_damaged_count'])])
si=table_rows(si,'tab:S1',rows)
rows=[]
for s in 'ABC':
 for m,z in D['E2'][s]['summary'].items():rows.append([s,m,z['n'],mci(z['critical_mission_completion_time_s'],2),f(z['critical_mission_deadline_violation']['mean']*100,2),'N/A' if not z['affected_n'] else f"{z['recovered_n']}/{z['affected_n']}",'N/A' if not z['affected_n'] else '100.00'])
si=table_rows(si,'tab:S2',rows)
si=si.replace('Recovery (\%), Wilson interval','Restoration (\%)')
rows=[]
for s in 'ABC':
 for m,z in D['E3'][s]['summary'].items():rows.append([s,m,z['n'],mci(z['critical_mission_completion_time_s'],2),f(z['critical_mission_deadline_violation']['mean']*100,2),mci(z['system_weighted_loss'])])
si=table_rows(si,'tab:S7',rows)
si=si.replace('60 & 302.0 & 341.0 & 302.0 & 302.0','60 & 242.0 & 341.0 & 302.0 & 302.0')
si=si.replace('These tables retain the frozen results relocated from the main article. Table and figure captions in the main article identify the relevant populations. No experiments or statistical tests were rerun.','These tables report the revised numerical analysis. Means preserve the original fixed scenario weights. Intervals use seed blocks, and B0 D60 incorporates the closed-loop duplicate-command correction. Original data and earlier tables remain in the version archive.')
si=si.replace('Completion and damage use t intervals; deadline proportions use Wilson intervals. Each site--policy cell has 240 runs. These intervals characterize the fixed panel, not a population of cities.','Completion, damage and deadline-rate intervals use 20 seed blocks. Each block averages the same 12 scenarios. Zero-width intervals indicate no seed-to-seed variation in that fixed-panel average; they do not establish a universal rate. Each site--policy cell contains 240 runs.')
si=si.replace('Recovery intervals are Wilson intervals.','Restoration is reported as observed recovered/affected counts; no independent-run Wilson interval is assigned to this dependent multi-scenario population.')
si=si.replace('Interface and frozen implementation details','Interface and implementation details').replace('Frozen policy details','Policy inputs and parameters')
st=si.index(r'\subsection{Policy inputs and parameters}');en=si.index(r'\section{Statistical',st)
si=si[:st]+r'''\subsection{Policy inputs and parameters}

The complete template is supplied as \nolinkurl{reproducibility/prompts/manager_v2.txt}; the input renderer and action schema accompany it. B4a and B4b both use the full global snapshot excluding the \nolinkurl{candidates} field. B4b appends that field as a separate JSON section, while B4a omits it. Both retain raw resource state, mission assignments, priorities, positions, deadlines, ground ETA, prompt rules and the common checker. Only B4b receives the derived air ETA, completion prediction, per-candidate legality/rejection reason and explicit preempted-mission mapping. The ablation therefore measures explicit candidate-information support, jointly including information derivation and presentation.

\begin{table}[H]\centering\small
\caption{Input-field comparison for the E1 ablation.}\label{tab:S10}
\begin{tabularx}{\textwidth}{@{}Yll@{}}\toprule
Field & B4a & B4b \\\midrule
Raw aircraft and mission state; ground ETA & Included & Included \\
Rules, objectives, output schema, checker & Same & Same \\
Derived candidate air ETA and completion time & Omitted & Included \\
Per-candidate legal flag and rejection reason & Omitted & Included \\
Predicted deadline violation and preemption consequence & Omitted & Included \\\bottomrule
\end{tabularx}\end{table}

\begin{table}[H]\centering\small
\caption{Key operational and analysis parameters.}\label{tab:S11}
\begin{tabularx}{\textwidth}{@{}lY@{}}\toprule
Parameter & Value or implemented rule \\\midrule
Core fleet & Two medical UAVs, one logistics UAV, one passenger eVTOL \\
Cruise speed & Medical/logistics 15 m/s; passenger 40 m/s; inspection role 10 m/s (no core inspection aircraft) \\
Nominal altitude & UAV 328 ft; passenger eVTOL 656 ft \\
Arrival radius & 100 m; this can make realized duration shorter than geometric ETA \\
Dispatch overhead & 0 s in candidate estimates \\
Endurance & Initial 1,800 s, reduced by a seeded 0--15\%; candidate reserve margin 60 s \\
Busy-aircraft progress & Seeded fraction 0.05--0.40 of its initial route \\
Simulation step / ordinary decision period & 1 s / 30 s while actionable; E4A overrides observation polling \\
Simulation horizon / primary emergency release & 900 s (E3 L3/L4: 1,200 s) / 300 s \\
E1 deadline slack & HIGH 300 s; CRITICAL 180 s \\
E2/E4 primary deadline & 480 s at Site A; site-adapted configurations accompany the data \\
Incumbent default deadline & 1,800 s for initial background missions \\
Ground completion & Execution-time SUMO D1--H1 ETA rounded to seconds, added to issue time \\
LLM decoding & Temperature 0; JSON output; 8,192 output-token budget \\
SWL priority weights & CRITICAL/HIGH/NORMAL/LOW: 4/3/2/1; penalties are task-specific flat values \\\bottomrule
\end{tabularx}\end{table}

B2 weights and the prompt template are unchanged. Mission-specific delay and cancellation penalties, secondary releases, workload assignments and site adaptations are specified in the supplied YAML matrices. The policy identifier records the configured backend service; no unverified underlying model-version claim is made.

'''+si[en:]
st=si.index(r'\section{Statistical and outcome conventions}');en=si.index(r'\section{Additional timing',st)
stats_text=r'''\section{Statistical and outcome conventions}

\subsection{Fixed-panel estimand and random streams}

The runner initializes a fresh \nolinkurl{random.Random(seed)} for every scenario. Aircraft are visited in sorted order; every aircraft consumes an endurance draw and each busy aircraft an additional progress draw. The same SUMO seed is also reused. Workload-dependent draw consumption changes realizations, but does not create independently keyed scenario streams. We retain dependence within each seed across the fixed scenario panel and pair policies by scenario and seed. This choice follows implementation, not seed labels or state hashes alone.

For a complete panel, each seed contributes the average of its scenario-specific outcomes or paired differences. Means retain equal scenario--run weights. A t interval uses the standard deviation across 20 seed averages (10 in the E1 ablation). For a conditional endpoint with $N$ retained pairs, let $\bar d$ be the original pair-weighted mean and $K$ the number of represented seeds. The cluster contribution is
\[
B_s=\bar d+\frac{K}{N}\sum_{i:\,s_i=s}(d_i-\bar d).
\]
The interval is $\bar d\pm t_{.975,K-1}\operatorname{sd}(B_s)/\sqrt K$. This preserves the jointly affected pair-weighted estimand instead of silently reweighting seeds with different exposure counts. Conditional populations remain policy-dependent: at Site C, B4b has 201 affected runs and the B4b--B2 recovery comparison retains 200 jointly affected pairs.

Continuous tests use these seed contributions with the original constant-difference signed-rank fallback. Binary tests enumerate policy-label swaps of whole seed blocks; the test statistic is the total discordant paired difference. This retains the paired design while replacing an independent-pair McNemar assumption. No scenarios, endpoints or correction families are selected according to their p-values. Intervals are unadjusted; Holm-adjusted p-values retain the original three E1 ablation, 12 E2 and 12 E3 compound endpoints per site. E1 scenario-specific and E4 single-scenario comparisons retain their original seed units. The E2 family includes completion, recovery time, replan latency, incumbent damage, candidate reduction, deadline violation, restoration, recovered completion, ground fallback, failure-induced fallback, necessary-fallback correctness and air intervention. E3 compares B4b with B1/B2 at L2--L4 for SWL and CRITICAL+HIGH loss.

\input{reproducibility/statistical_tests.tex}

\subsection{Service-loss audit}

All 2,880 E3 run registries were checked against their run-specific horizons: 900 s for L1/L2 and 1,200 s for L3/L4. At each site, 1,440 task instances had deadlines at or before the horizon, and all were COMPLETED. Across sites, zero overdue tasks remained EN\_ROUTE or ASSIGNED. Thus no SWL correction or overdue-task penalty sensitivity is needed for this dataset. Background missions with 1,800 s deadlines are not treated as failures merely for remaining in service at the end of a 900 or 1,200 s run. Incumbent damage remains a count of damaged final states, not an accumulated interruption duration.

'''
si=si[:st]+stats_text+si[en:]
st=si.index(r'\section{Additional timing');en=si.index(r'\section{Figure production',st)
si=si[:st]+r'''\section{Technical checks and timing sensitivity}

\subsection{Duplicate pending commands and E4B regression}

The original B0 D60 action pipeline records GROUND\_FALLBACK at 300 s, due at 360 s. The 360 s fault invokes a new decision with the identical normalized action and identical 181.763 s ETA field. The original queue replaces the first command, restarts the 60 s wait, issues at 420 s and completes at 602 s. This caused the original 302 s completion duration.

The revision preserves the original due time when a validated normalized action exactly matches a pending one. It continues to supersede a pending command when the action changes, and revalidates the surviving command at execution. The correction is implemented in \nolinkurl{queue_fix.py}, as an overlay without altering original project source or raw runs. All 20 B0 D60 seeds were rerun through SUMO--BlueSky: issue at 360 s, completion at 542 s, duration 242 s. Single-seed D00/D30 controls retain 182/212 s; fault times 359/361 s both give 242 s. B2's changed air-to-ground command retains a 302 s duration. B1 retains its air-to-air replacement sequence; patched and unpatched control reruns both give 342 s in the current runtime, versus the archived 341 s, a 1 s runtime reproduction difference unrelated to deduplication. Its archived cell is retained because the correction does not change its command sequence. No LLM calls were made in these regressions; original B4b traces contain genuine command replacement and remain unchanged.

Table S5 and Figures 7--8 replace the affected B0 cell only. D60 is an evaluated event-order configuration, not a universal transport-delay threshold. External backend wall time remains separate from controlled simulation waiting.

\subsection{Physical transfer semantics and offline added-time sensitivity}

The model replaces a service assignment; it does not track an individual payload. New air candidates route through the mission origin. Interrupted-service candidates route through V3 before the destination, but a backup can be dispatched before the original carrier has reached V3. Preemption interrupts and detaches the incumbent mission. Ground takeover establishes a service timer using the current reference corridor ETA. There is no explicit unloading, rendezvous, loading, new inventory or re-shipment state.

We therefore evaluate added transfer time as an \emph{offline trajectory-fixed sensitivity}, not a new closed-loop experiment. For an actually affected E2 mission with a post-failure DISPATCH, REASSIGN or GROUND\_FALLBACK, add one hypothesized transfer delay $h$ to its recorded completion. The same rule applies to every policy; uninterrupted services receive no added time. A previously timely completion changes status when $0\le d_m-c_m<h$. Choices, fault exposure and later scheduling are held fixed. Values $h=15,30,60$ s are illustrative assumptions, not measured handling durations.

\input{reproducibility/transfer_sensitivity.tex}

At Site B, 80 affected replacements per coordinated policy are timely with 19 s remaining; a 30 s addition makes all 80 late. At A, B1/B2 timely replacements have 60 s remaining and none flips for $h\le60$ s; B4b has one flip at 15/30 s and two at 60 s. At C, affected replacements in this subset are already late. For the preemption example in Section 4.2, 17 s of extra air-specific handling erases the realized 212 versus 229 s speed advantage; more than 88 s also loses its emergency deadline. Adding the same handling time to both initial alternatives preserves their speed difference, so this threshold applies specifically to an additional preemption step. These checks show which conclusions depend on omitted stages; they do not verify dynamic rescheduling with payload transfer.

\subsection{Road-statistics boundary}

The original morphology routine summed all imported passenger edges while dividing by 10.24 km$^2$, without clipping to its bbox argument. The revised lengths intersect every edge polyline with the configured geographic rectangle projected through the SUMO network transform. SUMO edge lengths are apportioned by the clipped polyline fraction. Density uses that same polygon's area. Intersection counts retain nodes within the polygon and count distinct neighbors in the full graph, avoiding artificial boundary intersections. Original full-network topology, OD samples and routing remain separately identified and unchanged. Site C still has higher intersection density than A; its description relies on dead ends, degree, circuity and facility distance.

\subsection{Fault state machines and recovery conditions}

\begin{table}[H]\centering\footnotesize
\caption{Six modeled fault families. Exact targets, geometry, times and windows are supplied in the YAML matrices.}\label{tab:S14}
\begin{tabularx}{\textwidth}{@{}lYYY@{}}\toprule
Fault & Trigger and state change & Independent local response & Service-recovery condition \\\midrule
F1 C2 loss & Target becomes non-commandable, non-reassignable and CONTINGENCY; mission interrupted & Return to V3 & Surviving compatible backup or ground; lost target remains excluded \\
F2 GNSS degradation & One-shot test of aircraft inside configured zone; GNSS DEGRADED & Occupied affected aircraft abandon mission and divert to V3 & Alternative with acceptable navigation and landing state; zone alone does not block other routes \\
F3 UTM change & DEGRADED blocks new noncritical air assignments; OUTAGE blocks all new air & OUTAGE interrupts in-flight missions and diverts them to V3 & Ground during outage; otherwise an eligible air assignment \\
F4 Landing closure & Configured site becomes unavailable; missions to it interrupted & Affected aircraft divert to V3 & Available compatible destination/continuation or ground \\
F5 Unknown aircraft & Prescribed noncooperative trajectory and temporary risk zone; affected missions interrupted & Commandable affected aircraft divert to V3 & Aircraft and route outside active zone, or ground; zone expires at configured end \\
F6 Flyaway & Target becomes uncontrolled and non-commandable; surrounding envelope can interrupt others & Target follows prescribed uncontrolled trajectory; other commandable affected aircraft divert & Exclude target and active envelope; use surviving air or ground \\\bottomrule
\end{tabularx}\end{table}

Zone applicability is evaluated at decision and execution, with configured active windows. C2/GNSS/UTM and landing changes are not automatically repaired during these runs. Recovery denotes establishing replacement service, not repairing the original aircraft or infrastructure.

'''+si[en:]
si=si.replace('Its map, scale and four findings are schematic.','Its map is marked Not to scale and its finding graphics are schematic.')
si=si.replace('All scientific labels and claims were checked against the frozen reports.','The retained illustration records identify the imagegen tool; no unverifiable model-release version is assigned.')
st=si.index('Figures 2--8 were restyled');en=si.index(r'\FloatBarrier',st)
si=si[:st]+r'''Figures 2--8 preserve the native PowerPoint workflow: vector map routes, editable labels, charts and embedded numerical workbooks. Figure 4 now shows logged decision regimes. Figure 7 uses revised B0 D60 completion; Figure 8 separates pending and executed transport. Figure 1 uses a measured candidate example, simulator-to-state feedback and an independent-contingency label. The complete figure remains a composition of editable objects and retained illustration assets.

\section{Reproduction files and entry points}

The local package has not been assigned a public repository URL. From the parent project root, run \nolinkurl{python 新方向手稿/source/revision_v3/analyze_revision.py} to reproduce the fixed-panel statistics and decision/transfer data; \nolinkurl{morphology_boundary.py} reproduces clipped statistics. Paths with non-ASCII directory names are given in the accompanying README and shell script. \nolinkurl{run_regression.py} executes only the documented small deterministic regression set. It does not call the LLM. The regression overlay imports the original runner and changes only identical pending-command handling.

The \nolinkurl{reproducibility/} directory supplies the full prompt, candidate renderer, schemas, B2 weights and experiment/site YAML configuration files. A file inventory identifies original run directories and the corrected E2 execution-metric inputs. \nolinkurl{results_revised.json} is the revised figure/table data source; \nolinkurl{all_metrics.json}, \nolinkurl{decision_regimes.json} and \nolinkurl{transfer_margins.json} expose the derived observations. Original metrics and the previous 25-page/6-page manuscript are preserved separately. Hashes accompany the files for verification, alongside the parameters and executable scripts. Build the article with pdfLaTeX, BibTeX and two further pdfLaTeX passes; build the supplement with two pdfLaTeX passes. Editable figure builders and their PowerPoint export script accompany the source package.

'''+si[en:]
# Avoid non-ASCII paths in pdfLaTeX body; exact executable paths live in README.
si=si.replace('python 新方向手稿/source/revision_v3/analyze_revision.py','python source/revision_v3/analyze_revision.py')
si=si.replace('frozen','specified').replace('Frozen','Specified')
(W/'overleaf/main.tex').write_text(main,encoding='utf-8');(W/'overleaf/supplement.tex').write_text(si,encoding='utf-8')

rep=W/'overleaf/reproducibility';rep.mkdir(exist_ok=True)
def tex_table(caption,label,head,rows,spec):
 return '\n'.join([r'\begin{table}[H]\centering\footnotesize',r'\caption{'+caption+'}'+r'\label{'+label+'}',r'\begin{tabularx}{\textwidth}{@{}'+spec+r'@{}}\toprule',' & '.join(head)+r' \\\midrule',*[' & '.join(map(str,row))+r' \\' for row in rows],r'\bottomrule\end{tabularx}\end{table}'])
rows=[]
for s in 'ABC':
 for t in D['E2'][s]['b4b_vs_b2_family']:
  short={'critical_mission_completion_time_s':'Completion','recovery_time_s':'Recovery time','failure_to_replan_latency_s':'Replan latency','existing_missions_damaged_count':'Damage','candidate_set_reduction_delta':'Candidate reduction','critical_mission_deadline_violation':'Deadline risk','recovery_success':'Restoration','recovered_completed':'Recovered/completed','ground_fallback_rate':'Ground fallback','failure_induced_ground_fallback':'Failure fallback','necessary_ground_fallback_correct':'Necessary fallback','air_intervention':'Air intervention'}[t['metric']]
  rows.append([s,short,t['n'],f(t['diff_mean']) if t['diff_mean'] is not None else 'N/A',interval(t) if t['diff_mean'] is not None else 'N/A',pval(t['p_holm'])])
# Split by site to avoid an over-height float.
stats_tex='\n'.join(tex_table('Complete E2 seed-block comparison family, Site '+s+'. Differences are B4b minus B2; binary differences are fractions.',f'tab:e2_{s}',['Site','Endpoint','Pairs','Difference','95\% interval','Holm p'],[r for r in rows if r[0]==s],'lYrrYr') for s in 'ABC')
rows=[]
for s in 'ABC':
 for t in D['E3'][s]['hypotheses']:
  if t['metric']!='system_weighted_loss':continue
  rows.append([s,t['level'],t['baseline'],t['n'],f(t['diff_mean']),interval(t),pval(t['p_holm'])])
stats_tex+='\n'+tex_table('E3 compound SWL comparisons. CRITICAL+HIGH differences and tests are identical in these cells; both endpoints remain in each 12-test family.','tab:e3_tests',['Site','Level','Base','Pairs','Difference','95\% interval','Holm p'],rows,'lllrrYr')
(rep/'statistical_tests.tex').write_text(stats_tex,encoding='utf-8')
T=read(O/'transfer_summary.json');rows=[]
for s in 'ABC':
 for m in ['B1','B2','B4b']:
  t=T[s+'_'+m];rows.append([s,m,t['n_replacements'],t['on_time'],t['additional_late']['15'],t['additional_late']['30'],t['additional_late']['60']])
(rep/'transfer_sensitivity.tex').write_text(tex_table('Offline added transfer time: number of previously timely E2 replacements becoming late.','tab:transfer',['Site','Policy','Replacements','Timely','+15 s','+30 s','+60 s'],rows,'llrrrrr'),encoding='utf-8')
print('Rewritten main.tex and supplement.tex; data-driven tables generated.')
