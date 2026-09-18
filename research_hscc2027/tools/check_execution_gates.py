"""Read-only ordered readiness check. Exit 2 means closed, not a test failure."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def main():
    config_path=ROOT/'config/execution_gates.v2.json'
    if not config_path.exists():config_path=ROOT/'config/execution_gates.v1.json'
    cfg=read(config_path);rows=[];prior=True
    for gate in cfg['sequence']:
        if gate=='R1':
            pointer=read(ROOT/cfg['r1_pointer']);report_path=ROOT/pointer['run_dir']/'report.json';r=read(report_path)
            source_match=all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in r['source_sha256'].items())
            if r.get('verification_method')=='symbolic_bmc_exact_property_decomposition_v0.3':
                evidence_match=all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in r['evidence_sha256'].items())
                passed=bool(r['full_G1_gate'] and r['depth']==12 and len(r['properties'])==6 and all(v=='PASS_BOUNDED' for v in r['properties'].values()) and all(r['checks'].values()) and source_match and evidence_match)
                reason='passed_declared_bounded_scope' if passed else 'symbolic_evidence_or_source_mismatch'
            else:
                search=r['bounded_exploration'];passed=bool(r['full_G1_gate'] and search['status']=='bounded_model_complete' and search['configured_depth']==12 and source_match)
                reason='passed_declared_bounded_scope' if passed else 'source_changed_requires_revalidation' if not source_match else search['stop_reason'] or r['status']
        else:
            report_path=cfg['acceptance_reports'][gate];r=read(ROOT/report_path) if report_path else {}
            # Future site acceptance runners must populate these evidence
            # records; manual status notes alone never enable this checker.
            passed=bool(r.get('gate')==gate and r.get('status')=='passed' and r.get('checks') and all(v is True for v in r['checks'].values()) and r.get('evidence_sha256') and all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in r['evidence_sha256'].items()))
            reason='passed' if passed else 'acceptance_evidence_missing'
        ready=prior and passed
        rows.append({'gate':gate,'status':'passed' if ready else 'blocked_by_prior_gate' if not prior else 'not_passed','reason':reason,'evidence':str(report_path) if report_path else None})
        prior=ready
    result={'sequence':rows,'first_unpassed':next((row['gate'] for row in rows if row['status']!='passed'),None),'formal_transport_run_enabled':False,'note':'Read-only inspection; does not mutate gates, freeze fixtures, or launch experiments.'}
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if prior else 2
if __name__=='__main__':raise SystemExit(main())
