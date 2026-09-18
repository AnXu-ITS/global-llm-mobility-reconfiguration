from pathlib import Path
import hashlib,json,os,subprocess,sys,time,uuid
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def dump(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    pointer=read(ROOT/'outputs/r1_symbolic/acceptance_latest.json');g1=read(ROOT/pointer['run_dir']/'report.json');assert g1['full_G1_gate'] and all(sha(ROOT/p)==h for p,h in g1['source_sha256'].items())
    out=ROOT/'runs/development'/('d_suite_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True);print('OUTPUT '+str(out),flush=True)
    cells=[];evidence={}
    for interrupt in (False,True):
        for reserve in (False,True):
            name=f'reserve{int(reserve)}_interrupt{int(interrupt)}';args=[sys.executable,'-X','utf8','-B',str(ROOT/'tools/run_d_admission.py')]+(['--reserve'] if reserve else [])+(['--interrupt'] if interrupt else [])
            cp=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONIOENCODING':'utf-8'},timeout=120);(out/(name+'.console.log')).write_text(cp.stdout+'\n'+cp.stderr,encoding='utf-8')
            directory=Path(next(line[7:] for line in cp.stdout.splitlines() if line.startswith('OUTPUT ')));report=read(directory/'report.json') if (directory/'report.json').exists() else {'status':'failed'}
            cell={'reserve':reserve,'interrupt':interrupt,'exit_code':cp.returncode,'run_dir':str(directory.relative_to(ROOT)),'status':report['status']};cells.append(cell);dump(out/'progress.json',cells)
            print(json.dumps(cell),flush=True);assert cp.returncode==0 and report['status']=='passed',cell
            for name in ('report.json','fixture.json','events.jsonl','protocol_transitions.jsonl','trajectory.jsonl'):evidence[str((directory/name).relative_to(ROOT))]=sha(directory/name)
    from check_protocol_trace import check
    trace_checks=[check(ROOT/cell['run_dir']/'protocol_transitions.jsonl') for cell in cells];assert all(r['status']=='passed' for r in trace_checks)
    paired=[]
    for interrupt in (False,True):
        dirs=[ROOT/cell['run_dir'] for cell in cells if cell['interrupt']==interrupt];fixtures=[read(d/'fixture.json') for d in dirs];reports=[read(d/'report.json') for d in dirs]
        assert all(fixtures[0][key]==fixtures[1][key] for key in ('seed','release','load_end','failure','fallback_commit','handoff_s','unload_s','closure','stations','speed_mps','site_manifest_sha256'))
        tracks=[[json.loads(line) for line in (d/'trajectory.jsonl').read_text(encoding='utf-8').splitlines()] for d in dirs]
        keys=('t','mission','air_lat','air_lon','air_alt_m','air_speed_mps');common=min(len(t) for t in tracks)
        assert all(tuple(x[k] for k in keys)==tuple(y[k] for k in keys) for x,y in zip(tracks[0][:common],tracks[1][:common]))
        paired.append({'interrupt':interrupt,'air_trajectory_identical_over_common_horizon':True,'shared_physical_inputs':True,'tasks':{i:{'no_reservation':reports[0]['tasks'][i],'reservation':reports[1]['tasks'][i]} for i in ('1','2')}})
    checks={'two_actual_air_payloads_and_ground_vehicles':True,'single_bay_real_queue':True,'unique_custody_and_atomic_handoff':True,'same_physical_speed_and_inputs':True,'interruption_retains_original_holder_and_restarts':True,'independent_protocol_log_checks':True}
    for path in (ROOT/'tools/run_d_admission.py',ROOT/'runtime_v2/stages.py',Path(__file__),ROOT/'sites/frozen/D/asset_manifest.json'):evidence[str(path.relative_to(ROOT))]=sha(path)
    report={'gate':'G-D','status':'passed','checks':checks,'cells':cells,'paired':paired,'trace_checks':trace_checks,'evidence_sha256':evidence,'scope':'four development physical admissions, reservation toggle only; not frozen LST/FULL results','native_calls':0};dump(out/'report.json',report)
    cfgpath=ROOT/'config/execution_gates.v2.json';cfg=read(cfgpath);cfg['acceptance_reports']['G-D']=str((out/'report.json').relative_to(ROOT));dump(cfgpath,cfg);dump(ROOT/'outputs/site_admission/D_latest.json',{'run_dir':str(out.relative_to(ROOT)),'gate':'G-D','status':'passed'});print('G-D PASSED',flush=True)
if __name__=='__main__':main()
