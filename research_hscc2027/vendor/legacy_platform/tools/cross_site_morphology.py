"""Three-site morphology quantification (Site A read-only, B, C).

Computes the identical metric set (see cross_site_lib docstring for
definitions) for Site A (sim/sumo), Site B and Site C, plus facility-level
D1->H1 quantities, and writes:
  outputs/cross_site/site_morphology_comparison.csv

Site A files are only READ; nothing in sim/sumo or config/scenario_config.yaml
is modified. (Water data for Site A is fetched for analysis and cached under
outputs/cross_site only.)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod  # noqa: E402
from orchestrator.geo import haversine  # noqa: E402
from tools import cross_site_lib as lib  # noqa: E402

OUT_ROOT = ROOT / "outputs" / "cross_site"
SITES = [
    {"key": "a", "site_id": "site_a_suzhou", "city": "Suzhou, China",
     "config": ROOT / "config" / "scenario_config.yaml",
     "net": ROOT / "sim" / "sumo" / "network.net.xml",
     "area_km2": lib.AREA_KM2},
    {"key": "b", "site_id": "site_b_amsterdam", "city": "Amsterdam, Netherlands",
     "config": ROOT / "config" / "site_b_amsterdam_config.yaml",
     "net": ROOT / "sim" / "sites" / "site_b_amsterdam" / "sumo" / "network.net.xml",
     "area_km2": lib.AREA_KM2},
    {"key": "c", "site_id": "site_c_edmonton", "city": "Edmonton, Canada",
     "config": ROOT / "config" / "site_c_edmonton_config.yaml",
     "net": ROOT / "sim" / "sites" / "site_c_edmonton" / "sumo" / "network.net.xml",
     "area_km2": lib.AREA_KM2},
]

FIELDS = [
    "site_id", "city", "area_km2", "road_length_km", "road_density_km_per_km2",
    "node_count", "edge_count", "intersection_density", "mean_node_degree",
    "dead_end_ratio", "mean_shortest_path_length", "median_shortest_path_length",
    "mean_od_circuity", "facility_network_distance_D1_H1",
    "facility_euclidean_distance_D1_H1", "D1_H1_circuity",
    "major_barrier_type", "usable_crossing_count",
    "critical_link_eta_increase_pct", "detour_exists",
]


def water_crossings_for_site(key: str, net, cfg, edge_meta, cache_dir: Path):
    """Fetch/load water + bridges for a site bbox and classify crossings."""
    wjson_path = cache_dir / "water_osm.json"
    bjson_path = cache_dir / "bridges_osm.json"
    if not wjson_path.exists():
        bbox = cfg["bbox"]
        try:
            wj = lib.fetch_water(bbox)
        except Exception:  # noqa: BLE001
            try:
                wj = lib.parse_full_map_water(lib.fetch_full_map(bbox))
            except Exception:  # noqa: BLE001
                wj = {"elements": []}
        wjson_path.write_text(json.dumps(wj), encoding="utf-8")
    if not bjson_path.exists():
        bbox = cfg["bbox"]
        try:
            bj = lib.fetch_bridges(bbox)
        except Exception:  # noqa: BLE001
            try:
                bj = lib.parse_full_map_bridges(lib.fetch_full_map(bbox))
            except Exception:  # noqa: BLE001
                bj = {"elements": []}
        bjson_path.write_text(json.dumps(bj), encoding="utf-8")
    water_json = json.loads(wjson_path.read_text(encoding="utf-8"))
    bridge_json = json.loads(bjson_path.read_text(encoding="utf-8"))
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
    usable = {e: c for e, c in crossings.items()}
    main_water = max(wgeoms, key=lambda w: w["in_area_m2"]) if wgeoms else None
    main_label = None
    if main_water is not None and main_water["in_area_m2"] > 50_000:
        main_label = f"{main_water['kind']}:{main_water['name'] or 'unnamed'}"
    return usable, main_label


def main() -> int:
    rows = []
    for site in SITES:
        if not site["config"].exists() or not site["net"].exists():
            print(f"\n=== {site['site_id']} === SKIP (files missing)")
            continue
        print(f"\n=== {site['site_id']} ===")
        cfg = config_mod.load_config(site["config"])
        net = lib.load_net(site["net"])
        m = lib.metrics_from_net(net, cfg["bbox"])
        edge_meta = m["edge_meta"]

        # D1 -> H1 network distance on the final net (identical code all sites)
        d1_edge = cfg["sumo_mapping"]["D1"]["edge_id"]
        h1_edge = cfg["sumo_mapping"]["H1"]["edge_id"]
        with lib.traci_session(site["net"], f"morph_{site['key']}") as traci:
            route = lib.route_edges(traci, d1_edge, h1_edge)
            net_dist = lib.route_distance_m(net, route) / 1000.0 if route else None
        eucl = haversine(cfg["facilities"]["D1"]["lat"], cfg["facilities"]["D1"]["lon"],
                         cfg["facilities"]["H1"]["lat"], cfg["facilities"]["H1"]["lon"]) / 1000.0

        cache_dir = OUT_ROOT / f"site_{site['key']}_analysis"
        cache_dir.mkdir(parents=True, exist_ok=True)
        usable, main_label = water_crossings_for_site(site["key"], net, cfg,
                                                      edge_meta, cache_dir)

        links = cfg.get("disruption_links", {}).get("links", {})
        b1 = links.get("B1", {})
        inc = b1.get("eta_increase_pct")
        has_detour = b1.get("has_detour")

        rows.append({
            "site_id": site["site_id"],
            "city": site["city"],
            "area_km2": site["area_km2"],
            "road_length_km": round(m["road_length_km"], 3),
            "road_density_km_per_km2": round(m["road_density_km_per_km2"], 3),
            "node_count": m["node_count"],
            "edge_count": m["edge_count"],
            "intersection_density": round(m["intersection_density_per_km2"], 3),
            "mean_node_degree": round(m["mean_node_degree"], 3),
            "dead_end_ratio": round(m["dead_end_ratio"], 4),
            "mean_shortest_path_length": round(m["mean_shortest_path_km"], 4),
            "median_shortest_path_length": round(m["median_shortest_path_km"], 4),
            "mean_od_circuity": round(m["mean_od_circuity"], 4),
            "facility_network_distance_D1_H1": round(net_dist, 4) if net_dist else "",
            "facility_euclidean_distance_D1_H1": round(eucl, 4),
            "D1_H1_circuity": round(net_dist / eucl, 4) if net_dist and eucl else "",
            "major_barrier_type": main_label or "none",
            "usable_crossing_count": len(usable),
            "critical_link_eta_increase_pct": round(inc, 2) if inc is not None else "",
            "detour_exists": bool(has_detour),
        })
        print(f"  road_dens={m['road_density_km_per_km2']:.2f} "
              f"inter_dens={m['intersection_density_per_km2']:.2f} "
              f"deg={m['mean_node_degree']:.2f} deadend={m['dead_end_ratio']:.3f} "
              f"meanSP={m['mean_shortest_path_km']:.2f} circ={m['mean_od_circuity']:.2f} "
              f"redun={m['route_redundancy_proxy']:.2f}")
        print(f"  D1->H1: net={net_dist:.2f} km eucl={eucl:.2f} km "
              f"circ={net_dist/eucl if net_dist else 0:.2f} "
              f"crossings={len(usable)} barrier={main_label}")

    out = OUT_ROOT / "site_morphology_comparison.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
