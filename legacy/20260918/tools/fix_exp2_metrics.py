"""Experiment 2 — metric recomputation from FROZEN run artifacts (bug fix).

The runner's recovery-metric aggregation had a bug: the recovery-event search
required an `aircraft` payload key, so GROUND recoveries (GROUND_FALLBACK_STARTED
has no aircraft key) were missed — recovery_success / recovery_time_s /
recovery_mode were wrong for ground-recovery runs (the simulation artifacts
themselves are correct).

This script recomputes ONLY those three derived fields for every primary run
from the frozen events.csv using EXACTLY the frozen formulas
(EXPERIMENT2_METRIC_DEFINITIONS.md §B/§D) and updates metrics.json in place,
writing a provenance record (metrics_recomputed.json) per run.

CHANGELOG: "Experiment 2 metric fix — recovery event must not require an
aircraft key (GROUND fallback recoveries)". No simulation artifact is touched.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MANAGERS = ("B0", "B1", "B2", "B4b")


def read_events(p: Path):
    out = []
    if not p.exists():
        return out
    with open(p, newline="") as f:
        for r in csv.DictReader(f):
            try:
                r["payload"] = json.loads(r["payload"])
            except (json.JSONDecodeError, TypeError):
                pass
            out.append(r)
    return out


def main() -> int:
    with open(ROOT / "config" / "experiment2_matrix.yaml", encoding="utf-8") as f:
        e2 = yaml.safe_load(f)["experiment2"]
    with open(ROOT / "config" / "experiment2_seeds.yaml", encoding="utf-8") as f:
        seeds = list(yaml.safe_load(f)["primary_seeds"])

    n_fixed = 0
    for s in e2["scenarios"]:
        sid = s["id"]
        for seed in seeds:
            for mgr in MANAGERS:
                rd = ROOT / "runs" / "experiment2" / sid / f"seed{seed}" / mgr
                mp = rd / "metrics.json"
                ftp = rd / "failure_trace.json"
                if not mp.exists() or not ftp.exists():
                    continue
                m = json.loads(mp.read_text(encoding="utf-8"))
                ft = json.loads(ftp.read_text(encoding="utf-8"))
                failure_t = int(m.get("failure_time", 360))
                support = m.get("critical_mission_id", "M-CRITICAL-001")
                affected = bool(m.get("affected_critical"))
                events = read_events(rd / "events.csv")
                recovery_event = next(
                    (e for e in events
                     if int(e["t"]) >= failure_t
                     and e["event_id"] in ("MISSION_STARTED", "GROUND_FALLBACK_STARTED")
                     and (e.get("payload") or {}).get("mission") == support), None)
                gf_event = next(
                    (e for e in events
                     if int(e["t"]) >= failure_t
                     and e["event_id"] == "GROUND_FALLBACK_STARTED"
                     and (e.get("payload") or {}).get("mission") == support), None)
                new_success = affected and recovery_event is not None
                new_mode = ("GROUND" if gf_event is not None else
                            ("AIR" if recovery_event is not None else None))
                new_time = (int(recovery_event["t"]) - failure_t
                            if recovery_event is not None else None)
                # failed-resource reselection: only AIR actions can "use" a
                # failed resource (a GROUND_FALLBACK carrying the mission
                # destination as target_site is not a reselection).
                failed_target = (s["failure"].get("target")
                                 or s["failure"].get("site") or "")
                pipeline_path = rd / "action_pipeline.jsonl"
                new_reselect = 0
                if pipeline_path.exists():
                    for line in pipeline_path.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            p = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if int(p.get("t") or 0) < failure_t:
                            continue
                        raw = p.get("raw_action") or {}
                        if raw.get("type") in ("GROUND_FALLBACK", "DELAY", "CANCEL",
                                               "NO_ACTION", "ESCALATE", None):
                            continue
                        if str(raw.get("aircraft_id")) == failed_target \
                                or str(raw.get("target_site")) == failed_target:
                            new_reselect += 1
                changed = False
                if (m.get("recovery_success") != new_success
                        or m.get("recovery_mode") != new_mode
                        or m.get("recovery_time_s") != new_time):
                    m["recovery_success"] = new_success
                    m["recovery_mode"] = new_mode
                    m["recovery_time_s"] = new_time
                    changed = True
                if m.get("failed_resource_reselection") != new_reselect:
                    m["failed_resource_reselection"] = new_reselect
                    changed = True
                if changed:
                    mp.write_text(json.dumps(m, indent=2, sort_keys=True), encoding="utf-8")
                    (rd / "metrics_recomputed.json").write_text(json.dumps({
                        "fields": ["recovery_success", "recovery_mode", "recovery_time_s",
                                   "failed_resource_reselection"],
                        "reason": "frozen formulas §B/§D/§F: recovery event must not "
                                  "require an aircraft key; reselection counts AIR "
                                  "actions only (GROUND_FALLBACK target_site is the "
                                  "mission destination, not the failed resource)",
                        "source_artifact": "events.csv + action_pipeline.jsonl"}, indent=2),
                        encoding="utf-8")
                    n_fixed += 1
    print(f"metric recomputation done: {n_fixed} runs updated (fields: "
          "recovery_success / recovery_mode / recovery_time_s / failed_resource_reselection)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
