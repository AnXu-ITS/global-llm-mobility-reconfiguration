# 项目进度：进入正式论文写作

更新：2026-09-10。四个实验与分析收尾已完成，当前阶段为论文写作。

| 实验 | 主运行 | 附加消融 | 最终版本 |
|---|---:|---:|---|
| E1 地面扰动与接口消融（三站点） | 2,880 | 180 | experiment1_final |
| E2 单一低空故障（三站点） | 3,840 | 0 | 原始运行＋修正条件指标 |
| E3 复合扰动（三站点） | 2,880 | 0 | matrix v2 |
| E4 观察、执行延迟与输入负担 | 1,360 | 0 | matrix v2 |
| 合计 | **10,960** | **180** | paper_final_20260910 |

## 写作主线

全局状态需要被组织成可比较、可执行且及时更新的候选信息，才能支持空地资源在扰动中的有效重配置。四个实验依次回答选择性协调、单故障恢复、复合扰动下的收益和运行时效/输入代价。

详细章节结构、贡献与结果叙事见 [论文主线与写作指南](reports/PAPER_STORY_AND_WRITING_GUIDE.md)。

## 已关闭的四项收尾

1. **版本统一**：E1 final、E2修正分析、E3 v2与E4 v2汇入唯一数据入口；旧报告保存在archive，当前最终报告已更新。
2. **统计修正**：共享Holm/配对检验实现；E2恢复时间使用两管理器均受影响的191对；E3假设文件按v2重算。
3. **指标修正**：E4重规划排除NO_ACTION；恢复指标使用条件分母；区分切换和回到先前选择；输出逐臂绝对值与CI。
4. **故事与解释**：4A按新任务/故障观察调度解释，4B按执行等待与队列转折解释，4C按固定核心机队的输入负担解释。保留正式机制，无需补跑。

## 验证

E3验收9/9、跨站点验收7/7通过；论文发布检查25/25（含E4离线12项）通过；640组4C匹配候选集合一致；10,960份主运行指标与审查前哈希一致。历史源码差异已通过反向单处补丁精确重建原哈希，原冻结清单保留。

## 唯一写作入口

- 全量数值/统计：`outputs/paper_final/results.json`
- 汇总CSV：`outputs/paper_final/main_results.csv`
- 最终报告索引：[reports/README.md](reports/README.md)
- 写作主线：[reports/PAPER_STORY_AND_WRITING_GUIDE.md](reports/PAPER_STORY_AND_WRITING_GUIDE.md)
- 重建：`python tools/finalize_paper_results.py`
- 验证：`python tools/check_paper_release.py`

历史进度报告（含v1结论及审计过程）保存在 `archive/paper_pre_20260910/PROGRESS_REPORT.md`，不作为当前论文数值来源。
