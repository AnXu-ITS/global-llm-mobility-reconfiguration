from pathlib import Path
import csv,json,collections
W=Path(__file__).resolve().parents[2];R=W.parent;O=W/'source/revision_v3'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
out={}; ds=[]
for p in (R/'runs/experiment4/primary/4B').glob('*/*/seed*/B*/action_pipeline.jsonl'):
    pending={};n=0
    for line in p.read_text(encoding='utf-8').splitlines():
        r=json.loads(line);a=r['normalized_action'];mid=a.get('mission_id')
        # SUPERSEDED is logged before the replacement DEFERRED; retain its
        # prior signature to test the incoming action for exact identity.
        if r['result']=='DEFERRED':
            if mid in pending and pending[mid][0]==a and r['t']<=pending[mid][1]+int(p.parts[-5][1:]):n+=1
            pending[mid]=(a,r['t'])
        elif r['result'] in ['ISSUED','STALE_REJECTED']:pending.pop(mid,None)
    if n:ds.append({'path':str(p.relative_to(R)),'duplicate_replacements':n})
out['duplicates']=ds
metrics=read(O/'all_metrics.json'); damage={}; common=0
for site in ['A','B','C']:
    rows=metrics['E1_'+site]
    for m in ['B0','B1','B2','B4b']:
        ints=[];late=0;due=0
        for r in rows:
            if r['paper_manager']!=m:continue
            rd=R/r['source_run'];reg=read(rd/'registry_final.json');H=r['duration_s'];mid=r['critical_mission_id']
            events=list(csv.DictReader((rd/'missions.csv').open(encoding='utf-8')))
            duration=0
            for mission in reg['missions']:
                if mission['mission_id']==mid:continue
                hist=[e for e in events if e['mission_id']==mission['mission_id']]
                for i,e in enumerate(hist):
                    end=float(hist[i+1]['t']) if i+1<len(hist) else H
                    if e['status'] in ['INTERRUPTED','NEEDS_REPLAN']:duration+=end-float(e['t'])
                if mission['deadline_s']<=H:
                    due+=1
                    ct=next((float(e['t']) for e in hist if e['status']=='COMPLETED'),None)
                    late+=ct is None or ct>mission['deadline_s']
            ints.append(duration)
        damage[site+'_'+m]={'mean_interrupted_state_seconds':sum(ints)/len(ints),'due_incumbent':due,'late_or_unfinished_due':late}
    for b in [r for r in rows if r['paper_manager']=='B2']:
        paths=[R/r['source_run']/'candidate_info.jsonl' for r in rows if r['seed']==b['seed'] and r['scenario_id']==b['scenario_id'] and r['paper_manager'] in ['B1','B2','B4b']]
        texts=[]
        for p in paths:
            with p.open(encoding='utf-8') as f:texts.append(json.loads(next(f)))
        assert len(texts)==3 and texts[0]==texts[1]==texts[2]
        common+=1
out['common_first_decision_states']=common;out['incumbent']=damage
(O/'details_verified.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'duplicate_runs':len(ds),'duplicates_by_policy':dict(collections.Counter(Path(x['path']).parent.name for x in ds)),'common_states':common,'incumbent':damage},indent=2))
