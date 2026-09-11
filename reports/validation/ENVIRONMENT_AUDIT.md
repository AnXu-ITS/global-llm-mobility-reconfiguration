# Environment Audit — Phase 0/1 (SUMO + BlueSky co-simulation)

**Date:** Phase 1
**Verdict:** Environment is usable; no reinstall required. Reused the existing
BlueSky virtual environment and added the missing SUMO/pyproj packages into it.

---

## 1. Interpreter & Python

| Item | Value |
|------|-------|
| Default system Python | 3.14.7 (`C:\Users\xuan1\AppData\Local\Python\pythoncore-3.14-64\python.exe`) |
| uv-provided interpreters | 3.11.16, 3.12.14 (available, unused) |
| **Project interpreter (all code)** | `C:\Users\xuan1\.venvs\bluesky\Scripts\python.exe` (Python **3.14.7**) |

All project scripts/tests are run with the BlueSky venv interpreter so that
`bluesky`, `sumo/traci`, `pyproj`, and plotting libraries coexist.

## 2. SUMO

| Item | Value |
|------|-------|
| Distribution | `eclipse-sumo==1.27.1` (pip wheel `py3-none-win_amd64`) |
| Companion data | `sumo-data==1.27.1` |
| `SUMO_HOME` (auto, via `import sumo`) | `C:\Users\xuan1\.venvs\bluesky\Lib\site-packages\sumo` |
| Binaries | `<SUMO_HOME>\bin\sumo.exe`, `sumo-gui.exe`, `netconvert.exe` |
| Python tools | `<SUMO_HOME>\tools\` (`traci`, `sumolib`) — **not importable by default** |

**Gotcha (handled):** the pip wheel does not put `traci`/`sumolib` on the import
path. `orchestrator/sumo_env.py` does `import sumo` (sets `SUMO_HOME`) then
appends `<SUMO_HOME>\tools` to `sys.path`. Every TraCI entry point calls
`sumo_env.setup()` first.

| Check | Result |
|-------|--------|
| `sumo` binary present | ✅ `...\sumo\bin\sumo.exe` |
| `netconvert` binary present | ✅ (network.net.xml built, 8.2 MB) |
| TraCI importable | ✅ (co-sim smoke test steps SUMO) |
| `--step-length 1` | ✅ (used by SumoAdapter) |

## 3. BlueSky

| Item | Value |
|------|-------|
| Source clone | `C:\Users\xuan1\OneDrive\桌面\学术agent\bluesky` (commit `dfdff5d`) |
| Import mode | in-process: `import bluesky as bs; bs.init(mode="sim", detached=True)` |
| OpenAP performance model | loaded ✅ |
| BADA performance model | not loaded (proprietary; expected) |
| Compiled geo functions | not loaded → Python fallback (benign warning) |
| RTree | not loaded (areafilter k-NN unavailable; unused) |

Aircraft types used (OpenAP rotor): `Amzn` (logistics), `M600` (medical),
`EC35` (passenger eVTOL proxy). The refined S0 fleet is sparse — 4 aircraft
(1 logistics + 1 eVTOL + 2 medical standby) — kept minimal so the project does
not become an air-congestion study.

## 4. Python dependencies (BlueSky venv)

| Package | Version | Role |
|---------|---------|------|
| eclipse-sumo | 1.27.1 | ground traffic (added this session) |
| sumo-data | 1.27.1 | SUMO data files (added this session) |
| pyproj | 3.7.2 | SUMO WGS84↔x/y projection (added this session) |
| numpy | 2.3.5 | numerical |
| scipy | 1.18.1 | numerical |
| matplotlib | 3.11.1 | unified scene figure |
| pandas | 3.0.5 | CSV/tabular |
| PyYAML | 6.0.3 | scenario config |
| openap | 2.6.0 | BlueSky aircraft performance |
| bluesky-navdata | — | BlueSky navigation database |
| msgpack | 1.2.2 | BlueSky networking |
| pyzmq | 27.2.0 | BlueSky networking |

**Absent (by design):** `requests`, `lxml`, `shapely` — OSM download uses
stdlib `urllib` (Overpass API); geometry uses pure-stdlib Haversine/point-to-
polyline code, so no `shapely` dependency is needed.

## 5. Network / data access

- OSM map + POIs fetched from the **Overpass API** (`https://overpass-api.de/api/map`
  and `/api/interpreter`) — succeeded (`sim/sumo/area.osm.xml`, 16.1 MB;
  `sim/sumo/osm_pois.json` with 1 hospital, 325 bridge ways, 49 industrial POIs).
- No network dependency at runtime; the co-sim runs fully offline from the
  generated `network.net.xml` and BlueSky's cached navdata.

## 6. Reuse vs. breakage

- **Reused unchanged:** the existing BlueSky venv (numpy/scipy/matplotlib/
  pandas/PyYAML/openap/PyQt6, BlueSky source clone, navdata cache).
- **Added (minimal):** `eclipse-sumo`, `sumo-data`, `pyproj` into the same venv.
  No global Python, no system SUMO install, no path changes outside the venv.
- The system SUMO/GUI and the BlueSky GUI were **not** disturbed.

## 7. Known benign warnings (not errors)

1. `Could not load compiled geo functions, Using Python-based geo functions` — Python fallback, identical results.
2. `Warning: RTree could not be loaded` — only affects areafilter k-NN, unused.
3. `Failed to load BADA performance model` — proprietary model absent; OpenAP used instead.
4. GBK-garbled Chinese names in console output — cosmetic; all files are UTF-8.

## 8. Conclusion

The environment satisfies all Phase-1 requirements: SUMO (headless + TraCI),
BlueSky (in-process sim), pyproj projection, plotting, and YAML/CSV tooling are
all present and exercised end-to-end by the smoke test. No reinstall is needed.
