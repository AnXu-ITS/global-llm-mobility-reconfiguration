# ITSAC V3 实验结果（受控交互搜索）

本目录收录 **ITSAC 受控交互协议 v3**（`itsac_controlled_interactions_v3`）的实验结果、冻结配置与分析脚本。这是针对交通信号组合中 **emergent persistent spillback** 的四细胞交互搜索实验。

## 关键结论（摘要）

合成网：反馈 LLM 以 58.0% 命中率碾压基线（heuristic 6.6%），概率确认 10/10 CONFIRMED。

三城（beijing / shanghai / taipei）：**LLM 反馈的碾压优势没有复现**。

| 方法 | beijing | shanghai | taipei |
|---|---|---|---|
| random | 36/500 (7.2%) | 2/500 (0.4%) | 23/500 (4.6%) |
| heuristic | 43/500 (8.6%) | 4/500 (0.8%) | 20/500 (4.0%) |
| ucb | 33/500 (6.6%) | 4/500 (0.8%) | **44/500 (8.8%)** |
| llm_nofb | **47/500 (9.4%)** | 4/500 (0.8%) | 9/500 (1.8%) |
| llm（反馈）| **51/500 (10.2%)** | 0/500 (0.0%) | 13/487 (2.7%) |

完整结果、失效模式（确定性 proposal collapse、传输超时）与结论见 `RESULTS_V3_FINAL.md`；协议与复现说明见 `README_REVISION_V3.md`。

## 目录

- `RESULTS_V3_FINAL.md` — 最终结果与结论（合成网 + 三城）
- `README_REVISION_V3.md` — 协议与复现说明
- `configs/` — 冻结的搜索/诊断/确认配置（43 个 JSON）
- `scripts/` — 候选对提取、全量表核对、LLM 聚合脚本

## 原始数据位置（未上传）

原始仿真输出约 **19.9 GB**（`ITSAC_REPRO_BUNDLE/outputs`，其中 `revision_v3` 约 19.3 GB），超出 GitHub 限制，保留在本地：

```
C:\Users\xuan1\OneDrive\桌面\PhD论文\llmTraffic\ITSAC_REPRO_WORKSPACE\ITSAC_REPRO_BUNDLE\outputs\revision_v3
```

复现时使用 `tools/run_revision_v3.py {prepare,baseline,confirm,search,status} --config <cfg>`，SUMO 环境配置见 `README_REVISION_V3.md`（关键：只设置 PATH，不设置 SUMO_HOME）。
