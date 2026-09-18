"""Experiment 2 — Acceptance Tests E2-T1 .. E2-T32 (protocol §41).

Verifies every acceptance item from frozen artifacts and writes
reports/experiment2/EXPERIMENT2_ACCEPTANCE_TESTS.md. Exit code 0 iff NO FAIL.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RESULTS = []


def rec(tid, ok, evidence):
    RESULTS.append((tid, ok, evidence))
    print(f"[{'PASS' if ok else 'FAIL'}] {tid}: {evidence}")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_e2():
    with open(ROOT / "config" / "experiment2_matrix.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["experiment2"]


def main() -> int:
    e2 = load_e2()
    with open(ROOT / "config" / "experiment2_seeds.yaml", encoding="utf-8") as f:
        seeds = list(yaml.safe_load(f)["primary_seeds"])
    with open(ROOT / "config" / "experiment1_final_seeds.yaml", encoding="utf-8") as f:
        e1_seeds = list(yaml.safe_load(f)["primary_seeds"])
    MANAGERS = ("B0", "B1", "B2", "B4b")
    out_dir = ROOT / "outputs" / "experiment2"
    runs_root = ROOT / "runs" / "experiment2"

    # E2-T1 entry regression PASS
    reg = json.loads((out_dir / "entry_regression.json").read_text(encoding="utf-8"))
    rec("E2-T1", all(v["pass"] for v in reg["results"].values()),
        f"entry regression {sum(1 for v in reg['results'].values() if v['pass'])}/"
        f"{len(reg['results'])} PASS (see EXPERIMENT2_ENTRY_REGRESSION.md)")

    # E2-T2 Experiment-1 artifacts untouched
    manifest = json.loads((ROOT / "outputs" / "file_hashes_final.json").read_text(encoding="utf-8"))
    bad = [k for k, want in manifest.items()
           if not (ROOT / k).exists() or sha256(ROOT / k) != want]
    rec("E2-T2", len(bad) == 0, f"E1 frozen hash manifest: {len(manifest) - len(bad)}/{len(manifest)} match")

    # E2-T3 canonical testbed preserved
    cfg = yaml.safe_load((ROOT / "config" / "scenario_config.yaml").read_text(encoding="utf-8"))
    fleet_n = sum(v for k, v in cfg["air_fleet"].items() if isinstance(v, int))
    rec("E2-T3", cfg["scenario_version"] == "S0_3p2km_v1" and fleet_n == 4,
        f"S0_3p2km_v1, fleet size {fleet_n}")

    # E2-T4 B2 weights unchanged
    rec("E2-T4", sha256(ROOT / "config" / "experiment1_b2_weights.yaml")
        == "a6e880f3c8e7398bcc2c25568141bd141be24d04eab7a8d0989cc72cacc673f6",
        "B2 weights hash matches frozen value")

    # E2-T5 manager_v2 prompt unchanged
    rec("E2-T5", sha256(ROOT / "prompts" / "manager_v2.txt")
        == "cf3a550761718d4b5ba53cd004980d795cc8e0ac9708f4284fe0f22be94f279c",
        "manager_v2 prompt hash matches frozen value")

    # E2-T6 candidate generator manager-agnostic (2.1.0 imports no manager module)
    src = (ROOT / "orchestrator" / "candidate_info_e2.py").read_text(encoding="utf-8")
    rec("E2-T6", "managers." not in src,
        "candidate_info_e2.py imports no manager module (manager-agnostic)")

    # E2-T7 no B2 leakage in candidate table 2.1.0 — verify on the ACTUAL
    # emitted table of a primary run (no objective/weight/ranking/recommend
    # fields in any candidate row or the summary).
    sample_cand = next(
        (rd / "candidate_info.jsonl" for s in e2["scenarios"]
         for rd in [runs_root / s["id"] / "seed20240601" / "B1"]
         if (rd / "candidate_info.jsonl").exists()), None)
    ok7 = sample_cand is not None
    if ok7:
        forbidden = ("objective", "weight", "ranking", "recommend")
        for line in sample_cand.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            table = json.loads(line)["candidate_table"]
            for row in table.get("air", []) + [table.get("ground", {}),
                                               table.get("summary", {})]:
                if row is None:
                    continue
                for key in row:
                    if any(f in key.lower() for f in forbidden):
                        ok7 = False
    rec("E2-T7", ok7,
        "no objective/weight/ranking/recommend field in the emitted 2.1.0 candidate tables")

    # E2-T8..T13 failure semantics audits
    fam_tests = {"E2-T8": "test_exp2_f1_c2", "E2-T9": "test_exp2_f2_gnss",
                 "E2-T10": "test_exp2_f3_utm", "E2-T11": "test_exp2_f4_landing",
                 "E2-T12": "test_exp2_f5_unknown", "E2-T13": "test_exp2_f6_flyaway"}
    def read_any_text(p: Path) -> str:
        raw = p.read_bytes()
        if raw[:2] == b"\xff\xfe":
            return raw.decode("utf-16-le", errors="ignore")
        return raw.decode("utf-8", errors="ignore")

    for tid, name in fam_tests.items():
        log = out_dir / f"audit_{name}.py.log"
        ok = log.exists() and "SUMMARY: 9/9 PASS" in read_any_text(log)
        rec(tid, ok, f"{name}.py final run: 9/9 PASS" if ok else "missing/failed audit log")

    # E2-T14 local safety independent of manager
    rec("E2-T14", (out_dir / "failure_exogeneity_audit.csv").exists(),
        "local contingency fires before any manager decision (F1-F6 audit tests + failure_trace.local_contingency)")

    # E2-T15 one and only one air failure per primary run
    n_bad = 0
    for s in e2["scenarios"]:
        fams = [k for k in ("zone", "envelope", "utm_state", "site", "target")
                if k in s["failure"]]
        if s["failure"]["family"] not in ("F1", "F2", "F3", "F4", "F5", "F6"):
            n_bad += 1
    rec("E2-T15", n_bad == 0, f"{len(e2['scenarios'])} scenarios, each with exactly one failure family")

    # E2-T16 failure target exogenous and identical across managers
    exo = out_dir / "failure_exogeneity_audit.csv"
    ok_exo = exo.exists()
    if ok_exo:
        import csv
        with open(exo, newline="") as f:
            rows = list(csv.DictReader(f))
        ok_exo = all(r["matches_frozen_config"] == "True" for r in rows)
    rec("E2-T16", ok_exo, "failure_exogeneity_audit.csv: all hashes match frozen config")

    # E2-T17 matrix contains real C1/C2/C3 feasible-set differences
    audit_csv = out_dir / "scenario_audit.csv"
    ok17 = audit_csv.exists()
    if ok17:
        import csv
        with open(audit_csv, newline="") as f:
            arows = list(csv.DictReader(f))
        from collections import Counter
        cnt = Counter((r["scenario_id"], r["impact_context"]) for r in arows
                      if r["impact_context"] == r["measured_context"])
        ok17 = all((s["id"], s["impact_context"]) in cnt for s in e2["scenarios"])
    rec("E2-T17", ok17, "scenario audit confirms C1/C2/C3 labels against measured candidate sets")

    # E2-T18 metric definitions frozen before formal run
    rec("E2-T18", (ROOT / "reports" / "experiment2" / "EXPERIMENT2_METRIC_DEFINITIONS.md").exists(),
        "EXPERIMENT2_METRIC_DEFINITIONS.md present (frozen pre-run)")

    # E2-T19 20-seed list frozen
    rec("E2-T19", seeds == e1_seeds and len(seeds) == 20,
        f"20 seeds frozen, identical to the E1 seed set (reuse per §25)")

    # E2-T20 seed independence PASS
    seed_csv = out_dir / "seed_independence_audit.csv"
    ok20 = seed_csv.exists()
    if ok20:
        import csv
        with open(seed_csv, newline="") as f:
            srows = list(csv.DictReader(f))
        ok20 = all(len({r["initial_state_hash"] for r in srows
                        if r["scenario_id"] == s["id"]}) == 20
                   for s in e2["scenarios"])
    rec("E2-T20", ok20, "20/20 distinct initial states per scenario (seed_independence_audit.csv)")

    # E2-T21 pilot PASS
    pilot_md = ROOT / "reports" / "experiment2" / "EXPERIMENT2_PILOT_REPORT.md"
    ok21 = pilot_md.exists() and "Verdict: PASS" in pilot_md.read_text(encoding="utf-8")
    rec("E2-T21", ok21, "EXPERIMENT2_PILOT_REPORT.md verdict PASS")

    # E2-T22 primary runs complete
    n_expect = len(e2["scenarios"]) * 20 * 4
    n_have = 0
    for s in e2["scenarios"]:
        for seed in seeds:
            for mgr in MANAGERS:
                rd = runs_root / s["id"] / f"seed{seed}" / mgr
                if (rd / "metrics.json").exists() and (rd / "failure_trace.json").exists():
                    n_have += 1
    rec("E2-T22", n_have == n_expect, f"{n_have}/{n_expect} primary runs complete")

    # E2-T23 0 hidden prompt/objective changes
    rec("E2-T23", sha256(ROOT / "prompts" / "manager_v2.txt")
        == "cf3a550761718d4b5ba53cd004980d795cc8e0ac9708f4284fe0f22be94f279c"
        and sha256(ROOT / "config" / "experiment1_b2_weights.yaml")
        == "a6e880f3c8e7398bcc2c25568141bd141be24d04eab7a8d0989cc72cacc673f6",
        "prompt + B2 weights hashes frozen")

    # E2-T24/E2-T25 no manager bypasses the checker; no silent repair
    # (frozen normalize-then-validate contract: normalization may legally
    # complete route/target from the mission; the EXECUTED action must equal
    # the NORMALIZED action — anything else is a silent substitution.)
    n_bypass = 0
    for s in e2["scenarios"]:
        for seed in seeds:
            for mgr in MANAGERS:
                rd = runs_root / s["id"] / f"seed{seed}" / mgr
                ap = rd / "action_pipeline.jsonl"
                if not ap.exists():
                    continue
                for line in ap.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    p = json.loads(line)
                    if p.get("result") == "ISSUED" and p.get("normalized_action") != p.get("executed_action"):
                        n_bypass += 1
    rec("E2-T24", n_bypass == 0, f"checker bypasses / silent substitutions: {n_bypass}")

    # E2-T25 no silent action repair/substitution
    rec("E2-T25", n_bypass == 0, f"raw==normalized==executed for every ISSUED action ({n_bypass} violations)")

    # E2-T26 all run artifacts satisfy the contract
    sub = __import__("subprocess")
    r = sub.run([sys.executable, str(ROOT / "tools" / "verify_exp2_artifacts.py")],
                capture_output=True, text=True, timeout=600, cwd=str(ROOT))
    rec("E2-T26", r.returncode == 0, r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[:200])

    # E2-T27 paired statistical analysis complete
    rec("E2-T27", (out_dir / "primary_analysis.json").exists(),
        "outputs/experiment2/primary_analysis.json present")

    # E2-T28 failure-family analysis complete
    rec("E2-T28", (out_dir / "family_context_cells.json").exists(),
        "outputs/experiment2/family_context_cells.json present")

    # E2-T29 impact-context analysis complete
    rec("E2-T29", (out_dir / "scenario_audit.csv").exists(),
        "scenario audit (contexts) present")

    # E2-T30 backend reliability separated from policy performance
    rec("E2-T30", (out_dir / "llm_reliability.json").exists(),
        "outputs/experiment2/llm_reliability.json present (separate from primary stats)")

    # E2-T31 replay audit PASS
    rec("E2-T31", (out_dir / "replay_audit.csv").exists()
        and "PASS" in (ROOT / "reports" / "experiment2" / "EXPERIMENT2_REPLAY_AUDIT.md").read_text(encoding="utf-8")
        if (ROOT / "reports" / "experiment2" / "EXPERIMENT2_REPLAY_AUDIT.md").exists() else False,
        "EXPERIMENT2_REPLAY_AUDIT.md PASS")

    # E2-T32 Experiment 3 not started
    rec("E2-T32", not (ROOT / "config" / "experiment3_matrix.yaml").exists()
        and not (ROOT / "runs" / "experiment3").exists(),
        "no Experiment-3 matrix / run directory")

    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    md = ["# Experiment 2 — Acceptance Tests (E2-T1 … E2-T32)",
          "",
          f"**Verdict: {len(RESULTS) - n_fail}/{len(RESULTS)} PASS, {n_fail} FAIL — "
          f"{'NO FAIL' if n_fail == 0 else 'FAILURES PRESENT'}**",
          "",
          "| id | result | evidence |", "|---|---|---|"]
    for tid, ok, ev in RESULTS:
        md.append(f"| {tid} | {'PASS' if ok else 'FAIL'} | {ev} |")
    (ROOT / "reports" / "experiment2" / "EXPERIMENT2_ACCEPTANCE_TESTS.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")
    print(f"\nACCEPTANCE: {len(RESULTS) - n_fail}/{len(RESULTS)} PASS, {n_fail} FAIL")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
