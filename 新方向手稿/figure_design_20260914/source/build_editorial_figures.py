"""Rebuild Figures 2–6 and S3 from the unchanged manuscript source data.

Authoritative outputs: PDF and SVG with editable text; Python is the drawing
backend. Geometry is projected in metres. No simulation, fitting or new tests.
"""
from pathlib import Path
from collections import Counter
import json
import hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from audit_panel_alignment import require_matplotlib_panel_alignment

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'output'
QA = HERE.parent / 'qa'
OUT.mkdir(exist_ok=True, parents=True)
QA.mkdir(exist_ok=True, parents=True)
D = json.loads((HERE / 'figure_data.json').read_text(encoding='utf-8'))
R = D['results']
MAPS = json.loads((HERE / 'site_geometry.json').read_text(encoding='utf-8'))
POL = ['B0', 'B1', 'B2', 'B4b']
SITES = ['A', 'B', 'C']
LEVELS = ['L1', 'L2', 'L3', 'L4']
C = dict(B0='#858B8D', B1='#BA8D58', B2='#658571', B4b='#887299',
         ink='#293038', muted='#657078', ground='#557A9A', air='#BA8D58',
         red='#AD6B6F', grid='#E5E2DC', border='#D0CEC8', header='#F6F4F0',
         road='#C2C8C9', water='#DDE8EB', auxiliary='#96A5AC')
MARK = dict(B0='s', B1='^', B2='o', B4b='D')
plt.rcParams.update({'font.family': 'Times New Roman', 'font.size': 8,
    'axes.labelsize': 8, 'xtick.labelsize': 7, 'ytick.labelsize': 7,
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.spines.left': False, 'axes.spines.bottom': False,
    'axes.linewidth': .55, 'axes.edgecolor': C['border'],
    'text.color': C['ink'], 'axes.labelcolor': C['ink'],
    'xtick.color': C['muted'], 'ytick.color': C['muted'],
    'xtick.major.size': 0, 'ytick.major.size': 0,
    'legend.frameon': False, 'legend.fontsize': 7.5,
    'svg.fonttype': 'none', 'pdf.fonttype': 42, 'ps.fonttype': 42,
    'savefig.dpi': 300, 'axes.unicode_minus': True})
LOSS_CMAP = LinearSegmentedColormap.from_list('muted_loss',
    ['#F7F4ED', '#E7DDCA', '#C4B49C', '#9B8885', '#71637E'])
TRACE = {'source_hashes': {}, 'figures': {}, 'exclusions': []}
for name in ['figure_data.json', 'site_geometry.json', 'figure3_means_intervals.csv',
             'figure4_matched_states.csv', 'figure4_regime_choices.json']:
    TRACE['source_hashes'][name] = hashlib.sha256((HERE/name).read_bytes()).hexdigest()

def mix(color, strength):
    rgb = np.array(to_rgb(color))
    return tuple((1-strength)*np.ones(3) + strength*rgb)

def page(height):
    fig = plt.figure(figsize=(7.083333333333333, height/72), facecolor='white')
    fig._sizept = (510, height)
    return fig

def text(fig, x, y, value, size=8, weight='normal', color=None, ha='left', va='center', **kw):
    w,h=fig._sizept
    return fig.text(x/w,y/h,value,fontsize=size,fontweight=weight,
                    color=color or C['ink'],ha=ha,va=va,**kw)

def rule(fig, x1, y1, x2, y2, color=None, lw=.5):
    w,h=fig._sizept
    fig.add_artist(Line2D([x1/w,x2/w],[y1/h,y2/h],transform=fig.transFigure,
                         color=color or C['border'],lw=lw,zorder=-1))

def rect(fig,x,y,w,h,face='white',edge=None,lw=.45,z=-3):
    fw,fh=fig._sizept
    fig.add_artist(Rectangle((x/fw,y/fh),w/fw,h/fh,transform=fig.transFigure,
        facecolor=face,edgecolor=edge or C['border'],linewidth=lw,zorder=z))

def module(fig,x,y,w,h,letter,title,subtitle=None):
    rect(fig,x,y,w,h)
    hh=39 if subtitle else 25
    rect(fig,x+.3,y+h-hh,w-.6,hh-.3,C['header'],C['header'],0,-2)
    text(fig,x+6,y+h-12,letter,9,'bold')
    text(fig,x+19,y+h-12,title,8.5,'bold')
    if subtitle: text(fig,x+6,y+h-28,subtitle,7.2,color=C['muted'])
    rule(fig,x,y+h-hh,x+w,y+h-hh)

def axis(fig,x,y,w,h,gid):
    fw,fh=fig._sizept
    ax=fig.add_axes([x/fw,y/fh,w/fw,h/fh]); ax.set_gid(gid)
    ax.set_axisbelow(True)
    return ax

def clean(ax, grid=True):
    if grid: ax.grid(axis='y',color=C['grid'],lw=.4)
    ax.tick_params(pad=3)
    ax.axhline(0,color=C['border'],lw=.6,zorder=1)

def policy_legend(fig,y,lines=False,x=.5):
    handles=[Line2D([],[],color=C[p],marker=MARK[p] if lines else 's',
        linestyle=(0,(2.5,1.5)) if lines and p=='B4b' else '-' if lines else '',
        markersize=5.8 if lines and p=='B1' else 4.8 if lines and p=='B2' else 3.4 if lines else 6,
        markerfacecolor='white' if lines and p in ['B1','B2'] else C[p],
        markeredgewidth=.7,linewidth=1.1,label=p) for p in POL]
    fig.legend(handles=handles,loc='center',bbox_to_anchor=(x,y/fig._sizept[1]),
        ncol=4,handlelength=1.8 if lines else .8,columnspacing=2.6,handletextpad=.6)

def save(fig,name,axes,exemptions=()):
    ids=[a.get_gid() for a in axes]
    require_matplotlib_panel_alignment(fig,axes=axes,panel_ids=ids,
        row_groups=[ids],exemptions=exemptions,
        json_out=QA/f'{name}.alignment.json',
        overlay_svg=QA/f'{name}.alignment.svg',strict=True,
        tolerance_pt=1.5,gutter_tolerance_pt=1.5)
    fig.savefig(OUT/f'{name}.pdf',facecolor='white')
    fig.savefig(OUT/f'{name}.svg',facecolor='white')
    fig.savefig(OUT/f'{name}.png',facecolor='white',dpi=300)
    plt.close(fig)

def figure2():
    fig=page(257); axes=[]
    span=max(max(m['bounds'][2]-m['bounds'][0],m['bounds'][3]-m['bounds'][1]) for m in MAPS)
    titles=['Site A: Suzhou','Site B: Amsterdam','Site C: Edmonton']
    subtitles=['Urban (meshed)','River (barrier)','Suburban (sparse)']
    offsets=[{'D1':(-9,5),'H1':(5,-7),'B1':(7,5)},
             {'D1':(-8,8),'H1':(7,-8),'B1':(10,6)},
             {'D1':(-8,7),'H1':(6,-7),'B1':(5,5)}]
    counts=[]
    for j,m in enumerate(MAPS):
        left=5+j*169
        module(fig,left,49,162,202,chr(97+j),titles[j],subtitles[j])
        ax=axis(fig,left+8,74,146,146,chr(97+j));axes.append(ax)
        cx=(m['bounds'][0]+m['bounds'][2])/2;cy=(m['bounds'][1]+m['bounds'][3])/2
        half=span*.52
        ax.set_xlim(cx-half,cx+half);ax.set_ylim(cy-half,cy+half)
        ax.set_aspect('equal');ax.set_axis_off()
        for wa in m['water']:
            pts=np.asarray(wa['points'])
            if wa['closed']:
                ax.add_patch(Polygon(pts,facecolor=C['water'],edgecolor='#CADBE0',lw=.2,zorder=0))
            else: ax.plot(pts[:,0],pts[:,1],color='#CADBE0',lw=.35,zorder=0)
        ax.add_collection(LineCollection(m['roads'],color=C['road'],linewidth=.23,zorder=1))
        for paths in m['auxiliary']:
            ax.add_collection(LineCollection(paths,color=C['auxiliary'],linewidth=.6,zorder=2))
        ax.add_collection(LineCollection(m['baseline'],color=C['ground'],linewidth=1.05,zorder=3))
        ax.add_collection(LineCollection(m['detour'],color=C['ground'],linewidth=.8,
                                        linestyle=(0,(3,2)),zorder=4))
        f=m['facilities']
        def route(a,b,primary=False):
            if a not in f or b not in f:return
            ax.plot([f[a]['x'],f[b]['x']],[f[a]['y'],f[b]['y']],
                color=C['air'] if primary else '#B6A181',lw=.95 if primary else .65,
                ls='-' if primary else (0,(3,3)),zorder=5)
        for a,b in m['background_air']:route(a,b)
        route('V5','V4');route('V1','V2',True)
        for key in ['D1','H1','B1','V3','D2','H2','C2','C3']:
            if key not in f:continue
            x,y=f[key]['x'],f[key]['y'];primary=key in ['D1','H1','B1']
            color=C['red'] if key=='B1' else C['air'] if key=='V3' else C['ink'] if primary else '#8A8178'
            ax.plot(x,y,marker='D' if key=='B1' else 'o' if primary else 's',
                ms=2.7 if primary else 2.4,mfc=color if primary else 'white',mec=color,mew=.55,zorder=7)
            dx,dy=offsets[j].get(key,(5,0))
            label=ax.annotate('Closure' if key=='B1' else key,(x,y),xytext=(dx,dy),
                textcoords='offset points',fontsize=6.8,fontweight='bold' if primary else 'normal',
                color=color,ha='right' if dx<0 else 'left',va='center',zorder=8,
                bbox=dict(facecolor='white',edgecolor='none',alpha=1,pad=1.2))
        # Identical metres-per-point scale across all sites, calibrated to the axes.
        scale_length=146*500/(2*half)
        rule(fig,left+10,63,left+10+scale_length,63,C['ink'],1.0)
        text(fig,left+10+scale_length+5,63,'500 m',7,color=C['muted'])
        counts.append({'site':SITES[j],'roads':len(m['roads']),'water':len(m['water']),
                       'map_span_m':2*half,'scale_bar_m':500})
    handles=[Line2D([],[],color=c,lw=lw,ls=ls,label=label) for label,c,lw,ls in [
        ('Primary ground',C['ground'],1.1,'-'),('Detour',C['ground'],.8,(0,(3,2))),
        ('Primary air',C['air'],1.1,'-'),('Auxiliary ground',C['auxiliary'],.8,'-'),
        ('Other air','#B6A181',.8,(0,(3,3)))]]
    fig.legend(handles=handles,ncol=5,loc='center',bbox_to_anchor=(.5,31/257),
               handlelength=1.8,columnspacing=1.55,handletextpad=.5,fontsize=7)
    text(fig,255,13,'© OpenStreetMap contributors · Full imported networks at a common projected scale',6.8,
         color=C['muted'],ha='center')
    TRACE['figures']['2']=counts;save(fig,'Figure2',axes)

def figure3():
    fig=page(261);axes=[];values=[]
    policy_legend(fig,242)
    configs=[('critical_mission_completion_time_s','Completion time','Time (s)',360,[0,120,240,360],1),
        ('critical_mission_deadline_violation','Missed deadlines','Runs (%)',100,[0,25,50,75,100],100),
        ('existing_missions_damaged_count','Incumbent damage','Damaged services / run',.62,[0,.2,.4,.6],1)]
    for j,(metric,title,unit,ymax,ticks,scale) in enumerate(configs):
        left=5+169*j;module(fig,left,37,162,185,chr(97+j),title)
        ax=axis(fig,left+28,62,127,112,chr(97+j));axes.append(ax)
        text(fig,left+6,184,unit,7.5,color=C['muted'])
        ax.set_ylim(0,ymax);ax.set_xlim(-.6,2.6);ax.set_yticks(ticks)
        if j==2:ax.set_yticklabels(['0','0.2','0.4','0.6'])
        ax.set_xticks(range(3),['A','B','C']);clean(ax)
        ax.set_xlabel('Site',labelpad=4)
        value_labels=[]
        for i,p in enumerate(POL):
            positions=np.arange(3)+(i-1.5)*.19
            stats=[R['E1'][site]['summary'][p][metric] for site in SITES]
            mean=np.array([s['mean']*scale for s in stats])
            lo=np.array([s['ci95'][0]*scale for s in stats]);hi=np.array([s['ci95'][1]*scale for s in stats])
            assert np.all(lo<=mean+1e-10) and np.all(mean<=hi+1e-10)
            ax.bar(positions,mean,width=.17,color=C[p],edgecolor='white',linewidth=.25,zorder=3)
            ax.errorbar(positions,mean,yerr=[mean-lo,hi-mean],fmt='none',
                ecolor=C['ink'],elinewidth=.65,capsize=1.8,capthick=.65,zorder=4)
            if p=='B4b':
                for xx,yy,high in zip(positions,mean,hi):
                    label=f'{yy:.3f}' if j==2 else f'{yy:.2f}'
                    value_labels.append(ax.annotate(label,(xx,high),xytext=(0,5),textcoords='offset points',
                        ha='center',va='bottom',fontsize=6.5,color=C['B4b'],fontweight='bold'))
            for site,s in zip(SITES,stats):values.append(dict(site=site,policy=p,metric=metric,**s))
        # Move labels above the intervals until their rendered glyph boxes clear gridlines.
        for label in value_labels:
            for attempt in range(8):
                fig.canvas.draw();bb=label.get_window_extent(fig.canvas.get_renderer())
                grid_y=[ax.transData.transform((0,t))[1] for t in ticks]
                if not any(bb.y0-1<yy<bb.y1+1 for yy in grid_y):break
                label.xyann=(0,label.xyann[1]+3)
            else:raise RuntimeError('Could not clear bar-value label from grid')
    text(fig,255,21,'Means and 95% seed-block intervals · 240 runs / 20 seed blocks per site and policy',7.2,
         ha='center',color=C['muted'])
    text(fig,255,9,'Bar labels identify B4b; exact summaries remain in Supplementary Table S1.',6.8,
         ha='center',color=C['muted'])
    TRACE['figures']['3']=values;save(fig,'Figure3',axes)

def figure4():
    fig=page(306)
    module(fig,5,38,264,262,'a','Decision space at Site A','First candidate snapshot · 240 matched states')
    module(fig,278,38,227,262,'b','Policy behavior','Air selected when faster air preempts a service')
    ax=axis(fig,40,79,213,156,'a');bx=axis(fig,288,79,207,156,'b')
    bx.set_axis_off();bx.set_xlim(0,207);bx.set_ylim(0,156)
    ax.set_xlim(-100,150);ax.set_ylim(-60,240)
    # y<0: no timely candidate. For x>=0, the ground margin is y-x.
    ax.add_patch(Rectangle((-100,-60),250,60,fc='#F5EAEB',ec='none',zorder=0))
    ax.add_patch(Rectangle((-100,0),100,240,fc='#EDF2F5',ec='none',zorder=0))
    ax.add_patch(Polygon([[0,0],[0,240],[150,240],[150,150]],fc='#F5F0E7',ec='none',zorder=0))
    ax.add_patch(Polygon([[0,0],[150,0],[150,150]],fc='#F9F7F1',ec='none',zorder=0))
    ax.axhline(0,color=C['red'],lw=.7,ls=(0,(3,2)),zorder=2)
    ax.axvline(0,color=C['border'],lw=.6,zorder=2)
    ax.plot([0,150],[0,150],color='#B9AD99',lw=.6,ls=(0,(3,2)),zorder=2)
    ax.set_xticks([-100,-50,0,50,100,150]);ax.set_yticks([-50,0,100,200])
    ax.set_xlabel('Ground ETA − air ETA (s)',labelpad=6)
    text(fig,40,245,'Best remaining deadline margin (s)',7.4,color=C['muted'])
    ax.text(-91,230,'Ground faster',fontsize=7,color=C['ground'],va='top')
    ax.text(62,230,'Faster air;\nground timely',fontsize=7,color='#8B6C45',va='top',linespacing=1.1)
    ax.text(113,25,'Only air\ntimely',fontsize=6.7,color=C['muted'],ha='center')
    ax.text(-91,-39,'No timely\ncandidate',fontsize=7,color=C['red'],linespacing=1.05)
    rows=[v for v in D['regimes'] if v['site']=='A' and v['policy']=='B2']
    assert len(rows)==240 and all(v['air_advantage'] is not None for v in rows)
    groups=Counter((v['air_advantage'],v['best_margin'],v['preemption']) for v in rows)
    for (x,y,preempt),n in groups.items():
        ax.scatter(x,y,s=7+2.1*np.sqrt(n),marker='D' if preempt else 'o',
            c=C['air'] if preempt else C['ground'],edgecolors='white',linewidths=.35,zorder=4)
    ax.annotate('20 service-conflict states',xy=(25,94),xytext=(-82,72),fontsize=6.7,
        color='#8B6C45',arrowprops=dict(arrowstyle='-',lw=.6,color='#A79278'),
        bbox=dict(boxstyle='square,pad=.15',fc='white',ec='none'),zorder=5)
    # Right side: a choice matrix with explicit per-site denominators, then outcomes.
    bx.text(0,154,'Ground also remains timely',fontsize=7.2,color=C['muted'],va='top')
    for i,p in enumerate(POL[1:]):
        bx.text(69+i*53,135,p,ha='center',fontsize=8,fontweight='bold',color=C[p])
    reg='B: speed/service conflict'
    matrix=[]
    for j,site in enumerate(SITES):
        cy=106-j*26
        bx.text(0,cy,f'Site {site}',fontsize=7.8,va='center',fontweight='bold')
        for i,p in enumerate(POL[1:]):
            s=D['regime_summary'][site][p][reg];n=s['n'];v=s['air']
            xx=44+i*53
            bx.add_patch(Rectangle((xx,cy-11),49,22,fc=mix(C['air'],.12+.65*v/n),ec='white',lw=.7))
            bx.text(xx+24.5,cy,f'{v}/{n}',ha='center',va='center',fontsize=8.5,
                fontweight='bold',color=C['ink'])
            matrix.append(dict(site=site,policy=p,n=n,air=v))
    bx.text(207,35,'Air selections / matched states',fontsize=6.8,ha='right',color=C['muted'])
    bx.plot([0,207],[23,23],lw=.5,color=C['border'])
    bx.text(0,11,'c',fontsize=9,fontweight='bold',va='center')
    bx.text(13,11,'No candidate predicted timely',fontsize=8,fontweight='bold',va='center')
    text(fig,292,73,'Observed late / matched states, per policy',6.9,color=C['muted'])
    for x,site,val in [(320,'A','40/40'),(388,'B','No states'),(463,'C','24/27')]:
        text(fig,x,55,f'{site}: {val}',7.6,ha='center',weight='bold' if site!='B' else 'normal')
    handles=[Line2D([],[],marker=m,color=c,linestyle='',ms=4,label=label)
        for m,c,label in [('D',C['air'],'Preemption'),('o',C['ground'],'No preemption')]]
    fig.legend(handles=handles,ncol=2,loc='center',bbox_to_anchor=(.244,48/306),
        fontsize=7,handletextpad=.5,columnspacing=1.6)
    text(fig,255,22,'Decision space → policy choice → observed outcome',8.5,'bold',ha='center')
    text(fig,255,9,'Snapshots match across B1, B2 and B4b in all 720 states; subsequent trajectories may differ.',6.8,
         ha='center',color=C['muted'])
    TRACE['figures']['4']={'scatter_rows':len(rows),'coincident_locations':len(groups),
        'scatter_counts_sum':sum(groups.values()),'choice_matrix':matrix,
        'diagonal':'y = x follows from ground deadline margin = best margin − air ETA advantage for x >= 0'}
    save(fig,'Figure4',[ax,bx])

def figure5():
    fig=page(238);axes=[];values=[]
    for j,site in enumerate(SITES):
        left=5+169*j;module(fig,left,67,162,165,chr(97+j),f'Site {site}')
        ax=axis(fig,left+26,80,128,110,chr(97+j));axes.append(ax)
        data=np.array([[R['E3'][site]['levels'][lev][p]['system_weighted_loss']['mean'] for p in POL] for lev in LEVELS])
        assert np.isfinite(data).all() and data.min()>=0 and data.max()<=400
        ax.set_xlim(-.5,3.5);ax.set_ylim(3.5,-.5)
        for rr in range(4):
            for cc in range(4):
                ax.add_patch(Rectangle((cc-.5,rr-.5),1,1,facecolor=LOSS_CMAP(data[rr,cc]/400),
                                      edgecolor='white',linewidth=1.1))
        ax.set_xticks(range(4),POL);ax.xaxis.tick_top();ax.tick_params(axis='x',pad=5)
        for t,p in zip(ax.get_xticklabels(),POL):t.set_color(C[p]);t.set_fontweight('bold')
        ax.set_yticks(range(4),LEVELS);ax.tick_params(axis='y',pad=4)
        for k in np.arange(.5,3.5):
            ax.axhline(k,color='white',lw=1.1);ax.axvline(k,color='white',lw=1.1)
        for row,lev in enumerate(LEVELS):
            for col,p in enumerate(POL):
                val=data[row,col];label=str(int(val)) if val.is_integer() else f'{val:.1f}'
                ax.text(col,row,label,ha='center',va='center',fontsize=8.1,
                    color='white' if val>=300 else C['ink'])
                values.append(dict(site=site,level=lev,policy=p,value=val))
    cbax=axis(fig,155,44,200,7,'colorbar')
    sm=plt.cm.ScalarMappable(norm=plt.Normalize(0,400),cmap=LOSS_CMAP)
    cb=fig.colorbar(sm,cax=cbax,orientation='horizontal',ticks=[0,120,240,400]);cb.outline.set_visible(False)
    cb.solids.set_rasterized(False)
    cbax.tick_params(pad=3,labelsize=6.8)
    text(fig,149,48,'Lower loss',6.8,ha='right',color=C['muted'])
    text(fig,361,48,'Higher loss',6.8,color=C['muted'])
    text(fig,255,18,'System weighted loss (SWL) · 40 runs in L1/L4; 80 in L2/L3, per policy',7.2,ha='center',color=C['muted'])
    text(fig,255,7,'Paired B4b − B0 differences and 95% intervals: Supplementary Figure S3',6.8,ha='center',color=C['muted'])
    TRACE['figures']['5']=values;save(fig,'Figure5',axes)

def figure_s3():
    fig=page(222);axes=[];vals=[]
    for j,site in enumerate(SITES):
        left=5+169*j;module(fig,left,34,162,182,chr(97+j),f'Site {site}','Paired B4b − B0 difference')
        ax=axis(fig,left+29,61,122,100,chr(97+j));axes.append(ax)
        ax.set_xlim(-400,50);ax.set_ylim(3.5,-.5);ax.set_yticks(range(4),LEVELS)
        ax.set_xticks([-400,-200,0]);ax.axvline(0,color=C['border'],lw=.75,ls=(0,(3,2)))
        ax.grid(axis='x',color=C['grid'],lw=.4)
        for i,lev in enumerate(LEVELS):
            s=next(v for v in R['E3'][site]['vs_b0'] if v['other']=='B4b' and v['level']==lev and v['metric']=='system_weighted_loss')
            mean=s['diff_mean'];lo,hi=s['ci95']
            ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='D',ms=3.8,
                color=C['B4b'],ecolor=C['B4b'],elinewidth=.9,capsize=2,capthick=.8)
            vals.append(dict(site=site,**s))
        ax.set_xlabel('Change in SWL',labelpad=5)
    text(fig,255,21,'Paired means and 95% seed-block intervals · Negative values indicate lower loss under B4b',7.2,
         ha='center',color=C['muted'])
    text(fig,255,8,'40 runs in L1/L4; 80 in L2/L3 per policy · Levels jointly vary disturbance and demand',6.8,ha='center',color=C['muted'])
    TRACE['figures']['S3']=vals;save(fig,'FigureS3',axes)

def figure6():
    fig=page(302);axes=[];vals=[]
    policy_legend(fig,284,True)
    configs=[('4A','Observation interval','Interval (s)',315,600,[0,100,200,300],[0,180,300,450,600]),
        ('4B','Execution wait','Wait (s)',64,400,[0,20,40,60],[0,100,180,300,400]),
        ('4C','Input burden','Aircraft records',53,24,[0,10,20,30,40,50],[0,6,12,18,24])]
    for j,(key,title,xlabel,xmax,ymax,xticks,yticks) in enumerate(configs):
        left=5+169*j;module(fig,left,40,162,223,chr(97+j),title)
        ax=axis(fig,left+28,106,127,115,chr(97+j));axes.append(ax)
        text(fig,left+6,231,'Tokens / call (×10³)' if j==2 else 'Completion duration (s)',7.3,color=C['muted'])
        arms=R['E4'][key]['arms'];names=sorted(arms,key=lambda n:int(''.join(filter(str.isdigit,n))))
        xs=np.array([int(''.join(filter(str.isdigit,n))) for n in names])
        ax.set_xlim(-3 if j==1 else 0,xmax);ax.set_ylim(0,ymax);ax.set_xticks(xticks);ax.set_yticks(yticks)
        ax.set_xlabel(xlabel,labelpad=5);clean(ax)
        if j<2:
            ax.axhspan(0,180,color='#F1F4F0',zorder=0)
            ax.axhline(180,color=C['red'],lw=.75,ls=(0,(3,2)),zorder=2)
            vals_by_policy={p:np.array([arms[n][p]['metrics']['critical_mission_completion_time_s']['mean'] for n in names]) for p in POL}
            assert np.array_equal(vals_by_policy['B2'],vals_by_policy['B4b'])
            for p in POL:
                ys=vals_by_policy[p]
                # Large hollow B2 circles under smaller B4b diamonds disclose overlap.
                ax.plot(xs,ys,color=C[p],lw=1.0 if p!='B2' else 1.6,
                    ls=(0,(2.5,1.5)) if p=='B4b' else '-',marker=MARK[p],
                    ms=6.8 if p=='B1' else 4.8 if p=='B2' else 2.8 if p=='B4b' else 3.8,
                    mfc='white' if p in ['B1','B2'] else C[p],mec=C[p],mew=.8,zorder=3+POL.index(p))
                for n,x,y in zip(names,xs,ys):
                    st=arms[n][p]['metrics']['critical_mission_completion_time_s']
                    # These deterministic panels have zero-width source intervals.
                    assert st['ci95'][0]==st['ci95'][1]==st['mean']
                    vals.append(dict(panel=key,arm=n,policy=p,x=int(x),mean=float(y),ci95=st['ci95']))
        else:
            ys=np.array([arms[n]['B4b']['llm_reliability']['prompt_tokens_per_logged_call']/1000 for n in names])
            ax.plot(xs,ys,color=C['B4b'],lw=1.2,marker='D',ms=3.7,mew=.6,zorder=3)
            for n,x,y in zip(names,xs,ys):vals.append(dict(panel=key,arm=n,policy='B4b',records=int(x),tokens=float(y*1000)))
            ax.annotate('3,982.1',(5,ys[0]),xytext=(7,-7),textcoords='offset points',fontsize=6.8,color=C['B4b'])
            ax.annotate('20,593.5',(50,ys[-1]),xytext=(-1,8),textcoords='offset points',fontsize=6.8,ha='right',color=C['B4b'])
        if j==0:
            ax.annotate('OBS60: 180 s',(60,180),xytext=(140,80),textcoords='data',
                fontsize=6.6,color=C['B2'],arrowprops=dict(arrowstyle='-',lw=.5,color=C['B2']))
            ax.plot(120,240,'o',ms=7.4,mfc='none',mec=C['red'],mew=.85,zorder=9)
            text(fig,left+7,69,'B2 = B4b at every setting',7.2,'bold',C['B4b'])
            text(fig,left+7,54,'OBS120 and OBS300: late',7.1,color=C['muted'])
        elif j==1:
            ax.axvline(60,color='#C7B9AE',lw=.7,ls=(0,(2,2)),zorder=2)
            ax.annotate('D60',(60,341),xytext=(-9,11),textcoords='offset points',
                        ha='right',fontsize=7,color=C['red'])
            text(fig,left+7,69,'0–30 s: B1 = B2 = B4b',7.2,'bold',C['B4b'])
            text(fig,left+7,54,'D60: pending command replaced',7.1,color=C['muted'])
        else:
            text(fig,left+7,69,'Four active aircraft throughout',7.2,'bold',C['B4b'])
            text(fig,left+7,54,'All 100 B4b runs on time',7.1,color=C['muted'])
    h=Line2D([],[],color=C['red'],ls=(0,(3,2)),lw=.75)
    fig.legend(handles=[h],labels=['180 s service window (a,b)'],loc='center',
        bbox_to_anchor=(.26,25/302),fontsize=7.2,handlelength=2.2)
    text(fig,500,25,'Site A · 20 runs per arm and policy',7.2,color=C['muted'],ha='right')
    text(fig,255,10,'Lines connect tested settings; the highlighted settings do not establish a continuous threshold.',6.8,
         ha='center',color=C['muted'])
    TRACE['figures']['6']=vals;save(fig,'Figure6',axes)

if __name__=='__main__':
    for fn in [figure2,figure3,figure4,figure5,figure6,figure_s3]:
        fn();print(fn.__name__,'complete')
    (QA/'source_data_trace.json').write_text(json.dumps(TRACE,indent=2),encoding='utf-8')
