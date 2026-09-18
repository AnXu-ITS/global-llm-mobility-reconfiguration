"""Experiment 1 — v2 corrected analysis.

Recomputes the execution-based metrics and statistics that the independent review
flagged in the v1 report, WITHOUT re-running any simulation:

  * air_intervention is derived from the ISSUED execution result
    (critical_mission_final_mode == "AIR"), not from proposed manager actions,
    so rejected DISPATCH-to-busy proposals no longer inflate the air rate.
  * signed seconds-saved vs B0 (negative = slower than ground), reported
    separately from the truncated DE proxy.
  * unnecessary_air keeps the frozen "ground could meet deadline" predicate but
    is re-based on the corrected air intervention.
  * paired t-test AND Wilcoxon signed-rank; Holm correction over the comparison
    family; t-quantile 95% CI (n-1 dof); a direct B4-vs-B2 test; deterministic
    differences reported as exact deltas with "effect size undefined" instead of
    a spurious p=0.

Usage: python tools/analyze_experiment1_v2.py [runs_root]
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# v1 logs were archived; the corrected v2 analysis re-reads them from the archive.
# Pass an explicit path to analyze a future v2 re-run.
RUNS = ROOT / "archive" / "experiment1_v1" / "runs" / "experiment1"

try:
    import numpy as np
    from scipy import stats as sps
except Exception:  # pragma: no cover
    np = None
    sps = None

MANAGERS = ["B0", "B1", "B2", "B4"]
KIND = {"B0": "no_cross_layer", "B1": "rule_based", "B2": "optimization", "B4": "llm"}


def load_runs(root: Path = RUNS):
    rows = []
    for mf in sorted(root.rglob("metrics.json")):
        rows.append(json.loads(mf.read_text(encoding="utf-8")))
    return rows


def ground_eta_by_scenario(rows):
    """B0 is ground-only, so its completion time is the scenario ground ETA."""
    g = {}
    for m in rows:
        if m.get("manager_kind") == "no_cross_layer":
            g[m["scenario_id"]] = m["critical_mission_completion_time_s"]
    return g


def corrected(rows):
    ge = ground_eta_by_scenario(rows)
    out = []
    for m in rows:
        sc = m["scenario_id"]
        comp = m["critical_mission_completion_time_s"]
        release = 300
        slack = m.get("critical_mission_deadline_s", release) - release
        air = (m.get("critical_mission_final_mode") == "AIR")
        ground_eta = ge.get(sc)
        unnec = bool(air and ground_eta is not None and ground_eta <= slack)
        out.append({
            "scenario": sc,
            "manager": m.get("manager_kind"),
            "seed": m.get("seed"),
            "completion": comp,
            "deadline_violation": bool(m.get("critical_mission_deadline_violation")),
            "damage": int(m.get("existing_missions_damaged_count", 0)),
            "air": air,
            "ground": m.get("critical_mission_final_mode") == "GROUND",
            "unnecessary": unnec,
            "ground_eta": ground_eta,
        })
    return out


def signed_saved(rows):
    """signed seconds saved vs B0 completion (negative = slower than ground)."""
    b0 = {r["scenario"]: r["completion"] for r in rows if r["manager"] == "no_cross_layer"}
    return [{**r, "signed_saved": b0[r["scenario"]] - r["completion"]} for r in rows]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def sd(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return 0.0
    mu = mean(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1))


def t_ci(xs, conf=0.95):
    xs = [x for x in xs if x is not None]
    n = len(xs)
    if n < 2:
        return (mean(xs), mean(xs))
    mu = mean(xs)
    se = sd(xs) / math.sqrt(n)
    if se == 0:
        return (mu, mu)
    tcrit = float(sps.t.ppf(1 - (1 - conf) / 2, df=n - 1)) if sps else 1.96
    return (round(mu - tcrit * se, 2), round(mu + tcrit * se, 2))


def paired_stats(a, b):
    """Returns (p_t, p_wilcoxon, effect_d_or_note)."""
    if np is None or len(a) < 2 or len(a) != len(b):
        return None, None, None
    aa = np.array(a, float); bb = np.array(b, float)
    d = aa - bb
    if float(np.std(d, ddof=1)) == 0.0:
        # deterministic difference -> exact delta, effect size undefined
        return (None, None, "deterministic" if abs(float(d.mean())) < 1e-9 else "deterministic-diff")
    p_t = float(sps.ttest_rel(aa, bb).pvalue)
    p_w = float(sps.wilcoxon(aa, bb).pvalue) if len(aa) >= 6 else None
    pooled = math.sqrt((aa.var(ddof=1) + bb.var(ddof=1)) / 2)
    d_eff = float(d.mean() / pooled) if pooled > 0 else None
    return p_t, p_w, d_eff


def holm(ps):
    ps = [(i, p) for i, p in enumerate(ps) if p is not None]
    ps.sort(key=lambda x: x[1])
    n = len(ps)
    adj = {}
    for rank, (i, p) in enumerate(ps):
        adj[i] = min(1.0, p * (n - rank))
    return adj


def aggregate(rows):
    by = defaultdict(list)
    for r in rows:
        by[(r["scenario"], r["manager"])].append(r)
    entries = []
    for (sc, mgr), rs in sorted(by.items()):
        comps = [r["completion"] for r in rs]
        lo, hi = t_ci(comps)
        entries.append({
            "scenario": sc, "manager": mgr, "n": len(rs),
            "completion_mean": round(mean(comps), 2),
            "completion_ci": (round(lo, 2), round(hi, 2)),
            "deadline_violation": round(mean([r["deadline_violation"] for r in rs]), 4),
            "damage": round(mean([r["damage"] for r in rs]), 4),
            "air_rate": round(mean([r["air"] for r in rs]), 4),
            "unnecessary_rate": round(mean([r["unnecessary"] for r in rs]), 4),
            "signed_saved_mean": round(mean([r["signed_saved"] for r in rs]), 2),
        })
    return entries


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else RUNS
    rows = signed_saved(corrected(load_runs(root)))
    entries = aggregate(rows)

    print("# Experiment 1 — v2 corrected analysis (execution-based)\n")
    print("scenario | mgr | n | comp | comp 95%CI | viol | damage | air | unnec | signed_saved")
    print("---|---|---|---|---|---|---|---|---|---")
    for e in entries:
        print(f"{e['scenario']} | {e['manager']} | {e['n']} | {e['completion_mean']} | "
              f"{e['completion_ci']} | {e['deadline_violation']} | {e['damage']} | "
              f"{e['air_rate']} | {e['unnecessary_rate']} | {e['signed_saved_mean']}")

    # per-manager means over the 12 scenarios (equal weight)
    print("\n## per-manager mean over 12 scenarios (equal weight)\n")
    print("mgr | comp | viol | damage | air | unnec | signed_saved")
    print("---|---|---|---|---|---|---")
    for mgr in MANAGERS:
        es = [e for e in entries if e["manager"] == KIND[mgr]]
        if not es:
            continue
        print(f"{mgr} | {mean([e['completion_mean'] for e in es]):.2f} | "
              f"{mean([e['deadline_violation'] for e in es]):.4f} | "
              f"{mean([e['damage'] for e in es]):.4f} | "
              f"{mean([e['air_rate'] for e in es]):.4f} | "
              f"{mean([e['unnecessary_rate'] for e in es]):.4f} | "
              f"{mean([e['signed_saved_mean'] for e in es]):.2f}")

    # paired comparisons: B4 vs B0 and B4 vs B2 (the review's key contrast)
    print("\n## paired comparisons (per scenario)\n")
    by = defaultdict(list)
    for r in rows:
        by[r["scenario"]].append(r)

    family = []  # (label, scenario, a_mgr, b_mgr, a, b) with seed-aligned vectors
    for sc in sorted(by):
        rs = defaultdict(list)
        for r in by[sc]:
            rs[r["manager"]].append(r)
        for mgr in rs.values():
            mgr.sort(key=lambda r: r["seed"])
        for am, bm in [("llm", "no_cross_layer"), ("llm", "optimization")]:
            if am in rs and bm in rs:
                a = [x["completion"] for x in rs[am]]
                b = [x["completion"] for x in rs[bm]]
                family.append((f"{am} vs {bm}", sc, am, bm, a, b))

    results = []
    for label, sc, am, bm, a, b in family:
        p_t, p_w, d = paired_stats(a, b)
        results.append((label, sc, p_t, p_w, d))

    pvals = [r[2] for r in results]
    adj = holm(pvals)
    print("scenario | contrast | t-p | wilcoxon-p | holm-adj | effect")
    print("---|---|---|---|---|---")
    for i, (label, sc, p_t, p_w, d) in enumerate(results):
        pt = f"{p_t:.4g}" if p_t is not None else "det"
        pw = f"{p_w:.4g}" if p_w is not None else "-"
        pa = f"{adj.get(i, 1):.4g}" if p_t is not None else "-"
        de = f"{d:.3f}" if isinstance(d, float) else str(d)
        print(f"{sc} | {label} | {pt} | {pw} | {pa} | {de}")

    # save
    out = {"entries": entries, "comparisons": [
        {"scenario": sc, "contrast": label, "t_p": p_t, "wilcoxon_p": p_w,
         "holm_adj": adj.get(i), "effect": d}
        for i, (label, sc, p_t, p_w, d) in enumerate(results)]}
    dest = ROOT / "runs" / "experiment1_v2_corrected.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[saved] {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
