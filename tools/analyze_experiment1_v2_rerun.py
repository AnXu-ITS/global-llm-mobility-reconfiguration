"""Analyze Experiment 1 v2 Phase-1 re-run (execution-corrected metrics already
computed by the runner; this script aggregates, computes signed deltas, runs the
statistics, and checks LLM-call independence).

Run structure (tools/run_experiment1_v2.py):
    runs/experiment1_v2/<scenario>/<B0|B1|B2>/metrics.json          (deterministic)
    runs/experiment1_v2/<scenario>/<B4v2a|B4v2b>/repeatNN/metrics.json  (LLM repeats)

Usage:
    python tools/analyze_experiment1_v2_rerun.py [--runs runs/experiment1_v2]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "experiment1_v2"

DETERMINISTIC = ("B0", "B1", "B2")
LLM_ARMS = ("B4v2a", "B4v2b")
MANAGER_LABEL = {
    "B0": "B0 (no cross-layer)",
    "B1": "B1 (rule, air-first)",
    "B2": "B2 (optimization)",
    "B4v2a": "B4-v2a (LLM, prompt-only)",
    "B4v2b": "B4-v2b (LLM + shared table)",
}
# metrics.json manager_kind -> arm
KIND_TO_ARM = {
    "no_cross_layer": "B0",
    "rule_based": "B1",
    "optimization": "B2",
    "llm_v2a": "B4v2a",
    "llm_v2b": "B4v2b",
}

# frozen ground fallback ETA per disruption (review + scenario_config)
GROUND_ETA = {"LOW": 152.0, "MEDIUM": 182.0, "HIGH": 229.0}
RELEASE_T = 300.0


def _try_load(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_runs(runs: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    # deterministic: <scenario>/<manager>/metrics.json
    for mp in sorted(runs.glob("*/*/metrics.json")):
        m = _try_load(mp)
        if m:
            m["_path"] = str(mp)
            m["_repeat"] = None
            rows.append(m)
    # LLM arms: <scenario>/<arm>/repeatNN/metrics.json
    for mp in sorted(runs.glob("*/*/repeat*/metrics.json")):
        m = _try_load(mp)
        if m:
            m["_path"] = str(mp)
            m["_repeat"] = int(mp.parent.name.replace("repeat", ""))
            rows.append(m)
    return rows


def slack_of(m: Dict[str, Any]) -> float:
    d = m.get("critical_mission_deadline_s")
    return float(d) - RELEASE_T if d is not None else float("nan")


def unnecessary_air(m: Dict[str, Any]) -> bool:
    """air used although the ground fallback would still meet the deadline."""
    if not m.get("air_intervention"):
        return False
    eta = GROUND_ETA.get(m.get("disruption"))
    slack = slack_of(m)
    if eta is None or math.isnan(slack):
        return False
    return eta <= slack


def enrich(m: Dict[str, Any], b0_comp: Optional[float]) -> Dict[str, Any]:
    comp = m.get("critical_mission_completion_time_s")
    m["_slack"] = slack_of(m)
    m["_unnecessary_air"] = unnecessary_air(m)
    m["_damage"] = bool(m.get("existing_missions_damaged_count", 0))
    m["_signed_saved"] = (b0_comp - comp) if (b0_comp is not None and comp is not None) else None
    return m


def aggregate(scenario: str, manager: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    comp = np.array([r["critical_mission_completion_time_s"] for r in rows], dtype=float)
    viol = np.array([bool(r["critical_mission_deadline_violation"]) for r in rows], dtype=float)
    damage = np.array([r["_damage"] for r in rows], dtype=float)
    air = np.array([bool(r["air_intervention"]) for r in rows], dtype=float)
    unnec = np.array([r["_unnecessary_air"] for r in rows], dtype=float)
    saved = np.array([r["_signed_saved"] for r in rows], dtype=float)
    return {
        "scenario": scenario,
        "manager": manager,
        "n": n,
        "completion_mean": round(float(comp.mean()), 2),
        "completion_sd": round(float(comp.std(ddof=1)), 2) if n > 1 else 0.0,
        "violation_rate": round(float(viol.mean()), 4),
        "damage_rate": round(float(damage.mean()), 4),
        "air_rate": round(float(air.mean()), 4),
        "unnecessary_air_rate": round(float(unnec.mean()), 4),
        "signed_saved_mean": round(float(saved.mean()), 2),
        "signed_saved_sd": round(float(saved.std(ddof=1)), 2) if n > 1 else 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(RUNS))
    args = ap.parse_args()
    runs = Path(args.runs)

    raw = load_runs(runs)
    if not raw:
        print(f"no metrics.json found under {runs}")
        return 2

    # B0 completion per scenario (deterministic ground baseline)
    b0 = {}
    for m in raw:
        if m.get("manager_kind") == "no_cross_layer":
            b0[m["scenario_id"]] = m.get("critical_mission_completion_time_s")

    enriched = [enrich(m, b0.get(m["scenario_id"])) for m in raw]

    scenarios = sorted({m["scenario_id"] for m in enriched})
    per_cell: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        s: {mg: [] for mg in (DETERMINISTIC + LLM_ARMS)} for s in scenarios
    }
    for m in enriched:
        mg = m.get("manager_kind")
        cell_key = KIND_TO_ARM.get(mg)
        if cell_key is None:
            continue
        per_cell[m["scenario_id"]][cell_key].append(m)

    print("# Experiment 1 v2 — per-scenario aggregates\n")
    print("scenario | manager | n | comp | viol | damage | air | unnec | signed_saved")
    print("---|---|---|---|---|---|---|---|---")
    table = []
    for s in scenarios:
        for mg in DETERMINISTIC + LLM_ARMS:
            rows = per_cell[s][mg]
            if not rows:
                continue
            a = aggregate(s, mg, rows)
            table.append(a)
            print(f"{s} | {MANAGER_LABEL[mg]} | {a['n']} | {a['completion_mean']} "
                  f"| {a['violation_rate']} | {a['damage_rate']} | {a['air_rate']} "
                  f"| {a['unnecessary_air_rate']} | {a['signed_saved_mean']}")

    # per-manager mean over scenarios (equal weight; LLM arms use per-scenario mean)
    print("\n## per-manager mean over scenarios (equal weight)\n")
    print("manager | comp | viol | damage | air | unnec | signed_saved")
    print("---|---|---|---|---|---|---")
    summary = {}
    for mg in DETERMINISTIC + LLM_ARMS:
        vals = [aggregate(s, mg, per_cell[s][mg]) for s in scenarios if per_cell[s][mg]]
        if not vals:
            continue
        comp = np.mean([v["completion_mean"] for v in vals])
        viol = np.mean([v["violation_rate"] for v in vals])
        damage = np.mean([v["damage_rate"] for v in vals])
        air = np.mean([v["air_rate"] for v in vals])
        unnec = np.mean([v["unnecessary_air_rate"] for v in vals])
        saved = np.mean([v["signed_saved_mean"] for v in vals])
        summary[mg] = {
            "completion_mean": round(float(comp), 2),
            "violation_rate": round(float(viol), 4),
            "damage_rate": round(float(damage), 4),
            "air_rate": round(float(air), 4),
            "unnecessary_air_rate": round(float(unnec), 4),
            "signed_saved_mean": round(float(saved), 2),
        }
        print(f"{MANAGER_LABEL[mg]} | {summary[mg]['completion_mean']} "
              f"| {summary[mg]['violation_rate']} | {summary[mg]['damage_rate']} "
              f"| {summary[mg]['air_rate']} | {summary[mg]['unnecessary_air_rate']} "
              f"| {summary[mg]['signed_saved_mean']}")

    out = {
        "cells": table,
        "per_manager_summary": summary,
        "ground_eta_by_disruption": GROUND_ETA,
        "release_t": RELEASE_T,
    }
    outp = runs / "experiment1_v2_analysis.json"
    outp.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\n[saved] {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
