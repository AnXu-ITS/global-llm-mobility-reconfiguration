"""R1 acceptance attempt: witnesses, independent audit, mailbox, progress, BFS.

An incomplete search returns exit code 2 and keeps G1 closed. No transport runs
or model calls occur here. Every attempt writes a new immutable result folder.
"""
from pathlib import Path
from dataclasses import asdict,is_dataclass
from concurrent.futures import ThreadPoolExecutor
import argparse,hashlib,itertools,json,sys,time,uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from runtime_v2.core import Kernel,Payload
from runtime_v2.audit import checked_call
from runtime_v2.response_adapter import ResponseMailbox,Response
from run_r1 import VARIANTS,semantic_witness
from r1_model import explore

def dump(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False,default=lambda x:asdict(x) if is_dataclass(x) else str(x))+'\n',encoding='utf-8')

class Trace:
    def __init__(self,mutant=None):self.k=Kernel(mutant=mutant);self.rows=[]
    def call(self,action,*args,**kw):
        result,row=checked_call(self.k,action,*args,**kw);self.rows.append(row);return result
    def proposal(self,op='op',m='m1',resources=('a1',),due=0):
        p=self.k.propose(op,m,resources,due);assert self.call('admit',p);return p
    def errors(self):return sorted({e for r in self.rows for e in r['errors']})

def regressions(out):
    records={}
    for name in ('shared_bay','shared_carrier','loaded_replacement','terminal_hold','terminal_idempotence','interrupted_bay','carrier_failure','foreign_bay','atomic_hold','duplicate_changed_due'):
        x=Trace();k=x.k;k.payloads={'p1':Payload('a1','WAITING_HANDOFF','V3'),'p2':Payload('a2','WAITING_HANDOFF','V3')}
        if name in ('shared_bay','shared_carrier'):
            assert x.call('start_transfer','p1','g1','V3',True,True,True,2)
            if name=='shared_carrier':
                from runtime_v2.core import Resource
                k.resources['bay2']=Resource()
            assert not x.call('start_transfer','p2','g1','V3',True,True,True,2,bay_resource='bay2' if name=='shared_carrier' else 'bay')
            assert not x.call('hold','m2',('g1',),4)
        elif name=='loaded_replacement':
            assert not x.call('start_transfer','p1','a2','V3',True,True,True,2)
            assert x.call('start_transfer','p1','g1','V3',True,True,True,2);x.call('tick',2);assert x.call('finish_transfer','p1')
            assert not x.call('start_transfer','p2','g1','V3',True,True,True,2)
        elif name=='terminal_hold':
            x.call('complete','m1');assert not x.call('hold','m1',('g1',),4)
        elif name=='terminal_idempotence':
            assert x.call('complete','m1');before=k.audit_state();assert not x.call('complete','m1');assert k.audit_state()==before
        elif name in ('interrupted_bay','carrier_failure'):
            assert x.call('start_transfer','p1','g1','V3',True,True,True,2)
            x.call('tick',2);x.call('fail_resource','bay' if name=='interrupted_bay' else 'g1')
            assert not x.call('finish_transfer','p1',True);assert k.payloads['p1'].holder=='a1' and not k.transfer_claims
        elif name=='foreign_bay':
            assert x.call('hold','m2',('bay',),4)
            assert not x.call('start_transfer','p1','g1','V3',True,True,True,2,mission='m1')
        elif name=='atomic_hold':
            assert x.call('hold','m2',('bay',),4);before=k.audit_state()['resources']
            assert not x.call('hold','m1',('g1','bay'),4);assert k.audit_state()['resources']==before
        else:
            p=x.proposal(due=2);assert not x.call('admit',k.propose('op','m1',('a2',),4))
            assert k.operations['op']['proposal']==p
        assert not x.errors(),(name,x.errors());records[name]='passed';dump(out/(name+'.json'),x.rows)
    return records

def mutations(out):
    records={}
    for mutant in ('skip_version','duplicate_resets_due','allow_conflict','teleport_cargo','rollback_applied','renew_forever'):
        x=Trace(mutant);k=x.k
        if mutant=='skip_version':x.proposal();x.call('invalidate','m1');x.call('apply','op')
        elif mutant=='duplicate_resets_due':x.proposal(due=2);x.call('admit',k.propose('op','m1',('a1',),4))
        elif mutant=='allow_conflict':x.call('hold','m2',('a1',),4);x.proposal();x.call('apply','op')
        elif mutant=='teleport_cargo':
            k.payloads['p']=Payload('a1','WAITING_HANDOFF','V3');x.call('start_transfer','p','g1','V3',True,False,True,2)
        elif mutant=='rollback_applied':x.proposal();x.call('apply','op');x.call('cancel','op')
        else:x.call('set_wait','m1',2);x.call('set_wait','m1',100)
        errors=x.errors();assert errors,mutant
        first=next(i for i,r in enumerate(x.rows) if r['errors'])
        dump(out/(mutant+'.json'),{'mutant':mutant,'detected_by':errors,'minimal_failing_prefix_of_designated_witness':x.rows[:first+1],'note':'prefix minimality within this witness, not a global shortest mutant counterexample'})
        records[mutant]=errors
    return records

def mailbox_tests(out):
    records={}
    for name in ('zero_delay_next_tick','reordered','late_after_fallback','cancelled','duplicate','forged_binding','fault_before_response','one_inflight','world_owner'):
        k=Kernel();box=ResponseMailbox(k);p=k.propose('q1-op','m1',('a1',),1);box.issue('q1',p)
        with ThreadPoolExecutor(1) as pool:pool.submit(box.enqueue,Response('q1',p,0 if name=='zero_delay_next_tick' else 2)).result()
        if name=='zero_delay_next_tick':
            assert box.drain()==[];k.tick(1);assert box.drain()==['q1-op'];assert k.apply('q1-op')
        elif name=='reordered':
            q=k.propose('q2-op','m2',('a2',),1);box.issue('q2',q);box.enqueue(Response('q2',q,1));k.tick(1)
            assert box.drain()==['q2-op'];assert k.apply('q2-op');k.tick(2);assert box.drain()==['q1-op'];assert k.apply('q1-op')
        elif name=='late_after_fallback':
            assert k.admit(k.propose('fb','m1',('g1',),0));assert k.apply('fb');k.tick(2);assert box.drain()==[];assert 'q1-op' not in k.operations
        elif name=='cancelled':
            box.cancel('q1');k.tick(2);assert box.drain()==[];assert not k.operations
        elif name=='duplicate':
            box.enqueue(Response('q1',p,2));k.tick(2);assert box.drain()==['q1-op'];assert k.apply('q1-op');box.enqueue(Response('q1',p,3));k.tick(3);assert box.drain()==[];assert k.operations['q1-op']['proposal'].due==1
        elif name=='forged_binding':
            box.enqueue(Response('q1',k.propose('forged','m2',('g1',),0),0));assert box.drain()==[];assert not k.operations
        elif name=='fault_before_response':
            k.tick(2);k.fail_resource('a1');assert box.drain()==['q1-op'];assert not k.apply('q1-op')
        elif name=='one_inflight':
            try:box.issue('q2',k.propose('op2','m1',('g1',),2))
            except ValueError:pass
            else:raise AssertionError('second in-flight request accepted')
            box.cancel('q1');box.issue('q2',k.propose('op2','m1',('g1',),2))
        else:
            with ThreadPoolExecutor(1) as pool:
                try:pool.submit(box.drain).result()
                except RuntimeError:pass
                else:raise AssertionError('non-owner admitted response')
        dump(out/(name+'.json'),{'events':k.events,'final_state':k.audit_state()});records[name]='passed'
    return records

def progress_tests(out):
    cases=[]
    for wait,monitor,compute,issue,noise in itertools.product(range(5),range(2),range(2),range(2),(False,True)):
        x=Trace();k=x.k;x.call('set_wait','m1',wait);submitted=None;committed=None
        for t in range(wait+4):
            x.call('tick',t)
            if noise:x.call('set_wait','m1',t+100)
            if submitted is None and t>=wait+monitor:
                x.proposal('fallback','m1',('g1',),t+compute+issue);submitted=t
            if submitted is not None and committed is None and x.call('apply','fallback'):committed=t
        assert committed is not None and committed<=wait+monitor+compute+issue
        assert not x.errors(),x.errors()
        cases.append({'wait_bound':wait,'monitor_delay':monitor,'compute_delay':compute,'issue_delay':issue,'replanning_noise':noise,'committed_at':committed,'trigger_to_commit':committed-wait,'event_to_commit':committed,'declared_trigger_bound':3,'declared_event_bound':wait+3})
    dump(out/'cases.json',cases)
    return {'passed':len(cases),'conditional_assumptions':['ground fallback continuously available and legal','owner monitor runs within 1 tick','local fallback computation <=1 tick','application issue <=1 tick','waiting episode bound fixed before retries'],'trigger_to_commit_bound_ticks':3,'event_to_commit_bound':'saved finite waiting bound + 3 ticks','basis':'exhaustive 0..4 waits and all 0/1 stage-delay combinations, with/without repeated replanning; additive conditional argument in R1 report','not_claimed':['unbounded-scheduler liveness','transport deadline guarantee','measured native process WCET']}

def mapping_tests(out):
    """Reproducible conformance walks, explicitly not exhaustive equivalence."""
    import random,collections
    from r1_model import initial,successors,R,Q,P,N,NONE
    rng=random.Random(731606);coverage=collections.Counter();traces=[]
    resource_names=('a1','a2','g1','bay');phase={'FREE':0,'HELD':1,'OCCUPIED':2}
    for trial in range(490):
        x=Trace();k=x.k;k.payloads={f'p{m}':Payload(resource_names[m],'WAITING_HANDOFF','V3') for m in range(2)}
        k.set_wait('m1',2);k.set_wait('m2',2);requests={};receipts=collections.Counter();invalid=0;s=initial();trace=[]
        forced=[]
        if trial<90:
            mode=trial//30;m=(trial%30)//15;mask=trial%15+1;q=2*m
            forced=[('issue',q,mask,1),('tick',),('receive',q),('apply',q)]
            if mode==1:forced.insert(0,('hold',m,mask,2))
            elif mode==2:forced.insert(3,('hold',1-m,mask,2))
        for depth in range(12):
            choices=collections.defaultdict(list)
            for action,z in successors(s):choices[action[0]].append((action,z))
            if not choices:break
            if depth<len(forced):action,z=next(pair for pairs in choices.values() for pair in pairs if pair[0]==forced[depth])
            else:action,z=rng.choice(choices[rng.choice(sorted(choices))])
            kind=action[0];v=action[1:];trace.append(action);coverage[kind]+=1
            if kind=='issue':
                q,mask,due=v;requests[q]=(k.propose(f'q{q}',f'm{q//2+1}',tuple(resource_names[r] for r in range(4) if mask&(1<<r)),due),k.now)
            elif kind=='receive':q=v[0];x.call('admit',requests[q][0]);receipts[q]+=1
            elif kind in ('apply','cancel'):x.call(kind,f'q{v[0]}')
            elif kind=='tick':x.call('tick',k.now+1)
            elif kind=='hold':m,mask,expiry=v;x.call('hold',f'm{m+1}',tuple(resource_names[r] for r in range(4) if mask&(1<<r)),expiry)
            elif kind=='wait':m,bound=v;x.call('set_wait',f'm{m+1}',bound)
            elif kind=='invalidate':invalid|=1<<v[0];x.call('invalidate',f'm{v[0]+1}')
            elif kind=='terminate':x.call('complete',f'm{v[0]+1}')
            elif kind=='fail':x.call('fail_resource',resource_names[v[0]])
            elif kind=='start':m,replacement,duration=v;x.call('start_transfer',f'p{m}',resource_names[replacement],'V3',True,True,True,duration,mission=f'm{m+1}')
            elif kind=='finish':x.call('finish_transfer',f'p{v[0]}')
            elif kind=='interrupt':x.call('finish_transfer',f'p{v[0]}',False)
            actual=bytearray(N);actual[0]=k.now;actual[1]=k.versions['m1'];actual[2]=k.versions['m2'];actual[3]=sum(1<<m for m in range(2) if f'm{m+1}' in k.terminal);actual[4]=invalid;actual[5]=k.wait_until['m1'];actual[6]=k.wait_until['m2']
            for r,name in enumerate(resource_names):
                obj=k.resources[name];actual[R(r):R(r)+5]=bytes((obj.version,0 if obj.owner is None else int(obj.owner[1:]),int(obj.available),phase[obj.phase],NONE if obj.valid_through is None else obj.valid_through))
            for q,(proposal,issued) in requests.items():
                j=Q(q);rv=[0]*4
                # Unselected snapshot versions are bookkeeping, not proposal preconditions.
                rv=list(z[j+3:j+7])
                for name,version in zip(proposal.resources,proposal.resource_versions):rv[resource_names.index(name)]=version
                entry=k.operations.get(f'q{q}');status=0 if not receipts[q] else 3 if entry is None else {'PENDING':1,'APPLIED':2,'REJECTED':3,'CANCELLED':4}[entry['state']]
                mask=sum(1<<resource_names.index(name) for name in proposal.resources)
                actual[j:j+11]=bytes((1,proposal.mission_version,mask,*rv,proposal.due,issued,receipts[q],status))
            for m in range(2):
                obj=k.payloads[f'p{m}'];actual[P(m):P(m)+5]=bytes(({'WAITING_HANDOFF':0,'TRANSFERRING':1,'ON_REPLACEMENT':2}[obj.state],resource_names.index(obj.holder),NONE if obj.replacement is None else resource_names.index(obj.replacement),NONE if obj.transfer_start is None else obj.transfer_start,obj.transfer_duration))
            if bytes(actual)!=z or x.errors():
                dump(out/'counterexample.json',{'trial':trial,'trace':trace,'actual_hex':bytes(actual).hex(),'model_hex':z.hex(),'runtime':x.rows,'audit_errors':x.errors()});raise AssertionError('model/runtime mapping mismatch')
            s=z
        traces.append(trace)
    assert set(coverage)=={'issue','receive','apply','cancel','tick','hold','wait','invalidate','terminate','fail','start','finish','interrupt'},coverage
    dump(out/'traces.json',traces)
    return {'walks':len(traces),'maximum_depth':12,'seed':731606,'matched_transitions':sum(coverage.values()),'coverage':dict(coverage),'systematic_prefixes':90,'prefix_scope':'both missions x all 15 bundles x free/own-held/conflicting-version; random continuations plus 400 fully sampled walks','scope':'sampled conformance, all action kinds represented; not exhaustive refinement proof'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--max-states',type=int,default=1_000_000);p.add_argument('--max-seconds',type=int,default=600);a=p.parse_args()
    out=ROOT/'runs/protocol'/('r1_full_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True);print('OUTPUT '+str(out),flush=True)
    try:
        witnesses=[]
        for family,variants in VARIANTS.items():
            for variant in variants:dump(out/'witnesses'/(family+'_'+variant+'.json'),semantic_witness(family,variant));witnesses.append(family+'_'+variant)
        report={'specified_witnesses_passed':len(witnesses),'regressions':regressions(out/'regressions'),'independent_audit_mutants':mutations(out/'mutants'),'mailbox':mailbox_tests(out/'mailbox'),'conditional_progress':progress_tests(out/'progress'),'model_runtime_mapping':mapping_tests(out/'mapping'),'llm_calls':0}
        dump(out/'component_report.json',report);print('COMPONENTS_PASSED '+str(len(witnesses)),flush=True)
        report['bounded_exploration']=explore(out/'model',a.max_states,a.max_seconds,12)
        report['full_G1_gate']=report['bounded_exploration']['status']=='bounded_model_complete'
        report['status']='passed_bounded_scope' if report['full_G1_gate'] else 'incomplete_G1_closed'
        report['implementation_refinement']='designated runtime witnesses, sampled compact-model conformance and independent pre/post-state audit; not universal simulator correctness'
        report['remaining_gate_requirements']=[] if report['full_G1_gate'] else ['complete declared depth-12 exploration without resource limit']
        if report['bounded_exploration']['status']=='counterexample':report['status']='failed_counterexample'
        sources=[ROOT/'runtime_v2/core.py',ROOT/'runtime_v2/audit.py',ROOT/'runtime_v2/response_adapter.py',Path(__file__),Path(__file__).with_name('r1_model.py')]
        report['source_sha256']={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
        dump(out/'report.json',report);dump(ROOT/'outputs/r1_full/latest.json',{'run_dir':str(out.relative_to(ROOT)),'status':report['status'],'full_G1_gate':report['full_G1_gate']})
        print(json.dumps(report,indent=2),flush=True);raise SystemExit(2 if not report['full_G1_gate'] else 0)
    except SystemExit:raise
    except Exception as error:
        import traceback
        dump(out/'failure.json',{'error':str(error),'traceback':traceback.format_exc()});raise

if __name__=='__main__':main()
