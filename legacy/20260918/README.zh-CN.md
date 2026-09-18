# 地面–低空移动系统在中断场景下的服务重构管理器

[English](README.md) · [中文说明](README.zh-CN.md)

论文 *"A Ground–Low-Altitude Mobility Manager for Service Reconfiguration under
Disruptions"* 的参考实现。**候选生成器**把地面–空中联合观测转化为共享的**可执行候选接口**；
可替换的**监督策略**（启发式或 LLM）选择干预动作；**执行器**检查并落地该动作，而本地的
飞行器应急程序独立运行。四个 SUMO–BlueSky 实验在**三个差异化的交通场景**上评估。

---

## 1. 概览

- **三个研究场地**（均为 3.2 km × 3.2 km，OpenStreetMap）：
  - **A** —— 中国苏州（网状城市）
  - **B** —— 荷兰阿姆斯特丹
  - **C** —— 加拿大埃德蒙顿
- **联合仿真** —— SUMO 1.27.1（地面）+ BlueSky（空中），步长 1 s，时长 900 s。
- **核心机队** —— 2 架医疗无人机 + 1 架物流无人机 + 1 架载人 eVTOL（共 4 架）。
- **LLM** —— OpenAI 兼容的 chat-completions 接口（默认 `corp-ai/openai/deepseek-v4-pro`）；
  客户端仅用标准库（`managers/llm_client.py`），密钥取自 `CORP_AI_API_KEY` 或
  `~/.dsh/.credentials.yaml`。

### 监督策略（不同运行之间唯一改变的东西）

| ID | 策略 | 含义 |
|---|---|---|
| `B0` | 仅地面 | 基线：不调度空中资源 |
| `B1` | 规则 | 手写规则，只排序空中候选 |
| `B2` | 固定目标启发式 | 单步打分，在速度与保护在途服务间权衡 |
| `B4a` | LLM（无候选信息） | 消融：LLM 缺少派生的候选信息段 |
| `B4b` | LLM（带候选信息） | 主方法：LLM 带显式候选信息支持 |

### 实验

| 编号 | 问题 | 覆盖 |
|---|---|---|
| E1 | 选择性空中支援（基线与协调策略对比） | 3 场地 |
| E2 | 空中失效（F1–F6 六类故障） | 3 场地 |
| E3 | 复合扰动（L1–L4 层级） | 3 场地 |
| E4 | 观测–执行时序（4A 刷新 · 4B 延迟 · 4C 规模） | 场地 A |

**E4 各臂** —— 4A 观测间隔 `OBS10/30/60/120/300` · 4B 执行延迟 `D00/01/05/10/20/30/60` ·
4C 机队记录规模 `N05/10/20/30/50`（核心机队固定为 4）。

---

## 2. 目录结构

```
├── orchestrator/   实验运行器、SUMO/BlueSky 适配器、注册表、机队
├── managers/       B0/B1/B2/B4a/B4b 策略 + LLM 客户端
├── safety/         可行性检查器 + 语义校验器（策略无关的闸门）
├── config/         场景 + 实验矩阵（3 场地）+ LLM（phase3_config.yaml）
├── prompts/        LLM 提示词模板（manager_v1/v2）
├── schemas/        动作校验的 JSON schema
├── failures/       E2 故障注入模型（F1–F6）
├── state/          全局状态模型
├── sim/            site_a/b/c 的 SUMO 路网/路径 + BlueSky 输入
├── tests/          独立验收测试（无需 pytest）
├── tools/          run_experiment{1..4}[_cross_site].py + analyze_*.py
├── docs/           设计文档
└── manuscript/     论文 + 复现管线（见下）
```

`manuscript/` 包含论文权威源码及其复现管线：

```
manuscript/
├── overleaf/               主文 main.tex、补充 supplement.tex、references.bib、期刊类文件
│   ├── figures/            PDF 图件
│   ├── editable_figures/   PowerPoint 图件底稿
│   └── reproducibility/    论文冻结复现包（配置、提示词、schema、派生数据、哈希清单、queue_fix.py）
├── source/revision_v3/     分析脚本 + 派生数据 + 回归运行
├── figure1/                Figure 1 构建器与素材
├── reproduce_analysis.ps1  后处理/复现入口
└── REPRODUCTION_README.md  完整复现说明（见第 6 节）
```

运行产物（`runs/`、`outputs/`）与 `archive/` 均为 **git 忽略**（体积大、可重生成；
`archive/` 还存放已淘汰的规划文档与评审）。

---

## 3. 环境要求

- **Python 3.14**（建议虚拟环境）
- **SUMO 1.27.1** —— 通过 `eclipse-sumo` pip 包安装（无需单独安装）
- **BlueSky** —— *源码检出*（非 pip 包）；见「环境配置」
- Python 依赖见 [`requirements.txt`](requirements.txt)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   POSIX: source .venv/bin/activate
pip install -r requirements.txt
```

---

## 4. 环境配置

### 4.1 SUMO

`eclipse-sumo` 已列在 `requirements.txt`。运行时 `orchestrator/sumo_env.py` 导入 `sumo`
来定位 `SUMO_HOME` 并把 `traci`/`sumolib` 加进路径。

### 4.2 BlueSky

BlueSky 是**从源码**导入的（`orchestrator/bluesky_adapter.py`）：

```bash
git clone https://github.com/TUDelft-CNS-ATM/bluesky.git
```

通过 `BLUESKY_REPO` 指向它：

```bash
# Windows (PowerShell)                    # POSIX
$env:BLUESKY_REPO = "C:\...\bluesky"      export BLUESKY_REPO=/path/to/bluesky
```

### 4.3 LLM 接口

编辑 [`config/phase3_config.yaml`](config/phase3_config.yaml) 的 `llm:` 块：

```yaml
llm:
  model: corp-ai/openai/deepseek-v4-pro
  base_url: http://<你的主机>:<端口>/v1
  api_key_env: CORP_AI_API_KEY
  max_tokens: 8192
```

再设置密钥（`CORP_AI_API_KEY`，或 `~/.dsh/.credentials.yaml`）。代码读取的环境变量见
[`.env.example`](.env.example)。

---

## 5. 快速开始

```bash
# 单次进程内运行（E4 4B、D10 臂、LLM 策略、种子 20240601）
python tools/run_experiment4.py --sub 4B --arm D10 --manager B4b \
    --seed 20240601 --scenario E4_ANCHOR --cohort primary --direct

# E4 完整扫描（并行 worker）
python tools/run_experiment4.py --sub 4A --manager all --jobs 8

# 跨场地实验（3 场地 A/B/C）
python tools/run_experiment1_cross_site.py --help
python tools/run_experiment2_cross_site.py --help
python tools/run_experiment3_cross_site.py --help

# 分析
python tools/analyze_experiment4.py primary
```

运行写入 `runs/<experiment>/<cohort>/...`；`--force` 可重跑已有运行。
`tests/` 为独立脚本（无需 pytest）：`python tests/test_experiment4_acceptance.py`。

---

## 6. 复现论文

1. 安装环境（第 3 节）并配置 SUMO / BlueSky / LLM（第 4 节）。
2. 用 `tools/run_*.py` 跑框架扫描（第 5 节）。
3. 按 [`manuscript/REPRODUCTION_README.md`](manuscript/REPRODUCTION_README.md) 与
   `manuscript/reproduce_analysis.ps1` 从保存的运行产物与冻结的
   `manuscript/overleaf/reproducibility/` 包复现数值分析与图件。后处理不调用 LLM；
   `-RunRegression` 追加论文声明的确定性回归运行（需要 SUMO/traci）。

机器相关的设置只有 LLM 接口地址与 BlueSky 路径两处。
