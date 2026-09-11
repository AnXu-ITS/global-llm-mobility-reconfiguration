"""Independent E4 design probes. No simulation setup, stepping, or LLM calls.

Existing unit test functions are invoked directly because pytest is absent.
Only new files inside this audit directory are written.
"""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import inspect
import json
import random
import sys
import traceback
import hashlib
from collections import Counter

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from orchestrator import config
from orchestrator.experiment4_runner import Experiment4Runner,Experiment4BRunner,Experiment4CRunner
from orchestrator.experiment3_runner import Experiment3Runner
from orchestrator.experiment4_fleet import expand_fleet
from orchestrator.phase2_orchestrator import Phase2Orchestrator
from orchestrator.registry import Registry,Mission
from safety.feasibility_checker import FeasibilityChecker


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


testmod=load(ROOT/'tests/test_experiment4_acceptance.py','e4_existing_unit_tests')
result={'unit_tests':[],'probes':{},'scope':'offline unit tests and mock-state probes only'}
for name,func in vars(testmod).items():
    if name.startswith('test_') and callable(func):
        td=OUT/'unit_artifacts'/name;td.mkdir(parents=True,exist_ok=True)
        try:
            func(**({'tmp_path':td} if 'tmp_path' in inspect.signature(func).parameters else {}))
            item={'name':name,'result':'PASS'}
        except Exception as e:
            item={'name':name,'result':'FAIL','error':repr(e),'traceback':traceback.format_exc()}
        result['unit_tests'].append(item)

cfg=config.load_config();e4=testmod._load_e4()
scale=next(s['scale'] for s in e4['scenarios'] if s['id']=='E4_SCALE')
fleets=[]
for n in [5,10,20,30,50]:
    exp=expand_fleet(cfg,n,random.Random(20240601),scale)
    fleets.append({'n':n,'synthetic':exp['n_synthetic'],'extra_failure_count':len(exp['extra_failures']),
        'synthetic_busy_roles':dict(Counter(r[1] for r in exp['fleet_rows'][4:] if r[5])),
        'all_idle_roles':dict(Counter(r[1] for r in exp['fleet_rows'] if not r[5]))})
result['probes']['fleet_mix']=fleets

# Reproduce primary-only trigger regression in the actual E4 inheritance chain.
r=Experiment4Runner.__new__(Experiment4Runner)
r.t=450;r.critical_t=300;r.periodic_s=30;r.support_mission_id='primary'
r.registry=SimpleNamespace(missions={'primary':SimpleNamespace(status='COMPLETED'),
                                     'secondary':SimpleNamespace(status='WAITING')})
result['probes']['secondary_waiting_trigger']={'E4':r._periodic_due(),'E3_v2':Experiment3Runner._periodic_due(r)}

# With successful event decisions and no new actionable task, all 4A arms have
# no additional periodic work. This tests the trigger logic, not aircraft motion.
arms={}
for arm in e4['exp4a']['arms']:
    r.periodic_s=arm['periodic_decision_s'];extra=[]
    for t in range(301,900):
        r.t=t;r.registry.missions['primary'].status='EN_ROUTE' if t<421 else 'COMPLETED'
        if r._periodic_due():extra.append(t)
    arms[arm['id']]={'extra_periodic_calls':len(extra),'event_calls':2}
result['probes']['frequency_arms_success_path']=arms

# Reproduce step-boundary order with fake simulator adapters; no simulator exists.
b=Experiment4BRunner.__new__(Experiment4BRunner);b.t=359;b.audit_snapshot_times=[]
order=[]
b._apply_scheduled_events=lambda t:order.append(['scheduled_events',t])
b.sumo=SimpleNamespace(step=lambda:None)
b.bs=SimpleNamespace(step=lambda:None,state=lambda:{})
b._collect_ground=lambda t:{};b._update_registry=lambda a:None
b._process_ground_fallbacks=lambda t:None;b._log=lambda *args:None
b._process_pending_actions=lambda t:order.append(['pending_execution',t])
b._step_once()
result['probes']['delay_step_order']=order

# Repeated delayed ground commands pass the live checker and reset completion.
reg=Registry();mission=Mission('primary','medical_blood','CRITICAL','V2','V1',deadline_s=480)
reg.add_mission(mission)
mock=SimpleNamespace(registry=reg,sumo=SimpleNamespace(get_route_eta=lambda a,b:182),
    d1_edge='D1',h1_edge='H1',ground_fallback_timers={},
    _record_mission=lambda *a:None,_record_action=lambda *a:None,_record_event=lambda *a:None)
action={'type':'GROUND_FALLBACK','mission_id':'primary'}
Phase2Orchestrator._execute_ground_fallback(mock,360,action,{'decision_id':'D1'})
first=mock.ground_fallback_timers['primary']
valid=FeasibilityChecker(reg,cfg).check(action)
Phase2Orchestrator._execute_ground_fallback(mock,390,action,{'decision_id':'D2'})
result['probes']['duplicate_ground_command']={'first_completion_t':first,'second_live_check':valid,
    'second_completion_t':mock.ground_fallback_timers['primary']}

# Actual analysis helper: a constant shift produces d=0 under current formula.
an=load(ROOT/'tools/analyze_experiment4.py','e4_analysis_review')
result['probes']['constant_difference_effect_size']={'a':[110]*20,'b':[100]*20,
    'reported_cohens_d':an._cohens_d([110]*20,[100]*20)}
result['probes']['paired_all_zero']=an._wilcoxon_paired(
    [{'seed':s,'metrics':1} for s in range(20)], [{'seed':s,'metrics':1} for s in range(20)])

# Verify new E3 runs are present and versioned without making this an E3 re-audit.
import yaml
e3groups={}
for site,folder in [('A','runs/experiment3'),('B','runs/experiment3_cross_site/site_b_amsterdam'),
                    ('C','runs/experiment3_cross_site/site_c_edmonton')]:
    configs=list((ROOT/folder).glob('*/seed*/B*/run_config.yaml'))
    versions=Counter(yaml.safe_load(p.read_text(encoding='utf-8')).get('matrix_version') for p in configs)
    e3groups[site]={'runs':len(configs),'versions':dict(versions)}
result['e3_version_inventory']=e3groups
result['e4_existing_metrics']=len(list((ROOT/'runs/experiment4').rglob('metrics.json')))
paths=[ROOT/'docs/EXPERIMENT4_DESIGN.md',ROOT/'config/experiment4_matrix.yaml',
    ROOT/'config/experiment4_seeds.yaml',ROOT/'orchestrator/experiment4_runner.py',
    ROOT/'orchestrator/experiment4_fleet.py',ROOT/'tools/run_experiment4.py',
    ROOT/'tools/analyze_experiment4.py',ROOT/'tests/test_experiment4_acceptance.py']
result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
result=json.loads(json.dumps(result),parse_constant=lambda value:value)  # Preserve non-finite diagnostics as strings in valid JSON.
(OUT/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True,indent=2))
