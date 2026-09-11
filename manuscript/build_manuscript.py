"""Build the venue-neutral manuscript and figures from the frozen paper release."""
from pathlib import Path
import csv
import hashlib
import json
import re
import shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
FIG = HERE / 'figures'
FIG.mkdir(exist_ok=True)
DATA = ROOT / 'outputs/paper_final/results.json'
R = json.loads(DATA.read_text(encoding='utf-8'))
MANAGERS = ['B0', 'B1', 'B2', 'B4b']
COLORS = ['#8c969f', '#e6a04b', '#497ca5', '#237f72']
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'svg.fonttype': 'none', 'pdf.fonttype': 42})

def save(fig, name):
    for ext in ['png', 'svg', 'pdf']:
        fig.savefig(FIG / f'{name}.{ext}', dpi=220, bbox_inches='tight', facecolor='white')
    plt.close(fig)

fig, ax = plt.subplots(figsize=(12, 5.2))
ax.set(xlim=(0, 12.2), ylim=(0, 4.8)); ax.axis('off')
boxes = {
    'sim': (0.15, 3.1, 3.15, 1.35, 'COUPLED ENVIRONMENT\nSUMO roads + BlueSky air\nMissions, sites, disturbances\n1 s simulation clock'),
    'state': (4.5, 3.1, 3.15, 1.35, 'GLOBAL SNAPSHOT\nGround ETA and closures\nAir availability and endurance\nMission priority and deadline'),
    'cand': (8.85, 3.1, 3.15, 1.35, 'SHARED CANDIDATES\nLegal air and ground options\nETA, preemption, margins\nNo policy-specific ranking'),
    'policy': (8.85, 0.35, 3.15, 1.5, 'SUPERVISORY DECISION\nB0 ground / B1 air-first\nB2 objective / B4b LLM\nOne structured action'),
    'exec': (4.5, 0.35, 3.15, 1.5, 'CHECK AND EXECUTION\nValidate state and identifiers\nIssue or queue an action\nSupersede or reject if needed'),
    'local': (0.15, 0.35, 3.15, 1.5, 'LOCAL CONTINGENCY\nAircraft-level failure handling\nIndependent of the supervisor'),
}
for key, (x,y,w,h,label) in boxes.items():
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.06',
                 facecolor='#eaf3f2' if key in ['cand','policy'] else '#f1f3f6',
                 edgecolor='#356572',linewidth=1.3))
    ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=9.5,linespacing=1.65)
def arrow(a,b,**kw):
    ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',color='#356572',lw=1.6,**kw))
for a,b in [((3.3,3.77),(4.5,3.77)),((7.65,3.77),(8.85,3.77)),
            ((10.43,3.1),(10.43,1.85)),((8.85,1.1),(7.65,1.1)),
            ((5.05,1.85),(2.8,3.1)),((1.1,1.85),(1.1,3.1))]:
    arrow(a,b)
ax.text(4.05,2.77,'Execute and update',ha='center',fontsize=8.5,color='#356572',rotation=-24)
ax.text(10.65,2.46,'Select',ha='left',fontsize=9,color='#356572')
save(fig,'fig01_architecture')
shutil.copy2(ROOT/'sim/sites/comparison/three_site_cross_validation_paper.png', FIG/'fig02_sites.png')
shutil.copy2(ROOT/'sim/sites/comparison/three_site_cross_validation_paper.pdf', FIG/'fig02_sites.pdf')

fig, axs = plt.subplots(1,3,figsize=(12,3.9),gridspec_kw={'width_ratios':[1,1,1.08]})
x=np.arange(4)
for ax,metric,title in zip(axs[:2],['critical_mission_completion_time_s','existing_missions_damaged_count'],
                         ['(a) Emergency completion, Site A','(b) Existing-service damage, Site A']):
    vals=[R['E1']['A']['summary'][m][metric] for m in MANAGERS]
    means=np.array([v['mean'] for v in vals]); ci=np.array([v['ci95'] for v in vals])
    ax.bar(x,means,color=COLORS,width=.65)
    ax.errorbar(x,means,yerr=np.maximum(0,np.array([means-ci[:,0],ci[:,1]-means])),fmt='none',ecolor='#333333',capsize=3)
    ax.set_xticks(x,MANAGERS); ax.set_title(title,fontsize=10)
    ax.set_ylabel('Time from release (s)' if ax==axs[0] else 'Affected services per run')
    ax.grid(axis='y',alpha=.2); ax.set_axisbelow(True)
ax=axs[2]
for i,s in enumerate('ABC'):
    q=R['E1'][s]['ablation'][0]; lo,hi=q['diff_ci95']
    ax.errorbar(q['diff_mean'],i,xerr=[[q['diff_mean']-lo],[hi-q['diff_mean']]],fmt='o',color=COLORS[3],capsize=4)
ax.axvline(0,color='#888888',lw=1); ax.set_yticks(range(3),['Site A','Site B','Site C']); ax.invert_yaxis()
ax.set(xlabel='B4b minus B4a completion (s)',title='(c) Candidate-table ablation')
ax.text(.02,.03,'Negative: faster with candidate table',transform=ax.transAxes,fontsize=8)
fig.tight_layout(w_pad=2); save(fig,'fig03_e1_coordination')

fig,axs=plt.subplots(1,2,figsize=(10,3.8))
for j,m in enumerate(MANAGERS):
    vals=[100*R['E2'][s]['summary'][m]['critical_mission_deadline_violation']['mean'] for s in 'ABC']
    axs[0].bar(np.arange(3)+(j-1.5)*.19,vals,width=.18,color=COLORS[j],label=m)
axs[0].set_xticks(range(3),['Site A','Site B','Site C']); axs[0].set(ylabel='Deadline violations (%)',ylim=(0,110),title='(a) All emergency missions')
axs[0].legend(ncol=4,fontsize=8,loc='upper center'); axs[0].grid(axis='y',alpha=.2); axs[0].set_axisbelow(True)
for i,s in enumerate('ABC'):
    q=R['E2'][s]['b4b_vs_b2_family'][0]; lo,hi=q['diff_ci95']
    axs[1].errorbar(q['diff_mean'],i,xerr=[[q['diff_mean']-lo],[hi-q['diff_mean']]],fmt='o',color=COLORS[3],capsize=4)
axs[1].axvline(0,color='#888888',lw=1); axs[1].set_yticks(range(3),['Site A','Site B','Site C']); axs[1].invert_yaxis()
axs[1].set(xlabel='B4b minus B2 completion (s)',title='(b) Paired completion differences')
fig.tight_layout(w_pad=3); save(fig,'fig04_e2_recovery')
for n,src in [('fig05_e3_compound_loss','e3_cross_site_swl'),('fig06_e4_operational_conditions','e4_operational_sensitivity')]:
    for ext in ['png','svg']:
        shutil.copy2(ROOT/f'outputs/paper_final/{src}.{ext}',FIG/f'{n}.{ext}')

def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])
def fmt(v,d=2):
    return 'N/A' if v is None else f'{v:.{d}f}'
def ci(v,d=2): return '['+', '.join(fmt(x,d) for x in v)+']'
def pval(p): return f'{p:.3g}' if p<.001 else f'{p:.3f}'
T={}
T['E1']=table(['Site','Manager','Completion (s)','Deadline violations (%)','Service damage/run'],
 [[s,m,fmt(v['critical_mission_completion_time_s']['mean']),fmt(100*v['critical_mission_deadline_violation']['mean']),fmt(v['existing_missions_damaged_count']['mean'],3)]
  for s in 'ABC' for m in MANAGERS for v in [R['E1'][s]['summary'][m]]])
T['ABLATION']=table(['Site','Endpoint','Paired difference','95% CI','Holm-adjusted p'],
 [[s, {'critical_mission_completion_time_s':'Completion (s)','existing_missions_damaged_count':'Service damage/run','air_intervention':'Air intervention (pp)'}[q['metric']],
   fmt(q['diff_mean']*(100 if q['metric']=='air_intervention' else 1),3),
   ci([x*(100 if q['metric']=='air_intervention' else 1) for x in q['ci95']],3),pval(q['p_holm'])]
  for s in 'ABC' for q in R['E1'][s]['ablation']])
T['E2']=table(['Site','Manager','Completion (s)','Deadline violations (%)','Recovered/affected','Recovery rate, 95% CI (%)'],
 [[s,m,fmt(v['critical_mission_completion_time_s']['mean']),fmt(100*v['critical_mission_deadline_violation']['mean']),
   f"{v['recovered_n']}/{v['affected_n']}" if v['affected_n'] else 'N/A',
   fmt(100*v['recovery_success']['mean'],0)+' '+ci([100*x for x in v['recovery_success']['ci95']],1) if v['affected_n'] else 'N/A']
  for s in 'ABC' for m in MANAGERS for v in [R['E2'][s]['summary'][m]]])
T['E2PAIRS']=table(['Site','Endpoint','Matched n','B4b − B2 (s)','95% CI (s)','Holm-adjusted p'],
 [[s,'Completion' if q['metric']=='critical_mission_completion_time_s' else 'Conditional recovery',q['n'],fmt(q['diff_mean'],3),ci(q['ci95'],3),pval(q['p_holm'])]
  for s in 'ABC' for q in R['E2'][s]['b4b_vs_b2_family'] if q['metric'] in ['critical_mission_completion_time_s','recovery_time_s']])
T['E3']=table(['Site','Level','n/manager','B0','B1','B2','B4b'],
 [[s,l,R['E3'][s]['levels'][l]['B0']['n']]+[fmt(R['E3'][s]['levels'][l][m]['system_weighted_loss']['mean'],3) for m in MANAGERS]
  for s in 'ABC' for l in ['L1','L2','L3','L4']])
T['OBS']=table(['Interval (s)','Task first visible (s)','Fault first visible (s)','Completion (s)','Deadline violations (%)','Calls/run','Prompt tokens/run'],
 [[int(a[3:]),task,fault,fmt(v['critical_mission_completion_time_s']['mean'],0),fmt(100*v['critical_mission_deadline_violation']['mean'],0),fmt(v['num_manager_decisions']['mean'],0),fmt(v['llm_total_prompt_tokens']['mean'],0)]
  for a,task,fault in zip(['OBS10','OBS30','OBS60','OBS120','OBS300'],[310,330,360,360,600],[380,390,420,480,600])
  for v in [R['E4']['4A']['arms'][a]['B4b']['metrics']]])
T['INPUT']=table(['Aircraft records','Physical fleet','Mean completion (s)','On-time runs','Logged calls','Mean prompt tokens/call'],
 [[int(a[1:]),4,fmt(q['B4b']['metrics']['critical_mission_completion_time_s']['mean'],1),
   f"{round(q['B4b']['n_runs']*(1-q['B4b']['metrics']['critical_mission_deadline_violation']['mean']))}/{q['B4b']['n_runs']}",
   q['B4b']['llm_reliability']['calls'],fmt(q['B4b']['llm_reliability']['prompt_tokens_per_logged_call'],1)]
  for a,q in R['E4']['4C']['arms'].items()])
T['FULL']=table(['Experiment','Site','Manager','n','Completion: mean [95% CI] (s)','Deadline violations: % [95% CI]','SWL: mean [95% CI]'],
 [[e,s,m,v['n'],fmt(v['critical_mission_completion_time_s']['mean'])+' '+ci(v['critical_mission_completion_time_s']['ci95']),
   fmt(100*v['critical_mission_deadline_violation']['mean'])+' '+ci([100*x for x in v['critical_mission_deadline_violation']['ci95']]),
   fmt(v['system_weighted_loss']['mean'])+' '+ci(v['system_weighted_loss']['ci95']) if v['system_weighted_loss']['n'] else 'N/A']
  for e in ['E1','E2','E3'] for s in 'ABC' for m in MANAGERS for v in [R[e][s]['summary'][m]]])
T['DELAY']=table(['Delay (s)','Mean completion (s)','Deadline violations (%)'],
 [[int(a[1:]),fmt(q['B4b']['metrics']['critical_mission_completion_time_s']['mean'],0),fmt(100*q['B4b']['metrics']['critical_mission_deadline_violation']['mean'],0)]
  for a,q in R['E4']['4B']['arms'].items()])

source=(HERE/'manuscript.template.md').read_text(encoding='utf-8')
for key,value in T.items(): source=source.replace('{{TABLE_'+key+'}}',value)
# Absolute image targets let the desktop preview display figures; conversion uses the figure basename.
source=source.replace('{{FIGDIR}}',FIG.as_posix())
assert not re.search(r'\{\{.*?\}\}',source), 'Unresolved manuscript field'
(HERE/'first_manuscript.md').write_text(source,encoding='utf-8')
anchors=re.findall(r'<a id="([^"]+)"></a>',source)
refs=re.findall(r'\]\(#([^\)]+)\)',source)
images=re.findall(r'!\[[^\]]*\]\(<([^>]+)>\)',source)
bib=(HERE/'references.bib').read_text(encoding='utf-8')
table_blocks=re.findall(r'(?:^\|.*\|\n)+',source,re.M)
prose=source.split('<a id="data-availability">')[0]
prose=re.sub(r'(?:^\|.*\|\n)+','',prose,flags=re.M)
prose=re.sub(r'!\[.*?\]\(<.*?>\)','',prose)
prose=re.sub(r'\]\([^)]*\)',']',prose)
prose=re.sub(r'<[^>]*>','',prose)
checks={
 'unique_anchors':len(anchors)==len(set(anchors)),
 'all_internal_links_resolve':all(x in anchors for x in refs),
 'all_six_images_exist':len(images)==6 and all(Path(x).is_file() for x in images),
 'no_unresolved_template_fields':'{{' not in source,
 'no_editorial_placeholders':not re.search(r'\b(TODO|TBD|INSERT HERE|PLACEHOLDER)\b',source),
 'numbered_sections':all(f'## {i}. ' in source for i in range(1,9)),
 'all_citations_defined':all(f'ref-{x}' in anchors for x in re.findall(r'\[\[(\d+)\]\]',source)),
 'fourteen_references':len(re.findall(r'<a id="ref-\d+">',source))==14,
 'primary_run_count':R['primary_runs']==10960,
 'ablation_run_count':R['ablation_runs']==180,
 'eleven_equations':re.findall(r'\\tag\{(\d+)\}',source)==[str(i) for i in range(1,12)],
 'fourteen_tables':re.findall(r'\*\*Table (\d+)\.',source)==[str(i) for i in range(1,15)],
 'six_figures':re.findall(r'\*\*Figure (\d+)\.',source)==[str(i) for i in range(1,7)],
 'rectangular_markdown_tables':all(len({line.count('|') for line in b.splitlines()})==1 for b in table_blocks),
 'all_fourteen_bibtex_entries':len(re.findall(r'^@\w+\{',bib,re.M))==14,
 'balanced_bibtex_braces':bib.count('{')==bib.count('}'),
 'e1_abstract_reduction':round(100*(1-R['E1']['A']['summary']['B4b']['critical_mission_completion_time_s']['mean']/R['E1']['A']['summary']['B0']['critical_mission_completion_time_s']['mean']),1)==21.9,
 'e1_ablation_headline':round(R['E1']['A']['ablation'][0]['diff_mean'],2)==-13.57,
 'e3_abstract_reduction':round(100*(1-R['E3']['A']['summary']['B4b']['system_weighted_loss']['mean']/R['E3']['A']['summary']['B0']['system_weighted_loss']['mean']),1)==57.4,
 'e4_all_input_runs_on_time':all(q['B4b']['metrics']['critical_mission_deadline_violation']['mean']==0 for q in R['E4']['4C']['arms'].values()),
 'e4_total_transport_errors':sum(q['B4b']['llm_reliability']['transport_errors'] for e in ['4A','4B','4C'] for q in R['E4'][e]['arms'].values())==4,
 'e4_total_structured_retries':sum(q['B4b']['llm_reliability']['structured_retries'] for e in ['4A','4B','4C'] for q in R['E4'][e]['arms'].values())==4,
}
record={'checks':checks,'passed':all(checks.values()),'word_count_including_tables_references':len(source.split()),
        'main_text_words_excluding_tables':len(re.findall(r"\b[\w]+(?:[-'][\w]+)*\b",prose)),
        'numeric_source':str(DATA.relative_to(ROOT)),'numeric_source_sha256':hashlib.sha256(DATA.read_bytes()).hexdigest(),
        'manuscript_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'generated_tables':list(T),'figure_files':sorted(x.name for x in FIG.iterdir())}
(HERE/'validation.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
assert all(checks.values()), 'Manuscript validation failed'
