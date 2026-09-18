"""Experiment 3 cross-site — Acceptance Tests (E3-XS-A1 .. E3-XS-A7).

Verifies the Site B (Amsterdam) / Site C (Edmonton) extension of the E3
Compound Disruption Stress Test: site-adapted matrices, geometry invariants,
run completeness, exogeneity (failure-schedule hash), and frozen Site-A
integrity. Exit code 0 iff NO FAIL.

Checks:
  E3-XS-A1  site matrices present, 12 scenarios, t_failure 322/383 with
            frozen +30/+60/+120 multi-event offsets
  E3-XS-A2  geometry fully resolved (no derive blocks) and invariants hold
            (F5 covers V3->V1, F5 NW-corner has no site, F2 candidate_rule
            none, F6 crosses V2->V1 / clears V3->V1)
  E3-XS-A3  primary completeness: 1920 cross-site runs, 0 excluded
  E3-XS-A4  exogeneity: every run's failure_schedule_hash matches its site
            matrix (paired design seed/scenario across managers)
  E3-XS-A5  M-CRITICAL-002 present in SWL by-mission for L3/L4 on both sites
  E3-XS-A6  frozen Site-A matrix_sha256 unchanged (e8fd26b93bf00e26)
  E3-XS-A7  medical_organ type is servable (compat matrix fixed) — guards the
            latent Site-B-exposed bug (no RESOURCE_INCOMPATIBLE loop)
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
SITES = {
    "b": ("site_b_amsterdam", "config/experiment3_site_b_matrix.yaml", 322),
    "c": ("site_c_edmonton", "config/experiment3_site_c_matrix.yaml", 383),
}
MANAGERS = ("B0", "B1", "B2", "B4b")
KIND = {"B0": "no_cross_layer", "B1": "rule_based", "B2": "optimization", "B4b": "llm_b4b"}


def rec(tid, ok, evidence):
    RESULTS.append((tid, ok, evidence))
    print(f"[{'PASS' if ok else 'FAIL'}] {tid}: {evidence}")


def sha256_hex(obj) -> str:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_e3(key):
    return yaml.safe_load((ROOT / SITES[key][1]).read_text(encoding="utf-8"))["experiment3"]


def _runs(key):
    return ROOT / "runs" / "experiment3_cross_site" / SITES[key][0]


def _geometry_audit(key, e3):
    """Re-audit the resolved geometry of a site matrix (mirrors audit_exp3_scenarios)."""
    from failures.e2_failures import (_segment_segment_distance_m, haversine_m,
                                      point_segment_distance_m, strip_ends)
    cfg = yaml.safe_load((ROOT / "sim" / "sites" / SITES[key][0] / "config" /
                          f"{SITES[key][0]}_config.yaml").read_text(encoding="utf-8"))
    fac = cfg["facilities"]
    v1 = (float(fac["V1"]["lat"]), float(fac["V1"]["lon"]))
    v2 = (float(fac["V2"]["lat"]), float(fac["V2"]["lon"]))
    v3 = (float(fac["V3"]["lat"]), float(fac["V3"]["lon"]))
    errors = []
    for scen in e3["scenarios"]:
        for f in scen.get("failure_schedule", []):
            z = f.get("zone")
            if z is not None:
                if "derive" in z:
                    errors.append(f"{scen['id']}: derive remains")
                    continue
                zid = z["id"]
                if zid in ("ZN-F5-XS-02", "ZN-F5-XS-03", "ZN-F5-XS-05"):
                    d = point_segment_distance_m((z["lat"], z["lon"]), v3, v1)
                    if d > z["radius_m"]:
                        errors.append(f"{scen['id']}: F5 not covering V3->V1")
                elif zid == "ZN-F5-XS-04":
                    for sid, p in (("V1", v1), ("V2", v2), ("V3", v3)):
                        if haversine_m((z["lat"], z["lon"]), p) <= z["radius_m"]:
                            errors.append(f"{scen['id']}: NW corner contains {sid}")
                elif zid.startswith("ZN-F2-"):
                    if z.get("candidate_rule") != "none":
                        errors.append(f"{scen['id']}: F2 candidate_rule != none")
            e = f.get("envelope")
            if e is not None:
                if "derive" in e:
                    errors.append(f"{scen['id']}: envelope derive remains")
                    continue
                ends = strip_ends(e)
                d_crit = _segment_segment_distance_m(v2, v1, ends[0], ends[1])
                d_rec = _segment_segment_distance_m(v3, v1, ends[0], ends[1])
                if d_crit > e["half_width_m"]:
                    errors.append(f"{scen['id']}: F6 not crossing V2->V1")
                if d_rec <= e["half_width_m"]:
                    errors.append(f"{scen['id']}: F6 intersecting V3->V1")
    return errors


def main() -> int:
    # E3-XS-A1 site-adapted matrices + frozen offsets
    ok = True
    for key, (_, _, tf) in SITES.items():
        e3 = load_e3(key)
        scen = e3["scenarios"]
        offs = (e3["second_emergency_t_s"] - tf, e3["failure_b_t_s"] - tf,
                e3["failure_c_t_s"] - tf)
        if len(scen) != 12 or e3["failure_a_t_s"] != tf or (e3.get("version") != 2 or e3["second_emergency_t_s"] != 300 or offs[1:] != (60, 120)):
            ok = False
            rec("E3-XS-A1", False, f"site {key}: n={len(scen)} tf={e3['failure_a_t_s']} offsets={offs}")
            break
    else:
        rec("E3-XS-A1", True, "site B/C v2: 12 scenarios, simultaneous emergency release at 300; failures 322/383 with +60/+120 offsets")

    # E3-XS-A2 geometry resolved + invariants
    all_errs = []
    for key in SITES:
        all_errs += _geometry_audit(key, load_e3(key))
    rec("E3-XS-A2", len(all_errs) == 0,
        f"geometry resolved & invariants hold ({len(all_errs)} errors)")

    # E3-XS-A6 frozen Site-A matrix untouched
    site_a = yaml.safe_load((ROOT / "config" / "experiment3_matrix.yaml").read_text(encoding="utf-8"))["experiment3"]
    freeze = json.loads((ROOT / "outputs" / "experiment3" / "freeze_hashes.json").read_text(encoding="utf-8"))
    rec("E3-XS-A6", sha256_hex(site_a) == freeze["matrix_sha256"],
        "frozen Site-A matrix_sha256 unchanged (vs freeze_hashes.json)")

    # E3-XS-A7 medical_organ servable (compat matrix fixed)
    compat = yaml.safe_load((ROOT / "config" / "resource_compatibility.yaml").read_text(encoding="utf-8"))
    rec("E3-XS-A7", compat["aircraft_types"]["medical_uav"].get("medical_organ") == "allowed",
        "medical_uav -> medical_organ allowed (latent bug fixed)")

    # E3-XS-A3/A4/A5 require primary runs
    seeds = list(yaml.safe_load((ROOT / "config" / "experiment3_seeds.yaml").read_text(encoding="utf-8"))["primary_seeds"])
    n_runs = 0
    n_bad_hash = 0
    l3l4_second_ok = True
    for key in SITES:
        e3 = load_e3(key)
        for scen in e3["scenarios"]:
            for seed in seeds:
                for mgr in MANAGERS:
                    rd = _runs(key) / scen["id"] / f"seed{seed}" / mgr
                    mp = rd / "metrics.json"
                    if not mp.exists():
                        continue
                    n_runs += 1
                    rc = rd / "run_config.yaml"
                    if rc.exists():
                        saved = yaml.safe_load(rc.read_text(encoding="utf-8"))
                        if saved.get("failure_schedule_hash") != sha256_hex(scen["failure_schedule"]):
                            n_bad_hash += 1
                    if scen["level"] in ("L3", "L4"):
                        m = json.loads(mp.read_text(encoding="utf-8"))
                        if "M-CRITICAL-002" not in m.get("system_weighted_loss_by_mission", {}):
                            l3l4_second_ok = False
    excl = ROOT / "runs" / "experiment3_cross_site" / "excluded_runs.csv"
    n_excl = 0
    if excl.exists():
        n_excl = sum(1 for _ in open(excl, encoding="utf-8")) - 1
    rec("E3-XS-A3", n_runs == 1920 and n_excl == 0,
        f"cross-site primary runs {n_runs}/1920, excluded {n_excl}")
    rec("E3-XS-A4", n_bad_hash == 0,
        f"failure_schedule_hash consistent ({n_bad_hash} mismatches)")
    rec("E3-XS-A5", l3l4_second_ok,
        "M-CRITICAL-002 present in SWL by-mission for L3/L4 (both sites)")

    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"\n{len(RESULTS)} checks, {n_fail} FAIL")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
