"""Experiment 2 — figure set E2-A .. E2-J (protocol §36).

All figures are generated ONLY from the frozen primary dataset
(outputs/experiment2/run_metrics.csv + failure traces).

  E2-A Mission Recovery Success by Failure Family x Manager
  E2-B Recovery Time by Failure Family x Manager
  E2-C Deadline Violation after Failure
  E2-D Existing Service Damage after Failure
  E2-E Candidate-Set Reduction vs Recovery Outcome
  E2-F Ground Fallback Rate by C1/C2/C3
  E2-G Post-Failure Invalid Proposal Rate
  E2-H B2 vs B4b paired recovery-time difference
  E2-I Speed / Service-Damage trade-off after failure
  E2-J Representative failure trace (E2_F1_C2 seed 20240601 B1 vs B4b)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "outputs" / "experiment2" / "figures"
FAMILIES = ("F1", "F2", "F3", "F4", "F5", "F6")
CONTEXTS = ("C1", "C2", "C3")
MANAGERS = ("B0", "B1", "B2", "B4b")
COLORS = {"B0": "#9e9e9e", "B1": "#ef8a62", "B2": "#67a9cf", "B4b": "#7a0177"}


def load():
    df = pd.read_csv(OUT.parent / "run_metrics.csv")
    df["manager_kind"] = df["manager_kind"].map({
        "no_cross_layer": "B0", "rule_based": "B1",
        "optimization": "B2", "llm_b4b": "B4b"}).fillna(df["manager_kind"])
    return df


def bar_group(ax, df, metric, agg="mean", title="", ylab="", ylim=None,
              err=None, legend=True):
    x = np.arange(len(FAMILIES))
    width = 0.19
    for i, mgr in enumerate(MANAGERS):
        vals, errs = [], []
        for fam in FAMILIES:
            sub = df[(df["failure_family"] == fam) & (df["manager_kind"] == mgr)]
            if agg == "mean":
                v = sub[metric].mean() if len(sub) else np.nan
                e = sub[metric].sem() if len(sub) else np.nan
            else:
                v = sub[metric].mean() if len(sub) else np.nan
                e = np.nan
            vals.append(v)
            errs.append(e)
        ax.bar(x + (i - 1.5) * width, vals, width, label=mgr, color=COLORS[mgr],
               yerr=errs, capsize=2)
    ax.set_xticks(x)
    ax.set_xticklabels(FAMILIES)
    ax.set_title(title)
    ax.set_ylabel(ylab)
    if ylim:
        ax.set_ylim(*ylim)
    if legend:
        ax.legend(ncol=4, fontsize=7)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load()

    # E2-A recovery success by family x manager
    fig, ax = plt.subplots(figsize=(9, 4.2))
    bar_group(ax, df, "recovery_success", title="E2-A  Mission Recovery Success by Failure Family x Manager",
              ylab="recovery success rate", ylim=(0, 1.12))
    fig.tight_layout()
    fig.savefig(OUT / "E2_A_recovery_success.png", dpi=150)
    plt.close(fig)

    # E2-B recovery time (affected runs only)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(len(FAMILIES))
    width = 0.19
    for i, mgr in enumerate(MANAGERS):
        vals, errs = [], []
        for fam in FAMILIES:
            sub = df[(df["failure_family"] == fam) & (df["manager_kind"] == mgr)
                     & (df["affected_critical"] == True)]  # noqa: E712
            v = sub["recovery_time_s"].dropna().mean() if len(sub) else np.nan
            e = sub["recovery_time_s"].dropna().sem() if len(sub) else np.nan
            vals.append(v)
            errs.append(e)
        ax.bar(x + (i - 1.5) * width, vals, width, label=mgr, color=COLORS[mgr],
               yerr=errs, capsize=2)
    ax.set_xticks(x)
    ax.set_xticklabels(FAMILIES)
    ax.set_title("E2-B  Recovery Time by Failure Family x Manager (affected runs)")
    ax.set_ylabel("recovery time (s)")
    ax.legend(ncol=4, fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "E2_B_recovery_time.png", dpi=150)
    plt.close(fig)

    # E2-C deadline violation after failure
    fig, ax = plt.subplots(figsize=(9, 4.2))
    bar_group(ax, df, "critical_mission_deadline_violation",
              title="E2-C  Deadline Violation after Failure",
              ylab="deadline violation rate", ylim=(0, 1.12))
    fig.tight_layout()
    fig.savefig(OUT / "E2_C_deadline_violation.png", dpi=150)
    plt.close(fig)

    # E2-D existing service damage
    fig, ax = plt.subplots(figsize=(9, 4.2))
    bar_group(ax, df, "existing_missions_damaged_count",
              title="E2-D  Existing Service Damage after Failure",
              ylab="mean damaged existing missions")
    fig.tight_layout()
    fig.savefig(OUT / "E2_D_service_damage.png", dpi=150)
    plt.close(fig)

    # E2-E candidate-set reduction vs recovery outcome
    fig, ax = plt.subplots(figsize=(7, 4.2))
    scen = df.groupby("scenario_id").agg(
        red=("candidate_set_reduction_delta", "first"),
        rec=("recovery_success", "mean"),
        ctx=("impact_context", "first"),
        fam=("failure_family", "first")).reset_index()
    ctx_mark = {"C1": "o", "C2": "s", "C3": "^"}
    for ctx in CONTEXTS:
        sub = scen[scen["ctx"] == ctx]
        ax.scatter(sub["red"], sub["rec"], marker=ctx_mark[ctx], s=60, label=ctx)
        for _, r in sub.iterrows():
            ax.annotate(r["fam"], (r["red"], r["rec"]), fontsize=7,
                        xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("candidate-set reduction (pre - post feasible air)")
    ax.set_ylabel("recovery success rate (all managers)")
    ax.set_title("E2-E  Candidate-Set Reduction vs Recovery Outcome")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "E2_E_reduction_vs_recovery.png", dpi=150)
    plt.close(fig)

    # E2-F ground fallback rate by context
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    x = np.arange(len(CONTEXTS))
    width = 0.19
    for i, mgr in enumerate(MANAGERS):
        vals = [df[(df["impact_context"] == c) & (df["manager_kind"] == mgr)]
                ["ground_fallback_rate"].mean() for c in CONTEXTS]
        ax.bar(x + (i - 1.5) * width, vals, width, label=mgr, color=COLORS[mgr])
    ax.set_xticks(x)
    ax.set_xticklabels(CONTEXTS)
    ax.set_ylim(0, 1.12)
    ax.set_title("E2-F  Ground Fallback Rate by Impact Context")
    ax.set_ylabel("ground fallback rate")
    ax.legend(ncol=4, fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "E2_F_ground_fallback.png", dpi=150)
    plt.close(fig)

    # E2-G post-failure invalid proposal rate
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    vals = []
    for mgr in MANAGERS:
        sub = df[df["manager_kind"] == mgr]
        tot = sub["post_failure_proposals"].sum()
        rej = sub["post_failure_rejected_failure_related"].sum()
        vals.append(rej / tot if tot else 0.0)
    ax.bar(list(MANAGERS), vals, color=[COLORS[m] for m in MANAGERS])
    ax.set_title("E2-G  Post-Failure Invalid Proposal Rate (failure-related)")
    ax.set_ylabel("failure-related rejected / post-failure proposals")
    fig.tight_layout()
    fig.savefig(OUT / "E2_G_invalid_proposals.png", dpi=150)
    plt.close(fig)

    # E2-H B2 vs B4b paired recovery-time difference
    fig, ax = plt.subplots(figsize=(9, 4.2))
    rows = []
    for sid in df["scenario_id"].unique():
        sub = df[df["scenario_id"] == sid]
        b2 = sub[sub["manager_kind"] == "B2"].sort_values("seed")
        b4b = sub[sub["manager_kind"] == "B4b"].sort_values("seed")
        diffs = [x - y for x, y in zip(b4b["recovery_time_s"], b2["recovery_time_s"])
                 if pd.notna(x) and pd.notna(y)]
        if diffs:
            rows.append((sid, sub["failure_family"].iloc[0], np.mean(diffs),
                         np.std(diffs) / np.sqrt(len(diffs))))
    rows.sort(key=lambda r: r[1])
    labels = [f"{r[0]}" for r in rows]
    x = np.arange(len(rows))
    ax.bar(x, [r[2] for r in rows], yerr=[r[3] for r in rows], capsize=2,
           color=[COLORS["B4b"] if r[2] < 0 else COLORS["B2"] for r in rows])
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=6)
    ax.set_title("E2-H  B4b - B2 paired recovery-time difference (per scenario)")
    ax.set_ylabel("recovery time difference (s); <0 = B4b faster")
    fig.tight_layout()
    fig.savefig(OUT / "E2_H_paired_recovery_diff.png", dpi=150)
    plt.close(fig)

    # E2-I speed vs service-damage trade-off after failure
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    for mgr in MANAGERS:
        sub = df[df["manager_kind"] == mgr]
        ax.scatter(sub["critical_mission_completion_time_s"],
                   sub["existing_missions_damaged_count"],
                   label=mgr, color=COLORS[mgr], alpha=0.25, s=12)
        ax.scatter([sub["critical_mission_completion_time_s"].mean()],
                   [sub["existing_missions_damaged_count"].mean()],
                   marker="X", s=160, color=COLORS[mgr], edgecolor="black")
    ax.set_xlabel("critical mission completion time (s)")
    ax.set_ylabel("existing service damage (missions)")
    ax.set_title("E2-I  Speed / Service-Damage trade-off after failure")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "E2_I_speed_damage.png", dpi=150)
    plt.close(fig)

    # E2-J representative failure trace (E2_F1_C2, seed 20240601, B2 vs B4b)
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True)
    for axx, mgr in zip(axes, ("B2", "B4b")):
        rd = ROOT / "runs" / "experiment2" / "E2_F1_C2" / "seed20240601" / mgr
        tr = json.loads((rd / "failure_trace.json").read_text(encoding="utf-8"))
        axx.axvspan(0, 300, color="#eeeeee")
        axx.axvspan(360, 900, color="#fff3cd", alpha=0.6)
        axx.axvline(300, color="gray", ls="--", lw=0.8)
        axx.axvline(360, color="red", lw=1.4)
        axx.axvline(480, color="purple", ls=":", lw=1.2)
        import csv
        with open(rd / "events.csv", newline="") as f:
            evs = list(csv.DictReader(f))
        comp = next((e for e in evs if e["event_id"] in
                     ("MISSION_COMPLETED", "GROUND_FALLBACK_COMPLETED")), None)
        axx.plot([360, int(comp["t"])], [1, 1], lw=6, color=COLORS[mgr], alpha=0.7)
        axx.text(360, 0.5, "failure (C2 lost on M-UAV-02)", rotation=90,
                 va="center", ha="right", fontsize=8, color="red")
        axx.text(480, 0.5, "deadline 480 s", rotation=90, va="center",
                 ha="right", fontsize=8, color="purple")
        axx.set_ylabel(f"{mgr}\nmode", fontsize=9)
        axx.set_yticks([])
        axx.set_title(f"E2-J  E2_F1_C2 seed 20240601 — {mgr} trace" if mgr == "B2"
                      else f"{mgr} trace")
    axes[1].set_xlabel("simulation time (s)")
    fig.tight_layout()
    fig.savefig(OUT / "E2_J_trace.png", dpi=150)
    plt.close(fig)

    print(f"figures written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
