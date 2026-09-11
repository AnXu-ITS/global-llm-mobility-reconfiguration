import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const p=Presentation.create({slideSize:{width:1280,height:720}});
const s=p.slides.add();
s.background.fill='#FFFFFF';
const a=s.shapes.add({geometry:'rect',position:{left:80,top:80,width:480,height:100},fill:'#F2F5F7',line:{fill:'#334455',width:1}});
a.text='Ground–Low-Altitude Mobility Manager';
a.text.style={typeface:'Arial',fontSize:24,color:'#172B3A',alignment:'center',verticalAlignment:'middle',insets:{left:6,right:6,top:6,bottom:6}};
await(await PresentationFile.exportPptx(p)).save(fileURLToPath(new URL('./smoke.pptx',import.meta.url)));
for(const format of ['png','svg']){
try{const b=await p.export({slide:s,format,scale:1});await fs.writeFile(new URL('./smoke.'+format,import.meta.url),new Uint8Array(await b.arrayBuffer()));console.log(format,'ok');}catch(e){console.log(format,e.message)}
}
