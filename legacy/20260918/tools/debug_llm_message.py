"""Dump full message object for the empty-content case (S17) to find the fix."""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from managers.llm_manager import LLMManager  # noqa: E402

cfg = yaml.safe_load((ROOT / "config" / "scenario_config.yaml").read_text(encoding="utf-8"))
p3 = yaml.safe_load((ROOT / "config" / "phase3_config.yaml").read_text(encoding="utf-8"))
mgr = LLMManager(cfg, p3)


def snap(case, t):
    p = ROOT / "runs" / "phase2_rule_manager" / case / "snapshots.jsonl"
    for l in p.read_text(encoding="utf-8").splitlines():
        o = json.loads(l)
        if o["t"] == t:
            return o["global_state"]


gs = snap("C2_A", 361)
prompt = mgr.prompt_template.replace(
    "{GLOBAL_STATE}", json.dumps(gs, sort_keys=True, ensure_ascii=False, separators=(",", ":")))

# raw call with full body access
import urllib.request
from managers.llm_client import load_api_key
key = load_api_key()
body = {
    "model": "corp-ai/openai/deepseek-v4-pro",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 2048,
    "temperature": 0,
    "response_format": {"type": "json_object"},
    "reasoning_effort": "off",
}
req = urllib.request.Request("http://192.168.27.4:18888/v1/chat/completions",
                             data=json.dumps(body).encode("utf-8"),
                             headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
import urllib.error
try:
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8"))
    msg = data["choices"][0]["message"]
    print("MESSAGE KEYS:", list(msg.keys()))
    for k, v in msg.items():
        s = str(v)
        print(f"--- {k}: {s[:200]}")
    print("USAGE:", data.get("usage"))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode("utf-8", "replace")[:800])
