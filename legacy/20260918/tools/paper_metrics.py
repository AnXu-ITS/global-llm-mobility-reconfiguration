"""Execution-derived corrections; raw run artifacts are never rewritten."""
import csv,json
from pathlib import Path

TASK_ACTIONS={'DISPATCH','REASSIGN','DIVERT','REROUTE','GROUND_FALLBACK'}

def execution_metrics(rd, original):
    m=dict(original)
    with (Path(rd)/'actions.csv').open(encoding='utf-8',newline='') as f:
        actions=list(csv.DictReader(f))
    issued=sorted((a for a in actions if a['result']=='ISSUED'),key=lambda a:int(a['t']))
    ft=m.get('failure_time'); mid=m.get('critical_mission_id')
    post=[a for a in issued if ft is not None and int(a['t'])>=ft
          and a.get('mission_id')==mid and a['action_type'] in TASK_ACTIONS]
    m['failure_to_replan_latency_s']=(int(post[0]['t'])-ft if post else None)
    m['critical_first_valid_replan_time_s']=int(post[0]['t']) if post else None
    # Recovery is conditional on an actually interrupted critical chain.
    affected=bool(m.get('affected_critical'))
    m['recovery_success']=bool(m.get('recovery_success')) if affected else None
    m['recovered_completed']=bool(m.get('recovered_completed')) if affected else None
    m['recovery_time_s']=m.get('recovery_time_s') if affected else None
    history={}; switches=oscillations=0
    for a in issued:
        if not a.get('mission_id') or a['action_type'] not in TASK_ACTIONS: continue
        sig='GROUND' if a['action_type']=='GROUND_FALLBACK' else 'AIR:'+a['aircraft_id']
        h=history.setdefault(a['mission_id'],[])
        if h and h[-1]!=sig:
            switches+=1
            if sig in h: oscillations+=1
        if not h or h[-1]!=sig: h.append(sig)
    m['decision_switch_count']=switches
    m['decision_oscillation_count']=oscillations
    m['analysis_version']='paper_final_20260910'
    return m
