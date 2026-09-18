"""Experiment 2 cross-site primary analysis (Site B / Site C).

Site-scoped paired statistics mirroring the frozen canonical analyzer:
aggregate per (site, manager); paired B2 vs B4b per site (t/Wilcoxon/McNemar/
Holm/effect size); family x context cells per site. The frozen canonical
Site-A dataset is NOT touched.

Artifacts: outputs/experiment2/cross_site_primary_analysis.json
           outputs/experiment2/cross_site_run_metrics.csv
"""
from __future__ import annotations

import json
import math
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SITES = ("site_b_amsterdam", "site_c_edmonton")
MANAGERS = ("B0", "B1", "B2", "B4b")
KIND = {"B0": "no_cross_layer", "B1": "rule_based",
        "B2": "optimization", "B4b": "llm_b4b"}
MATRIX_OF = {
    "site_b_amsterdam": ROOT / "config" / "experiment2_site_b_matrix.yaml",
    "site_c_edmonton": ROOT / "config" / "experiment2_site_c_matrix.yaml",
}
CONT_METRICS = ["critical_mission_completion_time_s", "recovery_time_s",
                "failure_to_replan_latency_s", "existing_missions_damaged_count",
                "candidate_set_reduction_delta"]
BIN_METRICS = ["critical_mission_deadline_violation", "recovery_success",
               "recovered_completed", "ground_fallback_rate",
               "failure_induced_ground_fallback",
               "necessary_ground_fallback_correct", "air_intervention"]


def load_runs():
    rows = []
    for site_id in SITES:
        e2 = yaml.safe_load(MATRIX_OF[site_id].read_text(encoding="utf-8"))["experiment2"]
        scen_by_id = {s["id"]: s for s in e2["scenarios"]}
        for sid, scen in scen_by_id.items():
            sdir = ROOT / "runs" / "experiment2_cross_site" / site_id / sid
            if not sdir.exists():
                continue
            for sd in sdir.iterdir():
                if not sd.name.startswith("seed"):
                    continue
                seed = int(sd.name[4:])
                for mgr in MANAGERS:
                    mp = sd / mgr / "metrics.json"
                    if not mp.exists():
                        continue
                    m = json.loads(mp.read_text(encoding="utf-8"))
                    m["site_id"] = site_id
                    m["scenario_id"] = sid
                    m["failure_family"] = scen["failure_family"]
                    m["impact_context"] = scen["impact_context"]
                    m["seed"] = seed
                    rows.append(m)
    return rows


def _valid(v):
    if v is None:
        return False
    try:
        return not math.isnan(float(v))
    except (TypeError, ValueError):
        return True


def mean_ci(vals):
    a = np.array([v for v in vals if _valid(v)], dtype=float)
    if len(a) == 0:
        return None, None, None, None
    m = float(np.mean(a))
    sd = float(np.std(a, ddof=1)) if len(a) > 1 else 0.0
    se = sd / math.sqrt(len(a))
    tc = stats.t.ppf(0.975, len(a) - 1) if len(a) > 1 else math.nan
    return m, sd, m - tc * se, m + tc * se


def paired_stats(a_vals, b_vals):
    pairs = [(a, b) for a, b in zip(a_vals, b_vals) if _valid(a) and _valid(b)]
    if len(pairs) < 2:
        return None
    a = np.array([p[0] for p in pairs], dtype=float)
    b = np.array([p[1] for p in pairs], dtype=float)
    d = b - a
    t = stats.ttest_rel(b, a)
    try:
        w_p = float(stats.wilcoxon(b, a).pvalue)
        if np.isnan(w_p):
            w_p = 1.0
    except Exception:
        w_p = float(t.pvalue)
    pooled = np.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2) if len(a) > 1 else 1.0
    cohend = float(np.mean(d) / pooled) if pooled > 1e-12 else math.nan
    m, sd, lo, hi = mean_ci(list(d))
    return {"n": len(pairs), "diff_mean": m, "diff_ci95": [lo, hi],
            "p": float(t.pvalue), "wilcoxon_p": w_p, "cohens_d": cohend}


def mcnemar(a_vals, b_vals):
    pairs = [(bool(a), bool(b)) for a, b in zip(a_vals, b_vals)
             if _valid(a) and _valid(b)]
    if not pairs:
        return None
    b = sum(1 for x, y in pairs if not x and y)
    c = sum(1 for x, y in pairs if x and not y)
    if b + c == 0:
        p = 1.0
    else:
        p = min(1.0, stats.binomtest(min(b, c), b + c, 0.5).pvalue * 2)
    return {"n": len(pairs), "b": b, "c": c, "p": p}


def main() -> int:
    rows = load_runs()
    df = pd.DataFrame(rows)
    print(f"loaded {len(df)} cross-site runs")
    out = {}
    for site_id in SITES:
        sub = df[df["site_id"] == site_id]
        if len(sub) == 0:
            continue
        site_out = {}
        for mgr in MANAGERS:
            s2 = sub[sub["manager_kind"] == KIND[mgr]]
            cell = {"n": len(s2)}
            for met in CONT_METRICS:
                m, sd, lo, hi = mean_ci(s2[met].tolist())
                cell[met] = {"mean": m, "ci95": [lo, hi]}
            for met in BIN_METRICS:
                vals = [v for v in s2[met].tolist() if _valid(v)]
                cell[met + "_rate"] = float(np.mean(vals)) if vals else None
            site_out[mgr] = cell
        # paired B2 vs B4b
        b2 = sub[sub["manager_kind"] == "optimization"].sort_values(
            ["scenario_id", "seed"])
        b4b = sub[sub["manager_kind"] == "llm_b4b"].sort_values(
            ["scenario_id", "seed"])
        paired = {}
        for met in CONT_METRICS:
            paired[met] = paired_stats(b2[met].tolist(), b4b[met].tolist())
        for met in BIN_METRICS:
            paired[met] = mcnemar(b2[met].tolist(), b4b[met].tolist())
        site_out["paired_b2_b4b"] = paired
        # family x context cells
        cells = []
        for fam in ("F1", "F2", "F3", "F4", "F5", "F6"):
            for ctx in ("C1", "C2", "C3"):
                for mgr in MANAGERS:
                    s3 = sub[(sub["failure_family"] == fam)
                             & (sub["impact_context"] == ctx)
                             & (sub["manager_kind"] == KIND[mgr])]
                    if len(s3) == 0:
                        continue
                    c = {"failure_family": fam, "impact_context": ctx,
                         "manager": mgr, "n": len(s3)}
                    for met in CONT_METRICS:
                        m, sd, lo, hi = mean_ci(s3[met].tolist())
                        c[met] = {"mean": m, "ci95": [lo, hi]}
                    for met in BIN_METRICS:
                        vals = [v for v in s3[met].tolist() if _valid(v)]
                        c[met + "_rate"] = float(np.mean(vals)) if vals else None
                    cells.append(c)
        site_out["family_context_cells"] = cells
        out[site_id] = site_out

    out_dir = ROOT / "outputs" / "experiment2"
    (out_dir / "cross_site_primary_analysis.json").write_text(
        json.dumps(out, indent=2, default=float), encoding="utf-8")
    df.to_csv(out_dir / "cross_site_run_metrics.csv", index=False)
    for site_id in SITES:
        if site_id not in out:
            continue
        p = out[site_id]["paired_b2_b4b"]
        print(f"\n== {site_id}: aggregate ==")
        for mgr in MANAGERS:
            c = out[site_id][mgr]
            comp = c["critical_mission_completion_time_s"]
            print(f"  {mgr}: n={c['n']} comp={comp['mean']} viol="
                  f"{c['critical_mission_deadline_violation_rate']}")
        print(f"  B2 vs B4b paired:")
        for met in CONT_METRICS:
            st = p[met]
            if st:
                print(f"    {met}: diff={st['diff_mean']:.2f} p={st['p']:.4f} "
                      f"d={st['cohens_d']:.3f}")
    print("\nartifacts: outputs/experiment2/cross_site_primary_analysis.json, "
          "cross_site_run_metrics.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
