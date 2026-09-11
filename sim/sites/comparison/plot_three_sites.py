"""Canonical three-site unified plotter (sim/sites/comparison/plot_three_sites.py).

Reads the canonical tree:
  sim/sites/<site_id>/{config,osm,sumo,facilities,routes}
and writes:
  sim/sites/<site_id>/figures/site_<id>_unified_scene_v2.png       (DEBUG)
  sim/sites/<site_id>/figures/site_<id>_unified_scene_paper.png    (PAPER)
  sim/sites/comparison/three_site_cross_validation_v2.png
  sim/sites/comparison/three_site_cross_validation_paper.png (300 dpi)
  sim/sites/comparison/three_site_cross_validation_paper.pdf
  sim/sites/comparison/plot_qa.json  (label-overlap + style self-check)

Unified visual grammar (single source of truth for all three panels):
  Layer 1 roads            thin neutral gray
  Layer 2 water            light blue
  Layer 3 primary ground   solid thick red
  Layer 4 primary detour   dashed thick pink
  Layer 5 primary air      dotted green (straight line)
  Layer 6 auxiliary ground thin semi-transparent brown
  Layer 7 facilities       primary filled / auxiliary hollow
  Layer 8 B1               orange X
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from tools import cross_site_lib as lib  # noqa: E402

SITES_ROOT = Path(__file__).resolve().parents[1]
COMPARISON = SITES_ROOT / "comparison"

STYLE = {
    "road": {"color": "#c9c9c9", "lw": 0.5, "alpha": 0.75},
    "water": {"facecolor": "#9ecae1", "alpha": 0.75},
    "primary_ground": {"color": "#d62728", "lw": 3.2, "ls": "-", "alpha": 1.0},
    "primary_detour": {"color": "#e377c2", "lw": 2.8, "ls": "--", "alpha": 1.0},
    "primary_air": {"color": "#2ca02c", "lw": 2.4, "ls": ":", "alpha": 1.0},
    "aux_ground": {"color": "#8c564b", "lw": 1.8, "ls": "-", "alpha": 0.62},
    "aux_air": {"color": "#17becf", "lw": 1.4, "ls": ":", "alpha": 0.55},
    "bbox": {"color": "black", "lw": 1.6},
}

FAC_STYLE = {
    "H1": {"c": "#d62728", "m": "o", "filled": True},
    "D1": {"c": "#1f77b4", "m": "o", "filled": True},
    "V1": {"c": "#2ca02c", "m": "s", "filled": True},
    "V2": {"c": "#2ca02c", "m": "s", "filled": True},
    "V3": {"c": "#2ca02c", "m": "s", "filled": True},
    "B1": {"c": "#ff7f0e", "m": "X", "filled": True},
    "H2": {"c": "#d62728", "m": "o", "filled": False},
    "C2": {"c": "#7f7f7f", "m": "D", "filled": False},
    "C3": {"c": "#7f7f7f", "m": "D", "filled": False},
    "D2": {"c": "#1f77b4", "m": "o", "filled": False},
    "V4": {"c": "#2ca02c", "m": "s", "filled": False},
    "V5": {"c": "#2ca02c", "m": "s", "filled": False},
}

SITE_META = {
    "site_a_suzhou": {"label": "Site A", "city": "Suzhou, China",
                      "morph": "Meshed Urban"},
    "site_b_amsterdam": {"label": "Site B", "city": "Amsterdam, Netherlands",
                         "morph": "Water-Barrier Urban"},
    "site_c_edmonton": {"label": "Site C", "city": "Edmonton, Canada",
                        "morph": "Sparse Suburban"},
}

QA: dict = {"label_overlaps": [], "styles": {}}


def load_site(site_id: str):
    import yaml
    site = SITES_ROOT / site_id
    cfg_path = site / "config" / f"{site_id}_config.yaml"
    if not cfg_path.exists():
        cfg_path = site / "config" / "scenario_config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    net = lib.load_net(site / "sumo" / "network.net.xml")
    water_json = json.loads((site / "osm" / "water_osm.json")
                            .read_text(encoding="utf-8"))
    wgeoms = lib.water_geometries(water_json, net)
    primary = json.loads((site / "routes" / "primary.json")
                         .read_text(encoding="utf-8"))
    aux_path = site / "routes" / "auxiliary.json"
    auxiliary = json.loads(aux_path.read_text(encoding="utf-8")) \
        if aux_path.exists() else {}
    return cfg, net, wgeoms, primary, auxiliary


def draw_routes(ax, net, edges, style):
    pts = []
    for eid in edges:
        try:
            pts.extend(net.getEdge(eid).getShape())
        except Exception:  # noqa: BLE001
            continue
    if len(pts) >= 2:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], zorder=4, **style)
    return len(pts) >= 2


def draw_panel(ax, site_id: str, cfg, net, wgeoms, primary, auxiliary,
               paper: bool, panel_label: str = ""):
    xmin, ymin, xmax, ymax = net.getBoundary()

    # Layer 1: roads
    segs = []
    for e in net.getEdges():
        if not e.allows("passenger"):
            continue
        s = e.getShape()
        if len(s) >= 2:
            segs.append([(x, y) for x, y in s])
    ax.add_collection(LineCollection(segs, colors=STYLE["road"]["color"],
                                     linewidths=STYLE["road"]["lw"],
                                     alpha=STYLE["road"]["alpha"], zorder=1))

    # Layer 2: water
    for w in wgeoms:
        g = w["geom"]
        if g.geom_type == "Polygon":
            ax.add_patch(MplPolygon(list(g.exterior.coords), closed=True,
                                    facecolor=STYLE["water"]["facecolor"],
                                    edgecolor="none",
                                    alpha=STYLE["water"]["alpha"], zorder=0))
        elif g.geom_type == "LineString":
            ax.plot(*g.xy, color=STYLE["water"]["facecolor"],
                    linewidth=1.2, alpha=0.9, zorder=0)

    # bbox
    ax.add_patch(plt.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin,
                               fill=False, **{k: STYLE["bbox"][k]
                                              for k in ("color", "lw")},
                               zorder=5))

    mapping = cfg["sumo_mapping"]
    # Layers 3-5: primary routes
    base = primary.get("baseline", {}).get("edges") or []
    det = primary.get("detour", {}).get("edges") or []
    draw_routes(ax, net, base, STYLE["primary_ground"])
    draw_routes(ax, net, det, STYLE["primary_detour"])
    if "V2" in mapping and "V1" in mapping:
        ax.plot([mapping["V2"]["x"], mapping["V1"]["x"]],
                [mapping["V2"]["y"], mapping["V1"]["y"]], zorder=4,
                **STYLE["primary_air"])

    # Layer 6: auxiliary routes
    for od_id, r in auxiliary.items():
        draw_routes(ax, net, r.get("edges") or [], STYLE["aux_ground"])
    if "V4" in mapping and "V5" in mapping:
        ax.plot([mapping["V5"]["x"], mapping["V4"]["x"]],
                [mapping["V5"]["y"], mapping["V4"]["y"]], zorder=4,
                **STYLE["aux_air"])

    # Layer 7: facilities (primary first, then auxiliary)
    primary_keys = ["H1", "D1", "V1", "V2", "V3"]
    aux_keys = [k for k in mapping if k not in primary_keys and k != "B1"
                and k in FAC_STYLE]
    # landing sites V1/V2/V4/V5 are co-located with their parent facility --
    # draw the symbol but no separate label (prevents label overlap)
    no_label = {"V1", "V2", "V4", "V5"}
    label_texts = []
    for k in primary_keys + aux_keys + ["B1"]:
        if k not in mapping:
            continue
        st = FAC_STYLE[k]
        ax.scatter(mapping[k]["x"], mapping[k]["y"],
                   s=110 if st["filled"] else 100,
                   marker=st["m"],
                   facecolors=st["c"] if st["filled"] else "none",
                   edgecolors=st["c"], linewidths=1.4 if st["filled"] else 1.6,
                   zorder=6)
        if k in no_label:
            continue
        off = {"H1": (14, 14), "D1": (-14, 14), "V3": (-14, 14),
               "B1": (20, -18), "H2": (-16, 14), "D2": (14, -16),
               "C2": (-16, -16), "C3": (14, 16)}.get(k, (0, 0))
        t = ax.text(mapping[k]["x"] + off[0], mapping[k]["y"] + off[1], k,
                    fontsize=8.5 if not paper else 6.5,
                    fontweight="bold" if st["filled"] else "normal",
                    color=st["c"], zorder=7,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white",
                              ec="none", alpha=0.85) if not paper else None)
        label_texts.append((k, t))

    # north arrow + scale bar
    ax.annotate("N", xy=(xmax - 60, ymax - 60), xytext=(xmax - 60, ymax - 150),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.4),
                fontsize=9, ha="center", zorder=8)
    scale_m = 500
    ax.plot([xmin + 60, xmin + 60 + scale_m], [ymin + 60, ymin + 60],
            color="black", lw=2.2, zorder=8)
    ax.text(xmin + 60 + scale_m / 2, ymin + 78, f"{scale_m} m",
            fontsize=8, ha="center", zorder=8)

    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(xmin - 40, xmax + 40)
    ax.set_ylim(ymin - 40, ymax + 40)

    # title
    meta = SITE_META[site_id]
    if paper:
        ax.set_title(panel_label or f"{meta['label']} — {meta['morph']}",
                     fontsize=10, fontweight="bold", loc="left", pad=4)
    else:
        ax.set_title(f"{meta['label']} -- {meta['city']}\n"
                     f"{meta['morph']} | primary D1->H1 + auxiliary ODs",
                     fontsize=10, fontweight="bold")

    return label_texts


def unified_legend(ax, paper: bool):
    handles = [
        Line2D([0], [0], color=STYLE["primary_ground"]["color"],
               lw=STYLE["primary_ground"]["lw"], label="Primary ground route"),
        Line2D([0], [0], color=STYLE["primary_detour"]["color"],
               lw=STYLE["primary_detour"]["lw"], ls="--",
               label="Primary detour (B1 closed)"),
        Line2D([0], [0], color=STYLE["primary_air"]["color"],
               lw=STYLE["primary_air"]["lw"], ls=":",
               label="Primary low-altitude route"),
        Line2D([0], [0], color=STYLE["aux_ground"]["color"],
               lw=STYLE["aux_ground"]["lw"], alpha=STYLE["aux_ground"]["alpha"],
               label="Auxiliary ground routes"),
        Line2D([0], [0], color=STYLE["aux_air"]["color"],
               lw=STYLE["aux_air"]["lw"], ls=":", alpha=STYLE["aux_air"]["alpha"],
               label="Auxiliary low-altitude"),
        Line2D([0], [0], marker="o", color="#d62728", lw=0,
               label="Primary facility (H1/D1)"),
        Line2D([0], [0], marker="s", color="#2ca02c", lw=0,
               label="Landing site (V1/V2/V3)"),
        Line2D([0], [0], marker="X", color="#ff7f0e", lw=0,
               label="Disruption B1"),
        Line2D([0], [0], marker="o", color="#8c564b", lw=0,
               markerfacecolor="none", markeredgecolor="#8c564b",
               label="Auxiliary facility"),
    ]
    ax.legend(handles=handles, loc="lower center",
              bbox_to_anchor=(0.5, -0.02), ncol=3 if paper else 2,
              fontsize=7.5 if paper else 8.5, frameon=True,
              framealpha=0.95, title=None)


def main() -> int:
    sites = ["site_a_suzhou", "site_b_amsterdam", "site_c_edmonton"]
    data = {}
    for sid in sites:
        data[sid] = load_site(sid)

    # ---------------- single-site figures ----------------
    for sid in sites:
        cfg, net, wgeoms, primary, auxiliary = data[sid]
        meta = SITE_META[sid]
        for paper, tag in ((False, "v2"), (True, "paper")):
            fig, ax = plt.subplots(figsize=(9.6, 9.2))
            texts = draw_panel(ax, sid, cfg, net, wgeoms, primary, auxiliary,
                               paper=paper)
            if not paper:
                unified_legend(ax, paper=False)
            out = SITES_ROOT / sid / "figures" / \
                f"{sid}_unified_scene_{tag}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"wrote {out}")
            if not paper:
                QA["styles"][sid] = {k: v for k, v in STYLE.items()}

    # ---------------- three-site comparison ----------------
    panels = [("site_a_suzhou", "(a) Site A — Meshed Urban"),
              ("site_b_amsterdam", "(b) Site B — Water-Barrier Urban"),
              ("site_c_edmonton", "(c) Site C — Sparse Suburban")]
    for paper, tag, dpi, figsize in (
            (False, "v2", 150, (19.5, 6.8)),
            (True, "paper", 300, (10.8, 3.75))):
        fig, axes = plt.subplots(1, 3, figsize=figsize)
        label_boxes = []
        for ax, (sid, plabel) in zip(axes, panels):
            cfg, net, wgeoms, primary, auxiliary = data[sid]
            texts = draw_panel(ax, sid, cfg, net, wgeoms, primary, auxiliary,
                               paper=paper, panel_label=plabel)
            meta = SITE_META[sid]
            if paper:
                ax.text(0.5, 0.985, meta["city"], transform=ax.transAxes,
                        fontsize=6.0, ha="center", va="top", style="italic",
                        color="#444444")
            label_boxes.append((sid, texts))
        if not paper:
            for ax in axes:
                unified_legend(ax, paper=False)
        else:
            # compact shared legend for the paper version
            handles = [
                Line2D([0], [0], color=STYLE["primary_ground"]["color"], lw=2.2,
                       label="primary route"),
                Line2D([0], [0], color=STYLE["primary_detour"]["color"], lw=2.2,
                       ls="--", label="detour (B1 closed)"),
                Line2D([0], [0], color=STYLE["primary_air"]["color"], lw=1.8,
                       ls=":", label="low-altitude"),
                Line2D([0], [0], color=STYLE["aux_ground"]["color"], lw=1.6,
                       alpha=0.62, label="auxiliary"),
                Line2D([0], [0], marker="X", color="#ff7f0e", lw=0,
                       label="B1"),
            ]
            fig.legend(handles=handles, loc="lower center", ncol=5,
                       fontsize=7.0, frameon=False, bbox_to_anchor=(0.5, 0.0))
        fig.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.06,
                            wspace=0.06)
        png_out = COMPARISON / f"three_site_cross_validation_{tag}.png"
        fig.savefig(png_out, dpi=dpi, bbox_inches="tight",
                    facecolor="white")
        if paper:
            pdf_out = COMPARISON / "three_site_cross_validation_paper.pdf"
            fig.savefig(pdf_out, dpi=300, bbox_inches="tight",
                        facecolor="white")
            print(f"wrote {pdf_out}")
        plt.close(fig)
        print(f"wrote {png_out}")

        # label-overlap QA (renderer-based geometry check)
        if not paper:
            fig2, axes2 = plt.subplots(1, 3, figsize=(19.5, 6.8))
            for ax, (sid, plabel) in zip(axes2, panels):
                cfg, net, wgeoms, primary, auxiliary = data[sid]
                texts = draw_panel(ax, sid, cfg, net, wgeoms, primary,
                                   auxiliary, paper=False, panel_label=plabel)
                fig2.canvas.draw()
                ren = fig2.canvas.get_renderer()
                boxes = []
                for k, t in texts:
                    bb = t.get_window_extent(renderer=ren)
                    boxes.append((k, (bb.x0, bb.y0, bb.x1, bb.y1)))
                for i in range(len(boxes)):
                    for j in range(i + 1, len(boxes)):
                        a, b = boxes[i][1], boxes[j][1]
                        if not (a[2] <= b[0] or b[2] <= a[0]
                                or a[3] <= b[1] or b[3] <= a[1]):
                            QA["label_overlaps"].append(
                                {"figure": tag, "site": sid,
                                 "pair": [boxes[i][0], boxes[j][0]],
                                 "bboxes": [a, b]})
            plt.close(fig2)

    QA["label_overlaps_n"] = len(QA["label_overlaps"])
    (COMPARISON / "plot_qa.json").write_text(
        json.dumps(QA, indent=2, default=str), encoding="utf-8")
    print(f"QA: {len(QA['label_overlaps'])} label overlaps recorded -> "
          f"{COMPARISON / 'plot_qa.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
