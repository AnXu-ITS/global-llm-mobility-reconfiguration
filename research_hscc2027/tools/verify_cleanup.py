"""Post-cleanup checks; original freeze manifests remain unchanged."""
from pathlib import Path
import csv,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1];WS=ROOT.parent;OUT=ROOT/'outputs/bootstrap';LEGACY=WS/'legacy/20260918'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    cache=json.loads((OUT/'cleanup_plan.json').read_text(encoding='utf-8'))
    cold=json.loads((OUT/'cold_storage_plan.json').read_text(encoding='utf-8'))
    assert all(not Path(x['path']).exists() for x in cache['files'])
    assert all(not Path(x).exists() for x in cold['targets'])
    journal=[json.loads(x) for x in (OUT/'cold_storage_journal.jsonl').read_text(encoding='utf-8-sig').splitlines() if x.strip()]
    assert {x['target'] for x in journal}==set(cold['targets'])
    tracked=subprocess.check_output(['git','-C',str(LEGACY),'ls-files','-z']).decode('utf-8').strip('\0').split('\0')
    with (WS/'provenance/hscc2027/legacy_file_inventory.csv').open(encoding='utf-8-sig') as f:inventory={r['original_path']:r for r in csv.DictReader(f)}
    for rel in tracked:assert sha(LEGACY/rel)==inventory[rel]['sha256'],rel
    with (ROOT/'design/generated/r0_plan.csv').open(encoding='utf-8-sig') as f:
        anchors={r['historical_metrics']:r['historical_sha256'] for r in csv.DictReader(f)}
    for rel,expected in anchors.items():assert sha(WS/rel)==expected
    subprocess.run(['git','-C',str(LEGACY),'diff','--quiet'],check=True)
    assert not subprocess.check_output(['git','-C',str(WS/'manuscript_hscc2027'),'status','--porcelain'],text=True).strip()
    probe=json.loads((OUT/'restore_probe_report.json').read_text(encoding='utf-8'));assert probe['passed']
    report={'status':'passed','cache_files_removed':len(cache['files']),'cache_bytes_removed':cache['total_bytes'],'cold_copy_files_removed':cold['files'],'cold_copy_bytes_removed':cold['bytes'],'total_files_removed':len(cache['files'])+cold['files'],'total_logical_bytes_removed':cache['total_bytes']+cold['bytes'],'tracked_legacy_files_hash_verified':len(tracked),'r0_source_metrics_hash_verified':len(anchors),'overleaf_clean':True,'backup':cold['backup'],'backup_sha256_verified_before_prune':cold['backup_sha256'],'selective_restore_test_passed':True,'preserved_linked_archive':'legacy/20260918/archive/manuscript_workspace','note':'Logical file sizes, not a measurement of physical disk blocks or OneDrive cloud sync. Original full backup retained.'}
    (OUT/'cleanup_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
