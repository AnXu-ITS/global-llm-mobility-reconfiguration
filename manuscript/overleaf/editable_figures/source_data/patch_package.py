from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
import sys,json,re,io
O=Path(__file__).resolve().parent
A='http://schemas.openxmlformats.org/drawingml/2006/main';C='http://schemas.openxmlformats.org/drawingml/2006/chart';ns={'a':A,'c':C}
palette={'7B858E':'2878B5','D78A3A':'F28E2B','477F60':'20A387','7954A3':'9B4BD1','808080':'2878B5','ED7D31':'F28E2B','70AD47':'20A387','7030A0':'9B4BD1'}
def el(p,ns,n,**kw):return E.SubElement(p,'{'+ns+'}'+n,**kw)
def xml_patch(data,colors=False):
 root=E.fromstring(data)
 for x in root.xpath('//*[@typeface]'):x.set('typeface','Times New Roman')
 for x in root.xpath('//*[local-name()="rPr" or local-name()="defRPr" or local-name()="endParaRPr"]'):
  for tag in ['latin','ea','cs']:
   f=x.find('{'+A+'}'+tag)
   if f is None:f=el(x,A,tag)
   f.set('typeface','Times New Roman')
 if colors:
  for x in root.findall('.//a:srgbClr',ns):
   v=x.get('val','').upper()
   if v in palette:x.set('val',palette[v])
 return root
p=Path(sys.argv[1]);mode=sys.argv[2] if len(sys.argv)>2 else 'fonts'
with ZipFile(p) as z:entries=[(i,z.read(i.filename)) for i in z.infolist()]
count=0
with ZipFile(p.with_suffix('.patched.pptx'),'w',ZIP_DEFLATED) as z:
 for info,data in entries:
  n=info.filename
  if n.endswith('.xml'):
   root=xml_patch(data,mode!='fonts')
   if n=='ppt/slides/slide3.xml' and mode=='polish':
    for shape in root.xpath('//*[local-name()="sp"]'):
     if ''.join(shape.xpath('.//a:t/text()',namespaces=ns))=='Air selection (%) when air requires preemption':
      shape.find('.//a:xfrm/a:off',ns).set('y','1390650')
   if '/charts/' in n and mode!='fonts':
    for ser in root.findall('.//c:scatterChart/c:ser',ns):
     name=''.join(ser.xpath('c:tx//c:v/text()',namespaces=ns))
     if name=='B4b':
      line=ser.find('c:spPr/a:ln',ns)
      if line is not None:
       for old in line.findall('a:prstDash',ns):line.remove(old)
       el(line,A,'prstDash',val='dash')
    for ser in root.findall('.//c:barChart/c:ser',ns):
     name=''.join(ser.xpath('c:tx//c:v/text()',namespaces=ns))
     if name=='On time':
      for color in ser.xpath('./c:spPr/a:solidFill/a:srgbClr | ./c:dPt/c:spPr/a:solidFill/a:srgbClr',namespaces=ns):color.set('val','44B3E1')
   if mode=='bar' and re.fullmatch(r'ppt/(?:slides/)?charts/chart\d+.xml',n):
    j=int(re.search(r'(\d+)\.xml',n)[1])-1;spec=json.loads((O/'bar_contract.json').read_text())[j]
    area=root.find('.//c:plotArea',ns)
    for old in area.findall('c:layout',ns):area.remove(old)
    layout=E.Element('{'+C+'}layout');area.insert(0,layout);ml=el(layout,C,'manualLayout');el(ml,C,'layoutTarget',val='inner')
    for k,v in [('xMode','edge'),('yMode','edge'),('wMode','factor'),('hMode','factor'),('x','.19'),('y','.06'),('w','.76'),('h','.82')]:el(ml,C,k,val=v)
    for k,ser in enumerate(root.findall('.//c:barChart/c:ser',ns)):
     err=E.Element('{'+C+'}errBars');el(err,C,'errDir',val='y');el(err,C,'errBarType',val='both');el(err,C,'errValType',val='cust');el(err,C,'noEndCap',val='0')
     for key in ['plus','minus']:
      nl=el(el(err,C,key),C,'numLit');el(nl,C,'formatCode').text='General';el(nl,C,'ptCount',val='3')
      for q,r in enumerate(spec['series'][k]['values']):el(el(nl,C,'pt',idx=str(q)),C,'v').text=str(round(max(0,r['hi']-r['mean'] if key=='plus' else r['mean']-r['lo']),8))
     sp=el(err,C,'spPr');line=el(sp,A,'ln',w='12700');el(el(line,A,'solidFill'),A,'srgbClr',val='222222')
     cat=ser.find('c:cat',ns);ser.insert(list(ser).index(cat),err);count+=1
   data=E.tostring(root,encoding='UTF-8',xml_declaration=True)
  elif n.endswith('.xlsx'):
   src=io.BytesIO(data);dst=io.BytesIO()
   with ZipFile(src) as zi,ZipFile(dst,'w',ZIP_DEFLATED) as zo:
    for item in zi.infolist():
     b=zi.read(item.filename)
     if item.filename=='xl/styles.xml':
      rr=E.fromstring(b)
      for f in rr.xpath('//*[local-name()="font"]/*[local-name()="name"]'):f.set('val','Times New Roman')
      b=E.tostring(rr,encoding='UTF-8',xml_declaration=True)
     zo.writestr(item,b)
   data=dst.getvalue()
  z.writestr(info,data)
p.with_suffix('.patched.pptx').replace(p)
print('Patched',p.name,'custom error-bar series:',count)
