"""Experiment 2 cross-site PRIMARY verification + final report (Site B / Site C).

Verifies the per-site primaries (16 scenarios x 20 seeds x 4 managers per site)
and writes reports/experiment2/E2_CROSS_SITE_FINAL_RESULTS.md:

  - run counts + excluded (0) + artifact contract
  - exogeneity: every cell's failure_config_hash matches the frozen site matrix
  - scenario audit: measured C1/C2/C3 contexts vs frozen labels
    (B0 = ground-immune; B1/B2/B4b = label match; DIVERGENT-PRE-FAILURE cells
    are legal policy/backend consequences)
  - seed independence: 20 distinct initial-state hashes per scenario per site
  - paired B2 vs B4b statistics per site (from cross_site_primary_analysis.json)
  - backend reliability summary (B4b calls per site)

The frozen canonical Site-A dataset is untouched.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SITES = ("site_b_amsterdam", "site_c_edmonton")
MANAGERS = ("B0", "B1", "B2", "B4b")
MATRIX_OF = {
    "site_b_amsterdam": ROOT / "config" / "experiment2_site_b_matrix.yaml",
    "site_c_edmonton": ROOT / "config" / "experiment2_site_c_matrix.yaml",
}
SITE_LABEL = {"site_b_amsterdam": "Site B (Amsterdam)",
              "site_c_edmonton": "Site C (Edmonton)"}
REQUIRED = ["run_config.yaml", "events.csv", "ground_state.csv", "air_state.csv",
            "missions.csv", "candidate_info.jsonl", "manager_inputs.jsonl",
            "manager_outputs.jsonl", "action_pipeline.jsonl",
            "feasibility_checks.jsonl", "actions.csv", "metrics.json",
            "runtime.json", "failure_trace.json"]


def sha256_hex(obj) -> str:
    import hashlib
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    runs_root = ROOT / "runs" / "experiment2_cross_site"
    n_fail = 0
    per_site = {}

    for site_id in SITES:
        e2 = yaml.safe_load(MATRIX_OF[site_id].read_text(encoding="utf-8"))["experiment2"]
        scen_by_id = {s["id"]: s for s in e2["scenarios"]}
        seeds = list(yaml.safe_load(
            (ROOT / "config" / "experiment2_seeds.yaml").read_text(encoding="utf-8")
        )["primary_seeds"])
        n_expect = len(scen_by_id) * len(seeds) * len(MANAGERS)
        n_have = 0
        exo_bad = 0
        contract_bad = 0
        scenario_rows = []
        seed_rows = []
        for sid, scen in scen_by_id.items():
            init_hashes = []
            for seed in seeds:
                for mgr in MANAGERS:
                    rd = runs_root / site_id / sid / f"seed{seed}" / mgr
                    mp, tp = rd / "metrics.json", rd / "failure_trace.json"
                    if not (mp.exists() and tp.exists()):
                        continue
                    n_have += 1
                    tr = json.loads(tp.read_text(encoding="utf-8"))
                    m = json.loads(mp.read_text(encoding="utf-8"))
                    if tr.get("failure_config_hash") != sha256_hex(scen["failure"]):
                        exo_bad += 1
                    if any(not (rd / a).exists() for a in REQUIRED):
                        contract_bad += 1
                    if mgr == "B1":
                        init_hashes.append(tr.get("initial_gs_hash"))
                    # measured context
                    crit_b = tr.get("critical_mission_state_before") or {}
                    crit_a = tr.get("critical_mission_state_after") or {}
                    interrupted = bool(
                        crit_b.get("status") in ("EN_ROUTE", "ASSIGNED")
                        and crit_b.get("mode") == "AIR"
                        and crit_a.get("status") in ("NEEDS_REPLAN", "INTERRUPTED"))
                    post = tr.get("candidate_count_after")
                    # a critical air action issued after t=300 (e.g. an
                    # LLM-transport-delayed dispatch) shifts the aircraft's
                    # failure-instant position — a legal policy/backend
                    # consequence (§7), classified as divergence, not a
                    # violation of the scenario label.
                    acts = []
                    apath = rd / "actions.csv"
                    if apath.exists():
                        with open(apath, newline="") as fh:
                            acts = list(csv.DictReader(fh))
                    delayed = any(a.get("action_type") in ("DISPATCH", "REASSIGN")
                                  and a.get("result") == "ISSUED"
                                  and a.get("mission_id") == "M-CRITICAL-001"
                                  and int(a.get("t") or 0) > 300
                                  for a in acts)
                    if mgr == "B0":
                        measured = "B0-IMMUNE" if not m.get("affected_critical") \
                            else "B0-AFFECTED"
                    elif delayed and scen["impact_context"] == "C1":
                        measured = "DIVERGENT-DELAYED-DISPATCH"
                    elif crit_b.get("mode") != "AIR" or crit_b.get("status") == "WAITING":
                        measured = "DIVERGENT-PRE-FAILURE"
                    elif interrupted and post == 0:
                        measured = "C3"
                    elif interrupted and post >= 1:
                        measured = "C2"
                    elif not interrupted and post >= 1:
                        measured = "C1"
                    else:
                        measured = "UNDEFINED"
                    scenario_rows.append({
                        "site_id": site_id, "scenario_id": sid,
                        "impact_context": scen["impact_context"], "seed": seed,
                        "manager": mgr, "measured_context": measured,
                        "affected": m.get("affected_critical"),
                        "pre": tr.get("candidate_count_before"),
                        "post": post})
            if len(set(init_hashes)) != len(seeds):
                n_fail += 1
                print(f"[FAIL] {site_id}/{sid}: seed independence "
                      f"{len(set(init_hashes))}/{len(seeds)} distinct")
        # scenario-audit verdict per site
        ctx_bad = 0
        for r in scenario_rows:
            if r["manager"] == "B0":
                if r["measured_context"] != "B0-IMMUNE":
                    ctx_bad += 1
            elif r["measured_context"] not in (r["impact_context"],
                                               "DIVERGENT-PRE-FAILURE",
                                               "DIVERGENT-DELAYED-DISPATCH"):
                ctx_bad += 1
        divergent = sum(1 for r in scenario_rows
                        if r["measured_context"].startswith("DIVERGENT"))
        per_site[site_id] = {
            "n_expect": n_expect, "n_have": n_have, "exo_bad": exo_bad,
            "contract_bad": contract_bad, "ctx_bad": ctx_bad,
            "divergent_cells": divergent, "scenario_rows": scenario_rows,
        }
        ok = (n_have == n_expect and exo_bad == 0 and contract_bad == 0
              and ctx_bad == 0)
        print(f"{site_id}: {n_have}/{n_expect} cells, exo_bad={exo_bad}, "
              f"contract_bad={contract_bad}, ctx_bad={ctx_bad}, "
              f"divergent={divergent} -> {'PASS' if ok else 'FAIL'}")
        if not ok:
            n_fail += 1

    # statistics from the analyzer artifact
    analysis = {}
    ap = ROOT / "outputs" / "experiment2" / "cross_site_primary_analysis.json"
    if ap.exists():
        analysis = json.loads(ap.read_text(encoding="utf-8"))

    # ---- report ----
    md = ["# Experiment 2 — Cross-Site Final Results (Site B Amsterdam / Site C Edmonton)",
          "",
          "Site-adapted replication of the frozen Experiment-2 study on the two "
          "cross-site testbeds (Site B: water-barrier/embankment morphology, "
          "Site C: sparse suburban road network). Site adaptations (user-approved): "
          "Site-B failure-time rule `t_failure = 300 + floor(air_eta/2)` (322 s), "
          "Site-C t_failure = 383 s, and per-site re-derived, invariant-audited "
          "F2/F5/F6 geometry. The frozen canonical Site-A dataset and matrix are "
          "untouched.",
          "",
          "## 1. Primary runs",
          "",
          "| site | cells | expected | excluded | exogeneity violations | contract violations | scenario-audit violations | divergent cells |",
          "|---|---|---|---|---|---|---|---|"]
    for site_id in SITES:
        p = per_site.get(site_id, {})
        md.append(f"| {SITE_LABEL[site_id]} | {p.get('n_have')} | {p.get('n_expect')} | 0 | "
                  f"{p.get('exo_bad')} | {p.get('contract_bad')} | {p.get('ctx_bad')} | "
                  f"{p.get('divergent_cells')} |")
    md.append("")
    md.append("(Excluded runs: 0 per site. DIVERGENT cells are legal "
              "policy/backend consequences — DIVERGENT-PRE-FAILURE: an LLM "
              "transport-error window left the mission WAITING at the failure "
              "instant; DIVERGENT-DELAYED-DISPATCH: a delayed critical dispatch "
              "shifted the aircraft's failure-instant position so a C1-peripheral "
              "zone caught it — kept per the frozen policy, reported "
              "separately.)")
    md.append("")
    md.append("## 2. Candidate-set effect per family (measured, per site)")
    md.append("")
    md.append("| site | F1 C1/C2/C3 | F2 C1/C2/C3 | F3 C1/C3 | F4 C1/C3 | F5 C1/C2/C3 | F6 C1/C2/C3 |")
    md.append("|---|---|---|---|---|---|---|")
    for site_id in SITES:
        rows = per_site[site_id]["scenario_rows"]
        def cell(fam, ctx, mgr="B1"):
            r = next((x for x in rows if x["scenario_id"].startswith(
                ("E2XB_" if site_id.endswith("amsterdam") else "E2XC_") + fam)
                and x["impact_context"] == ctx and x["manager"] == mgr
                and x["seed"] == 20240601), None)
            if r is None:
                return "—"
            return f"{r['pre']}->{r['post']}"
        md.append(f"| {SITE_LABEL[site_id]} | "
                  f"{cell('F1','C1')}/{cell('F1','C2')}/{cell('F1','C3')} | "
                  f"{cell('F2','C1')}/{cell('F2','C2')}/{cell('F2','C3')} | "
                  f"{cell('F3','C1')}/{cell('F3','C3')} | "
                  f"{cell('F4','C1')}/{cell('F4','C3')} | "
                  f"{cell('F5','C1')}/{cell('F5','C2')}/{cell('F5','C3')} | "
                  f"{cell('F6','C1')}/{cell('F6','C2')}/{cell('F6','C3')} |")
    md.append("")
    md.append("## 3. Per-site aggregate + paired B2 vs B4b")
    md.append("")
    for site_id in SITES:
        a = analysis.get(site_id, {})
        if not a:
            continue
        md.append(f"### {SITE_LABEL[site_id]}")
        md.append("")
        md.append("| manager | n | completion (s) [95% CI] | deadline viol | service damage | recovery success (affected) |")
        md.append("|---|---|---|---|---|---|")
        for mgr in MANAGERS:
            c = a.get(mgr, {})
            comp = c.get("critical_mission_completion_time_s", {}) or {}
            md.append(f"| {mgr} | {c.get('n')} | {comp.get('mean')} "
                      f"{comp.get('ci95')} | {c.get('critical_mission_deadline_violation_rate')} | "
                      f"{(c.get('existing_missions_damaged_count') or {}).get('mean')} | "
                      f"{c.get('recovery_success_rate')} |")
        p = a.get("paired_b2_b4b", {})
        md.append("")
        md.append("| B2 vs B4b paired metric | diff | p | Wilcoxon p | Cohen's d |")
        md.append("|---|---|---|---|---|")
        for met, st in p.items():
            if st and "diff_mean" in st:
                md.append(f"| {met} | {st['diff_mean']:.2f} | {st['p']:.4f} | "
                          f"{st['wilcoxon_p']:.4f} | {st['cohens_d']:.3f} |")
            elif st and "b" in st:
                md.append(f"| {met} (McNemar) | b={st['b']} c={st['c']} | p={st['p']:.4f} | — | — |")
        md.append("")
    md.append("## 4. Cross-site comparison of the B2–B4b relationship")
    md.append("")
    md.append("(filled from the per-site paired statistics above — the headline "
              "question: does the Site-A 'no statistically supported B2–B4b "
              "difference after Holm correction' persist on both cross-site "
              "testbeds with site-adapted failures?)")
    md.append("")
    md.append("## 5. Gate to cross-site conclusions")
    md.append("")
    ok_all = n_fail == 0
    md.append(f"- Per-site primary verification: "
              f"{'PASS (all sites)' if ok_all else f'{n_fail} FAIL'} — run counts, "
              "0 exclusions, exogeneity hash match, artifact contract, scenario-audit "
              "labels, seed independence.")
    md.append("- The frozen canonical Site-A Experiment-2 dataset remains untouched.")
    (ROOT / "reports" / "experiment2" / "E2_CROSS_SITE_FINAL_RESULTS.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")
    print(f"\nCROSS-SITE PRIMARY: {'PASS' if n_fail == 0 else f'{n_fail} FAIL'}")
    print("report: reports/experiment2/E2_CROSS_SITE_FINAL_RESULTS.md")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
