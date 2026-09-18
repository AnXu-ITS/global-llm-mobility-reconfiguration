"""Experiment-4 4C input-scale distractor generation.

The 4C sub-experiment measures the LLM's tolerance to GROWING INPUT SIZE while
the actual decision problem stays identical.  To do that without touching the
frozen base fleet, this module generates INERT "distractor" entries:

  - distractor aircraft     UNAVAILABLE, not commandable, not reassignable,
                            landing-incompatible with the core sites, zero
                            endurance -> always an ILLEGAL candidate row;
  - distractor landing sites  backup_landing_site, inert (never a destination);
  - distractor missions     COMPLETED (never actionable).

Every distractor therefore appears in the Global State (air / infrastructure /
missions) and in the derived candidate table as an illegal row, so the LLM's
prompt grows with N, but the legal candidate set, the failure, and the
reference-optimal action are bit-identical across all arms.

All generation is a pure function of (cfg, n_distractor, seed), so the paired
B0/B1/B2/B4b runs see identical states per (scenario, seed).
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple


def _bbox(cfg: Dict[str, Any]) -> Tuple[float, float, float, float]:
    b = cfg["bbox"]
    return (float(b["south"]), float(b["north"]), float(b["west"]), float(b["east"]))


def _random_pos(rng: random.Random, cfg: Dict[str, Any]) -> Tuple[float, float]:
    south, north, west, east = _bbox(cfg)
    lat = rng.uniform(south, north)
    lon = rng.uniform(west, east)
    return round(lat, 7), round(lon, 7)


def generate_distractors(cfg: Dict[str, Any], n_distractor: int,
                         rng: random.Random,
                         scale_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Return inert distractor entries for `n_distractor` extra aircraft."""
    n_distractor = max(0, int(n_distractor))
    n_sites = int(scale_cfg.get("distractor_site_count", 0))

    sites: Dict[str, Dict[str, Any]] = {}
    for i in range(n_sites):
        lat, lon = _random_pos(rng, cfg)
        sites[f"DX{i + 1}"] = {"type": "backup_landing_site", "lat": lat, "lon": lon}
    site_names = sorted(sites.keys())

    ac_prefix = scale_cfg.get("distractor_aircraft_prefix", "D-UAV")
    m_prefix = scale_cfg.get("distractor_mission_prefix", "M-D")
    role = scale_cfg.get("distractor_role", "inspection_uav")

    aircraft: List[Dict[str, Any]] = []
    missions: List[Dict[str, Any]] = []
    for i in range(n_distractor):
        acid = f"{ac_prefix}-{i + 1:02d}"
        lat, lon = _random_pos(rng, cfg)
        compat = [site_names[i % max(1, len(site_names))]] if site_names else []
        aircraft.append({
            "id": acid,
            "role": role,
            "lat": lat,
            "lon": lon,
            "status": "UNAVAILABLE",
            "commandable": False,
            "reassignable": False,
            "landing_site_compatibility": list(compat),
            "battery_pct": 0.05,
            "remaining_endurance_s": 0.0,
        })
        mid = f"{m_prefix}-{100 + i:03d}"
        missions.append({
            "id": mid,
            "type": "inspection",
            "priority": "LOW",
            "origin": compat[0] if compat else "V1",
            "destination": compat[0] if compat else "V1",
            "deadline_s": 3600.0,
            "aircraft": acid,
        })

    return {
        "n_distractor": n_distractor,
        "distractor_aircraft": aircraft,
        "distractor_sites": sites,
        "distractor_missions": missions,
    }
