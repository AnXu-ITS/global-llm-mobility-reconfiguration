"""Record final analysis inputs, source snapshot and local package versions."""
from pathlib import Path
import hashlib,importlib.metadata,json,platform,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/paper_final'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sources={}
for folder in ('tools','orchestrator','managers','safety','failures','state','tests','config','prompts','schemas'):
    for p in (ROOT/folder).glob('*'):
        if p.is_file() and p.suffix in ('.py','.yaml','.txt','.json'):
            rel=p.relative_to(ROOT);sources[str(rel)]=digest(p)
            # Keep credential-bearing connection config in place, hash only.
            if p.name!='phase3_config.yaml':
                q=OUT/'source_snapshot'/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
inputs={}
for exp in ('experiment2','experiment2_cross_site/site_b_amsterdam','experiment2_cross_site/site_c_edmonton'):
    for p in (ROOT/'runs'/exp).glob('*/seed*/B*/actions.csv'):inputs[str(p.relative_to(ROOT))]=digest(p)
for filename in ('actions.csv','manager_outputs.jsonl'):
    for p in (ROOT/'runs/experiment4/primary').glob(f'*/*/*/seed*/B*/{filename}'):inputs[str(p.relative_to(ROOT))]=digest(p)
versions={}
for name in ('numpy','scipy','pandas','PyYAML','matplotlib','eclipse-sumo','bluesky-simulator'):
    try:versions[name]=importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:versions[name]='not found in package metadata'
release={'release':'paper_final_20260910','python':sys.version,'platform':platform.platform(),
         'packages':versions,'sources_sha256':sources,
         'note':'Post-analysis snapshot; historical run-time hashes remain in raw run configs. No claim that this snapshot predates runs.'}
(OUT/'source_and_environment.json').write_text(json.dumps(release,indent=2),encoding='utf-8')
(OUT/'derived_input_sha256.json').write_text(json.dumps(inputs,indent=2),encoding='utf-8')
print(f'Frozen {len(sources)} source/config hashes and {len(inputs)} derived-input hashes')
