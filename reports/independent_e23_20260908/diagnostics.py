"""Frozen-log diagnostics; writes only to this independent audit directory."""
from pathlib import Path
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv, json, hashlib
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
rows=list(csv.DictReader((OUT/'run_summary.csv').open(encoding='utf-8-sig')))
manifest={}


def read(p):
    b=p.read_bytes()
    manifest[str(p.relative_to(ROOT)).replace('\\','/')]=hashlib.sha256(b).hexdigest()
    return b.decode('utf-8-sig')


def jl(p):return [json.loads(l) for l in read(p).splitlines() if l.strip()]


def run(row):
    rd=ROOT/row['path'];m=json.loads(read(rd/'metrics.json'))
    pipes=jl(rd/'action_pipeline.jsonl')
    def sig(keep_all=False):
        # Ground executor uses mission + current corridor ETA, and ignores target_site.
        return [(p['t'],a.get('type'),
                 a.get('aircraft_id') if a.get('type') not in ['GROUND_FALLBACK','CANCEL'] else None,
                 a.get('mission_id'),
                 a.get('target_site') if a.get('type') not in ['GROUND_FALLBACK','CANCEL'] else None,
                 a.get('route') if a.get('type') not in ['GROUND_FALLBACK','CANCEL'] else None)
                for p in pipes if p['result']=='ISSUED'
                for a in [p.get('executed_action') or {}]
                if keep_all or a.get('type') in ['DISPATCH','REASSIGN','GROUND_FALLBACK','DIVERT','REROUTE','CANCEL']]
    d=dict(row,signature=sig(),all_action_signature=sig(True))
    if row['mgr']=='B4b':
        decisions=jl(rd/'manager_outputs.jsonl')
        metadata=[x.get('llm_metadata') or {} for x in decisions]
        d.update(llm_status=dict(Counter(x.get('validation_status','NA') for x in metadata)),
            transport_errors=sum(x.get('validation_status')=='LLM_TRANSPORT_ERROR' for x in metadata),
            llm_decisions=len(metadata),llm_retry_count=sum(x.get('retry_count',0) for x in metadata),
            low_latency_transport_errors=sum(x.get('validation_status')=='LLM_TRANSPORT_ERROR' and x.get('latency_s',1)<1 for x in metadata),
            empty_count=sum(x.get('empty_content_count',0) for x in metadata),
            response_ids=[x['response_id'] for x in metadata if x.get('response_id')],
            latency_total=sum(x.get('latency_s',0) for x in metadata))
    if row['experiment']=='3':
        traces=json.loads(read(rd/'failure_traces.json'))
        events=list(csv.DictReader(read(rd/'events.csv').splitlines()))
        for e in events:e['payload']=json.loads(e['payload']);e['t']=int(e['t'])
        missing=[k for k in ['resource_competition_correct','priority_consistency_violations','spare_medical_assets_at_t420'] if k not in m]
        wrong_mode=[];false_attribution=[]
        for tr,cm in zip(traces,m['cascade_recovery']):
            t=tr['failure_time']
            rec=next((e for e in events if e['t']>=t and e['event_id'] in ['MISSION_STARTED','GROUND_FALLBACK_STARTED'] and e['payload'].get('mission')=='M-CRITICAL-001'),None)
            if rec and cm['recovery_mode']!=('AIR' if rec['event_id']=='MISSION_STARTED' else 'GROUND'):
                wrong_mode.append({'event_index':tr['event_index'],'t':t,'first_recovery_t':rec['t'],'first_recovery_event':rec['event_id'],'reported':cm['recovery_mode']})
            affected='M-CRITICAL-001' in tr['affected_resources']['missions']
            if not affected and cm['recovery_success']:false_attribution.append(tr['event_index'])
        d.update(missing_metrics=missing,wrong_recovery_modes=wrong_mode,unaffected_recovery_success_events=false_attribution)
    return d


with ThreadPoolExecutor(max_workers=8) as pool: details=list(pool.map(run,rows))
out={'scope':len(details),'groups':{},'failure_runs':[],'action_differences':[],
     'cascade_examples':[],'missing_metric_counts':{},'e3_a_l2_scenarios':[]}
for exp in ['2','3']:
    for site in ['A','B','C']:
        rr=[r for r in details if r['experiment']==exp and r['site']==site]
        llms=[r for r in rr if r['mgr']=='B4b']
        status=Counter();ids=[]
        for r in llms:status.update(r['llm_status']);ids.extend(r['response_ids'])
        by={(r['sid'],r['seed'],r['mgr']):r for r in rr}
        paired=[(r,by[(r['sid'],r['seed'],'B2')]) for r in llms]
        group=dict(llm_status=dict(status),transport_error_runs=sum(r['transport_errors']>0 for r in llms),
            transport_error_decisions=sum(r['transport_errors'] for r in llms),
            low_latency_transport_errors=sum(r['low_latency_transport_errors'] for r in llms),
            llm_retry_count=sum(r['llm_retry_count'] for r in llms),
            response_id_entries=len(ids),unique_response_ids=len(set(ids)),
            semantic_operation_sequence_equal=sum(a['signature']==b['signature'] for a,b in paired),
            all_issued_action_sequence_equal=sum(a['all_action_signature']==b['all_action_signature'] for a,b in paired),
            primary_completion_different=sum(a['critical_mission_completion_time_s']!=b['critical_mission_completion_time_s'] for a,b in paired),
            primary_not_completed=sum(not r['critical_mission_completion_time_s'] for r in llms),
            recorded_deadline_violation_count=sum(r['critical_mission_deadline_violation']=='True' for r in llms),
            deadline_not_met_including_unfinished=sum(r['critical_mission_deadline_violation']=='True' or not r['critical_mission_completion_time_s'] for r in llms))
        if exp=='3':
            group['wrong_recovery_mode_events']=sum(len(r['wrong_recovery_modes']) for r in rr)
            group['unaffected_recovery_success_events']=sum(len(r['unaffected_recovery_success_events']) for r in rr)
            for r in rr:
                for k in r['missing_metrics']:out['missing_metric_counts'][k]=out['missing_metric_counts'].get(k,0)+1
                if r['wrong_recovery_modes'] and len(out['cascade_examples'])<6:
                    out['cascade_examples'].append({'path':r['path'],'modes':r['wrong_recovery_modes']})
        out['groups'][f'E{exp}{site}']=group
        for r in llms:
            if r['transport_errors']:
                out['failure_runs'].append({k:r[k] for k in ['experiment','site','sid','seed','path','transport_errors','llm_retry_count','critical_mission_completion_time_s','system_weighted_loss']})
        for a,b in paired:
            if exp=='3' and a['signature']!=b['signature']:
                out['action_differences'].append({'site':site,'sid':a['sid'],'seed':a['seed'],'b2_signature':b['signature'],'b4b_signature':a['signature']})

for sid in sorted({r['sid'] for r in details if r['experiment']=='3' and r['site']=='A' and r['level']=='L2'}):
    for manager in ['B0','B2','B4b']:
        rr=[r for r in details if r['experiment']=='3' and r['site']=='A' and r['sid']==sid and r['mgr']==manager]
        vals=[json.loads(read(ROOT/r['path']/'metrics.json')) for r in rr]
        keys=set(k for v in vals for k in v['system_weighted_loss_by_mission'])
        out['e3_a_l2_scenarios'].append(dict(sid=sid,manager=manager,
          by_mission={k:sum(v['system_weighted_loss_by_mission'].get(k,0) for v in vals)/len(vals) for k in sorted(keys)}))
(OUT/'diagnostic_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'diagnostic_sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k in ['groups','missing_metric_counts','e3_a_l2_scenarios']},indent=2),flush=True)
