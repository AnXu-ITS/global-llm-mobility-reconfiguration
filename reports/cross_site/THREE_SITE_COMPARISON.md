# THREE-SITE EXPERIMENT-1 COMPARISON (same scale)

All three sites share the SAME experimental scale: 12 scenarios x
20 frozen seeds x 4 managers = 960 primary runs + 60 B4a ablation runs
per site. Statistical unit = scenario x seed (n=20 per scenario).

| site (morphology) | manager | comp (95% CI) | viol | damage | air | unnec | saved vs B0 |
|---|---|---|---|---|---|---|---|---|
| **site_a_suzhou** — Suzhou, China, meshed / mixed urban (single-link bottleneck) | | | | | | | |
| | B0 | 187.667 [183.629, 191.705] | 0.333 | 0.0 | 0.0 | 0.0 | 0.0 |
| | B1 | 160.775 [154.276, 167.274] | 0.25 | 0.5 | 1.0 | 0.333 | 26.892 |
| | B2 | 147.617 [142.15, 153.083] | 0.167 | 0.058 | 0.558 | 0.0 | 40.05 |
| | B4b | 146.633 [141.409, 151.857] | 0.167 | 0.133 | 0.633 | 0.05 | 41.033 |
| **site_b_amsterdam** — Amsterdam, NL, water-barrier / bridge-constrained | | | | | | | |
| | B0 | 262.667 [249.67, 275.663] | 0.5 | 0.0 | 0.0 | 0.0 | 0.0 |
| | B1 | 47.7 [46.618, 48.782] | 0.0 | 0.5 | 1.0 | 0.0 | 214.967 |
| | B2 | 47.7 [46.618, 48.782] | 0.0 | 0.5 | 1.0 | 0.0 | 214.967 |
| | B4b | 49.096 [47.243, 50.949] | 0.0 | 0.487 | 0.988 | 0.0 | 213.571 |
| **site_c_edmonton** — Edmonton, CA, sparse suburban / polycentric | | | | | | | |
| | B0 | 323.667 [318.371, 328.962] | 0.833 | 0.0 | 0.0 | 0.0 | 0.0 |
| | B1 | 168.275 [166.828, 169.722] | 0.1 | 0.5 | 1.0 | 0.0 | 155.392 |
| | B2 | 168.275 [166.828, 169.722] | 0.1 | 0.5 | 1.0 | 0.0 | 155.392 |
| | B4b | 168.65 [167.074, 170.226] | 0.1 | 0.5 | 1.0 | 0.0 | 155.017 |

## Reading notes

- Site A = frozen primary (`runs/experiment1_final`); Sites B/C =
  cross-site reproduction at identical scale
  (`runs/experiment1_cross_site/<site_id>/`).
- Severity magnitudes differ per site by design (Amsterdam +88.69 %
  water-barrier penalty vs Suzhou +73.41 % vs Edmonton +34.76 %); the
  factor STRUCTURE (LOW/MEDIUM/HIGH x CRITICAL/HIGH x low/high workload)
  is identical.
- Machine-readable: `outputs\cross_site\three_site_comparison.csv`
