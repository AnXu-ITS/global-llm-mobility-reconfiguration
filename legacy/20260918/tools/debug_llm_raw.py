"""Debug raw LLM outputs on a few states to understand JSON failures."""
import copy
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from managers.llm_client import LLMClient  # noqa: E402
from managers.llm_manager import LLMManager  # noqa: E402

cfg = yaml.safe_load((ROOT / "config" / "scenario_config.yaml").read_text(encoding="utf-8"))
p3 = yaml.safe_load((ROOT / "config" / "phase3_config.yaml").read_text(encoding="utf-8"))

# rebuild the busy_resources synthetic state
mi = (ROOT / "runs" / "phase2_rule_manager" / "C2_B" / "manager_inputs.jsonl")
base = json.loads([l for l in mi.read_text(encoding="utf-8").splitlines() if l.strip()][0])


def busy(gs):
    g = copy.deepcopy(gs)
    for a in g["air"]:
        if a["id"] in ("M-UAV-01", "M-UAV-02"):
            a["status"] = "BUSY"
            a["availability"] = "BUSY"
            a["reassignable"] = False
            a["current_mission"] = "M-M-BACKUP-001"
            a["mission_priority"] = "HIGH"
    return g


gs = busy(base)

mgr = LLMManager(cfg, p3)
prompt = mgr.prompt_template.replace(
    "{GLOBAL_STATE}", json.dumps(gs, sort_keys=True, ensure_ascii=False, separators=(",", ":")))

client = LLMClient(base_url="http://192.168.27.4:18888/v1",
                   model="corp-ai/openai/deepseek-v4-pro",
                   api_key_env="CORP_AI_API_KEY", temperature=0.0, max_tokens=2048)

for i in range(3):
    resp = client.chat([{"role": "user", "content": prompt}])
    content = resp["content"]
    obj, method = mgr._extract_json(content)
    print(f"\n===== call {i} | latency={resp['latency_s']}s | extraction={method} =====")
    print("RAW CONTENT (first 600 chars):")
    print(repr(content[:600]))
    print("--- parsed:", json.dumps(obj, ensure_ascii=False)[:300] if obj else "FAILED")
