"""Cross-site unified scene figures + three-site morphology comparison.

Outputs:
  outputs/cross_site/site_b_amsterdam_unified_scene.png
  outputs/cross_site/site_c_edmonton_unified_scene.png
  outputs/cross_site/three_site_morphology_comparison.png

Site A data is READ-ONLY (plotting only). All drawing is done in each site's
own SUMO UTM projection.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402

from orchestrator import config as config_mod  # noqa: E402
from orchestrator.sumo_env import setup as sumo_setup  # noqa: E402
from tools import cross_site_lib as lib  # noqa: E402

OUT_ROOT = ROOT / "outputs" / "cross_site"

SITES = {
    "a": {"site_id": "site_a_suzhou", "config": ROOT / "config" / "scenario_config.yaml",
          "net": ROOT / "sim" / "sumo" / "network.net.xml", "city": "Suzhou, China",
          "cache": OUT_ROOT / "site_a_analysis"},
    "b": {"site_id": "site_b_amsterdam",
          "config": ROOT / "config" / "site_b_amsterdam_config.yaml",
          "net": ROOT / "sim" / "sites" / "site_b_amsterdam" / "sumo" / "network.net.xml",
          "city": "Amsterdam, Netherlands", "cache": OUT_ROOT / "site_b_analysis"},
    "c": {"site_id": "site_c_edmonton",
          "config": ROOT / "config" / "site_c_edmonton_config.yaml",
          "net": ROOT / "sim" / "sites" / "site_c_edmonton" / "sumo" / "network.net.xml",
          "city": "Edmonton, Canada", "cache": OUT_ROOT / "site_c_analysis"},
}

FAC_COLORS = {"H1": "#d62728", "D1": "#1f77b4", "V1": "#2ca02c",
              "V2": "#2ca02c", "V3": "#17becf", "B1": "#ff7f0e"}


def load_water(site: dict, cfg: dict, net):
    wjson = site["cache"] / "water_osm.json"
    if not wjson.exists():
        site["cache"].mkdir(parents=True, exist_ok=True)
        wjson.write_text(json.dumps(lib.fetch_water(cfg["bbox"])), encoding="utf-8")
    return lib.water_geometries(json.loads(wjson.read_text(encoding="utf-8")), net)


def draw_site(ax, site: dict, cfg: dict, net, title: str, show_routes: bool = True,
              site_key: str = "x"):
    # roads
    segs, alpha = [], []
    for e in net.getEdges():
        if not e.allows("passenger"):
            continue
        shape = e.getShape()
        if len(shape) < 2:
            continue
        segs.append([(x, y) for x, y in shape])
        alpha.append(0.35 if e.getSpeed() > 13.0 else 0.22)
    lc = LineCollection(segs, colors="#444444", linewidths=0.6, alpha=0.5, zorder=1)
    ax.add_collection(lc)

    # water
    wgeoms = load_water(site, cfg, net)
    for w in wgeoms:
        g = w["geom"]
        if g.geom_type == "Polygon":
            patch = MplPolygon(list(g.exterior.coords), closed=True,
                               facecolor="#9ecae1", edgecolor="none",
                               alpha=0.75, zorder=0)
            ax.add_patch(patch)
        elif g.geom_type == "LineString":
            ax.plot(*g.xy, color="#6baed6", linewidth=max(1.0, min(3.0, w["area_m2"] / 200000)),
                    alpha=0.9, zorder=0)

    # bbox
    xmin, ymin, xmax, ymax = net.getBoundary()
    ax.add_patch(plt.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin,
                               fill=False, edgecolor="black", linewidth=1.6, zorder=5))

    # routes
    fac = cfg["facilities"]
    mapping = cfg["sumo_mapping"]
    if show_routes:
        b1 = cfg["disruption_links"]["links"]["B1"]
        detour = b1.get("detour_edges") or []
        with lib.traci_session(site["net"], f"fig_{site_key}") as traci:
            baseline = lib.route_edges(traci, mapping["D1"]["edge_id"],
                                       mapping["H1"]["edge_id"])
        if baseline:
            pts = []
            for eid in baseline:
                pts.extend(net.getEdge(eid).getShape())
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#d62728",
                    linewidth=2.4, zorder=4, label="baseline ground route")
        if detour:
            pts = []
            for eid in detour:
                pts.extend(net.getEdge(eid).getShape())
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#e377c2",
                    linewidth=2.2, linestyle="--", zorder=4, label="detour (B1 closed)")
        # air straight line V2 -> V1
        ax.plot([mapping["V2"]["x"], mapping["V1"]["x"]],
                [mapping["V2"]["y"], mapping["V1"]["y"]],
                color="#2ca02c", linewidth=2.0, linestyle=":",
                zorder=4, label="low-altitude straight-line")

    # facilities
    for name, m in mapping.items():
        if name not in FAC_COLORS:
            continue
        col = FAC_COLORS[name]
        marker = "X" if name == "B1" else ("s" if name.startswith("V") else "o")
        ax.scatter(m["x"], m["y"], s=110, c=col, marker=marker, edgecolors="white",
                   linewidths=1.2, zorder=6, label=name)

    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(xmin - 40, xmax + 40)
    ax.set_ylim(ymin - 40, ymax + 40)


def unified_scene(site_key: str) -> None:
    site = SITES[site_key]
    cfg = config_mod.load_config(site["config"])
    sumo_setup()
    import sumolib
    net = sumolib.net.readNet(str(site["net"]))
    fig, ax = plt.subplots(figsize=(11, 11))
    label = {"a": "Site A", "b": "Site B", "c": "Site C"}[site_key]
    draw_site(ax, site, cfg, net,
              f"{label} -- {site['city']}\nunified scene (roads, water, facilities, "
              f"baseline + detour routes, air straight-line)", site_key=site_key)
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="upper right", fontsize=9,
              framealpha=0.9)
    out = OUT_ROOT / f"{site['site_id']}_unified_scene.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def three_site_comparison() -> None:
    import csv as _csv
    csv_path = OUT_ROOT / "site_morphology_comparison.csv"
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = {r["site_id"]: r for r in _csv.DictReader(fh)}
    order = [("site_a_suzhou", "a"), ("site_b_amsterdam", "b"), ("site_c_edmonton", "c")]
    fig, axes = plt.subplots(1, 3, figsize=(19, 6.4))
    sumo_setup()
    import sumolib
    for ax, (sid, key) in zip(axes, order):
        site = SITES[key]
        cfg = config_mod.load_config(site["config"])
        net = sumolib.net.readNet(str(site["net"]))
        r = rows[sid]
        label = {"a": "Site A\nMeshed / Mixed Urban (Suzhou)",
                 "b": "Site B\nWater-Barrier / Bridge-Constrained (Amsterdam)",
                 "c": "Site C\nSparse Suburban / Polycentric (Edmonton)"}[key]
        draw_site(ax, site, cfg, net, label, show_routes=True, site_key=key)
        txt = (f"road density {r['road_density_km_per_km2']} km/km2\n"
               f"intersections {r['intersection_density']} /km2\n"
               f"mean degree {r['mean_node_degree']} | dead-ends {r['dead_end_ratio']}\n"
               f"mean SP {r['mean_shortest_path_length']} km | circuity {r['mean_od_circuity']}\n"
               f"D1->H1 net {r['facility_network_distance_D1_H1']} km "
               f"(eucl {r['facility_euclidean_distance_D1_H1']} km)\n"
               f"barrier: {r['major_barrier_type']} | crossings {r['usable_crossing_count']}\n"
               f"B1 closure ETA +{r['critical_link_eta_increase_pct']}% "
               f"(detour {r['detour_exists']})")
        ax.text(0.02, 0.02, txt, transform=ax.transAxes, fontsize=8.2,
                va="bottom", ha="left", bbox=dict(facecolor="white", alpha=0.88,
                                                  boxstyle="round,pad=0.4"))
    fig.suptitle("Three-site morphology comparison (identical 3.2 x 3.2 km extent, "
                 "identical SUMO pipeline)", fontsize=13, fontweight="bold")
    out = OUT_ROOT / "three_site_morphology_comparison.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def main() -> int:
    unified_scene("b")
    unified_scene("c")
    three_site_comparison()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
