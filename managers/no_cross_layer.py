"""B0 — No Cross-Layer Coordination (Experiment 1 baseline).

When the ground emergency mission appears, B0 uses ONLY the ground system
(ground fallback). Existing air missions continue unchanged. There is no
ground-air resource reconfiguration, so no air asset is ever re-tasked.

B0 is NOT "do nothing": it actively routes the emergency by ground fallback and
lets existing air services keep flying.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from managers.rule_based import (ACTIONABLE_STATES, PRIORITY_ORDER, RuleBasedManager)


class NoCrossLayerManager(RuleBasedManager):
    """B0: ground-only handling; never re-tasks an air asset."""

    manager_kind = "no_cross_layer"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.manager_kind = "no_cross_layer"

    # ------------------------------------------------------------------
    def decide(self, global_state: Dict[str, Any]) -> Dict[str, Any]:
        self._decision_counter += 1
        decision_id = f"D{self._decision_counter:03d}"
        t = global_state["simulation_time"]

        target = self._select_target_mission(global_state)
        if target is None:
            return self._noop(decision_id, t, global_state)

        # ground-only: the emergency is always served by ground fallback.
        # Experiment-1 Finalization §17: consume the shared ground candidate
        # when present (same facts B1/B2/B4b see); legacy fallback otherwise.
        shared = global_state.get("candidates")
        if shared is not None:
            ground = shared.get("ground", {})
            feasible = bool(ground.get("legal"))
            eta = ground.get("eta_s")
        else:
            ground = self._evaluate_ground(global_state, target)
            feasible = bool(ground.get("feasible"))
            eta = ground.get("eta_s")
        if feasible:
            action = {"type": "GROUND_FALLBACK", "mission_id": target["id"],
                      "ground_eta_s": eta}
            selected = {"resource": "GROUND", "type": "GROUND",
                        "eta_s": eta, "reject_reason": None}
            reason = "no cross-layer coordination: ground fallback only"
            action = {"type": "GROUND_FALLBACK", "mission_id": target["id"],
                      "ground_eta_s": ground["eta_s"]}
            selected = {"resource": "GROUND", "type": "GROUND",
                        "eta_s": ground["eta_s"], "reject_reason": None}
            reason = "no cross-layer coordination: ground fallback only"
        else:
            # no ground route -> DELAY/CANCEL as in the rule fallback
            if target.get("deadline_s") is not None and target["deadline_s"] > t:
                action = {"type": "DELAY", "mission_id": target["id"],
                          "reason": "no ground fallback available; deadline not passed"}
                selected = {"resource": None, "type": "DELAY", "eta_s": None,
                            "reject_reason": None}
                reason = "no ground route; deadline slack remains -> DELAY"
            else:
                action = {"type": "CANCEL", "mission_id": target["id"],
                          "reason": "no ground fallback available and deadline passed"}
                selected = {"resource": None, "type": "CANCEL", "eta_s": None,
                            "reject_reason": None}
                reason = "no ground route; deadline passed -> CANCEL"

        return {
            "decision_id": decision_id,
            "simulation_time": t,
            "scenario_id": global_state.get("scenario_id"),
            "manager": "no_cross_layer",
            "trigger": self._derive_trigger(global_state, target),
            "mission_id": target["id"],
            "mission_priority": target["priority"],
            "candidates": [],
            "ground_candidate": ground,
            "selected": selected,
            "action": action,
            "reason": reason,
        }
