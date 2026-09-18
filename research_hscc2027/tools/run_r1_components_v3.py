"""Fresh component evidence, preserving all previous R1 attempts."""
from pathlib import Path
from dataclasses import replace
import hashlib,json,sys,time,uuid
from run_r1_full import ROOT,dump,VARIANTS,semantic_witness,regressions,mutations,mailbox_tests,progress_tests
from r1_conformance import Projection
from r1_symbolic import decode_action
from check_protocol_trace import check

def main():
    out=ROOT/'runs/protocol'/('r1_components_v3_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True);print('OUTPUT '+str(out),flush=True)
    n=0
    for family,variants in VARIANTS.items():
        for variant in variants:dump(out/'witnesses'/(family+'_'+variant+'.json'),semantic_witness(family,variant));n+=1
    report={'semantic_witnesses':n,'regressions':regressions(out/'regressions'),'runtime_mutants':mutations(out/'mutants'),'mailbox':mailbox_tests(out/'mailbox'),'progress':progress_tests(out/'progress')}
    pointer=json.loads((ROOT/'outputs/r1_symbolic/mutants_latest.json').read_text(encoding='utf-8'));mutant_root=ROOT/pointer['run_dir'];replays={}
    for mutant in ('skip_version','duplicate_resets_due','allow_conflict','teleport_cargo','rollback_applied'):
        source=next((mutant_root/mutant/'witnesses').glob('*.json'));w=json.loads(source.read_text(encoding='utf-8'));p=Projection(mutant)
        for a in w['actions']:
            chosen=decode_action(a)
            if mutant=='teleport_cargo' and chosen[0]=='start':
                m,rep,duration=chosen[1:];ready=a['readiness'];p.call('start_transfer',f'p{m}',('a1','a2','g1')[rep],'V3' if ready&8 else 'V2',bool(ready&1),bool(ready&2),bool(ready&4),duration,mission=f'm{m+1}')
            elif mutant=='duplicate_resets_due' and chosen[0]=='receive' and p.receipts[chosen[1]]==1:
                q=chosen[1];proposal=p.requests[q][0];p.call('admit',replace(proposal,due=a['value']));p.receipts[q]+=1
            else:p.execute(chosen)
        errors=sorted({e for row in p.audit for e in row['errors']});assert errors,(mutant,source)
        dump(out/'symbolic_witness_replay'/(mutant+'.json'),{'symbolic_witness':str(source.relative_to(ROOT)),'detected_by_independent_runtime_audit':errors,'runtime':p.audit})
        replays[mutant]={'status':'detected','errors':errors,'witness':str(source.relative_to(ROOT))}
    report['symbolic_witness_runtime_replays']=replays
    report['additional_symbolic_only_mutants']=['partial_atomic','terminal_hold']
    report['physical_A_trace']=check(ROOT/'runs/development/physical_20260918_174345_352f9c/protocol_transitions.jsonl')
    assert report['physical_A_trace']['status']=='passed'
    report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'runtime_v2/core.py',ROOT/'runtime_v2/audit.py',ROOT/'runtime_v2/response_adapter.py',Path(__file__)]}
    report['status']='passed';dump(out/'report.json',report);dump(ROOT/'outputs/r1_symbolic/components_latest.json',{'run_dir':str(out.relative_to(ROOT)),'status':'passed'});print(json.dumps(report,indent=2))
if __name__=='__main__':main()
