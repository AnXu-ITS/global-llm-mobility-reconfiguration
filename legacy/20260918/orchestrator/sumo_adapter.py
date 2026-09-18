"""SUMO adapter: run SUMO as a TraCI subprocess with a 1 s step."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]


class SumoAdapter:
    """Wraps TraCI (socket) control of a SUMO subprocess.

    TraCI's `traci.start(cmd, label=...)` spawns sumo.exe itself and talks to it
    over a local socket, so no manual subprocess management is needed.
    """

    def __init__(self, sumocfg: Path, step_length: float = 1.0,
                 gui: bool = False, seed: Optional[int] = None):
        self.sumocfg = str(sumocfg)
        self.gui = gui
        self.seed = seed
        self.step_length = step_length
        self._traci = None

    def start(self) -> None:
        from orchestrator.sumo_env import setup, binary
        setup()
        import traci
        self._traci = traci
        binary = binary("sumo-gui" if self.gui else "sumo")
        cmd = [binary, "-c", self.sumocfg, "--step-length", f"{self.step_length}",
               "--start", "--quit-on-end", "false", "--no-warnings", "true",
               "--time-to-teleport", "-1"]
        if self.seed is not None:
            cmd += ["--seed", str(self.seed)]
        traci.start(cmd, label="cosim")

    def step(self) -> None:
        self._traci.simulationStep()

    def get_time(self) -> float:
        return self._traci.simulation.getTime()

    def close(self) -> None:
        try:
            if self._traci is not None:
                self._traci.close()
        except Exception:
            pass

    def convert_geo_to_xy(self, lon: float, lat: float):
        return self._traci.simulation.convertGeo(lon, lat)

    def convert_xy_to_geo(self, x: float, y: float):
        return self._traci.simulation.convertGeo(x, y, fromGeo=False)

    # ---- vehicle / edge helpers ----

    def vehicle_ids(self) -> List[str]:
        return list(self._traci.vehicle.getIDList())

    def vehicle_position_xy(self, vid: str):
        return self._traci.vehicle.getPosition(vid)

    def vehicle_position_geo(self, vid: str):
        x, y = self._traci.vehicle.getPosition(vid)
        return self._traci.simulation.convertGeo(x, y, fromGeo=False)

    def edge_ids(self) -> List[str]:
        return list(self._traci.edge.getIDList())

    def edge_travel_time(self, edge_id: str) -> float:
        return self._traci.edge.getTraveltime(edge_id)

    def set_edge_disallowed(self, edge_id: str, disallowed: bool) -> None:
        if disallowed:
            self._traci.edge.setDisallowed(edge_id, ["passenger"])
        else:
            self._traci.edge.setAllowed(edge_id, ["passenger"])

    def set_edge_maxspeed(self, edge_id: str, speed: float) -> None:
        self._traci.edge.setMaxSpeed(edge_id, speed)

    def lane_maxspeed(self, edge_id: str) -> float:
        return float(self._traci.lane.getMaxSpeed(f"{edge_id}_0"))

    def get_route_edges(self, from_edge: str, to_edge: str) -> List[str]:
        try:
            route = self._traci.simulation.findRoute(from_edge, to_edge)
            return list(route.edges) if route.edges else []
        except Exception:
            return []

    def edge_is_blocked(self, edge_id: str) -> bool:
        allowed = self._traci.edge.getAllowed(edge_id)
        return "passenger" not in allowed

    def get_route_eta(self, from_edge: str, to_edge: str) -> Optional[float]:
        """Free-flow ETA (s) between two edges along the TraCI-router shortest path.

        Uses static edge length / max speed, NOT the dynamic getTraveltime
        (which spikes to ~1e5 s when a vehicle is momentarily stuck).  Free-flow
        ETA is stable before the disruption and reflects only the route change.
        """
        try:
            route = self._traci.simulation.findRoute(from_edge, to_edge)
            if route.edges is None or len(route.edges) == 0:
                return None
            eta = 0.0
            for e in route.edges:
                lane = f"{e}_0"  # first lane always exists for an edge
                speed = max(self._traci.lane.getMaxSpeed(lane), 1e-3)
                eta += self._traci.lane.getLength(lane) / speed
            return float(eta)
        except Exception:
            return None

    def set_vehicle_route(self, vid: str, edge_list: List[str]) -> None:
        self._traci.vehicle.setRoute(vid, edge_list)

    def add_vehicle(self, vid: str, route_id: str, vtype: str = "ground_fallback") -> None:
        self._traci.vehicle.add(vid, route_id, typeID=vtype)
