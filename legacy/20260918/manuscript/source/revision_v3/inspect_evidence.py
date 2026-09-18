from pathlib import Path
import json,csv,collections,sys
W=Path(__file__).resolve().parents[2]; R=W.parent
out={}
def rd(p): return json.loads(p.read_text(encoding='utf-8'))
for site,base in [('A',R/'runs/experiment3'),('B',R/'runs/experiment3_cross_site/site_b_amsterdam'),('C',R/'runs/experiment3_cross_site/site_c_edmonton')]:
    counts=collections.Counter(); expired=[]; nr=0; rows=[]
    for p in base.glob('*/seed*/B*/registry_final.json'):
        if p.parent.name not in ['B0','B1','B2','B4b']:continue
        nr+=1; met=rd(p.parent/'metrics.json'); horizon=met['duration_s']
        for m in rd(p)['missions']:
            if m['deadline_s']<=horizon:
                counts[m['status']]+=1
                if m['status'] in ['EN_ROUTE','ASSIGNED']:expired.append([str(p.relative_to(R)),m])
        rows.append(met|{'policy':p.parent.name,'path':str(p.parent.relative_to(R))})
    out[site]={'runs':nr,'deadline_le_horizon_states':dict(counts),'expired_ongoing':expired}
    (W/f'source/revision_v3/e3_{site}_metrics.json').write_text(json.dumps(rows),encoding='utf-8')
out['result_schema']={}
r=rd(R/'outputs/paper_final/results.json')
for e in r:
    out['result_schema'][e]=list(r[e]) if isinstance(r[e],dict) else type(r[e]).__name__
out['e2_schema']=list(rd(R/'outputs/paper_final/e2_a_run_metrics.json')[0])
out['e1_example']=rd(R/'runs/experiment1_final/E1_H_H_high/seed20240601/B2/metrics.json')
(W/'source/revision_v3/initial_evidence.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
