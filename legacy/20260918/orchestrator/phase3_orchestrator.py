"""Phase 3 orchestrator — the Phase-2 closed loop with the LLM Manager swapped in.

    Global State -> { Rule | LLM } Manager (ManagerAction)
                 -> Semantic Validator (shared)
                 -> FeasibilityChecker (shared)
                 -> Executor (shared)
                 -> Simulators (SUMO / BlueSky)

The LLM sees only the Global State v1 snapshot. The local C2 contingency remains
manager-independent (it fires before, and does not wait for, the manager). Real
LLM wall-clock latency is recorded but never affects simulation time (Frozen
Simulation Decision Mode).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from managers.rule_based import RuleBasedManager
from orchestrator.phase2_orchestrator import Phase2Orchestrator
from safety.semantic_validator import SemanticValidator

ROOT = Path(__file__).resolve().parents[1]

# new Phase-3 action types executed (beyond Phase-2 DISPATCH/REASSIGN/
# GROUND_FALLBACK/DELAY/CANCEL)
SIMPLE_ACTIONS = ("NO_ACTION", "ESCALATE", "RESERVE", "RETURN", "LAND",
                  "REROUTE", "DIVERT")


class Phase3Orchestrator(Phase2Orchestrator):
    def __init__(self, cfg: Dict[str, Any], sumo_cfg: Path, run_dir: Path,
                 case: str = "C2_B", gui: bool = False, manager=None,
                 phase3_config: Optional[Dict[str, Any]] = None):
        super().__init__(cfg, sumo_cfg, run_dir, case, gui)
        # swap in the LLM manager (or keep Rule for parity runs)
        self.manager = manager if manager is not None else RuleBasedManager(cfg)
        self.p3 = phase3_config or {}
        self.semantic = SemanticValidator(
            str(ROOT / self.p3.get("resource_compatibility",
                                   "config/resource_compatibility.yaml")))
        self.semantic_checks_f = open(self.run_dir / "semantic_checks.jsonl", "w", encoding="utf-8")
        # Experiment-1 Finalization §16: raw -> normalized -> executed triple.
        self.action_pipeline_f = open(self.run_dir / "action_pipeline.jsonl", "w", encoding="utf-8")

    # ------------------------------------------------------------------
    # manager pipeline (+ semantic validation)
    # ------------------------------------------------------------------
    def _run_manager(self, t: int) -> None:
        gs = self._build_gs(t)
        self.manager_inputs_f.write(json.dumps(gs, sort_keys=True, ensure_ascii=False,
                                               separators=(",", ":")) + "\n")
        self.manager_inputs_f.flush()

        decision = self.manager.decide(gs)
        self.manager_decisions.append(decision)
        self.manager_outputs_f.write(json.dumps(
            decision, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.manager_outputs_f.flush()
        self.events_since_last_decision = []

        action = decision.get("action")
        if action is None:
            return  # NOOP / final LLM failure

        # Experiment-1 Finalization §16: record the raw action BEFORE any
        # normalization, so provenance is lossless and no silent substitution
        # can hide.  `decision` already carries the raw action, but the triple
        # below makes raw/normalized/executed explicit and auditable.
        raw_action = copy.deepcopy(action)

        # FIX (review §9): normalize FIRST so the checker validates the SAME
        # action that will be executed.  The v1 code validated the raw action
        # (target_site/route still null), then filled them after the check, so
        # an action that omitted a closed destination could pass both gates and
        # later inherit that closed site.
        action = self._normalize_action(action)
        normalized_action = copy.deepcopy(action)
        executed_action: Optional[Dict[str, Any]] = None

        # shared semantic validation (both managers pass through here)
        sem = self.semantic.validate(action, gs)
        self.semantic_checks_f.write(json.dumps({
            "t": t, "decision_id": decision["decision_id"], "action": action,
            "valid": sem["valid"], "error_types": sem["error_types"],
        }, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.semantic_checks_f.flush()

        if not sem["valid"]:
            self._record_violation(t, action, sem["error_types"], decision["decision_id"])
            self._record_action(t, action.get("type"), action.get("aircraft_id"),
                                action.get("mission_id"), action.get("target_site"),
                                action.get("route"), "REJECTED_SEMANTIC", decision["decision_id"])
            self._write_action_pipeline(t, decision["decision_id"],
                                        raw_action, normalized_action, None, "REJECTED_SEMANTIC")
            return

        # shared feasibility checker
        result = self.checker.check(action)
        self.feasibility_checks_f.write(json.dumps({
            "t": t, "decision_id": decision["decision_id"], "action": action,
            "valid": result["valid"], "violations": result["violations"],
        }, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.feasibility_checks_f.flush()

        if not result["valid"]:
            self._record_violation(t, action, result["violations"], decision["decision_id"])
            self._record_action(t, action.get("type"), action.get("aircraft_id"),
                                action.get("mission_id"), action.get("target_site"),
                                action.get("route"), "REJECTED", decision["decision_id"])
            self._write_action_pipeline(t, decision["decision_id"],
                                        raw_action, normalized_action, None, "REJECTED")
            return

        executed_action = copy.deepcopy(action)
        self._execute_manager_action(t, action, decision)
        self._write_action_pipeline(t, decision["decision_id"],
                                    raw_action, normalized_action, executed_action, "ISSUED")

    def _write_action_pipeline(self, t: int, decision_id: str, raw_action: Any,
                               normalized_action: Any, executed_action: Any,
                               result: str) -> None:
        self.action_pipeline_f.write(json.dumps({
            "t": t, "decision_id": decision_id,
            "raw_action": raw_action,
            "normalized_action": normalized_action,
            "executed_action": executed_action,
            "result": result,
        }, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.action_pipeline_f.flush()

    def _normalize_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Fill concrete route/target from the mission when the LLM omits them.

        The LLM emits a high-level action (schema allows null route/target_site);
        this translation step (identical to the Rule Manager's route semantics)
        makes it executable without changing the shared checker/executor.
        """
        atype = action.get("type")
        if atype in ("DISPATCH", "REASSIGN", "DIVERT", "REROUTE"):
            m = self.registry.missions.get(action.get("mission_id"))
            if m is not None:
                if not action.get("target_site"):
                    action["target_site"] = m.destination
                if not action.get("route"):
                    if atype == "REASSIGN" and m.status in ("INTERRUPTED", "NEEDS_REPLAN"):
                        action["route"] = ([self.contingency_site, m.destination]
                                           if self.contingency_site != m.destination
                                           else [m.destination])
                    else:
                        action["route"] = ([m.origin, m.destination]
                                           if m.origin and m.origin != m.destination
                                           else [m.destination])
        return action

    # ------------------------------------------------------------------
    # executor (Phase-2 actions + Phase-3 simple actions)
    # ------------------------------------------------------------------
    def _execute_manager_action(self, t: int, action: Dict[str, Any],
                                decision: Dict[str, Any]) -> None:
        atype = action["type"]
        if atype in ("DISPATCH", "REASSIGN", "REROUTE", "DIVERT"):
            self._execute_air_action(t, action, decision)
        elif atype == "GROUND_FALLBACK":
            self._execute_ground_fallback(t, action, decision)
        elif atype == "DELAY":
            self._delay_mission(t, action)
        elif atype == "CANCEL":
            self._cancel_mission(t, action)
        elif atype in SIMPLE_ACTIONS:
            self._execute_simple_action(t, action, decision)
        # unknown action type: record as violation (should not reach here)

    def _execute_simple_action(self, t: int, action: Dict[str, Any],
                               decision: Dict[str, Any]) -> None:
        atype = action["type"]
        acid = action.get("aircraft_id")
        mid = action.get("mission_id")
        if atype == "RESERVE" and acid:
            ac = self.registry.aircraft.get(acid)
            if ac and ac.status == "AVAILABLE":
                ac.transition("RESERVED")
        elif atype == "LAND" and acid:
            self.bs.park(acid)
        elif atype == "RETURN" and acid:
            target = action.get("target_site") or self.contingency_site
            role = self.aircraft_role[acid]
            self.bs.fly_to(acid, target, alt_ft=100.0,
                           spd_kts=self._role_speed(role))
            self.aircraft_dest[acid] = target
        self._record_action(t, atype, acid, mid, action.get("target_site"),
                            action.get("route"), "ISSUED", decision["decision_id"])
        self._record_event(t, atype, "MANAGER_ACTION",
                           {"aircraft": acid, "mission": mid, "type": atype,
                            "reason": action.get("reason")})

    def _role_speed(self, role: str) -> float:
        from orchestrator.fleet import MPS_TO_KTS, ROLE_CRUISE_MS
        return ROLE_CRUISE_MS.get(role, 15.0) * MPS_TO_KTS

    # ------------------------------------------------------------------
    # run_config + metrics
    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        super().shutdown()
        # Phase2Orchestrator.shutdown hardcodes manager=rule_based; overwrite with
        # the actual Phase-3 manager metadata.
        (self.run_dir / "run_config.yaml").write_text(
            yaml.safe_dump(self._run_config(), sort_keys=False, allow_unicode=True),
            encoding="utf-8")
        try:
            self.semantic_checks_f.close()
        except Exception:
            pass
        try:
            self.action_pipeline_f.close()
        except Exception:
            pass

    def _run_config(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.cfg.get("scenario_id", "S0"),
            "scenario_version": self.cfg.get("scenario_version", "S0_3p2km_v1"),
            "phase": "phase3_llm_manager",
            "case": self.case,
            "duration_s": self.duration_s,
            "simulation_step_s": 1,
            "seed": self.seed,
            "b1_close_t": self.b1_close_t,
            "critical_mission_t_s": self.critical_t,
            "c2_lost_t_s": self.c2_lost_t,
            "manager": getattr(self.manager, "manager_kind", "rule_based"),
            "llm_model": getattr(self.manager, "model", None),
            "prompt_version": getattr(self.manager, "prompt_version", None),
            "contingency_site": self.contingency_site,
        }

    def _metrics(self) -> Dict[str, Any]:
        m = super()._metrics()
        m["phase"] = "phase3_llm_manager"
        m["manager"] = getattr(self.manager, "manager_kind", "rule_based")
        m["llm_model"] = getattr(self.manager, "model", None)
        m["prompt_version"] = getattr(self.manager, "prompt_version", None)
        m["llm_latency_total_s"] = round(sum(
            (d.get("llm_metadata") or {}).get("latency_s", 0.0)
            for d in self.manager_decisions), 3)
        m["llm_retry_total"] = sum(
            (d.get("llm_metadata") or {}).get("retry_count", 0)
            for d in self.manager_decisions)
        return m
