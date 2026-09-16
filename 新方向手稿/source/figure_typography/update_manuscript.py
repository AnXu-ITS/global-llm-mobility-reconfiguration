from pathlib import Path
import re
W=Path(__file__).resolve().parents[2];ov=W/'overleaf'
main=(ov/'main.tex').read_text(encoding='utf-8');sup=(ov/'supplement.tex').read_text(encoding='utf-8')
old=(W/'archive/figures_before_reference_redesign/main.tex').read_text(encoding='utf-8')
def block(text,num):
 return next(m.group() for m in re.finditer(r'\\begin\{figure\}.*?\\end\{figure\}',text,re.S) if f'fig{num:02d}.pdf' in m.group())
main=main.replace(block(main,4),block(old,4))
newcap=r'\caption{E1 service benefit and incumbent cost. Clustered bars show site--policy mean completion time, missed deadlines and incumbent services damaged at the horizon. Whiskers are 95\% seed-block intervals (240 runs, 20 seed blocks per site and policy). All bars start at zero; zero-width intervals have coincident caps. Colors identify policies consistently across the result figures. Supplementary Table S1 retains exact values.}'
b=block(main,3);main=main.replace(b,re.sub(r'\\caption\{.*?\}\n\\label',lambda m:newcap+'\n\\label',b,flags=re.S))
moved=[]
for num,lab in [(5,'sfig:e2'),(8,'sfig:queue')]:
 b=block(main,num);main=main.replace(b+'\n','');b=re.sub(r'\\label\{[^}]+\}',lambda m:'\\label{'+lab+'}',b)
 moved.append(b)
for num in [1,2,3,4,6,7]:
 main=re.sub(r'\bFigure '+str(num)+r'\b',lambda m:'Figure~\\ref{fig:fig'+f'{num:02d}'+'}',main)
 # Numeric panel references have no word boundary before a/b/c.
 main=re.sub(r'\bFigure '+str(num)+r'([abc])',lambda m:'Figure~\\ref{fig:fig'+f'{num:02d}'+'}'+m[1],main)
main=main.replace('Figure 5','Supplementary Figure S1').replace('Figure 8','Supplementary Figure S2')
sup=sup.replace(r'\usepackage{amsmath,',r'\usepackage{graphicx,amsmath,')
sup=sup.replace(r'\renewcommand{\thetable}{S\arabic{table}}',r'\renewcommand{\thetable}{S\arabic{table}}'+'\n'+r'\renewcommand{\thefigure}{S\arabic{figure}}')
sup=sup.replace('Table S5 and Figures 7--8','Table S5, main Figure 6 and Supplementary Figure S2')
oldprod=next(x for x in sup.splitlines() if x.startswith('Figures 2--8 retain'))
newprod='All figure text uses Times New Roman. Main Figure 3 uses native clustered-column charts with the existing seed-block intervals. Main Figure 4 restores the candidate-geometry, preemption-choice and deadline-outcome layout. Main Figure 5 contains editable vector heatmaps and contrasts; main Figure 6 and Supplementary Figure S1 use native charts with embedded workbooks. Supplementary Figure S2 retains editable pending-command and transport segments. The two PowerPoint files retain their source slide order; the editing guide maps slides to current main and supplementary figure numbers.'
sup=sup.replace(oldprod,newprod)
suppfigs='\n\\clearpage\n\\section{Supporting transport outcomes and command sequence}\n\n'+moved[0]+'\n\n\\clearpage\n'+moved[1]+'\n\n'
sup=sup.replace(r'\end{document}',suppfigs+r'\end{document}')
(ov/'main.tex').write_text(main,encoding='utf-8');(ov/'supplement.tex').write_text(sup,encoding='utf-8')
print('Six main figures; E2 outcome summary and queue example moved to Supplementary Figures S1–S2.')
