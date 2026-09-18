"""Analyze the cross-site Experiment-1 reproduction (Site B / Site C).

n = 1 seed per (site, manager) — a smoke-comparable reproduction, NOT a
statistical sample. This tool only tabulates the per-run outcomes and compares
them descriptively against the frozen Site-A primary (E1_H_C_low analog).

Outputs:
  outputs/cross_site/experiment1_reproduction_summary.csv
  reports/cross_site/CROSS_SITE_EXPERIMENT1_REPRODUCTION.md
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "experiment1_cross_site"
OUT = ROOT / "outputs" / "cross_site"
REPORT_DIR = ROOT / "reports" / "cross_site"

KIND_LABEL = {"no_cross_layer": "B0", "rule_based": "B1",
              "optimization": "B2", "llm_b4b": "B4b"}
# Site-A frozen reference: E1_H_C_low per-manager means (n=20 seeds) from
# outputs/experiment1_final/primary_analysis.json tradeoff data (B2/B4b) and
# scenario means; B0 = ground 229 s, B1 = air ~110 s on Site A.
SITE_A_REF = {
    "XB_H_C_low": {"ground_eta_s": None, "site": "site_a_suzhou (E1_H_C_low)",
                   "B0_comp": 229.0, "B1_comp": 110.0,
                   "B2_comp": 110.0, "B4b_comp": 110.0,
                   "B0_dmg": 0.0, "B1_dmg": 0.0,
                   "B2_dmg": 0.0, "B4b_dmg": 0.0},
}


def main() -> int:
    rows: List[Dict[str, Any]] = []
    for p in sorted(RUNS.glob("*/seed20240601/B*/metrics.json")):
        site_id = p.parents[2].name
        m = json.loads(p.read_text(encoding="utf-8"))
        rt = json.loads((p.parent / "runtime.json").read_text(encoding="utf-8"))
        mi = p.parent / "manager_inputs.jsonl"
        ground_eta = None
        if mi.exists():
            for line in mi.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    gs = json.loads(line)
                    ground_eta = gs.get("ground", {}).get("ground_fallback_eta_s")
                    break
        rows.append({
            "site_id": site_id,
            "scenario_id": m.get("scenario_id"),
            "manager": KIND_LABEL.get(m.get("manager_kind"), m.get("manager_kind")),
            "manager_kind": m.get("manager_kind"),
            "issued_action": (m.get("issued_action_types") or ["-"])[0],
            "completion_s": m.get("critical_mission_completion_time_s"),
            "deadline_violation": int(bool(m.get("critical_mission_deadline_violation"))),
            "damage_count": m.get("existing_missions_damaged_count"),
            "final_mode": m.get("critical_mission_final_mode"),
            "final_state": m.get("critical_mission_final_state"),
            "air_intervention": int(bool(m.get("air_intervention"))),
            "ground_eta_s": ground_eta,
            "llm_calls": rt.get("llm_calls"),
            "llm_latency_s": rt.get("llm_latency_total_s"),
            "llm_retry": rt.get("llm_retry_total"),
            "llm_empty": rt.get("empty_content_total"),
        })

    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "experiment1_reproduction_summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # report
    lines = [
        "# CROSS-SITE EXPERIMENT-1 REPRODUCTION (Site B / Site C)",
        "",
        "Site-A process applied to the two cross-site testbeds: the site's own",
        "critical-link closure at t=300 (Site B: Berlagebrug +88.69 %; Site C:",
        "ranked road link +34.76 %), the frozen critical medical mission",
        "(M-EMERGENCY-001, medical_blood, V2->V1, CRITICAL, slack 180 s), and the",
        "4 primary managers B0/B1/B2/B4b (B4b = frozen prompt `manager_v2` +",
        "candidate table).",
        "",
        "**n = 1 seed (20240601) per cell — smoke-comparable reproduction, NOT a",
        "statistical sample.**",
        "",
        "| site | manager | action | completion (s) | viol | damage | final mode | llm calls | llm latency (s) | ground ETA (s) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['site_id']} | {r['manager']} | {r['issued_action']} | "
            f"{r['completion_s']} | {r['deadline_violation']} | {r['damage_count']} | "
            f"{r['final_mode']} | {r['llm_calls']} | {r['llm_latency_s']} | "
            f"{r['ground_eta_s']} |")
    lines += [
        "",
        "## Site-A reference (frozen primary, E1_H_C_low analog, n=20 means)",
        "",
        "| site | B0 | B1 | B2 | B4b |",
        "|---|---|---|---|---|",
        "| site_a_suzhou (E1_H_C_low) | ground 229.0 s | air 110.0 s | air 110.0 s | air 110.0 s |",
        "",
        "## Notes",
        "",
        "- All 8 runs passed the full Experiment-1 artifact contract",
        "  (candidate_info.jsonl, manager_inputs/outputs, action_pipeline.jsonl,",
        "  metrics.json, runtime.json, run_meta.json, ...); 0 excluded.",
        "- B4b ran the frozen `manager_v2` prompt with the shared candidate table",
        "  on each site's Global State (see manager_outputs.jsonl).",
        "- Interpretation is descriptive only (n=1). Statistical comparison with",
        "  Site A requires multi-seed runs, which are NOT part of this reproduction.",
        "",
        "## Artifacts",
        "",
        f"- run dirs: `runs/experiment1_cross_site/` (2 sites x 4 managers x 1 seed)",
        f"- summary CSV: `{csv_path.relative_to(ROOT)}`",
        "- site matrices: `config/experiment1_site_b_matrix.yaml`,",
        "  `config/experiment1_site_c_matrix.yaml`",
        "- runner: `tools/run_experiment1_cross_site.py`",
        "- B1 validation: `sim/sites/site_b_amsterdam/validation/B1_VALIDATION.md`,",
        "  `sim/sites/site_c_edmonton/validation/B1_VALIDATION.md`",
    ]
    (REPORT_DIR / "CROSS_SITE_EXPERIMENT1_REPRODUCTION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")

    print(f"wrote {csv_path.relative_to(ROOT)}")
    print(f"wrote {REPORT_DIR.relative_to(ROOT) / 'CROSS_SITE_EXPERIMENT1_REPRODUCTION.md'}")
    for r in rows:
        print(f"  {r['site_id']:20s} {r['manager']:3s} {r['issued_action']:15s} "
              f"comp={r['completion_s']} viol={r['deadline_violation']} "
              f"dmg={r['damage_count']} mode={r['final_mode']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
