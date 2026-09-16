from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import pymupdf as fitz,json,re
O=Path(__file__).resolve().parent;W=O.parents[1];ov=W/'overleaf';qa=O/'qa';qa.mkdir(exist_ok=True)
report={}
for i in range(1,9):
 p=ov/'figures'/f'fig{i:02d}.pdf';doc=fitz.open(p);page=doc[0]
 spans=[s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans'] if s['text'].strip()]
 fonts=sorted(set(s['font'] for s in spans));bad=[s for s in spans if 'TimesNewRoman' not in s['font'].replace('-','') and 'TimesNewRoman' not in s['font']]
 assert not bad,(i,[(s['text'],s['font']) for s in bad])
 report[f'fig{i:02d}']={'fonts':fonts,'minimum_pt_at_180mm':min(s['size'] for s in spans)}
 if i==3:
  boxes=[]
  for d in page.get_drawings():
   for item in d['items']:
    if item[0]=='re':
     r=item[1]
     if 110<r.width<140 and 140<r.height<180:boxes.append(tuple(r))
  boxes=sorted(set(tuple(round(v,2) for v in r) for r in boxes))
  report['bar_axes_rectangles']=boxes
  if len(boxes)==3:
   widths=[r[2]-r[0] for r in boxes];heights=[r[3]-r[1] for r in boxes];gaps=[boxes[j+1][0]-boxes[j][2] for j in range(2)]
   assert max(widths)-min(widths)<1.5 and max(heights)-min(heights)<1.5 and abs(gaps[0]-gaps[1])<1.5
   report['bar_alignment']={'widths':widths,'heights':heights,'gutters':gaps,'passed':True}
for stem in ['main','supplement']:
 doc=fitz.open(ov/f'{stem}_revised.pdf');report[stem+'_pages']=len(doc);pages=[]
 for n,p in enumerate(doc):
  text=p.get_text()
  if re.search(r'Figure\s+(?:S?[1-6])[.:]',text):
   p.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(qa/f'{stem}_{n+1:02d}.png');pages.append(n+1)
 report[stem+'_figure_pages']=pages
with ZipFile(O/'output/Figures2_to_8_Times_ready.pptx') as z:
 counts=[]
 for n in z.namelist():
  if re.search(r'/charts/chart\d+\.xml$',n):
   e=E.fromstring(z.read(n));counts.append((n,len(e.xpath('//*[local-name()="errBars"]'))))
 assert sum(c for _,c in counts)==12,counts
 report['errorbar_series']=counts
 ns={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
 contract=json.loads((O/'bar_contract.json').read_text())
 max_error=0
 for j in range(3):
  e=E.fromstring(z.read(f'ppt/charts/chart{j+1}.xml'))
  for k,ser in enumerate(e.findall('.//c:barChart/c:ser',ns)):
   actual=[float(v) for v in ser.xpath('c:val//c:pt/c:v/text()',namespaces=ns)]
   plus=[float(v) for v in ser.xpath('c:errBars/c:plus//c:pt/c:v/text()',namespaces=ns)]
   minus=[float(v) for v in ser.xpath('c:errBars/c:minus//c:pt/c:v/text()',namespaces=ns)]
   assert len(actual)==len(plus)==len(minus)==3
   for q,r in enumerate(contract[j]['series'][k]['values']):
    max_error=max(max_error,abs(actual[q]-r['mean']),abs(plus[q]-(r['hi']-r['mean'])),abs(minus[q]-(r['mean']-r['lo'])))
 assert max_error<5.1e-9,max_error
 report['figure3_max_excel_rounding_error']=max_error
(qa/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
