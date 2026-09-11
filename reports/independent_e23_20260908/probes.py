"""Pure offline regression probes for the audit; no production imports."""
from pathlib import Path
from types import SimpleNamespace
import ast, json, math
import numpy as np
from scipy import stats
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent


def functions_from(path,names,ns):
    t=ast.parse(path.read_text(encoding='utf-8'))
    funcs=[n for n in ast.walk(t) if isinstance(n,ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=funcs,type_ignores=[]),str(path),'exec'),ns)
    return ns


ns=functions_from(OUT/'audit.py',{'finite','mean','paired','mc','holm'},dict(math=math,np=np,stats=stats))
tests=[{'p':.01},{'p':.04},{'p':.05}];ns['holm'](tests)
assert np.allclose([x['holm_p'] for x in tests],[.03,.08,.08])
tests=[{'p':float('nan')},{'p':.01}];ns['holm'](tests)
assert np.allclose([x['holm_p'] for x in tests],[1,.02])
assert ns['paired']([1,2],[1,2])['p']==1
assert ns['mc']([False]*5,[True]*5)['p']==.0625

periodic=functions_from(ROOT/'orchestrator/experiment3_runner.py',{'_periodic_due'},{} )['_periodic_due']
fake=SimpleNamespace(t=450,critical_t=300,periodic_s=30,emergencies=['M-CRITICAL-001'],
    registry=SimpleNamespace(missions={
        'M-CRITICAL-001':SimpleNamespace(status='EN_ROUTE'),
        'M-P-001':SimpleNamespace(status='NEEDS_REPLAN')}))
observed=periodic(fake)
assert observed is False
fake.registry.missions['M-CRITICAL-001'].status='NEEDS_REPLAN'
assert periodic(fake) is True

x=json.loads((OUT/'source_sha256.json').read_text(encoding='utf-8'))
y=json.loads((OUT/'diagnostic_sha256.json').read_text(encoding='utf-8'))
shared=x.keys()&y.keys()
changed=[k for k in shared if x[k]!=y[k]]
assert not changed
out={'independent_statistics_probes_passed':4,
     'production_periodic_trigger':{'background_needs_replan_primary_enroute':observed,'primary_needs_replan':True},
     'source_stability':{'shared_files':len(shared),'changed_files':changed}}
(OUT/'probe_results.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
