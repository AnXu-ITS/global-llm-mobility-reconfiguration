"""Python Master Orchestrator -- the single master clock for the co-simulation.

Master step = 1 s. Invariants enforced each step:
    orchestrator_time == SUMO time == BlueSky time
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestrator import config as config_mod
from orchestrator.bluesky_adapter import BlueSkyAdapter, ROLE_TO_ACTYPE
from orchestrator.fleet import (FLEET, MPS_TO_KTS, ROLE_ALT_FT, ROLE_CRUISE_MS,
                                build_scene_commands, origin_latlon)
from orchestrator.geo import haversine
from orchestrator.registry import Aircraft, Mission, Registry
from orchestrator.sumo_adapter import SumoAdapter
from safety.feasibility_checker import FeasibilityChecker

ROOT = Path(__file__).resolve().parents[1]

ARRIVAL_RADIUS_M = 100.0


class Orchestrator:
    def __init__(self, cfg: Dict[str, Any], sumo_cfg: Path, run_dir: Path,
                 duration_s: int, b1_close_t: Optional[int] = None,
                 gui: bool = False, seed: Optional[int] = None):
        self.cfg = cfg
        self.sumo_cfg = sumo_cfg
        self.run_dir = run_dir
        self.duration_s = duration_s
        self.b1_close_t = b1_close_t
        self.gui = gui
        self.seed = seed
        self.t = 0

        # event schedule is fixed in config (single source of truth) -- the
        # explicit b1_close_t argument only overrides when provided.
        self.schedule = cfg.get("schedule", {})
        if self.b1_close_t is None:
            self.b1_close_t = self.schedule.get("b1_close_t_s")
        self.reverse_air_t = self.schedule.get("reverse_air_event_t_s", 450)

        self.fac = cfg["facilities"]
        self.sumo_mapping = cfg["sumo_mapping"]
        self.b1_edge = self.sumo_mapping["B1"]["edge_id"]
        self.d1_edge = self.sumo_mapping["D1"]["edge_id"]
        self.h1_edge = self.sumo_mapping["H1"]["edge_id"]

        self.registry = Registry()
        self.checker = FeasibilityChecker(self.registry, cfg)

        self.aircraft_dest: Dict[str, Optional[str]] = {}   # acid -> facility wpt name
        self.aircraft_role: Dict[str, str] = {}             # acid -> role
        self.shuttle_pairs: Dict[str, tuple] = {}           # acid -> (wptA, wptB) for shuttle loop

        self.scheduled_events: List[Dict[str, Any]] = []
        self.pending_actions: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.eta_baseline: Optional[float] = None
        self.eta_last: Optional[float] = None
        self.b1_blocked = False
        self.support_dispatched = False
        self.air_event_done = False

        self.sumo: Optional[SumoAdapter] = None
        self.bs: Optional[BlueSkyAdapter] = None

        self._setup_logs()

    # ---------------- setup ----------------
    def _setup_logs(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.ground_f = open(self.run_dir / "ground_state.csv", "w", newline="")
        self.air_f = open(self.run_dir / "air_state.csv", "w", newline="")
        self.clock_f = open(self.run_dir / "clock_sync.csv", "w", newline="")
        self.event_f = open(self.run_dir / "events.csv", "w", newline="")
        self.action_f = open(self.run_dir / "actions.csv", "w", newline="")
        self.mission_f = open(self.run_dir / "missions.csv", "w", newline="")

        self.ground_w = csv.writer(self.ground_f)
        self.air_w = csv.writer(self.air_f)
        self.clock_w = csv.writer(self.clock_f)
        self.event_w = csv.writer(self.event_f)
        self.action_w = csv.writer(self.action_f)
        self.mission_w = csv.writer(self.mission_f)

        self.ground_w.writerow(["t", "sim_time_s", "sumo_vehicles", "b1_blocked",
                                "eta_d1_h1_s", "eta_baseline_s", "accessibility_degraded"])
        self.air_w.writerow(["t", "sim_time_s", "aircraft_id", "type", "lat", "lon",
                             "alt_m", "status", "mission_id", "dest"])
        self.clock_w.writerow(["t", "orchestrator_time", "sumo_time", "bluesky_time", "sync_ok"])
        self.event_w.writerow(["t", "event_id", "event_type", "payload"])
        self.action_w.writerow(["t", "action_type", "aircraft_id", "mission_id",
                                "target_site", "result"])
        self.mission_w.writerow(["t", "mission_id", "type", "priority", "origin",
                                 "destination", "status", "assigned_resource"])

    def setup(self) -> None:
        # SUMO
        self.sumo = SumoAdapter(self.sumo_cfg, step_length=1.0, gui=self.gui, seed=self.seed)
        self.sumo.start()

        # BlueSky
        self.bs = BlueSkyAdapter(self.cfg)

        self._build_registry()
        self._build_bluesky_scene()

        # schedule the B1 closure (GD1)
        if self.b1_close_t is not None:
            self.scheduled_events.append({
                "t": self.b1_close_t, "event_id": "GD1", "event_type": "B1_CLOSE",
            })

    def _build_registry(self) -> None:
        for acid, role, origin, dest, pair, mid in FLEET:
            lat, lon = origin_latlon(self.cfg, origin)
            status = "BUSY" if mid else "AVAILABLE"
            ac = Aircraft(acid, role, lat, lon, status=status, mission_id=mid)
            ac.status = status
            self.registry.add_aircraft(ac)
            self.aircraft_role[acid] = role
            self.aircraft_dest[acid] = dest
            if pair is not None:
                self.shuttle_pairs[acid] = pair

        # existing (preserved) missions for busy aircraft
        for acid, _role, origin, dest, _pair, mid in FLEET:
            if mid is None:
                continue
            mtype, mpri = self._mission_type(mid)
            m = Mission(mid, mtype, mpri, origin or "V2", dest or "V1",
                        deadline_s=1800, assigned_resource=acid)
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

    # ---------------- main loop ----------------
    def run(self) -> None:
        for _ in range(self.duration_s):
            self._step_once()
        self.shutdown()

    def _step_once(self) -> None:
        t = self.t  # master clock; simulators are currently at time t
        # 1. apply scheduled events at t
        self._apply_scheduled_events(t)
        # 2. apply queued actions at t
        self._apply_queued_actions(t)
        # 3. SUMO step t -> t+1
        self.sumo.step()
        # 4. BlueSky step t -> t+1
        self.bs.step()
        # 11. advance global simulation time
        self.t += 1
        now = self.t
        # 5. collect SUMO state
        ground = self._collect_ground()
        # 6. collect BlueSky state
        air = self.bs.state()
        # 7/8. update registry + shared state (positions)
        self._update_registry(air)
        # 9. detect events
        self._detect_events(now, ground)
        # 10. log timestamp
        self._log(now, ground, air)

    def _apply_scheduled_events(self, t: int) -> None:
        for ev in list(self.scheduled_events):
            if ev["t"] == t:
                if ev["event_type"] == "B1_CLOSE":
                    self.sumo.set_edge_disallowed(self.b1_edge, True)
                    self.b1_blocked = True
                    self._record_event(t, "GD1", "GROUND_DISRUPTION",
                                       {"edge": self.b1_edge, "action": "closed"})
                    self._on_ground_disruption(t)
                self.scheduled_events.remove(ev)

    def _apply_queued_actions(self, t: int) -> None:
        for action in list(self.pending_actions):
            if action.get("t", t) == t:
                self._execute_action(action)
                self.pending_actions.remove(action)

    def _on_ground_disruption(self, t: int) -> None:
        """Deterministic (non-LLM) response: dispatch one AVAILABLE UAV to a
        predefined support mission V2 -> V1 (medical resupply toward H1)."""
        if self.support_dispatched:
            return
        support_mission_id = "M-SUPPORT-001"
        # add the support mission (WAITING)
        m = Mission(support_mission_id, "medical_resupply", "CRITICAL", "V2", "V1",
                    deadline_s=900, ground_fallback=True)
        self.registry.add_mission(m)
        self._record_mission(t, m)

        # deterministic rule: choose first AVAILABLE medical UAV (M-UAV-02)
        candidate = None
        for acid in ["M-UAV-02", "M-UAV-01"]:
            if self.registry.aircraft[acid].status == "AVAILABLE":
                candidate = acid
                break
        if candidate is None:
            self._record_event(t, "DISPATCH_FAIL", "ACTION_INFEASIBLE",
                               {"reason": "no available aircraft"})
            return

        action = {"type": "DISPATCH", "aircraft_id": candidate, "mission_id": support_mission_id,
                  "target_site": "V1", "reason": "B1 closure; ground ETA degraded"}
        result = self.checker.check(action)
        if not result["valid"]:
            self._record_event(t, "DISPATCH_REJECTED", "ACTION_INFEASIBLE",
                               {"violations": result["violations"]})
            self._record_action(t, "DISPATCH", candidate, support_mission_id, "V1", "REJECTED")
            return
        self._record_event(t, "DISPATCH", "ACTION_ISSUED",
                           {"aircraft": candidate, "mission": support_mission_id, "target": "V1"})
        self._record_action(t, "DISPATCH", candidate, support_mission_id, "V1", "ISSUED")
        self.pending_actions.append({**action, "t": t})
        self.support_dispatched = True

    def _execute_action(self, action: Dict[str, Any]) -> None:
        atype = action["type"]
        if atype == "DISPATCH":
            acid = action["aircraft_id"]
            mid = action["mission_id"]
            self.registry.assign(acid, mid)          # AVAILABLE->BUSY, WAITING->ASSIGNED
            self._record_mission(self.t, self.registry.missions[mid])
            self.registry.en_route(mid)              # ASSIGNED->EN_ROUTE
            self._record_mission(self.t, self.registry.missions[mid])
            self.aircraft_dest[acid] = action["target_site"]
            role = self.aircraft_role[acid]
            self.bs.fly_to(acid, action["target_site"],
                           alt_ft=ROLE_ALT_FT[role],
                           spd_kts=ROLE_CRUISE_MS[role] * MPS_TO_KTS)
            self._record_event(self.t, "MISSION_STARTED", "MISSION",
                               {"aircraft": acid, "mission": mid, "origin": "V2", "dest": action["target_site"]})

    def _collect_ground(self) -> Dict[str, Any]:
        g: Dict[str, Any] = {}
        g["vehicles"] = len(self.sumo.vehicle_ids())
        g["b1_blocked"] = self.b1_blocked
        eta = self.sumo.get_route_eta(self.d1_edge, self.h1_edge)
        g["eta_d1_h1"] = eta
        if eta is not None:
            if self.eta_baseline is None and not self.b1_blocked:
                # establish baseline during warm-up (first few steps)
                if self.t >= 10:
                    self.eta_baseline = eta
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
        mid = self.registry.aircraft[acid].mission_id
        if mid == "M-SUPPORT-001":
            # T3: WAITING->ASSIGNED->EN_ROUTE->COMPLETED
            self.registry.complete_mission(mid)
            self._record_mission(self.t, self.registry.missions[mid])
            self.aircraft_dest[acid] = None
            self._record_event(self.t, "MISSION_COMPLETED", "MISSION",
                               {"aircraft": acid, "mission": mid, "dest": dest})
            self.bs.park(acid)
            return
        # shuttle: flip destination to keep existing missions moving (preserved)
        if acid in self.shuttle_pairs:
            a, b = self.shuttle_pairs[acid]
            new_dest = b if dest == a else a
            self.aircraft_dest[acid] = new_dest
            role = self.aircraft_role[acid]
            self.bs.fly_to(acid, new_dest, alt_ft=ROLE_ALT_FT[role],
                           spd_kts=ROLE_CRUISE_MS[role] * MPS_TO_KTS)

    def _detect_events(self, t: int, ground: Dict[str, Any]) -> None:
        # GD3: accessibility trigger (derived) -- evidence of H1 accessibility drop
        if ground.get("accessibility_degraded") and not getattr(self, "_gd3_recorded", False):
            self._gd3_recorded = True
            self._record_event(t, "GD3", "GROUND_ACCESSIBILITY_DEGRADED",
                               {"eta_now": ground["eta_d1_h1"], "eta_baseline": ground["eta_baseline"]})

        # reverse air event (config-fixed time): one aircraft becomes unavailable
        if t == self.reverse_air_t and not self.air_event_done:
            self.air_event_done = True
            ac = self.registry.aircraft["L-UAV-01"]
            ac.transition("CONTINGENCY")   # BUSY -> CONTINGENCY (valid)
            ac.transition("UNAVAILABLE")   # CONTINGENCY -> UNAVAILABLE (valid)
            mid = ac.mission_id
            if mid:
                self.registry.missions[mid].transition("NEEDS_REPLAN")
                self._record_mission(t, self.registry.missions[mid])
            self.aircraft_dest["L-UAV-01"] = None
            self.bs.command("DEL L-UAV-01")  # remove from BlueSky (air resource lost)
            self._record_event(t, "F-AIR-001", "AIR_EVENT",
                               {"aircraft": "L-UAV-01", "status": "UNAVAILABLE",
                                "mission": mid, "mission_status": "NEEDS_REPLAN"})

    def _record_event(self, t: int, event_id: str, event_type: str, payload: Any) -> None:
        self.events.append({"t": t, "event_id": event_id, "event_type": event_type, "payload": payload})
        self.event_w.writerow([t, event_id, event_type, json.dumps(payload, ensure_ascii=False)])

    def _record_action(self, t: int, action_type: str, aircraft_id: str, mission_id: str,
                       target_site: str, result: str) -> None:
        self.action_w.writerow([t, action_type, aircraft_id, mission_id, target_site, result])

    def _record_mission(self, t: int, m: Mission) -> None:
        self.mission_w.writerow([t, m.id, m.type, m.priority, m.origin,
                                 m.destination, m.status, m.assigned_resource])

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

    def shutdown(self) -> None:
        # save registry snapshot
        self.registry.save(self.run_dir / "registry_final.json")
        # write run_config.yaml
        import yaml
        rc = {
            "scenario_id": self.cfg.get("scenario_id", "S0"),
            "duration_s": self.duration_s,
            "simulation_step_s": 1,
            "seed": self.seed,
            "b1_close_t": self.b1_close_t,
            "reverse_air_event_t_s": self.reverse_air_t,
            "manager": "deterministic_smoke_test_action",
            "llm_model": None,
        }
        (self.run_dir / "run_config.yaml").write_text(
            yaml.safe_dump(rc, sort_keys=False, allow_unicode=True), encoding="utf-8")

        for f in (self.ground_f, self.air_f, self.clock_f, self.event_f,
                  self.action_f, self.mission_f):
            try:
                f.close()
            except Exception:
                pass
        if self.sumo:
            self.sumo.close()
