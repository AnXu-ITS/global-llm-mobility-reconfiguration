"""Create a complete local ZIP backup and SHA-256 inventory; never moves/deletes inputs."""
from pathlib import Path
import csv, hashlib, json, os, subprocess, time, zipfile
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BACKUP = Path.home() / 'research-backups' / 'ground-air-legacy-20260918'
NAMES = ['.git', '.env.example', '.gitignore', 'README.md', 'README.zh-CN.md',
         'requirements.txt', 'archive', 'config', 'docs', 'failures', 'managers',
         'manuscript', 'orchestrator', 'outputs', 'prompts', 'runs', 'safety',
         'schemas', 'sim', 'state', 'tests', 'tmp', 'tools']

def longpath(p):
    return '\\\\?\\' + str(p.resolve()) if os.name == 'nt' else str(p)

def git(*args):
    p = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.decode('utf-8', 'replace'))
    return p.stdout.decode('utf-8', 'replace')

def read_entry(item):
    rel, path = item
    before = os.stat(longpath(path))
    with open(longpath(path), 'rb') as f: data = f.read()
    after = os.stat(longpath(path))
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError('Input changed during snapshot: ' + rel)
    return rel, data, after, hashlib.sha256(data).hexdigest()

def main():
    BACKUP.mkdir(parents=True, exist_ok=False)
    state = {'root_before': str(ROOT), 'archive_root': 'legacy/20260918',
             'backup': str(BACKUP), 'names': NAMES, 'head': git('rev-parse', 'HEAD').strip(),
             'branch': git('branch', '--show-current').strip(),
             'status_before': git('status', '--porcelain'), 'started': time.time()}
    (OUT/'git_status_before.txt').write_text(state['status_before'], encoding='utf-8')
    (OUT/'tracked_files_before.txt').write_text(git('ls-files'), encoding='utf-8')
    for name, args in [('unstaged.patch',['diff','--binary']), ('staged.patch',['diff','--cached','--binary'])]:
        (BACKUP/name).write_text(git(*args), encoding='utf-8')
    subprocess.run(['git','-C',str(ROOT),'bundle','create',str(BACKUP/'legacy.bundle'),'--all'], check=True)
    subprocess.run(['git','-C',str(ROOT),'bundle','verify',str(BACKUP/'legacy.bundle')], check=True)
    entries=[]
    for name in NAMES:
        base=ROOT/name
        if base.is_file(): entries.append((name,base)); continue
        for folder, dirs, files in os.walk(longpath(base)):
            dirs.sort()
            for f in sorted(files):
                p=Path(folder)/f
                ordinary=Path(str(p).removeprefix('\\\\?\\'))
                entries.append((ordinary.relative_to(ROOT).as_posix(), ordinary))
    print(f'Backing up {len(entries):,} files to {BACKUP}', flush=True)
    totals={}; metrics={}; count=0; total=0
    fields=['original_path','archive_path','bytes','mtime_ns','sha256','layer']
    with (OUT/'legacy_file_inventory.csv').open('w',newline='',encoding='utf-8-sig') as inv, \
         zipfile.ZipFile(BACKUP/'legacy_snapshot.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z, \
         ThreadPoolExecutor(max_workers=8) as pool:
        w=csv.DictWriter(inv,fieldnames=fields); w.writeheader()
        for rel,data,st,digest in pool.map(read_entry,entries,buffersize=24):
            info=zipfile.ZipInfo(rel,time.localtime(st.st_mtime)[:6]); info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(st.st_mode & 0xffff)<<16
            z.writestr(info,data,compresslevel=1)
            layer='legacy_revised' if 'revision_v3/' in rel or rel.startswith('manuscript/overleaf/') else 'legacy_original'
            if '__pycache__/' in rel or rel.startswith('tmp/'): layer='legacy_cache_or_scratch'
            w.writerow(dict(zip(fields,[rel,'legacy/20260918/'+rel,len(data),st.st_mtime_ns,digest,layer])))
            top=rel.split('/')[0]; t=totals.setdefault(top,{'files':0,'bytes':0}); t['files']+=1;t['bytes']+=len(data)
            if rel.endswith('/metrics.json') and (rel.startswith('runs/') or rel.startswith('archive/') or '/regression/' in rel):
                try:
                    m=json.loads(data)
                    metrics[rel]={'path':rel,'sha256':digest,'metadata':{k:m[k] for k in ['experiment','scenario','scenario_id','manager','manager_id','seed','arm','status'] if k in m}}
                except Exception as e: metrics[rel]={'path':rel,'sha256':digest,'parse_error':str(e)}
            count+=1; total+=len(data)
            if count%10000==0: print(f'Backup {count:,}/{len(entries):,} files; {total/1024**3:.2f} GiB',flush=True)
    print('Verifying complete ZIP contents against SHA-256 inventory',flush=True)
    with zipfile.ZipFile(BACKUP/'legacy_snapshot.zip') as z, (OUT/'legacy_file_inventory.csv').open(encoding='utf-8-sig',newline='') as f:
        for i,row in enumerate(csv.DictReader(f),1):
            if hashlib.sha256(z.read(row['original_path'])).hexdigest()!=row['sha256']: raise RuntimeError('ZIP mismatch: '+row['original_path'])
            if i%50000==0: print(f'ZIP verified {i:,} files',flush=True)
    (OUT/'observed_run_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    state.update(files=count,bytes=total,totals=totals,backup_full_hash_verification=True,finished=time.time(),observed_metrics_files=len(metrics))
    with open(BACKUP/'legacy_snapshot.zip','rb') as f: state['backup_zip_sha256']=hashlib.file_digest(f,'sha256').hexdigest()
    (OUT/'legacy_freeze_manifest.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    for name in ['legacy_file_inventory.csv','legacy_freeze_manifest.json','observed_run_metrics.json','git_status_before.txt','tracked_files_before.txt']:
        (BACKUP/name).write_bytes((OUT/name).read_bytes())
    print(json.dumps({'backup_verified':True,'files':count,'bytes':total,'backup':str(BACKUP)},ensure_ascii=False),flush=True)

if __name__=='__main__': main()
