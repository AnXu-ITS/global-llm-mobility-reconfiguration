"""Recheck runtime pre/post-state logs without trusting recorded error flags."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from runtime_v2.audit import check_transition

def check(path):
    failures=[];count=0;previous=None
    with Path(path).open(encoding='utf-8') as stream:
        for count,line in enumerate(stream,1):
            r=json.loads(line);errors=check_transition(r['before'],r['after'],r['action'],r['args'])
            if previous is not None:
                for key in ('t','versions','resources','operations','applied','terminal','wait_until','transfer_claims'):
                    if r['before'][key]!=previous[key]:errors.append('unlogged_protocol_state_change:'+key)
            previous=r['after']
            if errors:failures.append({'line':count,'action':r['action'],'errors':errors})
    return {'status':'passed' if not failures and count else 'failed','transitions':count,'failures':failures,'scope':'protocol pre/post-state predicates; not a substitute for physical event provenance'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('trace');a=p.parse_args();report=check(a.trace);print(json.dumps(report,indent=2));raise SystemExit(0 if report['status']=='passed' else 1)
