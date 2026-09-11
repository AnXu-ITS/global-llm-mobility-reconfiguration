"""Render the unified ground-air scene as evidence of a shared WGS84 scene.

Draws the SUMO road network (colored by road speed), the D1->H1 critical
corridor, the B1/B2/B3 candidate disruption links, the shared facilities, the
two background low-altitude services, and the 4-aircraft initial fleet -- all
in one SUMO-UTM (WGS84-projected) frame. Does NOT use the BlueSky GUI.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from orchestrator.sumo_env import setup as sumo_setup  # noqa: E402

sumo_setup()
import sumolib  # noqa: E402

from orchestrator import config as config_mod  # noqa: E402
from orchestrator.fleet import FLEET, origin_latlon  # noqa: E402

OUT = ROOT / "outputs" / "unified_ground_air_scene.png"
OUT_POST = ROOT / "outputs" / "unified_ground_air_scene_post_resize.png"


def main() -> int:
    cfg = config_mod.load_config()
    net = sumolib.net.readNet(str(ROOT / "sim" / "sumo" / "network.net.xml"))
    fac = cfg["facilities"]

    def xy(name: str):
        f = fac[name]
        x, y = net.convertLonLat2XY(f["lon"], f["lat"])
        return x, y

    corridor_edges = [c["edge"] for c in cfg["disruption_links"]["closure_impact"]]

    fig, ax = plt.subplots(figsize=(13, 13))

    # 1) SUMO road network, colored by speed limit (major vs minor)
    for e in net.getEdges():
        xs = [p[0] for p in e.getShape()]
        ys = [p[1] for p in e.getShape()]
        if e.getSpeed() >= 13.0:      # ~47 km/h+ => major road
            ax.plot(xs, ys, color="#8a8a8a", lw=0.9, zorder=1)
        else:
            ax.plot(xs, ys, color="#d5d5d5", lw=0.45, zorder=1)

    # 2) D1 -> H1 critical corridor (base route edges, in route order)
    for eid in corridor_edges:
        e = net.getEdge(eid)
        xs = [p[0] for p in e.getShape()]
        ys = [p[1] for p in e.getShape()]
        ax.plot(xs, ys, color="#1f77b4", lw=2.6, zorder=3)

    # 3) B1/B2/B3 candidate disruption links (high/medium/low impact)
    link_colors = {"high": "#d62728", "medium": "#ff7f00", "low": "#f1c40f"}
    links = cfg["disruption_links"]["links"]
    for name, meta in links.items():
        be = net.getEdge(meta["edge_id"])
        bxs = [p[0] for p in be.getShape()]
        bys = [p[1] for p in be.getShape()]
        ax.plot(bxs, bys, color=link_colors[meta["impact_level"]], lw=5.0, zorder=4,
                solid_capstyle="round")

    # 4) background low-altitude services (sparse: 2 routes)
    services = cfg["air_fleet"].get("background_services", [])
    for svc in services:
        a, b = svc["route"]
        xa, ya = xy(a)
        xb, yb = xy(b)
        ax.plot([xa, xb], [ya, yb], color="#9467bd", lw=1.4, ls="--", zorder=2)

    # 5) facilities
    marker_cfg = {
        "H1": ("#e41a1c", "s", 230, "H1  hospital"),
        "D1": ("#377eb8", "s", 230, "D1  logistics depot"),
        "V1": ("#4daf4a", "^", 200, "V1  hospital landing"),
        "V2": ("#4daf4a", "^", 200, "V2  logistics hub landing"),
        "V3": ("#4daf4a", "^", 200, "V3  backup landing"),
        "B1": (link_colors["high"], "X", 260, "B1  disruption link (high)"),
        "B2": (link_colors["medium"], "X", 260, "B2  disruption link (medium)"),
        "B3": (link_colors["low"], "X", 260, "B3  disruption link (low)"),
    }
    # label offsets to reduce overlap (H1/V1 are close, D1/V2 are close)
    offsets = {"H1": (9, 9), "D1": (9, -14), "V1": (-80, 14), "V2": (9, -32),
               "V3": (9, 9), "B1": (9, 9), "B2": (9, 9), "B3": (9, 9)}
    for name, (col, mk, s, lbl) in marker_cfg.items():
        x, y = xy(name)
        ax.scatter(x, y, c=col, marker=mk, s=s, zorder=6, edgecolors="k",
                   linewidths=0.7, label=lbl)
        dx, dy = offsets[name]
        ax.annotate(name, (x, y), textcoords="offset points", xytext=(dx, dy),
                    fontsize=12, fontweight="bold", color=col, zorder=7,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))

    # 6) initial fleet positions (single source of truth: fleet.py)
    for acid, role, origin, dest, _pair, _mid in FLEET:
        if origin == "CENTER":
            c = cfg["study_area"]["center"]
            px, py = net.convertLonLat2XY(c["lon"], c["lat"])
        else:
            px, py = xy(origin)
        # slight per-aircraft jitter so overlapping dots are visible
        jx = (hash(acid) % 7 - 3) * 9
        jy = (hash(acid + "y") % 7 - 3) * 9
        ax.scatter(px + jx, py + jy, c="#111111", marker=".", s=34, zorder=8)

    # 7) study-area bbox frame
    b = cfg["bbox"]
    xs, ys = net.convertLonLat2XY(b["west"], b["south"])
    xn, yn = net.convertLonLat2XY(b["east"], b["north"])
    ax.add_patch(plt.Rectangle((xs, ys), xn - xs, yn - ys, fill=False,
                               edgecolor="#111111", lw=1.2, ls=":", zorder=0))

    ax.set_aspect("equal")
    ax.set_xlabel("SUMO x (m)  [UTM / WGS84-projected]")
    ax.set_ylabel("SUMO y (m)  [UTM / WGS84-projected]")
    ax.set_title("Unified ground–air scene — canonical_suzhou_testbed (S0, 3.2 km crop)\n"
                 "roads (gray) · D1→H1 corridor (blue) · B1/B2/B3 disruption links (red/orange/yellow) · "
                 "2 background air services (dashed) · 4-aircraft fleet (black dots)")
    ax.grid(alpha=0.15)

    legend_handles = [
        Line2D([0], [0], color="#8a8a8a", lw=1.0, label="major road"),
        Line2D([0], [0], color="#d5d5d5", lw=0.6, label="minor road"),
        Line2D([0], [0], color="#1f77b4", lw=2.6, label="D1→H1 corridor"),
        Line2D([0], [0], color=link_colors["high"], lw=5.0, label="B1 (high impact)"),
        Line2D([0], [0], color=link_colors["medium"], lw=5.0, label="B2 (medium)"),
        Line2D([0], [0], color=link_colors["low"], lw=5.0, label="B3 (low)"),
        Line2D([0], [0], color="#9467bd", lw=1.4, ls="--", label="background air service"),
    ]
    for name, (col, mk, s, lbl) in marker_cfg.items():
        legend_handles.append(Line2D([0], [0], marker=mk, color="w",
                                     markerfacecolor=col, markeredgecolor="k",
                                     markersize=9, label=lbl))
    legend_handles.append(Line2D([0], [0], marker=".", color="w",
                                 markerfacecolor="#111111", markersize=9,
                                 label="aircraft (initial)"))
    ax.legend(handles=legend_handles, loc="upper right", fontsize=8.5,
              framealpha=0.92, ncol=1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT, dpi=200)
    fig.savefig(OUT_POST, dpi=200)
    print(f"wrote {OUT}")
    print(f"wrote {OUT_POST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
