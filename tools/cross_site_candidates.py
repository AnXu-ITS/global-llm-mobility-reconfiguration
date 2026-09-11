"""Cross-site candidate search: Amsterdam (Site B) and Edmonton (Site C).

For every candidate 3.2x3.2 km bbox this tool:
  1. downloads the highways-only OSM extract + water + bridges/tunnels + POIs,
  2. builds a SUMO net with the EXACT Site A netconvert flags,
  3. computes network morphology metrics (see cross_site_lib docstring),
  4. classifies water crossings (bridge / tunnel / embankment),
  5. selects the best (H1 hospital, D1 depot) OD pair:
       - Amsterdam: both facilities on OPPOSITE sides of a water barrier whose
         baseline route uses the barrier, ranked by closure ETA sensitivity,
       - Edmonton : ranked by baseline network distance (spatial dispersion),
  6. runs single-edge crossing-closure analysis (baseline vs detour ETA),
  7. scores the candidate and writes an analysis.json + the scoring CSV.

Usage:
  python tools/cross_site_candidates.py --city amsterdam [--only ams_zeeburg]
  python tools/cross_site_candidates.py --city edmonton
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.geo import bbox_from_center, haversine  # noqa: E402
from tools import cross_site_lib as lib  # noqa: E402

OUT_ROOT = ROOT / "outputs" / "cross_site"
CAND_DIR = OUT_ROOT / "candidates"

# (candidate_id, center_lat, center_lon, note)
AMSTERDAM = [
    ("ams_ij_centraal",      52.3835, 4.9010, "IJ waterfront, Centraal Station"),
    ("ams_ij_oost",          52.3815, 4.9320, "IJ, Oostelijke Handelskade / Zeeburg west"),
    ("ams_zeeburg",          52.3680, 4.9780, "Buiten-IJ + Amsterdam-Rijnkanaal (Zeeburgereiland)"),
    ("ams_zeeburg2",         52.3775, 4.9750, "Buiten-IJ: Enneus Heermabrug + Schellingwouderbrug in-box"),
    ("ams_amstel_rivieren",  52.3450, 4.9020, "Amstel, Rivierenbuurt bridges"),
    ("ams_amstel_zuid",      52.3270, 4.9180, "Amstel south: Utrechtsebrug / Rozenoordbrug"),
    ("ams_sloterplas",       52.3620, 4.8225, "Sloterplas lake, Nieuw-West"),
    ("ams_nieuwe_meer",      52.3310, 4.8300, "Nieuwe Meer / Schinkel canal"),
    ("ams_duivendrecht",     52.3220, 4.9350, "Weespertrekvaart + Amstel (Duivendrecht)"),
    ("ams_noord_canal",      52.4160, 4.8500, "Noordhollandsch Kanaal, Amsterdam-Noord"),
    ("ams_ijburg",           52.3560, 5.0120, "IJburg / Buiten-IJ island access"),
    ("ams_olvg_amstel",      52.3500, 4.9120, "OLVG Oost hospital + Amstel (Berlage/Nieuwe Amstel/Torontobrug)"),
    ("ams_amc_amstel",       52.3030, 4.9380, "AMC hospital + Amstel south (A2/S110 bridges)"),
]

EDMONTON = [
    ("edm_millwoods",        53.4580, -113.4300, "Mill Woods: superblocks + Grey Nuns hospital"),
    ("edm_millwoods_south",  53.4350, -113.4350, "Meadows / Ellerslie big-box retail"),
    ("edm_grey_nuns",        53.4720, -113.4250, "Grey Nuns hospital + industrial edge"),
    ("edm_terwillegar",      53.4420, -113.5850, "Terwillegar / Windermere SW"),
    ("edm_castle_downs",     53.6300, -113.5200, "Castle Downs NW suburb"),
    ("edm_clareview",        53.5980, -113.3850, "Clareview + Manning Town Centre NE"),
    ("edm_west_jasper",      53.5100, -113.6400, "Misericordia hospital + West Edmonton Mall"),
    ("edm_heritage_valley",  53.4080, -113.5450, "Heritage Valley far-south"),
    ("edm_callingwood",      53.5320, -113.6550, "Callingwood / Lewis Estates W"),
    ("edm_summerside",       53.4250, -113.4750, "Summerside SE (lake community control)"),
    ("edm_grey_nuns_se",     53.4540, -113.4150, "Grey Nuns hospital NW + sparse Meadows SE"),
    ("edm_misericordia",     53.5270, -113.6400, "Misericordia hospital + WEM + Callingwood/Lewis"),
]


# ----------------------------------------------------------------------------
def snap_facility(net, lat, lon):
    edge, x, y, d = lib.snap_to_edge(net, lat, lon)
    return {"edge_id": edge.getID(), "x": x, "y": y, "snap_m": d,
            "lat": lat, "lon": lon}


def xy_to_latlon(net, x, y):
    lon, lat = net.convertXY2LonLat(x, y)
    return lat, lon


def process_candidate(city: str, cid: str, clat: float, clon: float) -> dict:
    t0 = time.time()
    bbox = bbox_from_center(clat, clon, lib.AREA_KM, lib.AREA_KM)
    print(f"\n=== [{city}] {cid} bbox {lib.fmt_bbox(bbox)} ===")
    cdir = CAND_DIR / city / cid
    cdir.mkdir(parents=True, exist_ok=True)

    # 1) downloads (cached; interpreter first, full-map fallback)
    osm_path = cdir / "area.osm.xml"
    if not osm_path.exists() or osm_path.stat().st_size < 10_000:
        print("  fetch highways extract ...")
        osm_path.write_bytes(lib.fetch_highways_osm(bbox))
        print(f"    {osm_path.stat().st_size/1e6:.2f} MB")
    full_map_bytes = None

    def _full_map():
        nonlocal full_map_bytes
        if full_map_bytes is None:
            print("    [fallback] downloading full OSM map ...")
            full_map_bytes = lib.fetch_full_map(bbox)
            print(f"    {len(full_map_bytes)/1e6:.1f} MB")
        return full_map_bytes

    wjson_path = cdir / "water_osm.json"
    if not wjson_path.exists():
        try:
            water_json = lib.fetch_water(bbox)
        except Exception:
            water_json = lib.parse_full_map_water(_full_map())
        wjson_path.write_text(json.dumps(water_json), encoding="utf-8")
    else:
        water_json = json.loads(wjson_path.read_text(encoding="utf-8"))
    bjson_path = cdir / "bridges_osm.json"
    if not bjson_path.exists():
        try:
            bridge_json = lib.fetch_bridges(bbox)
        except Exception:
            bridge_json = lib.parse_full_map_bridges(_full_map())
        bjson_path.write_text(json.dumps(bridge_json), encoding="utf-8")
    else:
        bridge_json = json.loads(bjson_path.read_text(encoding="utf-8"))
    pjson_path = cdir / "osm_pois.json"
    if not pjson_path.exists():
        try:
            pois = lib.fetch_pois(bbox)
        except Exception:
            pois = lib.parse_full_map_pois(_full_map())
        pjson_path.write_text(json.dumps(pois, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    else:
        pois = json.loads(pjson_path.read_text(encoding="utf-8"))

    # 2) netconvert (cached)
    net_path = cdir / "network.net.xml"
    if not net_path.exists() or net_path.stat().st_size < 10_000:
        ok, log = lib.netconvert(osm_path, net_path)
        if not ok:
            print("  netconvert FAILED")
            print(log[-1500:])
            return {"candidate_id": cid, "error": "netconvert_failed", "log": log[-2000:]}
    print(f"  net built ({net_path.stat().st_size/1e6:.2f} MB, {time.time()-t0:.0f}s)")

    # 3) metrics
    net = lib.load_net(net_path)
    m = lib.metrics_from_net(net, bbox)
    edge_meta = m.pop("edge_meta")

    # 4) water + crossings
    wgeoms = lib.water_geometries(water_json, net)
    xmin, ymin, xmax, ymax = net.getBoundary()
    from shapely.geometry import box as shapely_box
    bbox_poly = shapely_box(xmin, ymin, xmax, ymax)
    # keep only water bodies with a meaningful in-study-area footprint
    for w in wgeoms:
        try:
            w["in_area_m2"] = w["geom"].intersection(bbox_poly).area
        except Exception:  # noqa: BLE001
            w["in_area_m2"] = 0.0
    wgeoms = [w for w in wgeoms if w["in_area_m2"] >= 10_000]
    crossings = lib.classify_crossings(net, edge_meta, wgeoms, bridge_json)
    main_water = max(wgeoms, key=lambda w: w["in_area_m2"]) if wgeoms else None
    main_crossings = {}
    if main_water is not None:
        from shapely.geometry import LineString
        mg = main_water["geom"]
        mg_test = mg.buffer(4.0) if mg.geom_type == "LineString" else mg
        for eid in crossings:
            line = LineString(edge_meta[eid]["shape"])
            if line.intersects(mg_test):
                main_crossings[eid] = crossings[eid]
    # usable crossing = ANY passenger edge crossing water (OSM bridge/tunnel/
    # embankment tag recorded as metadata; all are real ground crossings)
    usable = dict(crossings)
    # boundary artifact check: does the main water body touch the bbox edge?
    main_touches_boundary = False
    if main_water is not None:
        band = bbox_poly.buffer(10.0).difference(bbox_poly.buffer(-10.0))
        main_touches_boundary = main_water["geom"].intersects(band)
    water_area_km2 = sum(w["in_area_m2"] for w in wgeoms) / 1e6

    # 5) facilities
    hospitals = [e for e in pois.get("elements", []) if lib.poi_kind(e) == "hospital"]
    depots = [e for e in pois.get("elements", [])
              if lib.poi_kind(e) in ("industrial", "warehouse", "retail")]

    result = {
        "candidate_id": cid, "city": city,
        "center_lat": clat, "center_lon": clon, "bbox": bbox,
        "metrics": m,
        "water_area_km2": water_area_km2,
        "main_water": {"name": main_water["name"], "kind": main_water["kind"],
                       "area_km2": main_water["in_area_m2"] / 1e6,
                       "touches_boundary": main_touches_boundary} if main_water else None,
        "n_water_geoms": len(wgeoms),
        "n_crossings_total": len(crossings),
        "n_main_crossings": len(main_crossings),
        "main_crossing_edges": sorted(main_crossings.keys()),
        "n_usable_crossings": len(usable),
        "usable_crossings": usable,
        "n_hospitals": len(hospitals),
        "n_depots": len(depots),
        "hospitals": [{"id": e["id"], "name": lib.poi_name(e), "latlon": lib.el_latlon(e)}
                      for e in hospitals],
        "depots": [{"id": e["id"], "name": lib.poi_name(e), "kind": lib.poi_kind(e),
                    "latlon": lib.el_latlon(e)} for e in depots],
    }
    print(f"  metrics: road_dens={m['road_density_km_per_km2']:.1f} "
          f"inter_dens={m['intersection_density_per_km2']:.1f} "
          f"nodes={m['node_count']} edges={m['edge_count']} "
          f"deadend={m['dead_end_ratio']:.3f} "
          f"meanSP={m['mean_shortest_path_km']:.2f}km circ={m['mean_od_circuity']:.3f}")
    print(f"  water: area={water_area_km2:.2f} km2 geoms={len(wgeoms)} "
          f"crossings={len(crossings)} main_crossings={len(main_crossings)} "
          f"main={main_water['name'] or main_water['kind'] if main_water else 'none'} "
          f"touches_boundary={main_touches_boundary}")
    print(f"  pois: hospitals={len(hospitals)} depots={len(depots)}")

    if city == "amsterdam":
        with lib.traci_session(net_path, f"cand_{cid}") as traci:
            pair = best_pair_amsterdam(net, edge_meta, traci, crossings, usable,
                                       hospitals, depots)
    else:
        with lib.traci_session(net_path, f"cand_{cid}") as traci:
            pair = best_pair_edmonton(net, edge_meta, traci, crossings,
                                      hospitals, depots, pois)
    result["best_pair"] = pair

    score = score_candidate(city, result)
    result["score"] = score
    (cdir / "analysis.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"  score={score:.1f}  ({time.time()-t0:.0f}s total)")
    return result


def _pair_analysis(net, edge_meta, traci, crossings, h, d):
    """Baseline route + closure rows for one (hospital, depot) pair."""
    h_ll = lib.el_latlon(h)
    d_ll = lib.el_latlon(d)
    hsnap = snap_facility(net, h_ll[0], h_ll[1])
    dsnap = snap_facility(net, d_ll[0], d_ll[1])
    base_edges = lib.route_edges(traci, dsnap["edge_id"], hsnap["edge_id"])
    if base_edges is None:
        return None
    base_eta = lib.ff_eta(traci, base_edges)
    base_dist = lib.route_distance_m(net, base_edges)
    crossing_on_path = [e for e in base_edges if e in crossings]
    # all crossings are real ground crossings; keep the OSM kind as metadata.
    # origin/destination edges are excluded from closure (Site A convention:
    # closing the O/D edge disconnects the mission by definition)
    usable_on_path = [e for e in crossing_on_path
                      if e not in (dsnap["edge_id"], hsnap["edge_id"])]
    eucl = haversine(h_ll[0], h_ll[1], d_ll[0], d_ll[1])
    an = lib.closure_analysis(net, traci, dsnap["edge_id"], hsnap["edge_id"],
                              usable_on_path)
    best_closure = None
    if an["closures"]:
        c0 = an["closures"][0]
        if c0["detour_exists"]:
            best_closure = c0
    return {
        "hospital": {"id": h["id"], "name": lib.poi_name(h)},
        "depot": {"id": d["id"], "name": lib.poi_name(d), "kind": lib.poi_kind(d)},
        "h_snap": hsnap, "d_snap": dsnap,
        "baseline_edges": base_edges, "baseline_eta_s": base_eta,
        "baseline_dist_m": base_dist,
        "euclidean_m": eucl, "circuity": base_dist / eucl if eucl else None,
        "n_crossings_on_path": len(crossing_on_path),
        "n_usable_on_path": len(usable_on_path),
        "best_closure": best_closure,
    }


def _is_true_hospital(h):
    t = h.get("tags") or {}
    return t.get("amenity") == "hospital" or t.get("building") == "hospital"


def _snap_penalty(p):
    hs, ds = p["h_snap"]["snap_m"], p["d_snap"]["snap_m"]
    return ((0 if hs <= 50 else (1 if hs <= 100 else 2)) +
            (0 if ds <= 50 else (1 if ds <= 100 else 2)))


def best_pair_amsterdam(net, edge_meta, traci, crossings, usable, hospitals, depots):
    """Rank (h, d) pairs: baseline route must cross a water barrier AND the
    closure of at least one crossing on the path must keep a detour.
    Rank: closure-with-detour required, then snap quality, then ETA impact."""
    true_h = [h for h in hospitals if _is_true_hospital(h)] or hospitals
    acute = [h for h in true_h if (h.get("tags") or {}).get("emergency") == "yes"]
    pool = acute or true_h

    def _pair_search(depot_pool, require_industrial):
        out = []
        for h in pool:
            h_ll = lib.el_latlon(h)
            hx = snap_facility(net, h_ll[0], h_ll[1])
            for d in depot_pool:
                if require_industrial and lib.poi_kind(d) not in ("industrial", "warehouse"):
                    continue
                d_ll = lib.el_latlon(d)
                dx = snap_facility(net, d_ll[0], d_ll[1])
                an = _pair_analysis(net, edge_meta, traci, crossings, h, d)
                if an is None or an["n_usable_on_path"] == 0:
                    continue
                # closure of some crossing on the path MUST keep a detour
                if an["best_closure"] is None:
                    continue
                # both facilities must sit clearly away from the crossing midpoints
                mids = [crossings[e]["midpoint_xy"] for e in an["baseline_edges"]
                        if e in usable]
                far = all(math.hypot(hx["x"] - mx, hx["y"] - my) > 150.0 and
                          math.hypot(dx["x"] - mx, dx["y"] - my) > 150.0
                          for mx, my in mids)
                if not far:
                    continue
                an["opposite_side_ok"] = True
                out.append(an)
        return out

    pairs = _pair_search(depots, require_industrial=True) or \
        _pair_search(depots, require_industrial=False)
    if not pairs:
        return None
    pairs.sort(key=lambda p: (
        _snap_penalty(p),
        -(p["best_closure"]["increase_pct"] or 0),
    ))
    return pairs[0]


def best_pair_edmonton(net, edge_meta, traci, crossings, hospitals, depots, pois):
    """Rank (h, d) pairs: acute-care hospitals (emergency=yes) preferred, then
    snap quality, then baseline network distance (spatial dispersion)."""
    true_h = [h for h in hospitals if _is_true_hospital(h)] or hospitals
    acute = [h for h in true_h if (h.get("tags") or {}).get("emergency") == "yes"]
    pool = acute or true_h
    pairs = []
    for h in pool:
        for d in depots:
            an = _pair_analysis(net, edge_meta, traci, crossings, h, d)
            if an is None:
                continue
            pairs.append(an)
    if not pairs:
        return None
    pairs.sort(key=lambda p: (_snap_penalty(p), -p["baseline_dist_m"]))
    # facility dispersion: H1 + D1 + top activity POI clusters
    activities = [lib.el_latlon(e) for e in pois.get("elements", [])
                  if lib.poi_kind(e) == "activity"]
    clusters = lib.cluster_centers(activities)
    centers = [c["center"] for c in clusters[:3]]
    pts = [lib.el_latlon(h) for h in hospitals[:3]] + centers
    disp = None
    if len(pts) >= 3:
        ds = [haversine(*a, *b) for i, a in enumerate(pts) for b in pts[i + 1:]]
        disp = sum(ds) / len(ds) / 1000.0
    best = pairs[0]
    best["facility_dispersion_km"] = disp
    best["n_activity_clusters"] = len(clusters)
    return best


def score_candidate(city: str, r: dict) -> float:
    if city == "amsterdam":
        return score_amsterdam(r)
    return score_edmonton(r)


def score_amsterdam(r: dict) -> float:
    score = 0.0
    mw = r.get("main_water") or {}
    if mw.get("area_km2", 0) >= 0.1:
        score += 20.0
    elif mw:
        score += 8.0
    n = r.get("n_main_crossings", 0)
    if 2 <= n <= 5:
        score += 15.0
    elif n == 1 or 6 <= n <= 8:
        score += 8.0
    else:
        score += 4.0
    if mw.get("touches_boundary"):
        score -= 8.0  # main water clipped by bbox => boundary-artifact risk
    p = r.get("best_pair")
    if p and p.get("best_closure"):
        inc = p["best_closure"]["increase_pct"] or 0.0
        if inc >= 40:
            score += 25.0
        elif inc >= 25:
            score += 18.0
        elif inc >= 10:
            score += 8.0
        else:
            score += 2.0
        score += 20.0  # detour exists
        cid = p["best_closure"]["edge_id"]
        cmeta = r["usable_crossings"].get(cid, {})
        margin = cmeta.get("boundary_margin_m", 0.0)
        if margin >= 300:
            score += 10.0
        elif margin >= 150:
            score += 5.0
        bshare = p["best_closure"].get("detour_boundary_share", 1.0)
        if bshare <= 0.30:
            score += 5.0
        elif bshare <= 0.50:
            score += 3.0
    if p:
        hs, ds = p["h_snap"]["snap_m"], p["d_snap"]["snap_m"]
        if hs <= 50 and ds <= 50:
            score += 10.0
        elif hs <= 100 and ds <= 100:
            score += 7.0
        else:
            score += 3.0
    return round(score, 1)


def score_edmonton(r: dict) -> float:
    score = 0.0
    m = r["metrics"]
    rd = m["road_density_km_per_km2"]
    if rd < 12:
        score += 20.0
    elif rd < 16:
        score += 12.0
    else:
        score += 4.0
    idd = m["intersection_density_per_km2"]
    if idd < 25:
        score += 20.0
    elif idd < 35:
        score += 12.0
    else:
        score += 4.0
    p = r.get("best_pair")
    if p:
        dkm = p["baseline_dist_m"] / 1000.0
        if dkm >= 3.0:
            score += 20.0
        elif dkm >= 2.5:
            score += 15.0
        elif dkm >= 2.0:
            score += 8.0
        else:
            score += 2.0
        circ = p.get("circuity") or 0.0
        if circ >= 1.25:
            score += 15.0
        elif circ >= 1.15:
            score += 10.0
        else:
            score += 4.0
        disp = p.get("facility_dispersion_km") or 0.0
        if disp >= 1.5:
            score += 15.0
        elif disp >= 1.0:
            score += 10.0
        else:
            score += 5.0
        ncross = p.get("n_crossings_on_path", 0)
        if ncross == 0:
            score += 10.0
        elif ncross == 1:
            score += 6.0
        else:
            score += 0.0
    return round(score, 1)


def write_csv(city: str, results: List[dict]) -> None:
    out = OUT_ROOT / f"{city}_candidate_bboxes.csv"
    if city == "amsterdam":
        fieldnames = ["candidate_id", "center_lat", "center_lon", "bbox",
                      "road_density", "intersection_density", "water_crossing_count",
                      "best_crossing_id", "baseline_eta", "closure_eta",
                      "eta_increase_pct", "detour_exists", "boundary_margin_m",
                      "score", "selected"]
        rows = []
        for r in results:
            p = r.get("best_pair") or {}
            bc = (p or {}).get("best_closure") or {}
            bbox = r.get("bbox") or {}
            metrics = r.get("metrics") or {}
            rows.append({
                "candidate_id": r["candidate_id"],
                "center_lat": r.get("center_lat", ""), "center_lon": r.get("center_lon", ""),
                "bbox": f"{bbox.get('south', '')},{bbox.get('west', '')},{bbox.get('north', '')},{bbox.get('east', '')}",
                "road_density": (round(metrics["road_density_km_per_km2"], 2)
                                 if metrics else ""),
                "intersection_density": (round(metrics["intersection_density_per_km2"], 2)
                                         if metrics else ""),
                "water_crossing_count": r.get("n_usable_crossings", 0),
                "best_crossing_id": bc.get("edge_id", ""),
                "baseline_eta": round(p.get("baseline_eta_s", 0), 2) if p else "",
                "closure_eta": round(bc.get("eta_s", 0), 2) if bc else "",
                "eta_increase_pct": round(bc.get("increase_pct", 0), 2) if bc else "",
                "detour_exists": bool(bc.get("detour_exists")),
                "boundary_margin_m": round(
                    (r.get("usable_crossings") or {}).get(bc.get("edge_id", ""), {}).get(
                        "boundary_margin_m", 0), 1) if bc.get("edge_id") else "",
                "score": r.get("score", ""),
                "selected": bool(r.get("selected", False)),
            })
    else:
        fieldnames = ["candidate_id", "center_lat", "center_lon", "bbox",
                      "road_density", "intersection_density", "dead_end_ratio",
                      "mean_od_network_distance", "mean_od_euclidean_distance",
                      "circuity", "facility_dispersion", "river_dependency",
                      "score", "selected"]
        rows = []
        for r in results:
            p = r.get("best_pair") or {}
            m = r.get("metrics") or {}
            bbox = r.get("bbox") or {}
            rows.append({
                "candidate_id": r["candidate_id"],
                "center_lat": r.get("center_lat", ""), "center_lon": r.get("center_lon", ""),
                "bbox": f"{bbox.get('south', '')},{bbox.get('west', '')},{bbox.get('north', '')},{bbox.get('east', '')}",
                "road_density": round(m.get("road_density_km_per_km2", 0), 2) if m else "",
                "intersection_density": round(m.get("intersection_density_per_km2", 0), 2) if m else "",
                "dead_end_ratio": round(m.get("dead_end_ratio") or 0, 4) if m else "",
                "mean_od_network_distance": round(p.get("baseline_dist_m", 0) / 1000.0, 3) if p else "",
                "mean_od_euclidean_distance": round(p.get("euclidean_m", 0) / 1000.0, 3) if p else "",
                "circuity": round(p.get("circuity", 0), 3) if p else "",
                "facility_dispersion": round(p.get("facility_dispersion_km", 0), 3) if p else "",
                "river_dependency": p.get("n_crossings_on_path", 0) if p else "",
                "score": r.get("score", ""),
                "selected": bool(r.get("selected", False)),
            })
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out} ({len(rows)} candidates)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True, choices=["amsterdam", "edmonton"])
    ap.add_argument("--only", default=None)
    ap.add_argument("--csv-only", action="store_true",
                    help="regenerate the scoring CSV from existing analysis.json files")
    args = ap.parse_args()
    if args.csv_only:
        results = []
        for adir in sorted((CAND_DIR / args.city).glob("*/analysis.json")):
            try:
                r = json.loads(adir.read_text(encoding="utf-8"))
                results.append(r)
            except Exception as ex:  # noqa: BLE001
                print(f"skip {adir}: {ex}")
        write_csv(args.city, results)
        return 0
    cands = AMSTERDAM if args.city == "amsterdam" else EDMONTON
    if args.only:
        cands = [c for c in cands if c[0] == args.only]
        if not cands:
            print(f"unknown candidate {args.only}")
            return 2
    results = []
    for cid, clat, clon, note in cands:
        try:
            r = process_candidate(args.city, cid, clat, clon)
            r["note"] = note
        except Exception as ex:  # noqa: BLE001
            print(f"  CANDIDATE {cid} ERROR: {type(ex).__name__}: {ex}")
            import traceback
            traceback.print_exc()
            r = {"candidate_id": cid, "error": str(ex), "center_lat": clat,
                 "center_lon": clon, "note": note,
                 "bbox": bbox_from_center(clat, clon, lib.AREA_KM, lib.AREA_KM)}
        results.append(r)
    write_csv(args.city, results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
