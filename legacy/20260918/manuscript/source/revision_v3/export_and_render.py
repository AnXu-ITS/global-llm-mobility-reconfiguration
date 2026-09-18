from pathlib import Path
import pymupdf,shutil,json
from PIL import Image,ImageDraw
W=Path(__file__).resolve().parents[2];O=W/'source/revision_v3';ov=W/'overleaf'
def export_figures():
    for pdf,indices in [('figure1_native_r3.pdf',[(0,1)]),('figures_native_r2.pdf',[(i,i+2) for i in range(7)])]:
        d=pymupdf.open(O/pdf)
        for idx,num in indices:
            p=d[idx];w=180/25.4*72;h=w*p.rect.height/p.rect.width
            new=pymupdf.open();page=new.new_page(width=w,height=h);page.show_pdf_page(page.rect,d,idx)
            dest=ov/f'figures/fig{num:02d}.pdf';new.save(dest,garbage=4,deflate=True)
            shutil.copy2(dest,W/f'figures_revised/fig{num:02d}.pdf')
    for src,name in [(W/'figure1/Figure1_revised_r3.pptx','Figure1_revised.pptx'),(W/'figures_revised/MANUSCRIPT_FIGURES_2_to_8_revised_r2.pptx','Figures2_to_8_revised.pptx')]:shutil.copy2(src,ov/'editable_figures'/name)
def render():
    out=O/'qa';out.mkdir(exist_ok=True)
    for stem in ['main_revised','supplement_revised']:
        d=pymupdf.open(ov/(stem+'.pdf'));tiles=[]
        for i,p in enumerate(d):
            pix=p.get_pixmap(dpi=110,alpha=False);pix.save(out/f'{stem}_{i+1:02d}.png')
            im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);im.thumbnail((306,434))
            tile=Image.new('RGB',(326,464),'#E9EDF1');tile.paste(im,((326-im.width)//2,22));ImageDraw.Draw(tile).text((9,5),str(i+1),fill='black');tiles.append(tile)
        for start in range(0,len(tiles),12):
            subset=tiles[start:start+12];sheet=Image.new('RGB',(1304,464*((len(subset)+3)//4)),'#D5DAE0')
            for j,tile in enumerate(subset):sheet.paste(tile,((j%4)*326,(j//4)*464))
            sheet.save(out/f'{stem}_contact{start//12+1}.png')
        print(stem,len(d))
if __name__=='__main__':
    import sys
    export_figures() if '--figures' in sys.argv else render()
