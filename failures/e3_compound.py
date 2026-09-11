"""Experiment-3 compound-disruption helpers (E3-EXT-SCHED-1).

Experiment 3 composes the FROZEN E2 F1-F6 injectors on one multi-event
timeline; it introduces NO new failure family. This module provides:

  - register_failure_zones: register every zone/envelope geometry of a failure
    schedule into the runner (`zone_geometries` + `air_risk_zones`), so the GS
    `failure_zones` list, the candidate evaluator and the semantic validator all
    see the COMPOUND geometry (not just the first failure's zone).
  - dispatch: call the frozen injector for one failure config.
"""
from __future__ import annotations

from typing import Any, Dict

from failures.e2_failures import INJECTORS


def register_failure_zones(runner, failure_cfg: Dict[str, Any]) -> None:
    """Register the zone/envelope geometry of one failure config into the runner.

    Mirrors Experiment2Runner._parse_failure_cfg, but is called per schedule
    entry so ALL compound zones are visible. Zone activity windows come from the
    config's active_from_s / active_until_s and are rendered by the runner's
    `_failure_zones` (CLOSED while active).
    """
    zone = failure_cfg.get("zone")
    if zone is not None:
        z = dict(zone)
        runner.zone_geometries[z["id"]] = z
        runner.air_risk_zones.append(z)
    env = failure_cfg.get("envelope")
    if env is not None:
        e = dict(env)
        runner.zone_geometries[e["id"]] = e
        runner.air_risk_zones.append(e)


def dispatch(runner, failure_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Call the frozen F1-F6 injector for one failure config."""
    return INJECTORS[failure_cfg["family"]](runner, failure_cfg)
