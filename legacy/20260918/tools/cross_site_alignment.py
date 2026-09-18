"""Geographic alignment validation for Site B / Site C.

For each facility: WGS84 -> SUMO x/y -> WGS84 round-trip error (CRS) and the
build-time snap distance (facility POI -> snapped SUMO access point).

Acceptance (identical to Site A):
  CRS round-trip: median < 5 m AND max < 15 m
  snapping      : > 50 m = WARNING, > 100 m = FAIL

Writes outputs/cross_site/site_b_geographic_alignment.csv and
outputs/cross_site/site_c_geographic_alignment.csv.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod  # noqa: E402
from orchestrator.geo import haversine  # noqa: E402
from orchestrator.sumo_env import setup as sumo_setup  # noqa: E402

OUT_ROOT = ROOT / "outputs" / "cross_site"
FACILITIES = ["H1", "D1", "V1", "V2", "V3", "B1"]
SITES = {
    "b": "site_b_amsterdam",
    "c": "site_c_edmonton",
}


def run(site_key: str) -> dict:
    site_id = SITES[site_key]
    cfg = config_mod.load_config(ROOT / "config" / f"{site_id}_config.yaml")
    net_path = ROOT / "sim" / "sites" / site_id / "sumo" / "network.net.xml"
    sumo_setup()
    import sumolib
    net = sumolib.net.readNet(str(net_path))
    fac = cfg["facilities"]
    mapping = cfg["sumo_mapping"]

    rows = []
    for name in FACILITIES:
        raw_lat, raw_lon = fac[name]["lat"], fac[name]["lon"]
        sx, sy = net.convertLonLat2XY(raw_lon, raw_lat)
        rt_lon, rt_lat = net.convertXY2LonLat(sx, sy)
        crs_err = haversine(raw_lat, raw_lon, rt_lat, rt_lon)
        m = mapping[name]
        snap = m["snapped_distance_m"]
        flag = "OK"
        if snap > 100.0:
            flag = "FAIL"
        elif snap > 50.0:
            flag = "WARNING"
        rows.append({
            "facility_id": name, "raw_lat": raw_lat, "raw_lon": raw_lon,
            "sumo_x": round(sx, 3), "sumo_y": round(sy, 3),
            "roundtrip_lat": round(rt_lat, 8), "roundtrip_lon": round(rt_lon, 8),
            "crs_error_m": round(crs_err, 6),
            "snapped_edge_id": m["edge_id"],
            "snap_distance_m": snap,
            "campus_centroid_offset_m": fac[name].get("campus_centroid_offset_m", ""),
            "flag": flag,
        })
    out = OUT_ROOT / f"{site_key}_geographic_alignment.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    crs = sorted(r["crs_error_m"] for r in rows)
    n = len(crs)
    median_crs = (crs[n // 2] + crs[(n - 1) // 2]) / 2
    max_crs = max(crs)
    crs_ok = median_crs < 5.0 and max_crs < 15.0
    snap_fail = any(r["flag"] == "FAIL" for r in rows)
    snap_warn = any(r["flag"] == "WARNING" for r in rows)
    overall = "FAIL" if (not crs_ok or snap_fail) else ("WARNING" if snap_warn else "PASS")
    print(f"[{site_id}] CRS median={median_crs:.4f} m max={max_crs:.4f} m "
          f"({'PASS' if crs_ok else 'FAIL'})  snapping -> {overall}")
    for r in rows:
        print(f"  {r['facility_id']:4s} crs={r['crs_error_m']:.4f} m "
              f"snap={r['snap_distance_m']:.3f} m {r['flag']}")
    print(f"  wrote {out}")
    return {"site": site_id, "median_crs_m": median_crs, "max_crs_m": max_crs,
            "crs_pass": crs_ok, "overall": overall, "rows": rows}


def main() -> int:
    res = {}
    for k in ("b", "c"):
        site_id = SITES[k]
        cfg_path = ROOT / "config" / f"{site_id}_config.yaml"
        if not cfg_path.exists():
            print(f"[{site_id}] config missing -- skipping")
            continue
        res[k] = run(k)
    if not res:
        return 1
    return 0 if all(v["overall"] == "PASS" for v in res.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
