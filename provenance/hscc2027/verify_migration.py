"""Verify every moved byte and build traceability indexes, without executing experiments."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import csv, hashlib, json, os, re, subprocess, time

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def lp(p): return '\\\\?\\'+str(p.resolve()) if os.name=='nt' else str(p)
def check(row):
    p=ROOT/row['archive_path']
    try:
        st=os.stat(lp(p))
        if st.st_size!=int(row['bytes']): return row['original_path']+': size mismatch'
        with open(lp(p),'rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
        if digest!=row['sha256']: return row['original_path']+': hash mismatch'
    except Exception as e: return row['original_path']+': '+str(e)
    return None
def command(cwd,*args):
    p=subprocess.run(['git','-C',str(cwd),*args],capture_output=True,text=True,encoding='utf-8',errors='replace',env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
    return {'exit_code':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
def write_csv(name,rows,fields):
    with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    with (OUT/'legacy_file_inventory.csv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    errors=[]
    with ThreadPoolExecutor(max_workers=12) as pool:
        for i,result in enumerate(pool.map(check,rows,buffersize=48),1):
            if result: errors.append(result)
            if i%25000==0: print(f'Archive SHA-256 verified {i:,}/{len(rows):,}',flush=True)
    manifest=json.loads((OUT/'legacy_freeze_manifest.json').read_text(encoding='utf-8'))
    legacy=ROOT/manifest['archive_root']
    actual=set()
    for folder,dirs,files in os.walk(lp(legacy)):
        for f in files: actual.add((Path(str(Path(folder)/f).removeprefix('\\\\?\\'))).relative_to(legacy).as_posix())
    expected={r['original_path'] for r in rows}
    if actual!=expected: errors.append({'missing':sorted(expected-actual),'extra':sorted(actual-expected)})
    index={r['original_path']:r for r in rows}
    run_dirs={}
    markers={'metrics.json','missions.csv','actions.csv','decisions.jsonl','run_meta.json','events.jsonl'}
    for r in rows:
        path=r['original_path']; parent,_,name=path.rpartition('/')
        if name not in markers or not (path.startswith(('runs/','archive/')) or '/regression/' in path): continue
        run_dirs.setdefault(parent,set()).add(name)
    observed=json.loads((OUT/'observed_run_metrics.json').read_text(encoding='utf-8'))
    inventory=[]
    for parent,markers_found in sorted(run_dirs.items()):
        mp=parent+'/metrics.json'; metric=observed.get(mp,{})
        m=metric.get('metadata',{})
        inventory.append({'run_path_original':parent,'run_path_archive':manifest['archive_root']+'/'+parent,
            'experiment':m.get('experiment',''), 'scenario':m.get('scenario_id',m.get('scenario','')),
            'manager':m.get('manager_id',m.get('manager',parent.split('/')[-1])),
            'seed':m.get('seed',next(iter(re.findall(r'seed[_-]?(\d+)',parent)),'')),
            'metrics_state':'parse_error' if 'parse_error' in metric else ('present' if mp in index else 'missing'),
            'metrics_sha256':index.get(mp,{}).get('sha256',''),
            'layer': 'legacy_revised' if '/revision_v3/' in parent else 'legacy_original',
            'markers_found':';'.join(sorted(markers_found)),
            'logical_matrix_coverage':'not_audited'})
    fields=['run_path_original','run_path_archive','experiment','scenario','manager','seed','metrics_state','metrics_sha256','layer','markers_found','logical_matrix_coverage']
    write_csv('legacy_inventory.csv',inventory,fields)
    corrections=[]
    for seed in range(20240601,20240621):
        old=f'runs/experiment4/primary/4B/D60/E4_ANCHOR/seed{seed}/B0/metrics.json'
        new=f'manuscript/source/revision_v3/regression/D60_F360/seed{seed}/B0/metrics.json'
        corrections.append({'logical_unit':f'E4B/D60/E4_ANCHOR/seed{seed}/B0',
            'original_path':manifest['archive_root']+'/'+old,'revised_path':manifest['archive_root']+'/'+new,
            'original_status':'present' if old in index else 'missing','revised_status':'present' if new in index else 'missing',
            'original_sha256':index.get(old,{}).get('sha256',''),'revised_sha256':index.get(new,{}).get('sha256',''),
            'reason':'Identical pending command retains original due time; replacement observation, not extra sample',
            'executor':'DeduplicatedExperiment4BRunner','analysis_entry':'manuscript/source/revision_v3/finalize_data.py'})
    write_csv('correction_map.csv',corrections,list(corrections[0]))
    report={'checked_files':len(rows),'verified_bytes':sum(int(r['bytes']) for r in rows),'hash_errors':errors,
        'file_set_exact_match':actual==expected,'observed_run_directories':len(inventory),
        'observed_metrics_files':len(observed),'logical_matrix_completeness':'not_audited',
        'missing_metrics_in_observed_run_dirs':sum(x['metrics_state']=='missing' for x in inventory),
        'correction_pairs_present':sum(x['original_status']==x['revised_status']=='present' for x in corrections),
        'legacy_head':command(legacy,'rev-parse','HEAD'),'legacy_status':command(legacy,'status','--porcelain'),
        'overleaf_head':command(ROOT/'manuscript_hscc2027','rev-parse','HEAD'),
        'overleaf_status':command(ROOT/'manuscript_hscc2027','status','--porcelain'),
        'simulation_or_api_runs':0,'deleted_legacy_files':0,'completed':time.time()}
    (OUT/'migration_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    backup=Path(manifest['backup'])
    for name in ['legacy_inventory.csv','correction_map.csv','migration_verification.json']:
        (backup/name).write_bytes((OUT/name).read_bytes())
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    if errors: raise SystemExit(1)

if __name__=='__main__':main()
