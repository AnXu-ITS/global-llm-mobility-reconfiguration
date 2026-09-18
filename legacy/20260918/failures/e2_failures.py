"""Experiment-2 air-failure injectors (F1-F6) + risk-zone geometry.

Each injector is a PURE function of (runner state, frozen failure config):
it never reads any manager's decision and never chooses the target from
manager behaviour — the failure family, target, time, zone/site/trajectory are
all frozen in `config/experiment2_matrix.yaml` (exogeneity per protocol §7/§8).

Injectors mutate ONLY:
  - the registry (aircraft / mission states, per the frozen semantics),
  - BlueSky commands (local safety: contingency / divert flights, UNKN-01),
  - runner bookkeeping (aircraft_dest / aircraft_route / diverted set),
and record events through the runner's frozen `_record_event`.

Frozen semantics per family: see EXPERIMENT2_PROTOCOL_EXTENSIONS.md
(E2-EXT-F1-1 ... E2-EXT-F6-1).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from failures.state_ext import apply_transition
from orchestrator.fleet import MPS_TO_KTS, ROLE_ALT_FT, ROLE_CRUISE_MS

LAT_M = 111194.9  # meters per degree of latitude
ACTIONABLE_AIR = ("EN_ROUTE", "ASSIGNED")


# ----------------------------------------------------------------------
# geometry (deterministic, haversine-based, frozen for the run)
# ----------------------------------------------------------------------
def haversine_m(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371008.8 * 2 * math.asin(min(1.0, math.sqrt(h)))


def _to_xy(lat: float, lon: float, origin: Tuple[float, float]) -> Tuple[float, float]:
    """Local tangent-plane meters relative to origin."""
    return ((lat - origin[0]) * LAT_M,
            (lon - origin[1]) * LAT_M * math.cos(math.radians(origin[0])))


def point_segment_distance_m(p: Tuple[float, float],
                             a: Tuple[float, float],
                             b: Tuple[float, float]) -> float:
    """Great-circle distance from point p to segment a-b (tangent-plane approx)."""
    o = a
    pp = _to_xy(*p, origin=o)
    aa = (0.0, 0.0)
    bb = _to_xy(*b, origin=o)
    dx, dy = bb[0] - aa[0], bb[1] - aa[1]
    seg_len2 = dx * dx + dy * dy
    if seg_len2 <= 1e-12:
        return math.hypot(pp[0], pp[1])
    t = max(0.0, min(1.0, ((pp[0] - aa[0]) * dx + (pp[1] - aa[1]) * dy) / seg_len2))
    cx, cy = aa[0] + t * dx, aa[1] + t * dy
    return math.hypot(pp[0] - cx, pp[1] - cy)


def _segments_intersect_xy(a1, a2, b1, b2) -> bool:
    """Proper segment-segment intersection in tangent-plane XY (orientation test)."""
    def _orient(p, q, r):
        val = (q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0])
        if abs(val) < 1e-12:
            return 0
        return 1 if val > 0 else -1

    def _on_seg(p, q, r):
        return (min(p[0], r[0]) - 1e-9 <= q[0] <= max(p[0], r[0]) + 1e-9 and
                min(p[1], r[1]) - 1e-9 <= q[1] <= max(p[1], r[1]) + 1e-9)

    o1, o2 = _orient(a1, a2, b1), _orient(a1, a2, b2)
    o3, o4 = _orient(b1, b2, a1), _orient(b1, b2, a2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_seg(a1, b1, a2):
        return True
    if o2 == 0 and _on_seg(a1, b2, a2):
        return True
    if o3 == 0 and _on_seg(b1, a1, b2):
        return True
    if o4 == 0 and _on_seg(b1, a2, b2):
        return True
    return False


def _segment_segment_distance_m(a1: Tuple[float, float], a2: Tuple[float, float],
                                b1: Tuple[float, float], b2: Tuple[float, float]) -> float:
    """Min distance between two segments; 0 when they intersect (tangent-plane).

    FIX (review 20260908 §6.3): the previous version sampled only the four
    endpoints, so an orthogonal crossing through the strip interior was reported
    as "not intersecting".
    """
    o = a1
    pa = (0.0, 0.0)
    qa = _to_xy(*a2, origin=o)
    pb = _to_xy(*b1, origin=o)
    qb = _to_xy(*b2, origin=o)
    if _segments_intersect_xy(pa, qa, pb, qb):
        return 0.0
    best = float("inf")
    for p in (a1, a2):
        best = min(best, point_segment_distance_m(p, b1, b2))
    for p in (b1, b2):
        best = min(best, point_segment_distance_m(p, a1, a2))
    return best


def circle_center(zone: Dict[str, Any]) -> Tuple[float, float]:
    return (float(zone["lat"]), float(zone["lon"]))


def point_in_zone(lat: float, lon: float, zone: Dict[str, Any]) -> bool:
    zt = zone.get("type")
    if zt == "circle":
        return haversine_m((lat, lon), circle_center(zone)) <= float(zone["radius_m"])
    if zt == "strip":
        a, b = strip_ends(zone)
        return point_segment_distance_m((lat, lon), a, b) <= float(zone["half_width_m"])
    raise ValueError(f"unknown zone type {zt}")


def strip_ends(zone: Dict[str, Any]) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    lat0, lon0 = float(zone["lat0"]), float(zone["lon0"])
    hdg = math.radians(float(zone["heading_deg"]))
    length = float(zone["length_m"])
    dlat = length * math.cos(hdg) / LAT_M
    dlon = length * math.sin(hdg) / (LAT_M * math.cos(math.radians(lat0)))
    return (lat0, lon0), (lat0 + dlat, lon0 + dlon)


def segment_intersects_zone(a: Tuple[float, float], b: Tuple[float, float],
                            zone: Dict[str, Any]) -> bool:
    if point_in_zone(a[0], a[1], zone) or point_in_zone(b[0], b[1], zone):
        return True
    if zone.get("type") == "circle":
        return point_segment_distance_m(circle_center(zone), a, b) <= float(zone["radius_m"])
    if zone.get("type") == "strip":
        s1, s2 = strip_ends(zone)
        return _segment_segment_distance_m(a, b, s1, s2) <= float(zone["half_width_m"])
    raise ValueError(f"unknown zone type {zone.get('type')}")


def route_intersects_zone(route: List[Tuple[float, float]], zone: Dict[str, Any]) -> bool:
    for a, b in zip(route, route[1:]):
        if segment_intersects_zone(a, b, zone):
            return True
    return False


def active_zones(zones: List[Dict[str, Any]], t: int) -> List[Dict[str, Any]]:
    return [z for z in zones if z["active_from_s"] <= t <= z["active_until_s"]]


# ----------------------------------------------------------------------
# failure injectors
# ----------------------------------------------------------------------
def _mission_state_snapshot(runner) -> Dict[str, Dict[str, Any]]:
    return {mid: {"status": m.status, "mode": m.mode,
                  "assigned_resource": m.assigned_resource,
                  "priority": m.priority}
            for mid, m in runner.registry.missions.items()}


def _aircraft_state_snapshot(runner) -> Dict[str, Dict[str, Any]]:
    return {acid: {"status": ac.status, "c2_status": ac.c2_status,
                   "gnss_status": ac.gnss_status, "commandable": ac.commandable,
                   "reassignable": ac.reassignable, "mission_id": ac.mission_id}
            for acid, ac in runner.registry.aircraft.items()}


def _divert_to_v3(runner, acid: str, reason: str) -> None:
    """Local safety: the (commandable) aircraft abandons its mission and flies
    to the backup site V3. Manager-independent; recorded as an event."""
    runner.aircraft_dest[acid] = "V3"
    runner.aircraft_route.pop(acid, None)
    runner.diverted_aircraft[acid] = reason
    role = runner.aircraft_role[acid]
    runner.bs.fly_to(acid, "V3", alt_ft=ROLE_ALT_FT[role],
                     spd_kts=ROLE_CRUISE_MS[role] * MPS_TO_KTS)
    runner._record_event(runner.t, "LOCAL_SAFETY_DIVERT", "LOCAL_CONTINGENCY",
                         {"aircraft": acid, "target_site": "V3", "reason": reason})


def _abandon_mission(runner, acid: str) -> Optional[str]:
    """Interrupt the aircraft's current air mission and detach the aircraft
    (frozen F1 pattern: the aircraft abandons the mission)."""
    ac = runner.registry.aircraft[acid]
    mid = ac.mission_id
    if not mid:
        return None
    m = runner.registry.missions.get(mid)
    if m is None:
        ac.mission_id = None
        return None
    if m.status in ("EN_ROUTE", "ASSIGNED"):
        if m.status == "EN_ROUTE":
            m.transition("INTERRUPTED")
        m.transition("NEEDS_REPLAN")
    ac.mission_id = None
    m.assigned_resource = None
    runner._record_mission(runner.t, m)
    runner._record_event(runner.t, "MISSION_INTERRUPTED", "MISSION",
                         {"mission": mid, "status": m.status, "cause": "air_failure"})
    return mid


def _critical_candidate_stats(runner, gs: Dict[str, Any]) -> Dict[str, Any]:
    """Feasible-air stats for the critical mission on this GS.

    Uses the REAL candidate table when the critical mission is the table's
    target; otherwise a deterministic as-if NEEDS_REPLAN evaluation
    (cargo staged at V3, frozen recovery route), labelled `source`.
    """
    cand = gs.get("candidates") or {}
    if cand.get("summary", {}).get("target_mission_id") == runner.support_mission_id:
        air = cand.get("air", [])
        ground = cand.get("ground", {})
        source = "decision_table"
    else:
        crit = runner.registry.missions.get(runner.support_mission_id)
        if crit is None:
            return {"count": 0, "best_eta_s": None, "legal_resources": [],
                    "ground_feasible": False, "ground_eta_s": None, "source": "no_mission"}
        row = {"id": crit.id, "type": crit.type, "priority": crit.priority,
               "origin": crit.origin, "destination": crit.destination,
               "deadline_s": crit.deadline_s, "state": "NEEDS_REPLAN"}
        table = runner.candidate_evaluator.evaluate_for(gs, row, is_new=False)
        air = table.get("air", [])
        ground = table.get("ground", {})
        source = "as_if_needs_replan"
    legal = [c for c in air if c.get("legal")]
    etas = [c.get("eta_s") for c in legal if c.get("eta_s") is not None]
    return {"count": len(legal),
            "best_eta_s": round(min(etas), 3) if etas else None,
            "legal_resources": [c.get("resource_id") for c in legal],
            "ground_feasible": bool(ground.get("legal")),
            "ground_eta_s": ground.get("eta_s"),
            "source": source}


def _critical_candidate_count(runner, gs: Dict[str, Any]) -> int:
    return _critical_candidate_stats(runner, gs)["count"]


def _availability_counts(runner) -> Dict[str, int]:
    usable = sum(1 for ac in runner.registry.aircraft.values()
                 if ac.status in ("AVAILABLE", "BUSY"))
    commandable = sum(1 for ac in runner.registry.aircraft.values()
                      if ac.commandable and ac.c2_status == "NORMAL")
    compatible = sum(1 for ac in runner.registry.aircraft.values()
                     if "V1" in ac.landing_site_compatibility)
    return {"usable": usable, "commandable": commandable, "compatible": compatible}


def _zone_in_gs(runner, t: int) -> List[Dict[str, Any]]:
    return [z for z in runner.air_risk_zones
            if z["active_from_s"] <= t <= z["active_until_s"]]


# ----------------------------------------------------------------------
# F1 — C2 Lost Link (frozen semantics; extension: idle target allowed)
# ----------------------------------------------------------------------
def inject_f1(runner, cfg: Dict[str, Any]) -> Dict[str, Any]:
    target = cfg["target"]
    ac = runner.registry.aircraft[target]
    before = {"aircraft": _aircraft_state_snapshot(runner),
              "missions": _mission_state_snapshot(runner),
              "air_availability": _availability_counts(runner)}
    old_status = ac.status
    ac.c2_status = "LOST"
    ac.commandable = False
    ac.reassignable = False
    ac.contingency_mode = "RETURN"
    trans = apply_transition(ac, "CONTINGENCY")
    mid = _abandon_mission(runner, target)

    # local contingency: immediate, independent of the manager (frozen RETURN -> V3)
    runner.aircraft_dest[target] = "V3"
    runner.aircraft_route.pop(target, None)
    role = runner.aircraft_role[target]
    runner.bs.fly_to(target, "V3", alt_ft=ROLE_ALT_FT[role],
                     spd_kts=ROLE_CRUISE_MS[role] * MPS_TO_KTS)
    plan = {"aircraft_id": target, "mode": "RETURN", "target_site": "V3",
            "reason": "civil-UAS lost-link return-to-base (local, manager-independent)"}
    runner._record_event(runner.t, "C2_LOST", "C2_LOST",
                         {"aircraft_id": target, "old_status": old_status,
                          "new_status": ac.status, "c2_status": ac.c2_status,
                          "commandable": ac.commandable, "reassignable": ac.reassignable,
                          "mission_id": mid, "transition": trans})
    runner._record_event(runner.t, "LOCAL_CONTINGENCY", "LOCAL_CONTINGENCY", plan)

    after = {"aircraft": _aircraft_state_snapshot(runner),
             "missions": _mission_state_snapshot(runner),
             "air_availability": _availability_counts(runner)}
    return {"failure_family": "F1", "target": target, "local_contingency": plan,
            "state_before": before, "state_after": after,
            "affected_resources": {"aircraft": [target],
                                   "missions": [mid] if mid else []}}


# ----------------------------------------------------------------------
# F2 — GNSS / localization degradation (frozen one-shot zone policy)
# ----------------------------------------------------------------------
def inject_f2(runner, cfg: Dict[str, Any]) -> Dict[str, Any]:
    zone = dict(cfg["zone"])
    zone_id = zone["id"]
    before = {"aircraft": _aircraft_state_snapshot(runner),
              "missions": _mission_state_snapshot(runner),
              "air_availability": _availability_counts(runner)}
    affected_ac: List[str] = []
    affected_missions: List[str] = []
    for acid, ac in sorted(runner.registry.aircraft.items()):
        if point_in_zone(ac.lat, ac.lon, zone):
            ac.gnss_status = "DEGRADED"
            apply_transition(ac, "DEGRADED")
            affected_ac.append(acid)
            # frozen GNSS safe-policy: a BUSY aircraft en route to a precision
            # landing site can no longer guarantee the approach -> its mission
            # is interrupted and the aircraft diverts to V3 (local safety).
            if ac.mission_id:
                mid = _abandon_mission(runner, acid)
                if mid:
                    affected_missions.append(mid)
                _divert_to_v3(runner, acid, "GNSS degraded -> safe divert to V3")
    runner._record_event(runner.t, "GNSS_DEGRADED", "GNSS_DEGRADATION",
                         {"zone": zone_id, "aircraft": affected_ac,
                          "missions": affected_missions})
    after = {"aircraft": _aircraft_state_snapshot(runner),
             "missions": _mission_state_snapshot(runner),
             "air_availability": _availability_counts(runner)}
    return {"failure_family": "F2", "target": affected_ac,
            "zone_id": zone_id, "local_contingency": None,
            "state_before": before, "state_after": after,
            "affected_resources": {"aircraft": affected_ac,
                                   "missions": affected_missions}}


# ----------------------------------------------------------------------
# F3 — UTM / U-space outage (frozen DEGRADED / OUTAGE semantics)
# ----------------------------------------------------------------------
def inject_f3(runner, cfg: Dict[str, Any]) -> Dict[str, Any]:
    utm = cfg["utm_state"]
    before = {"aircraft": _aircraft_state_snapshot(runner),
              "missions": _mission_state_snapshot(runner),
              "air_availability": _availability_counts(runner)}
    runner.utm_state = utm
    affected_missions: List[str] = []
    if utm == "OUTAGE":
        # frozen safe-policy: all in-flight air missions terminate safely.
        for acid, ac in sorted(runner.registry.aircraft.items()):
            if ac.mission_id:
                mid = _abandon_mission(runner, acid)
                if mid:
                    affected_missions.append(mid)
                _divert_to_v3(runner, acid, "UTM OUTAGE -> safe termination to V3")
    runner._record_event(runner.t, "UTM_STATE_CHANGE", "UTM_OUTAGE",
                         {"utm_state": utm, "affected_missions": affected_missions})
    after = {"aircraft": _aircraft_state_snapshot(runner),
             "missions": _mission_state_snapshot(runner),
             "air_availability": _availability_counts(runner)}
    return {"failure_family": "F3", "target": "UTM_SERVICE",
            "utm_state": utm, "local_contingency": None,
            "state_before": before, "state_after": after,
            "affected_resources": {"missions": affected_missions}}


# ----------------------------------------------------------------------
# F4 — landing-site failure (Vx.available = false)
# ----------------------------------------------------------------------
def inject_f4(runner, cfg: Dict[str, Any]) -> Dict[str, Any]:
    site = cfg["site"]
    before = {"aircraft": _aircraft_state_snapshot(runner),
              "missions": _mission_state_snapshot(runner),
              "air_availability": _availability_counts(runner)}
    runner.fac[site]["available"] = False
    affected_ac: List[str] = []
    affected_missions: List[str] = []
    for acid, ac in sorted(runner.registry.aircraft.items()):
        mid = ac.mission_id
        if not mid:
            continue
        m = runner.registry.missions.get(mid)
        if m is not None and m.destination == site and m.mode != "GROUND":
            _abandon_mission(runner, acid)
            affected_missions.append(mid)
            affected_ac.append(acid)
            _divert_to_v3(runner, acid, f"landing site {site} unavailable -> divert V3")
    runner._record_event(runner.t, "LANDING_SITE_FAILURE", "LANDING_SITE_FAILURE",
                         {"site": site, "aircraft": affected_ac,
                          "missions": affected_missions})
    after = {"aircraft": _aircraft_state_snapshot(runner),
             "missions": _mission_state_snapshot(runner),
             "air_availability": _availability_counts(runner)}
    return {"failure_family": "F4", "target": site, "local_contingency": None,
            "state_before": before, "state_after": after,
            "affected_resources": {"sites": [site], "aircraft": affected_ac,
                                   "missions": affected_missions}}


# ----------------------------------------------------------------------
# F5 — unknown / non-cooperative aircraft + temporary risk zone
# ----------------------------------------------------------------------
def inject_f5(runner, cfg: Dict[str, Any]) -> Dict[str, Any]:
    zone = dict(cfg["zone"])
    before = {"aircraft": _aircraft_state_snapshot(runner),
              "missions": _mission_state_snapshot(runner),
              "air_availability": _availability_counts(runner)}
    # create the non-cooperative aircraft in BlueSky (never in the registry)
    traj = cfg["unknown_trajectory"]
    strip = {"type": "strip", "lat0": traj["lat0"], "lon0": traj["lon0"],
             "heading_deg": traj["heading_deg"], "half_width_m": 1.0,
             "length_m": traj["length_m"]}
    end_lat, end_lon = strip_ends(strip)[1]
    runner.bs.command(f"DEFWPT UNKN-END,{end_lat:.7f},{end_lon:.7f},FIX")
    runner.bs.command(f"CRE UNKN-01,Phan4,{traj['lat0']},{traj['lon0']},"
                      f"{traj['heading_deg']:.1f},600,{traj['speed_kts']:.1f}")
    runner.bs.command("DEST UNKN-01,UNKN-END")
    affected_ac: List[str] = []
    affected_missions: List[str] = []
    for acid, ac in sorted(runner.registry.aircraft.items()):
        if point_in_zone(ac.lat, ac.lon, zone):
            if ac.mission_id:
                mid = _abandon_mission(runner, acid)
                if mid:
                    affected_missions.append(mid)
                if ac.commandable and ac.status != "CONTINGENCY":
                    _divert_to_v3(runner, acid, "risk zone crossing -> local divert to V3")
                affected_ac.append(acid)
    runner._record_event(runner.t, "UNKNOWN_AIRCRAFT", "UNKNOWN_AIRCRAFT_INTRUSION",
                         {"aircraft": "UNKN-01", "zone": zone["id"],
                          "affected_aircraft": affected_ac,
                          "affected_missions": affected_missions})
    after = {"aircraft": _aircraft_state_snapshot(runner),
             "missions": _mission_state_snapshot(runner),
             "air_availability": _availability_counts(runner)}
    return {"failure_family": "F5", "target": "UNKN-01", "zone_id": zone["id"],
            "local_contingency": None,
            "state_before": before, "state_after": after,
            "affected_resources": {"aircraft": affected_ac,
                                   "missions": affected_missions}}


# ----------------------------------------------------------------------
# F6 — flyaway / uncontrolled trajectory + envelope
# ----------------------------------------------------------------------
def inject_f6(runner, cfg: Dict[str, Any]) -> Dict[str, Any]:
    target = cfg["target"]
    strip = dict(cfg["envelope"])
    before = {"aircraft": _aircraft_state_snapshot(runner),
              "missions": _mission_state_snapshot(runner),
              "air_availability": _availability_counts(runner)}
    ac = runner.registry.aircraft[target]
    ac.contingency_mode = "UNCONTROLLED"
    ac.trajectory_mode = "UNCONTROLLED_PREDEFINED"  # dynamic attribute (E2-EXT-F6-1)
    ac.commandable = False
    ac.reassignable = False
    trans = apply_transition(ac, "CONTINGENCY")
    mid = _abandon_mission(runner, target)
    # uncontrolled flight along the frozen trajectory (end waypoint pre-defined)
    traj = cfg["trajectory"]
    end_lat, end_lon = strip_ends(strip)[1]
    runner.bs.command(f"DEFWPT FLYEND,{end_lat:.7f},{end_lon:.7f},FIX")
    runner.bs.command(f"DEST {target},FLYEND")
    runner.bs.command(f"SPD {target},{traj['speed_kts']:.1f}")
    # no aircraft_dest: the flyaway aircraft is NOT tracked for arrival
    # (FLYEND is not a facility); BlueSky flies it, the registry ignores it.
    runner.aircraft_dest.pop(target, None)
    runner.aircraft_route.pop(target, None)

    # envelope intersections: other missions crossing the envelope
    affected_ac: List[str] = [target]
    affected_missions: List[str] = [mid] if mid else []
    for acid, ac2 in sorted(runner.registry.aircraft.items()):
        if acid == target:
            continue
        if point_in_zone(ac2.lat, ac2.lon, strip):
            if ac2.mission_id:
                mid2 = _abandon_mission(runner, acid)
                if mid2:
                    affected_missions.append(mid2)
                if ac2.commandable and ac2.status != "CONTINGENCY":
                    _divert_to_v3(runner, acid, "flyaway envelope crossing -> divert V3")
                affected_ac.append(acid)
    runner._record_event(runner.t, "FLYAWAY", "FLYAWAY_UNCONTROLLED",
                         {"aircraft": target, "trajectory_mode": ac.trajectory_mode,
                          "envelope": strip["id"], "affected_aircraft": affected_ac,
                          "affected_missions": affected_missions})
    after = {"aircraft": _aircraft_state_snapshot(runner),
             "missions": _mission_state_snapshot(runner),
             "air_availability": _availability_counts(runner)}
    return {"failure_family": "F6", "target": target, "local_contingency": None,
            "state_before": before, "state_after": after,
            "affected_resources": {"aircraft": affected_ac,
                                   "missions": affected_missions}}


INJECTORS = {"F1": inject_f1, "F2": inject_f2, "F3": inject_f3,
             "F4": inject_f4, "F5": inject_f5, "F6": inject_f6}
