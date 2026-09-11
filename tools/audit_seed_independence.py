"""Seed-independence audit (Finalization §9).

For each (scenario, seed) it runs the deterministic B1 manager once (the
manager INPUT is the shared Global State, identical across managers for a given
seed) and verifies that different seeds genuinely change the manager-visible
state.  Outputs outputs/experiment1_final/seed_independence_audit.csv.

Fields: scenario_id, seed, global_state_hash, prompt_hash, ground_eta,
aircraft_state_hash, mission_state_hash, cache_hit, backend_latency.

The B1 manager issues no LLM call, so prompt_hash / cache_hit / backend_latency
are recorded as "n/a (deterministic manager)".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RUNS = ROOT / "runs" / "experiment1_final"
OUT = ROOT / "outputs" / "experiment1_final"
RUNNER = ROOT / "tools" / "run_experiment1_final.py"

AUDIT_SCENARIOS = ("E1_H_C_low", "E1_H_H_high", "E1_M_C_high")
AUDIT_SEEDS = [20240601, 20240602, 20240603, 20240604, 20240605,
               20240606, 20240607, 20240608, 20240609, 20240610]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def first_input(run_dir: Path) -> dict:
    p = run_dir / "manager_inputs.jsonl"
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            return json.loads(line)
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default=",".join(AUDIT_SCENARIOS))
    ap.add_argument("--seeds", default=",".join(str(s) for s in AUDIT_SEEDS))
    args = ap.parse_args()

    scenarios = args.scenarios.split(",")
    seeds = [int(x) for x in args.seeds.split(",")]

    rows = []
    for s in scenarios:
        for sd in seeds:
            rd = RUNS / s / f"seed{sd}" / "B1"
            if not (rd / "metrics.json").exists():
                rcode = subprocess.run(
                    [sys.executable, str(RUNNER), "--scenario", s,
                     "--seed", str(sd), "--manager", "B1", "--direct"],
                    cwd=str(ROOT)).returncode
                if rcode != 0:
                    rows.append({"scenario_id": s, "seed": sd, "global_state_hash": "RUN_FAILED",
                                 "prompt_hash": "n/a", "ground_eta": None,
                                 "aircraft_state_hash": "RUN_FAILED",
                                 "mission_state_hash": "RUN_FAILED",
                                 "cache_hit": "n/a", "backend_latency": "n/a"})
                    continue
            gs = first_input(rd)
            if not gs:
                rows.append({"scenario_id": s, "seed": sd, "global_state_hash": "EMPTY",
                             "prompt_hash": "n/a", "ground_eta": None,
                             "aircraft_state_hash": "EMPTY", "mission_state_hash": "EMPTY",
                             "cache_hit": "n/a", "backend_latency": "n/a"})
                continue
            air_json = json.dumps(gs.get("air", []), sort_keys=True)
            mis_json = json.dumps(gs.get("missions", {}), sort_keys=True)
            rows.append({
                "scenario_id": s,
                "seed": sd,
                "global_state_hash": sha(json.dumps(gs, sort_keys=True)),
                "prompt_hash": "n/a (deterministic manager)",
                "ground_eta": gs.get("ground", {}).get("ground_fallback_eta_s"),
                "aircraft_state_hash": sha(air_json),
                "mission_state_hash": sha(mis_json),
                "cache_hit": "n/a",
                "backend_latency": "n/a",
            })

    OUT.mkdir(parents=True, exist_ok=True)
    outp = OUT / "seed_independence_audit.csv"
    import csv
    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "seed", "global_state_hash",
                                          "prompt_hash", "ground_eta",
                                          "aircraft_state_hash", "mission_state_hash",
                                          "cache_hit", "backend_latency"])
        w.writeheader()
        w.writerows(rows)

    # per-scenario distinct-hash summary
    print("scenario | n_seeds | distinct global_state_hash | distinct aircraft_hash | distinct mission_hash")
    for s in scenarios:
        sr = [r for r in rows if r["scenario_id"] == s]
        g = len({r["global_state_hash"] for r in sr if r["global_state_hash"] not in ("RUN_FAILED", "EMPTY")})
        a = len({r["aircraft_state_hash"] for r in sr if r["aircraft_state_hash"] not in ("RUN_FAILED", "EMPTY")})
        m = len({r["mission_state_hash"] for r in sr if r["mission_state_hash"] not in ("RUN_FAILED", "EMPTY")})
        print(f"{s} | {len(sr)} | {g} | {a} | {m}")
    print(f"\n[saved] {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
