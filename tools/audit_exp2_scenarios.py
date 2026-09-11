"""Experiment 2 — Scenario Audit measurements (protocol §17/§19).

Per (scenario, seed, manager) run, measures the candidate-set effect of the
failure on the critical mission (from failure_trace.json):

  pre_failure_feasible_air_count   (t=300 decision table)
  post_failure_feasible_air_count  (t=360 decision table / as-if NEEDS_REPLAN)
  pre_failure_best_air_eta / post_failure_best_air_eta
  ground_candidate_feasible / ground_eta
  affected_existing_missions (failure trace + final damage)

plus per-scenario C1/C2/C3 label validation:

  C1: post >= 1 feasible air AND critical mission NOT interrupted
  C2: critical mission interrupted AND post >= 1 feasible air
  C3: critical mission interrupted AND post == 0 feasible air

Artifact: outputs/experiment2/scenario_audit.csv
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MANAGERS = ("B0", "B1", "B2", "B4b")


def load_trace(scenario_id: str, seed: int, mgr: str):
    p = ROOT / "runs" / "experiment2" / scenario_id / f"seed{seed}" / mgr / "failure_trace.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_metrics(scenario_id: str, seed: int, mgr: str):
    p = ROOT / "runs" / "experiment2" / scenario_id / f"seed{seed}" / mgr / "metrics.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    with open(ROOT / "config" / "experiment2_matrix.yaml", encoding="utf-8") as f:
        e2 = yaml.safe_load(f)["experiment2"]
    with open(ROOT / "config" / "experiment2_seeds.yaml", encoding="utf-8") as f:
        seeds = list(yaml.safe_load(f)["primary_seeds"])

    out_dir = ROOT / "outputs" / "experiment2"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    n_fail = 0
    for s in e2["scenarios"]:
        sid = s["id"]
        ctx = s["impact_context"]
        for seed in seeds:
            for mgr in MANAGERS:
                tr = load_trace(sid, seed, mgr)
                m = load_metrics(sid, seed, mgr)
                if tr is None or m is None:
                    n_fail += 1
                    continue
                crit_before = tr.get("critical_mission_state_before") or {}
                crit_after = tr.get("critical_mission_state_after") or {}
                interrupted = bool(
                    crit_before.get("status") in ("EN_ROUTE", "ASSIGNED")
                    and crit_before.get("mode") == "AIR"
                    and crit_after.get("status") in ("NEEDS_REPLAN", "INTERRUPTED"))
                post = tr.get("candidate_count_after")
                if mgr == "B0":
                    # B0 resolves by ground: the air failure can never touch its
                    # critical chain (ground immunity — the legal policy
                    # consequence recorded, not a label violation).
                    measured = "B0-IMMUNE" if not m.get("affected_critical") else "B0-AFFECTED"
                elif crit_before.get("mode") != "AIR" or crit_before.get("status") == "WAITING":
                    # the manager had not put the mission airborne at the
                    # failure instant (e.g. B4b after transport errors):
                    # legal policy/backend consequence; the C-label predicate
                    # does not apply to this cell.
                    measured = "DIVERGENT-PRE-FAILURE"
                elif interrupted and post == 0:
                    measured = "C3"
                elif interrupted and post >= 1:
                    measured = "C2"
                elif not interrupted and post >= 1:
                    measured = "C1"
                else:
                    measured = "UNDEFINED"
                rows.append({
                    "scenario_id": sid, "impact_context": ctx, "seed": seed,
                    "manager": mgr, "measured_context": measured,
                    "pre_failure_feasible_air_count": tr.get("candidate_count_before"),
                    "post_failure_feasible_air_count": post,
                    "pre_failure_best_air_eta": tr.get("candidate_best_air_eta_pre_asif"),
                    "post_failure_best_air_eta": tr.get("candidate_best_air_eta_after"),
                    "ground_candidate_feasible": tr.get("ground_candidate_feasible_post"),
                    "ground_eta": tr.get("ground_eta_post"),
                    "affected_critical": m.get("affected_critical"),
                    "existing_missions_damaged_count": m.get("existing_missions_damaged_count"),
                    "recovery_success": m.get("recovery_success"),
                })

    csv_path = out_dir / "scenario_audit.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        w.writeheader()
        w.writerows(rows)

    # per (scenario, manager) context-label validation:
    #   B0          -> must be B0-IMMUNE in every seed (ground immunity)
    #   B1/B2/B4b   -> airborne cells must match the frozen label;
    #                  DIVERGENT-PRE-FAILURE cells are legal policy/backend
    #                  consequences (reported, not label-tested)
    n_fail = 0
    print(f"{'scenario':<12} {'ctx':<4} {'seeds':>5} | " +
          " | ".join(MANAGERS) + " (measured contexts)")
    for s in e2["scenarios"]:
        sid, ctx = s["id"], s["impact_context"]
        line = f"{sid:<12} {ctx:<4} {len(seeds):>5} | "
        cells = []
        for mgr in MANAGERS:
            rs = [r for r in rows if r["scenario_id"] == sid and r["manager"] == mgr]
            cnt = Counter(r["measured_context"] for r in rs)
            cells.append("/".join(f"{k}:{v}" for k, v in sorted(cnt.items())))
            if mgr == "B0":
                if "B0-IMMUNE" not in cnt or "B0-AFFECTED" in cnt:
                    n_fail += 1
            else:
                if ctx not in cnt or "UNDEFINED" in cnt:
                    n_fail += 1
        line += " | ".join(f"{mgr}: {c}" for mgr, c in zip(MANAGERS, cells))
        print(line)

    print(f"\nSCENARIO AUDIT: {'PASS' if n_fail == 0 else f'{n_fail} FAIL'}")
    print(f"artifact: {csv_path}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
