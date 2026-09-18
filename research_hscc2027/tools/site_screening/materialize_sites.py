"""Build runnable map packages, explicit modeled resources, and development fixtures."""
from screen_sites import ROOT,OUT,dump,sha
import argparse,json,math,sys,xml.etree.ElementTree as ET
import yaml
def materialize(site):
    d=OUT/'frozen'/site;r=json.loads((d/'site_candidate_report.json').read_text(encoding='utf-8'));f=r['facilities']
    if site!='F':f['V4']['handoff_capacity']=0
    compatibility={
      'M-UAV-1':{'classes':['medical'],'sites':['V1','V2','V3','V4','H1','H2'],'capacity':1},
      'M-UAV-2':{'classes':['medical'],'sites':['V1','V2','V3','H1'],'capacity':1},
      'L-UAV-1':{'classes':['logistics'],'sites':['D1','D2','V2','V3','V4','H1','H2'],'capacity':1},
      'EVTOL-1':{'classes':['passenger','nonmedical_cargo'],'sites':['V1','V2','V3','V4'],'capacity':1},
      'GV-1':{'classes':['medical','logistics'],'sites':['D1','V3','H1'],'capacity':1},
      'GV-2':{'classes':['medical','logistics'],'sites':['D2','V3','V4','H2'],'capacity':1}}
    if site=='F':compatibility['M-UAV-3']={'classes':['medical'],'sites':['V2','V3','V4','H2'],'capacity':1}
    bays={'BAY_V3':{'site':'V3','capacity':1}}
    if site=='F':bays['BAY_V4']={'site':'V4','capacity':1}
    dump(d/'facilities.json',{'site_id':site,'facilities':f,'facility_semantics':'abstract service sites snapped to passenger lanes; not real operating permissions'})
    dump(d/'compatibility.json',{'resources':compatibility,'bays':bays,'default':'deny_unlisted_class_or_site','task_library':[{'id':'medical_h1','class':'medical','destination':'H1','preferred':['M-UAV-1'],'legal_backups':['M-UAV-1','M-UAV-2']},{'id':'medical_h2','class':'medical','destination':'H2','preferred':['M-UAV-1'],'legal_backups':['M-UAV-1']+(['M-UAV-3'] if site=='F' else [])},{'id':'logistics_h2','class':'logistics','destination':'H2','preferred':['L-UAV-1'],'legal_backups':['L-UAV-1']}]})
    routes=ET.Element('routes');ET.SubElement(routes,'vType',id='probe',vClass='passenger',length='5',maxSpeed='13.89',sigma='0')
    for key,row in r['routes'].items():ET.SubElement(routes,'route',id=key,edges=' '.join(row['primary_edges']))
    # No method-specific traffic. Exactly the same static route table serves diagnostics.
    ET.ElementTree(routes).write(d/'routes.rou.xml',encoding='utf-8',xml_declaration=True)
    config=ET.Element('configuration');inp=ET.SubElement(config,'input');ET.SubElement(inp,'net-file',value='network.net.xml');ET.SubElement(inp,'route-files',value='routes.rou.xml')
    tim=ET.SubElement(config,'time');ET.SubElement(tim,'begin',value='0');ET.SubElement(tim,'end',value='900');ET.SubElement(tim,'step-length',value='1')
    ET.ElementTree(config).write(d/'site.sumocfg',encoding='utf-8',xml_declaration=True)
    site_cfg={'site_id':site,'facilities':{key:{'lat':v['lat'],'lon':v['lon']} for key,v in f.items()},'sumo_mapping':{key:{'edge_id':v['edge_id'],'x':v['x'],'y':v['y'],'lane_id':v['lane_id'],'lane_pos_m':v['lane_pos_m']} for key,v in f.items()},'sumo_config':str((d/'site.sumocfg').relative_to(ROOT)),'air_fleet_n':5 if site=='F' else 4,'resource_model':str((d/'compatibility.json').relative_to(ROOT))}
    dump(d/'site_config.json',site_cfg)
    (d/'site_config.yaml').write_text(yaml.safe_dump(site_cfg,allow_unicode=True,sort_keys=False),encoding='utf-8')
    # A development skeleton contains numeric deadlines from declared nominal references.
    # It is never promoted to a formal fixture simply because it has been serialized.
    air_return=math.dist((f['V2']['x'],f['V2']['y']),(f['V3']['x'],f['V3']['y']))/15
    reference={'rule':'parallel carrier readiness then handoff then transport then unloading','air_return_nominal_s':air_return,'ground_ready_nominal_s':0,'handoff_s':30,'ground_V3_H1_freeflow_s':r['routes']['V3_H1']['freeflow_eta_s'],'unload_s':15,'calibrated':False}
    external=[]
    if site=='E':
        corridor=r['routes']['D1_H1']['primary_edges'];affected=corridor[max(1,len(corridor)//4):max(2,len(corridor)//2)]
        external=[{'event_id':'E_CAPACITY_DROP','start_s':330,'end_s':450,'type':'physical_speed_limit','edges':affected,'speed_mps':2.0,'selection':'fixed middle-quarter of reference D1-H1 route; no controller outcomes used'}]
    dump(d/'external_events.json',external)
    for family in ('R6_SINGLE','R6_COMPETING'):
        tasks=[]
        for i in range(1 if family=='R6_SINGLE' else 2):
            release=300 if i==0 else 360;slack=(90 if i==0 else 30) if site=='F' else (60 if site=='E' else 30)
            origin='D1' if i==0 else 'D2';dest='H1' if i==0 else 'H2'
            if site=='E':anchor=release;tau=15+r['routes'][origin+'_'+dest]['freeflow_eta_s']+15
            elif site=='F':anchor=release;tau=15+math.dist((f[origin]['x'],f[origin]['y']),(f['V3']['x'],f['V3']['y']))/15+30+r['routes']['V3_'+dest]['freeflow_eta_s']+15
            else:anchor=360;tau=max(air_return,0)+30+r['routes']['V3_'+dest]['freeflow_eta_s']+15
            if site=='E':stages=[{'id':'load','duration_s':15},{'id':'direct_ground','duration_s':r['routes'][origin+'_'+dest]['freeflow_eta_s']},{'id':'unload','duration_s':15}]
            elif site=='F':stages=[{'id':'load','duration_s':15},{'id':'candidate_air_to_V3','duration_s':math.dist((f[origin]['x'],f[origin]['y']),(f['V3']['x'],f['V3']['y']))/15},{'id':'handoff','duration_s':30},{'id':'ground_from_V3','duration_s':r['routes']['V3_'+dest]['freeflow_eta_s']},{'id':'unload','duration_s':15}]
            else:stages=[{'id':'parallel_ready_max','duration_s':max(air_return,0),'parallel_durations_s':[air_return,0]},{'id':'handoff','duration_s':30},{'id':'ground_from_V3','duration_s':r['routes']['V3_'+dest]['freeflow_eta_s']},{'id':'unload','duration_s':15}]
            assert abs(sum(s['duration_s'] for s in stages)-tau)<1e-8
            tasks.append({'mission_id':f'{site}-T{i+1}','release_s':release,'deadline_s':math.ceil(anchor+tau+slack),'deadline_anchor_s':anchor,'reference_tau_s':tau,'reference_stage_graph':stages,'reference_validation':'candidate_chain_only_best_legal_not_yet_established' if site=='F' else 'nominal_skeleton_physical_initial_state_pending','priority':'HIGH' if i==0 and site=='F' else 'CRITICAL','payload_id':f'{site}-P{i+1}','origin':origin,'destination':dest,'slack_s':slack,'reference_only':True})
        dump(ROOT/'fixtures/development'/site/f'{family}_seed20270901.json',{'site_id':site,'scenario_family':family,'seed':20270901,'status':'development_skeleton_not_execution_frozen','tasks':tasks,'external_events':external,'failure_time_s':360,'network_sha256':sha(d/'network.net.xml'),'facility_layout_sha256':sha(d/'facilities.json'),'compatibility_sha256':sha(d/'compatibility.json'),'missing_for_formal':['physically consistent pre-fault carrier/payload initial states','full background mission realization','supervisor admission gates','all held-out seed realizations','individual best legal reference plan validation'],'native_model_calls':0})
    dump(d/'asset_manifest.json',{'site_id':site,'map_assets_frozen':True,'formal_fixture_frozen':False,'files':{x.name:sha(x) for x in d.iterdir() if x.is_file() and x.name!='asset_manifest.json'},'selection_source':'selection.json'})
    print('MATERIALIZED',site,flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--site',choices=['D','E','F']);a=p.parse_args()
    for site in [a.site] if a.site else ['D','E','F']:materialize(site)
if __name__=='__main__':main()
