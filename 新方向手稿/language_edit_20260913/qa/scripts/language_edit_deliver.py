from pathlib import Path
import re,json,zipfile,shutil,hashlib
ROOT=Path(__file__).resolve().parents[4]
SRC=ROOT/'新方向手稿'/'overleaf'
OUT=ROOT/'新方向手稿'/'language_edit_20260913'
PKG=OUT/'overleaf'
edits=json.loads((OUT/'paragraph_changes.json').read_text(encoding='utf8'))
def prose(t):
    t=re.sub(r'%[^\n]*','',t) if False else t
    t=re.sub(r'\\begin\{(?:table|figure|equation)\*?\}.*?\\end\{(?:table|figure|equation)\*?\}',' ',t,flags=re.S)
    t=re.sub(r'(?<!\\)\\\[.*?\\\]|(?<!\\)\$.*?(?<!\\)\$',' MATH ',t,flags=re.S)
    t=re.sub(r'\\(?:cite\w*|ref|label|nolinkurl|input)\{[^}]*\}',' ',t)
    t=re.sub(r'\\(?:sub)*section\*?\{[^}]*\}',' ',t)
    t=re.sub(r'\\[A-Za-z]+\*?',' ',t)
    return t
def count(t):return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*",prose(t)))
stats=[]
for n in ['main.tex','supplement.tex']:
    old=(SRC/n).read_text(encoding='utf8').split(r'\begin{document}',1)[1].split(r'\bibliographystyle',1)[0]
    new=(PKG/n).read_text(encoding='utf8').split(r'\begin{document}',1)[1].split(r'\bibliographystyle',1)[0]
    stats.append((n,count(old),count(new)))
before=(SRC/'main.tex').read_text(encoding='utf8');after=(PKG/'main.tex').read_text(encoding='utf8')
def res_sections(text):
    r=text.split(r'\section{Results}',1)[1].split(r'\section{Discussion}',1)[0]
    blocks=re.split(r'\\subsection\{([^}]+)\}',r)
    return {blocks[i]:count(blocks[i+1]) for i in range(1,len(blocks),2)}
ba,af=res_sections(before),res_sections(after)
stat_lines='\n'.join(f'| {n} | {a} | {b} | {b-a:+} |' for n,a,b in stats)
result_lines='\n'.join(f'| {k} | {ba[k]} | {af[k]} | {af[k]-ba[k]:+} |' for k in ba)
report=f'''# 英文可读性编辑说明

本次以 `新方向手稿/overleaf/main_revised.pdf`（25 页）和 `supplement_revised.pdf`（12 页）为内容依据。已用原 LaTeX 重编译核对：除编译日期与空白外，两份 PDF 的提取文字一致，因此在对应源文件中编辑并另存。原 PDF、源文件和研究数据均未覆盖。

## 交付与使用

- `main_edited.pdf`、`supplement_edited.pdf`：完整排版编辑稿。
- `paragraph_comparison.html`：逐段原文／编辑稿对照和中文编辑目的，供浏览器查看；保留 LaTeX 标记便于回写。
- `overleaf/` 与 `edited_overleaf.zip`：可继续编辑和编译的 LaTeX 稿件包。
- `main_changes.diff`、`supplement_changes.diff`：精确源文件差异。
- `preservation_checks.json`、`qa/build_report.json`：保真与编译记录。

正文修改 70 个原段落，补充材料修改 21 个原段落；其余段落、公式引导语、表格、图注和参考文献均已审阅，保留已有清楚表达。部分长段拆为两至三段，章节标题、顺序及材料归属未变。未执行下文任何移位建议。未新增文献、数据、例子或研究结论。

## 编辑重点

1. 摘要先交代受扰动服务如何失去按时完成的机会，再说明候选生成、策略选择、执行检查与独立应急；保留所有摘要数值。
2. 将 `service-preservation pressure` 等密集表述展开为原稿已有关系：地面仍可按时完成紧急任务，空中改派更快，却会中断既有服务。
3. 区分 B1 的空中优先规则、B2 的跨模式固定目标排名，以及 B4b 对显式候选信息的使用。未把共同可行性检查误写为某策略独有能力。
4. 结果先写比较、数据与适用条件；讨论解释结果对服务义务、观测安排、排队与实体转运意味着什么。
5. 压缩相邻重复说明，并保留有用的被动语态、对照结构和条件从句。35 词仅作复查提示；保留完整的技术定义和统计限定，不机械切句。

## 术语与主体

| 固定称呼 | 本次采用的含义及写法 |
|---|---|
| Ground--Low-Altitude Mobility Manager / Manager | 系统整体；正文首次完整定义后明确简称 Manager。摘要与独立补充标题仍给完整名称。 |
| supervisor / supervisory policy | 从可用信息中选择或提出一项干预；B0、B1、B2、B4b 标签保持不变。 |
| candidate generator | 从观测状态计算候选事实；不执行 B2 排名，也不加入其偏好权重。 |
| shared executable candidate interface / candidate interface | 候选事实的共同字段与动作语义；清楚指代后采用短称。 |
| executor | 规范化、检查、排队／发出及执行动作；不是选择策略的泛称。 |
| local contingency | 独立运行的航空器本地应急；不等待监督推理或命令队列。 |
| incumbent service | 已在提供的服务；preemption 指改派占用资源而中断该服务。 |
| incumbent-service damage | 原稿定义的期末服务状态计数；不改写为物理损坏或完整累计中断成本。 |
| path restoration / timely completion | 建立可执行替代路径／在截止期内完成运输；始终分开。 |
| ETA / remaining deadline margin | 保留估计性质及与实际轨迹可能不同的限定。 |
| explicit candidate-information support | B4a--B4b 的主要定义；包含派生事实和呈现，§5.2 的歧义措辞另列 Q3。 |

## 作者需确认的问题（未自行修正）

以下页码均指用户指定的原 PDF，而非重新分页的编辑稿。问题不是新的研究结论；在确认前，编辑稿保留原数值、规则与范围。

**Q1：E3 的 horizon 是否全部为 900 s？** 正文 §5.3、原第 14 页写 “Horizons are 900 or 1,200 s.”；补充 §S3.2、原第 8 页写全部 2,880 个 E3 registry 按 “their 900 s horizons” 检查。是否指同一 E3 版本和分析队列？如果部分运行用 1,200 s，需要作者说明审计按各运行实际 horizon 还是统一 900 s 截断。本次两处均保留。

**Q2：“Identical differences” 的统计含义是什么？** 正文 §5.5、原第 16 页先说 constant nonzero differences 用 signed-rank fallback，随后说 “Identical differences receive p=1.”。这里是否实际指各配对结果相等、差值全零？若指恒定非零差值，就与前句存在歧义。只有作者确认后，才宜将后句改为 “When all paired differences are zero, p=1.”；本次没有这样改写，也未重新计算检验。

**Q3：§5.2 的消融是否应统一称 information support？** 正文原第 13 页将 B4a versus B4b 写为 “explicit candidate presentation”，而 §2.4、§4.3 及补充 §S2.3 明确说明同时移除了派生事实和呈现。是否同意统一为 “explicit candidate-information support”？原段还以 “Two comparisons” 开头，随后另述第三类消融；它可能意在“两类主要比较加一项消融”，需确认该层次。本次保留整段，未自行统一研究范围。

**Q4：ground completion 的 “issue time” 与 “execution time” 是否同义？** 补充 Table S11、原第 6 页写 ground completion 将 ETA 加到 issue time；正文 §4.1 与 §4.5 将执行、发出、排队等阶段分开说明。对存在等待的 E4B，建议明确这里的 issue 是实际发出执行时刻，还是提案获准／入队时刻。当前未替换时间基准。

**Q5：“transport error” 是否指后端调用的通信错误？** 正文 §6.6.3、原第 22 页的 “transport error / transport-error calls” 与 backend outcomes、structured retries 并列。在交通论文中读者可能理解为运输任务故障。若原意是 API 通信错误，可在首次出现时使用 “backend communication error”，并保留现有错误与重试数量；本次保留原术语，避免猜测错误类型。

图号复核结果：正文中的主图实际依次为 Figures 1–6；文件名 `fig05.pdf` 和 `fig08.pdf` 分别用于补充图 S1、S2。补充材料所述 main Figures 5 和 6 与正文实际编号相符，未将文件名误当作图号，也未改号。

## 修订历史与审计材料：仅建议，不已执行

| 位置 | 原段的透明性信息 | 可考虑的移位／合并方式 | 主文仍应保留 |
|---|---|---|---|
| 正文 §6.6.2、§7.3；补充 §S4.1 | B0 重复命令修正、20 seeds 回归、D00/D30 与邻近故障时刻、归档与运行环境差异 | 将详细回归记录集中在 §S4.1；正文保留简短修正披露并指向该节。§7.3 的修正句可与 §6.6.2 合并。 | B0 修正后的 242 s、B4b 真正换命令的 302 s、两者机制不同及事件顺序边界。任何移位都不抹去原记录。 |
| 正文 §5.5；补充 §S3.1 | seed-block 替换旧独立运行推断、原 comparison families | 主文突出实际使用的估计对象、分块、检验、区间和多重校正；旧／新方案沿革可集中在 §S3.1 或已有 revision 文件。 | 固定面板权重、依赖处理、配对方式、非显著不等于等效。Q2 须先澄清。 |
| 正文 §5.6、Data and code availability；补充 §S6 | 本地包、原始运行保留、覆盖层、复现入口、尚无公开仓库 | 合并重复的包内容清单，由 availability 指向 §S6；§5.6 主要承担模型范围说明。 | 公开仓库尚未分配、原始记录保存及更正来源。 |
| 正文 §5.1；补充 §S4.3 | road density 的边界修正 | 主文保留计算定义和分母，旧例程问题与修正步骤集中在已存在的 §S4.3。 | 真实道路底图与模拟服务之分，不能单独识别形态因果效应。 |
| 补充 §S5 | AI 图示来源、作者后续编辑、字体、原生图表和 PPT 页序 | 保留 AI 来源与示意性质披露；可将纯字体／PPT 对象操作说明合并至已有图件编辑指南。 | AI 生成与非观测图像的明确说明，不删来源记录。 |

## 正文证据分配检查

| 结果 | 段落任务 | 本次处理 |
|---|---|---|
| E1 协调收益与抢占代价 | 核心发现 | 原位保留比较、例子、全部数值和置信区间；用具体动作说明取舍。 |
| B4a--B4b 与 first-decision logs | 信息支持、选择机制及场地异质性 | 原位保留；拆开跨站统计、策略选择、ETA 边界。 |
| E2 路径恢复但仍迟到 | 核心发现及分母限定 | 原位保留；条件恢复与 all-run deadline rates 明确区分。 |
| E3 分级损失与无收益条件 | 核心发现及结论边界 | 保留所有无收益／不显著比较，未挪入补充材料。 |
| 跨站形态 | 情境解释及非因果限定 | 保留共同变化因素与不可分离的因果效应。 |
| E4A/B | 观测、等待及替换机制 | 原位保留时间序列、对照与审计；仅拆分段落功能。 |
| E4C | 输入负担及固定机队边界 | 保留错误调用、重试、输入记录数与可用飞机数量的区别。 |

最短证据链仍为：可用空中支持改善按时服务 → 同一候选事实允许不同服务取舍 → 有替代路径也可能迟到 → 复合扰动的收益取决于仍能满足截止期的选项 → 观测和命令执行时间决定选定干预能否落实。首次定义、结果证明、讨论综合与结论提醒各自保留；相邻无新增信息的接口说明和消融端点重复报告已合并。

所有主要描述量、区间、p 值仍在原位置；补充中的完整检验族和敏感性表原样保留。没有把任何不利结果移出正文。

## 篇幅与核对

以下是同一脚本提取的近似英文正文词项数，排除主要表格、图、展示公式和参考文献；数学表达按占位词计算。用于比较编辑前后，不作为期刊正式字数。编辑目标是易读而非最大压缩，因此部分拆句增加了必要的主体与动作。

| 文档 | 原稿 | 编辑稿 | 变化 |
|---|---:|---:|---:|
{stat_lines}

| Results 小节 | 原稿 | 编辑稿 | 变化 |
|---|---:|---:|---:|
{result_lines}

机器核对通过：各修改段落数值词项一致；展示公式逐块一致；行内数学表达集合一致；全部表格主体、引用序列、章节标题、标签、图像引用均一致。图文件、引入的统计表与转运敏感性表、参考文献库未修改。还人工复查了主体、比较方向、条件分母、统计限定和假设范围。没有重跑交通实验，也没有将语言编辑当作独立科学复核。

两份编辑 PDF 已成功编译并逐页渲染检查。研究内容疑问按上表保留，未通过润色给出未经作者确认的答案。
'''
(OUT/'编辑说明与作者问题.md').write_text(report,encoding='utf8')
(OUT/'README.md').write_text('''# 英文可读性编辑稿

先阅读 main_edited.pdf 和 supplement_edited.pdf。编辑说明与作者问题.md 记录未解决含义、术语及未执行的移位建议。paragraph_comparison.html 提供逐段对照。

overleaf/ 是独立的稿件编译包，并非独立交通仿真复现包。研究数据、原始 PPT 和完整复现工作区保留在原项目。原件位于 ../overleaf/，未被本次覆盖。

在 overleaf/ 内运行 build.ps1 重新编译；不要用此编辑包覆盖原研究材料。编辑后的篇幅与分页以 PDF 为准，作者问题中的页码均对应原 PDF。
''',encoding='utf8')
(PKG/'README.md').write_text('''# Language-edited manuscript

Compile main.tex and supplement.tex with pdfLaTeX. Run build.ps1 for the output names main_edited.pdf and supplement_edited.pdf. References and all numeric tables and figure assets are preserved from the source manuscript. The supplied main_edited.bbl also allows compilation with the archived bibliography output.

This is a manuscript compilation package, not a standalone simulation release. See REPRODUCTION_README.md for the original local research package. Author queries and proposed (unapplied) relocations are in the parent folder. No sections were reordered.
''',encoding='utf8')
(PKG/'REPRODUCTION_README.md').write_text('''# Original research reproduction entry

The language edit retains the research package at its original location. In the shared workspace, see ../../overleaf/REPRODUCTION_README.md and ../../REPRODUCTION_README.md. The full experiment runners and raw logs remain in the parent research project. The editable figure sources remain in ../../overleaf/editable_figures/.

The local reproducibility/ files here are copied unchanged to support manuscript tables and document the original analysis. Their inherited inventory describes the original research artifacts, not this language-edited manuscript. This copy is not a standalone simulation package. No traffic simulation or LLM experiment was rerun for the language edit.
''',encoding='utf8')
(PKG/'build.ps1').write_text('''$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_edited main.tex
    if ($LASTEXITCODE -ne 0) { throw 'Main first pass failed' }
    bibtex main_edited
    if ($LASTEXITCODE -ne 0) { throw 'Bibliography failed' }
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_edited main.tex
    if ($LASTEXITCODE -ne 0) { throw 'Main second pass failed' }
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_edited main.tex
    if ($LASTEXITCODE -ne 0) { throw 'Main final pass failed' }
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=supplement_edited supplement.tex
    if ($LASTEXITCODE -ne 0) { throw 'Supplement first pass failed' }
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=supplement_edited supplement.tex
    if ($LASTEXITCODE -ne 0) { throw 'Supplement final pass failed' }
} finally { Pop-Location }
''',encoding='utf8')
with zipfile.ZipFile(OUT/'edited_overleaf.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in PKG.rglob('*'):
        if p.is_file() and p.suffix not in ['.aux','.log','.out','.blg']:
            z.write(p,p.relative_to(PKG))
pres=json.loads((OUT/'preservation_checks.json').read_text(encoding='utf8'))
assert all(hashlib.sha256((SRC/n).read_bytes()).hexdigest()==v for n,v in pres['original_sha256'].items())
for name in ['references.bib','reproducibility/statistical_tests.tex','reproducibility/transfer_sensitivity.tex']:
    assert (SRC/name).read_bytes()==(PKG/name).read_bytes(),name
assert all((SRC/p.relative_to(PKG)).read_bytes()==p.read_bytes() for p in (PKG/'figures').glob('*.pdf'))
print(json.dumps({'word_counts':stats,'results':{'before':ba,'after':af},'source_files_unchanged':True},ensure_ascii=False,indent=2))
