import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const O=path.dirname(fileURLToPath(import.meta.url));
const MOD='C:/Users/xuan1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(MOD,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const SK='C:/Users/xuan1/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const {applyPresentationChartFont}=await import(pathToFileURL(path.join(SK,'container_tools/artifact_tool_utils.mjs')));
const input=await fs.access(path.join(O,'figure_data.json')).then(()=>path.join(O,'figure_data.json')).catch(()=>path.join(O,'../figure_redesign/figure_data.json'));
const D=JSON.parse(await fs.readFile(input,'utf8'));
const p=Presentation.create({slideSize:{width:1280,height:720}}),s=p.slides.add();s.background.fill='#FFFFFF';
const policies=['B0','B1','B2','B4b'],sites=['A','B','C'],colors=['#2878B5','#F28E2B','#20A387','#9B4BD1'];
const font='Times New Roman';
function text(t,x,y,w,h=36,size=28,bold=false){const o=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});o.text=t;o.text.style={typeface:font,fontSize:size,bold,color:'#151515',autoFit:'none',wrap:'none',insets:{left:0,right:0,top:0,bottom:0},verticalAlignment:'middle'};}
const specs=[['critical_mission_completion_time_s','Completion time','Time (s)',360,120,1],['critical_mission_deadline_violation','Missed deadlines','Runs (%)',100,25,100],['existing_missions_damaged_count','Incumbent damage','Damaged services / run',.6,.2,1]];
const contract=[];
for(let j=0;j<3;j++){
 const [metric,title,unit,max,step,scale]=specs[j],l=30+j*417;
 text(String.fromCharCode(97+j),l,23,32,40,31,true);text(title,l+40,23,350,40,29,true);text(unit,l+40,78,352,36,26);
 const series=policies.map((policy,k)=>({name:policy,values:sites.map(site=>Number((D.results.E1[site].summary[policy][metric].mean*scale).toFixed(8))),fill:colors[k],line:{fill:'#343434',width:.65}}));
 const chart=s.charts.add('bar',{position:{left:l-10,top:123,width:406,height:487},categories:sites.map(x=>'Site '+x),series,barOptions:{direction:'column',grouping:'clustered',gapWidth:80,overlap:0,varyColors:false},hasLegend:false,chartFill:'#FFFFFF',chartLine:{fill:'none',width:0},plotAreaFill:'#FFFFFF',plotAreaLine:{fill:'#303030',width:1.2},xAxis:{textStyle:{typeface:font,fontSize:27},line:{fill:'#303030',width:1.2}},yAxis:{min:0,max,majorUnit:step,numberFormatCode:max<1?'0.0':'0',textStyle:{typeface:font,fontSize:26},majorGridlines:{fill:'#E2E2E2',width:.65},line:{fill:'#303030',width:1.2}},dataLabels:{showValue:false}});
 applyPresentationChartFont(chart,{fontFamily:font});
 contract.push({metric,scale,series:policies.map(policy=>({policy,values:sites.map(site=>{const r=D.results.E1[site].summary[policy][metric];return {site,mean:r.mean*scale,lo:r.ci95[0]*scale,hi:r.ci95[1]*scale}})}))});
}
policies.forEach((v,i)=>{const x=335+i*163;s.shapes.add({geometry:'rect',position:{left:x,top:655,width:26,height:20},fill:colors[i],line:{fill:'#343434',width:.65}});text(v,x+38,644,110,40,28);});
s.speakerNotes.textFrame.setText('Figure 3. E1 selective air support and incumbent cost. Every site–policy mean and existing 95% seed-block interval is retained: 240 runs and 20 seed blocks per site–policy. Bars start at zero. Source: figure_data.json, results.E1. Error bars are custom asymmetric intervals.');
await fs.mkdir(path.join(O,'output'),{recursive:true});
await (await PresentationFile.exportPptx(p)).save(path.join(O,'bar.candidate.pptx'));
await fs.writeFile(path.join(O,'bar_contract.json'),JSON.stringify(contract,null,2));
console.log('Native clustered bars authored with unchanged means.');
