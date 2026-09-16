from pathlib import Path
import sys,json,collections,csv
import numpy as np
W=Path(__file__).resolve().parents[2];R=W.parent;O=W/'source/revision_v3'
sys.path.insert(0,str(R/'tools'))
from paper_stats import summary
from paper_metrics import execution_metrics
import analyze_experiment4 as e4
def read(p):return json.loads(p.read_text(encoding='utf-8'))
d=read(O/'results_revised.json');new=[]
for p in sorted((O/'regression/D60_F360').glob('seed*/B0/metrics.json')):new.append(execution_metrics(p.parent,read(p)))
assert len(new)==20 and all(r['critical_mission_completion_time_s']==242 for r in new)
for k,st in d['E4']['4B']['arms']['D60']['B0']['metrics'].items():
    if k in ['recovery_time_s','recovery_success']:continue
    if all(k in r for r in new):d['E4']['4B']['arms']['D60']['B0']['metrics'][k]=summary([r[k] for r in new],k in ['critical_mission_deadline_violation','affected_critical'])
t=next(t for t in d['E4']['4B']['paired']['critical_mission_completion_time_s @ B0']['arms'] if t['arm']=='D60')
t['mean_delta']=60.;t['ci95']={'mean':60.,'ci95_low':60.,'ci95_high':60.}
# Replan is not applicable to B0: replacement is a duplicate pending command,
# not recovery of an affected primary air chain. Keep the archived ancillary
# replan endpoint identifiable rather than treating it as a new observation.
d['revision']={'queue_fix':'20 B0 D60 runs replaced; other primary cells retained','statistics':'fixed-panel seed blocks','B0_ancillary_timing':'see run-level revised metrics; B0 is not an affected recovery population'}
(O/'results_revised.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
old=read(R/'outputs/paper_final/e4_run_metrics.json')
for i,r in enumerate(old):
    if r['arm_id']=='D60' and r.get('paper_manager',r.get('manager'))=='B0':
        rr=next(x for x in new if x['seed']==r['seed']);old[i]=r|rr|{'revision_run':f'source/revision_v3/regression/D60_F360/seed{r["seed"]}/B0'}
(O/'e4_run_metrics_revised.json').write_text(json.dumps(old,indent=2),encoding='utf-8')
groups={}
for r in old:groups.setdefault((r['sub_experiment'],r['arm_id'],r['paper_manager']),{})[(r['scenario_id'],r['seed'])]=r
d['E4']['4B']=e4._analyze_sub('4B',groups,[])
d['inference']='Fixed scenario panel, seed-block intervals and paired tests; single-scenario E4 retains seed pairing.'
(O/'results_revised.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
regs=read(O/'decision_regimes.json');data=read(O/'all_metrics.json');duration={}
for s in 'ABC':
 for m in ['B1','B2','B4b']:
  vals=[]
  for r in data['E1_'+s]:
   if r['paper_manager']!=m:continue
   rd=R/r['source_run'];final=read(rd/'registry_final.json')
   damaged={x['mission_id'] for x in final['missions'] if x['mission_id']!=r['critical_mission_id'] and x['status']=='INTERRUPTED'}
   with (rd/'candidate_info.jsonl').open(encoding='utf-8') as cf:ct=json.loads(next(cf))['candidate_table']
   acts=list(csv.DictReader((rd/'actions.csv').open(encoding='utf-8')));loss=0
   for a in acts:
    if a['result']=='ISSUED' and a['action_type']=='REASSIGN':
     cand=next((c for c in ct['air'] if c['resource_id']==a['aircraft_id']),None)
     if cand and cand['preempted_mission_id'] in damaged:loss+=r['duration_s']-float(a['t'])
   assert len(damaged)==r['existing_missions_damaged_count']
   vals.append(loss)
  duration[s+'_'+m]=sum(vals)/len(vals)
(O/'persistent_interruption_duration.json').write_text(json.dumps(duration,indent=2))
print(duration)
