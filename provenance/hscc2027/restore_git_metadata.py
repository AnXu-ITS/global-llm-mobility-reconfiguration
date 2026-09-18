"""Fill missing archived Git files from the verified backup; never overwrite existing bytes."""
from pathlib import Path
import hashlib, json, zipfile

root=Path(__file__).resolve().parents[2]
out=Path(__file__).resolve().parent
manifest=json.loads((out/'legacy_freeze_manifest.json').read_text(encoding='utf-8'))
target=(root/manifest['archive_root']).resolve()
assert target.is_relative_to(root)
restored=[]
with zipfile.ZipFile(Path(manifest['backup'])/'legacy_snapshot.zip') as z:
    for member in z.infolist():
        if not member.filename.startswith('.git/') or member.is_dir(): continue
        destination=(target/member.filename).resolve()
        assert destination.is_relative_to(target/'.git')
        data=z.read(member)
        if destination.exists():
            assert hashlib.sha256(destination.read_bytes()).digest()==hashlib.sha256(data).digest(), member.filename
        else:
            destination.parent.mkdir(parents=True,exist_ok=True)
            with destination.open('xb') as f: f.write(data)
            restored.append(member.filename)
(out/'git_metadata_recovery.json').write_text(json.dumps({'restored_missing_files':restored,'overwritten_files':0,'original_remainder':str(Path(manifest['backup'])/'git_move_remainder'),'reason':'Windows hidden/read-only attributes interrupted initial Move-Item; original remainder retained, missing entries restored from fully verified ZIP'},ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Restored {len(restored)} missing Git files without overwriting existing files.')
