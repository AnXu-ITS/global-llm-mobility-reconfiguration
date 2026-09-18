from pathlib import Path
W=Path(__file__).resolve().parents[2]
s=(W/'source/build_figures_v2.mjs').read_text(encoding='utf-8')
s=s.replace("out=path.join(work,'figures_v2')","out=path.join(work,'figures_revised')")
s=s.replace("path.join(root,'outputs/paper_final/results.json')","path.join(work,'source/revision_v3/results_revised.json')")
s=s.replace("'MANUSCRIPT_FIGURES_2_to_8_v2.pptx'","'MANUSCRIPT_FIGURES_2_to_8_revised.pptx'")
s=s.replace("figures_v2_candidate.pptx","figures_v3_candidate.pptx")
s=s.replace("Source: paper_final_20260910; figures use frozen reported data.","Source: revision_v3/results_revised.json and decision_regimes.json.")
s=s.replace("function foot(s,t){txt(s,t,44,675,1192,32,17,false,'#52616D');}","function foot(s,t){ /* Detailed notes are retained in the caption and speaker notes. */ }")
s=s.replace("68,23,17,true","78,27,21,true").replace("36,24,16,true","42,28,20,true").replace("100,25,17)","100,28,21)").replace("205,30,18)","205,34,20)")
s=s.replace("B1 Rule","B1 Air-first").replace("B2 Heuristic","B2 Heuristic")
s=s.replace("E1: emergency transport and existing-service consequences","E1: selective air support and incumbent-service cost")
start=s.index("// 4.");end=s.index("// 5.",start)
s=s[:start]+r'''// 4. Log-derived supervisory decision regimes; all primary first states retained.
{
const regimes=JSON.parse(await fs.readFile(path.join(work,'source/revision_v3/decision_regimes.json'),'utf8'));
const counts=JSON.parse(await fs.readFile(path.join(work,'source/revision_v3/regime_summary.json'),'utf8'));
const s=base('fig04_candidate_ablation','Supervisory decision regimes','E1 first-decision logs. 720 matched scenario-seed states; subsequent trajectories may diverge. Candidate ETA is predictive, not actual completion.');
txt(s,'(a) Candidate geometry at Site A',45,111,570,42,25,true);
const x=110,y=214,w=486,h=355,fx=v=>x+(v+160)/260*w,fy=v=>y+h-(v+70)/330*h;
line(s,x,y+h,x+w,y+h,C.ink,1.4);line(s,x,y,x,y+h,C.ink,1.4);
[-150,-100,-50,0,50,100].forEach(v=>{line(s,fx(v),y+h,fx(v),y+h+6,C.ink);txt(s,String(v),fx(v)-28,y+h+9,56,28,19,false,C.ink,'center')});
[-50,0,100,200].forEach(v=>{line(s,x-6,fy(v),x,fy(v),C.ink);txt(s,String(v),x-62,fy(v)-14,48,28,19,false,C.ink,'right')});
line(s,fx(0),y,fx(0),y+h,'#A9B5BD',1);line(s,x,fy(0),x+w,fy(0),'#A9B5BD',1);
txt(s,'Best deadline margin (s)',49,161,545,35,21);
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
'''+s[end:]
s=s.replace("// 8. D60 event sequence, true simulation times.","// 8. Revised D60 event sequence, true simulation times.")
start=s.index("// 8.");end=s.index("await fs.mkdir(out",start)
s=s[:start]+r'''// 8. Pending versus executed transport, including corrected B0.
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
'''+s[end:]
s=s.replace("foot(s,'20 runs per arm and policy. B2/B4b overlap in (a,b). Panel (c) expands records around a fixed four-aircraft fleet.');","txt(s,'B2 = B4b (all arms)',95,635,342,31,21,true);txt(s,'B1 = B2 = B4b (0–30 s)',480,635,377,31,21,true);txt(s,'B2 = B4b (60 s)',502,669,325,30,21);")
# Keep source/marker normalization and embedded workbook finalization unchanged.
s=s.replace('fx=v=>x+(v+160)/260*w','fx=v=>x+(v+160)/310*w').replace('[-150,-100,-50,0,50,100]','[-150,-100,-50,0,50,100,150]')
s=s.replace("txt(s,'Best deadline margin (s)',49,161,545,35,21);","txt(s,'Margin (s)',43,191,183,26,19);")
(W/'source/build_figures_v3.mjs').write_text(s,encoding='utf-8')

s=(W/'figure1/.build/build_hybrid_figure1.mjs').read_text(encoding='utf-8')
s=s.replace("'Figure1_vC_hybrid_reference'","'Figure1_revised'")
start=s.index("shape('rect',32,1006");end=s.index('// Compact two-column',start)
s=s[:start]+"text('Not to scale',57,1015,367,42,28,false,'#5D646A','center');\n"+s[end:]
s=s.replace("await img(id,549,y-20,159,i===3?120:144);text(label,720,y+13,157,77,29,i===3);",r'''if(id==='interface'){
 shape('rect',540,y-13,344,136,'#FFFFFF',C.border,1.7);
 text('Candidate interface',549,y-9,325,31,25,true,C.ink,'center');
 const xs=[550,630,711,796],widths=[76,76,78,76];
 ['Mode','ETA s','Margin','Loss'].forEach((v,k)=>text(v,xs[k],y+27,widths[k],25,20,true,C.ink,'center'));
 [['Gnd','228.6','+71.4','0'],['Air','212.8','+87.2','1']].forEach((row,j)=>row.forEach((v,k)=>text(v,xs[k],y+55+j*28,widths[k],25,20,false,C.ink,'center')));
 text('Both legal; air preempts M-L-002',543,y+111,338,26,18.5,false,C.ink,'center');
 }else {await img(id,549,y-20,159,i===3?120:144);text(label,720,y+13,157,77,29,i===3);}''')
s=s.replace("line(902,283,902,1117,C.air,2.3,true);arrow(902,283,885,283,C.air,2.3,true);arrow(885,1117,902,1117,C.air,2.3,true);shape('rect',801,1002,109,32,'#FFFFFF');text('Feedback',805,1002,103,32,22,false,'#AE6C32','center');","line(902,242,902,1282,C.air,2.3,true);arrow(902,242,885,242,C.air,2.3,true);line(885,1282,902,1282,C.air,2.3,true);shape('rect',800,1002,109,32,'#FFFFFF');text('Feedback',803,1002,104,32,22,false,'#AE6C32','center');")
s=s.replace("text('Control input',751,1188,146,32,22,false,C.green,'right');","text('Independent local contingency',531,1196,365,28,22,true,C.purple,'center');")
s=s.replace("'Air support\\ndisruption'","'Selective\\nair support'").replace("'Observation\\nsensitivity'","'Observation /\\nexecution /\\ninput burden'")
s=s.replace("text(label,x+70,y-3,160,66,25)","text(label,x+66,y-3,170,79,id==='e4'?22:25)")
start=s.index('const curve=');end=s.index("await img('balance_large'",start)
s=s[:start]+r'''// Explicit deadline timeline, qualitative (no invented travel-time values).
line(1485,643,1790,643,C.ink,2);
line(1680,593,1680,757,C.red,2.2,true);text('Deadline',1630,566,150,34,25,true,C.red,'center');
line(1490,675,1640,675,C.ground,5);dot(1640,675,8,C.ground,C.ground,1);
line(1490,731,1777,731,'#898B94',4,true);dot(1777,731,8,'#898B94','#898B94',1);
text('Timely',1483,682,159,33,25,false,C.ground);text('Late',1703,747,89,32,25,false,'#747883');
text('Completion',1501,609,153,32,24);text('Time',1744,605,70,32,24);
'''+s[end:]
s=s.replace('The map and its scale are schematic.','The map is Not to scale. Candidate data: E1_H_H_high, seed20240601, t=300; air preemption interrupts one NORMAL incumbent.').replace('No experiment or policy was changed.','The revised manuscript documents an identical pending-command correction.')
s=s.replace("line(529,407,529,797,C.purple,2.4,true);arrow(529,407,557,407,C.purple,2.4,true);arrow(529,797,557,797,C.purple,2.4,true);",'')
s=s.replace("shape('rect',496,583,78,82,'#FFFFFF');text('Shared\\ndata',497,589,77,68,24,false,C.purple,'center');",'')
s=s.replace("344,136,'#FFFFFF'","344,149,'#FFFFFF'").replace("y+111,338,26","y+108,338,26")
s=s.replace("y+(i===3?193:111)","y+(i===3?193:i===2?145:111)")
s=s.replace("text('Independent local contingency',531,1196,365,28,22,true,C.purple,'center');","text('Independent local contingency',535,1295,346,26,20,true,C.purple,'center');")
s=s.replace("text('SUMO + BlueSky',661,1250,218,57,27)","text('SUMO + BlueSky',661,1245,218,39,27)")
s=s.replace("await img(id,x-4,y+76,222,218);","await img(id==='e3'?'site_a':id,x-4,y+76,222,218);if(id==='e3'){cross(x+43,y+109,13);cross(x+171,y+153,13);}")
s=s.replace("text('Figure 1. Overview of the Ground-Low-Altitude Mobility Manager',56,5,1728,60,40,true,C.ink,'center');",'')
s=s.replace("text(label,720,y+13,157,77,29,i===3);", "text(label,({state:732,generator:734.4,safety:745,executor:749})[id]??720,y+(({state:14,generator:19.4,safety:15,executor:15.5})[id]??13),({safety:122.6,executor:122.2})[id]??157,77,29,i===3);")
s=s.replace("537,1244,116,75", "537,1244,116,46")
(W/'figure1/.build/build_figure1_revised.mjs').write_text(s,encoding='utf-8')
print('Prepared editable revised figure builders')
