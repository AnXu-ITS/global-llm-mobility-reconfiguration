"""Phase 2 orchestrator — closed loop with the formal Rule-Based Manager and the
C2 Lost Link failure (F1), with a manager-independent local contingency.

Data flow (per the Phase-2 contract):

    Global State  ->  Rule-Based Manager (ManagerAction)
                  ->  FeasibilityChecker
                  ->  Executor
                  ->  Simulators (SUMO / BlueSky)

The Phase-1 deterministic dispatch path (`orchestrator/orchestrator.py`) is left
untouched; this is a separate orchestrator so the Phase-1 replay stays green.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from failures.c2_lost import C2LostLink, LocalContingency
from managers.rule_based import RuleBasedManager
from orchestrator.bluesky_adapter import BlueSkyAdapter, ROLE_TO_ACTYPE
from orchestrator.candidate_info import CandidateEvaluator
from orchestrator.fleet import (FLEET, MPS_TO_KTS, ROLE_ALT_FT, ROLE_CRUISE_MS,
                                build_scene_commands, origin_latlon)
from orchestrator.geo import haversine
from orchestrator.registry import Aircraft, Mission, Registry
from orchestrator.sumo_adapter import SumoAdapter
from safety.feasibility_checker import FeasibilityChecker
from state.global_state import GlobalStateBuilder, to_json

ROOT = Path(__file__).resolve().parents[1]

ARRIVAL_RADIUS_M = 100.0

SUPPORT_CASES = ("C2_B", "C2_C")


class Phase2Orchestrator:
    def __init__(self, cfg: Dict[str, Any], sumo_cfg: Path, run_dir: Path,
                 case: str = "C2_B", gui: bool = False):
        self.cfg = cfg
        self.sumo_cfg = sumo_cfg
        self.run_dir = run_dir
        self.case = case
        self.gui = gui

        p2 = cfg.get("phase2", {})
        sched = p2.get("schedule", {})
        self.duration_s = int(sched.get("duration_s", 900))
        self.b1_close_t = sched.get("b1_close_t_s")
        self.critical_t = sched.get("critical_mission_t_s")
        self.c2_lost_t = sched.get("c2_lost_t_s")
        self.seed = sched.get("seed")
        self.audit_snapshot_times = set(sched.get("audit_snapshot_t_s", []) or [])

        self.manager_cfg = p2.get("manager", {})
        self.contingency_site = p2.get("c2_lost", {}).get("contingency_site", "V3")

        self.fac = cfg["facilities"]
        self.sumo_mapping = cfg["sumo_mapping"]
        self.b1_edge = self.sumo_mapping["B1"]["edge_id"]
        self.d1_edge = self.sumo_mapping["D1"]["edge_id"]
        self.h1_edge = self.sumo_mapping["H1"]["edge_id"]

        self.t = 0
        self.registry = Registry()
        self.checker = FeasibilityChecker(self.registry, cfg)
        self.manager = RuleBasedManager(cfg)
        self.gs_builder = GlobalStateBuilder(cfg)
        # shared candidate evaluator (Experiment-1 v2, Fix B): every manager sees
        # the same derived legal-action / ETA / violation / preemption table.
        self.candidate_evaluator = CandidateEvaluator(
            self.fac,
            dispatch_overhead_s=float(self.manager_cfg.get("dispatch_overhead_s", 0)),
            contingency_site=self.contingency_site)
        self.c2lost = C2LostLink(cfg)
        self.local_contingency = LocalContingency(cfg)

        self.aircraft_role: Dict[str, str] = {}
        self.aircraft_dest: Dict[str, Optional[str]] = {}
        self.aircraft_route: Dict[str, List[str]] = {}
        self.shuttle_pairs: Dict[str, tuple] = {}

        self.scheduled_events: List[Dict[str, Any]] = []
        self.pending_actions: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.events_since_last_decision: List[Dict[str, Any]] = []
        self.manager_decisions: List[Dict[str, Any]] = []

        self.eta_baseline: Optional[float] = None
        self.eta_last: Optional[float] = None
        self.b1_blocked = False
        self.c2_done = False

        self.support_mission_id = p2.get("critical_mission", {}).get("mission_id", "M-CRITICAL-001")
        self.support_aircraft: Optional[str] = None
        self.injected_mission_ids: Set[str] = set()
        self.ground_fallback_timers: Dict[str, int] = {}

        self.last_air: Dict[str, Any] = {}
        self.last_ground: Dict[str, Any] = {}

        self.sumo: Optional[SumoAdapter] = None
        self.bs: Optional[BlueSkyAdapter] = None

        self._t0 = time.time()
        self._setup_logs()

    # ------------------------------------------------------------------
    # logging setup
    # ------------------------------------------------------------------
    def _setup_logs(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.ground_f = open(self.run_dir / "ground_state.csv", "w", newline="")
        self.air_f = open(self.run_dir / "air_state.csv", "w", newline="")
        self.clock_f = open(self.run_dir / "clock_sync.csv", "w", newline="")
        self.event_f = open(self.run_dir / "events.csv", "w", newline="")
        self.action_f = open(self.run_dir / "actions.csv", "w", newline="")
        self.mission_f = open(self.run_dir / "missions.csv", "w", newline="")
        self.violation_f = open(self.run_dir / "violations.csv", "w", newline="")

        self.ground_w = csv.writer(self.ground_f)
        self.air_w = csv.writer(self.air_f)
        self.clock_w = csv.writer(self.clock_f)
        self.event_w = csv.writer(self.event_f)
        self.action_w = csv.writer(self.action_f)
        self.mission_w = csv.writer(self.mission_f)
        self.violation_w = csv.writer(self.violation_f)

        self.ground_w.writerow(["t", "sim_time_s", "sumo_vehicles", "b1_blocked",
                                "eta_d1_h1_s", "eta_baseline_s", "accessibility_degraded"])
        self.air_w.writerow(["t", "sim_time_s", "aircraft_id", "type", "lat", "lon",
                             "alt_m", "status", "mission_id", "dest"])
        self.clock_w.writerow(["t", "orchestrator_time", "sumo_time", "bluesky_time", "sync_ok"])
        self.event_w.writerow(["t", "event_id", "event_type", "payload"])
        self.action_w.writerow(["t", "action_type", "aircraft_id", "mission_id",
                                "target_site", "route", "result", "decision_id"])
        self.mission_w.writerow(["t", "mission_id", "type", "priority", "origin",
                                 "destination", "status", "assigned_resource"])
        self.violation_w.writerow(["t", "action_type", "aircraft_id", "mission_id",
                                   "violations", "decision_id"])

        # JSONL streams (flushed per line)
        self.manager_inputs_f = open(self.run_dir / "manager_inputs.jsonl", "w", encoding="utf-8")
        self.manager_outputs_f = open(self.run_dir / "manager_outputs.jsonl", "w", encoding="utf-8")
        self.feasibility_checks_f = open(self.run_dir / "feasibility_checks.jsonl", "w", encoding="utf-8")
        self.snapshots_f = open(self.run_dir / "snapshots.jsonl", "w", encoding="utf-8")
        # Experiment-1 Finalization §20: the shared candidate table is written
        # verbatim per decision so its (non-)leakage is independently auditable.
        self.candidate_info_f = open(self.run_dir / "candidate_info.jsonl", "w", encoding="utf-8")

    # ------------------------------------------------------------------
    # setup
    # ------------------------------------------------------------------
    def setup(self) -> None:
        self.sumo = SumoAdapter(self.sumo_cfg, step_length=1.0, gui=self.gui, seed=self.seed)
        self.sumo.start()
        self.bs = BlueSkyAdapter(self.cfg)

        self._build_registry()
        self._apply_case_setup()
        self._build_bluesky_scene()
        self.last_air = self.bs.state()

        if self.b1_close_t is not None:
            self.scheduled_events.append({"t": self.b1_close_t, "event_id": "GD1", "event_type": "B1_CLOSE"})
        if self.critical_t is not None:
            self.scheduled_events.append({"t": self.critical_t, "event_id": "NEW_CRITICAL", "event_type": "CRITICAL_MISSION"})
        if self.c2_lost_t is not None:
            self.scheduled_events.append({"t": self.c2_lost_t, "event_id": "C2_LOST", "event_type": "C2_LOST"})

    def _build_registry(self) -> None:
        for acid, role, origin, dest, pair, mid in FLEET:
            lat, lon = origin_latlon(self.cfg, origin)
            status = "BUSY" if mid else "AVAILABLE"
            ac = Aircraft(acid, role, lat, lon, status=status, mission_id=mid,
                          reassignable=(mid is None))
            ac.status = status
            if mid:
                ac.priority = self._mission_type(mid)[1]
            self.registry.add_aircraft(ac)
            self.aircraft_role[acid] = role
            self.aircraft_dest[acid] = dest
            if pair is not None:
                self.shuttle_pairs[acid] = pair

        for acid, _role, origin, dest, _pair, mid in FLEET:
            if mid is None:
                continue
            mtype, mpri = self._mission_type(mid)
            m = Mission(mid, mtype, mpri, origin or "V2", dest or "V1",
                        deadline_s=1800, assigned_resource=acid)
            m.status = "EN_ROUTE"
            self.registry.add_mission(m)
            self._record_mission(0, m)

    def _apply_case_setup(self) -> None:
        """Case-specific fleet variation (never expands the 4-aircraft fleet)."""
        if self.case == "C2_C":
            # no backup air resource: M-UAV-01 is already committed to a HIGH
            # priority medical transfer and is NOT reassignable.
            ac = self.registry.aircraft["M-UAV-01"]
            ac.status = "BUSY"
            ac.reassignable = False
            ac.priority = "HIGH"
            ac.mission_id = "M-M-BACKUP-001"
            m = Mission("M-M-BACKUP-001", "medical_transfer", "HIGH", "V1", "V3",
                        deadline_s=900, assigned_resource="M-UAV-01")
            m.status = "EN_ROUTE"
            self.registry.add_mission(m)
            self._record_mission(0, m)

    @staticmethod
    def _mission_type(mid: str):
        if mid.startswith("M-L"):
            return "logistics", "NORMAL"
        if mid.startswith("M-M"):
            return "medical_transfer", "HIGH"
        if mid.startswith("M-I"):
            return "inspection", "LOW"
        if mid.startswith("M-P"):
            return "passenger_transfer", "NORMAL"
        return "generic", "NORMAL"

    def _build_bluesky_scene(self) -> None:
        for cmd in build_scene_commands(self.cfg):
            self.bs.command(cmd)

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        for _ in range(self.duration_s):
            self._step_once()
        self.shutdown()

    def _step_once(self) -> None:
        t = self.t
        self._apply_scheduled_events(t)
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
        if now in self.audit_snapshot_times:
            self._write_snapshot(now)
        self._log(now, ground, air)

    # ------------------------------------------------------------------
    # scheduled events
    # ------------------------------------------------------------------
    def _apply_scheduled_events(self, t: int) -> None:
        for ev in list(self.scheduled_events):
            if ev["t"] != t:
                continue
            etype = ev["event_type"]
            if etype == "B1_CLOSE":
                self._on_b1_close(t)
            elif etype == "CRITICAL_MISSION":
                self._on_critical_mission(t)
            elif etype == "C2_LOST":
                self._apply_c2_lost(t)
            self.scheduled_events.remove(ev)

    def _on_b1_close(self, t: int) -> None:
        self.sumo.set_edge_disallowed(self.b1_edge, True)
        self.b1_blocked = True
        self._record_event(t, "GD1", "GROUND_DISRUPTION",
                           {"edge": self.b1_edge, "action": "closed"})

    def _on_critical_mission(self, t: int) -> None:
        cm = self.cfg["phase2"]["critical_mission"]
        mid = cm["mission_id"]
        m = Mission(mid, cm["type"], cm["priority"], cm["origin"], cm["destination"],
                    deadline_s=cm["deadline_s"], ground_fallback=cm["ground_fallback"])
        self.registry.add_mission(m)
        self.injected_mission_ids.add(mid)
        self._record_mission(t, m)
        self._record_event(t, "NEW_CRITICAL_MISSION", "MISSION",
                           {"mission": mid, "priority": cm["priority"],
                            "origin": cm["origin"], "destination": cm["destination"]})
        self._run_manager(t)

    def _apply_c2_lost(self, t: int) -> None:
        if self.c2_done:
            return
        self.c2_done = True
        target = self._c2_target()
        ac = self.registry.aircraft[target]
        mid = ac.mission_id
        mission = self.registry.missions.get(mid) if mid else None

        # F1 state mutation (aircraft + mission)
        change = self.c2lost.trigger(ac, mission)
        if mid:
            ac.mission_id = None  # aircraft abandons the mission for contingency
            self._record_mission(t, mission)

        # local contingency: immediate, independent of the manager
        plan = self.local_contingency.plan(target)
        self.aircraft_dest[target] = plan["target_site"]
        role = self.aircraft_role[target]
        self.bs.fly_to(target, plan["target_site"],
                       alt_ft=ROLE_ALT_FT[role], spd_kts=ROLE_CRUISE_MS[role] * MPS_TO_KTS)

        self._record_event(t, "C2_LOST", "C2_LOST", change)
        self._record_event(t, "LOCAL_CONTINGENCY", "LOCAL_CONTINGENCY", plan)
        if mission:
            self._record_event(t, "MISSION_INTERRUPTED", "MISSION",
                               {"mission": mid, "status": mission.status})

        # rule-manager reconfiguration (after local contingency has fired)
        self._run_manager(t)

    def _c2_target(self) -> str:
        if self.case == "C2_A":
            return "L-UAV-01"
        return self.support_aircraft or "M-UAV-02"

    # ------------------------------------------------------------------
    # manager decision pipeline
    # ------------------------------------------------------------------
    def _run_manager(self, t: int) -> None:
        gs = self._build_gs(t)
        self.manager_inputs_f.write(to_json(gs) + "\n")
        self.manager_inputs_f.flush()

        decision = self.manager.decide(gs)
        self.manager_decisions.append(decision)
        self.manager_outputs_f.write(json.dumps(
            decision, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.manager_outputs_f.flush()
        self.events_since_last_decision = []  # reset for the next decision window

        action = decision.get("action")
        if action is None:
            return  # NOOP

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
            return

        self._execute_manager_action(t, action, decision)

    def _ground_snapshot(self) -> Dict[str, Any]:
        eta = self.sumo.get_route_eta(self.d1_edge, self.h1_edge)
        degraded = (self.eta_baseline is not None and eta is not None
                    and eta >= 2.0 * self.eta_baseline)
        return {
            "b1_blocked": self.b1_blocked,
            "eta_d1_h1": eta,
            "eta_baseline": self.eta_baseline,
            "accessibility_degraded": degraded,
            "ground_fallback_available": eta is not None,
        }

    def _trend(self, ground: Dict[str, Any]) -> Dict[str, Any]:
        prev = self.eta_last if self.eta_last is not None else self.eta_baseline
        cur = ground.get("eta_d1_h1")
        trend = "N/A"
        if prev is not None and cur is not None:
            if cur > prev:
                trend = "INCREASING"
            elif cur < prev:
                trend = "DECREASING"
            else:
                trend = "STABLE"
        return {"previous_eta_s": prev, "current_eta_s": cur, "eta_trend": trend}

    def _failure_zones(self) -> List[Dict[str, Any]]:
        b1 = self.fac["B1"]
        return [{"id": "B1", "edge_id": self.b1_edge,
                 "impact_level": b1.get("impact_level", "high"),
                 "state": "CLOSED" if self.b1_blocked else "OPEN"}]

    def _build_gs(self, t: int) -> Dict[str, Any]:
        ground = self._ground_snapshot()
        trend = self._trend(ground)
        gs = self.gs_builder.build(
            t=t, registry=self.registry, ground=ground, air=self.last_air,
            events=list(self.events_since_last_decision), trend=trend,
            new_mission_ids=self.injected_mission_ids,
            failure_zones=self._failure_zones(),
        )
        # shared candidate table (Experiment-1 Finalization) — injected for every
        # manager so B1/B2/B4b consume the same derived numbers.
        gs["candidates"] = self.candidate_evaluator.evaluate(gs)
        self.candidate_info_f.write(json.dumps(
            {"t": t, "candidate_table": gs["candidates"]},
            sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.candidate_info_f.flush()
        return gs

    def _write_snapshot(self, t: int) -> None:
        gs = self._build_gs(t)
        self.snapshots_f.write(json.dumps({"t": t, "global_state": gs},
                                          sort_keys=True, ensure_ascii=False,
                                          separators=(",", ":")) + "\n")
        self.snapshots_f.flush()

    # ------------------------------------------------------------------
    # executor
    # ------------------------------------------------------------------
    def _execute_manager_action(self, t: int, action: Dict[str, Any],
                                decision: Dict[str, Any]) -> None:
        atype = action["type"]
        if atype in ("DISPATCH", "REASSIGN"):
            self._execute_air_action(t, action, decision)
        elif atype == "GROUND_FALLBACK":
            self._execute_ground_fallback(t, action, decision)
        elif atype == "DELAY":
            self._delay_mission(t, action)
        elif atype == "CANCEL":
            self._cancel_mission(t, action)

    def _execute_air_action(self, t: int, action: Dict[str, Any],
                            decision: Dict[str, Any]) -> None:
        acid = action["aircraft_id"]
        mid = action["mission_id"]
        route = list(action.get("route", [action.get("target_site")]))
        ac = self.registry.aircraft[acid]
        # skip the first waypoint when already at it
        if route:
            first = route[0]
            f = self.fac[first]
            if haversine(ac.lat, ac.lon, f["lat"], f["lon"]) < ARRIVAL_RADIUS_M:
                route.pop(0)

        if action["type"] == "REASSIGN":
            self.registry.reassign(acid, mid)
        else:
            self.registry.assign(acid, mid)
            self.registry.en_route(mid)
        self._record_mission(t, self.registry.missions[mid])

        if route:
            self.aircraft_route[acid] = route
            self.aircraft_dest[acid] = route[0]
            role = self.aircraft_role[acid]
            self.bs.fly_to(acid, route[0], alt_ft=ROLE_ALT_FT[role],
                           spd_kts=ROLE_CRUISE_MS[role] * MPS_TO_KTS)
        else:
            self.aircraft_dest[acid] = None
            self._complete_air_mission(acid)

        self._record_action(t, action["type"], acid, mid, action.get("target_site"),
                            action.get("route"), "ISSUED", decision["decision_id"])
        self._record_event(t, "MISSION_STARTED", "MISSION",
                           {"aircraft": acid, "mission": mid, "route": action.get("route")})
        if mid == self.support_mission_id:
            self.support_aircraft = acid

    def _execute_ground_fallback(self, t: int, action: Dict[str, Any],
                                 decision: Dict[str, Any]) -> None:
        mid = action["mission_id"]
        # FIX (review §9): the physical completion time is computed by the
        # environment, never trusted from the manager's `ground_eta_s` field
        # (a manager that claimed 1 s would otherwise be evaluated on a 1 s
        # completion).  Recompute the live corridor ETA from SUMO.
        eta = self.sumo.get_route_eta(self.d1_edge, self.h1_edge)
        if eta is None:
            eta = float(action.get("ground_eta_s") or 0.0)
        self.registry.ground_fallback(mid)
        self._record_mission(t, self.registry.missions[mid])
        self.ground_fallback_timers[mid] = t + int(round(eta))
        self._record_action(t, "GROUND_FALLBACK", "GROUND", mid, None, None,
                            "ISSUED", decision["decision_id"])
        self._record_event(t, "GROUND_FALLBACK_STARTED", "MISSION",
                           {"mission": mid, "eta_s": eta, "complete_t": t + int(round(eta))})

    def _delay_mission(self, t: int, action: Dict[str, Any]) -> None:
        mid = action["mission_id"]
        self._record_action(t, "DELAY", None, mid, None, None, "ISSUED", action.get("decision_id", ""))
        self._record_event(t, "MISSION_DELAYED", "MISSION",
                           {"mission": mid, "reason": action.get("reason")})

    def _cancel_mission(self, t: int, action: Dict[str, Any]) -> None:
        mid = action["mission_id"]
        m = self.registry.missions.get(mid)
        if m:
            if m.status not in ("COMPLETED", "CANCELLED", "FAILED"):
                m.transition("CANCELLED")
            self._record_mission(t, m)
        self._record_action(t, "CANCEL", None, mid, None, None, "ISSUED", action.get("decision_id", ""))
        self._record_event(t, "MISSION_CANCELLED", "MISSION",
                           {"mission": mid, "reason": action.get("reason")})

    # ------------------------------------------------------------------
    # runtime state updates
    # ------------------------------------------------------------------
    def _collect_ground(self, now: int) -> Dict[str, Any]:
        g: Dict[str, Any] = {}
        g["vehicles"] = len(self.sumo.vehicle_ids())
        g["b1_blocked"] = self.b1_blocked
        eta = self.sumo.get_route_eta(self.d1_edge, self.h1_edge)
        g["eta_d1_h1"] = eta
        if eta is not None:
            if self.eta_baseline is None and not self.b1_blocked and now >= 10:
                self.eta_baseline = eta
            self.eta_last = eta
            g["eta_baseline"] = self.eta_baseline
            g["accessibility_degraded"] = (
                self.eta_baseline is not None and eta >= 2.0 * self.eta_baseline
            )
        else:
            g["eta_baseline"] = self.eta_baseline
            g["accessibility_degraded"] = False
        return g

    def _update_registry(self, air: Dict[str, Any]) -> None:
        for acid, st in air.items():
            ac = self.registry.aircraft.get(acid)
            if ac is None:
                continue
            ac.lat, ac.lon = st["lat"], st["lon"]
            dest = self.aircraft_dest.get(acid)
            if dest is None:
                continue
            d = self.fac[dest]
            if haversine(st["lat"], st["lon"], d["lat"], d["lon"]) < ARRIVAL_RADIUS_M:
                self._on_arrival(acid, dest)

    def _on_arrival(self, acid: str, dest: str) -> None:
        ac = self.registry.aircraft[acid]
        if ac.status == "CONTINGENCY":
            self._on_contingency_arrival(acid, dest)
            return
        route = self.aircraft_route.get(acid)
        if route:
            route.pop(0)
            if route:
                nxt = route[0]
                self.aircraft_dest[acid] = nxt
                role = self.aircraft_role[acid]
                self.bs.fly_to(acid, nxt, alt_ft=ROLE_ALT_FT[role],
                               spd_kts=ROLE_CRUISE_MS[role] * MPS_TO_KTS)
            else:
                self._complete_air_mission(acid)
            return
        if acid in self.shuttle_pairs:
            a, b = self.shuttle_pairs[acid]
            new_dest = b if dest == a else a
            self.aircraft_dest[acid] = new_dest
            role = self.aircraft_role[acid]
            self.bs.fly_to(acid, new_dest, alt_ft=ROLE_ALT_FT[role],
                           spd_kts=ROLE_CRUISE_MS[role] * MPS_TO_KTS)

    def _on_contingency_arrival(self, acid: str, dest: str) -> None:
        if dest == self.contingency_site:
            self.aircraft_dest[acid] = None
            self.bs.park(acid)
            self._record_event(self.t, "CONTINGENCY_LANDED", "LOCAL_CONTINGENCY",
                               {"aircraft": acid, "site": dest,
                                "mode": self.local_contingency.contingency_mode})

    def _complete_air_mission(self, acid: str) -> None:
        ac = self.registry.aircraft[acid]
        mid = ac.mission_id
        if not mid:
            return
        self.registry.complete_mission(mid)
        self.aircraft_dest[acid] = None
        self.aircraft_route.pop(acid, None)
        self._record_mission(self.t, self.registry.missions[mid])
        self._record_event(self.t, "MISSION_COMPLETED", "MISSION",
                           {"aircraft": acid, "mission": mid})
        self.bs.park(acid)

    def _process_ground_fallbacks(self, now: int) -> None:
        for mid in list(self.ground_fallback_timers.keys()):
            if now >= self.ground_fallback_timers[mid]:
                del self.ground_fallback_timers[mid]
                m = self.registry.missions.get(mid)
                if m and m.status not in ("COMPLETED", "CANCELLED", "FAILED"):
                    self.registry.complete_ground_mission(mid)
                    self._record_mission(now, m)
                    self._record_event(now, "GROUND_FALLBACK_COMPLETED", "MISSION",
                                       {"mission": mid})

    # ------------------------------------------------------------------
    # logging helpers
    # ------------------------------------------------------------------
    def _record_event(self, t: int, event_id: str, event_type: str, payload: Any) -> None:
        ev = {"t": t, "event_id": event_id, "event_type": event_type, "payload": payload}
        self.events.append(ev)
        self.events_since_last_decision.append(ev)
        self.event_w.writerow([t, event_id, event_type, json.dumps(payload, ensure_ascii=False)])

    def _record_action(self, t: int, action_type: str, aircraft_id: Optional[str],
                       mission_id: Optional[str], target_site: Optional[str],
                       route: Any, result: str, decision_id: str) -> None:
        self.action_w.writerow([t, action_type, aircraft_id, mission_id, target_site,
                                json.dumps(route) if route is not None else "", result, decision_id])

    def _record_mission(self, t: int, m: Mission) -> None:
        self.mission_w.writerow([t, m.id, m.type, m.priority, m.origin,
                                 m.destination, m.status, m.assigned_resource])

    def _record_violation(self, t: int, action: Dict[str, Any], violations: List[str],
                          decision_id: str) -> None:
        self.violation_w.writerow([t, action.get("type"), action.get("aircraft_id"),
                                   action.get("mission_id"), ";".join(violations), decision_id])

    def _log(self, t: int, ground: Dict[str, Any], air: Dict[str, Any]) -> None:
        sumo_t = self.sumo.get_time()
        bs_t = self.bs.get_time()
        sync_ok = abs(sumo_t - t) < 1e-6 and abs(bs_t - t) < 1e-6
        self.clock_w.writerow([t, t, f"{sumo_t:.6f}", f"{bs_t:.6f}", sync_ok])

        self.ground_w.writerow([t, t, ground["vehicles"], ground["b1_blocked"],
                                ground["eta_d1_h1"], ground["eta_baseline"],
                                ground["accessibility_degraded"]])

        for acid in sorted(air.keys()):
            st = air[acid]
            ac = self.registry.aircraft.get(acid)
            status = ac.status if ac else ""
            mission = ac.mission_id if ac else ""
            self.air_w.writerow([t, t, acid, st["type"], f"{st['lat']:.7f}", f"{st['lon']:.7f}",
                                 f"{st['alt_m']:.1f}", status, mission, self.aircraft_dest.get(acid, "")])

    # ------------------------------------------------------------------
    # shutdown
    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        self.registry.save(self.run_dir / "registry_final.json")
        metrics = self._metrics()
        (self.run_dir / "metrics.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")

        rc = {
            "scenario_id": self.cfg.get("scenario_id", "S0"),
            "scenario_version": self.cfg.get("scenario_version", "S0_3p2km_v1"),
            "phase": "phase2_rule_manager",
            "case": self.case,
            "duration_s": self.duration_s,
            "simulation_step_s": 1,
            "seed": self.seed,
            "b1_close_t": self.b1_close_t,
            "critical_mission_t_s": self.critical_t,
            "c2_lost_t_s": self.c2_lost_t,
            "manager": "rule_based",
            "llm_model": None,
            "contingency_site": self.contingency_site,
        }
        (self.run_dir / "run_config.yaml").write_text(
            yaml.safe_dump(rc, sort_keys=False, allow_unicode=True), encoding="utf-8")

        for f in (self.ground_f, self.air_f, self.clock_f, self.event_f,
                  self.action_f, self.mission_f, self.violation_f,
                  self.manager_inputs_f, self.manager_outputs_f, self.feasibility_checks_f,
                  self.snapshots_f, self.candidate_info_f):
            try:
                f.close()
            except Exception:
                pass
        if self.sumo:
            self.sumo.close()

    def _metrics(self) -> Dict[str, Any]:
        missions = self.registry.missions
        crit = missions.get(self.support_mission_id)
        return {
            "scenario_version": self.cfg.get("scenario_version"),
            "case": self.case,
            "duration_s": self.duration_s,
            "seed": self.seed,
            "num_manager_decisions": len(self.manager_decisions),
            "decision_ids": [d["decision_id"] for d in self.manager_decisions],
            "b1_eta_increase_pct": (self.eta_last and self.eta_baseline
                                    and round(100.0 * (self.eta_last - self.eta_baseline) / self.eta_baseline, 3)),
            "critical_mission_id": self.support_mission_id,
            "critical_mission_final_state": crit.status if crit else None,
            "critical_mission_final_resource": crit.assigned_resource if crit else None,
            "critical_mission_final_mode": crit.mode if crit else None,
            "support_aircraft": self.support_aircraft,
            "c2_done": self.c2_done,
            "manager": "rule_based",
            "llm_model": None,
        }
