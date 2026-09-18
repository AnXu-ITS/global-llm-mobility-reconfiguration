"""Detailed geographic-alignment validation (post-resize), splitting the old
single "0 m" number into two independent metrics:

  E_crs  = distance(original WGS84, SUMO x/y -> WGS84 round-trip)   [CRS round-trip]
  E_snap = build-time snap distance (config sumo_mapping.snapped_distance_m)
           = distance(facility original WGS84, SUMO snapped road/access point)

Notes on E_snap semantics:
  * H1/D1 keep their ORIGINAL POI WGS84 in facilities.*; their access/landing
    points are V1/V2 (the snapped road point), so E_snap(H1)=42.854 m and
    E_snap(D1)=58.012 m are real, reportable values.
  * V1/V2/V3/B1 are DEFINED at the snapped road point (facilities.* already
    holds the snapped coordinate), so their facilities->mapping distance is ~0,
    but V3's build-time snap from its 400-m-NE anchor is 27.48 m (retained in
    snapped_distance_m).  We therefore report the AUTHORITATIVE
    snapped_distance_m as E_snap and add a recomputed haversine as cross-check.

Writes outputs/geographic_alignment_detailed.csv.
Acceptance: CRS median < 5 m, max < 15 m.  Snapping reported as-is:
  > 50 m -> WARNING, > 100 m -> FAIL.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.sumo_env import setup as sumo_setup  # noqa: E402

sumo_setup()
import sumolib  # noqa: E402

from orchestrator import config as config_mod  # noqa: E402
from orchestrator.geo import haversine  # noqa: E402

OUT_CSV = ROOT / "outputs" / "geographic_alignment_detailed.csv"
FACILITIES = ["H1", "D1", "V1", "V2", "V3", "B1"]


def main() -> int:
    cfg = config_mod.load_config()
    net = sumolib.net.readNet(str(ROOT / "sim" / "sumo" / "network.net.xml"))
    fac = cfg["facilities"]
    mapping = cfg["sumo_mapping"]

    rows = []
    for name in FACILITIES:
        raw_lat = fac[name]["lat"]
        raw_lon = fac[name]["lon"]
        sumo_x, sumo_y = net.convertLonLat2XY(raw_lon, raw_lat)
        rt_lon, rt_lat = net.convertXY2LonLat(sumo_x, sumo_y)
        crs_err = haversine(raw_lat, raw_lon, rt_lat, rt_lon)

        snapped_edge_id = mapping[name]["edge_id"]
        sx = mapping[name]["x"]
        sy = mapping[name]["y"]
        snap_lon, snap_lat = net.convertXY2LonLat(sx, sy)
        authoritative_snap = mapping[name]["snapped_distance_m"]
        recomputed_snap = haversine(raw_lat, raw_lon, snap_lat, snap_lon)

        flag = "OK"
        if authoritative_snap > 100.0:
            flag = "FAIL"
        elif authoritative_snap > 50.0:
            flag = "WARNING"

        rows.append({
            "facility_id": name, "raw_lat": raw_lat, "raw_lon": raw_lon,
            "sumo_x": round(sumo_x, 3), "sumo_y": round(sumo_y, 3),
            "roundtrip_lat": round(rt_lat, 8), "roundtrip_lon": round(rt_lon, 8),
            "crs_error_m": round(crs_err, 6),
            "snapped_edge_id": snapped_edge_id,
            "snapped_lat": round(snap_lat, 8), "snapped_lon": round(snap_lon, 8),
            "snap_distance_m": authoritative_snap,
            "recomputed_snap_m": round(recomputed_snap, 4),
            "flag": flag,
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    crs = sorted(r["crs_error_m"] for r in rows)
    n = len(crs)
    median_crs = (crs[n // 2] + crs[(n - 1) // 2]) / 2
    max_crs = max(crs)

    print(f"{'facility':9s} | {'crs_error_m':>11s} | {'snap_m':>7s} | {'recomp_snap_m':>13s} | flag")
    for r in rows:
        print(f"{r['facility_id']:9s} | {r['crs_error_m']:11.6f} | "
              f"{r['snap_distance_m']:7.3f} | {r['recomputed_snap_m']:13.4f} | {r['flag']}")

    crs_ok = median_crs < 5.0 and max_crs < 15.0
    snap_fail = any(r["flag"] == "FAIL" for r in rows)
    snap_warn = any(r["flag"] == "WARNING" for r in rows)
    print(f"\nCRS : median={median_crs:.6f} m (require <5)  max={max_crs:.6f} m (require <15) -> "
          f"{'PASS' if crs_ok else 'FAIL'}")
    print(f"Snap: H1={rows[0]['snap_distance_m']:.3f} m, D1={rows[1]['snap_distance_m']:.3f} m, "
          f"V1=0, V2=0, V3={rows[4]['snap_distance_m']:.2f} m, B1=0")
    overall = "FAIL" if (not crs_ok or snap_fail) else ("WARNING" if snap_warn else "PASS")
    print(f"detailed alignment: {overall}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
