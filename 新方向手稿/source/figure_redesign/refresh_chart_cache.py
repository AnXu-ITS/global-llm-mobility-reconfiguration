from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from openpyxl import load_workbook
import io,posixpath,re,sys
p=Path(sys.argv[1]);ns={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
with ZipFile(p) as z:
 entries=[(i,z.read(i.filename)) for i in z.infolist()];fixed={};count=0
 for n in z.namelist():
  if '/charts/chart' not in n or not n.endswith('.xml'):continue
  root=E.fromstring(z.read(n));rels=posixpath.dirname(n)+'/_rels/'+posixpath.basename(n)+'.rels';r=E.fromstring(z.read(rels));t=[x.get('Target') for x in r if x.get('Type').endswith('/package')][0]
  wb=load_workbook(io.BytesIO(z.read(posixpath.normpath(posixpath.join(posixpath.dirname(n),t)))),data_only=True)
  for nr in root.findall('.//c:numRef',ns):
   formula=nr.find('c:f',ns).text;mat=re.match(r"'?([^']+?)'?!(\$?[A-Z]+\$?\d+):(\$?[A-Z]+\$?\d+)",formula)
   if not mat:continue
   sheet,lo,hi=mat.groups();data=[v.value for row in wb[sheet][lo.replace('$',''):hi.replace('$','')] for v in row]
   for pt in nr.findall('c:numCache/c:pt',ns):
    value=pt.find('c:v',ns);target=str(data[int(pt.get('idx'))])
    if value.text!=target:value.text=target;count+=1
  fixed[n]=E.tostring(root,encoding='UTF-8',xml_declaration=True)
with ZipFile(p.with_suffix('.cache.pptx'),'w',ZIP_DEFLATED) as z:
 for info,b in entries:z.writestr(info,fixed.get(info.filename,b))
p.with_suffix('.cache.pptx').replace(p)
print('Refreshed cache values from the existing workbook:',count)
