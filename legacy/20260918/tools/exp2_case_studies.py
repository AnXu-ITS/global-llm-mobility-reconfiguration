"""Experiment 2 — Representative Case Studies (protocol §35).

CASE-A: simple resource failure            -> E2_F1_C1 (C2 lost on background aircraft)
CASE-B: critical-chain failure with backup -> E2_F1_C2 (C2 lost on the critical aircraft)
CASE-C: low-redundancy forced ground       -> E2_F1_C3 (only air option fails -> ground)

For each case, a fixed representative (scenario, seed) is traced for ALL FOUR
managers: failure -> Global State -> candidate-set changes -> per-manager
decision -> checker -> recovery outcome.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CASES = [
    ("CASE-A", "simple resource failure", "E2_F1_C1", 20240601),
    ("CASE-B", "critical-chain failure with backup", "E2_F1_C2", 20240601),
    ("CASE-C", "low-redundancy forced ground fallback", "E2_F1_C3", 20240601),
]
MANAGERS = ("B0", "B1", "B2", "B4b")


def read_jsonl(p: Path):
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def events_csv(p: Path):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def actions_csv(p: Path):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    md = ["# Experiment 2 — Representative Case Studies (protocol §35)", ""]
    for case_id, label, sid, seed in CASES:
        md.append(f"## {case_id} — {label}  ({sid}, seed {seed})")
        md.append("")
        for mgr in MANAGERS:
            rd = ROOT / "runs" / "experiment2" / sid / f"seed{seed}" / mgr
            if not (rd / "metrics.json").exists():
                md.append(f"### {mgr}: MISSING")
                md.append("")
                continue
            m = json.loads((rd / "metrics.json").read_text(encoding="utf-8"))
            tr = json.loads((rd / "failure_trace.json").read_text(encoding="utf-8"))
            evs = events_csv(rd / "events.csv")
            acts = actions_csv(rd / "actions.csv")
            key_events = [f"t={e['t']} {e['event_id']}" for e in evs
                          if e["event_id"] in
                          ("MISSION_STARTED", "MISSION_COMPLETED", "GROUND_FALLBACK_STARTED",
                           "GROUND_FALLBACK_COMPLETED", "C2_LOST", "LOCAL_CONTINGENCY",
                           "CONTINGENCY_LANDED", "MISSION_INTERRUPTED")]
            pipeline = read_jsonl(rd / "action_pipeline.jsonl")
            decisions = [(p.get("t"), (p.get("raw_action") or {}).get("type"),
                          p.get("result"))
                         for p in pipeline]
            md.append(f"### {mgr}")
            md.append("")
            md.append(f"- failure: {tr['failure_family']} on {tr['target']} at "
                      f"t={tr['failure_time']}; local contingency: "
                      f"{json.dumps(tr.get('local_contingency'), ensure_ascii=False)}")
            md.append(f"- candidate set: pre={tr.get('candidate_count_before')} "
                      f"(t300 table), pre-asif={tr.get('candidate_count_pre_failure_asif')}, "
                      f"post={tr.get('candidate_count_after')} "
                      f"({tr.get('candidate_count_after_label')}); "
                      f"ground feasible={tr.get('ground_candidate_feasible_post')} "
                      f"eta={tr.get('ground_eta_post')}")
            md.append(f"- timeline: {' ; '.join(key_events)}")
            md.append(f"- decisions (t, proposed type, result): "
                      f"{decisions}")
            md.append(f"- outcome: affected={m['affected_critical']} "
                      f"recovery={m['recovery_success']}"
                      f"({'AIR' if m['recovery_mode']=='AIR' else str(m['recovery_mode'])}) "
                      f"recovery_time={m['recovery_time_s']} s, "
                      f"completion_t={m['critical_mission_completion_t']} "
                      f"(time {m['critical_mission_completion_time_s']} s), "
                      f"deadline violation={m['critical_mission_deadline_violation']}, "
                      f"service damage={m['existing_missions_damaged_count']}, "
                      f"post-failure rejected={m['post_failure_rejected']} "
                      f"({m['post_failure_rejected_failure_related']} failure-related), "
                      f"failed-resource reselection={m['failed_resource_reselection']}")
            md.append("")
        md.append("---")
        md.append("")
    (ROOT / "reports" / "experiment2" / "E2_CASE_STUDIES.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")
    print("report: reports/experiment2/E2_CASE_STUDIES.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
