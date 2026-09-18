"""Thin OpenAI-compatible chat-completions client (standard library only).

Used by the LLM Manager. Reads the API key from the environment variable named
by `api_key_env`, falling back to `~/.dsh/.credentials.yaml`.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_api_key(env_name: str = "CORP_AI_API_KEY") -> Optional[str]:
    key = os.environ.get(env_name)
    if key:
        return key
    cred = Path.home() / ".dsh" / ".credentials.yaml"
    if cred.exists():
        text = cred.read_text(encoding="utf-8")
        m = re.search(rf'{re.escape(env_name)}:\s*["\']?([^"\'\s]+)', text)
        if m:
            return m.group(1)
    return None


class LLMClient:
    """Minimal chat.completions client for an OpenAI-compatible endpoint."""

    # max_tokens=8192 is a FROZEN interface requirement: at 2048 the reasoning
    # model consumes the whole budget on reasoning tokens and returns empty
    # content (~12 % JSON_ERROR in Phase 3), i.e. reasoning-output budget
    # truncation -- NOT an inability to emit JSON.
    def __init__(self, base_url: str, model: str, api_key_env: str = "CORP_AI_API_KEY",
                 temperature: float = 0.0, max_tokens: int = 8192, timeout_s: int = 180,
                 json_mode: bool = True):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self.json_mode = json_mode
        self.api_key = load_api_key(api_key_env)
        if not self.api_key:
            raise RuntimeError(
                f"LLM API key not found (env {api_key_env} or ~/.dsh/.credentials.yaml)")

    def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Return content/model/usage/latency + finish_reason and token breakdown.

        Extra interface fields (frozen for Experiment 1 observability):
            finish_reason      endpoint stop condition (e.g. stop / length)
            reasoning_tokens   tokens spent on the reasoning chain
            output_tokens      completion_tokens - reasoning_tokens (the answer)
            content_length     length of the returned `content` string
            empty_content      True when `content` is blank (interface/output
                               failure -- NEVER silently substituted)
        """
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        if self.json_mode:
            body["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_txt = e.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(f"LLM HTTP {e.code}: {body_txt}") from e
        latency = time.time() - t0
        content = data["choices"][0]["message"].get("content") or ""
        finish_reason = data["choices"][0].get("finish_reason")
        usage = data.get("usage", {})
        completion_tokens = int(usage.get("completion_tokens", 0))
        reasoning_tokens = int(
            usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0) or 0)
        output_tokens = completion_tokens - reasoning_tokens
        empty_content = not bool(content.strip())
        # cache / identity observability (Experiment-1 v2, Fix D): capture the
        # backend response id + creation timestamp + cached-prompt-token count so
        # repeated calls can be flagged as cached rather than treated as
        # independent inference samples.
        cached_tokens = int(
            usage.get("prompt_tokens_details", {}).get("cached_tokens", 0) or 0)
        return {
            "content": content,
            "model": data.get("model", self.model),
            "usage": usage,
            "latency_s": round(latency, 3),
            "finish_reason": finish_reason,
            "reasoning_tokens": reasoning_tokens,
            "output_tokens": output_tokens,
            "content_length": len(content),
            "empty_content": empty_content,
            "response_id": data.get("id"),
            "created": data.get("created"),
            "cached_tokens": cached_tokens,
        }
