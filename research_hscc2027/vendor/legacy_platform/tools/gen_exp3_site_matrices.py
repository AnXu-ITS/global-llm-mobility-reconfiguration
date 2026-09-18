"""Experiment 3 cross-site matrix generator + geometry-invariant audit.

Site-adapts the frozen Site-A Experiment-3 L1-L4 matrix (12 scenarios) to
Site B (Amsterdam) and Site C (Edmonton), reusing the FROZEN site-adaptation
rules from E2 (E2-EXT-XSITE-1) and the E2 cross-site geometry procedure:

  SITE FAILURE-TIME RULE (frozen):  t_failure = 300 + max(20, round(air_eta/2))
      air_eta = haversine(V2->V1)/15 m/s. Site A frozen 360 s (air_eta ~114.5 s
      -> rule 357 s, within 3 s). The multi-event timeline keeps its frozen
      relative offsets: failure-A = t_failure, second-emergency = +30,
      failure-B = +60, failure-C = +120.

  GEOMETRY RE-DERIVATION (per site, from the site's own V1/V2/V3):
      pos_tf        = critical aircraft position at t_failure (15 m/s along V2->V1)
      v3v1_mid      = midpoint(V3, V1)  (F5 "cover recovery route" zones)
      F2 corridor   = circle r=100 at pos_tf (candidate_rule none)
      F2 V3         = circle r=300 at V3   (candidate_rule none)
      F5 NW corner  = circle r=400 at bbox NW corner (no asset)
      F6 envelope   = strip PARALLEL to V3->V1 through pos_tf,
                      half_width = min(200, min_clearance - 40)  (E2 F6-C2 rule)
      F5 trajectory = starts SW of its zone (lon - 0.0025), heading 90 deg.

  INVARIANTS AUDITED (mirror tools/audit_exp3_scenarios.py):
      F5 cover zones intersect V3->V1; F5 NW-corner contains no site;
      F2 zones candidate_rule none; F6 envelope crosses V2->V1 (via pos_tf) and
      stays clear of V3->V1.

Writes config/experiment3_site_b_matrix.yaml / config/experiment3_site_c_matrix.yaml
and outputs/experiment3/cross_site_geometry_audit.json. The frozen Site-A matrix
(config/experiment3_matrix.yaml) and Site-A dataset are untouched.

Usage:  python tools/gen_exp3_site_matrices.py [--check]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from failures.e2_failures import (haversine_m, point_in_zone,  # noqa: E402
                                  point_segment_distance_m, segment_intersects_zone,
                                  strip_ends)
from orchestrator import config as config_mod  # noqa: E402

LAT_M = 111194.9
CRUISE_MS = 15.0
DISPATCH_OVERHEAD_S = 0.0

SITES = {
    "b": {
        "site_id": "site_b_amsterdam",
        "config": ROOT / "sim" / "sites" / "site_b_amsterdam" / "config" /
                  "site_b_amsterdam_config.yaml",
        "matrix": ROOT / "config" / "experiment3_site_b_matrix.yaml",
        "prefix": "E3XB_",
    },
    "c": {
        "site_id": "site_c_edmonton",
        "config": ROOT / "sim" / "sites" / "site_c_edmonton" / "config" /
                  "site_c_edmonton_config.yaml",
        "matrix": ROOT / "config" / "experiment3_site_c_matrix.yaml",
        "prefix": "E3XC_",
    },
}


def _d2m(lat1, lon1, lat2, lon2) -> Tuple[float, float]:
    return ((lat2 - lat1) * LAT_M,
            (lon2 - lon1) * LAT_M * math.cos(math.radians((lat1 + lat2) / 2)))


def point_along(a, b, dist_m):
    total = haversine_m(a, b)
    f = max(0.0, min(1.0, dist_m / total if total > 0 else 1.0))
    return (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))


def midpoint(a, b):
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def bearing(a, b):
    dy, dx = _d2m(*a, *b)
    return math.degrees(math.atan2(dx, dy)) % 360.0


def shift(pt, north_m, east_m):
    lat = pt[0] + north_m / LAT_M
    lon = pt[1] + east_m / (LAT_M * math.cos(math.radians(pt[0])))
    return (lat, lon)


def seg_points(a, b, n=12):
    return [point_along(a, b, haversine_m(a, b) * i / n) for i in range(n + 1)]


def audit_line(label, ok, detail, lines):
    lines.append(f"[{'PASS' if ok else 'FAIL'}] {label}: {detail}")


def derive_site(site_key, lines):
    site = SITES[site_key]
    cfg = config_mod.load_config(site["config"])
    fac = cfg["facilities"]
    v1 = (float(fac["V1"]["lat"]), float(fac["V1"]["lon"]))
    v2 = (float(fac["V2"]["lat"]), float(fac["V2"]["lon"]))
    v3 = (float(fac["V3"]["lat"]), float(fac["V3"]["lon"]))
    bbox = cfg["bbox"]

    air_eta = haversine_m(v2, v1) / CRUISE_MS + DISPATCH_OVERHEAD_S
    t_failure = 300 + max(20, int(round(air_eta / 2.0)))
    pos_tf = point_along(v2, v1, CRUISE_MS * (t_failure - 300))
    v3v1_mid = midpoint(v3, v1)
    nw = (bbox["north"] - 0.0015, bbox["west"] + 0.0015)
    lines.append(f"site {site_key}: air_eta={air_eta:.1f}s -> t_failure={t_failure} "
                 f"(second_emergency={t_failure+30}, failure_B={t_failure+60}, "
                 f"failure_C={t_failure+120}); pos_tf=({pos_tf[0]:.6f},{pos_tf[1]:.6f})")

    # ---- F5 cover-V3->V1 zones (center = midpoint) ----
    # The centre lies ON the V3->V1 segment by construction, so it trivially
    # "covers" (intersects) the recovery route; radius kept from frozen Site A.
    d_center_seg = point_segment_distance_m(v3v1_mid, v3, v1)
    audit_line(f"{site_key}/F5-cover centre on V3->V1", d_center_seg < 1.0,
               f"dist={d_center_seg:.2f} m", lines)
    cover = {
        "E3-01": {"radius_m": 250},   # L2_F1_F5 failure-B
        "E3-02": {"radius_m": 200},   # L2_F6_F5 failure-B
        "E3-04": {"radius_m": 200},   # L4_B failure-B
    }
    zones_f5_cover = {
        k: {"type": "circle", "lat": round(v3v1_mid[0], 7),
            "lon": round(v3v1_mid[1], 7), "radius_m": v["radius_m"]}
        for k, v in cover.items()}

    # ---- F2 corridor zone at pos_tf (candidate_rule none) ----
    zone_f2_corridor = {"type": "circle", "lat": round(pos_tf[0], 7),
                        "lon": round(pos_tf[1], 7), "radius_m": 100,
                        "candidate_rule": "none"}
    # ---- F5 corridor zone at pos_tf (route intrusion, NO candidate_rule) ----
    zone_f5_corridor = {"type": "circle", "lat": round(pos_tf[0], 7),
                        "lon": round(pos_tf[1], 7), "radius_m": 100}

    # ---- F2 V3 zones (candidate_rule none) ----
    zone_f2_v3 = {"type": "circle", "lat": round(v3[0], 7), "lon": round(v3[1], 7),
                  "radius_m": 300, "candidate_rule": "none"}

    # ---- F5 NW-corner zone (no asset) ----
    zone_f5_nw = {"type": "circle", "lat": round(nw[0], 7), "lon": round(nw[1], 7),
                  "radius_m": 400}
    nw_clear = all(haversine_m(nw, p) > 400.0 for p in (v1, v2, v3))
    audit_line(f"{site_key}/F5-NW corner contains no site", nw_clear,
               f"corner=({nw[0]:.4f},{nw[1]:.4f})", lines)

    # ---- F6 envelope: strip parallel to V3->V1 through pos_tf, clear of V3->V1
    # (E2 F6-C2 rule). Because it passes through pos_tf (on V2->V1) it crosses
    # the critical corridor; because it is parallel to V3->V1 with >=40 m
    # clearance it stays clear of the recovery route.
    def perp_from_line(pt, line_pt, heading):
        dy, dx = _d2m(*line_pt, *pt)
        n = (math.sin(math.radians(heading)), -math.cos(math.radians(heading)))
        return abs(dy * n[0] + dx * n[1])

    head = bearing(v3, v1)
    clear_v1 = perp_from_line(v1, pos_tf, head)
    clear_v3 = perp_from_line(v3, pos_tf, head)
    clear_seg = min(perp_from_line(p, pos_tf, head) for p in seg_points(v3, v1))
    hw = min(200.0, min(clear_v1, clear_v3, clear_seg) - 40.0)
    start = shift(pos_tf, -150.0 * math.cos(math.radians(head)),
                  -150.0 * math.sin(math.radians(head)))
    env_f6 = {"type": "strip", "lat0": round(start[0], 7),
              "lon0": round(start[1], 7), "heading_deg": round(head, 4),
              "half_width_m": round(hw, 2), "length_m": 3000.0}
    ends = strip_ends(env_f6)
    d_crit = min(point_segment_distance_m(p, *ends) for p in seg_points(v2, v1))
    d_rec = min(point_segment_distance_m(p, *ends) for p in seg_points(v3, v1))
    ok_f6 = (d_crit <= hw) and (d_rec > hw + 30.0)
    audit_line(f"{site_key}/F6 envelope crosses V2->V1 and clears V3->V1", ok_f6,
               f"heading={head:.1f} hw={hw:.0f} m (crit {d_crit:.0f}, rec {d_rec:.0f} m)",
               lines)

    return {
        "air_eta_s": round(air_eta, 3), "t_failure": t_failure,
        "pos_tf": (round(pos_tf[0], 7), round(pos_tf[1], 7)),
        "v3v1_mid": (round(v3v1_mid[0], 7), round(v3v1_mid[1], 7)),
        "zones_f5_cover": zones_f5_cover,
        "zone_f2_corridor": zone_f2_corridor,
        "zone_f5_corridor": zone_f5_corridor,
        "zone_f2_v3": zone_f2_v3,
        "zone_f5_nw": zone_f5_nw,
        "env_f6": env_f6,
    }


def f5_traj(zcenter):
    """F5 unknown_trajectory: SW of the zone centre, heading east (frozen rule)."""
    return {"lat0": round(zcenter[0], 7), "lon0": round(zcenter[1] - 0.0025, 7),
            "heading_deg": 90, "speed_kts": 25, "length_m": 2500}


def build_scenarios(g, tf, prefix):
    def f1(target, t):
        return {"family": "F1", "time_s": t, "target": target}

    def f2(zone, t, zid, until):
        z = dict(zone)
        z.update({"id": zid, "active_from_s": t, "active_until_s": until})
        return {"family": "F2", "time_s": t, "zone": z}

    def f4(site, t):
        return {"family": "F4", "time_s": t, "site": site}

    def f5(zone, t, zid):
        z = dict(zone)
        z.update({"id": zid, "active_from_s": t, "active_until_s": t + 120})
        return {"family": "F5", "time_s": t, "zone": z,
                "unknown_trajectory": f5_traj((z["lat"], z["lon"]))}

    def f6(env, t, eid, until):
        e = dict(env)
        e.update({"id": eid, "active_from_s": t, "active_until_s": until})
        return {"family": "F6", "time_s": t, "target": "L-UAV-01",
                "envelope": e, "trajectory": {"speed_kts": 30}}

    ta = tf
    tb = tf + 60
    tc = tf + 120

    S = []
    S.append({"id": f"{prefix}L1_F1_C2", "level": "L1", "motif": "anchor_single_c2_lost",
              "disruption": "MEDIUM", "urgency": "CRITICAL", "workload": "W0",
              "duration_s": 900, "emergencies": ["M-CRITICAL-001"],
              "failure_schedule": [f1("M-UAV-02", ta)]})
    S.append({"id": f"{prefix}L1_F5_C2", "level": "L1", "motif": "anchor_single_intrusion",
              "disruption": "MEDIUM", "urgency": "CRITICAL", "workload": "W0",
              "duration_s": 900, "emergencies": ["M-CRITICAL-001"],
              "failure_schedule": [f5(g["zone_f5_corridor"], ta, "ZN-F5-XS-01")]})
    S.append({"id": f"{prefix}L2_F1_F1", "level": "L2", "motif": "cascade_double_c2_lost",
              "disruption": "MEDIUM", "urgency": "CRITICAL", "workload": "W0",
              "duration_s": 900, "emergencies": ["M-CRITICAL-001"],
              "failure_schedule": [f1("M-UAV-02", ta), f1("M-UAV-01", tb)]})
    S.append({"id": f"{prefix}L2_F1_F5", "level": "L2", "motif": "cascade_c2lost_then_intrusion",
              "disruption": "MEDIUM", "urgency": "CRITICAL", "workload": "W0",
              "duration_s": 900, "emergencies": ["M-CRITICAL-001"],
              "failure_schedule": [f1("M-UAV-02", ta),
                                   f5(g["zones_f5_cover"]["E3-01"], tb, "ZN-F5-XS-02")]})
    S.append({"id": f"{prefix}L2_F2_F4", "level": "L2", "motif": "cascade_gnss_then_site",
              "disruption": "MEDIUM", "urgency": "CRITICAL", "workload": "W0",
              "duration_s": 900, "emergencies": ["M-CRITICAL-001"],
              "failure_schedule": [f2(g["zone_f2_corridor"], ta, "ZN-F2-XS-01", 900),
                                   f4("V1", tb)]})
    S.append({"id": f"{prefix}L2_F6_F5", "level": "L2", "motif": "cascade_flyaway_then_intrusion",
              "disruption": "MEDIUM", "urgency": "CRITICAL", "workload": "W0",
              "duration_s": 900, "emergencies": ["M-CRITICAL-001"],
              "failure_schedule": [f6(g["env_f6"], ta, "ENV-F6-XS-01", 900),
                                   f5(g["zones_f5_cover"]["E3-02"], tb, "ZN-F5-XS-03")]})
    S.append({"id": f"{prefix}L3_COMP_F1", "level": "L3", "motif": "competition_peripheral_c2_lost",
              "disruption": "MEDIUM", "urgency": "CRITICAL", "workload": "W1",
              "duration_s": 1200, "emergencies": ["M-CRITICAL-001", "M-CRITICAL-002"],
              "failure_schedule": [f1("L-UAV-01", ta)]})
    S.append({"id": f"{prefix}L3_COMP_F2", "level": "L3", "motif": "competition_peripheral_gnss",
              "disruption": "MEDIUM", "urgency": "CRITICAL", "workload": "W1",
              "duration_s": 1200, "emergencies": ["M-CRITICAL-001", "M-CRITICAL-002"],
              "failure_schedule": [f2(g["zone_f2_v3"], ta, "ZN-F2-XS-02", 900)]})
    S.append({"id": f"{prefix}L3_COMP_F4", "level": "L3", "motif": "competition_peripheral_site",
              "disruption": "MEDIUM", "urgency": "CRITICAL", "workload": "W1",
              "duration_s": 1200, "emergencies": ["M-CRITICAL-001", "M-CRITICAL-002"],
              "failure_schedule": [f4("V2", ta)]})
    S.append({"id": f"{prefix}L3_COMP_F5", "level": "L3", "motif": "competition_peripheral_intrusion",
              "disruption": "MEDIUM", "urgency": "CRITICAL", "workload": "W1",
              "duration_s": 1200, "emergencies": ["M-CRITICAL-001", "M-CRITICAL-002"],
              "failure_schedule": [f5(g["zone_f5_nw"], ta, "ZN-F5-XS-04")]})
    S.append({"id": f"{prefix}L4_A", "level": "L4", "motif": "full_compound_aircraft_site_competition",
              "disruption": "MEDIUM", "urgency": "CRITICAL", "workload": "W1",
              "duration_s": 1200, "emergencies": ["M-CRITICAL-001", "M-CRITICAL-002"],
              "failure_schedule": [f1("L-UAV-01", ta), f4("V1", tb)]})
    S.append({"id": f"{prefix}L4_B", "level": "L4", "motif": "full_compound_triple_zone",
              "disruption": "MEDIUM", "urgency": "CRITICAL", "workload": "W1",
              "duration_s": 1200, "emergencies": ["M-CRITICAL-001", "M-CRITICAL-002"],
              "failure_schedule": [f6(g["env_f6"], ta, "ENV-F6-XS-02", 1200),
                                   f5(g["zones_f5_cover"]["E3-04"], tb, "ZN-F5-XS-05"),
                                   f2(g["zone_f2_v3"], tc, "ZN-F2-XS-03", 1200)]})
    return S


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    # frozen top-level E3 config (copied verbatim from Site A; only times change)
    base = yaml.safe_load(
        (ROOT / "config" / "experiment3_matrix.yaml").read_text(encoding="utf-8"))["experiment3"]

    lines = []
    audit_out = {}
    for key in ("b", "c"):
        site = SITES[key]
        r = derive_site(key, lines)
        tf = r["t_failure"]
        audit_out[key] = r
        scen = build_scenarios(r, tf, site["prefix"])

        data = {
            "experiment3": {
                "version": 1, "step_s": 1,
                "mission_release_t_s": int(base["mission_release_t_s"]),
                "disruption_t_s": int(base["disruption_t_s"]),
                "failure_a_t_s": tf,
                "second_emergency_t_s": tf + 30,
                "failure_b_t_s": tf + 60,
                "failure_c_t_s": tf + 120,
                "periodic_decision_s": int(base["periodic_decision_s"]),
                "primary_emergency": base["primary_emergency"],
                "second_emergency": base["second_emergency"],
                "disruptions": base["disruptions"],
                "urgencies": base["urgencies"],
                "workloads": base["workloads"],
                "scenarios": scen,
                "pilots": [
                    {"scenario": f"{site['prefix']}L1_F1_C2", "label": "PILOT-L1"},
                    {"scenario": f"{site['prefix']}L1_F5_C2", "label": "PILOT-L1-F5"},
                    {"scenario": f"{site['prefix']}L2_F1_F5", "label": "PILOT-L2"},
                    {"scenario": f"{site['prefix']}L2_F6_F5", "label": "PILOT-L2-zones"},
                    {"scenario": f"{site['prefix']}L3_COMP_F1", "label": "PILOT-L3"},
                    {"scenario": f"{site['prefix']}L4_B", "label": "PILOT-L4"},
                ],
            }
        }
        doc = (
            "# Experiment 3 cross-site matrix — "
            + ("Site B (Amsterdam)." if key == "b" else "Site C (Edmonton).")
            + "\n#\n"
            "# Site-adapted per the frozen E2 cross-site rule (E2-EXT-XSITE-1):\n"
            f"#   t_failure = 300 + round(air_eta/2) = {tf} s (air_eta = {r['air_eta_s']} s)\n"
            "#   with the frozen E3 multi-event offsets +30/+60/+120 and per-site\n"
            "#   F2/F5/F6 geometry re-derived from the site's own V1/V2/V3 and audited\n"
            "#   (outputs/experiment3/cross_site_geometry_audit.json). Site A frozen.\n"
        )
        if not args.check:
            site["matrix"].write_text(
                doc + yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8")
            print(f"wrote {site['matrix']} ({len(scen)} scenarios, t_failure={tf})")

    print("\n".join(lines))
    n_fail = sum(1 for l in lines if l.startswith("[FAIL]"))
    if not args.check:
        out_dir = ROOT / "outputs" / "experiment3"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "cross_site_geometry_audit.json").write_text(
            json.dumps(audit_out, indent=2, default=float), encoding="utf-8")
        print(f"wrote outputs/experiment3/cross_site_geometry_audit.json")
    print(f"GEOMETRY AUDIT: {'PASS' if n_fail == 0 else str(n_fail) + ' FAIL'}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
