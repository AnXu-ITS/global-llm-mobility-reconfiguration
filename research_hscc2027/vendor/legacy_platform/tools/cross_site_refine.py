"""Three-site scene refinement: auxiliary remote facilities + auxiliary ODs.

For Site B (Amsterdam): adds southern/eastern auxiliary assets so the scene
uses the whole 3.2x3.2 km bbox while KEEPING the primary D1->H1 / B1_B logic
untouched. For Site C (Edmonton): adds a west->east transverse structure so
the scene is longitudinal + transverse sparse, NOT bridge-constrained.

Everything is anchored on REAL OSM POIs (ids from the candidate analysis);
routes are computed on the REAL SUMO net (TraCI). Primary sections of the
site configs are never modified -- the tool RE-VALIDATES them and refuses to
proceed if the primary route/B1 numbers drift.

Outputs (per site):
  outputs/cross_site/refinement/<site_id>/
    auxiliary.json          (facilities, ODs, routes, closure sensitivity)
    spatial_utilization.csv (BEFORE = primary only, AFTER = +auxiliary)
    transverse_routes.csv   (Site C only; Site B writes od_routes.csv)
    primary_revalidation.json
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.geo import haversine  # noqa: E402
from tools import cross_site_lib as lib  # noqa: E402

OUT = ROOT / "outputs" / "cross_site" / "refinement"

# ---------------------------------------------------------------------------
# auxiliary facility designs (all REAL OSM POIs, verified inside the bbox)
# ---------------------------------------------------------------------------
SITES = {
    "b": {
        "site_id": "site_b_amsterdam",
        "cfg": ROOT / "config" / "site_b_amsterdam_config.yaml",
        "net": ROOT / "sim" / "sites" / "site_b_amsterdam" / "sumo" / "network.net.xml",
        "pois": ROOT / "outputs" / "cross_site" / "candidates" / "amsterdam"
                / "ams_olvg_amstel" / "osm_pois.json",
        "aux_facilities": {
            "H2": {"poi_id": 4763328999, "type": "secondary_medical_destination",
                   "note": "GZC Amstelkwartier (health centre), SE quadrant"},
            "D2": {"poi_id": 2818225044, "type": "secondary_logistics_origin",
                   "note": "HEMA retail store, Rivierenbuurt (south, west bank)"},
            "C2": {"poi_id": 1260595065, "type": "secondary_service_destination",
                   "note": "Medisch Centrum Oost, NE quadrant"},
        },
        "landings": {"V4": "H2", "V5": "D2"},
        "ods": [("OD-B1", "D2", "H1"), ("OD-B2", "D1", "H2")],
    },
    "c": {
        "site_id": "site_c_edmonton",
        "cfg": ROOT / "config" / "site_c_edmonton_config.yaml",
        "net": ROOT / "sim" / "sites" / "site_c_edmonton" / "sumo" / "network.net.xml",
        "pois": ROOT / "outputs" / "cross_site" / "candidates" / "edmonton"
                / "edm_grey_nuns" / "osm_pois.json",
        "aux_facilities": {
            "D2": {"poi_id": 295699431, "type": "west_commercial_origin",
                   "note": "66 Street Plaza (retail), north-west side"},
            "H2": {"poi_id": 2955340269, "type": "east_medical_destination",
                   "note": "Everyday Medical (clinic), south-east"},
            "C2": {"poi_id": 574145086, "type": "southwest_commercial_activity",
                   "note": "Kameyosek Shopping Centre, south-west"},
            "C3": {"poi_id": 556875401, "type": "east_commercial_activity",
                   "note": "Aspenwood (retail), east side"},
        },
        "landings": {"V4": "H2", "V5": "D2"},
        "ods": [("OD-C1", "C2", "C3"), ("OD-C2", "D2", "H2")],
    },
}


# ---------------------------------------------------------------------------
def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def find_poi(pois_elements, poi_id):
    for e in pois_elements:
        if e.get("id") == poi_id:
            return e
    raise RuntimeError(f"POI {poi_id} not found in {pois_elements}")


def turns_of_route(net, edges, angle_deg=30.0):
    """Count heading changes > angle_deg between consecutive edges."""
    n = 0
    for a, b in zip(edges[:-1], edges[1:]):
        sa = net.getEdge(a).getShape()
        sb = net.getEdge(b).getShape()
        (x1, y1), (x2, y2) = sa[-2], sa[-1]
        (x3, y3), (x4, y4) = sb[0], sb[1]
        h1 = math.degrees(math.atan2(y2 - y1, x2 - x1))
        h2 = math.degrees(math.atan2(y4 - y3, x4 - x3))
        d = abs((h2 - h1 + 180.0) % 360.0 - 180.0)
        if d > angle_deg:
            n += 1
    return n


def route_metrics(net, traci, a_edge, b_edge, name=""):
    edges = lib.route_edges(traci, a_edge, b_edge)
    if not edges:
        return None
    dist = lib.route_distance_m(net, edges)
    eta = lib.ff_eta(traci, edges)
    xmin, ymin, xmax, ymax = net.getBoundary()
    xs, ys = [], []
    for eid in edges:
        for x, y in net.getEdge(eid).getShape():
            xs.append(x)
            ys.append(y)
    return {
        "od_id": name, "edges": edges, "distance_m": dist, "eta_s": eta,
        "turns": turns_of_route(net, edges),
        "span_x_pct": 100.0 * (max(xs) - min(xs)) / (xmax - xmin),
        "span_y_pct": 100.0 * (max(ys) - min(ys)) / (ymax - ymin),
        "n_edges": len(edges),
    }


def facility_geometry(fac_xy: dict, routes, net):
    """Spatial-utilization metrics for a set of facility points + route edges."""
    from shapely.geometry import MultiPoint, LineString
    from shapely.ops import unary_union
    xmin, ymin, xmax, ymax = net.getBoundary()
    site_area = (xmax - xmin) * (ymax - ymin)
    pts = [MultiPoint([(v["x"], v["y"]) for v in fac_xy.values()])]
    hull = pts[0].convex_hull
    hull_area = hull.area
    fac_minx, fac_miny, fac_maxx, fac_maxy = hull.bounds
    # route envelope: 100 m buffer around all route polylines
    lines = []
    for edges in routes:
        shape = []
        for eid in edges:
            shape.extend(net.getEdge(eid).getShape())
        if len(shape) >= 2:
            lines.append(LineString(shape).buffer(100.0))
    envelope = unary_union(lines) if lines else None
    env_area = envelope.area if envelope else 0.0
    # 3x3 grid cell coverage
    cells = set()
    for key, v in fac_xy.items():
        cells.add((int((v["x"] - xmin) // ((xmax - xmin) / 3)),
                   int((v["y"] - ymin) // ((ymax - ymin) / 3))))
    for edges in routes:
        for eid in edges:
            for x, y in net.getEdge(eid).getShape():
                cells.add((int((x - xmin) // ((xmax - xmin) / 3)),
                           int((y - ymin) // ((ymax - ymin) / 3))))
    return {
        "facility_hull_area_pct": 100.0 * hull_area / site_area,
        "facility_bbox_area_pct": 100.0 * (fac_maxx - fac_minx) * (fac_maxy - fac_miny)
                                  / site_area,
        "facility_span_x_pct": 100.0 * (fac_maxx - fac_minx) / (xmax - xmin),
        "facility_span_y_pct": 100.0 * (fac_maxy - fac_miny) / (ymax - ymin),
        "route_envelope_area_pct": 100.0 * env_area / site_area,
        "grid_cells_covered": len(cells),
        "grid_cells_of_9": min(len(cells), 9),
    }


def refine(site_key: str) -> dict:
    meta = SITES[site_key]
    site_id = meta["site_id"]
    site_out = OUT / site_id
    site_out.mkdir(parents=True, exist_ok=True)
    print(f"\n===== refine {site_id} =====")
    import yaml
    cfg = yaml.safe_load(meta["cfg"].read_text(encoding="utf-8"))
    net = lib.load_net(meta["net"])
    pois = load_json(meta["pois"]).get("elements", [])
    fac = cfg["facilities"]
    mapping = cfg["sumo_mapping"]

    def xy_of(key):
        return {"x": mapping[key]["x"], "y": mapping[key]["y"]}

    xmin, ymin, xmax, ymax = net.getBoundary()

    # ---- snap auxiliary facilities to REAL roads ----
    aux = {}
    for key, spec in meta["aux_facilities"].items():
        el = find_poi(pois, spec["poi_id"])
        lat, lon = lib.el_latlon(el)
        name = lib.poi_name(el)
        edge, x, y, d = lib.snap_to_edge(net, lat, lon)
        inside = (xmin + 20 <= x <= xmax - 20) and (ymin + 20 <= y <= ymax - 20)
        print(f"  {key}: {name!r} ({lat:.5f},{lon:.5f}) -> edge {edge.getID()} "
              f"snap={d:.1f} m inside_bbox={inside}")
        if not inside:
            raise RuntimeError(f"{key} POI outside bbox ({lat},{lon})")
        if d > 100:
            raise RuntimeError(f"{key} snap {d:.1f} m > 100 m (FAIL)")
        aux[key] = {
            "osm_id": spec["poi_id"], "name": name, "type": spec["type"],
            "note": spec["note"], "lat": lat, "lon": lon,
            "snap_m": round(d, 3), "edge_id": edge.getID(),
            "x": round(x, 3), "y": round(y, 3), "synthetic": False,
        }
    for lkey, parent in meta["landings"].items():
        lon, lat = net.convertXY2LonLat(aux[parent]["x"], aux[parent]["y"])
        aux[lkey] = {
            "osm_id": None, "name": f"{lkey} landing (snapped to {parent} access edge)",
            "type": "auxiliary_landing_site", "note": "experimental low-altitude landing node",
            "lat": lat, "lon": lon, "snap_m": 0.0,
            "edge_id": aux[parent]["edge_id"], "x": aux[parent]["x"], "y": aux[parent]["y"],
            "synthetic": True,
        }

    # ---- routes (TraCI) ----
    with lib.traci_session(meta["net"], f"refine_{site_key}") as traci:
        od_rows = []
        for od_id, o_key, d_key in meta["ods"]:
            o_edge = aux[o_key]["edge_id"] if o_key in aux else mapping[o_key]["edge_id"]
            d_edge = aux[d_key]["edge_id"] if d_key in aux else mapping[d_key]["edge_id"]
            m = route_metrics(net, traci, o_edge, d_edge, od_id)
            if m is None:
                raise RuntimeError(f"{od_id} no route")
            # euclidean + circuity + crossings on path
            o_lat = aux[o_key]["lat"] if o_key in aux else fac[o_key]["lat"]
            o_lon = aux[o_key]["lon"] if o_key in aux else fac[o_key]["lon"]
            d_lat = aux[d_key]["lat"] if d_key in aux else fac[d_key]["lat"]
            d_lon = aux[d_key]["lon"] if d_key in aux else fac[d_key]["lon"]
            eucl = haversine(o_lat, o_lon, d_lat, d_lon)
            m["origin"] = o_key
            m["destination"] = d_key
            m["euclidean_distance_m"] = round(eucl, 1)
            m["circuity"] = round(m["distance_m"] / eucl, 4)
            print(f"  {od_id}: {o_key}->{d_key} dist={m['distance_m']:.0f} m "
                  f"eucl={eucl:.0f} m circ={m['circuity']:.2f} eta={m['eta_s']:.0f} s "
                  f"turns={m['turns']} spanX={m['span_x_pct']:.0f}% spanY={m['span_y_pct']:.0f}%")
            od_rows.append(m)
        # crossing sensitivity for auxiliary ODs (which crossings on path;
        # closing each keeps a detour? -- Site B morphology demo)
        wpath = ROOT / "sim" / "sites" / site_id / "sumo" / "water_osm.json"
        bpath = ROOT / "sim" / "sites" / site_id / "sumo" / "bridges_osm.json"
        if wpath.exists():
            wgeoms = lib.water_geometries(load_json(wpath), net)
            g, pos, edge_meta = lib.build_junction_graph(net)
            crossings = lib.classify_crossings(
                net, edge_meta, wgeoms,
                load_json(bpath) if bpath.exists() else {"elements": []})
            for row in od_rows:
                row["n_water_crossings"] = sum(1 for e in row["edges"] if e in crossings)
                row["crossing_edges"] = [e for e in row["edges"] if e in crossings]
                o_key = row["origin"]
                d_key = row["destination"]
                o_edge = (aux[o_key]["edge_id"] if o_key in aux
                          else mapping[o_key]["edge_id"])
                d_edge = (aux[d_key]["edge_id"] if d_key in aux
                          else mapping[d_key]["edge_id"])
                sens = []
                for ce in row["crossing_edges"]:
                    alt = lib.close_edge_route(traci, o_edge, d_edge, ce)
                    if alt is None:
                        sens.append({"edge": ce, "detour": False, "inc_pct": None})
                    else:
                        alt_eta = lib.ff_eta(traci, alt)
                        inc = (alt_eta - row["eta_s"]) / row["eta_s"] * 100.0
                        sens.append({"edge": ce, "detour": True,
                                     "inc_pct": round(inc, 2)})
                row["crossing_sensitivity"] = sens
                for s in sens:
                    print(f"    crossing {s['edge']}: detour={s['detour']} "
                          f"inc={s['inc_pct']}%")

        # ---- primary revalidation (must be unchanged) ----
        d1_edge = mapping["D1"]["edge_id"]
        h1_edge = mapping["H1"]["edge_id"]
        base = route_metrics(net, traci, d1_edge, h1_edge, "PRIMARY D1->H1")
        b1 = cfg["disruption_links"]["links"]["B1"]
        det = lib.close_edge_route(traci, d1_edge, h1_edge, b1["edge_id"])
        det_eta = lib.ff_eta(traci, det) if det else None
        det_dist = lib.route_distance_m(net, det) if det else None
        inc = (det_eta - base["eta_s"]) / base["eta_s"] * 100.0 if det_eta else None
        primary_ok = (abs(base["eta_s"] - b1["base_eta_s"]) < 1.0
                      and det is not None
                      and abs(inc - b1["eta_increase_pct"]) < 1.0)
        print(f"  PRIMARY revalidation: eta={base['eta_s']:.2f} s "
              f"(config {b1['base_eta_s']}) | B1 closure inc={inc:.2f}% "
              f"(config {b1['eta_increase_pct']}) | detour={det is not None} "
              f"-> {'PASS' if primary_ok else 'FAIL'}")
        if not primary_ok:
            raise RuntimeError("primary OD/B1 drifted -- aborting refinement")

        # ---- spatial utilization BEFORE (primary) / AFTER (+aux) ----
        primary_fac = {k: xy_of(k) for k in ("H1", "D1", "V1", "V2", "V3", "B1")}
        all_fac = dict(primary_fac)
        for k, v in aux.items():
            all_fac[k] = {"x": v["x"], "y": v["y"]}
        primary_routes = [base["edges"], det] if det else [base["edges"]]
        aux_routes = [r["edges"] for r in od_rows]
        before = facility_geometry(primary_fac, primary_routes, net)
        after = facility_geometry(all_fac, primary_routes + aux_routes, net)
        print("  utilization BEFORE:", json.dumps(before))
        print("  utilization AFTER :", json.dumps(after))

    # ---- write outputs ----
    primary_cfg_snapshot = {
        "facilities": {k: v for k, v in fac.items()},
        "sumo_mapping": {k: v for k, v in mapping.items()},
        "disruption_links": cfg["disruption_links"],
    }
    (site_out / "auxiliary.json").write_text(json.dumps({
        "aux_facilities": aux, "ods": od_rows,
        "primary_revalidation": {
            "baseline_eta_s": round(base["eta_s"], 3),
            "config_base_eta_s": b1["base_eta_s"],
            "b1_closure_inc_pct": round(inc, 3) if inc is not None else None,
            "config_b1_inc_pct": b1["eta_increase_pct"],
            "detour_exists": det is not None,
            "primary_unchanged": primary_ok,
        },
        "spatial_utilization": {"before": before, "after": after},
    }, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (site_out / "primary_revalidation.json").write_text(json.dumps({
        "primary_unchanged": primary_ok,
        "baseline_eta_s": round(base["eta_s"], 3),
        "config_base_eta_s": b1["base_eta_s"],
        "b1_closure_inc_pct": round(inc, 3) if inc is not None else None,
        "config_b1_inc_pct": b1["eta_increase_pct"],
        "b1_edge_id": b1["edge_id"],
        "detour_exists": det is not None,
        "primary_config_snapshot": primary_cfg_snapshot,
    }, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    util_rows = []
    for tag, u in (("before", before), ("after", after)):
        util_rows.append({"stage": tag, **{k: round(v, 4) for k, v in u.items()}})
    with open(site_out / "spatial_utilization.csv", "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(util_rows[0].keys()))
        w.writeheader()
        w.writerows(util_rows)

    route_csv = site_out / ("transverse_routes.csv" if site_key == "c"
                            else "od_routes.csv")
    fields = ["od_id", "origin", "destination", "euclidean_distance_m",
              "network_distance_m", "travel_time_s", "circuity",
              "number_of_turns", "bbox_span_x_pct", "bbox_span_y_pct",
              "river_dependency", "critical_crossing_dependency"]
    with open(route_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in od_rows:
            sens = r.get("crossing_sensitivity", [])
            w.writerow({
                "od_id": r["od_id"], "origin": r["origin"],
                "destination": r["destination"],
                "euclidean_distance_m": r["euclidean_distance_m"],
                "network_distance_m": round(r["distance_m"], 1),
                "travel_time_s": round(r["eta_s"], 1),
                "circuity": r["circuity"],
                "number_of_turns": r["turns"],
                "bbox_span_x_pct": round(r["span_x_pct"], 2),
                "bbox_span_y_pct": round(r["span_y_pct"], 2),
                "river_dependency": r.get("n_water_crossings", 0),
                "critical_crossing_dependency": any(
                    not s["detour"] for s in sens),
            })
    print(f"  wrote {site_out}")
    return {"site": site_id, "primary_unchanged": primary_ok}


def main() -> int:
    results = {}
    for k in ("b", "c"):
        results[k] = refine(k)
    ok = all(r["primary_unchanged"] for r in results.values())
    print(f"\nrefinement done; primary unchanged: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
