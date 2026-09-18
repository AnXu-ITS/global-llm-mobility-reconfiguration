"""Two physical BlueSky cargos, two actual SUMO vehicles, one shared bay.

Reservation on/off is a development mechanism toggle, not frozen FULL/LST.
The same physical inputs apply to both toggles. No model calls.
"""
from pathlib import Path
from dataclasses import asdict,is_dataclass
import argparse,hashlib,json,math,sys,time,uuid
ROOT=Path(__file__).resolve().parents[1];VENDOR=ROOT/'vendor/legacy_platform';sys.path.insert(0,str(VENDOR));sys.path.insert(0,str(ROOT))
from runtime_v2.stages import StageKernel
from runtime_v2.core import Payload,check_events
def dump(path,value):path.write_text(json.dumps(value,indent=2,default=lambda x:asdict(x) if is_dataclass(x) else str(x)),encoding='utf-8')
def main():
    p=argparse.ArgumentParser();p.add_argument('--reserve',action='store_true');p.add_argument('--interrupt',action='store_true');a=p.parse_args()
    out=ROOT/'runs/development'/('d_admission_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True);print('OUTPUT '+str(out),flush=True)
    from orchestrator.config import load_config
    from orchestrator.sumo_env import setup,binary
    from orchestrator.bluesky_adapter import BlueSkyAdapter
    from orchestrator.geo import haversine,bearing
    setup();import traci;import sumolib.geomhelper as gh
    site=ROOT/'sites/frozen/D';selected=json.loads((site/'site_config.json').read_text(encoding='utf-8'));cfg=load_config();cfg['facilities']=selected['facilities'];cfg['sumo_mapping']=selected['sumo_mapping']
    k=StageKernel(missions=('m1','m2'),resources=('GV-1','GV-2','BAY_V3'))
    k.payloads={f'p{i}':Payload('V2' if i==1 else 'V1','AT_ORIGIN','V2' if i==1 else 'V1') for i in (1,2)}
    traci.start([binary('sumo'),'-c',str(site/'site.sumocfg'),'--step-length','1','--seed','20270901','--no-step-log','true','--no-warnings','true','--time-to-teleport','-1','--log',str(out/'sumo.log')])
    tracks=[];checks={};report=None
    try:
        stations={}
        for name in ('V1','V2','V3'):
            m=cfg['sumo_mapping'][name];edge=m['edge_id'];lane=m.get('lane_id',edge+'_0');pos=max(20,min(float(m.get('lane_pos_m',gh.polygonOffsetWithMinimumDistanceToPoint((m['x'],m['y']),traci.lane.getShape(lane)))),traci.lane.getLength(lane)-20))
            lon,lat=traci.simulation.convert2D(edge,pos,toGeo=True);stations[name]={'edge':edge,'lane':lane,'pos':pos,'lat':lat,'lon':lon};cfg['facilities'][name]={'lat':lat,'lon':lon}
        tasks={}
        for i in (1,2):
            origin='V2' if i==1 else 'V1';dest='V1' if i==1 else 'V2';src=stations['V3'];target=stations[dest];gv=f'GV-{i}';route=list(traci.simulation.findRoute(src['edge'],target['edge']).edges);assert len(route)>1
            pos=src['pos']-8*(i-1);traci.route.add(gv,route);traci.vehicle.add(gv,gv,depart='0',departPos=str(pos-3),departSpeed='0',arrivalPos=str(target['pos']))
            traci.vehicle.setStop(gv,src['edge'],pos=pos,duration=100000,flags=traci.constants.STOP_PARKING)
            tasks[i]={'mission':f'm{i}','payload':f'p{i}','air':f'M-UAV-0{3-i}','gv':gv,'origin':origin,'destination':dest,'park_pos':pos,'route':route,'ready':None,'first_start':None,'starts':[],'interruptions':[],'transfer_end':None,'arrival':None,'delivered':None,'air_distance':0.,'last_air':None,'ground_distance':0.}
        bs=BlueSkyAdapter(cfg);bs.define_landmarks()
        for task in tasks.values():s=stations[task['origin']];bs.create_aircraft(task['air'],'M600',s['lat'],s['lon'],0,0,0)
        for acid in ('L-UAV-01','EVTOL-01'):s=stations['V2'];bs.create_aircraft(acid,'M600',s['lat'],s['lon'],0,0,0)
        fixture={'site':'D','mode':'ADVANCE_RESERVATION_DIAGNOSTIC' if a.reserve else 'NO_RESERVATION_DIAGNOSTIC','interrupt':a.interrupt,'seed':20270901,'release':300,'load_end':315,'failure':360,'fallback_commit':365,'handoff_s':30,'unload_s':15,'bay_capacity':1,'parking_positions':2,'parking_semantics':'two off-road SUMO parking stops within modeled V3 footprint, not two service bays','closure':[440,450] if a.interrupt else None,'stations':stations,'tasks':tasks,'reservation_rule':'at commitment, hold later-stage bay until ceil(current-distance/15 + current-altitude/1 + now + handoff) + epsilon(5)+2','speed_mps':15,'formal_method_comparison':False,'llm_calls':0}
        fixture['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'runtime_v2/stages.py',ROOT/'runtime_v2/core.py',ROOT/'runtime_v2/audit.py']};fixture['site_manifest_sha256']=hashlib.sha256((site/'asset_manifest.json').read_bytes()).hexdigest();dump(out/'fixture.json',fixture)
        active=None;max_active=0;reserved_at=None;reservation_expiry=None
        for t in range(1,901):
            traci.simulationStep();bs.step();k.tick(t);assert abs(traci.simulation.getTime()-t)<1e-6 and abs(bs.get_time()-t)<1e-6
            if a.interrupt and t==440:k.fail_resource('BAY_V3');k.emit('EXTERNAL_BAY_CLOSURE',event_id='D-CLOSURE-440')
            if a.interrupt and t==450:k.restore_resource('BAY_V3','fixed_exogenous_recovery')
            airs=bs.state();vids=set(traci.vehicle.getIDList());arrived=set(traci.simulation.getArrivedIDList());live={}
            if t==360:
                for task in tasks.values():k.invalidate(task['mission']);k.emit('C2_LOST',aircraft=task['air'],contingency='V3')
            for i,task in tasks.items():
                air=airs[task['air']];lat,lon,alt=air['lat'],air['lon'],air['alt_m'];speed=float(bs.bs.traf.tas[bs.aircraft_ids().index(task['air'])]);payload=k.payloads[task['payload']]
                if task['last_air']:task['air_distance']+=haversine(*task['last_air'],lat,lon)
                task['last_air']=(lat,lon)
                if t==300:payload.state='LOADING';k.emit('LOAD_STARTED',payload=task['payload'])
                if t==315:payload.holder=task['air'];payload.state='ON_CARRIER';payload.location=None;k.emit('LOAD_COMPLETE',payload=task['payload'],holder=payload.holder)
                src=stations['V3'];air_ready=t>=360 and haversine(lat,lon,src['lat'],src['lon'])<=20 and alt<=2 and speed<=0.5
                if t>=315 and not air_ready and task['ready'] is None:
                    target=src if t>=360 else stations[task['destination']];distance=haversine(lat,lon,target['lat'],target['lon']);v=min(15.,distance/5.) if distance>=8 else 0
                    bs.command(f'HDG {task["air"]},{bearing(lat,lon,target["lat"],target["lon"])}');bs.command(f'SPD {task["air"]},{v*1.943844492}');bs.command(f'ALT {task["air"]},{0 if distance<30 else 328}')
                if air_ready and payload.state=='ON_CARRIER':payload.state='WAITING_HANDOFF';payload.location='V3';k.emit('AIR_PHYSICALLY_READY',payload=task['payload'],aircraft=task['air'],distance_m=haversine(lat,lon,src['lat'],src['lon']),alt_m=alt,speed_mps=speed)
                ground_ready=False;road=None;pos=None;gs=None
                if task['gv'] in vids:
                    gv=task['gv'];road=traci.vehicle.getRoadID(gv);pos=traci.vehicle.getLanePosition(gv);gs=traci.vehicle.getSpeed(gv);task['ground_distance']=traci.vehicle.getDistance(gv)
                    ground_ready=road==src['edge'] and abs(pos-task['park_pos'])<=2 and gs<0.1 and traci.vehicle.isStopped(gv)
                if air_ready and ground_ready and task['ready'] is None:task['ready']=t;k.emit('BOTH_CARRIERS_READY',mission=task['mission'])
                live[i]=(air_ready,ground_ready)
                if task['gv'] in arrived:assert payload.holder==task['gv'] and task['transfer_end'] is not None;task['arrival']=t;k.emit('GROUND_PHYSICAL_ARRIVAL',mission=task['mission'],carrier=task['gv'],source='SUMO arrived IDs')
                if task['arrival'] is not None and task['delivered'] is None and t>=task['arrival']+15:
                    payload.holder=task['destination'];payload.state='DELIVERED';payload.location=task['destination'];task['delivered']=t;k.complete(task['mission']);k.emit('DELIVERED',payload=task['payload'])
                tracks.append({'t':t,'mission':task['mission'],'air_lat':lat,'air_lon':lon,'air_alt_m':alt,'air_speed_mps':speed,'ground_road':road,'ground_pos_m':pos,'ground_speed_mps':gs,'payload_holder':payload.holder,'payload_state':payload.state})
            if t==365:
                for i,task in tasks.items():op=f'ground-commit-{i}';assert k.admit(k.propose(op,task['mission'],(task['gv'],),t));assert k.apply(op)
                if a.reserve:
                    first=tasks[1];air=airs[first['air']];src=stations['V3'];reservation_expiry=math.ceil(t+haversine(air['lat'],air['lon'],src['lat'],src['lon'])/15+air['alt_m']/1.0+30)+7
                    assert k.hold('m1',('BAY_V3',),reservation_expiry);reserved_at=t;k.emit('DOWNSTREAM_BAY_RESERVED',mission='m1',valid_through=reservation_expiry,estimate_uses_current_state_only=True)
            # Exogenous closure precedes completion; interruption restarts the full process.
            if active is not None:
                task=tasks[active];payload=k.payloads[task['payload']];before=payload.holder;valid=all(live[active]) and k.resources['BAY_V3'].available
                finished=k.finish_transfer(task['payload'],valid)
                if finished:
                    task['transfer_end']=t;assert payload.holder==task['gv'];traci.vehicle.resume(task['gv']);k.release_resources(task['mission'],('BAY_V3',),'handoff_complete');active=None
                elif payload.state=='WAITING_HANDOFF':
                    assert payload.holder==before;task['interruptions'].append(t);k.release_resources(task['mission'],('BAY_V3',),'handoff_interrupted');active=None
            if active is None and t>=365:
                for i,task in tasks.items():
                    payload=k.payloads[task['payload']]
                    if payload.state!='WAITING_HANDOFF' or not all(live[i]) or not k.resources['BAY_V3'].available:continue
                    owner=k.resources['BAY_V3'].owner
                    if owner not in (None,task['mission']):k.emit('BAY_QUEUE_WAIT',mission=task['mission'],owner=owner,reason='advance_reservation');continue
                    op=f'bay-start-{i}-{t}';assert k.admit(k.propose(op,task['mission'],('BAY_V3',),t));assert k.apply(op)
                    assert k.start_transfer(task['payload'],task['gv'],'V3',*live[i],True,30,bay_resource='BAY_V3',mission=task['mission']);active=i;task['starts'].append(t)
                    if task['first_start'] is None:task['first_start']=t
                    break
            if active is not None:
                for i,task in tasks.items():
                    if i!=active and task['ready'] is not None and k.payloads[task['payload']].state=='WAITING_HANDOFF':k.emit('BAY_QUEUE_WAIT',mission=task['mission'],owner=tasks[active]['mission'],reason='physical_service')
            max_active=max(max_active,sum(p.state=='TRANSFERRING' for p in k.payloads.values()));assert max_active<=1
            if all(task['delivered'] is not None for task in tasks.values()):break
        checks={'two_unique_payloads':len(k.payloads)==2,'both_delivered':all(task['delivered'] is not None for task in tasks.values()),'single_bay_exclusion':max_active<=1,'actual_queue':any(e['event']=='BAY_QUEUE_WAIT' for e in k.events),'actual_sumo_arrivals':all(task['arrival'] is not None for task in tasks.values()),'custody_events':not check_events(k.events),'independent_protocol_audit':not any(row['errors'] for row in k.audit_records),'interruption_retains_holder':not a.interrupt or any(task['interruptions'] for task in tasks.values())}
        for task in tasks.values():task['queue_wait_to_first_start']=None if task['first_start'] is None else task['first_start']-task['ready']
        report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,'tasks':tasks,'max_active_transfers':max_active,'reservation_created':reserved_at,'reservation_valid_through':reservation_expiry,'mode':fixture['mode'],'interrupt':a.interrupt,'formal_comparison':False,'llm_calls':0};dump(out/'report.json',report);print(json.dumps(report,indent=2),flush=True)
        if not all(checks.values()):raise AssertionError(checks)
    except Exception as error:dump(out/'failure.json',{'error':str(error)});raise
    finally:
        (out/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in k.events),encoding='utf-8');(out/'trajectory.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in tracks),encoding='utf-8');(out/'protocol_transitions.jsonl').write_text(''.join(json.dumps(row,default=lambda x:asdict(x) if is_dataclass(x) else str(x))+'\n' for row in k.audit_records),encoding='utf-8');traci.close()
if __name__=='__main__':main()
