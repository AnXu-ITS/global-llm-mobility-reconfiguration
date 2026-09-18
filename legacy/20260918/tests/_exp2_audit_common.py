"""Shared helpers for the Experiment-2 failure audit tests (protocol §10).

Each family test proves the 8 audit points:
  1. failure event fires correctly
  2. affected state changes correctly
  3. unaffected state is NOT wrongly modified
  4. the failure is visible in the Global State
  5. the Candidate Generator updates correctly
  6. the checker enforces the hard constraints
  7. the simulator clock is unaffected
  8. replay is deterministic
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VENV_PY = r"C:\Users\user\.venvs\bluesky\Scripts\python.exe"


RESULTS = []


def record(name, passed, evidence, results=None):
    (results if results is not None else RESULTS).append((name, passed, evidence))
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: {evidence}")


def run_combo(scenario_id: str, seed: int, manager: str, tag: str) -> Path:
    """Run one combo in a dedicated directory (run_dir override via --direct)."""
    rd = ROOT / "runs" / f"exp2_audit_{tag}"
    cmd = [VENV_PY, str(ROOT / "tools" / "run_experiment2_audit.py"),
           "--scenario", scenario_id, "--seed", str(seed), "--manager", manager,
           "--run-dir", str(rd)]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=1800)
    return rd, r


def read_csv(path: Path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: Path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def summary(failures) -> int:
    nfail = sum(1 for _, p, _ in failures if not p)
    print(f"\nSUMMARY: {len(failures) - nfail}/{len(failures)} PASS, {nfail} FAIL")
    return 1 if nfail else 0


def final_summary() -> int:
    nfail = sum(1 for _, p, _ in RESULTS if not p)
    print(f"\nSUMMARY: {len(RESULTS) - nfail}/{len(RESULTS)} PASS, {nfail} FAIL")
    return 1 if nfail else 0
