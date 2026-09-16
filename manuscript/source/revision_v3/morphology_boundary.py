from pathlib import Path
import json,sys,yaml
from shapely.geometry import LineString,Polygon,Point
W=Path(__file__).resolve().parents[2];R=W.parent
sys.path.insert(0,str(R))
from tools.cross_site_lib import load_net,build_junction_graph
out={}
for site,cfg,netpath in [('A','scenario_config.yaml','sim/sumo/network.net.xml'),('B','site_b_amsterdam_config.yaml','sim/sites/site_b_amsterdam/sumo/network.net.xml'),('C','site_c_edmonton_config.yaml','sim/sites/site_c_edmonton/sumo/network.net.xml')]:
    c=yaml.safe_load((R/'config'/cfg).read_text(encoding='utf-8'));net=load_net(R/netpath);g,pos,edges=build_junction_graph(net)
    box=c['bbox'];poly=Polygon([net.convertLonLat2XY(lon,lat) for lon,lat in [(box['west'],box['south']),(box['east'],box['south']),(box['east'],box['north']),(box['west'],box['north'])]])
    area=poly.area/1e6
    # Apportion SUMO edge length by clipped geometry fraction; directional
    # carriageways remain separate, internal intersection edges excluded.
    length=0.;outside=0
    for e in edges.values():
        shape=LineString(e['shape']); frac=shape.intersection(poly).length/shape.length if shape.length else 0
        length+=e['length_m']*frac
        outside+=frac<.999999
    inside=[v for v in g if poly.covers(Point(pos[v]))]
    intersections=sum(g.degree(v)>=3 for v in inside)
    out[site]={'polygon_area_km2':area,'clipped_directional_km':length/1000,'clipped_density':length/1000/area,'intersections':intersections,'intersection_density':intersections/area,'nodes_inside':len(inside),'edges_partly_outside':outside,'total_length_km':sum(e['length_m'] for e in edges.values())/1000}
(W/'source/revision_v3/morphology_boundary.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
