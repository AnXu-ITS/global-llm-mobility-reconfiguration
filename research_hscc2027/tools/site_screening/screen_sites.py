"""Controller-free OSM candidate screening. Never runs a compared supervisor.

Five overlapping windows per regional extract are candidate geometries, not
independent cities. Selection uses only declared network/route diagnostics.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,math,shutil,subprocess,sys,time,urllib.request,urllib.parse
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];VENDOR=ROOT/'vendor/legacy_platform'
sys.dont_write_bytecode=True;sys.path.insert(0,str(VENDOR))
from orchestrator.geo import bbox_from_center,haversine
from orchestrator.sumo_env import setup,binary
setup()
import sumolib,networkx as nx

REGIONS={'D':('Leipzig',51.3397,12.3731),'E':('Barcelona',41.3890,2.1600),'F':('Berlin-Prenzlauer-Berg',52.5480,13.4170)}
MIRRORS=['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter','https://overpass.private.coffee/api/interpreter']
OUT=ROOT/'sites';SELECTION_VERSION='structural-screen-v2-actuated-signals'
def dump(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def download(site,region,lat,lon):
    d=OUT/'sources'/site;d.mkdir(parents=True,exist_ok=True);p=d/'area.osm.xml';b=bbox_from_center(lat,lon,5.6,5.6)
    if p.exists():
        meta=json.loads((d/'osm_source.json').read_text(encoding='utf-8'));assert sha(p)==meta['sha256'];return p,meta
    box=','.join(str(b[k]) for k in ('south','west','north','east'))
    q=f'[out:xml][timeout:40];(way["highway"]({box});nwr["amenity"~"hospital|clinic|university"]({box});nwr["landuse"~"industrial|commercial"]({box});node["place"]({box}););(._;>;);out body;'
    (d/'query.overpass').write_text(q,encoding='utf-8');errors=[]
    for endpoint in MIRRORS:
        print('DOWNLOAD',site,endpoint,flush=True)
        try:
            req=urllib.request.Request(endpoint,data=urllib.parse.urlencode({'data':q}).encode(),headers={'User-Agent':'HSCC2027-ground-air-research/0.2','Content-Type':'application/x-www-form-urlencoded'})
            with urllib.request.urlopen(req,timeout=55) as response:raw=response.read()
            xml=ET.fromstring(raw);assert xml.tag=='osm' and xml.find('way') is not None and xml.find('remark') is None
            p.write_bytes(raw)
            meta={'region_label':region,'site_target':site,'bbox':b,'downloaded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'endpoint':endpoint,'query_sha256':hashlib.sha256(q.encode()).hexdigest(),'sha256':sha(p),'bytes':len(raw),'osm_base_timestamp':xml.find('meta').get('osm_base') if xml.find('meta') is not None else None,'attribution':'© OpenStreetMap contributors','license':'ODbL 1.0','license_url':'https://www.openstreetmap.org/copyright','failed_attempts':errors}
            dump(d/'osm_source.json',meta);return p,meta
        except Exception as e:errors.append({'endpoint':endpoint,'error':str(e)});print('DOWNLOAD_FAILED',str(e),flush=True)
    dump(d/'download_failures.json',errors);raise RuntimeError(errors)

def graph(net):
    edges={e.getID():e for e in net.getEdges() if e.allows('passenger')}
    g=nx.DiGraph();g.add_nodes_from(edges)
    for eid,e in edges.items():
        for dest in e.getAllowedOutgoing('passenger'):
            if dest.getID() in edges:g.add_edge(eid,dest.getID(),weight=dest.getLength())
    return g,edges
def path_stats(edges,path):
    return {'distance_m':sum(edges[e].getLength() for e in path),'freeflow_eta_s':sum(edges[e].getLength()/max(.1,edges[e].getSpeed()) for e in path)}
def routes(g,edges,a,b):
    primary=nx.shortest_path(g,a,b,weight='weight');stats=path_stats(edges,primary)
    alternatives=[];seen={tuple(primary)};base_set=set(primary)
    # Deterministic bounded lower bound, not exhaustive k-shortest-path count.
    interior=primary[1:-1];sample=interior[::max(1,len(interior)//8)][:8]
    for blocked in sample:
        view=nx.subgraph_view(g,filter_node=lambda n,blocked=blocked:n!=blocked)
        try:p=nx.shortest_path(view,a,b,weight='weight')
        except (nx.NetworkXNoPath,nx.NodeNotFound):continue
        if tuple(p) in seen:continue
        seen.add(tuple(p));s=path_stats(edges,p)
        overlap=sum(edges[e].getLength() for e in set(p)&base_set)/stats['distance_m']
        if s['distance_m']<=1.25*stats['distance_m'] and overlap<=.8:alternatives.append({'edges':p,**s,'overlap_with_primary':overlap,'blocked_edge':blocked})
    blocked=interior[len(interior)//2] if interior else None;detour=None
    if blocked:
        try:
            p=nx.shortest_path(nx.subgraph_view(g,filter_node=lambda n:n!=blocked),a,b,weight='weight')
            detour=path_stats(edges,p)['freeflow_eta_s']/stats['freeflow_eta_s']
        except nx.NetworkXNoPath:pass
    return {'from_edge':a,'to_edge':b,'primary_edges':primary,**stats,'reasonably_distinct_paths_lower_bound':1+len(alternatives),'alternatives':alternatives,'reference_closure_edge':blocked,'closure_freeflow_eta_ratio':detour}

def facilities(net,g,edges,lat,lon):
    scc=max(nx.strongly_connected_components(g),key=len)
    center=net.convertLonLat2XY(lon,lat)
    targets={'D1':(-850,550),'D2':(-850,-550),'H1':(850,550),'H2':(850,-550),'V1':(650,700),'V2':(-650,700),'V3':(-100,0),'V4':(300,-650)}
    result={};used=set()
    candidates=[edges[e] for e in sorted(scc) if edges[e].getLength()>45]
    for name,(dx,dy) in targets.items():
        target=(center[0]+dx,center[1]+dy)
        scored=[]
        for e in candidates:
            if e.getID() in used:continue
            lane=next((l for l in e.getLanes() if l.allows('passenger')),None)
            if lane is None:continue
            shape=lane.getShape();pos=sumolib.geomhelper.polygonOffsetWithMinimumDistanceToPoint(target,shape)
            pos=max(12,min(pos,lane.getLength()-12));xy=sumolib.geomhelper.positionAtShapeOffset(shape,pos)
            scored.append((math.dist(target,xy),e.getID(),lane.getID(),pos,xy))
        dist,eid,lid,pos,xy=min(scored);used.add(eid);lo,la=net.convertXY2LonLat(*xy)
        result[name]={'lat':la,'lon':lo,'x':xy[0],'y':xy[1],'edge_id':eid,'lane_id':lid,'lane_pos_m':pos,'snap_to_design_target_m':dist,'source':'synthetic_service_point_on_real_OSM_road','parking_capacity':2 if name in ('V3','V4') else 1,'handoff_capacity':1 if name in ('V3','V4') else 0}
    return result,len(scc)/len(edges)

def screen(site,index,lat,lon,osm,source):
    cid=f'{site}_{index:02d}';d=OUT/'candidates'/cid;d.mkdir(parents=True,exist_ok=True)
    b=bbox_from_center(lat,lon,3.2,3.2);netpath=d/'network.net.xml'
    cmd=[binary('netconvert'),'--osm-files',str(osm),'--output-file',str(netpath),'--geometry.remove','--roundabouts.guess','--ramps.guess','--junctions.join','--tls.guess-signals','true','--keep-edges.by-vclass','passenger','--remove-edges.isolated','true','--keep-edges.in-geo-boundary',','.join(str(b[k]) for k in ('west','south','east','north'))]
    cmd+=['--tls.join','--tls.discard-simple','--tls.default-type','actuated']
    cp=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
    (d/'netconvert.log').write_text(cp.stdout+'\n'+cp.stderr,encoding='utf-8');assert cp.returncode==0,cp.stderr[-1000:]
    net=sumolib.net.readNet(str(netpath));g,edges=graph(net);f,scc_share=facilities(net,g,edges,lat,lon)
    pairs=[('D1','H1'),('D2','H2'),('D1','V3'),('D2','V3'),('V3','H1'),('V3','H2'),('D2','V4'),('V4','H2')]
    route_rows={a+'_'+b:routes(g,edges,f[a]['edge_id'],f[b]['edge_id']) for a,b in pairs}
    tls=len(net.getTrafficLights());alts=sum(r['reasonably_distinct_paths_lower_bound']>=2 for r in route_rows.values())
    dg=nx.Graph()
    for e in edges.values():dg.add_edge(e.getFromNode().getID(),e.getToNode().getID())
    m={'edge_count':len(edges),'junction_count':len(dg),'largest_edge_scc_fraction':scc_share,'dead_end_ratio':sum(deg==1 for _,deg in dg.degree())/len(dg),'mean_node_degree':sum(deg for _,deg in dg.degree())/len(dg),'intersection_density_per_km2':sum(deg>=3 for _,deg in dg.degree())/10.24,'traffic_light_systems':tls,'redundant_od_count_of_8':alts,'hub_separation_m':haversine(f['V3']['lat'],f['V3']['lon'],f['V4']['lat'],f['V4']['lon'])}
    acceptable=scc_share>=.65 and alts>=2 and all(100<=r['distance_m']<=6000 for r in route_rows.values()) and (site!='E' or tls>=5) and (site!='F' or m['hub_separation_m']>=500)
    # Predeclared lexicographic priorities; no method performance in this rule.
    score=[int(acceptable),alts,round(scc_share,6),-round(m['dead_end_ratio'],6),-index]
    if site=='E':score=[int(acceptable),tls,alts,round(scc_share,6),-index]
    if site=='F':score=[int(acceptable),alts,round(m['hub_separation_m'],3),round(scc_share,6),-index]
    loc=ET.parse(netpath).getroot().find('location').attrib
    report={'candidate_id':cid,'target_site':site,'center':[lat,lon],'bbox':b,'source':source,'network_sha256':sha(netpath),'conversion_command':cmd,'projection':loc,'metrics':m,'structural_screen_passed':acceptable,'selection_score':score,'selection_version':SELECTION_VERSION,'facilities':f,'routes':route_rows,'limitations':['service facilities are modeled, not verified operating hospitals/vertiports','five overlapping regional windows are not independent cities','redundancy is a bounded lower bound over at most eight reference-edge exclusions','traffic signals and lanes follow recorded SUMO import assumptions','no FULL/LST runs used; physical and protocol gates reported separately']}
    dump(d/'site_candidate_report.json',report)
    dump(d/'boundary.geojson',{'type':'Feature','properties':{'candidate_id':cid},'geometry':{'type':'Polygon','coordinates':[[[b['west'],b['south']],[b['east'],b['south']],[b['east'],b['north']],[b['west'],b['north']],[b['west'],b['south']]]]}})
    print('SCREEN',cid,'PASS',acceptable,'SCORE',score,flush=True);return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--site',choices=list(REGIONS));args=p.parse_args();sites=[args.site] if args.site else list(REGIONS)
    rule={'version':SELECTION_VERSION,'candidate_windows_per_site':5,'window_km':[3.2,3.2],'regional_extract_km':[5.6,5.6],'offsets_km':[[0,0],[.75,0],[-.75,0],[0,.75],[0,-.75]],'minimum_scc_fraction':.65,'minimum_redundant_ods_of_8':2,'route_distance_range_m':[100,6000],'E_min_signal_systems':5,'F_min_hub_separation_m':500,'ranking':'D: pass, redundant ODs, SCC fraction, negative dead ends; E: pass, signal systems, redundant ODs, SCC; F: pass, redundant ODs, hub separation, SCC; lower candidate index breaks ties','selection_uses_controller_performance':False,'import_revision_reason':'Controller-free Barcelona probes exposed excessive delay with legacy static unjoined signals; all15 windows reimported uniformly with SUMO-recommended joined, simplified actuated signals. Previous maps/results retained in archive/import_v1.'}
    rulepath=OUT/'selection_rule.json'
    if rulepath.exists():assert json.loads(rulepath.read_text(encoding='utf-8'))==rule
    else:dump(rulepath,rule)
    for site in sites:
        city,lat,lon=REGIONS[site];osm,source=download(site,city,lat,lon);reports=[]
        for i,(dx,dy) in enumerate(rule['offsets_km']):
            try:reports.append(screen(site,i,lat+dy/111.2,lon+dx/(111.2*math.cos(math.radians(lat))),osm,source))
            except Exception as e:
                dump(OUT/'candidates'/f'{site}_{i:02d}'/'failure.json',{'error':str(e)});print('SCREEN_FAILED',site,i,str(e),flush=True)
        eligible=[r for r in reports if r['structural_screen_passed']]
        assert eligible,f'No structurally eligible {site} candidate'
        winner=max(eligible,key=lambda r:r['selection_score']);dest=OUT/'frozen'/site
        assert not dest.exists(),'Do not overwrite a frozen map; create a new version'
        shutil.copytree(OUT/'candidates'/winner['candidate_id'],dest)
        dump(dest/'selection.json',{'site_id':site,'region':city,'selected_candidate':winner['candidate_id'],'selection_rule_sha256':sha(rulepath),'all_candidates':[{'id':r['candidate_id'],'score':r['selection_score'],'pass':r['structural_screen_passed']} for r in reports],'map_assets_frozen':True,'formal_fixture_frozen':False,'formal_admission':False})
        print('SELECTED',site,winner['candidate_id'],city,flush=True)
if __name__=='__main__':main()
