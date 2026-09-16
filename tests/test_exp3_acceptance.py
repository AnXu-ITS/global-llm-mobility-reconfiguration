"""Experiment 3 — Acceptance Tests (E3-A1 .. E3-A9).

Verifies frozen-artifact integrity and run-artifact consistency for the
Compound Disruption Stress Test. Exit code 0 iff NO FAIL.

Checks:
  E3-A1  matrix frozen (matrix_sha256 == outputs/experiment3/freeze_hashes.json)
  E3-A2  E1/E2 frozen artifacts untouched (file_hashes_final.json manifest)
  E3-A3  E3 code manager-agnostic (no `managers.` import in runner/evaluator)
  E3-A4  frozen E2 failure injectors present + unchanged signature (F1..F6)
  E3-A5  candidate table 2.2.0 version + emission guard on real runs
         (L1: no mission_candidates; L4: mission_candidates present)
  E3-A6  multi-event timeline: len(failure_traces) == num_failure_events
  E3-A7  SWL internal consistency: SWL == round(sum(by_mission), 3)
  E3-A8  cascade_recovery length == num_failure_events
  E3-A9  second emergency (L3/L4) released and present in SWL by-mission
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


def sha256_hex(obj) -> str:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _find_run(scenario_id: str, seed: int, manager: str) -> Path:
    return ROOT / "runs" / "experiment3" / scenario_id / f"seed{seed}" / manager


def main() -> int:
    e3 = yaml.safe_load((ROOT / "config" / "experiment3_matrix.yaml").read_text(encoding="utf-8"))["experiment3"]

    # E3-A1 matrix frozen
    freeze = json.loads((ROOT / "outputs" / "experiment3" / "freeze_hashes.json").read_text(encoding="utf-8"))
    rec("E3-A1", sha256_hex(e3) == freeze["matrix_sha256"],
        "matrix_sha256 matches post-pilot freeze")

    # E3-A2 E1/E2 frozen artifacts untouched
    manifest = json.loads((ROOT / "outputs" / "file_hashes_final.json").read_text(encoding="utf-8"))
    from tools.frozen_compatibility import check_manifest
    bad, transitions = check_manifest(ROOT, manifest)
    rec("E3-A2", len(bad) == 0,
        f"E1/E2 manifest: {len(manifest)-len(bad)-len(transitions)} exact; "
        f"{len(transitions)} exactly reconstructed documented metric fix; {len(bad)} unexplained")

    # E3-A3 manager-agnostic
    for name in ("orchestrator/experiment3_runner.py", "orchestrator/candidate_info_e3.py",
                 "failures/e3_compound.py"):
        src = (ROOT / name).read_text(encoding="utf-8")
        if "managers." in src:
            rec("E3-A3", False, f"{name} imports a manager module")
            break
    else:
        rec("E3-A3", True, "E3 runner/evaluator/compound modules are manager-agnostic")

    # E3-A4 frozen E2 injectors present
    import importlib.util
    spec = importlib.util.spec_from_file_location("e2f", ROOT / "failures" / "e2_failures.py")
    e2f = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(e2f)
    fams = sorted(k for k in e2f.INJECTORS if k.startswith("F") and k[1:].isdigit())
    rec("E3-A4", fams == ["F1", "F2", "F3", "F4", "F5", "F6"],
        f"frozen INJECTORS families = {fams}")

    # ---- run-artifact checks on a representative L1, L4 run (seed 20240601, B1)
    run_checks = 0
    for sid, seed in (("E3_L1_F1_C2", 20240601), ("E3_L4_B", 20240601)):
        rd = _find_run(sid, seed, "B1")
        m = json.loads((rd / "metrics.json").read_text(encoding="utf-8"))
        ft = json.loads((rd / "failure_traces.json").read_text(encoding="utf-8"))
        run_checks += 1

        # E3-A6 multi-event timeline
        if len(ft) != m.get("num_failure_events"):
            rec("E3-A6", False, f"{sid}: failure_traces {len(ft)} != num_failure_events {m.get('num_failure_events')}")
            break
        # E3-A8 cascade_recovery length
        if len(m.get("cascade_recovery", [])) != m.get("num_failure_events"):
            rec("E3-A8", False, f"{sid}: cascade_recovery length mismatch")
            break
    else:
        rec("E3-A6", True, "failure_traces length == num_failure_events (L1/L4)")
        rec("E3-A8", True, "cascade_recovery length == num_failure_events (L1/L4)")

    # E3-A7 SWL consistency
    for sid, seed in (("E3_L1_F1_C2", 20240601), ("E3_L4_B", 20240601), ("E3_L3_COMP_F1", 20240601)):
        m = json.loads((_find_run(sid, seed, "B1") / "metrics.json").read_text(encoding="utf-8"))
        tot = round(sum(m.get("system_weighted_loss_by_mission", {}).values()), 3)
        if abs(tot - m.get("system_weighted_loss", 0)) > 0.01:
            rec("E3-A7", False, f"{sid}: SWL {m.get('system_weighted_loss')} != sum(by_mission) {tot}")
            break
    else:
        rec("E3-A7", True, "SWL == sum(system_weighted_loss_by_mission)")

    # E3-A5 candidate 2.2.0 + emission guard
    def _cand_records(sid, seed):
        p = _find_run(sid, seed, "B1") / "candidate_info.jsonl"
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

    l1_recs = _cand_records("E3_L1_F1_C2", 20240601)
    l4_recs = _cand_records("E3_L4_B", 20240601)
    l1_ver = all(r["candidate_table"].get("summary", {}).get("candidate_table_version") == "2.2.0" for r in l1_recs)
    l1_no_mc = all("mission_candidates" not in r["candidate_table"] for r in l1_recs)
    l4_has_mc = any(len(r["candidate_table"].get("mission_candidates", [])) >= 2 for r in l4_recs)
    rec("E3-A5", l1_ver and l1_no_mc and l4_has_mc,
        f"2.2.0 emitted; L1 no mission_candidates ({l1_no_mc}); L4 emits >=2 ({l4_has_mc})")

    # E3-A9 second emergency in L3/L4
    l3 = json.loads((_find_run("E3_L3_COMP_F1", 20240601, "B1") / "metrics.json").read_text(encoding="utf-8"))
    l4 = json.loads((_find_run("E3_L4_B", 20240601, "B1") / "metrics.json").read_text(encoding="utf-8"))
    ok = ("M-CRITICAL-002" in l3.get("system_weighted_loss_by_mission", {})
          and "M-CRITICAL-002" in l4.get("system_weighted_loss_by_mission", {}))
    rec("E3-A9", ok, "M-CRITICAL-002 present in SWL by-mission for L3 and L4")

    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"\n{len(RESULTS)} checks, {n_fail} FAIL")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
