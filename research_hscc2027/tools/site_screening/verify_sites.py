"""Integrity, route legality, plan identity and admission checks for six-site design."""
from screen_sites import ROOT,OUT,dump,sha,sumolib
import csv,json,collections,subprocess,sys
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    registry=read(ROOT/'config/sites.v1.json');assert set(registry['sites'])==set('ABCDEF')
    checked=[]
    for site in 'DEF':
        d=OUT/'frozen'/site;manifest=read(d/'asset_manifest.json')
        for filename,expected in manifest['files'].items():assert sha(d/filename)==expected,(site,filename)
        assert registry['sites'][site]['asset_hashes']['network']==sha(d/'network.net.xml')
        net=sumolib.net.readNet(str(d/'network.net.xml'));r=read(d/'site_candidate_report.json')
        for route in r['routes'].values():
            for path in [route['primary_edges']]+[x['edges'] for x in route['alternatives']]:
                for a,b in zip(path,path[1:]):assert net.getEdge(b) in net.getEdge(a).getAllowedOutgoing('passenger')
        facilities=read(d/'facilities.json')['facilities']
        for f in facilities.values():
            lane=net.getLane(f['lane_id']);assert lane.allows('passenger') and 0<f['lane_pos_m']<lane.getLength()
        resource=read(d/'compatibility.json');assert len(resource['bays'])==(2 if site=='F' else 1)
        assert all(x['capacity']==1 and x['site'] in facilities for x in resource['bays'].values())
        for task in resource['task_library']:
            for rid in task['legal_backups']:
                assert task['class'] in resource['resources'][rid]['classes'] and task['destination'] in resource['resources'][rid]['sites']
        a=read(d/'acceptance.json');assert not a['formal_admission'] and not a['status']['formal_fixture_frozen']
        phy=read(d/'physical_diagnostic_pointer.json');assert phy['exit_code']==0 and phy['status']=='passed'
        fixture=read(ROOT/phy['run_dir']/'fixture.json');assert fixture['site_id']==site and fixture['network_sha256']==sha(d/'network.net.xml')
        ptr=read(d/'traffic_diagnostic_pointer.json');traffic=read(ROOT/ptr['report']);assert traffic['nominal_probe_passed']
        if site=='E':assert traffic['perturbed_probe_passed'] and traffic['physical_volatility_observed']
        for p in (ROOT/'fixtures/development'/site).glob('*.json'):
            fixture=read(p);assert fixture['status']=='development_skeleton_not_execution_frozen'
            assert all(t['deadline_s']>=t['release_s'] and t['reference_only'] for t in fixture['tasks'])
        checked.append(site)
    config=read(ROOT/'config/experiment_protocol.v2.json');assert config['scenario_sites']['H_A']=='A' and config['scenario_sites']['H_B']=='B'
    seeds=set(config['seed_sets']['cross_site'])
    assert all(seeds.isdisjoint(set(values)) for key,values in config['seed_sets'].items() if key!='cross_site')
    rows=list(csv.DictReader((ROOT/'design/generated_v0.2/run_plan.csv').open(encoding='utf-8-sig')))
    r6=[r for r in rows if r['group']=='R6_SITE'];b2=[r for r in rows if r['group']=='R6_B2'];assert len(r6)==240 and len(b2)==120
    groups=collections.defaultdict(list)
    for row in r6:groups[row['pair_id']].append(row)
    assert len(groups)==120 and all(len(v)==2 and {x['method'] for x in v}=={'X_LST','X_FULL'} and len({x['environment_id'] for x in v})==1 for v in groups.values())
    assert len({r['environment_id'] for r in r6})==120,'Cross-site environment collision'
    assert {r['environment_id'] for r in r6}=={r['environment_id'] for r in b2}
    assert all(r['delay_s']=='' and r['proposer']=='B2_FAST' for r in b2)
    assert all(r['environment_identity_status']=='planning_only_formal_fixture_missing' for r in rows)
    assert not config['gates']['run_enabled'] and all(s['formal_signature'] is None for s in registry['sites'].values())
    report={'status':'passed','map_packages_verified':checked,'candidate_networks_current':len(list((OUT/'candidates').glob('*/site_candidate_report.json'))),'r6_cells':len(r6),'r6_b2_optional':len(b2),'paired_environments':len(groups),'cross_site_identity_collisions':0,'formal_admission':False,'native_calls':0,'checks':['asset hashes','legal route turns and lane positions','modeled resource compatibility','actual SUMO and air-ground diagnostic provenance','site-aware unique paired environment IDs','fast B2 no artificial delay','seed disjointness','historical H_A/H_B geography preserved','formal gate remains closed']}
    assert report['candidate_networks_current']==15
    dump(ROOT/'outputs/site_integration/verification.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
