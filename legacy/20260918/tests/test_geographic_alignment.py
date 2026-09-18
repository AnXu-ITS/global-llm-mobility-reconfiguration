"""T1 -- Geographic alignment validation.

For every shared landmark, round-trip the WGS84 coordinate through SUMO's
projection and measure the Haversine error:

    scenario_config WGS84 -> SUMO (x,y) -> SUMO geo-conversion -> WGS84
    -> Haversine(original, roundtrip)

Acceptance: median < 5 m, max < 15 m. Also records the road-snapping distance
for each facility from config/sumo_mapping.
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

OUT_CSV = ROOT / "outputs" / "geographic_alignment.csv"


def main() -> int:
    cfg = config_mod.load_config()
    net = sumolib.net.readNet(str(ROOT / "sim" / "sumo" / "network.net.xml"))
    fac = cfg["facilities"]
    mapping = cfg.get("sumo_mapping", {})

    rows = []
    for name, f in fac.items():
        lat, lon = f["lat"], f["lon"]
        x, y = net.convertLonLat2XY(lon, lat)
        lon_rt, lat_rt = net.convertXY2LonLat(x, y)
        err_m = haversine(lat, lon, lat_rt, lon_rt)
        snap_m = mapping.get(name, {}).get("snapped_distance_m", None)
        rows.append({
            "facility": name, "type": f["type"],
            "lat": lat, "lon": lon,
            "x": round(x, 3), "y": round(y, 3),
            "lat_rt": round(lat_rt, 8), "lon_rt": round(lon_rt, 8),
            "error_m": round(err_m, 4),
            "snapped_distance_m": snap_m,
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    errs = [r["error_m"] for r in rows]
    errs_sorted = sorted(errs)
    n = len(errs)
    median = (errs_sorted[n // 2] + errs_sorted[(n - 1) // 2]) / 2 if n else 0.0
    maxerr = max(errs)

    print("facility | type | error_m | snapped_m")
    for r in rows:
        print(f"{r['facility']:9s} | {r['type']:30s} | {r['error_m']:8.4f} | {r['snapped_distance_m']}")

    median_ok = median < 5.0
    max_ok = maxerr < 15.0
    passed = median_ok and max_ok
    print(f"\nmedian error = {median:.4f} m  (require < 5)  -> {'PASS' if median_ok else 'FAIL'}")
    print(f"max error    = {maxerr:.4f} m  (require < 15) -> {'PASS' if max_ok else 'FAIL'}")
    print(f"\nT1 geographic alignment: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
