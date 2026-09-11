"""Replay manager for B4b (reproducibility ONLY, protocol §30).

Replays the CACHED manager decisions of a previously recorded run in order, so
the simulator determinism can be verified without calling the LLM again. These
replays are NEVER counted as independent statistical samples (frozen rule).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from managers.llm_manager import LLMManager


class ReplayLLMManager(LLMManager):
    """B4b replay arm: consume cached decisions instead of calling the LLM."""

    def __init__(self, config: Dict[str, Any], phase3_config: Dict[str, Any],
                 replay_from: Path):
        super().__init__(config, phase3_config)
        self.manager_kind = "llm_b4b"
        self.replay_from = replay_from
        self.cached: List[Dict[str, Any]] = []
        src = replay_from / "manager_outputs.jsonl"
        for line in src.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                self.cached.append(json.loads(line))
        self.idx = 0

    def decide(self, global_state: Dict[str, Any]) -> Dict[str, Any]:
        self._decision_counter += 1
        decision_id = f"D{self._decision_counter:03d}"
        t = global_state["simulation_time"]
        if self.idx < len(self.cached):
            cached = self.cached[self.idx]
            self.idx += 1
            meta = dict(cached.get("llm_metadata") or {})
            meta["replay"] = True
            return {
                "decision_id": decision_id,
                "simulation_time": t,
                "scenario_id": global_state.get("scenario_id"),
                "manager": "llm",
                "llm_model": self.model,
                "prompt_version": self.prompt_version,
                "trigger": cached.get("trigger") or ["replay"],
                "mission_id": cached.get("mission_id"),
                "mission_priority": cached.get("mission_priority"),
                "candidates": [],
                "ground_candidate": cached.get("ground_candidate", {}),
                "selected": cached.get("selected", {}),
                "action": cached.get("action"),
                "reason": cached.get("reason"),
                "llm_metadata": meta,
            }
        return {
            "decision_id": decision_id,
            "simulation_time": t,
            "scenario_id": global_state.get("scenario_id"),
            "manager": "llm",
            "llm_model": self.model,
            "prompt_version": self.prompt_version,
            "trigger": ["replay exhausted"],
            "mission_id": None,
            "mission_priority": None,
            "candidates": [],
            "ground_candidate": {},
            "selected": {"resource": None, "type": "NONE", "eta_s": None, "reject_reason": None},
            "action": None,
            "reason": "replay exhausted",
            "llm_metadata": {"replay": True, "validation_status": "REPLAY_EXHAUSTED"},
        }
