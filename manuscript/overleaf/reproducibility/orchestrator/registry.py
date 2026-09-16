"""Aircraft and mission registries with validated state machines (spec 9 & 10)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]

AIRCRAFT_STATES = ["AVAILABLE", "BUSY", "RESERVED", "DEGRADED",
                   "CONTINGENCY", "UNAVAILABLE", "RECOVERED"]

AIRCRAFT_TRANSITIONS = {
    "AVAILABLE": {"BUSY", "RESERVED"},
    "BUSY": {"AVAILABLE", "DEGRADED", "CONTINGENCY"},
    "RESERVED": {"AVAILABLE", "BUSY"},
    "DEGRADED": {"CONTINGENCY", "AVAILABLE"},
    "CONTINGENCY": {"UNAVAILABLE", "RECOVERED"},
    "UNAVAILABLE": set(),
    "RECOVERED": {"AVAILABLE"},
}

MISSION_STATES = ["WAITING", "ASSIGNED", "EN_ROUTE", "INTERRUPTED",
                  "NEEDS_REPLAN", "REASSIGNED", "COMPLETED", "CANCELLED", "FAILED"]

MISSION_TRANSITIONS = {
    "WAITING": {"ASSIGNED"},
    "ASSIGNED": {"EN_ROUTE", "CANCELLED"},
    "EN_ROUTE": {"COMPLETED", "INTERRUPTED", "NEEDS_REPLAN", "CANCELLED"},
    "INTERRUPTED": {"NEEDS_REPLAN", "REASSIGNED", "CANCELLED", "FAILED"},
    "NEEDS_REPLAN": {"REASSIGNED", "CANCELLED", "FAILED"},
    "REASSIGNED": {"EN_ROUTE"},
    "COMPLETED": set(),
    "CANCELLED": set(),
    "FAILED": set(),
}


class StateMachineError(Exception):
    pass


class Aircraft:
    def __init__(self, aircraft_id: str, type_: str, lat: float, lon: float, **kw):
        self.id = aircraft_id
        self.type = type_
        self.status = kw.get("status", "AVAILABLE")
        self.mission_id: Optional[str] = kw.get("mission_id")
        self.priority = kw.get("priority", "NORMAL")
        self.lat = lat
        self.lon = lon
        self.battery_pct = kw.get("battery_pct", 100)
        self.remaining_endurance_s = kw.get("remaining_endurance_s", 1800)
        self.reassignable = kw.get("reassignable", True)
        self.landing_site_compatibility = kw.get("landing_site_compatibility", ["V1", "V2", "V3"])
        self.c2_status = kw.get("c2_status", "NORMAL")
        self.gnss_status = kw.get("gnss_status", "NORMAL")
        self.utm_status = kw.get("utm_status", "NORMAL")
        self.contingency_mode = kw.get("contingency_mode", "NONE")
        self.commandable = kw.get("commandable", True)

    def transition(self, new_status: str) -> None:
        if new_status not in AIRCRAFT_STATES:
            raise StateMachineError(f"unknown aircraft status {new_status}")
        if new_status not in AIRCRAFT_TRANSITIONS.get(self.status, set()):
            raise StateMachineError(f"illegal aircraft transition {self.status}->{new_status}")
        self.status = new_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aircraft_id": self.id, "type": self.type, "status": self.status,
            "mission_id": self.mission_id, "priority": self.priority,
            "lat": self.lat, "lon": self.lon, "battery_pct": self.battery_pct,
            "remaining_endurance_s": self.remaining_endurance_s,
            "reassignable": self.reassignable,
            "landing_site_compatibility": self.landing_site_compatibility,
            "c2_status": self.c2_status, "gnss_status": self.gnss_status,
            "utm_status": self.utm_status, "contingency_mode": self.contingency_mode,
        }


class Mission:
    def __init__(self, mission_id: str, type_: str, priority: str, origin: str,
                 destination: str, deadline_s: float, **kw):
        self.id = mission_id
        self.type = type_
        self.priority = priority
        self.origin = origin
        self.destination = destination
        self.deadline_s = deadline_s
        self.assigned_resource: Optional[str] = kw.get("assigned_resource")
        self.mode = kw.get("mode")  # AIR or GROUND
        self.status = kw.get("status", "WAITING")
        self.ground_fallback = kw.get("ground_fallback", True)
        self.delay_cost = kw.get("delay_cost", 10.0)
        self.cancellation_cost = kw.get("cancellation_cost", 100.0)

    def transition(self, new_status: str) -> None:
        if new_status not in MISSION_STATES:
            raise StateMachineError(f"unknown mission status {new_status}")
        if new_status not in MISSION_TRANSITIONS.get(self.status, set()):
            raise StateMachineError(f"illegal mission transition {self.status}->{new_status}")
        self.status = new_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.id, "type": self.type, "priority": self.priority,
            "origin": self.origin, "destination": self.destination,
            "deadline_s": self.deadline_s, "assigned_resource": self.assigned_resource,
            "mode": self.mode, "status": self.status, "ground_fallback": self.ground_fallback,
            "delay_cost": self.delay_cost, "cancellation_cost": self.cancellation_cost,
        }


class Registry:
    def __init__(self):
        self.aircraft: Dict[str, Aircraft] = {}
        self.missions: Dict[str, Mission] = {}

    def add_aircraft(self, ac: Aircraft) -> None:
        self.aircraft[ac.id] = ac

    def add_mission(self, m: Mission) -> None:
        self.missions[m.id] = m

    def assign(self, acid: str, mission_id: str) -> None:
        ac = self.aircraft[acid]
        m = self.missions[mission_id]
        ac.transition("BUSY")
        ac.mission_id = mission_id
        ac.priority = m.priority
        m.assigned_resource = acid
        m.mode = "AIR"
        m.transition("ASSIGNED")

    def en_route(self, mission_id: str) -> None:
        self.missions[mission_id].transition("EN_ROUTE")

    def reassign(self, acid: str, mission_id: str) -> None:
        """Reassign a mission to an aircraft (C2 recovery or preemption).

        When the aircraft is BUSY on a DIFFERENT mission, that mission is
        detached and interrupted (preemption); the aircraft then takes over
        `mission_id`.
        """
        ac = self.aircraft[acid]
        m = self.missions[mission_id]
        # preemption: detach + interrupt the aircraft's current (different) mission
        if ac.status == "BUSY" and ac.mission_id and ac.mission_id != mission_id:
            old = self.missions.get(ac.mission_id)
            if old is not None and old.status not in ("COMPLETED", "CANCELLED", "FAILED"):
                old.transition("INTERRUPTED")
                old.assigned_resource = None
        # detach the prior (lost/inactive) holder of the target mission
        if m.assigned_resource and m.assigned_resource in self.aircraft:
            prior = self.aircraft[m.assigned_resource]
            if prior.mission_id == mission_id:
                prior.mission_id = None
        if ac.status != "BUSY":
            ac.transition("BUSY")
        ac.mission_id = mission_id
        ac.priority = m.priority
        m.assigned_resource = acid
        m.mode = "AIR"
        if m.status == "WAITING":
            m.transition("ASSIGNED")
        else:
            m.transition("REASSIGNED")
        m.transition("EN_ROUTE")

    def ground_fallback(self, mission_id: str) -> None:
        """Route a mission by ground (fallback) instead of air."""
        m = self.missions[mission_id]
        m.mode = "GROUND"
        m.assigned_resource = "GROUND"
        if m.status == "WAITING":
            m.transition("ASSIGNED")
            m.transition("EN_ROUTE")
        elif m.status in ("INTERRUPTED", "NEEDS_REPLAN"):
            m.transition("REASSIGNED")
            m.transition("EN_ROUTE")
        elif m.status == "ASSIGNED":
            m.transition("EN_ROUTE")

    def complete_ground_mission(self, mission_id: str) -> None:
        self.missions[mission_id].transition("COMPLETED")

    def complete_mission(self, mission_id: str) -> None:
        m = self.missions[mission_id]
        m.transition("COMPLETED")
        if m.assigned_resource:
            ac = self.aircraft[m.assigned_resource]
            ac.transition("AVAILABLE")
            ac.mission_id = None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "aircraft": [a.to_dict() for a in self.aircraft.values()],
            "missions": [m.to_dict() for m in self.missions.values()],
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.snapshot(), indent=2), encoding="utf-8")
