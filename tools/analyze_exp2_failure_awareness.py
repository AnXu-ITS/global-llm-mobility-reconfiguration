"""Experiment 2 — Failure Awareness & Safety-Layer Value analysis (§38/§39).

Distinguishes POLICY reliability from SYSTEM safety:
  - post-failure invalid proposals per manager (checker/semantic rejections),
  - failed-resource reselection per manager,
  - first-decision failure-awareness (avoid failed aircraft / unavailable site /
    prohibited route / recognise no-air condition / switch fallback),
  - checker interception counts (proposals the safety layer stopped).

Artifact: outputs/experiment2/failure_awareness.json
Report:   reports/experiment2/FAILURE_AWARENESS_ANALYSIS.md
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MANAGERS = ("B0", "B1", "B2", "B4b")
KIND = {"B0": "no_cross_layer", "B1": "rule_based",
        "B2": "optimization", "B4b": "llm_b4b"}
KIND2LABEL = {v: k for k, v in KIND.items()}

FAILURE_SUBSTR = (
    "AIRCRAFT_IN_CONTINGENCY", "AIRCRAFT_NOT_COMMANDABLE", "AIRCRAFT_UNAVAILABLE",
    "GNSS_DEGRADED_AIRCRAFT", "AIRCRAFT_DEGRADED", "UTM_AIR_PROHIBITED",
    "RISK_ZONE_VIOLATION", "SITE_UNAVAILABLE", "_UNAVAILABLE",
    "C2 status", "not commandable", "aircraft CONTINGENCY", "aircraft DEGRADED",
)


def read_jsonl(p: Path):
    out = []
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def main() -> int:
    with open(ROOT / "config" / "experiment2_matrix.yaml", encoding="utf-8") as f:
        e2 = yaml.safe_load(f)["experiment2"]
    with open(ROOT / "config" / "experiment2_seeds.yaml", encoding="utf-8") as f:
        seeds = list(yaml.safe_load(f)["primary_seeds"])

    per_mgr = {m: {"runs": 0, "post_proposals": 0, "rejected": 0,
                   "rejected_failure_related": 0, "failed_resource_reselection": 0,
                   "first_decision_targets_failed_resource": 0,
                   "no_air_correct_fallback": 0, "no_air_total": 0,
                   "checker_interceptions": 0}
               for m in MANAGERS}
    per_family = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for s in e2["scenarios"]:
        sid, fam = s["id"], s["failure_family"]
        failed_target = (s["failure"].get("target")
                         or s["failure"].get("site")
                         or s["failure"].get("utm_state") or "UNKN-01")
        for seed in seeds:
            for mgr in MANAGERS:
                rd = ROOT / "runs" / "experiment2" / sid / f"seed{seed}" / mgr
                mp = rd / "metrics.json"
                if not mp.exists():
                    continue
                m = json.loads(mp.read_text(encoding="utf-8"))
                k = KIND2LABEL.get(m.get("manager_kind"), m.get("manager_kind"))
                cell = per_mgr[k]
                cell["runs"] += 1
                cell["post_proposals"] += m.get("post_failure_proposals", 0)
                cell["rejected"] += m.get("post_failure_rejected", 0)
                cell["rejected_failure_related"] += m.get(
                    "post_failure_rejected_failure_related", 0)
                cell["failed_resource_reselection"] += m.get(
                    "failed_resource_reselection", 0)
                if m.get("post_failure_rejected", 0) > 0:
                    cell["checker_interceptions"] += 1

                # first post-failure decision awareness (AIR actions only —
                # a GROUND_FALLBACK's target_site is the mission destination,
                # not a reselection of the failed resource)
                pipeline = read_jsonl(rd / "action_pipeline.jsonl")
                post = [p for p in pipeline if int(p.get("t") or 0) >= 360]
                if post:
                    first_raw = post[0].get("raw_action") or {}
                    if first_raw.get("type") not in ("GROUND_FALLBACK", "DELAY",
                                                     "CANCEL", "NO_ACTION",
                                                     "ESCALATE", None):
                        if (first_raw.get("aircraft_id") == failed_target
                                or first_raw.get("target_site") == failed_target):
                            cell["first_decision_targets_failed_resource"] += 1
                            per_family[fam][mgr]["first_decision_targets_failed"] += 1

                # no-air condition -> correct fallback
                if m.get("necessary_ground_fallback"):
                    cell["no_air_total"] += 1
                    per_family[fam][mgr]["no_air_total"] += 1
                    if m.get("necessary_ground_fallback_correct"):
                        cell["no_air_correct_fallback"] += 1
                        per_family[fam][mgr]["no_air_correct"] += 1

    out = {"per_manager": per_mgr,
           "per_family": {f: {m: dict(v) for m, v in d.items()}
                          for f, d in per_family.items()}}
    out_dir = ROOT / "outputs" / "experiment2"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "failure_awareness.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    # report
    md = ["# Experiment 2 — Failure Awareness & Safety-Layer Value (protocol §38/§39)",
          "",
          "Policy reliability (manager behaviour) is reported separately from "
          "system safety (checker interceptions). A checker rejection is "
          "recorded, never repaired; a mission that completes AFTER a rejected "
          "proposal shows the SAFETY LAYER working — not the manager.",
          "",
          "## Per-manager post-failure proposal behaviour (primary runs)",
          "",
          "| manager | runs | post-fail proposals | rejected | rejected failure-related | failed-resource reselection | first decision hits failed resource | runs w/ ≥1 interception |",
          "|---|---|---|---|---|---|---|---|"]
    for mgr in MANAGERS:
        c = per_mgr[mgr]
        md.append(f"| {mgr} | {c['runs']} | {c['post_proposals']} | {c['rejected']} | "
                  f"{c['rejected_failure_related']} | {c['failed_resource_reselection']} | "
                  f"{c['first_decision_targets_failed_resource']} | {c['checker_interceptions']} |")
    md.append("")
    md.append("## No-air condition handling (necessary ground fallback)")
    md.append("")
    md.append("| manager | no-air runs | correct ground fallback |")
    md.append("|---|---|---|")
    for mgr in MANAGERS:
        c = per_mgr[mgr]
        md.append(f"| {mgr} | {c['no_air_total']} | {c['no_air_correct_fallback']} |")
    md.append("")
    md.append("## By failure family")
    md.append("")
    md.append("| family | manager | first decision hits failed resource | no-air correct/total |")
    md.append("|---|---|---|---|")
    for fam in ("F1", "F2", "F3", "F4", "F5", "F6"):
        for mgr in MANAGERS:
            c = per_family[fam][mgr]
            md.append(f"| {fam} | {mgr} | {c.get('first_decision_targets_failed', 0)} | "
                      f"{c.get('no_air_correct', 0)}/{c.get('no_air_total', 0)} |")
    md.append("")
    md.append("## Interpretation rules")
    md.append("")
    md.append("- **System safety** = 0 infeasible EXECUTED actions (every run is "
              "verified via action_pipeline.jsonl: raw == normalized == executed).")
    md.append("- **Manager failure-awareness** = proposal-level behaviour above: "
              "invalid proposals, reselection of the just-failed resource, and "
              "no-air fallback correctness are POLICY properties, credited to "
              "the manager — never to the checker.")
    (ROOT / "reports" / "experiment2" / "FAILURE_AWARENESS_ANALYSIS.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(per_mgr, indent=2))
    print("report: reports/experiment2/FAILURE_AWARENESS_ANALYSIS.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
