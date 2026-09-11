"""Read-only audit of frozen E2/E3 runs. Writes only beside this script.

No simulator imports, network requests, experiment LLM calls, or source edits.
Run from repository root: python reports/independent_e23_20260908/audit.py
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import warnings
from collections import Counter, defaultdict

import numpy as np
import yaml
from scipy import stats

warnings.filterwarnings('ignore', category=RuntimeWarning)
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MANAGERS = ['B0', 'B1', 'B2', 'B4b']
CONT = ['critical_mission_completion_time_s', 'recovery_time_s',
        'failure_to_replan_latency_s', 'existing_missions_damaged_count',
        'candidate_set_reduction_delta']
BIN = ['critical_mission_deadline_violation', 'recovery_success',
       'recovered_completed', 'ground_fallback_rate',
       'failure_induced_ground_fallback', 'necessary_ground_fallback_correct',
       'air_intervention']
ACTIONABLE = {'WAITING', 'NEEDS_REPLAN', 'INTERRUPTED'}
manifest = {}


def read(p):
    b = p.read_bytes()
    manifest[str(p.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(b).hexdigest()
    return b.decode('utf-8-sig')


def js(p):
    return json.loads(read(p))


def lines(p):
    return [json.loads(x) for x in read(p).splitlines() if x.strip()] if p.exists() else []


def finite(x):
    return x is not None and math.isfinite(float(x))


def mean(v):
    v = [float(x) for x in v if finite(x)]
    return float(np.mean(v)) if v else None


def paired(a, b):
    xy = [(float(x), float(y)) for x, y in zip(a, b) if finite(x) and finite(y)]
    if len(xy) < 2:
        return {'n': len(xy), 'p': 1.0, 'note': 'insufficient paired observations'}
    a, b = np.array(xy).T
    d = b - a
    if np.all(d == 0):
        p, wp = 1.0, 1.0
    else:
        p = float(stats.ttest_rel(b, a).pvalue)
        wp = float(stats.wilcoxon(d).pvalue)
    se = float(np.std(d, ddof=1) / np.sqrt(len(d)))
    ci = float(stats.t.ppf(.975, len(d)-1)) * se
    return {'n': len(d), 'base_mean': mean(a), 'b4b_mean': mean(b),
            'diff': mean(d), 'nonzero_pairs': int(np.count_nonzero(d)),
            'ci95': [mean(d)-ci, mean(d)+ci], 'p': p, 'wilcoxon_p': wp}


def mc(a, b):
    xy = [(bool(x), bool(y)) for x, y in zip(a, b) if finite(x) and finite(y)]
    n01 = sum(not x and y for x, y in xy)
    n10 = sum(x and not y for x, y in xy)
    p = float(stats.binomtest(n01, n01+n10, .5, alternative='two-sided').pvalue) if n01+n10 else 1.0
    return {'n': len(xy), 'n01': n01, 'n10': n10, 'p': p}


def holm(tests, pkey='p', outkey='holm_p'):
    # Undefined all-identical comparisons are retained conservatively as p=1.
    ps = [float(t[pkey]) if finite(t.get(pkey)) else 1.0 for t in tests]
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    prev = 0.
    for k, i in enumerate(order):
        prev = max(prev, min(1., ps[i]*(len(ps)-k)))
        tests[i][outkey] = prev


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


allrows = []
summary = {'scope': {}, 'e2_stats': {}, 'e3_stats': {}, 'e3_cells': [],
           'input_and_actions': {}, 'e3_differences': [], 'integrity_issues': []}
for exp in [2, 3]:
    seeds = yaml.safe_load(read(ROOT / f'config/experiment{exp}_seeds.yaml'))['primary_seeds']
    for site, suffix in [('A',''), ('B','site_b_amsterdam'), ('C','site_c_edmonton')]:
        cfg = f'config/experiment{exp}' + (f'_site_{site.lower()}' if site != 'A' else '') + '_matrix.yaml'
        matrix = yaml.safe_load(read(ROOT / cfg))[f'experiment{exp}']
        root = ROOT / f'runs/experiment{exp}' if site == 'A' else ROOT / f'runs/experiment{exp}_cross_site' / suffix
        rows, missing = [], []
        initial = defaultdict(dict)
        signatures = defaultdict(dict)
        competition = Counter()
        scenario_multimission = Counter()
        healthy_penalty_runs = Counter()
        for scenario in matrix['scenarios']:
            sid = scenario['id']
            for seed in seeds:
                for manager in MANAGERS:
                    rd = root / sid / f'seed{seed}' / manager
                    mp = rd / 'metrics.json'
                    if not mp.exists():
                        missing.append(str(mp.relative_to(ROOT)))
                        continue
                    m = js(mp)
                    for name in ['manager_inputs.jsonl', 'action_pipeline.jsonl', 'events.csv',
                                 'registry_final.json', 'runtime.json', 'run_meta.json']:
                        if not (rd/name).exists():
                            summary['integrity_issues'].append(str((rd/name).relative_to(ROOT)))
                    row = dict(m, experiment=exp, site=site, mgr=manager, sid=sid,
                               seed=seed, path=str(rd.relative_to(ROOT)).replace('\\', '/'))
                    row['level'] = scenario.get('level')
                    inputs = lines(rd/'manager_inputs.jsonl')
                    pipeline = lines(rd/'action_pipeline.jsonl')
                    initial[(sid,seed)][manager] = digest(inputs[0]) if inputs else None
                    signatures[(sid,seed)][manager] = digest([
                        (p['t'], p.get('executed_action')) for p in pipeline if p.get('result') == 'ISSUED'])
                    if exp == 3:
                        reg = js(rd/'registry_final.json')
                        healthy_loss = 0.
                        for mission in reg['missions']:
                            mid = mission['mission_id']
                            if (not mid.startswith('M-CRITICAL-') and mission['status'] == 'EN_ROUTE'
                                    and mission['deadline_s'] > m['duration_s']):
                                healthy_loss += m['system_weighted_loss_by_mission'].get(mid, 0.)
                        row['pending_before_deadline_penalty'] = healthy_loss
                        # Sensitivity only; not a repaired physical experiment or validated welfare metric.
                        row['swl_sensitivity_exclude_pending'] = m['system_weighted_loss'] - healthy_loss
                        row['critical_high_loss'] = sum(m['system_weighted_loss_by_priority'].get(k,0) for k in ['CRITICAL','HIGH'])
                        healthy_penalty_runs[manager] += healthy_loss > 0
                        second = next((x for x in reg['missions'] if x['mission_id']=='M-CRITICAL-002'), None)
                        row['second_state'] = second['status'] if second else None
                        row['second_mode'] = second['mode'] if second else None
                        for inp in inputs:
                            ms = [x for bucket in ['new','existing'] for x in inp.get('missions',{}).get(bucket,[]) if x.get('state') in ACTIONABLE]
                            emergency_ms = [x for x in ms if x['id'].startswith('M-CRITICAL-')]
                            if len(ms)>=2:
                                competition[f'{manager}_all_multi_decisions'] += 1
                                scenario_multimission[f'{manager}:{sid}'] += 1
                            if len(emergency_ms)>=2:
                                competition[f'{manager}_two_emergency_decisions'] += 1
                            if inp.get('candidates',{}).get('mission_candidates'):
                                competition[f'{manager}_table_multi_decisions'] += 1
                    rows.append(row)
        summary['scope'][f'E{exp}{site}'] = {'expected': len(matrix['scenarios'])*len(seeds)*4,
            'found': len(rows), 'missing': missing, 'scenarios': len(matrix['scenarios']), 'seeds': len(seeds)}
        summary['input_and_actions'][f'E{exp}{site}'] = {
            'initial_all_four_equal': sum(len(x)==4 and len(set(x.values()))==1 for x in initial.values()),
            'pairs': len(initial),
            'issued_B1_B2_equal': sum(x.get('B1')==x.get('B2') for x in signatures.values()),
            'issued_B2_B4b_equal': sum(x.get('B2')==x.get('B4b') for x in signatures.values()),
            'actionable_competition': dict(competition), 'multi_mission_scenarios': dict(scenario_multimission),
            'runs_with_pending_penalty': dict(healthy_penalty_runs)}
        bykey = {(r['sid'],r['seed'],r['mgr']):r for r in rows}
        ordered_keys = sorted((s['id'],seed) for s in matrix['scenarios'] for seed in seeds)
        b2 = [bykey[k+('B2',)] for k in ordered_keys if k+('B2',) in bykey and k+('B4b',) in bykey]
        b4 = [bykey[k+('B4b',)] for k in ordered_keys if k+('B2',) in bykey and k+('B4b',) in bykey]
        if exp == 2:
            ts = []
            for met in CONT + BIN:
                st = (paired if met in CONT else mc)([r.get(met) for r in b2],[r.get(met) for r in b4])
                ts.append(dict(st, metric=met))
            holm(ts)
            scenario_tests = []
            for sid in [s['id'] for s in matrix['scenarios']]:
                a = [r for r in b2 if r['sid']==sid]
                b = [r for r in b4 if r['sid']==sid]
                for met in CONT+BIN:
                    st=(paired if met in CONT else mc)([r.get(met) for r in a],[r.get(met) for r in b])
                    scenario_tests.append(dict(st, metric=met, sid=sid))
            holm(scenario_tests)
            aggregates = {}
            for mgr in MANAGERS:
                rr = [r for r in rows if r['mgr']==mgr]
                affected = [r for r in rr if r['affected_critical']]
                aggregates[mgr] = {'n':len(rr), 'completion':mean([r['critical_mission_completion_time_s'] for r in rr]),
                    'deadline_violation':mean([r['critical_mission_deadline_violation'] for r in rr]),
                    'affected_n':len(affected), 'recovered_affected_n':sum(bool(r['recovery_success']) for r in affected),
                    'unconditional_recovery':mean([r['recovery_success'] for r in rr]),
                    'damage':mean([r['existing_missions_damaged_count'] for r in rr])}
            summary['e2_stats'][site] = {'aggregate_tests_family_12':ts,'per_scenario_tests':scenario_tests,'aggregates':aggregates}
        else:
            ts = []
            for other in ['B1','B2']:
                for lvl in ['L2','L3','L4']:
                    keys = [k for k in ordered_keys if bykey[k+('B4b',)]['level']==lvl]
                    for met in ['system_weighted_loss','critical_high_loss']:
                        st=paired([bykey[k+(other,)][met] for k in keys],[bykey[k+('B4b',)][met] for k in keys])
                        ts.append(dict(st, metric=met, level=lvl, other=other))
            holm(ts)
            summary['e3_stats'][site] = ts
            for lvl in ['L1','L2','L3','L4']:
                for mgr in MANAGERS:
                    rr=[r for r in rows if r['level']==lvl and r['mgr']==mgr]
                    summary['e3_cells'].append(dict(site=site,level=lvl,manager=mgr,n=len(rr),
                        swl=mean([r['system_weighted_loss'] for r in rr]),
                        pending_penalty=mean([r['pending_before_deadline_penalty'] for r in rr]),
                        sensitivity=mean([r['swl_sensitivity_exclude_pending'] for r in rr]),
                        completion=mean([r['critical_mission_completion_time_s'] for r in rr]),
                        second_modes=dict(Counter(r['second_mode'] for r in rr if r['second_mode']))))
            for a,b in zip(b2,b4):
                if a['system_weighted_loss'] != b['system_weighted_loss']:
                    summary['e3_differences'].append({'site':site,'sid':a['sid'],'seed':a['seed'],
                        'b2_swl':a['system_weighted_loss'],'b4b_swl':b['system_weighted_loss'],
                        'b2_by_mission':a['system_weighted_loss_by_mission'],'b4b_by_mission':b['system_weighted_loss_by_mission'],
                        'b2':a['path'],'b4b':b['path']})
        allrows.extend(rows)
        print(f'E{exp} {site}: {len(rows)} / {len(matrix["scenarios"])*len(seeds)*4}; audit read complete', flush=True)

# Record reviewed code, configs and reports separately from original run hashes.
for folder in ['orchestrator','failures','managers','tools','reports/experiment2','reports/experiment3','config']:
    for p in (ROOT/folder).rglob('*'):
        if p.is_file() and p.suffix in {'.py','.yaml','.json','.md'}:
            read(p)

def clean(x):
    if isinstance(x,dict): return {k:clean(v) for k,v in x.items()}
    if isinstance(x,list): return [clean(v) for v in x]
    if isinstance(x,float) and not math.isfinite(x): return None
    return x

(OUT/'audit_results.json').write_text(json.dumps(clean(summary),ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'source_sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'run_summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
    cols=['experiment','site','sid','seed','mgr','level','critical_mission_completion_time_s',
          'critical_mission_deadline_violation','affected_critical','recovery_success',
          'system_weighted_loss','pending_before_deadline_penalty','swl_sensitivity_exclude_pending',
          'second_state','second_mode','path']
    w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(allrows)
print(f'Wrote independent outputs to {OUT}; {len(manifest)} SHA256 entries',flush=True)
