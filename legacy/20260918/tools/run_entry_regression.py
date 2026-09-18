"""Experiment 2 Entry Regression Gate (§1 of the Exp-2 protocol).

Reruns ONLY the existing (frozen) regression tests — no new test design:
  Phase 1:   tests/test_geographic_alignment.py, tests/test_acceptance.py,
             tests/test_bluesky_state_provenance.py,
             tests/test_clock_sync_post_resize.py
  Phase 2:   tests/test_rule_based_manager.py,
             tests/test_c2_local_contingency.py,
             tests/test_phase2_acceptance.py,
             tests/test_reverse_air_post_resize.py
  Phase 3:   tests/test_phase3_acceptance.py,
             tests/test_feasibility_post_resize.py
  Replay:    tests/test_deterministic_replay_post_resize.py
  E1 frozen artifact hash check vs outputs/file_hashes_final.json.

Writes outputs/experiment2/entry_regression.json (used by the report generator).
Exit code 0 iff every test passes.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PY = r"C:\Users\user\.venvs\bluesky\Scripts\python.exe"

TESTS = [
    ("geographic_alignment", "tests/test_geographic_alignment.py"),
    ("bluesky_state_provenance", "tests/test_bluesky_state_provenance.py"),
    ("clock_sync_post_resize", "tests/test_clock_sync_post_resize.py"),
    ("phase1_acceptance_T2_T3_T4_T8_T9", "tests/test_acceptance.py"),
    ("rule_based_manager", "tests/test_rule_based_manager.py"),
    ("c2_local_contingency", "tests/test_c2_local_contingency.py"),
    ("phase2_acceptance", "tests/test_phase2_acceptance.py"),
    ("reverse_air_post_resize", "tests/test_reverse_air_post_resize.py"),
    ("feasibility_post_resize", "tests/test_feasibility_post_resize.py"),
    ("deterministic_replay_post_resize", "tests/test_deterministic_replay_post_resize.py"),
    ("phase3_acceptance", "tests/test_phase3_acceptance.py"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_hash_check() -> dict:
    manifest = json.loads((ROOT / "outputs" / "file_hashes_final.json").read_text(encoding="utf-8"))
    mismatches = []
    for rel, want in manifest.items():
        p = ROOT / Path(*rel.split("/"))
        if not p.exists():
            mismatches.append(f"{rel}: MISSING")
            continue
        got = sha256(p)
        if got != want:
            mismatches.append(f"{rel}: mismatch")
    return {"checked": len(manifest), "mismatches": mismatches,
            "pass": len(mismatches) == 0}


def main() -> int:
    t0 = time.time()
    results = {}
    # 1) frozen-hash check (E1 artifacts untouched)
    results["e1_frozen_hash_check"] = frozen_hash_check()
    # 2) rerun existing tests
    for name, rel in TESTS:
        p = ROOT / rel
        t1 = time.time()
        try:
            r = subprocess.run([VENV_PY, str(p)], cwd=str(ROOT),
                               capture_output=True, text=True, timeout=3600)
            ok = r.returncode == 0
            tail = (r.stdout or "").strip().splitlines()[-12:]
            results[name] = {"path": rel, "pass": ok, "exit_code": r.returncode,
                             "wall_s": round(time.time() - t1, 1),
                             "tail": "\n".join(tail)}
            print(f"[{'PASS' if ok else 'FAIL'}] {name} ({results[name]['wall_s']}s)",
                  flush=True)
        except subprocess.TimeoutExpired:
            results[name] = {"path": rel, "pass": False, "exit_code": None,
                             "wall_s": round(time.time() - t1, 1),
                             "tail": "TIMEOUT (3600 s)"}
            print(f"[FAIL] {name}: TIMEOUT", flush=True)
        except Exception as e:  # noqa: BLE001
            results[name] = {"path": rel, "pass": False, "exit_code": None,
                             "wall_s": round(time.time() - t1, 1), "tail": str(e)}
            print(f"[FAIL] {name}: {e}", flush=True)

    out_dir = ROOT / "outputs" / "experiment2"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "entry_regression.json").write_text(
        json.dumps({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "total_wall_s": round(time.time() - t0, 1), "results": results},
                   indent=2), encoding="utf-8")

    n_fail = sum(1 for v in results.values() if not v["pass"])
    print(f"\nENTRY REGRESSION: {len(results) - n_fail}/{len(results)} PASS, "
          f"{n_fail} FAIL, total {time.time() - t0:.1f}s")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
