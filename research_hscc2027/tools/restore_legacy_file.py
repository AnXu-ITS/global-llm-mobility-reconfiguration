"""Restore one old artifact from cold storage to a separate directory; no overwrites."""
from pathlib import Path,PurePosixPath
import argparse,csv,hashlib,json,zipfile
WS=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('relative_path');p.add_argument('--destination',required=True);a=p.parse_args()
    rel=PurePosixPath(a.relative_path.replace('\\','/'))
    if rel.is_absolute() or '..' in rel.parts or ':' in str(rel):p.error('Expected safe relative archive path')
    freeze=json.loads((WS/'provenance/hscc2027/legacy_freeze_manifest.json').read_text(encoding='utf-8'))
    rows=csv.DictReader((WS/'provenance/hscc2027/legacy_file_inventory.csv').open(encoding='utf-8-sig'))
    entry=next((r for r in rows if r['original_path']==str(rel)),None)
    if entry is None:p.error('File is not in frozen inventory')
    with zipfile.ZipFile(Path(freeze['backup'])/'legacy_snapshot.zip') as z:data=z.read(str(rel))
    assert hashlib.sha256(data).hexdigest()==entry['sha256']
    dest=Path(a.destination).resolve();dest.mkdir(parents=True,exist_ok=True);target=(dest/str(rel)).resolve()
    if not target.is_relative_to(dest):p.error('Destination escape')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(data)
    print(target)
if __name__=='__main__':main()
