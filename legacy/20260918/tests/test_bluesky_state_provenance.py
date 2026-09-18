"""BlueSky dynamics-provenance validation (post-resize).

Proves that UAV trajectory state is produced by the BlueSky simulator, not by
the Python Hub.  This test runs the BlueSky scene DIRECTLY (no SUMO, no
orchestrator stepping) and reads aircraft position/altitude/speed straight out
of the BlueSky runtime traffic object `bs.traf` at multiple simulation times.

Writes outputs/bluesky_state_provenance.csv and prints PASS/FAIL.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod           # noqa: E402
from orchestrator.bluesky_adapter import BlueSkyAdapter  # noqa: E402
from orchestrator.fleet import build_scene_commands, FLEET  # noqa: E402
from orchestrator.geo import haversine                    # noqa: E402

OUT_CSV = ROOT / "outputs" / "bluesky_state_provenance.csv"
# mission status per aircraft (mirrors fleet definition; for labelling only)
MISSION_STATUS = {acid: ("BUSY" if mid else "AVAILABLE") for acid, _r, _o, _d, _p, mid in FLEET}
WATCH = ["L-UAV-01", "EVTOL-01", "M-UAV-02"]   # 2 moving + 1 parked control
TIMES = [0, 30, 60, 90, 120]


def main() -> int:
    cfg = config_mod.load_config()
    adapter = BlueSkyAdapter(cfg)
    bs = adapter.bs
    for cmd in build_scene_commands(cfg):
        bs.stack.stack(cmd)

    rows = []
    positions = {acid: [] for acid in WATCH}
    # step to t=120; sample at requested times
    for t in range(0, 121):
        if t in TIMES:
            ids = [str(i) for i in bs.traf.id]
            for acid in WATCH:
                if acid not in ids:
                    continue
                i = ids.index(acid)
                lat = float(bs.traf.lat[i])
                lon = float(bs.traf.lon[i])
                alt = float(bs.traf.alt[i])
                spd = float(bs.traf.tas[i])
                positions[acid].append((lat, lon))
                rows.append({
                    "simulation_time_s": t,
                    "aircraft_id": acid,
                    "lat_from_bluesky": round(lat, 8),
                    "lon_from_bluesky": round(lon, 8),
                    "altitude_from_bluesky": round(alt, 3),
                    "speed_from_bluesky": round(spd, 3),
                    "source_object_or_api": "bs.traf.lat/lon/alt/tas (BlueSky traffic array)",
                    "mission_status": MISSION_STATUS[acid],
                })
        adapter.step()

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # movement check: first vs last sampled position
    ok = True
    for acid in WATCH:
        if len(positions[acid]) < 2:
            print(f"[FAIL] {acid}: fewer than 2 sampled positions")
            ok = False
            continue
        (lat0, lon0) = positions[acid][0]
        (lat1, lon1) = positions[acid][-1]
        dist = haversine(lat0, lon0, lat1, lon1)
        print(f"{acid}: t={TIMES[0]}->{TIMES[-1]} displacement = {dist:.1f} m")
    # authoritative assertion: the two busy aircraft MUST move; the parked one MUST NOT
    moved_l = haversine(*positions["L-UAV-01"][0], *positions["L-UAV-01"][-1])
    moved_e = haversine(*positions["EVTOL-01"][0], *positions["EVTOL-01"][-1])
    parked_m = haversine(*positions["M-UAV-02"][0], *positions["M-UAV-02"][-1])
    if moved_l < 50.0 or moved_e < 50.0:
        print("[FAIL] a BUSY aircraft did not move -> BlueSky dynamics not advancing")
        ok = False
    if parked_m > 20.0:
        print("[FAIL] parked M-UAV-02 moved -> possible position faking / spurious drift")
        ok = False

    print(f"\nL-UAV-01 moved {moved_l:.1f} m; EVTOL-01 moved {moved_e:.1f} m; "
          f"M-UAV-02 (parked) moved {parked_m:.1f} m")
    print(f"provenance: {'PASS' if ok else 'FAIL'} "
          f"(positions read directly from bs.traf; no Python Hub position stepping)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
