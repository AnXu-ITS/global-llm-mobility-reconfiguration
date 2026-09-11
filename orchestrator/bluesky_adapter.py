"""BlueSky adapter: in-process BlueSky simulation with a 1 s master step."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

BLUESKY_REPO = Path(r"C:\Users\xuan1\OneDrive\桌面\学术agent\bluesky")

ROLE_TO_ACTYPE = {
    "logistics_uav": "Amzn",
    "medical_uav": "M600",
    "inspection_uav": "Phan4",
    "passenger_evtol": "EC35",
}


class BlueSkyAdapter:
    def __init__(self, config: Dict[str, Any]):
        if str(BLUESKY_REPO) not in sys.path:
            sys.path.insert(0, str(BLUESKY_REPO))
        import bluesky as bs
        self.bs = bs
        bs.init(mode="sim", detached=True, workdir=str(BLUESKY_REPO))
        # Enter OPERATE state immediately: otherwise the first sim.step() stays in
        # INIT (no traffic yet) and does not advance the clock, producing a 1-step
        # lag relative to SUMO.
        bs.sim.op()
        bs.stack.stack("DT 1.0")
        self.config = config

    def define_landmarks(self) -> None:
        bs = self.bs
        for name, f in self.config["facilities"].items():
            bs.stack.stack(f"DEFWPT {name},{f['lat']},{f['lon']},FIX")

    def create_aircraft(self, acid: str, actype: str, lat: float, lon: float,
                        hdg: float, alt_ft: float, spd_kts: float) -> None:
        self.bs.stack.stack(f"CRE {acid},{actype},{lat},{lon},{hdg},{alt_ft},{spd_kts}")

    def fly_to(self, acid: str, wpt: str, alt_ft: float = 328.0, spd_kts: float = None) -> None:
        self.bs.stack.stack(f"DEST {acid},{wpt}")
        self.bs.stack.stack(f"ALT {acid},{alt_ft}")
        if spd_kts is not None:
            # restore cruise speed (a parked aircraft has SPD 0)
            self.bs.stack.stack(f"SPD {acid},{spd_kts}")

    def command(self, cmd: str) -> None:
        """Queue a raw BlueSky command (processed on the next sim step)."""
        self.bs.stack.stack(cmd)

    def park(self, acid: str, alt_ft: float = 100.0) -> None:
        self.bs.stack.stack(f"ALT {acid},{alt_ft}")
        self.bs.stack.stack(f"SPD {acid},0")

    def step(self) -> None:
        self.bs.sim.step()

    def get_time(self) -> float:
        return float(self.bs.sim.simt)

    def aircraft_ids(self) -> List[str]:
        return [str(i) for i in self.bs.traf.id]

    def state(self) -> Dict[str, Any]:
        bs = self.bs
        ids = self.aircraft_ids()
        out = {}
        for i, acid in enumerate(ids):
            out[acid] = {
                "id": acid,
                "type": str(bs.traf.type[i]),
                "lat": float(bs.traf.lat[i]),
                "lon": float(bs.traf.lon[i]),
                "alt_m": float(bs.traf.alt[i]),
                "tas_kts": float(bs.traf.tas[i]),
                "trk_deg": float(bs.traf.trk[i]),
            }
        return out

    def aircraft_position(self, acid: str):
        bs = self.bs
        ids = self.aircraft_ids()
        if acid not in ids:
            return None
        i = ids.index(acid)
        return float(bs.traf.lat[i]), float(bs.traf.lon[i]), float(bs.traf.alt[i])
