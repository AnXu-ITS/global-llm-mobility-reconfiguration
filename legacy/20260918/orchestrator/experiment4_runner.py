"""Experiment 4 runner — LLM Operational Limits (4A / 4B / 4C).

Post-review revision (EXPERIMENT4_INDEPENDENT_REVIEW_20260909).  Reuses the
FROZEN Experiment-2 machinery (Global State v1 -> manager -> normalize ->
semantic -> feasibility -> executor -> SUMO/BlueSky) with three additive,
non-destructive extensions:

  4A  Information Update Frequency  — THREE clocks: (1) physical events
       (frozen), (2) the observation snapshot refresh (every `obs_interval_s`),
       (3) the manager decision (event-triggered AND every observation tick).
       The manager ALWAYS decides on the latest OBSERVED snapshot (never the
       live state); the local safety layer still reacts immediately.  Arms are
       observation intervals, so failure-discovery latency scales with the
       interval and LLM-call count with its reciprocal.

  4B  Inference Latency             — Mode B delayed execution: decide on S_t,
       re-validate (semantic + feasibility) and execute at S_(t+delay).  Fixed
       time-slice order (events before same-time pending), plus a pending queue
       with per-mission versioning (new decision supersedes older), idempotency
       (never re-ground / re-dispatch an already-handled mission), and stale
       actions -> STALE_REJECTED (never silently repaired).

  4C  Global State Scale (input)    — the CORE decision problem (4-aircraft base
       fleet + F1-C2 anchor + reference-optimal action) is identical across
       arms; only INERT distractor entries (UNAVAILABLE / not commandable /
       incompatible aircraft, inert sites, COMPLETED missions) grow the Global
       State and the candidate table's illegal rows.

No frozen component (base fleet, candidate table, B2 objective, action contract,
failure semantics, state machines) is modified. Architecture:
docs/EXPERIMENT4_DESIGN.md.
"""
from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from orchestrator.experiment2_runner import Experiment2Runner, sha256_hex
from orchestrator.experiment4_fleet import generate_distractors
from orchestrator.fleet import FLEET
from orchestrator.registry import Aircraft, Mission

ROOT = Path(__file__).resolve().parents[1]

# actions whose (type + resource) signature participates in oscillation /
# redundancy bookkeeping.
SIGNATURE_ACTIONS = ("DISPATCH", "REASSIGN", "DIVERT", "REROUTE", "GROUND_FALLBACK")


class Experiment4Runner(Experiment2Runner):
    """E4 base runner: 4A observation clock + shared E4 cost/quality metrics.

    With `obs_interval_s == 0` (4B/4C) the runner is behaviorally identical to
    the frozen Mode-A pipeline except for the full-task periodic trigger fix.
    With `obs_interval_s > 0` (4A) the manager decides on the latest observation
    snapshot instead of the live state.
    """

    def __init__(self, cfg: Dict[str, Any], e4_cfg: Dict[str, Any],
                 sub: str, arm: Dict[str, Any], scenario: Dict[str, Any],
                 manager, sumo_cfg: Path, run_dir: Path, seed: int,
                 phase3_config: Optional[Dict[str, Any]] = None):
        self.e4 = e4_cfg
        self.sub = sub
        self.arm = dict(arm)
        self.arm_id = str(arm["id"])

        # Build an E2-shaped config/scenario view so the frozen Experiment2Runner
        # __init__ (candidate table 2.1.0 + E2 checker + E2 semantic + single
        # failure parse) runs unchanged; E4 state is layered on afterwards.
        e2_scenario = dict(scenario)
        e2_scenario["failure"] = copy.deepcopy(scenario["failure"])
        e2_scenario["failure_family"] = scenario["failure"]["family"]
        e2_scenario["impact_context"] = "C2"  # placeholder; E4 uses sub/arm
        periodic = int(arm.get("periodic_decision_s")
                       or e4_cfg.get("periodic_decision_s", 30))
        e2_cfg_view = {
            "version": 4,
            "duration_s": int(scenario.get("duration_s", e4_cfg.get("duration_s", 900))),
            "step_s": int(e4_cfg["step_s"]),
            "mission_release_t_s": int(e4_cfg["mission_release_t_s"]),
            "disruption_t_s": int(e4_cfg["disruption_t_s"]),
            "periodic_decision_s": periodic,
            "failure_t_s": int(scenario["failure"]["time_s"]),
            "emergency_mission": dict(e4_cfg["emergency_mission"]),
            "disruptions": {k: dict(v) for k, v in e4_cfg["disruptions"].items()},
            "urgencies": {k: dict(v) for k, v in e4_cfg["urgencies"].items()},
            "workloads": {k: {"busy": [list(r) for r in v["busy"]],
                              "idle": list(v["idle"])}
                          for k, v in e4_cfg["workloads"].items()},
            "scenarios": [e2_scenario],
        }
        super().__init__(cfg, e2_cfg_view, e2_scenario, manager, sumo_cfg, run_dir,
                         seed, phase3_config=phase3_config)

        # 4A observation clock (0 -> disabled, i.e. 4B/4C use live state).
        self.obs_interval_s = int(arm.get("obs_interval_s", 0) or 0)
        self.observed_gs: Optional[Dict[str, Any]] = None
        self.observed_t: Optional[int] = None
        self.snapshot_ages: List[int] = []
        self.failure_discovery_t: Optional[int] = None
        self._prompt_sizes: List[int] = []
        self._selection_quality = {"legal": 0, "illegal": 0, "absent": 0}
        self._legal_candidate_counts: List[int] = []

    # ------------------------------------------------------------------
    # time-slice: events -> (pending) -> physics -> registry -> (observation)
    # ------------------------------------------------------------------
    def _step_once(self) -> None:
        t = self.t
        self._apply_scheduled_events(t)
        self._process_pending_actions(t)   # 4B only (no-op otherwise)
        self.sumo.step()
        self.bs.step()
        self.t += 1
        now = self.t
        ground = self._collect_ground(now)
        air = self.bs.state()
        self.last_ground = ground
        self.last_air = air
        self._update_registry(air)
        self._process_ground_fallbacks(now)
        self._refresh_observation_if_due(now)  # 4A only (no-op otherwise)
        if now in self.audit_snapshot_times:
            self._write_snapshot(now)
        self._log(now, ground, air)

    # ------------------------------------------------------------------
    # periodic trigger (E3-v2 full-task fix): continue while ANY mission is
    # actionable, not only the primary emergency.
    # ------------------------------------------------------------------
    def _periodic_due(self) -> bool:
        t = self.t
        if self.critical_t is None or t <= self.critical_t:
            return False
        # 4A: poll the manager at every observation tick (cost ∝ 1/interval).
        if self.obs_interval_s:
            return t % self.obs_interval_s == 0
        # 4B/4C: frozen event+periodic, but trigger on ANY actionable mission.
        if self.periodic_s is None:
            return False
        if (t - self.critical_t) % self.periodic_s != 0:
            return False
        for m in self.registry.missions.values():
            if m.status in ("WAITING", "NEEDS_REPLAN", "INTERRUPTED"):
                return True
        return False

    # ------------------------------------------------------------------
    # observation snapshot (4A): refresh every `obs_interval_s`; the manager's
    # view is the latest snapshot, never the live state.
    # ------------------------------------------------------------------
    def _refresh_observation_if_due(self, t: int) -> None:
        if not self.obs_interval_s:
            return
        if t % self.obs_interval_s != 0:
            return
        self.observed_gs = self._build_gs(t)  # record=True -> candidate provenance
        self.observed_t = t
        if (self.failure_discovery_t is None and self.failure_t is not None
                and t >= self.failure_t):
            self.failure_discovery_t = t

    def _manager_gs(self, t: int) -> Dict[str, Any]:
        if not self.obs_interval_s:
            return self._build_gs(t)  # live state (4B/4C)
        if self.observed_gs is None:
            self.observed_gs = self._build_gs(t, record=False)
            self.observed_t = t
        gs = copy.deepcopy(self.observed_gs)
        gs["observation_snapshot_time"] = self.observed_t
        gs["observation_snapshot_age_s"] = int(t) - int(self.observed_t)
        return gs

    # ------------------------------------------------------------------
    # pending queue (4B): no-op in base / 4A / 4C.
    # ------------------------------------------------------------------
    def _process_pending_actions(self, now: int) -> None:
        pass

    # ------------------------------------------------------------------
    # manager pipeline: replicate the frozen Phase-3 pipeline but route the
    # VALID action through `_apply_valid_action` (immediate in Mode A, deferred
    # in Mode B) and feed the manager from `_manager_gs` (live or observed).
    # ------------------------------------------------------------------
    def _run_manager(self, t: int) -> None:
        self.checker.current_t = t
        if t == self.release_t:
            gs0 = self._build_gs(t, record=False)
            self.initial_critical_air_count = sum(
                1 for c in gs0["candidates"]["air"] if c.get("legal"))
            self.initial_gs_hash = sha256_hex({k: v for k, v in gs0.items()
                                               if k != "candidates"})

        gs = self._manager_gs(t)
        self.manager_inputs_f.write(json.dumps(
            gs, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.manager_inputs_f.flush()
        decision = self.manager.decide(gs)
        self.manager_decisions.append(decision)
        self.manager_outputs_f.write(json.dumps(
            decision, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.manager_outputs_f.flush()
        self.events_since_last_decision = []

        # diagnostics: per-decision snapshot age (4A) + prompt size + selection.
        if self.obs_interval_s and self.observed_t is not None:
            self.snapshot_ages.append(int(t) - int(self.observed_t))
        self._prompt_sizes.append(len(json.dumps(
            gs, sort_keys=True, ensure_ascii=False, separators=(",", ":"))))
        self._record_selection_quality(decision, gs)

        action = decision.get("action")
        if action is None:
            return

        raw_action = copy.deepcopy(action)
        action = self._normalize_action(action)
        normalized_action = copy.deepcopy(action)

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
            self._write_action_pipeline(t, decision["decision_id"], raw_action,
                                        normalized_action, None, "REJECTED_SEMANTIC")
            return

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
            self._write_action_pipeline(t, decision["decision_id"], raw_action,
                                        normalized_action, None, "REJECTED")
            return

        self._apply_valid_action(t, decision, raw_action, normalized_action)

    def _record_selection_quality(self, decision: Dict[str, Any],
                                  gs: Dict[str, Any]) -> None:
        pass  # 4C overrides

    # ------------------------------------------------------------------
    # Mode A (default): execute immediately.
    # ------------------------------------------------------------------
    def _apply_valid_action(self, t: int, decision: Dict[str, Any],
                            raw_action: Dict[str, Any],
                            normalized_action: Dict[str, Any]) -> None:
        executed_action = copy.deepcopy(normalized_action)
        self._execute_manager_action(t, normalized_action, decision)
        self._write_action_pipeline(t, decision["decision_id"], raw_action,
                                    normalized_action, executed_action, "ISSUED")

    # ------------------------------------------------------------------
    # E4 metrics helpers
    # ------------------------------------------------------------------
    def _llm_total(self, key: str) -> int:
        return sum((d.get("llm_metadata") or {}).get(key, 0)
                   for d in self.manager_decisions)

    def _redundant_decision_count(self) -> int:
        issued = [a for a in self._read_actions() if a.get("result") == "ISSUED"]
        issued.sort(key=lambda a: int(a.get("t") or 0))
        last: Dict[str, str] = {}
        redundant = 0
        for a in issued:
            mid = a.get("mission_id")
            atype = a.get("action_type")
            if not mid or atype not in SIGNATURE_ACTIONS:
                continue
            sig = ("GROUND" if atype == "GROUND_FALLBACK"
                   else f"{atype}:{a.get('aircraft_id') or ''}")
            if mid in last and last[mid] == sig:
                redundant += 1
            last[mid] = sig
        return redundant

    def _decision_oscillation_count(self) -> int:
        issued = [a for a in self._read_actions() if a.get("result") == "ISSUED"]
        issued.sort(key=lambda a: int(a.get("t") or 0))
        last: Dict[str, str] = {}
        osc = 0
        for a in issued:
            mid = a.get("mission_id")
            atype = a.get("action_type")
            if not mid or atype not in SIGNATURE_ACTIONS:
                continue
            sig = ("GROUND" if atype == "GROUND_FALLBACK"
                   else "AIR:" + str(a.get("aircraft_id") or ""))
            if mid in last and last[mid] != sig:
                osc += 1
            last[mid] = sig
        return osc

    def _refresh_failure_state(self) -> None:
        """Keep the E2 checker's failure state current (utm / zones / new missions)."""
        self.checker.set_failure_state({
            "utm_state": self.utm_state,
            "new_mission_ids": set(self.injected_mission_ids),
            "zones": [z for z in self.air_risk_zones
                      if z["active_from_s"] <= self.t <= z["active_until_s"]
                      and z.get("candidate_rule", "full") != "none"],
        })

    # ------------------------------------------------------------------
    # metrics: E1/E2 + E4 additions
    # ------------------------------------------------------------------
    def _metrics(self) -> Dict[str, Any]:
        m = super()._metrics()
        m["experiment"] = "experiment4"
        m["sub_experiment"] = self.sub
        m["arm_id"] = self.arm_id
        m["arm"] = dict(self.arm)
        m["num_manager_decisions"] = len(self.manager_decisions)
        m["redundant_decision_count"] = self._redundant_decision_count()
        m["decision_oscillation_count"] = self._decision_oscillation_count()
        m["llm_total_prompt_tokens"] = self._llm_total("prompt_tokens")
        m["llm_total_completion_tokens"] = self._llm_total("completion_tokens")
        m["llm_total_tokens"] = (m["llm_total_prompt_tokens"]
                                 + m["llm_total_completion_tokens"])
        m["prompt_size_chars_mean"] = (round(sum(self._prompt_sizes)
                                             / len(self._prompt_sizes), 1)
                                       if self._prompt_sizes else 0.0)
        # 4A observation-staleness metrics
        if self.obs_interval_s:
            m["obs_interval_s"] = self.obs_interval_s
            m["snapshot_age_s_max"] = (max(self.snapshot_ages)
                                       if self.snapshot_ages else 0)
            m["failure_discovery_latency_s"] = (
                (self.failure_discovery_t - self.failure_t)
                if self.failure_discovery_t is not None else None)
        return m

    def _run_config(self) -> Dict[str, Any]:
        return {
            "experiment": "experiment4",
            "sub_experiment": self.sub,
            "arm_id": self.arm_id,
            "arm": dict(self.arm),
            "scenario_id": self.scenario["id"],
            "seed": self.seed,
            "manager": self._manager_label,
            "manager_kind": (self.manager.manager_kind
                             if hasattr(self.manager, "manager_kind") else self._manager_label),
            "disruption": self.scenario["disruption"],
            "urgency": self.scenario["urgency"],
            "workload": self.scenario["workload"],
            "duration_s": self.duration_s,
            "mission_release_t_s": self.release_t,
            "disruption_t_s": self.disruption_t,
            "failure_t_s": self.failure_t,
            "periodic_decision_s": self.periodic_s,
            "obs_interval_s": self.obs_interval_s,
            "llm_model": getattr(self.manager, "model", None),
            "prompt_version": getattr(self.manager, "prompt_version", None),
            "candidate_table_version": "2.1.0",
            "matrix_version": int(self.e4.get("version", 1)),
            "matrix_hash": sha256_hex(self.e4),
        }

    def shutdown(self) -> None:
        super().shutdown()  # writes metrics.json (E4 polymorphic) + E2 run_config
        (self.run_dir / "run_config.yaml").write_text(
            yaml.safe_dump(self._run_config(), sort_keys=False, allow_unicode=True),
            encoding="utf-8")


# ----------------------------------------------------------------------
# 4B — Inference Latency (Mode B delayed execution)
# ----------------------------------------------------------------------
class Experiment4BRunner(Experiment4Runner):
    def __init__(self, cfg: Dict[str, Any], e4_cfg: Dict[str, Any],
                 sub: str, arm: Dict[str, Any], scenario: Dict[str, Any],
                 manager, sumo_cfg: Path, run_dir: Path, seed: int,
                 phase3_config: Optional[Dict[str, Any]] = None):
        super().__init__(cfg, e4_cfg, sub, arm, scenario, manager, sumo_cfg,
                         run_dir, seed, phase3_config=phase3_config)
        self.delay_s = int(arm.get("delay_s", 0))
        self.pending_actions: List[Dict[str, Any]] = []
        self._mission_version: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Periodic re-decision is suppressed while a deferred (pending) action for
    # that mission is still in flight.  Without this, arms with delay_s >=
    # periodic_s re-decide every tick and supersede their own pending action
    # before it can ever execute (a decide->supersede->decide livelock that
    # leaves the mission WAITING until the deadline).
    # ------------------------------------------------------------------
    def _periodic_due(self) -> bool:
        t = self.t
        if self.critical_t is None or t <= self.critical_t:
            return False
        if self.periodic_s is None:
            return False
        if (t - self.critical_t) % self.periodic_s != 0:
            return False
        for mid, m in self.registry.missions.items():
            if m.status in ("WAITING", "NEEDS_REPLAN", "INTERRUPTED"):
                if not any(pa["normalized_action"].get("mission_id") == mid
                           for pa in self.pending_actions):
                    return True
        return False

    # ------------------------------------------------------------------
    def _apply_valid_action(self, t: int, decision: Dict[str, Any],
                            raw_action: Dict[str, Any],
                            normalized_action: Dict[str, Any]) -> None:
        if self.delay_s <= 0:
            return super()._apply_valid_action(t, decision, raw_action, normalized_action)
        mid = normalized_action.get("mission_id")
        # task versioning: a new decision for the same mission supersedes any
        # older pending action (they are now stale).
        ver = self._mission_version.get(mid, 0) + 1
        self._mission_version[mid] = ver
        for old in list(self.pending_actions):
            if old["normalized_action"].get("mission_id") == mid:
                self.pending_actions.remove(old)
                self._record_action(old["capture_t"],
                                    old["normalized_action"].get("type"),
                                    old["normalized_action"].get("aircraft_id"),
                                    mid, old["normalized_action"].get("target_site"),
                                    old["normalized_action"].get("route"),
                                    "SUPERSEDED", old["decision"]["decision_id"])
                self._write_action_pipeline(old["capture_t"],
                                            old["decision"]["decision_id"],
                                            old["raw_action"], old["normalized_action"],
                                            None, "SUPERSEDED")
        self.pending_actions.append({
            "decision": decision,
            "raw_action": raw_action,
            "normalized_action": normalized_action,
            "capture_t": t,
            "execute_t": t + self.delay_s,
            "version": ver,
        })
        self._write_action_pipeline(t, decision["decision_id"], raw_action,
                                    normalized_action, None, "DEFERRED")
        self._record_action(t, normalized_action.get("type"),
                            normalized_action.get("aircraft_id"),
                            normalized_action.get("mission_id"),
                            normalized_action.get("target_site"),
                            normalized_action.get("route"), "DEFERRED",
                            decision["decision_id"])

    # ------------------------------------------------------------------
    def _action_no_longer_needed(self, action: Dict[str, Any]) -> bool:
        """Idempotency / dedup guard: skip actions whose effect already holds."""
        mid = action.get("mission_id")
        atype = action.get("type")
        if not mid or mid not in self.registry.missions:
            return True
        m = self.registry.missions[mid]
        if m.status in ("COMPLETED", "CANCELLED", "FAILED"):
            return True
        if atype == "GROUND_FALLBACK":
            return m.mode == "GROUND"
        if atype in ("DISPATCH", "REASSIGN"):
            acid = action.get("aircraft_id")
            return (m.assigned_resource == acid
                    and m.status in ("ASSIGNED", "EN_ROUTE"))
        return False

    def _process_pending_actions(self, now: int) -> None:
        for pa in list(self.pending_actions):
            if pa["execute_t"] != now:
                continue
            self.pending_actions.remove(pa)
            decision = pa["decision"]
            did = decision["decision_id"]
            self.checker.current_t = now
            self._refresh_failure_state()
            gs_now = self._build_gs(now, record=False)
            action_now = self._normalize_action(copy.deepcopy(pa["normalized_action"]))

            if self._action_no_longer_needed(action_now):
                self._record_action(now, action_now.get("type"),
                                    action_now.get("aircraft_id"),
                                    action_now.get("mission_id"),
                                    action_now.get("target_site"),
                                    action_now.get("route"), "SUPERSEDED", did)
                self._write_action_pipeline(now, did, pa["raw_action"], action_now,
                                            None, "SUPERSEDED")
                continue

            sem = self.semantic.validate(action_now, gs_now)
            if not sem["valid"]:
                self._record_violation(now, action_now, sem["error_types"], did)
                self._record_action(now, action_now.get("type"),
                                    action_now.get("aircraft_id"),
                                    action_now.get("mission_id"),
                                    action_now.get("target_site"),
                                    action_now.get("route"), "STALE_REJECTED", did)
                self._write_action_pipeline(now, did, pa["raw_action"], action_now,
                                            None, "STALE_REJECTED")
                self._run_manager(now)
                continue

            res = self.checker.check(action_now)
            if not res["valid"]:
                self._record_violation(now, action_now, res["violations"], did)
                self._record_action(now, action_now.get("type"),
                                    action_now.get("aircraft_id"),
                                    action_now.get("mission_id"),
                                    action_now.get("target_site"),
                                    action_now.get("route"), "STALE_REJECTED", did)
                self._write_action_pipeline(now, did, pa["raw_action"], action_now,
                                            None, "STALE_REJECTED")
                self._run_manager(now)
                continue

            executed = copy.deepcopy(action_now)
            self._execute_manager_action(now, action_now, decision)
            self._write_action_pipeline(now, did, pa["raw_action"], action_now,
                                        executed, "ISSUED")

    def _metrics(self) -> Dict[str, Any]:
        m = super()._metrics()
        actions = self._read_actions()
        m["delay_s"] = self.delay_s
        m["deferred_action_count"] = sum(1 for a in actions if a.get("result") == "DEFERRED")
        m["stale_rejected_count"] = sum(1 for a in actions if a.get("result") == "STALE_REJECTED")
        m["superseded_action_count"] = sum(1 for a in actions if a.get("result") == "SUPERSEDED")
        return m


# ----------------------------------------------------------------------
# 4C — Global State Scale (input burden ONLY)
# ----------------------------------------------------------------------
class Experiment4CRunner(Experiment4Runner):
    def __init__(self, cfg: Dict[str, Any], e4_cfg: Dict[str, Any],
                 sub: str, arm: Dict[str, Any], scenario: Dict[str, Any],
                 manager, sumo_cfg: Path, run_dir: Path, seed: int,
                 phase3_config: Optional[Dict[str, Any]] = None):
        import random
        scale_cfg = scenario.get("scale", {})
        rng = random.Random(seed)
        n_distractor = max(0, int(arm["fleet_n"]) - len(FLEET))
        dist = generate_distractors(cfg, n_distractor, rng, scale_cfg)
        self.e4_n = int(arm["fleet_n"])
        self.e4_n_distractor = n_distractor
        self.e4_distractor_aircraft = dist["distractor_aircraft"]
        self.e4_distractor_sites = dist["distractor_sites"]
        self.e4_distractor_missions = dist["distractor_missions"]

        # Inject inert distractor landing sites into facilities BEFORE the E2
        # machinery (candidate evaluator / checker / semantic) is built.
        cfg = copy.deepcopy(cfg)
        cfg["facilities"].update({name: dict(s) for name, s in self.e4_distractor_sites.items()})
        super().__init__(cfg, e4_cfg, sub, arm, scenario, manager, sumo_cfg,
                         run_dir, seed, phase3_config=phase3_config)

    # ------------------------------------------------------------------
    # add inert distractors AFTER the frozen base fleet is fully realized
    # (so they never perturb the shared seed RNG stream / base realization).
    # ------------------------------------------------------------------
    def setup(self) -> None:
        super().setup()
        for d in self.e4_distractor_aircraft:
            ac = Aircraft(d["id"], d["role"], d["lat"], d["lon"],
                          status="UNAVAILABLE", commandable=False,
                          reassignable=False, mission_id=None)
            ac.landing_site_compatibility = list(d["landing_site_compatibility"])
            ac.battery_pct = float(d["battery_pct"])
            ac.remaining_endurance_s = float(d["remaining_endurance_s"])
            self.registry.add_aircraft(ac)
            self.aircraft_role[d["id"]] = d["role"]
            self.aircraft_dest[d["id"]] = None
        for dm in self.e4_distractor_missions:
            m = Mission(dm["id"], dm["type"], dm["priority"], dm["origin"],
                        dm["destination"], deadline_s=dm["deadline_s"],
                        assigned_resource=dm["aircraft"], mode="AIR",
                        status="COMPLETED")
            self.registry.add_mission(m)
            self._record_mission(0, m)

    # ------------------------------------------------------------------
    # selection-quality: is the manager's chosen resource a LEGAL candidate,
    # an ILLEGAL (distractor) candidate, or ABSENT from the table entirely?
    # ------------------------------------------------------------------
    def _record_selection_quality(self, decision: Dict[str, Any],
                                  gs: Dict[str, Any]) -> None:
        rows = gs.get("candidates", {}).get("air", [])
        legal_ids = {c.get("resource_id") for c in rows if c.get("legal")}
        all_ids = {c.get("resource_id") for c in rows}
        self._legal_candidate_counts.append(len(legal_ids))
        sel = decision.get("selected") or {}
        rid = sel.get("resource")
        if not rid or rid == "GROUND":
            return
        if rid in legal_ids:
            self._selection_quality["legal"] += 1
        elif rid in all_ids:
            self._selection_quality["illegal"] += 1
        else:
            self._selection_quality["absent"] += 1

    def _read_violations(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        p = self.run_dir / "violations.csv"
        if p.exists():
            with open(p, newline="") as f:
                for r in csv.DictReader(f):
                    rows.append(r)
        return rows

    def _used_aircraft(self) -> set:
        used = set()
        for d in self.manager_decisions:
            sel = d.get("selected") or {}
            if sel.get("resource") and sel.get("resource") != "GROUND":
                used.add(sel["resource"])
        for a in self._read_actions():
            if a.get("result") == "ISSUED" and a.get("aircraft_id"):
                used.add(a["aircraft_id"])
        return used

    def _metrics(self) -> Dict[str, Any]:
        m = super()._metrics()
        m["fleet_n"] = self.e4_n
        m["n_distractor"] = self.e4_n_distractor
        m["num_aircraft_in_gs"] = len(self.registry.aircraft)
        m["num_landing_sites"] = len([k for k in self.cfg["facilities"]
                                      if k.startswith(("V", "DX"))])
        m["num_missions"] = len(self.registry.missions)
        # input-scale invariant: the legal candidate count must be IDENTICAL
        # across arms (distractors only add illegal rows).
        m["legal_candidate_count_mean"] = (
            round(sum(self._legal_candidate_counts) / len(self._legal_candidate_counts), 3)
            if self._legal_candidate_counts else None)
        m["legal_selection_count"] = self._selection_quality["legal"]
        m["illegal_selection_count"] = self._selection_quality["illegal"]
        m["absent_selection_count"] = self._selection_quality["absent"]

        pipeline = self._read_action_pipeline()
        m["constraint_violation_count"] = sum(
            1 for p in pipeline if p.get("result") in ("REJECTED", "REJECTED_SEMANTIC"))
        m["infeasible_air_action_count"] = sum(
            1 for p in pipeline
            if p.get("result") == "REJECTED"
            and (p.get("raw_action") or {}).get("type") in
            ("DISPATCH", "REASSIGN", "DIVERT", "REROUTE"))

        viols = self._read_violations()
        m["duplicate_assignment_count"] = sum(
            1 for v in viols if "DUPLICATE_ASSIGNMENT" in str(v.get("violations", "")))
        m["priority_inversion_count"] = sum(
            1 for v in viols if "PRIORITY_VIOLATION" in str(v.get("violations", "")))

        used = self._used_aircraft()
        m["forgotten_aircraft_count"] = sum(
            1 for acid, ac in self.registry.aircraft.items()
            if acid not in used and ac.status == "AVAILABLE"
            and ac.commandable and ac.c2_status == "NORMAL")
        return m
