"""Offline strip-intersection probe and frozen candidate/action scan.

Only executes geometry function ASTs, never imports the simulator or LLM.
"""
from pathlib import Path
import ast
import json
import math
import typing
from collections import Counter
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
source = (ROOT/'failures/e2_failures.py').read_text(encoding='utf-8')
tree = ast.parse(source)
names = {'haversine_m','_to_xy','point_segment_distance_m','_segment_segment_distance_m',
         'circle_center','point_in_zone','strip_ends','segment_intersects_zone','route_intersects_zone'}
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
ns = dict(math=math,LAT_M=111194.9,**vars(typing))
exec(compile(ast.Module(body=nodes,type_ignores=[]),'geometry_functions_only','exec'),ns)


def crossing(a,b,c,d):
    def cross(p,q,r): return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    return cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0


def fixed_hit(a,b,z):
    if ns['segment_intersects_zone'](a,b,z): return True
    c,d=ns['strip_ends'](z)
    return crossing(a,b,c,d)


z={'type':'strip','lat0':-.005,'lon0':0,'heading_deg':0,'length_m':1111.949,'half_width_m':10}
a,b=(0,-.005),(0,.005)
out={'synthetic_crossing':{'a':a,'b':b,'zone':z,
     'original_hit':ns['segment_intersects_zone'](a,b,z),'corrected_hit':fixed_hit(a,b,z),
     'original_distance_m':ns['_segment_segment_distance_m'](a,b,*ns['strip_ends'](z))},
     'counts':{},'missed_candidates':[],'missed_executed':[]}
for exp in [2,3]:
    for site,suffix in [('A',''),('B','site_b_amsterdam'),('C','site_c_edmonton')]:
        cfg=f'config/experiment{exp}'+(f'_site_{site.lower()}' if site!='A' else '')+'_matrix.yaml'
        matrix=yaml.safe_load((ROOT/cfg).read_text(encoding='utf-8'))[f'experiment{exp}']
        root=ROOT/f'runs/experiment{exp}' if site=='A' else ROOT/f'runs/experiment{exp}_cross_site'/suffix
        count=Counter()
        for s in matrix['scenarios']:
            fs=s.get('failure_schedule',[s.get('failure',{})])
            zones=[f['envelope'] for f in fs if f.get('envelope',{}).get('type')=='strip']
            if not zones: continue
            for p in (root/s['id']).glob('seed*/B*/manager_inputs.jsonl'):
                pp=p.parent/'action_pipeline.jsonl'
                pipeline=[json.loads(l) for l in pp.read_text(encoding='utf-8').splitlines() if l.strip()]
                for line in p.read_text(encoding='utf-8').splitlines():
                    if not line.strip():continue
                    gs=json.loads(line);t=gs['simulation_time']
                    active={x['id'] for x in gs['infrastructure']['failure_zones'] if x['state']=='CLOSED'}
                    zs=[x for x in zones if x['id'] in active]
                    if not zs:continue
                    acs={a['id']:a for a in gs['air']}
                    fac=gs['infrastructure']['landing_sites']
                    def points(acid,route):
                        pos=acs[acid]['position']
                        return [(pos['lat'],pos['lon'])]+[(fac[k]['lat'],fac[k]['lon']) for k in route if k in fac]
                    tables=[gs['candidates']]+gs['candidates'].get('mission_candidates',[])
                    for table in tables:
                        for c in table.get('air',[]):
                            if not c.get('legal') or not c.get('route'):continue
                            count['legal_candidates_tested']+=1
                            pts=points(c['resource_id'],c['route'])
                            for zone in zs:
                                if any(fixed_hit(a,b,zone) for a,b in zip(pts,pts[1:])) and not ns['route_intersects_zone'](pts,zone):
                                    out['missed_candidates'].append(dict(exp=exp,site=site,path=str(p.relative_to(ROOT)),
                                        t=t,resource=c['resource_id'],route=c['route'],zone=zone['id']))
                    for entry in pipeline:
                        action=entry.get('executed_action') or {}
                        if entry['t']!=t or entry['result']!='ISSUED' or not action.get('route') or not action.get('aircraft_id'):continue
                        count['executed_air_routes_tested']+=1
                        pts=points(action['aircraft_id'],action['route'])
                        for zone in zs:
                            if any(fixed_hit(a,b,zone) for a,b in zip(pts,pts[1:])) and not ns['route_intersects_zone'](pts,zone):
                                out['missed_executed'].append(dict(exp=exp,site=site,path=str(pp.relative_to(ROOT)),
                                    t=t,action=action,zone=zone['id']))
        out['counts'][f'E{exp}{site}']=dict(count)
        print(f'E{exp}{site}: {dict(count)}',flush=True)
(OUT/'geometry_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'missed legal candidate records={len(out["missed_candidates"])}; missed executed={len(out["missed_executed"])}',flush=True)
