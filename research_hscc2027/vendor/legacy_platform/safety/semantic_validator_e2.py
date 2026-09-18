"""Experiment-2 semantic-validator extension (E2-EXT-SEM-1).

Subclasses the FROZEN SemanticValidator (safety/semantic_validator.py,
untouched) and adds GS-based error types mirroring the E2 checker:

    GNSS_DEGRADED_AIRCRAFT   aircraft in the GS has gnss_status DEGRADED
    RISK_ZONE_VIOLATION      aircraft position or route intersects an active
                             air risk zone (geometry frozen per scenario)
    UTM_AIR_PROHIBITED       UTM state prohibits the air mission action

F4 is already covered by the frozen `SITE_UNAVAILABLE` (GS landing_sites) and
the frozen checker's `<site>_UNAVAILABLE`. The LLM manager's INTERNAL
validation/retry still uses the frozen validator (unchanged); this validator
runs in the orchestrator pipeline for EVERY manager, so a proposal violating
only E2 constraints is rejected and recorded — never silently repaired.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from failures.e2_failures import point_in_zone, route_intersects_zone
from safety.semantic_validator import SemanticValidator

AIR_MISSION_ACTIONS = ("DISPATCH", "REASSIGN", "DIVERT", "REROUTE")


class E2SemanticValidator(SemanticValidator):
    def __init__(self, resource_compat_path: str,
                 zone_geometries: Optional[Dict[str, Dict[str, Any]]] = None):
        super().__init__(resource_compat_path)
        self.zone_geometries = zone_geometries or {}
        self.facilities_coords: Dict[str, tuple] = {}

    def set_facilities(self, facilities: Dict[str, Any]) -> None:
        self.facilities_coords = {
            name: (float(f["lat"]), float(f["lon"]))
            for name, f in facilities.items()
            if f.get("lat") is not None and f.get("lon") is not None}

    # ------------------------------------------------------------------
    def validate(self, action: Dict[str, Any], global_state: Dict[str, Any]) -> Dict[str, Any]:
        base = super().validate(action, global_state)
        errors: List[str] = list(base["error_types"])
        atype = (action.get("type") or "").upper()
        acid = action.get("aircraft_id")
        mid = action.get("mission_id")
        air = {a["id"]: a for a in global_state.get("air", [])}
        missions = self._all_missions(global_state)

        zones = self._active_zones(global_state)

        # GNSS + risk-zone checks on the referenced aircraft
        if acid and acid in air:
            a = air[acid]
            if a.get("gnss_status") == "DEGRADED":
                errors.append("GNSS_DEGRADED_AIRCRAFT")
            if a.get("status") == "DEGRADED":
                errors.append("AIRCRAFT_DEGRADED")
            if atype in AIR_MISSION_ACTIONS:
                pos = a.get("position") or {}
                lat, lon = pos.get("lat"), pos.get("lon")
                if lat is not None and lon is not None:
                    if any(point_in_zone(float(lat), float(lon), z) for z in zones):
                        errors.append("RISK_ZONE_VIOLATION")
                route = action.get("route") or []
                if route and not any(e == "RISK_ZONE_VIOLATION" for e in errors):
                    pts: List[tuple] = []
                    if lat is not None and lon is not None:
                        pts.append((float(lat), float(lon)))
                    for wpt in route:
                        c = self.facilities_coords.get(wpt)
                        if c is not None:
                            pts.append(c)
                    for z in zones:
                        if route_intersects_zone(pts, z):
                            errors.append("RISK_ZONE_VIOLATION")
                            break

        # UTM prohibition
        if atype in AIR_MISSION_ACTIONS:
            utm = global_state.get("infrastructure", {}).get("utm_state", "NOMINAL")
            if utm == "OUTAGE":
                errors.append("UTM_AIR_PROHIBITED")
            elif utm == "DEGRADED" and mid and mid in missions:
                m = missions[mid]
                is_new = any(x.get("id") == mid
                             for x in global_state.get("missions", {}).get("new", []))
                if is_new and m.get("priority") != "CRITICAL":
                    errors.append("UTM_AIR_PROHIBITED")

        return {"valid": len(errors) == 0, "error_types": errors,
                "violations": errors}

    def _active_zones(self, gs: Dict[str, Any]) -> List[Dict[str, Any]]:
        zones: List[Dict[str, Any]] = []
        for fz in gs.get("infrastructure", {}).get("failure_zones", []):
            if fz.get("state") != "CLOSED":
                continue
            geom = self.zone_geometries.get(fz.get("id"))
            if geom is not None and geom.get("candidate_rule", "full") != "none":
                zones.append(dict(geom))
        return zones
