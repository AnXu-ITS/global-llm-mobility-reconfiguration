"""Audit Experiment-3 scenario geometry against the frozen invariants.

Verifies, for every resolved scenario in `config/experiment3_matrix.yaml`:

  1. no `derive` block remains (geometry is fully resolved);
  2. F5 "cover V3->V1 recovery route" zones intersect the V3->V1 segment;
  3. F5 "NW corner" zones contain no site (V1/V2/V3 all outside the radius);
  4. F2 zones are aircraft-state-only (candidate_rule == none);
  5. F6 envelopes cross the critical V2->V1 corridor and stay clear of V3->V1.

Geometry primitives are reused from `failures/e2_failures` (haversine /
segment-distance), so the audit is identical in kind to the E2 cross-site audit.

Usage:
    python tools/audit_exp3_scenarios.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from failures.e2_failures import (_segment_segment_distance_m, haversine_m,  # noqa: E402
                                  point_segment_distance_m, strip_ends)

SITES = {k: (float(v["lat"]), float(v["lon"]))
         for k, v in yaml.safe_load(
             (ROOT / "config" / "scenario_config.yaml").read_text(encoding="utf-8")
         )["facilities"].items() if k in ("V1", "V2", "V3")}

COVER_V3V1 = {"ZN-F5-E3-01", "ZN-F5-E3-02", "ZN-F5-E3-04"}
NW_CORNER = {"ZN-F5-E3-03"}
F2_IDS = {"ZN-F2-E3-01", "ZN-F2-E3-02", "ZN-F2-E3-03"}
F6_IDS = {"ENV-F6-E3-01", "ENV-F6-E3-02"}


def main():
    doc = yaml.safe_load((ROOT / "config" / "experiment3_matrix.yaml").read_text(encoding="utf-8"))
    scenarios = doc["experiment3"]["scenarios"]
    errors = []
    checks = 0

    v3, v1 = SITES["V3"], SITES["V1"]
    v2 = SITES["V2"]

    for scen in scenarios:
        for f in scen.get("failure_schedule", []):
            z = f.get("zone")
            if z is not None:
                checks += 1
                if "derive" in z:
                    errors.append(f"{scen['id']}: zone {z['id']} still has derive")
                    continue
                if z["id"] in COVER_V3V1:
                    d = point_segment_distance_m((z["lat"], z["lon"]), v3, v1)
                    if d > z["radius_m"]:
                        errors.append(
                            f"{scen['id']}: {z['id']} does not cover V3->V1 "
                            f"(min dist {d:.1f} > r {z['radius_m']})")
                elif z["id"] in NW_CORNER:
                    for sid, p in SITES.items():
                        if haversine_m((z["lat"], z["lon"]), p) <= z["radius_m"]:
                            errors.append(f"{scen['id']}: {z['id']} contains site {sid}")
                elif z["id"] in F2_IDS:
                    if z.get("candidate_rule") != "none":
                        errors.append(f"{scen['id']}: {z['id']} F2 must be candidate_rule none")
            e = f.get("envelope")
            if e is not None:
                checks += 1
                if "derive" in e:
                    errors.append(f"{scen['id']}: envelope {e['id']} still has derive")
                    continue
                if e["id"] in F6_IDS:
                    ends = strip_ends(e)
                    d_crit = _segment_segment_distance_m(v2, v1, ends[0], ends[1])
                    d_rec = _segment_segment_distance_m(v3, v1, ends[0], ends[1])
                    if d_crit > e["half_width_m"]:
                        errors.append(
                            f"{scen['id']}: {e['id']} does not cross V2->V1 "
                            f"(min dist {d_crit:.1f} > hw {e['half_width_m']})")
                    if d_rec <= e["half_width_m"]:
                        errors.append(
                            f"{scen['id']}: {e['id']} intersects V3->V1 "
                            f"(min dist {d_rec:.1f} <= hw {e['half_width_m']})")

    print(f"audited {checks} geometry objects across {len(scenarios)} scenarios")
    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("AUDIT_EXP3_SCENARIOS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
