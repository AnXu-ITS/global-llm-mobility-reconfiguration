# CROSS-SITE EXPERIMENT-1 — FULL SCALE (Site B / Site C)

Site-A process applied to the two cross-site testbeds at the SAME experimental
scale as the frozen primary, per site:

- **primary**: 12 scenarios × 20 frozen seeds × 4 managers (B0/B1/B2/B4b) = 960
- **B4a ablation**: 6 scenarios × 10 seeds = 60
- **total per site**: 1020 · **both sites**: 2040 · **0 excluded**

Statistical unit = scenario × seed (n = 20 per scenario), identical to Site A.
Run dirs: `runs/experiment1_cross_site/<site_id>/<scenario>/seed<seed>/<manager>/`.

The earlier 8 single-seed smoke runs are preserved (superseded) in
`runs/experiment1_cross_site_legacy_smoke/`.

## Per-site disruption severity (site-adapted, same factor STRUCTURE as Site A)

| level | Site A (frozen) | Site B Amsterdam | Site C Edmonton |
|---|---|---|---|
| LOW = [B2] | +15.43 % | +17.78 % (`7370322`) | +22.14 % (`1427039799`) |
| MEDIUM = [B1] | +37.87 % | +88.69 % (`379148751#2` Berlagebrug) | +34.76 % (`471736601#0-AddedOnRampEdge`) |
| HIGH = [B1,B2] + degradation | +73.41 % | measured (ground ≈ 397 s) | measured (ground ≈ 380 s) |

## Per-site primary results (pooled n = 240, mean [95 % CI])

### Site B — Amsterdam (water-barrier / bridge-constrained)

| manager | completion | deadline viol | damage | air | unnecessary air | saved vs B0 |
|---|---|---|---|---|---|---|
| B0 | 262.7 [249.7, 275.7] | 50.0 % | 0.000 | 0 % | 0 % | 0.0 |
| B1 | 47.7 [46.6, 48.8] | **0 %** | 0.500 | 100 % | 0 % | 215.0 |
| B2 | 47.7 [46.6, 48.8] | **0 %** | 0.500 | 100 % | 0 % | 215.0 |
| B4b | 49.1 [47.2, 50.9] | **0 %** | 0.487 | 98.8 % | 0 % | 213.6 |

### Site C — Edmonton (sparse suburban / polycentric)

| manager | completion | deadline viol | damage | air | unnecessary air | saved vs B0 |
|---|---|---|---|---|---|---|
| B0 | 323.7 [318.4, 329.0] | 83.3 % | 0.000 | 0 % | 0 % | 0.0 |
| B1 | 168.3 [166.8, 169.7] | 10.0 % | 0.500 | 100 % | 0 % | 155.4 |
| B2 | 168.3 [166.8, 169.7] | 10.0 % | 0.500 | 100 % | 0 % | 155.4 |
| B4b | 168.7 [167.1, 170.2] | 10.0 % | 0.500 | 100 % | 0 % | 155.0 |

## B2 vs B4b (paired, Holm-corrected)

**No significant B2↔B4b divergence on either site** (all Holm p ≥ 0.33; the
largest per-scenario gaps are XB_L_C_high 55.4 vs 61.6 s, XB_L_H_high 55.4 vs
65.9 s, XC_M_C_high 175.6 vs 178.6 s — all n.s.). On Site B, B1 ≡ B2 exactly
and B4b is marginally more conservative (98.8 % air vs 100 %, damage 0.487 vs
0.500 — it takes GROUND_FALLBACK in 3/240 runs).

The Site-A `E1_H_H_high` divergence (B4b preempts where B2 falls back to
ground) **does not replicate** on Sites B/C — see interpretation below.

## B4a vs B4b ablation (n = 60 paired cells)

| site | B4a (no candidate table) | B4b (with table) | paired p |
|---|---|---|---|
| Site B | comp 53.1 s, air ≈ 100 % | comp ≈ 48.9 s, air ≈ 100 % | t p = 0.379 (n.s.), all McNemar n.s. |
| Site C | comp 167.7 s, air 100 % | comp 168.7 s, air 100 % | identical decisions in all 60 cells |

The Site-A ablation effect (B4a degrades to damaging air-first) **does not
replicate** on B/C: there the air-vs-ground decision is so strongly
air-favourable that the candidate table is behaviourally inert.

## Interpretation — the trade-off region is site-dependent

| site | ground range vs air | where manager choice matters |
|---|---|---|
| Site A Suzhou | ground 152–229 s vs air ≈ 110 s | **comparable** → B2 preserves service (ground fallback 44 %), B4b trades speed↔service in E1_H_H_high; candidate table load-bearing |
| Site B Amsterdam | ground 150–397 s vs air ≈ 40 s | **air dominates** → all coordinated managers air-first (0.5 preemption damage in high workload); B2 ≡ B1; B4b ≈ B2 |
| Site C Edmonton | ground 230–380 s vs air ≈ 161 s | **air dominates** → all coordinated managers air-first; B1 ≡ B2 ≡ B4b |

Three sites therefore instantiate three regions of the speed↔service-
preservation space: only where ground and air are comparable (Site A) do the
policies diverge; where air dominates (Sites B/C) the frozen optimizer, the
rule baseline and the candidate-informed LLM converge, and the LLM's candidate
table adds no behavioural value.

## Artifacts

- runs: `runs/experiment1_cross_site/` (2040 runs; legacy smoke preserved in
  `runs/experiment1_cross_site_legacy_smoke/`)
- matrices: `config/experiment1_site_b_matrix.yaml`,
  `config/experiment1_site_c_matrix.yaml`
- runner: `tools/run_experiment1_cross_site.py`
- analyses: `outputs/site_b_amsterdam/`, `outputs/site_c_edmonton/`
  (primary_analysis.json, B2_vs_B4b_tradeoff.csv, ablation_b4a_vs_b4b.json)
- three-site comparison: `outputs/cross_site/three_site_comparison.csv`,
  `reports/cross_site/THREE_SITE_COMPARISON.md`
- B2 selection evidence: `outputs/cross_site/site_b_disruption_ranking.csv`,
  `site_c_disruption_ranking.csv`
