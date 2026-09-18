"""Verify the Rule Manager now filters unavailable destinations at candidate time."""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from managers.rule_based import RuleBasedManager  # noqa: E402

cfg = yaml.safe_load((ROOT / "config" / "scenario_config.yaml").read_text(encoding="utf-8"))
rule = RuleBasedManager(cfg)

mi = [json.loads(l) for l in
      (ROOT / "runs" / "phase2_rule_manager" / "C2_B" / "manager_inputs.jsonl")
      .read_text(encoding="utf-8").splitlines() if l.strip()]

# 1. normal critical mission -> DISPATCH M-UAV-02 (unchanged)
d = rule.decide(mi[0])
print("normal t=300:", d["action"]["type"], d["action"].get("aircraft_id"), "->", d["action"].get("target_site"))
assert d["action"]["type"] == "DISPATCH" and d["action"]["aircraft_id"] == "M-UAV-02"

# 2. V1 unavailable -> must NOT dispatch to V1 (now ground fallback, no air to V1)
import copy
gs = copy.deepcopy(mi[0])
gs["infrastructure"]["landing_sites"]["V1"]["state"] = "UNAVAILABLE"
d2 = rule.decide(gs)
print("V1-unavailable:", d2["action"]["type"], d2["action"].get("aircraft_id"), "->", d2["action"].get("target_site"))
assert d2["action"]["type"] == "GROUND_FALLBACK", f"expected GROUND_FALLBACK, got {d2['action']}"
# confirm no air candidate proposes V1
air_cands = [c for c in d2["candidates"] if c["type"] == "AIR"]
assert all(c.get("route") != ["V2", "V1"] and "V1" not in (c.get("route") or []) or not c["feasible"]
           for c in air_cands), "some feasible air candidate still targets V1"
print("\nPASS: Rule Manager filters unavailable destination at candidate generation")
