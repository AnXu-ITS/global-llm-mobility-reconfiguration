"""E1_H_H_high deep case study (Finalization §25).

For each of the 20 seeds, compares B2 vs B4b on: issued action, completion time,
deadline status, existing-service damage, the shared candidate table (target
mission priority, air/ground alternatives, preempted mission), and answers
whether B4b systematically trades existing-service preservation for emergency
completion speed, or the earlier divergence was a single-state artefact.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "experiment1_final"
OUT = ROOT / "outputs" / "experiment1_final"
SCEN = "E1_H_H_high"


def load_metrics(seed: int, manager: str) -> Dict[str, Any]:
    p = RUNS / SCEN / f"seed{seed}" / manager / "metrics.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load_first_input(seed: int, manager: str) -> Dict[str, Any]:
    p = RUNS / SCEN / f"seed{seed}" / manager / "manager_inputs.jsonl"
    if not p.exists():
        return {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            return json.loads(line)
    return {}


def main() -> int:
    seeds = sorted({int(p.parent.parent.name.replace("seed", ""))
                    for p in RUNS.glob(f"{SCEN}/seed*/B2/metrics.json")})
    rows: List[Dict[str, Any]] = []
    for sd in seeds:
        b2 = load_metrics(sd, "B2")
        b4 = load_metrics(sd, "B4b")
        gs = load_first_input(sd, "B2")
        cand = gs.get("candidates", {})
        air_feasible = [c for c in cand.get("air", []) if c.get("legal")]
        rows.append({
            "seed": sd,
            "ground_eta_s": gs.get("ground", {}).get("ground_fallback_eta_s"),
            "deadline_slack_s": (cand.get("summary", {}).get("deadline_slack_s")),
            "target_priority": cand.get("summary", {}).get("target_mission_priority"),
            "B2_action": (b2.get("issued_action_types") or [None])[0],
            "B4b_action": (b4.get("issued_action_types") or [None])[0],
            "B2_completion_s": b2.get("critical_mission_completion_time_s"),
            "B4b_completion_s": b4.get("critical_mission_completion_time_s"),
            "B2_deadline_violation": int(bool(b2.get("critical_mission_deadline_violation"))),
            "B4b_deadline_violation": int(bool(b4.get("critical_mission_deadline_violation"))),
            "B2_damage_count": b2.get("existing_missions_damaged_count"),
            "B4b_damage_count": b4.get("existing_missions_damaged_count"),
            "B2_final_mode": b2.get("critical_mission_final_mode"),
            "B4b_final_mode": b4.get("critical_mission_final_mode"),
        })

    import csv
    OUT.mkdir(parents=True, exist_ok=True)
    outp = OUT / "E1_H_H_high_case_study.csv"
    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        w.writeheader()
        w.writerows(rows)

    n_b2_air = sum(1 for r in rows if r["B2_action"] in ("DISPATCH", "REASSIGN"))
    n_b4_air = sum(1 for r in rows if r["B4b_action"] in ("DISPATCH", "REASSIGN"))
    n_b4_preempt = sum(1 for r in rows if r["B4b_action"] == "REASSIGN")
    n_divergence = sum(1 for r in rows if r["B2_action"] != r["B4b_action"])
    b4_faster = sum(1 for r in rows if (r["B4b_completion_s"] is not None
                    and r["B2_completion_s"] is not None
                    and r["B4b_completion_s"] < r["B2_completion_s"]))
    b4_damage = sum(1 for r in rows if (r["B4b_damage_count"] or 0) > (r["B2_damage_count"] or 0))
    print(f"E1_H_H_high case study (n = {len(rows)} seeds)")
    print(f"  B2 air-interventions : {n_b2_air}/{len(rows)}")
    print(f"  B4b air-interventions: {n_b4_air}/{len(rows)} (REASSIGN/preempt: {n_b4_preempt})")
    print(f"  action divergence B2 vs B4b: {n_divergence}/{len(rows)}")
    print(f"  B4b faster than B2: {b4_faster}/{len(rows)}")
    print(f"  B4b more damage than B2: {b4_damage}/{len(rows)}")
    print(f"\n[saved] {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
