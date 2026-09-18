"""B4a (LLM-State) vs B4b (LLM-Candidate) interface ablation (Finalization §26).

Compares, over the ablation scenarios x seeds (paired on identical state):
air-intervention rate, unnecessary-air rate, existing-service damage, deadline
violation, completion time.  Reports mean/95% CI and paired contrasts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RUNS = ROOT / "runs" / "experiment1_final"
OUT = ROOT / "outputs" / "experiment1_final"
RELEASE_T = 300.0
THETA_TIME = 60.0

# reuse the primary analyzer's loaders to avoid drift
from tools.analyze_experiment1_final import (KIND_TO_LABEL, enrich,  # noqa: E402
                                             load_runs)


def mean_ci(vals):
    a = np.asarray([v for v in vals if v is not None], dtype=float)
    if a.size == 0:
        return {"n": 0, "mean": None, "ci95": [None, None]}
    mean = float(a.mean())
    sd = float(a.std(ddof=1)) if a.size > 1 else 0.0
    if a.size > 1:
        h = sd / np.sqrt(a.size) * stats.t.ppf(0.975, a.size - 1)
        return {"n": int(a.size), "mean": round(mean, 3), "ci95": [round(mean - h, 3), round(mean + h, 3)]}
    return {"n": int(a.size), "mean": round(mean, 3), "ci95": [round(mean, 3), round(mean, 3)]}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(RUNS))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    runs_root = Path(args.runs)
    rows = enrich(load_runs(runs_root))
    out_root = Path(args.out)
    a = [r for r in rows if r["_label"] == "B4a"]
    b_all = [r for r in rows if r["_label"] == "B4b"]

    # restrict B4b to the SAME (scenario, seed) cells as B4a (paired ablation)
    ak = {(r["_scenario"], r["_seed"]): r for r in a}
    b = [r for r in b_all if (r["_scenario"], r["_seed"]) in ak]
    ab = {"B4a": a, "B4b": b}

    out = {}
    for lbl, rs in ab.items():
        out[lbl] = {
            "n": len(rs),
            "air_rate": mean_ci([bool(r.get("air_intervention")) for r in rs]),
            "unnecessary_rate": mean_ci([r["_unnecessary"] for r in rs]),
            "damage": mean_ci([r.get("existing_missions_damaged_count", 0) for r in rs]),
            "violation_rate": mean_ci([bool(r.get("critical_mission_deadline_violation")) for r in rs]),
            "completion": mean_ci([r.get("critical_mission_completion_time_s") for r in rs]),
        }

    # paired contrasts on shared (scenario, seed)
    bk = {(r["_scenario"], r["_seed"]): r for r in b}
    keys = sorted(set(ak) & set(bk))
    ca = [ak[k].get("critical_mission_completion_time_s") for k in keys]
    cb = [bk[k].get("critical_mission_completion_time_s") for k in keys]
    contrasts = {
        "n_paired": len(keys),
        "completion_t_p": round(float(stats.ttest_rel(cb, ca).pvalue), 6) if len(keys) > 1 else None,
        "completion_d": round(float(np.mean([x - y for x, y in zip(ca, cb)]) /
                                np.std([x - y for x, y in zip(ca, cb)], ddof=1)), 3) if len(keys) > 1 else None,
    }
    # binary paired (B4a vs B4b)
    def mcnemar(field):
        x = [bool(ak[k].get(field)) for k in keys]
        y = [bool(bk[k].get(field)) for k in keys]
        bd = sum(1 for i, j in zip(x, y) if i and not j)
        cd = sum(1 for i, j in zip(x, y) if j and not i)
        n = bd + cd
        if n == 0:
            return 1.0
        from scipy.stats import binom
        return round(float(min(1.0, 2 * binom.cdf(min(bd, cd), n, 0.5))), 6)

    contrasts["air_mcnemar_p"] = mcnemar("air_intervention")
    contrasts["unnecessary_mcnemar_p"] = mcnemar("_unnecessary")
    contrasts["violation_mcnemar_p"] = mcnemar("critical_mission_deadline_violation")

    out["paired_contrasts"] = contrasts
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "ablation_b4a_vs_b4b.json").write_text(
        json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"\n[saved] {out_root / 'ablation_b4a_vs_b4b.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
