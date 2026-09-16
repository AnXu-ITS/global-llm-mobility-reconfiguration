from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json, re
W=Path(__file__).resolve().parents[2]
paths=[W/'overleaf/editable_figures/Figure1_revised.pptx',W/'archive/figures_before_times_revision/Figures2_to_8_revised.pptx',W/'overleaf/figures/MANUSCRIPT_FIGURES.pptx',W/'archive/figures_before_reference_redesign/editable_figures/Figures2_to_8_revised.pptx']
out=[]
for p in paths:
 with ZipFile(p) as z:
  slides=[]
  for n in sorted([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+.xml',n)],key=lambda n:int(re.search(r'(\d+)\.xml',n)[1])):
   e=E.fromstring(z.read(n));t=e.xpath('//*[local-name()="t"]/text()')
   slides.append({'part':n,'text':t,'fonts':sorted(set(e.xpath('//@typeface'))),'shapes':len(e.xpath('//*[local-name()="sp"]'))})
  out.append({'path':str(p.relative_to(W)),'bytes':p.stat().st_size,'slides':slides})
(Path(__file__).parent/'inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
for x in out:
 print(x['path'],x['bytes'])
 for s in x['slides']:print(s['part'],s['shapes'],s['fonts'],' / '.join(s['text'])[:330])
