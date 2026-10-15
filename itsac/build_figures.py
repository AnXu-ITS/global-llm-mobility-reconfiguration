from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import t
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'itsac/figures';OUT.mkdir(exist_ok=True)
rows=json.loads((ROOT/'manuscript/source/revision_v3/all_metrics.json').read_text())
plt.rcParams.update({'font.family':'Times New Roman','font.size':8,'axes.labelsize':8,'axes.titlesize':8.5,'xtick.labelsize':8,'ytick.labelsize':7,'svg.fonttype':'path','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
colors=['#7D858A','#B48146','#527D67','#826999'];policies=['B0','B1','B2','B4b']
fig,axs=plt.subplots(1,3,figsize=(4.8,2.45));fig.subplots_adjust(left=.08,right=.99,bottom=.27,top=.83,wspace=.52)
fields=['critical_mission_completion_time_s','critical_mission_deadline_violation','existing_missions_damaged_count']
titles=['(a) Completion','(b) Missed deadlines','(c) Incumbent damage'];units=['Time (s)','Runs (%)','Services / run']
records=[]
for ax,field,title,unit in zip(axs,fields,titles,units):
    ax.set_title(title,loc='left',fontweight='bold',pad=18);ax.text(0,1.04,unit,transform=ax.transAxes,fontsize=7)
    for pi,pol in enumerate(policies):
        means=[];errs=[]
        for site in 'ABC':
            r=[r for r in rows['E1_'+site] if r['paper_manager']==pol];assert len(r)==240
            blocks=np.array([np.mean([float(x[field]) for x in r if x['seed']==s]) for s in sorted({x['seed'] for x in r})]);scale=100 if field.endswith('violation') else 1
            mu=blocks.mean()*scale;err=t.ppf(.975,19)*blocks.std(ddof=1)/np.sqrt(20)*scale
            means.append(mu);errs.append(err);records.append({'site':site,'policy':pol,'metric':field,'mean':mu,'ci_low':mu-err,'ci_high':mu+err,'runs':len(r),'seed_blocks':20})
        ax.bar(np.arange(3)+(pi-1.5)*.18,means,.17,label=pol,color=colors[pi],yerr=errs,error_kw={'elinewidth':.55,'capsize':1.3,'capthick':.55},edgecolor='white',linewidth=.25)
    ax.set_xticks(range(3),['A','B','C']);ax.set_xlabel('Site',labelpad=2);ax.spines['left'].set_color('#9aa1a7');ax.spines['bottom'].set_color('#9aa1a7');ax.tick_params(length=2,color='#9aa1a7');ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
axs[0].set_ylim(0,380);axs[0].set_yticks([0,120,240,360]);axs[1].set_ylim(0,104);axs[1].set_yticks([0,25,50,75,100]);axs[2].set_ylim(0,.62);axs[2].set_yticks([0,.2,.4,.6])
fig.legend(*axs[0].get_legend_handles_labels(),loc='lower center',ncol=4,frameon=False,bbox_to_anchor=(.5,.005),handlelength=.9,columnspacing=1.4)
for ext in ['svg','pdf','png']:fig.savefig(OUT/('e1_results.'+ext),dpi=1000 if ext=='png' else 300)
plt.close(fig);(OUT/'e1_results_data.json').write_text(json.dumps(records,indent=2))

fig,ax=plt.subplots(figsize=(4.8,1.65));ax.set_xlim(0,12);ax.set_ylim(0,4);ax.axis('off');fig.subplots_adjust(0,0,1,1)
boxes=[(.1,2.0,2.7,1.5,'Observe services','Road ETA, aircraft,\nmissions and faults'),(3.15,2.0,2.7,1.5,'Compare candidates','Feasibility, time,\nincumbent interruption'),(6.2,2.0,2.55,1.5,'Select intervention','B0 / B1 / B2 / B4b'),(9.1,2.0,2.8,1.5,'Check and execute','Current constraints,\npending command')]
for x,y,ww,hh,title,desc in boxes:
    ax.add_patch(FancyBboxPatch((x,y),ww,hh,boxstyle='round,pad=0.02,rounding_size=.08',facecolor='#F5F7F8',edgecolor='#566A76',linewidth=.7));ax.text(x+ww/2,y+hh-.38,title,ha='center',va='center',fontsize=8,fontweight='bold');ax.text(x+ww/2,y+.52,desc,ha='center',va='center',fontsize=7.5,linespacing=1.35)
for x1,x2 in [(2.82,3.12),(5.87,6.17),(8.77,9.07)]:ax.annotate('',(x2,2.75),(x1,2.75),arrowprops={'arrowstyle':'->','linewidth':.8,'color':'#566A76'})
ax.plot([10.5,10.5,1.45,1.45],[2,1.25,1.25,1.8],color='#566A76',lw=.8);ax.annotate('',(1.45,2),(1.45,1.7),arrowprops={'arrowstyle':'->','linewidth':.8,'color':'#566A76'})
ax.text(6,.67,'Transport evolves with independent local contingencies',ha='center',fontsize=8);ax.text(6,.21,'Observe completion, missed deadlines and incumbent service',ha='center',fontsize=7.5,color='#4F5A62')
for ext in ['svg','pdf','png']:fig.savefig(OUT/('manager.'+ext),dpi=1000 if ext=='png' else 300)
plt.close(fig)
print('Built two vector figures from archived evidence and service model.')
