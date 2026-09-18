"""Safety / feasibility checker (spec 16). All actions pass through here."""
from __future__ import annotations

from typing import Any, Dict, List

from orchestrator.registry import Registry


class FeasibilityChecker:
    """Hard-constraint filter for manager actions.

    The checker answers "can it safely be done?"; it never silently fixes a
    rejected action -- infeasible actions are recorded as violations.
    """

    def __init__(self, registry: Registry, config: Dict[str, Any]):
        self.registry = registry
        self.config = config
        self.facilities = config["facilities"]

    def check(self, action: Dict[str, Any]) -> Dict[str, Any]:
        atype = action.get("type", "").upper()
        if atype in ("DISPATCH", "REASSIGN", "DIVERT", "REROUTE"):
            return self._check_air_mission_action(action, atype)
        if atype == "RESERVE":
            return self._check_reserve(action)
        if atype in ("RETURN", "LAND"):
            return self._check_aircraft_only(action)
        if atype == "CANCEL":
            return self._check_cancel(action)
        if atype == "GROUND_FALLBACK":
            return self._check_ground_fallback(action)
        if atype == "DELAY":
            return self._check_delay(action)
        # actions without an aircraft/mission target are trivially valid here
        # (NO_ACTION, ESCALATE)
        return {"valid": True, "violations": []}

    def _check_air_mission_action(self, action: Dict[str, Any], atype: str) -> Dict[str, Any]:
        v: List[str] = []
        ac = self.registry.aircraft.get(action.get("aircraft_id"))
        m = self.registry.missions.get(action.get("mission_id"))
        target_site = action.get("target_site")

        # aircraft feasibility
        if ac is None:
            v.append("AIRCRAFT_NOT_FOUND")
        else:
            # DISPATCH requires an AVAILABLE aircraft; REASSIGN may preempt a BUSY
            # aircraft only when it is explicitly reassignable (the SemanticValidator
            # enforces the no-equal/higher-priority preemption rule upstream).
            if atype == "DISPATCH" and ac.status != "AVAILABLE":
                v.append(f"AIRCRAFT_NOT_AVAILABLE_{ac.status}")
            if atype == "REASSIGN" and ac.status == "BUSY" and not ac.reassignable:
                v.append("AIRCRAFT_NOT_REASSIGNABLE")
            if not ac.commandable:
                v.append("AIRCRAFT_NOT_COMMANDABLE")
            if ac.status == "UNAVAILABLE":
                v.append("AIRCRAFT_UNAVAILABLE")
            if ac.status in ("CONTINGENCY",):
                v.append("AIRCRAFT_IN_CONTINGENCY")
            if ac.remaining_endurance_s <= 0:
                v.append("INSUFFICIENT_ENDURANCE")
            elif ac.remaining_endurance_s < 300:
                v.append("LOW_ENDURANCE_WARNING")

        # mission feasibility
        if m is None:
            v.append("MISSION_NOT_FOUND")
        else:
            if m.status == "COMPLETED":
                v.append("MISSION_ALREADY_COMPLETED")
            if m.status == "CANCELLED":
                v.append("MISSION_ALREADY_CANCELLED")

        # duplicate assignment: only when the current holder is still active
        if m is not None and m.assigned_resource is not None and m.assigned_resource != action.get("aircraft_id"):
            current = self.registry.aircraft.get(m.assigned_resource)
            if current is not None and current.status not in ("UNAVAILABLE", "CONTINGENCY"):
                v.append("DUPLICATE_ASSIGNMENT")

        # infrastructure feasibility
        if target_site is not None:
            if target_site not in self.facilities:
                v.append("SITE_NOT_FOUND")
            else:
                if self.facilities[target_site].get("available", True) is False:
                    v.append(f"{target_site}_UNAVAILABLE")
            if ac is not None and target_site not in ac.landing_site_compatibility:
                v.append("SITE_INCOMPATIBLE_WITH_AIRCRAFT")

        # battery gate (T8): must reject a UAV with insufficient battery
        if ac is not None and ac.battery_pct is not None and ac.battery_pct <= 0:
            v.append("INSUFFICIENT_BATTERY")

        return {"valid": len(v) == 0, "violations": v}

    def _check_reserve(self, action: Dict[str, Any]) -> Dict[str, Any]:
        v = []
        ac = self.registry.aircraft.get(action.get("aircraft_id"))
        if ac is None:
            v.append("AIRCRAFT_NOT_FOUND")
        elif ac.status != "AVAILABLE":
            v.append("AIRCRAFT_NOT_AVAILABLE")
        return {"valid": len(v) == 0, "violations": v}

    def _check_aircraft_only(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """RESERVE / RETURN / LAND: reference a real, commandable aircraft."""
        v = []
        ac = self.registry.aircraft.get(action.get("aircraft_id"))
        if ac is None:
            v.append("AIRCRAFT_NOT_FOUND")
        else:
            if ac.status == "UNAVAILABLE":
                v.append("AIRCRAFT_UNAVAILABLE")
            if ac.status == "CONTINGENCY":
                v.append("AIRCRAFT_IN_CONTINGENCY")
            if not ac.commandable:
                v.append("AIRCRAFT_NOT_COMMANDABLE")
        return {"valid": len(v) == 0, "violations": v}

    def _check_cancel(self, action: Dict[str, Any]) -> Dict[str, Any]:
        v = []
        m = self.registry.missions.get(action.get("mission_id"))
        if m is None:
            v.append("MISSION_NOT_FOUND")
        elif m.status in ("COMPLETED", "CANCELLED", "FAILED"):
            v.append("MISSION_TERMINAL")
        return {"valid": len(v) == 0, "violations": v}

    def _check_ground_fallback(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Ground fallback: route the mission by ground instead of air.

        Valid iff the mission exists, is not terminal, and explicitly allows a
        ground fallback.
        """
        v = []
        m = self.registry.missions.get(action.get("mission_id"))
        if m is None:
            v.append("MISSION_NOT_FOUND")
        else:
            if m.status in ("COMPLETED", "CANCELLED", "FAILED"):
                v.append("MISSION_TERMINAL")
            if not m.ground_fallback:
                v.append("GROUND_FALLBACK_NOT_ALLOWED")
        return {"valid": len(v) == 0, "violations": v}

    def _check_delay(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Delay: park the mission for a later re-evaluation.

        Valid iff the mission exists and is not terminal.
        """
        v = []
        m = self.registry.missions.get(action.get("mission_id"))
        if m is None:
            v.append("MISSION_NOT_FOUND")
        elif m.status in ("COMPLETED", "CANCELLED", "FAILED"):
            v.append("MISSION_TERMINAL")
        return {"valid": len(v) == 0, "violations": v}
