# 旧项目恢复与校验

初次迁移档案位于 `legacy/20260918/`。2026-09-18 首轮实现时，已验证的缓存和旧批量数据工作区副本被清理；完整内容以以下独立 ZIP 为准。旧 tracked 源码、主 Git 历史、稿件和 R0 回放所需历史证据仍在工作区。

独立备份目录：`C:/Users/user/research-backups/ground-air-legacy-20260918/`。

- `legacy_snapshot.zip`：旧项目所有发现文件的备份，含 `.git/` 和未跟踪/被忽略内容。
- `legacy.bundle`：主仓库全部 refs 和可达 Git 历史；不包含原始数据等 Git 外材料。
- `legacy_file_inventory.csv`：原位置、现位置、字节数、mtime 和 SHA-256。
- `legacy_freeze_manifest.json`：备份 SHA-256、分组规模及备份内容校验状态。
- `migration_verification.json`：迁移后逐文件内容和文件集合校验结果。

需要恢复时，先从 manifest 核对 ZIP 的 SHA-256，再解压到一个**全新空目录**（建议短路径，例如 `C:/research-restore/ground-air-20260918/`）。不要覆盖当前新方向或现有档案。ZIP 内路径从旧项目根开始，因此解压后的根目录应直接包含 `.git/`、`runs/`、`manuscript/` 等。

完整备份经过逐条解压读取并与原文件 SHA-256 对照；迁移后的档案另做逐文件 SHA-256 校验。这验证了内容保留，不等于重新执行旧仿真，也不认证旧论文逻辑实验单元全部齐全。

旧源码的相对路径结构被保留。历史日志、文稿和图件构建器中可能仍记录旧绝对路径；这些记录为溯源而保留，若运行环境需要迁移路径，应在恢复副本中调整，避免改写冻结档案。

本备份位于同一台电脑的 C 盘，不代表异地备份。OneDrive 云端同步完成状态未核验。

本轮清理索引和日志：`research_hscc2027/outputs/bootstrap/cleanup_plan.json`、`cleanup_journal.jsonl`、`cold_storage_files.csv`、`cold_storage_plan.json`、`cold_storage_journal.jsonl`。原 `legacy_file_inventory.csv` 和 `migration_verification.json` 是清理前历史证据，不覆写。

如只需一个文件，可从总工作区根目录运行：

```powershell
python -B research_hscc2027/tools/restore_legacy_file.py "runs/旧运行目录/metrics.json" --destination "C:/research-restore/selected"
```

将示例相对路径替换为索引中的真实路径。工具验证 ZIP 中该文件的 SHA-256，拒绝路径逃逸及覆盖已有文件。旧稿归档含目录链接的 `archive/manuscript_workspace` 分支被保留，未沿链接清理外部依赖。
