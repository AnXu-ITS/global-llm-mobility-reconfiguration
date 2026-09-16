from pathlib import Path
import sys,json,copy,subprocess,argparse
W=Path(__file__).resolve().parents[2]; R=W.parent
sys.path.insert(0,str(R))
from queue_fix import DeduplicatedExperiment4BRunner
from tools.run_experiment4 import load_e4,load_p3
from orchestrator import config as config_mod
from orchestrator.experiment1_runner import make_manager

def single(seed,manager,delay,fault,baseline=False):
    e4=load_e4(); p3=load_p3();cfg=config_mod.load_config()
    scenario=copy.deepcopy(next(s for s in e4['scenarios'] if s['id']=='E4_ANCHOR'))
    scenario['failure']['time_s']=fault
    arm={'id':f'D{delay:02d}','delay_s':delay}
    rd=W/f'source/revision_v3/regression/D{delay:02d}_F{fault}{"_baseline" if baseline else ""}/seed{seed}/{manager}'
    rd.mkdir(parents=True,exist_ok=True)
    from orchestrator.experiment4_runner import Experiment4BRunner
    cls=Experiment4BRunner if baseline else DeduplicatedExperiment4BRunner
    runner=cls(cfg,e4,'4B',arm,scenario,
        make_manager(manager,cfg,p3),R/'sim/sumo/canonical.sumocfg',rd,seed,phase3_config=p3)
    try:runner.setup();runner.run()
    finally:
        if runner.sumo:runner.sumo.close()
    print(json.dumps({'seed':seed,'manager':manager,'delay':delay,'fault':fault,
        'completion':json.loads((rd/'metrics.json').read_text())['critical_mission_completion_time_s']}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--single',nargs=4);ap.add_argument('--baseline',action='store_true');a=ap.parse_args()
    if a.single:
        seed,manager,delay,fault=a.single;single(int(seed),manager,int(delay),int(fault),a.baseline)
    else:
        jobs=[(s,'B0',60,360) for s in range(20240601,20240621)]
        jobs += [(20240601,m,d,f) for m,d,f in [('B0',0,360),('B0',30,360),('B0',60,359),('B0',60,361),('B1',60,360),('B2',60,360)]]
        for vals in jobs:
            log=W/('source/revision_v3/regression_'+('_'.join(map(str,vals)))+'.log')
            with log.open('w',encoding='utf-8') as f:
                p=subprocess.run([sys.executable,__file__,'--single',*map(str,vals)],stdout=f,stderr=subprocess.STDOUT)
            print(vals,p.returncode,flush=True)
            if p.returncode:raise RuntimeError(log.read_text()[-5000:])
