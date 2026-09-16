"""Read saved E3 registries using each run's actual horizon; no simulation calls."""
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import argparse
import csv
import hashlib
import json
import yaml

HERE = Path(__file__).resolve().parent
POLICIES = {'B0', 'B1', 'B2', 'B4b'}
SITES = [
    ('A', 'runs/experiment3', 'experiment3_matrix.yaml'),
    ('B', 'runs/experiment3_cross_site/site_b_amsterdam', 'experiment3_site_b_matrix.yaml'),
    ('C', 'runs/experiment3_cross_site/site_c_edmonton', 'experiment3_site_c_matrix.yaml'),
]

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=HERE)
    args = parser.parse_args()
    root = args.project_root.resolve()
    report = {'method': 'Use metrics.duration_s, checked against run_config.yaml and the site scenario matrix; count mission states with deadline_s <= that horizon.',
              'policies': sorted(POLICIES), 'simulation_reruns': 0, 'sites': {}}
    rows = []
    for site, folder, matrix_name in SITES:
        matrix_path = HERE / 'config' / matrix_name
        scenarios = yaml.safe_load(matrix_path.read_text(encoding='utf-8'))['experiment3']['scenarios']
        scenario_map = {s['id']: s for s in scenarios}
        paths = sorted(p for p in (root / folder).glob('*/seed*/B*/registry_final.json') if p.parent.name in POLICIES)
        assert len(paths) == 960, (site, len(paths))

        def check(path):
            met = read_json(path.parent / 'metrics.json')
            cfg = yaml.safe_load((path.parent / 'run_config.yaml').read_text(encoding='utf-8'))
            scenario = scenario_map[met['scenario_id']]
            horizon = met['duration_s']
            assert horizon == cfg['duration_s'] == scenario['duration_s'], path
            assert met['level'] == cfg['level'] == scenario['level'], path
            states = Counter(m['status'] for m in read_json(path)['missions'] if m['deadline_s'] <= horizon)
            return {'site': site, 'scenario': met['scenario_id'], 'level': met['level'],
                    'seed': met['seed'], 'policy': path.parent.name, 'horizon_s': horizon,
                    'eligible_tasks': sum(states.values()), 'completed': states['COMPLETED'],
                    'overdue_en_route': states['EN_ROUTE'], 'overdue_assigned': states['ASSIGNED'],
                    'states': dict(states), 'run': path.parent.relative_to(root).as_posix(),
                    'registry_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

        with ThreadPoolExecutor(max_workers=8) as pool:
            site_rows = list(pool.map(check, paths))
        rows.extend(site_rows)
        states = Counter()
        for row in site_rows:
            states.update(row['states'])
        report['sites'][site] = {
            'runs': len(site_rows),
            'runs_by_horizon_s': dict(Counter(str(r['horizon_s']) for r in site_rows)),
            'runs_by_level': dict(Counter(r['level'] for r in site_rows)),
            'horizon_s_by_level': {lev: sorted({r['horizon_s'] for r in site_rows if r['level'] == lev}) for lev in ['L1','L2','L3','L4']},
            'deadline_le_horizon_states': dict(states),
            'expired_ongoing': states['EN_ROUTE'] + states['ASSIGNED'],
            'matrix_sha256': hashlib.sha256(matrix_path.read_bytes()).hexdigest(),
            'all_run_configs_match': True,
        }
        assert states == Counter({'COMPLETED': 1440}), (site, states)
    report['total_runs'] = len(rows)
    report['total_eligible_tasks'] = sum(r['eligible_tasks'] for r in rows)
    report['total_expired_ongoing'] = sum(r['overdue_en_route'] + r['overdue_assigned'] for r in rows)
    assert report['total_runs'] == 2880 and report['total_eligible_tasks'] == 4320
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'e3_horizon_audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    columns = [k for k in rows[0] if k != 'states']
    with (args.output_dir / 'e3_horizon_runs.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
