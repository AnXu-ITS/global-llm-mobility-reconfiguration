"""Deterministic Global State v1 builder.

Builds the single, fixed-schema snapshot a manager (rule-based now, LLM later)
sees.  The builder is a pure function of:

    (scenario config, registry, ground snapshot, air snapshot,
     infrastructure, events, ETA trend, injected-mission ids)

Determinism contract: for the same scenario + seed + simulation time the
serialised JSON is **byte-identical**.  This is achieved by (a) sorting all
collections by a stable key, (b) rounding every float to a fixed precision, and
(c) dumping with `sort_keys=True` and fixed separators.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set

SCHEMA_VERSION = "1.0.0"

# fixed float precisions (decimal places) used for canonical serialisation
P_LATLON = 7
P_METERS = 1
P_SECONDS = 3
P_PERCENT = 3


def _r(x: Optional[float], nd: int) -> Optional[float]:
    if x is None:
        return None
    return round(float(x), nd)


class GlobalStateBuilder:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.facilities = config["facilities"]
        self.b1_edge = config["sumo_mapping"]["B1"]["edge_id"]

    # ------------------------------------------------------------------
    # public build
    # ------------------------------------------------------------------
    def build(self, *, t: int, registry, ground: Dict[str, Any],
              air: Dict[str, Any], events: List[Dict[str, Any]],
              trend: Dict[str, Any], new_mission_ids: Set[str],
              failure_zones: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        gs: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "simulation_time": int(t),
            "scenario_id": self.config.get("scenario_id", "S0"),
            "scenario_version": self.config.get("scenario_version", "S0_3p2km_v1"),
            # FIX (review §6): the E1 runner sets the run seed in
            # phase2.schedule.seed, not the top-level schedule.seed, so the v1 GS
            # always reported the default 20240601.  Read the phase-2 seed with
            # a top-level fallback.
            "seed": ((self.config.get("phase2", {}) or {}).get("schedule", {}) or {}).get("seed")
                    or self.config.get("schedule", {}).get("seed"),
            "ground": self._build_ground(ground),
            "air": self._build_air(registry, air),
            "infrastructure": self._build_infrastructure(failure_zones),
            "missions": self._build_missions(registry, new_mission_ids),
            "events": self._build_events(events),
            "trend": self._build_trend(trend),
        }
        return gs

    # ------------------------------------------------------------------
    # sections
    # ------------------------------------------------------------------
    def _build_ground(self, ground: Dict[str, Any]) -> Dict[str, Any]:
        eta = ground.get("eta_d1_h1")
        baseline = ground.get("eta_baseline")
        inc = None
        if eta is not None and baseline:
            inc = 100.0 * (eta - baseline) / baseline
        # accessibility is DEGRADED on the B1 closure event (GD1), and/or on the
        # derived 2x-ETA threshold (GD3).
        degraded = bool(ground.get("b1_blocked")) or bool(ground.get("accessibility_degraded", False))
        fb_eta = ground.get("ground_fallback_eta_s") or eta
        return {
            "b1_state": "CLOSED" if ground.get("b1_blocked") else "OPEN",
            "current_d1_h1_eta_s": _r(eta, P_SECONDS),
            "baseline_eta_s": _r(baseline, P_SECONDS),
            "eta_increase_pct": _r(inc, P_PERCENT),
            "accessibility_status": "DEGRADED" if degraded else "NOMINAL",
            "available_ground_fallback": bool(ground.get("ground_fallback_available", True)),
            "ground_fallback_eta_s": _r(fb_eta, P_SECONDS),
        }

    def _build_air(self, registry, air: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for acid in sorted(registry.aircraft.keys()):
            ac = registry.aircraft[acid]
            st = air.get(acid, {})
            status = ac.status
            if status == "AVAILABLE":
                availability = "AVAILABLE"
            elif status == "BUSY" and ac.reassignable:
                availability = "REASSIGNABLE"
            elif status == "BUSY":
                availability = "BUSY"
            else:
                availability = "UNAVAILABLE"
            rows.append({
                "id": ac.id,
                "type": ac.type,
                "status": status,
                "position": {
                    "lat": _r(st.get("lat", ac.lat), P_LATLON),
                    "lon": _r(st.get("lon", ac.lon), P_LATLON),
                    "alt_m": _r(st.get("alt_m"), P_METERS),
                },
                "current_mission": ac.mission_id,
                "mission_priority": ac.priority,
                "battery_pct": _r(ac.battery_pct, P_PERCENT),
                "remaining_endurance_s": _r(ac.remaining_endurance_s, P_SECONDS),
                "availability": availability,
                "reassignable": bool(ac.reassignable),
                "commandable": bool(ac.commandable),
                "c2_status": ac.c2_status,
                "gnss_status": ac.gnss_status,
                "landing_compatibility": list(ac.landing_site_compatibility),
            })
        return rows

    def _build_infrastructure(self, failure_zones) -> Dict[str, Any]:
        sites: Dict[str, Any] = {}
        for name in sorted(self.facilities.keys()):
            f = self.facilities[name]
            if f.get("type") not in ("hospital_landing_site", "logistics_hub_landing_site",
                                     "backup_landing_site"):
                continue
            sites[name] = {
                "state": "AVAILABLE" if f.get("available", True) else "UNAVAILABLE",
                "lat": _r(f.get("lat"), P_LATLON),
                "lon": _r(f.get("lon"), P_LATLON),
            }
        zones = failure_zones if failure_zones is not None else self._default_failure_zones()
        zones = sorted(zones, key=lambda z: z.get("id", ""))
        return {
            "landing_sites": sites,
            "utm_state": "NOMINAL",
            "failure_zones": zones,
        }

    def _default_failure_zones(self) -> List[Dict[str, Any]]:
        b1 = self.config["facilities"]["B1"]
        return [{
            "id": "B1",
            "edge_id": self.b1_edge,
            "impact_level": b1.get("impact_level", "high"),
            "state": "CLOSED",
        }]

    def _build_missions(self, registry, new_mission_ids: Set[str]) -> Dict[str, Any]:
        existing: List[Dict[str, Any]] = []
        new: List[Dict[str, Any]] = []
        for mid in sorted(registry.missions.keys()):
            m = registry.missions[mid]
            row = self._mission_row(m)
            if mid in new_mission_ids:
                new.append(row)
            else:
                existing.append(row)
        return {"existing": existing, "new": new}

    @staticmethod
    def _mission_row(m) -> Dict[str, Any]:
        return {
            "id": m.id,
            "type": m.type,
            "priority": m.priority,
            "deadline_s": _r(m.deadline_s, P_SECONDS),
            "origin": m.origin,
            "destination": m.destination,
            "assigned_resource": m.assigned_resource,
            "mode": m.mode,
            "state": m.status,
            "ground_fallback": bool(m.ground_fallback),
            "delay_cost": _r(m.delay_cost, P_PERCENT),
            "cancellation_cost": _r(m.cancellation_cost, P_PERCENT),
        }

    @staticmethod
    def _build_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for ev in sorted(events, key=lambda e: (e.get("t", 0), e.get("event_id", ""))):
            rows.append({
                "t": int(ev.get("t", 0)),
                "event_id": ev.get("event_id"),
                "event_type": ev.get("event_type"),
                "payload": ev.get("payload"),
            })
        return rows

    @staticmethod
    def _build_trend(trend: Dict[str, Any]) -> Dict[str, Any]:
        prev = trend.get("previous_eta_s")
        cur = trend.get("current_eta_s")
        return {
            "previous_eta_s": _r(prev, P_SECONDS),
            "current_eta_s": _r(cur, P_SECONDS),
            "eta_trend": trend.get("eta_trend", "N/A"),
        }


def to_json(global_state: Dict[str, Any]) -> str:
    """Canonical, deterministic JSON serialisation of a Global State."""
    return json.dumps(global_state, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
