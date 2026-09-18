"""Focused statistical, artifact and provenance checks; no simulator/API."""
from pathlib import Path
import importlib.util,inspect,json,sys,tempfile,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from paper_stats import holm,paired,mcnemar
from paper_metrics import execution_metrics
from frozen_compatibility import check_manifest
OUT=ROOT/'outputs/paper_final'
checks=[]
def check(name,fn):
    try:fn();checks.append({'name':name,'status':'PASS'})
    except Exception as exc:checks.append({'name':name,'status':'FAIL','error':repr(exc)})
def need(ok):
    if not ok:raise AssertionError('condition not met')
def read(p):return json.loads(p.read_text(encoding='utf-8'),parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
check('Holm cumulative max',lambda:need(holm([.01,.011,.012])==[.03,.03,.03]))
check('Holm nonfinite retains family',lambda:need(holm([.01,float('nan')])==[.02,1.]))
check('McNemar exact 5:0',lambda:need(mcnemar([0]*5,[1]*5)['p']==.0625))
check('Constant equal paired outcomes',lambda:need(paired([100]*20,[100]*20)['p']==1.))
check('Constant nonzero effect undefined',lambda:need(paired([100]*20,[110]*20)['cohens_d'] is None))
def metrics_probe():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)
        (p/'actions.csv').write_text('t,action_type,aircraft_id,mission_id,result\n10,NO_ACTION,,,ISSUED\n19,REASSIGN,B,m,ISSUED\n20,REASSIGN,C,m,ISSUED\n21,REASSIGN,B,m,ISSUED\n',encoding='utf-8')
        m=execution_metrics(p,{'failure_time':10,'critical_mission_id':'m','affected_critical':False,'recovery_success':False})
        need(m['failure_to_replan_latency_s']==9 and m['recovery_success'] is None and m['decision_switch_count']==2 and m['decision_oscillation_count']==1)
check('NO_ACTION, conditional recovery, switch vs oscillation',metrics_probe)
d=read(OUT/'results.json')
check('Release counts',lambda:need(sum(d[e][s]['primary_n'] for e in ('E1','E2','E3') for s in 'ABC')+1360==10960))
t=next(t for t in d['E2']['A']['b4b_vs_b2_family'] if t['metric']=='recovery_time_s')
check('E2 conditional 191 pairs',lambda:need(t['n']==191 and abs(t['diff_mean']-3.926701570680628)<1e-10))
check('E3 v2 L2 240 and refreshed hypothesis file',lambda:need(d['E3']['A']['levels']['L2']['B4b']['system_weighted_loss']['mean']==240 and read(ROOT/'outputs/experiment3/hypothesis_tests.json')['h3a'][0]['b4b_mean']==240))
check('E4 corrected latency and conditional denominator',lambda:need(d['E4']['4A']['arms']['OBS30']['B4b']['metrics']['failure_to_replan_latency_s']['mean']==19 and d['E4']['4A']['arms']['OBS300']['B4b']['metrics']['recovery_success']['n']==0))
def candidate_sets():
    compared=0
    for mgr in ('B0','B1','B2','B4b'):
        for seed in range(20240601,20240621):
            refs={}
            for arm in ('N05','N10','N20','N30','N50'):
                p=ROOT/f'runs/experiment4/primary/4C/{arm}/E4_INPUT/seed{seed}/{mgr}/manager_inputs.jsonl'
                inputs=[json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line]
                for i,g in enumerate(inputs[:2]):
                    need(g['simulation_time']==(300,360)[i])
                    legal=sorted(c['resource_id'] for c in g['candidates']['air'] if c.get('legal'))
                    # Initial and failure-triggered snapshots occur at 300/360;
                    # an extra transport retry can only add a later third call.
                    if arm=='N05':refs[i]=legal
                    else:need(legal==refs[i]);compared+=1
    need(compared==640)
check('E4C matched-stage legal candidate sets, 640 comparisons',candidate_sets)
def original_hashes():
    for p in (ROOT/'reports/writing_readiness_20260910').glob('*_metrics_sha256.json'):
        for name,want in read(p).items():need(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==want)
check('All 10960 primary metrics unchanged since audit',original_hashes)
bad,transitions=check_manifest(ROOT,read(ROOT/'outputs/file_hashes_final.json'))
check('Historical manifest exact reconstruction',lambda:need(not bad and len(transitions)==1))
(OUT/'historical_source_transition.json').write_text(json.dumps(transitions,indent=2),encoding='utf-8')
spec=importlib.util.spec_from_file_location('e4accept',ROOT/'tests/test_experiment4_acceptance.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for name,fn in inspect.getmembers(module,inspect.isfunction):
    if name.startswith('test_'):
        with tempfile.TemporaryDirectory() as td:check('E4 '+name,lambda fn=fn,td=td:fn(tmp_path=Path(td)))
(OUT/'verification.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
for c in checks:print(c)
sys.exit(any(c['status']=='FAIL' for c in checks))
