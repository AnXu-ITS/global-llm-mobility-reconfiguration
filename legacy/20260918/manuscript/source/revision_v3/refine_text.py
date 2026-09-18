from pathlib import Path
import json,re,shutil,hashlib
W=Path(__file__).resolve().parents[2];R=W.parent;O=W/'source/revision_v3';ov=W/'overleaf'
m=(ov/'main.tex').read_text(encoding='utf-8');s=(ov/'supplement.tex').read_text(encoding='utf-8')
# Loading float before hyperref avoids duplicate anchors on [H] tables.
s=s.replace('amsmath,amssymb,booktabs,array,tabularx,hyperref,natbib,float','amsmath,amssymb,booktabs,array,tabularx,float,natbib,hyperref')
s=s.replace('recovered/affected counts; no independent-run Wilson interval is assigned to this dependent multi-scenario population.','recovered/affected counts. The fixed-panel dependence is retained without an independent-run Wilson interval.')
s=s.replace('Incumbent damage remains a count of damaged final states, not an accumulated interruption duration.',r'''Incumbent damage remains a count of damaged final states. As a complementary E1 measure, the recorded preemption time was linked to the incumbent identified in the candidate log and its final interrupted state. The preemption-to-horizon exposure of these persistently interrupted services averages 35 s per run for B2 and 80 s for B4b at A (B1: 300 s). This is horizon-truncated exposure, not a complete cumulative interruption-cost measure. Mission CSV records omit some incumbent preemption transitions, so zero logged interruption duration would be misleading. Initial incumbent deadlines are 1,800 s, beyond the 900 s horizon; no incumbent lateness claim is inferred from this exposure.''')
s=s.replace('non-commandable, non-reassignable and CONTINGENCY','non-commandable and in CONTINGENCY')
s=s.replace('From the parent project root, run','From the manuscript directory, run')
s=s.replace('C2/GNSS/UTM and landing changes are not automatically repaired during these runs.','Communication, navigation, UTM and landing-site states are not automatically repaired during these runs.')
m=m.replace("Its matched comparison with B4b concerns the presentation of candidate facts within this LLM implementation.","Its matched comparison with B4b concerns explicit candidate-information support.")
m=m.replace('full descriptive results and Wilson recovery intervals','full descriptive results and exact restoration counts')
# Figure 4 now displays mechanism observations, not the old interval plot.
m=m.replace('The effect was site-dependent. B showed no difference passing Holm adjustment, and C had zero observed difference on all three endpoints.','The information-support effect was site-dependent: B had no difference passing Holm adjustment and C had zero difference on all three endpoints.')
# Make the grounded decision-regime contrast precise, including the air-first exception.
m=m.replace('Figure 4 explains the decision conditions.', 'Figure 4 relates choices to ETA advantage, deadline margin and preemption. When ground is both faster and non-preemptive, it dominates those two service criteria; B1 can still prefer air because its rule ranks only air candidates. This explains why candidate availability alone does not ensure a useful selection.')
m=m.replace(r'\paragraph{A decision with service-preservation pressure.}',r'\noindent\textbf{A decision with service-preservation pressure.}')
m=m.replace('Resource/mode & ETA','Resource / mode & ETA')
m=m.replace(' It is not a fitted transition model or a proof of closed-loop stability.','')
m=m.replace('Equation (8) organizes the interpretation of the experiments; it does not introduce a newly measured candidate-count endpoint or a continuous delay threshold.','Equation (8) connects candidate facts to the decision regimes analyzed in Figure 4.')
m=m.replace('The difference follows a retained transport error and subsequent decision opportunity. ','')
m=m.replace('B2 and B4b overlap in panels (a,b).','B2 and B4b overlap in panels (a,b); B1 also overlaps with them at 0--30 s in panel (b).')
s=s.replace('Its map is marked Not to scale and its finding graphics are schematic.','Its map is marked Not to scale and its finding graphics are schematic. A later author-edited PowerPoint removed the duplicate figure title and adjusted module labels; these edits are retained in the revision.')
st=s.index(r'\section{Reproduction files and entry points}');en=s.index(r'\FloatBarrier',st)
s=s[:st]+r'''\section{Reproduction files and entry points}

No public repository URL is assigned. The accompanying \nolinkurl{REPRODUCTION_README.md} and \nolinkurl{reproduce_analysis.ps1} provide original run locations, dependencies and executable processing order. The \nolinkurl{reproducibility/} folder contains prompts, schemas, weights, experiment configurations, derived data and a hashed file inventory. The local correction overlay and optional regression entry point are included; the regression makes no LLM calls. Editable figure builders and PowerPoint sources accompany the LaTeX package.

'''+s[en:]
(ov/'main.tex').write_text(m,encoding='utf-8');(ov/'supplement.tex').write_text(s,encoding='utf-8')
rep=ov/'reproducibility'
files=['prompts/manager_v2.txt','schemas/manager_action_v1.schema.json','managers/llm_manager.py','orchestrator/candidate_info.py','orchestrator/candidate_info_e2.py','orchestrator/candidate_info_e3.py','orchestrator/experiment4_runner.py','orchestrator/experiment1_runner.py','orchestrator/registry.py','orchestrator/phase2_orchestrator.py','orchestrator/phase3_orchestrator.py','failures/e2_failures.py','config/experiment1_b2_weights.yaml','config/experiment1_final_matrix.yaml','config/experiment1_final_seeds.yaml','config/experiment2_matrix.yaml','config/experiment3_matrix.yaml','config/experiment4_matrix.yaml','config/experiment4_seeds.yaml','config/scenario_config.yaml','config/site_b_amsterdam_config.yaml','config/site_c_edmonton_config.yaml']
files += [str(p.relative_to(R)) for p in (R/'config').glob('*site*matrix.yaml')]
files += [str(p.relative_to(R)) for p in (R/'config').glob('experiment[23]*.yaml')]
inventory=[]
for rel in sorted(set(files)):
 p=R/rel
 if not p.exists():continue
 dest=rep/rel;dest.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(p,dest)
 inventory.append({'path':rel,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(rep/'file_inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
for name in ['results_revised.json','all_metrics.json','decision_regimes.json','regime_summary.json','transfer_margins.json','transfer_summary.json','morphology_boundary.json','initial_evidence.json','persistent_interruption_duration.json','e4_run_metrics_revised.json']:
 shutil.copy2(O/name,rep/name)
# Transfer time and mean tables remain generated from the numerical files.
print('Text refinements and supporting files synchronized.')
