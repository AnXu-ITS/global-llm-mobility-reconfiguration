"""Experiment 3 — primary statistical analysis (Compound Disruption Stress Test).

Paired design: independent unit = scenario x seed (n=20 per scenario);
managers paired on identical (scenario, seed). Primary metric = system-weighted
loss (SWL); secondary = critical completion time, deadline violation, recovery,
decision oscillation, priority-consistent loss.

Continuous metrics: paired t-test + paired Wilcoxon; binary: McNemar; multiple
comparisons: Holm; effect size Cohen's d + 95% CI. Stratifications: by level
(L1..L4), by motif, by manager.

Hypotheses (protocol): H3a — B4b lowers SWL vs B1/B2 under compound (L3/L4);
H3b — B4b is priority-consistent (lower CRITICAL/HIGH loss at the cost of
NORMAL/LOW). Nulls are reported honestly (no assumed effect).

Artifacts:
  outputs/experiment3/primary_analysis.json
  outputs/experiment3/run_metrics.csv
  outputs/experiment3/level_manager_cells.csv
  outputs/experiment3/paired_vs_b0.csv
  outputs/experiment3/paired_b4b_vs.csv
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
    "system_weighted_loss",
    "critical_mission_completion_time_s",
    "decision_oscillation_count",
    "existing_missions_damaged_count",
]
BIN_METRICS = [
    "critical_mission_deadline_violation",
    "recovery_success",
]
PRIO = ["CRITICAL", "HIGH", "NORMAL", "LOW"]


def load_runs():
    e3 = yaml.safe_load((ROOT / "config" / "experiment3_matrix.yaml").read_text(encoding="utf-8"))["experiment3"]
    seeds = list(yaml.safe_load((ROOT / "config" / "experiment3_seeds.yaml").read_text(encoding="utf-8"))["primary_seeds"])
    rows = []
    for s in e3["scenarios"]:
        for seed in seeds:
            for mgr in MANAGERS:
                mp = ROOT / "runs" / "experiment3" / s["id"] / f"seed{seed}" / mgr / "metrics.json"
                if not mp.exists():
                    continue
                m = json.loads(mp.read_text(encoding="utf-8"))
                m["scenario_id"] = s["id"]
                m["level"] = s["level"]
                m["motif"] = s["motif"]
                m["workload"] = s["workload"]
                rows.append(m)
    return rows


def mean_ci(vals):
    a = np.array([v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))], dtype=float)
    if len(a) == 0:
        return None, None, None, None
    m = float(np.mean(a))
    sd = float(np.std(a, ddof=1)) if len(a) > 1 else 0.0
    se = sd / math.sqrt(len(a))
    tcrit = stats.t.ppf(0.975, len(a) - 1) if len(a) > 1 else math.nan
    return m, sd, (m - tcrit * se if not math.isnan(tcrit) else m), (m + tcrit * se if not math.isnan(tcrit) else m)


def _valid(v):
    if v is None:
        return False
    try:
        return not math.isnan(float(v))
    except (TypeError, ValueError):
        return True


def paired_stats(a_vals, b_vals):
    from paper_stats import paired as shared_paired
    return shared_paired(a_vals, b_vals)


def mcnemar(a_vals, b_vals):
    pairs = [(bool(a), bool(b)) for a, b in zip(a_vals, b_vals) if _valid(a) and _valid(b)]
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
    from paper_stats import holm as shared_holm
    return shared_holm(ps)


def prio_breakdown(m):
    bp = m.get("system_weighted_loss_by_priority", {}) or {}
    return {p: float(bp.get(p, 0.0)) for p in PRIO}


def main() -> int:
    rows = load_runs()
    print(f"loaded {len(rows)} runs")
    df = pd.DataFrame(rows)
    for p in PRIO:
        df[f"swl_{p.lower()}"] = df["system_weighted_loss_by_priority"].apply(
            lambda bp, p=p: float((bp or {}).get(p, 0.0)))
    out = {}
    available = sorted(df["manager_kind"].unique())

    # ---- per-manager aggregate ----
    agg = {}
    for mgr in MANAGERS:
        sub = df[df["manager_kind"] == KIND[mgr]]
        if len(sub) == 0:
            continue
        cell = {"n": len(sub)}
        for met in CONT_METRICS:
            m, sd, lo, hi = mean_ci(sub[met].tolist())
            cell[met] = {"mean": m, "sd": sd, "ci95": [lo, hi]}
        for met in BIN_METRICS:
            vals = [v for v in sub[met].tolist() if v is not None]
            cell[met + "_rate"] = float(np.mean(vals)) if vals else None
        for p in PRIO:
            m, sd, lo, hi = mean_ci(sub[f"swl_{p.lower()}"].tolist())
            cell[f"swl_{p.lower()}"] = {"mean": m, "ci95": [lo, hi]}
        agg[mgr] = cell
    out["aggregate"] = agg

    # ---- level x manager cells (SWL + key secondaries) ----
    cells = []
    for lvl in ("L1", "L2", "L3", "L4"):
        for mgr in MANAGERS:
            sub = df[(df["level"] == lvl) & (df["manager_kind"] == KIND[mgr])]
            if len(sub) == 0:
                continue
            cell = {"level": lvl, "manager": mgr, "n": len(sub)}
            for met in CONT_METRICS:
                m, sd, lo, hi = mean_ci(sub[met].tolist())
                cell[met] = {"mean": m, "ci95": [lo, hi]}
            for met in BIN_METRICS:
                vals = [v for v in sub[met].tolist() if v is not None]
                cell[met + "_rate"] = float(np.mean(vals)) if vals else None
            for p in PRIO:
                m, sd, lo, hi = mean_ci(sub[f"swl_{p.lower()}"].tolist())
                cell[f"swl_{p.lower()}_mean"] = m
            cells.append(cell)
    out["level_manager_cells"] = cells

    # ---- paired vs B0 (per level, primary metric SWL) ----
    ps_all = []
    paired_rows = []
    base = df[df["manager_kind"] == "no_cross_layer"].sort_values(["scenario_id", "seed"])
    for mgr in ("B1", "B2", "B4b"):
        k = KIND[mgr]
        other = df[df["manager_kind"] == k]
        if len(other) == 0:
            continue
        for lvl in ("L1", "L2", "L3", "L4"):
            bs = base[base["level"] == lvl]
            os = other[other["level"] == lvl].sort_values(["scenario_id", "seed"])
            if len(bs) == 0 or len(os) == 0:
                continue
            # align on (scenario, seed)
            key = lambda d: list(zip(d["scenario_id"], d["seed"]))
            bm = bs.set_index(["scenario_id", "seed"])["system_weighted_loss"].sort_index()
            om = os.set_index(["scenario_id", "seed"])["system_weighted_loss"].sort_index()
            common = bm.index.intersection(om.index)
            st = paired_stats(bm.loc[common].tolist(), om.loc[common].tolist())
            if not st:
                continue
            row = {"manager": mgr, "level": lvl, **st}
            ps_all.append((f"{mgr}|{lvl}", st["p"]))
            paired_rows.append(row)
    ps_sorted = sorted(ps_all, key=lambda x: x[1])
    holm_adj = {k: v for (k, _), v in zip(ps_sorted, holm([p for _, p in ps_sorted]))}
    for row in paired_rows:
        row["p_holm"] = holm_adj.get(f"{row['manager']}|{row['level']}")
    out["paired_vs_b0_swl"] = paired_rows

    # ---- paired B4b vs B1/B2 (per level) if B4b available ----
    if "llm_b4b" in available:
        b4b = df[df["manager_kind"] == "llm_b4b"].sort_values(["scenario_id", "seed"])
        comp_rows = []
        for other, label in (("rule_based", "B1"), ("optimization", "B2")):
            o = df[df["manager_kind"] == other].sort_values(["scenario_id", "seed"])
            for lvl in ("L1", "L2", "L3", "L4"):
                bs = b4b[b4b["level"] == lvl].set_index(["scenario_id", "seed"])["system_weighted_loss"].sort_index()
                os = o[o["level"] == lvl].set_index(["scenario_id", "seed"])["system_weighted_loss"].sort_index()
                common = bs.index.intersection(os.index)
                st = paired_stats(os.loc[common].tolist(), bs.loc[common].tolist())
                if st:
                    comp_rows.append({"manager_pair": f"B4b_vs_{label}", "level": lvl, **st})
        out["paired_b4b_vs_swl"] = comp_rows

    # ---- decision behaviour (post-failure issued types) ----
    behav = defaultdict(lambda: defaultdict(int))
    for r in rows:
        for t in r.get("post_failure_issued_types", []):
            behav[r["manager_kind"]][t] += 1
    out["decision_behavior"] = {k: dict(v) for k, v in behav.items()}

    out_dir = ROOT / "outputs" / "experiment3"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "primary_analysis.json").write_text(json.dumps(out, indent=2, default=float, allow_nan=False), encoding="utf-8")
    df.to_csv(out_dir / "run_metrics.csv", index=False)
    pd.DataFrame(cells).to_csv(out_dir / "level_manager_cells.csv", index=False)
    pd.DataFrame(paired_rows).to_csv(out_dir / "paired_vs_b0.csv", index=False)

    print("\n== level x manager SWL (mean [95% CI]) ==")
    for lvl in ("L1", "L2", "L3", "L4"):
        line = f"{lvl}: "
        for mgr in MANAGERS:
            c = next((x for x in cells if x["level"] == lvl and x["manager"] == mgr), None)
            if c and c["system_weighted_loss"]["mean"] is not None:
                line += f"{mgr}={c['system_weighted_loss']['mean']:.1f} "
        print(line)
    print("\n== paired vs B0 (SWL), Holm-corrected ==")
    for r in paired_rows:
        print(f"  {r['manager']} {r['level']}: diff={r['diff_mean']:.1f} p={r['p']:.4f} holm={r['p_holm']:.4f} d={r['cohens_d']}")
    print(f"\nartifacts: outputs/experiment3/primary_analysis.json (+ run_metrics.csv, level_manager_cells.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
