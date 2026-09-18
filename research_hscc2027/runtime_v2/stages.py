"""Audited physical-stage releases and availability restoration.

These extension operations are covered by physical admission tests, not by the
R1 v0.3 13-action finite core. They cannot acquire a resource or move a payload.
"""
from .audit import AuditedKernel,check_transition

class StageKernel(AuditedKernel):
    def _stage_change(self,action,args,change):
        self._owner();before=self.audit_state();result=change();after=self.audit_state()
        errors=check_transition(before,after,action,args)
        self.audit_records.append({'action':action,'args':list(args),'kwargs':{},'result':result,'before':before,'after':after,'errors':errors})
        if errors:raise AssertionError(errors)
        return result
    def release_resources(self,mission,keys,reason):
        keys=tuple(keys)
        def change():
            if any(key in self.transfer_claims or 'carrier:'+key in self.transfer_claims for key in keys):raise ValueError('interrupt/finish physical transfer before release')
            released=[]
            for key in keys:
                r=self.resources[key]
                if r.owner==mission:
                    r.owner=None;r.phase='FREE';r.valid_through=None;r.version+=1;released.append(key)
                    self.emit('STAGE_RESOURCE_RELEASED',mission=mission,resource=key,reason=reason)
            return released
        return self._stage_change('release_resources',(mission,keys,reason),change)
    def restore_resource(self,key,reason):
        def change():
            r=self.resources[key]
            if r.available:return False
            r.available=True;r.version+=1;self.emit('RESOURCE_RESTORED',resource=key,reason=reason);return True
        return self._stage_change('restore_resource',(key,reason),change)
