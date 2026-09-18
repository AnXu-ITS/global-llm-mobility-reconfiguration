"""Single-owner protocol kernel with inclusive leases and causal custody.

No simulator or model calls in this module. Times use simulator seconds.
Mutants are explicit test-only faults, never valid comparison methods.
"""
from dataclasses import dataclass,field
import copy,math,threading

@dataclass(frozen=True)
class Proposal:
    operation_id:str
    mission_id:str
    mission_version:int
    resources:tuple[str,...]
    resource_versions:tuple[int,...]
    due:int

@dataclass
class Resource:
    version:int=0
    owner:str|None=None
    available:bool=True
    valid_through:int|None=None
    phase:str='FREE'

@dataclass
class Payload:
    holder:str
    state:str='AT_ORIGIN'
    location:str|None=None
    transfer_start:int|None=None
    transfer_duration:int=0
    replacement:str|None=None
    transfer_bay:str|None=None

class Kernel:
    def __init__(self,missions=('m1','m2'),resources=('a1','a2','g1','bay'),mutant=None):
        self.owner_thread=threading.get_ident()
        self.versions={m:0 for m in missions}
        self.resources={r:Resource() for r in resources}
        self.operations={};self.applied=set();self.events=[];self.mutant=mutant
        self.payloads={};self.wait_until={};self.terminal=set();self.now=0
        self.transfer_claims={}
    def _owner(self):
        if threading.get_ident()!=self.owner_thread:raise RuntimeError('World mutation from non-owner thread')
    def emit(self,event,**fields):
        self._owner();self.events.append({'seq':len(self.events),'t':self.now,'event':event,**fields})
    def tick(self,t):
        self._owner()
        if t<self.now:raise ValueError('Time cannot reverse')
        self.now=t
        for key,r in self.resources.items():
            if r.phase=='HELD' and r.valid_through is not None and t>r.valid_through:
                self.emit('LEASE_EXPIRED',resource=key,owner=r.owner)
                r.owner=None;r.phase='FREE';r.valid_through=None;r.version+=1
    def hold(self,mission,resource_ids,valid_through):
        self._owner()
        if (mission not in self.versions or mission in self.terminal or not resource_ids
            or len(set(resource_ids))!=len(resource_ids) or any(r not in self.resources for r in resource_ids)
            or type(valid_through) is not int or valid_through<self.now):return False
        if any(r in self.transfer_claims or 'carrier:'+r in self.transfer_claims for r in resource_ids):return False
        if any(not self.resources[r].available or self.resources[r].owner not in (None,mission) for r in resource_ids):return False
        for key in resource_ids:
            r=self.resources[key]
            if r.phase=='OCCUPIED':continue
            if r.owner is None:r.version+=1
            r.owner=mission;r.phase='HELD'
            r.valid_through=min(r.valid_through,valid_through) if r.valid_through is not None else valid_through
        self.emit('HELD',mission=mission,resources=list(resource_ids),valid_through=valid_through);return True
    def propose(self,op,mission,resource_ids,due):
        return Proposal(op,mission,self.versions[mission],tuple(resource_ids),tuple(self.resources[r].version for r in resource_ids),due)
    def admit(self,p):
        self._owner()
        if (p.mission_id not in self.versions or not p.operation_id or not p.resources
            or len(p.resources)!=len(p.resource_versions) or len(set(p.resources))!=len(p.resources)
            or any(r not in self.resources for r in p.resources) or type(p.due) is not int
            or type(p.mission_version) is not int or any(type(v) is not int for v in p.resource_versions)):
            self.emit('MALFORMED_REJECTED',operation=p.operation_id);return False
        if p.operation_id in self.operations:
            if self.mutant=='duplicate_resets_due':self.operations[p.operation_id]['proposal']=p
            self.emit('DUPLICATE',operation=p.operation_id);return False
        if p.mission_id in self.terminal or p.mission_version!=self.versions[p.mission_id]:
            self.emit('STALE_REJECTED',operation=p.operation_id);return False
        self.operations[p.operation_id]={'proposal':p,'state':'PENDING'}
        self.emit('ADMITTED',operation=p.operation_id,due=p.due,mission=p.mission_id);return True
    def apply(self,op):
        self._owner();entry=self.operations[op];p=entry['proposal']
        if entry['state']!='PENDING' or self.now<p.due:return False
        valid=p.mission_id not in self.terminal and p.mission_version==self.versions[p.mission_id] and all(self.resources[r].version==v and self.resources[r].available for r,v in zip(p.resources,p.resource_versions))
        if not valid and self.mutant!='skip_version':
            entry['state']='REJECTED';self.emit('STALE_REJECTED',operation=op);return False
        conflict=any(self.resources[r].owner not in (None,p.mission_id) or r in self.transfer_claims or 'carrier:'+r in self.transfer_claims for r in p.resources)
        if conflict and self.mutant!='allow_conflict':
            entry['state']='REJECTED';self.emit('CONFLICT_REJECTED',operation=op);return False
        for key in p.resources:
            r=self.resources[key];r.owner=p.mission_id;r.phase='OCCUPIED';r.valid_through=None;r.version+=1
        entry['state']='APPLIED';self.applied.add(op);self.versions[p.mission_id]+=1
        self.emit('APPLIED',operation=op,mission=p.mission_id,resources=list(p.resources),validated=valid,conflict=conflict)
        return True
    def invalidate(self,mission):
        self._owner();self.versions[mission]+=1;self.emit('MISSION_INVALIDATED',mission=mission)
    def fail_resource(self,key):
        self._owner();r=self.resources[key];r.available=False;r.version+=1
        self.emit('RESOURCE_FAILED',resource=key)
    def cancel(self,op):
        self._owner();entry=self.operations[op]
        if entry['state']=='APPLIED':
            self.emit('CANCEL_AFTER_APPLIED',operation=op)
            if self.mutant=='rollback_applied':entry['state']='CANCELLED';self.applied.discard(op)
            return False
        if entry['state']!='PENDING':return False
        entry['state']='CANCELLED';self.emit('CANCELLED',operation=op);return True
    def complete(self,mission):
        self._owner()
        if mission in self.terminal:return False
        if any(self.resources[b].owner==mission for b in self.transfer_claims if b in self.resources):
            self.emit('TERMINAL_DEFERRED_ACTIVE_TRANSFER',mission=mission);return False
        self.terminal.add(mission);self.versions[mission]+=1
        for key,r in self.resources.items():
            if r.owner==mission:
                r.owner=None;r.phase='FREE';r.valid_through=None;r.version+=1
                self.emit('RESOURCE_RELEASED',resource=key,mission=mission)
        self.emit('MISSION_COMPLETE',mission=mission)
        return True
    def set_wait(self,mission,latest_start):
        self._owner();bound=math.floor(latest_start)
        if mission not in self.wait_until or self.mutant=='renew_forever':self.wait_until[mission]=bound
        else:self.wait_until[mission]=min(self.wait_until[mission],bound)
    def fallback_due(self,mission):return self.now>=self.wait_until[mission]
    def start_transfer(self,payload_id,replacement,site,old_ready,new_ready,bay_ready,duration,bay_resource='bay',mission=None):
        self._owner();p=self.payloads[payload_id]
        bay=self.resources.get(bay_resource)
        carrier=self.resources.get(replacement)
        cargo_slot_free=not any(key!=payload_id and cargo.holder==replacement and cargo.state not in ('DELIVERED','LOST') for key,cargo in self.payloads.items())
        legal=old_ready and new_ready and bay_ready and p.location==site and p.state=='WAITING_HANDOFF' and type(duration) is int and duration>0 and replacement!=p.holder and cargo_slot_free and bay is not None and bay.available and (bay.owner is None or bay.owner==mission) and (mission is None or mission in self.versions and mission not in self.terminal) and (carrier is None or carrier.available and (carrier.owner is None or carrier.owner==mission)) and bay_resource not in self.transfer_claims and 'carrier:'+replacement not in self.transfer_claims
        if not legal and self.mutant!='teleport_cargo':return False
        p.state='TRANSFERRING';p.transfer_start=self.now;p.transfer_duration=duration;p.replacement=replacement;p.transfer_bay=bay_resource
        self.transfer_claims[bay_resource]=payload_id;self.transfer_claims['carrier:'+replacement]=payload_id
        self.emit('TRANSFER_STARTED',payload=payload_id,holder=p.holder,replacement=replacement,site=site,duration=duration,bay=bay_resource,prerequisites=bool(legal));return True
    def finish_transfer(self,payload_id,still_ready=True):
        self._owner();p=self.payloads[payload_id]
        if p.state!='TRANSFERRING':return False
        carrier=self.resources.get(p.replacement)
        if not still_ready or not self.resources[p.transfer_bay].available or carrier is not None and not carrier.available:
            self.transfer_claims.pop(p.transfer_bay,None);self.transfer_claims.pop('carrier:'+p.replacement,None)
            p.state='WAITING_HANDOFF';p.transfer_start=None
            self.emit('TRANSFER_INTERRUPTED',payload=payload_id,holder=p.holder);return False
        if self.now<p.transfer_start+p.transfer_duration:return False
        self.transfer_claims.pop(p.transfer_bay,None);self.transfer_claims.pop('carrier:'+p.replacement,None)
        old=p.holder;p.holder=p.replacement;p.state='ON_REPLACEMENT';p.location=None
        self.emit('TRANSFER_COMPLETE',payload=payload_id,old_holder=old,holder=p.holder);return True
    def snapshot(self):
        return copy.deepcopy({'t':self.now,'versions':self.versions,'resources':{k:vars(v).copy() for k,v in self.resources.items()}})

    def audit_state(self):
        """Complete evidence for an independent transition checker, not an LLM view."""
        from dataclasses import asdict
        return copy.deepcopy({'t':self.now,'versions':self.versions,
            'resources':{k:asdict(v) for k,v in self.resources.items()},
            'operations':{k:{'proposal':asdict(v['proposal']),'state':v['state']} for k,v in self.operations.items()},
            'applied':sorted(self.applied),'terminal':sorted(self.terminal),
            'payloads':{k:asdict(v) for k,v in self.payloads.items()},
            'wait_until':self.wait_until,'transfer_claims':self.transfer_claims})

def check_events(events):
    errors=[];seen=set();transfers={}
    for e in events:
        if e['event']=='APPLIED':
            if e['operation'] in seen:errors.append('duplicate_side_effect')
            seen.add(e['operation'])
            if not e['validated']:errors.append('stale_applied')
            if e['conflict']:errors.append('resource_conflict')
        if e['event']=='TRANSFER_STARTED':
            if not e['prerequisites']:errors.append('cargo_prerequisites')
            if e['payload'] in transfers:errors.append('overlapping_transfer')
            transfers[e['payload']]=e
        if e['event']=='TRANSFER_INTERRUPTED':transfers.pop(e['payload'],None)
        if e['event']=='TRANSFER_COMPLETE':
            start=transfers.pop(e['payload'],None)
            if start is None:errors.append('unstarted_transfer')
            elif e['t']<start['t']+start['duration']:errors.append('early_transfer')
            elif e['old_holder']!=start['holder'] or e['holder']!=start['replacement']:errors.append('custody_mismatch')
    return errors
