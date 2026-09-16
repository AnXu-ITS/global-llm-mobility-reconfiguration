# 地面–低空移动系统在中断场景下的全局 LLM 监督重构

[English](README.md) · [中文说明](README.zh-CN.md)

一个 LLM 作为**全局监督器**，在中断发生时对耦合的**地面–低空移动系统**（SUMO 路网 +
BlueSky 空域）进行重构。LLM 读取*全局状态快照*（地面车辆 + 飞行器 + 任务 + 设施），输出
结构化动作（`DISPATCH`、`REASSIGN`、`REROUTE` 等），再由与具体管理器无关的
**可行性检查器 + 执行器**把决策落到联合仿真中。本仓库包含论文所用的冻结测试床、
实验框架与分析工具。

---

## 1. 概览

- **测试床** `S0_3p2km_v1` —— 3.2 km × 3.2 km 的苏州标准区域
  （中心 `31.30377, 120.59981`），时长 1800 s，步长 1 s。
- **联合仿真** —— SUMO 1.27.1（地面）+ BlueSky（空中），锁步推进。
- **机队** —— `L-UAV-01`（物流）、`EVTOL-01`（载人转运）、`M-UAV-01`、`M-UAV-02`（医疗）。
  一个定时事件会关闭某条地面链路，迫使监督器重新规划。
- **LLM** —— OpenAI 兼容的 chat-completions 接口（默认 `corp-ai/openai/deepseek-v4-pro`）；
  客户端只依赖标准库（`managers/llm_client.py`），密钥取自 `CORP_AI_API_KEY` 或
  `~/.dsh/.credentials.yaml`。

### 实验序列

| 编号 | 研究问题 | 臂 |
|---|---|---|
| E1 | 基线与方法对比（管理器） | `B0/B1/B2/B4b` |
| E2 | 失效感知 | `F1…F6` |
| E3 | 全局状态设计 | — |
| **E4** | **LLM 运行极限** | `4A` 信息刷新频率 · `4B` 推理延迟 · `4C` 全局状态规模 |

**E4 各臂**

| 子实验 | 扫描参数 | 取值 |
|---|---|---|
| 4A | 观测间隔（s） | `OBS10, OBS30, OBS60, OBS120, OBS300` |
| 4B | 动作延迟（s） | `D00, D01, D05, D10, D20, D30, D60` |
| 4C | 机队规模（候选表规模） | `N05, N10, N20, N30, N50` |

**管理器**（不同运行之间唯一改变的东西）

| ID | 管理器 | 含义 |
|---|---|---|
| `B0` | `NoCrossLayerManager` | 仅地面基线（无空中调度） |
| `B1` | `RuleBasedManager` | 手写跨层规则 |
| `B2` | 加权规则 | 带调优权重的规则 |
| `B4b` | `LLMManager`（候选表） | LLM 监督器 |

---

## 2. 目录结构

```
├── orchestrator/   实验运行器、SUMO/BlueSky 适配器、注册表、机队
├── managers/       B0/B1/B2/B4b 管理器 + LLM 客户端
├── safety/         可行性检查器 + 语义校验器（与管理器无关的闸门）
├── config/         场景 + 实验矩阵 + LLM（phase3_config.yaml）
├── tools/          run_experiment{1..4}.py 调度器 + analyze_*.py
├── sim/            SUMO 路网/路径 + BlueSky 场景输入
├── tests/          独立验收测试（纯脚本，无需 pytest）
├── docs/           设计文档
├── prompts/        LLM 提示词模板
├── schemas/        LLM 动作校验的 JSON schema
├── failures/       失效注入模型（E2）
├── state/          全局状态模型
├── reports/        独立评审 / 审计
├── 新方向手稿/      论文工作区（论文 + 复现包）
└── archive/        历史版本与旧运行（git 忽略）
```

运行产物（`runs/`、`outputs/`）与 `archive/` 均被 **git 忽略**（体积大，可按需重新生成）。

---

## 3. 环境要求

- **Python 3.14**（建议使用虚拟环境）
- **SUMO 1.27.1** —— 通过 `eclipse-sumo` pip 包自动安装
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

`eclipse-sumo` 已列在 `requirements.txt` 中。运行时 `orchestrator/sumo_env.py`
导入 `sumo` 来定位 `SUMO_HOME` 并把 `traci`/`sumolib` 加进路径 —— 无需单独安装 SUMO。

### 4.2 BlueSky

BlueSky 是**从源码**导入的（进程内，`orchestrator/bluesky_adapter.py`）：

```bash
git clone https://github.com/TUDelft-CNS-ATM/bluesky.git
```

通过环境变量 `BLUESKY_REPO` 指向它：

```bash
# Windows (PowerShell)                    # POSIX
$env:BLUESKY_REPO = "C:\...\bluesky"      export BLUESKY_REPO=/path/to/bluesky
```

论文使用的历史检出为 commit `dfdff5d`。

### 4.3 LLM 接口

编辑 [`config/phase3_config.yaml`](config/phase3_config.yaml) 的 `llm:` 块：

```yaml
llm:
  model: corp-ai/openai/deepseek-v4-pro
  base_url: http://<你的主机>:<端口>/v1
  api_key_env: CORP_AI_API_KEY
  max_tokens: 8192
```

再提供密钥：

```bash
# Windows (PowerShell)                    # POSIX
$env:CORP_AI_API_KEY = "sk-..."           export CORP_AI_API_KEY=sk-...
```

（`managers/llm_client.py` 也会回退读取 `~/.dsh/.credentials.yaml`。）

---

## 5. 快速开始

```bash
# 单次进程内运行（E4 4B、D10 臂、LLM 管理器、种子 20240601）
python tools/run_experiment4.py --sub 4B --arm D10 --manager B4b \
    --seed 20240601 --scenario E4_ANCHOR --cohort primary --direct

# 完整扫描（并行子进程 worker）
python tools/run_experiment4.py --sub 4A --manager all --jobs 8

# 分析结果 -> outputs/experiment4_summary.md + .json
python tools/analyze_experiment4.py primary
```

运行写入 `runs/experiment4/<cohort>/<sub>/<arm>/<scenario>/seed<seed>/<manager>/`。
`--force` 可重跑已有的（且未过时的）运行。

### 测试

测试是独立脚本（无需 pytest）：

```bash
python tests/test_experiment4_acceptance.py
python tests/test_acceptance.py
```

---

## 6. 复现论文结果

1. 安装环境（第 3 节）并配置 SUMO / BlueSky / LLM（第 4 节）。
2. 对每个实验跑 primary 扫描（如 `tools/run_experiment4.py`）。
3. 分析（`tools/analyze_experiment4.py`），并对照 `outputs/experiment4_summary.json`
   或论文复现包（`新方向手稿/overleaf/reproducibility/`）。

E4 primary 结果（1360 次运行）汇总在 `outputs/experiment4_summary.md` 与 `.json`。
机器相关的设置只有 LLM 接口地址与 BlueSky 路径两处。
