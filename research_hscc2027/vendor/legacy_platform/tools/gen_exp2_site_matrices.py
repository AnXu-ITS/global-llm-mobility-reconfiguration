"""Experiment 2 cross-site matrix generator + geometry-invariant audit.

Implements the user-approved site adaptations:

  SITE-B FAILURE-TIME ADAPTATION (E2-EXT-XSITE-1):
      The canonical t=360 failure assumes the critical flight outlasts the
      60-s post-dispatch lead time (Site A: 114.5 s). Site B's flight is
      ~44 s, so the failure would land AFTER completion. Frozen site rule:
          t_failure = 300 + floor(air_eta_s / 2)          (>= 320 s)
      where air_eta_s is the frozen candidate-ETA formula (haversine V2->V1 /
      medical cruise 15 m/s, dispatch overhead 0). Site A's canonical 360 s
      is within 3 s of this rule's 357 s (documented, Site A dataset stays
      frozen at 360 s). The rule puts the failure at ~50% of the critical
      flight on every site.

  SITE-C (AND SITE-B) F2/F5/F6 GEOMETRY RE-DERIVATION:
      All corridor-dependent geometry is recomputed from each site's own
      V1/V2/V3 coordinates and the t_failure aircraft position (15 m/s along
      V2->V1), then AUDITED against frozen invariants:
        F2-C2/F5-C2 zone : circle r=100 m at pos(t_failure); backup M-UAV-01
                           at V1 outside; for F5 additionally the V3->V1
                           recovery segment must stay clear of the zone.
        F6-C2 envelope   : 200-m half-width strip crossing pos(t_failure);
                           V1/V3 and the V3->V1 segment stay clear (>=30 m).
        F5-C3 zone       : circle covering pos(t_failure) AND the V3->V1
                           segment (backup route illegal -> no air).
        F6-C3 envelope   : strip covering pos(t_failure), V1 and V3
                           (aircraft + route illegal -> no air).
        C1 geometries    : F2 zone at the site V3 (r=300, aircraft-state-only),
                           F5 corner zone (bbox NW corner, r=400), F6
                           low-latitude strip south of V3.

Writes config/experiment2_site_b_matrix.yaml / config/experiment2_site_c_matrix.yaml
(full 16-class matrices mirroring the canonical E2 matrix with the two
documented SCENARIO_DESIGN_LIMITATIONs) and
outputs/experiment2/cross_site_geometry_audit.json.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from failures.e2_failures import (haversine_m, point_in_zone,  # noqa: E402
                                  point_segment_distance_m, segment_intersects_zone,
                                  strip_ends)
from orchestrator import config as config_mod  # noqa: E402

LAT_M = 111194.9
CRUISE_MS = 15.0           # medical_uav frozen cruise speed
DISPATCH_OVERHEAD_S = 0.0  # frozen scenario manager config

SITES = {
    "b": {
        "site_id": "site_b_amsterdam",
        "config": ROOT / "sim" / "sites" / "site_b_amsterdam" / "config" /
                  "site_b_amsterdam_config.yaml",
        "matrix": ROOT / "config" / "experiment2_site_b_matrix.yaml",
        "prefix": "E2XB_",
    },
    "c": {
        "site_id": "site_c_edmonton",
        "config": ROOT / "sim" / "sites" / "site_c_edmonton" / "config" /
                  "site_c_edmonton_config.yaml",
        "matrix": ROOT / "config" / "experiment2_site_c_matrix.yaml",
        "prefix": "E2XC_",
    },
}


def _d2m(lat1, lon1, lat2, lon2) -> Tuple[float, float]:
    return ((lat2 - lat1) * LAT_M,
            (lon2 - lon1) * LAT_M * math.cos(math.radians((lat1 + lat2) / 2)))


def point_along(a: Tuple[float, float], b: Tuple[float, float],
                dist_m: float) -> Tuple[float, float]:
    total = haversine_m(a, b)
    f = max(0.0, min(1.0, dist_m / total if total > 0 else 1.0))
    return (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))


def bearing(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    dy, dx = _d2m(*a, *b)
    return math.degrees(math.atan2(dx, dy)) % 360.0


def shift(pt: Tuple[float, float], north_m: float, east_m: float):
    lat = pt[0] + north_m / LAT_M
    lon = pt[1] + east_m / (LAT_M * math.cos(math.radians(pt[0])))
    return (lat, lon)


def strip_geom(start: Tuple[float, float], heading_deg: float,
               half_width_m: float, length_m: float = 2000.0) -> Dict[str, Any]:
    return {"type": "strip", "lat0": start[0], "lon0": start[1],
            "heading_deg": heading_deg, "half_width_m": half_width_m,
            "length_m": length_m}


def seg_points(a: Tuple[float, float], b: Tuple[float, float],
               n: int = 12) -> List[Tuple[float, float]]:
    return [point_along(a, b, haversine_m(a, b) * i / n) for i in range(n + 1)]


def audit_line(label: str, ok: bool, detail: str, lines: List[str]) -> None:
    lines.append(f"[{'PASS' if ok else 'FAIL'}] {label}: {detail}")


def derive_site(site_key: str, lines: List[str]) -> Dict[str, Any]:
    site = SITES[site_key]
    cfg = config_mod.load_config(site["config"])
    fac = cfg["facilities"]
    v1 = (fac["V1"]["lat"], fac["V1"]["lon"])
    v2 = (fac["V2"]["lat"], fac["V2"]["lon"])
    v3 = (fac["V3"]["lat"], fac["V3"]["lon"])
    bbox = cfg["bbox"]

    air_eta = haversine_m(v2, v1) / CRUISE_MS + DISPATCH_OVERHEAD_S
    t_failure = 300 + max(20, int(round(air_eta / 2.0)))
    d_tf = CRUISE_MS * (t_failure - 300)
    pos_tf = point_along(v2, v1, d_tf)
    lines.append(f"site {site_key}: air_eta={air_eta:.1f}s -> "
                 f"t_failure={t_failure}, pos_tf=({pos_tf[0]:.6f},{pos_tf[1]:.6f})")

    audited: Dict[str, Any] = {}

    # ---- F2-C2 / F5-C2 zone at pos_tf ----
    # F5 has route rules, so the zone radius must leave the V3->V1 recovery
    # segment clear (site rule: r = min(100, min_seg - 45) rounded down to 5).
    min_seg = point_segment_distance_m(pos_tf, v3, v1)
    r_c2 = min(100.0, math.floor((min_seg - 45.0) / 5.0) * 5.0)
    zone_c2 = {"type": "circle", "lat": pos_tf[0], "lon": pos_tf[1],
               "radius_m": r_c2}
    d_backup = haversine_m(v1, pos_tf)
    audit_line(f"{site_key}/F2-C2 backup M-UAV-01@V1 outside zone",
               d_backup > r_c2 + 30.0, f"dist={d_backup:.1f} m", lines)
    d_v3 = haversine_m(v3, pos_tf)
    audit_line(f"{site_key}/F2-C2 V3 outside zone", d_v3 > r_c2 + 30.0,
               f"dist={d_v3:.1f} m", lines)
    audit_line(f"{site_key}/F5-C2 V3->V1 segment clear of zone (r={r_c2:.0f})",
               min_seg > r_c2 + 30.0, f"min dist={min_seg:.1f} m", lines)
    audited["zone_c2"] = zone_c2

    # ---- F6-C2 envelope: strip PARALLEL to the V3->V1 recovery leg through
    # pos_tf; half-width = min(200, min clearance - 40) so the recovery leg,
    # V1 and V3 all stay >= 40 m clear (site rule; site A's 200 m is kept
    # wherever the clearance allows it).
    def perp_from_line(pt, line_pt, heading):
        dy, dx = _d2m(*line_pt, *pt)
        n = (math.sin(math.radians(heading)), -math.cos(math.radians(heading)))
        return abs(dy * n[0] + dx * n[1])

    head_v3v1 = bearing(v3, v1)
    clear_v1 = perp_from_line(v1, pos_tf, head_v3v1)
    clear_v3 = perp_from_line(v3, pos_tf, head_v3v1)
    clear_seg = min(perp_from_line(p, pos_tf, head_v3v1)
                    for p in seg_points(v3, v1))
    hw_c2 = min(200.0, min(clear_v1, clear_v3, clear_seg) - 40.0)
    start_c2 = shift(pos_tf,
                     -150.0 * math.cos(math.radians(head_v3v1)),
                     -150.0 * math.sin(math.radians(head_v3v1)))
    env_c2 = strip_geom(start_c2, head_v3v1, hw_c2, 3000.0)
    in_tf = point_in_zone(*pos_tf, env_c2)
    d1c = point_segment_distance_m(v1, *strip_ends(env_c2))
    d3c = point_segment_distance_m(v3, *strip_ends(env_c2))
    seg_min_c2 = min(point_segment_distance_m(p, *strip_ends(env_c2))
                     for p in seg_points(v3, v1))
    ok_env = in_tf and d1c > hw_c2 + 30.0 and d3c > hw_c2 + 30.0 \
        and seg_min_c2 > hw_c2 + 30.0
    audit_line(f"{site_key}/F6-C2 envelope valid (crosses pos_tf, "
               f"V1/V3/V3->V1 clear)", ok_env,
               f"heading={head_v3v1:.1f} half={hw_c2:.0f} m "
               f"(V1 {d1c:.0f}, V3 {d3c:.0f}, seg {seg_min_c2:.0f} m)", lines)
    audited["env_c2"] = env_c2 if ok_env else None

    # ---- F5-C3 zone: covers pos_tf AND the V3->V1 segment ----
    center_c3 = point_along(pos_tf, v3, haversine_m(pos_tf, v3) / 2.0)
    r_c3 = max(haversine_m(center_c3, pos_tf) + 80.0,
               haversine_m(center_c3, v3) + 80.0,
               max(point_segment_distance_m(center_c3, p, p)
                   for p in seg_points(v3, v1)) + 80.0)
    zone_c3 = {"type": "circle", "lat": center_c3[0], "lon": center_c3[1],
               "radius_m": r_c3}
    in_tf3 = point_in_zone(*pos_tf, zone_c3)
    route_illegal = any(segment_intersects_zone(p, q, zone_c3)
                        for p, q in zip(seg_points(v3, v1)[:-1],
                                        seg_points(v3, v1)[1:]))
    audit_line(f"{site_key}/F5-C3 zone covers pos_tf + V3->V1 route",
               in_tf3 and route_illegal, f"r={r_c3:.0f} m", lines)
    audited["zone_c3"] = zone_c3

    # ---- F6-C3 envelope: strip ALONG the corridor (bearing V2->V1) through
    # pos_tf, half = max perpendicular offset of {pos_tf, V1, V3} + 60, so the
    # aircraft, the destination and the recovery leg all lie inside.
    head_cor = bearing(v2, v1)
    hw_c3 = max(perp_from_line(p, pos_tf, head_cor)
                for p in (pos_tf, v1, v3)) + 60.0
    start_c3 = shift(pos_tf,
                     -200.0 * math.cos(math.radians(head_cor)),
                     -200.0 * math.sin(math.radians(head_cor)))
    length_c3 = haversine_m(pos_tf, v1) + 1000.0
    env_c3 = strip_geom(start_c3, head_cor, hw_c3, length_c3)
    covers = (point_in_zone(*pos_tf, env_c3) and point_in_zone(*v1, env_c3)
              and point_in_zone(*v3, env_c3))
    route_in = all(point_in_zone(*p, env_c3) for p in seg_points(v3, v1))
    audit_line(f"{site_key}/F6-C3 envelope covers pos_tf + V1 + V3 (+V3->V1 "
               f"route)", covers and route_in,
               f"heading={head_cor:.1f} half={hw_c3:.0f} m", lines)
    audited["env_c3"] = env_c3 if (covers and route_in) else None

    # ---- C1 geometries ----
    zone_f2_c1 = {"type": "circle", "lat": v3[0], "lon": v3[1],
                  "radius_m": 300.0, "candidate_rule": "none"}
    corner = (bbox["north"] - 0.0015, bbox["west"] + 0.0015)
    zone_f5_c1 = {"type": "circle", "lat": corner[0], "lon": corner[1],
                  "radius_m": 400.0}
    # F6-C1: low-latitude strip SOUTH of the lowest facility/aircraft latitude
    # (V3 / V1 / pos_tf) so the critical corridor never touches it (fix: the
    # old "V3 - 0.0025" rule sat too close to the corridor on Site C and the
    # envelope caught the critical aircraft).
    strip_lat = min(v3[0], v1[0], pos_tf[0]) - 0.0030
    strip_f6_c1 = strip_geom((strip_lat, bbox["west"] + 0.0020), 90.0,
                             250.0, 2000.0)
    # audit: the critical corridor (V2->V1) and pos_tf stay clear of the
    # F6-C1 envelope (C1 = peripheral flyaway, critical chain untouched)
    f6c1_clear = (not point_in_zone(*pos_tf, strip_f6_c1)
                  and not point_in_zone(*v1, strip_f6_c1)
                  and not point_in_zone(*v3, strip_f6_c1)
                  and not any(segment_intersects_zone(p, q, strip_f6_c1)
                              for p, q in zip(seg_points(v2, v1)[:-1],
                                              seg_points(v2, v1)[1:])))
    audit_line(f"{site_key}/F6-C1 envelope clear of the critical corridor",
               f6c1_clear, f"strip lat={strip_lat:.4f}", lines)
    audited["zone_f2_c1"] = zone_f2_c1
    audited["zone_f5_c1"] = zone_f5_c1
    audited["env_f6_c1"] = strip_f6_c1

    return {"air_eta": air_eta, "t_failure": t_failure, "pos_tf": pos_tf,
            "audited": audited}


def main() -> int:
    lines: List[str] = []
    out: Dict[str, Any] = {}
    for key in ("b", "c"):
        r = derive_site(key, lines)
        out[key] = {
            "air_eta_s": round(r["air_eta"], 3),
            "t_failure": r["t_failure"],
            "pos_tf": {"lat": round(r["pos_tf"][0], 6),
                       "lon": round(r["pos_tf"][1], 6)},
            "geometry": {k: v for k, v in r["audited"].items()},
        }
    print("\n".join(lines))
    n_fail = sum(1 for l in lines if l.startswith("[FAIL]"))
    out_dir = ROOT / "outputs" / "experiment2"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cross_site_geometry_audit.json").write_text(
        json.dumps(out, indent=2, default=float), encoding="utf-8")
    print(f"\nGEOMETRY AUDIT: {'PASS' if n_fail == 0 else f'{n_fail} FAIL'}")
    if n_fail:
        return 1

    # ---- write the full per-site matrices ----
    for key in ("b", "c"):
        site = SITES[key]
        r = out[key]
        g = r["geometry"]
        t_f = r["t_failure"]
        prefix = site["prefix"]
        scen = []
        scen.append({"id": f"{prefix}F1_C1", "failure_family": "F1",
                     "impact_context": "C1", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F1", "time_s": t_f,
                                 "target": "L-UAV-01"}})
        scen.append({"id": f"{prefix}F1_C2", "failure_family": "F1",
                     "impact_context": "C2", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F1", "time_s": t_f,
                                 "target": "M-UAV-02"}})
        scen.append({"id": f"{prefix}F1_C3", "failure_family": "F1",
                     "impact_context": "C3", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W1",
                     "failure": {"family": "F1", "time_s": t_f,
                                 "target": "M-UAV-02"}})

        def f2_zone(zid, geometry):
            z = dict(geometry)
            z.update({"id": zid, "active_from_s": t_f, "active_until_s": 900,
                      "candidate_rule": "none"})
            return z

        scen.append({"id": f"{prefix}F2_C1", "failure_family": "F2",
                     "impact_context": "C1", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F2", "time_s": t_f,
                                 "zone": f2_zone("ZN-F2-01", g["zone_f2_c1"])}})
        scen.append({"id": f"{prefix}F2_C2", "failure_family": "F2",
                     "impact_context": "C2", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F2", "time_s": t_f,
                                 "zone": f2_zone("ZN-F2-02", g["zone_c2"])}})
        scen.append({"id": f"{prefix}F2_C3", "failure_family": "F2",
                     "impact_context": "C3", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W1",
                     "failure": {"family": "F2", "time_s": t_f,
                                 "zone": f2_zone("ZN-F2-03", g["zone_c2"])}})

        scen.append({"id": f"{prefix}F3_C1", "failure_family": "F3",
                     "impact_context": "C1", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "extra_mission": {
                         "id": "M-L-002", "type": "logistics",
                         "priority": "NORMAL", "origin": "V2",
                         "destination": "V3", "deadline_s": 900,
                         "ground_fallback": False, "delay_cost": 10.0,
                         "cancellation_cost": 100.0},
                     "failure": {"family": "F3", "time_s": t_f,
                                 "utm_state": "DEGRADED"}})
        scen.append({"id": f"{prefix}F3_C3", "failure_family": "F3",
                     "impact_context": "C3", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F3", "time_s": t_f,
                                 "utm_state": "OUTAGE"}})

        scen.append({"id": f"{prefix}F4_C1", "failure_family": "F4",
                     "impact_context": "C1", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F4", "time_s": t_f, "site": "V2"}})
        scen.append({"id": f"{prefix}F4_C3", "failure_family": "F4",
                     "impact_context": "C3", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F4", "time_s": t_f, "site": "V1"}})

        def f5_zone(zid, geometry, until=480):
            z = dict(geometry)
            z.update({"id": zid, "active_from_s": t_f, "active_until_s": until})
            return z

        def f5_traj():
            corner = g["zone_f5_c1"]
            return {"lat0": corner["lat"], "lon0": corner["lon"] - 0.0025,
                    "heading_deg": 90, "speed_kts": 25, "length_m": 2500}

        scen.append({"id": f"{prefix}F5_C1", "failure_family": "F5",
                     "impact_context": "C1", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F5", "time_s": t_f,
                                 "zone": f5_zone("ZN-F5-01", g["zone_f5_c1"]),
                                 "unknown_trajectory": f5_traj()}})
        scen.append({"id": f"{prefix}F5_C2", "failure_family": "F5",
                     "impact_context": "C2", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F5", "time_s": t_f,
                                 "zone": f5_zone("ZN-F5-02", g["zone_c2"]),
                                 "unknown_trajectory": {
                                     "lat0": g["zone_c2"]["lat"],
                                     "lon0": g["zone_c2"]["lon"] - 0.0030,
                                     "heading_deg": 90, "speed_kts": 25,
                                     "length_m": 2500}}})
        scen.append({"id": f"{prefix}F5_C3", "failure_family": "F5",
                     "impact_context": "C3", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F5", "time_s": t_f,
                                 "zone": f5_zone("ZN-F5-03", g["zone_c3"]),
                                 "unknown_trajectory": {
                                     "lat0": g["zone_c3"]["lat"],
                                     "lon0": g["zone_c3"]["lon"] - 0.0030,
                                     "heading_deg": 90, "speed_kts": 25,
                                     "length_m": 2500}}})

        def f6_env(eid, geometry):
            e = dict(geometry)
            e.update({"id": eid, "active_from_s": t_f, "active_until_s": 900})
            return e

        scen.append({"id": f"{prefix}F6_C1", "failure_family": "F6",
                     "impact_context": "C1", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F6", "time_s": t_f,
                                 "target": "L-UAV-01",
                                 "envelope": f6_env("ENV-F6-01",
                                                    g["env_f6_c1"]),
                                 "trajectory": {"speed_kts": 30}}})
        scen.append({"id": f"{prefix}F6_C2", "failure_family": "F6",
                     "impact_context": "C2", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F6", "time_s": t_f,
                                 "target": "L-UAV-01",
                                 "envelope": f6_env("ENV-F6-02", g["env_c2"]),
                                 "trajectory": {"speed_kts": 30}}})
        scen.append({"id": f"{prefix}F6_C3", "failure_family": "F6",
                     "impact_context": "C3", "disruption": "MEDIUM",
                     "urgency": "CRITICAL", "workload": "W0",
                     "failure": {"family": "F6", "time_s": t_f,
                                 "target": "L-UAV-01",
                                 "envelope": f6_env("ENV-F6-03", g["env_c3"]),
                                 "trajectory": {"speed_kts": 30}}})

        doc = (
            "# Experiment 2 cross-site matrix — "
            + ("Site B (Amsterdam)." if key == "b" else "Site C (Edmonton).")
            + "\n#\n"
            "# Site-adapted per the user-approved plan (E2-EXT-XSITE-1):\n"
            f"#   t_failure = 300 + floor(air_eta/2) = {t_f} s (air_eta = "
            f"{out[key]['air_eta_s']} s), so the critical chain is airborne at the\n"
            "#   failure on this site (Site B's canonical-t=360 issue fixed).\n"
            "#   F2/F5/F6 geometry re-derived from the site's own V1/V2/V3 and\n"
            "#   audited (outputs/experiment2/cross_site_geometry_audit.json).\n"
            "# Mirrors the canonical 16-class matrix incl. the two documented\n"
            "# SCENARIO_DESIGN_LIMITATIONs (F3-C2, F4-C2). Site A frozen.\n"
        )
        data = {
            "experiment2": {
                "version": 1, "duration_s": 900, "step_s": 1,
                "mission_release_t_s": 300, "disruption_t_s": 300,
                "failure_t_s": t_f, "periodic_decision_s": 30,
                "emergency_mission": {"mission_id": "M-CRITICAL-001",
                                      "type": "medical_blood", "origin": "V2",
                                      "destination": "V1", "ground_fallback": True},
                "disruptions": {"MEDIUM": {"severity": "MEDIUM", "links": ["B1"]}},
                "urgencies": {"CRITICAL": {"priority": "CRITICAL",
                                           "deadline_slack_s": 180,
                                           "delay_cost": 60.0,
                                           "cancellation_cost": 600.0}},
                "workloads": {
                    "W0": {"busy": [
                        ["L-UAV-01", "M-L-001", "logistics", "NORMAL", "V2", "V3", False],
                        ["EVTOL-01", "M-P-001", "passenger_transfer", "NORMAL", "V2", "V1", False]],
                        "idle": ["M-UAV-01", "M-UAV-02"]},
                    "W1": {"busy": [
                        ["L-UAV-01", "M-L-001", "logistics", "NORMAL", "V2", "V3", False],
                        ["EVTOL-01", "M-P-001", "passenger_transfer", "NORMAL", "V2", "V1", False],
                        ["M-UAV-01", "M-M-001", "medical_transfer", "HIGH", "V1", "V3", False]],
                        "idle": ["M-UAV-02"]}},
                "scenarios": scen,
                "smoke": [f"{prefix}F1_C2", f"{prefix}F2_C2", f"{prefix}F3_C3",
                          f"{prefix}F4_C3", f"{prefix}F5_C2", f"{prefix}F6_C2"],
                "pilots": [
                    {"scenario": f"{prefix}F1_C1", "label": "PILOT-F1-C1"},
                    {"scenario": f"{prefix}F4_C1", "label": "PILOT-F4-C1"},
                    {"scenario": f"{prefix}F2_C2", "label": "PILOT-F2-C2"},
                    {"scenario": f"{prefix}F5_C2", "label": "PILOT-F5-C2"},
                    {"scenario": f"{prefix}F3_C3", "label": "PILOT-F3-C3"},
                    {"scenario": f"{prefix}F6_C3", "label": "PILOT-F6-C3"}],
            }
        }
        site["matrix"].write_text(
            doc + yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8")
        print(f"wrote {site['matrix']} ({len(scen)} scenarios, t_failure={t_f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
