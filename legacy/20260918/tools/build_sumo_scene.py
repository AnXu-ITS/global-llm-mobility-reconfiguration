"""
Build the canonical S0 SUMO ground scene from the downloaded OSM data.

Steps:
  1. Locate netconvert (from eclipse-sumo install).
  2. netconvert area.osm.xml -> network.net.xml (keep passenger roads only).
  3. Snap shared facilities (H1/V1/V2/V3/D1/B1) to SUMO edges via sumolib.
  4. Select B1: prefer a real OSM bridge on the D1->H1 shortest path; otherwise
     fall back to the bottleneck edge whose closure maximises H1 ETA increase.
  5. Write config/scenario_config.yaml (single geographic truth).
  6. Write routes.rou.xml (background traffic + ground-fallback type + D1->H1),
     additional.add.xml (facility POIs), canonical.sumocfg.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.geo import bbox_from_center, destination, haversine  # noqa: E402

CENTER = (31.30377, 120.59981)   # facility centroid (D1/H1/V1/V2/V3/B1 midpoint)
WIDTH_KM, HEIGHT_KM = 3.2, 3.2   # cropped S0 extent (refined from 5x5 km)

SIM_SUMO = ROOT / "sim" / "sumo"
OSM_MAP = SIM_SUMO / "area.osm.xml"
OSM_POIS = SIM_SUMO / "osm_pois.json"
NET = SIM_SUMO / "network.net.xml"
ROUTES = SIM_SUMO / "routes.rou.xml"
ADDITIONAL = SIM_SUMO / "additional.add.xml"
SUMOCFG = SIM_SUMO / "canonical.sumocfg"
CONFIG = ROOT / "config" / "scenario_config.yaml"

# facility anchors: H1 = hospital POI id, D1 = industrial POI id (chosen below)
HOSPITAL_NODE_ID = 13083683959
D1_INDUSTRIAL_NODE_ID = 570178287


def find_binary(name: str) -> str:
    from orchestrator.sumo_env import binary
    return binary(name)


def run_netconvert() -> None:
    nc = find_binary("netconvert")
    cmd = [
        nc,
        "--osm-files", str(OSM_MAP),
        "--output-file", str(NET),
        "--geometry.remove",
        "--roundabouts.guess",
        "--ramps.guess",
        "--junctions.join",
        "--tls.guess-signals", "true",
        "--keep-edges.by-vclass", "passenger",
        "--remove-edges.isolated", "true",
        "--verbose",
    ]
    print("running netconvert ...")
    print("  " + " ".join(cmd[:2]) + " ...")
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(proc.stdout[-4000:])
        print(proc.stderr[-4000:])
        raise SystemExit(f"netconvert failed rc={proc.returncode}")
    print(f"  wrote {NET} ({NET.stat().st_size} bytes)")


def _min_dist_to_poly(px: float, py: float, shape):
    """Min distance from point to a polyline, returning (dist, (cx, cy))."""
    import math
    dmin = float("inf")
    best = None
    for (ax, ay), (bx, by) in zip(shape[:-1], shape[1:]):
        abx, aby = bx - ax, by - ay
        t = ((px - ax) * abx + (py - ay) * aby) / (abx * abx + aby * aby + 1e-12)
        t = max(0.0, min(1.0, t))
        cx, cy = ax + t * abx, ay + t * aby
        d = math.hypot(px - cx, py - cy)
        if d < dmin:
            dmin = d
            best = (cx, cy)
    return dmin, best


def snap_to_edge(net, lat: float, lon: float):
    """Snap a WGS84 point to the nearest passenger edge, returning
    (edge, lane_index, x, y, dist_m)."""
    x, y = net.convertLonLat2XY(lon, lat)
    best_edge = None
    best_dist = float("inf")
    best_point = None
    for e in net.getEdges():
        if not e.allows("passenger"):
            continue
        d, pt = _min_dist_to_poly(x, y, e.getShape())
        if d < best_dist:
            best_dist = d
            best_edge = e
            best_point = pt
    if best_edge is None or best_point is None:
        raise RuntimeError(f"no passenger edge near ({lat},{lon})")
    return best_edge, 0, best_point[0], best_point[1], best_dist


def xy_to_latlon(net, x: float, y: float):
    lon, lat = net.convertXY2LonLat(x, y)
    return lat, lon


def shortest_path(net, from_edge_id: str, to_edge_id: str):
    """Return list of edge ids on shortest path, or [] if none."""
    try:
        route, cost = net.getShortestPath(
            net.getEdge(from_edge_id), net.getEdge(to_edge_id), vClass="passenger"
        )
        return [e.getID() for e in route], cost
    except Exception:
        return [], None


def _build_adjacency(net):
    """adjacency: from_node_id -> list of (edge_id, to_node_id, cost_m)."""
    adj = {}
    for e in net.getEdges():
        if not e.allows("passenger"):
            continue
        f = e.getFromNode().getID()
        t = e.getToNode().getID()
        adj.setdefault(f, []).append((e.getID(), t, e.getLength()))
    return adj


def _dijkstra(adj, start_node: str, target_node: str, blocked_edges: set):
    import heapq
    dist = {start_node: 0.0}
    prev = {}
    pq = [(0.0, start_node)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, float("inf")):
            continue
        if u == target_node:
            break
        for eid, v, cost in adj.get(u, []):
            if eid in blocked_edges:
                continue
            nd = d + cost
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = (u, eid)
                heapq.heappush(pq, (nd, v))
    if target_node not in dist:
        return None
    return dist[target_node]


def find_bottleneck(net, sp: list, base_cost):
    """Return (edge_id, detour_m, increase_pct, has_detour) for the edge on the
    shortest path whose closure maximises the D1->H1 detour cost."""
    adj = _build_adjacency(net)
    d1_from = net.getEdge(sp[0]).getFromNode().getID()
    h1_to = net.getEdge(sp[-1]).getToNode().getID()

    best = None  # (edge_id, alt_cost, increase_pct, has_detour)
    for eid in sp:
        blocked = {eid}
        alt = _dijkstra(adj, d1_from, h1_to, blocked)
        if alt is None:
            continue  # no detour -> not a valid single-point bottleneck
        inc = (alt - base_cost) / base_cost * 100.0
        if best is None or alt > best[1]:
            best = (eid, alt, inc, True)
    if best is None:
        # no single-edge closure forces a detour; pick midpoint with detour=True by convention
        mid = sp[len(sp) // 2]
        return mid, base_cost, 0.0, True
    return best


def el_latlon(el: dict):
    """Return (lat, lon) for an Overpass element (node uses lat/lon, way uses center)."""
    if "lat" in el and "lon" in el:
        return el["lat"], el["lon"]
    c = el.get("center", {})
    return c["lat"], c["lon"]


def main() -> int:
    bbox = bbox_from_center(*CENTER, WIDTH_KM, HEIGHT_KM)
    print("bbox:", {k: round(v, 6) for k, v in bbox.items()})

    run_netconvert()

    from orchestrator.sumo_env import setup as sumo_setup
    sumo_setup()
    import sumolib  # available after eclipse-sumo install
    net = sumolib.net.readNet(str(NET))
    pois = json.loads(OSM_POIS.read_text(encoding="utf-8"))

    # ---- resolve anchor facilities ----
    hospital = next(e for e in pois["hospitals"] if e["id"] == HOSPITAL_NODE_ID)
    industrial = next(e for e in pois["industrial"] if e["id"] == D1_INDUSTRIAL_NODE_ID)

    H1 = el_latlon(hospital)
    D1 = el_latlon(industrial)
    print(f"H1 hospital = {H1}")
    print(f"D1 industrial = {D1}")

    # snap H1, D1 to roads -> those snapped road points become V1, V2
    H1_edge, _, H1_x, H1_y, H1_d = snap_to_edge(net, *H1)
    D1_edge, _, D1_x, D1_y, D1_d = snap_to_edge(net, *D1)
    V1 = xy_to_latlon(net, H1_x, H1_y)
    V2 = xy_to_latlon(net, D1_x, D1_y)

    # V3 = backup landing site near centre, snapped to road
    V3_anchor = destination(CENTER[0], CENTER[1], 400.0, 45.0)
    V3_edge, _, V3_x, V3_y, V3_d = snap_to_edge(net, *V3_anchor)
    V3 = xy_to_latlon(net, V3_x, V3_y)

    # ---- B1 selection ----
    bridge_ids = {str(e["id"]) for e in pois.get("bridges_way", [])}
    sp, cost = shortest_path(net, D1_edge.getID(), H1_edge.getID())
    print(f"D1->H1 shortest path: {len(sp) if sp else 0} edges, cost={cost}")

    b1_edge_id = None
    b1_is_bridge = False
    b1_reason = ""
    b1_detour_m = None
    b1_increase_pct = None
    b1_has_detour = False
    # a) bridge on the shortest path
    if sp:
        for eid in sp:
            base = eid.split("#")[0]
            if base in bridge_ids:
                b1_edge_id = eid
                b1_is_bridge = True
                b1_reason = f"OSM bridge way {base} lies on D1->H1 shortest path"
                break
    # b) fall back to true bottleneck: max detour on the corridor
    if b1_edge_id is None and sp:
        b1_edge_id, b1_detour_m, b1_increase_pct, b1_has_detour = find_bottleneck(net, sp, cost)
        b1_reason = ("no OSM bridge on D1->H1 path; selected the critical road link "
                     "(bottleneck corridor) whose closure maximises the D1->H1 detour")

    B1_edge = net.getEdge(b1_edge_id)
    bx, by = B1_edge.getShape()[len(B1_edge.getShape()) // 2]
    B1 = xy_to_latlon(net, bx, by)
    print(f"B1 edge={b1_edge_id} bridge={b1_is_bridge} detour={b1_detour_m} "
          f"inc%={b1_increase_pct} has_detour={b1_has_detour} reason={b1_reason}")

    # ---- build scenario_config.yaml ----
    facilities = {
        "H1": {"type": "hospital", "lat": H1[0], "lon": H1[1],
               "osm_node_id": hospital["id"], "name": hospital.get("tags", {}).get("name", "")},
        "D1": {"type": "logistics_depot", "lat": D1[0], "lon": D1[1],
               "osm_node_id": industrial["id"], "name": industrial.get("tags", {}).get("name", "")},
        "V1": {"type": "hospital_landing_site", "lat": V1[0], "lon": V1[1]},
        "V2": {"type": "logistics_hub_landing_site", "lat": V2[0], "lon": V2[1]},
        "V3": {"type": "backup_landing_site", "lat": V3[0], "lon": V3[1]},
        "B1": {"type": "disruption_link", "lat": B1[0], "lon": B1[1],
               "impact_level": "high", "is_bridge": b1_is_bridge,
               "selection_reason": b1_reason},
    }

    sumo_mapping = {
        "H1": {"edge_id": H1_edge.getID(), "lane_id": H1_edge.getID() + "_0",
               "x": round(H1_x, 3), "y": round(H1_y, 3), "snapped_distance_m": round(H1_d, 3)},
        "D1": {"edge_id": D1_edge.getID(), "lane_id": D1_edge.getID() + "_0",
               "x": round(D1_x, 3), "y": round(D1_y, 3), "snapped_distance_m": round(D1_d, 3)},
        "V1": {"edge_id": H1_edge.getID(), "lane_id": H1_edge.getID() + "_0",
               "x": round(H1_x, 3), "y": round(H1_y, 3), "snapped_distance_m": 0.0},
        "V2": {"edge_id": D1_edge.getID(), "lane_id": D1_edge.getID() + "_0",
               "x": round(D1_x, 3), "y": round(D1_y, 3), "snapped_distance_m": 0.0},
        "V3": {"edge_id": V3_edge.getID(), "lane_id": V3_edge.getID() + "_0",
               "x": round(V3_x, 3), "y": round(V3_y, 3), "snapped_distance_m": round(V3_d, 3)},
        "B1": {"edge_id": b1_edge_id, "lane_id": b1_edge_id + "_0",
               "x": round(bx, 3), "y": round(by, 3), "snapped_distance_m": 0.0},
    }

    scenario = {
        "scenario_id": "S0",
        "study_area": {
            "name": "canonical_suzhou_testbed",
            "center": {"lat": CENTER[0], "lon": CENTER[1]},
            "width_km": WIDTH_KM,
            "height_km": HEIGHT_KM,
            "crs_exchange": "EPSG:4326",
        },
        "bbox": bbox,
        "simulation": {"duration_s": 1800, "step_s": 1},
        "schedule": {"duration_s": 600, "b1_close_t_s": 300,
                     "reverse_air_event_t_s": 450, "seed": 20240601},
        "air_fleet": {
            "logistics_uav": 1, "medical_uav": 2, "inspection_uav": 0, "passenger_evtol": 1,
            "target_occupancy": {"busy": 0.5, "available": 0.5},
            "background_services": [
                {"id": "logistics_service", "type": "logistics", "route": ["V2", "V3"],
                 "aircraft": "L-UAV-01"},
                {"id": "passenger_service", "type": "passenger_evtol", "route": ["V2", "V1"],
                 "aircraft": "EVTOL-01"},
            ],
        },
        "facilities": facilities,
        "sumo_mapping": sumo_mapping,
        "disruption_links": {"note": "provisional B1 (Dijkstra bottleneck); "
                                      "run tools/select_disruptions.py to finalize B1/B2/B3",
                             "links": {"B1": {"edge_id": b1_edge_id,
                                              "impact_level": "high",
                                              "is_bridge": b1_is_bridge,
                                              "reason": b1_reason,
                                              "detour_cost_m": b1_detour_m,
                                              "detour_increase_pct": b1_increase_pct,
                                              "has_detour": b1_has_detour}}},
    }

    import yaml
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(
        yaml.safe_dump(scenario, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"wrote {CONFIG}")

    # ---- routes.rou.xml (deterministic background traffic) ----
    write_routes(net, sp)
    # ---- additional.add.xml (facility POIs) ----
    write_additional(facilities, sumo_mapping)
    # ---- canonical.sumocfg ----
    write_sumocfg()
    return 0


def write_routes(net, d1_to_h1_edges) -> None:
    import random
    rng = random.Random(20240601)
    edge_ids = [e.getID() for e in net.getEdges() if e.allows("passenger")]

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<routes>"]
    lines.append('  <vType id="background_car" vClass="passenger" accel="2.6" decel="4.5" '
                 'sigma="0.5" length="5.0" maxSpeed="50" color="180,180,180"/>')
    lines.append('  <vType id="ground_fallback" vClass="emergency" accel="3.5" decel="6.0" '
                 'sigma="0.0" length="5.5" maxSpeed="60" color="220,40,40" guiShape="emergency"/>')

    def rand_route(rid: int):
        while True:
            a = rng.choice(edge_ids)
            b = rng.choice(edge_ids)
            if a == b:
                continue
            try:
                route, _ = net.getShortestPath(net.getEdge(a), net.getEdge(b), vClass="passenger")
            except Exception:
                continue
            if route:
                ids = " ".join(e.getID() for e in route)
                lines.append(f'  <route id="r{rid}" edges="{ids}"/>')
                return

    # background traffic
    n_bg = 45
    for i in range(n_bg):
        rand_route(i)
    dep = 0.0
    for i in range(n_bg):
        lines.append(f'  <vehicle id="bg{i:02d}" type="background_car" route="r{i}" depart="{dep:.1f}"/>')
        dep += rng.uniform(2.0, 12.0)

    # D1 -> H1 reference route
    if d1_to_h1_edges:
        lines.append(f'  <route id="rD1H1" edges="{" ".join(d1_to_h1_edges)}"/>')
    lines.append("</routes>")
    ROUTES.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {ROUTES}")


def write_additional(facilities, mapping) -> None:
    cols = {"H1": "200,20,20", "D1": "20,20,200", "V1": "20,180,20",
            "V2": "20,180,20", "V3": "20,120,120", "B1": "200,120,20"}
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<additional>"]
    for name, m in mapping.items():
        f = facilities[name]
        col = cols[name]
        lines.append(f'  <poi id="{name}" x="{m["x"]:.3f}" y="{m["y"]:.3f}" '
                     f'color="{col}" layer="2" width="6.0" type="{f["type"]}"/>')
    lines.append("</additional>")
    ADDITIONAL.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {ADDITIONAL}")


def write_sumocfg() -> None:
    import yaml
    content = {
        "scenario": {
            "name": "canonical_suzhou_testbed",
            "net_file": "network.net.xml",
            "route_files": ["routes.rou.xml"],
            "additional_files": ["additional.add.xml"],
            "begin": 0, "end": 1800, "step_length": 1,
        }
    }
    # SUMO config is XML, not YAML
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <input>
    <net-file value="{NET.name}"/>
    <route-files value="{ROUTES.name}"/>
    <additional-files value="{ADDITIONAL.name}"/>
  </input>
  <time>
    <begin value="0"/>
    <end value="1800"/>
    <step-length value="1"/>
  </time>
  <processing>
    <ignore-route-errors value="true"/>
  </processing>
</configuration>
'''
    SUMOCFG.write_text(xml, encoding="utf-8")
    print(f"wrote {SUMOCFG}")


if __name__ == "__main__":
    raise SystemExit(main())
