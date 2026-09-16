import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url)),out=path.dirname(here),work=path.dirname(out),assets=path.join(out,'hybrid_assets');
const MOD='C:/Users/xuan1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
process.env.RUNTIME_NODE_MODULES=MOD;
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(MOD,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const SK='C:/Users/xuan1/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const PY='C:/Users/xuan1/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const {finalizePresentation}=await import(pathToFileURL(path.join(SK,'container_tools/artifact_tool_utils.mjs')));
const W=1840,H=1380,name=process.env.HYBRID_STEM??'Figure1_revised';
const p=Presentation.create({slideSize:{width:W,height:H}}),s=p.slides.add();s.background.fill='#FFFFFF';
const C={ink:'#1C2430',blue:'#386AA4',ground:'#2F659D',road:'#A5ABB5',air:'#D78A3A',red:'#B52935',purple:'#7954A3',green:'#477F60',border:'#AAB0B8'};
const provenance=JSON.parse(await fs.readFile(path.join(assets,'asset_provenance.json'),'utf8'));
const svg=[],objects=[],texts=[],images=[];let n=0;
const esc=t=>String(t).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function shape(g,x,y,w,h,fill='none',stroke='none',lw=0,label=''){
 const a=s.shapes.add({name:label||`object_${++n}`,geometry:g,position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:lw}});
 objects.push({g,x,y,w,h,label});
 if(g==='ellipse')svg.push(`<ellipse cx="${x+w/2}" cy="${y+h/2}" rx="${w/2}" ry="${h/2}" fill="${fill}" stroke="${stroke}" stroke-width="${lw}"/>`);
 else if(g!=='textbox')svg.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" stroke="${stroke}" stroke-width="${lw}"/>`);
 return a;
}
function text(t,x,y,w,h,sz=27,bold=false,color=C.ink,align='left'){
 const a=shape('textbox',x,y,w,h,'none','none',0,t);a.text=t;
 a.text.style={typeface:'Times New Roman',fontSize:sz,bold,color,alignment:align,verticalAlignment:'middle',autoFit:'none',wrap:'none',insets:{left:0,right:0,top:0,bottom:0}};
 // Explicit line-height accommodation, without shrinking source-calibrated glyphs.
 const needed=t.split('\n').length*sz*1.2;
 if(h<needed){a.position={left:x,top:y-(needed-h)/2,width:w,height:needed};}
 texts.push({text:t,x,y,w,h,size:sz});
 const lines=t.split('\n'),lh=sz*1.05,base=y+(h-lines.length*lh)/2+sz*.83,tx=align==='center'?x+w/2:align==='right'?x+w:x;
 svg.push(`<text font-family="Times New Roman,serif" font-size="${sz}" font-weight="${bold?700:400}" fill="${color}" text-anchor="${align==='center'?'middle':align==='right'?'end':'start'}">${lines.map((l,i)=>`<tspan x="${tx}" y="${base+i*lh}">${esc(l)}</tspan>`).join('')}</text>`);return a;
}
function route(pts,col=C.road,lw=3,dash=false,fill='none',closed=false){
 const xx=pts.map(q=>q[0]),yy=pts.map(q=>q[1]),x=Math.min(...xx),y=Math.min(...yy),w=Math.max(.01,Math.max(...xx)-x),h=Math.max(.01,Math.max(...yy)-y);
 const commands=pts.map((q,i)=>({[i?'lineTo':'moveTo']:{x:q[0]-x,y:q[1]-y}}));if(closed)commands.push({close:{}});
 s.shapes.add({name:`path_${++n}`,geometry:'custom',position:{left:x,top:y,width:w,height:h},fill,line:{fill:col,width:lw,style:dash?'dashed':'solid'},customPaths:[{width:w,height:h,commands}]});
 svg.push(`<path d="${pts.map((q,i)=>`${i?'L':'M'}${q.join(',')}`).join(' ')}${closed?' Z':''}" fill="${fill}" stroke="${col}" stroke-width="${lw}" stroke-linejoin="round" ${dash?'stroke-dasharray="11 7"':''}/>`);
}
function line(x1,y1,x2,y2,c=C.road,lw=2,d=false){route([[x1,y1],[x2,y2]],c,lw,d)}
function arrow(x1,y1,x2,y2,col=C.blue,lw=2.7,dash=false){
 const a=shape('ellipse',x1-.01,y1-.01,.02,.02),b=shape('ellipse',x2-.01,y2-.01,.02,.02);
 s.shapes.connect(a,b,{kind:'straight',fromSide:'right',toSide:'left',line:{fill:col,width:lw,style:dash?'dashed':'solid'},tail:{type:'triangle',width:'med',length:'med'}});
 svg.push(`<path d="M${x1},${y1} L${x2},${y2}" fill="none" stroke="${col}" stroke-width="${lw}" marker-end="url(#a${col.slice(1)})" ${dash?'stroke-dasharray="8 5"':''}/>`);
}
function dot(x,y,r,c=C.blue,fill='#FFFFFF',lw=2.5){shape('ellipse',x-r,y-r,r*2,r*2,fill,c,lw)}
function cross(x,y,r=15){line(x-r,y-r,x+r,y+r,'#FFFFFF',12);line(x-r,y+r,x+r,y-r,'#FFFFFF',12);line(x-r,y-r,x+r,y+r,C.red,7);line(x-r,y+r,x+r,y-r,C.red,7)}
async function img(id,x,y,w,h,fit='contain'){
 const meta=provenance.find(q=>q.name===id),buf=await fs.readFile(path.join(assets,id+'.png'));
 const [iw,ih]=meta.pixels;let ww=w,hh=h,xx=x,yy=y;
 if(fit==='contain'){let k=Math.min(w/iw,h/ih);ww=iw*k;hh=ih*k;xx+=(w-ww)/2;yy+=(h-hh)/2;}
 s.images.add({blob:buf,contentType:'image/png',alt:`Text-free ${id} illustration generated from user Figure 1 reference`,fit,position:{left:xx,top:yy,width:ww,height:hh}});
 svg.push(`<image x="${xx}" y="${yy}" width="${ww}" height="${hh}" href="data:image/png;base64,${buf.toString('base64')}"/>`);
 images.push({id,x:xx,y:yy,w:ww,h:hh,pixels:meta.pixels,effective_dpi_at_180mm:Math.min(iw/(ww/W*180/25.4),ih/(hh/W*180/25.4))});
}
// Four-panel frame and source-faithful typographic hierarchy.

const panels=[[9,476,'(a)  Problem context'],[494,426,'(b)  Manager architecture'],[929,505,'(c)  Experimental program'],[1443,388,'(d)  Main findings']];
for(const [x,w,title] of panels){shape('rect',x,85,w,1265,'#FFFFFF',C.border,1.5);text(title,x+20,96,w-34,58,34,true);}
// (a) Map background, editable route topology and every map label.
await img('map_base',24,167,446,895,'cover');
text('N',48,184,34,34,27,true);route([[61,225],[49,254],[61,245],[73,254]],'#24354B',2,false,'#55709A',true);
const D=[95,834],HH=[430,679];
const roads=[[[24,590],[81,607],[180,654],[318,680],HH],[[81,607],[57,712],D],[[57,712],[155,747],[229,763],[319,738],HH],[[155,747],[163,840],[177,902],[306,916],[431,906]],[[163,840],[309,850],[326,817]],[[319,738],[309,850],[306,916]],[[D[0],D[1]],[163,840]],[[318,680],[319,738]]];
for(const rr of roads)route(rr,C.road,4);
route([D,[136,791],[155,747],[203,758],[229,763],[277,754],[319,738],[368,717],[390,681],HH],C.ground,6);
route([D,[163,840],[177,902],[247,914],[306,916],[373,915],[431,906],[427,867],[405,806],[386,756],[385,697],HH],C.ground,4,true);
route([[112,548],[163,533],[223,545],[278,568],[313,595],[344,625]],C.air,4,true);
route([[181,389],[234,409],[305,425],[365,449],[404,477],[429,533],[436,593],HH],C.air,4,true);
route([[209,518],[266,533],[321,555],[358,591],[389,640],HH],C.red,4,true);
for(const q of [[81,607],[180,654],[318,680],[57,712],[155,747],[319,738],[163,840],[309,850],[326,817],[306,916],[431,906]])dot(...q,7,'#283653');
dot(...D,13,C.ground,'#C7E3F4',4);cross(229,763,15);
shape('rect',207,699,46,32,C.red,C.red,1);text('B1',207,699,46,32,25,true,'#FFFFFF','center');
for(const [x,y,t] of [[112,548,'V1'],[344,625,'V2'],[404,477,'V3']]){dot(x,y,16,'#B87229','#F5AE45',2.4);text('V',x-14,y-14,28,28,25,true,'#FFFFFF','center');text(t,x-23,y+20,48,31,25,true,C.ink,'center');}
await img('existing_air',143,349,70,58);text('Existing\nservice',233,345,130,57,27,true,'#B77730');
await img('emergency_air',177,477,70,58);text('Emergency\nmission',257,471,140,63,27,true,C.red);
await img('logistics',42,834,40,64);text('D1',89,852,54,35,27,true);
await img('hospital',407,654,48,48);text('H1',411,707,54,35,27,true);
text('Not to scale',57,1015,367,42,28,false,'#5D646A','center');
// Compact two-column reference legend, all labels editable.
shape('rect',24,1075,446,256,'#FFFFFF',C.border,1.4);line(270,1091,270,1315,'#C8CDD2',1.2);
for(const [yy,label,c,d] of [[1107,'Road network',C.road,false],[1143,'Baseline route',C.ground,false],[1179,'Detour route',C.ground,true],[1215,'Low-altitude route',C.air,true]]){line(43,yy,91,yy,c,4,d);text(label,108,yy-18,160,35,label.startsWith('Low-')?20.5:24);}
text('(eVTOL/UAV)',108,1233,160,31,22);cross(68,1285,12);text('Disrupted link',108,1268,160,35,24);
text('D1',286,1090,44,32,25,true);text('Logistics',336,1090,117,32,24);text('H1',286,1128,44,32,25,true);text('Hospital',336,1128,117,32,24);
dot(308,1184,16,'#B87229','#F5AE45',2);text('V',294,1170,28,28,25,true,'#FFFFFF','center');text('Vertiport',336,1167,117,34,24);
await img('existing_air',285,1220,44,34);text('Existing',336,1218,117,35,24);
await img('emergency_air',285,1268,44,34);text('Emergency',336,1266,127,35,24);
// (b) Native sequence and feedback channels, with independent image assets.
const mods=[['state','Global state',187],['generator','Candidate\ngenerator',348],['interface','Executable\ninterface',509],['policy','Supervisor\npolicy',680],['safety','Safety &\nfeasibility',894],['executor','Executor',1070]];
for(let i=0;i<mods.length;i++){
 const [id,label,y]=mods[i];shape('rect',624,y,260,i===3?183:103,i===3?'#EEF0F5':'#FFFFFF',C.border,1.7);
 if(id==='interface'){
 shape('rect',540,y-13,344,149,'#FFFFFF',C.border,1.7);
 text('Candidate interface',549,y-9,325,31,25,true,C.ink,'center');
 const xs=[550,630,711,796],widths=[76,76,78,76];
 ['Mode','ETA s','Margin','Loss'].forEach((v,k)=>text(v,xs[k],y+27,widths[k],25,20,true,C.ink,'center'));
 [['Gnd','228.6','+71.4','0'],['Air','212.8','+87.2','1']].forEach((row,j)=>row.forEach((v,k)=>text(v,xs[k],y+55+j*28,widths[k],25,20,false,C.ink,'center')));
 text('Both legal; air preempts M-L-002',543,y+108,338,26,18.5,false,C.ink,'center');
 }else {await img(id,549,y-20,159,i===3?120:144);text(label,({state:732,generator:734.4,safety:745,executor:749})[id]??720,y+(({state:14,generator:19.4,safety:15,executor:15.5})[id]??13),({safety:122.6,executor:122.2})[id]??157,77,29,i===3);}
 if(i<mods.length-1)arrow(733,y+(i===3?193:i===2?145:111),733,mods[i+1][2]-10,C.blue,3);
}
shape('rect',527,1235,358,94,'#F5F7FC',C.border,1.7);await img('simulators',537,1244,116,46);text('SUMO + BlueSky',661,1245,218,39,27);arrow(733,1184,733,1225,C.blue,3);


line(902,242,902,1282,C.air,2.3,true);arrow(902,242,885,242,C.air,2.3,true);line(885,1282,902,1282,C.air,2.3,true);shape('rect',800,1002,109,32,'#FFFFFF');text('Feedback',803,1002,104,32,22,false,'#AE6C32','center');
text('B0 Ground    B1 Rule',637,786,240,28,20,true,C.ink,'center');text('B2 Heuristic  B4b LLM',632,812,246,28,20,true,C.ink,'center');
text('B4a: interface ablation',630,839,251,27,19,false,'#68707A','center');
text('Independent local contingency',535,1295,346,26,20,true,C.purple,'center');
// (c) Scenario pictures are independent, labels and grid are native.
text('Scenarios',948,169,253,38,30,true);line(946,210,1415,210,C.border,1.2,true);line(1180,226,1180,850,C.border,1.2,true);line(946,534,1415,534,C.border,1.2,true);
const scenario=[['E1','Selective\nair support','e1',951,233,C.blue],['E2','Air-layer\nreconfiguration','e2',1194,233,C.blue],['E3','Compound\ndisturbance','e3',951,555,C.green],['E4','Observation /\nexecution /\ninput burden','e4',1194,555,C.air]];
for(const [badge,label,id,x,y,c] of scenario){shape('rect',x,y,58,42,c,'#41536B',1.3);text(badge,x,y,58,42,30,false,'#FFFFFF','center');text(label,x+66,y-3,170,79,id==='e4'?22:25);await img(id==='e3'?'site_a':id,x-4,y+76,222,218);if(id==='e3'){cross(x+43,y+109,13);cross(x+171,y+153,13);}}
line(946,870,1415,870,C.border,1.3);text('Study sites',948,884,400,43,31,true);line(946,933,1415,933,C.border,1.2,true);
const sites=[['A','Urban (meshed)','site_a','Dense network\nRoute choices'],['B','River (barrier)','site_b','River crossing\nLimited links'],['C','Suburban (sparse)','site_c','Sparse network\nLonger trips']];
for(let i=0;i<3;i++){let x=947+157*i;const [a,lab,id,desc]=sites[i];text('Site '+a,x,946,151,36,29,true,C.ink,'center');text(lab.replace(' (','\n('),x-2,985,154,65,26,false,C.ink,'center');await img(id,x+3,1060,145,169);text(desc,x+3,1237,148,64,23,false,C.ink,'center');if(i<2)line(x+154,948,x+154,1314,C.border,1.1,true);}
// (d) Conceptual finding graphics follow the reference. No plotted measurements.
const dx=1460,dw=352,starts=[180,493,822,1138],findings=['Coordination helps','Timely recovery matters','Interface shapes choices','Delay changes outcomes'];
line(dx,167,dx+dw,167,C.border,1.3);
for(let i=0;i<4;i++){dot(dx+28,starts[i]+28,28,[C.blue,C.air,C.purple,C.green][i],[C.blue,C.air,C.purple,C.green][i],1);text(String(i+1),dx+1,starts[i]+1,54,54,43,true,'#FFFFFF','center');text(findings[i],dx+71,starts[i]-2,dw-71,62,25.5,true);}
line(dx,475,dx+dw,475,C.border,1.3);line(dx,802,dx+dw,802,C.border,1.3);line(dx,1115,dx+dw,1115,C.border,1.3);
line(1476,405,1798,405,'#606B78',2);
[[1508,350,31,55,'#C5C9D1'],[1550,326,31,79,'#BBC0C9'],[1658,344,31,61,'#A7C0E0'],[1701,321,31,84,'#709ACD'],[1744,280,31,125,'#5C8FC7']].forEach(([x,y,w,h,c])=>shape('rect',x,y,w,h,c,'#526179',1.8));
route([[1609,331],[1650,319],[1686,299],[1712,277],[1728,257],[1737,281],[1725,278],[1702,306],[1664,324],[1625,333]],'#425978',1.7,false,'#7D9EC8',true);
text('Uncoordinated',1471,414,158,35,25,false,C.ink,'center');text('Coordinated',1646,414,150,35,25,false,C.ink,'center');
// Explicit deadline timeline, qualitative (no invented travel-time values).
line(1485,643,1790,643,C.ink,2);
line(1680,593,1680,757,C.red,2.2,true);text('Deadline',1630,566,150,34,25,true,C.red,'center');
line(1490,675,1640,675,C.ground,5);dot(1640,675,8,C.ground,C.ground,1);
line(1490,731,1777,731,'#898B94',4,true);dot(1777,731,8,'#898B94','#898B94',1);
text('Timely',1483,682,159,33,25,false,C.ground);text('Late',1703,747,89,32,25,false,'#747883');
text('Completion',1501,609,153,32,24);text('Time',1744,605,70,32,24);
await img('balance_large',1496,897,289,187);text('Air',1481,1071,128,32,26,false,C.ink,'center');text('Ground',1674,1071,130,32,26,false,C.ink,'center');
await img('delay_large',1474,1211,327,100);text('Observation / execution delay',1473,1305,330,32,25,false,C.ink,'center');
s.speakerNotes.textFrame.setText('Figure 1. Overview of the Ground-Low-Altitude Mobility Manager. Hybrid reference reconstruction: all words, labels and numbers are native editable PowerPoint text; complex text-free illustrations are separately embedded AI-generated assets. Reference: user-provided Gemini figure, supplied 12 September 2026. Individual illustrations and clean map base generated with built-in imagegen for this composition. The map is Not to scale. Candidate data: E1_H_H_high, seed20240601, t=300; air preemption interrupts one NORMAL incumbent. B1 on the map denotes a disrupted link, distinct from policy B1. E1–E3 use A/B/C, E4 uses A. B4a is only an E1 interface ablation. Four primary policies share modeled facts and execution constraints; B2 is a fixed-preference structured comparator. Main findings are conceptual, not quantitative charts. Candidate-interface effects are strongest at Site A. Scientific claims follow paper_final_20260910. The revised manuscript documents an identical pending-command correction.');
const draft=path.join(here,name+'.candidate.pptx');await(await PresentationFile.exportPptx(p)).save(draft);
const png=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(path.join(here,name+'.artifact.png'),new Uint8Array(await png.arrayBuffer()));
await fs.writeFile(path.join(here,name+'.inventory.json'),JSON.stringify({W,H,panels,texts,images,objects},null,2));
const defs=Object.values(C).map(c=>`<marker id="a${c.slice(1)}" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,3.5 L0,7z" fill="${c}"/></marker>`).join('');
await fs.writeFile(path.join(out,name+'.svg'),`<svg xmlns="http://www.w3.org/2000/svg" width="180mm" height="135mm" viewBox="0 0 ${W} ${H}"><title>Overview of the Ground-Low-Altitude Mobility Manager</title><desc>Hybrid illustration with all labels retained as editable text; maps and finding symbols are schematic.</desc><defs>${defs}</defs><rect width="${W}" height="${H}" fill="white"/>${svg.join('\n')}</svg>`);
await finalizePresentation({workspaceDir:work,candidatePath:draft,finalPath:path.join(out,name+'.pptx'),pythonExecutable:PY,integrityValidatorPath:path.join(SK,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SK,'container_tools/inspect_presentation_layout_geometry.py'),explicitTotalSlideCount:1,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:['Times New Roman']},layoutArgs:['--expected-slide-size-emu',`${W*9525},${H*9525}`,'--validate-heading-fit'],verifyArtifactToolImport:true,receiptPath:path.join(work,'.figure1-qa',name+'.'+Date.now()+'.validation.json')});
console.log(JSON.stringify({name,editable_texts:texts.length,independent_images:images.length,min_dpi:Math.min(...images.map(i=>i.effective_dpi_at_180mm))}));

