"""Shared Semantic Validator (Phase 3).

Validates a ManagerAction against the Global State snapshot BEFORE the
FeasibilityChecker.  It is manager-agnostic: both the Rule-Based Manager and the
LLM Manager pass their actions through here, so resource compatibility and
reference sanity never depend on the manager type.

Checks (error types mirror the Phase-3 contract):
    UNKNOWN_RESOURCE      aircraft_id not present in the Global State
    UNKNOWN_MISSION       mission_id not present in the Global State
    RESOURCE_INCOMPATIBLE aircraft type <-> mission type denied / conditional
                          whose condition is not satisfied
    DUPLICATE_ASSIGNMENT  mission already held by a different active aircraft
    PRIORITY_VIOLATION    action would preempt an equal/higher-priority mission

A clean action yields error_types == [] (equivalent to VALID_ACTION).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import yaml

PRIORITY_ORDER = {"LOW": 1, "NORMAL": 2, "HIGH": 3, "CRITICAL": 4}

# actions that bind an aircraft to a mission
AIR_MISSION_ACTIONS = ("DISPATCH", "REASSIGN", "DIVERT", "REROUTE")
# actions that reference an aircraft
AIRCRAFT_ACTIONS = ("DISPATCH", "REASSIGN", "DIVERT", "REROUTE",
                    "RESERVE", "RETURN", "LAND")
# actions that reference a mission
MISSION_ACTIONS = ("DISPATCH", "REASSIGN", "DIVERT", "REROUTE",
                   "DELAY", "CANCEL", "GROUND_FALLBACK")

RESERVE_MISSION_STATES = ("WAITING", "NEEDS_REPLAN", "INTERRUPTED")
RESERVE_MIN_PRIORITY = "HIGH"


class SemanticValidator:
    def __init__(self, resource_compat_path: str):
        with open(resource_compat_path, encoding="utf-8") as f:
            self.compat = yaml.safe_load(f)
        self.matrix = self.compat.get("aircraft_types", {})

    # ------------------------------------------------------------------
    def validate(self, action: Dict[str, Any], global_state: Dict[str, Any]) -> Dict[str, Any]:
        errors: List[str] = []
        air = {a["id"]: a for a in global_state.get("air", [])}
        missions = self._all_missions(global_state)

        atype = (action.get("type") or "").upper()
        acid = action.get("aircraft_id")
        mid = action.get("mission_id")

        # 1. unknown resource
        if acid and acid != "GROUND" and acid not in air:
            errors.append("UNKNOWN_RESOURCE")

        # 2. unknown mission
        if mid and mid not in missions:
            errors.append("UNKNOWN_MISSION")

        # 3. resource compatibility (aircraft bound to a mission)
        if atype in AIR_MISSION_ACTIONS and acid and acid in air and mid and mid in missions:
            ac, m = air[acid], missions[mid]
            verdict = self._verdict(ac.get("type"), m.get("type"))
            if verdict == "denied":
                errors.append("RESOURCE_INCOMPATIBLE")
            elif verdict == "conditional" and not self._conditional_ok(
                    ac.get("type"), m.get("type"), air, missions):
                errors.append("RESOURCE_INCOMPATIBLE")

        # 4. duplicate assignment
        if atype in ("DISPATCH", "REASSIGN", "DIVERT") and mid and mid in missions:
            m = missions[mid]
            holder = m.get("assigned_resource")
            if holder and holder != acid:
                h = air.get(holder)
                if h is not None and h.get("status") not in ("UNAVAILABLE", "CONTINGENCY"):
                    errors.append("DUPLICATE_ASSIGNMENT")

        # 5. priority violation (preempting an equal/higher-priority mission)
        if atype in ("REASSIGN", "DIVERT", "REROUTE") and acid and acid in air \
                and mid and mid in missions:
            ac, m = air[acid], missions[mid]
            if ac.get("status") in ("BUSY", "RESERVED") and ac.get("current_mission"):
                cur = missions.get(ac["current_mission"])
                if cur is not None:
                    cur_pri = PRIORITY_ORDER.get(cur.get("priority", "NORMAL"), 2)
                    tgt_pri = PRIORITY_ORDER.get(m.get("priority", "NORMAL"), 2)
                    if tgt_pri <= cur_pri:
                        errors.append("PRIORITY_VIOLATION")

        # 6. target landing site unavailable (from Global State infrastructure)
        target = action.get("target_site")
        if target and atype in AIR_MISSION_ACTIONS:
            sites = global_state.get("infrastructure", {}).get("landing_sites", {})
            if target in sites and sites[target].get("state") == "UNAVAILABLE":
                errors.append("SITE_UNAVAILABLE")

        return {"valid": len(errors) == 0, "error_types": errors,
                "violations": errors}

    # ------------------------------------------------------------------
    @staticmethod
    def _all_missions(gs: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for bucket in ("new", "existing"):
            for m in gs.get("missions", {}).get(bucket, []):
                out[m["id"]] = m
        return out

    def _verdict(self, aircraft_type: Optional[str], mission_type: Optional[str]) -> str:
        if not aircraft_type or not mission_type:
            return "denied"
        row = self.matrix.get(aircraft_type, {})
        return row.get(mission_type, "denied")

    def _conditional_ok(self, aircraft_type: str, mission_type: str,
                        air: Dict[str, Any], missions: Dict[str, Any]) -> bool:
        """Evaluate the condition attached to a `conditional` verdict."""
        # medical UAV taking a non-medical (logistics) mission: strategic reserve.
        if aircraft_type == "medical_uav" and mission_type in ("logistics",):
            return self._strategic_reserve_ok(missions)
        # non-medical airframe taking a medical mission: allowed only when no
        # AVAILABLE medical UAV exists.
        if aircraft_type in ("logistics_uav", "passenger_evtol") and mission_type.startswith("medical"):
            return not self._has_available_medical_uav(air)
        return True

    @staticmethod
    def _strategic_reserve_ok(missions: Dict[str, Any]) -> bool:
        """True when no HIGH/CRITICAL medical mission is still unresolved."""
        for m in missions.values():
            if str(m.get("type", "")).startswith("medical") \
                    and m.get("priority") in (RESERVE_MIN_PRIORITY, "CRITICAL") \
                    and m.get("state") in RESERVE_MISSION_STATES:
                return False
        return True

    @staticmethod
    def _has_available_medical_uav(air: Dict[str, Any]) -> bool:
        return any(a.get("type") == "medical_uav" and a.get("status") == "AVAILABLE"
                   for a in air.values())
