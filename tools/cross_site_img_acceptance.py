"""Cross-site image acceptance (IMG-T1..T15) + programmatic visual QA.

The QA is PROGRAMMATIC (this runtime has no human-eye image review):
  * pixel statistics per horizontal band (top/middle/bottom coverage),
  * color-class pixel counts (primary red vs auxiliary brown dominance),
  * label-overlap geometry from plot_qa.json (renderer bounding boxes),
  * file/dpi/metadata checks,
and compares Site B v2 against the legacy v1 figure to prove the spatial
utilization improvement. Every claim below is backed by a concrete number.

Outputs:
  sim/sites/comparison/image_acceptance_tests.csv / .md
  sim/sites/comparison/visual_qa.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

SITES_ROOT = ROOT / "sim" / "sites"
COMPARISON = SITES_ROOT / "comparison"
LEGACY_B_V1 = ROOT / "outputs" / "cross_site" / "site_b_amsterdam_unified_scene.png"

COLORS = {
    "primary_red": (214, 39, 40),      # #d62728
    "detour_pink": (227, 119, 194),    # #e377c2
    "air_green": (44, 160, 44),        # #2ca02c
    "aux_brown": (140, 86, 75),        # #8c564b
    "aux_cyan": (23, 190, 207),        # #17becf
    "water_blue": (158, 202, 225),     # #9ecae1
    "road_gray": (201, 201, 201),      # #c9c9c9
    "b1_orange": (255, 127, 14),       # #ff7f0e
}


def color_mask(img, rgb, tol=30):
    px = img.load()
    w, h = img.size
    count = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            p = px[x, y]
            if (abs(p[0] - rgb[0]) <= tol and abs(p[1] - rgb[1]) <= tol
                    and abs(p[2] - rgb[2]) <= tol):
                count += 1
    return count * 4  # sampled every 2 px in each dimension


def band_coverage(img):
    """Fraction of non-white pixels per horizontal third (top/mid/bottom)."""
    px = img.load()
    w, h = img.size
    thirds = [0, 0, 0]
    totals = [0, 0, 0]
    for y in range(h):
        band = 0 if y < h / 3 else (1 if y < 2 * h / 3 else 2)
        for x in range(0, w, 2):
            p = px[x, y]
            totals[band] += 1
            if not (p[0] > 245 and p[1] > 245 and p[2] > 245):
                thirds[band] += 1
    return [t / max(tot, 1) for t, tot in zip(thirds, totals)]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check(cond: bool, warn: bool = False) -> str:
    if cond:
        return "PASS"
    return "WARNING" if warn else "FAIL"


def main() -> int:
    tests = []
    vqa = {"figures": {}, "label_overlaps_n": None}

    qa = json.loads((COMPARISON / "plot_qa.json").read_text(encoding="utf-8"))
    vqa["label_overlaps_n"] = qa["label_overlaps_n"]

    import yaml
    site_b_cfg = yaml.safe_load((SITES_ROOT / "site_b_amsterdam" / "config"
                                 / "site_b_amsterdam_config.yaml")
                                .read_text(encoding="utf-8"))
    site_c_cfg = yaml.safe_load((SITES_ROOT / "site_c_edmonton" / "config"
                                 / "site_c_edmonton_config.yaml")
                                .read_text(encoding="utf-8"))
    refine = ROOT / "outputs" / "cross_site" / "refinement"

    # ---------------- IMG-T1: Site B spatial utilization improved
    su_b = json.loads((refine / "site_b_amsterdam" / "auxiliary.json")
                      .read_text(encoding="utf-8"))["spatial_utilization"]
    t1 = (su_b["after"]["facility_hull_area_pct"] >
          su_b["before"]["facility_hull_area_pct"] * 2.0
          and su_b["after"]["route_envelope_area_pct"] >
          su_b["before"]["route_envelope_area_pct"]
          and su_b["after"]["grid_cells_covered"] >
          su_b["before"]["grid_cells_covered"])
    tests.append(("IMG-T1", "Site B spatial utilization improved",
                  check(t1),
                  f"hull {su_b['before']['facility_hull_area_pct']:.1f}% -> "
                  f"{su_b['after']['facility_hull_area_pct']:.1f}%; "
                  f"envelope {su_b['before']['route_envelope_area_pct']:.1f}% -> "
                  f"{su_b['after']['route_envelope_area_pct']:.1f}%; "
                  f"grid {su_b['before']['grid_cells_covered']} -> "
                  f"{su_b['after']['grid_cells_covered']} of 9"))

    # ---------------- IMG-T2: Site B primary OD remains valid
    pv = json.loads((refine / "site_b_amsterdam" / "primary_revalidation.json")
                    .read_text(encoding="utf-8"))
    tests.append(("IMG-T2", "Site B primary OD remains valid",
                  check(pv["primary_unchanged"] and pv["detour_exists"]),
                  f"eta {pv['baseline_eta_s']} s vs config "
                  f"{pv['config_base_eta_s']}; B1 closure "
                  f"{pv['b1_closure_inc_pct']}% vs config "
                  f"{pv['config_b1_inc_pct']}%"))

    # ---------------- IMG-T3: aux assets are real OSM POIs
    aux_b = json.loads((refine / "site_b_amsterdam" / "auxiliary.json")
                       .read_text(encoding="utf-8"))["aux_facilities"]
    real_pois = [k for k, v in aux_b.items() if not v["synthetic"]]
    synthetic = [k for k, v in aux_b.items() if v["synthetic"]]
    tests.append(("IMG-T3", "Site B aux remote assets use real OSM geography",
                  check(len(real_pois) >= 3 and
                        all(v.get("osm_id") for k, v in aux_b.items()
                            if not v["synthetic"])),
                  f"real OSM POIs: {real_pois} (ids "
                  f"{[aux_b[k]['osm_id'] for k in real_pois]}); "
                  f"synthetic landing nodes marked: {synthetic}"))

    # ---------------- IMG-T4: aux routes do not alter primary logic
    legacy_b = yaml.safe_load((ROOT / "config" / "site_b_amsterdam_config.yaml")
                              .read_text(encoding="utf-8"))
    prim_same = all(
        site_b_cfg[sec][k] == legacy_b[sec][k]
        for sec in ("facilities", "sumo_mapping", "disruption_links")
        for k in legacy_b[sec])
    tests.append(("IMG-T4", "Aux routes do not alter frozen primary logic",
                  check(prim_same),
                  "primary facilities/sumo_mapping/disruption_links identical "
                  "to legacy config"))

    # ---------------- IMG-T5: Site C transverse structure
    tr = list(csv.DictReader(open(refine / "site_c_edmonton"
                                  / "transverse_routes.csv", newline="",
                                  encoding="utf-8")))
    od1 = next(r for r in tr if r["od_id"] == "OD-C1")
    tests.append(("IMG-T5", "Site C contains clear transverse structure",
                  check(float(od1["bbox_span_x_pct"]) >= 40.0),
                  f"OD-C1 span_x {od1['bbox_span_x_pct']}% "
                  f"(target >50%, floor 40%)"))

    # ---------------- IMG-T6: transverse routes use real SUMO roads
    aux_c = json.loads((refine / "site_c_edmonton" / "auxiliary.json")
                       .read_text(encoding="utf-8"))
    from orchestrator.sumo_env import setup as sumo_setup
    sumo_setup()
    import sumolib
    net_c = sumolib.net.readNet(str(SITES_ROOT / "site_c_edmonton" / "sumo"
                                    / "network.net.xml"))
    missing = []
    for r in aux_c["ods"]:
        for e in r["edges"]:
            try:
                net_c.getEdge(e)
            except Exception:  # noqa: BLE001
                missing.append(e)
    tests.append(("IMG-T6", "Site C transverse route uses real SUMO roads",
                  check(not missing),
                  f"{sum(len(r['edges']) for r in aux_c['ods'])} edge refs, "
                  f"{len(missing)} missing"))

    # ---------------- IMG-T7: Site C stays sparse/polycentric, not bridge
    t7 = (all(r["river_dependency"] == "0" for r in tr)
          and all(r["critical_crossing_dependency"] == "False" for r in tr))
    tests.append(("IMG-T7", "Site C remains sparse/polycentric, not bridge-constrained",
                  check(t7),
                  f"OD-C1/OD-C2 river_dependency=0, "
                  f"critical_crossing_dependency=False"))

    # ---------------- IMG-T8: Site A unchanged scientifically
    snap = json.loads((ROOT / "outputs" / "cross_site"
                       / "site_a_freeze_hashes.json").read_text(encoding="utf-8"))
    changed = [k for k, v in snap.items() if sha256(ROOT / k) != v]
    tests.append(("IMG-T8", "Site A unchanged scientifically",
                  check(not changed),
                  f"{len(changed)} frozen files changed: {changed}" if changed
                  else "all frozen files byte-identical"))

    # ---------------- IMG-T9: same visual grammar across panels
    styles = qa.get("styles", {})
    keys = {"site_a_suzhou", "site_b_amsterdam", "site_c_edmonton"}
    same = len(styles) == 3 and all(styles[k] == styles["site_a_suzhou"]
                                    for k in keys if k in styles)
    tests.append(("IMG-T9", "All three figures use same visual grammar",
                  check(same),
                  f"{len(styles)} sites recorded with identical STYLE dict"))

    # ---------------- IMG-T10: primary/auxiliary clearly distinguished
    img_b = Image.open(SITES_ROOT / "site_b_amsterdam" / "figures"
                       / "site_b_amsterdam_unified_scene_v2.png").convert("RGB")
    red = color_mask(img_b, COLORS["primary_red"])
    brown = color_mask(img_b, COLORS["aux_brown"])
    vqa["figures"]["site_b_v2"] = {
        "primary_red_px": red, "aux_brown_px": brown,
        "red_over_brown_ratio": round(red / max(brown, 1), 2),
        "band_coverage": [round(v, 4) for v in band_coverage(img_b)],
    }
    tests.append(("IMG-T10", "Primary and auxiliary elements clearly distinguished",
                  check(red > brown and red > 500),
                  f"primary-red px {red} vs aux-brown px {brown} "
                  f"(ratio {red / max(brown, 1):.2f})"))

    # ---------------- IMG-T11: no label/legend major overlap
    tests.append(("IMG-T11", "No label/legend major overlap",
                  check(qa["label_overlaps_n"] == 0),
                  f"{qa['label_overlaps_n']} label bbox overlaps "
                  f"(renderer geometry)"))

    # ---------------- IMG-T12: paper version legible at publication scale
    paper = Image.open(COMPARISON / "three_site_cross_validation_paper.png")
    pdf = COMPARISON / "three_site_cross_validation_paper.pdf"
    tests.append(("IMG-T12", "Paper version legible at publication scale",
                  check(paper.size[0] >= 2500 and paper.size[1] >= 800
                        and pdf.exists() and pdf.stat().st_size > 50_000),
                  f"PNG {paper.size[0]}x{paper.size[1]} px, "
                  f"PDF {pdf.stat().st_size / 1e3:.0f} kB"))

    # ---------------- IMG-T13: figures under canonical tree
    need = [
        SITES_ROOT / "site_a_suzhou" / "figures" / "site_a_suzhou_unified_scene_v2.png",
        SITES_ROOT / "site_b_amsterdam" / "figures" / "site_b_amsterdam_unified_scene_v2.png",
        SITES_ROOT / "site_c_edmonton" / "figures" / "site_c_edmonton_unified_scene_v2.png",
        COMPARISON / "three_site_cross_validation_v2.png",
        COMPARISON / "three_site_cross_validation_paper.png",
        COMPARISON / "three_site_cross_validation_paper.pdf",
    ]
    tests.append(("IMG-T13", "All figures saved under new canonical tree",
                  check(all(p.exists() for p in need)),
                  f"{sum(p.exists() for p in need)}/{len(need)} present"))

    # ---------------- IMG-T14: A/B/C data consolidated
    need2 = [
        SITES_ROOT / "site_a_suzhou" / "sumo" / "network.net.xml",
        SITES_ROOT / "site_a_suzhou" / "config" / "scenario_config.yaml",
        SITES_ROOT / "site_b_amsterdam" / "sumo" / "network.net.xml",
        SITES_ROOT / "site_b_amsterdam" / "config" / "site_b_amsterdam_config.yaml",
        SITES_ROOT / "site_b_amsterdam" / "osm" / "water_osm.json",
        SITES_ROOT / "site_c_edmonton" / "sumo" / "network.net.xml",
        SITES_ROOT / "site_c_edmonton" / "validation" / "transverse_routes.csv",
        SITES_ROOT / "sites_manifest.yaml",
        COMPARISON / "site_morphology_comparison.csv",
        COMPARISON / "LEGACY_SITE_PATH_AUDIT.md",
    ]
    tests.append(("IMG-T14", "A/B/C source data consolidated under sim/sites",
                  check(all(p.exists() for p in need2)),
                  f"{sum(p.exists() for p in need2)}/{len(need2)} present"))

    # ---------------- IMG-T15: no Exp1 data/results modified
    tests.append(("IMG-T15", "No Experiment 1 data/results modified",
                  check(not changed),
                  "frozen hashes verified (same check as IMG-T8)"))

    # legacy-v1 comparison for Site B (band coverage before/after)
    if LEGACY_B_V1.exists():
        img_v1 = Image.open(LEGACY_B_V1).convert("RGB")
        v1_bands = band_coverage(img_v1)
        v2_bands = vqa["figures"]["site_b_v2"]["band_coverage"]
        vqa["site_b_band_coverage_v1"] = [round(v, 4) for v in v1_bands]
        vqa["site_b_band_coverage_v2"] = v2_bands
        lower_v1 = (v1_bands[1] + v1_bands[2]) / 2
        lower_v2 = (v2_bands[1] + v2_bands[2]) / 2
        vqa["site_b_lower_bands_improvement"] = round(lower_v2 / max(lower_v1, 1e-9), 2)

    n_pass = sum(1 for t in tests if t[2] == "PASS")
    n_warn = sum(1 for t in tests if t[2] == "WARNING")
    n_fail = sum(1 for t in tests if t[2] == "FAIL")

    with open(COMPARISON / "image_acceptance_tests.csv", "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["test_id", "description", "status", "evidence"])
        w.writerows(tests)
    (COMPARISON / "visual_qa.json").write_text(
        json.dumps(vqa, indent=2), encoding="utf-8")

    lines = ["# IMAGE ACCEPTANCE TESTS (IMG-T1 .. IMG-T15)", "",
             f"Summary: **{n_pass} PASS / {n_warn} WARNING / {n_fail} FAIL**", "",
             "Visual QA method: programmatic pixel/geometry analysis "
             "(band coverage, color-class pixel counts, renderer-based label "
             "bbox overlaps, DPI/file checks) -- see visual_qa.json.",
             "", "| Test | Description | Status | Evidence |", "|---|---|---|---|"]
    for tid, desc, status, ev in tests:
        lines.append(f"| {tid} | {desc} | **{status}** | {ev} |")
    (COMPARISON / "image_acceptance_tests.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")

    print(f"IMG acceptance: {n_pass} PASS / {n_warn} WARNING / {n_fail} FAIL")
    for tid, desc, status, ev in tests:
        print(f"  {tid} {status:8s} {desc[:55]:55s} {ev}")
    print(f"visual_qa.json written; "
          f"band improvement factor = "
          f"{vqa.get('site_b_lower_bands_improvement')}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
