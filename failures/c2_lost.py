"""C2 Lost Link failure (F1) + manager-independent Local Contingency.

Research definition of a C2 Lost Link (F1):

    aircraft.c2_status      = LOST
    aircraft.status         = CONTINGENCY
    aircraft.reassignable   = false
    aircraft.commandable    = false
    current mission (EN_ROUTE) -> INTERRUPTED -> NEEDS_REPLAN

The local contingency executes IMMEDIATELY and does NOT wait for, and is NOT
controlled by, the Rule Manager, the LLM, or the global planner.  It is the
aircraft's own pre-programmed behaviour.

Local contingency mode selection (Phase 2): **RETURN** — the lost-link UAV
autonomously returns to its pre-programmed safe landing site (V3 backup site).
Rationale: standard civil-UAS lost-link behaviour (RTB); it keeps the aircraft
inside the monitored volume and frees it from the interrupted mission without
any ground-control input, while a medical/logistics UAV carrying (or that had
been carrying) cargo lands safely at a known recovery point so a backup can take
over.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class C2LostLink:
    """Applies the C2 Lost Link state mutation to an aircraft + its mission."""

    def __init__(self, config: Dict[str, Any]):
        c2 = config.get("phase2", {}).get("c2_lost", {})
        self.contingency_site = c2.get("contingency_site", "V3")
        self.contingency_mode = c2.get("contingency_mode", "RETURN")
        self.contingency_reason = c2.get("contingency_reason",
                                         "standard lost-link return-to-base")

    def trigger(self, aircraft, mission=None) -> Dict[str, Any]:
        """Mutate aircraft + mission per the F1 definition.

        Returns a plain dict describing the change (for deterministic event
        logging).  No simulator or manager interaction happens here.
        """
        old_status = aircraft.status
        aircraft.c2_status = "LOST"
        aircraft.commandable = False
        aircraft.reassignable = False
        aircraft.contingency_mode = self.contingency_mode

        # BUSY -> CONTINGENCY (the in-flight lost-link transition)
        aircraft.transition("CONTINGENCY")

        mission_change = None
        if mission is not None:
            old_m = mission.status
            if old_m == "EN_ROUTE":
                mission.transition("INTERRUPTED")
                mission.transition("NEEDS_REPLAN")
            elif old_m in ("INTERRUPTED", "NEEDS_REPLAN"):
                mission.transition("NEEDS_REPLAN")
            mission_change = {"from": old_m, "to": mission.status}

        return {
            "aircraft_id": aircraft.id,
            "old_status": old_status,
            "new_status": aircraft.status,
            "c2_status": aircraft.c2_status,
            "commandable": aircraft.commandable,
            "reassignable": aircraft.reassignable,
            "mission_id": mission.id if mission else None,
            "mission_change": mission_change,
            "contingency_mode": self.contingency_mode,
            "contingency_site": self.contingency_site,
        }

    def contingency_plan(self, aircraft) -> Dict[str, Any]:
        """The aircraft's own pre-programmed local contingency action."""
        return {
            "aircraft_id": aircraft.id,
            "mode": self.contingency_mode,       # RETURN (or LAND)
            "target_site": self.contingency_site,
            "reason": self.contingency_reason,
        }


class LocalContingency:
    """Encapsulates the autonomous contingency behaviour (no manager/LLM)."""

    def __init__(self, config: Dict[str, Any]):
        c2 = config.get("phase2", {}).get("c2_lost", {})
        self.contingency_site = c2.get("contingency_site", "V3")
        self.contingency_mode = c2.get("contingency_mode", "RETURN")

    def plan(self, aircraft_id: str) -> Dict[str, Any]:
        return {
            "aircraft_id": aircraft_id,
            "mode": self.contingency_mode,
            "target_site": self.contingency_site,
        }
