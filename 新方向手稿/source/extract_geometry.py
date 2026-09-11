"""Read existing site geometry for native PowerPoint paths. No simulation or plotting."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import yaml
from shapely.geometry import box
from tools import cross_site_lib as lib
out=[]
for sid in ['site_a_suzhou','site_b_amsterdam','site_c_edmonton']:
    site=ROOT/'sim/sites'/sid
    cfgpath=site/'config'/f'{sid}_config.yaml'
    if not cfgpath.exists(): cfgpath=site/'config/scenario_config.yaml'
    cfg=yaml.safe_load(cfgpath.read_text(encoding='utf-8'))
    net=lib.load_net(site/'sumo/network.net.xml')
    routes=json.loads((site/'routes/primary.json').read_text(encoding='utf-8'))
    waters=lib.water_geometries(json.loads((site/'osm/water_osm.json').read_text(encoding='utf-8')),net)
    w=[]
    for item in waters:
        g=item['geom'].intersection(box(*net.getBoundary()))
        geoms=list(g.geoms) if hasattr(g,'geoms') else [g]
        for part in geoms:
            if part.is_empty:continue
            if part.geom_type=='Polygon':w.append({'closed':True,'points':list(part.exterior.coords)})
            elif part.geom_type=='LineString':w.append({'closed':False,'points':list(part.coords)})
    edgepaths={e.getID():list(e.getShape()) for e in net.getEdges() if e.allows('passenger')}
    auxpath=site/'routes/auxiliary.json'
    aux=json.loads(auxpath.read_text(encoding='utf-8')) if auxpath.exists() else {}
    out.append({'site':sid,'bounds':list(net.getBoundary()),'roads':list(edgepaths.values()),'water':w,
                'auxiliary':[[edgepaths[e] for e in v['edges'] if e in edgepaths] for v in aux.values()],
                'background_air':[v['route'] for v in cfg['air_fleet'].get('background_services',[])],
                'baseline':[edgepaths[e] for e in routes.get('baseline',{}).get('edges',[]) if e in edgepaths],
                'detour':[edgepaths[e] for e in routes.get('detour',{}).get('edges',[]) if e in edgepaths],
                'facilities':cfg['sumo_mapping']})
dest=ROOT/'新方向手稿/.build/geometry.json'
dest.write_text(json.dumps(out),encoding='utf-8')
print([(v['site'],len(v['roads']),len(v['water'])) for v in out])
