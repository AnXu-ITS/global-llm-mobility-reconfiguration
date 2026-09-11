"""Targeted read-only checks supplementing the writing-readiness inventory."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,hashlib,json,statistics,sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/writing_readiness_20260910'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def csvrows(p):
    with p.open(encoding='utf-8',newline='') as f: return list(csv.DictReader(f))
result={'e4_replan_miscounts':[],'e4_llm':{},'e4_first_observation':{},'d00_e2_comparison':{},'freeze_mismatches':[]}
manifest=read(ROOT/'outputs/file_hashes_final.json')
for p,expected in manifest.items():
    actual=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    if actual != expected: result['freeze_mismatches'].append({'path':p,'expected':expected,'actual':actual})
groups=defaultdict(list)
for f in sorted((ROOT/'runs/experiment4/primary').glob('*/*/*/seed*/B*/metrics.json')):
    d=read(f);rd=f.parent
    if rd.name == 'B4b':
        outputs=[json.loads(line) for line in (rd/'manager_outputs.jsonl').read_text(encoding='utf-8').splitlines() if line]
        for o in outputs: groups[d['sub_experiment']+'/'+d['arm_id']].append(o.get('llm_metadata') or {})
    if d['sub_experiment']=='4A':
        rows=csvrows(rd/'actions.csv')
        valid=[a for a in rows if a['result']=='ISSUED' and a['mission_id']==d['critical_mission_id'] and int(a['t'])>=d['failure_time'] and a['action_type'] in ('DISPATCH','REASSIGN','GROUND_FALLBACK','REROUTE','DIVERT')]
        corrected=int(valid[0]['t'])-d['failure_time'] if valid else None
        if corrected != d['failure_to_replan_latency_s']:
            result['e4_replan_miscounts'].append({'run':str(rd.relative_to(ROOT)),'reported':d['failure_to_replan_latency_s'],'first_executed_mission_action_delay':corrected})
        if d['seed']==20240601 and rd.name=='B2':
            inputs=[json.loads(line) for line in (rd/'manager_inputs.jsonl').read_text(encoding='utf-8').splitlines() if line]
            g=inputs[0]
            result['e4_first_observation'][d['arm_id']]={'snapshot_time':g.get('observation_snapshot_time'),'age':g.get('observation_snapshot_age_s'),'mission_present':d['critical_mission_id'] in json.dumps(g),'first_actions':rows[:4]}
for k,ls in groups.items():
    result['e4_llm'][k]={'calls':len(ls),'statuses':dict(Counter(str(x.get('validation_status')) for x in ls)),'retry_total':sum(x.get('retry_count',0) or 0 for x in ls),'errors':sum(bool(x.get('errors')) for x in ls),'prompt_tokens_per_call_mean':statistics.mean(x.get('prompt_tokens',0) or 0 for x in ls),'latency_s_mean_logged':statistics.mean(x.get('latency_s',0) or 0 for x in ls)}
for mgr in ('B0','B1','B2','B4b'):
    same_actions=same_metrics=0;differences=[]
    for seed in range(20240601,20240621):
        p=ROOT/f'runs/experiment4/primary/4B/D00/E4_ANCHOR/seed{seed}/{mgr}'
        q=ROOT/f'runs/experiment2/E2_F1_C2/seed{seed}/{mgr}'
        a=csvrows(p/'actions.csv');b=csvrows(q/'actions.csv')
        same_actions+=a==b
        da,db=read(p/'metrics.json'),read(q/'metrics.json')
        keys=['critical_mission_completion_time_s','critical_mission_deadline_violation','critical_mission_final_mode','critical_mission_final_state']
        match=all(da.get(k)==db.get(k) for k in keys);same_metrics+=match
        if not match:differences.append({'seed':seed,'e4':{k:da.get(k) for k in keys},'e2':{k:db.get(k) for k in keys}})
    result['d00_e2_comparison'][mgr]={'same_action_rows':same_actions,'same_four_outcome_metrics':same_metrics,'n':20,'differences':differences}
(OUT/'details.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('replan miscounts',len(result['e4_replan_miscounts']))
print('D00',json.dumps(result['d00_e2_comparison']))
print('LLM',json.dumps(result['e4_llm']))
