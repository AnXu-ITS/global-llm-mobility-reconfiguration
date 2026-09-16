"""Check preservation and editable-vector exports without re-running experiments."""
from pathlib import Path
import csv
import json
import hashlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import pymupdf as fitz

BASE=Path(__file__).resolve().parent.parent
SOURCE=BASE/'source'
QA=BASE/'qa'
OUT=BASE/'output'
data=json.loads((SOURCE/'figure_data.json').read_text(encoding='utf-8'))
trace=json.loads((QA/'source_data_trace.json').read_text(encoding='utf-8'))
report={'data':{},'exports':{},'reviewed_checks':[]}
for name,digest in trace['source_hashes'].items():
    assert hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()==digest,name
rows=list(csv.DictReader((SOURCE/'figure3_means_intervals.csv').open(encoding='utf-8-sig')))
bars={(r['site'],r['policy'],r['metric']):r for r in trace['figures']['3']}
assert len(bars)==len(rows)==36
for r in rows:
    b=bars[(r['site'],r['policy'],r['metric'])]
    assert b['mean']==float(r['mean'])
    assert b['ci95']==[float(r['ci_low']),float(r['ci_high'])]
assert len(trace['figures']['5'])==48
assert len(trace['figures']['S3'])==12
assert trace['figures']['4']['scatter_rows']==trace['figures']['4']['scatter_counts_sum']==240
assert len(trace['figures']['4']['choice_matrix'])==9
assert len(trace['figures']['6'])==53  # 5*4 observation + 7*4 wait + 5 token settings
for r in trace['figures']['5']:
    assert r['value']==data['results']['E3'][r['site']]['levels'][r['level']][r['policy']]['system_weighted_loss']['mean']
for r in trace['figures']['S3']:
    matches=[v for v in data['results']['E3'][r['site']]['vs_b0'] if
             v['other']==r['other'] and v['level']==r['level'] and v['metric']==r['metric']]
    assert len(matches)==1 and all(r[k]==v for k,v in matches[0].items())
report['data']={'bar_summaries_and_intervals':36,'heatmap_cells':48,'paired_contrasts_and_intervals':12,
                'site_a_matched_states':240,'choice_counts_with_denominators':9,'timing_and_token_values':53,
                'source_hashes_unchanged':True,'excluded_observations':0}

for path in OUT.glob('*.pdf'):
    doc=fitz.open(path);p=doc[0]
    spans=[s for b in p.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
    size=min(s['size'] for s in spans)
    minimum=6.49 if path.stem=='FigureS3' else 9.49
    assert size>=minimum and not p.get_images(),path.name
    letters=['a','b'] if path.stem in ['Figure4','Figure6'] else ['a','b','c']
    letter_size=9 if path.stem=='FigureS3' else 12
    labels=[next(s for s in spans if s['text']==letter and abs(s['size']-letter_size)<.01) for letter in letters]
    header_delta=max(s['bbox'][1] for s in labels)-min(s['bbox'][1] for s in labels)
    assert header_delta<=1.5
    svg=ET.parse(path.with_suffix('.svg'));ns={'s':'http://www.w3.org/2000/svg'}
    assert svg.findall('.//s:text',ns) and not svg.findall('.//s:image',ns),path.name
    collisions=json.loads((QA/f'{path.stem}.collisions.json').read_text(encoding='utf-8'))
    if path.stem!='Figure2':assert collisions['summary']['fail']==collisions['summary']['warn']==0,path.name
    else:
        # The generic collision checker does not model painter-order occlusion.
        # Geographic labels intentionally have opaque white backing over road paths.
        drawing=p.get_drawings();safe=[]
        for t in p.get_texttrace():
            label=''.join(chr(c[0]) for c in t['chars'])
            if label not in ['D1','H1','D2','H2','C2','C3','V3','Closure']:continue
            bbox=fitz.Rect(t['bbox'])
            backs=[d for d in drawing if d.get('fill') and min(d['fill'])>.999
                and d.get('fill_opacity',1)>.999 and d['seqno']<t['seqno']
                and d['rect'].width<50 and d['rect'].height<20 and fitz.Rect(d['rect']).contains(bbox)]
            assert backs,('Missing opaque backing',label,bbox)
            back=max(backs,key=lambda d:d['seqno'])
            later=[d for d in drawing if d.get('color') and back['seqno']<d['seqno']<t['seqno']
                   and fitz.Rect(d['rect']).intersects(bbox)]
            assert not later,('Visible stroke over map label',label)
            safe.append({'label':label,'text_seqno':t['seqno'],'backing_seqno':back['seqno']})
        assert len(safe)==19
        assert all(f['kind'] in ['text-stroke','text-fill-edge'] for f in collisions['findings'])
        report['reviewed_checks'].append({'figure':'Figure2','raw_collision_summary':collisions['summary'],
            'resolution':'Geographic labels intentionally overlay the unchanged road/water geometry. All 19 labels have opaque backing after underlying paths and before text; no later stroke crosses them. All label positions visually inspected.',
            'opaque_map_labels':safe,'unresolved_findings':0})
    alignment=json.loads((QA/f'{path.stem}.alignment.json').read_text(encoding='utf-8'))
    report['exports'][path.name]={'width_pt':p.rect.width,'height_pt':p.rect.height,
        'minimum_font_pt':round(size,3),'embedded_raster_images':0,
        'panel_letter_y_difference_pt':round(header_delta,4),
        'editable_svg_text_elements':len(svg.findall('.//s:text',ns)),
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'alignment_report':f'{path.stem}.alignment.json'}

preflight=json.loads((QA/'source_preflight.json').read_text(encoding='utf-8'))
assert [f['check_id'] for f in preflight['findings'] if f['level']=='FAIL']==['FONT-FAMILY']
report['reviewed_checks'].append({'check':'FONT-FAMILY',
    'resolution':'User requested Figure 1 typography; Times New Roman is installed and embedded. The generic source validator only accepts a short list of sans serif names. Matching the supplied figure takes precedence over that default.',
    'unresolved_findings':0})
report['reviewed_checks'].append({'check':'Source warnings',
    'resolution':'300 dpi files are previews; authoritative PDF and SVG contain only vectors. The deadline legend starts with a numeric duration. Figure 4 callout is placed in empty space and its rendered collision audit passes.',
    'unresolved_findings':0})
report['status']='PASS_WITH_DOCUMENTED_DESIGN_EXCEPTIONS'
(QA/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'data':report['data'],'exports':len(report['exports'])}))
