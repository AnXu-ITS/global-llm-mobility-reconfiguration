"""Experiment 2 — primary statistical analysis (protocol §31-§34, §37-§39).

Paired design: independent unit = scenario x seed (n=20 per scenario);
managers paired on identical (scenario, seed). Continuous metrics: paired
t-test + paired Wilcoxon; binary: McNemar; multiple comparisons: Holm; report
effect size (Cohen's d) and 95% CI.

Stratifications: by failure family (F1..F6), by impact context (C1/C2/C3),
by manager, B2-vs-B4b paired differences, candidate-set reduction magnitude.

Artifacts:
  outputs/experiment2/primary_analysis.json
  outputs/experiment2/aggregate_metrics.csv
  outputs/experiment2/paired_b2_b4b.csv
  outputs/experiment2/family_context_cells.csv
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

import warnings
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MANAGERS = ("B0", "B1", "B2", "B4b")
KIND = {"B0": "no_cross_layer", "B1": "rule_based",
        "B2": "optimization", "B4b": "llm_b4b"}
CONT_METRICS = [
    "critical_mission_completion_time_s",
    "recovery_time_s",
    "failure_to_replan_latency_s",
    "existing_missions_damaged_count",
    "candidate_set_reduction_delta",
]
BIN_METRICS = [
    "critical_mission_deadline_violation",
    "recovery_success",
    "recovered_completed",
    "ground_fallback_rate",
    "failure_induced_ground_fallback",
    "necessary_ground_fallback_correct",
    "air_intervention",
]


def load_runs():
    with open(ROOT / "config" / "experiment2_matrix.yaml", encoding="utf-8") as f:
        e2 = yaml.safe_load(f)["experiment2"]
    with open(ROOT / "config" / "experiment2_seeds.yaml", encoding="utf-8") as f:
        seeds = list(yaml.safe_load(f)["primary_seeds"])
    rows = []
    for s in e2["scenarios"]:
        for seed in seeds:
            for mgr in MANAGERS:
                rd = ROOT / "runs" / "experiment2" / s["id"] / f"seed{seed}" / mgr
                mp = rd / "metrics.json"
                if not mp.exists():
                    continue
                m = json.loads(mp.read_text(encoding="utf-8"))
                m["scenario_id"] = s["id"]
                m["failure_family"] = s["failure_family"]
                m["impact_context"] = s["impact_context"]
                m["workload"] = s["workload"]
                rows.append(m)
    return rows


def mean_ci(vals):
    a = np.array([v for v in vals if v is not None], dtype=float)
    if len(a) == 0:
        return None, None, None, None
    m = float(np.mean(a))
    sd = float(np.std(a, ddof=1)) if len(a) > 1 else 0.0
    se = sd / math.sqrt(len(a))
    tcrit = stats.t.ppf(0.975, len(a) - 1) if len(a) > 1 else math.nan
    return m, sd, m - tcrit * se, m + tcrit * se


def _valid(v) -> bool:
    if v is None:
        return False
    try:
        return not math.isnan(float(v))
    except (TypeError, ValueError):
        return True


def paired_stats(b2_vals, b4b_vals):
    """Paired B2 vs B4b: returns dict with t-test, Wilcoxon, Cohen's d, CI."""
    pairs = [(a, b) for a, b in zip(b2_vals, b4b_vals)
             if _valid(a) and _valid(b)]
    if len(pairs) < 2:
        return None
    a = np.array([p[0] for p in pairs], dtype=float)
    b = np.array([p[1] for p in pairs], dtype=float)
    d = b - a
    t = stats.ttest_rel(b, a)
    try:
        w = stats.wilcoxon(b, a)
        w_p = float(w.pvalue)
        if np.isnan(w_p):
            w_p = 1.0
    except Exception:
        w_p = float(t.pvalue)
    pooled = np.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2) if len(a) > 1 else 1.0
    cohend = float(np.mean(d) / pooled) if pooled > 1e-12 else math.nan
    m, sd, lo, hi = mean_ci(list(d))
    return {"n": len(pairs), "diff_mean": m, "diff_sd": sd,
            "diff_ci95": [lo, hi], "t": float(t.statistic), "p": float(t.pvalue),
            "wilcoxon_p": w_p, "cohens_d": cohend}


def mcnemar(b2_vals, b4b_vals):
    pairs = [(bool(a), bool(b)) for a, b in zip(b2_vals, b4b_vals)
             if _valid(a) and _valid(b)]
    if not pairs:
        return None
    b = sum(1 for x, y in pairs if not x and y)
    c = sum(1 for x, y in pairs if x and not y)
    if b + c == 0:
        return {"n": len(pairs), "b": b, "c": c, "p": 1.0}
    # FIX (review 20260908 §5.4): binomtest is already two-sided; the extra ×2
    # doubled the exact McNemar p-value.
    p = stats.binomtest(min(b, c), b + c, 0.5).pvalue
    return {"n": len(pairs), "b": b, "c": c, "p": min(1.0, float(p))}


def holm(ps):
    # FIX (review 20260908 §5.4): Holm step-down requires the cumulative max of
    # p_(i) * (m - k); the previous version omitted it and mishandled NaN.
    n = len(ps)
    vals = [1.0 if p is None or (isinstance(p, float) and math.isnan(p)) else float(p)
            for p in ps]
    idx = sorted(range(n), key=lambda i: vals[i])
    adj = [1.0] * n
    running = float("-inf")
    for k, i in enumerate(idx):
        running = max(running, min(1.0, vals[i] * (n - k)))
        adj[i] = running
    return adj


def main() -> int:
    rows = load_runs()
    print(f"loaded {len(rows)} runs")
    df = pd.DataFrame(rows)
    out = {}

    # ---- aggregate per-manager metrics ----
    agg = {}
    for mgr in MANAGERS:
        sub = df[df["manager_kind"] == KIND[mgr]]
        cell = {"n": len(sub)}
        for met in CONT_METRICS:
            m, sd, lo, hi = mean_ci(sub[met].tolist())
            cell[met] = {"mean": m, "sd": sd, "ci95": [lo, hi]}
        for met in BIN_METRICS:
            vals = [v for v in sub[met].tolist() if v is not None]
            cell[met + "_rate"] = float(np.mean(vals)) if vals else None
        agg[mgr] = cell
    out["aggregate"] = agg

    # ---- per-scenario paired B2 vs B4b ----
    scen = sorted(df["scenario_id"].unique())
    paired_rows = []
    ps_cont = []
    for sid in scen:
        sub = df[df["scenario_id"] == sid]
        b2 = sub[sub["manager_kind"] == "optimization"].sort_values("seed")
        b4b = sub[sub["manager_kind"] == "llm_b4b"].sort_values("seed")
        row = {"scenario_id": sid,
               "failure_family": sub["failure_family"].iloc[0],
               "impact_context": sub["impact_context"].iloc[0]}
        for met in CONT_METRICS:
            st = paired_stats(b2[met].tolist(), b4b[met].tolist())
            if st:
                row[f"{met}_diff"] = st["diff_mean"]
                row[f"{met}_p"] = st["p"]
                row[f"{met}_d"] = st["cohens_d"]
                ps_cont.append((sid, met, st["p"]))
        for met in BIN_METRICS:
            mc = mcnemar(b2[met].tolist(), b4b[met].tolist())
            if mc:
                row[f"{met}_mcnemar_p"] = mc["p"]
                row[f"{met}_b"] = mc["b"]
                row[f"{met}_c"] = mc["c"]
                ps_cont.append((sid, f"{met}_mcnemar", mc["p"]))
        paired_rows.append(row)
    # Holm correction over all per-scenario comparisons
    ps_sorted = sorted(ps_cont, key=lambda x: x[2])
    holm_adj = {f"{sid}|{met}": v for (sid, met, _), v in
                zip(ps_sorted, holm([p for _, _, p in ps_sorted]))}
    for row in paired_rows:
        for key in list(row.keys()):
            if key.endswith("_p"):
                met = key[:-2]
                row[key + "_holm"] = holm_adj.get(f"{row['scenario_id']}|{met}")
    out["paired_b2_b4b_per_scenario"] = paired_rows

    # ---- aggregate paired B2 vs B4b (all runs pooled) ----
    b2 = df[df["manager_kind"] == "optimization"].sort_values(["scenario_id", "seed"])
    b4b = df[df["manager_kind"] == "llm_b4b"].sort_values(["scenario_id", "seed"])
    agg_paired = {}
    for met in CONT_METRICS:
        agg_paired[met] = paired_stats(b2[met].tolist(), b4b[met].tolist())
    for met in BIN_METRICS:
        agg_paired[met] = mcnemar(b2[met].tolist(), b4b[met].tolist())
    out["paired_b2_b4b_aggregate"] = agg_paired

    # ---- stratified: family x context x manager ----
    cells = []
    for fam in ("F1", "F2", "F3", "F4", "F5", "F6"):
        for ctx in ("C1", "C2", "C3"):
            for mgr in MANAGERS:
                sub = df[(df["failure_family"] == fam)
                         & (df["impact_context"] == ctx)
                         & (df["manager_kind"] == KIND[mgr])]
                if len(sub) == 0:
                    continue
                cell = {"failure_family": fam, "impact_context": ctx, "manager": mgr,
                        "n": len(sub)}
                for met in CONT_METRICS:
                    m, sd, lo, hi = mean_ci(sub[met].tolist())
                    cell[met] = {"mean": m, "ci95": [lo, hi]}
                for met in BIN_METRICS:
                    vals = [v for v in sub[met].tolist() if v is not None]
                    cell[met + "_rate"] = float(np.mean(vals)) if vals else None
                cells.append(cell)
    out["family_context_cells"] = cells

    # B2-vs-B4b gap vs candidate reduction (stratified by reduction magnitude)
    gap_rows = []
    for sid in scen:
        sub = df[df["scenario_id"] == sid]
        b2s = sub[sub["manager_kind"] == "optimization"].sort_values("seed")
        b4bs = sub[sub["manager_kind"] == "llm_b4b"].sort_values("seed")
        red = b2s["candidate_set_reduction_delta"].iloc[0] if len(b2s) else None
        st = paired_stats(b2s["critical_mission_completion_time_s"].tolist(),
                          b4bs["critical_mission_completion_time_s"].tolist())
        gap_rows.append({"scenario_id": sid,
                         "candidate_set_reduction_delta": red,
                         "b2_comp": mean_ci(b2s["critical_mission_completion_time_s"].tolist())[0],
                         "b4b_comp": mean_ci(b4bs["critical_mission_completion_time_s"].tolist())[0],
                         "diff": st["diff_mean"] if st else None,
                         "p": st["p"] if st else None,
                         "d": st["cohens_d"] if st else None})
    out["gap_vs_reduction"] = gap_rows

    # decision behaviour (post-failure issued types)
    behav = defaultdict(lambda: defaultdict(int))
    for r in rows:
        for t in r.get("post_failure_issued_types", []):
            behav[r["manager_kind"]][t] += 1
    out["decision_behavior"] = {k: dict(v) for k, v in behav.items()}

    # failure awareness: post-failure rejected proposals by manager
    aware = defaultdict(lambda: {"proposals": 0, "rejected": 0,
                                 "rejected_failure_related": 0,
                                 "failed_resource_reselection": 0})
    for r in rows:
        k = r["manager_kind"]
        aware[k]["proposals"] += r.get("post_failure_proposals", 0)
        aware[k]["rejected"] += r.get("post_failure_rejected", 0)
        aware[k]["rejected_failure_related"] += r.get("post_failure_rejected_failure_related", 0)
        aware[k]["failed_resource_reselection"] += r.get("failed_resource_reselection", 0)
    out["failure_awareness"] = {k: dict(v) for k, v in aware.items()}

    out_dir = ROOT / "outputs" / "experiment2"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "primary_analysis.json").write_text(
        json.dumps(out, indent=2, default=float), encoding="utf-8")

    df.to_csv(out_dir / "run_metrics.csv", index=False)
    pd.DataFrame(paired_rows).to_csv(out_dir / "paired_b2_b4b.csv", index=False)
    pd.DataFrame(cells).to_json(out_dir / "family_context_cells.json", orient="records", indent=2)

    print("\n== aggregate per-manager ==")
    for mgr in MANAGERS:
        c = agg[mgr]
        print(f"{mgr}: n={c['n']} comp={c['critical_mission_completion_time_s']['mean']:.1f} "
              f"[{c['critical_mission_completion_time_s']['ci95'][0]:.1f}, "
              f"{c['critical_mission_completion_time_s']['ci95'][1]:.1f}] "
              f"viol={c['critical_mission_deadline_violation_rate']:.3f} "
              f"dmg={c['existing_missions_damaged_count']['mean']:.3f} "
              f"recov={c['recovery_success_rate']:.3f}")
    print("\n== B2 vs B4b aggregate paired ==")
    for met in CONT_METRICS:
        st = agg_paired[met]
        if st:
            print(f"{met}: diff={st['diff_mean']:.2f} p={st['p']:.4f} W={st['wilcoxon_p']:.4f} d={st['cohens_d']:.3f}")
    for met in BIN_METRICS:
        mc = agg_paired[met]
        if mc:
            print(f"{met}: McNemar p={mc['p']:.4f} (b={mc['b']}, c={mc['c']})")
    print("\nartifacts: outputs/experiment2/primary_analysis.json, paired_b2_b4b.csv, run_metrics.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
