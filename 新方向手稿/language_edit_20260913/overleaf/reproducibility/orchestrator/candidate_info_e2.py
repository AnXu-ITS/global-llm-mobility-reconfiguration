"""Experiment-2 candidate-table extension (E2-EXT-CAND-1) — v2.1.0.

Subclasses the FROZEN CandidateEvaluator (orchestrator/candidate_info.py,
2.0.0, untouched). All frozen fields and frozen reject reasons are inherited;
B1 / B2 / B4b consume the SAME extended table. Additions are purely factual
and manager-agnostic (protocol §13/§14):

  new fields per air candidate:
    failure_reason          str|null   failure-state that made the candidate
                                      illegal (only for E2-specific rules)
    risk_zone_intersection  bool       candidate aircraft/route intersects an
                                      active air risk zone
    utm_eligible            bool|null  UTM state permits a new air assignment

  new legality rules (applied AFTER the frozen filters, so a frozen
  reject_reason is never overwritten):
    UTM DEGRADED -> new non-CRITICAL air missions prohibited
    UTM OUTAGE   -> any new air assignment prohibited
    air risk zone -> aircraft-in-zone or route-intersection -> illegal

Version bump 2.0.0 -> 2.1.0 recorded in CHANGELOG.md + the protocol-extensions
comparability note. No B2 score / ranking / recommendation is added.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from failures.e2_failures import point_in_zone, route_intersects_zone
from orchestrator.candidate_info import CandidateEvaluator

CANDIDATE_TABLE_VERSION = "2.1.0"


class E2CandidateEvaluator(CandidateEvaluator):
    def __init__(self, facilities: Dict[str, Any],
                 dispatch_overhead_s: float = 0.0,
                 contingency_site: str = "V3",
                 zone_geometries: Optional[Dict[str, Dict[str, Any]]] = None):
        super().__init__(facilities, dispatch_overhead_s, contingency_site)
        # zone_id -> frozen geometry (circle / strip); activity windows come
        # from the Global State failure_zones state (CLOSED = active).
        self.zone_geometries = zone_geometries or {}

    # ------------------------------------------------------------------
    def _mission_is_new(self, gs: Dict[str, Any], mission_id: Optional[str]) -> bool:
        for m in gs.get("missions", {}).get("new", []):
            if m.get("id") == mission_id:
                return True
        return False

    def _active_zone_list(self, gs: Dict[str, Any], t: int) -> List[Dict[str, Any]]:
        zones: List[Dict[str, Any]] = []
        for fz in gs.get("infrastructure", {}).get("failure_zones", []):
            if fz.get("state") != "CLOSED":
                continue
            geom = self.zone_geometries.get(fz.get("id"))
            if geom is None:
                continue
            if geom.get("candidate_rule", "full") == "none":
                # e.g. the F2 GNSS zone: aircraft-state-only (degradation is
                # applied at the trigger; no route/position candidate rule).
                continue
            z = dict(geom)
            z["active_from_s"] = 0
            z["active_until_s"] = 10 ** 9
            zones.append(z)
        return zones

    def _air_position(self, gs: Dict[str, Any], resource_id: str) -> Optional[tuple]:
        for a in gs.get("air", []):
            if a.get("id") == resource_id:
                pos = a.get("position") or {}
                lat, lon = pos.get("lat"), pos.get("lon")
                if lat is not None and lon is not None:
                    return (float(lat), float(lon))
        return None

    # ------------------------------------------------------------------
    # E2 rules (fact fields + legality) — applied after the frozen filter
    # ------------------------------------------------------------------
    def _apply_e2_rules(self, gs: Dict[str, Any], air: List[Dict[str, Any]],
                        target_row: Optional[Dict[str, Any]], t: int,
                        is_new: Optional[bool] = None) -> None:
        utm = gs.get("infrastructure", {}).get("utm_state", "NOMINAL")
        target_id = target_row.get("id") if target_row else None
        target_pri = target_row.get("priority") if target_row else None
        if is_new is None:
            is_new = self._mission_is_new(gs, target_id)
        zones = self._active_zone_list(gs, t)

        for cand in air:
            cand.setdefault("failure_reason", None)
            cand.setdefault("risk_zone_intersection", False)
            cand.setdefault("utm_eligible", None)

            # --- UTM rule ---
            utm_ok = True
            utm_reason: Optional[str] = None
            if utm == "OUTAGE":
                utm_ok, utm_reason = False, "UTM_OUTAGE_NEW_AIR_PROHIBITED"
            elif utm == "DEGRADED" and is_new and target_pri != "CRITICAL":
                utm_ok, utm_reason = False, "UTM_DEGRADED_NEW_NONCRITICAL_AIR_PROHIBITED"
            cand["utm_eligible"] = utm_ok

            # --- risk-zone rule (aircraft position / route) ---
            pos = self._air_position(gs, cand["resource_id"])
            zone_hit = False
            if pos is not None:
                for z in zones:
                    if point_in_zone(pos[0], pos[1], z):
                        zone_hit = True
                        break
            route = cand.get("route")
            if route and not zone_hit:
                pts: List[tuple] = []
                if pos is not None:
                    pts.append(pos)
                for wpt in route:
                    f = self.facilities.get(wpt)
                    if f is not None and f.get("lat") is not None:
                        pts.append((float(f["lat"]), float(f["lon"])))
                for z in zones:
                    if route_intersects_zone(pts, z):
                        zone_hit = True
                        break
            cand["risk_zone_intersection"] = zone_hit

            # apply legality only when the frozen filter accepted the candidate
            if cand.get("legal") and (not utm_ok or zone_hit):
                cand["legal"] = False
                if not utm_ok:
                    cand["failure_reason"] = utm_reason
                    cand["reject_reason"] = utm_reason
                else:
                    cand["failure_reason"] = ("AIRCRAFT_IN_RISK_ZONE" if pos is not None
                                              and any(point_in_zone(pos[0], pos[1], z)
                                                      for z in zones)
                                              else "ROUTE_INTERSECTS_RISK_ZONE")
                    cand["reject_reason"] = cand["failure_reason"]

    # ------------------------------------------------------------------
    def evaluate(self, gs: Dict[str, Any]) -> Dict[str, Any]:
        table = super().evaluate(gs)
        t = int(gs.get("simulation_time", 0))
        target = self.target_mission(gs)
        self._apply_e2_rules(gs, table["air"], target, t)
        table["summary"]["candidate_table_version"] = CANDIDATE_TABLE_VERSION
        return table

    # ------------------------------------------------------------------
    def evaluate_for(self, gs: Dict[str, Any], mission_row: Dict[str, Any],
                     is_new: bool = False) -> Dict[str, Any]:
        """Candidate table for an EXPLICIT mission (audit / as-if evaluation).

        Used by the failure trace + scenario audit to measure the feasible air
        set for the critical mission even when it is not the actionable target
        (e.g. it is EN_ROUTE and therefore not in the decision table). Same
        frozen formulas + E2 rules as evaluate().
        """
        t = int(gs.get("simulation_time", 0))
        slack = None
        if mission_row.get("deadline_s") is not None:
            slack = float(mission_row["deadline_s"]) - float(t)
        air: List[Dict[str, Any]] = []
        for ac in gs.get("air", []):
            air.append(self._air_candidate(gs, ac, mission_row, slack))
        ground = self._ground_candidate(gs, mission_row, slack)
        summary = {
            "candidate_table_version": CANDIDATE_TABLE_VERSION,
            "simulation_time": t,
            "target_mission_id": mission_row.get("id"),
            "target_mission_priority": mission_row.get("priority"),
            "target_mission_origin": mission_row.get("origin"),
            "target_mission_destination": mission_row.get("destination"),
            "deadline_slack_s": slack,
            "cruise_speed_ms": {"ROLE": "see frozen table"},
            "dispatch_overhead_s": self.dispatch_overhead_s,
            "endurance_margin_s": 60.0,
            "as_if_evaluation": True,
        }
        table = {"summary": summary, "air": air, "ground": ground}
        # apply E2 rules with the explicit mission (is_new passed by caller)
        self._apply_e2_rules(gs, table["air"], mission_row, t, is_new=is_new)
        return table
