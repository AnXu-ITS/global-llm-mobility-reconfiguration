"""Experiment 3 cross-site analysis — three-site comparison (Site A/B/C).

Loads the frozen Site-A E3 primary dataset (runs/experiment3/) plus the
cross-site datasets (runs/experiment3_cross_site/<site_id>/...) and produces
per-site, per-level x per-manager SWL + deadline-violation tables and the
three-site comparison.

Artifacts: outputs/experiment3/cross_site_analysis.json
           outputs/experiment3/cross_site_cells.csv
"""
from __future__ import annotations

import json
import math
import sys
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
KIND = {"B0": "no_cross_layer", "B1": "rule_based", "B2": "optimization", "B4b": "llm_b4b"}
PRIO = ["CRITICAL", "HIGH", "NORMAL", "LOW"]


def _load(site_label, run_root, matrix_path):
    e3 = yaml.safe_load((ROOT / matrix_path).read_text(encoding="utf-8"))["experiment3"]
    seeds = list(yaml.safe_load((ROOT / "config" / "experiment3_seeds.yaml").read_text(encoding="utf-8"))["primary_seeds"])
    rows = []
    for s in e3["scenarios"]:
        for seed in seeds:
            for mgr in MANAGERS:
                mp = run_root / s["id"] / f"seed{seed}" / mgr / "metrics.json"
                if not mp.exists():
                    continue
                m = json.loads(mp.read_text(encoding="utf-8"))
                m["scenario_id"] = s["id"]
                m["level"] = s["level"]
                m["site"] = site_label
                rows.append(m)
    return rows


def mean_ci(vals):
    a = np.array([v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))], dtype=float)
    if len(a) == 0:
        return None, None
    m = float(np.mean(a))
    sd = float(np.std(a, ddof=1)) if len(a) > 1 else 0.0
    se = sd / math.sqrt(len(a))
    tcrit = stats.t.ppf(0.975, len(a) - 1) if len(a) > 1 else math.nan
    lo = m - tcrit * se if not math.isnan(tcrit) else m
    hi = m + tcrit * se if not math.isnan(tcrit) else m
    return m, (lo, hi)


def main() -> int:
    rows = []
    rows += _load("A", ROOT / "runs" / "experiment3", "config/experiment3_matrix.yaml")
    rows += _load("B", ROOT / "runs" / "experiment3_cross_site" / "site_b_amsterdam",
                  "config/experiment3_site_b_matrix.yaml")
    rows += _load("C", ROOT / "runs" / "experiment3_cross_site" / "site_c_edmonton",
                  "config/experiment3_site_c_matrix.yaml")
    df = pd.DataFrame(rows)
    for p in PRIO:
        df[f"swl_{p.lower()}"] = df["system_weighted_loss_by_priority"].apply(
            lambda bp, p=p: float((bp or {}).get(p, 0.0)))
    print(f"loaded {len(df)} runs (sites {sorted(df['site'].unique())})")

    cells = []
    for site in ("A", "B", "C"):
        for lvl in ("L1", "L2", "L3", "L4"):
            for mgr in MANAGERS:
                sub = df[(df["site"] == site) & (df["level"] == lvl)
                         & (df["manager_kind"] == KIND[mgr])]
                if len(sub) == 0:
                    continue
                swl_m, swl_ci = mean_ci(sub["system_weighted_loss"].tolist())
                viol = float(np.mean([v for v in sub["critical_mission_deadline_violation"].tolist() if v is not None]))
                crit_m, _ = mean_ci(sub["swl_critical"].tolist())
                cell = {"site": site, "level": lvl, "manager": mgr, "n": len(sub),
                        "swl_mean": swl_m, "swl_ci95": swl_ci, "deadline_violation_rate": viol,
                        "swl_critical_mean": crit_m}
                cells.append(cell)
    out = {"cells": cells}

    # three-site comparison: per-site aggregate + per-level SWL by manager
    print("\n== three-site SWL by level x manager (mean) ==")
    print(f"{'site':<5}{'L1':>18}{'L2':>18}{'L3':>18}{'L4':>18}")
    for site in ("A", "B", "C"):
        for mgr in MANAGERS:
            vals = []
            for lvl in ("L1", "L2", "L3", "L4"):
                sub = df[(df["site"] == site) & (df["level"] == lvl)
                         & (df["manager_kind"] == KIND[mgr])]
                m, _ = mean_ci(sub["system_weighted_loss"].tolist()) if len(sub) else (None, None)
                vals.append(f"{m:.0f}" if m is not None else "—")
            print(f"{site}-{mgr:<3}{vals[0]:>18}{vals[1]:>18}{vals[2]:>18}{vals[3]:>18}")

    print("\n== per-site aggregate SWL + deadline violation ==")
    for site in ("A", "B", "C"):
        line = f"site {site}: "
        for mgr in MANAGERS:
            sub = df[(df["site"] == site) & (df["manager_kind"] == KIND[mgr])]
            if len(sub) == 0:
                continue
            m, _ = mean_ci(sub["system_weighted_loss"].tolist())
            viol = float(np.mean([v for v in sub["critical_mission_deadline_violation"].tolist() if v is not None]))
            line += f"{mgr} SWL={m:.1f} viol={viol:.2f} | "
        print(line)

    out_dir = ROOT / "outputs" / "experiment3"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cross_site_analysis.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    pd.DataFrame(cells).to_csv(out_dir / "cross_site_cells.csv", index=False)
    print("\nwrote outputs/experiment3/cross_site_analysis.json (+ cross_site_cells.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
