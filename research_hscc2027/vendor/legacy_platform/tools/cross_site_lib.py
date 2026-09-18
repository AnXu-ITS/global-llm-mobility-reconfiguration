"""Cross-site testbed shared library (Site B Amsterdam / Site C Edmonton).

This module provides everything the cross-site pipeline needs:

  * Overpass downloads (highways-only OSM extract, water, bridges/tunnels, POIs)
    with mirror failover and retries,
  * netconvert wrapper using the EXACT Site A flags (comparable nets),
  * junction-level networkx graph + morphology metrics,
  * water-barrier / road-crossing classification via shapely,
  * edge-level routing (sumolib shortest path with temporary edge closure),
  * facility snapping and scene-file writers (SUMO + config YAML).

Site A (sim/sumo + config/scenario_config.yaml) is READ-ONLY for this pipeline:
nothing here ever writes to it.

Metric definitions (documented in reports/cross_site):
  * road_length_km          : sum of directional passenger-edge lengths
                              (a two-way road counts twice) -- identical
                              treatment on all three sites.
  * node_count              : SUMO junctions touched by >=1 passenger edge.
  * edge_count              : directional passenger edges.
  * intersection_density    : junctions with >=3 distinct neighbours per km2.
  * mean_node_degree        : mean number of distinct neighbouring junctions.
  * dead_end_ratio          : junctions with exactly 1 neighbour / all junctions.
  * gridness_proxy          : share of intersections that are 4-way.
  * road_spacing_proxy_m    : median nearest-neighbour distance between
                              intersections (>=3-way junctions).
  * shortest-path sampling  : 200 deterministic OD pairs over junctions in the
                              largest weakly-connected component (Euclidean
                              distance >= 200 m), length-weighted Dijkstra.
  * mean_od_circuity        : mean(network_km / euclidean_km) over sampled pairs.
  * route redundancy proxy  : over 60 sampled pairs, fraction for which EVERY
                              single-edge closure of the baseline path still
                              admits a detour within 1.5x baseline length.
  * water_crossing_count    : passenger edges whose geometry crosses any water
                              geometry in the bbox.
  * usable_crossings        : crossing edges whose OSM way is tagged bridge=yes
                              or tunnel=yes (engineered ground crossings).
  * boundary artifact check : crossing midpoint distance to bbox edge
                              (boundary_margin_m) plus the share of the detour
                              path within 150 m of the bbox boundary
                              (detour_boundary_share; >0.30 => artifact risk).
"""
from __future__ import annotations

import io as _io
import json
import math
import random
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.geo import bbox_from_center, haversine  # noqa: E402

# ----------------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------------
AREA_KM = 3.2
AREA_KM2 = AREA_KM * AREA_KM
HEADERS = {"User-Agent": "ground-air-llm-cosim/1.0 (academic cross-site testbed)"}
OVERPASS_INTERPRETERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://overpass-api.osm.ch/api/interpreter",
    "https://overpass.si/api/interpreter",
]
METRIC_SEED = 20240901
REDUNDANCY_PAIRS = 60
SP_PAIRS = 200
BOUNDARY_BAND_M = 150.0          # "close to the bbox edge" band for artifact test
BOUNDARY_ARTIFACT_SHARE = 0.30   # detour share inside the band => artifact risk
CROSSING_MARGIN_MIN_M = 300.0    # crossing must sit >= this far from bbox edge


def fmt_bbox(bbox: Dict[str, float]) -> str:
    return (f"s={bbox['south']:.6f},n={bbox['north']:.6f},"
            f"w={bbox['west']:.6f},e={bbox['east']:.6f}")


# ----------------------------------------------------------------------------
# Overpass I/O
# ----------------------------------------------------------------------------
def http_post(url: str, data: str, timeout: int = 300) -> bytes:
    req = urllib.request.Request(url, data=data.encode("utf-8"),
                                 headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def overpass_query_fast(q: str, timeout: int = 60) -> dict:
    """One attempt per mirror, short timeouts (for queries with a fallback)."""
    last_err: Optional[Exception] = None
    for mirror in OVERPASS_INTERPRETERS:
        try:
            payload = "data=" + urllib.parse.quote(q)
            raw = http_post(mirror, payload, timeout=timeout)
            if raw.strip().startswith(b"<"):
                return {"__xml__": raw}
            return json.loads(raw.decode("utf-8"))
        except Exception as ex:  # noqa: BLE001
            last_err = ex
            print(f"    [overpass] {mirror} failed: {type(ex).__name__}")
    raise RuntimeError(f"all Overpass mirrors failed: {last_err}")


def overpass_query(q: str, timeout: int = 300) -> dict:
    """POST an Overpass QL query, failing over across mirrors with retries."""
    last_err: Optional[Exception] = None
    for mirror in OVERPASS_INTERPRETERS:
        for attempt in range(2):
            try:
                payload = "data=" + urllib.parse.quote(q)
                raw = http_post(mirror, payload, timeout=timeout)
                if raw.strip().startswith(b"<"):
                    return {"__xml__": raw}
                return json.loads(raw.decode("utf-8"))
            except Exception as ex:  # noqa: BLE001
                last_err = ex
                print(f"    [overpass] {mirror} attempt {attempt+1} failed: "
                      f"{type(ex).__name__} {str(ex)[:100]}")
                time.sleep(4)
    raise RuntimeError(f"all Overpass mirrors failed: {last_err}")


def fetch_highways_osm(bbox: Dict[str, float]) -> bytes:
    """Highways-only OSM extract (ways + their nodes) for netconvert.

    Primary: interpreter QL query. Fallback: /api/map GET (full map; netconvert
    only consumes highway ways, so the result is equivalent for our pipeline).
    """
    s, w, n, e = bbox["south"], bbox["west"], bbox["north"], bbox["east"]
    q = (
        "[out:xml][timeout:240];\n"
        f'(way["highway"]({s},{w},{n},{e});\n'
        f' way["railway"]({s},{w},{n},{e}););\n'
        "(._;>;);\n"
        "out body;"
    )
    try:
        res = overpass_query(q, timeout=300)
        if "__xml__" in res:
            return res["__xml__"]
        raise RuntimeError("highways query returned JSON instead of XML")
    except Exception:  # noqa: BLE001
        print("    [overpass] interpreter failed for highways extract; "
              "trying /api/map fallback ...")
        for mirror in ["https://overpass-api.de", "https://overpass.kumi.systems",
                       "https://overpass.private.coffee"]:
            url = f"{mirror}/api/map?bbox={w:.6f},{s:.6f},{e:.6f},{n:.6f}"
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=600) as resp:
                    return resp.read()
            except Exception as ex:  # noqa: BLE001
                print(f"    [overpass] map fallback {mirror} failed: "
                      f"{type(ex).__name__}")
        raise RuntimeError("highways extract unavailable (interpreter + map)")


def pad_bbox(bbox: Dict[str, float], deg: float = 0.004) -> Dict[str, float]:
    """Pad a bbox (default ~300-440 m) so barrier geometries are not clipped."""
    return {
        "south": bbox["south"] - deg, "north": bbox["north"] + deg,
        "west": bbox["west"] - deg, "east": bbox["east"] + deg,
    }


def fetch_water(bbox: Dict[str, float], pad: bool = True) -> dict:
    s, w, n, e = (pad_bbox(bbox) if pad else bbox).values()
    q = (
        "[out:json][timeout:180];\n"
        f'(way["natural"="water"]({s},{w},{n},{e});\n'
        f' way["waterway"~"river|canal|stream|riverbank|dock|basin"]({s},{w},{n},{e});\n'
        f' relation["natural"="water"]({s},{w},{n},{e});\n'
        f' relation["waterway"~"river|canal|riverbank"]({s},{w},{n},{e}););\n'
        "out geom;"
    )
    return overpass_query_fast(q, timeout=60)


def fetch_bridges(bbox: Dict[str, float], pad: bool = True) -> dict:
    s, w, n, e = (pad_bbox(bbox) if pad else bbox).values()
    q = (
        "[out:json][timeout:60];\n"
        f'(way["bridge"="yes"]["highway"]({s},{w},{n},{e});\n'
        f' way["man_made"="bridge"]["highway"]({s},{w},{n},{e});\n'
        f' way["tunnel"="yes"]["highway"]({s},{w},{n},{e}););\n'
        "out geom;"
    )
    return overpass_query_fast(q, timeout=60)


def fetch_pois(bbox: Dict[str, float]) -> dict:
    s, w, n, e = bbox["south"], bbox["west"], bbox["north"], bbox["east"]
    q = (
        "[out:json][timeout:120];\n"
        f'(\n  node["amenity"~"hospital|clinic|doctors"]({s},{w},{n},{e});\n'
        f'  way["amenity"~"hospital|clinic|doctors"]({s},{w},{n},{e});\n'
        f'  node["healthcare"]({s},{w},{n},{e});\n'
        f'  way["healthcare"]({s},{w},{n},{e});\n'
        f'  node["landuse"="industrial"]({s},{w},{n},{e});\n'
        f'  way["landuse"="industrial"]({s},{w},{n},{e});\n'
        f'  node["building"~"warehouse|industrial|distribution"]({s},{w},{n},{e});\n'
        f'  way["building"~"warehouse|industrial|distribution"]({s},{w},{n},{e});\n'
        f'  way["landuse"="retail"]({s},{w},{n},{e});\n'
        f'  node["shop"~"mall|department_store"]({s},{w},{n},{e});\n'
        f'  way["shop"~"mall|department_store"]({s},{w},{n},{e});\n'
        f'  node["amenity"~"school|community_centre|university|college"]({s},{w},{n},{e});\n'
        f'  way["amenity"~"school|community_centre|university|college"]({s},{w},{n},{e});\n'
        f'  node["leisure"="sports_centre"]({s},{w},{n},{e});\n'
        f'  way["leisure"="sports_centre"]({s},{w},{n},{e});\n'
        f");\n"
        "out center;"
    )
    return overpass_query_fast(q, timeout=60)


# ----------------------------------------------------------------------------
# SUMO net building (Site A flags, unchanged)
# ----------------------------------------------------------------------------
def netconvert(osm_path: Path, net_path: Path,
               original_names: bool = False) -> Tuple[bool, str]:
    from orchestrator.sumo_env import binary
    nc = binary("netconvert")
    cmd = [
        nc,
        "--osm-files", str(osm_path),
        "--output-file", str(net_path),
        "--geometry.remove",
        "--roundabouts.guess",
        "--ramps.guess",
        "--junctions.join",
        "--tls.guess-signals", "true",
        "--keep-edges.by-vclass", "passenger",
        "--remove-edges.isolated", "true",
        "--verbose",
    ]
    if original_names:
        cmd += ["--output.original-names", "true"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=1800)
    except subprocess.TimeoutExpired:
        return False, "netconvert timeout"
    log = (proc.stdout or "")[-3000:] + "\n" + (proc.stderr or "")[-3000:]
    return proc.returncode == 0, log


def load_net(net_path: Path):
    from orchestrator.sumo_env import setup as sumo_setup
    sumo_setup()
    import sumolib
    return sumolib.net.readNet(str(net_path))


# ----------------------------------------------------------------------------
# graph construction + metrics
# ----------------------------------------------------------------------------
def build_junction_graph(net):
    """Return (networkx.Graph, positions, edge_meta).

    graph: junction-level, undirected-simple (unique neighbours), edge weight
           = average directional length between the two junctions.
    edge_meta: {edge_id: {length_m, speed_ms, time_s, highway, shape,
                          from_node, to_node, base_way}}
    """
    import networkx as nx
    g = nx.Graph()
    pos: Dict[str, Tuple[float, float]] = {}
    edge_meta: Dict[str, Dict[str, Any]] = {}
    for node in net.getNodes():
        pos[node.getID()] = node.getCoord()
    for e in net.getEdges():
        if not e.allows("passenger"):
            continue
        eid = e.getID()
        if ":" in eid:  # internal edge
            continue
        f = e.getFromNode().getID()
        t = e.getToNode().getID()
        length = e.getLength()
        speed = max(e.getSpeed(), 0.1)
        base_way = eid.lstrip("-").split("#")[0]
        edge_meta[eid] = {
            "length_m": length, "speed_ms": speed, "time_s": length / speed,
            "highway": str(e.getType()), "shape": e.getShape(),
            "from_node": f, "to_node": t, "base_way": base_way,
        }
        if g.has_edge(f, t):
            g[f][t]["weight"] = min(g[f][t]["weight"], length)
        else:
            g.add_edge(f, t, weight=length)
    return g, pos, edge_meta


def sample_od_pairs(g, pos, n: int, seed: int = METRIC_SEED):
    """Sample OD junction pairs (largest component, Euclid dist >= 200 m)."""
    import networkx as nx
    comps = [c for c in nx.connected_components(g) if len(c) >= 10]
    if not comps:
        return []
    nodes = sorted(max(comps, key=len))
    rng = random.Random(seed)
    pairs = []
    tries = 0
    while len(pairs) < n and tries < 20 * n:
        tries += 1
        a, b = rng.sample(nodes, 2)
        (ax, ay), (bx, by) = pos[a], pos[b]
        d = math.hypot(bx - ax, by - ay)
        if d >= 200.0:
            pairs.append((a, b))
    return pairs


def metrics_from_net(net, bbox: Dict[str, float]) -> Dict[str, Any]:
    import networkx as nx
    g, pos, edge_meta = build_junction_graph(net)
    xmin, ymin, xmax, ymax = net.getBoundary()

    total_len = sum(m["length_m"] for m in edge_meta.values())
    n_nodes = len(g.nodes)
    degs = [len(list(g.neighbors(v))) for v in g.nodes]
    n_inter = sum(1 for d in degs if d >= 3)
    n_dead = sum(1 for d in degs if d == 1)
    n_grid4 = sum(1 for d in degs if d == 4)

    # road spacing: median NN distance among >=3-way junctions
    inter_nodes = [v for v in g.nodes if len(list(g.neighbors(v))) >= 3]
    spacing = None
    if len(inter_nodes) >= 5:
        dnn = []
        for i, v in enumerate(inter_nodes):
            xv, yv = pos[v]
            best = min(
                math.hypot(pos[u][0] - xv, pos[u][1] - yv)
                for j, u in enumerate(inter_nodes) if j != i
            )
            dnn.append(best)
        dnn.sort()
        spacing = dnn[len(dnn) // 2]

    pairs = sample_od_pairs(g, pos, SP_PAIRS)
    sp_len = []
    circ = []
    for a, b in pairs:
        try:
            L = nx.shortest_path_length(g, a, b, weight="weight")
        except nx.NetworkXNoPath:
            continue
        (ax, ay), (bx, by) = pos[a], pos[b]
        eucl = math.hypot(bx - ax, by - ay)
        sp_len.append(L / 1000.0)
        if eucl > 0:
            circ.append(L / eucl)
    mean_sp = sum(sp_len) / len(sp_len) if sp_len else None
    median_sp = sorted(sp_len)[len(sp_len) // 2] if sp_len else None
    mean_circ = sum(circ) / len(circ) if circ else None

    comps = list(nx.connected_components(g))
    major = [c for c in comps if len(c) >= 10]
    largest_share = (len(max(comps, key=len)) / n_nodes) if comps and n_nodes else None

    # route redundancy proxy
    red_pairs = pairs[:REDUNDANCY_PAIRS]
    redundant = 0
    tested = 0
    for a, b in red_pairs:
        try:
            base_path = nx.shortest_path(g, a, b, weight="weight")
            base_L = nx.shortest_path_length(g, a, b, weight="weight")
        except nx.NetworkXNoPath:
            continue
        tested += 1
        ok = True
        gg = g.copy()
        for i in range(len(base_path) - 1):
            u, v = base_path[i], base_path[i + 1]
            w = gg[u][v]["weight"]
            gg.remove_edge(u, v)
            try:
                alt = nx.shortest_path_length(gg, u, v, weight="weight") + base_L - w
                if alt > 1.5 * base_L:
                    ok = False
                    break
            except nx.NetworkXNoPath:
                ok = False
                break
            gg.add_edge(u, v, weight=w)
        if ok:
            redundant += 1

    return {
        "road_length_km": total_len / 1000.0,
        "road_density_km_per_km2": (total_len / 1000.0) / AREA_KM2,
        "node_count": n_nodes,
        "edge_count": len(edge_meta),
        "intersection_count": n_inter,
        "intersection_density_per_km2": n_inter / AREA_KM2,
        "mean_node_degree": (sum(degs) / n_nodes) if n_nodes else None,
        "dead_end_ratio": n_dead / n_nodes if n_nodes else None,
        "gridness_4way_share": (n_grid4 / n_inter) if n_inter else None,
        "road_spacing_proxy_m": spacing,
        "mean_shortest_path_km": mean_sp,
        "median_shortest_path_km": median_sp,
        "mean_od_circuity": mean_circ,
        "n_components": len(comps),
        "n_major_components": len(major),
        "largest_component_share": largest_share,
        "route_redundancy_proxy": (redundant / tested) if tested else None,
        "sampled_pairs": len(sp_len),
        "boundary": {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax},
        "edge_meta": edge_meta,
    }


# ----------------------------------------------------------------------------
# water / crossing analysis
# ----------------------------------------------------------------------------
def _element_geometry(el: Dict[str, Any], net=None):
    """Return (shapely geometry or None, kind), projected to net UTM if given."""
    from shapely.geometry import LineString, Polygon
    geom = el.get("geometry")
    if not geom:
        return None, None
    tags = el.get("tags") or {}
    kind = tags.get("natural") or tags.get("waterway") or "water"
    if net is not None:
        coords = [net.convertLonLat2XY(p["lon"], p["lat"]) for p in geom]
    else:
        coords = [(p["lon"], p["lat"]) for p in geom]
    if len(coords) < 2:
        return None, None
    is_closed = coords[0] == coords[-1]
    if is_closed and len(coords) >= 4:
        try:
            poly = Polygon(coords)
            if poly.is_valid and poly.area > 0:
                return poly, kind
        except Exception:  # noqa: BLE001
            pass
    return LineString(coords), kind


def water_geometries(water_json: dict, net=None) -> List[Dict[str, Any]]:
    """Normalised list of {geom, kind, name, type, area_m2}.

    When `net` is given, geometries are projected into the net's UTM system
    (required for intersection with SUMO edges / area computation).
    """
    out = []
    for el in water_json.get("elements", []):
        geom, kind = _element_geometry(el, net=net)
        if geom is None:
            continue
        tags = el.get("tags") or {}
        name = tags.get("name", "")
        etype = "way" if el.get("type") == "way" else "relation"
        out.append({
            "geom": geom, "kind": kind, "name": name, "osm_type": etype,
            "area_m2": geom.area if hasattr(geom, "area") else geom.length * 6.0,
        })
    return out


def bbox_utm_polygon(net):
    """bbox polygon in SUMO UTM coordinates (shapely)."""
    from shapely.geometry import box
    xmin, ymin, xmax, ymax = net.getBoundary()
    return box(xmin, ymin, xmax, ymax)


def classify_crossings(net, edge_meta, water_geoms, bridge_json,
                       water_buffer_m: float = 4.0):
    """Classify passenger edges that cross water bodies.

    Returns dict edge_id -> {water_name, water_kind, crossing_kind,
                             midpoint_xy, boundary_margin_m}.
    crossing_kind in {bridge, tunnel, embankment(unclassified)}.
    """
    from shapely.geometry import LineString
    bridge_ids = set()
    tunnel_ids = set()
    for el in bridge_json.get("elements", []):
        tags = el.get("tags") or {}
        wid = str(el.get("id"))
        if tags.get("bridge") in ("yes", "true", "viaduct") or tags.get("man_made") == "bridge":
            bridge_ids.add(wid)
        if tags.get("tunnel") in ("yes", "true"):
            tunnel_ids.add(wid)

    xmin, ymin, xmax, ymax = net.getBoundary()
    crossings: Dict[str, Dict[str, Any]] = {}
    for eid, m in edge_meta.items():
        shape = m["shape"]
        line = LineString([(x, y) for x, y in shape])
        for w in water_geoms:
            geom = w["geom"]
            test = geom.buffer(water_buffer_m) if geom.geom_type == "LineString" else geom
            if not line.intersects(test):
                continue
            base = m["base_way"]
            if base in bridge_ids:
                ckind = "bridge"
            elif base in tunnel_ids:
                ckind = "tunnel"
            else:
                ckind = "embankment"
            mid = line.interpolate(0.5, normalized=True)
            margin = min(mid.x - xmin, xmax - mid.x, mid.y - ymin, ymax - mid.y)
            crossings[eid] = {
                "water_name": w["name"], "water_kind": w["kind"],
                "crossing_kind": ckind, "midpoint_xy": (mid.x, mid.y),
                "boundary_margin_m": margin,
            }
    return crossings


def point_side_of_water(pt_xy, w: Dict[str, Any]) -> Optional[int]:
    """Side of a water body: +1 / -1 / 0(on) / None (unknown)."""
    from shapely.geometry import Point
    geom = w["geom"]
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        if geom.contains(Point(*pt_xy)):
            return 0
        # use representative interior point and a test point far away
        return 1 if pt_xy[1] > geom.centroid.y else -1
    if geom.geom_type == "LineString":
        # signed side via cross product w.r.t. first segment
        coords = list(geom.coords)
        (ax, ay), (bx, by) = coords[0], coords[-1]
        cross = (bx - ax) * (pt_xy[1] - ay) - (by - ay) * (pt_xy[0] - ax)
        return 1 if cross > 0 else (-1 if cross < 0 else 0)
    return None


# ----------------------------------------------------------------------------
# routing (edge level, sumolib) + closure analysis
# ----------------------------------------------------------------------------
def snap_to_edge(net, lat: float, lon: float):
    """Snap a WGS84 point to the nearest passenger edge.

    Returns (edge, x, y, dist_m).
    """
    x, y = net.convertLonLat2XY(lon, lat)
    best_edge, best_dist, best_point = None, float("inf"), None
    for e in net.getEdges():
        if not e.allows("passenger"):
            continue
        d, pt = _min_dist_to_poly(x, y, e.getShape())
        if d < best_dist:
            best_dist, best_edge, best_point = d, e, pt
    if best_edge is None:
        raise RuntimeError(f"no passenger edge near ({lat},{lon})")
    return best_edge, best_point[0], best_point[1], best_dist


def _min_dist_to_poly(px, py, shape):
    dmin, best = float("inf"), None
    for (ax, ay), (bx, by) in zip(shape[:-1], shape[1:]):
        abx, aby = bx - ax, by - ay
        t = ((px - ax) * abx + (py - ay) * aby) / (abx * abx + aby * aby + 1e-12)
        t = max(0.0, min(1.0, t))
        cx, cy = ax + t * abx, ay + t * aby
        d = math.hypot(px - cx, py - cy)
        if d < dmin:
            dmin, best = d, (cx, cy)
    return dmin, best


def route_edges(traci, from_edge_id: str, to_edge_id: str):
    """Shortest path edge list via the TraCI router (same method as Site A)."""
    try:
        r = traci.simulation.findRoute(from_edge_id, to_edge_id)
        return list(r.edges) if r.edges else None
    except Exception:  # noqa: BLE001
        return None


def route_distance_m(net, edges: List[str]) -> float:
    return sum(net.getEdge(e).getLength() for e in edges)


def ff_eta(traci, edges: List[str]) -> float:
    """Free-flow ETA (s): lane length / lane max speed (Site A convention)."""
    eta = 0.0
    for e in edges:
        lane = f"{e}_0"
        speed = max(traci.lane.getMaxSpeed(lane), 1e-3)
        eta += traci.lane.getLength(lane) / speed
    return eta


def close_edge_route(traci, from_edge_id: str, to_edge_id: str, blocked: str):
    """Route with one edge temporarily disallowed for passenger (TraCI)."""
    traci.edge.setDisallowed(blocked, ["passenger"])
    try:
        return route_edges(traci, from_edge_id, to_edge_id)
    finally:
        traci.edge.setAllowed(blocked, ["passenger"])


def traci_session(net_path: Path, label: str):
    """Context manager for a headless TraCI session on a bare net."""
    import contextlib
    from orchestrator.sumo_env import setup as sumo_setup, binary
    sumo_setup()
    import traci

    @contextlib.contextmanager
    def _session():
        traci.start([binary("sumo"), "-n", str(net_path),
                     "--no-warnings", "true"], label=label)
        traci.simulationStep()
        try:
            yield traci
        finally:
            try:
                traci.close()
            except Exception:  # noqa: BLE001
                pass
    return _session()


def detour_boundary_share(net, route: List[str], band_m: float = BOUNDARY_BAND_M) -> float:
    """Share of the route length lying within `band_m` of the net boundary."""
    xmin, ymin, xmax, ymax = net.getBoundary()
    total, inside = 0.0, 0.0
    for eid in route:
        for x, y in net.getEdge(eid).getShape():
            d = min(x - xmin, xmax - x, y - ymin, ymax - y)
            if d < band_m:
                inside += 1
            total += 1
    return inside / total if total else 0.0


def closure_analysis(net, traci, d1_edge: str, h1_edge: str,
                     crossing_candidates: List[str]) -> Dict[str, Any]:
    """Baseline D1->H1 route + per-candidate single-edge closure analysis.

    Returns {baseline: {...}, closures: [rows sorted by eta increase desc]}.
    Free-flow ETA = lane length / lane max speed (Site A convention).
    """
    base_edges = route_edges(traci, d1_edge, h1_edge)
    if base_edges is None:
        return {"baseline": None, "closures": [], "unreachable": True}
    base_dist = route_distance_m(net, base_edges)
    base_eta = ff_eta(traci, base_edges)
    base = {"edges": base_edges, "eta_s": base_eta, "distance_m": base_dist}
    rows = []
    for eid in crossing_candidates:
        if eid in (d1_edge, h1_edge):
            rows.append({"edge_id": eid, "eta_s": None, "dist_m": None,
                         "increase_pct": None, "detour_exists": False,
                         "reason": "origin/destination edge"})
            continue
        r = close_edge_route(traci, d1_edge, h1_edge, eid)
        if r is None:
            rows.append({"edge_id": eid, "eta_s": None, "dist_m": None,
                         "increase_pct": None, "detour_exists": False,
                         "reason": "unreachable"})
            continue
        eta = ff_eta(traci, r)
        dist = route_distance_m(net, r)
        rows.append({
            "edge_id": eid, "eta_s": eta, "dist_m": dist,
            "increase_pct": (eta - base_eta) / base_eta * 100.0 if base_eta else None,
            "detour_exists": True, "reason": "",
            "detour_edges": r,
            "detour_boundary_share": detour_boundary_share(net, r),
        })
    rows.sort(key=lambda r: (r["increase_pct"] is None, -(r["increase_pct"] or 0)))
    return {"baseline": base, "closures": rows, "unreachable": False}


# ----------------------------------------------------------------------------
# POI helpers
# ----------------------------------------------------------------------------
def fetch_full_map(bbox: Dict[str, float]) -> bytes:
    """Full OSM map via /api/map GET (independent of the interpreter service)."""
    s, w, n, e = bbox["south"], bbox["west"], bbox["north"], bbox["east"]
    last_err: Optional[Exception] = None
    for mirror in ["https://overpass-api.de", "https://overpass.kumi.systems",
                   "https://overpass.private.coffee"]:
        for attempt in range(2):
            url = f"{mirror}/api/map?bbox={w:.6f},{s:.6f},{e:.6f},{n:.6f}"
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=240) as resp:
                    data = resp.read()
                if len(data) > 10_000:
                    return data
            except Exception as ex:  # noqa: BLE001
                last_err = ex
                print(f"    [osm-map] {mirror} attempt {attempt+1} failed: "
                      f"{type(ex).__name__}")
                time.sleep(3)
    raise RuntimeError(f"full map download failed: {last_err}")


def _parse_osm(xml_bytes: bytes):
    """Bounded-memory OSM XML parse.

    Returns (nodes, ways, rels, node_tags, way_tags, rel_tags) where:
      nodes    : id -> (lat, lon)
      ways     : id -> [node ids]
      rels     : id -> [(type, ref, role), ...]
      *_tags   : id -> {k: v} (captured for ALL elements)
    """
    import xml.etree.ElementTree as ET
    nodes: Dict[str, Tuple[float, float]] = {}
    ways: Dict[str, List[str]] = {}
    rels: Dict[str, List[Tuple[str, str, str]]] = {}
    node_tags: Dict[str, Dict[str, str]] = {}
    way_tags: Dict[str, Dict[str, str]] = {}
    rel_tags: Dict[str, Dict[str, str]] = {}
    stack: List[Tuple[str, str, Dict[str, str]]] = []
    for ev, elem in ET.iterparse(_io.BytesIO(xml_bytes), events=("start", "end")):
        if ev == "start":
            if elem.tag in ("node", "way", "relation"):
                stack.append((elem.tag, elem.get("id"), {}))
                if elem.tag == "node":
                    nodes[elem.get("id")] = (float(elem.get("lat")),
                                             float(elem.get("lon")))
            elif elem.tag == "nd" and stack and stack[-1][0] == "way":
                ways.setdefault(stack[-1][1], []).append(elem.get("ref"))
            elif elem.tag == "member" and stack and stack[-1][0] == "relation":
                rels.setdefault(stack[-1][1], []).append(
                    (elem.get("type"), elem.get("ref"), elem.get("role")))
            elif elem.tag == "tag" and stack:
                stack[-1][2][elem.get("k")] = elem.get("v")
        else:  # end
            if elem.tag in ("node", "way", "relation"):
                kind, eid, tags = stack.pop()
                if kind == "node":
                    node_tags[eid] = tags
                elif kind == "way":
                    way_tags[eid] = tags
                else:
                    rel_tags[eid] = tags
            elem.clear()
    return nodes, ways, rels, node_tags, way_tags, rel_tags


def _rel_rings(rel_id: str, ways, rels, _visited=None):
    """Assemble outer ring node-id chains for a multipolygon relation."""
    _visited = _visited or set()
    if rel_id in _visited:
        return []
    _visited.add(rel_id)
    members = rels.get(rel_id)
    if not members:
        return []
    chains: List[List[str]] = []
    for mtype, ref, role in members:
        if role not in ("outer", ""):
            continue
        if mtype == "way" and ref in ways:
            chains.append(list(ways[ref]))
        elif mtype == "relation":
            chains.extend(_rel_rings(ref, ways, rels, _visited))
    rings: List[List[str]] = []
    while chains:
        chain = chains.pop(0)
        grew = True
        while grew:
            grew = False
            for other in list(chains):
                if chain[0] == other[-1]:
                    chain = other[:-1] + chain
                    chains.remove(other)
                    grew = True
                elif chain[-1] == other[0]:
                    chain = chain + other[1:]
                    chains.remove(other)
                    grew = True
        rings.append(chain)
    return rings


def parse_full_map_water(xml_bytes: bytes) -> dict:
    """Extract water elements (way/relation) from a full OSM map download,
    in Overpass-`out geom` JSON shape."""
    nodes, ways, rels, _nt, way_tags, rel_tags = _parse_osm(xml_bytes)
    elements = []
    for wid, tags in way_tags.items():
        if tags.get("natural") == "water" or "waterway" in tags or \
                tags.get("landuse") in ("reservoir", "basin"):
            coords = [{"lat": nodes[r][0], "lon": nodes[r][1]} for r in ways.get(wid, [])
                      if r in nodes]
            if len(coords) >= 3:
                elements.append({"type": "way", "id": int(wid), "tags": tags,
                                 "geometry": coords})
    for rid, tags in rel_tags.items():
        if tags.get("natural") == "water" or "waterway" in tags:
            for ring in _rel_rings(rid, ways, rels):
                coords = [{"lat": nodes[r][0], "lon": nodes[r][1]} for r in ring
                          if r in nodes]
                if len(coords) >= 4 and coords[0] != coords[-1]:
                    coords.append(coords[0])
                if len(coords) >= 4:
                    elements.append({"type": "relation", "id": int(rid), "tags": tags,
                                     "geometry": coords})
    return {"elements": elements}


def parse_full_map_bridges(xml_bytes: bytes) -> dict:
    """Extract bridge/tunnel highway ways from a full OSM map download."""
    nodes, ways, rels, _nt, way_tags, _rt = _parse_osm(xml_bytes)
    elements = []
    for wid, tags in way_tags.items():
        is_bridge = (tags.get("bridge") in ("yes", "true", "viaduct")
                     or tags.get("man_made") == "bridge")
        is_tunnel = tags.get("tunnel") in ("yes", "true")
        if (is_bridge or is_tunnel) and "highway" in tags:
            coords = [{"lat": nodes[r][0], "lon": nodes[r][1]} for r in ways.get(wid, [])
                      if r in nodes]
            if len(coords) >= 2:
                elements.append({"type": "way", "id": int(wid), "tags": tags,
                                 "geometry": coords})
    return {"elements": elements}


def parse_full_map_pois(xml_bytes: bytes) -> dict:
    """Extract hospital/medical + industrial/retail/activity POIs from a full
    OSM map download (nodes + way centroids), Overpass-`out center` shape."""
    nodes, ways, rels, node_tags, way_tags, _rt = _parse_osm(xml_bytes)
    med_amen = {"hospital", "clinic", "doctors"}
    act_amen = {"school", "community_centre", "university", "college"}
    elements = []

    def _is_med(t):
        return (t.get("amenity") in med_amen or "healthcare" in t
                or t.get("building") == "hospital")

    def _is_depot(t):
        return (t.get("landuse") in ("industrial", "retail")
                or any(k in (t.get("building") or "")
                       for k in ("warehouse", "industrial", "distribution"))
                or t.get("shop") in ("mall", "department_store"))

    def _is_act(t):
        return (t.get("amenity") in act_amen
                or t.get("leisure") == "sports_centre")

    for nid, tags in node_tags.items():
        if _is_med(tags) or _is_depot(tags) or _is_act(tags):
            lat, lon = nodes[nid]
            elements.append({"type": "node", "id": int(nid), "tags": tags,
                             "lat": lat, "lon": lon})
    for wid, tags in way_tags.items():
        if _is_med(tags) or _is_depot(tags) or _is_act(tags):
            refs = ways.get(wid, [])
            lats = [nodes[r][0] for r in refs if r in nodes]
            lons = [nodes[r][1] for r in refs if r in nodes]
            if lats:
                elements.append({"type": "way", "id": int(wid), "tags": tags,
                                 "center": {"lat": sum(lats) / len(lats),
                                            "lon": sum(lons) / len(lons)}})
    return {"elements": elements}


def fetch_entrances_near(lat: float, lon: float, radius_m: int = 600) -> list:
    """OSM entrance nodes around a POI (for precise facility access points)."""
    q = (
        "[out:json][timeout:60];\n"
        f'(node["entrance"](around:{radius_m},{lat},{lon}););\n'
        "out center;"
    )
    res = overpass_query(q, timeout=120)
    return res.get("elements", [])


def fetch_way_full_geometry(way_id) -> list:
    """Full geometry of an OSM way (for building-footprint containment)."""
    q = (
        "[out:json][timeout:60];\n"
        f"(way({way_id}););\n"
        "out geom;"
    )
    res = overpass_query(q, timeout=120)
    return res.get("elements", [])


def osm_way_ids_with_name(osm_path: Path, street: str) -> set:
    """OSM way ids whose `name` tag matches `street` (parsed from the extract)."""
    import xml.etree.ElementTree as ET
    ids = set()
    try:
        for _ev, elem in ET.iterparse(str(osm_path), events=("end",)):
            if elem.tag != "way":
                continue
            tags = {}
            for child in elem:
                if child.tag == "tag":
                    tags[child.get("k")] = child.get("v")
                child.clear()
            if tags.get("name") == street:
                ids.add(elem.get("id"))
            elem.clear()
    except ET.ParseError:
        pass
    return ids


def refine_address_street(osm_path: Path, net, lat: float, lon: float,
                          street: str):
    """Project a POI onto its official address street (OSM way name match).

    Returns (edge_id, x, y, dist_m) of the closest passenger edge belonging to
    an OSM way named `street`, or None.
    """
    way_ids = osm_way_ids_with_name(osm_path, street)
    if not way_ids:
        return None
    px, py = net.convertLonLat2XY(lon, lat)
    best = None  # (edge_id, x, y, d)
    for e in net.getEdges():
        if not e.allows("passenger"):
            continue
        if e.getID().lstrip("-").split("#")[0] not in way_ids:
            continue
        d, pt = _min_dist_to_poly(px, py, e.getShape())
        if best is None or d < best[3]:
            best = (e.getID(), pt[0], pt[1], d)
    return best


def best_entrance_for_poi(net, lat: float, lon: float, poi_element=None,
                          radius_m: int = 600):
    """Find the OSM entrance near a POI with the smallest snap distance.

    Returns (entrance_element, snap_edge_id, snap_m, snapped_latlon) or None.
    Only entrances inside the POI building footprint (when known) qualify.
    """
    from shapely.geometry import Point, Polygon
    footprint = None
    if poi_element is not None and poi_element.get("geometry"):
        coords = [(p["lon"], p["lat"]) for p in poi_element["geometry"]]
        if len(coords) >= 4:
            try:
                fp = Polygon(coords)
                if fp.is_valid:
                    footprint = fp
            except Exception:  # noqa: BLE001
                footprint = None
    ents = fetch_entrances_near(lat, lon, radius_m)
    best = None
    for e in ents:
        if "lat" not in e or "lon" not in e:
            continue
        if footprint is not None:
            pt = Point(e["lon"], e["lat"])
            if not footprint.contains(pt) and not footprint.boundary.distance(pt) < 1e-6:
                continue
        try:
            edge, x, y, d = snap_to_edge(net, e["lat"], e["lon"])
        except RuntimeError:
            continue
        if best is None or d < best[2]:
            best = (e, edge.getID(), d, (x, y))
    return best


def el_latlon(el: Dict[str, Any]) -> Tuple[float, float]:
    if "lat" in el and "lon" in el:
        return el["lat"], el["lon"]
    c = el.get("center", {})
    return c["lat"], c["lon"]


def poi_name(el: Dict[str, Any]) -> str:
    return (el.get("tags") or {}).get("name", "") or ""


def poi_kind(el: Dict[str, Any]) -> str:
    t = el.get("tags") or {}
    amenity = t.get("amenity")
    if amenity in ("hospital", "clinic", "doctors") or "healthcare" in t \
            or t.get("building") == "hospital":
        return "hospital"
    if t.get("landuse") == "industrial" or "industrial" in (t.get("building") or ""):
        return "industrial"
    if "warehouse" in (t.get("building") or "") or "distribution" in (t.get("building") or ""):
        return "warehouse"
    if t.get("landuse") == "retail" or t.get("shop") in ("mall", "department_store"):
        return "retail"
    if amenity in ("school", "community_centre", "university", "college"):
        return "activity"
    if t.get("leisure") == "sports_centre":
        return "activity"
    return "other"


def cluster_centers(latlons: List[Tuple[float, float]], radius_km: float = 0.35):
    """Greedy union-find clustering of (lat, lon) points; returns cluster list."""
    n = len(latlons)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if haversine(*latlons[i], *latlons[j]) < radius_km * 1000.0:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri
    clusters: Dict[int, List[int]] = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)
    out = []
    for members in clusters.values():
        lats = [latlons[i][0] for i in members]
        lons = [latlons[i][1] for i in members]
        out.append({
            "size": len(members),
            "center": (sum(lats) / len(lats), sum(lons) / len(lons)),
        })
    return sorted(out, key=lambda c: -c["size"])


# ----------------------------------------------------------------------------
# scene writers (SUMO + config YAML) -- never touch Site A
# ----------------------------------------------------------------------------
def write_sumo_scene(site_dir: Path, net, cfg: Dict[str, Any],
                     d1_h1_route: Optional[List[str]], seed: int = 20240601) -> None:
    """Write routes.rou.xml / additional.add.xml / site.sumocfg into site_dir."""
    sumo_dir = site_dir / "sumo"
    sumo_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
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
            except Exception:  # noqa: BLE001
                continue
            if route:
                lines.append(f'  <route id="r{rid}" edges="{" ".join(e.getID() for e in route)}"/>')
                return

    n_bg = 45
    for i in range(n_bg):
        rand_route(i)
    dep = 0.0
    for i in range(n_bg):
        lines.append(f'  <vehicle id="bg{i:02d}" type="background_car" route="r{i}" depart="{dep:.1f}"/>')
        dep += rng.uniform(2.0, 12.0)
    if d1_h1_route:
        lines.append(f'  <route id="rD1H1" edges="{" ".join(d1_h1_route)}"/>')
    lines.append("</routes>")
    (sumo_dir / "routes.rou.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    cols = {"H1": "200,20,20", "D1": "20,20,200", "V1": "20,180,20",
            "V2": "20,180,20", "V3": "20,120,120", "B1": "200,120,20"}
    alines = ['<?xml version="1.0" encoding="UTF-8"?>', "<additional>"]
    for name, m in cfg["sumo_mapping"].items():
        f = cfg["facilities"][name]
        alines.append(f'  <poi id="{name}" x="{m["x"]:.3f}" y="{m["y"]:.3f}" '
                      f'color="{cols.get(name, "200,200,200")}" layer="2" width="6.0" '
                      f'type="{f["type"]}"/>')
    alines.append("</additional>")
    (sumo_dir / "additional.add.xml").write_text("\n".join(alines) + "\n", encoding="utf-8")

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <input>
    <net-file value="network.net.xml"/>
    <route-files value="routes.rou.xml"/>
    <additional-files value="additional.add.xml"/>
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
    (sumo_dir / "site.sumocfg").write_text(xml, encoding="utf-8")


def write_config_yaml(path: Path, scenario: Dict[str, Any]) -> None:
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(scenario, sort_keys=False, allow_unicode=True,
                       default_flow_style=False), encoding="utf-8")


def write_bluesky_scn(path: Path, cfg: Dict[str, Any], site_label: str) -> int:
    from orchestrator.fleet import build_scene_commands
    cmds = build_scene_commands(cfg)
    lines = [f"# {site_label} -- low-altitude scene (single WGS84 source: {path.parent.parent.name})"]
    for c in cmds:
        lines.append(f"0:00:00.00>{c}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(cmds)
