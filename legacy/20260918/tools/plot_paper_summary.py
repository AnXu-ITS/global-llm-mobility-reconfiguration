"""Standalone scientific figures from the final paper JSON."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/paper_final'
d=json.loads((OUT/'results.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
blue='#166c99';orange='#cd6133'
fig,ax=plt.subplots(1,3,figsize=(12.4,3.9),layout='constrained')
for i,(sub,arms,x,label) in enumerate([
 ('4A',['OBS10','OBS30','OBS60','OBS120','OBS300'],[10,30,60,120,300],'Observation interval (s)'),
 ('4B',['D00','D01','D05','D10','D20','D30','D60'],[0,1,5,10,20,30,60],'Injected execution delay (s)')]):
 y=[d['E4'][sub]['arms'][a]['B4b']['metrics']['critical_mission_completion_time_s']['mean'] for a in arms]
 ax[i].plot(x,y,'o-',color=blue,lw=2,label='B4b')
 ax[i].axhline(180,color=orange,ls='--',lw=1.4,label='Deadline (180 s)')
 ax[i].set(xlabel=label,ylabel='Mission completion time (s)',title=['(a) Observation timing','(b) Execution timing'][i])
 ax[i].legend(frameon=False,fontsize=8)
ax[0].set_xscale('log');ax[0].set_xticks([10,30,60,120,300],labels=['10','30','60','120','300'])
x=[5,10,20,30,50]
y=[d['E4']['4C']['arms'][f'N{n:02d}']['B4b']['llm_reliability']['prompt_tokens_per_logged_call']/1000 for n in x]
ax[2].plot(x,y,'s-',color=blue,lw=2)
ax[2].set(xlabel='Aircraft records in input',ylabel='Prompt tokens / call (thousands)',title='(c) Input burden; 4 core aircraft')
ax[2].text(.04,.94,'0 illegal / absent selections\n100/100 runs on time',transform=ax[2].transAxes,va='top',fontsize=9)
for a in ax:a.grid(axis='y',alpha=.18)
fig.savefig(OUT/'e4_operational_sensitivity.png',dpi=220)
fig.savefig(OUT/'e4_operational_sensitivity.svg')
plt.close(fig)
fig,axs=plt.subplots(1,3,figsize=(11.5,3.6),layout='constrained')
for a,site,title in zip(axs,'ABC',['Site A','Site B','Site C']):
 arr=np.array([[d['E3'][site]['levels'][lvl][m]['system_weighted_loss']['mean'] for m in ['B0','B1','B2','B4b']] for lvl in ['L1','L2','L3','L4']])
 im=a.imshow(arr,cmap='Blues',vmin=0,vmax=400,aspect='auto')
 a.set_xticks(range(4),labels=['B0','B1','B2','B4b']);a.set_yticks(range(4),labels=['L1','L2','L3','L4']);a.set_title(title)
 for row in range(4):
  for col in range(4):a.text(col,row,f'{arr[row,col]:.1f}'.removesuffix('.0'),ha='center',va='center',color='white' if arr[row,col]>230 else '#192f40')
fig.colorbar(im,ax=axs,label='Mean system-weighted loss (lower is better)',shrink=.86)
fig.savefig(OUT/'e3_cross_site_swl.png',dpi=220)
fig.savefig(OUT/'e3_cross_site_swl.svg')
plt.close(fig)
print('Wrote E3 and E4 PNG/SVG figures')
