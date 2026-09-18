"""Finalize E3 v2: completeness check + v1-vs-v2 SWL comparison + key audit checks.

Run AFTER both re-runs finish (Site A + cross-site). Read-only; does not modify
runner/config/frozen artifacts. Outputs a markdown summary to stdout and to
outputs/experiment3/e3_v2_finalization.md.

Checks:
  1. Completeness: every (scenario, seed, manager) has metrics.json for Site A
     (12x20x4=960) and cross-site (2x12x20x4=1920).
  2. matrix_version == 2 on every recorded run_config.yaml.
  3. v1-vs-v2 mean SWL per scenario (Site A), using archive/experiment3_v1 as v1.
  4. Audit P0-1 case check: background missions are not charged cancellation in v2.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE_A = ROOT / "runs" / "experiment3"
XSITE = ROOT / "runs" / "experiment3_cross_site"
ARCHIVE = ROOT / "archive" / "experiment3_v1" / "runs" / "experiment3"
OUT = ROOT / "outputs" / "experiment3"
MANAGERS = ("B0", "B1", "B2", "B4b")

SITES = {
    "site_b_amsterdam": ROOT / "config" / "experiment3_site_b_matrix.yaml",
    "site_c_edmonton": ROOT / "config" / "experiment3_site_c_matrix.yaml",
}


def load_seeds():
    return list(yaml.safe_load(
        (ROOT / "config" / "experiment3_seeds.yaml").read_text(encoding="utf-8"))["primary_seeds"])


def load_scenarios(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))["experiment3"]["scenarios"]


def swl(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("system_weighted_loss")
    except Exception:
        return None


def main() -> int:
    seeds = load_seeds()
    sa_scen = load_scenarios(ROOT / "config" / "experiment3_matrix.yaml")
    lines: list[str] = []
    lines.append("# Experiment 3 v2 — Finalization Report\n")

    # 1. completeness
    lines.append("## 1. Completeness\n")
    missing_sa, missing_xs = [], []
    for s in sa_scen:
        for seed in seeds:
            for m in MANAGERS:
                if not (SITE_A / s["id"] / f"seed{seed}" / m / "metrics.json").exists():
                    missing_sa.append(f"{s['id']}/{seed}/{m}")
    for site_id, matrix in SITES.items():
        for s in load_scenarios(matrix):
            for seed in seeds:
                for m in MANAGERS:
                    if not (XSITE / site_id / s["id"] / f"seed{seed}" / m / "metrics.json").exists():
                        missing_xs.append(f"{site_id}/{s['id']}/{seed}/{m}")
    lines.append(f"- Site A: {960 - len(missing_sa)}/960 complete; missing {len(missing_sa)}")
    lines.append(f"- Cross-site: {1920 - len(missing_xs)}/1920 complete; missing {len(missing_xs)}")
    for x in missing_sa[:40]:
        lines.append(f"  - MISSING SiteA {x}")
    for x in missing_xs[:40]:
        lines.append(f"  - MISSING xsite {x}")
    if len(missing_sa) > 40:
        lines.append(f"  - ... {len(missing_sa) - 40} more Site A missing")
    if len(missing_xs) > 40:
        lines.append(f"  - ... {len(missing_xs) - 40} more cross-site missing")

    # 2. matrix_version
    lines.append("\n## 2. matrix_version guard\n")
    bad_ver = 0
    for root in (SITE_A, XSITE):
        for rc in root.rglob("run_config.yaml"):
            d = yaml.safe_load(rc.read_text(encoding="utf-8"))
            if d.get("matrix_version") != 2:
                bad_ver += 1
                lines.append(f"  - wrong version: {rc.relative_to(ROOT)} -> {d.get('matrix_version')}")
    lines.append(f"- runs with matrix_version != 2: {bad_ver}")

    # 3. v1 vs v2 mean SWL (Site A)
    lines.append("\n## 3. Site A v1 vs v2 mean SWL (per scenario, all seeds x managers)\n")
    lines.append("| scenario | v1 mean | v2 mean | Δ |")
    lines.append("|---|---|---|---|")
    for s in sa_scen:
        v1v, v2v = [], []
        for seed in seeds:
            for m in MANAGERS:
                v1v.append(swl(ARCHIVE / s["id"] / f"seed{seed}" / m / "metrics.json"))
                v2v.append(swl(SITE_A / s["id"] / f"seed{seed}" / m / "metrics.json"))
        v1v = [x for x in v1v if x is not None]
        v2v = [x for x in v2v if x is not None]
        if not v1v or not v2v:
            lines.append(f"| {s['id']} | n/a | n/a | n/a |")
            continue
        m1 = sum(v1v) / len(v1v)
        m2 = sum(v2v) / len(v2v)
        lines.append(f"| {s['id']} | {m1:.1f} | {m2:.1f} | {m2 - m1:+.1f} |")

    # 4. audit P0-1 background-mission check (Site A, all completed runs)
    lines.append("\n## 4. Audit P0-1: background missions charged in v2?\n")
    charged = 0
    checked = 0
    for p in SITE_A.rglob("metrics.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        bm = d.get("system_weighted_loss_by_mission", {})
        for k, v in bm.items():
            if k in ("M-L-001", "M-M-001", "M-P-001") and v != 0:
                charged += 1
        checked += 1
    lines.append(f"- completed Site A runs checked: {checked}")
    lines.append(f"- runs where a background mission has non-zero SWL: {charged} "
                 f"(should be 0; a positive count means a genuinely damaged background service)")

    text = "\n".join(lines) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "e3_v2_finalization.md").write_text(text, encoding="utf-8")
    print(text)
    return 1 if (missing_sa or missing_xs or bad_ver) else 0


if __name__ == "__main__":
    sys.exit(main())
