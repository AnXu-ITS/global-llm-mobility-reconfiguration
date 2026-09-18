import {execFileSync} from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const MODULES=process.env.RUNTIME_NODE_MODULES??'C:/Users/xuan1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
process.env.RUNTIME_NODE_MODULES=MODULES;
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const here=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../.build');
const work=path.dirname(here),root=path.dirname(work),out=path.join(work,'figures_revised');
const SK='C:/Users/xuan1/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const PY='C:/Users/xuan1/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(SK,'container_tools/artifact_tool_utils.mjs')));
const R=JSON.parse(await fs.readFile(path.join(work,'source/revision_v3/results_revised.json'),'utf8'));
const maps=JSON.parse(await fs.readFile(path.join(work,'.build/geometry.json'),'utf8'));
const p=Presentation.create({slideSize:{width:1280,height:720}});
const M=['B0','B1','B2','B4b'],sites=['A','B','C'];
const C={B0:'#7B858E',B1:'#D78A3A',B2:'#477F60',B4b:'#7954A3',ground:'#2F659D',air:'#D78A3A',disruption:'#B52935',ink:'#172B3A',gray:'#DDE3E8'};
const slides=[];
function shape(s,g,x,y,w,h,fill='none',stroke='none',lw=0){return s.shapes.add({geometry:g,position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:lw}})}
function txt(s,text,x,y,w,h,size=22,bold=false,color=C.ink,align='left'){
 const a=shape(s,'textbox',x,y,w,h);a.text=text;a.text.style={typeface:'Times New Roman',fontSize:size,bold,color,alignment:align,verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:{left:0,right:0,top:0,bottom:0}};return a;
}
function line(s,x1,y1,x2,y2,color=C.ink,width=1.4){
 const x=Math.min(x1,x2),y=Math.min(y1,y2),w=Math.max(0.01,Math.abs(x2-x1)),h=Math.max(0.01,Math.abs(y2-y1));
 return s.shapes.add({geometry:'custom',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:color,width},customPaths:[{width:w,height:h,commands:[{moveTo:{x:x1-x,y:y1-y}},{lineTo:{x:x2-x,y:y2-y}}]}]});
}
function arrow(s,a,b){s.shapes.connect(a,b,{kind:'straight',fromSide:'right',toSide:'left',line:{fill:C.ink,width:2},tail:{type:'triangle',width:'sm',length:'sm'}})}
function base(name,title,note){let s=p.slides.add();s.background.fill='#FFFFFF';txt(s,title,42,22,1196,52,30,true);line(s,42,84,1238,84,'#BCC6CE',1);s.speakerNotes.textFrame.setText(note+'\nSource: revision_v3/results_revised.json and decision_regimes.json.');slides.push({s,name});return s;}
function foot(s,t){ /* Detailed notes are retained in the caption and speaker notes. */ }
function legend(s,x=200,y=105){M.forEach((m,i)=>{shape(s,'rect',x+i*252,y+7,20,16,C[m]);txt(s,{B0:'B0 Ground',B1:'B1 Air-first',B2:'B2 Heuristic',B4b:'B4b LLM'}[m],x+28+i*252,y,207,30,21);});}
function chart(s,type,x,y,w,h,cats,series,max,unit,opts={}){
// Display-series precision only; frozen source numbers remain untouched.
series=series.map(z=>({...z,values:z.values.map(v=>Number(v.toFixed(8))),...(type==='scatter'?{points:z.values.map((v,idx)=>({idx,fill:z.fill,line:{fill:z.fill,width:1}}))}:{})}));
const c=s.charts.add(type,{position:{left:x,top:y,width:w,height:h},categories:cats,series:type==='bar'?series.map(z=>({...z,line:{fill:'none',width:0}})):series,hasLegend:false,
chartFill:'#FFFFFF',chartLine:{fill:'none',width:0},plotAreaFill:'#FFFFFF',plotAreaLine:{fill:'none',width:0},
barOptions:{direction:'column',grouping:'clustered',gapWidth:70},scatterOptions:{style:'lineWithMarkers',varyColors:false},
xAxis:{title:opts.xtitle??'',textStyle:{typeface:'Times New Roman',fontSize:19,fill:C.ink},line:{fill:'#637583',width:1},...(opts.xAxis??{})},
yAxis:{title:{text:unit,textStyle:{typeface:'Times New Roman',fontSize:19,fill:C.ink}},min:0,max,majorUnit:opts.major??max/4,numberFormatCode:opts.fmt??'0',textStyle:{typeface:'Times New Roman',fontSize:18,fill:C.ink},majorGridlines:{fill:'#E0E5E9',width:0.8}},
dataLabels:{showValue:false},...opts.extra});applyPresentationChartFont(c,{fontFamily:'Times New Roman'});return c;}
function ser(vals){return M.map(m=>({name:m,values:vals(m),fill:C[m],line:{fill:C[m],width:m==='B2'?4:2},marker:{symbol:{B0:'square',B1:'triangle',B2:'circle',B4b:'diamond'}[m],size:m==='B2'?11:7}}));}
// 2. Site maps from original projected geometry, native vector paths.
{
const s=base('fig02_sites','Contrasting network morphology','Source: canonical sim/sites geometry, primary routes and facility mappings. Map data © OpenStreetMap contributors, ODbL. Facilities and operations are modeled. Maps show the full imported road substrate at a common projected scale, not identical crop extents.');
const labels=['(a) Site A: Suzhou','(b) Site B: Amsterdam','(c) Site C: Edmonton'];
const maxSpan=Math.max(...maps.map(m=>Math.max(m.bounds[2]-m.bounds[0],m.bounds[3]-m.bounds[1]))),scale=390/maxSpan;
maps.forEach((m,k)=>{
const left=44+k*412,top=155,cx=(m.bounds[0]+m.bounds[2])/2,cy=(m.bounds[1]+m.bounds[3])/2;
const tr=pt=>[left+194+(pt[0]-cx)*scale,top+194-(pt[1]-cy)*scale];
txt(s,labels[k],left,105,370,34,25,true);
function paths(arr,col,lw,fill='none',close=false,dash=false){
 const pts=arr.flat().map(tr);if(!pts.length)return;
 const minx=Math.min(...pts.map(a=>a[0])),miny=Math.min(...pts.map(a=>a[1]));const ww=Math.max(.1,Math.max(...pts.map(a=>a[0]))-minx),hh=Math.max(.1,Math.max(...pts.map(a=>a[1]))-miny);
 const commands=[];for(const seg of arr){if(seg.length<2)continue;seg.map(tr).forEach((q,i)=>commands.push(i?{lineTo:{x:q[0]-minx,y:q[1]-miny}}:{moveTo:{x:q[0]-minx,y:q[1]-miny}}));if(close)commands.push({close:{}});}
 s.shapes.add({geometry:'custom',position:{left:minx,top:miny,width:ww,height:hh},fill,line:{fill:col,width:lw,style:dash?'dashed':'solid'},customPaths:[{width:ww,height:hh,commands}]});
}
for(const wa of m.water)paths([wa.points],'#B8D9EC',.8,wa.closed?'#DFEDF5':'none',wa.closed);
paths(m.roads,'#B9C2C9',.65);
for(const rr of m.auxiliary)paths(rr,'#7D95A8',1.9);
paths(m.baseline,C.ground,2.8);paths(m.detour,C.ground,2,'none',false,true);
const f=m.facilities;
function air(a,b,col,lw){if(!f[a]||!f[b])return;const aa=[f[a].x,f[a].y],bb=[f[b].x,f[b].y];const nn=45;const seg=[];for(let q=0;q<nn;q+=2)seg.push([aa.map((v,i)=>v+(bb[i]-v)*q/nn),aa.map((v,i)=>v+(bb[i]-v)*(q+1)/nn)]);paths(seg,col,lw);}
for(const [aa,bb] of m.background_air)air(aa,bb,'#BF9A6A',1.5);
air('V5','V4','#BF9A6A',1.5);
if(f.V1&&f.V2)paths([[[f.V1.x,f.V1.y],[f.V2.x,f.V2.y]]],C.air,2.3);
for(const key of ['D1','H1','B1']){if(!f[key])continue;const [xx,yy]=tr([f[key].x,f[key].y]);shape(s,key==='B1'?'diamond':'ellipse',xx-4,yy-4,8,8,key==='B1'?C.disruption:C.ink);const offs={D1:[-57,-24],H1:[8,3],B1:[9,-24]}[key];txt(s,key==='B1'?'Closure':key,xx+offs[0],yy+offs[1],78,27,21,true);}
for(const key of ['V3','D2','H2','C2','C3']){if(!f[key])continue;const [xx,yy]=tr([f[key].x,f[key].y]);shape(s,'rect',xx-4,yy-4,8,8,'#FFFFFF',key==='V3'?C.air:'#8C7168',1.6);txt(s,key,xx+7,yy-12,42,28,20,true,key==='V3'?C.air:'#735C55');}
line(s,left+12,561,left+12+500*scale,561,C.ink,2.4);txt(s,'500 m',left+8,566,100,28,21);
txt(s,['Urban (meshed)','River (barrier)','Suburban (sparse)'][k],left,610,390,30,21);
});
[['Primary ground',C.ground],['Detour',C.ground],['Primary air',C.air],['Auxiliary ground','#7D95A8'],['Other air','#BF9A6A']].forEach(([l,c],i)=>{if(l==='Detour'){line(s,45+i*244,652,56+i*244,652,c,2.5);line(s,62+i*244,652,73+i*244,652,c,2.5);}else line(s,45+i*244,652,73+i*244,652,c,2.5);txt(s,l,81+i*244,636,205,34,20);});
foot(s,'© OpenStreetMap contributors. Auxiliary routes show site context; they are not additional frozen E1 missions.');
}
// 3. E1 full policy comparison.
{
const s=base('fig03_e1_coordination','E1: selective air support and incumbent-service cost','results.json E1.{A,B,C}.summary. Each site-policy mean contains 240 runs. Charts show descriptive means; exact paired inference appears in the manuscript.');legend(s);
const metrics=[['critical_mission_completion_time_s','(a) Emergency completion','Time (s)',360,90],['critical_mission_deadline_violation','(b) Deadline violations','Percent',100,25],['existing_missions_damaged_count','(c) Service damage','Services / run',.6,.15]];
metrics.forEach(([met,title,unit,max,major],i)=>{txt(s,title,45+i*412,160,398,44,23,true);chart(s,'bar',38+i*412,213,400,400,['A','B','C'],ser(m=>sites.map(q=>R.E1[q].summary[m][met].mean*(met.includes('violation')?100:1))),max,unit,{major,fmt:met.includes('damaged')?'0.00':'0',xtitle:'Site'});});
foot(s,'Means over 240 runs per site and policy. Damage counts non-primary missions in specified horizon states.');
}
// 4. Log-derived supervisory decision regimes; all primary first states retained.
{
const regimes=JSON.parse(await fs.readFile(path.join(work,'source/revision_v3/decision_regimes.json'),'utf8'));
const counts=JSON.parse(await fs.readFile(path.join(work,'source/revision_v3/regime_summary.json'),'utf8'));
const s=base('fig04_candidate_ablation','Supervisory decision regimes','E1 first-decision logs. 720 matched scenario-seed states; subsequent trajectories may diverge. Candidate ETA is predictive, not actual completion.');
txt(s,'(a) Candidate geometry at Site A',45,111,570,42,25,true);
const x=110,y=214,w=486,h=355,fx=v=>x+(v+160)/310*w,fy=v=>y+h-(v+70)/330*h;
line(s,x,y+h,x+w,y+h,C.ink,1.4);line(s,x,y,x,y+h,C.ink,1.4);
[-150,-100,-50,0,50,100,150].forEach(v=>{line(s,fx(v),y+h,fx(v),y+h+6,C.ink);txt(s,String(v),fx(v)-28,y+h+9,56,28,19,false,C.ink,'center')});
[-50,0,100,200].forEach(v=>{line(s,x-6,fy(v),x,fy(v),C.ink);txt(s,String(v),x-62,fy(v)-14,48,28,19,false,C.ink,'right')});
line(s,fx(0),y,fx(0),y+h,'#A9B5BD',1);line(s,x,fy(0),x+w,fy(0),'#A9B5BD',1);
txt(s,'Margin (s)',43,191,183,26,19);
txt(s,'Ground ETA − air ETA (s)',107,623,489,32,21,false,C.ink,'center');
const aa=regimes.filter(r=>r.site==='A'&&r.policy==='B2'&&r.air_advantage!==null);
for(const r of aa){shape(s,r.preemption?'diamond':'ellipse',fx(r.air_advantage)-4,fy(r.best_margin)-4,8,8,r.preemption?C.air:C.ground,'#FFFFFF',.5)}
shape(s,'diamond',96,170,10,10,C.air);txt(s,'Preemption',114,155,173,32,19);shape(s,'ellipse',310,170,10,10,C.ground);txt(s,'No preemption',329,155,216,32,19);
txt(s,'(b) Faster air vs timely ground',674,111,548,42,25,true);
txt(s,'Air selection (%) when air requires preemption',674,156,548,33,21);
const policies=['B1','B2','B4b'],data=policies.map(m=>({name:m,values:sites.map(q=>{const z=counts[q][m]['B: speed/service conflict'];return z.n?z.air/z.n*100:0}),fill:C[m],line:{fill:'none',width:0}}));
chart(s,'bar',665,208,560,329,sites,data,100,'Air selection (%)',{major:25,xtitle:'Site'});
policies.forEach((m,i)=>{shape(s,'rect',720+i*157,185,15,12,C[m]);txt(s,m,741+i*157,175,103,28,20)});
txt(s,'Matched states: A 20 · B 60 · C 20',714,537,497,30,21);
txt(s,'(c) No candidate predicted timely',672,593,550,34,24,true);
txt(s,'Observed late: A 40/40 · C 24/27 per policy',675,635,550,32,22);
}
// 5. Conditional recovery and all-run timeliness.
{
const s=base('fig05_e2_recovery','E2: restoring a path and meeting the deadline','results.json E2 summaries. Recovery denominators are affected critical air chains. Deadline outcomes use all 320 runs per site and policy. B0 has no affected critical air chain.');legend(s);
txt(s,'(a) Deadline violations in all runs',55,160,560,42,24,true);
chart(s,'bar',40,216,575,410,['A','B','C'],ser(m=>sites.map(q=>100*R.E2[q].summary[m].critical_mission_deadline_violation.mean)),100,'Percent',{major:25,xtitle:'Site'});
txt(s,'(b) Recovered / affected critical chains',676,160,558,42,24,true);
const yy=252;['Site','Rule\n(B1)','Heuristic\n(B2)','LLM\n(B4b)'].forEach((z,i)=>txt(s,z,675+i*139,yy-14,130,58,21,true,C.ink,'center'));
for(let j=0;j<3;j++){line(s,675,yy+49+j*88,1230,yy+49+j*88,'#D9E0E5');txt(s,sites[j],675,yy+66+j*88,130,38,23,true,C.ink,'center');['B1','B2','B4b'].forEach((m,i)=>{const z=R.E2[sites[j]].summary[m];txt(s,`${z.recovered_n}/${z.affected_n}`,814+i*139,yy+66+j*88,130,38,24,true,C[m],'center');});}
txt(s,'Every affected coordinated run restores a path\nB0 recovery: not applicable',677,586,547,62,21);
foot(s,'All-run outcomes: 320 runs per site and policy. Conditional restoration can coexist with substantial lateness.');
}
// 6. E3 site panels, all policies.
{
const s=base('fig06_e3_compound','E3: priority-weighted service loss across network contexts','results.json E3.{site}.levels. SWL weights CRITICAL/HIGH/NORMAL/LOW = 4/3/2/1. L1/L4 have 40 runs per manager; L2/L3 have 80.');legend(s);
sites.forEach((q,i)=>{txt(s,`(${String.fromCharCode(97+i)}) Site ${q}`,46+i*412,162,380,40,24,true);chart(s,'bar',36+i*412,218,402,403,['L1','L2','L3','L4'],ser(m=>['L1','L2','L3','L4'].map(l=>R.E3[q].levels[l][m].system_weighted_loss.mean)),400,'Loss units',{major:100,xtitle:'Scenario level'});});
foot(s,'L1/L4: 40 runs per policy. L2/L3: 80. Levels vary in both disturbance structure and mission demand.');
}
// 7. Timing curves and input burden.
{
const s=base('fig07_operational','E4: observation, execution and input burden','results.json E4 4A/4B/4C arms. 20 runs per arm-policy. All curves connect discrete tested arms. B2 and B4b completion outcomes coincide. Input burden uses a fixed core fleet of 4 aircraft.');legend(s);
const xs=[[10,30,60,120,300],[0,1,5,10,20,30,60],[5,10,20,30,50]],keys=['4A','4B','4C'],pref=['OBS','D','N'];
const titles=['(a) Observation interval','(b) Execution delay','(c) LLM input burden'];
for(let i=0;i<3;i++){
txt(s,titles[i],46+i*412,160,385,42,24,true);
const arms=Object.keys(R.E4[keys[i]].arms),data=i<2?ser(m=>arms.map(a=>R.E4[keys[i]].arms[a][m].metrics.critical_mission_completion_time_s.mean)):[{name:'B4b',values:arms.map(a=>R.E4['4C'].arms[a].B4b.llm_reliability.prompt_tokens_per_logged_call/1000),fill:C.B4b,line:{fill:C.B4b,width:2.6},marker:{symbol:'diamond',size:8}}];
data.forEach(z=>z.xValues=xs[i]);
chart(s,'scatter',36+i*412,217,402,402,[],data,i===0?600:i===1?400:24,i===2?'Prompt tokens / call (thousands)':'Completion (s)',{major:i===0?150:i===1?100:6,xtitle:i===2?'Aircraft records':i===0?'Interval (s)':'Delay (s)',xAxis:{min:0,max:i===0?300:i===1?60:50,majorUnit:i===0?100:i===1?20:10}});
}
txt(s,'B2 = B4b (all arms)',95,635,342,31,21,true);txt(s,'B1 = B2 = B4b (0–30 s)',480,635,377,31,21,true);txt(s,'B2 = B4b (60 s)',502,669,325,30,21);
}
// 8. Pending versus executed transport, including corrected B0.
{
const s=base('fig08_execution_timeline','Execution waiting: repeated command or changed intervention','Revised E4B D60. B0 retains its original due time for an identical pending command. B4b genuinely changes air to ground. Absolute deadline 480 s.');
const fx=t=>224+(t-300)/320*984;
function seg(a,b,y,c,dashed){if(dashed){for(let t=a;t<b;t+=7)line(s,fx(t),y,fx(Math.min(t+4,b)),y,c,5)}else line(s,fx(a),y,fx(b),y,c,5);}
txt(s,'B0 ground-only',34,198,177,50,24,true);txt(s,'B4b air command',34,346,179,56,23,true);txt(s,'B4b ground',34,478,180,52,24,true);
seg(300,360,229,C.ground,true);seg(360,542,229,C.ground,false);
txt(s,'Identical command retained',228,122,471,35,24,true,C.ground);
txt(s,'360 s execute',fx(360)-70,261,189,34,22);txt(s,'542 s complete',fx(542)-72,261,208,34,22);
seg(300,360,377,C.air,true);shape(s,'diamond',fx(360)-7,370,14,14,C.disruption);
txt(s,'300 s air selected',224,310,263,34,22);txt(s,'360 s fault: air → ground',fx(360)+18,355,480,38,23,true,C.disruption);
seg(360,420,504,C.ground,true);seg(420,602,504,C.ground,false);
txt(s,'420 s execute',fx(420)-65,540,212,32,22);txt(s,'602 s complete',fx(602)-171,540,222,32,22);
line(s,fx(480),173,fx(480),577,C.disruption,1.6);txt(s,'480 s deadline',fx(480)-77,118,223,42,23,true,C.disruption);
line(s,fx(300),613,fx(620),613,C.ink,1.5);[300,360,420,480,540,600].forEach(t=>{line(s,fx(t),607,fx(t),621,C.ink,1.2);txt(s,String(t),fx(t)-30,628,60,27,20,false,C.ink,'center')});
txt(s,'Simulation time (s)',870,668,331,31,22,false,C.ink,'right');
seg(300,324,681,'#697984',true);txt(s,'Pending',fx(327),665,151,31,20);seg(378,401,681,'#697984',false);txt(s,'Actual transport',fx(405),665,270,31,20);
}
await fs.mkdir(out,{recursive:true});
const candidate=path.join(here,'figures_v3_candidate.pptx');
await(await PresentationFile.exportPptx(p)).save(candidate);
execFileSync(PY,[path.join(work,'source/revision_v2/normalize_chart_markers.py'),candidate],{stdio:'inherit'});
console.log('PPTX exported',slides.length);
for(const {s,name} of slides){const b=await p.export({slide:s,format:'png',scale:1.5});await fs.writeFile(path.join(out,name+'.png'),new Uint8Array(await b.arrayBuffer()));const l=await s.export({format:'layout'});await fs.writeFile(path.join(here,name+'.layout.json'),await l.text());console.log('Rendered',name);}
const final=path.join(out,process.env.FIGURE_PPTX_NAME??'MANUSCRIPT_FIGURES_2_to_8_revised.pptx');
await finalizePresentation({workspaceDir:work,candidatePath:candidate,finalPath:final,pythonExecutable:PY,
integrityValidatorPath:path.join(SK,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SK,'container_tools/inspect_presentation_layout_geometry.py'),
layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],requiredNativeChartOwnerSlides:[2,4,5,6],
fontPolicy:{basis:'design',families:['Times New Roman']},verifyArtifactToolImport:true,materializeLiteralChartWorkbooks:true,nativeChartTargetApplication:'portable',
receiptPath:path.join(here,'revision_v2',Date.now()+'.figures.validation.json')});
console.log('Final',final);
