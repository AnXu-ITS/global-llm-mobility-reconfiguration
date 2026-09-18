"""Print the per-scenario paired B2-vs-B4b table (post-Holm)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path


def f(x, fmt="{:.4f}", default="—"):
    try:
        if x is None or x == "":
            return default
        return fmt.format(float(x))
    except (TypeError, ValueError):
        return default


def main() -> int:
    p = Path("outputs/experiment2/paired_b2_b4b.csv")
    rows = list(csv.DictReader(open(p, newline="")))
    print(f"{'scenario':<11} {'ctx':<3} | {'comp diff':>9} {'t p':>8} {'holm':>8} "
          f"{'d':>7} | {'viol holm':>9} {'recov holm':>10} {'dmg holm':>8}")
    for r in rows:
        print(f"{r['scenario_id']:<11} {r['impact_context']:<3} | "
              f"{f(r['critical_mission_completion_time_s_diff'], '{:+.2f}'):>9} "
              f"{f(r['critical_mission_completion_time_s_p']):>8} "
              f"{f(r['critical_mission_completion_time_s_p_holm']):>8} "
              f"{f(r['critical_mission_completion_time_s_d'], '{:+.3f}'):>7} | "
              f"{f(r['critical_mission_deadline_violation_mcnemar_p_holm']):>9} "
              f"{f(r['recovery_success_mcnemar_p_holm']):>10} "
              f"{f(r['existing_missions_damaged_count_p_holm']):>8}")
    sig = [r for r in rows if any(
        r.get(k) not in ("", None) and float(r[k]) < 0.05
        for k in r if k.endswith("_holm"))]
    print("\nsignificant after Holm:", len(sig))
    for r in sig:
        print(" ", r["scenario_id"], r["impact_context"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
