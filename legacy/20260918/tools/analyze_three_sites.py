"""Three-site Experiment-1 comparison (Site A frozen + Site B + Site C).

Reads the per-site primary_analysis.json files produced by
analyze_experiment1_final.py and writes a unified three-site table:

  outputs/cross_site/three_site_comparison.csv
  reports/cross_site/THREE_SITE_COMPARISON.md

All three sites now share the SAME experimental scale (12 scenarios x 20 seeds
x 4 managers = 960 primary + 60 B4a ablation per site).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
SITES = {
    "site_a_suzhou": ROOT / "outputs" / "experiment1_final" / "primary_analysis.json",
    "site_b_amsterdam": ROOT / "outputs" / "site_b_amsterdam" / "primary_analysis.json",
    "site_c_edmonton": ROOT / "outputs" / "site_c_edmonton" / "primary_analysis.json",
}
MANAGERS = ("B0", "B1", "B2", "B4b")
OUT = ROOT / "outputs" / "cross_site"
REPORT_DIR = ROOT / "reports" / "cross_site"

SITE_META = {
    "site_a_suzhou": ("Suzhou, China", "meshed / mixed urban (single-link bottleneck)"),
    "site_b_amsterdam": ("Amsterdam, NL", "water-barrier / bridge-constrained"),
    "site_c_edmonton": ("Edmonton, CA", "sparse suburban / polycentric"),
}


def main() -> int:
    data: Dict[str, Any] = {}
    for sid, p in SITES.items():
        if not p.exists():
            print(f"SKIP {sid}: {p} missing")
            continue
        data[sid] = json.loads(p.read_text(encoding="utf-8"))["summary"]

    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for sid in SITES:
        if sid not in data:
            continue
        for m in MANAGERS:
            s = data[sid][m]
            rows.append({
                "site_id": sid,
                "manager": m,
                "n_runs": s["n_runs"],
                "comp_mean_s": s["completion_time_s"]["mean"],
                "comp_ci_lo": s["completion_time_s"]["ci95"][0],
                "comp_ci_hi": s["completion_time_s"]["ci95"][1],
                "deadline_violation_rate": s["deadline_violation_rate"]["rate"],
                "damage_mean": s["existing_service_damage"]["mean"],
                "air_rate": s["air_intervention_rate"]["rate"],
                "unnecessary_air_rate": s["unnecessary_air_rate"]["rate"],
                "ground_rate": s["ground_fallback_rate"]["rate"],
                "saved_vs_b0_s": s["time_saving_vs_b0_s"]["mean"],
                "disruption_efficiency": s["disruption_efficiency"]["mean"],
            })
    csv_path = OUT / "three_site_comparison.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    lines = [
        "# THREE-SITE EXPERIMENT-1 COMPARISON (same scale)",
        "",
        "All three sites share the SAME experimental scale: 12 scenarios x",
        "20 frozen seeds x 4 managers = 960 primary runs + 60 B4a ablation runs",
        "per site. Statistical unit = scenario x seed (n=20 per scenario).",
        "",
        "| site (morphology) | manager | comp (95% CI) | viol | damage | air | unnec | saved vs B0 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for sid in SITES:
        if sid not in data:
            continue
        city, morph = SITE_META[sid]
        lines.append(f"| **{sid}** — {city}, {morph} | | | | | | | |")
        for m in MANAGERS:
            s = data[sid][m]
            c = s["completion_time_s"]
            lines.append(
                f"| | {m} | {c['mean']} [{c['ci95'][0]}, {c['ci95'][1]}] "
                f"| {s['deadline_violation_rate']['rate']} "
                f"| {s['existing_service_damage']['mean']} "
                f"| {s['air_intervention_rate']['rate']} "
                f"| {s['unnecessary_air_rate']['rate']} "
                f"| {s['time_saving_vs_b0_s']['mean']} |")
    lines += [
        "",
        "## Reading notes",
        "",
        "- Site A = frozen primary (`runs/experiment1_final`); Sites B/C =",
        "  cross-site reproduction at identical scale",
        "  (`runs/experiment1_cross_site/<site_id>/`).",
        "- Severity magnitudes differ per site by design (Amsterdam +88.69 %",
        "  water-barrier penalty vs Suzhou +73.41 % vs Edmonton +34.76 %); the",
        "  factor STRUCTURE (LOW/MEDIUM/HIGH x CRITICAL/HIGH x low/high workload)",
        "  is identical.",
        f"- Machine-readable: `{csv_path.relative_to(ROOT)}`",
    ]
    (REPORT_DIR / "THREE_SITE_COMPARISON.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {csv_path.relative_to(ROOT)}")
    print(f"wrote {REPORT_DIR.relative_to(ROOT) / 'THREE_SITE_COMPARISON.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
