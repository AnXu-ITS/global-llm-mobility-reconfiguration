"""Experiment 3 runner — Compound Disruption Stress Test.

Runs ONE (scenario, seed, manager) closed loop and reuses the FROZEN
Experiment-2 machinery (Global State v1 -> manager -> normalize -> semantic ->
feasibility -> executor -> SUMO/BlueSky) with the additive Experiment-3
extensions:

  - fixed ground-side context (B1 closure + M-CRITICAL-001 at t=300, deadline
    480 s) — identical for every manager and scenario;
  - a MULTI-EVENT timeline: failure-A t=360, M-CRITICAL-002 t=390 (L3/L4),
    failure-B t=420 (L2/L3/L4), failure-C t=480 (L4 only); each failure is one
    frozen F1-F6 injector composed on the timeline (exogenous, frozen in
    config/experiment3_matrix.yaml);
  - candidate table 2.2.0 (multi-mission section, emission-guarded);
  - per-event failure traces + compound metrics (system-weighted loss, cascade
    recovery, second-wave readiness, decision oscillation).

All managers (B0/B1/B2/B4b) share identical initial conditions, ground
realization, missions, air workload and failure schedule per (scenario, seed)
— paired design (protocol §28).
"""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from failures.e2_failures import INJECTORS, _critical_candidate_stats
from failures.e3_compound import register_failure_zones
from orchestrator.candidate_info_e3 import E3CandidateEvaluator
from orchestrator.experiment2_runner import Experiment2Runner, sha256_hex
from orchestrator.registry import Mission
from safety.semantic_validator_e2 import E2SemanticValidator

ROOT = Path(__file__).resolve().parents[1]

PRIORITY_WEIGHT = {"CRITICAL": 4, "HIGH": 3, "NORMAL": 2, "LOW": 1}


class Experiment3Runner(Experiment2Runner):
    def __init__(self, cfg: Dict[str, Any], e3_cfg: Dict[str, Any],
                 scenario: Dict[str, Any], manager, sumo_cfg: Path,
                 run_dir: Path, seed: int,
                 phase3_config: Optional[Dict[str, Any]] = None):
        self.e3 = e3_cfg
        self.e3_scenario = scenario
        self.level = scenario.get("level")
        self.motif = scenario.get("motif")
        self.duration_e3 = int(scenario.get("duration_s", e3_cfg.get("duration_s", 900)))
        self.failure_schedule = [copy.deepcopy(f) for f in scenario["failure_schedule"]]
        self.emergencies = list(scenario.get("emergencies", ["M-CRITICAL-001"]))
        self.second_emergency = dict(e3_cfg.get("second_emergency", {}))
        self.second_emergency_t = int(scenario.get("second_emergency_t_s",
                                                   e3_cfg.get("second_emergency_t_s", 390)))
        self.failure_traces: List[Dict[str, Any]] = []

        # Build an E2-shaped config/scenario view so the frozen Experiment2Runner
        # __init__ (candidate table 2.1.0 + E2 checker + E2 semantic + single
        # failure parse) runs unchanged; E3 state is layered on afterwards.
        first = self.failure_schedule[0]
        e2_scenario = dict(scenario)
        e2_scenario["failure"] = copy.deepcopy(first)
        e2_scenario["failure_family"] = first["family"]
        e2_scenario["impact_context"] = "C1"  # placeholder; E3 uses level/motif
        e2_cfg_view = {
            "version": 3,
            "duration_s": self.duration_e3,
            "step_s": int(e3_cfg["step_s"]),
            "mission_release_t_s": int(e3_cfg["mission_release_t_s"]),
            "disruption_t_s": int(e3_cfg["disruption_t_s"]),
            "periodic_decision_s": int(e3_cfg["periodic_decision_s"]),
            "failure_t_s": int(first["time_s"]),
            "emergency_mission": dict(e3_cfg["primary_emergency"]),
            "disruptions": {k: dict(v) for k, v in e3_cfg["disruptions"].items()},
            "urgencies": {k: dict(v) for k, v in e3_cfg["urgencies"].items()},
            "workloads": {k: {"busy": [list(r) for r in v["busy"]],
                              "idle": list(v["idle"])}
                          for k, v in e3_cfg["workloads"].items()},
            "scenarios": [e2_scenario],
        }
        super().__init__(cfg, e2_cfg_view, e2_scenario, manager, sumo_cfg, run_dir,
                         seed, phase3_config=phase3_config)

        # Re-register ALL schedule zone geometries (the E2 __init__ only parsed
        # the first failure's zone), then rebuild the candidate evaluator and the
        # semantic validator against the FULL compound zone set.
        self.zone_geometries: Dict[str, Dict[str, Any]] = {}
        self.air_risk_zones: List[Dict[str, Any]] = []
        for f in self.failure_schedule:
            register_failure_zones(self, f)
        p2mgr = self.cfg.get("phase2", {}).get("manager", {})
        self.candidate_evaluator = E3CandidateEvaluator(
            self.fac,
            dispatch_overhead_s=float(p2mgr.get("dispatch_overhead_s", 0)),
            contingency_site=self.contingency_site,
            zone_geometries=self.zone_geometries)
        rc_path = str(ROOT / self.p3.get("resource_compatibility",
                                         "config/resource_compatibility.yaml"))
        self.semantic = E2SemanticValidator(rc_path, self.zone_geometries)
        self.semantic.set_facilities(self.cfg["facilities"])

    # ------------------------------------------------------------------
    # setup: multi-event timeline (B1_CLOSE + CRITICAL_MISSION + second
    # emergency + one AIR_FAILURE per schedule entry)
    # ------------------------------------------------------------------
    def setup(self) -> None:
        super().setup()  # schedules B1_CLOSE + CRITICAL_MISSION + ONE AIR_FAILURE(first)
        self.scheduled_events = [e for e in self.scheduled_events
                                 if e.get("event_type") != "AIR_FAILURE"]
        for idx, f in enumerate(self.failure_schedule):
            self.scheduled_events.append({"t": int(f["time_s"]),
                                          "event_id": f"AIR_FAILURE_{idx}",
                                          "event_type": "AIR_FAILURE",
                                          "failure_index": idx})
        if len(self.emergencies) >= 2 and self.second_emergency_t != self.critical_t:
            self.scheduled_events.append({"t": self.second_emergency_t,
                                          "event_id": "SECOND_EMERGENCY",
                                          "event_type": "SECOND_EMERGENCY"})
        self.scheduled_events.sort(key=lambda e: e["t"])

    def _apply_scheduled_events(self, t: int) -> None:
        for ev in list(self.scheduled_events):
            if ev["t"] != t:
                continue
            etype = ev["event_type"]
            if etype == "B1_CLOSE":
                self._on_b1_close(t)
            elif etype == "CRITICAL_MISSION":
                self._on_critical_mission(t)
            elif etype == "SECOND_EMERGENCY":
                self._on_second_emergency(t)
            elif etype == "AIR_FAILURE":
                self._apply_air_failure(t, ev)
            self.scheduled_events.remove(ev)

    def _on_second_emergency(self, t: int, run_manager: bool = True) -> None:
        em = self.second_emergency
        if not em:
            return
        deadline = t + int(em.get("deadline_slack_s", 240))
        m = Mission(em["mission_id"], em["type"], em["priority"], em["origin"],
                    em["destination"], deadline_s=deadline,
                    ground_fallback=em.get("ground_fallback", True),
                    delay_cost=em.get("delay_cost", 45.0),
                    cancellation_cost=em.get("cancellation_cost", 450.0))
        self.registry.add_mission(m)
        self.injected_mission_ids.add(em["mission_id"])
        self._record_mission(t, m)
        self._record_event(t, "NEW_SECOND_EMERGENCY", "MISSION",
                           {"mission": em["mission_id"], "priority": em["priority"],
                            "origin": em["origin"], "destination": em["destination"],
                            "deadline_s": deadline})
        if run_manager:
            self._run_manager(t)

    def _on_critical_mission(self, t: int) -> None:
        # FIX (review 20260908 P0-3): when the second emergency shares the primary
        # release instant, inject BOTH missions before the single manager decision
        # so the two emergencies genuinely compete for the scarce medical asset.
        if len(self.emergencies) >= 2 and self.second_emergency_t == t:
            self._on_second_emergency(t, run_manager=False)
        super()._on_critical_mission(t)

    # ------------------------------------------------------------------
    # failure injection (exogenous, per-event): frozen injector -> local safety
    # -> candidate-set update -> manager replanning -> checker -> execution
    # ------------------------------------------------------------------
    def _apply_air_failure(self, t: int, ev: Dict[str, Any]) -> None:
        idx = int(ev.get("failure_index", 0))
        failure_cfg = self.failure_schedule[idx]
        family = failure_cfg["family"]
        gs_pre = self._build_gs(t, record=False)
        pre_stats = _critical_candidate_stats(self, gs_pre)
        trace = INJECTORS[family](self, failure_cfg)
        gs_post = self._build_gs(t, record=False)
        post_stats = _critical_candidate_stats(self, gs_post)

        # keep the checker's failure state current for later decisions
        self.checker.set_failure_state({
            "utm_state": self.utm_state,
            "new_mission_ids": set(self.injected_mission_ids),
            "zones": [z for z in self.air_risk_zones
                      if z["active_from_s"] <= t <= z["active_until_s"]
                      and z.get("candidate_rule", "full") != "none"],
        })

        spare = sorted(acid for acid, ac in self.registry.aircraft.items()
                       if ac.status == "AVAILABLE" and ac.commandable
                       and ac.c2_status == "NORMAL")

        rec = {
            "event_index": idx,
            "failure_family": family,
            "failure_time": t,
            "target": (failure_cfg.get("target") or failure_cfg.get("site")
                       or failure_cfg.get("utm_state") or "UNKN-01"),
            "failure_config": failure_cfg,
            "failure_config_hash": sha256_hex(failure_cfg),
            "state_before": trace["state_before"],
            "state_after": trace["state_after"],
            "affected_resources": trace["affected_resources"],
            "candidate_count_pre_event": pre_stats["count"],
            "candidate_count_after": post_stats["count"],
            "candidate_count_after_label": post_stats["source"],
            "candidate_best_air_eta_pre_asif": pre_stats["best_eta_s"],
            "candidate_best_air_eta_after": post_stats["best_eta_s"],
            "ground_candidate_feasible_post": post_stats["ground_feasible"],
            "ground_eta_post": post_stats["ground_eta_s"],
            "candidate_set_pre_hash": sha256_hex(gs_pre.get("candidates", {}).get("air", [])),
            "candidate_set_post_hash": sha256_hex(gs_post.get("candidates", {}).get("air", [])),
            "local_contingency": trace["local_contingency"],
            "manager_trigger_time": t,
            "spare_aircraft": spare,
            "critical_mission_state_before": trace["state_before"]["missions"].get(
                self.support_mission_id),
            "critical_mission_state_after": trace["state_after"]["missions"].get(
                self.support_mission_id),
        }
        if idx == 0:
            rec["candidate_count_before"] = self.initial_critical_air_count
            rec["candidate_count_before_label"] = "t300_decision_table"
        self.failure_traces.append(rec)
        if self.failure_trace is None:
            self.failure_trace = rec  # first event, for E2-backward-compat metrics

        self._run_manager(t)

    # ------------------------------------------------------------------
    # periodic trigger: continue while EITHER emergency is actionable (L3/L4)
    # ------------------------------------------------------------------
    def _periodic_due(self) -> bool:
        # FIX (review 20260908 P0-2): trigger on ANY actionable mission, not just
        # the emergency missions — otherwise background services left NEEDS_REPLAN
        # are never recovered (the L2 "+100 SWL" attribution error).
        t = self.t
        if self.critical_t is None or t <= self.critical_t:
            return False
        if (t - self.critical_t) % self.periodic_s != 0:
            return False
        for m in self.registry.missions.values():
            if m.status in ("WAITING", "NEEDS_REPLAN", "INTERRUPTED"):
                return True
        return False

    # ------------------------------------------------------------------
    # metrics: inherited E1/E2 (first event) + compound additions
    # ------------------------------------------------------------------
    def _metrics(self) -> Dict[str, Any]:
        m = super()._metrics()  # E2 metrics on the first event + E1 metrics
        m["experiment"] = "experiment3"
        m["level"] = self.level
        m["motif"] = self.motif
        m["num_failure_events"] = len(self.failure_traces)

        total, by_prio, by_mission = self._system_weighted_loss()
        m["system_weighted_loss"] = round(total, 3)
        m["system_weighted_loss_by_priority"] = {k: round(v, 3)
                                                 for k, v in by_prio.items()}
        m["system_weighted_loss_by_mission"] = {k: round(v, 3)
                                                for k, v in by_mission.items()}

        m["spare_aircraft_at_second_failure"] = (
            self.failure_traces[1].get("spare_aircraft") if len(self.failure_traces) >= 2
            else None)
        m["cascade_recovery"] = self._cascade_recovery()
        m["decision_oscillation_count"] = self._decision_oscillation_count()
        # FIX (review 20260908 P1-1): these two were previously missing entirely.
        # Emitted as explicit null (N/A) until a per-decision competition-instant
        # detector is implemented; the review permits N/A when no competitive
        # moment exists. See CHANGELOG 2026-09-08.
        m["resource_competition_correct"] = None
        m["priority_consistency_violations"] = None
        return m

    def _completion_t(self, mid: str) -> Optional[int]:
        for ev in self.events:
            if ev["event_id"] in ("MISSION_COMPLETED", "GROUND_FALLBACK_COMPLETED") \
                    and (ev.get("payload") or {}).get("mission") == mid:
                return int(ev["t"])
        return None

    # FIX (review 20260908 P0-1): align the implementation with the frozen SWL
    # definition (§A). Only CANCELLED/FAILED/INTERRUPTED/NEEDS_REPLAN/WAITING are
    # charged cancellation; a normal ongoing EN_ROUTE/ASSIGNED service is NOT.
    SWL_CHARGED_STATES = ("CANCELLED", "FAILED", "INTERRUPTED", "NEEDS_REPLAN", "WAITING")

    def _system_weighted_loss(self):
        total = 0.0
        by_prio: Dict[str, float] = {}
        by_mission: Dict[str, float] = {}
        for mid, msn in self.registry.missions.items():
            w = PRIORITY_WEIGHT.get(msn.priority, 1)
            if msn.status == "COMPLETED":
                ct = self._completion_t(mid)
                loss = (msn.delay_cost if (ct is not None and msn.deadline_s is not None
                                           and ct > msn.deadline_s) else 0.0)
            elif msn.status in self.SWL_CHARGED_STATES:
                loss = msn.cancellation_cost
            else:
                loss = 0.0  # EN_ROUTE / ASSIGNED — normal in-flight service
            contrib = w * float(loss)
            total += contrib
            by_prio[msn.priority] = by_prio.get(msn.priority, 0.0) + contrib
            by_mission[mid] = contrib
        return total, by_prio, by_mission

    def _cascade_recovery(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        actions = self._read_actions()
        for i, tr in enumerate(self.failure_traces):
            t_e = int(tr["failure_time"])
            rec_ev = next((e for e in self.events
                           if int(e["t"]) >= t_e
                           and e["event_id"] in ("MISSION_STARTED", "GROUND_FALLBACK_STARTED")
                           and (e.get("payload") or {}).get("mission") == self.support_mission_id),
                          None)
            post_issued = [a for a in actions
                           if a.get("result") == "ISSUED" and int(a.get("t") or 0) >= t_e]
            # FIX (review 20260908 P1-1): derive mode from the FIRST recovery event
            # (MISSION_STARTED => AIR, GROUND_FALLBACK_STARTED => GROUND), not from
            # "whether ANY ground recovery ever occurred later" (which backfilled
            # air-then-ground sequences to GROUND).
            out.append({
                "event_index": i,
                "failure_time": t_e,
                "recovery_success": bool(rec_ev is not None),
                "recovery_mode": ("GROUND" if rec_ev is not None
                                  and rec_ev["event_id"] == "GROUND_FALLBACK_STARTED"
                                  else ("AIR" if rec_ev is not None else None)),
                "recovery_time_s": (int(rec_ev["t"]) - t_e) if rec_ev is not None else None,
                "failure_to_replan_latency_s": (int(post_issued[0]["t"]) - t_e)
                if post_issued else None,
            })
        return out

    def _decision_oscillation_count(self) -> int:
        issued = [a for a in self._read_actions() if a.get("result") == "ISSUED"]
        issued.sort(key=lambda a: int(a.get("t") or 0))
        last: Dict[str, str] = {}
        osc = 0
        for a in issued:
            mid = a.get("mission_id")
            atype = a.get("action_type")
            if not mid or atype not in ("DISPATCH", "REASSIGN", "DIVERT",
                                        "REROUTE", "GROUND_FALLBACK"):
                continue
            sig = ("GROUND" if atype == "GROUND_FALLBACK"
                   else "AIR:" + str(a.get("aircraft_id") or ""))
            if mid in last and last[mid] != sig:
                osc += 1
            last[mid] = sig
        return osc

    # ------------------------------------------------------------------
    # shutdown: full multi-event failure trace + E3 run_config
    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        super().shutdown()  # E2 shutdown (metrics.json + failure_trace.json + runtime.json)

        (self.run_dir / "failure_traces.json").write_text(
            json.dumps(self.failure_traces, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8")
        rc = {
            "experiment": "experiment3",
            "scenario_id": self.e3_scenario["id"],
            "level": self.level,
            "motif": self.motif,
            "seed": self.seed,
            "manager": self._manager_label,
            "manager_kind": self.manager.manager_kind if hasattr(self.manager, "manager_kind") else self._manager_label,
            "disruption": self.e3_scenario["disruption"],
            "urgency": self.e3_scenario.get("urgency", "CRITICAL"),
            "workload": self.e3_scenario["workload"],
            "duration_s": self.duration_e3,
            "mission_release_t_s": self.release_t,
            "disruption_t_s": self.disruption_t,
            "second_emergency_t_s": (self.second_emergency_t
                                     if len(self.emergencies) >= 2 else None),
            "periodic_decision_s": self.periodic_s,
            "llm_model": getattr(self.manager, "model", None),
            "prompt_version": getattr(self.manager, "prompt_version", None),
            "candidate_table_version": "2.2.0",
            "matrix_version": int(self.e3.get("version", 1)),
            "failure_schedule": self.failure_schedule,
            "failure_schedule_hash": sha256_hex(self.failure_schedule),
        }
        (self.run_dir / "run_config.yaml").write_text(
            yaml.safe_dump(rc, sort_keys=False, allow_unicode=True), encoding="utf-8")
