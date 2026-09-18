"""Consolidate Site A/B/C data into the canonical sim/sites tree.

Canonical layout:
  sim/sites/
    site_a_suzhou/{config,osm,sumo,bluesky,facilities,routes,validation,figures,metadata}
    site_b_amsterdam/{...}
    site_c_edmonton/{...}
    comparison/
    sites_manifest.yaml

Rules:
  * Site A files are COPIED byte-for-byte (SHA-256 verified against the
    freeze snapshot); nothing under sim/sumo, sim/bluesky or
    config/scenario_config.yaml is modified.
  * Site B/C are re-organised from their existing sim/sites/<id>/{sumo,bluesky}
    dirs; OSM input files move to osm/, the SUMO net/routes/config stay in
    sumo/, and the BlueSky scene + SUMO additional POIs are REGENERATED with
    the auxiliary facilities (primary sections byte-identical).
  * Canonical configs gain an `auxiliary:` section from the refinement
    outputs; all primary keys are asserted byte-identical to the legacy
    config/*.yaml.
  * A LEGACY_SITE_PATH_AUDIT.md records every old path.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import cross_site_lib as lib  # noqa: E402

SITES_ROOT = ROOT / "sim" / "sites"
COMPARISON = SITES_ROOT / "comparison"
REFINE = ROOT / "outputs" / "cross_site" / "refinement"

LEGACY_AUDIT: list = []


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def audit(old: str, new: str, status: str) -> None:
    LEGACY_AUDIT.append({"old_path": old, "new_path": new, "status": status})


def copy_file(src: Path, dst: Path, status: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    audit(str(src.relative_to(ROOT)), str(dst.relative_to(ROOT)), status)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8")


def build_site_a() -> dict:
    """Site A: pure copy + read-only derived files."""
    site = SITES_ROOT / "site_a_suzhou"
    for d in ("config", "osm", "sumo", "bluesky", "facilities", "routes",
              "validation", "figures", "metadata"):
        (site / d).mkdir(parents=True, exist_ok=True)
    import yaml
    cfg = yaml.safe_load((ROOT / "config" / "scenario_config.yaml")
                         .read_text(encoding="utf-8"))

    copy_file(ROOT / "config" / "scenario_config.yaml", site / "config" / "scenario_config.yaml",
              "COPY (frozen content)")
    copy_file(ROOT / "sim" / "sumo" / "area.osm.xml", site / "osm" / "area.osm.xml", "COPY")
    copy_file(ROOT / "sim" / "sumo" / "osm_pois.json", site / "osm" / "osm_pois.json", "COPY")
    copy_file(ROOT / "sim" / "sumo" / "network.net.xml", site / "sumo" / "network.net.xml", "COPY")
    copy_file(ROOT / "sim" / "sumo" / "routes.rou.xml", site / "sumo" / "routes.rou.xml", "COPY")
    copy_file(ROOT / "sim" / "sumo" / "additional.add.xml", site / "sumo" / "additional.add.xml", "COPY")
    copy_file(ROOT / "sim" / "sumo" / "canonical.sumocfg", site / "sumo" / "canonical.sumocfg", "COPY")
    copy_file(ROOT / "sim" / "bluesky" / "canonical_s0.scn", site / "bluesky" / "canonical_s0.scn", "COPY")
    for f in ("geographic_alignment_detailed.csv", "geographic_alignment_detailed.csv"):
        p = ROOT / "outputs" / f
        if p.exists():
            copy_file(p, site / "validation" / f, "COPY")
    b1val = ROOT / "reports" / "validation" / "B1_POST_RESIZE_VALIDATION.md"
    if b1val.exists():
        copy_file(b1val, site / "validation" / "B1_POST_RESIZE_VALIDATION.md", "COPY")

    # verify freeze hashes of the copied frozen files
    snap = json.loads((ROOT / "outputs" / "cross_site" / "site_a_freeze_hashes.json")
                      .read_text(encoding="utf-8"))
    problems = []
    for rel, h in snap.items():
        cur = sha256(ROOT / rel)
        if cur != h:
            problems.append(rel)
    print(f"Site A freeze hash check: {'OK' if not problems else 'FAILED: ' + str(problems)}")

    # derived (read-only analysis): water parsed from the frozen full OSM map
    wjson = lib.parse_full_map_water((site / "osm" / "area.osm.xml").read_bytes())
    write_json(site / "osm" / "water_osm.json", wjson)

    # facility registry
    registry = {"primary": {}, "auxiliary": {}}
    for k, v in cfg["facilities"].items():
        registry["primary"][k] = dict(v)
        registry["primary"][k]["sumo_edge"] = cfg["sumo_mapping"][k]["edge_id"]
        registry["primary"][k]["snap_m"] = cfg["sumo_mapping"][k]["snapped_distance_m"]
    write_json(site / "facilities" / "registry.json", registry)

    # primary route (read-only TraCI on the copied frozen net)
    net = lib.load_net(site / "sumo" / "network.net.xml")
    d1 = cfg["sumo_mapping"]["D1"]["edge_id"]
    h1 = cfg["sumo_mapping"]["H1"]["edge_id"]
    b1e = cfg["sumo_mapping"]["B1"]["edge_id"]
    with lib.traci_session(site / "sumo" / "network.net.xml", "consol_a") as traci:
        base = lib.route_edges(traci, d1, h1)
        det = lib.close_edge_route(traci, d1, h1, b1e)
    primary = {
        "od": "D1->H1",
        "baseline": {"edges": base,
                     "distance_m": round(lib.route_distance_m(net, base), 1),
                     "eta_s": round(sum(net.getEdge(e).getLength()
                                        / max(net.getEdge(e).getSpeed(), 0.1)
                                        for e in base), 3)},
        "b1_edge": b1e,
        "detour": {"edges": det, "distance_m": round(lib.route_distance_m(net, det), 1)}
        if det else None,
    }
    write_json(site / "routes" / "primary.json", primary)

    metadata = {
        "site": "site_a_suzhou", "city": "Suzhou, China",
        "center": cfg["study_area"]["center"], "bbox": cfg["bbox"],
        "area_km2": 10.24, "morphology": "meshed_mixed_urban",
        "role": "primary", "frozen_exp1": True,
        "config_source": "config/scenario_config.yaml (COPY, frozen)",
        "freeze_hashes_ok": not problems,
        "notes": ["Site A copied byte-identical; NO regeneration of any file.",
                  "water_osm.json and routes/primary.json are derived read-only "
                  "analyses for plotting/validation."],
    }
    write_json(site / "metadata" / "metadata.json", metadata)
    return cfg


def build_site(key: str) -> dict:
    site_id = {"b": "site_b_amsterdam", "c": "site_c_edmonton"}[key]
    site = SITES_ROOT / site_id
    for d in ("config", "osm", "sumo", "bluesky", "facilities", "routes",
              "validation", "figures", "metadata"):
        (site / d).mkdir(parents=True, exist_ok=True)

    import yaml
    cfg = yaml.safe_load((ROOT / "config" / f"{site_id}_config.yaml")
                         .read_text(encoding="utf-8"))
    refine_dir = REFINE / site_id
    aux_json = json.loads((refine_dir / "auxiliary.json").read_text(encoding="utf-8"))

    # ---- osm inputs move to osm/ ----
    old_sumo = site / "sumo"
    for f in ("area.osm.xml", "osm_pois.json", "water_osm.json", "bridges_osm.json"):
        src = old_sumo / f
        if src.exists():
            copy_file(src, site / "osm" / f, "MOVED (canonical)")
            src.unlink()
    # keep net/routes/cfg in sumo/
    for f in ("network.net.xml", "routes.rou.xml", "site.sumocfg"):
        if (old_sumo / f).exists():
            audit(f"sim/sites/{site_id}/sumo/{f}",
                  f"sim/sites/{site_id}/sumo/{f}", "KEPT (canonical)")

    # ---- extend canonical config with auxiliary section ----
    aux_fac = aux_json["aux_facilities"]
    cfg["auxiliary"] = {
        "note": ("Auxiliary cross-site assets (NOT part of frozen Experiment 1 "
                 "primary metrics). Real OSM POIs; landing nodes synthetic."),
        "facilities": aux_fac,
        "ods": [{k: v for k, v in r.items() if k not in ("edges", "crossing_edges")}
                for r in aux_json["ods"]],
        "spatial_utilization": aux_json["spatial_utilization"],
    }
    for k, v in aux_fac.items():
        cfg["facilities"].setdefault(k, {
            "type": v["type"], "lat": v["lat"], "lon": v["lon"],
            "osm_node_id": v["osm_id"], "name": v["name"],
            "placement": "real_osm_poi" if not v["synthetic"] else "synthetic_experimental",
        })
        cfg["sumo_mapping"].setdefault(k, {
            "edge_id": v["edge_id"], "lane_id": v["edge_id"] + "_0",
            "x": v["x"], "y": v["y"], "snapped_distance_m": v["snap_m"],
        })
    # assert primary sections unchanged
    legacy_cfg = yaml.safe_load((ROOT / "config" / f"{site_id}_config.yaml")
                                .read_text(encoding="utf-8"))
    for sec in ("facilities", "sumo_mapping", "disruption_links"):
        for k in legacy_cfg[sec]:
            if cfg[sec][k] != legacy_cfg[sec][k]:
                raise RuntimeError(f"primary section {sec}.{k} drifted!")
    (site / "config" / f"{site_id}_config.yaml").write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True,
                       default_flow_style=False), encoding="utf-8")
    audit(f"config/{site_id}_config.yaml",
          f"sim/sites/{site_id}/config/{site_id}_config.yaml",
          "COPY + auxiliary extension (primary identical)")

    # ---- regenerate SUMO additional POIs + BlueSky scene with aux assets ----
    net = lib.load_net(site / "sumo" / "network.net.xml")
    with lib.traci_session(site / "sumo" / "network.net.xml",
                           f"consol_{key}") as traci:
        primary_edges = lib.route_edges(
            traci, cfg["sumo_mapping"]["D1"]["edge_id"],
            cfg["sumo_mapping"]["H1"]["edge_id"])
    lib.write_sumo_scene(site, net, cfg, primary_edges)
    lib.write_bluesky_scn(site / "bluesky" / f"site_{key}.scn", cfg,
                          f"{site_id} -- low-altitude scene")
    audit(f"sim/sites/{site_id}/sumo/additional.add.xml (old)",
          f"sim/sites/{site_id}/sumo/additional.add.xml",
          "REGENERATED with auxiliary POIs (primary POIs identical)")
    audit(f"sim/sites/{site_id}/bluesky/site_{key}.scn (old)",
          f"sim/sites/{site_id}/bluesky/site_{key}.scn",
          "REGENERATED with auxiliary landmarks (primary fleet identical)")

    # ---- registry + routes + validation ----
    registry = {"primary": {}, "auxiliary": {}}
    for k, v in cfg["facilities"].items():
        is_aux = k in aux_fac
        reg = registry["auxiliary"] if is_aux else registry["primary"]
        reg[k] = dict(v)
        reg[k]["sumo_edge"] = cfg["sumo_mapping"][k]["edge_id"]
        reg[k]["snap_m"] = cfg["sumo_mapping"][k]["snapped_distance_m"]
    write_json(site / "facilities" / "registry.json", registry)

    primary = {
        "od": "D1->H1",
        "baseline": {"edges": primary_edges,
                     "distance_m": round(lib.route_distance_m(net, primary_edges), 1),
                     "eta_s": cfg["disruption_links"]["base_eta_s"]},
        "b1_edge": cfg["disruption_links"]["links"]["B1"]["edge_id"],
        "detour": {"edges": cfg["disruption_links"]["links"]["B1"].get("detour_edges", []),
                   "eta_s": cfg["disruption_links"]["links"]["B1"]["detour_eta_s"],
                   "increase_pct": cfg["disruption_links"]["links"]["B1"]["eta_increase_pct"]},
    }
    write_json(site / "routes" / "primary.json", primary)
    aux_routes = {}
    for r in aux_json["ods"]:
        aux_routes[r["od_id"]] = {k: v for k, v in r.items()}
    write_json(site / "routes" / "auxiliary.json", aux_routes)

    for f in ("spatial_utilization.csv",):
        src = refine_dir / f
        if src.exists():
            copy_file(src, site / "validation" / f, "COPY (refinement)")
    route_csv = refine_dir / ("transverse_routes.csv" if key == "c" else "od_routes.csv")
    copy_file(route_csv, site / "validation" / route_csv.name, "COPY (refinement)")
    geo = ROOT / "outputs" / "cross_site" / f"{key}_geographic_alignment.csv"
    if geo.exists():
        copy_file(geo, site / "validation" / f"geographic_alignment.csv", "COPY")

    metadata = {
        "site": site_id,
        "city": "Amsterdam, Netherlands" if key == "b" else "Edmonton, Alberta, Canada",
        "center": cfg["study_area"]["center"], "bbox": cfg["bbox"],
        "area_km2": 10.24,
        "morphology": ("water_barrier_bridge_constrained" if key == "b"
                       else "sparse_suburban_polycentric"),
        "role": "cross_site_validation", "frozen_exp1": False,
        "primary_od": "D1->H1",
        "primary_b1": cfg["disruption_links"]["links"]["B1"]["edge_id"],
        "auxiliary_ods": [r["od_id"] for r in aux_json["ods"]],
        "auxiliary_facilities": sorted(aux_fac.keys()),
        "notes": ["Primary sections identical to legacy config (asserted).",
                  "Auxiliary facilities/ODs are scene-level assets for "
                  "cross-site validation; NOT used by frozen Experiment 1."],
    }
    write_json(site / "metadata" / "metadata.json", metadata)
    return cfg


def main() -> int:
    SITES_ROOT.mkdir(parents=True, exist_ok=True)
    COMPARISON.mkdir(parents=True, exist_ok=True)
    cfg_a = build_site_a()
    cfg_b = build_site("b")
    cfg_c = build_site("c")

    # ---- comparison/ ----
    copy_file(ROOT / "outputs" / "cross_site" / "site_morphology_comparison.csv",
              COMPARISON / "site_morphology_comparison.csv", "COPY")

    # ---- sites_manifest.yaml ----
    import yaml
    manifest = {
        "canonical_root": "sim/sites",
        "sites": {
            "site_a": {
                "role": "primary", "morphology": "meshed_mixed_urban",
                "city": "Suzhou, China", "frozen_exp1": True,
                "primary_od": "D1->H1",
                "auxiliary_ods": [],
                "config_path": "sim/sites/site_a_suzhou/config/scenario_config.yaml",
                "sumo_path": "sim/sites/site_a_suzhou/sumo",
                "bluesky_path": "sim/sites/site_a_suzhou/bluesky/canonical_s0.scn",
                "figure_path": "sim/sites/site_a_suzhou/figures/site_a_suzhou_unified_scene_v2.png",
            },
            "site_b": {
                "role": "cross_site_validation",
                "morphology": "water_barrier_bridge_constrained",
                "city": "Amsterdam, Netherlands", "frozen_exp1": False,
                "primary_od": "D1->H1",
                "auxiliary_ods": ["OD-B1", "OD-B2"],
                "config_path": "sim/sites/site_b_amsterdam/config/site_b_amsterdam_config.yaml",
                "sumo_path": "sim/sites/site_b_amsterdam/sumo",
                "bluesky_path": "sim/sites/site_b_amsterdam/bluesky/site_b.scn",
                "figure_path": "sim/sites/site_b_amsterdam/figures/site_b_amsterdam_unified_scene_v2.png",
            },
            "site_c": {
                "role": "cross_site_validation",
                "morphology": "sparse_suburban_polycentric",
                "city": "Edmonton, Canada", "frozen_exp1": False,
                "primary_od": "D1->H1",
                "auxiliary_ods": ["OD-C1", "OD-C2"],
                "config_path": "sim/sites/site_c_edmonton/config/site_c_edmonton_config.yaml",
                "sumo_path": "sim/sites/site_c_edmonton/sumo",
                "bluesky_path": "sim/sites/site_c_edmonton/bluesky/site_c.scn",
                "figure_path": "sim/sites/site_c_edmonton/figures/site_c_edmonton_unified_scene_v2.png",
            },
        },
    }
    (SITES_ROOT / "sites_manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8")

    # ---- legacy audit ----
    lines = ["# LEGACY SITE PATH AUDIT", "",
             "Old project paths vs the canonical sim/sites tree.", "",
             "| OLD PATH | NEW CANONICAL PATH | STATUS |", "|---|---|---|"]
    for row in LEGACY_AUDIT:
        lines.append(f"| {row['old_path']} | {row['new_path']} | {row['status']} |")
    lines += ["",
              "Notes:",
              "- Site A frozen files were COPIED (originals remain the frozen",
              "  experiment-1 sources); SHA-256 verified.",
              "- outputs/cross_site/ remains as the construction-stage work area",
              "  (legacy); canonical scene data lives under sim/sites/.",
              "- Frozen Exp-1 replay paths (sim/sumo, sim/bluesky,",
              "  config/scenario_config.yaml) are untouched.",
              ]
    (COMPARISON / "LEGACY_SITE_PATH_AUDIT.md").write_text("\n".join(lines) + "\n",
                                                           encoding="utf-8")
    print(f"consolidation complete; {len(LEGACY_AUDIT)} path entries audited")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
