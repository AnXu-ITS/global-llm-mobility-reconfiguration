"""B2 — Optimization / Heuristic Manager (Experiment 1).

Same Global-State -> ManagerAction contract, same candidate filter as B1, but
ranks the feasible set (air + ground) by a frozen scalar objective J instead of
the B1 "minimum completion time" rule. Hard constraints are identical to B1
(same `_reject_air` destination/aircraft/compatibility/battery/endurance filter,
same no-equal/higher-priority preemption rule); B2 only changes the RANKING.

Objective (frozen in config/experiment1_b2_weights.yaml):

    J = w1 * completion_time_s
      + w_deadline * deadline_violation_s
      + w2[preempted_priority]          (REASSIGN only)
      + w3 * is_reassignment
      + w_risk * risk_score
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import yaml

from managers.rule_based import RuleBasedManager

ROOT_DUMMY = None


class OptimizationManager(RuleBasedManager):
    """B2: heuristic optimisation baseline (objective-ranking)."""

    manager_kind = "optimization"

    def __init__(self, config: Dict[str, Any], weights_path: str):
        super().__init__(config)
        self.manager_kind = "optimization"
        with open(weights_path, encoding="utf-8") as f:
            w = yaml.safe_load(f)["objective"]
        self.w1 = float(w["w1_completion_time"])
        self.w_deadline = float(w["w_deadline"])
        self.w2 = {k: float(v) for k, v in w["w2_existing_disruption"].items()}
        self.w3 = float(w["w3_reassignment"])
        self.w_risk = float(w["w_risk"])
        self.risk_thresholds = [float(x) for x in w["risk_thresholds_s"]]

    # ------------------------------------------------------------------
    def decide(self, global_state: Dict[str, Any]) -> Dict[str, Any]:
        self._decision_counter += 1
        decision_id = f"D{self._decision_counter:03d}"
        t = global_state["simulation_time"]

        target = self._select_target_mission(global_state)
        if target is None:
            return self._noop(decision_id, t, global_state)

        # Experiment-1 Finalization §3/§17: B2 computes its frozen objective
        # FROM the shared candidate-table fields (never re-derives candidate
        # facts privately).  Legacy path is only a fallback for unit tests.
        shared = global_state.get("candidates")
        if shared is not None:
            return self._decide_from_shared(shared, target, t, decision_id, global_state)
        return self._decide_legacy(global_state, target, decision_id, t)

    def _decide_from_shared(self, shared: Dict[str, Any], target: Dict[str, Any],
                            t: int, decision_id: str,
                            global_state: Dict[str, Any]) -> Dict[str, Any]:
        deadline = target.get("deadline_s")

        best_cand: Optional[Dict[str, Any]] = None
        best_kind = "AIR"
        best_j = float("inf")
        best_meta: Dict[str, Any] = {}

        for c in shared.get("air", []):
            if not c.get("legal"):
                continue
            is_reassign = (c.get("action_type") == "REASSIGN"
                           and c.get("preempted_mission_id") is not None)
            preempted_pri = c.get("preempted_mission_priority") if is_reassign else None
            j = self._objective(c.get("eta_s"), is_reassign, preempted_pri,
                                c.get("endurance_margin_s"), deadline, t)
            if j < best_j:
                best_j, best_cand, best_kind = j, c, "AIR"
                best_meta = {"is_reassignment": is_reassign,
                             "preempted_priority": preempted_pri,
                             "objective_j": round(j, 3)}

        ground = shared.get("ground", {})
        if ground.get("legal"):
            jg = self._objective(ground.get("eta_s"), False, None, None, deadline, t)
            if jg < best_j:
                best_j, best_cand, best_kind = jg, ground, "GROUND"
                best_meta = {"is_reassignment": False, "preempted_priority": None,
                             "objective_j": round(jg, 3)}

        if best_cand is None:
            if deadline is not None and deadline > t:
                action = {"type": "DELAY", "mission_id": target["id"],
                          "reason": "no feasible air/ground; deadline not passed"}
                selected = {"resource": None, "type": "DELAY", "eta_s": None,
                            "reject_reason": None}
                reason = "no feasible resource; deadline slack remains -> DELAY"
            else:
                action = {"type": "CANCEL", "mission_id": target["id"],
                          "reason": "no feasible air/ground; deadline passed"}
                selected = {"resource": None, "type": "CANCEL", "eta_s": None,
                            "reject_reason": None}
                reason = "no feasible resource; deadline passed -> CANCEL"
        elif best_kind == "AIR":
            action = self._air_action_from_shared(best_cand, target)
            selected = {"resource": best_cand["resource_id"], "type": "AIR",
                        "eta_s": best_cand["eta_s"], "reject_reason": None}
            reason = f"minimum objective J={best_meta['objective_j']}"
        else:
            action = {"type": "GROUND_FALLBACK", "mission_id": target["id"],
                      "ground_eta_s": best_cand["eta_s"]}
            selected = {"resource": "GROUND", "type": "GROUND",
                        "eta_s": best_cand["eta_s"], "reject_reason": None}
            reason = f"minimum objective J={best_meta['objective_j']} (ground)"

        return {
            "decision_id": decision_id,
            "simulation_time": t,
            "scenario_id": global_state.get("scenario_id"),
            "manager": "optimization",
            "trigger": self._derive_trigger(global_state, target),
            "mission_id": target["id"],
            "mission_priority": target["priority"],
            "candidates": shared.get("air", []),
            "ground_candidate": shared.get("ground", {}),
            "selected": selected,
            "action": action,
            "reason": reason,
            "objective_meta": best_meta,
        }

    def _decide_legacy(self, global_state: Dict[str, Any], target: Dict[str, Any],
                       decision_id: str, t: int) -> Dict[str, Any]:
        candidates = self._evaluate_air_candidates(global_state, target)
        feasible = [c for c in candidates if c["feasible"]]
        ground = self._evaluate_ground(global_state, target)
        air_lookup = {a["id"]: a for a in global_state.get("air", [])}
        deadline = target.get("deadline_s")

        best_cand: Optional[Dict[str, Any]] = None
        best_kind = "AIR"
        best_j = float("inf")
        best_meta: Dict[str, Any] = {}

        for c in feasible:
            ac = air_lookup[c["resource_id"]]
            is_reassign = ac.get("status") in ("BUSY", "RESERVED")
            preempted_pri = ac.get("mission_priority", "NORMAL") if is_reassign else None
            j = self._objective(c["eta_s"], is_reassign, preempted_pri,
                                c["endurance_margin_s"], deadline, t)
            if j < best_j:
                best_j, best_cand, best_kind = j, c, "AIR"
                best_meta = {"is_reassignment": is_reassign,
                             "preempted_priority": preempted_pri,
                             "objective_j": round(j, 3)}

        if ground["feasible"]:
            jg = self._objective(ground["eta_s"], False, None, None, deadline, t)
            if jg < best_j:
                best_j, best_cand, best_kind = jg, ground, "GROUND"
                best_meta = {"is_reassignment": False, "preempted_priority": None,
                             "objective_j": round(jg, 3)}

        if best_cand is None:
            if deadline is not None and deadline > t:
                action = {"type": "DELAY", "mission_id": target["id"],
                          "reason": "no feasible air/ground; deadline not passed"}
                selected = {"resource": None, "type": "DELAY", "eta_s": None,
                            "reject_reason": None}
                reason = "no feasible resource; deadline slack remains -> DELAY"
            else:
                action = {"type": "CANCEL", "mission_id": target["id"],
                          "reason": "no feasible air/ground; deadline passed"}
                selected = {"resource": None, "type": "CANCEL", "eta_s": None,
                            "reject_reason": None}
                reason = "no feasible resource; deadline passed -> CANCEL"
        elif best_kind == "AIR":
            action = self._air_action(best_cand, target)
            selected = {"resource": best_cand["resource_id"], "type": "AIR",
                        "eta_s": best_cand["eta_s"], "reject_reason": None}
            reason = f"minimum objective J={best_meta['objective_j']}"
        else:
            action = {"type": "GROUND_FALLBACK", "mission_id": target["id"],
                      "ground_eta_s": best_cand["eta_s"]}
            selected = {"resource": "GROUND", "type": "GROUND",
                        "eta_s": best_cand["eta_s"], "reject_reason": None}
            reason = f"minimum objective J={best_meta['objective_j']} (ground)"

        return {
            "decision_id": decision_id,
            "simulation_time": t,
            "scenario_id": global_state.get("scenario_id"),
            "manager": "optimization",
            "trigger": self._derive_trigger(global_state, target),
            "mission_id": target["id"],
            "mission_priority": target["priority"],
            "candidates": candidates,
            "ground_candidate": ground,
            "selected": selected,
            "action": action,
            "reason": reason,
            "objective_meta": best_meta,
        }

    # ------------------------------------------------------------------
    def _objective(self, completion_s: Optional[float], is_reassign: bool,
                   preempted_pri: Optional[str], endurance_margin: Optional[float],
                   deadline_s: Optional[float], t: int) -> float:
        j = self.w1 * float(completion_s or 0.0)
        if deadline_s is not None and completion_s is not None:
            dv = max(0.0, float(t) + float(completion_s) - float(deadline_s))
            j += self.w_deadline * dv
        if is_reassign:
            j += self.w2.get(preempted_pri or "NORMAL", self.w2["NORMAL"])
            j += self.w3
        if endurance_margin is not None:
            risk = 0
            for thr in self.risk_thresholds:
                if endurance_margin < thr:
                    risk += 1
            j += self.w_risk * risk
        return j
