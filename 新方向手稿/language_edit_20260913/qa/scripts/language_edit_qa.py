from pathlib import Path
import subprocess, re, json, shutil, hashlib, os, difflib
import pymupdf as fitz
from PIL import Image,ImageOps,ImageDraw
ROOT=Path(__file__).resolve().parents[4]
SRC=ROOT/'新方向手稿'/'overleaf'
OUT=ROOT/'新方向手稿'/'language_edit_20260913'
PKG=OUT/'overleaf'
QA=OUT/'qa'
QA.mkdir(exist_ok=True)
BASE=QA/'baseline'
BASE.mkdir(exist_ok=True)
def run(args,cwd):
    p=subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if p.returncode: raise RuntimeError(p.stdout.decode(errors='replace')[-3500:])
    return p.stdout.decode(errors='replace')
def build(cwd,job,inputname,outdir=None,bbl=None):
    dest=outdir or cwd
    if bbl: shutil.copy2(bbl,dest/(job+'.bbl'))
    args=['pdflatex','-interaction=nonstopmode','-halt-on-error','-jobname='+job]
    if outdir: args+=['-output-directory='+str(outdir)]
    args+=[inputname]
    run(args,cwd);run(args,cwd)
    return dest/(job+'.pdf')
def clean(t):
    t=re.sub(r'Compiled September \d+, 2026','Compiled DATE',t)
    return re.sub(r'\s+','',t)
report={}
for name in ['main','supplement']:
    sourcepdf=SRC/(name+'_revised.pdf')
    basepdf=build(SRC,name+'_source_check',name+'.tex',BASE,SRC/'main_revised.bbl' if name=='main' else None)
    a,b=fitz.open(sourcepdf),fitz.open(basepdf)
    aa='\n'.join(p.get_text() for p in a); bb='\n'.join(p.get_text() for p in b)
    (QA/(name+'_source_pdf.txt')).write_text(aa,encoding='utf8')
    same=clean(aa)==clean(bb)
    report[name]={'source_pages':len(a),'source_tex_rebuild_pages':len(b),'source_pdf_matches_tex_rebuild_except_compile_date_whitespace':same}
    if not same:
        (QA/(name+'_source_comparison.diff')).write_text(''.join(difflib.unified_diff(aa.splitlines(True),bb.splitlines(True))),encoding='utf8')
    edited=build(PKG,name+'_edited',name+'.tex',None,SRC/'main_revised.bbl' if name=='main' else None)
    shutil.copy2(edited,OUT/edited.name)
    d=fitz.open(edited)
    report[name]['edited_pages']=len(d)
    (QA/(name+'_edited_pdf.txt')).write_text('\n'.join(p.get_text() for p in d),encoding='utf8')
    log=(PKG/(name+'_edited.log')).read_text(errors='replace')
    report[name]['latex_warnings']=[line for line in log.splitlines() if 'Warning' in line or 'Overfull' in line]
    pages=[]
    for i,p in enumerate(d):
        pix=p.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
        im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
        im.save(QA/(name+f'_page_{i+1:02}.png'))
        im.thumbnail((297,425))
        tile=Image.new('RGB',(317,459),'#e9edf2'); tile.paste(im,((317-im.width)//2,24))
        ImageDraw.Draw(tile).text((12,5),name+' '+str(i+1),fill='black')
        pages.append(tile)
    for batch in range(0,len(pages),12):
        subset=pages[batch:batch+12]
        sheet=Image.new('RGB',(317*4,459*((len(subset)+3)//4)),'white')
        for j,im in enumerate(subset):sheet.paste(im,((j%4)*317,(j//4)*459))
        sheet.save(QA/(name+f'_contact_{batch//12+1}.png'))
    # Source page landmarks for editorial queries.
    needles=['Horizons are','Identical differences','candidate presentation','300 s slack','242 s','900 s horizons','main Figure 6','Main Figure 5','Main Figure 6','342 s','Ground completion','Scope and next steps']
    report[name]['source_query_pages']={needle:[i+1 for i,p in enumerate(a) if needle in p.get_text()] for needle in needles}
(QA/'build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))
