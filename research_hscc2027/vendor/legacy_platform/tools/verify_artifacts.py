"""Verify the Experiment-1 Finalization artifact contract per run (Finalization §20).

Checks that every completed run dir has the required artifacts, and reports
any missing file or zero-size anomaly.  Also cross-checks the expected run count
(primary 12x20x4=960; ablation 6x10x1=60).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "experiment1_final"

REQUIRED = [
    "run_config.yaml", "events.csv", "ground_state.csv", "air_state.csv",
    "missions.csv", "candidate_info.jsonl", "manager_inputs.jsonl",
    "manager_outputs.jsonl", "feasibility_checks.jsonl", "actions.csv",
    "metrics.json", "runtime.json", "semantic_checks.jsonl",
    "action_pipeline.jsonl", "run_meta.json",
]


def check_run(run_dir: Path) -> List[str]:
    missing = []
    for name in REQUIRED:
        p = run_dir / name
        if not p.exists():
            missing.append(name + " (missing)")
        elif p.stat().st_size == 0 and not name.endswith(".jsonl"):
            missing.append(name + " (empty)")
    return missing


def main() -> int:
    arms = {"B0": [], "B1": [], "B2": [], "B4b": [], "B4a": []}
    problems: Dict[str, List[str]] = {}
    total = 0
    for mp in sorted(RUNS.glob("*/*/B*/metrics.json")):
        label = mp.parent.name
        run_dir = mp.parent
        total += 1
        arms.setdefault(label, []).append(run_dir)
        miss = check_run(run_dir)
        if miss:
            problems[str(run_dir.relative_to(RUNS))] = miss

    print("arm counts (metrics.json present):")
    for k, v in sorted(arms.items()):
        print(f"  {k}: {len(v)}")

    exp_primary = {"B0": 240, "B1": 240, "B2": 240, "B4b": 240}
    exp_ablation = {"B4a": 60}
    print("\ncompleteness vs expectation:")
    for k, want in {**exp_primary, **exp_ablation}.items():
        got = len(arms.get(k, []))
        mark = "OK" if got == want else f"SHORT {want - got}"
        print(f"  {k}: {got}/{want} {mark}")

    if problems:
        print(f"\n{len(problems)} run(s) with missing artifacts:")
        for k, v in list(problems.items())[:30]:
            print(" ", k, "->", v)
        return 1
    print(f"\nall {total} completed runs satisfy the artifact contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
