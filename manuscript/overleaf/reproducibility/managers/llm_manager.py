"""LLM Manager (Phase 3).

Same public contract as the Rule-Based Manager:

    Global State (dict)  ->  decision dict (with an `action` key)

The LLM sees ONLY the Global State v1 snapshot. Its raw output is passed
through a fixed pipeline before it becomes an action:

    JSON parse -> schema validation -> semantic validation -> (1 retry)

Any failure is recorded (never silently repaired) and triggers ONE structured
retry. The FeasibilityChecker and Executor remain the shared, manager-agnostic
gates downstream (run by the orchestrator).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema

from managers.llm_client import LLMClient
from safety.semantic_validator import SemanticValidator

ROOT = Path(__file__).resolve().parents[1]

ACTION_TYPES = ("DISPATCH", "REASSIGN", "REROUTE", "DELAY", "CANCEL", "RESERVE",
                "DIVERT", "RETURN", "LAND", "GROUND_FALLBACK", "NO_ACTION", "ESCALATE")

AIR_ACTIONS = ("DISPATCH", "REASSIGN", "DIVERT", "REROUTE", "RESERVE", "RETURN", "LAND")

MAX_ATTEMPTS = 2  # initial + 1 structured retry


class LLMManager:
    def __init__(self, config: Dict[str, Any], phase3_config: Dict[str, Any]):
        self.config = config
        self.p3 = phase3_config
        llm = self.p3.get("llm", {})
        self.model = llm.get("model", "corp-ai/openai/deepseek-v4-pro")
        self.temperature = float(llm.get("temperature", 0.0))
        self.client = LLMClient(
            base_url=llm.get("base_url", "http://192.168.27.4:18888/v1"),
            model=self.model,
            api_key_env=llm.get("api_key_env", "CORP_AI_API_KEY"),
            temperature=self.temperature,
            max_tokens=int(llm.get("max_tokens", 8192)),
            timeout_s=int(llm.get("timeout_s", 180)),
            json_mode=bool(llm.get("json_mode", True)),
        )

        prompt_path = ROOT / self.p3.get("prompt", "prompts/manager_v1.txt")
        self.prompt_template = prompt_path.read_text(encoding="utf-8")

        schema_path = ROOT / self.p3.get("action_schema", "schemas/manager_action_v1.schema.json")
        self.action_schema = json.loads(schema_path.read_text(encoding="utf-8"))

        rc_path = ROOT / self.p3.get("resource_compatibility", "config/resource_compatibility.yaml")
        self.semantic = SemanticValidator(str(rc_path))

        self.prompt_version = prompt_path.stem  # "manager_v1" | "manager_v2"
        # Experiment-1 v2 (Fix B): when True the shared candidate table is
        # rendered into the prompt (v2b arm); when False it is withheld (v2a arm).
        self.include_candidates = bool(self.p3.get("include_candidates", False))
        self.manager_kind = "llm"
        self._decision_counter = 0

    # ------------------------------------------------------------------
    # public entry point (mirrors RuleBasedManager.decide)
    # ------------------------------------------------------------------
    def decide(self, global_state: Dict[str, Any]) -> Dict[str, Any]:
        self._decision_counter += 1
        decision_id = f"D{self._decision_counter:03d}"
        t = global_state["simulation_time"]

        prompt = self.prompt_template.replace(
            "{GLOBAL_STATE}", json.dumps(
                {k: v for k, v in global_state.items() if k != "candidates"},
                sort_keys=True, ensure_ascii=False, separators=(",", ":")))
        # render the shared candidate table as a separate section (v2b only)
        cand_section = ""
        candidates = global_state.get("candidates")
        if self.include_candidates and candidates:
            cand_section = (
                "\n\nCANDIDATE TABLE (derived by the shared evaluator; use these "
                "numbers verbatim for ETA / legality / predicted deadline "
                "violation / preempted mission):\n"
                + json.dumps(candidates, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")))
        prompt = prompt.replace("{CANDIDATE_SECTION}", cand_section)
        messages: List[Dict[str, str]] = [{"role": "user", "content": prompt}]

        action, reason, metadata = self._run_pipeline(global_state, messages)

        mid = (action or {}).get("mission_id")
        return {
            "decision_id": decision_id,
            "simulation_time": t,
            "scenario_id": global_state.get("scenario_id"),
            "manager": "llm",
            "llm_model": self.model,
            "prompt_version": self.prompt_version,
            "trigger": self._derive_trigger(global_state, mid),
            "mission_id": mid,
            "mission_priority": self._mission_priority(global_state, mid),
            "candidates": [],
            "ground_candidate": self._ground_candidate(global_state),
            "selected": self._selected(action, global_state),
            "action": action,
            "reason": reason,
            "llm_metadata": metadata,
        }

    # ------------------------------------------------------------------
    # parse -> schema -> semantic, with one structured retry
    # ------------------------------------------------------------------
    def _run_pipeline(self, gs: Dict[str, Any],
                      messages: List[Dict[str, str]]) -> Tuple[Optional[Dict], str, Dict]:
        total_latency = 0.0
        prompt_tokens = 0
        completion_tokens = 0
        reasoning_tokens = 0
        output_tokens = 0
        empty_content_count = 0
        finish_reason = None
        attempts = 0
        last_error = "NO_OUTPUT"
        first_error = None
        extraction = "none"

        for attempt in range(MAX_ATTEMPTS):
            attempts = attempt + 1
            try:
                resp = self.client.chat(messages)
            except Exception as e:  # transport / auth error -> no action
                last_error = "LLM_TRANSPORT_ERROR"
                if first_error is None:
                    first_error = last_error
                return None, "", self._meta(
                    attempts, last_error, [str(e)[:200]], total_latency,
                    prompt_tokens, completion_tokens, extraction, resp=None,
                    first_error=first_error, reasoning_tokens=reasoning_tokens,
                    output_tokens=output_tokens, empty_content_count=empty_content_count,
                    finish_reason=finish_reason)

            raw = resp["content"]
            total_latency += resp.get("latency_s", 0.0)
            usage = resp.get("usage", {})
            prompt_tokens += int(usage.get("prompt_tokens", 0))
            completion_tokens += int(usage.get("completion_tokens", 0))
            reasoning_tokens += int(resp.get("reasoning_tokens", 0))
            output_tokens += int(resp.get("output_tokens", 0))
            if resp.get("empty_content"):
                empty_content_count += 1
            if resp.get("finish_reason") is not None:
                finish_reason = resp["finish_reason"]

            obj, extraction = self._extract_json(raw)
            if obj is None:
                last_error = "JSON_ERROR"
                detail = "output was not a single JSON object"
            else:
                schema_errors = self._schema_errors(obj)
                if schema_errors:
                    last_error = "SCHEMA_ERROR"
                    detail = "; ".join(schema_errors[:3])
                else:
                    sem = self.semantic.validate(obj, gs)
                    if not sem["valid"]:
                        last_error = sem["error_types"][0]
                        detail = "; ".join(sem["error_types"])
                    else:
                        return obj, (obj.get("reason") or ""), self._meta(
                            attempts, "VALID_ACTION", [], total_latency,
                            prompt_tokens, completion_tokens, extraction, resp=resp,
                            first_error=first_error, reasoning_tokens=reasoning_tokens,
                            output_tokens=output_tokens, empty_content_count=empty_content_count,
                            finish_reason=finish_reason)

            if first_error is None:
                first_error = last_error
            # one structured retry
            if attempt == 0:
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content":
                                 f"Your previous output was invalid because {last_error}: "
                                 f"{detail}. Return corrected JSON only."})

        return None, "", self._meta(
            attempts, last_error, [last_error], total_latency,
            prompt_tokens, completion_tokens, extraction, resp=None,
            first_error=first_error, reasoning_tokens=reasoning_tokens,
            output_tokens=output_tokens, empty_content_count=empty_content_count,
            finish_reason=finish_reason)

    @staticmethod
    def _meta(attempts: int, status: str, errors: List[str], latency: float,
              pt: int, ct: int, extraction: str, resp: Optional[Dict],
              first_error: Optional[str] = None, reasoning_tokens: int = 0,
              output_tokens: int = 0, empty_content_count: int = 0,
              finish_reason: Optional[str] = None) -> Dict[str, Any]:
        meta: Dict[str, Any] = {
            "attempts": attempts,
            "retry_count": max(0, attempts - 1),
            "validation_status": status,
            "errors": errors,
            "first_attempt_error": first_error,
            "latency_s": round(latency, 3),
            "prompt_tokens": pt,
            "completion_tokens": ct,
            "reasoning_tokens": reasoning_tokens,
            "output_tokens": output_tokens,
            "total_tokens": pt + ct,
            "finish_reason": finish_reason,
            "empty_content_count": empty_content_count,
            "extraction": extraction,
        }
        if resp:
            meta["model"] = resp.get("model")
            meta["temperature"] = 0.0
            meta["content_length"] = resp.get("content_length")
            meta["response_id"] = resp.get("response_id")
            meta["created"] = resp.get("created")
            meta["cached_tokens"] = int(resp.get("cached_tokens", 0) or 0)
        return meta

    # ------------------------------------------------------------------
    # validation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_json(raw: str) -> Tuple[Optional[Dict], str]:
        """Parse the model's reply into a dict. Extraction method is recorded."""
        s = raw.strip()
        if not s:
            return None, "empty"
        try:
            return json.loads(s), "clean"
        except json.JSONDecodeError:
            pass
        # markdown fence
        if s.startswith("```"):
            lines = s.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            inner = "\n".join(lines).strip()
            try:
                return json.loads(inner), "fenced"
            except json.JSONDecodeError:
                pass
        # first balanced { ... } object (recorded, never silent)
        start = s.find("{")
        if start >= 0:
            depth = 0
            for i in range(start, len(s)):
                c = s[i]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(s[start:i + 1]), "brace_match"
                        except json.JSONDecodeError:
                            break
        return None, "unparseable"

    def _schema_errors(self, obj: Any) -> List[str]:
        validator = jsonschema.Draft7Validator(self.action_schema)
        errs = list(validator.iter_errors(obj))
        if not errs:
            return []
        out = []
        for e in errs[:5]:
            path = ".".join(str(p) for p in e.absolute_path) or "(root)"
            out.append(f"{path}: {e.message}")
        return out

    # ------------------------------------------------------------------
    # decision-shape helpers (parity with RuleBasedManager)
    # ------------------------------------------------------------------
    def _derive_trigger(self, gs: Dict[str, Any], mission_id: Optional[str]) -> List[str]:
        triggers: List[str] = []
        for ev in gs.get("events", []):
            et = ev.get("event_type")
            if et in ("GROUND_DISRUPTION", "GROUND_ACCESSIBILITY_DEGRADED"):
                triggers.append("B1 closure (ground disruption)")
            if et == "C2_LOST":
                triggers.append("C2 lost link")
        if mission_id:
            m = self._find_mission(gs, mission_id)
            if m:
                if m.get("state") in ("INTERRUPTED", "NEEDS_REPLAN"):
                    triggers.append("mission interrupted -> NEEDS_REPLAN")
                if m.get("state") == "WAITING":
                    triggers.append(f"new {m.get('priority', 'NORMAL')} mission")
        return triggers or ["scheduled re-evaluation"]

    @staticmethod
    def _find_mission(gs: Dict[str, Any], mid: str) -> Optional[Dict[str, Any]]:
        for bucket in ("new", "existing"):
            for m in gs.get("missions", {}).get(bucket, []):
                if m.get("id") == mid:
                    return m
        return None

    def _mission_priority(self, gs: Dict[str, Any], mid: Optional[str]) -> Optional[str]:
        if not mid:
            return None
        m = self._find_mission(gs, mid)
        return m.get("priority") if m else None

    @staticmethod
    def _ground_candidate(gs: Dict[str, Any]) -> Dict[str, Any]:
        g = gs.get("ground", {})
        eta = g.get("ground_fallback_eta_s")
        feasible = bool(g.get("available_ground_fallback", True) and eta is not None)
        return {"resource_id": "GROUND", "type": "GROUND", "feasible": feasible,
                "eta_s": eta, "reject_reason": None if feasible else "no ground fallback"}

    @staticmethod
    def _selected(action: Optional[Dict], gs: Dict[str, Any]) -> Dict[str, Any]:
        if not action:
            return {"resource": None, "type": "NONE", "eta_s": None, "reject_reason": None}
        atype = action.get("type")
        if atype in AIR_ACTIONS and action.get("aircraft_id"):
            return {"resource": action["aircraft_id"], "type": "AIR", "eta_s": None,
                    "reject_reason": None}
        if atype == "GROUND_FALLBACK":
            return {"resource": "GROUND", "type": "GROUND",
                    "eta_s": action.get("ground_eta_s"), "reject_reason": None}
        if atype == "NO_ACTION":
            return {"resource": None, "type": "NOOP", "eta_s": None, "reject_reason": None}
        return {"resource": None, "type": atype, "eta_s": None, "reject_reason": None}
