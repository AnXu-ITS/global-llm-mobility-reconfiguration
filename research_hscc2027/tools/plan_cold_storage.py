"""Verify obsolete bulk datasets against the frozen backup before local pruning."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import csv,hashlib,json,subprocess,time,zipfile
ROOT=Path(__file__).resolve().parents[1];WS=ROOT.parent;LEGACY=WS/'legacy/20260918'
OUT=ROOT/'outputs/bootstrap';CATEGORIES=('runs','outputs','tmp','archive/experiment1_v1','archive/experiment3_v1')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    freeze=json.loads((WS/'provenance/hscc2027/legacy_freeze_manifest.json').read_text(encoding='utf-8'))
    backup=Path(freeze['backup'])/'legacy_snapshot.zip'
    assert sha(backup)==freeze['backup_zip_sha256']
    tracked=subprocess.check_output(['git','-C',str(LEGACY),'ls-files',*CATEGORIES]).decode().strip()
    assert not tracked,'Refuse to prune versioned evidence'
    rows=list(csv.DictReader((WS/'provenance/hscc2027/legacy_file_inventory.csv').open(encoding='utf-8-sig')))
    expected={r['original_path']:r for r in rows if any(r['original_path'].startswith(c+'/') for c in CATEGORIES)}
    prior=json.loads((OUT/'cleanup_plan.json').read_text(encoding='utf-8'))
    removed={x['relative_path'] for x in prior['files']}
    actual={}
    for category in CATEGORIES:
        for p in (LEGACY/category).rglob('*'):
            if p.is_symlink() or p.is_junction():raise RuntimeError('Link in removal tree: '+str(p))
            if p.is_file():actual[p.relative_to(LEGACY).as_posix()]=p
    assert set(actual)==set(expected)-removed,{'unexpected':list(set(actual)-set(expected))[:10],'missing':list(set(expected)-removed-set(actual))[:10]}
    with zipfile.ZipFile(backup) as z:
        for rel in actual:assert z.getinfo(rel).file_size==int(expected[rel]['bytes'])
    def verify(rel):
        r=expected[rel];assert sha(actual[rel])==r['sha256'],rel
        return {'relative_path':rel,'bytes':int(r['bytes']),'sha256':r['sha256']}
    verified=[];names=sorted(actual)
    with ThreadPoolExecutor(12) as pool:
        for i in range(0,len(names),2048):
            verified.extend(pool.map(verify,names[i:i+2048]))
            if i%20480==0:print(f'Verified {len(verified)}/{len(names)}',flush=True)
    manifest=OUT/'cold_storage_files.csv'
    with manifest.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['relative_path','bytes','sha256']);w.writeheader();w.writerows(verified)
    plan={'created_unix':time.time(),'legacy_root':str(LEGACY.resolve()),'backup':str(backup),'backup_sha256':freeze['backup_zip_sha256'],'verified':True,'manifest':str(manifest.resolve()),'files':len(verified),'bytes':sum(r['bytes'] for r in verified),'targets':[str((LEGACY/c).resolve()) for c in CATEGORIES],'reason':'Obsolete bulk results, historical duplicated archives, derived outputs and scratch data. Fully retained in immutable ZIP; new R0 source evidence remains in manuscript/source/revision_v3/regression.'}
    (OUT/'cold_storage_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(plan,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
