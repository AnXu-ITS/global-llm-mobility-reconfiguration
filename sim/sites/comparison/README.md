# comparison/ — cross-site comparison assets

Canonical cross-site comparison directory. Contents:

| File | Purpose |
|---|---|
| `site_morphology_comparison.csv` | three-row morphology metrics (Site A/B/C) |
| `plot_three_sites.py` | THE unified plotting pipeline (single visual grammar) |
| `three_site_cross_validation_v2.png` | debug/annotated three-panel figure |
| `three_site_cross_validation_paper.png` | publication version (300 DPI PNG) |
| `three_site_cross_validation_paper.pdf` | publication version (vector PDF) |
| `plot_qa.json` | label-overlap geometry + style self-check |
| `visual_qa.json` | pixel-level QA (band coverage, color classes) |
| `image_acceptance_tests.csv` / `.md` | IMG-T1..IMG-T15 results |
| `SITE_DATA_INVENTORY.md` | per-site data inventory |
| `LEGACY_SITE_PATH_AUDIT.md` | old path -> canonical path audit |
| `SITE_REFINEMENT_FINAL_REPORT.md` | final refinement report |

Regenerate everything:

```powershell
python sim\sites\comparison\plot_three_sites.py
python tools\cross_site_img_acceptance.py
```

Visual grammar (single source of truth: `STYLE` dict in plot_three_sites.py):
roads thin gray -> water light blue -> primary ground route solid thick red ->
primary detour dashed thick pink -> primary low-altitude dotted green ->
auxiliary ground thin semi-transparent brown -> facilities (primary filled,
auxiliary hollow) -> B1 orange X.
