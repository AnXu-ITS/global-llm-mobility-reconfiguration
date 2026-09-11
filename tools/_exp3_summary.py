import json, csv
from pathlib import Path

d = json.load(open('outputs/experiment3/primary_analysis.json', encoding='utf-8'))
print('== deadline violation / recovery / oscillation / damage by level x manager ==')
for c in d['level_manager_cells']:
    viol = c.get('critical_mission_deadline_violation_rate')
    rec = c.get('recovery_success_rate')
    osc = c.get('decision_oscillation_count', {}).get('mean')
    dmg = c.get('existing_missions_damaged_count', {}).get('mean')
    crit = c.get('swl_critical_mean')
    high = c.get('swl_high_mean')
    norm = c.get('swl_normal_mean')
    print(f"{c['level']} {c['manager']}: n={c['n']} SWL={c['system_weighted_loss']['mean']:.0f} "
          f"viol={viol} rec={rec} osc={osc} dmg={dmg} | prio CRIT={crit} HIGH={high} NORM={norm}")

print()
print('== aggregate per manager ==')
for mgr, c in d['aggregate'].items():
    swl = c['system_weighted_loss']['mean']
    viol = c.get('critical_mission_deadline_violation_rate')
    rec = c.get('recovery_success_rate')
    print(f"{mgr}: n={c['n']} SWL={swl:.1f} viol={viol} rec={rec}")

print()
print('== decision behavior (post-failure issued types) ==')
print(json.dumps(d.get('decision_behavior', {}), indent=1))
