from pathlib import Path
import json,time,uuid
from run_r1_symbolic import run,dump,ROOT
def main():
    out=ROOT/'runs/protocol'/('r1_smt_mutants_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True);print('OUTPUT '+str(out),flush=True)
    targets={'skip_version':'version_consistency','duplicate_resets_due':'idempotence','allow_conflict':'resource_capacity','teleport_cargo':'transfer_causality','rollback_applied':'cancellation_consistency','partial_atomic':'resource_capacity','terminal_hold':'resource_capacity'}
    reports={}
    for mutant,prop in targets.items():
        report=run(out/mutant,12,15000,mutant,[prop]);rows=report['results'][prop];sat=next((r for r in rows if r['result']=='sat'),None)
        reports[mutant]={'property':prop,'detected':sat is not None,'shortest_depth':sat['depth'] if sat else None,'shortest_certified':sat.get('shortest') if sat else False,'report':str((out/mutant/'report.json').relative_to(ROOT))}
        dump(out/'report.json',{'mutants':reports,'all_detected':all(r['detected'] for r in reports.values())})
    assert all(r['detected'] and r['shortest_certified'] for r in reports.values()),reports
    dump(ROOT/'outputs/r1_symbolic/mutants_latest.json',{'run_dir':str(out.relative_to(ROOT)),'all_detected':True});print(json.dumps(reports,indent=2))
if __name__=='__main__':main()
