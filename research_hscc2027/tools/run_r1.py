"""Executable protocol witnesses, test-only mutations and bounded schedule exploration."""
from pathlib import Path
import itertools,json,sys,time,uuid,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from runtime_v2.core import Kernel,Payload,Proposal,check_events

VARIANTS={
    'duplicate':['same_pending','later_due','earlier_due','after_apply','after_cancel','different_resources'],
    'reordered':['mission_version','resource_failure','lease_expiry_version','terminal_mission','fresh_after_invalidate','snapshot_isolation'],
    'timeout':['late_after_fallback','late_admit','floor_boundary','retries_no_renewal','earlier_bound','terminal_pending'],
    'contention':['held_conflict','occupied_conflict','atomic_bundle','inclusive_expiry','commit_at_boundary','release_after_boundary'],
    'handoff':['old_absent','new_absent','bay_closed','wrong_site','interrupt_restart','exact_duration'],
    'cancel':['pending','applied','repeated','rejected','duplicate_after_cancel','resources_unchanged'],
    'fault_same_tick':['fault_before_apply','apply_before_fault','mission_fault','other_resource_fault','held_resource_fault','fresh_faulty_resource'],
    'progress':['fixed_wait','shorten_wait','no_hold_renewal','fallback_commit','terminal_release','terminal_no_new_work'],
}

def semantic_witness(family,variant):
    k=Kernel();k.tick(10)
    def admit(op='op1',mission='m1',resources=('a1',),due=12):
        p=k.propose(op,mission,resources,due);assert k.admit(p);return p
    v=variant
    if family=='duplicate':
        p=admit()
        if v=='after_apply':k.tick(12);assert k.apply('op1')
        if v=='after_cancel':assert k.cancel('op1')
        before=k.operations['op1'].copy()
        due={'later_due':19,'earlier_due':10}.get(v,12)
        q=k.propose('op1','m1',('a2',) if v=='different_resources' else ('a1',),due)
        assert not k.admit(q);assert k.operations['op1']==before
        assert k.resources['a2'].owner is None
    elif family=='reordered':
        p=admit()
        if v=='mission_version':k.invalidate('m1')
        elif v=='resource_failure':k.fail_resource('a1')
        elif v=='lease_expiry_version':assert k.hold('m2',('a1',),10);k.tick(11)
        elif v=='terminal_mission':k.complete('m1')
        elif v=='fresh_after_invalidate':
            k.invalidate('m1');admit('fresh');k.tick(12);assert k.apply('fresh')
        elif v=='snapshot_isolation':
            snap=k.snapshot();snap['versions']['m1']=999;snap['resources']['a1']['owner']='m2'
            assert k.versions['m1']==0 and k.resources['a1'].owner is None
            k.tick(12);assert k.apply('op1');return k.events
        k.tick(12);assert not k.apply('op1')
    elif family=='timeout':
        p=k.propose('late','m1',('a1',),13)
        if v=='late_after_fallback':
            assert k.admit(p);admit('fb',resources=('g1',),due=10);assert k.apply('fb');k.tick(13);assert not k.apply('late')
        elif v=='late_admit':
            admit('fb',resources=('g1',),due=10);assert k.apply('fb');assert not k.admit(p)
        elif v=='floor_boundary':
            k.set_wait('m1',12.9);k.tick(11);assert not k.fallback_due('m1');k.tick(12);assert k.fallback_due('m1')
        elif v=='retries_no_renewal':
            k.set_wait('m1',12)
            for bound in (13,99,1000):k.set_wait('m1',bound)
            assert k.wait_until['m1']==12
        elif v=='earlier_bound':k.set_wait('m1',20);k.set_wait('m1',11);k.tick(11);assert k.fallback_due('m1')
        elif v=='terminal_pending':assert k.admit(p);k.complete('m1');k.tick(13);assert not k.apply('late')
    elif family=='contention':
        if v=='held_conflict':
            assert k.hold('m2',('a1',),12);admit(due=10);assert not k.apply('op1');assert k.resources['a1'].owner=='m2'
        elif v=='occupied_conflict':
            admit('owner','m2',due=10);assert k.apply('owner');admit(due=10);assert not k.apply('op1')
        elif v=='atomic_bundle':
            assert k.hold('m2',('bay',),12);admit(resources=('g1','bay'),due=10)
            assert not k.apply('op1');assert k.resources['g1'].owner is None and k.resources['g1'].version==0
        elif v=='inclusive_expiry':
            assert k.hold('m1',('a1',),12);k.tick(12);assert not k.hold('m2',('a1',),13)
        elif v=='commit_at_boundary':
            assert k.hold('m1',('a1',),12);admit();k.tick(12);assert k.apply('op1');k.tick(13);assert k.resources['a1'].phase=='OCCUPIED'
        elif v=='release_after_boundary':
            assert k.hold('m1',('a1',),12);k.tick(13);assert k.hold('m2',('a1',),14)
    elif family=='handoff':
        k.payloads['p']=Payload('a1','WAITING_HANDOFF','V3')
        flags={'old_absent':(False,True,True),'new_absent':(True,False,True),'bay_closed':(True,True,False)}
        if v in flags:assert not k.start_transfer('p','g1','V3',*flags[v],2)
        elif v=='wrong_site':assert not k.start_transfer('p','g1','V2',True,True,True,2)
        else:
            assert k.start_transfer('p','g1','V3',True,True,True,2)
            k.tick(11);assert not k.finish_transfer('p');assert k.payloads['p'].holder=='a1'
            if v=='interrupt_restart':
                assert not k.finish_transfer('p',False);assert k.payloads['p'].holder=='a1'
                assert k.start_transfer('p','g1','V3',True,True,True,2)
                k.tick(12);assert not k.finish_transfer('p');k.tick(13)
            else:k.tick(12)
            assert k.finish_transfer('p');assert k.payloads['p'].holder=='g1';assert not k.finish_transfer('p')
    elif family=='cancel':
        p=admit()
        if v=='applied':
            k.tick(12);assert k.apply('op1');assert not k.cancel('op1');assert k.operations['op1']['state']=='APPLIED' and 'op1' in k.applied
        elif v=='rejected':
            k.invalidate('m1');k.tick(12);assert not k.apply('op1');assert not k.cancel('op1');assert k.operations['op1']['state']=='REJECTED'
        else:
            before=k.snapshot()['resources'];assert k.cancel('op1')
            if v=='repeated':assert not k.cancel('op1')
            if v=='duplicate_after_cancel':assert not k.admit(p)
            if v=='resources_unchanged':assert k.snapshot()['resources']==before
            k.tick(12);assert not k.apply('op1')
    elif family=='fault_same_tick':
        if v=='held_resource_fault':assert k.hold('m1',('a1',),12)
        admit();k.tick(12)
        if v=='apply_before_fault':
            assert k.apply('op1');k.fail_resource('a1');assert 'op1' in k.applied
        elif v=='other_resource_fault':k.fail_resource('a2');assert k.apply('op1')
        else:
            if v=='mission_fault':k.invalidate('m1')
            else:k.fail_resource('a1')
            if v=='fresh_faulty_resource':admit('fresh');assert not k.apply('fresh')
            assert not k.apply('op1')
    elif family=='progress':
        if v=='fixed_wait':k.set_wait('m1',12);k.set_wait('m1',99);k.tick(12);assert k.fallback_due('m1')
        elif v=='shorten_wait':k.set_wait('m1',20);k.set_wait('m1',12);k.tick(12);assert k.fallback_due('m1')
        elif v=='no_hold_renewal':
            assert k.hold('m1',('a1',),12);assert k.hold('m1',('a1',),99);k.tick(13);assert k.resources['a1'].owner is None
        elif v=='fallback_commit':
            k.set_wait('m1',12);k.tick(12);assert k.fallback_due('m1');admit('fb',resources=('g1','bay'));assert k.apply('fb')
        elif v=='terminal_release':
            admit(due=10);assert k.apply('op1');k.complete('m1');assert k.resources['a1'].owner is None
        elif v=='terminal_no_new_work':k.complete('m1');assert not k.admit(k.propose('new','m1',('a1',),12))
    assert not check_events(k.events),check_events(k.events)
    return k.events

def witness(family,offset,mutant=None):
    k=Kernel(mutant=mutant);k.tick(offset)
    p=k.propose('op1','m1',('a1',),offset+2);k.admit(p)
    if family=='duplicate':
        k.admit(k.propose('op1','m1',('a1',),offset+9))
        assert k.operations['op1']['proposal'].due==offset+2
        k.tick(offset+2);assert k.apply('op1');assert not k.apply('op1')
    elif family=='reordered':
        k.invalidate('m1');k.tick(offset+2);assert not k.apply('op1')
    elif family=='timeout':
        k.invalidate('m1');q=k.propose('fallback','m1',('g1',),offset);k.admit(q);assert k.apply('fallback')
        k.tick(offset+3);assert not k.apply('op1')
    elif family=='contention':
        q=k.propose('op2','m2',('a1',),offset+2);k.admit(q)
        assert k.hold('m2',('a1',),offset+2)
        # Refresh m1's expected version so resource conflict is tested independently.
        k.operations['op1']['proposal']=k.propose('op1','m1',('a1',),offset+2)
        k.tick(offset+2);assert not k.apply('op1');assert k.resources['a1'].owner=='m2'
        k.tick(offset+3);assert k.resources['a1'].owner is None
    elif family=='handoff':
        k.payloads['p']=Payload('a1','WAITING_HANDOFF','V3')
        assert not k.start_transfer('p','g1','V3',True,False,True,2)
        assert k.start_transfer('p','g1','V3',True,True,True,2)
        k.tick(offset+1);assert not k.finish_transfer('p');assert k.payloads['p'].holder=='a1'
        assert not k.finish_transfer('p',False);assert k.payloads['p'].holder=='a1'
        assert k.start_transfer('p','g1','V3',True,True,True,2)
        k.tick(offset+3);assert k.finish_transfer('p');assert k.payloads['p'].holder=='g1'
    elif family=='cancel':
        k.tick(offset+2);assert k.apply('op1');assert not k.cancel('op1');assert 'op1' in k.applied
        assert k.operations['op1']['state']=='APPLIED'
    elif family=='fault_same_tick':
        k.tick(offset+2);k.fail_resource('a1');assert not k.apply('op1')
    elif family=='progress':
        k.set_wait('m1',offset+2.9);k.tick(offset+2)
        k.set_wait('m1',offset+100);assert k.fallback_due('m1')
        # Inclusive lease remains available for atomic commit at the boundary.
        assert k.hold('m1',('g1',),offset+2)
        q=k.propose('fb','m1',('g1',),offset+2);k.admit(q);assert k.apply('fb')
        assert k.resources['g1'].phase=='OCCUPIED'
    assert not check_events(k.events),check_events(k.events)
    return k.events

def explore():
    """All 6! orders in a deliberately smaller, explicitly reported R1 submodel."""
    seen=set();errors=[];traces=0
    for order in itertools.permutations(('admit1','admit2','fault','invalidate','apply1','apply2')):
        k=Kernel();p=k.propose('o1','m1',('a1',),0);q=k.propose('o2','m2',('a1',),0)
        for event in order:
            if event=='admit1':k.admit(p)
            elif event=='admit2':k.admit(q)
            elif event=='fault':k.fail_resource('a1')
            elif event=='invalidate':k.invalidate('m1')
            elif event=='apply1' and 'o1' in k.operations:k.apply('o1')
            elif event=='apply2' and 'o2' in k.operations:k.apply('o2')
            state={'versions':k.versions,'resources':{r:vars(v) for r,v in k.resources.items()},'ops':{o:v['state'] for o,v in k.operations.items()}}
            seen.add(json.dumps(state,sort_keys=True))
        errors.extend(check_events(k.events));traces+=1
    assert not errors
    return {'traces':traces,'unique_states':len(seen),'depth':6,'scope':'all permutations of six one-shot events, two missions sharing one aircraft; not complete proposed depth-12 model','errors':errors}

def main():
    out=ROOT/'runs/protocol'/('r1_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
    families=['duplicate','reordered','timeout','contention','handoff','cancel','fault_same_tick','progress'];passed=[]
    for f in families:
        for variant in VARIANTS[f]:
            events=semantic_witness(f,variant)
            (out/f'{f}_{variant}.json').write_text(json.dumps(events,indent=2),encoding='utf-8');passed.append(f'{f}_{variant}')
    mutants={'duplicate_resets_due':'duplicate','skip_version':'reordered','allow_conflict':'contention','teleport_cargo':'handoff','rollback_applied':'cancel','renew_forever':'progress'}
    caught={}
    for mutant,family in mutants.items():
        try:witness(family,0,mutant)
        except AssertionError:caught[mutant]=True
        else:caught[mutant]=False
    assert all(caught.values()),caught
    # World-owner protection is independent of the simulator backend.
    from concurrent.futures import ThreadPoolExecutor
    k=Kernel()
    with ThreadPoolExecutor(1) as pool:
        try:pool.submit(k.tick,1).result()
        except RuntimeError:owner_guard=True
        else:owner_guard=False
    assert owner_guard
    malformed=[Proposal('bad','m1',0,('a1',),(),12),Proposal('bad','unknown',0,('a1',),(0,),12),Proposal('bad','m1',0,('a1','a1'),(0,0),12)]
    for p in malformed:assert not Kernel().admit(p)
    report={'specified_witnesses_passed':len(passed),'witness_note':'8 families x 6 named semantic variants; engineering coverage, not a proof of full protocol','variants':VARIANTS,'mutants_detected':caught,'bounded_exploration':explore(),'owner_thread_guard':owner_guard,'malformed_proposals_rejected':len(malformed),'full_G1_gate':'not_claimed; larger depth-12 model and adapter-level delayed/reordered I/O pending','llm_calls':0}
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2));print('REPORT '+str(out/'report.json'))
if __name__=='__main__':main()
