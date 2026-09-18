"""Canonical S0 fleet definition -- single source of truth for both the
orchestrator and the BlueSky scenario generator.

Sparse air network (refined S0): exactly TWO background low-altitude services
plus two standby medical response assets.  4 aircraft total (2 busy / 2
available):

  - L-UAV-01  ordinary logistics route     V2 <-> V3  (background service 1)
  - EVTOL-01  passenger / eVTOL route      V2 <-> V1  (background service 2)
  - M-UAV-01  medical UAV standby at V1
  - M-UAV-02  medical UAV standby at V2    (dispatched on ground disruption)

Each tuple: (acid, role, origin_site, first_dest, shuttle_pair, mission_id)
  - origin_site / first_dest: facility key ('V1','V2','V3') or 'CENTER'
  - shuttle_pair: (siteA, siteB) loop for busy aircraft; None for available
  - mission_id: None for available aircraft
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from orchestrator.bluesky_adapter import ROLE_TO_ACTYPE

# (acid, role, origin_site, first_dest, shuttle_pair, mission_id)
FleetRow = Tuple[str, str, str, Optional[str], Optional[Tuple[str, str]], Optional[str]]

FLEET: List[FleetRow] = [
    ("L-UAV-01", "logistics_uav", "V2", "V3", ("V2", "V3"), "M-L-001"),
    ("EVTOL-01", "passenger_evtol", "V2", "V1", ("V2", "V1"), "M-P-001"),
    ("M-UAV-01", "medical_uav", "V1", None, None, None),   # standby
    ("M-UAV-02", "medical_uav", "V2", None, None, None),   # standby (dispatched)
]

ROLE_CRUISE_MS = {"logistics_uav": 15.0, "medical_uav": 15.0,
                  "inspection_uav": 10.0, "passenger_evtol": 40.0}
ROLE_ALT_FT = {"logistics_uav": 328.0, "medical_uav": 328.0,
               "inspection_uav": 328.0, "passenger_evtol": 656.0}
MPS_TO_KTS = 1.94384


def origin_latlon(config: Dict[str, Any], site: Optional[str]):
    if site == "CENTER":
        c = config["study_area"]["center"]
        return c["lat"], c["lon"]
    if site is None:
        raise ValueError("available aircraft must have an explicit origin site")
    f = config["facilities"][site]
    return f["lat"], f["lon"]


def build_scene_commands(config: Dict[str, Any]) -> List[str]:
    """Build the ordered BlueSky stack commands for the canonical S0 scene."""
    from orchestrator.geo import bearing
    fac = config["facilities"]
    cmds: List[str] = []
    cmds.append("DT 1.0")
    for name, f in fac.items():
        cmds.append(f"DEFWPT {name},{f['lat']},{f['lon']},FIX")

    for acid, role, origin, dest, _pair, _mid in FLEET:
        actype = ROLE_TO_ACTYPE[role]
        lat, lon = origin_latlon(config, origin)
        hdg = 0.0
        if dest:
            df = fac[dest]
            hdg = bearing(lat, lon, df["lat"], df["lon"])
        spd = ROLE_CRUISE_MS[role] * MPS_TO_KTS if dest else 0.0
        cmds.append(f"CRE {acid},{actype},{lat},{lon},{hdg:.1f},{ROLE_ALT_FT[role]:.0f},{spd:.1f}")

    for acid, role, origin, dest, _pair, _mid in FLEET:
        if dest:
            cmds.append(f"DEST {acid},{dest}")
            cmds.append(f"ALT {acid},{ROLE_ALT_FT[role]:.0f}")
        else:
            cmds.append(f"ALT {acid},100")
            cmds.append(f"SPD {acid},0")
    return cmds
