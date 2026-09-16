"""Experiment 2 runner — Air-Layer Failure Management.

Runs ONE (scenario, seed, manager) closed loop and reuses the FROZEN
Phase-2/3 machinery (Global State v1 -> manager -> normalize -> semantic ->
feasibility -> executor -> SUMO/BlueSky) with the additive Experiment-2
extensions:

  - fixed ground-side context (B1 closure + M-CRITICAL-001 at t=300, deadline
    480 s, duration 900 s) — identical for every manager and scenario;
  - ONE air-layer failure injected at t=360, exogenous (frozen in
    config/experiment2_matrix.yaml): failure -> local safety -> candidate-set
    update -> manager replanning -> checker -> execution;
  - candidate table 2.1.0, E2 checker, E2 semantic validator (new files);
  - failure_trace.json artifact + Experiment-2 metrics.

All managers (B0/B1/B2/B4b) share identical initial conditions, ground
realization, critical mission, air workload and failure config per
(scenario, seed) — paired design (protocol §28).
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from failures.e2_failures import INJECTORS, _critical_candidate_stats
from managers.llm_manager import LLMManager
from orchestrator.candidate_info_e2 import E2CandidateEvaluator
from orchestrator.experiment1_runner import Experiment1Runner
from orchestrator.registry import Mission
from safety.feasibility_checker_e2 import E2FeasibilityChecker
from safety.semantic_validator_e2 import E2SemanticValidator
from state.global_state import to_json

ROOT = Path(__file__).resolve().parents[1]

# failure-related rejection codes (metric E — protocol §20)
FAILURE_VIOLATION_SUBSTRINGS = (
    "AIRCRAFT_IN_CONTINGENCY", "AIRCRAFT_NOT_COMMANDABLE", "AIRCRAFT_UNAVAILABLE",
    "GNSS_DEGRADED_AIRCRAFT", "AIRCRAFT_DEGRADED", "UTM_AIR_PROHIBITED",
    "RISK_ZONE_VIOLATION", "SITE_UNAVAILABLE", "_UNAVAILABLE",
    "C2 status", "not commandable", "aircraft CONTINGENCY", "aircraft DEGRADED",
)


def sha256_hex(obj: Any) -> str:
    if isinstance(obj, (dict, list)):
        s = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    else:
        s = str(obj)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class Experiment2Runner(Experiment1Runner):
    def __init__(self, cfg: Dict[str, Any], e2_cfg: Dict[str, Any],
                 scenario: Dict[str, Any], manager, sumo_cfg: Path,
                 run_dir: Path, seed: int,
                 phase3_config: Optional[Dict[str, Any]] = None):
        self.e2 = e2_cfg
        self.e2_scenario = scenario
        self.failure_cfg = copy.deepcopy(scenario["failure"])
        self.failure_t = int(e2_cfg["failure_t_s"])
        self.failure_family = scenario.get("failure_family")
        self.impact_context = scenario.get("impact_context")

        # build the E1-shaped config from the E2 fixed ground-side context
        # (protocol §4: MEDIUM disruption + CRITICAL urgency + frozen release).
        e1_cfg = {
            "version": 2,
            "duration_s": int(e2_cfg["duration_s"]),
            "step_s": int(e2_cfg["step_s"]),
            "mission_release_t_s": int(e2_cfg["mission_release_t_s"]),
            "disruption_t_s": int(e2_cfg["disruption_t_s"]),
            "periodic_decision_s": int(e2_cfg["periodic_decision_s"]),
            "emergency_mission": dict(e2_cfg["emergency_mission"]),
            "disruptions": {k: dict(v) for k, v in e2_cfg["disruptions"].items()},
            "urgencies": {k: dict(v) for k, v in e2_cfg["urgencies"].items()},
            "workloads": {k: {"busy": [list(r) for r in v["busy"]],
                              "idle": list(v["idle"])}
                          for k, v in e2_cfg["workloads"].items()},
            "scenarios": [scenario],
        }
        super().__init__(cfg, e1_cfg, scenario, manager, sumo_cfg, run_dir, seed,
                         phase3_config=phase3_config)

        # --------------------------------------------------------------
        # Experiment-2 extension state
        # --------------------------------------------------------------
        self.utm_state = "NOMINAL"
        self.zone_geometries: Dict[str, Dict[str, Any]] = {}
        self.air_risk_zones: List[Dict[str, Any]] = []
        self.diverted_aircraft: Dict[str, str] = {}
        self.failure_trace: Optional[Dict[str, Any]] = None
        self.initial_critical_air_count: Optional[int] = None
        self.initial_gs_hash: Optional[str] = None
        self._parse_failure_cfg()

        # swap in the E2 candidate evaluator / checker / semantic validator
        p2mgr = self.cfg.get("phase2", {}).get("manager", {})
        self.candidate_evaluator = E2CandidateEvaluator(
            self.fac,
            dispatch_overhead_s=float(p2mgr.get("dispatch_overhead_s", 0)),
            contingency_site=self.contingency_site,
            zone_geometries=self.zone_geometries)
        self.checker = E2FeasibilityChecker(self.registry, self.cfg)
        self.checker.current_t = 0
        rc_path = str(ROOT / self.p3.get("resource_compatibility",
                                         "config/resource_compatibility.yaml"))
        self.semantic = E2SemanticValidator(rc_path, self.zone_geometries)
        self.semantic.set_facilities(self.cfg["facilities"])

    # ------------------------------------------------------------------
    def _parse_failure_cfg(self) -> None:
        f = self.failure_cfg
        zone = f.get("zone")
        if zone is not None:
            z = dict(zone)
            self.zone_geometries[z["id"]] = z
            self.air_risk_zones.append(z)
        env = f.get("envelope")
        if env is not None:
            e = dict(env)
            self.zone_geometries[e["id"]] = e
            self.air_risk_zones.append(e)

    # ------------------------------------------------------------------
    # setup: schedule the (single) air failure
    # ------------------------------------------------------------------
    def setup(self) -> None:
        super().setup()
        self.scheduled_events.append({"t": self.failure_t, "event_id": "AIR_FAILURE",
                                      "event_type": "AIR_FAILURE"})

    def _on_critical_mission(self, t: int) -> None:
        # extra scenario mission (F3-C1's M-L-002) is released BEFORE the
        # critical mission so the t=300 Global State shows both new missions.
        em = self.e2_scenario.get("extra_mission")
        if em:
            m = Mission(em["id"], em["type"], em["priority"], em["origin"],
                        em["destination"], deadline_s=em["deadline_s"],
                        ground_fallback=em.get("ground_fallback", False),
                        delay_cost=em.get("delay_cost", 10.0),
                        cancellation_cost=em.get("cancellation_cost", 100.0))
            self.registry.add_mission(m)
            self.injected_mission_ids.add(em["id"])
            self._record_mission(t, m)
        super()._on_critical_mission(t)

    def _apply_scheduled_events(self, t: int) -> None:
        for ev in list(self.scheduled_events):
            if ev["t"] != t:
                continue
            etype = ev["event_type"]
            if etype == "B1_CLOSE":
                self._on_b1_close(t)
            elif etype == "CRITICAL_MISSION":
                self._on_critical_mission(t)
            elif etype == "AIR_FAILURE":
                self._apply_air_failure(t)
            self.scheduled_events.remove(ev)

    # ------------------------------------------------------------------
    # failure injection (exogenous: config only, never manager-dependent)
    # ------------------------------------------------------------------
    def _apply_air_failure(self, t: int) -> None:
        family = self.failure_cfg["family"]
        gs_pre = self._build_gs(t, record=False)
        pre_stats = _critical_candidate_stats(self, gs_pre)
        trace = INJECTORS[family](self, self.failure_cfg)
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

        self.failure_trace = {
            "failure_family": family,
            "failure_time": t,
            "target": (self.failure_cfg.get("target")
                       or self.failure_cfg.get("site")
                       or self.failure_cfg.get("utm_state")
                       or "UNKN-01"),
            "failure_config": self.failure_cfg,
            "failure_config_hash": sha256_hex(self.failure_cfg),
            "state_before": trace["state_before"],
            "state_after": trace["state_after"],
            "affected_resources": trace["affected_resources"],
            "candidate_count_before": self.initial_critical_air_count,
            "candidate_count_before_label": "t300_decision_table",
            "candidate_count_pre_failure_asif": pre_stats["count"],
            "candidate_best_air_eta_pre_asif": pre_stats["best_eta_s"],
            "candidate_count_after": post_stats["count"],
            "candidate_count_after_label": post_stats["source"],
            "candidate_best_air_eta_after": post_stats["best_eta_s"],
            "ground_candidate_feasible_post": post_stats["ground_feasible"],
            "ground_eta_post": post_stats["ground_eta_s"],
            "initial_gs_hash": self.initial_gs_hash,
            "candidate_set_pre_hash": sha256_hex(gs_pre.get("candidates", {}).get("air", [])),
            "candidate_set_post_hash": sha256_hex(gs_post.get("candidates", {}).get("air", [])),
            "local_contingency": trace["local_contingency"],
            "manager_trigger_time": t,
            "first_valid_replan_time": None,  # filled at shutdown from actions.csv
            "pre_failure_gs_hash": sha256_hex({k: v for k, v in gs_pre.items()
                                               if k != "candidates"}),
            "post_failure_gs_hash": sha256_hex({k: v for k, v in gs_post.items()
                                                if k != "candidates"}),
            "critical_mission_state_before": trace["state_before"]["missions"].get(
                self.support_mission_id),
            "critical_mission_state_after": trace["state_after"]["missions"].get(
                self.support_mission_id),
        }

        # manager replanning (after local safety has fired)
        self._run_manager(t)

    # ------------------------------------------------------------------
    # GS / candidate / zones
    # ------------------------------------------------------------------
    def _failure_zones(self) -> List[Dict[str, Any]]:
        zones: List[Dict[str, Any]] = []
        for link in self.disruption_links:
            f = self.fac[link]
            zones.append({"id": link, "edge_id": self.sumo_mapping[link]["edge_id"],
                          "impact_level": f.get("impact_level", "high"),
                          "state": "CLOSED" if self.b1_blocked else "OPEN"})
        for z in self.air_risk_zones:
            active = z["active_from_s"] <= self.t <= z["active_until_s"]
            zones.append({"id": z["id"], "edge_id": "",
                          "impact_level": "high",
                          "state": "CLOSED" if active else "OPEN"})
        return zones

    def _build_gs(self, t: int, record: bool = True) -> Dict[str, Any]:
        ground = self._ground_snapshot()
        trend = self._trend(ground)
        gs = self.gs_builder.build(
            t=t, registry=self.registry, ground=ground, air=self.last_air,
            events=list(self.events_since_last_decision), trend=trend,
            new_mission_ids=self.injected_mission_ids,
            failure_zones=self._failure_zones(),
        )
        gs["infrastructure"]["utm_state"] = self.utm_state
        gs["candidates"] = self.candidate_evaluator.evaluate(gs)
        if record:
            self.candidate_info_f.write(json.dumps(
                {"t": t, "candidate_table": gs["candidates"]},
                sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
            self.candidate_info_f.flush()
        return gs

    # ------------------------------------------------------------------
    # manager pipeline bookkeeping
    # ------------------------------------------------------------------
    def _run_manager(self, t: int) -> None:
        self.checker.current_t = t
        if t == self.release_t:
            gs0 = self._build_gs(t, record=False)
            self.initial_critical_air_count = sum(
                1 for c in gs0["candidates"]["air"] if c.get("legal"))
            self.initial_gs_hash = sha256_hex({k: v for k, v in gs0.items()
                                               if k != "candidates"})
        super()._run_manager(t)

    # ------------------------------------------------------------------
    # arrival handling: diverted aircraft park at V3 (local safety)
    # ------------------------------------------------------------------
    def _on_arrival(self, acid: str, dest: str) -> None:
        if acid in self.diverted_aircraft:
            if dest == "V3":
                self.aircraft_dest[acid] = None
                self.bs.park(acid)
                self._record_event(self.t, "DIVERT_LANDED", "LOCAL_CONTINGENCY",
                                   {"aircraft": acid, "site": dest,
                                    "reason": self.diverted_aircraft[acid]})
                del self.diverted_aircraft[acid]
            return
        super()._on_arrival(acid, dest)

    # ------------------------------------------------------------------
    # metrics (Experiment-1 frozen fields + Experiment-2 additions)
    # ------------------------------------------------------------------
    def _read_action_pipeline(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        p = self.run_dir / "action_pipeline.jsonl"
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return rows

    def _read_events(self) -> List[Dict[str, Any]]:
        if not (self.run_dir / "events.csv").exists():
            return []
        with open(self.run_dir / "events.csv", newline="") as f:
            out = []
            for r in csv.DictReader(f):
                try:
                    r["payload"] = json.loads(r["payload"])
                except (json.JSONDecodeError, TypeError):
                    pass
                out.append(r)
            return out

    def _metrics(self) -> Dict[str, Any]:
        m = super()._metrics()
        m["experiment"] = "experiment2"
        m["failure_family"] = self.failure_family
        m["impact_context"] = self.impact_context
        m["failure_time"] = self.failure_t
        ft = self.failure_trace or {}
        m["failure_config_hash"] = ft.get("failure_config_hash")
        m["candidate_count_before"] = ft.get("candidate_count_before")
        m["candidate_count_after"] = ft.get("candidate_count_after")
        m["candidate_count_pre_failure_asif"] = ft.get("candidate_count_pre_failure_asif")

        crit_before = ft.get("critical_mission_state_before") or {}
        crit_after = ft.get("critical_mission_state_after") or {}
        affected = bool(
            crit_before.get("mode") == "AIR"
            and crit_before.get("status") in ("EN_ROUTE", "ASSIGNED")
            and crit_after.get("status") in ("NEEDS_REPLAN", "INTERRUPTED"))
        m["affected_critical"] = affected

        events = self._read_events()
        actions = self._read_actions()
        issued = [a for a in actions if a.get("result") == "ISSUED"]
        post_issued = [a for a in issued if int(a.get("t") or 0) >= self.failure_t]

        # recovery metrics (protocol §20 B/C/D)
        recovery_event = next((e for e in events
                               if int(e["t"]) >= self.failure_t
                               and e["event_id"] in ("MISSION_STARTED", "GROUND_FALLBACK_STARTED")
                               and (e.get("payload") or {}).get("mission") == self.support_mission_id), None)
        gf_event = next((e for e in events
                         if int(e["t"]) >= self.failure_t
                         and e["event_id"] == "GROUND_FALLBACK_STARTED"
                         and (e.get("payload") or {}).get("mission") == self.support_mission_id), None)
        m["recovery_success"] = affected and recovery_event is not None
        m["recovery_mode"] = ("GROUND" if gf_event is not None else
                              ("AIR" if recovery_event is not None else None))
        m["recovery_time_s"] = (int(recovery_event["t"]) - self.failure_t
                                if recovery_event is not None else None)
        m["failure_to_replan_latency_s"] = (int(post_issued[0]["t"]) - self.failure_t
                                            if post_issued else None)
        crit_post_issued = [a for a in post_issued
                            if a.get("mission_id") == self.support_mission_id]
        m["critical_first_valid_replan_time_s"] = (int(crit_post_issued[0]["t"])
                                                   if crit_post_issued else None)
        m["recovered_completed"] = bool(affected and m.get("critical_mission_completion_t")
                                        and m["critical_mission_completion_t"] >= self.failure_t)
        m["failure_induced_ground_fallback"] = bool(
            gf_event is not None and int(gf_event["t"]) >= self.failure_t)
        m["ground_fallback_rate"] = (m.get("critical_mission_final_mode") == "GROUND")

        # invalid proposal / failed-resource reselection (protocol §20 E/F)
        pipeline = self._read_action_pipeline()
        post_pipeline = [p for p in pipeline if int(p.get("t") or 0) >= self.failure_t]
        m["post_failure_proposals"] = len(post_pipeline)
        rejected = [p for p in post_pipeline
                    if p.get("result") in ("REJECTED", "REJECTED_SEMANTIC")]
        m["post_failure_rejected"] = len(rejected)
        fail_codes = []
        for p in rejected:
            if p.get("result") == "REJECTED_SEMANTIC":
                errs = p.get("normalized_action", {}) and []
                # semantic violations are in violations.csv / semantic_checks.jsonl;
                # reconstruct from the pipeline action against E2 rules instead:
                errs = list(self._e2_violations_for(p.get("raw_action") or {}))
            else:
                errs = list((p.get("executed_action") or {}).get("violations", []))
            if any(any(sub in str(e) for sub in FAILURE_VIOLATION_SUBSTRINGS)
                   for e in errs):
                fail_codes.append(p)
        m["post_failure_rejected_failure_related"] = len(fail_codes)

        failed_target = (self.failure_cfg.get("target")
                         or self.failure_cfg.get("site") or "")
        failed_refs = []
        for p in post_pipeline:
            raw = p.get("raw_action") or {}
            # only AIR actions can "use" a failed resource; a GROUND_FALLBACK
            # carrying the mission destination as target_site is not a
            # reselection of the failed site.
            if raw.get("type") in ("GROUND_FALLBACK", "DELAY", "CANCEL",
                                   "NO_ACTION", "ESCALATE"):
                continue
            if str(raw.get("aircraft_id")) == failed_target \
                    or str(raw.get("target_site")) == failed_target:
                failed_refs.append(p)
        m["failed_resource_reselection"] = len(failed_refs)

        # necessary ground fallback (protocol §20 I)
        m["necessary_ground_fallback"] = bool(
            affected and (ft.get("candidate_count_after") or 0) == 0)
        m["necessary_ground_fallback_correct"] = bool(
            m["necessary_ground_fallback"] and gf_event is not None)

        # decision behaviour (protocol §20 L)
        m["post_failure_issued_types"] = [a.get("action_type") for a in post_issued]
        m["post_failure_proposed_types"] = [
            (p.get("raw_action") or {}).get("type") for p in post_pipeline]

        # air resource availability (protocol §20 K)
        sb = ft.get("state_before", {}).get("air_availability", {})
        sa = ft.get("state_after", {}).get("air_availability", {})
        m["air_availability_before"] = sb
        m["air_availability_after"] = sa
        m["candidate_set_reduction_delta"] = (
            (ft.get("candidate_count_before") or 0) - (ft.get("candidate_count_after") or 0))
        return m

    def _e2_violations_for(self, action: Dict[str, Any]) -> List[str]:
        """Best-effort E2 violations for a raw proposal (semantic-rejected path)."""
        gs = None
        try:
            lines = (self.run_dir / "manager_inputs.jsonl").read_text(
                encoding="utf-8").splitlines()
            if lines:
                gs = json.loads(lines[-1])
        except Exception:  # noqa: BLE001
            gs = None
        if gs is None:
            return []
        res = self.semantic.validate(action, gs)
        if res["valid"]:
            return []
        return [e for e in res["error_types"]
                if any(sub in str(e) for sub in FAILURE_VIOLATION_SUBSTRINGS)]

    # ------------------------------------------------------------------
    # shutdown: failure_trace + run_config + runtime (E2 additions)
    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        self.registry.save(self.run_dir / "registry_final.json")
        # flush the CSV writers BEFORE reading artifacts for metrics (the csv
        # writers buffer rows; metrics must reflect what actually executed).
        for f in (self.event_f, self.action_f, self.mission_f, self.violation_f,
                  self.ground_f, self.air_f, self.clock_f):
            try:
                f.flush()
            except Exception:
                pass
        metrics = self._metrics()
        # fill first_valid_replan_time in the trace from actions.csv
        if self.failure_trace is not None:
            actions = self._read_actions()
            post_issued = [a for a in actions
                           if a.get("result") == "ISSUED"
                           and int(a.get("t") or 0) >= self.failure_t]
            self.failure_trace["first_valid_replan_time"] = (
                int(post_issued[0]["t"]) if post_issued else None)
            (self.run_dir / "failure_trace.json").write_text(
                json.dumps(self.failure_trace, indent=2, sort_keys=True,
                           ensure_ascii=False), encoding="utf-8")
        (self.run_dir / "metrics.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")

        rc = {
            "experiment": "experiment2",
            "scenario_id": self.scenario["id"],
            "failure_family": self.failure_family,
            "impact_context": self.impact_context,
            "seed": self.seed,
            "manager": self._manager_label,
            "manager_kind": self.manager.manager_kind if hasattr(self.manager, "manager_kind") else self._manager_label,
            "disruption": self.scenario["disruption"],
            "urgency": self.scenario["urgency"],
            "workload": self.scenario["workload"],
            "duration_s": self.duration_s,
            "mission_release_t_s": self.release_t,
            "disruption_t_s": self.disruption_t,
            "failure_t_s": self.failure_t,
            "periodic_decision_s": self.periodic_s,
            "llm_model": getattr(self.manager, "model", None),
            "prompt_version": getattr(self.manager, "prompt_version", None),
            "candidate_table_version": "2.1.0",
            "failure_config": self.failure_cfg,
            "failure_config_hash": (self.failure_trace or {}).get("failure_config_hash"),
        }
        (self.run_dir / "run_config.yaml").write_text(
            yaml.safe_dump(rc, sort_keys=False, allow_unicode=True), encoding="utf-8")

        runtime = {
            "wall_seconds": round(time.time() - self._t0, 3),
            "duration_s": self.duration_s,
            "num_manager_decisions": len(self.manager_decisions),
            "seed": self.seed,
            "seed_realization": self.seed_realization,
            "failure_family": self.failure_family,
            "impact_context": self.impact_context,
            "llm_calls": sum(1 for d in self.manager_decisions
                             if d.get("llm_metadata") is not None),
            "llm_latency_total_s": round(sum(
                (d.get("llm_metadata") or {}).get("latency_s", 0.0)
                for d in self.manager_decisions), 3),
            "llm_retry_total": sum(
                (d.get("llm_metadata") or {}).get("retry_count", 0)
                for d in self.manager_decisions),
            "empty_content_total": sum(
                (d.get("llm_metadata") or {}).get("empty_content_count", 0)
                for d in self.manager_decisions),
            "cache_subsecond_calls": sum(
                1 for d in self.manager_decisions
                if d.get("llm_metadata") is not None
                and (d["llm_metadata"].get("latency_s") or 0.0) < 1.0),
        }
        (self.run_dir / "runtime.json").write_text(
            json.dumps(runtime, indent=2, sort_keys=True), encoding="utf-8")

        for f in (self.ground_f, self.air_f, self.clock_f, self.event_f,
                  self.action_f, self.mission_f, self.violation_f,
                  self.manager_inputs_f, self.manager_outputs_f, self.feasibility_checks_f,
                  self.snapshots_f, self.candidate_info_f):
            try:
                f.close()
            except Exception:
                pass
        try:
            self.semantic_checks_f.close()
        except Exception:
            pass
        try:
            self.action_pipeline_f.close()
        except Exception:
            pass
        if self.sumo:
            self.sumo.close()
