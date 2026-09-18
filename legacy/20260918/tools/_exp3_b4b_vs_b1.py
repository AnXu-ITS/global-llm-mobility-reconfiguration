import json
from pathlib import Path

e3_root = Path('runs/experiment3')
b4b_runs = list(e3_root.rglob('B4b/metrics.json'))
print(f'B4b runs: {len(b4b_runs)}')
mismatch = 0
checked = 0
for p in sorted(b4b_runs):
    rel = p.relative_to(e3_root)
    parts = rel.parts  # scenario/seedXXXX/B4b/metrics.json
    sid = parts[0]
    seed = parts[1]
    b1 = e3_root / sid / seed / 'B1' / 'metrics.json'
    if not b1.exists():
        continue
    m4 = json.load(open(p, encoding='utf-8'))
    m1 = json.load(open(b1, encoding='utf-8'))
    checked += 1
    if m4.get('system_weighted_loss') != m1.get('system_weighted_loss'):
        mismatch += 1
        print(f'  MISMATCH {sid}/{seed}: B4b SWL={m4.get("system_weighted_loss")} B1 SWL={m1.get("system_weighted_loss")}')
    elif m4.get('recovery_mode') != m1.get('recovery_mode'):
        mismatch += 1
        print(f'  MODE MISMATCH {sid}/{seed}: B4b={m4.get("recovery_mode")} B1={m1.get("recovery_mode")}')
print(f'checked {checked} B4b vs B1 runs, {mismatch} mismatch')
