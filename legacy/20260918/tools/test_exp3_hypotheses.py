"""Experiment 3 — Hypothesis tests (H3a / H3b), run after the full 4-manager primary.

H3a (compound advantage): under compound stress (L2 cascade, L3 competition,
L4 full compound), the LLM-supervised manager B4b achieves LOWER system-weighted
loss (SWL) than the frozen rule-based B1 and the frozen optimization B2.

H3b (priority consistency): B4b preserves high-priority missions better than
B1/B2 — its CRITICAL+HIGH weighted loss is lower — at the cost of (or not worse
on) NORMAL/LOW. The priority-weighted loss is taken from
`system_weighted_loss_by_priority` (weights CRITICAL=4, HIGH=3, NORMAL=2, LOW=1).

Paired design (managers share scenario x seed); paired t-test; Holm correction
across all tests in the family. Nulls are reported honestly (p>=0.05 after Holm
=> "no evidence").

Usage: python tools/test_exp3_hypotheses.py
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


def load():
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
                rows.append(m)
    return rows


def paired(a_vals, b_vals):
    from paper_stats import paired as shared_paired
    return shared_paired(a_vals, b_vals)


def holm(ps):
    from paper_stats import holm as shared_holm
    return shared_holm(ps)


def main() -> int:
    df = pd.DataFrame(load())
    for p in ("CRITICAL", "HIGH", "NORMAL", "LOW"):
        df[f"swl_{p}"] = df["system_weighted_loss_by_priority"].apply(
            lambda bp, p=p: float((bp or {}).get(p, 0.0)))
    df["swl_crit_high"] = df["swl_CRITICAL"] + df["swl_HIGH"]

    b4b = df[df["manager_kind"] == "llm_b4b"].sort_values(["scenario_id", "seed"])
    tests = []  # (label, level, p, b4b_mean, other_mean, diff, d, metric)

    print(f"B4b runs: {len(b4b)}")
    if len(b4b) == 0:
        print("B4b not yet run — nothing to test.")
        return 1

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

    # Holm across the whole family
    ps = [t["p"] for t in tests]
    adj = holm(ps)
    for t, h in zip(tests, adj):
        t["p_holm"] = h

    print("\n== H3a / H3b tests (B4b vs B1/B2, paired; Holm across all rows) ==")
    print(f"{'test':<30} {'B4b':>7} {'other':>7} {'diff':>8} {'p':>8} {'holm':>8} {'d':>7}")
    for t in tests:
        sig = " *" if t["p_holm"] < 0.05 else ""
        print(f"{t['label']:<30} {t['b4b_mean']:>7.1f} {t['other_mean']:>7.1f} "
              f"{t['diff']:>+8.1f} {t['p']:>8.4f} {t['p_holm']:>8.4f} {str(t['d']):>7}{sig}")

    print("\n== verdict ==")
    h3a = [t for t in tests if t["metric"] == "SWL"]
    h3a_sig = [t for t in h3a if t["p_holm"] < 0.05 and t["diff"] < 0]
    h3a_against = [t for t in h3a if t["p_holm"] < 0.05 and t["diff"] > 0]
    print(f"H3a (B4b lowers SWL vs B1/B2 under compound): {len(h3a_sig)}/{len(h3a)} "
          f"tests support (B4b < other, Holm p<0.05); {len(h3a_against)} oppose.")
    for t in h3a_sig:
        print("   support:", t["label"], f"diff={t['diff']:.1f} holm={t['p_holm']:.4f}")
    for t in h3a_against:
        print("   OPPOSE:", t["label"], f"diff={t['diff']:.1f} holm={t['p_holm']:.4f}")

    h3b = [t for t in tests if t["metric"] == "CRIT+HIGH loss"]
    h3b_sig = [t for t in h3b if t["p_holm"] < 0.05 and t["diff"] < 0]
    print(f"H3b (B4b lowers CRIT+HIGH loss vs B1/B2): {len(h3b_sig)}/{len(h3b)} tests support.")

    (ROOT / "outputs" / "experiment3" / "hypothesis_tests.json").write_text(
        json.dumps({"h3a": h3a, "h3b": h3b, "all": tests}, indent=2, default=float, allow_nan=False),
        encoding="utf-8")
    print("\nwrote outputs/experiment3/hypothesis_tests.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
