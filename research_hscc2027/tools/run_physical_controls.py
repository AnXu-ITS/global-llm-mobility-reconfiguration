"""Run and audit facility-delay controls with saved console and source fingerprints."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time,uuid
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'runs/development'/('physical_controls_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
    records=[]
    for delay in (0,30,120):
        cp=subprocess.run([sys.executable,'-B',str(ROOT/'tools/run_minimal_physical.py'),'--facility-delay',str(delay)],capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONIOENCODING':'utf-8'},timeout=120)
        (out/f'facility_{delay}_console.log').write_text(cp.stdout+'\n'+cp.stderr,encoding='utf-8')
        assert cp.returncode==0,cp.stdout+cp.stderr
        rd=Path(next(x[7:] for x in cp.stdout.splitlines() if x.startswith('OUTPUT ')))
        report=json.loads((rd/'report.json').read_text());events=[json.loads(x) for x in (rd/'events.jsonl').read_text().splitlines()]
        trajectory=[json.loads(x) for x in (rd/'trajectory.jsonl').read_text().splitlines()]
        def event(name):return next(e for e in events if e['event']==name)
        start=event('TRANSFER_STARTED');end=event('TRANSFER_COMPLETE');arrival=event('GROUND_PHYSICAL_ARRIVAL');delivered=event('DELIVERED')
        assert start['t']==report['physical_ready_s']+delay
        assert end['t']==start['t']+30
        assert delivered['t']==arrival['t']+15
        assert any(x['ground_speed'] and x['ground_speed']>0.1 for x in trajectory if end['t']<x['t']<arrival['t'])
        holders=[(a,b) for a,b in zip(trajectory,trajectory[1:]) if a['payload_holder']!=b['payload_holder']]
        assert [(b['t'],b['payload_holder']) for a,b in holders]==[(315,'M-UAV-02'),(end['t'],'GROUND-CARGO'),(delivered['t'],'V1')]
        assert event('LATE_RESPONSE_DISCARDED')['t']==480
        assert report['air_moving_ticks_while_proposal_pending']>0 and not report['errors']
        records.append({'run_dir':str(rd.relative_to(ROOT)),**report,'handoff_complete_s':end['t'],'trace_audit_passed':True})
    assert len({r['physical_ready_s'] for r in records})==1
    assert records[-1]['delivery_time_s']>records[0]['delivery_time_s']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'runtime_v2/core.py',ROOT/'tools/run_minimal_physical.py',Path(__file__)]}
    summary={'status':'passed','records':records,'source_sha256':hashes,'llm_calls':0,'scope':'Three deterministic engineering controls; real SUMO/BlueSky traces, emulated late proposer, not native model or full S1 cohort'}
    (out/'report.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2));print('REPORT '+str(out/'report.json'))
if __name__=='__main__':main()
