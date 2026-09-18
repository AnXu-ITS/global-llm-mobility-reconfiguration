"""Prepare immutable legacy reuse and a hash-verified, conservative cleanup plan."""
from pathlib import Path
import csv, hashlib, json, shutil, subprocess, zipfile

ROOT=Path(__file__).resolve().parents[1]; WS=ROOT.parent
LEGACY=WS/'legacy/20260918'; OUT=ROOT/'outputs/bootstrap'
OUT.mkdir(parents=True,exist_ok=True)
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    manifest=json.loads((WS/'provenance/hscc2027/legacy_freeze_manifest.json').read_text(encoding='utf-8'))
    backup=Path(manifest['backup'])/'legacy_snapshot.zip'
    assert sha(backup)==manifest['backup_zip_sha256'],'Backup no longer matches freeze'
    tracked=set(subprocess.check_output(['git','-C',str(LEGACY),'ls-files','-z']).decode().split('\0'))
    inventory=list(csv.DictReader((WS/'provenance/hscc2027/legacy_file_inventory.csv').open(encoding='utf-8-sig')))
    cleanup=[]
    with zipfile.ZipFile(backup) as z:
        for row in inventory:
            rel=row['original_path']; p=Path(rel); parts=p.parts
            if '.git' in parts or rel in tracked or rel.startswith(('runs/','outputs/','tmp/','manuscript/source/revision_v3/regression/')): continue
            if any(part in ('overleaf_remote','overleaf_recovery') for part in parts): continue
            reason=None
            if '__pycache__' in parts or p.suffix.lower() in ('.pyc','.pyo'): reason='python_bytecode'
            elif p.suffix.lower() in ('.aux','.toc','.out','.fls','.fdb_latexmk') or p.name.endswith('.synctex.gz'): reason='latex_build_cache'
            elif any(part in ('qa','reference_qa','final_qa','rendered','rendered2') for part in parts) and p.suffix.lower() in ('.png','.jpg','.jpeg'):
                reason='regenerable_visual_qa_raster'
            if not reason: continue
            current=(LEGACY/p).resolve(); assert current.is_relative_to(LEGACY.resolve())
            if not current.exists(): continue
            assert sha(current)==row['sha256'],rel
            assert hashlib.sha256(z.read(rel)).hexdigest()==row['sha256'],rel
            cleanup.append({'path':str(current),'relative_path':rel,'sha256':row['sha256'],'bytes':int(row['bytes']),'reason':reason})
    (OUT/'cleanup_plan.json').write_text(json.dumps({'backup':str(backup),'backup_verified':True,'files':cleanup,'total_bytes':sum(x['bytes'] for x in cleanup)},ensure_ascii=False,indent=2),encoding='utf-8')
    vendor=ROOT/'vendor/legacy_platform'; vendor.mkdir(parents=True,exist_ok=False)
    copied=[]
    for folder in ['orchestrator','managers','failures','safety','schemas','state','config','prompts','tools','sim']:
        for src in (LEGACY/folder).rglob('*'):
            if not src.is_file() or '__pycache__' in src.parts: continue
            rel=src.relative_to(LEGACY)
            if src.suffix in ('.pyc','.pyo'):continue
            dest=vendor/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
            copied.append({'source':str(rel),'sha256':sha(src)})
    for name in ['queue_fix.py']:
        src=LEGACY/'manuscript/source/revision_v3'/name; shutil.copy2(src,vendor/name)
        copied.append({'source':str(src.relative_to(LEGACY)),'sha256':sha(src)})
    (vendor/'PROVENANCE.json').write_text(json.dumps({'legacy_commit':manifest['head'],'copied_files':copied,'note':'Reusable source/data copy; legacy outputs and action caches excluded'},indent=2),encoding='utf-8')
    print(json.dumps({'cleanup_candidates':len(cleanup),'cleanup_bytes':sum(x['bytes'] for x in cleanup),'copied_assets':len(copied)},indent=2))
if __name__=='__main__':main()
