"""Render reproducible diagnostic map panels, not field-site certification."""
from screen_sites import ROOT,OUT,dump,sumolib
import csv,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
def main():
    fig,axes=plt.subplots(1,3,figsize=(16,5.4),layout='constrained')
    for ax,site in zip(axes,'DEF'):
        d=OUT/'frozen'/site;r=json.loads((d/'site_candidate_report.json').read_text(encoding='utf-8'));net=sumolib.net.readNet(str(d/'network.net.xml'));f=json.loads((d/'facilities.json').read_text(encoding='utf-8'))['facilities']
        ax.add_collection(LineCollection([e.getShape() for e in net.getEdges() if e.allows('passenger')],colors='#d3d8df',linewidths=.45))
        route=r['routes']['D1_H1'];ax.add_collection(LineCollection([net.getEdge(e).getShape() for e in route['primary_edges']],colors='#2861a3',linewidths=1.8))
        if route['alternatives']:ax.add_collection(LineCollection([net.getEdge(e).getShape() for e in route['alternatives'][0]['edges']],colors='#55a17d',linewidths=1,linestyles='dashed'))
        for name,v in f.items():
            color='#c55443' if v['handoff_capacity'] else '#253d55';ax.scatter(v['x'],v['y'],s=45 if v['handoff_capacity'] else 22,c=color,zorder=5)
            ax.annotate(name,(v['x'],v['y']),xytext=(4,5),textcoords='offset points',fontsize=9,weight='bold')
        bbox=r['bbox'];xy0=net.convertLonLat2XY(bbox['west'],bbox['south']);xy1=net.convertLonLat2XY(bbox['east'],bbox['north']);ax.set_xlim(xy0[0],xy1[0]);ax.set_ylim(xy0[1],xy1[1]);ax.set_aspect('equal');ax.set_xticks([]);ax.set_yticks([])
        title={'D':'D  Transfer hub | Leipzig','E':'E  Travel-time variation | Barcelona','F':'F  Shared resources | Berlin'}[site];ax.set_title(title,fontsize=12,pad=12)
        subtitle={'D':'1 modeled handoff bay at V3','E':'Physical road-speed event: 330-450 s','F':'2 modeled hubs; shared medical backup'}[site];ax.set_xlabel(subtitle,fontsize=10)
        with (d/'route_diagnostics.csv').open('w',newline='',encoding='utf-8-sig') as out:
            fields=['od','distance_m','freeflow_eta_s','reasonably_distinct_paths_lower_bound','closure_freeflow_eta_ratio'];w=csv.DictWriter(out,fieldnames=fields);w.writeheader()
            for od,v in r['routes'].items():w.writerow({'od':od,**{k:v[k] for k in fields[1:]}})
        dump(d/'candidate_facilities.geojson',{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':key,'modeled_service_point':True,'handoff_capacity':v['handoff_capacity']},'geometry':{'type':'Point','coordinates':[v['lon'],v['lat']]}} for key,v in f.items()]})
    fig.suptitle('Real OSM roads with modeled service facilities | selected 3.2 km windows',fontsize=14)
    fig.supxlabel('Blue: primary road route   Green dashed: bounded alternate   Red: modeled handoff hub   |   © OpenStreetMap contributors, ODbL',fontsize=9)
    out=OUT/'figures';out.mkdir(exist_ok=True);fig.savefig(out/'sites_D_E_F.png',dpi=180);fig.savefig(out/'sites_D_E_F.svg');plt.close(fig)
    print(out/'sites_D_E_F.png')
if __name__=='__main__':main()
