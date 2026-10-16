# 异步地空服务监督研究设计

后续研究考察慢速提案生成期间的执行时效、资源承诺与载荷交接。运行时以不可变快照请求提案，由单一仿真所有者执行世界状态更新，并在命令应用前检查版本、资源和物理前置条件。

当前实现、配置和实验定义位于 `research_hscc2027/`。以下文档分别记录共同规则、六场地扩展和验收条件：

- [基础实验协议](research_hscc2027/design/EXPERIMENT_PROTOCOL_v0.1.md)：物理语义、监督器、指标、随机流和模型调用协议。
- [六场地协议](research_hscc2027/design/EXPERIMENT_PROTOCOL_v0.2.md)：场地身份、运行矩阵与配对分析。
- [开发验收依赖](research_hscc2027/design/EXECUTION_PRIORITY_v0.1.md)：协议、载荷、资源和场地验收顺序。
- [实现状态](research_hscc2027/IMPLEMENTATION_STATUS.md)：已完成检查及未解决的验证边界。
- [历史数据来源](provenance/hscc2027/REPOSITORY_AUDIT.md)：旧平台归档和纠正单元映射。

这些协议描述研究设计，不代表正式实验已经执行。ITSAC 论文使用独立的 `itsac-restored-20261016` 分支。
