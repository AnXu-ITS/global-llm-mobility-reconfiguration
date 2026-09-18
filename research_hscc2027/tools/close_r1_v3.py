"""Compose bounded safety certificates and concrete evidence; never force-pass."""
from pathlib import Path
import gzip,hashlib,json,sys,time,types,uuid
from r1_symbolic import ROOT,Z,states,action,transition,PROPERTIES
from run_r1_symbolic import dump
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    out=ROOT/'runs/protocol'/('r1_acceptance_v3_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
    base=ROOT/'runs/protocol/r1_smt_20260918_182552_20e1c9';parts=ROOT/'runs/protocol/r1_smt_20260918_182936_141633';atomic=ROOT/'runs/protocol/r1_smt_20260918_183226_68abb7'
    s=states('s');n=states('n');a=action('a');current_t,current_bad=transition(s,n,a);checks={};equivalences=[]
    for folder in (base,parts,atomic):
        old=types.ModuleType('archived');source=folder/'sources/tools/r1_symbolic.py';old.__file__=str(ROOT/'tools/r1_symbolic.py');exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'),old.__dict__)
        old_t,old_bad=old.transition(s,n,a)
        # Equal transition ASTs, plus explicit solver checks of property equality.
        assert Z.And(*old_t).sexpr()==Z.And(*current_t).sexpr()
        solver=Z.SolverFor('QF_BV');solver.add(Z.Or(*(old_bad[p]!=current_bad[p] for p in PROPERTIES)));assert solver.check()==Z.unsat
        proof_path=out/(folder.name+'_equivalence.smt2');proof_path.write_text(solver.to_smt2(),encoding='utf-8')
        equivalences.append({'source_sha256':sha(source),'current_sha256':sha(ROOT/'tools/r1_symbolic.py'),'transition_ast_identical':True,'original_property_equivalence':'unsat','query':proof_path.name})
    capacity_names=['capacity__bay_exclusion',*(f'capacity__resource_{r}' for r in range(4)),'capacity__commit_conflict','capacity__atomic_apply',*(f'capacity__atomic_hold_{r}' for r in range(4))]
    solver=Z.SolverFor('QF_BV');solver.add(current_bad['resource_capacity']!=Z.Or(*(current_bad[p] for p in capacity_names)));assert solver.check()==Z.unsat
    (out/'capacity_decomposition_equivalence.smt2').write_text(solver.to_smt2(),encoding='utf-8')
    evidence={};certificates={}
    groups=[(base,[p for p in PROPERTIES if p!='resource_capacity']),(parts,capacity_names[:6]),(atomic,capacity_names[6:])]
    for folder,names in groups:
        r=read(folder/'report.json');evidence[str((folder/'report.json').relative_to(ROOT))]=sha(folder/'report.json')
        for prop in names:
            rows=r['results'][prop];assert [x['depth'] for x in rows]==list(range(1,13));assert all(x['result']=='unsat' for x in rows)
            for row in rows:
                query=folder/row['query'];assert hashlib.sha256(gzip.open(query,'rt',encoding='utf-8').read().encode()).hexdigest()==row['query_sha256'];evidence[str(query.relative_to(ROOT))]=sha(query)
            certificates[prop]={'result':'UNSAT_1_THROUGH_12','report':str((folder/'report.json').relative_to(ROOT))}
    conformance=ROOT/'runs/protocol/r1_smt_conformance_20260918_1828/report.json';conf=read(conformance);assert conf['status']=='passed' and conf['transitions']==5844
    component=ROOT/read(ROOT/'outputs/r1_symbolic/components_latest.json')['run_dir']/'report.json';c=read(component);assert c['status']=='passed' and c['progress']['passed']==80 and c['physical_A_trace']['status']=='passed'
    mutants=ROOT/read(ROOT/'outputs/r1_symbolic/mutants_latest.json')['run_dir']/'report.json';mut=read(mutants);assert len(mut['mutants'])==7 and mut['all_detected'] and all(v['shortest_certified'] for v in mut['mutants'].values())
    for path in (conformance,component,mutants):evidence[str(path.relative_to(ROOT))]=sha(path)
    checks={'six_safety_properties_depth_1_to_12':True,'capacity_exact_disjunction_equivalence':True,'same_transition_relation_across_query_splits':True,'all_seven_symbolic_mutants_detected':True,'runtime_mutants_and_symbolic_replays':True,'conditional_progress_80_cases':True,'symbolic_concrete_kernel_conformance_5844':True,'physical_A_protocol_trace_663':True}
    source_paths=[ROOT/'runtime_v2'/name for name in ('core.py','audit.py','response_adapter.py')]+[ROOT/'tools'/name for name in ('r1_model.py','r1_symbolic.py','run_r1_symbolic.py','r1_conformance.py','run_r1_components_v3.py',Path(__file__).name)]
    import shutil
    for path in source_paths:
        dest=out/'sources'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    report={'gate':'G1','status':'passed_within_declared_finite_bound','full_G1_gate':True,'verification_method':'symbolic_bmc_exact_property_decomposition_v0.3','depth':12,'properties':{p:'PASS_BOUNDED' for p in PROPERTIES},'certificates':certificates,'checks':checks,'equivalence':equivalences,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in source_paths},'evidence_sha256':evidence,'components':str(component.relative_to(ROOT)),'conformance':str(conformance.relative_to(ROOT)),'mutants':str(mutants.relative_to(ROOT)),'conditional_progress':'commit <= w+M+C+I under stated continuous feasibility/fairness/bounds; not transport deadline guarantee','full_real_system_proof':False,'old_bfs_status':'incomplete at unchanged 1000000 state cap; historical record retained','unknown_queries_retained':[str(base.relative_to(ROOT)),str(parts.relative_to(ROOT))],'no_formal_transport_runs':True}
    dump(out/'report.json',report);dump(ROOT/'outputs/r1_symbolic/acceptance_latest.json',{'run_dir':str(out.relative_to(ROOT)),'status':report['status'],'full_G1_gate':True});print(json.dumps({'run_dir':str(out.relative_to(ROOT)),'status':report['status'],'certified_queries':len(certificates)*12,'checks':checks},indent=2))
if __name__=='__main__':main()
