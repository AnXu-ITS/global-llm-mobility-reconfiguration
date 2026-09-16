import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const require=createRequire('C:/Users/xuan1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/_entry.cjs');
const sharp=require('sharp');
const here=path.dirname(fileURLToPath(import.meta.url)), assets=path.join(path.dirname(here),'hybrid_assets');
await fs.mkdir(assets,{recursive:true});
const gen='C:/Users/xuan1/.codex/generated_images/01a0912c-5c72-7f53-97b4-8370d1ea0062';
const defs=[['illustrations', 'exec-bdff5bff-dbec-41fd-960b-a121d26884bd.png',4,['state','generator','interface','policy','safety','executor','e1','e2','e3','e4','site_a','site_b','site_c','balance','delay','simulators']],['symbols','exec-04ce22b1-3023-4547-bfe9-76599ad7270a.png',2,['existing_air','emergency_air','logistics','hospital']]];
const record=[];
defs.push(['finding_details','exec-99cd75bc-50da-47cc-a0e0-0aaa334569f6.png',2,['balance_large','delay_large'],1]);
for(const [sheet,file,n,names,rows=n] of defs){
 const src=path.join(gen,file); await fs.copyFile(src,path.join(assets,sheet+'_sheet.png'));
 const meta=await sharp(src).metadata();
 for(let k=0;k<names.length;k++){
  const left=Math.round((k%n)*meta.width/n),top=Math.round(Math.floor(k/n)*meta.height/rows),right=Math.round((k%n+1)*meta.width/n),bottom=Math.round((Math.floor(k/n)+1)*meta.height/rows);
  const extract={left,top,width:right-left,height:bottom-top};
  const filename=names[k]+'.png';
  const extracted=await sharp(src).extract(extract).png().toBuffer();
  const tile=await sharp(extracted).trim({background:'#FFFFFF',threshold:22}).extend({top:3,bottom:3,left:3,right:3,background:'#FFFFFF'}).png().toBuffer();
  // User-authorized composition: isolate the white sheet background from the three overlay icons.
  // The artwork is generated; no semantic object is redrawn or painted here.
  if(['existing_air','emergency_air','logistics'].includes(names[k])){
   const {data,info}=await sharp(tile).ensureAlpha().raw().toBuffer({resolveWithObject:true});
   for(let q=0;q<data.length;q+=4){const lo=Math.min(data[q],data[q+1],data[q+2]);data[q+3]=Math.round(255*Math.max(0,Math.min(1,(250-lo)/25)));}
   await sharp(data,{raw:info}).png().toFile(path.join(assets,filename));
  }else await fs.writeFile(path.join(assets,filename),tile);
  const m=await sharp(path.join(assets,filename)).metadata();record.push({name:names[k],path:filename,producer:'builtin-imagegen',source:file,source_pixels:[meta.width,meta.height],cell:extract,pixels:[m.width,m.height],text:'none (warning exclamation is an illustrative symbol)'});
 }
}
await fs.copyFile(path.join(gen,'exec-97c91b95-e079-4bc1-ad10-f03aaf825d1d.png'),path.join(assets,'map_base.png'));
const m=await sharp(path.join(assets,'map_base.png')).metadata();record.push({name:'map_base',path:'map_base.png',producer:'builtin-imagegen',source:'exec-97c91b95-e079-4bc1-ad10-f03aaf825d1d.png',pixels:[m.width,m.height],text:'none'});
await fs.writeFile(path.join(assets,'asset_provenance.json'),JSON.stringify(record,null,2));
console.log(JSON.stringify(record.map(r=>({name:r.name,pixels:r.pixels})),null,2));
