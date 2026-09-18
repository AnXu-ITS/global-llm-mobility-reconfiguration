"""Concrete executor for the finite model's transitions and SMT correspondence."""
from pathlib import Path
from collections import Counter
import json,sys,time
from r1_symbolic import ROOT,Z,N,R,Q,P,NONE,B,states,action,transition,KINDS
sys.path.insert(0,str(ROOT))
from runtime_v2.core import Kernel,Payload
from runtime_v2.audit import checked_call
from r1_model import initial,successors

RES=('a1','a2','g1','bay')
class Projection:
    def __init__(self,mutant=None):
        self.k=Kernel(mutant=mutant);self.k.payloads={f'p{m}':Payload(RES[m],'WAITING_HANDOFF','V3') for m in range(2)}
        self.k.set_wait('m1',2);self.k.set_wait('m2',2);self.requests={};self.receipts=Counter();self.invalid=0;self.audit=[]
    def call(self,name,*args,**kw):
        result,row=checked_call(self.k,name,*args,**kw);self.audit.append(row);return result
    def execute(self,a):
        kind=a[0];v=a[1:];k=self.k
        if kind=='issue':
            q,mask,due=v;self.requests[q]=(k.propose(f'q{q}',f'm{q//2+1}',tuple(RES[r] for r in range(4) if mask&(1<<r)),due),k.now,tuple(k.resources[r].version for r in RES))
        elif kind=='receive':q=v[0];self.call('admit',self.requests[q][0]);self.receipts[q]+=1
        elif kind in ('apply','cancel'):self.call(kind,f'q{v[0]}')
        elif kind=='tick':self.call('tick',k.now+1)
        elif kind=='hold':m,mask,expiry=v;self.call('hold',f'm{m+1}',tuple(RES[r] for r in range(4) if mask&(1<<r)),expiry)
        elif kind=='wait':m,bound=v;self.call('set_wait',f'm{m+1}',bound)
        elif kind=='invalidate':self.invalid|=1<<v[0];self.call('invalidate',f'm{v[0]+1}')
        elif kind=='terminate':self.call('complete',f'm{v[0]+1}')
        elif kind=='fail':self.call('fail_resource',RES[v[0]])
        elif kind=='start':m,rep,duration=v;self.call('start_transfer',f'p{m}',RES[rep],'V3',True,True,True,duration,mission=f'm{m+1}')
        elif kind=='finish':self.call('finish_transfer',f'p{v[0]}')
        elif kind=='interrupt':self.call('finish_transfer',f'p{v[0]}',False)
        elif kind!='noop':raise ValueError(a)
    def encode(self):
        k=self.k;s=bytearray(N);s[0]=k.now;s[1]=k.versions['m1'];s[2]=k.versions['m2'];s[3]=sum(1<<m for m in range(2) if f'm{m+1}' in k.terminal);s[4]=self.invalid;s[5]=k.wait_until['m1'];s[6]=k.wait_until['m2']
        for r,name in enumerate(RES):
            obj=k.resources[name];s[R(r):R(r)+5]=bytes((obj.version,0 if obj.owner is None else int(obj.owner[1:]),int(obj.available),{'FREE':0,'HELD':1,'OCCUPIED':2}[obj.phase],NONE if obj.valid_through is None else obj.valid_through))
        for q,(p,issued,versions) in self.requests.items():
            entry=k.operations.get(f'q{q}');status=0 if not self.receipts[q] else 3 if entry is None else {'PENDING':1,'APPLIED':2,'REJECTED':3,'CANCELLED':4}[entry['state']]
            s[Q(q):Q(q)+11]=bytes((1,p.mission_version,sum(1<<RES.index(r) for r in p.resources),*versions,p.due,issued,self.receipts[q],status))
        for m in range(2):
            p=k.payloads[f'p{m}'];s[P(m):P(m)+5]=bytes(({'WAITING_HANDOFF':0,'TRANSFERRING':1,'ON_REPLACEMENT':2}[p.state],RES.index(p.holder),NONE if p.replacement is None else RES.index(p.replacement),NONE if p.transfer_start is None else p.transfer_start,p.transfer_duration))
        return bytes(s)

def action_values(a):
    out=dict.fromkeys(('kind','m','q','r','mask','value','replacement','duration','readiness'),0);out['kind']=KINDS.index(a[0]);out['readiness']=15;k=a[0];v=a[1:]
    if k=='issue':out.update(q=v[0],mask=v[1],value=v[2])
    elif k in ('receive','apply','cancel'):out['q']=v[0]
    elif k=='hold':out.update(m=v[0],mask=v[1],value=v[2])
    elif k=='wait':out.update(m=v[0],value=v[1])
    elif k=='start':out.update(m=v[0],replacement=v[1],duration=v[2])
    elif k=='fail':out['r']=v[0]
    elif k not in ('noop','tick'):out['m']=v[0]
    return out

def verify(out,trace_source):
    paths=json.loads(Path(trace_source).read_text(encoding='utf-8'));s=states('pre');n=states('post');a=action('action');relation,_=transition(s,n,a);solver=Z.SolverFor('QF_BV');solver.set(timeout=5000);solver.add(*relation)
    coverage=Counter();count=0;begin=time.monotonic()
    for index,path in enumerate(paths):
        runtime=Projection();old=initial()
        for chosen in path:
            action_tuple=tuple(chosen);expected=next(value for key,value in successors(old) if key==action_tuple)
            runtime.execute(action_tuple);actual=runtime.encode();assert actual==expected,('concrete_model_to_kernel',index,chosen)
            assert not any(r['errors'] for r in runtime.audit),(index,chosen,'independent_audit')
            values=action_values(chosen);solver.push();solver.add(*(v==B(x) for v,x in zip(s,old)),*(a[k]==B(value) for k,value in values.items()))
            assert solver.check()==Z.sat,('symbolic_transition_missing',index,chosen)
            solver.add(Z.Or(*(v!=B(x) for v,x in zip(n,actual))))
            assert solver.check()==Z.unsat,('symbolic_next_state_mismatch',index,chosen)
            solver.pop();old=actual;coverage[chosen[0]]+=1;count+=1
        if index%50==0:print(json.dumps({'conformance_paths':index+1,'transitions':count,'elapsed_s':round(time.monotonic()-begin,1)}),flush=True)
    report={'status':'passed','paths':len(paths),'transitions':count,'actions':dict(coverage),'source':str(trace_source),'comparison':'concrete model successor == projected actual kernel state == unique SMT next state (SAT existence + UNSAT disequality)','elapsed_s':round(time.monotonic()-begin,3),'full_implementation_proof':False}
    out.mkdir(parents=True,exist_ok=True);(out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--traces',required=True);p.add_argument('--out',required=True);args=p.parse_args();print(json.dumps(verify(Path(args.out),args.traces),indent=2))
