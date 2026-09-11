"""Check manuscript links, equations and native PPT chart values against frozen data."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

work = Path(__file__).resolve().parents[1]
root = work.parent
r = json.loads((root/'outputs/paper_final/results.json').read_text(encoding='utf-8'))
ns = {'c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
managers = ['B0','B1','B2','B4b']
sites = ['A','B','C']
expected = []
for metric,scale in [('critical_mission_completion_time_s',1),
                     ('critical_mission_deadline_violation',100),
                     ('existing_missions_damaged_count',1)]:
    expected.append([[r['E1'][s]['summary'][p][metric]['mean']*scale for s in sites] for p in managers])
expected.append([[100*r['E2'][s]['summary'][p]['critical_mission_deadline_violation']['mean'] for s in sites] for p in managers])
for s in sites:
    expected.append([[r['E3'][s]['levels'][l][p]['system_weighted_loss']['mean'] for l in ['L1','L2','L3','L4']] for p in managers])
for e in ['4A','4B']:
    expected.append([[a[p]['metrics']['critical_mission_completion_time_s']['mean'] for a in r['E4'][e]['arms'].values()] for p in managers])
expected.append([[a['B4b']['llm_reliability']['prompt_tokens_per_logged_call']/1000 for a in r['E4']['4C']['arms'].values()]])

with zipfile.ZipFile(work/'figures/MANUSCRIPT_FIGURES.pptx') as z:
    names = sorted([n for n in z.namelist() if re.search(r'/charts/chart\d+\.xml$',n)],
                   key=lambda n:int(re.search(r'(\d+)\.xml',n)[1]))
    assert len(names) == len(expected) == 10
    count = 0
    for name,values in zip(names,expected):
        t = ET.fromstring(z.read(name))
        series = t.findall('.//c:ser',ns)
        assert len(series) == len(values)
        for ser,ex in zip(series,values):
            val = ser.find('c:val',ns)
            if val is None:
                val = ser.find('c:yVal',ns)
            got = [float(a.text) for a in val.findall('.//c:pt/c:v',ns)]
            assert len(got)==len(ex), (name,got,ex)
            assert all(abs(a-b)<1e-8 for a,b in zip(got,ex)), (name,got,ex)
            count += len(got)
    slides = [n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
    pics = sum(z.read(n).count(b'<p:pic>') for n in slides)
    assert len(slides)==8 and pics==0
    worksheets = [n for n in z.namelist() if n.endswith('.xlsx')]
    assert len(worksheets)==10

md = (work/'FIRST_DRAFT_TRANSPORTMETRICA_B.md').read_text(encoding='utf-8')
for link in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',md):
    assert (work/link).exists()
assert sorted(map(int,re.findall(r'\\tag\{(\d+)\}',md)))==list(range(1,14))
assert md.count('$$')%2==0
assert not re.search(r'@@\w+@@|\bTODO\b|\bTBD\b',md)
for p in ['prompts/manager_v2.txt','config/experiment1_b2_weights.yaml']:
    assert hashlib.sha256((root/p).read_bytes()).hexdigest() in md
receipt = json.loads((work/'.build/MANUSCRIPT_FIGURES.pptx.validation.json').read_text(encoding='utf-8'))
assert receipt['finalSha256']==hashlib.sha256((work/'figures/MANUSCRIPT_FIGURES.pptx').read_bytes()).hexdigest()
report = {'native_chart_count':10,'validated_chart_values':count,
          'embedded_chart_workbooks':len(worksheets),'raster_picture_shapes':pics,
          'equations':13,'linked_previews':8,'final_pptx_hash_matches_receipt':True,
          'package_integrity':receipt['packageIntegrity']['status'],
          'layout_findings':receipt['presentationLayout']['finding_count']}
(work/'.build/final_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
