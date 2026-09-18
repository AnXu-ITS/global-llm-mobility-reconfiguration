# 六场地开发顺序与论文机制定位

2026-09-18，按作者本轮明确排序执行。本文件覆盖v0.2末节原先的“并行推进”表述，不修改已冻结的地图或原矩阵。机器顺序见 [execution_gates.v1.json](../config/execution_gates.v1.json)。

## 1. 顺序与证据

| 次序 | 工作 | 准入证据 | 当前状态 |
|---|---|---|---|
| 1 | 完整R1 | 版本、幂等、容量、载荷因果、取消和条件进展；规定有限模型边界及实现映射 | 已修复缺陷并扩大检查；枚举触及100万状态，完整G1未通过 |
| 2 | D双任务单bay | 两个实际载荷、共同就绪、容量1的实际服务区间、可测队列及保管权；预留帮助与机会成本的开发构造 | 等待R1；单载荷报告不替代本项 |
| 3 | F多任务执行 | 两任务共享M-UAV-1；实际执行层拒绝双重分配；含端点lease严格过期；上游失败解除下游预留 | 等待G-D；兼容配置不替代执行证据 |
| 4 | E deadline/load标定 | 共同无控制器参考、开发与验证划分、900s窗口、完整配对margin分布 | 等待G-F；不得要求每条轨迹恶化 |
| 5 | A/B/C统一签名与新语义fixture | 同一计算函数、量纲、路由/ETA定义、处理规则、初态和事件schema | 等待G-E；旧descriptor不直接拼接热图 |
| 6 | 冻结240个R6单元 | 六场地×两族×十seed的120个共同环境；每环境LST/FULL配对，全部完整签名 | 等待前五项；B2_FAST另120个可选参考 |

本顺序下，上一门未通过时不运行下一项验收。协议修复后的已有物理闭环回归仍属于R1实现联调，不计D/F/E新验收。R0剩余六桥接及原G0–G4适用门仍为正式批跑的附加条件，不能被本表删除。

检查入口：`python -X utf8 -B research_hscc2027/tools/check_execution_gates.py`。返回2表示门关闭，不表示已经完成的组件测试失败。

## 2. D/F/E验收边界

D应保存两个载荷实际到位、开始等待、获得bay、处理起止及后续真实到达的完整时间线。所有方法使用相同速度、服务时长、设施容量和外生事件。预留可能减少一项任务的争抢，也可能让已到位的另一任务等待；这两种情形须在方法比较前作为开发条件声明，不能按FULL净收益挑样本。核算bay实际忙碌、有效预留但未使用、任务排队和最终失约，不把预留时间全部计成物理占用。

F必须让执行器收到存在冲突的实际指派，并在任何副作用前原子拒绝不兼容资源束。lease在有效端点仍可由本人转为占用，越过端点才释放；资源计数不能同时把本人的预留和其转换后的占用计两次。上游阶段失败需要显式因果ID、下游release日志和再分配证据。仅修改JSON中的owner或检查资源总数不足以通过。

E保留既有七组差值 `+75, 0, -22, +94, +277, +291, -189 s` 及失败/截尾记录。标定前在开发方案中声明负载、候选OD、名义参考、slack与覆盖目标；参考不能读取未来扰动或FULL/LST表现。汇报名义可及时比例、名义可及时案例中的margin侵蚀比例、margin差值全分布、负差值与900s截尾。开发集选择共同参数后固定到验证/正式集，不要求正式seed逐个呈现预设坏结果。

## 3. 六场地的两层叙事

| 层 | Site | 机制标签 |
|---|---|---|
| Transport structure | A | Meshed flexibility |
| Transport structure | B | Barrier bottleneck |
| Transport structure | C | Sparse long-haul |
| Execution structure | D | Transfer bottleneck |
| Execution structure | E | Temporal volatility |
| Execution structure | F | Resource coupling |

R6的研究问题是：**deadline-aware supervision与cross-stage reservation的机制，能否跨不同transport/execution constraints重现？** 六场地是固定机制面板，不代表随机抽样的城市总体，也不构成只改变一个因素的城市因果实验。

每seed先计算12个site×scenario单元的FULL−LST差，再等权聚合；之后对完整seed block重采样。240条运行不是240个独立样本。R6保持240个核心单元，B2_FAST可选120；原R2–R5不乘六。

Figure 2/site-signature heatmap须由统一版本的签名生成器产出A–F。导入后的signal systems数量（E=408、D=59、F=49）只说明本版SUMO网络，统一导入参数包含 `--tls.join --tls.discard-simple --tls.default-type actuated`；这些数量不支持真实现场交通灯密度或城市优劣比较。

## 4. 当前阻塞与解除条件

当前阻塞为R1显式枚举达到预设状态上限，不是场地缺失或模型额度。后续应评估有正确性论证的状态归约或等价符号验证；保留本次未完成记录。若改变验证方法，先记录模型对应、覆盖边界和新版本，不能将随机深轨迹或本次浅层枚举改名为完整R1。
