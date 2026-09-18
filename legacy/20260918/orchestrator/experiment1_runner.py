"""Experiment 1 runner — Ground Disruption and Selective Air Support.

Runs ONE (scenario, seed, manager) closed loop and writes the full Phase-2/3
artifact set into runs/experiment1/<scenario>/<seed>/<manager>/.

All managers (B0/B1/B2/B4) share the identical:
    Global State v1 -> Manager -> SemanticValidator -> FeasibilityChecker -> Executor

The manager is the ONLY thing that changes between the B0/B1/B2/B4 runs of a
given (scenario, seed) pair; the ground realization (SUMO seed + disruption),
air initial state, mission release time and facility state are identical.
"""
from __future__ import annotations

import copy
import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from managers.no_cross_layer import NoCrossLayerManager
from managers.optimization import OptimizationManager
from managers.rule_based import RuleBasedManager
from orchestrator.bluesky_adapter import BlueSkyAdapter, ROLE_TO_ACTYPE
from orchestrator.fleet import (FLEET, MPS_TO_KTS, ROLE_ALT_FT, ROLE_CRUISE_MS,
                                origin_latlon)
from orchestrator.geo import bearing
from orchestrator.phase3_orchestrator import Phase3Orchestrator
from orchestrator.registry import Mission
from orchestrator.sumo_adapter import SumoAdapter

ROOT = Path(__file__).resolve().parents[1]


def make_manager(kind: str, cfg: Dict[str, Any],
                 p3: Optional[Dict[str, Any]] = None):
    """Factory for the Experiment-1 managers (B0/B1/B2/B4 + v2 arms)."""
    if kind == "B0":
        return NoCrossLayerManager(cfg)
    if kind == "B1":
        return RuleBasedManager(cfg)
    if kind == "B2":
        wpath = str(ROOT / "config" / "experiment1_b2_weights.yaml")
        return OptimizationManager(cfg, wpath)
    if kind == "B4":
        from managers.llm_manager import LLMManager
        return LLMManager(cfg, p3 or {})
    if kind in ("B4v2a", "B4v2b", "B4a", "B4b"):
        # B4a = LLM-State (prompt v2, NO candidate table)  [alias of B4-v2a]
        # B4b = LLM-Candidate (prompt v2 + shared candidate table) [alias of B4-v2b]
        from managers.llm_manager import LLMManager
        p3v = dict(p3 or {})
        p3v["prompt"] = "prompts/manager_v2.txt"
        p3v["include_candidates"] = (kind in ("B4v2b", "B4b"))
        m = LLMManager(cfg, p3v)
        if kind in ("B4a", "B4b"):
            m.manager_kind = "llm_b4a" if kind == "B4a" else "llm_b4b"
        else:
            m.manager_kind = "llm_v2a" if kind == "B4v2a" else "llm_v2b"
        return m
    raise ValueError(f"unknown manager kind {kind}")


MANAGER_NAMES = {"B0": "no_cross_layer", "B1": "rule_based",
                 "B2": "optimization", "B4": "llm",
                 "B4v2a": "llm_v2a", "B4v2b": "llm_v2b",
                 "B4a": "llm_b4a", "B4b": "llm_b4b"}


class Experiment1Runner(Phase3Orchestrator):
    def __init__(self, cfg: Dict[str, Any], e1_cfg: Dict[str, Any],
                 scenario: Dict[str, Any], manager, sumo_cfg: Path,
                 run_dir: Path, seed: int, phase3_config: Optional[Dict[str, Any]] = None):
        self.e1 = e1_cfg
        self.scenario = scenario
        self.workload = e1_cfg["workloads"][scenario["workload"]]
        self.disruption = e1_cfg["disruptions"][scenario["disruption"]]
        self.urgency = e1_cfg["urgencies"][scenario["urgency"]]
        self.emergency = e1_cfg["emergency_mission"]
        self.periodic_s = int(e1_cfg["periodic_decision_s"])
        self.release_t = int(e1_cfg["mission_release_t_s"])
        self.disruption_t = int(e1_cfg["disruption_t_s"])
        self.e1_manager = manager
        self._manager_label = getattr(manager, "manager_kind", "unknown")
        # Experiment-1 Finalization §8/§9: a per-seed, deterministic RNG drives
        # the initial-state realization (aircraft progress + battery/endurance),
        # so different seeds genuinely change the manager-visible Global State.
        self.rng = random.Random(seed)
        self.seed_positions: Dict[str, tuple] = {}
        self.seed_realization: Dict[str, Any] = {}

        # build a phase-2-shaped config from the E1 scenario so the frozen
        # Phase-2/3 machinery (GS builder, semantic validator, executor, logging)
        # runs unchanged.
        deadline = self.release_t + int(self.urgency["deadline_slack_s"])
        cfg2 = copy.deepcopy(cfg)
        cfg2["phase2"] = {
            "scenario_version": cfg.get("scenario_version", "S0_3p2km_v1"),
            "schedule": {
                "duration_s": int(e1_cfg["duration_s"]),
                "b1_close_t_s": self.disruption_t,
                "critical_mission_t_s": self.release_t,
                "c2_lost_t_s": None,
                "seed": seed,
                "audit_snapshot_t_s": [],
            },
            "critical_mission": {
                "mission_id": self.emergency["mission_id"],
                "type": self.emergency["type"],
                "priority": self.urgency["priority"],
                "origin": self.emergency["origin"],
                "destination": self.emergency["destination"],
                "deadline_s": deadline,
                "ground_fallback": self.emergency["ground_fallback"],
            },
            "manager": cfg.get("phase2", {}).get("manager", {}),
            "c2_lost": cfg.get("phase2", {}).get("c2_lost", {}),
            "cases": {},
        }
        super().__init__(cfg2, sumo_cfg, run_dir, case=scenario["id"], gui=False,
                         manager=manager, phase3_config=phase3_config or {})
        self.support_mission_id = self.emergency["mission_id"]
        self.disruption_links: List[str] = list(self.disruption["links"])

    # ------------------------------------------------------------------
    def setup(self) -> None:
        self.sumo = SumoAdapter(self.sumo_cfg, step_length=1.0, gui=self.gui, seed=self.seed)
        self.sumo.start()
        self.bs = BlueSkyAdapter(self.cfg)
        self._build_registry()
        self._apply_case_setup()
        self._apply_seed_realization()
        self._build_bluesky_scene()
        self._apply_workload_fly()
        self.last_air = self.bs.state()
        if self.b1_close_t is not None:
            self.scheduled_events.append({"t": self.b1_close_t, "event_id": "GD1", "event_type": "B1_CLOSE"})
        if self.critical_t is not None:
            self.scheduled_events.append({"t": self.critical_t, "event_id": "NEW_CRITICAL", "event_type": "CRITICAL_MISSION"})

    # ------------------------------------------------------------------
    def _apply_case_setup(self) -> None:
        """Apply the Experiment-1 workload (busy / idle aircraft)."""
        for acid, mid, mtype, mpri, origin, dest, reassignable in self.workload["busy"]:
            ac = self.registry.aircraft[acid]
            if mid not in self.registry.missions:
                m = Mission(mid, mtype, mpri, origin, dest, deadline_s=1800,
                            assigned_resource=acid)
                m.status = "EN_ROUTE"
                self.registry.add_mission(m)
                self._record_mission(0, m)
            ac.status = "BUSY"
            ac.mission_id = mid
            ac.priority = mpri
            ac.reassignable = reassignable
            self.aircraft_dest[acid] = dest
            self.shuttle_pairs[acid] = (origin, dest)
        for acid in self.workload["idle"]:
            ac = self.registry.aircraft[acid]
            ac.status = "AVAILABLE"
            ac.mission_id = None
            ac.priority = "NORMAL"
            ac.reassignable = True
            self.aircraft_dest[acid] = None
            self.shuttle_pairs.pop(acid, None)

    def _apply_workload_fly(self) -> None:
        """Start BlueSky flight for busy aircraft added by the workload."""
        for acid, _mid, _mt, _mp, _o, dest, _r in self.workload["busy"]:
            if acid in ("L-UAV-01", "EVTOL-01"):
                continue  # already flying via the FLEET scene commands
            role = self.aircraft_role.get(acid, self.registry.aircraft[acid].type)
            self.bs.fly_to(acid, dest, alt_ft=ROLE_ALT_FT[role],
                           spd_kts=ROLE_CRUISE_MS[role] * MPS_TO_KTS)

    # ------------------------------------------------------------------
    # seed-dependent initial-state realization (Finalization §8/§9)
    # ------------------------------------------------------------------
    def _apply_seed_realization(self) -> None:
        """Apply the per-seed deterministic initial-state realization.

        Changes (all manager-visible and all deterministic given the seed):
          - battery_pct / remaining_endurance_s of every aircraft (0..15 %
            reduction), which flows into the Global State air section and the
            candidate table's endurance margin / feasibility gate;
          - initial position of each busy aircraft advanced along its
            origin -> destination leg by a seed-derived fraction (0.05..0.40),
            which flows into the Global State air position and the candidate
            table's air ETA.

        The same seed produces an identical realization for every manager, so
        the B0/B1/B2/B4b paired design sees identical initial states per
        (scenario, seed).  Scenario definitions (workload / disruption / urgency)
        are untouched.
        """
        fac = self.cfg["facilities"]
        busy_map = {acid: (origin, dest) for acid, _mid, _mt, _mp, origin, dest, _r
                    in self.workload["busy"]}
        for acid in sorted(self.registry.aircraft.keys()):
            ac = self.registry.aircraft[acid]
            frac = self.rng.uniform(0.0, 0.15)
            ac.remaining_endurance_s = round(ac.remaining_endurance_s * (1.0 - frac), 1)
            ac.battery_pct = round(ac.battery_pct * (1.0 - frac), 3)
            self.seed_realization[acid] = {
                "battery_pct": ac.battery_pct,
                "remaining_endurance_s": ac.remaining_endurance_s,
                "position": {"lat": round(ac.lat, 7), "lon": round(ac.lon, 7)},
            }
            if acid in busy_map:
                origin, dest = busy_map[acid]
                o = fac[origin]
                d = fac[dest]
                p = self.rng.uniform(0.05, 0.40)
                lat = o["lat"] + p * (d["lat"] - o["lat"])
                lon = o["lon"] + p * (d["lon"] - o["lon"])
                ac.lat, ac.lon = lat, lon
                self.seed_positions[acid] = (lat, lon)
                self.seed_realization[acid]["position"] = {"lat": round(lat, 7),
                                                           "lon": round(lon, 7)}
                self.seed_realization[acid]["progress_fraction"] = round(p, 6)

    def _build_bluesky_scene(self) -> None:
        """Build the BlueSky scene with seed-jittered busy-aircraft positions.

        Identical to the canonical scene except busy aircraft are created at
        their seed-realized positions along the origin->dest leg (heading toward
        the destination).  The phase-1/2/3 `build_scene_commands` path is left
        untouched for the frozen baseline.
        """
        fac = self.cfg["facilities"]
        cmds = ["DT 1.0"]
        for name, f in fac.items():
            cmds.append(f"DEFWPT {name},{f['lat']},{f['lon']},FIX")
        for acid, role, origin, dest, _pair, _mid in FLEET:
            actype = ROLE_TO_ACTYPE[role]
            if acid in self.seed_positions:
                lat, lon = self.seed_positions[acid]
            else:
                lat, lon = origin_latlon(self.cfg, origin)
            hdg = 0.0
            if dest:
                df = fac[dest]
                hdg = bearing(lat, lon, df["lat"], df["lon"])
            spd = ROLE_CRUISE_MS[role] * MPS_TO_KTS if dest else 0.0
            cmds.append(f"CRE {acid},{actype},{lat},{lon},{hdg:.1f},"
                        f"{ROLE_ALT_FT[role]:.0f},{spd:.1f}")
        for acid, role, origin, dest, _pair, _mid in FLEET:
            if dest:
                cmds.append(f"DEST {acid},{dest}")
                cmds.append(f"ALT {acid},{ROLE_ALT_FT[role]:.0f}")
            else:
                cmds.append(f"ALT {acid},100")
                cmds.append(f"SPD {acid},0")
        for cmd in cmds:
            self.bs.command(cmd)

    # ------------------------------------------------------------------
    def _on_b1_close(self, t: int) -> None:
        self.b1_blocked = True
        for link in self.disruption_links:
            edge = self.sumo_mapping[link]["edge_id"]
            self.sumo.set_edge_disallowed(edge, True)
        factor = self.disruption.get("degrade_detour_factor")
        if factor is not None and float(factor) < 1.0:
            for e in self.sumo.get_route_edges(self.d1_edge, self.h1_edge):
                if e in (self.d1_edge, self.h1_edge):
                    continue
                self.sumo.set_edge_maxspeed(e, self.sumo.lane_maxspeed(e) * float(factor))
        self._record_event(t, "GD1", "GROUND_DISRUPTION",
                           {"edges": self.disruption_links, "action": "closed",
                            "degrade_detour_factor": factor})

    def _failure_zones(self) -> List[Dict[str, Any]]:
        zones = []
        for link in self.disruption_links:
            f = self.fac[link]
            zones.append({"id": link, "edge_id": self.sumo_mapping[link]["edge_id"],
                          "impact_level": f.get("impact_level", "high"),
                          "state": "CLOSED" if self.b1_blocked else "OPEN"})
        return zones

    def _on_critical_mission(self, t: int) -> None:
        cm = self.cfg["phase2"]["critical_mission"]
        mid = cm["mission_id"]
        m = Mission(mid, cm["type"], cm["priority"], cm["origin"], cm["destination"],
                    deadline_s=cm["deadline_s"], ground_fallback=cm["ground_fallback"],
                    delay_cost=self.urgency["delay_cost"],
                    cancellation_cost=self.urgency["cancellation_cost"])
        self.registry.add_mission(m)
        self.injected_mission_ids.add(mid)
        self._record_mission(t, m)
        self._record_event(t, "NEW_CRITICAL_MISSION", "MISSION",
                           {"mission": mid, "priority": cm["priority"],
                            "origin": cm["origin"], "destination": cm["destination"]})
        self._run_manager(t)

    # ------------------------------------------------------------------
    def run(self) -> None:
        for _ in range(self.duration_s):
            self._step_once()
            if self._periodic_due():
                self._run_manager(self.t)
        self.shutdown()

    def _periodic_due(self) -> bool:
        t = self.t
        if self.critical_t is None or t <= self.critical_t:
            return False
        if (t - self.critical_t) % self.periodic_s != 0:
            return False
        m = self.registry.missions.get(self.support_mission_id)
        if m is None:
            return False
        return m.status in ("WAITING", "NEEDS_REPLAN", "INTERRUPTED")

    # ------------------------------------------------------------------
    def _metrics(self) -> Dict[str, Any]:
        missions = self.registry.missions
        crit = missions.get(self.support_mission_id)
        # flush pending CSV rows before reading issued actions (the csv writer
        # buffers; metrics must reflect what actually executed, review §7).
        try:
            self.action_f.flush()
        except Exception:
            pass
        # completion time from events
        comp_t = None
        for ev in self.events:
            if ev["event_id"] in ("MISSION_COMPLETED", "GROUND_FALLBACK_COMPLETED") \
                    and ev["payload"].get("mission") == self.support_mission_id:
                comp_t = ev["t"]
        proposed_types = [(d.get("action") or {}).get("type") for d in self.manager_decisions]
        proposed_types = [t for t in proposed_types if t]
        # FIX (review §7): execution-based action types from actions.csv
        # result=ISSUED (a checker-rejected proposal must not count as an action).
        issued = self._read_actions()
        issued_types = [r.get("action_type") for r in issued if r.get("result") == "ISSUED"]
        existing_damaged = [m.id for m in missions.values()
                            if m.id != self.support_mission_id
                            and m.status in ("INTERRUPTED", "NEEDS_REPLAN", "CANCELLED", "FAILED")]
        return {
            "scenario_id": self.scenario["id"],
            "seed": self.seed,
            "manager": self._manager_label,
            "manager_kind": self.manager.manager_kind if hasattr(self.manager, "manager_kind") else self._manager_label,
            "duration_s": self.duration_s,
            "disruption": self.scenario["disruption"],
            "urgency": self.scenario["urgency"],
            "workload": self.scenario["workload"],
            "tradeoff_label": self.scenario.get("tradeoff"),
            "critical_mission_id": self.support_mission_id,
            "critical_mission_final_state": crit.status if crit else None,
            "critical_mission_final_mode": crit.mode if crit else None,
            "critical_mission_final_resource": crit.assigned_resource if crit else None,
            "critical_mission_deadline_s": crit.deadline_s if crit else None,
            "critical_mission_completion_t": comp_t,
            "critical_mission_completion_time_s": (comp_t - self.release_t) if comp_t else None,
            # FIX (review 20260908 P0-5): an unfinished mission that is already past
            # its deadline must count as a violation, not be silently marked on-time.
            "critical_mission_deadline_violation": bool(
                crit and crit.deadline_s is not None and (comp_t is None or comp_t > crit.deadline_s)),
            "num_manager_decisions": len(self.manager_decisions),
            "action_types": proposed_types,
            "issued_action_types": issued_types,
            "air_intervention": any(t in ("DISPATCH", "REASSIGN") for t in issued_types),
            "ground_fallback": any(t == "GROUND_FALLBACK" for t in issued_types),
            "reassignment_count": sum(1 for t in issued_types if t == "REASSIGN"),
            "existing_missions_damaged": existing_damaged,
            "existing_missions_damaged_count": len(existing_damaged),
            "llm_latency_total_s": round(sum(
                (d.get("llm_metadata") or {}).get("latency_s", 0.0)
                for d in self.manager_decisions), 3),
            "llm_retry_total": sum(
                (d.get("llm_metadata") or {}).get("retry_count", 0)
                for d in self.manager_decisions),
        }

    def _read_actions(self) -> List[Dict[str, Any]]:
        import csv
        rows = []
        p = self.run_dir / "actions.csv"
        if p.exists():
            with open(p, newline="") as f:
                for r in csv.DictReader(f):
                    rows.append(r)
        return rows

    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        self.registry.save(self.run_dir / "registry_final.json")
        metrics = self._metrics()
        (self.run_dir / "metrics.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
        rc = {
            "experiment": "experiment1",
            "scenario_id": self.scenario["id"],
            "seed": self.seed,
            "manager": self._manager_label,
            "manager_kind": self.manager.manager_kind if hasattr(self.manager, "manager_kind") else self._manager_label,
            "disruption": self.scenario["disruption"],
            "urgency": self.scenario["urgency"],
            "workload": self.scenario["workload"],
            "duration_s": self.duration_s,
            "mission_release_t_s": self.release_t,
            "disruption_t_s": self.disruption_t,
            "periodic_decision_s": self.periodic_s,
            "llm_model": getattr(self.manager, "model", None),
        }
        (self.run_dir / "run_config.yaml").write_text(
            yaml.safe_dump(rc, sort_keys=False, allow_unicode=True), encoding="utf-8")

        # Experiment-1 Finalization §20: runtime.json (wall-clock + seed
        # realization + LLM backend observability) is a required per-run artifact.
        runtime = {
            "wall_seconds": round(time.time() - self._t0, 3),
            "duration_s": self.duration_s,
            "num_manager_decisions": len(self.manager_decisions),
            "seed": self.seed,
            "seed_realization": self.seed_realization,
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
