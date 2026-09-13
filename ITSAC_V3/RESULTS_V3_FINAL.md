# V3 实验最终结果与结论（合成网 + 三城）

## 1. 协议回顾

- 协议版本：`itsac_controlled_interactions_v3`
- 四细胞设计（baseline / A / B / AB），交互边 `I_spill = S_AB − S0 − S_A − S_B`
- 五方法 × 10 run × 50 call（每城 500 call）：random / heuristic / ucb（LinUCB）/ llm_nofb（LLM 无反馈）/ llm（LLM 带结果反馈）
- 分类：execution_valid / endpoint_valid / traffic_outcome / single_action_acceptable
- LLM：`corp-ai/openai/deepseek-v4-pro`，temperature 0，max_tokens 32768，timeout 360s，contract_attempts 5，transport_errors 5

## 2. 合成网结果（对照基线）

| 方法 | hits / 500 calls | 命中率 |
|---|---|---|
| random | 11 | 2.2% |
| heuristic | 33 | 6.6% |
| ucb | 0 | 0.0% |
| llm_nofb | 27 | 5.4% |
| **llm（反馈）** | **290** | **58.0%** |

概率确认（top-10 候选 × 20 holdout 种子，p0=0.02）：**10/10 CONFIRMED**，p≈1e-34~1e-31。

→ 合成网结论：**反馈 LLM 能学机制并碾压基线（58% ≫ 6.6%）**，且结果在 holdout 上可靠复现。

## 3. 三城结果（本次主结果）

| 方法 | beijing | shanghai | taipei |
|---|---|---|---|
| random | 36/500 (7.2%) | 2/500 (0.4%) | 23/500 (4.6%) |
| heuristic | 43/500 (8.6%) | 4/500 (0.8%) | 20/500 (4.0%) |
| ucb | 33/500 (6.6%) | 4/500 (0.8%) | **44/500 (8.8%)** |
| llm_nofb | **47/500 (9.4%)** | 4/500 (0.8%) | 9/500 (1.8%) |
| llm（反馈）| **51/500 (10.2%)** | 0/500 (0.0%) | 13/487 (2.7%)* |

\* taipei llm r10 在 call 38 发生确定性 proposal collapse，按 37/50 计（详见 §5）。

## 4. 跨城 + 合成网对照分析

### 4.1 合成网「LLM 碾压」没有复现

合成网 LLM 反馈 58% ≫ heuristic 6.6%（9 倍优势）；三城中 LLM 反馈：
- beijing 10.2%（微弱领先 heuristic 8.6%，≈ llm_nofb 9.4%）
- shanghai **0.0%（全场最差，低于 random 0.4%）**
- taipei 2.7%（低于 ucb 8.8%，低于 random 4.6%）

**反馈机制在城市里没有稳定增益，甚至有害。**

### 4.2 城际交互密度是主变量

- beijing：6.6–10.2%（密）→ 方法间有区分度，LLM 微弱占优
- taipei：1.8–8.8%（中等）→ **ucb 最优**，LLM 反馈反而 < random
- shanghai：0.0–0.8%（极稀）→ 500 call 仅 0–4 hit，方法间无区分

「哪些城市网络容易产生 emergent spillback」本身被拓扑/需求结构主导，方法贡献是二阶的。

### 4.3 ucb 在城市里学得动（与合成网相反）

合成网 ucb=0（背景太稀 2.2% 学不到）；城市中 taipei ucb 8.8% ≈ 2× random、shanghai ucb 0.8% ≈ 2× random。说明交互更密时 LinUCB 能利用特征增益，成为非 LLM 最强（taipei）。

### 4.4 无跨城一致的最强方法

beijing 最优 llm、taipei 最优 ucb、shanghai 全员躺平——方法优劣强烈依赖网络结构，**不存在 universal winner**。

## 5. LLM 方法的两种失效模式（重要负结果）

### 5.1 传输超时（transport timeout）

beijing llm run 5 在 call 27 连续 5 次 API `TimeoutError`（各 ~360s）耗尽 transport 预算停机。续跑逻辑会从 ledger 重建 transport 计数导致卡死，需手工 reset 后重跑。属于瞬时网关波动，可恢复。

### 5.2 确定性 proposal collapse（本次新发现）

taipei llm r10 在 call 38 时，LLM **确定性**反复提出同一对 `B004+B016`（两个 demand 动作共享 flow `keelung_to_zhongxiao_e#0`），被 validator 判为 `L_SAME_LOCUS`（同类别同 locus = 剂量反应，非交互）而拒绝。

- LLM 推理明确认为「共享 flow = 叠加需求 = 强化」是**优点**，与协议「共享 flow = 同 locus = 非交互」的定义冲突。
- prompt 中「不要同 locus 叠加」按空间（edge）理解，未覆盖「同类别共享 flow」语义。
- **corp 网关对 temperature=0 + 相同 prompt 缓存 completion**：5 次 attempt 全部命中缓存（各 0.08–0.25s）返回同一错误对；correction 反馈无法纠偏。
- 因此 reset + 重跑**必然复现**同样塌陷（确定性 + 缓存，不可重置）。

统计上约 **1/50 call 触发不可恢复塌陷**（r10 的 call 38）；其余 L_SAME_LOCUS 拒绝都在 attempt 2 恢复。

## 6. 结论

1. **LLM 反馈的机制学习优势是「合成网特定」而非普适**：在机制干净、可学习的合成网（单一「需求×关闭」机制）上，反馈 LLM 能以 58% 命中率碾压基线并在 holdout 上 10/10 复现；但在真实城市中，交互机制分散、稀疏、异构，LLM 的机制假设命中率低，退化为与启发式/UCB 同级甚至更差（shanghai 0%、taipei < random）。

2. **城际网络结构是 emergent spillback 的主导变量**：beijing/taipei 密、shanghai 稀，方法间差异被密度差异掩盖。

3. **非 LLM 基线在城市里仍有价值**：ucb 在 taipei 最强（8.8%），heuristic 在 beijing 接近 LLM（8.6%）。

4. **LLM 方法存在真实可靠性缺陷**：确定性 proposal collapse（same-locus 剂量反应对，温度 0 + 响应缓存使其不可恢复）+ 传输超时停机。这些是部署层面的负结果，须与准确率一并报告。

## 7. 局限与后续

- **shanghai 无候选对**：500 call 0 hit，概率确认无对象（LLM 反馈在 shanghai 完全失效）。
- **taipei llm r10 不完整**（37/50）：proposal collapse 导致，如实标注。
- **概率确认未跑**（用户决策跳过）：候选对已提取（beijing top=B009+B054 50% 命中率；taipei 候选多为 1-hit 噪声），如需正式 holdout 确认可后续补跑。
- 合成网与三城使用同一 prompt（含「same locus」歧义）；若要改善城市命中率，需澄清 prompt 中「同类别共享 flow = same-locus」规则（代码变更 → 指纹变更 → 需重新 prepare，代价高）。
