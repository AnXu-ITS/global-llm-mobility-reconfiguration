"""Experiment 3 cross-site — Hypothesis tests (H3a/H3b) per site + replication.

Mirrors tools/test_exp3_hypotheses.py but stratifies by site (A/B/C) and adds a
replication check: whether the frozen Site-A E3 verdict (H3a/H3b NULL —
B1 == B2 == B4b) holds on Site B and Site C.

Paired design (managers share scenario x seed within a site); paired t-test +
Wilcoxon; Holm correction within the whole per-site family. A site's verdict is
"null" when no test reaches p<0.05 after Holm.

Usage: python tools/test_exp3_cross_site_hypotheses.py
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
SITES = {
    "A": ("runs/experiment3", "config/experiment3_matrix.yaml"),
    "B": ("runs/experiment3_cross_site/site_b_amsterdam", "config/experiment3_site_b_matrix.yaml"),
    "C": ("runs/experiment3_cross_site/site_c_edmonton", "config/experiment3_site_c_matrix.yaml"),
}


def load(site):
    run_root, matrix = SITES[site]
    e3 = yaml.safe_load((ROOT / matrix).read_text(encoding="utf-8"))["experiment3"]
    seeds = list(yaml.safe_load((ROOT / "config" / "experiment3_seeds.yaml").read_text(encoding="utf-8"))["primary_seeds"])
    rows = []
    for s in e3["scenarios"]:
        for seed in seeds:
            for mgr in MANAGERS:
                mp = ROOT / run_root / s["id"] / f"seed{seed}" / mgr / "metrics.json"
                if not mp.exists():
                    continue
                m = json.loads(mp.read_text(encoding="utf-8"))
                m["scenario_id"] = s["id"]
                m["level"] = s["level"]
                rows.append(m)
    return rows


def paired(a_vals, b_vals):
    from paper_stats import paired as shared_paired
    return shared_paired(a_vals, b_vals)


def holm(ps):
    from paper_stats import holm as shared_holm
    return shared_holm(ps)


def site_tests(df):
    for p in ("CRITICAL", "HIGH", "NORMAL", "LOW"):
        df[f"swl_{p}"] = df["system_weighted_loss_by_priority"].apply(
            lambda bp, p=p: float((bp or {}).get(p, 0.0)))
    df["swl_crit_high"] = df["swl_CRITICAL"] + df["swl_HIGH"]

    b4b = df[df["manager_kind"] == "llm_b4b"].sort_values(["scenario_id", "seed"])
    if len(b4b) == 0:
        return []
    tests = []
    for other_label, other_kind in (("B1", "rule_based"), ("B2", "optimization")):
        o = df[df["manager_kind"] == other_kind].sort_values(["scenario_id", "seed"])
        for lvl in ("L2", "L3", "L4"):
            for metric, key in (("SWL", "system_weighted_loss"), ("CRIT+HIGH loss", "swl_crit_high")):
                bb = b4b[b4b["level"] == lvl].set_index(["scenario_id", "seed"])[key].sort_index()
                oo = o[o["level"] == lvl].set_index(["scenario_id", "seed"])[key].sort_index()
                common = bb.index.intersection(oo.index)
                st = paired(oo.loc[common].tolist(), bb.loc[common].tolist())
                if st:
                    tests.append({
                        "label": f"B4b vs {other_label} {lvl} {metric}",
                        "level": lvl, "other": other_label, "metric": metric,
                        "b4b_mean": float(np.mean(bb.loc[common])),
                        "other_mean": float(np.mean(oo.loc[common])),
                        "diff": st["diff_mean"], "p": st["p"], "d": st["cohens_d"],
                        "n": st["n"], "diff_ci95": st["diff_ci95"], "wilcoxon_p": st["wilcoxon_p"]})
    return tests


def main() -> int:
    out = {}
    for site in ("A", "B", "C"):
        df = pd.DataFrame(load(site))
        tests = site_tests(df)
        if not tests:
            print(f"site {site}: B4b not run — skip")
            continue
        ps = [t["p"] for t in tests]
        adj = holm(ps)
        for t, h in zip(tests, adj):
            t["p_holm"] = h
        out[site] = tests

        print(f"\n== site {site}: H3a/H3b (B4b vs B1/B2, paired, Holm) ==")
        print(f"{'test':<30} {'B4b':>7} {'other':>7} {'diff':>8} {'p':>8} {'holm':>8} {'d':>7}")
        for t in tests:
            sig = " *" if t["p_holm"] < 0.05 else ""
            print(f"{t['label']:<30} {t['b4b_mean']:>7.1f} {t['other_mean']:>7.1f} "
                  f"{t['diff']:>+8.1f} {t['p']:>8.4f} {t['p_holm']:>8.4f} {str(t['d']):>7}{sig}")

        h3a_sig = [t for t in tests if t["metric"] == "SWL" and t["p_holm"] < 0.05 and t["diff"] < 0]
        h3a_against = [t for t in tests if t["metric"] == "SWL" and t["p_holm"] < 0.05 and t["diff"] > 0]
        verdict = ("support" if h3a_sig and not h3a_against else
                   ("oppose" if h3a_against else "null"))
        print(f"   verdict H3a: {verdict} "
              f"(support {len(h3a_sig)}, oppose {len(h3a_against)}, tests {len([t for t in tests if t['metric']=='SWL'])})")

    print("\n== replication summary ==")
    for site in out:
        ts = out[site]
        h3a_sig = [t for t in ts if t["metric"] == "SWL" and t["p_holm"] < 0.05 and t["diff"] < 0]
        h3a_against = [t for t in ts if t["metric"] == "SWL" and t["p_holm"] < 0.05 and t["diff"] > 0]
        v = "support" if h3a_sig and not h3a_against else ("oppose" if h3a_against else "null")
        print(f"  site {site}: H3a {v}")

    (ROOT / "outputs" / "experiment3" / "cross_site_hypothesis_tests.json").write_text(
        json.dumps(out, indent=2, default=float, allow_nan=False), encoding="utf-8")
    print("\nwrote outputs/experiment3/cross_site_hypothesis_tests.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
