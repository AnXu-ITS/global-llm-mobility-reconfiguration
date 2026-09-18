"""Analyze Experiment 1 Finalization — independent-seed primary dataset.

Reads runs/experiment1_final/<scenario>/seed<seed>/<manager>/metrics.json and
produces:
  - per-manager mean/median/SD/95% CI (Finalization §28)
  - per-scenario paired contrasts B0/B1/B2/B4b (t + Wilcoxon + Holm + effect size)
  - B2 vs B4b multi-objective trade-off CSV (Finalization §24)
  - outputs/experiment1_final/primary_analysis.json

Statistical unit: scenario x seed (n = 20 per scenario), paired across managers
on identical (scenario, seed) state.  Same-prompt repeats are NOT samples.
"""
from __future__ import annotations

import argparse
import json
import math
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "experiment1_final"
OUT = ROOT / "outputs" / "experiment1_final"

PRIMARY = ("B0", "B1", "B2", "B4b")
KIND_TO_LABEL = {"no_cross_layer": "B0", "rule_based": "B1",
                 "optimization": "B2", "llm_b4b": "B4b", "llm_b4a": "B4a"}
LABEL_TO_KIND = {v: k for k, v in KIND_TO_LABEL.items()}
RELEASE_T = 300.0
THETA_TIME = 60.0  # frozen "material critical benefit" threshold (seconds)

CONTRASTS = [("B0", "B1"), ("B0", "B2"), ("B0", "B4b"),
             ("B1", "B2"), ("B1", "B4b"), ("B2", "B4b")]


def _load_metrics(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _ground_eta(run_dir: Path) -> Optional[float]:
    p = run_dir / "manager_inputs.jsonl"
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        return d.get("ground", {}).get("ground_fallback_eta_s")
    return None


def load_runs(runs_root: Path = RUNS) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for mp in sorted(runs_root.glob("*/*/B*/metrics.json")):
        m = _load_metrics(mp)
        if not m:
            continue
        kind = m.get("manager_kind")
        label = KIND_TO_LABEL.get(kind, kind)
        if label not in PRIMARY + ("B4a",):
            continue
        seed = m.get("seed")
        scen = m.get("scenario_id")
        run_dir = mp.parent
        m["_label"] = label
        m["_scenario"] = scen
        m["_seed"] = seed
        m["_ground_eta"] = _ground_eta(run_dir)
        rows.append(m)
    return rows


def slack_of(m: Dict[str, Any]) -> Optional[float]:
    d = m.get("critical_mission_deadline_s")
    return float(d) - RELEASE_T if d is not None else None


def unnecessary_air(m: Dict[str, Any]) -> bool:
    """Frozen 3-condition predicate (EXPERIMENT1_FINAL_METRIC_DEFINITIONS.md §M5)."""
    if not m.get("air_intervention"):
        return False
    eta = m.get("_ground_eta")
    slack = slack_of(m)
    comp = m.get("critical_mission_completion_time_s")
    if eta is None or slack is None or comp is None:
        return False
    cond1 = eta <= slack
    cond2 = (eta - comp) < THETA_TIME
    cond3 = (m.get("reassignment_count", 0) > 0) or (m.get("existing_missions_damaged_count", 0) > 0)
    return bool(cond1 and cond2 and cond3)


def enrich(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # B0 completion per (scenario, seed) for paired time-saving
    b0 = {}
    for r in rows:
        if r["_label"] == "B0":
            b0[(r["_scenario"], r["_seed"])] = r.get("critical_mission_completion_time_s")
    for r in rows:
        comp = r.get("critical_mission_completion_time_s")
        b0c = b0.get((r["_scenario"], r["_seed"]))
        r["_slack"] = slack_of(r)
        r["_unnecessary"] = unnecessary_air(r)
        r["_damage_bin"] = bool(r.get("existing_missions_damaged_count", 0))
        r["_ground"] = (r.get("critical_mission_final_mode") == "GROUND")
        r["_saved_vs_b0"] = (b0c - comp) if (b0c is not None and comp is not None) else None
        r["_de"] = (r["_saved_vs_b0"] / (r.get("existing_missions_damaged_count", 0) + 1)
                    if r["_saved_vs_b0"] is not None else None)
    return rows


def mean_ci(vals: List[float]) -> Dict[str, Any]:
    a = np.asarray([v for v in vals if v is not None], dtype=float)
    if a.size == 0:
        return {"n": 0, "mean": None, "median": None, "sd": None, "ci95": [None, None]}
    mean = float(a.mean())
    sd = float(a.std(ddof=1)) if a.size > 1 else 0.0
    se = sd / math.sqrt(a.size) if a.size > 1 else float("nan")
    if a.size > 1:
        h = se * stats.t.ppf(0.975, a.size - 1)
        lo, hi = mean - h, mean + h
    else:
        lo, hi = mean, mean
    return {"n": int(a.size), "mean": round(mean, 3), "median": round(float(np.median(a)), 3),
            "sd": round(sd, 3), "ci95": [round(lo, 3), round(hi, 3)]}


def mean_ci_bool(vals: List[bool]) -> Dict[str, Any]:
    a = [1.0 if v else 0.0 for v in vals]
    r = mean_ci(a)
    if r["mean"] is not None:
        r["rate"] = round(r["mean"], 4)
    return r


def mcnemar_p(a: List[bool], b: List[bool]) -> float:
    b_disc = 0  # a=1,b=0
    c_disc = 0  # a=0,b=1
    for x, y in zip(a, b):
        if x and not y:
            b_disc += 1
        elif y and not x:
            c_disc += 1
    n = b_disc + c_disc
    if n == 0:
        return 1.0
    # exact binomial two-sided
    from scipy.stats import binom
    p = 0.5
    tail = binom.cdf(min(b_disc, c_disc), n, p)
    return float(min(1.0, 2 * tail))


def cohens_d_paired(a: List[float], b: List[float]) -> Optional[float]:
    d = [x - y for x, y in zip(a, b) if x is not None and y is not None]
    if len(d) < 2:
        return None
    sd = float(np.std(d, ddof=1))
    if sd == 0:
        return 0.0 if np.mean(d) == 0 else None  # undefined when no variance
    return float(np.mean(d) / sd)


def per_scenario_paired(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by = {}
    for r in rows:
        by.setdefault((r["_scenario"], r["_label"]), []).append(r)
    out: Dict[str, Any] = {}
    for scen in sorted({r["_scenario"] for r in rows}):
        for ma, mb in CONTRASTS:
            ra = by.get((scen, ma), [])
            rb = by.get((scen, mb), [])
            # pair on seed
            ra = {r["_seed"]: r for r in ra}
            rb = {r["_seed"]: r for r in rb}
            seeds = sorted(set(ra) & set(rb))
            if len(seeds) == 0:
                continue
            ca = [ra[s].get("critical_mission_completion_time_s") for s in seeds]
            cb = [rb[s].get("critical_mission_completion_time_s") for s in seeds]
            va = [ra[s].get("critical_mission_deadline_violation") for s in seeds]
            vb = [rb[s].get("critical_mission_deadline_violation") for s in seeds]
            da = [ra[s]["_damage_bin"] for s in seeds]
            db = [rb[s]["_damage_bin"] for s in seeds]
            ua = [ra[s]["_unnecessary"] for s in seeds]
            ub = [rb[s]["_unnecessary"] for s in seeds]
            key = f"{scen}|{ma}|{mb}"
            t_p = stats.ttest_rel(cb, ca).pvalue if all(v is not None for v in ca + cb) else None
            w_p = None
            with np.errstate(all="ignore"):
                try:
                    diffs = [x - y for x, y in zip(cb, ca) if x is not None and y is not None]
                    if diffs and any(d != 0 for d in diffs):
                        w_p = stats.wilcoxon(cb, ca).pvalue
                    elif diffs:
                        w_p = 1.0  # all-zero differences: no evidence of difference
                except Exception:
                    w_p = None
            d_val = cohens_d_paired(ca, cb)
            out[key] = {
                "scenario": scen, "a": ma, "b": mb, "n": len(seeds),
                "completion_t_p": round(float(t_p), 6) if t_p is not None else None,
                "completion_wilcoxon_p": round(float(w_p), 6) if w_p is not None else None,
                "completion_d": (round(d_val, 3) if d_val is not None else None),
                "violation_mcnemar_p": round(mcnemar_p(va, vb), 6),
                "damage_mcnemar_p": round(mcnemar_p(da, db), 6),
                "unnecessary_mcnemar_p": round(mcnemar_p(ua, ub), 6),
            }
    # Holm correction over the completion-time comparison family
    tps = [(k, v["completion_t_p"]) for k, v in out.items()
           if v["completion_t_p"] is not None]
    tps.sort(key=lambda x: x[1])
    m = len(tps)
    adj = {}
    for i, (k, p) in enumerate(tps):
        adj[k] = min(1.0, p * (m - i))
    for k in out:
        out[k]["completion_holm_p"] = (round(adj[k], 6) if k in adj else None)
    return out


def tradeoff(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    b2 = {(r["_scenario"], r["_seed"]): r for r in rows if r["_label"] == "B2"}
    b4 = {(r["_scenario"], r["_seed"]): r for r in rows if r["_label"] == "B4b"}
    out = []
    for key in sorted(set(b2) & set(b4)):
        x, y = b2[key], b4[key]
        out.append({
            "scenario_id": key[0], "seed": key[1],
            "B2_completion_s": x.get("critical_mission_completion_time_s"),
            "B4b_completion_s": y.get("critical_mission_completion_time_s"),
            "B2_deadline_violation": int(bool(x.get("critical_mission_deadline_violation"))),
            "B4b_deadline_violation": int(bool(y.get("critical_mission_deadline_violation"))),
            "B2_damage_count": x.get("existing_missions_damaged_count"),
            "B4b_damage_count": y.get("existing_missions_damaged_count"),
            "B2_unnecessary_air": int(bool(x["_unnecessary"])),
            "B4b_unnecessary_air": int(bool(y["_unnecessary"])),
            "completion_benefit_s": (x.get("critical_mission_completion_time_s")
                                     - y.get("critical_mission_completion_time_s")
                                     if x.get("critical_mission_completion_time_s") is not None
                                     and y.get("critical_mission_completion_time_s") is not None else None),
            "extra_damage": (y.get("existing_missions_damaged_count", 0)
                             - x.get("existing_missions_damaged_count", 0)),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(RUNS))
    ap.add_argument("--out", default=None,
                    help="output dir override (default: runs' sibling under outputs)")
    args = ap.parse_args()
    runs_root = Path(args.runs)
    rows = enrich(load_runs(runs_root))
    out_root = Path(args.out) if args.out else (ROOT / "outputs" /
                                                (runs_root.name if runs_root.name != "experiment1_final"
                                                 else "experiment1_final"))

    # per-manager summary (pooled over all scenario x seed, n = 240)
    by = {}
    for r in rows:
        by.setdefault(r["_label"], []).append(r)
    summary: Dict[str, Any] = {}
    for label in PRIMARY:
        rs = by.get(label, [])
        summary[label] = {
            "n_runs": len(rs),
            "completion_time_s": mean_ci([r.get("critical_mission_completion_time_s") for r in rs]),
            "deadline_violation_rate": mean_ci_bool([bool(r.get("critical_mission_deadline_violation")) for r in rs]),
            "existing_service_damage": mean_ci([r.get("existing_missions_damaged_count", 0) for r in rs]),
            "air_intervention_rate": mean_ci_bool([bool(r.get("air_intervention")) for r in rs]),
            "unnecessary_air_rate": mean_ci_bool([r["_unnecessary"] for r in rs]),
            "ground_fallback_rate": mean_ci_bool([r["_ground"] for r in rs]),
            "reassignment_count": mean_ci([r.get("reassignment_count", 0) for r in rs]),
            "time_saving_vs_b0_s": mean_ci([r["_saved_vs_b0"] for r in rs]),
            "disruption_efficiency": mean_ci([r["_de"] for r in rs]),
        }

    paired = per_scenario_paired(rows)
    trade = tradeoff(rows)

    out_root.mkdir(parents=True, exist_ok=True)
    result = {"summary": summary, "paired_per_scenario": paired,
              "tradeoff": trade, "contrasts": list(CONTRASTS)}
    (out_root / "primary_analysis.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    with open(out_root / "B2_vs_B4b_tradeoff.csv", "w", newline="", encoding="utf-8") as f:
        import csv
        if trade:
            w = csv.DictWriter(f, fieldnames=list(trade[0].keys()))
            w.writeheader()
            w.writerows(trade)

    # console table (Finalization §28)
    print("Manager | comp_mean (95% CI) | viol_rate | damage | air_rate | unnec_air | ground_rate | saved_vs_B0")
    for label in PRIMARY:
        s = summary[label]
        c = s["completion_time_s"]
        print(f"{label} | {c['mean']} [{c['ci95'][0]}, {c['ci95'][1]}] "
              f"| {s['deadline_violation_rate']['rate']} "
              f"| {s['existing_service_damage']['mean']} "
              f"| {s['air_intervention_rate']['rate']} "
              f"| {s['unnecessary_air_rate']['rate']} "
              f"| {s['ground_fallback_rate']['rate']} "
              f"| {s['time_saving_vs_b0_s']['mean']}")

    print(f"\n[saved] {out_root / 'primary_analysis.json'}")
    print(f"[saved] {out_root / 'B2_vs_B4b_tradeoff.csv'}")
    print(f"runs loaded: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
