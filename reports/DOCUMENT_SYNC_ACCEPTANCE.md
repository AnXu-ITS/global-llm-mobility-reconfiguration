# Document Sync — Acceptance (D-T1 … D-T15)

Synchronization of `ground_air_llm_experiment_plan.md` and
`EXPERIMENT_IMPLEMENTATION_SPEC.md` against the frozen Experiment-1 finalization
state. Each item: PASS / WARNING / FAIL.

| id | check | result | evidence |
|---|---|---|---|
| D-T1 | 两个旧文件均已备份 | **PASS** | `docs/archive/ground_air_llm_experiment_plan_pre_exp1_final.md`、`docs/archive/EXPERIMENT_IMPLEMENTATION_SPEC_pre_exp1_final.md`；SHA-256 与源文件 byte-identical |
| D-T2 | Current Frozen State 已加入两文件 | **PASS** | 两文件顶部均有 `# Current Frozen State after Experiment 1 Finalization` |
| D-T3 | 3.2 × 3.2 km 是当前 canonical truth | **PASS** | 两文件均写 `S0_3p2km_v1`、3.2 × 3.2 km、center 31.30377 N / 120.59981 E |
| D-T4 | 4-aircraft fleet 是当前 base fleet | **PASS** | 两文件逐架列出 L-UAV-01 / EVTOL-01 / M-UAV-01 / M-UAV-02（自 `scenario_config.yaml` + `resource_compatibility.yaml`） |
| D-T5 | 5 km / 12 aircraft 仅作为 historical/reference | **PASS** | 两文件均显式标注 "historical/default design reference"、"NOT current" |
| D-T6 | B4a / B4b 定义正确 | **PASS** | B4a = LLM-State（无 candidate table）；B4b = LLM-Candidate（有 candidate table）；B4b = primary LLM method |
| D-T7 | Candidate Generator 已进入正式架构 | **PASS** | spec 新增 `Manager-Agnostic Candidate Generator Contract`；plan 加入 Candidate Representation 小节 |
| D-T8 | Candidate Table 明确无 B2 leakage | **PASS** | 两文件均写 "no B2 objective score / ranking / recommendation leakage"；白名单/黑名单并列 |
| D-T9 | Action Contract v2 已成为 authoritative contract | **PASS**（note） | spec §15 写 "Action Contract v2 is authoritative"；权威 structural schema = `schemas/manager_action_v1.schema.json`（12 action types）。注：LLM-facing 语义为 v2（prompt `manager_v2.txt`），structural JSON schema 文件名仍是 `manager_action_v1.schema.json`（title `ManagerAction v1`），二者均已如实记录，非冲突 |
| D-T10 | Normalize-then-validate 已写入执行协议 | **PASS** | spec §15.5；四段日志 raw/normalized/validation/executed；禁止 normalization 修复 infeasible decision |
| D-T11 | B2 objective 明确 frozen | **PASS** | spec §23：FROZEN，权威来源 `config/experiment1_b2_weights.yaml` + `B2_OBJECTIVE_FREEZE.md`；禁止反向调参 |
| D-T12 | same-prompt cache 不再可作为 statistical replicate | **PASS** | spec §28 + plan §16：unit = scenario × seed；cache 只用于 replay/debug/stability |
| D-T13 | Experiment 1 已标记 COMPLETED/FROZEN | **PASS** | plan §10、spec §34 均标 `COMPLETED / FROZEN`；960 + 60 = 1020，0 excluded，20/20 PASS |
| D-T14 | Experiment 2 已标记 NEXT，但未被提前执行 | **PASS** | plan §11 / spec §30 标 `NEXT`；未生成 Experiment 2 matrix |
| D-T15 | 旧文档没有任何残留条目会误导 Agent 重建旧系统 | **PASS** | 一致性审计（`DOCUMENT_SYNC_AUDIT.md`）确认所有旧值已去除或降级为 historical reference；spec 明确 "must NOT rebuild Steps 1–16" |

## Result

**D-T1 … D-T15 = 15 / 15 PASS，0 WARNING，0 FAIL.**

## Notes (non-blocking)

1. **Action Contract 版本命名**：LLM-facing 契约语义是 v2（`prompts/manager_v2.txt`，
   含 REASSIGN preemption），而 structural JSON schema 文件名是
   `manager_action_v1.schema.json`（title `ManagerAction v1`）。两文档如实记录两者，
   未混淆。
2. **B1/B2 命名冲突**：`B1`/`B2` 同时是 manager 名与 frozen disruption-link id
   （`scenario_config.yaml`）。这是代码库既有命名，按"不改 config"约束保留，文档以
   上下文消歧。详见 `DOCUMENT_SYNC_AUDIT.md`。
