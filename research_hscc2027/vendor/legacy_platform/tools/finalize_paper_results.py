"""Build the single paper data release from current E1-final/E2/E3-v2/E4-v2.

No simulations/API calls. Writes derived outputs and final reports only.
"""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,platform,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from paper_stats import summary,paired,mcnemar,holm
from paper_metrics import execution_metrics
import analyze_experiment4 as e4
OUT=ROOT/'outputs/paper_final'
MGRS=('B0','B1','B2','B4b')
SITES={'A':'','B':'site_b_amsterdam','C':'site_c_edmonton'}

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
def table(head,rows):
    return '\n'.join(['| '+' | '.join(head)+' |','|'+'|'.join(['---']*len(head))+'|']+
                     ['| '+' | '.join(str(x) for x in row)+' |' for row in rows])
def fmt(x): return 'N/A' if x is None else (f'{x:.3g}' if 0<abs(x)<.0005 else f'{x:.3f}')
def load(exp,site):
    suffix='1_final' if exp==1 else str(exp)
    root=ROOT/f'runs/experiment{suffix}' if site=='A' else ROOT/f'runs/experiment{exp}_cross_site'/SITES[site]
    rows=[]
    for f in sorted(root.glob('*/seed*/B*/metrics.json')):
        mgr=f.parent.name
        if mgr not in MGRS+('B4a',):continue
        m=read(f)
        if exp==2:m=execution_metrics(f.parent,m)
        m.update(paper_manager=mgr,paper_site=site,paper_experiment=exp,source_run=str(f.parent.relative_to(ROOT)))
        rows.append(m)
    expected=1280 if exp==2 else 960
    primary=[r for r in rows if r['paper_manager'] in MGRS]
    if len(primary)!=expected:raise ValueError(f'E{exp} {site}: {len(primary)} != {expected}')
    for sid in {r['scenario_id'] for r in primary}:
        for mgr in MGRS:
            if {r['seed'] for r in primary if r['scenario_id']==sid and r['paper_manager']==mgr} != set(range(20240601,20240621)):
                raise ValueError(f'Incomplete {sid} {mgr}')
    return rows
def align(rows,base,other):
    a={(r['scenario_id'],r['seed']):r for r in rows if r['paper_manager']==base}
    b={(r['scenario_id'],r['seed']):r for r in rows if r['paper_manager']==other}
    keys=sorted(a.keys()&b.keys())
    return [(a[k],b[k]) for k in keys]
def contrast(rows,base,other,metric,binary=False,affected=False):
    pairs=align(rows,base,other)
    if affected:pairs=[(a,b) for a,b in pairs if a.get('affected_critical') and b.get('affected_critical')]
    st=(mcnemar if binary else paired)([a.get(metric) for a,b in pairs],[b.get(metric) for a,b in pairs])
    if st is None:st={'n':0,'p':None,'diff_mean':None,'ci95':[None,None]}
    return dict(st,metric=metric,baseline=base,other=other,denominator='both managers affected' if affected else 'all matched runs with observed metric')
def adjust(tests):
    for t,p in zip(tests,holm([t.get('p') for t in tests])):t['p_holm']=p
    return tests
def manager_summary(rows):
    result={}
    for mgr in MGRS:
        ds=[r for r in rows if r['paper_manager']==mgr]
        c={k:summary([r.get(k) for r in ds],k in ('critical_mission_deadline_violation','recovery_success'))
           for k in ('critical_mission_completion_time_s','critical_mission_deadline_violation',
                     'existing_missions_damaged_count','system_weighted_loss','recovery_success','recovery_time_s')}
        c.update(n=len(ds),affected_n=sum(bool(r.get('affected_critical')) for r in ds),
                 recovered_n=sum(r.get('recovery_success') is True for r in ds))
        result[mgr]=c
    return result
def main():
    OUT.mkdir(exist_ok=True)
    data={};manifest={}
    for exp in (1,2,3):
        data[f'E{exp}']={}
        for site in SITES:
            rows=load(exp,site)
            for r in rows:
                p=ROOT/r['source_run']/'metrics.json'
                manifest[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
            summary_by_mgr=manager_summary(rows)
            block={'summary':summary_by_mgr,'primary_n':sum(r['paper_manager'] in MGRS for r in rows),
                   'ablation_n':sum(r['paper_manager']=='B4a' for r in rows)}
            if exp==1:
                # Completion, service damage and intervention in the matched ablation.
                block['ablation']=adjust([contrast(rows,'B4a','B4b',met,binary) for met,binary in
                    [('critical_mission_completion_time_s',False),('existing_missions_damaged_count',False),('air_intervention',True)]])
                block['b4b_vs_b2_scenarios']=adjust([dict(contrast([r for r in rows if r['scenario_id']==sid],'B2','B4b','critical_mission_completion_time_s'),scenario_id=sid)
                    for sid in sorted({r['scenario_id'] for r in rows})])
            if exp==2:
                cont=['critical_mission_completion_time_s','recovery_time_s','failure_to_replan_latency_s','existing_missions_damaged_count','candidate_set_reduction_delta']
                bins=['critical_mission_deadline_violation','recovery_success','recovered_completed','ground_fallback_rate','failure_induced_ground_fallback','necessary_ground_fallback_correct','air_intervention']
                tests=[contrast(rows,'B2','B4b',met,False,met in ('recovery_time_s','failure_to_replan_latency_s')) for met in cont]
                tests += [contrast(rows,'B2','B4b',met,True,met in ('recovery_success','recovered_completed')) for met in bins]
                block['b4b_vs_b2_family']=adjust(tests)
                block['candidate_delta_interpretation']='Descriptive occupancy-mixed count, not an isolated causal failure effect.'
                write(OUT/f'e2_{site.lower()}_run_metrics.json',rows)
            if exp==3:
                block['levels']={lvl:manager_summary([r for r in rows if r['level']==lvl]) for lvl in ('L1','L2','L3','L4')}
                for r in rows:r['_critical_high_loss']=sum(r.get('system_weighted_loss_by_priority',{}).get(p,0) for p in ('CRITICAL','HIGH'))
                block['hypotheses']=adjust([dict(contrast([r for r in rows if r['level']==lvl],base,'B4b',met),level=lvl)
                    for base in ('B1','B2') for lvl in ('L2','L3','L4') for met in ('system_weighted_loss','_critical_high_loss')])
                block['vs_b0']=adjust([dict(contrast([r for r in rows if r['level']==lvl],'B0',mgr,'system_weighted_loss'),level=lvl)
                    for mgr in ('B1','B2','B4b') for lvl in ('L1','L2','L3','L4')])
            data[f'E{exp}'][site]=block
            print(f'E{exp} {site}: {block["primary_n"]} primary',flush=True)
    e4.main()
    data['E4']=read(ROOT/'outputs/experiment4_summary.json')
    for f in (ROOT/'runs/experiment4/primary').glob('*/*/*/seed*/B*/metrics.json'):
        manifest[str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
    write(OUT/'results.json',{'release':'paper_final_20260910','primary_runs':10960,'ablation_runs':180,
                            'inference':'conditional on the fixed scenario panel; matched scenario/seed units',**data})
    write(OUT/'input_metrics_sha256.json',manifest)
    # Compact machine-friendly table for figures and manuscript copying.
    fields=['experiment','site','manager','n','completion_s','deadline_rate','damage','swl','affected_n','recovered_n']
    with (OUT/'main_results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for exp in ('E1','E2','E3'):
            for site,block in data[exp].items():
                for mgr,c in block['summary'].items():
                    w.writerow(dict(experiment=exp,site=site,manager=mgr,n=c['n'],completion_s=c['critical_mission_completion_time_s']['mean'],
                        deadline_rate=c['critical_mission_deadline_violation']['mean'],damage=c['existing_missions_damaged_count']['mean'],
                        swl=c['system_weighted_loss']['mean'],affected_n=c['affected_n'],recovered_n=c['recovered_n']))
    # Final E1 and E2 reports use the exact current release, not prototype values.
    for exp in ('E1','E2'):
        lines=[f'# Experiment {exp[1]} — Final results (paper release 2026-09-10)','',
               'Authoritative data: `outputs/paper_final/results.json`. Raw runs retained; tables regenerated offline.','']
        rr=[]
        for site,b in data[exp].items():
            for mgr,c in b['summary'].items():
                rr.append([site,mgr,c['n'],fmt(c['critical_mission_completion_time_s']['mean']),fmt(c['critical_mission_deadline_violation']['mean']),fmt(c['existing_missions_damaged_count']['mean']),f"{c['recovered_n']}/{c['affected_n']}" if exp=='E2' and c['affected_n'] else 'N/A'])
        lines += [table(['site','manager','n','completion (s)','deadline rate','service damage','recovered/affected'],rr),'']
        if exp=='E1':
            lines += ['## Finding','', 'Shared candidate information enables selective coordination. On Site A, B4b and B2 have close mean completion times, while their service-preemption choices expose a speed–service trade-off. The paired no-table ablation identifies the role of the interface. Cross-site results evaluate the same architecture under adapted geography.','', '## Paired candidate-table ablation: B4b minus B4a','']
            lines += [table(['site','metric','n','difference','95% CI','Holm p'],[[site,t['metric'],t['n'],fmt(t['diff_mean']),str(t['ci95']),fmt(t['p_holm'])] for site,b in data[exp].items() for t in b['ablation']])]
            target=ROOT/'reports/experiment1/EXPERIMENT1_FINAL_RESULTS.md'
        else:
            lines += ['## Finding','', 'The shared execution layer restores an executable path after isolated air-layer failures. Report end-to-end completion/deadline results for all runs; recovery is conditional on an affected critical chain. Observed backend failures remain in the end-to-end comparison.','', '## B4b minus B2: corrected paired family','']
            lines += [table(['site','metric','paired n','difference','95% CI','Holm p'],[[site,t['metric'],t['n'],fmt(t['diff_mean']),str(t.get('ci95')),fmt(t['p_holm'])] for site,b in data[exp].items() for t in b['b4b_vs_b2_family'] if t['metric'] in ('critical_mission_completion_time_s','recovery_time_s')]),'',
                'Recovery-time pairs require both managers to be affected. The 12-item per-site family is retained for continuity, with conditional denominators corrected. Candidate-count reduction remains descriptive because aircraft occupancy also changes the count.']
            target=ROOT/'reports/experiment2/EXPERIMENT2_FINAL_RESULTS.md'
        target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    lines=['# Experiment 3 v2 — Final results (paper release 2026-09-10)','',
           'Three sites, 2,880 primary runs. This replaces v1 final-result claims. Primary outcome: system-weighted loss (SWL).','']
    lines += [table(['site','level','B0','B1','B2','B4b'],[[site,lvl]+[fmt(c[m]['system_weighted_loss']['mean']) for m in MGRS] for site,b in data['E3'].items() for lvl,c in b['levels'].items()]),'',
              '## Finding','', 'Coordination reduces loss where remaining transport options can preserve task deadlines. It offers no SWL gain in some exhausted/slack-limited cells. On Site A L2 all managers score 240; the old +100 cascade-backfire effect disappears after the lifecycle/scheduling correction. B4b does not show a significant SWL advantage over B1/B2 in the corrected compound comparisons.','',
              'B1 and B2 share the same SWL outcomes in these scenarios. B4b has small Site-A deviations; identical decisions are not claimed. CRITICAL+HIGH loss measures priority-weighted outcomes. Unimplemented action-level priority/competition fields are not used as findings.','',
              '## Corrected compound comparisons','',table(['site','baseline','level','metric','n','difference','95% CI','Holm p'],[[site,t['baseline'],t['level'],t['metric'],t['n'],fmt(t['diff_mean']),str(t['ci95']),fmt(t['p_holm'])] for site,b in data['E3'].items() for t in b['hypotheses']]),'',
              'Sources: `outputs/paper_final/results.json`; per-run data `runs/experiment3` and `runs/experiment3_cross_site`, matrix version 2.']
    (ROOT/'reports/experiment3/EXPERIMENT3_FINAL_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    for exp in (2,3):
        p=ROOT/f'reports/experiment{exp}/E{exp}_CROSS_SITE_FINAL_RESULTS.md'
        p.write_text(f'# Experiment {exp}: cross-site final results\n\nThe current three-site tables and corrected inference are consolidated in [EXPERIMENT{exp}_FINAL_RESULTS.md](EXPERIMENT{exp}_FINAL_RESULTS.md).\n\nData release: `outputs/paper_final/results.json`. Earlier report text is retained under `archive/paper_pre_20260910/reports/experiment{exp}/`.\n',encoding='utf-8')
    print('Paper release generated.',flush=True)
if __name__=='__main__':main()
