"""Independent pre/post-state assertions. Never trust APPLIED.validated/conflict.

This checks finite protocol transitions, not physical simulator truth. Arrival
observations still require backend provenance and physical integration tests.
"""

def check_transition(before, after, action, args=()):
    errors=[]
    def require(condition, name):
        if not condition: errors.append(name)
    require(after['t']>=before['t'],'clock_reversal')
    require(set(before['payloads'])==set(after['payloads']),'payload_created_or_lost')
    require(set(before['applied'])<=set(after['applied']),'applied_rollback')
    require(set(before['terminal'])<=set(after['terminal']),'terminal_rollback')
    for op,old in before['operations'].items():
        new=after['operations'].get(op)
        require(new is not None,'operation_erased')
        if new is None: continue
        require(new['proposal']==old['proposal'],'duplicate_changed_proposal_or_due')
        if old['state']!='PENDING':require(new['state']==old['state'],'terminal_operation_changed')
    fresh=set(after['applied'])-set(before['applied'])
    for op in fresh:
        old=before['operations'].get(op)
        require(old is not None and old['state']=='PENDING','apply_without_pending')
        if old is None: continue
        p=old['proposal'];m=p['mission_id']
        require(before['t']>=p['due'],'early_application')
        require(m not in before['terminal'] and p['mission_version']==before['versions'][m],'mission_version_mismatch')
        for r,v in zip(p['resources'],p['resource_versions']):
            resource=before['resources'][r]
            require(resource['version']==v and resource['available'],'resource_version_or_availability_mismatch')
            require(resource['owner'] in (None,m),'resource_capacity_conflict')
            require(r not in before['transfer_claims'] and 'carrier:'+r not in before['transfer_claims'],'active_transfer_conflict')
        require(all(after['resources'][r]['owner']==m and after['resources'][r]['phase']=='OCCUPIED' for r in p['resources']),'partial_bundle_commit')
    if action=='apply' and not fresh:
        require(after['resources']==before['resources'],'rejected_apply_changed_resources')
    if action=='hold':
        m,keys,_=args
        changed=before['resources']!=after['resources']
        if changed:
            require(m not in before['terminal'],'terminal_hold')
            require(all(after['resources'][r]['owner']==m for r in keys),'partial_bundle_hold')
    for m,bound in before['wait_until'].items():
        require(after['wait_until'].get(m,bound)<=bound,'waiting_episode_renewed')
    for r,resource in after['resources'].items():
        require(resource['phase'] in ('FREE','HELD','OCCUPIED'),'invalid_resource_phase')
        require((resource['owner'] is None)==(resource['phase']=='FREE'),'owner_phase_mismatch')
        if resource['phase']=='HELD':require(resource['valid_through'] is not None and resource['valid_through']>=after['t'],'expired_lease_retained')
        if resource['owner'] is not None:require(resource['owner'] not in after['terminal'],'terminal_resource_leak')
    expected={}
    for pid,p in after['payloads'].items():
        old=before['payloads'][pid]
        if p['holder']!=old['holder']:
            require(action=='finish_transfer' and old['state']=='TRANSFERRING','custody_without_transfer')
            require(before['t']>=old['transfer_start']+old['transfer_duration'],'premature_custody')
            require(p['holder']==old['replacement'],'wrong_new_custodian')
        if p['state']=='TRANSFERRING':
            for key in (p['transfer_bay'],'carrier:'+p['replacement']):
                require(key not in expected,'concurrent_transfer_capacity')
                expected[key]=pid
            require(p['holder']==old['holder'],'custody_before_completion')
            if old['state']!='TRANSFERRING':
                require(action=='start_transfer' and old['state']=='WAITING_HANDOFF','invalid_transfer_start')
                _,replacement,site,old_ready,new_ready,bay_ready,duration,*_=args
                require(old_ready and new_ready and bay_ready and old['location']==site and duration>0 and replacement!=old['holder'],'transfer_prerequisites')
                require(not any(key!=pid and other['holder']==replacement and other['state'] not in ('DELIVERED','LOST') for key,other in before['payloads'].items()),'replacement_already_carrying_payload')
    require(expected==after['transfer_claims'],'transfer_claim_state_mismatch')
    return sorted(set(errors))

def checked_call(kernel, action, *args, **kwargs):
    before=kernel.audit_state();result=getattr(kernel,action)(*args,**kwargs);after=kernel.audit_state()
    errors=check_transition(before,after,action,args)
    record={'action':action,'args':list(args),'kwargs':kwargs,'result':result,'before':before,'after':after,'errors':errors}
    return result,record


from .core import Kernel

class AuditedKernel(Kernel):
    """Same runtime transitions, with reusable independent evidence enabled."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.audit_records=[]

def _audited(name):
    def invoke(self,*args,**kwargs):
        before=self.audit_state();result=getattr(Kernel,name)(self,*args,**kwargs);after=self.audit_state()
        errors=check_transition(before,after,name,args)
        self.audit_records.append({'action':name,'args':list(args),'kwargs':kwargs,'result':result,'before':before,'after':after,'errors':errors})
        if errors:raise AssertionError({'action':name,'independent_audit':errors})
        return result
    return invoke

for _name in ('tick','hold','admit','apply','invalidate','fail_resource','cancel','complete','set_wait','start_transfer','finish_transfer'):
    setattr(AuditedKernel,_name,_audited(_name))
