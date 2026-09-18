"""Experiment 2 — Deterministic Replay Audit (protocol §30).

Randomly selects 2 (scenario, seed) pairs per failure family (12 pairs),
re-runs every manager:
  - B0/B1/B2: plain deterministic rerun -> non-API artifacts must be
    byte-identical to the primary run;
  - B4b: replay of the CACHED primary decisions (no LLM call) -> identical
    actions feed the simulator -> artifacts byte-identical.
    (Replay runs are reproducibility ONLY, never independent samples.)

Artifact comparison: events.csv / actions.csv / missions.csv / clock_sync.csv
+ failure_trace.json (excluding the hashes/fields that only differ by dir).
"""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VENV_PY = r"C:\Users\xuan1\.venvs\bluesky\Scripts\python.exe"
MANAGERS = ("B0", "B1", "B2", "B4b")
COMPARE_FILES = ("events.csv", "actions.csv", "missions.csv", "clock_sync.csv")


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> int:
    with open(ROOT / "config" / "experiment2_matrix.yaml", encoding="utf-8") as f:
        e2 = yaml.safe_load(f)["experiment2"]
    with open(ROOT / "config" / "experiment2_seeds.yaml", encoding="utf-8") as f:
        seeds = list(yaml.safe_load(f)["primary_seeds"])

    rng = random.Random(20260905)
    by_family = {}
    for s in e2["scenarios"]:
        by_family.setdefault(s["failure_family"], []).append(s["id"])
    picks = []
    for fam in ("F1", "F2", "F3", "F4", "F5", "F6"):
        ids = by_family[fam]
        chosen = []
        while len(chosen) < 2:
            sid = rng.choice(ids)
            seed = rng.choice(seeds)
            if (sid, seed) not in chosen and (sid, seed) not in picks:
                chosen.append((sid, seed))
        picks.extend(chosen)

    n_fail = 0
    rows = []
    for sid, seed in picks:
        for mgr in MANAGERS:
            orig = ROOT / "runs" / "experiment2" / sid / f"seed{seed}" / mgr
            rep = ROOT / "runs" / f"exp2_replay" / sid / f"seed{seed}" / mgr
            rep.mkdir(parents=True, exist_ok=True)
            cmd = [VENV_PY, str(ROOT / "tools" / "run_experiment2_audit.py"),
                   "--scenario", sid, "--seed", str(seed), "--manager", mgr,
                   "--run-dir", str(rep)]
            if mgr == "B4b":
                cmd += ["--replay-from", str(orig)]
            r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                               text=True, timeout=1800)
            if r.returncode != 0:
                print(f"[FAIL] {sid}/seed{seed}/{mgr}: replay run failed")
                n_fail += 1
                continue
            ok = True
            detail = {}
            for fname in COMPARE_FILES:
                same = md5(orig / fname) == md5(rep / fname)
                detail[fname] = same
                if not same:
                    ok = False
            # failure_trace: compare the deterministic fields only
            try:
                to = json.loads((orig / "failure_trace.json").read_text(encoding="utf-8"))
                tr = json.loads((rep / "failure_trace.json").read_text(encoding="utf-8"))
                trace_same = (to["failure_config_hash"] == tr["failure_config_hash"]
                              and to["state_before"] == tr["state_before"]
                              and to["state_after"] == tr["state_after"])
            except Exception:
                trace_same = False
            detail["failure_trace"] = trace_same
            if not trace_same:
                ok = False
            if not ok:
                n_fail += 1
            print(f"[{'PASS' if ok else 'FAIL'}] {sid}/seed{seed}/{mgr}: {detail}")
            rows.append({"scenario_id": sid, "seed": seed, "manager": mgr,
                         "pass": ok, **detail})

    out_dir = ROOT / "outputs" / "experiment2"
    out_dir.mkdir(parents=True, exist_ok=True)
    import csv
    with open(out_dir / "replay_audit.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # report
    md = ["# Experiment 2 — Replay / Reproducibility Audit (protocol §30)",
          "",
          f"Selected {len(picks)} (scenario, seed) pairs — 2 per failure family — "
          f"replayed for all 4 managers ({len(rows)} runs).",
          "",
          "- B0/B1/B2: deterministic rerun; non-API artifacts must be "
          "byte-identical to the primary run.",
          "- B4b: replay of the CACHED primary decisions (no LLM call, marked "
          "`replay: true`) — reproducibility ONLY; these runs are NEVER counted "
          "as independent samples (frozen rule §28/§30).",
          "",
          "| scenario | seed | manager | replay verdict |",
          "|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['scenario_id']} | {r['seed']} | {r['manager']} | "
                  f"{'PASS' if r['pass'] else 'FAIL'} |")
    verdict = "PASS" if n_fail == 0 else f"{n_fail} FAIL"
    md += ["", f"**Verdict: {verdict}**", "",
           "Compared artifacts: events.csv / actions.csv / missions.csv / "
           "clock_sync.csv (byte-identical) + failure_trace.json deterministic "
           "fields (failure_config_hash, state_before, state_after)."]
    (ROOT / "reports" / "experiment2" / "EXPERIMENT2_REPLAY_AUDIT.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")
    print(f"\nREPLAY AUDIT: {'PASS' if n_fail == 0 else f'{n_fail} FAIL'} "
          f"({len(rows)} replay runs)")
    print("report: reports/experiment2/EXPERIMENT2_REPLAY_AUDIT.md")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
