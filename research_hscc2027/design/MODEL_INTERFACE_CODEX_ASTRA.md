# GPT-6 Astra high：Codex 实验调用契约

六场地接入说明（v0.2）：本版R6使用SCRIPTED_V1和可选B2_FAST，不新增原生调用。R5仍为A的S1/S3、60运输run和400 CLI启动设计上限。模型/档位、隔离契约与响应schema保持不变。

宿主将 `site_id`、网络/设施/兼容性/外生实现/参考期限hash纳入运行日志与完整环境身份。城市名、原型标签、未来道路事件表、事后可行性搜索结果只用于离线分析，不注入模型。若后续将R5扩展到D/F，需在新版本更新输入规模校准、fixture和批次配对，不能复用A的计时证据作为跨场地验证。

## 已确认与待实现

本机存在 Codex CLI 0.147.0；`codex login status` 显示 ChatGPT 登录；本地模型缓存包含 `gpt-6-astra` 和 `high`。本轮没有发送实验模型请求。机器配置为 `config/llm_codex_astra_high.json`，新提示词为 `prompts/astra_proposer_v1.txt`，响应 schema 为 `schemas/proposal.schema.json`。

后续实现应以 Codex 非交互子进程作为提案 backend。它复用本机登录，但每次请求是新会话，不复用当前 Codex 对话历史。不要读取/导出 auth.json、复制令牌到实验目录，或把旧 DeepSeek base_url/key 填入新配置。

## 调用蓝图

以下是 PowerShell 中的**人工检查示例**，不是已经实现的异步适配器。`prompt.txt` 必须由固定 prompt 和当前快照拼接而成，schema、输入和输出必须在独立请求目录中；不得以研究仓库作为 CLI 工作目录。

```powershell
Get-Content -LiteralPath './prompt.txt' -Raw | codex exec - `
  --model gpt-6-astra `
  -c 'model_reasoning_effort="high"' `
  --ignore-user-config --ephemeral --skip-git-repo-check `
  --sandbox read-only `
  -c 'web_search="disabled"' `
  -c 'features.shell_tool=false' `
  -c 'features.multi_agent=false' `
  -c 'project_doc_max_bytes=0' `
  --output-schema './proposal.schema.json' `
  --json --output-last-message './proposal.json'
```

这些 CLI 参数的存在已通过本机帮助和官方配置说明核查；**仅这些参数仍不足以证明所有上下文/工具已经隔离**。原生准入需确认最终启用的插件、MCP、技能、记忆、工具及附加指令；不能确认没有实验外信息便不进入正式 R5。需保存有效配置、能力清单、完整可见输入和指令来源 hash，以及隔离探针报告。探针使用虚构标记，不向模型提供真实未来故障、正式答案或旧稿结论。

## 输入与返回的具体字段

快照 envelope：`schema_version, request_id, request_seq, snapshot_sha256, input_contract_hash, sim_time_s, event_seq, active_missions, visible_resources, visible_facilities, payload_states, legal_candidates`。

每个 mission 包含版本、释放/截止时刻、起终点、载荷 ID、当前阶段；每个 candidate 包含唯一 ID、任务 ID、资源/载荷版本、阶段图、预计交付时间、迟到量、背景损害估计以及已知交接条件。只包含当前可见事实和所有方法共享的估计。发送 envelope 前由宿主计算 hash，模型只回显，不让模型重算哈希。

`snapshot_sha256` 对 snapshot 的规范 JSON 内容计算，hash 字段本身排除；`input_contract_hash` 对 schema/prompt/输入字段白名单/估计器语义版本计算。不得包含 method label、未来故障日程、最优答案、论文描述或其他方法的轨迹。

响应只选择已给定的 candidate_id，不创建路由/资源。JSON schema 负责形状；宿主还需验证：request/hash/version 匹配、每活跃任务至多一个提案、candidate 属于该任务的快照候选、PROPOSE 对应非空 candidate、NO_FEASIBLE_ACTION 对应 null 且确无合法候选。然后在当前世界状态重新验证版本/容量/载荷并原子接纳。Schema 通过不是物理合法。

宿主分配 operation_id，按任务/载荷/实际动作标识实现幂等，不能把每次新 request_id 当成新物理操作。模型拒绝或无合法响应时由共同 B2 本地回退继续服务，不切换其他 LLM。

## 后台适配器的实现验收

1. 主进程 enqueue 前固定快照并记录单调时间；后台用参数数组启动 CLI，不拼 shell 字符串。stdout JSONL 和 stderr 分别流式写盘，不因管道填满阻塞主循环。
2. 逐请求记录输入、schema、提示词、CLI 版本、显式模型/档位、解析后的有效设置、实际暴露的响应模型元数据。没有服务端 snapshot/version 就记录 unknown，不补造。
3. response_ready 是完整输出可读时刻；validation_completed 是结构与输入契约校验结束时刻；只有主线程收到后能检查世界状态。延迟按协议分别计算，不能从 API 文档推测服务端耗时。
4. 240 s watchdog 与各监督器等待规则独立。取消/迟到和进程退出均记 terminal 原因；客户端结束不表示服务端一定停止计算。
5. 任何未经允许的工具尝试使原生准入失败；正式发现则停止该版本、保留 attempt 并审计影响，不默默删除样本后补跑。
6. 不设置未被此后端确认支持的 temperature、top_p 或模型随机 seed；不自行购买额度或切换付费 API endpoint。CLI 启动次数、可见服务端请求、token 和账号额度分别记账。

## 准入与批次

先用无未来信息的小型合成快照做 1 次连通性/契约诊断，再做 24 次输入规模测量。实际准入后更新模型与 CLI 元数据，但修改提示词、输入字段或环境语义需新版本。原生输入/调用记录可审计重放；模型输出因未固定服务端版本与随机性，不保证逐字重复。

正式每个 scenario×seed 块有 FIX/LST/FULL 三个运输 run，最多预留 12 次 CLI 启动；剩余额度不足则停在块边界。4 请求/run 和 400 次 CLI 启动上限为设计预算，实际启动批量实验前需按执行任务落实。当前阶段交付配置与协议，不声称后端适配器已完成。

参考：[模型说明](https://developers.openai.com/api/docs/models/gpt-6-astra)、[非交互运行](https://learn.chatgpt.com/docs/non-interactive-mode)、[配置字段](https://learn.chatgpt.com/docs/config-file/config-reference)。
