"""Experiment 2 — artifact contract verifier (protocol §29, acceptance E2-T26).

Every run must contain: run_config.yaml, events.csv, ground_state.csv,
air_state.csv, missions.csv, candidate_info.jsonl, manager_inputs.jsonl,
manager_outputs.jsonl, action_pipeline.jsonl, feasibility_checks.jsonl,
actions.csv, metrics.json, runtime.json, failure_trace.json
(+ inherited: semantic_checks.jsonl, violations.csv, registry_final.json).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REQUIRED = [
    "run_config.yaml", "events.csv", "ground_state.csv", "air_state.csv",
    "missions.csv", "candidate_info.jsonl", "manager_inputs.jsonl",
    "manager_outputs.jsonl", "action_pipeline.jsonl", "feasibility_checks.jsonl",
    "actions.csv", "metrics.json", "runtime.json", "failure_trace.json",
]

INHERITED = ["semantic_checks.jsonl", "violations.csv", "registry_final.json"]


def main() -> int:
    with open(ROOT / "config" / "experiment2_matrix.yaml", encoding="utf-8") as f:
        e2 = yaml.safe_load(f)["experiment2"]
    with open(ROOT / "config" / "experiment2_seeds.yaml", encoding="utf-8") as f:
        seeds = list(yaml.safe_load(f)["primary_seeds"])
    managers = ("B0", "B1", "B2", "B4b")

    total = 0
    ok = 0
    missing_cells = []
    missing_artifacts = []
    for s in e2["scenarios"]:
        for seed in seeds:
            for mgr in managers:
                total += 1
                rd = ROOT / "runs" / "experiment2" / s["id"] / f"seed{seed}" / mgr
                if not (rd / "metrics.json").exists():
                    missing_cells.append(f"{s['id']}/seed{seed}/{mgr}")
                    continue
                bad = [a for a in REQUIRED if not (rd / a).exists()]
                if bad:
                    missing_artifacts.append(f"{s['id']}/seed{seed}/{mgr}: {bad}")
                    continue
                # failure_trace sanity
                tr = json.loads((rd / "failure_trace.json").read_text(encoding="utf-8"))
                need = ["failure_family", "failure_time", "target", "state_before",
                        "state_after", "affected_resources", "candidate_count_before",
                        "candidate_count_after", "local_contingency",
                        "manager_trigger_time", "first_valid_replan_time"]
                if any(k not in tr for k in need):
                    missing_artifacts.append(
                        f"{s['id']}/seed{seed}/{mgr}: failure_trace missing keys")
                    continue
                ok += 1

    print(f"cells: {ok}/{total} complete with full artifact contract")
    print(f"missing cells: {len(missing_cells)}")
    for c in missing_cells[:20]:
        print("  ", c)
    print(f"missing artifacts: {len(missing_artifacts)}")
    for c in missing_artifacts[:20]:
        print("  ", c)
    verdict = ok == total
    print(f"ARTIFACT CONTRACT: {'PASS' if verdict else 'FAIL'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
