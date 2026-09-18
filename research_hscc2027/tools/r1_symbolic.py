"""Direct QF_BV encoding of r1_model's 81-byte abstraction plus stuttering.

No invariant is assumed at intermediate states. Properties are independent
queries over Init and the transition relation. Eight-bit versions cannot wrap
in 12 transitions (at most one increment per component per transition).
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor/python_verification'))
import z3 as Z
from r1_model import N,NONE,R,Q,P,initial

KINDS=('tick','issue','receive','hold','apply','cancel','invalidate','terminate','wait','fail','start','finish','interrupt','noop')
PROPERTIES=('version_consistency','idempotence','resource_capacity','custody_uniqueness','transfer_causality','cancellation_consistency')
def B(x):return Z.BitVecVal(x,8)
def A(*x):return Z.And(*x)
def O(*x):return Z.Or(*x)
def select(xs,index):
    value=xs[-1]
    for i in reversed(range(len(xs)-1)):value=Z.If(index==i,xs[i],value)
    return value
def selected(mask,r):return (mask & B(1<<r))!=0
def terminal(s,m):return (s[3]&B(1<<m))!=0
def busy(s,r):return O(*(A(s[P(m)]==1,O(r==3,s[P(m)+2]==r)) for m in range(2)))
def own_or_free(owner,m):return O(owner==0,owner==m+1)
def states(prefix):return [Z.BitVec(f'{prefix}_{i}',8) for i in range(N)]
def action(prefix):
    return {key:Z.BitVec(f'{prefix}_{key}',8) for key in ('kind','m','q','r','mask','value','replacement','duration','readiness')}

def transition(s,n,a,mutant=None):
    cases=[];commits=[];apply_attempts=[];starts=[];finishes=[];holds=[]
    def kind(name):return a['kind']==KINDS.index(name)
    def case(guard,updates):cases.append((guard,updates))
    # A real rejected/no-op call may consume a step. Adding stuttering preserves
    # the set of violations reachable at depth <= k in the original BFS model.
    case(kind('noop'),{})
    tick=A(kind('tick'),Z.ULT(s[0],B(4)));u={0:s[0]+1}
    for r in range(4):
        j=R(r);expired=A(s[j+3]==1,Z.UGT(s[0]+1,s[j+4]))
        u.update({j:Z.If(expired,s[j]+1,s[j]),j+1:Z.If(expired,B(0),s[j+1]),j+3:Z.If(expired,B(0),s[j+3]),j+4:Z.If(expired,B(NONE),s[j+4])})
    case(tick,u)
    for m in range(2):
        mv=1+m;p=P(m);owner=m+1;live=Z.Not(terminal(s,m));mask=a['mask'];value=a['value']
        mask_ok=A(Z.UGE(mask,B(1)),Z.ULE(mask,B(15)));value_ok=Z.ULE(value,B(4))
        compatible=A(*(Z.Implies(selected(mask,r),A(s[R(r)+2]==1,own_or_free(s[R(r)+1],m),Z.Not(busy(s,r)))) for r in range(4)))
        held=A(kind('hold'),a['m']==m,mask_ok,value_ok,Z.UGE(value,s[0]),compatible,True if mutant=='terminal_hold' else live)
        u={}
        for r in range(4):
            j=R(r);change=A(selected(mask,r),s[j+3]!=2)
            u.update({j:Z.If(A(change,s[j+1]==0),s[j]+1,s[j]),j+1:Z.If(change,B(owner),s[j+1]),j+3:Z.If(change,B(1),s[j+3]),j+4:Z.If(change,Z.If(Z.ULT(s[j+4],value),s[j+4],value),s[j+4])})
        case(held,u);holds.append((held,m,mask))
        case(A(kind('wait'),a['m']==m,live,value_ok,Z.ULT(value,s[5+m])),{5+m:value})
        case(A(kind('invalidate'),a['m']==m,live,(s[4]&B(1<<m))==0),{4:s[4]|B(1<<m),mv:s[mv]+1})
        active_owned=A(busy(s,3),s[R(3)+1]==owner)
        terminate=A(kind('terminate'),a['m']==m,live,Z.Not(active_owned));u={3:s[3]|B(1<<m),mv:s[mv]+1}
        for r in range(4):
            j=R(r);mine=s[j+1]==owner
            u.update({j:Z.If(mine,s[j]+1,s[j]),j+1:Z.If(mine,B(0),s[j+1]),j+3:Z.If(mine,B(0),s[j+3]),j+4:Z.If(mine,B(NONE),s[j+4])})
        case(terminate,u)
        rep=a['replacement'];duration=a['duration'];rep_ok=Z.ULT(rep,B(3));duration_ok=O(duration==1,duration==2)
        rep_available=select([s[R(r)+2] for r in range(3)],rep)==1
        rep_owner=select([s[R(r)+1] for r in range(3)],rep)
        physical_ready=a['readiness']==15
        legal_start=A(s[p]==0,live,s[R(3)+2]==1,own_or_free(s[R(3)+1],m),Z.Not(busy(s,3)),rep!=s[p+1],Z.Not(busy(s,rep)),rep_available,own_or_free(rep_owner,m),physical_ready,*(s[P(i)+1]!=rep for i in range(2) if i!=m))
        start=A(kind('start'),a['m']==m,rep_ok,duration_ok,True if mutant=='teleport_cargo' else legal_start)
        case(start,{p:B(1),p+2:rep,p+3:s[0],p+4:duration});starts.append((start,legal_start,m))
        case(A(kind('interrupt'),a['m']==m,s[p]==1),{p:B(0),p+3:B(NONE)})
        finish=A(kind('finish'),a['m']==m,s[p]==1,s[R(3)+2]==1,select([s[R(r)+2] for r in range(3)],s[p+2])==1,Z.UGE(s[0],s[p+3]+s[p+4]))
        case(finish,{p:B(2),p+1:s[p+2]});finishes.append((finish,m))
    for r in range(4):
        j=R(r);case(A(kind('fail'),a['r']==r,s[j+2]==1),{j:s[j]+1,j+2:B(0)})
    for q in range(4):
        j=Q(q);m=q//2;mv=1+m;mask=s[j+2];slots=(2*m,2*m+1)
        first_free=A(s[j]==0,True if q%2==0 else s[Q(q-1)]==1)
        no_inflight=A(*(Z.Not(A(s[Q(i)]==1,s[Q(i)+9]==0)) for i in slots))
        issue=A(kind('issue'),a['q']==q,first_free,no_inflight,Z.Not(terminal(s,m)),Z.UGE(a['mask'],B(1)),Z.ULE(a['mask'],B(15)),Z.ULE(a['value'],B(4)))
        values=[B(1),s[mv],a['mask'],*(s[R(r)] for r in range(4)),a['value'],s[0],B(0),B(0)]
        case(issue,{j+i:v for i,v in enumerate(values)})
        receive=A(kind('receive'),a['q']==q,s[j]==1,Z.ULT(s[j+9],B(2)),Z.UGT(s[0],s[j+8]))
        stale=O(terminal(s,m),s[j+1]!=s[mv]);u={j+9:s[j+9]+1,j+10:Z.If(s[j+9]==0,Z.If(stale,B(3),B(1)),s[j+10])}
        if mutant=='duplicate_resets_due':u[j+7]=Z.If(A(s[j+9]==1,Z.ULE(a['value'],B(4))),a['value'],s[j+7])
        case(receive,u)
        cancel=A(kind('cancel'),a['q']==q,s[j]==1,O(s[j+10]==1,s[j+10]==2))
        case(cancel,{j+10:Z.If(O(s[j+10]==1,mutant=='rollback_applied'),B(4),s[j+10])})
        apply=A(kind('apply'),a['q']==q,s[j]==1,s[j+10]==1,Z.UGE(s[0],s[j+7]))
        versions=A(Z.Not(terminal(s,m)),s[j+1]==s[mv],*(Z.Implies(selected(mask,r),A(s[R(r)]==s[j+3+r],s[R(r)+2]==1)) for r in range(4)))
        conflict=O(*(A(selected(mask,r),O(Z.Not(own_or_free(s[R(r)+1],m)),busy(s,r))) for r in range(4)))
        success=A(True if mutant=='skip_version' else versions,True if mutant=='allow_conflict' else Z.Not(conflict))
        u={j+10:Z.If(success,B(2),B(3)),mv:Z.If(success,s[mv]+1,s[mv])}
        for r in range(4):
            k=R(r);change=A(success,selected(mask,r))
            if mutant=='partial_atomic':change=O(change,A(versions,conflict,selected(mask,r),s[k+1]==0,Z.Not(busy(s,r))))
            u.update({k:Z.If(change,s[k]+1,s[k]),k+1:Z.If(change,B(m+1),s[k+1]),k+3:Z.If(change,B(2),s[k+3]),k+4:Z.If(change,B(NONE),s[k+4])})
        case(apply,u);commits.append((A(apply,success),q,versions,conflict));apply_attempts.append((apply,success))
    expressions=list(s)
    for guard,updates in cases:
        for index,value in updates.items():expressions[index]=Z.If(guard,value,expressions[index])
    relation=[O(*(g for g,_ in cases)),*(n[i]==expressions[i] for i in range(N))]
    # Independent predicates over before/after and action occurrence. Mutants
    # change transition guards/updates, never these property definitions.
    version_bad=O(*(A(commit,Z.Not(valid)) for commit,_,valid,_ in commits))
    immutable_bad=O(*(A(s[Q(q)]==1,O(*(n[Q(q)+i]!=s[Q(q)+i] for i in range(9)))) for q in range(4)))
    duplicate_effect=O(*(A(commit,s[Q(q)+10]==2) for commit,q,_,_ in commits))
    capacity=[];capacity_parts={}
    capacity_parts['capacity__bay_exclusion']=A(n[P(0)]==1,n[P(1)]==1)
    capacity.append(capacity_parts['capacity__bay_exclusion'])
    for r in range(4):
        j=R(r)
        parts=[(n[j+1]==0)!=(n[j+3]==0),A(n[j+3]==1,Z.ULT(n[j+4],n[0]))]
        parts.extend(A(n[j+1]==m+1,terminal(n,m)) for m in range(2))
        capacity_parts[f'capacity__resource_{r}']=O(*parts);capacity.extend(parts)
    capacity_parts['capacity__commit_conflict']=O(*(A(commit,conflict) for commit,_,_,conflict in commits));capacity.append(capacity_parts['capacity__commit_conflict'])
    atomic=[]
    for attempt,success in apply_attempts:
        atomic.append(A(attempt,Z.Not(success),O(*(s[R(r)+i]!=n[R(r)+i] for r in range(4) for i in range(5)))))
    capacity_parts['capacity__atomic_apply']=O(*atomic)
    for r in range(4):
        hold_r=O(*(A(held,selected(mask,r),n[R(r)+1]!=m+1) for held,m,mask in holds))
        capacity_parts[f'capacity__atomic_hold_{r}']=hold_r;atomic.append(hold_r)
    capacity_parts['capacity__atomicity']=O(*atomic);capacity.extend(atomic)
    custody=O(*(Z.UGT(n[P(m)+1],B(2)) for m in range(2)),n[P(0)+1]==n[P(1)+1])
    causality=[A(start,Z.Not(legal)) for start,legal,_ in starts]
    for m in range(2):
        p=P(m);changed=n[p+1]!=s[p+1]
        legal_finish=A(s[p]==1,Z.UGE(s[0],s[p+3]+s[p+4]),n[p+1]==s[p+2],s[R(3)+2]==1,select([s[R(r)+2] for r in range(3)],s[p+2])==1)
        causality.append(A(changed,Z.Not(A(kind('finish'),a['m']==m,legal_finish))))
        causality.append(A(s[p]==1,n[p]==1,n[p+1]!=s[p+1]))
    cancel_bad=O(*(A(s[Q(q)+10]==2,n[Q(q)+10]!=2) for q in range(4)))
    bad=dict(zip(PROPERTIES,(version_bad,O(immutable_bad,duplicate_effect),O(*capacity),custody,O(*causality),cancel_bad)))
    bad.update(capacity_parts)
    return relation,bad

def decode_action(values):
    kind=KINDS[values['kind']]
    if kind in ('tick','noop'):return (kind,)
    if kind=='issue':return kind,values['q'],values['mask'],values['value']
    if kind in ('receive','apply','cancel'):return kind,values['q']
    if kind=='hold':return kind,values['m'],values['mask'],values['value']
    if kind=='wait':return kind,values['m'],values['value']
    if kind=='start':return kind,values['m'],values['replacement'],values['duration']
    if kind=='fail':return kind,values['r']
    return kind,values['m']

def instantiate(solver,model,ss,aa):
    state_values=[[model.eval(v,model_completion=True).as_long() for v in s] for s in ss]
    action_values=[{k:model.eval(v,model_completion=True).as_long() for k,v in a.items()} for a in aa]
    return {'states':state_values,'actions':action_values,'decoded_actions':[decode_action(a) for a in action_values]}
