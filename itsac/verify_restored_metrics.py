"""Offline verification of restored metric records; no simulations or API calls.

Run: python itsac/verify_restored_metrics.py
Dependencies: numpy scipy
"""
from pathlib import Path
import collections, hashlib, json, math, warnings
import numpy as np
from scipy import stats

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'manuscript/source/revision_v3'
OUT=ROOT/'itsac/supplement/verification';OUT.mkdir(parents=True,exist_ok=True)
def read(n):return json.loads((DATA/n).read_text(encoding='utf-8'))
rows=read('all_metrics.json');e4=read('e4_run_metrics_revised.json');expected=read('results_revised.json')
checks=[];summaries={};contrasts={}
def close(actual,exp,where):
    assert math.isclose(float(actual),float(exp),rel_tol=1e-8,abs_tol=1e-8),(where,actual,exp)
    checks.append(where)
def block_summary(pairs):
    pairs=[(s,float(v)) for s,v in pairs if v is not None]
    n=len(pairs);seeds=sorted({s for s,v in pairs});k=len(seeds);mean=float(np.mean([v for s,v in pairs]))
    # Cluster influence also handles unequal conditional denominators.
    b=np.array([mean+k/n*sum(v-mean for ss,v in pairs if ss==s) for s in seeds])
    half=float(stats.t.ppf(.975,k-1)*b.std(ddof=1)/np.sqrt(k))
    return {'n':n,'seed_blocks':k,'mean':mean,'ci95':[mean-half,mean+half]},b
def contrast(rr,base,other,metric,binary=False,affected=False):
    a={(r['scenario_id'],r['seed']):r for r in rr if r['paper_manager']==base}
    b={(r['scenario_id'],r['seed']):r for r in rr if r['paper_manager']==other}
    pairs=[]
    for key in sorted(a.keys()&b.keys()):
        x,y=a[key],b[key]
        if affected and not(x.get('affected_critical') and y.get('affected_critical')):continue
        if x.get(metric) is not None and y.get(metric) is not None:pairs.append((key[1],float(y[metric])-float(x[metric])))
    if not pairs:return {'mean':None,'ci95':[None,None],'p':1.,'n':0}
    report,bs=block_summary(pairs)
    if np.allclose(bs,0):p=1.
    elif binary:
        dist=collections.Counter({0:1});sums=[int(round(sum(d for ss,d in pairs if ss==s))) for s in sorted({s for s,d in pairs})]
        for value in sums:
            nxt=collections.Counter()
            for subtotal,count in dist.items():nxt[subtotal+value]+=count;nxt[subtotal-value]+=count
            dist=nxt
        p=sum(count for subtotal,count in dist.items() if abs(subtotal)>=abs(sum(sums)))/2**len(sums)
    elif np.allclose(bs,bs[0]):p=float(stats.wilcoxon(bs).pvalue)
    else:p=float(stats.ttest_1samp(bs,0).pvalue)
    return report|{'p':p}
def holm(values):
    order=np.argsort(values);out=[0.]*len(values);prev=0.
    for rank,i in enumerate(order):prev=max(prev,min(1.,(len(values)-rank)*values[i]));out[i]=prev
    return out

total=sum(map(len,rows.values()))+len(e4);assert total==11140
ablation=sum(sum(r['paper_manager']=='B4a' for r in rr) for rr in rows.values());assert ablation==180
for group,rr in rows.items():
    keys=[(r['scenario_id'],r['seed'],r['paper_manager']) for r in rr];assert len(keys)==len(set(keys)),group
    exp,site=group.split('_');summaries[group]={}
    for pol in ['B0','B1','B2','B4b']:
        rs=[r for r in rr if r['paper_manager']==pol];want=320 if exp=='E2' else 240;assert len(rs)==want
        summaries[group][pol]={}
        for field in ['critical_mission_completion_time_s','critical_mission_deadline_violation','existing_missions_damaged_count','system_weighted_loss']:
            pairs=[(r['seed'],r.get(field)) for r in rs if r.get(field) is not None]
            if not pairs:continue
            val,_=block_summary(pairs);st=expected[exp][site]['summary'][pol][field]
            close(val['mean'],st['mean'],group+'/'+pol+'/'+field+'/mean')
            for i in range(2):close(val['ci95'][i],st['ci95'][i],group+'/'+pol+'/'+field+'/ci'+str(i))
            summaries[group][pol][field]=val
        if exp=='E2':
            affected=[r for r in rs if r.get('affected_critical')];recovered=sum(bool(r.get('recovery_success')) for r in affected)
            st=expected[exp][site]['summary'][pol]
            close(len(affected),st['affected_n'],group+'/'+pol+'/affected');close(recovered,st['recovered_n'],group+'/'+pol+'/restored')
            summaries[group][pol]['restored_affected']=[recovered,len(affected)]
    if exp=='E1':
        cc=[]
        for field,binary in [('critical_mission_completion_time_s',False),('existing_missions_damaged_count',False),('air_intervention',True)]:
            c=contrast(rr,'B4a','B4b',field,binary);c['metric']=field;cc.append(c)
        for c,padj,st in zip(cc,holm([c['p'] for c in cc]),expected['E1'][site]['ablation']):
            c['p_holm']=padj
            for k in ['mean','p','p_holm']:close(c[k],st[k],group+'/ablation/'+c['metric']+'/'+k)
            for i in range(2):close(c['ci95'][i],st['ci95'][i],group+'/ablation/'+c['metric']+'/ci'+str(i))
        contrasts[group+'_ablation']=cc

# Suzhou scenario-specific paired family (12 scenarios, not an isolated p value).
rr=rows['E1_A'];cs=[]
for st in expected['E1']['A']['b4b_vs_b2_scenarios']:
    scenario=st['scenario_id'];c=contrast([r for r in rr if r['scenario_id']==scenario],'B2','B4b','critical_mission_completion_time_s');c['scenario']=scenario;cs.append(c)
for c,padj,st in zip(cs,holm([c['p'] for c in cs]),expected['E1']['A']['b4b_vs_b2_scenarios']):
    c['p_holm']=padj;close(c['mean'],st['diff_mean'],'E1_A/'+c['scenario']+'/delta');close(padj,st['p_holm'],'E1_A/'+c['scenario']+'/p_holm')
contrasts['E1_A_scenario_family']=cs

# The archived E2 families contain twelve entries; recompute every recorded one.
for site in 'ABC':
    cc=[];family=expected['E2'][site]['b4b_vs_b2_family']
    for st in family:
        metric=st['metric'];binary=st.get('test')=='seed-block exact label swap';affected=metric in ['recovery_time_s','failure_to_replan_latency_s','recovery_success','recovered_completed'];c=contrast(rows['E2_'+site],st.get('baseline','B2'),st.get('other','B4b'),metric,binary,affected);c['metric']=metric;cc.append(c)
        if c['mean'] is not None and st.get('diff_mean') is not None:close(c['mean'],st['diff_mean'],'E2_'+site+'/'+metric+'/delta')
    for c,padj,st in zip(cc,holm([c['p'] for c in cc]),family):
        c['p_holm']=padj
        close(c['p'],st['p'],'E2_'+site+'/'+c['metric']+'/p')
        close(padj,st['p_holm'],'E2_'+site+'/'+c['metric']+'/p_holm')
        if c['mean'] is not None:
            for i in range(2):close(c['ci95'][i],st['ci95'][i],'E2_'+site+'/'+c['metric']+'/ci'+str(i))
    contrasts['E2_'+site]=cc

for site in 'ABC':
    rr=rows['E3_'+site];cc=[];family=expected['E3'][site]['hypotheses']
    for r in rr:r['_critical_high_loss']=sum(r.get('system_weighted_loss_by_priority',{}).get(p,0) for p in ['CRITICAL','HIGH'])
    for st in family:
        c=contrast([r for r in rr if r['level']==st['level']],st['baseline'],st['other'],st['metric']);c.update(level=st['level'],baseline=st['baseline'],metric=st['metric']);cc.append(c)
    for c,padj,st in zip(cc,holm([c['p'] for c in cc]),family):
        c['p_holm']=padj
        for key in ['mean','p','p_holm']:close(c[key],st[key],'E3_'+site+'/'+c['level']+'/'+c['baseline']+'/'+c['metric']+'/'+key)
    contrasts['E3_'+site+'_compound']=cc

groups=collections.defaultdict(list)
for r in e4:groups[(r['sub_experiment'],r['arm_id'],r['paper_manager'])].append(r)
for (panel,arm,pol),rr in groups.items():
    assert len(rr)==20
    for metric in ['critical_mission_completion_time_s','critical_mission_deadline_violation']:
        mean=float(np.mean([r[metric] for r in rr]));st=expected['E4'][panel]['arms'][arm][pol]['metrics'][metric]
        close(mean,st['mean'],'E4/'+panel+'/'+arm+'/'+pol+'/'+metric)
    summaries['E4_'+panel+'_'+arm+'_'+pol]={'n':20,'completion_mean':float(np.mean([r['critical_mission_completion_time_s'] for r in rr])),'late_rate':float(np.mean([r['critical_mission_deadline_violation'] for r in rr]))}
close(summaries['E4_4B_D60_B0']['completion_mean'],242,'corrected B0 D60')
close(summaries['E4_4B_D60_B4b']['completion_mean'],302,'retained B4b D60')

report={'status':'PASS','total_metric_records':total,'primary_records':total-ablation,'ablation_records':ablation,'numeric_checks_passed':len(checks),'simulation_runs_executed':0,'llm_calls_executed':0,'source_files_sha256_lf_normalized':{n:hashlib.sha256((DATA/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for n in ['all_metrics.json','e4_run_metrics_revised.json','results_revised.json']},'scope':'Recomputed from restored per-run metrics. Does not regenerate metrics from raw logs. Historical raw runs/ and outputs/ are missing from Git.','summaries':summaries,'contrasts':contrasts,'checks':checks}
(OUT/'metric_verification.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['summaries','contrasts','checks','source_files_sha256_lf_normalized']},indent=2))
