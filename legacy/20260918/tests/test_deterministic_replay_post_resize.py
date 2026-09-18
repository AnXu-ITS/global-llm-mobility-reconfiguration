"""Deterministic replay regression (post-resize).

Runs the post-resize smoke test twice with the SAME scenario / seed /
deterministic manager action (no LLM) and requires the produced
events.csv / actions.csv / missions.csv / clock_sync.csv to be byte-identical.

Usage: python tests/test_deterministic_replay_post_resize.py
"""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VENV_PY = r"C:\Users\xuan1\.venvs\bluesky\Scripts\python.exe"
RUNNER = ROOT / "tools" / "run_post_resize_smoke.py"
A_DIR = ROOT / "runs" / "replay_post_a"
B_DIR = ROOT / "runs" / "replay_post_b"
FILES = ["events.csv", "actions.csv", "missions.csv", "clock_sync.csv"]


def _run(run_dir: Path) -> None:
    subprocess.run([VENV_PY, str(RUNNER), str(run_dir)],
                   capture_output=True, text=True, timeout=600, check=True)


def _fp(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main() -> int:
    _run(A_DIR)
    _run(B_DIR)

    ok = True
    for f in FILES:
        fa, fb = A_DIR / f, B_DIR / f
        if not fa.exists() or not fb.exists():
            print(f"[FAIL] {f}: missing ({fa.exists()},{fb.exists()})")
            ok = False
            continue
        ha, hb = _fp(fa), _fp(fb)
        identical = ha == hb
        ok = ok and identical
        print(f"{f}: {'byte-identical' if identical else 'DIFF'} "
              f"(md5 {ha[:8]}.. vs {hb[:8]}..)")

    print(f"\ndeterministic replay (post-resize): {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
