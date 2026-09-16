# 复现入口

论文与人工图件编辑从本库 README.md 开始。完整分析工作区仍位于上级目录，避免移动破坏对父项目只读运行数据的路径。

- 完整说明：`../REPRODUCTION_README.md`
- 后处理入口：`../reproduce_analysis.ps1`（默认不重跑；只有显式传入 -RunRegression 才执行小范围回归）
- 当前分析代码/数据：`../source/revision_v3/`
- 原 25/6 页版本：`../source/revision_v3/baseline_overleaf/`
- 归档清单：`../archive/整理前_*/ARCHIVE_INDEX.json`

本库 reproducibility/ 保存论文所需的配置、prompt、派生数据和修正覆盖层。完整实验复现仍需要父项目原始代码与运行日志；这里未伪装成独立完整模拟器发布包。当前人工 PPT 在 editable_figures/，自动生成源只作复现参考。

E3 时长与终止状态核对使用 `reproducibility/audit_e3_horizons.py --project-root <原始项目根目录>`。该脚本只读取已保存的 metrics、run_config 和 registry_final，并对照本站点场景矩阵，不重跑仿真。`e3_horizon_audit.json` 汇总结果，`e3_horizon_runs.csv` 保留 2,880 次运行的时长、到期任务状态和注册表哈希。L1/L2 使用 900 s，L3/L4 使用 1,200 s。
