"""Read-only artifact audit; writes only reports/writing_readiness_20260910/."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, inspect, importlib.util, json, statistics, sys, tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'reports/writing_readiness_20260910'
OUT.mkdir(exist_ok=True)
result = {'datasets': {}, 'e4_arms': {}, 'e3_swl': {}, 'tests': []}
datasets = [
    ('E1_A', 'experiment1_final', 960),
    ('E1_B', 'experiment1_cross_site/site_b_amsterdam', 960),
    ('E1_C', 'experiment1_cross_site/site_c_edmonton', 960),
    ('E2_A', 'experiment2', 1280),
    ('E2_B', 'experiment2_cross_site/site_b_amsterdam', 1280),
    ('E2_C', 'experiment2_cross_site/site_c_edmonton', 1280),
    ('E3_A', 'experiment3', 960),
    ('E3_B', 'experiment3_cross_site/site_b_amsterdam', 960),
    ('E3_C', 'experiment3_cross_site/site_c_edmonton', 960),
    ('E4', 'experiment4/primary', 1360),
]
e4 = yaml.safe_load((ROOT/'config/experiment4_matrix.yaml').read_text(encoding='utf-8'))['experiment4']
e4hash = hashlib.sha256(json.dumps(e4, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
for name, directory, expected in datasets:
    base = ROOT/'runs'/directory
    pattern = '*/*/*/seed*/B*/metrics.json' if name == 'E4' else '*/seed*/B*/metrics.json'
    files = sorted(base.glob(pattern))
    counts, cells, states, versions = Counter(), defaultdict(set), Counter(), Counter()
    issues, rows, hashes = [], [], []
    for f in files:
        d = json.loads(f.read_text(encoding='utf-8'))
        mgr = f.parent.name
        counts[mgr] += 1
        if mgr not in ('B0','B1','B2','B4b'): continue
        rel = f.relative_to(base)
        cells['/'.join(rel.parts[:-3]) + '/' + mgr].add(d['seed'])
        states[str(d.get('critical_mission_final_state'))] += 1
        rows.append((f,d,mgr))
        hashes.append((str(f.relative_to(ROOT)), hashlib.sha256(f.read_bytes()).hexdigest()))
        for artifact in ('run_config.yaml','actions.csv','events.csv','registry_final.json'):
            if not (f.parent/artifact).is_file(): issues.append(str(rel)+': missing '+artifact)
        ct, deadline = d.get('critical_mission_completion_t'), d.get('critical_mission_deadline_s')
        truth = (ct > deadline) if ct is not None and deadline is not None else (deadline is not None and d.get('duration_s',0) > deadline)
        if bool(d.get('critical_mission_deadline_violation')) != truth:
            issues.append(str(rel)+': deadline mismatch')
        if name.startswith('E3') or name == 'E4':
            rc = yaml.safe_load((f.parent/'run_config.yaml').read_text(encoding='utf-8'))
            versions[rc.get('matrix_version')] += 1
            if rc.get('matrix_version') != 2: issues.append(str(rel)+': version !=2')
            if name == 'E4':
                if rc.get('matrix_hash') != e4hash: issues.append(str(rel)+': matrix hash mismatch')
                meta = json.loads((f.parent/'run_meta.json').read_text(encoding='utf-8'))
                if meta.get('cohort') != 'primary': issues.append(str(rel)+': cohort mismatch')
    primary = sum(counts[m] for m in ('B0','B1','B2','B4b'))
    result['datasets'][name] = {'expected_primary':expected,'primary':primary,'counts':dict(counts),'cells':len(cells),'bad_seed_cells':{k:len(v) for k,v in cells.items() if v != set(range(20240601,20240621))},'states':dict(states),'versions':dict(versions),'issues':issues,'mean_completion':{m:statistics.mean(d['critical_mission_completion_time_s'] for _,d,x in rows if x==m and d.get('critical_mission_completion_time_s') is not None) for m in ('B0','B1','B2','B4b')}}
    (OUT/(name+'_metrics_sha256.json')).write_text(json.dumps(dict(hashes),indent=2),encoding='utf-8')
    if name.startswith('E3'):
        groups = defaultdict(list)
        for f,d,m in rows: groups[d['level']+'/'+m].append(d['system_weighted_loss'])
        result['e3_swl'][name] = {k:statistics.mean(v) for k,v in groups.items()}
        result['datasets'][name]['null_priority_metric'] = sum(d.get('priority_consistency_violations') is None for _,d,_ in rows)
        result['datasets'][name]['null_competition_metric'] = sum(d.get('resource_competition_correct') is None for _,d,_ in rows)
    if name == 'E4':
        groups=defaultdict(list)
        for f,d,m in rows: groups[d['sub_experiment']+'/'+d['arm_id']+'/'+m].append(d)
        keys=['critical_mission_completion_time_s','critical_mission_deadline_violation','recovery_success','recovery_time_s','failure_to_replan_latency_s','failure_discovery_latency_s','num_manager_decisions','llm_total_prompt_tokens','legal_candidate_count_mean','illegal_selection_count','absent_selection_count','stale_rejected_count','superseded_action_count']
        for k,ds in groups.items():
            result['e4_arms'][k]={'n':len(ds),**{metric:statistics.mean(v) if (v:=[d[metric] for d in ds if d.get(metric) is not None]) else None for metric in keys}}
    print(name, primary, '/',expected,'ablation',counts.get('B4a',0),'issues',len(issues),flush=True)

# Direct execution of the repository's offline E4 functions, no pytest/sim/API.
spec=importlib.util.spec_from_file_location('e4accept',ROOT/'tests/test_experiment4_acceptance.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for name,fn in inspect.getmembers(module,inspect.isfunction):
    if not name.startswith('test_'): continue
    with tempfile.TemporaryDirectory(prefix='writing-audit-') as td:
        try:
            fn(tmp_path=Path(td)); status='PASS'; error=None
        except Exception as exc: status='FAIL'; error=repr(exc)
    result['tests'].append({'name':name,'status':status,'error':error})
result['scope']='All primary metrics and core artifact existence; E3/E4 config versions; E4 matrix hash/cohort; E4 offline tests. No simulator or LLM reruns; no blanket validation of all trajectories.'
(OUT/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('E4 tests',Counter(x['status'] for x in result['tests']),flush=True)
