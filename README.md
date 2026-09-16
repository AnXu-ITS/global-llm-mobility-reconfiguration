# Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions

地面–低空移动系统在中断场景下的全局 LLM 监督重构。

## 概览

- **测试床**：`S0_3p2km_v1`（苏州 3.2 km OSM 场景；SUMO 1.27.1 + BlueSky 联合仿真）
- **基础机队**：`L-UAV-01`、`EVTOL-01`、`M-UAV-01`、`M-UAV-02`
- **LLM**：`corp-ai/openai/deepseek-v4-pro`（OpenAI 兼容），`base_url = http://192.168.27.4:18888/v1`，`max_tokens = 8192`
- **实验序列**：
  - E1 — 基线与方法对比
  - E2 — 失效感知
  - E3 — 全局状态
  - E4 — LLM 运行极限（4A 信息刷新频率 / 4B 推理延迟 / 4C 全局状态规模）

## 目录结构（当前）

| 路径 | 用途 |
|---|---|
| `新方向手稿/` | 论文工作区（`overleaf/` 为当前交付稿，含 `reproducibility/` 复现包：config/prompts/派生数据与覆盖层） |
| `tools/` | 实验调度与后处理脚本（`run_experiment1..4.py`、`analyze_experiment*.py`） |
| `reports/` | 独立评审与审计报告 |
| `ITSAC_V3/` | ITSAC V3 交互结果 |
| `archive/` | 归档（含 `ground_air_framework/` 完整框架与各历史版本；**git 忽略**） |
| `runs/`、`outputs/` | 运行产物与结果（**git 忽略**） |

> 完整实验框架与历史版本归档于 `archive/ground_air_framework/`；论文复现所需的最小配置/prompt/派生数据位于 `新方向手稿/overleaf/reproducibility/`。

## 环境

- **解释器**：`C:\Users\xuan1\.venvs\bluesky\Scripts\python.exe`（Python 3.14.7；含 `sumo`/`traci`、`bluesky`、`pyproj`、`scipy`）
- **SUMO** 1.27.1、**BlueSky**
- **LLM 密钥**：环境变量 `CORP_AI_API_KEY`，或 `~/.dsh/.credentials.yaml`（由 `managers/llm_client.py::load_api_key` 读取，不纳入仓库）

## 运行实验

```powershell
$py = "C:\Users\xuan1\.venvs\bluesky\Scripts\python.exe"
# 调度（按 cohort/sub/arm/manager/seed 拆分，支持 --force 重跑）
& $py tools/run_experiment4.py --sub 4A --manager all --jobs 8
# 分析
& $py tools/analyze_experiment4.py primary
```

- 运行目录：`runs/experiment4/<cohort>/<sub>/<arm>/<scenario>/seed<seed>/<manager>/`
- 分析产物：`outputs/experiment4_summary.md` / `.json`
- 完整框架的调度/分析脚本对应 `archive/ground_air_framework/tools/`

## 论文

- 读稿/改稿从 `新方向手稿/README.md` 开始，当前交付稿在 `新方向手稿/overleaf/`（`main.tex`、`supplement.tex`）。
- 复现入口：`新方向手稿/REPRODUCTION_README.md`、`新方向手稿/reproduce_analysis.ps1`。
