"""Shared CandidateEvaluator (Experiment-1 Finalization, manager-agnostic).

Computes one identical derived candidate table for EVERY manager (B0/B1/B2/B4a/
B4b) so that no manager holds private physical/cost information.  The table is a
PURE function of the Global State + deterministic candidate evaluation: it is
produced by the Candidate Generator (this module) BEFORE any manager runs and
does NOT depend on any manager's decision policy or objective weights.

For the highest-priority actionable mission it exposes, per resource (air +
ground):

  - resource_id            candidate resource (aircraft id, or "GROUND")
  - mode                   "AIR" | "GROUND" (transport mode of the candidate)
  - type                   same as mode (kept for backward-compatible readers)
  - action_type            the legal action this candidate implies
                           (DISPATCH / REASSIGN / GROUND_FALLBACK)
  - legal                  legality after the deterministic candidate filter
  - reject_reason          why an illegal candidate was filtered out (or None)
  - eta_s                  remaining duration (s) from now to task completion
  - completion_time_s      absolute simulation time of completion (now + eta_s)
  - route                  ordered landing-site waypoints
  - predicted_deadline_violation_s   signed seconds (negative = meets deadline)
  - preempted_mission_id / preempted_mission_priority   the mission a REASSIGN
                           would preempt (id + priority), or None
  - battery_pct            aircraft battery level (air only)
  - endurance_margin_s     aircraft remaining endurance (s) (air only)
  - destination_available  whether the mission destination landing site is
                           AVAILABLE (air only)
  - landing_compatible     whether the aircraft can land at the destination
                           (air only)
  - service_loss_estimate  deterministic interruption estimate
                           {interrupts_existing_mission, interrupted_mission_id,
                            interrupted_mission_priority}

It reuses the Rule manager's exact ETA model (ROLE_CRUISE_MS + haversine +
dispatch overhead + endurance margin), so B1/B2 and the shared table agree to
the second.  Deterministic: same GS -> same table.

LEAKAGE CONTRACT (Experiment-1 Finalization §2): this table contains NO
optimizer scalar (B2 objective J), no ranking, no "best candidate", no
"recommended action", no shadow price, and no field whose value depends on the
B2 objective weights.  See reports/experiment1_final/CANDIDATE_TABLE_FAIRNESS_AUDIT.md.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from orchestrator.fleet import ROLE_CRUISE_MS
from orchestrator.geo import haversine

CANDIDATE_TABLE_VERSION = "2.0.0"

PRIORITY_ORDER = {"LOW": 1, "NORMAL": 2, "HIGH": 3, "CRITICAL": 4}
ENDURANCE_MARGIN_S = 60.0
ACTIONABLE_STATES = ("WAITING", "NEEDS_REPLAN", "INTERRUPTED")


def _r(x: Optional[float], nd: int = 3) -> Optional[float]:
    return None if x is None else round(float(x), nd)


def _destination_available(gs: Dict[str, Any], dest: Optional[str]) -> Optional[bool]:
    """Explicit destination landing-site availability (None when no destination)."""
    if not dest:
        return None
    site = gs.get("infrastructure", {}).get("landing_sites", {}).get(dest)
    if site is None:
        return None
    return bool(site.get("state") == "AVAILABLE")


class CandidateEvaluator:
    def __init__(self, facilities: Dict[str, Any],
                 dispatch_overhead_s: float = 0.0,
                 contingency_site: str = "V3"):
        self.facilities = facilities
        self.dispatch_overhead_s = float(dispatch_overhead_s)
        self.contingency_site = contingency_site

    # ------------------------------------------------------------------
    # target mission (same ranking as the Rule manager rule 1)
    # ------------------------------------------------------------------
    def target_mission(self, gs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        actionable: List[Dict[str, Any]] = []
        for bucket in ("new", "existing"):
            for m in gs.get("missions", {}).get(bucket, []):
                if m.get("state") in ACTIONABLE_STATES:
                    actionable.append(m)
        if not actionable:
            return None
        actionable.sort(key=lambda m: (
            -PRIORITY_ORDER.get(m.get("priority", "LOW"), 1),
            m.get("deadline_s") if m.get("deadline_s") is not None else 1e18))
        return actionable[0]

    # ------------------------------------------------------------------
    # full candidate table
    # ------------------------------------------------------------------
    def evaluate(self, gs: Dict[str, Any]) -> Dict[str, Any]:
        target = self.target_mission(gs)
        t = int(gs.get("simulation_time", 0))
        slack = None
        if target is not None and target.get("deadline_s") is not None:
            slack = float(target["deadline_s"]) - float(t)

        air: List[Dict[str, Any]] = []
        if target is not None:
            for ac in gs.get("air", []):
                air.append(self._air_candidate(gs, ac, target, slack))
        ground = self._ground_candidate(gs, target, slack)

        summary = {
            "candidate_table_version": CANDIDATE_TABLE_VERSION,
            "simulation_time": t,
            "target_mission_id": target.get("id") if target else None,
            "target_mission_priority": target.get("priority") if target else None,
            "target_mission_origin": target.get("origin") if target else None,
            "target_mission_destination": target.get("destination") if target else None,
            "deadline_slack_s": _r(slack),
            "cruise_speed_ms": {k: round(float(v), 2) for k, v in ROLE_CRUISE_MS.items()},
            "dispatch_overhead_s": _r(self.dispatch_overhead_s),
            "endurance_margin_s": _r(ENDURANCE_MARGIN_S),
        }
        return {"summary": summary, "air": air, "ground": ground}

    # ------------------------------------------------------------------
    # air candidates (same filter as RuleBasedManager._reject_air)
    # ------------------------------------------------------------------
    def _air_candidate(self, gs: Dict[str, Any], ac: Dict[str, Any],
                       mission: Dict[str, Any], slack: Optional[float]) -> Dict[str, Any]:
        t = int(gs.get("simulation_time", 0))
        dest = mission.get("destination")
        cand: Dict[str, Any] = {
            "resource_id": ac["id"],
            "mode": "AIR",
            "type": "AIR",
            "action_type": None,
            "legal": False,
            "reject_reason": None,
            "eta_s": None,
            "completion_time_s": None,
            "route": None,
            "predicted_deadline_violation_s": None,
            "preempted_mission_id": None,
            "preempted_mission_priority": None,
            "battery_pct": _r(ac.get("battery_pct")),
            "endurance_margin_s": _r(ac.get("remaining_endurance_s", 0)),
            "destination_available": _destination_available(gs, dest),
            "landing_compatible": bool(dest in ac.get("landing_compatibility", [])),
            "service_loss_estimate": {
                "interrupts_existing_mission": False,
                "interrupted_mission_id": None,
                "interrupted_mission_priority": None,
            },
        }
        rr = self._reject_air(ac, mission, gs)
        if rr is not None:
            cand["reject_reason"] = rr
            return cand

        route = self._air_route(ac, mission)
        eta = self._air_eta(ac, route)
        cand["eta_s"] = _r(eta)
        cand["completion_time_s"] = _r(t + eta)
        cand["route"] = route
        status = ac.get("status")
        cand["action_type"] = ("REASSIGN" if status in ("BUSY", "RESERVED")
                               or mission.get("state") in ("INTERRUPTED", "NEEDS_REPLAN")
                               else "DISPATCH")
        if status in ("BUSY", "RESERVED"):
            cand["preempted_mission_id"] = ac.get("current_mission")
            cand["preempted_mission_priority"] = ac.get("mission_priority")
            cand["service_loss_estimate"] = {
                "interrupts_existing_mission": True,
                "interrupted_mission_id": ac.get("current_mission"),
                "interrupted_mission_priority": ac.get("mission_priority"),
            }

        # endurance headroom (same gate as the Rule manager rule 4)
        if ac.get("remaining_endurance_s", 0) < eta + ENDURANCE_MARGIN_S:
            cand["reject_reason"] = (
                f"insufficient endurance ({ac.get('remaining_endurance_s')}s < "
                f"{round(eta + ENDURANCE_MARGIN_S, 1)}s required)")
        else:
            cand["legal"] = True

        if slack is not None and eta is not None:
            cand["predicted_deadline_violation_s"] = _r(eta - slack)
        return cand

    def _reject_air(self, ac: Dict[str, Any], mission: Dict[str, Any],
                    gs: Dict[str, Any]) -> Optional[str]:
        if ac.get("c2_status") != "NORMAL":
            return f"C2 status {ac.get('c2_status')} (not commandable)"
        if ac.get("commandable") is False:
            return "not commandable"
        status = ac.get("status")
        if status in ("UNAVAILABLE", "CONTINGENCY", "DEGRADED"):
            return f"aircraft {status}"
        if status in ("BUSY", "RESERVED"):
            if ac.get("reassignable") is False:
                return "busy non-reassignable"
            cur_pri = PRIORITY_ORDER.get(ac.get("mission_priority", "LOW"), 1)
            tgt_pri = PRIORITY_ORDER.get(mission.get("priority", "LOW"), 1)
            if tgt_pri <= cur_pri:
                return (f"would preempt {'higher' if cur_pri > tgt_pri else 'equal'} "
                        f"priority mission {ac.get('current_mission')}")
        if ac.get("battery_pct") is not None and ac.get("battery_pct") <= 0:
            return "insufficient battery"
        if ac.get("remaining_endurance_s", 0) <= 0:
            return "insufficient endurance"
        dest = mission.get("destination")
        if dest:
            site = gs.get("infrastructure", {}).get("landing_sites", {}).get(dest)
            if site is not None and site.get("state") != "AVAILABLE":
                return f"landing site {dest} {site.get('state')} (unavailable)"
            if dest not in ac.get("landing_compatibility", []):
                return f"landing site {dest} incompatible"
        return None

    def _air_route(self, ac: Dict[str, Any], mission: Dict[str, Any]) -> List[str]:
        dest = mission["destination"]
        status = mission.get("state")
        if status in ("INTERRUPTED", "NEEDS_REPLAN"):
            if self.contingency_site != dest:
                return [self.contingency_site, dest]
            return [dest]
        return [mission.get("origin", dest), dest]

    def _air_eta(self, ac: Dict[str, Any], route: List[str]) -> float:
        speed = ROLE_CRUISE_MS.get(ac.get("type"), 15.0)
        pos = ac.get("position", {})
        lat, lon = pos.get("lat"), pos.get("lon")
        total = 0.0
        if lat is not None and lon is not None and route:
            first = self.facilities[route[0]]
            total += haversine(lat, lon, first["lat"], first["lon"])
        for a, b in zip(route, route[1:]):
            fa, fb = self.facilities[a], self.facilities[b]
            total += haversine(fa["lat"], fa["lon"], fb["lat"], fb["lon"])
        return total / max(speed, 1e-6) + self.dispatch_overhead_s

    # ------------------------------------------------------------------
    # ground candidate
    # ------------------------------------------------------------------
    def _ground_candidate(self, gs: Dict[str, Any], mission: Optional[Dict[str, Any]],
                          slack: Optional[float]) -> Dict[str, Any]:
        t = int(gs.get("simulation_time", 0))
        ground = gs.get("ground", {})
        allowed = bool(mission.get("ground_fallback", True)) if mission else False
        eta = ground.get("ground_fallback_eta_s") or ground.get("current_d1_h1_eta_s")
        feasible = bool(allowed and eta is not None)
        cand: Dict[str, Any] = {
            "resource_id": "GROUND",
            "mode": "GROUND",
            "type": "GROUND",
            "action_type": "GROUND_FALLBACK",
            "legal": feasible,
            "reject_reason": None if feasible else
            ("ground fallback disabled" if not allowed else "no ground route ETA"),
            "eta_s": _r(eta),
            "completion_time_s": _r(t + eta) if eta is not None else None,
            "route": None,
            "predicted_deadline_violation_s": None,
            "preempted_mission_id": None,
            "preempted_mission_priority": None,
            "battery_pct": None,
            "endurance_margin_s": None,
            "destination_available": None,
            "landing_compatible": None,
            "service_loss_estimate": {
                "interrupts_existing_mission": False,
                "interrupted_mission_id": None,
                "interrupted_mission_priority": None,
            },
        }
        if feasible and eta is not None and slack is not None:
            cand["predicted_deadline_violation_s"] = _r(eta - slack)
        return cand
