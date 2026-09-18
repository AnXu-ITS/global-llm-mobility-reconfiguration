"""Actual SUMO probes on fixed routes; E changes physical road speed, not ETA alone."""
from screen_sites import ROOT,OUT,dump,binary,sha
import argparse,json,statistics,time,uuid
import traci

def probe(site,out,perturbed):
    d=OUT/'frozen'/site;r=json.loads((d/'site_candidate_report.json').read_text(encoding='utf-8'));path=r['routes']['D1_H1']['primary_edges']
    events=json.loads((d/'external_events.json').read_text(encoding='utf-8'));rows=[];arrivals={};departures={};teleports=[]
    traci.start([binary('sumo'),'-c',str(d/'site.sumocfg'),'--seed','20270901','--step-length','1','--no-step-log','true','--no-warnings','true','--time-to-teleport','-1','--log',str(out/('perturbed.log' if perturbed else 'nominal.log'))])
    try:
        schedule={t:f'PROBE-{t}' for t in (270,300,330,360,390,420,450)}
        # Small, deterministic background; screening evidence is not calibrated demand.
        backgrounds=[('D1_H1',t) for t in range(0,600,20)]+[('D2_H2',t) for t in range(5,600,25)]
        for i,(route,depart) in enumerate(backgrounds):traci.vehicle.add(f'BG{i}',route,typeID='probe',depart=str(depart),departSpeed='0')
        for t,vid in schedule.items():traci.vehicle.add(vid,'D1_H1',typeID='probe',depart=str(t),departSpeed='0')
        defaults={edge:traci.lane.getMaxSpeed(edge+'_0') for event in events for edge in event['edges']}
        for t in range(1,1801):
            traci.simulationStep()
            if perturbed:
                for event in events:
                    if t in (event['start_s'],event['end_s']):
                        for edge in event['edges']:traci.edge.setMaxSpeed(edge,event['speed_mps'] if t==event['start_s'] else defaults[edge])
            for vid in traci.simulation.getDepartedIDList():
                if vid.startswith('PROBE'):departures[vid]=t
            for vid in traci.simulation.getArrivedIDList():
                if vid.startswith('PROBE'):arrivals[vid]=t
            teleports.extend(traci.simulation.getStartingTeleportIDList())
            if t%10==0 and 250<=t<=600:
                eta=sum(traci.edge.getTraveltime(e) for e in path)
                rows.append({'t':t,'fixed_route_current_eta_s':eta,'running_vehicles':traci.vehicle.getIDCount()})
            if len(arrivals)==7 and t>=600:break
        traces=[{'vehicle_id':vid,'scheduled_release_s':t,'actual_depart_s':departures.get(vid),'arrival_s':arrivals.get(vid),'travel_time_s':arrivals[vid]-departures[vid] if vid in arrivals and vid in departures else None} for t,vid in schedule.items()]
        vals=[row['fixed_route_current_eta_s'] for row in rows]
        result={'site_id':site,'perturbed':perturbed,'all_7_arrived':len(arrivals)==7,'teleports':teleports,'probes':traces,'eta_samples':rows,'eta_cv':statistics.pstdev(vals)/statistics.mean(vals),'p95_eta_over_median':sorted(vals)[int(.95*(len(vals)-1))]/statistics.median(vals),'network_sha256':sha(d/'network.net.xml'),'horizon_s':1800,'seed':20270901,'controllers_used':[],'eta_source':'sum of current SUMO edge.getTraveltime along the fixed D1-H1 reference route; not oracle optimal routing','note':'Diagnostic horizon extended from1200 to1800 after recording censored trips; formal900 horizon unchanged. Arrival after900 is NOT formal timely service. Nominal deadline calibration still required.'}
        dump(out/('perturbed.json' if perturbed else 'nominal.json'),result);return result
    finally:traci.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--site',choices=['D','E','F'],required=True);a=p.parse_args()
    out=ROOT/'runs/site_diagnostics'/f'{a.site}_{time.strftime("%Y%m%d_%H%M%S")}_{uuid.uuid4().hex[:6]}';out.mkdir(parents=True)
    nominal=probe(a.site,out,False);perturbed=probe(a.site,out,True) if a.site=='E' else None
    report={'site_id':a.site,'nominal_probe_passed':nominal['all_7_arrived'] and not nominal['teleports'],'output':str(out.relative_to(ROOT)),'formal_gate_passed':False,'model_calls':0}
    if perturbed:
        deltas=[b['travel_time_s']-x['travel_time_s'] for x,b in zip(nominal['probes'],perturbed['probes']) if b['travel_time_s'] is not None and x['travel_time_s'] is not None]
        report.update({'perturbed_probe_passed':perturbed['all_7_arrived'] and not perturbed['teleports'],'max_actual_travel_increase_s':max(deltas) if deltas else None,'eta_series_changed':nominal['eta_samples']!=perturbed['eta_samples'],'physical_volatility_observed':bool(deltas and max(deltas)>=10),'paired_travel_time_deltas_s':deltas,'threshold_s':10,'threshold_scope':'engineering development check fixed before probe, not statistical significance or field calibration'})
    dump(out/'report.json',report);dump(OUT/'frozen'/a.site/'traffic_diagnostic_pointer.json',{'report':str((out/'report.json').relative_to(ROOT))})
    print(json.dumps(report,indent=2),flush=True)
    assert report['nominal_probe_passed']
    if perturbed:assert report['perturbed_probe_passed'] and report['physical_volatility_observed']
if __name__=='__main__':main()
