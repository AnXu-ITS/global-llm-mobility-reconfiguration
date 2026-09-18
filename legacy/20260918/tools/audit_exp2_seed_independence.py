"""Experiment 2 — Seed Independence Audit (protocol §26).

Reads the B1 run of every (scenario, seed) and verifies that different seeds
genuinely change the operational state. Fields (from failure_trace.json +
manager_inputs.jsonl):

  scenario_id, seed, initial_state_hash, pre_failure_state_hash,
  failure_config_hash, candidate_set_pre_hash, candidate_set_post_hash,
  prompt_hash, pre_failure_feasible_air, post_failure_feasible_air

Requirements (§26): different seeds -> genuinely different operational state;
same-prompt repeats are NOT replicates (here: hash distinctness across seeds).

Artifact: outputs/experiment2/seed_independence_audit.csv
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    with open(ROOT / "config" / "experiment2_matrix.yaml", encoding="utf-8") as f:
        e2 = yaml.safe_load(f)["experiment2"]
    with open(ROOT / "config" / "experiment2_seeds.yaml", encoding="utf-8") as f:
        seeds = list(yaml.safe_load(f)["primary_seeds"])

    out_dir = ROOT / "outputs" / "experiment2"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    missing = 0
    for s in e2["scenarios"]:
        for seed in seeds:
            rd = ROOT / "runs" / "experiment2" / s["id"] / f"seed{seed}" / "B1"
            ft_path = rd / "failure_trace.json"
            mi_path = rd / "manager_inputs.jsonl"
            if not ft_path.exists() or not mi_path.exists():
                missing += 1
                rows.append({"scenario_id": s["id"], "seed": seed,
                             "initial_state_hash": None,
                             "pre_failure_state_hash": None,
                             "failure_config_hash": None,
                             "candidate_set_pre_hash": None,
                             "candidate_set_post_hash": None,
                             "prompt_hash": None,
                             "pre_failure_feasible_air": None,
                             "post_failure_feasible_air": None})
                continue
            ft = json.loads(ft_path.read_text(encoding="utf-8"))
            first_input = None
            for line in mi_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    first_input = line
                    break
            rows.append({
                "scenario_id": s["id"], "seed": seed,
                "initial_state_hash": ft.get("initial_gs_hash"),
                "pre_failure_state_hash": ft.get("pre_failure_gs_hash"),
                "failure_config_hash": ft.get("failure_config_hash"),
                "candidate_set_pre_hash": ft.get("candidate_set_pre_hash"),
                "candidate_set_post_hash": ft.get("candidate_set_post_hash"),
                "prompt_hash": hashlib.sha256(first_input.encode("utf-8")).hexdigest()
                if first_input else None,
                "pre_failure_feasible_air": ft.get("candidate_count_before"),
                "post_failure_feasible_air": ft.get("candidate_count_after"),
            })

    csv_path = out_dir / "seed_independence_audit.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        w.writeheader()
        w.writerows(rows)

    # per-scenario distinctness of the initial state + pre-failure state
    n_fail = 0
    print(f"{'scenario':<12} {'seeds':>5} {'distinct_initial':>15} "
          f"{'distinct_prefail':>16} {'distinct_prompt':>15}")
    for s in e2["scenarios"]:
        rs = [r for r in rows if r["scenario_id"] == s["id"]]
        d_init = len({r["initial_state_hash"] for r in rs if r["initial_state_hash"]})
        d_pre = len({r["pre_failure_state_hash"] for r in rs if r["pre_failure_state_hash"]})
        d_prompt = len({r["prompt_hash"] for r in rs if r["prompt_hash"]})
        ok = d_init == len(seeds) and d_pre == len(seeds) and d_prompt == len(seeds)
        if not ok:
            n_fail += 1
        print(f"{s['id']:<12} {len(rs):>5} {d_init:>15} {d_pre:>16} {d_prompt:>15}"
              f"  {'PASS' if ok else 'FAIL'}")
    print(f"\nmissing cells: {missing}")
    print(f"SEED INDEPENDENCE: {'PASS' if n_fail == 0 and missing == 0 else 'FAIL'}")
    print(f"artifact: {csv_path}")
    return 1 if (n_fail or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
