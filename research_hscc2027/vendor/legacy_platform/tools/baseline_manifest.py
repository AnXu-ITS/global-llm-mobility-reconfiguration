"""Gather version manifest + SHA-256 for EXPERIMENT1_BASELINE_FREEZE.md."""
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


cfg = yaml.safe_load((ROOT / "config" / "scenario_config.yaml").read_text(encoding="utf-8"))
gs = json.loads((ROOT / "schemas" / "global_state_v1.schema.json").read_text(encoding="utf-8"))
act = json.loads((ROOT / "schemas" / "manager_action_v1.schema.json").read_text(encoding="utf-8"))
p3 = yaml.safe_load((ROOT / "config" / "phase3_config.yaml").read_text(encoding="utf-8"))
rc = yaml.safe_load((ROOT / "config" / "resource_compatibility.yaml").read_text(encoding="utf-8"))

print("scenario_version:", cfg.get("scenario_version"))
print("scenario_id:", cfg.get("scenario_id"))
print("global_state_schema_version:", gs.get("version"))
print("manager_action_schema_version:", act.get("version"))
print("prompt_version:", p3.get("prompt_version", "manager_v1"))
print("llm:", json.dumps(p3.get("llm", {}), sort_keys=True))
print("resource_compat keys:", list(rc.keys()))

print("\n--- SHA-256 (16 hex) of frozen files ---")
for f in [
    "config/scenario_config.yaml",
    "config/phase3_config.yaml",
    "config/resource_compatibility.yaml",
    "schemas/global_state_v1.schema.json",
    "schemas/manager_action_v1.schema.json",
    "prompts/manager_v1.txt",
    "managers/rule_based.py",
    "managers/llm_manager.py",
    "managers/llm_client.py",
    "safety/feasibility_checker.py",
    "safety/semantic_validator.py",
    "orchestrator/phase2_orchestrator.py",
    "orchestrator/phase3_orchestrator.py",
    "state/global_state.py",
    "orchestrator/registry.py",
    "failures/c2_lost.py",
]:
    print(f"{sha(ROOT / f)}  {f}")
