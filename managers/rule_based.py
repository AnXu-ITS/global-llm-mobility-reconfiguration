"""Formal Rule-Based Manager (B1) for Phase 2.

The manager is a pure decision function:

    Global State (dict)  ->  ManagerAction (dict)

It NEVER touches SUMO or BlueSky directly.  The orchestrator feeds it a Global
State snapshot, runs the returned action through the FeasibilityChecker, and
only then executes it against the simulators.

Ranking rules (strict, in order):
    1. mission priority: CRITICAL > HIGH > NORMAL > LOW
    2. a resource must be AVAILABLE, or explicitly reassignable (BUSY and
       preempting a strictly LOWER priority mission)
    3. never interrupt a HIGHER (or equal) priority mission for a lower one
    4. the candidate must satisfy the feasibility constraints (battery /
       endurance / C2 / commandability / landing compatibility)
    5. among feasible resources, pick the minimum estimated mission
       completion time
    6. tie -> pick the largest battery / endurance margin
    7. no feasible air resource -> ground fallback (when allowed)
    8. neither air nor ground feasible -> DELAY or CANCEL
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from orchestrator.fleet import ROLE_CRUISE_MS
from orchestrator.geo import haversine

PRIORITY_ORDER = {"LOW": 1, "NORMAL": 2, "HIGH": 3, "CRITICAL": 4}

# air resources require this endurance margin (s) beyond the estimated flight
# time before they are considered feasible (safety headroom for the flight).
ENDURANCE_MARGIN_S = 60.0

# mission states that require a manager decision (resource assignment/reconfig)
ACTIONABLE_STATES = ("WAITING", "NEEDS_REPLAN", "INTERRUPTED")


class RuleBasedManager:
    """Deterministic rule-based reconfiguration manager (B1)."""

    manager_kind = "rule_based"

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.facilities = config["facilities"]
        self.contingency_site = config.get("phase2", {}).get("c2_lost", {}).get(
            "contingency_site", "V3")
        self.dispatch_overhead_s = float(
            config.get("phase2", {}).get("manager", {}).get("dispatch_overhead_s", 0))
        self._decision_counter = 0

    # ------------------------------------------------------------------
    # public entry point
    # ------------------------------------------------------------------
    def decide(self, global_state: Dict[str, Any]) -> Dict[str, Any]:
        """Produce one ManagerAction for the highest-priority actionable mission.

        Experiment-1 Finalization §3/§17: when the shared candidate set is
        present in the Global State (injected by the Candidate Generator before
        any manager runs), B1 ranks over the SAME candidate fields the LLM (B4b)
        sees.  The legacy `_evaluate_air_candidates` path is kept only as a
        fallback for callers (unit tests) that do not attach a candidate table.
        """
        self._decision_counter += 1
        decision_id = f"D{self._decision_counter:03d}"
        t = global_state["simulation_time"]

        target = self._select_target_mission(global_state)
        if target is None:
            return self._noop(decision_id, t, global_state)

        shared = global_state.get("candidates")
        if shared is not None:
            return self._decide_from_shared(shared, target, t, decision_id, global_state)
        return self._decide_legacy(global_state, target, decision_id, t)

    def _decide_from_shared(self, shared: Dict[str, Any], target: Dict[str, Any],
                            t: int, decision_id: str,
                            global_state: Dict[str, Any]) -> Dict[str, Any]:
        """Rule ranking over the shared candidate table (manager-agnostic set)."""
        air = [c for c in shared.get("air", []) if c.get("legal")]
        # rule 5 (min completion time) + rule 6 (tie -> endurance margin)
        air.sort(key=lambda c: (c.get("eta_s") if c.get("eta_s") is not None
                                else float("inf"), -(c.get("endurance_margin_s") or 0.0)))

        if air:
            best = air[0]
            selected = {"resource": best["resource_id"], "type": "AIR",
                        "eta_s": best["eta_s"], "reject_reason": None}
            action = self._air_action_from_shared(best, target)
            reason = "minimum feasible estimated mission completion time"
        else:
            ground = shared.get("ground", {})
            if ground.get("legal"):
                selected = {"resource": "GROUND", "type": "GROUND",
                            "eta_s": ground.get("eta_s"), "reject_reason": None}
                action = {"type": "GROUND_FALLBACK", "mission_id": target["id"],
                          "ground_eta_s": ground.get("eta_s")}
                reason = "no feasible air resource; ground fallback available"
            elif target.get("deadline_s") is not None and target["deadline_s"] > t:
                selected = {"resource": None, "type": "DELAY", "eta_s": None,
                            "reject_reason": None}
                action = {"type": "DELAY", "mission_id": target["id"],
                          "reason": "no feasible air or ground resource; deadline not passed"}
                reason = "no feasible air/ground resource; deadline slack remains -> DELAY"
            else:
                selected = {"resource": None, "type": "CANCEL", "eta_s": None,
                            "reject_reason": None}
                action = {"type": "CANCEL", "mission_id": target["id"],
                          "reason": "no feasible air or ground resource and deadline passed"}
                reason = "no feasible air/ground resource; deadline passed -> CANCEL"

        return {
            "decision_id": decision_id,
            "simulation_time": t,
            "scenario_id": global_state.get("scenario_id"),
            "trigger": self._derive_trigger(global_state, target),
            "mission_id": target["id"],
            "mission_priority": target["priority"],
            "candidates": shared.get("air", []),
            "ground_candidate": shared.get("ground", {}),
            "selected": selected,
            "action": action,
            "reason": reason,
        }

    def _decide_legacy(self, global_state: Dict[str, Any], target: Dict[str, Any],
                       decision_id: str, t: int) -> Dict[str, Any]:
        """Original candidate evaluation path (fallback when no shared table)."""
        candidates = self._evaluate_air_candidates(global_state, target)
        feasible = [c for c in candidates if c["feasible"]]
        # rule 5 (min completion time) + rule 6 (tie -> endurance margin)
        feasible.sort(key=lambda c: (c["eta_s"], -c["endurance_margin_s"]))

        selected: Optional[Dict[str, Any]] = None
        action: Optional[Dict[str, Any]] = None
        reason = ""

        if feasible:
            best = feasible[0]
            selected = {"resource": best["resource_id"], "type": "AIR",
                        "eta_s": best["eta_s"], "reject_reason": None}
            action = self._air_action(best, target)
            reason = "minimum feasible estimated mission completion time"
        else:
            ground = self._evaluate_ground(global_state, target)
            if ground["feasible"]:
                selected = {"resource": "GROUND", "type": "GROUND",
                            "eta_s": ground["eta_s"], "reject_reason": None}
                action = {"type": "GROUND_FALLBACK", "mission_id": target["id"],
                          "ground_eta_s": ground["eta_s"]}
                reason = "no feasible air resource; ground fallback available"
            else:
                # rule 8: DELAY when deadline still in the future, else CANCEL
                if target.get("deadline_s") is not None and target["deadline_s"] > t:
                    selected = {"resource": None, "type": "DELAY", "eta_s": None,
                                "reject_reason": None}
                    action = {"type": "DELAY", "mission_id": target["id"],
                              "reason": "no feasible air or ground resource; deadline not passed"}
                    reason = "no feasible air/ground resource; deadline slack remains -> DELAY"
                else:
                    selected = {"resource": None, "type": "CANCEL", "eta_s": None,
                                "reject_reason": None}
                    action = {"type": "CANCEL", "mission_id": target["id"],
                              "reason": "no feasible air or ground resource and deadline passed"}
                    reason = "no feasible air/ground resource; deadline passed -> CANCEL"

        return {
            "decision_id": decision_id,
            "simulation_time": t,
            "scenario_id": global_state.get("scenario_id"),
            "trigger": self._derive_trigger(global_state, target),
            "mission_id": target["id"],
            "mission_priority": target["priority"],
            "candidates": candidates,
            "ground_candidate": self._evaluate_ground(global_state, target),
            "selected": selected,
            "action": action,
            "reason": reason,
        }

    # ------------------------------------------------------------------
    # target selection (rule 1)
    # ------------------------------------------------------------------
    def _select_target_mission(self, gs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        actionable = []
        for bucket in ("new", "existing"):
            for m in gs.get("missions", {}).get(bucket, []):
                if m.get("state") in ACTIONABLE_STATES:
                    actionable.append(m)
        if not actionable:
            return None
        actionable.sort(key=lambda m: (-PRIORITY_ORDER.get(m.get("priority", "LOW"), 1),
                                       m.get("deadline_s") if m.get("deadline_s") is not None else 1e18))
        return actionable[0]

    # ------------------------------------------------------------------
    # air candidate evaluation (rules 2, 3, 4, 5, 6)
    # ------------------------------------------------------------------
    def _evaluate_air_candidates(self, gs: Dict[str, Any], mission: Dict[str, Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for ac in gs.get("air", []):
            cand = {
                "resource_id": ac["id"],
                "type": "AIR",
                "feasible": False,
                "eta_s": None,
                "endurance_margin_s": ac.get("remaining_endurance_s", 0),
                "aircraft_status": ac.get("status"),
                "reject_reason": None,
            }
            rr = self._reject_air(ac, mission, gs)
            if rr is not None:
                cand["reject_reason"] = rr
                out.append(cand)
                continue
            route = self._air_route(ac, mission)
            eta = self._air_eta(ac, route)
            cand["eta_s"] = eta
            cand["route"] = route
            # rule 4: feasibility (endurance headroom)
            if ac.get("remaining_endurance_s", 0) < eta + ENDURANCE_MARGIN_S:
                cand["reject_reason"] = (
                    f"insufficient endurance ({ac.get('remaining_endurance_s')}s < "
                    f"{round(eta + ENDURANCE_MARGIN_S, 1)}s required)")
            else:
                cand["feasible"] = True
            out.append(cand)
        return out

    def _reject_air(self, ac: Dict[str, Any], mission: Dict[str, Any],
                    gs: Dict[str, Any]) -> Optional[str]:
        """Hard-filter an air candidate at candidate-generation time.

        Unavailable / non-commandable / incompatible / depleted resources and
        unavailable or hard-restricted destination landing sites are excluded
        BEFORE ranking, so the Rule baseline never proposes an action that the
        checker would have to reject (the checker stays as the final safety net).
        """
        if ac.get("c2_status") != "NORMAL":
            return f"C2 status {ac.get('c2_status')} (not commandable)"
        if ac.get("commandable") is False:
            return "not commandable"
        status = ac.get("status")
        if status in ("UNAVAILABLE", "CONTINGENCY", "DEGRADED"):
            return f"aircraft {status}"
        if status == "BUSY" or status == "RESERVED":
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
            # destination landing-site availability / hard restriction (Global State)
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
            # cargo is recovered at the lost aircraft's contingency site; a
            # backup flies there to take over, then continues to destination
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
    # ground fallback evaluation (rule 7)
    # ------------------------------------------------------------------
    def _evaluate_ground(self, gs: Dict[str, Any], mission: Dict[str, Any]) -> Dict[str, Any]:
        ground = gs.get("ground", {})
        allowed = mission.get("ground_fallback", True)
        eta = ground.get("ground_fallback_eta_s") or ground.get("current_d1_h1_eta_s")
        feasible = bool(allowed and eta is not None)
        return {"resource_id": "GROUND", "type": "GROUND", "feasible": feasible,
                "eta_s": eta, "reject_reason": None if feasible else
                ("ground fallback disabled" if not allowed else "no ground route ETA")}

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _air_action(self, candidate: Dict[str, Any], mission: Dict[str, Any]) -> Dict[str, Any]:
        # REASSIGN when the mission needs a new holder OR the aircraft is busy
        # (preemption of a lower-priority mission); DISPATCH only for an idle
        # aircraft taking a fresh mission.
        atype = "REASSIGN" if (mission.get("state") in ("INTERRUPTED", "NEEDS_REPLAN")
                               or candidate.get("aircraft_status") == "BUSY") else "DISPATCH"
        return {
            "type": atype,
            "aircraft_id": candidate["resource_id"],
            "mission_id": mission["id"],
            "target_site": mission["destination"],
            "route": candidate.get("route", [mission["destination"]]),
        }

    def _air_action_from_shared(self, candidate: Dict[str, Any],
                                mission: Dict[str, Any]) -> Dict[str, Any]:
        """Build the air action from a shared-table candidate (uses the table's
        pre-computed `action_type`; never re-derives it from a private field)."""
        atype = candidate.get("action_type") or (
            "REASSIGN" if mission.get("state") in ("INTERRUPTED", "NEEDS_REPLAN")
            else "DISPATCH")
        return {
            "type": atype,
            "aircraft_id": candidate["resource_id"],
            "mission_id": mission["id"],
            "target_site": mission["destination"],
            "route": candidate.get("route") or [mission["destination"]],
        }

    def _derive_trigger(self, gs: Dict[str, Any], mission: Dict[str, Any]) -> List[str]:
        triggers: List[str] = []
        for ev in gs.get("events", []):
            etype = ev.get("event_type")
            if etype in ("GROUND_DISRUPTION", "GROUND_ACCESSIBILITY_DEGRADED"):
                triggers.append("B1 closure (ground disruption)")
            if etype in ("C2_LOST",):
                triggers.append("C2 lost link")
        if mission.get("state") in ("INTERRUPTED", "NEEDS_REPLAN"):
            triggers.append("mission interrupted -> NEEDS_REPLAN")
        if mission.get("state") == "WAITING":
            triggers.append(f"new {mission.get('priority', 'NORMAL')} mission")
        return triggers or ["scheduled re-evaluation"]

    def _noop(self, decision_id: str, t: int, gs: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "decision_id": decision_id,
            "simulation_time": t,
            "scenario_id": gs.get("scenario_id"),
            "trigger": ["no actionable mission"],
            "mission_id": None,
            "mission_priority": None,
            "candidates": [],
            "ground_candidate": {"resource_id": "GROUND", "type": "GROUND",
                                 "feasible": False, "eta_s": None, "reject_reason": None},
            "selected": {"resource": None, "type": "NOOP", "eta_s": None, "reject_reason": None},
            "action": None,
            "reason": "no actionable mission",
        }
