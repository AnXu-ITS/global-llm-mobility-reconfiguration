"""Experiment-2 feasibility-checker extension (E2-EXT-CHECK-1).

Subclasses the FROZEN FeasibilityChecker (safety/feasibility_checker.py,
untouched). After the frozen checks pass, manager-agnostic hard constraints are
added for the six failure families:

    GNSS_DEGRADED_AIRCRAFT   action on an aircraft with gnss_status DEGRADED
    AIRCRAFT_DEGRADED        action on an aircraft with status DEGRADED
    UTM_AIR_PROHIBITED       air mission action while UTM rules prohibit it
    RISK_ZONE_VIOLATION      aircraft position or route intersects an active
                             air risk zone

F1 (commandability / CONTINGENCY), F4 (site availability) and the battery /
endurance / compatibility gates remain covered by the frozen checker codes.
The checker never repairs a rejected action (frozen contract).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from failures.e2_failures import (point_in_zone, route_intersects_zone)
from safety.feasibility_checker import FeasibilityChecker

AIR_MISSION_ACTIONS = ("DISPATCH", "REASSIGN", "DIVERT", "REROUTE")


class E2FeasibilityChecker(FeasibilityChecker):
    def __init__(self, registry, config: Dict[str, Any]):
        super().__init__(registry, config)
        self.failure_state: Dict[str, Any] = {}

    def set_failure_state(self, fs: Dict[str, Any]) -> None:
        """Failure state set by the runner at injection time:
        {utm_state, new_mission_ids: set, zones: [geometry dicts active now]}."""
        self.failure_state = fs or {}

    # ------------------------------------------------------------------
    def check(self, action: Dict[str, Any]) -> Dict[str, Any]:
        base = super().check(action)
        v: List[str] = list(base["violations"])
        atype = (action.get("type") or "").upper()
        acid = action.get("aircraft_id")
        mid = action.get("mission_id")
        fs = self.failure_state

        # GNSS / degraded aircraft
        if acid and acid != "GROUND":
            ac = self.registry.aircraft.get(acid)
            if ac is not None:
                if getattr(ac, "gnss_status", "NORMAL") == "DEGRADED":
                    v.append("GNSS_DEGRADED_AIRCRAFT")
                if ac.status == "DEGRADED":
                    v.append("AIRCRAFT_DEGRADED")
                if atype in AIR_MISSION_ACTIONS:
                    pos = (ac.lat, ac.lon)
                    for z in fs.get("zones", []):
                        if point_in_zone(pos[0], pos[1], z):
                            v.append("RISK_ZONE_VIOLATION")
                            break
                    route = action.get("route") or []
                    if route:
                        pts: List[tuple] = [pos]
                        for wpt in route:
                            f = self.facilities.get(wpt)
                            if f is not None and f.get("lat") is not None:
                                pts.append((float(f["lat"]), float(f["lon"])))
                        for z in fs.get("zones", []):
                            if route_intersects_zone(pts, z):
                                v.append("RISK_ZONE_VIOLATION")
                                break

        # UTM prohibition (air mission actions only)
        if atype in AIR_MISSION_ACTIONS:
            utm = fs.get("utm_state", "NOMINAL")
            mission = self.registry.missions.get(mid)
            if utm == "OUTAGE":
                v.append("UTM_AIR_PROHIBITED")
            elif utm == "DEGRADED" and mission is not None:
                if mid in fs.get("new_mission_ids", set()) \
                        and mission.priority != "CRITICAL":
                    v.append("UTM_AIR_PROHIBITED")

        return {"valid": len(v) == 0, "violations": v}
