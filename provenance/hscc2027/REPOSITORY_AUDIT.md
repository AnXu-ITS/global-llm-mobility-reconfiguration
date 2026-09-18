# 仓库与归档审计

日期：2026-09-18。

| 项目 | 观察 |
|---|---|
| 旧主仓库 | `legacy/20260918/`；原 GitHub remote 保留 |
| 原始提交 | `3078ffb60d58952b4c193b2edb1de7d85375bbab` |
| 远程核对 | 本次只读 `ls-remote` 查询到 GitHub `main` 为相同 SHA |
| 原始受跟踪改动 | 初始 `git status --short` 未显示受跟踪改动；暂存与未暂存补丁为空 |
| 原始未跟踪材料 | 转向计划书、两个旧 Overleaf 工作副本 |
| 新 Overleaf | `manuscript_hscc2027/`；HEAD `e94a0ef036ac2e3283f6257f8fb159115c8168b5`；分支 `main` |
| 远程写入 | 无；仅查询与 clone |
| 归档规模 | 329,525 个文件，7,808,576,298 字节；以机器清单为准 |
| 独立 ZIP 备份 | `C:/Users/user/research-backups/ground-air-legacy-20260918/legacy_snapshot.zip` |
| Git 历史备份 | 同目录 `legacy.bundle`，包含主仓库全部 refs，已通过 bundle verify |

`git_status_before.txt` 是备份开始时的状态，此时新 Overleaf 克隆和 provenance 目录已经创建；其中这些新增条目是本次整理产物。转向计划书保留在根目录，旧的两个 Overleaf 工作副本随整个 manuscript 归档。

完整 ZIP 的每一个文件条目已读取并与原始 SHA-256 清单匹配。归档后的再校验、原/替代纠正单元对应和最终 Git 状态见 `migration_verification.json`。本次没有执行模拟器测试，因此不能把这些存储校验描述为实验回归通过。

最终校验结果：329,525 个文件逐项 SHA-256 全部一致，文件集合完全一致；20 组 B0 D60 原始/纠正指标均存在；旧主仓库 HEAD 不变、受跟踪内容无差异；新 Overleaf 工作区干净。

运行标志文件共定位 15,385 个历史目录，其中 15,369 个具有 metrics。其余 16 个位于旧单元测试、smoke、quick verify 和 replay 目录，已在运行清单显式标记。这不是迁移丢失，也不能直接解释为 16 个主实验缺失；主实验逻辑矩阵完整性尚未另行审计。

## Git 目录迁移异常及处理

第一次 PowerShell `Move-Item` 迁移 `.git` 时受隐藏/只读属性影响中断，旧项目其他顶层目录已成功移动。未完成的 Git 元数据被完整保留到独立备份目录的 `git_move_remainder/`；随后仅从已验证 ZIP 补入归档仓库缺失的 84 个 Git 文件，对已存在文件先校验内容且不覆盖。

处理详情见 `git_metadata_recovery.json`，移动记录见 `move_journal.jsonl`。原始损坏的 `manuscript/overleaf_remote/` 属于另一个历史副本，原样保存，不与此次主仓库迁移异常混淆。

## 清单的解释边界

- `legacy_file_inventory.csv` 是逐文件的完整发现清单，记录原路径、现路径、字节数、mtime 和 SHA-256。
- `legacy_inventory.csv` 根据 metrics、missions、actions 等运行标志文件发现运行目录；缺少 metrics 的发现目录会显式标记。它不是按论文矩阵枚举的完整性认证。
- `correction_map.csv` 列出 E4B D60 的 20 个 B0 原始/纠正单元及哈希；旧结果仍保留，纠正单元不额外增加独立样本数。
- 本次备份未验证外部机器、OneDrive 云端副本或此前已经丢失的文件。
- 归档使用内容冻结与校验约束，没有更改用户 ACL 或将所有文件强制设为只读。
