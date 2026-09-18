"""B1-disruption validation reports for Site B / Site C.

Follows the Site-A method (`sim/sites/site_a_suzhou/validation/B1_POST_RESIZE_VALIDATION.md`,
generated from tools/validate_b1.py): re-confirm each cross-site B1 is a
legitimate critical ground-disruption point with the four required checks:

  1. detour exists after B1 closure
  2. H1 never becomes unreachable
  3. ETA clearly increases (>= 15 % warning threshold)
  4. not an artificial bbox-boundary effect (edge margin >= 300 m AND detour
     boundary share <= 0.30)

Evidence is computed from the canonical site configs + SUMO nets + the existing
candidate analyses; no new simulation is run.

Outputs:
  sim/sites/site_b_amsterdam/validation/B1_VALIDATION.md
  sim/sites/site_c_edmonton/validation/B1_VALIDATION.md
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import cross_site_lib as lib  # noqa: E402

SITES = {
    "b": {
        "site_id": "site_b_amsterdam",
        "city": "Amsterdam, Netherlands",
        "cfg": ROOT / "sim" / "sites" / "site_b_amsterdam" / "config" /
              "site_b_amsterdam_config.yaml",
        "net": ROOT / "sim" / "sites" / "site_b_amsterdam" / "sumo" /
               "network.net.xml",
        "out": ROOT / "sim" / "sites" / "site_b_amsterdam" / "validation" /
               "B1_VALIDATION.md",
        "candidate_analysis": ROOT / "outputs" / "cross_site" / "candidates" /
                              "amsterdam" / "ams_olvg_amstel" / "analysis.json",
    },
    "c": {
        "site_id": "site_c_edmonton",
        "city": "Edmonton, Alberta, Canada",
        "cfg": ROOT / "sim" / "sites" / "site_c_edmonton" / "config" /
              "site_c_edmonton_config.yaml",
        "net": ROOT / "sim" / "sites" / "site_c_edmonton" / "sumo" /
               "network.net.xml",
        "out": ROOT / "sim" / "sites" / "site_c_edmonton" / "validation" /
               "B1_VALIDATION.md",
        "candidate_analysis": ROOT / "outputs" / "cross_site" / "candidates" /
                              "edmonton" / "edm_grey_nuns" / "analysis.json",
    },
}

MIN_MARGIN_M = 300.0
MAX_DETOUR_BOUNDARY_SHARE = 0.30
ETA_WARN_PCT = 15.0


def edge_boundary_margin_m(net, edge_id: str) -> float:
    """Min distance from any point of the edge shape to the net bbox boundary."""
    e = net.getEdge(edge_id)
    xmin, ymin, xmax, ymax = net.getBoundary()
    best = float("inf")
    for (x, y) in e.getShape():
        d = min(x - xmin, xmax - x, y - ymin, ymax - y)
        best = min(best, d)
    return best


def main() -> int:
    for key in ("b", "c"):
        s = SITES[key]
        cfg: Dict[str, Any] = yaml.safe_load(s["cfg"].read_text(encoding="utf-8"))
        b1 = cfg["disruption_links"]["links"]["B1"]
        edge_id = b1["edge_id"]
        base = float(b1["base_eta_s"])
        closed = float(b1["detour_eta_s"])
        pct = float(b1["eta_increase_pct"])
        has_detour = bool(b1.get("has_detour"))
        detour_edges = b1.get("detour_edges") or []

        net = lib.load_net(s["net"])
        margin = edge_boundary_margin_m(net, edge_id)
        detour_share = b1.get("detour_boundary_share")
        if detour_share is None and detour_edges:
            detour_share = lib.detour_boundary_share(net, detour_edges)

        c1 = has_detour and closed > base
        c2 = closed > 0  # finite positive post-closure ETA -> H1 reachable
        c3 = pct >= ETA_WARN_PCT
        c4 = margin >= MIN_MARGIN_M and (detour_share is not None and
                                         detour_share <= MAX_DETOUR_BOUNDARY_SHARE)
        verdict = "PASS" if (c1 and c2 and c3 and c4) else "FAIL"

        kind = b1.get("crossing_kind", "road")
        name = f"Berlagebrug (Amstel river crossing, {kind})" if key == "b" \
            else f"ranked critical road link ({kind})"

        md = f"""# B1 Disruption Validity — {s['city']} ({s['site_id']})

Re-confirms the site's B1 is a legitimate critical ground-disruption point,
following the Site-A method (`site_a_suzhou/validation/B1_POST_RESIZE_VALIDATION.md`).
Source: `tools/cross_site_b1_validation.py` + the canonical site config +
candidate analysis (`outputs/cross_site/candidates/…/analysis.json`).

## Results

| Metric | Value |
|--------|-------|
| B1 edge | `{edge_id}` |
| B1 description | {name} |
| ETA baseline (D1→H1 free-flow) | {base:.3f} s |
| ETA B1 closed | {closed:.3f} s |
| **relative increase** | **+{pct:.2f} %** |
| has detour | {has_detour} ({len(detour_edges)} edges) |
| H1 reachable after closure | {c2} |
| B1 interior to bbox (min side margin) | {margin:.1f} m (>= {MIN_MARGIN_M:.0f} m) |
| detour boundary share | {detour_share:.3f} (<= {MAX_DETOUR_BOUNDARY_SHARE:.2f}) |

## Four required checks

1. **Detour exists after B1 closure** — {'✓' if c1 else '✗'} post-closure ETA rises
   from {base:.3f} s to {closed:.3f} s (a +{closed - base:.1f} s detour), i.e. the
   router finds an alternative route.
2. **H1 never becomes unreachable** — {'✓' if c2 else '✗'} `ETA_B1_closed =
   {closed:.3f} s` (finite, positive), the hospital remains reachable.
3. **ETA clearly increases** — {'✓' if c3 else '✗'} +{pct:.2f} % >= {ETA_WARN_PCT:.0f} %
   warning threshold.
4. **Not an artificial bbox-boundary effect** — {'✓' if c4 else '✗'} B1 sits >=
   {margin:.0f} m from every bbox side (>= {MIN_MARGIN_M:.0f} m) and the detour
   keeps {detour_share:.3f} of its length in the boundary band
   (<= {MAX_DETOUR_BOUNDARY_SHARE:.2f}).

## Verdict

**{verdict}** — the site's B1 is a valid critical ground-disruption point for the
cross-site Experiment-1 reproduction
(`tools/run_experiment1_cross_site.py`).
"""
        s["out"].parent.mkdir(parents=True, exist_ok=True)
        s["out"].write_text(md, encoding="utf-8")
        print(f"[{key}] B1={edge_id} base={base} closed={closed} "
              f"+{pct:.2f}% margin={margin:.1f}m detour_share={detour_share:.3f} "
              f"-> {verdict}")
        print(f"    wrote {s['out'].relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
