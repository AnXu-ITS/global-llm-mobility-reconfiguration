import json
from pathlib import Path

e3_root = Path('runs/experiment3')
import yaml
e3 = yaml.safe_load(open('config/experiment3_matrix.yaml', encoding='utf-8'))['experiment3']
seeds = yaml.safe_load(open('config/experiment3_seeds.yaml', encoding='utf-8'))['primary_seeds']

diff = 0
same = 0
for s in e3['scenarios']:
    sid = s['id']
    for sd in seeds:
        p1 = e3_root / sid / f'seed{sd}' / 'B1' / 'metrics.json'
        p2 = e3_root / sid / f'seed{sd}' / 'B2' / 'metrics.json'
        m1 = json.load(open(p1, encoding='utf-8'))
        m2 = json.load(open(p2, encoding='utf-8'))
        k1 = m1.get('system_weighted_loss')
        k2 = m2.get('system_weighted_loss')
        if k1 != k2:
            diff += 1
            if diff <= 5:
                print(f'{sid}/seed{sd}: B1 SWL={k1} B2 SWL={k2}')
        else:
            same += 1
print(f'B1==B2 SWL: {same} identical, {diff} differ (out of {same+diff})')
