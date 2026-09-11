import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const MODULES=process.env.RUNTIME_NODE_MODULES??'C:/Users/xuan1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const here=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../.build');
const work=path.dirname(here),root=path.dirname(work),out=path.join(work,'figures');
const SK='C:/Users/xuan1/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const PY='C:/Users/xuan1/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(SK,'container_tools/artifact_tool_utils.mjs')));
const R=JSON.parse(await fs.readFile(path.join(root,'outputs/paper_final/results.json'),'utf8'));
const maps=JSON.parse(await fs.readFile(path.join(here,'geometry.json'),'utf8'));
const p=Presentation.create({slideSize:{width:1280,height:720}});
const M=['B0','B1','B2','B4b'],sites=['A','B','C'];
const C={B0:'#7B858E',B1:'#D28A2E',B2:'#3266A8',B4b:'#217A67',ink:'#172B3A',gray:'#DDE3E8'};
const slides=[];
function shape(s,g,x,y,w,h,fill='none',stroke='none',lw=0){return s.shapes.add({geometry:g,position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:lw}})}
function txt(s,text,x,y,w,h,size=22,bold=false,color=C.ink,align='left'){
 const a=shape(s,'textbox',x,y,w,h);a.text=text;a.text.style={typeface:'Arial',fontSize:size,bold,color,alignment:align,verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:{left:0,right:0,top:0,bottom:0}};return a;
}
function line(s,x1,y1,x2,y2,color=C.ink,width=1.4){
 const x=Math.min(x1,x2),y=Math.min(y1,y2),w=Math.max(0.01,Math.abs(x2-x1)),h=Math.max(0.01,Math.abs(y2-y1));
 return s.shapes.add({geometry:'custom',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:color,width},customPaths:[{width:w,height:h,commands:[{moveTo:{x:x1-x,y:y1-y}},{lineTo:{x:x2-x,y:y2-y}}]}]});
}
function arrow(s,a,b){s.shapes.connect(a,b,{kind:'straight',fromSide:'right',toSide:'left',line:{fill:C.ink,width:2},tail:{type:'triangle',width:'sm',length:'sm'}})}
function base(name,title,note){let s=p.slides.add();s.background.fill='#FFFFFF';txt(s,title,42,22,1196,52,30,true);line(s,42,84,1238,84,'#BCC6CE',1);s.speakerNotes.textFrame.setText(note+'\nSource: paper_final_20260910; figures use frozen reported data.');slides.push({s,name});return s;}
function foot(s,t){txt(s,t,44,675,1192,32,17,false,'#52616D');}
function legend(s,x=340,y=105){M.forEach((m,i)=>{shape(s,'rect',x+i*165,y+7,20,16,C[m]);txt(s,m,x+28+i*165,y,100,30,21);});}
function chart(s,type,x,y,w,h,cats,series,max,unit,opts={}){
// Display-series precision only; frozen source numbers remain untouched.
series=series.map(z=>({...z,values:z.values.map(v=>Number(v.toFixed(8)))}));
const c=s.charts.add(type,{position:{left:x,top:y,width:w,height:h},categories:cats,series:type==='bar'?series.map(z=>({...z,line:{fill:'none',width:0}})):series,hasLegend:false,
chartFill:'#FFFFFF',chartLine:{fill:'none',width:0},plotAreaFill:'#FFFFFF',plotAreaLine:{fill:'none',width:0},
barOptions:{direction:'column',grouping:'clustered',gapWidth:70},scatterOptions:{style:'lineWithMarkers'},
xAxis:{title:opts.xtitle??'',textStyle:{typeface:'Arial',fontSize:19,fill:C.ink},line:{fill:'#637583',width:1},...(opts.xAxis??{})},
yAxis:{title:{text:unit,textStyle:{typeface:'Arial',fontSize:19,fill:C.ink}},min:0,max,majorUnit:opts.major??max/4,numberFormatCode:opts.fmt??'0',textStyle:{typeface:'Arial',fontSize:18,fill:C.ink},majorGridlines:{fill:'#E0E5E9',width:0.8}},
dataLabels:{showValue:false},...opts.extra});applyPresentationChartFont(c,{fontFamily:'Arial'});return c;}
function ser(vals){return M.map(m=>({name:m,values:vals(m),fill:C[m],line:{fill:C[m],width:m==='B2'?4:2},marker:{symbol:{B0:'square',B1:'triangle',B2:'circle',B4b:'diamond'}[m],size:m==='B2'?11:7}}));}
// 1. Architecture, all nodes editable.
{
const s=base('fig01_architecture','Ground–Low-Altitude Mobility Manager','Architecture based on frozen state, candidate, manager, checker and runner implementations. Safety denotes modeled constraints, not formal certification.');
const xs=[44,462,880],w=356;
function box(x,y,title,body,accent=false){const b=shape(s,'rect',x,y,w,153,accent?'#EEF6F3':'#F4F6F8','#577080',1.4);txt(s,title,x+15,y+12,w-30,58,21,true);txt(s,body,x+15,y+72,w-30,68,20);return b;}
const a=box(xs[0],135,'Global State','Ground, aircraft, facilities\nMissions, events, timestamps');
const b=box(xs[1],135,'Manager-Agnostic\nExecutable Candidate Interface','Legality, ETA, service consequences\nShared facts without B2 scores',true);
const c=box(xs[2],135,'Supervisory Policy','B0 ground-only     B1 air-first\nB2 heuristic          B4b LLM');arrow(s,a,b);arrow(s,b,c);
const d=box(xs[2],377,'Deterministic Safety /\nFeasibility Checker','Validate identifiers and constraints\nRecheck current execution state');
const e=box(xs[1],377,'Executor','Issue or queue structured actions\nTrack execution and supersession');
const f=box(xs[0],377,'SUMO + BlueSky closed loop','Ground and air evolution\nShared service registry, 1 s step');
s.shapes.connect(c,d,{kind:'straight',fromSide:'bottom',toSide:'top',line:{fill:C.ink,width:2},tail:{type:'triangle',width:'sm',length:'sm'}});
for(const [aa,bb] of [[d,e],[e,f]])s.shapes.connect(aa,bb,{kind:'straight',fromSide:'left',toSide:'right',line:{fill:C.ink,width:2},tail:{type:'triangle',width:'sm',length:'sm'}});
s.shapes.connect(f,a,{kind:'straight',fromSide:'top',toSide:'bottom',line:{fill:C.ink,width:2},tail:{type:'triangle',width:'sm',length:'sm'}});
txt(s,'Observe\nand update',48,299,145,65,20);txt(s,'Select\nintervention',891,299,145,65,20);
const l=shape(s,'rect',46,583,355,50,'#FFFFFF','#577080',1.3);txt(s,'Local contingency responses',57,588,330,38,21,true);
s.shapes.connect(l,f,{kind:'straight',fromSide:'top',toSide:'bottom',line:{fill:C.ink,width:1.5},tail:{type:'triangle',width:'sm',length:'sm'}});
txt(s,'Local responses operate independently of supervisory inference',462,581,755,54,22);
foot(s,'B0 restricts emergency support to ground. Background air services remain in the environment.');
}
// 2. Site maps from original projected geometry, native vector paths.
{
const s=base('fig02_sites','Three network contexts','Source: canonical sim/sites geometry, primary routes and facility mappings. Map data © OpenStreetMap contributors, ODbL. Facilities and operations are modeled. Maps show the full imported road substrate at a common projected scale, not identical crop extents.');
const labels=['(a) Suzhou','(b) Amsterdam','(c) Edmonton'];
const maxSpan=Math.max(...maps.map(m=>Math.max(m.bounds[2]-m.bounds[0],m.bounds[3]-m.bounds[1]))),scale=390/maxSpan;
maps.forEach((m,k)=>{
const left=44+k*412,top=155,cx=(m.bounds[0]+m.bounds[2])/2,cy=(m.bounds[1]+m.bounds[3])/2;
const tr=pt=>[left+194+(pt[0]-cx)*scale,top+194-(pt[1]-cy)*scale];
txt(s,labels[k],left,105,370,34,25,true);
function paths(arr,col,lw,fill='none',close=false){
 const pts=arr.flat().map(tr);if(!pts.length)return;
 const minx=Math.min(...pts.map(a=>a[0])),miny=Math.min(...pts.map(a=>a[1]));const ww=Math.max(.1,Math.max(...pts.map(a=>a[0]))-minx),hh=Math.max(.1,Math.max(...pts.map(a=>a[1]))-miny);
 const commands=[];for(const seg of arr){if(seg.length<2)continue;seg.map(tr).forEach((q,i)=>commands.push(i?{lineTo:{x:q[0]-minx,y:q[1]-miny}}:{moveTo:{x:q[0]-minx,y:q[1]-miny}}));if(close)commands.push({close:{}});}
 s.shapes.add({geometry:'custom',position:{left:minx,top:miny,width:ww,height:hh},fill,line:{fill:col,width:lw},customPaths:[{width:ww,height:hh,commands}]});
}
for(const wa of m.water)paths([wa.points],'#B8D9EC',.8,wa.closed?'#DFEDF5':'none',wa.closed);
paths(m.roads,'#B9C2C9',.65);
for(const rr of m.auxiliary)paths(rr,'#A8867A',1.9);
paths(m.baseline,'#BE4B49',2.8);paths(m.detour,'#B06491',2);
const f=m.facilities;
function air(a,b,col,lw){if(!f[a]||!f[b])return;const aa=[f[a].x,f[a].y],bb=[f[b].x,f[b].y];const nn=45;const seg=[];for(let q=0;q<nn;q+=2)seg.push([aa.map((v,i)=>v+(bb[i]-v)*q/nn),aa.map((v,i)=>v+(bb[i]-v)*(q+1)/nn)]);paths(seg,col,lw);}
for(const [aa,bb] of m.background_air)air(aa,bb,'#6797AC',1.5);
air('V5','V4','#6797AC',1.5);
if(f.V1&&f.V2)paths([[[f.V1.x,f.V1.y],[f.V2.x,f.V2.y]]],C.B4b,2.3);
for(const key of ['D1','H1','B1']){if(!f[key])continue;const [xx,yy]=tr([f[key].x,f[key].y]);shape(s,key==='B1'?'diamond':'ellipse',xx-4,yy-4,8,8,key==='B1'?C.B1:C.ink);const offs={D1:[-57,-24],H1:[8,3],B1:[9,-24]}[key];txt(s,key==='B1'?'Closure':key,xx+offs[0],yy+offs[1],68,23,17,true);}
for(const key of ['V3','D2','H2','C2','C3']){if(!f[key])continue;const [xx,yy]=tr([f[key].x,f[key].y]);shape(s,'rect',xx-4,yy-4,8,8,'#FFFFFF',key==='V3'?C.B4b:'#8C7168',1.6);txt(s,key,xx+7,yy-12,36,24,16,true,key==='V3'?C.B4b:'#735C55');}
line(s,left+12,561,left+12+500*scale,561,C.ink,2.4);txt(s,'500 m',left+8,566,100,25,17);
txt(s,['Meshed urban network','Water-barrier urban network','Dispersed suburban network'][k],left,610,390,30,21);
});
[['Primary ground','#BE4B49'],['Detour','#B06491'],['Primary air',C.B4b],['Auxiliary ground','#A8867A'],['Other air','#6797AC']].forEach(([l,c],i)=>{line(s,45+i*244,652,73+i*244,652,c,2.5);txt(s,l,81+i*244,636,205,30,18);});
foot(s,'© OpenStreetMap contributors. Auxiliary routes show site context; they are not additional frozen E1 missions.');
}
// 3. E1 full policy comparison.
{
const s=base('fig03_e1_coordination','E1: emergency transport and existing-service consequences','results.json E1.{A,B,C}.summary. Each site-policy mean contains 240 runs. Charts show descriptive means; exact paired inference appears in the manuscript.');legend(s);
const metrics=[['critical_mission_completion_time_s','(a) Emergency completion','Time (s)',360,90],['critical_mission_deadline_violation','(b) Deadline violations','Percent',100,25],['existing_missions_damaged_count','(c) Service damage','Services / run',.6,.15]];
metrics.forEach(([met,title,unit,max,major],i)=>{txt(s,title,45+i*412,160,398,44,23,true);chart(s,'bar',38+i*412,213,400,400,['A','B','C'],ser(m=>sites.map(q=>R.E1[q].summary[m][met].mean*(met.includes('violation')?100:1))),max,unit,{major,fmt:met.includes('damaged')?'0.00':'0',xtitle:'Site'});});
foot(s,'Means over 240 runs per site and policy. Damage counts non-primary missions in specified horizon states.');
}
// 4. Native editable forest plots for custom paired intervals.
{
const s=base('fig04_candidate_ablation','E1: effect of the executable candidate interface','results.json E1.{A,B,C}.ablation. B4b minus B4a, 60 matched runs per site. Intervals are frozen 95% paired intervals; binary risk-difference intervals are descriptive.');
const defs=[['Completion difference (s)',0,-25,10,1],['Service damage difference',1,-.6,.2,1],['Air intervention difference (pp)',2,-60,20,100]];
defs.forEach(([title,idx,mn,mx,mul],k)=>{
const x=80+k*407,w=322,y=239,h=278,fx=v=>x+(v-mn)/(mx-mn)*w;txt(s,'('+String.fromCharCode(97+k)+') '+title,x-34,145,w+65,65,23,true);
line(s,fx(0),217,fx(0),536,'#83929D',1.4);
for(let j=0;j<3;j++){const z=R.E1[sites[j]].ablation[idx],yy=y+j*109;txt(s,sites[j],x-36,yy-18,30,36,22,true);line(s,fx(z.ci95[0]*mul),yy,fx(z.ci95[1]*mul),yy,C.B4b,3);for(const v of z.ci95)line(s,fx(v*mul),yy-7,fx(v*mul),yy+7,C.B4b,2);shape(s,'ellipse',fx(z.diff_mean*mul)-6,yy-6,12,12,C.B4b);txt(s,(z.diff_mean*mul).toFixed(idx===1?3:2),x,yy+17,w,28,20,false,C.ink,'center');}
line(s,x,550,x+w,550,C.ink,1);[mn,0,mx].forEach(v=>txt(s,String(v),fx(v)-35,560,70,30,19,false,C.ink,'center'));
});
txt(s,'Negative differences indicate lower completion time, fewer damaged services or less air intervention',50,612,1180,38,21);
foot(s,'60 matched B4b–B4a runs per site. Bars show 95% intervals. The explicit-table effect is largest at Site A.');
}
// 5. Conditional recovery and all-run timeliness.
{
const s=base('fig05_e2_recovery','E2: restoring a path and meeting the deadline','results.json E2 summaries. Recovery denominators are affected critical air chains. Deadline outcomes use all 320 runs per site and policy. B0 has no affected critical air chain.');legend(s,360);
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
foot(s,'20 runs per arm and policy. B2/B4b overlap in (a,b). Panel (c) expands records around a fixed four-aircraft fleet.');
}
// 8. D60 event sequence, true simulation times.
{
const s=base('fig08_execution_timeline','Execution sequence with a 60 s action delay','E4B D60 B4b trace from final experiment report. At t=360 failure and a new ground decision supersede the pending dispatch. Ground executes at 420 and completes at 602. Release 300, deadline 480.');
const fx=t=>170+(t-300)/320*1000;
line(s,fx(300),596,fx(620),596,C.ink,1.8);
[300,360,420,480,540,600].forEach(t=>{line(s,fx(t),588,fx(t),604,C.ink,1.5);txt(s,String(t),fx(t)-35,610,70,30,21,false,C.ink,'center');});
txt(s,'Simulation time (s)',885,644,330,28,21,false,C.ink,'right');
txt(s,'Air command',35,214,130,45,22,true);txt(s,'Ground service',35,425,130,58,22,true);
line(s,fx(300),250,fx(360),250,C.B2,7);shape(s,'ellipse',fx(300)-6,244,12,12,C.B2);shape(s,'diamond',fx(360)-8,242,16,16,'#BE4B49');
txt(s,'300 s\nInitial dispatch selected',fx(300),131,276,68,23,true);
txt(s,'360 s\nFailure and replacement decision',fx(360)-20,293,390,72,23,true,'#A43B37');
line(s,fx(360),443,fx(420),443,C.B1,7);line(s,fx(420),443,fx(602),443,C.B4b,7);
[360,420,602].forEach(t=>shape(s,'ellipse',fx(t)-6,437,12,12,t===360?C.B1:C.B4b));
txt(s,'Pending',fx(302),257,170,30,21,false,C.B2);txt(s,'Pending',fx(362),453,170,30,21,false,C.B1);
txt(s,'420 s\nGround executes',fx(420)-15,482,220,65,23,true,C.B4b);
txt(s,'602 s\nMission completes',fx(602)-182,482,217,65,23,true,C.B4b,'right');
txt(s,'Ground travel',fx(500),389,235,35,23,false,C.B4b);
line(s,fx(480),126,fx(480),578,'#A43B37',1.8);txt(s,'480 s\nDeadline',fx(480)+10,136,173,64,23,true,'#A43B37');
txt(s,'Pending dispatch is superseded',fx(300),206,510,30,21);
foot(s,'Completion duration: 602 − 300 = 302 s. This is a tested queue transition, not a universal delay threshold.');
}
await fs.mkdir(out,{recursive:true});
const candidate=path.join(here,'figures_candidate.pptx');
await(await PresentationFile.exportPptx(p)).save(candidate);
console.log('PPTX exported',slides.length);
for(const {s,name} of slides){const b=await p.export({slide:s,format:'png',scale:1.5});await fs.writeFile(path.join(out,name+'.png'),new Uint8Array(await b.arrayBuffer()));const l=await s.export({format:'layout'});await fs.writeFile(path.join(here,name+'.layout.json'),await l.text());console.log('Rendered',name);}
const final=path.join(out,process.env.FIGURE_PPTX_NAME??'MANUSCRIPT_FIGURES.pptx');
await finalizePresentation({workspaceDir:work,candidatePath:candidate,finalPath:final,pythonExecutable:PY,
integrityValidatorPath:path.join(SK,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SK,'container_tools/inspect_presentation_layout_geometry.py'),
layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],requiredNativeChartOwnerSlides:[3,5,6,7],
fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,materializeLiteralChartWorkbooks:true,nativeChartTargetApplication:'portable',
receiptPath:path.join(here,(process.env.FIGURE_PPTX_NAME??'MANUSCRIPT_FIGURES.pptx')+'.validation.json')});
console.log('Final',final);
