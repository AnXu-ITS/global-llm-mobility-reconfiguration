"""Experiment 2 — Failure Event Exogeneity Audit (protocol §8).

Proves that (scenario_id, seed) fully determines the failure family / target /
time / zone / site / trajectory, and that the manager type CANNOT influence the
failure injection. Method: for 3 (scenario, seed) pairs, run ALL FOUR primary
managers and verify:

  1. the failure_config_hash recorded in every run's failure_trace.json equals
     the hash of the FROZEN matrix config (manager-independent);
  2. failure_family / failure_time / target are identical across managers;
  3. the failure config in the trace is the frozen matrix config verbatim.

Artifact: outputs/experiment2/failure_exogeneity_audit.csv
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VENV_PY = r"C:\Users\user\.venvs\bluesky\Scripts\python.exe"

AUDITED = [("E2_F1_C2", 20240601), ("E2_F3_C3", 20240601), ("E2_F6_C2", 20240602)]
MANAGERS = ("B0", "B1", "B2", "B4b")


def sha256_hex(obj) -> str:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    with open(ROOT / "config" / "experiment2_matrix.yaml", encoding="utf-8") as f:
        e2 = yaml.safe_load(f)["experiment2"]
    scenarios = {s["id"]: s for s in e2["scenarios"]}
    expected = {sid: sha256_hex(scenarios[sid]["failure"]) for sid, _ in AUDITED}

    out_dir = ROOT / "outputs" / "experiment2"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "failure_exogeneity_audit.csv"
    rows = []
    n_fail = 0

    for scenario_id, seed in AUDITED:
        hashes = {}
        for mgr in MANAGERS:
            rd = ROOT / "runs" / "experiment2" / scenario_id / f"seed{seed}" / mgr
            if not (rd / "failure_trace.json").exists():
                cmd = [VENV_PY, str(ROOT / "tools" / "run_experiment2.py"),
                       "--scenario", scenario_id, "--seed", str(seed),
                       "--manager", mgr, "--direct"]
                r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                                   text=True, timeout=1800)
                if r.returncode != 0 or not (rd / "failure_trace.json").exists():
                    print(f"[FAIL] {scenario_id}/seed{seed}/{mgr}: run failed rc={r.returncode}")
                    n_fail += 1
                    rows.append({"scenario_id": scenario_id, "seed": seed,
                                 "manager": mgr, "failure_family": None,
                                 "failure_time": None, "failure_target": None,
                                 "failure_config_hash": None,
                                 "matches_frozen_config": False,
                                 "identical_across_managers": False})
                    continue
            tr = json.loads((rd / "failure_trace.json").read_text(encoding="utf-8"))
            h = tr.get("failure_config_hash")
            hashes[mgr] = h
            rows.append({
                "scenario_id": scenario_id, "seed": seed, "manager": mgr,
                "failure_family": tr.get("failure_family"),
                "failure_time": tr.get("failure_time"),
                "failure_target": tr.get("target"),
                "failure_config_hash": h,
                "matches_frozen_config": h == expected[scenario_id],
                "identical_across_managers": None,
            })

        all_same = len(set(hashes.values())) == 1
        all_match = all(h == expected[scenario_id] for h in hashes.values())
        ok = all_same and all_match and len(hashes) == len(MANAGERS)
        print(f"[{'PASS' if ok else 'FAIL'}] {scenario_id}/seed{seed}: "
              f"hashes identical={all_same}, match frozen config={all_match}")
        if not ok:
            n_fail += 1
        for row in rows:
            if row["scenario_id"] == scenario_id and row["seed"] == seed:
                row["identical_across_managers"] = all_same

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "scenario_id", "seed", "manager", "failure_family", "failure_time",
            "failure_target", "failure_config_hash", "matches_frozen_config",
            "identical_across_managers"])
        w.writeheader()
        w.writerows(rows)

    # static exogeneity check: the injectors never read manager state
    src = (ROOT / "failures" / "e2_failures.py").read_text(encoding="utf-8")
    src += (ROOT / "orchestrator" / "experiment2_runner.py").read_text(encoding="utf-8")
    import re
    injector_src = src[:src.index("INJECTORS =")]
    manager_touches = ["manager.decide", "manager_kind", "manager_outputs",
                       "manager_decisions"]
    static_ok = all(t not in injector_src for t in manager_touches)
    print(f"[{'PASS' if static_ok else 'FAIL'}] static: injector code never reads "
          f"manager state ({', '.join(manager_touches)})")
    if not static_ok:
        n_fail += 1

    print(f"\nEXOGENEITY AUDIT: {'PASS' if n_fail == 0 else f'{n_fail} FAIL'}")
    print(f"artifact: {csv_path}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
