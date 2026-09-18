# 六场地资产与状态

当前协议：[EXPERIMENT_PROTOCOL_v0.2](../design/EXPERIMENT_PROTOCOL_v0.2.md)。场地注册：[sites.v1.json](../config/sites.v1.json)。实测、选择与限制：[D/E/F落地报告](../design/SITES_D_E_F_IMPLEMENTATION_v0.2.md)。

新增真实OSM场地：D=莱比锡D_03，E=巴塞罗那E_02，F=柏林F_04。每类比较同一区域内五个重叠的3.2×3.2 km窗口；这不是十五座独立城市。原始道路数据及查询保存在 `sources/`，选择依据固定于 `selection_rule.json`。地图上的服务设施为模拟设置。

| 目录 | 内容 |
|---|---|
| `sources/D,E,F/` | OSM原始XML、查询、下载日期、端点、许可证与SHA-256 |
| `candidates/<ID>/` | 15个候选网络、边界、设施/路线/结构分数及转换日志 |
| `frozen/D,E,F/` | 入选地图、可直接加载SUMO配置、设施、兼容矩阵、事件、signature及诊断证据指针 |
| `figures/` | 三地图PNG/SVG |
| `archive/import_v1/` | 首轮信号导入、原选择与失败版本；不作当前地图 |
| `../fixtures/development/D,E,F/` | 开发fixture骨架；未冻结、不可直接作正式运输运行 |

`map_assets_frozen=true`只冻结本版地图资产；`formal_fixture_frozen=false`、`formal_admission=false`仍有效。通过SUMO路线和单载荷闭环不等于通过多任务、期限和资源竞争验收。A/B/C保留原有地图，其signature仍需按同一算法重算后才能画六场地定量热图。

常用命令（总工作区根目录，环境同已有实验）：

```powershell
python -X utf8 -B research_hscc2027/tools/site_screening/verify_sites.py
python -X utf8 -B research_hscc2027/tools/site_screening/diagnose_traffic.py --site E
python -X utf8 -B research_hscc2027/tools/site_screening/run_physical_checks.py
python -X utf8 -B research_hscc2027/tools/run_minimal_physical.py --site D
```

SUMO GUI可打开 `frozen/D/site.sumocfg`（E/F同理）。默认配置加载网络和路线表；动态探针车辆/道路事件由诊断脚本注入，单独打开GUI不代表已运行这些事件。

`screen_sites.py`是联网建图与筛选入口，拒绝覆盖已冻结地图；重建应先创建明确的新版本目录。`materialize_sites.py`生成开发资源与配置；正式冻结后不能直接对同一路径重建。`update_registry.py`刷新地图资产清单后，计划生成器需显式 `--refresh-design`，并再次校验。

原始数据：© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)，ODbL 1.0。地图转换依据 [SUMO官方OSM导入文档](https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html)。输出保留OSM来源，不把假设设施与道路数据混称实地测量。
