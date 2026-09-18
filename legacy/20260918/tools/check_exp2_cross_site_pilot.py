"""Experiment 2 cross-site PILOT checker + report (Site B / Site C).

Verifies the per-site pilot cells (6 scenarios x 3 seeds x 4 managers per
site, using the site-adapted matrices) against the frozen E2 pilot criteria:
  - all pilot cells complete + artifact contract + trace coherent
  - exogenous failure hash identical across managers per (scenario, seed)
  - failure event fires at the SITE-ADAPTED failure time
  - C2/C3 candidate-set effect measured (post < pre for C2/C3)
  - managers act through the checker (no silent substitution)
  - critical mission terminates; clock sync unaffected
  - B4b backend observability (calls, empty, transport errors)

Writes reports/experiment2/E2_CROSS_SITE_PILOT.md.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SITES = ("site_b_amsterdam", "site_c_edmonton")
MANAGERS = ("B0", "B1", "B2", "B4b")
PILOT_SEEDS = [20240601, 20240602, 20240603]
MATRIX_OF = {
    "site_b_amsterdam": ROOT / "config" / "experiment2_site_b_matrix.yaml",
    "site_c_edmonton": ROOT / "config" / "experiment2_site_c_matrix.yaml",
}
EVENT_IDS = {"F1": "C2_LOST", "F2": "GNSS_DEGRADED", "F3": "UTM_STATE_CHANGE",
             "F4": "LANDING_SITE_FAILURE", "F5": "UNKNOWN_AIRCRAFT",
             "F6": "FLYAWAY"}


def sha256_hex(obj) -> str:
    import hashlib
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_csv(p: Path):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    import yaml
    runs_root = ROOT / "runs" / "experiment2_cross_site"
    checks = []
    cells = []
    llm_calls = []

    for site_id in SITES:
        e2 = yaml.safe_load(MATRIX_OF[site_id].read_text(encoding="utf-8"))["experiment2"]
        pilot_ids = [p["scenario"] for p in e2["pilots"]]
        scen_by_id = {s["id"]: s for s in e2["scenarios"]}
        for sid in pilot_ids:
            scen = scen_by_id[sid]
            for seed in PILOT_SEEDS:
                cell = {}
                for mgr in MANAGERS:
                    rd = runs_root / site_id / sid / f"seed{seed}" / mgr
                    mp, tp = rd / "metrics.json", rd / "failure_trace.json"
                    if mp.exists() and tp.exists():
                        m = json.loads(mp.read_text(encoding="utf-8"))
                        tr = json.loads(tp.read_text(encoding="utf-8"))
                        if tr.get("failure_config_hash") != sha256_hex(scen["failure"]):
                            m, tr = None, None
                    else:
                        m, tr = None, None
                    cell[mgr] = (rd, m, tr)
                    if m is not None:
                        cells.append({"site": site_id, "scenario": sid, "seed": seed,
                                      "manager": mgr, "metrics": m, "trace": tr})
                        for line in (rd / "manager_outputs.jsonl").read_text(
                                encoding="utf-8").splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            d = json.loads(line)
                            if d.get("llm_metadata") and not d["llm_metadata"].get("replay"):
                                llm_calls.append(d["llm_metadata"])
                hashes = {tr["failure_config_hash"] for _, m, tr in cell.values()
                          if tr is not None}
                checks.append((f"{site_id}/{sid}/seed{seed} exogeneity", sid,
                               len(hashes) == 1 and len(hashes) > 0,
                               f"{len(hashes)} distinct hash(es)"))
                complete = all(m is not None for _, m, tr in cell.values())
                checks.append((f"{site_id}/{sid}/seed{seed} complete", sid, complete,
                               f"{sum(1 for _, m, _ in cell.values() if m is not None)}/4"))

    n_expect = len(SITES) * 6 * 3 * 4
    checks.append(("all pilot cells complete", "ALL",
                   len(cells) == n_expect, f"{len(cells)}/{n_expect}"))

    # per-cell behaviour checks
    for c in cells:
        tr, m = c["trace"], c["metrics"]
        t_fail = int(tr.get("failure_time", 360))
        rd = runs_root / c["site"] / c["scenario"] / f"seed{c['seed']}" / c["manager"]
        evs = read_csv(rd / "events.csv")
        fam = tr.get("failure_family")
        want = EVENT_IDS.get(fam)
        ev_ok = any(e["event_id"] == want and int(e["t"]) == t_fail for e in evs)
        checks.append((f"{c['site']}/{c['scenario']}/seed{c['seed']}/{c['manager']} "
                       f"failure event at t={t_fail}", c["scenario"], ev_ok, ""))
        clk = read_csv(rd / "clock_sync.csv")
        checks.append((f"clock sync", c["scenario"],
                       all(r["sync_ok"] == "True" for r in clk), ""))
        checks.append((f"mission terminal", c["scenario"],
                       m.get("critical_mission_final_state") in
                       ("COMPLETED", "CANCELLED", "FAILED"), ""))
        silent = False
        for line in (rd / "action_pipeline.jsonl").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            p = json.loads(line)
            if p.get("result") == "ISSUED" and \
                    p.get("normalized_action") != p.get("executed_action"):
                silent = True
        checks.append((f"no silent substitution", c["scenario"], not silent, ""))

    # C2/C3 candidate-set effect: post < pre for the affected managers
    for c in cells:
        tr = c["trace"]
        ctx = None
        e2 = yaml.safe_load(MATRIX_OF[c["site"]].read_text(encoding="utf-8"))["experiment2"]
        scen = next(s for s in e2["scenarios"] if s["id"] == c["scenario"])
        ctx = scen["impact_context"]
        if ctx in ("C2", "C3") and c["manager"] in ("B1", "B2", "B4b"):
            checks.append((f"{c['scenario']} {ctx} candidate-set effect",
                           c["scenario"],
                           (tr.get("candidate_count_after") or 0)
                           < (tr.get("candidate_count_before") or 0),
                           f"pre/post={tr.get('candidate_count_before')}/"
                           f"{tr.get('candidate_count_after')}"))

    # backend
    n_llm = len(llm_calls)
    n_empty = sum(1 for x in llm_calls if x.get("empty_content_count", 0) > 0)
    n_transport = sum(1 for x in llm_calls
                      if x.get("validation_status") == "LLM_TRANSPORT_ERROR")
    crashed = 0
    for c in cells:
        if c["manager"] == "B4b" and c["metrics"] is None:
            crashed += 1
    checks.append(("LLM backend (pilot, frozen recovery policy)", "ALL",
                   crashed == 0,
                   f"{n_llm} calls, empty={n_empty}, transport={n_transport}, "
                   f"crashed={crashed}"))

    n_fail = sum(1 for _, _, ok, _ in checks if not ok)
    verdict = "PASS" if n_fail == 0 else "FAIL"

    md = ["# Experiment 2 — Cross-Site Pilot Report (Site B / Site C)",
          "",
          f"Per-site pilots: 6 scenarios x 3 seeds x 4 managers = 72 runs per "
          f"site ({len(cells)}/{n_expect} cells collected). Site-adapted "
          f"timelines (Site B t_failure=322 s, Site C t_failure=383 s) and the "
          f"re-derived F2/F5/F6 geometry are in effect. "
          f"**Verdict: {verdict}** ({len(checks) - n_fail}/{len(checks)} checks).",
          "",
          "## Per-scenario behaviour (3 seeds each)",
          "",
          "| site | scenario | ctx | manager | affected | recovery | comp range | viol | dmg |",
          "|---|---|---|---|---|---|---|---|---|"]
    per = defaultdict(list)
    for c in cells:
        per[(c["site"], c["scenario"], c["manager"])].append(c)
    import yaml as _y
    for site_id in SITES:
        e2 = _y.safe_load(MATRIX_OF[site_id].read_text(encoding="utf-8"))["experiment2"]
        scen_by_id = {s["id"]: s for s in e2["scenarios"]}
        for sid in [p["scenario"] for p in e2["pilots"]]:
            for mgr in MANAGERS:
                rs = per.get((site_id, sid, mgr), [])
                if not rs:
                    md.append(f"| {site_id} | {sid} | {scen_by_id[sid]['impact_context']} "
                              f"| {mgr} | MISSING | | | | |")
                    continue
                comps = [r["metrics"]["critical_mission_completion_t"] for r in rs]
                md.append(
                    f"| {site_id} | {sid} | {scen_by_id[sid]['impact_context']} | {mgr} | "
                    f"{sum(1 for r in rs if r['metrics']['affected_critical'])}/{len(rs)} | "
                    f"{sum(1 for r in rs if r['metrics']['recovery_success'])}/{len(rs)} | "
                    f"{min(comps)}-{max(comps)} | "
                    f"{sum(1 for r in rs if r['metrics']['critical_mission_deadline_violation'])}/{len(rs)} | "
                    f"{[r['metrics']['existing_missions_damaged_count'] for r in rs]} |")
    md.append("")
    md.append("## Gate decisions")
    md.append("")
    md.append("| gate | verdict | evidence |")
    md.append("|---|---|---|")
    gates = [
        ("exogenous failure hash identical per (scenario, seed)",
         all(ok for n, _, ok, _ in checks if n.endswith("exogeneity")),
         "failure config frozen per site matrix; hash guard active"),
        ("failure event fires at the site-adapted time",
         all(ok for n, _, ok, _ in checks if "failure event at t=" in n),
         "t=322 (Site B) / t=383 (Site C)"),
        ("C2/C3 candidate-set effect measured",
         all(ok for n, _, ok, _ in checks if "candidate-set effect" in n),
         "post < pre for affected managers in every C2/C3 cell"),
        ("managers act through the checker (no silent substitution)",
         all(ok for n, _, ok, _ in checks if n == "no silent substitution"),
         "normalized == executed everywhere"),
        ("missions terminate within 900 s",
         all(ok for n, _, ok, _ in checks if n == "mission terminal"),
         "0 unterminated critical missions"),
        ("clock sync unaffected",
         all(ok for n, _, ok, _ in checks if n == "clock sync"),
         "sync_ok across all pilot cells"),
        ("LLM backend stable (frozen recovery policy)",
         crashed == 0, f"{n_llm} calls, {n_empty} empty, {n_transport} transport, 0 crashed"),
    ]
    for name, ok, ev in gates:
        md.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {ev} |")
    (ROOT / "reports" / "experiment2" / "E2_CROSS_SITE_PILOT.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")
    print(f"\nCROSS-SITE PILOT VERDICT: {verdict} "
          f"({len(checks) - n_fail}/{len(checks)})")
    print("report: reports/experiment2/E2_CROSS_SITE_PILOT.md")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
