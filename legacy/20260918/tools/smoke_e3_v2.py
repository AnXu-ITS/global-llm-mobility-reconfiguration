"""Smoke test for E3 v2 fixes: all 12 scenarios x B0/B1 (no LLM), 1 seed.

Verifies each (scenario, manager) completes and writes metrics.json. Runs in
parallel subprocess workers (each writes its own console log, no stdout pipes).
"""
from __future__ import annotations

import concurrent.futures
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEED = "20240601"
MANAGERS = ("B0", "B1")


def main() -> int:
    e3 = yaml.safe_load((ROOT / "config" / "experiment3_matrix.yaml").read_text(encoding="utf-8"))["experiment3"]
    combos = [(s["id"], m) for s in e3["scenarios"] for m in MANAGERS]

    def work(c):
        sid, m = c
        rd = ROOT / "runs" / "experiment3" / sid / f"seed{SEED}" / m
        rd.mkdir(parents=True, exist_ok=True)
        logf = rd / "run_console.log"
        with open(logf, "w", encoding="utf-8") as lf:
            rc = subprocess.run(
                [sys.executable, "tools/run_experiment3.py",
                 "--scenario", sid, "--seed", SEED, "--manager", m, "--direct"],
                cwd=str(ROOT), stdout=lf, stderr=subprocess.STDOUT).returncode
        ok = (rc == 0) and (rd / "metrics.json").exists()
        return sid, m, rc, ok

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(work, combos):
            results.append(r)
            print(f"{r[0]:16s} {r[1]:3s} rc={r[2]} {'OK' if r[3] else 'FAIL'}", flush=True)

    fails = [r for r in results if not r[3]]
    print(f"\n{len(results)-len(fails)}/{len(results)} OK, {len(fails)} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
