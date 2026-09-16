from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
import sys,copy
p=Path(sys.argv[1]);C='http://schemas.openxmlformats.org/drawingml/2006/chart';A='http://schemas.openxmlformats.org/drawingml/2006/main';ns={'c':C,'a':A}
def sub(p,sp,n,**kw):return E.SubElement(p,'{'+sp+'}'+n,**kw)
with ZipFile(p) as z:entries=[(i,z.read(i.filename)) for i in z.infolist()]
with ZipFile(p.with_suffix('.fixed.pptx'),'w',ZIP_DEFLATED) as z:
 for info,data in entries:
  if '/charts/chart' in info.filename and info.filename.endswith('.xml'):
   root=E.fromstring(data)
   for ch in root.findall('.//c:scatterChart',ns):
    for v in ch.findall('c:varyColors',ns):ch.remove(v)
    ch.insert(1,E.Element('{'+C+'}varyColors',val='0'))
    for ser in ch.findall('c:ser',ns):
     name=''.join(ser.xpath('c:tx//c:v/text()',namespaces=ns));col=ser.find('c:spPr/a:ln/a:solidFill/a:srgbClr',ns)
     if col is None:col=ser.find('c:spPr/a:solidFill/a:srgbClr',ns)
     for old in ser.findall('c:smooth',ns):ser.remove(old)
     sub(ser,C,'smooth',val='0')
     marker=ser.find('c:marker',ns)
     if marker is not None and col is not None:
      color=col.get('val');fill='FFFFFF' if name=='B2' else color
      for old in marker.findall('c:spPr',ns):marker.remove(old)
      sp=sub(marker,C,'spPr');sub(sub(sp,A,'solidFill'),A,'srgbClr',val=fill);sub(sub(sub(sp,A,'ln',w='12700'),A,'solidFill'),A,'srgbClr',val=color)
      for dp in ser.findall('c:dPt',ns):
       for old in dp.findall('c:marker',ns):dp.remove(old)
       dp.insert(1,copy.deepcopy(marker))
   for ch in root.findall('.//c:barChart',ns):
    dl=ch.find('c:dLbls',ns)
    if dl is not None:dl.insert(0,E.Element('{'+C+'}numFmt',formatCode='0.00',sourceLinked='0'))
    for ser in ch.findall('c:ser',ns):
     nums=ser.xpath('c:val//c:pt',namespaces=ns)
     zeros=[int(pt.get('idx')) for pt in nums if float(pt.find('c:v',ns).text)==0]
     if zeros:
      sd=ser.find('c:dLbls',ns)
      if sd is None:
       sd=copy.deepcopy(dl);ser.append(sd)
      for idx in zeros:
       lab=E.Element('{'+C+'}dLbl');sd.insert(0,lab);sub(lab,C,'idx',val=str(idx));sub(lab,C,'delete',val='1')
   area=root.find('.//c:plotArea',ns)
   if area is not None:
    for old in area.findall('c:layout',ns):area.remove(old)
    layout=E.Element('{'+C+'}layout');area.insert(0,layout);manual=sub(layout,C,'manualLayout');sub(manual,C,'layoutTarget',val='inner')
    for name in ('xMode','yMode'):sub(manual,C,name,val='edge')
    for name in ('wMode','hMode'):sub(manual,C,name,val='factor')
    is_scatter=area.find('c:scatterChart',ns) is not None
    for name,v in zip(('x','y','w','h'),(.26,.055,.72,.73) if is_scatter else (.20,.055,.78,.75)):sub(manual,C,name,val=str(v))
   data=E.tostring(root,encoding='UTF-8',xml_declaration=True)
  z.writestr(info,data)
p.with_suffix('.fixed.pptx').replace(p)
print('Explicit chart precision, marker colors, straight joins and zero-label handling applied.')
