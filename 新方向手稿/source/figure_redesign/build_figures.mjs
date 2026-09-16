import {execFileSync} from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const O=path.dirname(fileURLToPath(import.meta.url)),W=path.resolve(O,'../..');
const MOD='C:/Users/xuan1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
process.env.RUNTIME_NODE_MODULES=MOD;
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(MOD,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const SK='C:/Users/xuan1/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const PY='C:/Users/xuan1/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(SK,'container_tools/artifact_tool_utils.mjs')));
const D=JSON.parse(await fs.readFile(path.join(O,'figure_data.json'),'utf8')),R=D.results;
const p=Presentation.create({slideSize:{width:1280,height:720}}),P=['B0','B1','B2','B4b'],sites=['A','B','C'];
const C={B0:'#7B858E',B1:'#D78A3A',B2:'#477F60',B4b:'#7954A3',ink:'#20252A',ground:'#2F659D',air:'#D78A3A',red:'#B52935',muted:'#62707A',grid:'#E1E5E8'};
const font='Arial',plots=[],labels=[],values=[];
function sh(s,g,x,y,w,h,fill='none',stroke='none',lw=0,name=''){return s.shapes.add({name,geometry:g,position:{left:x,top:y,width:Math.max(.01,w),height:Math.max(.01,h)},fill,line:{fill:stroke,width:lw}})}
function tx(s,t,x,y,w,h=32,sz=24,bold=false,col=C.ink,align='left') {const a=sh(s,'textbox',x,y,w,h);a.text=t;a.text.style={typeface:font,fontSize:sz,bold,color:col,alignment:align,verticalAlignment:'middle',autoFit:'none',wrap:'none',insets:{left:0,right:0,top:0,bottom:0}};labels.push({slide:p.slides.items.length,text:t,x,y,w,h,sz});return a;}
function ln(s,x1,y1,x2,y2,col=C.ink,lw=1.6,dash=false){const x=Math.min(x1,x2),y=Math.min(y1,y2),w=Math.max(.01,Math.abs(x2-x1)),h=Math.max(.01,Math.abs(y2-y1));return s.shapes.add({geometry:'custom',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:col,width:lw,style:dash?'dashed':'solid'},customPaths:[{width:w,height:h,commands:[{moveTo:{x:x1-x,y:y1-y}},{lineTo:{x:x2-x,y:y2-y}}]}]});}
function mark(s,x,y,m,size=12,fill=null){return sh(s,{B0:'rect',B1:'triangle',B2:'ellipse',B4b:'diamond'}[m]??'ellipse',x-size/2,y-size/2,size,size,fill??C[m],C[m]??C.ink,1.5)}
function slide(num,note){const s=p.slides.add();s.background.fill='#FFFFFF';s.speakerNotes.textFrame.setText(`Figure ${num}. ${note}\nSource data: figure_data.json, current revised experiment results. Native vector evidence objects are editable; E2 and E4 charts include embedded workbooks.`);return s;}
function title(s,t,x=30,y=22,w=1220){const m=t.match(/^\(([a-z])\) (.*)$/);if(m){tx(s,m[1],x,y,32,40,29,true);tx(s,m[2],x+43,y,w-43,40,29,true)}else tx(s,t,x,y,w,40,29,true)}
function xaxis(s,x,y,w,min,max,ticks,label,fmt=v=>String(v)){ln(s,x,y,x+w,y);const f=v=>x+(v-min)/(max-min)*w;ticks.forEach(v=>{ln(s,f(v),y,f(v),y+6);tx(s,fmt(v),f(v)-39,y+12,78,28,22,false,C.ink,'center')});if(label)tx(s,label,x-20,y+49,w+40,32,24,false,C.ink,'center');return f;}
function yaxis(s,x,y,h,min,max,ticks){ln(s,x,y,x,y+h);const f=v=>y+h-(v-min)/(max-min)*h;ticks.forEach(v=>{ln(s,x-6,f(v),x,f(v));tx(s,String(v),x-61,f(v)-14,46,28,22,false,C.ink,'right')});return f;}
function mix(a,b,t){let aa=a.slice(1).match(/../g).map(x=>parseInt(x,16)),bb=b.slice(1).match(/../g).map(x=>parseInt(x,16));return '#'+aa.map((v,i)=>Math.round(v+(bb[i]-v)*t).toString(16).padStart(2,'0')).join('')}
function ci(s,xlo,xhi,y,col){ln(s,xlo,y,xhi,y,col,2.2);ln(s,xlo,y-5,xlo,y+5,col,1.5);ln(s,xhi,y-5,xhi,y+5,col,1.5)}
// FIGURE 3: point estimates and their fixed-panel uncertainty.
{
const s=slide(3,'E1: completion time, deadline violations and incumbent service damage. Means and 95% seed-block intervals from 240 runs per site-policy, 20 seed blocks. Zero-width intervals remain points.');
const mets=[['critical_mission_completion_time_s','(a) Completion time','Time (s)',360,[0,120,240,360],1],['critical_mission_deadline_violation','(b) Missed deadlines','Runs (%)',100,[0,25,50,75,100],100],['existing_missions_damaged_count','(c) Incumbent damage','Damaged services / run',.6,[0,.2,.4,.6],1]];
mets.forEach(([met,head,unit,max,ticks,scale],j)=>{const l=30+j*417,x=l+88,w=285;title(s,head,l,22,390);tx(s,'Mean and 95% interval',l,65,390,30,22,false,C.muted);const fx=xaxis(s,x,628,w,0,max,ticks,unit,v=>max<1?v.toFixed(1):String(v));plots.push({slide:3,panel:j,x,y:121,w,h:507});
 sites.forEach((site,k)=>{let top=128+k*173;tx(s,'Site '+site,l,top-23,370,29,24,true);if(k>0)ln(s,l,top-29,l+373,top-29,C.grid,1);P.forEach((pol,i)=>{const yy=top+30+i*32,st=R.E1[site].summary[pol][met];tx(s,pol,l,yy-15,68,30,24,false,C[pol]);ci(s,fx(st.ci95[0]*scale),fx(st.ci95[1]*scale),yy,C[pol]);mark(s,fx(st.mean*scale),yy,pol,12);values.push({figure:3,site,policy:pol,metric:met,...st});});});
 });
}
// FIGURE 4: common-scale candidate geometry plus all regime-specific selections.
{
const s=slide(4,'E1 first-decision candidate geometry for all 720 matched scenario-seed states. B2 first states used once because snapshots match B1/B2/B4b. Coincident coordinates are aggregated, larger markers denote more coincident states. Negative best margin indicates no predicted timely alternative. Lower matrices report actual air selections, percent and row denominator.');
const rows=['A','B','C'];
const keys=['A: no timely-ground preemption conflict','B: speed/service conflict','C: no timely candidate'];
sh(s,'diamond',835,690,13,13,C.air);tx(s,'Preemptive air',858,680,190,32,22);sh(s,'ellipse',1053,690,13,13,C.ground);tx(s,'Other air',1077,680,164,32,22);
sites.forEach((site,j)=>{const l=30+j*417,x=l+66,y=99,w=309,h=242;title(s,`(${String.fromCharCode(97+j)}) Site ${site}`,l,22,390);let fx=xaxis(s,x,y+h,w,-100,400,[-100,0,200,400],null),fy=yaxis(s,x,y,h,-60,280,[0,100,200]);sh(s,'rect',x,fy(0),w,y+h-fy(0),'#F9EEEE');ln(s,x,fy(0),x+w,fy(0),'#B89898',1.5,true);ln(s,fx(0),y,fx(0),y+h,'#ACB5BC',1.3,true);
 const gg=new Map();for(const r of D.regimes.filter(r=>r.site===site&&r.policy==='B2'&&r.air_advantage!==null)){const key=[r.air_advantage,r.best_margin,r.preemption].join('|');let g=gg.get(key);if(g)g.n++;else gg.set(key,{...r,n:1});}
 for(const r of gg.values()){const size=5+Math.sqrt(r.n)*2.6;sh(s,r.preemption?'diamond':'ellipse',fx(r.air_advantage)-size/2,fy(r.best_margin)-size/2,size,size,r.preemption?'#E2AA6D':'#6792B8','#FFFFFF',1);}
 tx(s,'Best margin (s)',x,y-39,250,28,22);plots.push({slide:4,panel:j,x,y,w,h});
 const cy=479,cw=78,rh=48;tx(s,`(${String.fromCharCode(100+j)}) Air selection (%)`,l,415,390,35,26,true);P.slice(1).forEach((m,i)=>tx(s,m,l+75+i*cw,452,cw,28,22,true,C[m],'center'));
 keys.forEach((key,k)=>{const n=D.regime_summary[site].B2[key].n;tx(s,rows[k],l,cy+k*rh+8,61,28,23);P.slice(1).forEach((m,i)=>{const a=D.regime_summary[site][m][key],v=a.n?100*a.air/a.n:null;const xx=l+75+i*cw;sh(s,'rect',xx,cy+k*rh,cw,rh,v===null?'#F2F2F2':mix('#FAFBFC','#487BA5',v/100),'#FFFFFF',2);tx(s,v===null?'—':v.toFixed(0),xx,cy+k*rh+9,cw,30,23,v!==null&&v===100,v!==null&&v>65?'#FFFFFF':C.ink,'center');});tx(s,'n='+n,l+80+3*cw,cy+k*rh+10,87,27,21);});
});
tx(s,'Ground ETA − air ETA (s)',447,384,450,30,24,false,C.ink,'center');tx(s,'A  Other timely states     B  Faster preemptive air vs timely ground     C  No timely option',37,654,1200,31,22,false,C.muted);
}
// FIGURE 5: native stacked outcome charts and separate restoration denominators.
{
const s=slide(5,'E2 all-run deadline outcomes (320 runs per policy/site) and separately reported recovered/affected primary air-chain counts. Outcomes are composition percentages, without a new interval estimate. All affected coordinated runs establish a replacement path; denominators remain explicit.');
sh(s,'rect',831,74,19,14,'#729A87');tx(s,'On time',861,63,138,28,23);sh(s,'rect',1030,74,19,14,'#D3A0A0');tx(s,'Late',1060,63,130,28,23);
sites.forEach((site,j)=>{let l=30+j*417;title(s,`(${String.fromCharCode(97+j)}) Site ${site}`,l,22,380);
const late=P.map(m=>Number((R.E2[site].summary[m].critical_mission_deadline_violation.mean*100).toFixed(8)));
const ch=s.charts.add('bar',{position:{left:l,top:92,width:386,height:410},categories:P.slice().reverse(),series:[{name:'On time',values:late.map(v=>100-v).reverse(),fill:'#729A87',line:{fill:'none',width:0}},{name:'Late',values:late.slice().reverse(),fill:'#D3A0A0',line:{fill:'none',width:0}}],barOptions:{direction:'bar',grouping:'stacked',gapWidth:70},hasLegend:false,chartFill:'#FFFFFF',chartLine:{fill:'none',width:0},plotAreaFill:'#FFFFFF',plotAreaLine:{fill:'none',width:0},xAxis:{textStyle:{typeface:font,fontSize:24},line:{fill:C.ink,width:1.1}},yAxis:{min:0,max:100,majorUnit:25,numberFormatCode:'0',title:'',textStyle:{typeface:font,fontSize:23},majorGridlines:{fill:'none',width:0}},dataLabels:{showValue:true,position:'center',numberFormatCode:'0.#',textStyle:{typeface:font,fontSize:22}}});applyPresentationChartFont(ch,{fontFamily:font});
tx(s,'Runs (%)',l+66,503,309,30,24,false,C.ink,'center');tx(s,'Path restored / affected',l,548,376,34,25,true);P.slice(1).forEach((m,i)=>{const z=R.E2[site].summary[m];tx(s,m,l+3,594+i*34,65,30,23,true,C[m]);tx(s,`${z.recovered_n} / ${z.affected_n}`,l+83,594+i*34,215,30,24,false,C.ink);});
 });
}
// FIGURE 6: all level means, common color scale, and matched benefit against B0.
{
const s=slide(6,'E3 upper heatmaps contain every level/policy mean (40 runs in L1/L4; 80 in L2/L3). Common loss scale 0–400. Lower plots show paired B4b−B0 loss difference with 95% seed-block intervals. Levels are categorical changes in disturbance and demand.');
sites.forEach((site,j)=>{const l=30+j*417,x=l+74,top=115,cw=75,rh=49;title(s,`(${String.fromCharCode(97+j)}) Site ${site}`,l,22,380);['L1','L2','L3','L4'].forEach((v,i)=>tx(s,v,x+i*cw,77,cw,30,24,true,C.ink,'center'));
P.forEach((m,k)=>{tx(s,m,l,top+k*rh+10,65,30,23,true,C[m]);['L1','L2','L3','L4'].forEach((lev,i)=>{const v=R.E3[site].levels[lev][m].system_weighted_loss.mean;sh(s,'rect',x+i*cw,top+k*rh,cw,rh,mix('#F7FAFC','#355B78',v/400),'#FFFFFF',2);tx(s,Number(v.toFixed(1)).toString(),x+i*cw,top+k*rh+9,cw,31,22,false,v>215?'#FFFFFF':C.ink,'center');values.push({figure:6,site,policy:m,level:lev,value:v});});});plots.push({slide:6,panel:j,x,y:top,w:cw*4,h:rh*4});
const by=458,bh=157,xx=l+81,ww=294;title(s,`(${String.fromCharCode(100+j)}) B4b − B0`,l,397,385);let fx=xaxis(s,xx,630,ww,-400,50,[-400,-200,0],null);ln(s,fx(0),447,fx(0),615,'#A8B1B7',1.4,true);
['L1','L2','L3','L4'].forEach((lev,i)=>{const z=R.E3[site].vs_b0.find(t=>t.other==='B4b'&&t.level===lev&&t.metric==='system_weighted_loss'),yy=by+i*42;tx(s,lev,l+18,yy-15,52,30,23);ci(s,fx(z.ci95[0]),fx(z.ci95[1]),yy,C.B4b);mark(s,fx(z.diff_mean),yy,'B4b',13);values.push({figure:6,site,level:lev,contrast:'B4b-B0',...z});});
});
for(let i=0;i<100;i++)sh(s,'rect',428+i*3.3,345,3.4,14,mix('#F7FAFC','#355B78',i/99));tx(s,'0',383,336,37,30,22);tx(s,'400',765,336,59,30,22);tx(s,'SWL',830,336,97,30,23);tx(s,'Paired change in SWL (negative values indicate lower loss)',187,675,960,31,24,false,C.ink,'center');
}
// FIGURE 7: native charts with numeric x coordinates and redundant line/marker encoding.
{
const s=slide(7,'E4 Site A. Curves connect evaluated settings, without interpolation claims. 20 runs per policy/arm. B2 and B4b overlap; B1 also overlaps in execution waits 0–30 s. Timely service requires completion duration ≤180 s. Aircraft record burden changes input size around four active aircraft.');
P.forEach((m,i)=>{let x=256+i*235;ln(s,x,91,x+39,91,C[m],m==='B2'?4:2,m==='B4b');mark(s,x+20,91,m,m==='B2'?15:10,m==='B2'?'#FFFFFF':null);tx(s,m,x+51,75,121,31,24)});
const conf=[['4A','(a) Observation interval','Interval (s)',300,600,100,150],['4B','(b) Execution wait','Wait (s)',60,400,20,100],['4C','(c) Input burden','Aircraft records',50,24,10,6]];
conf.forEach(([key,head,xlabel,xmax,ymax,xstep,ystep],i)=>{const l=30+i*417;title(s,head,l,22,389);const arms=Object.keys(R.E4[key].arms);let series=i<2?P.map(m=>({name:m,values:arms.map(a=>R.E4[key].arms[a][m].metrics.critical_mission_completion_time_s.mean),xValues:arms.map(a=>Number(a.replace(/\D/g,''))),fill:C[m],line:{fill:C[m],width:m==='B2'?4.5:2.2,style:m==='B4b'?'dashed':'solid'},marker:{symbol:{B0:'square',B1:'triangle',B2:'circle',B4b:'diamond'}[m],size:m==='B2'?11:7},points:arms.map((a,k)=>({idx:k,fill:m==='B2'?'#FFFFFF':C[m],line:{fill:C[m],width:1.3}}))})):[{name:'B4b',values:arms.map(a=>R.E4[key].arms[a].B4b.llm_reliability.prompt_tokens_per_logged_call/1000),xValues:arms.map(a=>Number(a.replace(/\D/g,''))),fill:C.B4b,line:{fill:C.B4b,width:2.4},marker:{symbol:'diamond',size:8}}];
if(i<2)series.push({name:'Service window',values:[180,180],xValues:[0,xmax],line:{fill:'#B89898',width:1.2,style:'dashed'},marker:{symbol:'none',size:2}});
series=series.map(z=>({...z,values:z.values.map(v=>Number(v.toFixed(8)))}));
const ch=s.charts.add('scatter',{position:{left:l-9+(i===0?6.4:0),top:139,width:402,height:427},series,categories:[],scatterOptions:{style:'lineWithMarkers',varyColors:false},hasLegend:false,chartFill:'#FFFFFF',chartLine:{fill:'none',width:0},plotAreaFill:'#FFFFFF',plotAreaLine:{fill:'none',width:0},xAxis:{min:0,max:xmax,majorUnit:xstep,title:'',textStyle:{typeface:font,fontSize:23},line:{fill:C.ink,width:1.2}},yAxis:{min:0,max:ymax,majorUnit:ystep,title:{text:i===2?'Tokens / call (×10³)':'Completion (s)',textStyle:{typeface:font,fontSize:24}},textStyle:{typeface:font,fontSize:23},majorGridlines:{fill:C.grid,width:.8}},dataLabels:{showValue:false}});applyPresentationChartFont(ch,{fontFamily:font});tx(s,xlabel,l+72,572,310,32,24,false,C.ink,'center');
});
tx(s,'B2 = B4b at every interval',37,625,387,32,22);tx(s,'B1 = B2 = B4b at 0–30 s',455,625,383,32,22);tx(s,'Four active aircraft',872,625,364,32,22);tx(s,'180 s service window',37,664,387,32,22,false,C.muted);tx(s,'B2 = B4b at 60 s',455,664,383,32,22);tx(s,'5–50 total records',872,664,364,32,22,false,C.muted);
}
// FIGURE 8: two comparable supervisory trajectories in actual simulation time.
{
const s=slide(8,'E4B D60 representative deterministic event sequence. B0 duplicates retain due time; B4b changes pending air to ground at the fault. Dashed segments are pending commands, solid segments actual transport. Deadline at 480 s.');
title(s,'(a) B0: repeated ground command',32,29,920);title(s,'(b) B4b: air replaced by ground',32,336,920);
const x=144,w=1053,fx=t=>x+(t-300)/320*w;
for(const y of [120,429]){sh(s,'rect',fx(480),y-18,fx(620)-fx(480),151,'#FAEFEF');ln(s,fx(480),y+25,fx(480),y+159,C.red,1.8,true)}
function segment(a,b,y,c,dashed){ln(s,fx(a),y,fx(b),y,c,4.5,dashed)}
segment(300,360,176,C.ground,true);segment(360,542,176,C.ground,false);sh(s,'ellipse',fx(360)-6,170,12,12,'#FFFFFF',C.ground,2);sh(s,'ellipse',fx(542)-7,169,14,14,C.ground);
tx(s,'Selected',fx(300)-34,216,115,32,23);tx(s,'300 s',fx(300)-17,248,104,30,23);tx(s,'Execute',fx(360)-46,216,129,32,23);tx(s,'360 s',fx(360)-26,248,105,30,23);tx(s,'Complete',fx(542)-58,216,142,32,23);tx(s,'542 s',fx(542)-32,248,119,30,23);
tx(s,'Same command, same due time',fx(320),101,599,34,26,true,C.ground);tx(s,'Deadline',fx(480)-49,70,150,31,23,true,C.red);tx(s,'480 s',fx(480)-21,101,101,30,23,false,C.red);
segment(300,360,483,C.air,true);sh(s,'diamond',fx(360)-7,476,14,14,C.red);segment(360,420,483,C.ground,true);segment(420,602,483,C.ground,false);sh(s,'ellipse',fx(420)-6,477,12,12,'#FFFFFF',C.ground,2);sh(s,'ellipse',fx(602)-7,476,14,14,C.ground);
tx(s,'300 s',fx(300)-21,541,100,31,23);tx(s,'360 s fault',fx(360)-61,541,179,31,23);tx(s,'420 s execute',fx(420)-73,541,208,31,23);tx(s,'602 s complete',fx(602)-168,541,230,31,23);
tx(s,'Air selected',fx(300)-21,400,184,34,24,false,C.air);tx(s,'New ground command',fx(370),400,369,34,25,true,C.ground);tx(s,'Deadline',fx(480)-48,369,150,30,23,true,C.red);
xaxis(s,x,610,w,300,620,[300,360,420,480,540,600],null);tx(s,'Simulation time (s)',951,665,286,31,24,false,C.ink,'right');ln(s,144,681,204,681,C.muted,3,true);tx(s,'Pending',218,665,163,31,23);ln(s,417,681,477,681,C.ground,3);tx(s,'Actual transport',491,665,244,31,23);
}
await fs.mkdir(path.join(O,'output'),{recursive:true});
const stem=process.env.REDESIGN_STEM??'figures3_to_8_v4';
const candidate=path.join(O,stem+'.candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
execFileSync(PY,[path.join(O,'normalize_charts.py'),candidate],{stdio:'inherit'});
await fs.writeFile(path.join(O,'layout_contract.json'),JSON.stringify({plots,labels,values},null,2));
await finalizePresentation({workspaceDir:W,candidatePath:candidate,finalPath:path.join(O,'output',stem+'.pptx'),pythonExecutable:PY,integrityValidatorPath:path.join(SK,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SK,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],requiredNativeChartOwnerSlides:[3,5],materializeLiteralChartWorkbooks:true,nativeChartTargetApplication:'portable',fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(O,stem+'.validation.json')});
console.log('Finalized',stem);
