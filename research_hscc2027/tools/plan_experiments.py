"""Expand the design into auditable planned cells. Never launches a simulator/LLM."""
from __future__ import annotations
import argparse, csv, hashlib, itertools, json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=ROOT.parent
CONFIG=ROOT/'config/experiment_protocol.v1.json'

def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate(p,llm):
    assert p['gates']['run_enabled'] is False, 'Design exporter cannot authorize execution'
    assert p['runtime']['implementation_status'] in ('not_implemented','development_slice_verified_full_gates_pending')
    assert (llm['model'],llm['reasoning_effort'])==('gpt-6-astra','high')
    assert llm['backend']=='codex_cli' and llm['authentication']=='existing_chatgpt_login'
    assert llm['fallback_model'] is None and not llm['legacy_endpoint_reuse']
    assert p['runtime']['snapshot_policy']=='immutable_visible_state_created_before_queueing'
    methods=p['methods']
    assert methods['X_LST']['time_rule']==methods['X_FULL']['time_rule']
    assert methods['X_FIX']['time_rule']==methods['X_TX']['time_rule']
    assert [methods[m]['resource_plan'] for m in ['X_FIX','X_LST','X_TX','X_FULL']]==[False,False,True,True]
    seeds=p['seed_sets']
    assert set(seeds['development']).isdisjoint(seeds['primary'])
    assert set(seeds['development']).isdisjoint(seeds['native'])
    assert set(seeds['primary']).isdisjoint(seeds['native'])
    budget=llm['proposed_budget']
    assert budget['calibration_and_admission']+budget['formal_run_launch_upper_bound']+budget['rerun_and_operational_reserve']==budget['total_ceiling']
    assert budget['reserve_before_native_block']==3*llm['execution']['max_proposal_launches_per_run']

def expand(p,llm):
    registry=json.loads((ROOT/'config'/p['site_registry']).read_text(encoding='utf-8')) if 'site_registry' in p else None
    rows=[]
    for group in p['groups']:
        before=len(rows)
        axes=group['axes']; keys=list(axes)
        for vals in itertools.product(*(axes[k] for k in keys)):
            values={**group.get('fixed',{}),**dict(zip(keys,vals))}
            for seed in p['seed_sets'][group['seeds']]:
                cell={'group':group['id'],'cohort':group['cohort'],'mode':group['mode'],'seed':seed,**values}
                if registry:
                    cell['site_id']=cell.get('site_id',p['scenario_sites'].get(cell['scenario']))
                    assert cell['site_id'] in registry['sites']
                    cell['scenario_family']=cell['scenario']
                    cell['fixture_version']='pending_formal_freeze_v0.2'
                assert cell['method'] in p['methods']
                assert group['mode']!='ASYNC_EMULATED' or 'delay_s' in cell
                # Environment identity intentionally excludes method, latency and group.
                env={'protocol':p['protocol_id'],'scenario':cell['scenario'],'seed':seed,
                     'fault_offset_s':cell.get('fault_offset_s',0),
                     'handoff_s':cell.get('handoff_s',p['runtime']['default_handoff_s']),
                     'fleet_n':cell.get('fleet_n',4),'load_ratio':cell.get('load_ratio',None)}
                if registry:
                    site=registry['sites'][cell['site_id']]
                    env.update({'site_id':cell['site_id'],'site_asset_hashes':site['asset_hashes'],'scenario_family':cell['scenario_family'],'fixture_version':cell['fixture_version']})
                    if cell['group'].startswith('R6'):env['fleet_n']=site['air_fleet_n']
                    cell['environment_identity_status']='planning_only_formal_fixture_missing'
                    cell['network_sha256']=site['asset_hashes']['network']
                pair={k:v for k,v in cell.items() if k!='method'}
                cell['environment_id']=digest(env)[:20]
                if registry:pair['environment_id']=cell['environment_id']
                cell['pair_id']=digest(pair)[:20]
                cell['planned_cell_id']=group['id']+'-'+digest(cell)[:16]
                cell['proposer']='ASTRA_HIGH_CODEX' if group['mode']=='ASYNC_NATIVE' else ('B2_FAST' if cell['method']=='B2_FAST' else 'SCRIPTED_V1')
                cell['llm_model']=llm['model'] if group['mode']=='ASYNC_NATIVE' else ''
                cell['reasoning_effort']=llm['reasoning_effort'] if group['mode']=='ASYNC_NATIVE' else ''
                cell['status']='planned_not_executed'
                cell['fixture_status']='not_materialized'
                cell['runtime_signature']='pending_implementation_and_freeze'
                if group['mode']=='ASYNC_NATIVE':
                    index=p['seed_sets']['native'].index(seed)*2+['S1','S3'].index(cell['scenario'])
                    order=list(itertools.permutations(group['axes']['method']))[index%6]
                    cell['within_block_order']=order.index(cell['method'])+1
                rows.append(cell)
        assert len(rows)-before==group['expected_runs'],group['id']
    assert len({r['planned_cell_id'] for r in rows})==len(rows)
    # Declare, never double-count as independent observations, identical phase-zero anchors.
    anchors={(r['scenario'],r['seed'],r['method']):r['planned_cell_id'] for r in rows
             if r['group']=='R2_MAIN' and r['delay_s']==30}
    for r in rows:
        if r['group']=='R2_PHASE' and r['fault_offset_s']==0:
            r['reusable_anchor_cell_id']=anchors[(r['scenario'],r['seed'],r['method'])]
    return rows

def r0_plan():
    jobs=[(s,'B0',60,360,False) for s in range(20240601,20240621)]
    jobs += [(20240601,m,d,f,False) for m,d,f in [('B0',0,360),('B0',30,360),('B0',60,359),('B0',60,361),('B1',60,360),('B2',60,360)]]
    jobs += [(20240601,'B1',60,360,True)]
    bridge={('B0',0,360),('B0',30,360),('B0',60,360),('B0',60,359),('B0',60,361),('B2',60,360)}
    rows=[]
    for seed,method,delay,fault,baseline in jobs:
        rel=f'legacy/20260918/manuscript/source/revision_v3/regression/D{delay:02d}_F{fault}{"_baseline" if baseline else ""}/seed{seed}/{method}/metrics.json'
        path=WORKSPACE/rel
        assert path.is_file(),f'Missing historical R0 anchor: {rel}'
        metrics=json.loads(path.read_text(encoding='utf-8'))
        row={'group':'R0_REPLAY','seed':seed,'method':method,'delay_s':delay,'failure_time_s':fault,
             'executor':'legacy_original' if baseline else 'legacy_corrected',
             'historical_metrics':rel,'historical_sha256':file_hash(path),
             'expected_task_duration_s':metrics['critical_mission_completion_time_s'],
             'expected_completion_absolute_s':metrics.get('critical_mission_completion_t',''),
             'status':'planned_not_executed','output_root':'research_hscc2027/runs/regression_new_only'}
        rows.append(row)
        if seed==20240601 and not baseline and (method,delay,fault) in bridge:
            rows.append({**row,'group':'R0_BRIDGE','executor':'runtime_v2_legacy_compatible_pending'})
    assert len(rows)==33
    return rows

def write_csv(path,rows):
    fields=sorted({k for r in rows for k in r})
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Verify generated design files without writing')
    parser.add_argument('--protocol',choices=['v0.1','v0.2'],default='v0.2',help='Select preserved v0.1 snapshot or current six-site design')
    parser.add_argument('--refresh-design',action='store_true',help='Replace only the three generated planning files while still in design-only state')
    args=parser.parse_args()
    assert not (args.check and args.refresh_design),'Use check or refresh, not both'
    config_path=ROOT/'config'/('experiment_protocol.v1.json' if args.protocol=='v0.1' else 'experiment_protocol.v2.json')
    p=json.loads(config_path.read_text(encoding='utf-8'))
    llm_path=ROOT/'config'/p['model_config']
    llm=json.loads(llm_path.read_text(encoding='utf-8'))
    validate(p,llm); rows=expand(p,llm); r0=r0_plan()
    counts=dict(sorted(Counter(r['group'] for r in rows).items()))
    core=sum(counts[g] for g in ['R2_MAIN','R2_PHASE','R3_HANDOFF','R4_SCALE','R2_B2'])
    development=sum(counts[g] for g in ['DEV_CORE','DEV_B2','TUNE_TIMEOUT','TUNE_MARGIN'])
    assert core==3060 and development==428 and counts['R5_NATIVE']==60
    cross=counts.get('R6_SITE',0);optional=320+counts.get('R6_B2',0)
    summary={'protocol_id':p['protocol_id'],'status':'offline_design_validated_not_executed',
        'planned_cells_by_group':counts,'core_controlled_planned_cells':core+cross,'native_planned_runs':60,
        'development_planned_cells':development,'r0_planned_runs':len(r0),
        'base_transport_plan_slots':core+cross+60+development+len(r0),'optional_plan_slots':optional,
        'phase_zero_reusable_anchors':sum('reusable_anchor_cell_id' in r for r in rows),
        'independent_unit':'whole_seed_block_not_run_or_task',
        'experimental_model_calls_made':0,'simulations_executed':0,
        'source_hashes':{str(f.relative_to(ROOT)):file_hash(f) for f in [config_path,llm_path,ROOT/'schemas/proposal.schema.json',ROOT/'prompts/astra_proposer_v1.txt']}}
    if 'site_registry' in p:
        assert cross==240 and counts['R6_B2']==120
        summary['cross_site_core_planned_runs']=cross
        summary['map_screening_runs']='separate_controller_free_development_ledger_not_in_transport_counts'
        summary['source_hashes'][str(Path('config')/p['site_registry'])]=file_hash(ROOT/'config'/p['site_registry'])
    out=ROOT/'design'/('generated' if args.protocol=='v0.1' else 'generated_v0.2')
    if args.check:
        saved=json.loads((out/'plan_summary.json').read_text(encoding='utf-8'))
        assert saved==summary,'Generated summary/config hashes changed; regenerate in a new version'
        with (out/'run_plan.csv').open(encoding='utf-8-sig',newline='') as f: saved_rows=list(csv.DictReader(f))
        assert len(saved_rows)==len(rows)
        for expected,actual in zip(rows,saved_rows):
            assert all(actual.get(k)==str(v) for k,v in expected.items()),expected['planned_cell_id']
        with (out/'r0_plan.csv').open(encoding='utf-8-sig',newline='') as f: saved_r0=list(csv.DictReader(f))
        assert len(saved_r0)==len(r0)
        for expected,actual in zip(r0,saved_r0): assert all(actual.get(k)==str(v) for k,v in expected.items())
    else:
        if out.exists():
            assert args.refresh_design,'Design already exists; use --check or explicit --refresh-design'
            old=json.loads((out/'plan_summary.json').read_text(encoding='utf-8'))
            assert old['status']=='offline_design_validated_not_executed'
            assert old['experimental_model_calls_made']==old['simulations_executed']==0
        out.mkdir(parents=True,exist_ok=args.refresh_design)
        write_csv(out/'run_plan.csv',rows);write_csv(out/'r0_plan.csv',r0)
        (out/'plan_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
