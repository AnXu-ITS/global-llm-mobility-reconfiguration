"""Select B2 (secondary ground-disruption link) for Site B / Site C.

Mirrors the Site-A process (tools/select_disruptions.py): rank candidate edges
on the D1->H1 baseline route by single-closure ETA impact via the TraCI router,
then pick a B2 with a meaningful but SMALLER impact than the site's B1
(Site A: LOW B2 +15.4% < MEDIUM B1 +37.9%).

Outputs:
  outputs/cross_site/site_b_disruption_ranking.csv
  outputs/cross_site/site_c_disruption_ranking.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import cross_site_lib as lib  # noqa: E402

SITES = {
    "b": {
        "site_id": "site_b_amsterdam",
        "cfg": ROOT / "sim" / "sites" / "site_b_amsterdam" / "config" /
              "site_b_amsterdam_config.yaml",
        "net": ROOT / "sim" / "sites" / "site_b_amsterdam" / "sumo" /
               "network.net.xml",
        "label": "site_b_disruption_ranking.csv",
    },
    "c": {
        "site_id": "site_c_edmonton",
        "cfg": ROOT / "sim" / "sites" / "site_c_edmonton" / "config" /
              "site_c_edmonton_config.yaml",
        "net": ROOT / "sim" / "sites" / "site_c_edmonton" / "sumo" /
               "network.net.xml",
        "label": "site_c_disruption_ranking.csv",
    },
}

MIN_MEANINGFUL_PCT = 5.0


def main() -> int:
    out_root = ROOT / "outputs" / "cross_site"
    out_root.mkdir(parents=True, exist_ok=True)
    for key in ("b", "c"):
        s = SITES[key]
        cfg: Dict[str, Any] = yaml.safe_load(s["cfg"].read_text(encoding="utf-8"))
        d1 = cfg["sumo_mapping"]["D1"]["edge_id"]
        h1 = cfg["sumo_mapping"]["H1"]["edge_id"]
        b1_edge = cfg["disruption_links"]["links"]["B1"]["edge_id"]
        b1_pct = float(cfg["disruption_links"]["links"]["B1"]["eta_increase_pct"])

        net = lib.load_net(s["net"])
        with lib.traci_session(s["net"], f"rank_{key}") as traci:
            base_edges = lib.route_edges(traci, d1, h1) or []
            candidates: List[str] = [e for e in base_edges if e not in (d1, h1)]
            if key == "b":
                for e in cfg["water"]["main_crossing_edges"]:
                    if e not in candidates:
                        candidates.append(e)
            res = lib.closure_analysis(net, traci, d1, h1, candidates)

        rows = []
        for r in res["closures"]:
            pct = r.get("increase_pct")
            if pct is None or not r.get("detour_exists"):
                continue
            if pct < MIN_MEANINGFUL_PCT:
                continue
            rows.append(r)

        csv_path = out_root / s["label"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["edge_id", "eta_s", "dist_m",
                                              "increase_pct", "detour_exists",
                                              "detour_boundary_share"])
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in w.fieldnames})

        print(f"=== {s['site_id']} ranked closure candidates (>= {MIN_MEANINGFUL_PCT:.0f}%) ===")
        print(f"    B1 = {b1_edge} (+{b1_pct:.2f}%)")
        for r in rows[:12]:
            mark = " <== B1 (existing)" if r["edge_id"] == b1_edge else ""
            print(f"    {r['edge_id']:32s} +{r['increase_pct']:6.2f}%  "
                  f"eta={r['eta_s']:.1f}s  boundary_share={r['detour_boundary_share']:.3f}{mark}")
        # candidate B2: strongest below B1's impact (not B1 itself)
        b2 = None
        for r in rows:
            if r["edge_id"] != b1_edge and r["increase_pct"] < b1_pct:
                b2 = r
                break
        if b2:
            print(f"    -> suggested B2: {b2['edge_id']} (+{b2['increase_pct']:.2f}%)")
        print(f"    [saved] {csv_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
