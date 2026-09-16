"""Experiment-3 candidate-table extension (E3-EXT-CAND-1) — v2.2.0.

Subclasses the frozen E2 `E2CandidateEvaluator` (2.1.0, untouched). All frozen
fields, frozen reject reasons and frozen E2 rules are inherited; B0/B1/B2/B4b
consume the SAME extended table. The ONLY addition is the multi-mission
section, which is purely factual and manager-agnostic (no scoring / ranking /
recommendation):

    mission_candidates   (list, present ONLY when >= 2 actionable missions)
      one entry per actionable mission (WAITING / NEEDS_REPLAN / INTERRUPTED):
        {mission_id, priority, origin, destination, deadline_s, state,
         air: [...], ground: {...}}
      ordered by the frozen priority ordering (CRITICAL > HIGH > NORMAL > LOW,
      then deadline) — this ordering is factual, NOT a recommendation.

Emission guard (E3-EXT-CAND-1a): with exactly ONE actionable mission the table
renders byte-identically to 2.1.0 (no `mission_candidates` key), so the L1
anchor scenarios reproduce the E2 single-failure inputs for B4b exactly.

Version bump 2.1.0 -> 2.2.0 recorded in CHANGELOG + protocol-extensions
comparability note. The frozen 2.0.0 / 2.1.0 modules are untouched.
"""
from __future__ import annotations

from typing import Any, Dict, List

from orchestrator.candidate_info import ACTIONABLE_STATES, PRIORITY_ORDER
from orchestrator.candidate_info_e2 import E2CandidateEvaluator

CANDIDATE_TABLE_VERSION = "2.2.0"


class E3CandidateEvaluator(E2CandidateEvaluator):
    # ------------------------------------------------------------------
    def _actionable_missions(self, gs: Dict[str, Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for bucket in ("new", "existing"):
            for m in gs.get("missions", {}).get(bucket, []):
                if m.get("state") in ACTIONABLE_STATES:
                    out.append(m)
        out.sort(key=lambda m: (
            -PRIORITY_ORDER.get(m.get("priority", "LOW"), 1),
            m.get("deadline_s") if m.get("deadline_s") is not None else 1e18))
        return out

    def _mission_candidate_entry(self, gs: Dict[str, Any],
                                 m: Dict[str, Any]) -> Dict[str, Any]:
        is_new = self._mission_is_new(gs, m.get("id"))
        table = self.evaluate_for(gs, m, is_new=is_new)
        return {
            "mission_id": m.get("id"),
            "priority": m.get("priority"),
            "origin": m.get("origin"),
            "destination": m.get("destination"),
            "deadline_s": m.get("deadline_s"),
            "state": m.get("state"),
            "air": table["air"],
            "ground": table["ground"],
        }

    # ------------------------------------------------------------------
    def evaluate(self, gs: Dict[str, Any]) -> Dict[str, Any]:
        table = super().evaluate(gs)  # 2.1.0 table (single target, unchanged)
        table["summary"]["candidate_table_version"] = CANDIDATE_TABLE_VERSION
        actionable = self._actionable_missions(gs)
        # emission guard: only when >= 2 actionable missions
        if len(actionable) >= 2:
            table["mission_candidates"] = [
                self._mission_candidate_entry(gs, m) for m in actionable
            ]
        return table
