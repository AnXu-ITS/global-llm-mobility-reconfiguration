import json
from pathlib import Path

runs = list(Path('runs/experiment3').rglob('B4b/metrics.json'))
print(f'B4b runs: {len(runs)}')
retries = 0
anom = 0
max_lat = 0
for p in runs:
    m = json.load(open(p, encoding='utf-8'))
    r = m.get('llm_retry_total', 0) or 0
    lat = m.get('llm_latency_total_s', 0) or 0
    if r > 0:
        retries += 1
        print(f'  retry>0: {p.parent.name} retry={r}')
    if m.get('system_weighted_loss') is None:
        anom += 1
        print(f'  SWL None: {p}')
    max_lat = max(max_lat, lat)
print(f'retry>0: {retries}/{len(runs)}, SWL None: {anom}, max llm_latency={max_lat:.0f}s')
