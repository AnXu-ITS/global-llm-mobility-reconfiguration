"""Corrected offline recomputation of E2/E3 statistics (post independent review 20260908).

Applies the review's fixes to the FROZEN artifacts without re-running the
simulation or the experiment LLM (read-only on runs/, config/):

  1. Deadline violation (P0-5): unfinished + past deadline == violation.
  2. McNemar (§5.4): scipy binomtest is already two-sided — no ×2.
  3. Holm (§5.4): cumulative-max step-down + NaN-safe (p undefined -> 1.0).

Reads:  runs/experiment{2,3}(_cross_site/<site>)/... metrics.json, config matrices.
Writes: outputs/corrected_20260908/  (never overwrites frozen outputs/experiment{2,3}/).

Cross-checks against the independent review (should reproduce):
  - E3 Site B B4b deadline-violation rate 59/240 = 24.58% (was 53/240 = 22.08%).
  - E2 Site A aggregate completion-time diff Holm p ≈ 0.00868 (12-item family).
  - McNemar exact: 5:0 -> 0.0625; 9:0 -> 0.00390625.
  - E3 Site B L2 SWL Holm ≈ 0.21135 (not 0.036).

Run from repo root:  python tools/recompute_corrected_stats.py
"""
from __future__ import annotations

import json
import math
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml
from scipy import stats

warnings.filterwarnings("ignore", category=RuntimeWarning)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "corrected_20260908"
MANAGERS = ("B0", "B1", "B2", "B4b")
KIND = {"B0": "no_cross_layer", "B1": "rule_based",
        "B2": "optimization", "B4b": "llm_b4b"}
E2_CONT = ["critical_mission_completion_time_s", "recovery_time_s",
           "failure_to_replan_latency_s", "existing_missions_damaged_count",
           "candidate_set_reduction_delta"]
E2_BIN = ["critical_mission_deadline_violation", "recovery_success",
          "recovered_completed", "ground_fallback_rate",
          "failure_induced_ground_fallback", "necessary_ground_fallback_correct",
          "air_intervention"]
SITE_SUFFIX = {"A": "", "B": "site_b_amsterdam", "C": "site_c_edmonton"}


def finite(x):
    return x is not None and math.isfinite(float(x))


def mean(vals):
    v = [float(x) for x in vals if finite(x)]
    return float(np.mean(v)) if v else None


def correct_deadline_violation(m):
    """P0-5: unfinished (comp_t None) past deadline counts as a violation."""
    comp_t = m.get("critical_mission_completion_t")
    dl = m.get("critical_mission_deadline_s")
    if dl is None:
        return None
    return bool(comp_t is None or comp_t > dl)


def paired(a_vals, b_vals):
    """Paired t-test + Wilcoxon on (a=base, b=other). Returns dict or None."""
    xy = [(float(a), float(b)) for a, b in zip(a_vals, b_vals)
          if finite(a) and finite(b)]
    if len(xy) < 2:
        return None
    a, b = np.array(xy).T
    d = b - a
    if np.all(d == 0):
        p = wp = 1.0
    else:
        p = float(stats.ttest_rel(b, a).pvalue)
        try:
            wp = float(stats.wilcoxon(b, a).pvalue)
        except Exception:
            wp = p
    se = float(np.std(d, ddof=1) / math.sqrt(len(d)))
    ci = float(stats.t.ppf(0.975, len(d) - 1)) * se
    pooled = math.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2) if len(a) > 1 else 1.0
    return {"n": len(d), "diff_mean": float(np.mean(d)), "ci95": [float(np.mean(d) - ci), float(np.mean(d) + ci)],
            "p": p, "wilcoxon_p": wp,
            "cohens_d": float(np.mean(d) / pooled) if pooled > 1e-12 else None}


def mcnemar(a_vals, b_vals):
    """Exact McNemar: two-sided binomtest on discordant pairs (no ×2)."""
    xy = [(bool(a), bool(b)) for a, b in zip(a_vals, b_vals)
          if finite(a) and finite(b)]
    b = sum(not x and y for x, y in xy)
    c = sum(x and not y for x, y in xy)
    if b + c == 0:
        p = 1.0
    else:
        p = float(stats.binomtest(min(b, c), b + c, 0.5).pvalue)
    return {"n": len(xy), "b": b, "c": c, "p": p}


def holm(tests):
    """Holm step-down with cumulative max; undefined (all-identical) p -> 1.0."""
    ps = [float(t["p"]) if finite(t.get("p")) else 1.0 for t in tests]
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    running = float("-inf")
    for k, i in enumerate(order):
        running = max(running, min(1.0, ps[i] * (len(ps) - k)))
        tests[i]["holm_p"] = running


def load_runs():
    rows = []
    for exp in (2, 3):
        seeds = yaml.safe_load((ROOT / f"config/experiment{exp}_seeds.yaml").read_text(encoding="utf-8"))["primary_seeds"]
        for site in ("A", "B", "C"):
            cfg = ROOT / (f"config/experiment{exp}" + (f"_site_{site.lower()}" if site != "A" else "") + "_matrix.yaml")
            matrix = yaml.safe_load(cfg.read_text(encoding="utf-8"))[f"experiment{exp}"]
            root = ROOT / f"runs/experiment{exp}" if site == "A" else ROOT / f"runs/experiment{exp}_cross_site" / SITE_SUFFIX[site]
            for sc in matrix["scenarios"]:
                sid = sc["id"]
                for seed in seeds:
                    for mgr in MANAGERS:
                        mp = root / sid / f"seed{seed}" / mgr / "metrics.json"
                        if not mp.exists():
                            continue
                        m = json.loads(mp.read_text(encoding="utf-8"))
                        m["_exp"] = exp
                        m["_site"] = site
                        m["_sid"] = sid
                        m["_seed"] = seed
                        m["_mgr"] = mgr
                        m["_level"] = sc.get("level")
                        m["_corrected_violation"] = correct_deadline_violation(m)
                        m["_critical_high_loss"] = sum(
                            float((m.get("system_weighted_loss_by_priority") or {}).get(k, 0.0))
                            for k in ("CRITICAL", "HIGH"))
                        rows.append(m)
    return rows


def bykey(rows, exp, site):
    return {(r["_sid"], r["_seed"], r["_mgr"]): r
            for r in rows if r["_exp"] == exp and r["_site"] == site}


def main() -> int:
    rows = load_runs()
    print(f"loaded {len(rows)} runs across E2/E3 x A/B/C")

    summary = {"deadline_violation_rates": {}, "e2_aggregate_family": {}, "e3_site_family": {}}

    # ---- 1. corrected vs original deadline-violation rates ----
    for exp in (2, 3):
        for site in ("A", "B", "C"):
            for mgr in MANAGERS:
                rr = [r for r in rows if r["_exp"] == exp and r["_site"] == site and r["_mgr"] == mgr]
                if not rr:
                    continue
                orig = mean([r["critical_mission_deadline_violation"] for r in rr])
                corr = mean([r["_corrected_violation"] for r in rr])
                n_corr = sum(bool(r["_corrected_violation"]) for r in rr)
                summary["deadline_violation_rates"][f"E{exp}_{site}_{mgr}"] = {
                    "n": len(rr), "original_rate": orig, "corrected_rate": corr,
                    "corrected_count": n_corr}

    # ---- 2. E2 aggregate B2-vs-B4b 12-item family (per site) ----
    for site in ("A", "B", "C"):
        b2 = [r for r in rows if r["_exp"] == 2 and r["_site"] == site and r["_mgr"] == "B2"]
        b4 = [r for r in rows if r["_exp"] == 2 and r["_site"] == site and r["_mgr"] == "B4b"]
        key = lambda r: (r["_sid"], r["_seed"])
        a = sorted(b2, key=key)
        b = sorted(b4, key=key)
        tests = []
        for met in E2_CONT:
            st = paired([r[met] for r in a], [r[met] for r in b])
            if st:
                tests.append(dict(st, metric=met))
        for met in E2_BIN:
            if met == "critical_mission_deadline_violation":
                va = [r["_corrected_violation"] for r in a]
                vb = [r["_corrected_violation"] for r in b]
            else:
                va = [r[met] for r in a]
                vb = [r[met] for r in b]
            mc = mcnemar(va, vb)
            if mc:
                tests.append(dict(mc, metric=met, kind="mcnemar"))
        holm(tests)
        summary["e2_aggregate_family"][site] = tests

    # ---- 3. E3 site-level 12-item family (B4b vs B1/B2 x L2/L3/L4 x SWL/CRITICAL+HIGH) ----
    for site in ("A", "B", "C"):
        b4 = [r for r in rows if r["_exp"] == 3 and r["_site"] == site and r["_mgr"] == "B4b"]
        tests = []
        for other, label in (("B1", "B1"), ("B2", "B2")):
            o = [r for r in rows if r["_exp"] == 3 and r["_site"] == site and r["_mgr"] == other]
            for lvl in ("L2", "L3", "L4"):
                bo = sorted([r for r in b4 if r["_level"] == lvl], key=lambda r: (r["_sid"], r["_seed"]))
                oo = sorted([r for r in o if r["_level"] == lvl], key=lambda r: (r["_sid"], r["_seed"]))
                for met in ("system_weighted_loss", "_critical_high_loss"):
                    st = paired([r[met] for r in oo], [r[met] for r in bo])
                    if st:
                        tests.append(dict(st, metric=met, level=lvl, other=label))
        holm(tests)
        summary["e3_site_family"][site] = tests

    OUT.mkdir(parents=True, exist_ok=True)

    # per-run corrected violation CSV
    import csv
    with (OUT / "corrected_deadline_violations.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["experiment", "site", "scenario", "seed", "manager",
                                          "completion_t", "deadline_s", "original_violation",
                                          "corrected_violation"])
        w.writeheader()
        for r in rows:
            w.writerow({"experiment": f"E{r['_exp']}", "site": r["_site"], "scenario": r["_sid"],
                        "seed": r["_seed"], "manager": r["_mgr"],
                        "completion_t": r.get("critical_mission_completion_t"),
                        "deadline_s": r.get("critical_mission_deadline_s"),
                        "original_violation": r.get("critical_mission_deadline_violation"),
                        "corrected_violation": r["_corrected_violation"]})

    (OUT / "corrected_stats.json").write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")

    # ---- console cross-checks ----
    print("\n== corrected deadline-violation rates (E3 Site B) ==")
    for k in ("E3_B_B4b", "E3_B_B2", "E3_B_B1", "E3_B_B0"):
        v = summary["deadline_violation_rates"].get(k)
        if v:
            print(f"  {k}: orig={v['original_rate']:.4f} corrected={v['corrected_rate']:.4f} ({v['corrected_count']}/{v['n']})")

    print("\n== E2 Site A aggregate family (B2 vs B4b), corrected Holm ==")
    for t in summary["e2_aggregate_family"]["A"]:
        kind = t.get("kind", "paired")
        if kind == "mcnemar":
            print(f"  {t['metric']}: McNemar p={t['p']:.6f} holm={t['holm_p']:.6f} (b={t['b']}, c={t['c']})")
        else:
            print(f"  {t['metric']}: diff={t['diff_mean']:.4f} p={t['p']:.6f} holm={t['holm_p']:.6f}")

    print("\n== E3 Site B site-level family, corrected Holm ==")
    for t in summary["e3_site_family"]["B"]:
        if t["level"] == "L2" and t["metric"] == "system_weighted_loss":
            print(f"  B4b_vs_{t['other']} {t['level']} SWL: diff={t['diff_mean']:.3f} p={t['p']:.6f} holm={t['holm_p']:.6f}")

    print(f"\nartifacts written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
