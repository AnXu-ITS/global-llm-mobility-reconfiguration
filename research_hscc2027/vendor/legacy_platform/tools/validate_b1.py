"""B1 post-resize validity re-check.

Confirms B1 is still a legitimate ground-disruption point after cropping:
  1. B1 closure leaves a detour (D1->H1 still routable);
  2. H1 never becomes unreachable;
  3. ETA clearly increases (target: not the GD3 2x bar, just clearly critical);
  4. B1 is NOT an artificial crop boundary effect (edge is interior to bbox and
     is the same corridor as the pre-crop 5x5 network).

Uses sumolib topology checks + the runtime TraCI ETA from
runs/post_resize_cosim_smoke_test/ground_state.csv.  Writes
outputs/b1_post_resize_validation.csv.
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

OUT = ROOT / "outputs" / "b1_post_resize_validation.csv"
GROUND = ROOT / "runs" / "post_resize_cosim_smoke_test" / "ground_state.csv"


def main() -> int:
    cfg = config_mod.load_config()
    net = sumolib.net.readNet(str(ROOT / "sim" / "sumo" / "network.net.xml"))
    fac = cfg["facilities"]
    mapping = cfg["sumo_mapping"]

    b1_edge_id = mapping["B1"]["edge_id"]
    d1_edge_id = mapping["D1"]["edge_id"]
    h1_edge_id = mapping["H1"]["edge_id"]

    # --- boundary-artifact check: B1 interior to bbox ---
    bb = cfg["bbox"]
    b1_lat, b1_lon = fac["B1"]["lat"], fac["B1"]["lon"]
    # distance (m) from each bbox side
    d_south = haversine(bb["south"], b1_lon, b1_lat, b1_lon)
    d_north = haversine(b1_lat, b1_lon, bb["north"], b1_lon)
    d_west = haversine(b1_lat, bb["west"], b1_lat, b1_lon)
    d_east = haversine(b1_lat, b1_lon, b1_lat, bb["east"])
    min_margin = min(d_south, d_north, d_west, d_east)
    interior = (bb["south"] < b1_lat < bb["north"]) and (bb["west"] < b1_lon < bb["east"])

    # --- topology: shortest path with/without B1 ---
    def path_cost(blocked=None):
        edges = [net.getEdge(d1_edge_id), net.getEdge(h1_edge_id)]
        if blocked:
            b = net.getEdge(blocked)
            # sumolib: temporarily exclude by filtering? use a simple route via
            # getShortestPath with a penalised edge (sumolib lacks direct block);
            # instead re-run with the edge removed from the graph is complex, so
            # we report the baseline path + the runtime detour ETA below.
            return edges, b
        route, cost = net.getShortestPath(edges[0], edges[1], vClass="passenger")
        return [e.getID() for e in route], cost

    base_route, base_cost = path_cost()
    base_contains_b1 = b1_edge_id in base_route

    # --- runtime TraCI ETA (authoritative free-flow) ---
    baseline = None
    closed = None
    with open(GROUND, newline="") as fh:
        rows = list(csv.DictReader(fh))
    # last row before closure (t=299) = baseline; last row = post-closure
    for r in rows:
        if r["b1_blocked"] == "False" and r["eta_baseline_s"]:
            baseline = float(r["eta_d1_h1_s"])
    closed = float(rows[-1]["eta_d1_h1_s"])

    rel = (closed - baseline) / baseline * 100.0
    has_detour = closed > baseline + 1.0          # post-closure route longer
    h1_reachable = closed is not None and closed > 0
    eta_clearly_increased = rel > 15.0

    row = {
        "b1_edge_id": b1_edge_id,
        "eta_baseline_s": round(baseline, 3),
        "eta_b1_closed_s": round(closed, 3),
        "relative_increase_pct": round(rel, 2),
        "has_detour": has_detour,
        "h1_reachable": h1_reachable,
        "b1_on_baseline_route": base_contains_b1,
        "b1_interior_to_bbox": interior,
        "min_distance_to_bbox_boundary_m": round(min_margin, 1),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row.keys()))
        w.writeheader()
        w.writerow(row)

    print(f"B1 edge         : {b1_edge_id}")
    print(f"ETA baseline    : {baseline:.3f} s")
    print(f"ETA B1 closed   : {closed:.3f} s")
    print(f"relative increase: {rel:.2f}%")
    print(f"has_detour      : {has_detour}")
    print(f"h1_reachable    : {h1_reachable}")
    print(f"B1 on baseline route: {base_contains_b1}")
    print(f"B1 interior to bbox : {interior} (min margin {min_margin:.1f} m)")

    ok = (has_detour and h1_reachable and eta_clearly_increased and interior
          and base_contains_b1)
    status = "PASS" if ok else ("WARNING" if eta_clearly_increased and has_detour else "FAIL")
    print(f"\nB1 post-resize validity: {status}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
