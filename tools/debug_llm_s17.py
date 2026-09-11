"""Debug raw outputs for the states that hit JSON_ERROR (S17/S19)."""
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
    raise KeyError(t)


states = {"S17": snap("C2_A", 361), "S19": snap("C2_C", 361)}

for name, gs in states.items():
    prompt = mgr.prompt_template.replace(
        "{GLOBAL_STATE}", json.dumps(gs, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    print(f"\n############ {name} ############")
    for i in range(2):
        try:
            resp = mgr.client.chat([{"role": "user", "content": prompt}])
            raw = resp["content"]
            obj, method = mgr._extract_json(raw)
            print(f"--- call {i}: lat={resp['latency_s']}s extract={method} parsed={obj is not None}")
            print("RAW:", repr(raw[:400]))
        except Exception as e:
            print(f"--- call {i} ERROR: {type(e).__name__} {e}")
