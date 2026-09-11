# Document Sync — Diff Summary

Backups (byte-identical to pre-edit state):
- `docs/archive/ground_air_llm_experiment_plan_pre_exp1_final.md`
- `docs/archive/EXPERIMENT_IMPLEMENTATION_SPEC_pre_exp1_final.md`

## ground_air_llm_experiment_plan.md changes

- Added **"Current Frozen State after Experiment 1 Finalization"** (top).
- Added **"Source-of-Truth Hierarchy"**.
- Updated **RQ1** → "Selective Ground-to-Air Support"（中性措辞；Experiment 1 不以
  "证明 LLM 优于 baseline" 为目标）。
- Updated **RQ2** → "Air-Layer Failure Reconfiguration"，承接 Experiment 1 final
  finding（B2–B4b comparable aggregate performance 是否在 air-layer failure 下仍
  成立；不预设 B4b 会赢）。
- **Experiment 1 整节**改为 `Status: COMPLETED AND FROZEN`；primary managers
  B0/B1/B2/B4b；interface ablation B4a（LLM-State）/ B4b（LLM-Candidate）；不再
  使用 B3/B4 generic 命名。
- 写入 **final dataset**（960 + 60 = 1020；0 excluded；unit = scenario × seed；
  same-prompt ≠ statistical replicate）。
- 写入 **final headline results**（B0/B1/B2/B4b 四行，含 95 % CI；B4a ablation）。
- 冻结 **8 条 scientific conclusions**（comparable，不写 outperform/match）。
- 加入 **Candidate Representation**（manager-agnostic candidate generator 架构 +
  candidate facts 白名单 + 泄漏黑名单）。
- 更新 **Experiment 2** → failure-induced feasible-set reconfiguration + 重点指标
  建议（不预生成 matrix）。
- 更新 **Experiment 3** → 中性措辞（hypothesis, not assumed outcome）。
- 更新 **论文贡献预期** → shared structured candidate representation +
  comparative supervisory-policy evaluation（不再单纯"提出 LLM manager"）。
- 更新 Action Space / Prompt 章节 → Action Contract v2 +
  `manager_action_v1.schema.json`。

## EXPERIMENT_IMPLEMENTATION_SPEC.md changes

- Added **"Current Frozen State after Experiment 1 Finalization"**（top）。
- Added **"Source-of-Truth Hierarchy"**。
- **3.2 km canonical testbed**：5×5 km 降级为 historical/default reference，
  3.2 × 3.2 km / `S0_3p2km_v1` 成为 current frozen truth。
- **4-aircraft frozen fleet**：12-aircraft 降级为 historical initial design；
  逐架列出 L-UAV-01 / EVTOL-01 / M-UAV-01 / M-UAV-02。
- **12-aircraft acceptance 条款**改为 "frozen canonical fleet from scenario_config
  initialized（当前 = 4 aircraft）"。
- 新增 **Manager-Agnostic Candidate Generator Contract**（candidate_info.py；fact
  白名单 + 泄漏黑名单；B1/B2/B4b 共享）。
- 更新 **Global State → Manager pipeline**（含 candidate generator；B4a disabled /
  B4b enabled）。
- 新增 **Normalize-Then-Validate**（四段日志 raw/normalized/validation/executed；
  禁止 normalization 修复 infeasible decision）。
- 更新 **Action Contract 到 v2**（`manager_action_v1.schema.json` authoritative，
  12 action types，REASSIGN preemption precondition）。
- 更新 **B1 定义**（candidate generation before ranking + 全过滤链；frozen）。
- 更新 **B2 定义**（objective + weights FROZEN；不得反向调参；Exp 2 新增约束须为
  protocol extension）。
- 新增 **LLM Manager Variants**（B4a / B4b 定义 + input 差异）。
- 新增 **LLM Configuration**（model / temperature / response_format / max_tokens /
  prompt version；endpoint 只写 "local compatible API endpoint"）。
- 新增 **statistical independence rule**（cache 不得作为 independent replicate；
  unit = scenario × seed；seed audit）。
- 更新 **build status**（Historical Build Order 保留 + Current Execution Status：
  Exp 1 DONE/FROZEN，Exp 2 NEXT，Exp 3/4 PENDING；不得重建 Steps 1–16）。
- 更新 **acceptance philosophy**（T1–T9 = platform regression, previously
  passed/frozen；EF-T1…EF-T20 = final dataset acceptance 20/20 PASS）。
- 新增 **Experiment 1 Status (FROZEN)**（1020 runs / 0 excluded /
  superseded_for_primary_analysis = true）。
