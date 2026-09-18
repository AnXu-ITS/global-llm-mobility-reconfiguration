"""Incremental counterexample search, depth 1..12, one query per property.

SMT queries are archived before solver.check. SAT witnesses are shortest only
when every earlier depth for that property was UNSAT. UNKNOWN never opens G1.
"""
from pathlib import Path
import argparse,gzip,hashlib,json,platform,sys,time,uuid
from r1_symbolic import ROOT,Z,N,PROPERTIES,states,action,transition,initial,B,instantiate

def dump(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def run(out,depth=12,timeout_ms=15000,mutant=None,properties=PROPERTIES):
    import shutil
    for path in (Path(__file__),Path(__file__).with_name('r1_symbolic.py'),Path(__file__).with_name('r1_model.py')):
        dest=out/'sources'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    solver=Z.SolverFor('QF_BV');solver.set(timeout=timeout_ms,random_seed=731607)
    ss=[states('s0')];aa=[];solver.add(*(v==B(x) for v,x in zip(ss[0],initial())))
    past={p:[] for p in properties};results={p:[] for p in properties};found=set()
    for k in range(1,depth+1):
        aa.append(action(f'a{k-1}'));ss.append(states(f's{k}'))
        relation,bad=transition(ss[-2],ss[-1],aa[-1],mutant);solver.add(*relation)
        for prop in properties:
            if prop in found:continue
            past[prop].append(bad[prop]);solver.push();solver.add(Z.Or(*past[prop]))
            query=solver.to_smt2();query_path=out/'queries'/f'{prop}_d{k:02}.smt2.gz';query_path.parent.mkdir(parents=True,exist_ok=True)
            with gzip.open(query_path,'wt',encoding='utf-8',compresslevel=1) as f:f.write(query)
            begin=time.monotonic();status=solver.check();elapsed=time.monotonic()-begin
            rec={'depth':k,'result':str(status),'wall_s':round(elapsed,6),'assertions':len(solver.assertions()),'state_variables':N*(k+1),'action_variables':9*k,'query_sha256':hashlib.sha256(query.encode()).hexdigest(),'query':str(query_path.relative_to(out))}
            if status==Z.sat:
                rec['shortest']=all(r['result']=='unsat' for r in results[prop]);witness=instantiate(solver,solver.model(),ss,aa)
                dump(out/'witnesses'/f'{prop}_d{k:02}.json',{'property':prop,'mutant':mutant,'shortest':rec['shortest'],**witness});found.add(prop)
            elif status==Z.unknown:rec['reason']=solver.reason_unknown()
            results[prop].append(rec);solver.pop()
            dump(out/'partial.json',{'mutant':mutant,'results':results})
            print(json.dumps({'mutant':mutant,'property':prop,**{v:rec[v] for v in ('depth','result','wall_s')} }),flush=True)
    statuses={p:'FAIL' if any(r['result']=='sat' for r in rows) else 'PASS_BOUNDED' if len(rows)==depth and all(r['result']=='unsat' for r in rows) else 'INCONCLUSIVE' for p,rows in results.items()}
    report={'protocol_model':'R1 v0.3 direct symbolic encoding of v0.2 finite abstraction plus stuttering','depth':depth,'timeout_per_query_ms':timeout_ms,'mutant':mutant,'solver':Z.get_full_version(),'python':sys.version,'platform':platform.platform(),'properties':statuses,'results':results,'all_properties_pass':all(s=='PASS_BOUNDED' for s in statuses.values()),'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),Path(__file__).with_name('r1_symbolic.py'),Path(__file__).with_name('r1_model.py'))},'no_invariant_assumed':True,'full_real_system_proof':False}
    dump(out/'report.json',report);return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--depth',type=int,default=12);p.add_argument('--timeout-ms',type=int,default=15000);p.add_argument('--mutant',choices=['skip_version','duplicate_resets_due','allow_conflict','teleport_cargo','rollback_applied','partial_atomic','terminal_hold']);p.add_argument('--property',choices=PROPERTIES);p.add_argument('--capacity-parts',action='store_true');p.add_argument('--atomic-parts',action='store_true');a=p.parse_args()
    if not 1<=a.depth<=12:p.error('depth must be in 1..12')
    out=ROOT/'runs/protocol'/('r1_smt_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True);print('OUTPUT '+str(out),flush=True)
    properties=['capacity__bay_exclusion',*(f'capacity__resource_{r}' for r in range(4)),'capacity__commit_conflict','capacity__atomicity'] if a.capacity_parts else [a.property] if a.property else PROPERTIES
    if a.atomic_parts:properties=['capacity__atomic_apply',*(f'capacity__atomic_hold_{r}' for r in range(4))]
    r=run(out,a.depth,a.timeout_ms,a.mutant,properties)
    if a.depth==12 and a.mutant is None and not a.property and not a.capacity_parts and not a.atomic_parts:dump(ROOT/'outputs/r1_symbolic/latest.json',{'run_dir':str(out.relative_to(ROOT)),'all_properties_pass':r['all_properties_pass']})
    raise SystemExit(0 if r['all_properties_pass'] else 2)
if __name__=='__main__':main()
