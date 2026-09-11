"""Assemble the English draft from frozen results; no experiment or policy execution."""
import csv
import hashlib
import json
import re
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
ROOT = WORK.parent
RESULTS = ROOT / 'outputs/paper_final/results.json'
MORPH = ROOT / 'outputs/cross_site/site_morphology_comparison.csv'
INPUTS = [RESULTS, MORPH]
hash_before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUTS}
r = json.loads(RESULTS.read_text(encoding='utf-8'))
managers = ['B0', 'B1', 'B2', 'B4b']
sites = ['A', 'B', 'C']
completion = 'critical_mission_completion_time_s'
deadline = 'critical_mission_deadline_violation'
damage = 'existing_missions_damaged_count'
loss = 'system_weighted_loss'

def number(v, digits=2):
    if v is None:
        return 'N/A'
    if abs(v) < 0.5 * 10 ** -digits:
        v = 0
    return f'{v:.{digits}f}'

def ci(metric, mul=1, digits=2):
    if metric['mean'] is None:
        return 'N/A'
    return f"{number(metric['mean']*mul, digits)} [{number(metric['ci95'][0]*mul, digits)}, {number(metric['ci95'][1]*mul, digits)}]"

def pvalue(p):
    if p is None:
        return 'N/A'
    if p == 1:
        return '1.000'
    return f'{p:.3g}' if p < .001 else f'{p:.6f}'

def table(title, headings, rows, note=''):
    s = f'**{title}**\n\n'
    s += '| ' + ' | '.join(headings) + ' |\n'
    s += '|' + '|'.join(['---'] * len(headings)) + '|\n'
    for row in rows:
        assert len(row) == len(headings)
        s += '| ' + ' | '.join(str(v) for v in row) + ' |\n'
    if note:
        s += '\n' + note
    return s.rstrip()

replacements = {}
morph = list(csv.DictReader(MORPH.open(encoding='utf-8-sig')))
descriptors = [
    ('Directional road length (km)', 'road_length_km', 3, 1),
    ('Road density (km/km²)', 'road_density_km_per_km2', 3, 1),
    ('Nodes', 'node_count', 0, 1),
    ('Directional passenger edges', 'edge_count', 0, 1),
    ('Intersection density (km⁻²)', 'intersection_density', 3, 1),
    ('Mean node degree', 'mean_node_degree', 3, 1),
    ('Dead-end ratio', 'dead_end_ratio', 4, 1),
    ('Mean sampled OD circuity', 'mean_od_circuity', 4, 1),
    ('D1–H1 network distance (km)', 'facility_network_distance_D1_H1', 4, 1),
    ('D1–H1 Euclidean distance (km)', 'facility_euclidean_distance_D1_H1', 4, 1),
    ('D1–H1 circuity', 'D1_H1_circuity', 4, 1),
    ('Reference closure ETA increase (%)', 'critical_link_eta_increase_pct', 2, 1),
]
replacements['TABLE_SITE'] = table('Table 3. Network and reference-service descriptors.',
    ['Descriptor', 'A: Suzhou', 'B: Amsterdam', 'C: Edmonton'],
    [[name] + [number(float(v[key])*mul, d) for v in morph] for name,key,d,mul in descriptors],
    'Source: archived site-morphology comparison. Density denominators use the configured 10.24 km² study area at each site; route and edge definitions follow the original network audit.')

rows = []
for site in sites:
    for manager in managers:
        q = r['E1'][site]['summary'][manager]
        rows.append([site, manager, q['n'], ci(q[completion]), ci(q[deadline], 100), ci(q[damage], digits=3)])
replacements['TABLE_E1'] = table('Table 5. E1 service outcomes: mean [95% interval].',
    ['Site', 'Policy', 'n', 'Completion (s)', 'Deadline violations (%)', 'Damaged services/run'], rows,
    'Completion and damage use t intervals; deadline proportions use Wilson intervals. Intervals summarize the fixed scenario panel and do not estimate variability across cities.')

rows = []
for site in sites:
    for idx, name, mul, digits in [(0,'Completion (s)',1,3),(1,'Damaged services/run',1,3),(2,'Air intervention (pp)',100,3)]:
        q = r['E1'][site]['ablation'][idx]
        rows.append([site, name, q['n'], number(q['diff_mean']*mul,digits),
                     f"[{number(q['ci95'][0]*mul,digits)}, {number(q['ci95'][1]*mul,digits)}]",pvalue(q['p_holm'])])
replacements['TABLE_ABLATION'] = table('Table 6. Paired E1 candidate-interface ablation: B4b minus B4a.',
    ['Site', 'Endpoint', 'Pairs', 'Difference', '95% paired interval', 'Holm p'], rows,
    'The three endpoints form one adjustment family per site. Air intervention is a paired risk difference in percentage points (pp); its displayed interval is descriptive and its p-value comes from exact McNemar inference.')

rows = []
for site in sites:
    for manager in managers:
        q = r['E2'][site]['summary'][manager]
        recovered = f"{q['recovered_n']}/{q['affected_n']}" if q['affected_n'] else 'N/A'
        rows.append([site, manager, q['n'], ci(q[completion]), number(q[deadline]['mean']*100), recovered, ci(q['recovery_success'],100)])
replacements['TABLE_E2'] = table('Table 7. E2 all-run transport outcomes and conditional path restoration.',
    ['Site', 'Policy', 'All runs', 'Completion (s), mean [95% CI]', 'Deadline violations (%)', 'Recovered/affected', 'Recovery (%), Wilson interval'], rows,
    'All-run completion and deadline denominators are 320. Recovery is conditional on the primary air chain actually being affected. B0 has no affected-chain denominator.')

rows = []
for site in sites:
    for idx, name in [(0,'Completion (s)'),(1,'Recovery time (s)')]:
        q = r['E2'][site]['b4b_vs_b2_family'][idx]
        rows.append([site,name,q['n'],number(q['diff_mean'],3),f"[{number(q['ci95'][0],3)}, {number(q['ci95'][1],3)}]",pvalue(q['p_holm'])])
replacements['TABLE_E2_PAIRS'] = table('Table 8. Selected E2 paired comparisons: B4b minus B2.',
    ['Site','Endpoint','Pairs','Difference','95% paired interval','Holm p'],rows,
    'Adjustment retains the original 12-endpoint family per site. Completion uses all matched runs; recovery time uses jointly affected pairs. The displayed 95% intervals are unadjusted, while p-values are multiplicity-adjusted.')

rows = []
for site in sites:
    for level in ['L1','L2','L3','L4']:
        q = r['E3'][site]['levels'][level]
        rows.append([site,level,q['B0'][loss]['n']] + [number(q[m][loss]['mean'],3) for m in managers])
replacements['TABLE_E3'] = table('Table 9. Mean E3 system weighted loss by disturbance/task level.',
    ['Site','Level','Runs/policy'] + managers,rows,
    'Lower is better under the configured priority and flat service penalties. Levels change disturbance structure and demand together; they are not a one-dimensional severity scale.')

rows = []
for arm, policies in r['E4']['4A']['arms'].items():
    q = policies['B4b']['metrics']
    rows.append([int(arm.removeprefix('OBS'))] + [number(policies[m]['metrics'][completion]['mean'],1) for m in managers] +
                [number(q[deadline]['mean']*100,0),number(q['num_manager_decisions']['mean'],0),number(q['llm_total_prompt_tokens']['mean'],1)])
replacements['TABLE_E4A'] = table('Table 10. E4A observation scheduling, completion and B4b input demand.',
    ['Interval (s)','B0 completion (s)','B1 completion (s)','B2 completion (s)','B4b completion (s)','B4b late (%)','B4b decisions/run','B4b prompt tokens/run'], rows,
    'Each policy–arm cell contains 20 runs. Completion is measured from the task release. B4b decision counts include the full scheduled polling horizon; prompt-token means retain the recorded backend outcomes.')

rows = []
for arm, policies in r['E4']['4B']['arms'].items():
    rows.append([int(arm.removeprefix('D'))]+[number(policies[m]['metrics'][completion]['mean'],1) for m in managers]+[number(policies['B4b']['metrics'][deadline]['mean']*100,0)])
replacements['TABLE_E4B'] = table('Table 11. E4B injected execution delay and mean completion duration.',
    ['Delay (s)','B0 (s)','B1 (s)','B2 (s)','B4b (s)','B4b late (%)'],rows,
    'Each policy–arm cell contains 20 runs. These are controlled simulation delays, not measured wall-clock inference delays.')

rows = []
for arm, policies in r['E4']['4C']['arms'].items():
    q=policies['B4b']
    rows.append([int(arm.removeprefix('N')),4,number(q['metrics'][completion]['mean'],1),
                 number((1-q['metrics'][deadline]['mean'])*100,0),q['llm_reliability']['calls'],
                 number(q['llm_reliability']['prompt_tokens_per_logged_call'],1)])
replacements['TABLE_E4C'] = table('Table 12. E4C B4b input burden with an unchanged core fleet.',
    ['Total aircraft records','Core aircraft','Completion (s)','On time (%)','Logged calls (20 runs)','Prompt tokens/logged call'],rows,
    'Each arm contains 20 B4b runs. Added aircraft are unavailable and non-commandable. Token means include retained error calls with zero recorded tokens; active fleet size and legal candidate sets do not grow with input records.')

rows = []
for site in sites:
    for manager in managers:
        q = r['E3'][site]['summary'][manager]
        rows.append([site,manager,q['n'],ci(q[completion]),number(q[deadline]['mean']*100),ci(q[loss],digits=3)])
replacements['TABLE_E3_AGG'] = table('Table B1. Aggregate E3 outcomes across the 12-scenario panel.',
    ['Site','Policy','n','Completion (s), mean [95% CI]','Deadline violations (%)','SWL, mean [95% CI]'],rows)

figures = ['fig01_architecture','fig02_sites','fig03_e1_coordination','fig04_candidate_ablation',
           'fig05_e2_recovery','fig06_e3_compound','fig07_operational','fig08_execution_timeline']
for idx, name in enumerate(figures,1):
    assert (WORK/'figures'/f'{name}.png').exists(), name
    replacements[f'FIG{idx}'] = f'![Figure {idx}: {name[6:].replace("_", " ")}](figures/{name}.png)'
replacements['REFERENCES'] = (WORK/'source/references.md').read_text(encoding='utf-8').strip()
draft = (WORK/'source/manuscript.template.md').read_text(encoding='utf-8')
for key, value in replacements.items():
    assert draft.count('@@'+key+'@@') == 1, key
    draft = draft.replace('@@'+key+'@@',value)
assert not re.search(r'@@\w+@@',draft)
assert sorted(set(map(int,re.findall(r'\[\[(\d+)\]\]',draft)))) == list(range(1,19))
assert len(re.findall(r'^\*\*Figure \d+\.',draft,re.M)) == 8
assert len(re.findall(r'^\*\*Table (?:\d+|B1)\.',draft,re.M)) == 13
dest = WORK/'FIRST_DRAFT_TRANSPORTMETRICA_B.md'
dest.write_text(draft,encoding='utf-8')
assert hash_before == {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUTS}
report = {'draft':dest.name,'release':r['release'],'primary_runs':r['primary_runs'],
          'ablation_runs':r['ablation_runs'],'word_count':len(re.findall(r"\b[\w’–-]+\b",draft)),
          'figures':8,'tables':13,'references':18,'input_sha256':hash_before,
          'source_inputs_unchanged':True,'unresolved_placeholders':False}
(WORK/'.build/manuscript.validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='input_sha256'},indent=2))
