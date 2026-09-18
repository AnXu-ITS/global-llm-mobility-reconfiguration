"""Actual SUMO/BlueSky cargo handoff diagnostic; no ETA-based completion.

Two controls differ only in facility availability. This is an engineering
fixture, not a frozen S1/R2 method comparison or an aviation safety model.
"""
from pathlib import Path
import argparse,hashlib,json,math,os,subprocess,sys,time,uuid
ROOT=Path(__file__).resolve().parents[1];VENDOR=ROOT/'vendor/legacy_platform'
sys.dont_write_bytecode=True;sys.path.insert(0,str(VENDOR));sys.path.insert(0,str(ROOT))
from runtime_v2.core import Payload,check_events
from runtime_v2.audit import AuditedKernel as Kernel

def run(out,facility_delay=0,response_delay=120,site=None):
    from orchestrator.config import load_config
    from orchestrator.sumo_env import setup,binary
    from orchestrator.bluesky_adapter import BlueSkyAdapter
    from orchestrator.geo import haversine,bearing
    setup();import traci
    cfg=load_config();sumocfg=VENDOR/'sim/sumo/canonical.sumocfg'
    if site is not None:
        selected=json.loads((ROOT/'sites/frozen'/site/'site_config.json').read_text(encoding='utf-8'))
        cfg['facilities']=selected['facilities'];cfg['sumo_mapping']=selected['sumo_mapping'];sumocfg=ROOT/selected['sumo_config']
    mapping=cfg['sumo_mapping'];k=Kernel(missions=('m1',),resources=('air_primary','ground','bay'))
    k.payloads['cargo']=Payload('V2','AT_ORIGIN','V2')
    traci.start([binary('sumo'),'-c',str(sumocfg),'--step-length','1','--seed','20270901','--no-step-log','true','--no-warnings','true','--time-to-teleport','-1','--log',str(out/'sumo.log')])
    bs=None
    try:
        import sumolib.geomhelper as gh
        positions={};stations={}
        for facility_id in ('V1','V2','V3'):
            edge=str(mapping[facility_id]['edge_id']);lane=edge+'_0';shape=traci.lane.getShape(lane)
            offset=gh.polygonOffsetWithMinimumDistanceToPoint((mapping[facility_id]['x'],mapping[facility_id]['y']),shape)
            pos=max(10,min(float(offset),traci.lane.getLength(lane)-10));positions[facility_id]=pos
            lon,lat=traci.simulation.convert2D(edge,pos,toGeo=True)
            stations[facility_id]={'lat':lat,'lon':lon,'edge':edge,'lane_pos':pos}
            cfg['facilities'][facility_id]['lat']=lat;cfg['facilities'][facility_id]['lon']=lon
        src=stations['V3'];dest=stations['V1']
        route=list(traci.simulation.findRoute(src['edge'],dest['edge']).edges)
        if len(route)<2:raise RuntimeError('No usable V3 to V1 ground route')
        traci.route.add('cargo_route',route)
        traci.vehicle.add('GROUND-CARGO','cargo_route',typeID='DEFAULT_VEHTYPE',depart='0',departPos=str(src['lane_pos']-5),departSpeed='0',arrivalPos=str(dest['lane_pos']))
        traci.vehicle.setStop('GROUND-CARGO',src['edge'],pos=src['lane_pos'],duration=100000)
        bs=BlueSkyAdapter(cfg);bs.define_landmarks()
        from bluesky.core.entity import getproxied
        performance_class=type(getproxied(bs.bs.traf.perf))
        performance_model=performance_class.__module__+'.'+performance_class.__name__
        for acid,start_site in [('M-UAV-02','V2'),('M-UAV-01','V1'),('L-UAV-01','V2'),('EVTOL-01','V1')]:
            s=stations[start_site];bs.create_aircraft(acid,'M600',s['lat'],s['lon'],0,0,0)
        fixture={'id':'MINIMAL_AIR_TO_GROUND_V1','seed':20270901,'stations':stations,'route_edges':route,'facility_delay_s':facility_delay,'response_delay_s':response_delay,'load_s':15,'handoff_s':30,'unload_s':15,'air_ready_radius_m':20,'air_ready_alt_m':2,'air_ready_speed_mps':0.5,'bluesky_performance_model':performance_model,'sumo_version':traci.getVersion(),'note':'All four are rotor placeholders; no background service claims. Lane-aligned service points are explicit geometry change from legacy, not hidden cargo relocation. Installed BlueSky falls back to legacy performance; no calibrated UAV or flight-safety claim.'}
        fixture['site_id']=site or 'A';fixture['sumo_config']=str(sumocfg)
        if fixture['site_id']=='F':
            s=stations['V2'];bs.create_aircraft('M-UAV-03','M600',s['lat'],s['lon'],0,0,0)
            fixture['note']+=' F includes a fifth stationary M600 placeholder; compatibility competition is not exercised by this single-cargo probe.'
        fixture['network_sha256']=hashlib.sha256((sumocfg.parent/'network.net.xml').read_bytes()).hexdigest()
        fixture['runtime_sha256']={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT/'runtime_v2/core.py',ROOT/'runtime_v2/audit.py',Path(__file__))}
        (out/'fixture.json').write_text(json.dumps(fixture,indent=2),encoding='utf-8')
        logs=[];air_ready=False;ground_departed=False;arrived_at=None;load_start=None;faulted=False;response=None
        landing_commanded=False;unload_start=None;ground_distance=0.;air_distance=0.;last_air=None;applied=None
        movement_while_pending=0;transfer_start=None;delivered=None;physical_ready_t=None
        for t in range(1,901):
            traci.simulationStep();bs.step();k.tick(t)
            assert abs(traci.simulation.getTime()-t)<1e-6 and abs(bs.get_time()-t)<1e-6
            air=bs.state().get('M-UAV-02')
            if air is None:raise RuntimeError('Primary aircraft absent')
            lat,lon,alt=air['lat'],air['lon'],air['alt_m'];speed=float(bs.bs.traf.tas[bs.aircraft_ids().index('M-UAV-02')])
            if last_air:air_distance+=haversine(last_air[0],last_air[1],lat,lon)
            last_air=(lat,lon)
            if t==300:
                k.payloads['cargo'].state='LOADING';load_start=t;k.emit('LOAD_STARTED',payload='cargo',site='V2')
            if t==315:
                p=k.payloads['cargo'];p.holder='M-UAV-02';p.state='ON_CARRIER';p.location=None
                k.emit('LOAD_COMPLETE',payload='cargo',holder=p.holder)
                k.emit('ISSUED',operation='initial_flight',destination='V1')
            if t==360:
                faulted=True;k.invalidate('m1');k.emit('C2_LOST',aircraft='M-UAV-02',contingency='V3')
                snapshot=k.snapshot();response={'ready':t+response_delay,'snapshot':snapshot,'proposal':k.propose('slow_air_proposal','m1',('air_primary',),t+response_delay)}
                k.emit('PROPOSAL_REQUESTED',request='q1',snapshot_t=t,response_due=t+response_delay)
                k.set_wait('m1',365)
                k.emit('ISSUED',operation='local_return',destination='V3')
            if faulted and applied is None and k.fallback_due('m1'):
                k.admit(k.propose('ground_fallback','m1',('ground','bay'),t));assert k.apply('ground_fallback')
                applied=t;k.emit('GROUND_SERVICE_COMMITTED',operation='ground_fallback')
            if response and t==response['ready']:
                assert not k.admit(response['proposal']),'Late proposal must not replace committed fallback'
                k.emit('LATE_RESPONSE_DISCARDED',request='q1',observed_version=response['proposal'].mission_version,current_version=k.versions['m1'])
            if response and t>360 and t<response['ready'] and speed>0.1:movement_while_pending+=1
            if t>=315 and not air_ready:
                target=stations['V3' if faulted else 'V1'];distance=haversine(lat,lon,target['lat'],target['lon'])
                commanded_speed=min(15.,distance/5.)
                if distance<8:commanded_speed=0
                bs.command(f'HDG M-UAV-02,{bearing(lat,lon,target["lat"],target["lon"])}')
                bs.command(f'SPD M-UAV-02,{commanded_speed*1.943844492}')
                bs.command(f'ALT M-UAV-02,{0 if distance<30 else 328}')
                if faulted and distance<=20 and alt<=2 and speed<=0.5:
                    air_ready=True;p=k.payloads['cargo'];p.location='V3';p.state='WAITING_HANDOFF'
                    k.emit('AIR_PHYSICALLY_READY',aircraft='M-UAV-02',distance_m=distance,alt_m=alt,speed_mps=speed)
            vids=traci.vehicle.getIDList();ground_ready=False
            if 'GROUND-CARGO' in vids:
                road=traci.vehicle.getRoadID('GROUND-CARGO');pos=traci.vehicle.getLanePosition('GROUND-CARGO')
                gs=traci.vehicle.getSpeed('GROUND-CARGO');ground_distance=traci.vehicle.getDistance('GROUND-CARGO')
                ground_ready=road==src['edge'] and abs(pos-src['lane_pos'])<=2 and gs<0.1 and traci.vehicle.isStopped('GROUND-CARGO')
            else:road=None;pos=None;gs=None
            if air_ready and ground_ready and physical_ready_t is None:
                physical_ready_t=t;k.emit('BOTH_CARRIERS_READY')
            bay_ready=physical_ready_t is not None and t>=physical_ready_t+facility_delay
            live_air_ready=haversine(lat,lon,src['lat'],src['lon'])<=20 and alt<=2 and speed<=0.5
            committed_resources=all(k.resources[r].owner=='m1' and k.resources[r].available for r in ('ground','bay'))
            bay_ready=bay_ready and committed_resources
            p=k.payloads['cargo']
            if applied is not None and p.state=='WAITING_HANDOFF' and k.start_transfer('cargo','GROUND-CARGO','V3',live_air_ready,ground_ready,bay_ready,30,mission='m1'):
                transfer_start=t
            if p.state=='TRANSFERRING' and k.finish_transfer('cargo',live_air_ready and ground_ready and bay_ready):
                traci.vehicle.resume('GROUND-CARGO');ground_departed=True
                k.emit('ISSUED',operation='ground_drive',carrier='GROUND-CARGO')
            if 'GROUND-CARGO' in traci.simulation.getArrivedIDList():
                assert ground_departed and p.holder=='GROUND-CARGO';arrived_at=t;unload_start=t
                k.emit('GROUND_PHYSICAL_ARRIVAL',carrier='GROUND-CARGO',site='V1',source='traci.simulation.getArrivedIDList')
            if unload_start is not None and t>=unload_start+15 and delivered is None:
                p.holder='V1';p.location='V1';p.state='DELIVERED';delivered=t;k.complete('m1')
                k.emit('DELIVERED',payload='cargo',site='V1')
            logs.append({'t':t,'air_lat':lat,'air_lon':lon,'air_alt_m':alt,'air_speed_mps':speed,'ground_road':road,'ground_lane_pos':pos,'ground_speed':gs,'payload_holder':p.holder,'payload_state':p.state})
            if delivered and t>=max(500,response['ready']+1):break
        errors=check_events(k.events)
        if delivered is None:errors.append('not_delivered_within_horizon')
        if not movement_while_pending:errors.append('no_physical_progress_while_pending')
        if delivered is not None:
            assert arrived_at is not None and transfer_start is not None
            assert delivered>=arrived_at+15 and arrived_at>=transfer_start+30
        report={'fixture_id':fixture['id'],'status':'passed' if not errors else 'failed','errors':errors,'delivery_time_s':delivered,'ground_arrival_s':arrived_at,'handoff_start_s':transfer_start,'physical_ready_s':physical_ready_t,'fallback_commit_s':applied,'response_ready_s':response['ready'] if response else None,'air_moving_ticks_while_proposal_pending':movement_while_pending,'air_distance_m':air_distance,'ground_distance_m':ground_distance,'facility_delay_s':facility_delay,'response_delay_s':response_delay,'completion_source':'actual SUMO arrival plus unloading; no ETA timer','scope':'single unique cargo, actual air return and ground continuation; initial engineering diagnostic, not full S1 cohort','llm_calls':0,'independent_audit_transitions':len(k.audit_records),'independent_audit_errors':sum(bool(r['errors']) for r in k.audit_records)}
        (out/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in k.events),encoding='utf-8')
        (out/'trajectory.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in logs),encoding='utf-8')
        (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2),flush=True)
        if errors:raise RuntimeError(errors)
    finally:
        from dataclasses import asdict,is_dataclass
        (out/'protocol_transitions.jsonl').write_text(''.join(json.dumps(r,default=lambda x:asdict(x) if is_dataclass(x) else str(x))+'\n' for r in k.audit_records),encoding='utf-8')
        traci.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--facility-delay',type=int,default=0);p.add_argument('--response-delay',type=int,default=120);p.add_argument('--site',choices=['D','E','F']);a=p.parse_args()
    if a.facility_delay<0 or not 6<=a.response_delay<=539:p.error('facility delay must be nonnegative; late-response diagnostic requires response delay in [6,539]')
    out=ROOT/'runs/development'/('physical_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
    print('OUTPUT '+str(out),flush=True)
    try:run(out,a.facility_delay,a.response_delay,a.site)
    except Exception as e:
        (out/'failure.json').write_text(json.dumps({'error':str(e)},indent=2),encoding='utf-8');raise
if __name__=='__main__':main()
