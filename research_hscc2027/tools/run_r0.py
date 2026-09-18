"""Isolated deterministic legacy replay. No LLM factories, no legacy writes."""
from pathlib import Path
import argparse,copy,csv,hashlib,json,os,subprocess,sys,time,uuid
ROOT=Path(__file__).resolve().parents[1]; WS=ROOT.parent
VENDOR=ROOT/'vendor/legacy_platform'
sys.dont_write_bytecode=True
sys.path.insert(0,str(VENDOR))

def single(row,out):
    assert row['method'] in ('B0','B1','B2')
    from queue_fix import DeduplicatedExperiment4BRunner
    from orchestrator.experiment4_runner import Experiment4BRunner
    from tools.run_experiment4 import load_e4,load_p3
    from orchestrator.config import load_config
    from orchestrator.experiment1_runner import make_manager
    e4=load_e4();p3=load_p3();cfg=load_config()
    scenario=copy.deepcopy(next(x for x in e4['scenarios'] if x['id']=='E4_ANCHOR'))
    scenario['failure']['time_s']=int(row['failure_time_s']);delay=int(row['delay_s'])
    cls=Experiment4BRunner if row['executor']=='legacy_original' else DeduplicatedExperiment4BRunner
    runner=cls(cfg,e4,'4B',{'id':f'D{delay:02d}','delay_s':delay},scenario,
        make_manager(row['method'],cfg,p3),VENDOR/'sim/sumo/canonical.sumocfg',out,int(row['seed']),phase3_config=p3)
    try:runner.setup();runner.run()
    finally:
        if runner.sumo:runner.sumo.close()

def projection(path):
    if not path.exists():raise FileNotFoundError(path)
    with path.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    # decision identifiers may contain wallclock UUIDs; compare execution semantics.
    keys=['t','time_s','action_type','type','aircraft_id','mission_id','target_site','route','result']
    return [{k:r[k] for k in keys if k in r} for r in rows]

def pipeline(path):
    rows=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    return [{k:v for k,v in row.items() if k!='decision_id'} for row in rows]

def main():
    p=argparse.ArgumentParser();p.add_argument('--child');p.add_argument('--out');p.add_argument('--limit',type=int)
    a=p.parse_args()
    if a.child:
        row=json.loads(Path(a.child).read_text(encoding='utf-8')); single(row,Path(a.out));return
    out=ROOT/'runs/regression'/('r0_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
    rows=list(csv.DictReader((ROOT/'design/generated/r0_plan.csv').open(encoding='utf-8-sig')))
    rows=[r for r in rows if r['group']=='R0_REPLAY']
    if a.limit:rows=rows[:a.limit]
    results=[]
    for i,row in enumerate(rows):
        rd=out/f'{i:02d}_{row["method"]}_D{row["delay_s"]}_F{row["failure_time_s"]}_s{row["seed"]}';rd.mkdir()
        (rd/'input.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
        start=time.monotonic()
        with (rd/'console.log').open('w',encoding='utf-8') as log:
            proc=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--child',str(rd/'input.json'),'--out',str(rd)],cwd=rd,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1'},timeout=180)
        rec={'run_dir':str(rd.relative_to(ROOT)),'exit_code':proc.returncode,'wall_s':time.monotonic()-start,'expected_duration':float(row['expected_task_duration_s'])}
        if proc.returncode==0:
            observed=json.loads((rd/'metrics.json').read_text()); rec['observed_duration']=observed['critical_mission_completion_time_s']
            rec['metric_match']=rec['observed_duration']==rec['expected_duration']
            historical=(WS/row['historical_metrics']).parent
            rec['actions_match']=projection(rd/'actions.csv')==projection(historical/'actions.csv')
            rec['pipeline_match']=pipeline(rd/'action_pipeline.jsonl')==pipeline(historical/'action_pipeline.jsonl')
            rec['historical_metrics_sha256']=hashlib.sha256((historical/'metrics.json').read_bytes()).hexdigest()
            assert rec['historical_metrics_sha256']==row['historical_sha256']
        results.append(rec)
        report={'scope':'27 legacy replay controls; six runtime_v2 legacy bridges not yet implemented','runs':results,'completed':len(results),'planned':len(rows),'all_metric_match':all(r.get('metric_match',False) for r in results),'all_action_projections_match':all(r.get('actions_match',False) for r in results),'all_pipeline_projections_match':all(r.get('pipeline_match',False) for r in results),'llm_calls':0}
        (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(rec),flush=True)
        if proc.returncode:print((rd/'console.log').read_text(encoding='utf-8')[-4000:],flush=True);break
    print('REPORT '+str(out/'report.json'),flush=True)
    if not all(r.get('metric_match') and r.get('actions_match') and r.get('pipeline_match') for r in results):raise SystemExit(1)
if __name__=='__main__':main()
