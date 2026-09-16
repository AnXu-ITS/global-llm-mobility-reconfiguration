from pathlib import Path
import sys
import pymupdf
repo=Path(__file__).resolve().parents[1]
staging=Path(sys.argv[1])
for file,expected,start in [('figure1.pdf',1,1),('figures2_to_8.pdf',7,2)]:
    with pymupdf.open(staging/file) as doc:
        if len(doc)!=expected:raise ValueError(f'{file}: expected {expected} slides, got {len(doc)}')
        for i,page in enumerate(doc):
            width=180/25.4*72
            out=pymupdf.open();target=out.new_page(width=width,height=width*page.rect.height/page.rect.width)
            target.show_pdf_page(target.rect,doc,i)
            out.save(staging/f'fig{start+i:02d}.pdf',garbage=4,deflate=True)
# The earlier deck remains the source only for S1 and S2. Never restore its
# superseded main figures over the current Python/SVG figure set.
for num in [1,5,8]:
    (repo/'figures'/f'fig{num:02d}.pdf').write_bytes((staging/f'fig{num:02d}.pdf').read_bytes())
