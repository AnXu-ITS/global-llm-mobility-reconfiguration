from pathlib import Path
import sys,json,csv,collections,math,copy
import numpy as np
from scipy import stats
W=Path(__file__).resolve().parents[2];R=W.parent; O=W/'source/revision_v3'
sys.path[:0]=[str(R),str(R/'tools')]
from paper_stats import holm
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def block_summary(vals):
    vals=[(s,float(v)) for s,v in vals if v is not None and math.isfinite(float(v))]
    if not vals:return {'n':0,'mean':None,'ci95':[None,None]}
    n=len(vals);seeds=sorted({s for s,v in vals});k=len(seeds);mu=np.mean([v for s,v in vals])
    # Cluster influence retains the original run-weighted estimand even for
    # unequal conditional denominators. Complete panels reduce to seed means.
    b=np.array([mu+k/n*sum(v-mu for ss,v in vals if ss==s) for s in seeds])
    se=b.std(ddof=1)/np.sqrt(k) if k>1 else 0
    half=stats.t.ppf(.975,k-1)*se if k>1 else 0
    return {'n':n,'seed_blocks':k,'mean':float(mu),'ci95':[float(mu-half),float(mu+half)],'blocks':b.tolist()}
def contrast(rows,base,other,met,binary=False,affected=False):
    a={(r['scenario_id'],r['seed']):r for r in rows if r['paper_manager']==base}
    b={(r['scenario_id'],r['seed']):r for r in rows if r['paper_manager']==other}
    ds=[]
    for key in sorted(a.keys()&b.keys()):
        x,y=a[key],b[key]
        if affected and not(x.get('affected_critical') and y.get('affected_critical')):continue
        if x.get(met) is None or y.get(met) is None:continue
        ds.append((key[1],float(y[met])-float(x[met])))
    st=block_summary(ds)
    if not ds:return st|{'metric':met,'p':1,'baseline':base,'other':other,'diff_mean':None}
    v=np.array(st.pop('blocks'));mu=st['mean']
    if np.allclose(v,0):p=1.
    elif binary:
        # Exact policy-label swap for whole seed blocks, preserving all
        # within-seed scenario dependence (cluster analogue of McNemar).
        sums=[int(round(sum(d for ss,d in ds if ss==s))) for s in sorted({s for s,d in ds})]
        dist=collections.Counter({0:1})
        for v0 in sums:
            nxt=collections.Counter()
            for z,count in dist.items():nxt[z+v0]+=count;nxt[z-v0]+=count
            dist=nxt
        p=sum(c for z,c in dist.items() if abs(z)>=abs(sum(sums)))/2**len(sums)
    elif np.allclose(v,v[0]):p=float(stats.wilcoxon(v).pvalue)
    else:p=float(stats.ttest_1samp(v,0).pvalue)
    return st|{'metric':met,'baseline':base,'other':other,'diff_mean':mu,'p':p,'test':'seed-block exact label swap' if binary else 'seed-block paired t / constant signed rank'}
def adjust(ts):
    for t,p in zip(ts,holm([t['p'] for t in ts])):t['p_holm']=p
    return ts

result=read(R/'outputs/paper_final/results.json'); allrows={};regimes=[];transfer=[]
for exp in (1,2,3):
  for site,suffix in [('A',''),('B','site_b_amsterdam'),('C','site_c_edmonton')]:
    if exp==2:rows=read(R/f'outputs/paper_final/e2_{site.lower()}_run_metrics.json')
    elif exp==3:
        rows=read(O/f'e3_{site}_metrics.json')
        for r in rows:r.update(paper_manager=r['policy'],source_run=r['path'])
    else:
        base=R/'runs/experiment1_final' if site=='A' else R/'runs/experiment1_cross_site'/suffix
        rows=[]
        for p in base.glob('*/seed*/B*/metrics.json'):
            if p.parent.name not in ['B0','B1','B2','B4a','B4b']:continue
            rows.append(read(p)|{'paper_manager':p.parent.name,'source_run':str(p.parent.relative_to(R))})
    allrows[f'E{exp}_{site}']=rows
    block=result[f'E{exp}'][site]
    for mgr,summary in block['summary'].items():
        for met in ['critical_mission_completion_time_s','critical_mission_deadline_violation','existing_missions_damaged_count','system_weighted_loss']:
            summary[met]=block_summary([(r['seed'],r.get(met)) for r in rows if r['paper_manager']==mgr]);summary[met].pop('blocks',None)
    if exp==1:
        block['ablation']=adjust([contrast(rows,'B4a','B4b',m,b) for m,b in [('critical_mission_completion_time_s',False),('existing_missions_damaged_count',False),('air_intervention',True)]])
        # First-decision snapshots are compared at the common pre-action state.
        for r in rows:
            if r['paper_manager'] not in ['B1','B2','B4b']:continue
            rd=R/r['source_run']; cf=rd/'candidate_info.jsonl'
            with cf.open(encoding='utf-8') as f: first=json.loads(next(f))
            ct=first['candidate_table']; t=first['t'];slack=ct['summary']['deadline_slack_s']
            legal=[c for c in ct['air']+[ct['ground']] if c['legal'] and c['eta_s'] is not None]
            air=[c for c in legal if c['mode']=='AIR'];ground=[c for c in legal if c['mode']=='GROUND']
            bestair=min(air,key=lambda c:c['eta_s']) if air else None
            conflict=bool(bestair and ground and ground[0]['eta_s']<=slack and bestair['eta_s']<ground[0]['eta_s'] and bestair['service_loss_estimate']['interrupts_existing_mission'])
            no_timely=not any(c['eta_s']<=slack for c in legal)
            regime='C: no timely candidate' if no_timely else 'B: speed/service conflict' if conflict else 'A: no timely-ground preemption conflict'
            acts=list(csv.DictReader((rd/'actions.csv').open(encoding='utf-8')))
            selected=next((a for a in acts if a['result']=='ISSUED' and a['mission_id']==r['critical_mission_id']),{})
            regimes.append({'site':site,'scenario':r['scenario_id'],'seed':r['seed'],'policy':r['paper_manager'],'regime':regime,'legal_n':len(legal),'both_modes':bool(air and ground),'air_eta':bestair['eta_s'] if bestair else None,'ground_eta':ground[0]['eta_s'] if ground else None,'air_advantage':ground[0]['eta_s']-bestair['eta_s'] if ground and bestair else None,'best_margin':max([slack-c['eta_s'] for c in legal],default=None),'preemption':bool(bestair and bestair['service_loss_estimate']['interrupts_existing_mission']),'selected':selected.get('action_type'),'completion_s':r['critical_mission_completion_time_s'],'late':r['critical_mission_deadline_violation']})
    if exp==2:
        cont=['critical_mission_completion_time_s','recovery_time_s','failure_to_replan_latency_s','existing_missions_damaged_count','candidate_set_reduction_delta']
        bins=['critical_mission_deadline_violation','recovery_success','recovered_completed','ground_fallback_rate','failure_induced_ground_fallback','necessary_ground_fallback_correct','air_intervention']
        block['b4b_vs_b2_family']=adjust([contrast(rows,'B2','B4b',m,False,m in ('recovery_time_s','failure_to_replan_latency_s')) for m in cont]+[contrast(rows,'B2','B4b',m,True,m in ('recovery_success','recovered_completed')) for m in bins])
        for r in rows:
            if not r.get('affected_critical'):continue
            rd=R/r['source_run']; acts=list(csv.DictReader((rd/'actions.csv').open(encoding='utf-8')))
            replacements=[a for a in acts if a['result']=='ISSUED' and a['mission_id']==r['critical_mission_id'] and float(a['t'])>=r['failure_time'] and a['action_type'] in ['DISPATCH','REASSIGN','GROUND_FALLBACK']]
            if replacements:
                a=replacements[0]; margin=r['critical_mission_deadline_s']-r['critical_mission_completion_t']
                transfer.append({'site':site,'scenario':r['scenario_id'],'seed':r['seed'],'policy':r['paper_manager'],'replacement':a['action_type'],'margin_s':margin,'source_run':r['source_run']})
    if exp==3:
        for r in rows:r['_critical_high_loss']=sum(r.get('system_weighted_loss_by_priority',{}).get(p,0) for p in ('CRITICAL','HIGH'))
        block['hypotheses']=adjust([contrast([r for r in rows if r['level']==l],b,'B4b',m)|{'level':l} for b in ['B1','B2'] for l in ['L2','L3','L4'] for m in ['system_weighted_loss','_critical_high_loss']])
        for lev,by_policy in block['levels'].items():
            for pol,metrics in by_policy.items():
                for met,st in list(metrics.items()):
                    if isinstance(st,dict) and 'mean' in st:
                        metrics[met]=block_summary([(r['seed'],r.get(met)) for r in rows if r['level']==lev and r['paper_manager']==pol]);metrics[met].pop('blocks',None)
        block['vs_b0']=adjust([contrast([r for r in rows if r['level']==old['level']],old['baseline'],old['other'],old['metric'])|{'level':old['level']} for old in block['vs_b0']])
    print(exp,site,len(rows),flush=True)
write(O/'results_revised.json',result);write(O/'all_metrics.json',allrows);write(O/'decision_regimes.json',regimes);write(O/'transfer_margins.json',transfer)
summary={}
for site in ['A','B','C']:
    summary[site]={}
    for policy in ['B1','B2','B4b']:
        rr=[r for r in regimes if r['site']==site and r['policy']==policy]
        summary[site][policy]={g:{'n':sum(r['regime']==g for r in rr),'air':sum(r['regime']==g and r['selected'] in ['DISPATCH','REASSIGN'] for r in rr),'late':sum(r['regime']==g and r['late'] for r in rr)} for g in sorted({r['regime'] for r in regimes})}
write(O/'regime_summary.json',summary)
ts={}
for site in ['A','B','C']:
 for policy in ['B1','B2','B4b']:
  rr=[r for r in transfer if r['site']==site and r['policy']==policy]
  ts[site+'_'+policy]={'n_replacements':len(rr),'on_time':sum(r['margin_s']>=0 for r in rr),'additional_late':{str(h):sum(0<=r['margin_s']<h for r in rr) for h in [15,30,60]},'timely_margin_range':[min([r['margin_s'] for r in rr if r['margin_s']>=0],default=None),max([r['margin_s'] for r in rr if r['margin_s']>=0],default=None)]}
write(O/'transfer_summary.json',ts)
print(json.dumps({'ablation_A':result['E1']['A']['ablation'],'E2_A':result['E2']['A']['b4b_vs_b2_family'][:2],'regimes':summary,'transfer':ts},indent=2))
