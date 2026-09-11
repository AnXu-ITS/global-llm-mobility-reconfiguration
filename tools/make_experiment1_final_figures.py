"""Experiment 1 Finalization figures E1-A..E1-G (Finalization §29).

Reads runs/experiment1_final and writes PNGs to reports/experiment1_final/figures/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FIG = ROOT / "reports" / "experiment1_final" / "figures"
PRIMARY = ("B0", "B1", "B2", "B4b")
COLORS = {"B0": "#7f7f7f", "B1": "#d62728", "B2": "#1f77b4", "B4b": "#2ca02c"}

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from tools.analyze_experiment1_final import enrich, load_runs  # noqa: E402


def scenario_order(rows):
    return sorted({r["_scenario"] for r in rows})


def per_scenario_mean(rows, field, manager, kind="mean"):
    out = {}
    for r in rows:
        if r["_label"] != manager:
            continue
        v = r.get(field)
        if v is None:
            continue
        out.setdefault(r["_scenario"], []).append(v)
    res = {}
    for s, vs in out.items():
        a = np.asarray(vs, dtype=float)
        if kind == "mean":
            res[s] = float(a.mean())
        elif kind == "ci":
            se = a.std(ddof=1) / np.sqrt(a.size) if a.size > 1 else 0.0
            res[s] = (float(a.mean()), float(se))
    return res


def grouped_bar(ax, scenarios, managers, means, ci, title, ylabel):
    import numpy as np
    x = np.arange(len(scenarios))
    w = 0.2
    for i, m in enumerate(managers):
        vals = [means[m].get(s, 0) for s in scenarios]
        errs = [ci[m].get(s, (0, 0))[1] * 1.96 for s in scenarios]
        ax.bar(x + (i - 1.5) * w, vals, w, yerr=errs, capsize=2,
               label=m, color=COLORS[m])
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("E1_", "") for s in scenarios], rotation=45, ha="right")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend(ncol=4, fontsize="small")


def main() -> int:
    rows = enrich(load_runs())
    scenarios = scenario_order(rows)
    FIG.mkdir(parents=True, exist_ok=True)

    # per-manager per-scenario summaries
    def means(field):
        return {m: per_scenario_mean(rows, field, m) for m in PRIMARY}
    def cis(field):
        return {m: per_scenario_mean(rows, field, m, "ci") for m in PRIMARY}

    # E1-A completion time
    fig, ax = plt.subplots(figsize=(9, 4.2))
    grouped_bar(ax, scenarios, PRIMARY, means("critical_mission_completion_time_s"),
                cis("critical_mission_completion_time_s"),
                "Critical Mission Completion Time by Manager", "completion time (s)")
    fig.tight_layout(); fig.savefig(FIG / "E1-A_completion_time.png", dpi=150); plt.close(fig)

    # E1-B deadline violation rate
    fig, ax = plt.subplots(figsize=(9, 4.2))
    grouped_bar(ax, scenarios, PRIMARY, means("critical_mission_deadline_violation"),
                cis("critical_mission_deadline_violation"),
                "Deadline Violation Rate by Manager", "violation rate")
    fig.tight_layout(); fig.savefig(FIG / "E1-B_deadline_violation.png", dpi=150); plt.close(fig)

    # E1-C existing-service damage
    fig, ax = plt.subplots(figsize=(9, 4.2))
    grouped_bar(ax, scenarios, PRIMARY, means("existing_missions_damaged_count"),
                cis("existing_missions_damaged_count"),
                "Existing-Service Damage by Manager", "mean damaged missions")
    fig.tight_layout(); fig.savefig(FIG / "E1-C_service_damage.png", dpi=150); plt.close(fig)

    # E1-D air intervention + unnecessary air
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    grouped_bar(axes[0], scenarios, PRIMARY, means("air_intervention"),
                cis("air_intervention"), "Air Intervention Rate", "rate")
    grouped_bar(axes[1], scenarios, PRIMARY, means("_unnecessary"),
                cis("_unnecessary"), "Unnecessary Air Intervention Rate", "rate")
    fig.tight_layout(); fig.savefig(FIG / "E1-D_air_intervention.png", dpi=150); plt.close(fig)

    # E1-E Pareto: damage (x) vs completion (y) for B2 and B4b
    fig, ax = plt.subplots(figsize=(6, 5))
    for m in ("B2", "B4b"):
        xs = means("existing_missions_damaged_count")[m]
        ys = means("critical_mission_completion_time_s")[m]
        ax.scatter([xs.get(s, 0) for s in scenarios],
                   [ys.get(s, 0) for s in scenarios], s=90,
                   color=COLORS[m], label=m)
    for s in scenarios:
        ax.annotate(s.replace("E1_", ""), (means("existing_missions_damaged_count")["B4b"].get(s, 0),
                                           means("critical_mission_completion_time_s")["B4b"].get(s, 0)),
                    fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("existing-service damage (mean missions)")
    ax.set_ylabel("completion time (s)")
    ax.set_title("B2 vs B4b operating trade-off (per scenario)")
    ax.legend()
    fig.tight_layout(); fig.savefig(FIG / "E1-E_B2_vs_B4b_pareto.png", dpi=150); plt.close(fig)

    # E1-F time saving vs B0
    fig, ax = plt.subplots(figsize=(9, 4.2))
    grouped_bar(ax, scenarios, PRIMARY, means("_saved_vs_b0"), cis("_saved_vs_b0"),
                "Time Saving vs B0 by Manager", "saving vs B0 (s)")
    fig.tight_layout(); fig.savefig(FIG / "E1-F_time_saving_vs_B0.png", dpi=150); plt.close(fig)

    # E1-G heatmap completion time scenario x manager
    fig, ax = plt.subplots(figsize=(7, 4))
    mat = np.array([[means("critical_mission_completion_time_s")[m].get(s, np.nan)
                     for m in PRIMARY] for s in scenarios])
    im = ax.imshow(mat, aspect="auto", cmap="viridis_r")
    ax.set_xticks(range(4)); ax.set_xticklabels(PRIMARY)
    ax.set_yticks(range(len(scenarios))); ax.set_yticklabels([s.replace("E1_", "") for s in scenarios])
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if not np.isnan(mat[i, j]):
                ax.text(j, i, f"{mat[i, j]:.0f}", ha="center", va="center",
                        color="white", fontsize=8)
    fig.colorbar(im, ax=ax, label="completion time (s)")
    ax.set_title("Completion Time Heatmap (scenario x manager)")
    fig.tight_layout(); fig.savefig(FIG / "E1-G_completion_heatmap.png", dpi=150); plt.close(fig)

    print(f"figures written to {FIG}:")
    for p in sorted(FIG.glob("*.png")):
        print(" ", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
