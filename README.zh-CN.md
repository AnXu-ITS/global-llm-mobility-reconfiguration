# 地面与低空服务重构

[English](README.md)

本仓库研究交通扰动下的地空服务恢复，包含 ITSAC 论文材料及独立的后续运行时监督研究。

## ITSAC 论文

**A Ground–Low-Altitude Mobility Manager for Service Reconfiguration under Disruptions** 研究如何利用低空资源及时恢复地面服务，同时减少对已有服务承诺的影响。

- [论文专用分支](https://github.com/AnXu-ITS/global-llm-mobility-reconfiguration/tree/itsac-restored-20261016)
- [最终稿](https://github.com/AnXu-ITS/global-llm-mobility-reconfiguration/blob/itsac-restored-20261016/itsac/ITSAC_XU_AN.docx)
- [补充材料和保存数据](https://github.com/AnXu-ITS/global-llm-mobility-reconfiguration/tree/itsac-restored-20261016/itsac/supplement)

论文分支提供代码、配置、DeepSeek V4 Pro 实验提示词、11,140 条逐运行指标及离线统计核验脚本。完整历史原始轨迹缺失；保存的指标支持重新计算统计结果。

## 当前分支的后续研究

`main` 分支开发带资源预留、载荷保管和物理交接的异步运行时监督器，与 ITSAC 实验分开。

[research_hscc2027/](research_hscc2027/) 包含实现、实验协议、配置、场地和工具。已记录的检查包括历史回放、协议用例及单载荷物理闭环对照；[R1 v0.3 记录](research_hscc2027/design/R1_ACCEPTANCE_v0.3.md)报告了声明有限模型内的验收通过，这不代表整个部署系统已经证明正确；规划的正式运输实验尚未形成论文结果。[实现状态](research_hscc2027/IMPLEMENTATION_STATUS.md)列出检查范围和限制。

旧平台及分析保留在 [legacy/20260918/](legacy/20260918/)，来源清单和哈希保留在 [provenance/hscc2027/](provenance/hscc2027/)。

仓库尚未指定许可证，复用前请联系作者。代码问题可通过 [GitHub issues](https://github.com/AnXu-ITS/global-llm-mobility-reconfiguration/issues)提出。
