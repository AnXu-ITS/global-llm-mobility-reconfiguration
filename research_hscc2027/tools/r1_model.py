"""Breadth-first bounded protocol model, exact byte states (no hash collisions).

Stuttering rejections are omitted. No symmetry or partial-order reduction is
claimed. Reaching the configured state/time cap is INCOMPLETE, never a pass.
Physical arrivals are abstracted to two accessible payloads at one facility.
"""
from array import array
from collections import Counter
import gzip,json,time

N=81;NONE=255
R=lambda r:7+5*r
Q=lambda q:27+11*q
P=lambda m:71+5*m
MASKS=range(1,16)

def initial():
    s=bytearray(N);s[5]=s[6]=2
    for r in range(4):s[R(r)+2]=1;s[R(r)+4]=NONE
    for m in range(2):s[P(m)+1]=m;s[P(m)+2]=s[P(m)+3]=NONE
    return bytes(s)

def claims(s):
    occupied=set()
    for m in range(2):
        p=P(m)
        if s[p]==1:occupied.update((3,s[p+2]))
    return occupied

def successors(s):
    t=s[0];busy=claims(s)
    def emit(kind,args,z):
        b=bytes(z)
        return (kind,*args),b
    if t<4:
        z=bytearray(s);z[0]+=1
        for r in range(4):
            j=R(r)
            if z[j+3]==1 and z[0]>z[j+4]:z[j]+=1;z[j+1]=z[j+3]=0;z[j+4]=NONE
        yield emit('tick',(),z)
    for m in range(2):
        owner=m+1;terminal=bool(s[3]&(1<<m));slots=(2*m,2*m+1)
        if not terminal:
            free=next((q for q in slots if not s[Q(q)]),None)
            inflight=any(s[Q(q)] and s[Q(q)+9]==0 for q in slots)
            if free is not None and not inflight:
                for mask in MASKS:
                    for due in range(5):
                        z=bytearray(s);j=Q(free);z[j:j+11]=bytes((1,s[1+m],mask,*(s[R(r)] for r in range(4)),due,t,0,0))
                        yield emit('issue',(free,mask,due),z)
            for mask in MASKS:
                selected=[r for r in range(4) if mask&(1<<r)]
                if any(not s[R(r)+2] or s[R(r)+1] not in (0,owner) or r in busy for r in selected):continue
                for expiry in range(t,5):
                    z=bytearray(s)
                    for r in selected:
                        j=R(r)
                        if z[j+3]==2:continue
                        if z[j+1]==0:z[j]+=1
                        z[j+1]=owner;z[j+3]=1;z[j+4]=min(z[j+4],expiry)
                    if z!=s:yield emit('hold',(m,mask,expiry),z)
            for bound in range(s[5+m]):
                z=bytearray(s);z[5+m]=bound;yield emit('wait',(m,bound),z)
            if not s[4]&(1<<m):
                z=bytearray(s);z[4]|=1<<m;z[1+m]+=1;yield emit('invalidate',(m,),z)
            if not any(s[P(i)]==1 and s[R(3)+1]==owner for i in range(2)):
                z=bytearray(s);z[3]|=1<<m;z[1+m]+=1
                for r in range(4):
                    j=R(r)
                    if z[j+1]==owner:z[j]+=1;z[j+1]=z[j+3]=0;z[j+4]=NONE
                yield emit('terminate',(m,),z)
        p=P(m)
        if s[p]==0 and not terminal and s[R(3)+2] and s[R(3)+1] in (0,owner) and 3 not in busy:
            for replacement in range(3):
                if replacement==s[p+1] or replacement in busy:continue
                if any(i!=m and s[P(i)+1]==replacement for i in range(2)):continue
                if not s[R(replacement)+2] or s[R(replacement)+1] not in (0,owner):continue
                for duration in (1,2):
                    z=bytearray(s);z[p]=1;z[p+2]=replacement;z[p+3]=t;z[p+4]=duration
                    yield emit('start',(m,replacement,duration),z)
        if s[p]==1:
            z=bytearray(s);z[p]=0;z[p+3]=NONE;yield emit('interrupt',(m,),z)
            if s[R(3)+2] and s[R(s[p+2])+2] and t>=s[p+3]+s[p+4]:
                z=bytearray(s);z[p]=2;z[p+1]=s[p+2];yield emit('finish',(m,),z)
    for r in range(4):
        j=R(r)
        if s[j+2]:
            z=bytearray(s);z[j+2]=0;z[j]+=1;yield emit('fail',(r,),z)
    for q in range(4):
        j=Q(q);m=q//2
        if not s[j]:continue
        if s[j+9]<2 and t>s[j+8]:
            z=bytearray(s);z[j+9]+=1
            if s[j+9]==0:z[j+10]=3 if s[3]&(1<<m) or s[j+1]!=s[1+m] else 1
            yield emit('receive',(q,),z)
        if s[j+10]==1:
            z=bytearray(s);z[j+10]=4;yield emit('cancel',(q,),z)
            if t>=s[j+7]:
                selected=[r for r in range(4) if s[j+2]&(1<<r)]
                valid=not s[3]&(1<<m) and s[j+1]==s[1+m] and all(s[R(r)]==s[j+3+r] and s[R(r)+2] for r in selected)
                conflict=any(s[R(r)+1] not in (0,m+1) or r in busy for r in selected)
                z=bytearray(s);z[j+10]=2 if valid and not conflict else 3
                if valid and not conflict:
                    z[1+m]+=1
                    for r in selected:k=R(r);z[k]+=1;z[k+1]=m+1;z[k+3]=2;z[k+4]=NONE
                yield emit('apply',(q,),z)

def violations(s,z,action):
    """Assertions use before/after state, never an executor's claimed success."""
    bad=[];kind=action[0]
    if z[0]<s[0]:bad.append('clock')
    active=[m for m in range(2) if z[P(m)]==1]
    if len(active)>1:bad.append('bay_capacity')
    if len({z[P(m)+2] for m in active})!=len(active):bad.append('carrier_capacity')
    if z[P(0)+1]==z[P(1)+1]:bad.append('multiple_payloads_on_unit_capacity_carrier')
    for r in range(4):
        j=R(r)
        if (z[j+1]==0)!=(z[j+3]==0):bad.append('owner_phase')
        if z[j+3]==1 and z[j+4]<z[0]:bad.append('expired_hold')
        if z[j+1] and z[3]&(1<<(z[j+1]-1)):bad.append('terminal_resource')
    for m in range(2):
        p=P(m)
        if z[5+m]>s[5+m]:bad.append('renewed_wait')
        if z[p+1]!=s[p+1]:
            if kind!='finish' or s[p]!=1 or s[0]<s[p+3]+s[p+4] or z[p+1]!=s[p+2]:bad.append('custody_causality')
    for q in range(4):
        j=Q(q);m=q//2
        if s[j] and z[j:j+9]!=s[j:j+9]:bad.append('proposal_mutation')
        if s[j+10] in (2,3,4) and z[j+10]!=s[j+10]:bad.append('operation_rollback')
        if s[j+10]!=2 and z[j+10]==2:
            selected=[r for r in range(4) if s[j+2]&(1<<r)]
            if kind!='apply' or s[j+10]!=1 or s[0]<s[j+7]:bad.append('apply_state_or_due')
            if s[3]&(1<<m) or s[j+1]!=s[1+m]:bad.append('mission_version')
            if any(s[R(r)]!=s[j+3+r] or not s[R(r)+2] for r in selected):bad.append('resource_version')
            if any(s[R(r)+1] not in (0,m+1) or r in claims(s) for r in selected):bad.append('commit_capacity')
            if any(z[R(r)+1]!=m+1 or z[R(r)+3]!=2 for r in selected):bad.append('atomicity')
    return sorted(set(bad))

def explore(out,max_states=1_000_000,max_seconds=600,depth=12):
    out.mkdir(parents=True,exist_ok=True);start=time.monotonic()
    states=[initial()];seen={states[0]:0};parents=array('i',[-1]);actions=array('H',[0]);depths=array('B',[0])
    catalog=[('initial',)];codes={catalog[0]:0};head=0;edges=0;counts=Counter();reason=None;failure=None
    while head<len(states):
        if time.monotonic()-start>=max_seconds:reason='wall_time_limit';break
        s=states[head];d=depths[head]
        if d==depth:head+=1;continue
        for action,z in successors(s):
            edges+=1;counts[action[0]]+=1
            bad=violations(s,z,action)
            if bad:
                trace=[action];index=head
                while index:trace.append(catalog[actions[index]]);index=parents[index]
                failure={'properties':bad,'shortest_trace':list(reversed(trace)),'before_hex':s.hex(),'after_hex':z.hex()};reason='counterexample';break
            if z in seen:continue
            if len(states)>=max_states:reason='state_limit';break
            if action not in codes:codes[action]=len(catalog);catalog.append(action)
            seen[z]=len(states);states.append(z);parents.append(head);actions.append(codes[action]);depths.append(d+1)
        if reason:break
        head+=1
        if head%10000==0:print(json.dumps({'expanded':head,'discovered':len(states),'current_depth':d,'elapsed_s':round(time.monotonic()-start,1)}),flush=True)
    elapsed=time.monotonic()-start
    # One fixed-width state per index plus parent/action records makes shortest
    # traces reconstructible even when the cap prevents completing the frontier.
    with gzip.open(out/'states.bin.gz','wb',compresslevel=1) as f:
        for state in states:f.write(state)
    with gzip.open(out/'parents.bin.gz','wb',compresslevel=1) as f:f.write(parents.tobytes())
    with gzip.open(out/'actions.bin.gz','wb',compresslevel=1) as f:f.write(actions.tobytes())
    with gzip.open(out/'depths.bin.gz','wb',compresslevel=1) as f:f.write(depths.tobytes())
    (out/'action_catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    if failure:(out/'counterexample.json').write_text(json.dumps(failure,indent=2),encoding='utf-8')
    report={'status':'counterexample' if failure else 'incomplete' if reason else 'bounded_model_complete','stop_reason':reason,'configured_depth':depth,'max_states':max_states,'max_seconds':max_seconds,'unique_states':len(states),'expanded_states':head,'transitions_checked':edges,'maximum_discovered_depth':max(depths),'fully_expanded_through_depth':(depths[head]-1 if head<len(states) else depth),'depth_histogram':dict(sorted(Counter(depths).items())),'action_transition_counts':dict(counts),'elapsed_s':round(elapsed,3),'counterexample':failure,'state_encoding':{'bytes_per_state':N,'parents_typecode':parents.typecode,'actions_typecode':actions.typecode,'byte_order':__import__('sys').byteorder,'frontier_head':head},'bounds':{'missions':2,'aircraft':2,'ground_vehicles':1,'bays':1,'requests_per_mission':2,'responses':4,'duplicates_per_response':1,'times':[0,1,2,3,4],'resource_bundles':'all 15 nonempty subsets','due_and_lease_ticks':[0,1,2,3,4]},'abstraction':'Both unique payloads accessible at V3; physical approach/flight not part of R1. All interleavings overapproximate fixed scheduler order. Failed no-op actions omitted; no POR/symmetry reduction. No progress proof from search depth.'}
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
