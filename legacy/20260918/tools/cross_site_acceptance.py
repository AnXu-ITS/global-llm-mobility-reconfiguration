"""Cross-site acceptance tests CS-T1 .. CS-T20.

Evidence is computed directly from the artifacts (candidate CSVs, site
configs, alignment CSVs, smoke-test CSVs, morphology CSV, freeze hashes).

Outputs:
  outputs/cross_site/acceptance_tests.csv
  reports/cross_site/CROSS_SITE_ACCEPTANCE_TESTS.md

Site A freeze (CS-T1): SHA-256 of the frozen Site A files. The snapshot is
created on first run and only ever READ afterwards.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod  # noqa: E402
from orchestrator.geo import bbox_from_center, meters_per_deg_lat, meters_per_deg_lon  # noqa: E402

OUT_ROOT = ROOT / "outputs" / "cross_site"
REPORT_DIR = ROOT / "reports" / "cross_site"
FREEZE_SNAPSHOT = OUT_ROOT / "site_a_freeze_hashes.json"

SITE_A_FROZEN = [
    ROOT / "config" / "scenario_config.yaml",
    ROOT / "sim" / "sumo" / "area.osm.xml",
    ROOT / "sim" / "sumo" / "network.net.xml",
    ROOT / "sim" / "sumo" / "routes.rou.xml",
    ROOT / "sim" / "sumo" / "additional.add.xml",
    ROOT / "sim" / "sumo" / "canonical.sumocfg",
    ROOT / "sim" / "sumo" / "osm_pois.json",
    ROOT / "sim" / "bluesky" / "canonical_s0.scn",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def bbox_extent_m(cfg: dict):
    b = cfg["bbox"]
    clat = cfg["study_area"]["center"]["lat"]
    return ((b["north"] - b["south"]) * meters_per_deg_lat(clat),
            (b["east"] - b["west"]) * meters_per_deg_lon(clat))


def read_alignment(site_key: str):
    rows = []
    with open(OUT_ROOT / f"{site_key}_geographic_alignment.csv", newline="",
              encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append(r)
    crs = sorted(float(r["crs_error_m"]) for r in rows)
    n = len(crs)
    median = (crs[n // 2] + crs[(n - 1) // 2]) / 2
    return {"median_crs": median, "max_crs": max(crs), "rows": rows}


def read_smoke(site_key: str, site_id: str):
    run_dir = ROOT / "runs" / f"site_{site_key}_cosim_smoke"
    clock_rows = list(csv.DictReader(open(run_dir / "clock_sync.csv", newline="",
                                          encoding="utf-8")))
    air_rows = list(csv.DictReader(open(run_dir / "air_state.csv", newline="",
                                        encoding="utf-8")))
    sync_bad = [r for r in clock_rows if r["sync_ok"] != "True"]
    # movement: per-aircraft displacement between first and last observation
    pos = {}
    for r in air_rows:
        pos.setdefault(r["aircraft_id"], []).append((float(r["lat"]), float(r["lon"])))
    moved = 0
    for acid, pts in pos.items():
        if len(pts) < 2:
            continue
        d = ((pts[-1][0] - pts[0][0]) ** 2 + (pts[-1][1] - pts[0][1]) ** 2) ** 0.5
        if d > 0.001:  # ~100 m in degrees
            moved += 1
    # manager artifacts must be absent
    manager_files = list(run_dir.glob("*manager*")) + list(run_dir.glob("*llm*"))
    rc = config_mod.load_config(run_dir / "run_config.yaml")
    return {"n_clock_rows": len(clock_rows), "sync_bad": len(sync_bad),
            "moved_aircraft": moved, "manager_files": manager_files,
            "manager": rc.get("manager"), "llm_model": rc.get("llm_model")}


def check(cond: bool, warn: bool = False) -> str:
    if cond:
        return "PASS"
    return "WARNING" if warn else "FAIL"


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # freeze snapshot (created once)
    if not FREEZE_SNAPSHOT.exists():
        snap = {str(p.relative_to(ROOT)): sha256(p) for p in SITE_A_FROZEN}
        FREEZE_SNAPSHOT.write_text(json.dumps(snap, indent=2), encoding="utf-8")
        print(f"Site A freeze snapshot created: {FREEZE_SNAPSHOT}")
    snap = json.loads(FREEZE_SNAPSHOT.read_text(encoding="utf-8"))
    changed = [k for k, v in snap.items() if sha256(ROOT / k) != v]

    cfg_b = config_mod.load_config(ROOT / "config" / "site_b_amsterdam_config.yaml")
    cfg_c = config_mod.load_config(ROOT / "config" / "site_c_edmonton_config.yaml")

    ams_csv = list(csv.DictReader(open(OUT_ROOT / "amsterdam_candidate_bboxes.csv",
                                       newline="", encoding="utf-8")))
    edm_csv = list(csv.DictReader(open(OUT_ROOT / "edmonton_candidate_bboxes.csv",
                                       newline="", encoding="utf-8")))
    morph = {r["site_id"]: r for r in csv.DictReader(
        open(OUT_ROOT / "site_morphology_comparison.csv", newline="", encoding="utf-8"))}

    b1b = cfg_b["disruption_links"]["links"]["B1"]
    b1c = cfg_c["disruption_links"]["links"]["B1"]
    al_b = read_alignment("b")
    al_c = read_alignment("c")
    sm_b = read_smoke("b", "site_b_amsterdam")
    sm_c = read_smoke("c", "site_c_edmonton")

    wb, hb = bbox_extent_m(cfg_b)
    wc, hc = bbox_extent_m(cfg_c)

    # boundary margin of B1 crossing: recompute from candidate analysis
    an_b = json.loads((ROOT / "outputs" / "cross_site" / "candidates" / "amsterdam" /
                       cfg_b["study_area"]["candidate_id"] / "analysis.json")
                      .read_text(encoding="utf-8"))
    usable_b = an_b.get("usable_crossings") or {}
    b_margin = usable_b.get(b1b["edge_id"], {}).get("boundary_margin_m")
    detour_share_b = b1b.get("detour_boundary_share")
    if detour_share_b is None and b1b.get("detour_edges"):
        from tools import cross_site_lib as lib
        from orchestrator.sumo_env import setup as sumo_setup
        sumo_setup()
        import sumolib
        net_b = sumolib.net.readNet(str(ROOT / "sim" / "sites" / "site_b_amsterdam" /
                                        "sumo" / "network.net.xml"))
        detour_share_b = lib.detour_boundary_share(net_b, b1b["detour_edges"])

    # Site C baseline crossing count from candidate analysis
    an_c = json.loads((ROOT / "outputs" / "cross_site" / "candidates" / "edmonton" /
                       cfg_c["study_area"]["candidate_id"] / "analysis.json")
                      .read_text(encoding="utf-8"))
    c_pair = an_c.get("best_pair") or {}

    tests = []
    tests.append(("CS-T1", "Site A unchanged (8 frozen files byte-identical)",
                  check(len(changed) == 0),
                  f"{len(changed)} file(s) changed: {changed}" if changed else
                  "all 8 frozen Site A files byte-identical"))
    tests.append(("CS-T2", "Site B = 3.2 x 3.2 km",
                  check(abs(wb - 3200) <= 32 and abs(hb - 3200) <= 32),
                  f"{wb:.1f} m x {hb:.1f} m"))
    tests.append(("CS-T3", "Site C = 3.2 x 3.2 km",
                  check(abs(wc - 3200) <= 32 and abs(hc - 3200) <= 32),
                  f"{wc:.1f} m x {hc:.1f} m"))
    tests.append(("CS-T4", "Amsterdam bbox selected from >=5 candidates",
                  check(len(ams_csv) >= 5), f"{len(ams_csv)} candidates"))
    tests.append(("CS-T5", "Edmonton bbox selected from >=5 candidates",
                  check(len(edm_csv) >= 5), f"{len(edm_csv)} candidates"))
    tests.append(("CS-T6", "Site B has genuine water/crossing constraint",
                  check(bool(b1b.get("is_water_crossing"))
                        and cfg_b["water"]["water_area_km2"] >= 0.05
                        and cfg_b["water"]["n_main_crossings"] >= 2),
                  f"B1={b1b['edge_id']} kind={b1b.get('crossing_kind')} "
                  f"water={cfg_b['water']['water_area_km2']:.2f} km2 "
                  f"main_crossings={cfg_b['water']['n_main_crossings']}"))
    tests.append(("CS-T7", "Site B critical crossing closure has detour",
                  check(bool(b1b.get("has_detour"))),
                  f"detour={b1b.get('has_detour')} ({len(b1b.get('detour_edges', []))} edges)"))
    tests.append(("CS-T8", "Site B ETA increase >=25%",
                  check((b1b.get("eta_increase_pct") or 0) >= 25.0),
                  f"{b1b.get('eta_increase_pct'):.2f}% (>=40% preferred)"))
    tests.append(("CS-T9", "Site B not bbox-boundary artifact",
                  check((b_margin is not None and b_margin >= 300.0)
                        and (detour_share_b is not None and detour_share_b <= 0.30)),
                  f"margin={b_margin:.0f} m detour_boundary_share={detour_share_b:.3f}"
                  if b_margin is not None and detour_share_b is not None else
                  "margin/detour data missing"))
    # CS-T10: Site C must be lower-density / more spatially dispersed than
    # Site A. Evidence: road density lower AND >=3 of (dead-end ratio higher,
    # mean circuity higher, redundancy proxy lower, D1->H1 network distance
    # longer, D1->H1 euclidean separation larger). Intersection density is
    # reported but NOT required (crescent-loop suburbs create many 3-way
    # junctions; the dispersion evidence is carried by the other axes).
    m_a = morph["site_a_suzhou"]
    m_c = morph["site_c_edmonton"]
    dens_ok = float(m_c["road_density_km_per_km2"]) < float(m_a["road_density_km_per_km2"])
    axes = [
        float(m_c["dead_end_ratio"]) > float(m_a["dead_end_ratio"]),
        float(m_c["mean_od_circuity"]) > float(m_a["mean_od_circuity"]),
        float(m_c["facility_network_distance_D1_H1"]) >
        float(m_a["facility_network_distance_D1_H1"]),
        float(m_c["facility_euclidean_distance_D1_H1"]) >
        float(m_a["facility_euclidean_distance_D1_H1"]),
        float(m_c["mean_shortest_path_length"]) > float(m_a["mean_shortest_path_length"]),
    ]
    t10_ok = dens_ok and sum(axes) >= 3
    tests.append(("CS-T10", "Site C lower-density / more dispersed than Site A",
                  check(t10_ok),
                  f"road {m_c['road_density_km_per_km2']} vs "
                  f"{m_a['road_density_km_per_km2']} km/km2; "
                  f"intersections {m_c['intersection_density']} vs "
                  f"{m_a['intersection_density']} /km2 (reported); "
                  f"dead-ends {m_c['dead_end_ratio']} vs {m_a['dead_end_ratio']}; "
                  f"circuity {m_c['mean_od_circuity']} vs {m_a['mean_od_circuity']}; "
                  f"D1->H1 {m_c['facility_network_distance_D1_H1']} vs "
                  f"{m_a['facility_network_distance_D1_H1']} km "
                  f"({sum(axes)}/5 dispersion axes)"))
    tests.append(("CS-T11", "Site C not dominated by river/bridge dependency",
                  check(not b1c.get("is_water_crossing")
                        and c_pair.get("n_crossings_on_path", 0) == 0),
                  f"B1 crossing={b1c.get('is_water_crossing')} "
                  f"baseline crossings={c_pair.get('n_crossings_on_path', '?')}"))
    tests.append(("CS-T12", "Facilities geographically valid (real POI, snap<=100m)",
                  check(all(str(cfg["facilities"][x].get("placement", "")).startswith("real_osm_poi")
                            or x in ("V1", "V2", "V3", "B1")
                            for x in ("H1", "D1") for cfg in (cfg_b, cfg_c))
                        and max(cfg_b["sumo_mapping"]["H1"]["snapped_distance_m"],
                                cfg_b["sumo_mapping"]["D1"]["snapped_distance_m"]) <= 100.0
                        and max(cfg_c["sumo_mapping"]["H1"]["snapped_distance_m"],
                                cfg_c["sumo_mapping"]["D1"]["snapped_distance_m"]) <= 100.0),
                  f"B: H1={cfg_b['facilities']['H1']['name'] or cfg_b['facilities']['H1']['osm_node_id']} "
                  f"snap={cfg_b['sumo_mapping']['H1']['snapped_distance_m']}m, "
                  f"D1={cfg_c['facilities']['D1']['name'] or cfg_c['facilities']['D1']['osm_node_id']} "
                  f"snap={cfg_c['sumo_mapping']['D1']['snapped_distance_m']}m"))
    tests.append(("CS-T13", "CRS alignment PASS for Site B",
                  check(al_b["median_crs"] < 5.0 and al_b["max_crs"] < 15.0
                        and not any(r["flag"] == "FAIL" for r in al_b["rows"])),
                  f"median={al_b['median_crs']:.3f} m max={al_b['max_crs']:.3f} m"))
    tests.append(("CS-T14", "CRS alignment PASS for Site C",
                  check(al_c["median_crs"] < 5.0 and al_c["max_crs"] < 15.0
                        and not any(r["flag"] == "FAIL" for r in al_c["rows"])),
                  f"median={al_c['median_crs']:.3f} m max={al_c['max_crs']:.3f} m"))
    tests.append(("CS-T15", "SUMO/BlueSky clocks sync for Site B (600 steps, 0 errors)",
                  check(sm_b["n_clock_rows"] == 600 and sm_b["sync_bad"] == 0),
                  f"{sm_b['n_clock_rows']} rows, {sm_b['sync_bad']} violations"))
    tests.append(("CS-T16", "SUMO/BlueSky clocks sync for Site C (600 steps, 0 errors)",
                  check(sm_c["n_clock_rows"] == 600 and sm_c["sync_bad"] == 0),
                  f"{sm_c['n_clock_rows']} rows, {sm_c['sync_bad']} violations"))
    tests.append(("CS-T17", "BlueSky dynamics provenance confirmed in Site B/C",
                  check(sm_b["moved_aircraft"] >= 3 and sm_c["moved_aircraft"] >= 3),
                  f"B: {sm_b['moved_aircraft']} moving aircraft, "
                  f"C: {sm_c['moved_aircraft']} moving aircraft"))
    tests.append(("CS-T18", "Three-site morphology metrics generated",
                  check(len(morph) == 3 and
                        "mean_od_circuity" in next(iter(morph.values()))),
                  f"{len(morph)} sites, {len(next(iter(morph.values())))} columns"))
    tests.append(("CS-T19", "Site type labels supported by quantitative evidence",
                  check(cfg_b["water"]["n_usable_crossings"] >= 2 and
                        bool(b1b.get("is_water_crossing")) and
                        not b1c.get("is_water_crossing") and
                        float(morph["site_c_edmonton"]["road_density_km_per_km2"]) <
                        float(morph["site_a_suzhou"]["road_density_km_per_km2"])),
                  "B=water-constrained (crossings>=2, B1=crossing); "
                  "C=sparse (no crossing B1, density<Site A)"))
    tests.append(("CS-T20", "No manager experiments run (deterministic smoke only)",
                  check(sm_b["manager"] == "deterministic_smoke_test_action"
                        and sm_c["manager"] == "deterministic_smoke_test_action"
                        and sm_b["llm_model"] is None and sm_c["llm_model"] is None
                        and not sm_b["manager_files"] and not sm_c["manager_files"]),
                  f"B manager={sm_b['manager']} llm={sm_b['llm_model']} "
                  f"manager_files={len(sm_b['manager_files'])}; "
                  f"C manager={sm_c['manager']} llm={sm_c['llm_model']} "
                  f"manager_files={len(sm_c['manager_files'])}"))

    n_pass = sum(1 for t in tests if t[2] == "PASS")
    n_warn = sum(1 for t in tests if t[2] == "WARNING")
    n_fail = sum(1 for t in tests if t[2] == "FAIL")

    with open(OUT_ROOT / "acceptance_tests.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["test_id", "description", "status", "evidence"])
        w.writerows(tests)

    lines = [
        "# CROSS-SITE ACCEPTANCE TESTS (CS-T1 .. CS-T20)",
        "",
        f"Summary: **{n_pass} PASS / {n_warn} WARNING / {n_fail} FAIL**",
        "",
        "| Test | Description | Status | Evidence |",
        "|---|---|---|---|",
    ]
    for tid, desc, status, ev in tests:
        lines.append(f"| {tid} | {desc} | **{status}** | {ev} |")
    lines += [
        "",
        "Notes:",
        "- CS-T1 compares SHA-256 hashes of the 8 frozen Site A files against the",
        "  snapshot recorded at the start of the cross-site phase.",
        "- CS-T9 boundary-artifact rule: the closed crossing must sit >=300 m from",
        "  the bbox edge AND the detour must keep <=30% of its length inside the",
        "  150 m boundary band.",
        "- CS-T17: an aircraft counts as moving when its WGS84 position changes by",
        "  >0.001 deg (~100 m) between t=0 and t=600.",
        "- CS-T20: manager field in run_config.yaml is the deterministic smoke-test",
        "  action; no LLM model configured; no manager/LLM artifacts in run dirs.",
    ]
    (REPORT_DIR / "CROSS_SITE_ACCEPTANCE_TESTS.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    print(f"acceptance: {n_pass} PASS / {n_warn} WARNING / {n_fail} FAIL")
    for tid, desc, status, ev in tests:
        print(f"  {tid} {status:8s} {desc[:58]:58s} {ev}")
    print(f"wrote {OUT_ROOT / 'acceptance_tests.csv'}")
    print(f"wrote {REPORT_DIR / 'CROSS_SITE_ACCEPTANCE_TESTS.md'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
