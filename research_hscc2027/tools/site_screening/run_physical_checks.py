from screen_sites import ROOT,OUT,dump,sha
from pathlib import Path
import json,os,subprocess,sys,time,uuid
def main():
    out=ROOT/'runs/site_diagnostics'/('air_ground_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
    records=[]
    for site in 'DEF':
        cp=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/run_minimal_physical.py'),'--site',site],capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONIOENCODING':'utf-8'},timeout=120)
        (out/f'{site}_console.log').write_text(cp.stdout+'\n'+cp.stderr,encoding='utf-8')
        rd=Path(next(x[7:] for x in cp.stdout.splitlines() if x.startswith('OUTPUT ')))
        record={'site_id':site,'exit_code':cp.returncode,'run_dir':str(rd.relative_to(ROOT))}
        if (rd/'report.json').exists():record.update(json.loads((rd/'report.json').read_text(encoding='utf-8')))
        if (rd/'failure.json').exists():record['failure']=json.loads((rd/'failure.json').read_text(encoding='utf-8'))
        records.append(record);dump(OUT/'frozen'/site/'physical_diagnostic_pointer.json',record)
        print(json.dumps(record),flush=True)
    dump(out/'report.json',{'records':records,'all_passed':all(x['exit_code']==0 and x.get('status')=='passed' for x in records),'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'runtime_v2/core.py',ROOT/'tools/run_minimal_physical.py',Path(__file__)]},'scope':'single-cargo engineering path on each real road network; does not validate multi-task site admission gates','llm_calls':0})
    assert all(x['exit_code']==0 and x.get('status')=='passed' for x in records)
if __name__=='__main__':main()
