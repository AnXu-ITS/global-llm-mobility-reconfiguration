"""Derive + write the L2/L3/L4 compound geometry for Experiment 3.

Resolves every `derive:` block in `config/experiment3_matrix.yaml` into exact
lat/lon geometry from the frozen site coordinates (V1/V2/V3 in
`config/scenario_config.yaml`) and the frozen E2 corridor anchors. Mirrors the
E2 cross-site geometry procedure (protocol E3-EXT-GEOM-1).

Deterministic and reproducible: same sites -> same geometry. The output matrix
drops `derive` and carries exact values; `tools/audit_exp3_scenarios.py` verifies
the invariants afterwards. F1 (target), F3 (utm_state) and F4 (site) events carry
no geometry and are left untouched.

Usage:
    python tools/gen_exp3_geometry.py            # rewrite config/experiment3_matrix.yaml
    python tools/gen_exp3_geometry.py --check    # report only, do not write
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MATRIX = ROOT / "config" / "experiment3_matrix.yaml"


def load_sites() -> dict:
    cfg = yaml.safe_load((ROOT / "config" / "scenario_config.yaml").read_text(encoding="utf-8"))
    fac = cfg["facilities"]
    return {k: (float(fac[k]["lat"]), float(fac[k]["lon"])) for k in ("V1", "V2", "V3")}


def corridor_mid(a, b):
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def corridor_progress(a, b, p):
    return (a[0] + p * (b[0] - a[0]), a[1] + p * (b[1] - a[1]))


def _r(x, nd=7):
    return round(float(x), nd)


def resolution_tables():
    S = load_sites()
    v3v1_mid = corridor_mid(S["V3"], S["V1"])
    v2v1_052 = corridor_progress(S["V2"], S["V1"], 0.52)
    nw = (31.3140, 120.5870)  # frozen E2_F5_C1 NW corner (no asset, corridors clear)

    zones = {
        # L2_F1_F5 failure-B: cover the backup's V3->V1 recovery route
        "ZN-F5-E3-01": {"type": "circle", "lat": _r(v3v1_mid[0]), "lon": _r(v3v1_mid[1]),
                        "radius_m": 250},
        # L2_F2_F4 failure-A: degrade the critical aircraft (corridor 0.52, = E2_F2_C2)
        "ZN-F2-E3-01": {"type": "circle", "lat": _r(v2v1_052[0]), "lon": _r(v2v1_052[1]),
                        "radius_m": 100, "candidate_rule": "none"},
        # L2_F6_F5 failure-B: compound with ENV-F6-E3-01 to cover V3->V1
        "ZN-F5-E3-02": {"type": "circle", "lat": _r(v3v1_mid[0]), "lon": _r(v3v1_mid[1]),
                        "radius_m": 200},
        # L3_COMP_F2 failure-A: degrade logistics shuttle at V3 (= E2_F2_C1)
        "ZN-F2-E3-02": {"type": "circle", "lat": _r(S["V3"][0]), "lon": _r(S["V3"][1]),
                        "radius_m": 300, "candidate_rule": "none"},
        # L3_COMP_F5 failure-A: NW corner intrusion (= E2_F5_C1)
        "ZN-F5-E3-03": {"type": "circle", "lat": _r(nw[0]), "lon": _r(nw[1]),
                        "radius_m": 400},
        # L4_B failure-B: compound with ENV-F6-E3-02 to cover V3->V1
        "ZN-F5-E3-04": {"type": "circle", "lat": _r(v3v1_mid[0]), "lon": _r(v3v1_mid[1]),
                        "radius_m": 200},
        # L4_B failure-C: degrade the surviving backup (at V3)
        "ZN-F2-E3-03": {"type": "circle", "lat": _r(S["V3"][0]), "lon": _r(S["V3"][1]),
                        "radius_m": 300, "candidate_rule": "none"},
    }
    # F6 envelopes crossing the critical corridor, V3->V1 clear (= E2_F6_C2)
    env = {
        "ENV-F6-E3-01": {"type": "strip", "lat0": 31.3010, "lon0": 120.5970,
                         "heading_deg": 20, "half_width_m": 200, "length_m": 2000},
        "ENV-F6-E3-02": {"type": "strip", "lat0": 31.3010, "lon0": 120.5970,
                         "heading_deg": 20, "half_width_m": 200, "length_m": 2000},
    }
    return zones, env


def resolve(scenarios):
    zones, env = resolution_tables()
    changed = 0
    for scen in scenarios:
        for f in scen.get("failure_schedule", []):
            z = f.get("zone")
            if z is not None and "derive" in z:
                if z["id"] not in zones:
                    raise KeyError(f"no resolution for zone {z['id']}")
                z.update(zones[z["id"]])
                z.pop("derive")
                changed += 1
            e = f.get("envelope")
            if e is not None and "derive" in e:
                if e["id"] not in env:
                    raise KeyError(f"no resolution for envelope {e['id']}")
                e.update(env[e["id"]])
                e.pop("derive")
                changed += 1
            # F5 unknown_trajectory origin: SW of the resolved zone centre, heading east
            traj = f.get("unknown_trajectory")
            if traj is not None and "lat0" not in traj:
                if z is None or "lat" not in z:
                    raise KeyError(f"cannot place unknown_trajectory for {scen['id']}")
                traj["lat0"] = _r(z["lat"])
                traj["lon0"] = _r(z["lon"] - 0.0025)
                changed += 1
    return changed


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    doc = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
    e3 = doc["experiment3"]
    changed = resolve(e3["scenarios"])
    print(f"resolved {changed} derive block(s) across {len(e3['scenarios'])} scenarios")

    if args.check:
        return 0
    MATRIX.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"wrote {MATRIX}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
