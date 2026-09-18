"""Experiment 2 — Final Results report generator (protocol §42/§43).

Assembles reports/experiment2/EXPERIMENT2_FINAL_RESULTS.md from the frozen
primary dataset and all analysis artifacts. Wording discipline (§43): only
statistically supported statements; no "LLM is more intelligent/robust";
"comparable aggregate performance" without a frozen equivalence margin.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "outputs" / "experiment2"
MANAGERS = ("B0", "B1", "B2", "B4b")
MGR_LABEL = {"B0": "B0 (no cross-layer)", "B1": "B1 (rule/air-first)",
             "B2": "B2 (frozen optimizer)", "B4b": "B4b (LLM-candidate)"}


def load_json(name: str):
    p = OUT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main() -> int:
    df = pd.read_csv(OUT / "run_metrics.csv")
    pa = load_json("primary_analysis.json")
    fa = load_json("failure_awareness.json")
    lr = load_json("llm_reliability.json")
    with open(OUT / "paired_b2_b4b.csv", newline="") as f:
        paired = list(csv.DictReader(f))

    agg = pa.get("aggregate", {})
    agg_paired = pa.get("paired_b2_b4b_aggregate", {})

    # excluded runs
    excl = ROOT / "runs" / "experiment2" / "excluded_runs.csv"
    excluded = []
    if excl.exists():
        with open(excl, newline="", encoding="utf-8") as f:
            excluded = [r for r in csv.DictReader(f)]

    n_runs = len(df)
    fams = sorted(df["failure_family"].unique())

    md = ["# Experiment 2 — Final Results (Air-Layer Failure Management)",
          "",
          f"Primary dataset: {n_runs} runs (16 scenario classes × 20 seeds × 4 "
          f"managers; pilot cells reused only where their frozen-config hash "
          f"matches). Excluded runs: {len(excluded)}.",
          ""]

    # Q1/Q2/Q3/Q4
    md.append("## 1–4. Matrix, scenario classes, run counts, exclusions")
    md.append("")
    md.append("- Final matrix: 16 scenario classes (target 18). Two documented "
              "SCENARIO_DESIGN_LIMITATIONs: **F3-C2** (a single UTM state change "
              "cannot break the critical chain while leaving a legal air backup — "
              "OUTAGE forbids all new air assignments, DEGRADED does not interrupt "
              "in-flight missions) and **F4-C2** (a single landing-site failure on "
              "the critical destination V1 removes all air alternatives at once; "
              "V2/V3 failures are peripheral). Both documented in "
              "`EXPERIMENT2_SCENARIO_AUDIT.md`; per protocol §27 the matrix was "
              "reduced instead of padded.")
    md.append("- Primary runs: 16 × 20 × 4 = **1280** (B0/B1/B2/B4b = 320 each); "
              f"**{n_runs}** collected, **{len(excluded)}** excluded "
              f"({'; '.join(f\"{r['scenario_id']}/{r['seed']}/{r['manager']}\" for r in excluded[:5]) if excluded else 'none'}).")
    md.append("- Replay runs (reproducibility only, NOT samples): see "
              "`EXPERIMENT2_REPLAY_AUDIT.md`.")
    md.append("")

    # Q5 candidate-set effect per family
    md.append("## 5. How each failure changes the feasible candidate set")
    md.append("")
    md.append("| family | C1 (peripheral) | C2 (chain + backup) | C3 (no air) |")
    md.append("|---|---|---|---|")
    fam_desc = {
        "F1": ("2→1 (background C2-lost; backup intact)", "2→1 (critical aircraft lost; backup legal)",
               "1→0 (W1: no idle medical asset)"),
        "F2": ("2→1 (shuttle degraded; backup intact)", "2→1 (critical aircraft degraded; backup legal)",
               "1→0 (W1)"),
        "F3": ("2→1 (DEGRADED: new non-critical air blocked)", "— (SCENARIO_DESIGN_LIMITATION)",
               "2→0 (OUTAGE: no new air)"),
        "F4": ("2→1 (V2 down; critical destination intact)", "— (SCENARIO_DESIGN_LIMITATION)",
               "2→0 (V1 down: destination-level)"),
        "F5": ("2→1 (peripheral intrusion; backup intact)", "2→1 (corridor zone; V3→V1 clear)",
               "2→0 (zone covers corridor + recovery route)"),
        "F6": ("2→1 (flyaway; low-latitude envelope)", "2→1 (envelope crosses corridor only)",
               "2→0 (envelope covers corridor + V3→V1)"),
    }
    for fam in ("F1", "F2", "F3", "F4", "F5", "F6"):
        d = fam_desc[fam]
        md.append(f"| {fam} | {d[0]} | {d[1]} | {d[2]} |")
    md.append("")

    # Q6-12 per-manager results
    md.append("## 6–12. Core results per manager")
    md.append("")
    md.append("| metric | B0 | B1 | B2 | B4b |")
    md.append("|---|---|---|---|---|")
    rows_metric = [
        ("critical completion time (s)", "critical_mission_completion_time_s"),
        ("recovery time (s, affected runs)", "recovery_time_s"),
        ("failure-to-replan latency (s)", "failure_to_replan_latency_s"),
        ("existing service damage (mean missions)", "existing_missions_damaged_count"),
    ]
    for label, key in rows_metric:
        cells = []
        for mgr in MANAGERS:
            c = agg.get(mgr, {}).get(key, {}) or {}
            m, ci = c.get("mean"), c.get("ci95")
            cells.append(f"{m:.2f}" if m is not None else "—"
                         + (f" [{ci[0]:.2f},{ci[1]:.2f}]" if ci else ""))
        md.append(f"| {label} | {' | '.join(cells)} |")
    for label, key in [
        ("deadline violation rate", "critical_mission_deadline_violation_rate"),
        ("recovery success rate (affected runs)", "recovery_success_rate"),
        ("ground fallback rate", "ground_fallback_rate"),
    ]:
        cells = []
        for mgr in MANAGERS:
            v = agg.get(mgr, {}).get(key)
            cells.append(f"{v:.3f}" if v is not None else "—")
        md.append(f"| {label} | {' | '.join(cells)} |")
    fa_pm = fa.get("per_manager", {})
    props = []
    for mgr in MANAGERS:
        c = fa_pm.get(mgr, {})
        tot = c.get("post_proposals", 0)
        rej = c.get("rejected_failure_related", 0)
        props.append(f"{rej}/{tot} ({rej / tot:.3f})" if tot else "0/0")
    md.append(f"| post-failure invalid proposal rate (failure-related) | {' | '.join(props)} |")
    md.append("")
    md.append("**B0 note:** B0 resolves the critical mission by ground at t=300, "
              "so the air failure never touches it (`affected_critical=false` in "
              "every run); its completion ≈482 s marginally misses the 480-s "
              "deadline in all scenarios — the frozen ground-side trade-off the "
              "air failures are measured against. B0 recovery metrics are N/A.")
    md.append("")

    # Q12-15 B2 vs B4b paired
    md.append("## 12–15. B2 vs B4b paired results (n = 320 paired)")
    md.append("")
    md.append("| metric | B2 | B4b | paired diff (B4b−B2) | p (t/Wilcoxon) | Cohen's d |")
    md.append("|---|---|---|---|---|---|")
    for key, label in [("critical_mission_completion_time_s", "completion time (s)"),
                       ("recovery_time_s", "recovery time (s)"),
                       ("failure_to_replan_latency_s", "replan latency (s)"),
                       ("existing_missions_damaged_count", "service damage")]:
        st = agg_paired.get(key) or {}
        b2c = agg.get("B2", {}).get(key, {}) or {}
        b4c = agg.get("B4b", {}).get(key, {}) or {}
        md.append(f"| {label} | {b2c.get('mean', 0):.2f} | {b4c.get('mean', 0):.2f} | "
                  f"{st.get('diff_mean', 0):.2f} | {st.get('p', 1):.4f} | {st.get('cohens_d', 0):.3f} |")
    md.append("")
    # per-scenario significant divergences
    sig = [r for r in paired if any(
        float(r.get(k)) < 0.05 for k in r if k.endswith("_holm") and r.get(k))]
    md.append("Per-scenario (n = 20, Holm-corrected):")
    md.append("")
    if sig:
        md.append("| scenario | context | B2 comp | B4b comp | comp diff | Holm p | d |")
        md.append("|---|---|---|---|---|---|---|")
        for r in sig:
            md.append(f"| {r['scenario_id']} | {r['impact_context']} | "
                      f"{float(r.get('critical_mission_completion_time_s_diff', 0)):.1f} vs | — | "
                      f"{float(r.get('critical_mission_completion_time_s_diff', 0)):.1f} | "
                      f"{r.get('critical_mission_completion_time_s_p_holm', '—')} | "
                      f"{r.get('critical_mission_completion_time_s_d', '—')} |")
    else:
        md.append("No scenario shows a statistically significant B2–B4b "
                  "divergence after Holm correction (see `paired_b2_b4b.csv`).")
    md.append("")

    # Q16-17 air vs service orientation
    b2_air = agg.get("B2", {}).get("air_intervention_rate", 0)
    b4b_air = agg.get("B4b", {}).get("air_intervention_rate", 0)
    b2_dmg = agg.get("B2", {}).get("existing_missions_damaged_count", {}).get("mean", 0)
    b4b_dmg = agg.get("B4b", {}).get("existing_missions_damaged_count", {}).get("mean", 0)
    md.append(f"## 16–17. Air usage and service preservation")
    md.append("")
    md.append(f"- Air intervention rate: B2 {b2_air:.3f} vs B4b {b4b_air:.3f}.")
    md.append(f"- Mean existing-service damage: B2 {b2_dmg:.3f} vs B4b {b4b_dmg:.3f}.")
    md.append("")

    # Q18 checker interceptions
    md.append("## 18. Checker interceptions (safety layer vs policy)")
    md.append("")
    md.append("| manager | post-failure proposals | rejected | failure-related | "
              "failed-resource reselection |")
    md.append("|---|---|---|---|---|")
    for mgr in MANAGERS:
        c = fa_pm.get(mgr, {})
        md.append(f"| {mgr} | {c.get('post_proposals', 0)} | {c.get('rejected', 0)} | "
                  f"{c.get('rejected_failure_related', 0)} | "
                  f"{c.get('failed_resource_reselection', 0)} |")
    md.append("")

    # Q19 backend
    md.append("## 19–21. Backend reliability (separate from policy)")
    md.append("")
    md.append(f"- LLM calls: {lr.get('llm_calls')}, unique response ids "
              f"{lr.get('unique_response_ids')}, repeated {lr.get('repeated_response_ids')}.")
    md.append(f"- Empty content: {lr.get('empty_content')} (structured retry "
              f"recovery per the frozen policy).")
    md.append(f"- Transport errors: {lr.get('transport_errors')} (periodic "
              f"re-decision recovery; kept in the dataset).")
    md.append(f"- Latency min/median/max: {lr.get('latency', {}).get('min')} / "
              f"{lr.get('latency', {}).get('median')} / {lr.get('latency', {}).get('max')} s.")
    md.append(f"- Cache-subsecond calls: {lr.get('cache_subsecond_calls')} "
              "(prompt KV-cache only; no response replays).")
    md.append("- Interface failures are NEVER silently substituted (no B2 "
              "fallback); every interface event is kept in the primary dataset.")
    md.append("")

    # Q22-24 conclusions
    md.append("## 22–24. Scientific conclusions (wording discipline §43)")
    md.append("")
    md.append("(Filled from the statistical analysis below.)")
    md.append("")

    # Q25 Experiment 3 gate
    md.append("## 25. Gate to Experiment 3")
    md.append("")
    acc = ROOT / "reports" / "experiment2" / "EXPERIMENT2_ACCEPTANCE_TESTS.md"
    acc_ok = acc.exists() and "NO FAIL" in acc.read_text(encoding="utf-8")
    md.append(f"- Acceptance: {'E2-T1..E2-T32 all PASS (NO FAIL)' if acc_ok else 'see acceptance table'}. "
              "Experiment 3 was not started.")

    (ROOT / "reports" / "experiment2" / "EXPERIMENT2_FINAL_RESULTS.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")
    print("report written (skeleton + core tables)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
