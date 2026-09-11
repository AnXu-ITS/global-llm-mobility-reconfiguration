"""Smoke-test the LLM Manager on one real Phase-2 Global State snapshot."""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from managers.llm_manager import LLMManager  # noqa: E402

cfg = yaml.safe_load((ROOT / "config" / "scenario_config.yaml").read_text(encoding="utf-8"))
p3 = yaml.safe_load((ROOT / "config" / "phase3_config.yaml").read_text(encoding="utf-8"))

# C2_B t=300: B1 closure + critical mission dispatch moment.
inputs = (ROOT / "runs" / "phase2_rule_manager" / "C2_B" / "manager_inputs.jsonl")
lines = [l.strip() for l in inputs.read_text(encoding="utf-8").splitlines() if l.strip()]
gs = json.loads(lines[0])

mgr = LLMManager(cfg, p3)
decision = mgr.decide(gs)
print(json.dumps(decision, indent=2, ensure_ascii=False))
