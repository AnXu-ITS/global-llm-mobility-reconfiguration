"""Build the FINAL cross-site scene for the selected candidate bbox.

Outputs (mirrors Site A layout, but under sim/sites/<site>/):
  sim/sites/<site>/sumo/area.osm.xml          (highways-only OSM extract)
  sim/sites/<site>/sumo/network.net.xml       (netconvert, Site A flags)
  sim/sites/<site>/sumo/routes.rou.xml        (background traffic + D1->H1)
  sim/sites/<site>/sumo/additional.add.xml    (H1/D1/V1/V2/V3/B1 POIs)
  sim/sites/<site>/sumo/site.sumocfg
  sim/sites/<site>/sumo/osm_pois.json, water_osm.json, bridges_osm.json
  sim/sites/<site>/bluesky/site_<site>.scn
  config/site_b_amsterdam_config.yaml | config/site_c_edmonton_config.yaml

Facilities: H1 = real hospital POI, D1 = real logistics/industrial/commercial
depot POI (OSM-provenance recorded; no fabricated POIs). V1/V2 = snapped road
access points, V3 = snapped backup landing site near bbox centre.
B1 = selected critical ground disruption link:
  Site B: the main-barrier crossing whose single-edge closure maximises the
          D1->H1 ETA increase (must keep a detour and reachability).
  Site C: the single baseline-path edge whose closure maximises the ETA
          increase (sparse-network bottleneck; no water barrier involved).

Usage:
  python tools/cross_site_build.py --site b --candidate ams_zeeburg
  python tools/cross_site_build.py --site c --candidate edm_millwoods
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.geo import bbox_from_center, destination, haversine  # noqa: E402
from tools import cross_site_lib as lib  # noqa: E402

CAND_DIR = ROOT / "outputs" / "cross_site" / "candidates"

SITES = {
    "b": {"site_id": "site_b_amsterdam", "city": "amsterdam",
          "scenario_id": "SB", "label": "Site B -- Amsterdam (water-barrier / bridge-constrained)"},
    "c": {"site_id": "site_c_edmonton", "city": "edmonton",
          "scenario_id": "SC", "label": "Site C -- Edmonton (sparse suburban / polycentric)"},
}


def build(site_key: str, candidate_id: str) -> int:
    meta = SITES[site_key]
    city = meta["city"]
    site_dir = ROOT / "sim" / "sites" / meta["site_id"]
    cand = CAND_DIR / city / candidate_id / "analysis.json"
    if not cand.exists():
        print(f"candidate analysis not found: {cand}")
        return 2
    an = json.loads(cand.read_text(encoding="utf-8"))
    pair = an.get("best_pair")
    if not pair or not pair.get("baseline_edges"):
        print(f"candidate {candidate_id} has no usable OD pair")
        return 2
    if site_key == "b" and not pair.get("best_closure"):
        print(f"candidate {candidate_id} has no crossing closure data (Site B requires "
              f"a barrier-crossing OD with a detour)")
        return 2

    # ---- freeze the site dir from the CANDIDATE artifacts (analysis-consistent:
    # same net topology + same water/bridges/POI data that produced the scored
    # closure analysis; edge ids must not drift) ----
    sumo_dir = site_dir / "sumo"
    sumo_dir.mkdir(parents=True, exist_ok=True)
    cdir = CAND_DIR / city / candidate_id
    for name in ("area.osm.xml", "network.net.xml", "water_osm.json",
                 "bridges_osm.json", "osm_pois.json"):
        src = cdir / name
        if src.exists():
            shutil.copy2(src, sumo_dir / name)
    net = lib.load_net(sumo_dir / "network.net.xml")

    h = pair["hospital"]
    d = pair["depot"]
    hsnap = dict(pair["h_snap"])
    dsnap = dict(pair["d_snap"])

    # ---- entrance refinement: when a POI centroid snaps > 50 m, use its real
    # OSM entrance node (inside the building footprint) as the facility point --
    # provenance is recorded, never fabricated.
    pois_elements = json.loads(
        (sumo_dir / "osm_pois.json").read_text(encoding="utf-8")).get("elements", [])
    h_el = next((e for e in pois_elements if e.get("id") == h["id"]), None)
    h_placement = "real_osm_poi"
    h_campus_offset_m = None
    if hsnap["snap_m"] > 50.0:
        refined = False
        # 1) offline first: hospital's official address street (OSM addr:street)
        street = ((h_el or {}).get("tags") or {}).get("addr:street")
        if street:
            best = lib.refine_address_street(sumo_dir / "area.osm.xml", net,
                                             hsnap["lat"], hsnap["lon"], street)
            if best is not None:
                eid, px, py, dist_m = best
                lon2, lat2 = net.convertXY2LonLat(px, py)
                print(f"  H1 address-street refinement: snap {hsnap['snap_m']:.1f} m -> "
                      f"{dist_m:.1f} m (street '{street}', edge {eid})")
                h_campus_offset_m = hsnap["snap_m"]
                hsnap = {"edge_id": eid, "x": px, "y": py, "snap_m": 0.0,
                         "lat": lat2, "lon": lon2,
                         "address_street": street, "parent_osm_id": h["id"]}
                h_placement = "real_osm_poi_address_street"
                refined = True
        # 2) online fallback: real OSM entrance node inside the footprint
        if not refined:
            ent_el = h_el
            if h_el is not None and h_el.get("type") == "way":
                try:
                    full = lib.fetch_way_full_geometry(h["id"])
                    ent_el = next((w for w in full if w.get("id") == h["id"]), h_el)
                except Exception as ex:  # noqa: BLE001
                    print(f"  footprint fetch failed for H1 (keeping centroid): {ex}")
            ent = lib.best_entrance_for_poi(net, hsnap["lat"], hsnap["lon"], ent_el)
            if ent is not None and ent[2] < hsnap["snap_m"]:
                ent_node, ent_edge, ent_d, (ex, ey) = ent
                lon2, lat2 = net.convertXY2LonLat(ex, ey)
                print(f"  H1 entrance refinement: snap {hsnap['snap_m']:.1f} m -> "
                      f"{ent_d:.1f} m (entrance node {ent_node['id']}, edge {ent_edge})")
                h_campus_offset_m = hsnap["snap_m"]
                hsnap = {"edge_id": ent_edge, "x": ex, "y": ey, "snap_m": 0.0,
                         "lat": lat2, "lon": lon2,
                         "entrance_node_id": ent_node["id"],
                         "parent_osm_id": h["id"]}
                h_placement = "real_osm_poi_entrance"

    h_lat, h_lon = hsnap["lat"], hsnap["lon"]
    d_lat, d_lon = dsnap["lat"], dsnap["lon"]

    # D1 access-point refinement (same address-street rule as H1)
    d_el = next((e for e in pois_elements if e.get("id") == d["id"]), None)
    d_placement = "real_osm_poi"
    d_parcel_offset_m = None
    if dsnap["snap_m"] > 50.0:
        street = ((d_el or {}).get("tags") or {}).get("addr:street")
        if street:
            best = lib.refine_address_street(sumo_dir / "area.osm.xml", net,
                                             dsnap["lat"], dsnap["lon"], street)
            if best is not None:
                eid, px, py, dist_m = best
                lon2, lat2 = net.convertXY2LonLat(px, py)
                print(f"  D1 address-street refinement: snap {dsnap['snap_m']:.1f} m -> "
                      f"{dist_m:.1f} m (street '{street}', edge {eid})")
                d_parcel_offset_m = dsnap["snap_m"]
                dsnap = {"edge_id": eid, "x": px, "y": py, "snap_m": 0.0,
                         "lat": lat2, "lon": lon2,
                         "address_street": street, "parent_osm_id": d["id"]}
                d_placement = "real_osm_poi_address_street"

    def xy_to_latlon(x, y):
        lon, lat = net.convertXY2LonLat(x, y)
        return lat, lon

    H1 = (h_lat, h_lon)
    D1 = (d_lat, d_lon)
    V1 = xy_to_latlon(hsnap["x"], hsnap["y"])
    V2 = xy_to_latlon(dsnap["x"], dsnap["y"])
    center = an["center_lat"], an["center_lon"]
    # V3 = backup landing site: anchor near bbox centre, snap-search 8 bearings
    v3_edge, v3_x, v3_y, v3_d = None, None, None, float("inf")
    for brg in range(0, 360, 45):
        anchor = destination(center[0], center[1], 300.0, brg)
        try:
            v3_e, v3_ax, v3_ay, v3_ad = lib.snap_to_edge(net, *anchor)
        except RuntimeError:
            continue
        if v3_ad < v3_d:
            v3_edge, v3_x, v3_y, v3_d = v3_e, v3_ax, v3_ay, v3_ad
    if v3_edge is None:
        raise RuntimeError("no road near bbox centre for V3")
    V3 = xy_to_latlon(v3_x, v3_y)

    d1_edge_id = dsnap["edge_id"]
    h1_edge_id = hsnap["edge_id"]

    # ---- B1 selection ----
    edge_meta = None
    from tools.cross_site_lib import build_junction_graph
    _g, _pos, edge_meta = build_junction_graph(net)

    water_json = json.loads((sumo_dir / "water_osm.json").read_text(encoding="utf-8"))
    bridge_json = json.loads((sumo_dir / "bridges_osm.json").read_text(encoding="utf-8"))
    wgeoms = lib.water_geometries(water_json, net)
    xmin, ymin, xmax, ymax = net.getBoundary()
    from shapely.geometry import box as shapely_box
    bbox_poly = shapely_box(xmin, ymin, xmax, ymax)
    for w in wgeoms:
        try:
            w["in_area_m2"] = w["geom"].intersection(bbox_poly).area
        except Exception:  # noqa: BLE001
            w["in_area_m2"] = 0.0
    wgeoms = [w for w in wgeoms if w["in_area_m2"] >= 10_000]
    crossings = lib.classify_crossings(net, edge_meta, wgeoms, bridge_json)
    main_water = max(wgeoms, key=lambda w: w["in_area_m2"]) if wgeoms else None
    # usable crossing = ANY passenger edge crossing water (OSM tag metadata)
    usable = dict(crossings)
    main_crossings = {}
    if main_water is not None:
        from shapely.geometry import LineString
        mg = main_water["geom"]
        mg_test = mg.buffer(4.0) if mg.geom_type == "LineString" else mg
        for eid in crossings:
            line = LineString(edge_meta[eid]["shape"])
            if line.intersects(mg_test):
                main_crossings[eid] = crossings[eid]

    baseline = pair["baseline_edges"]
    if site_key == "b":
        # use the candidate-stage validated closure analysis (same net + same
        # water data -- no re-analysis, no drift)
        b1_row = pair["best_closure"]
        an2 = None
    else:
        # Site C: bottleneck over baseline-path edges (exclude origin/dest edges)
        closure_candidates = [e for e in baseline
                              if e not in (d1_edge_id, h1_edge_id)]
        with lib.traci_session(sumo_dir / "network.net.xml",
                               f"build_{site_key}") as traci:
            an2 = lib.closure_analysis(net, traci, d1_edge_id, h1_edge_id,
                                       closure_candidates)
        b1_row = None
        for row in an2["closures"]:
            if not row["detour_exists"]:
                continue
            if b1_row is None:
                b1_row = row
        if b1_row is None:
            print("FATAL: no single-edge closure with a detour found")
            return 3
    b1_edge_id = b1_row["edge_id"]
    b1_edge = net.getEdge(b1_edge_id)
    bx, by = b1_edge.getShape()[len(b1_edge.getShape()) // 2]
    B1 = xy_to_latlon(bx, by)
    b1_is_crossing = b1_edge_id in crossings
    b1_kind = crossings.get(b1_edge_id, {}).get("crossing_kind", "road")
    b1_water = crossings.get(b1_edge_id, {}).get("water_name") or \
        crossings.get(b1_edge_id, {}).get("water_kind") or ""

    detour_edges = b1_row.get("detour_edges", [])
    inc_pct = b1_row["increase_pct"]
    print(f"\nB1 selection (site {site_key}): edge={b1_edge_id} "
          f"kind={b1_kind} water='{b1_water}' crossing={b1_is_crossing}")
    print(f"  baseline eta={pair['baseline_eta_s']:.2f}s "
          f"dist={pair['baseline_dist_m']:.0f}m")
    print(f"  closure  eta={b1_row['eta_s']:.2f}s dist={b1_row['dist_m']:.0f}m "
          f"inc={inc_pct:.2f}% detour={b1_row['detour_exists']}")
    if site_key == "b":
        if not b1_is_crossing:
            print("  WARNING: chosen B1 does not cross a water body")
        else:
            print(f"  B1 is a water crossing (OSM tag '{b1_kind}')")
        if inc_pct is None or inc_pct < 25.0:
            print(f"  WARNING: ETA increase {inc_pct:.1f}% < 25% threshold")
        else:
            print(f"  OK: ETA increase {inc_pct:.1f}% >= 25% "
                  f"({'>=40% high-severity' if inc_pct >= 40 else 'acceptable'})")
        margin = crossings.get(b1_edge_id, {}).get("boundary_margin_m")
        print(f"  boundary margin of crossing: {margin:.1f} m "
              f"(require >= {lib.CROSSING_MARGIN_MIN_M:.0f})")
        bshare = b1_row.get("detour_boundary_share", 1.0)
        print(f"  detour boundary share: {bshare:.3f} "
              f"(artifact risk if > {lib.BOUNDARY_ARTIFACT_SHARE})")

    # ---- site config YAML ----
    bbox = an["bbox"]
    facilities = {
        "H1": {"type": "hospital", "lat": H1[0], "lon": H1[1],
               "osm_node_id": hsnap.get("entrance_node_id", h["id"]),
               "parent_osm_id": hsnap.get("parent_osm_id"),
               "name": h["name"], "placement": h_placement,
               "campus_centroid_offset_m": (round(h_campus_offset_m, 3)
                                            if h_campus_offset_m else None)},
        "D1": {"type": "logistics_depot", "lat": D1[0], "lon": D1[1],
               "osm_node_id": d["id"], "name": d["name"],
               "depot_kind": d.get("kind", "industrial"),
               "placement": d_placement,
               "campus_centroid_offset_m": (round(d_parcel_offset_m, 3)
                                            if d_parcel_offset_m else None)},
        "V1": {"type": "hospital_landing_site", "lat": V1[0], "lon": V1[1]},
        "V2": {"type": "logistics_hub_landing_site", "lat": V2[0], "lon": V2[1]},
        "V3": {"type": "backup_landing_site", "lat": V3[0], "lon": V3[1]},
        "B1": {"type": "disruption_link", "lat": B1[0], "lon": B1[1],
               "impact_level": "high",
               "is_water_crossing": b1_is_crossing,
               "crossing_kind": b1_kind,
               "water_name": b1_water,
               "selection_reason": (
                   f"{'water-barrier crossing' if b1_is_crossing else 'critical road link'} "
                   f"whose closure maximises D1->H1 ETA increase "
                   f"({inc_pct:.2f}%), detour retained")},
    }
    sumo_mapping = {
        "H1": {"edge_id": h1_edge_id, "lane_id": h1_edge_id + "_0",
               "x": round(hsnap["x"], 3), "y": round(hsnap["y"], 3),
               "snapped_distance_m": round(hsnap["snap_m"], 3)},
        "D1": {"edge_id": d1_edge_id, "lane_id": d1_edge_id + "_0",
               "x": round(dsnap["x"], 3), "y": round(dsnap["y"], 3),
               "snapped_distance_m": round(dsnap["snap_m"], 3)},
        "V1": {"edge_id": h1_edge_id, "lane_id": h1_edge_id + "_0",
               "x": round(hsnap["x"], 3), "y": round(hsnap["y"], 3),
               "snapped_distance_m": 0.0},
        "V2": {"edge_id": d1_edge_id, "lane_id": d1_edge_id + "_0",
               "x": round(dsnap["x"], 3), "y": round(dsnap["y"], 3),
               "snapped_distance_m": 0.0},
        "V3": {"edge_id": v3_edge.getID(), "lane_id": v3_edge.getID() + "_0",
               "x": round(v3_x, 3), "y": round(v3_y, 3),
               "snapped_distance_m": round(v3_d, 3)},
        "B1": {"edge_id": b1_edge_id, "lane_id": b1_edge_id + "_0",
               "x": round(bx, 3), "y": round(by, 3), "snapped_distance_m": 0.0},
    }
    base_eta = (an2["baseline"]["eta_s"] if an2 else pair["baseline_eta_s"])
    closure_rows = []
    if an2 is not None:
        for row in an2["closures"][:10]:
            closure_rows.append({
                "edge_id": row["edge_id"],
                "eta": (round(row["eta_s"], 2) if row["eta_s"] is not None else None),
                "inc_pct": (round(row["increase_pct"], 2)
                            if row["increase_pct"] is not None else None),
                "has_detour": row["detour_exists"],
                "reason": row.get("reason", ""),
            })
    else:
        closure_rows.append({
            "edge_id": b1_edge_id, "eta": round(b1_row["eta_s"], 2),
            "inc_pct": round(inc_pct, 2), "has_detour": b1_row["detour_exists"],
            "reason": "candidate-stage validated closure (single crossing)",
        })

    scenario = {
        "scenario_id": meta["scenario_id"],
        "scenario_version": f"{meta['scenario_id']}_3p2km_v1",
        "study_area": {
            "name": meta["site_id"],
            "center": {"lat": an["center_lat"], "lon": an["center_lon"]},
            "width_km": lib.AREA_KM, "height_km": lib.AREA_KM,
            "crs_exchange": "EPSG:4326",
            "city": {"amsterdam": "Amsterdam, Netherlands",
                     "edmonton": "Edmonton, Alberta, Canada"}[city],
            "candidate_id": candidate_id,
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
        "disruption_links": {
            "note": ("B1 = selected critical ground disruption link "
                     "(water-barrier crossing for Site B; sparse-network "
                     "bottleneck for Site C). Alternatives never simultaneous."),
            "base_eta_s": round(base_eta, 3),
            "links": {
                "B1": {
                    "edge_id": b1_edge_id,
                    "impact_level": "high",
                    "is_water_crossing": b1_is_crossing,
                    "crossing_kind": b1_kind,
                    "base_eta_s": round(base_eta, 3),
                    "detour_eta_s": round(b1_row["eta_s"], 3),
                    "eta_increase_pct": round(inc_pct, 3),
                    "has_detour": b1_row["detour_exists"],
                    "detour_edges": detour_edges,
                    "detour_boundary_share": round(
                        b1_row.get("detour_boundary_share", 1.0), 4),
                },
            },
            "closure_impact": closure_rows,
        },
        "water": {
            "main_water": {"name": main_water["name"], "kind": main_water["kind"],
                           "area_km2": main_water["in_area_m2"] / 1e6}
            if main_water else None,
            "water_area_km2": an.get("water_area_km2"),
            "n_water_geoms": an.get("n_water_geoms"),
            "n_usable_crossings": len(usable),
            "n_main_crossings": len(main_crossings),
            "main_crossing_edges": sorted(main_crossings.keys()),
            "usable_crossing_edges": sorted(usable.keys()),
        } if city == "amsterdam" else {
            "water_area_km2": an.get("water_area_km2"),
            "n_water_geoms": an.get("n_water_geoms"),
            "n_usable_crossings": len(usable),
        },
    }
    cfg_path = ROOT / "config" / f"{meta['site_id']}_config.yaml"
    lib.write_config_yaml(cfg_path, scenario)
    print(f"wrote {cfg_path}")

    # ---- SUMO scene files ----
    lib.write_sumo_scene(site_dir, net, scenario, baseline)
    # ---- BlueSky scene ----
    scn_path = site_dir / "bluesky" / f"site_{site_key}.scn"
    ncmds = lib.write_bluesky_scn(scn_path, scenario, meta["label"])
    print(f"wrote {scn_path} ({ncmds} commands)")

    # ---- quick geo-alignment self-check ----
    report = []
    for name in ("H1", "D1", "V1", "V2", "V3", "B1"):
        f = facilities[name]
        x, y = net.convertLonLat2XY(f["lon"], f["lat"])
        rlon, rlat = net.convertXY2LonLat(x, y)
        err = haversine(f["lat"], f["lon"], rlat, rlon)
        snap = sumo_mapping[name]["snapped_distance_m"]
        report.append(f"  {name}: crs_rt={err:.3f}m snap={snap}m")
    print("alignment self-check:\n" + "\n".join(report))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, choices=["b", "c"])
    ap.add_argument("--candidate", required=True)
    args = ap.parse_args()
    return build(args.site, args.candidate)


if __name__ == "__main__":
    raise SystemExit(main())
