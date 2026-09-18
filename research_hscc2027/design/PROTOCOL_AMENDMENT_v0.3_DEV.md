# v0.3开发修订记录（非正式冻结版）

2026-09-18。依据作者自主执行指令，保持研究方向、六场地、原方法/种子/矩阵和公平性规则。本文件记录会影响协议证据解释的改动；不得将其当作 `EXPERIMENT_PROTOCOL_v0.3_FROZEN.md`。

1. R1-A改为有界SMT/BMC安全检查，保持原有限模型边界；资源容量采用违例表达式的等价分解，求解UNKNOWN保留。证据见 [R1_ACCEPTANCE_v0.3](R1_ACCEPTANCE_v0.3.md)。
2. R1-B有条件进展、R1-C实现对应独立报告。G1通过只打开下一开发验收，不打开正式run。
3. 继续严格顺序：G1 → D → F → E → A/B/C统一 → 共享参数/完整fixture冻结。正式运行顺序按作者新指令为R2_MAIN → R2_PHASE → R3_HANDOFF → R6_SITE → R4_SCALE → R5_NATIVE；可选参考最后。
4. 物理验收期间的预留开关实验属于机制诊断，不能冒充已冻结的X_LST/X_FULL正式比较。两组共享速度、处理时长、观测和外生事件；不同deadline或负载版本必须留档。
5. 对Formal Freeze尚缺的共同估计器、reference/deadline、B2权重、timeout/epsilon和控制器hash逐项落实后，才生成正式冻结文件。原R0桥接与适用G0–G4仍为正式运行条件。
