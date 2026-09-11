# Experiment 2 — Cross-Site Smoke Report v2 (Site B / Site C, adapted)

MODIFIED SMOKE (post site-adaptation): 2 sites x 6 C2/C3 scenarios (one per failure family) x 1 seed x 4 managers = 48 runs. The site-adapted timeline (t_failure = 300 + floor(air_eta/2): Site B 322 s, Site C 383 s) and the re-derived F2/F5/F6 geometry are in effect and verified below. NOT a primary dataset; the frozen canonical Experiment-2 dataset (`runs/experiment2/`) is untouched.

| site | family | manager observations |
|---|---|---|
| site_b_amsterdam | F1 | B0: comp=541 affected=False pre/post=2/1 viol=True dmg=0; B1: comp=461 affected=True pre/post=2/1 viol=False dmg=0; B2: comp=461 affected=True pre/post=2/1 viol=False dmg=0; B4b: comp=461 affected=True pre/post=2/1 viol=False dmg=0 |
| site_b_amsterdam | F2 | B0: comp=541 affected=False pre/post=2/2 viol=True dmg=0; B1: comp=461 affected=True pre/post=2/1 viol=False dmg=0; B2: comp=461 affected=True pre/post=2/1 viol=False dmg=0; B4b: comp=461 affected=True pre/post=2/1 viol=False dmg=0 |
| site_b_amsterdam | F3 | B0: comp=541 affected=False pre/post=2/0 viol=True dmg=1; B1: comp=563 affected=True pre/post=2/0 viol=True dmg=2; B2: comp=563 affected=True pre/post=2/0 viol=True dmg=2; B4b: comp=563 affected=True pre/post=2/0 viol=True dmg=2 |
| site_b_amsterdam | F4 | B0: comp=541 affected=False pre/post=2/0 viol=True dmg=0; B1: comp=563 affected=True pre/post=2/0 viol=True dmg=1; B2: comp=563 affected=True pre/post=2/0 viol=True dmg=1; B4b: comp=563 affected=True pre/post=2/0 viol=True dmg=1 |
| site_b_amsterdam | F5 | B0: comp=541 affected=False pre/post=2/2 viol=True dmg=0; B1: comp=461 affected=True pre/post=2/1 viol=False dmg=0; B2: comp=461 affected=True pre/post=2/1 viol=False dmg=0; B4b: comp=461 affected=True pre/post=2/1 viol=False dmg=0 |
| site_b_amsterdam | F6 | B0: comp=541 affected=False pre/post=2/2 viol=True dmg=0; B1: comp=461 affected=True pre/post=2/1 viol=False dmg=1; B2: comp=461 affected=True pre/post=2/1 viol=False dmg=1; B4b: comp=461 affected=True pre/post=2/1 viol=False dmg=1 |
| site_c_edmonton | F1 | B0: comp=610 affected=False pre/post=2/1 viol=True dmg=0; B1: comp=581 affected=True pre/post=2/1 viol=True dmg=0; B2: comp=581 affected=True pre/post=2/1 viol=True dmg=0; B4b: comp=581 affected=True pre/post=2/1 viol=True dmg=0 |
| site_c_edmonton | F2 | B0: comp=610 affected=False pre/post=2/2 viol=True dmg=0; B1: comp=581 affected=True pre/post=2/1 viol=True dmg=0; B2: comp=581 affected=True pre/post=2/1 viol=True dmg=0; B4b: comp=581 affected=True pre/post=2/1 viol=True dmg=0 |
| site_c_edmonton | F3 | B0: comp=610 affected=False pre/post=2/0 viol=True dmg=1; B1: comp=693 affected=True pre/post=2/0 viol=True dmg=2; B2: comp=693 affected=True pre/post=2/0 viol=True dmg=2; B4b: comp=693 affected=True pre/post=2/0 viol=True dmg=2 |
| site_c_edmonton | F4 | B0: comp=610 affected=False pre/post=2/0 viol=True dmg=0; B1: comp=693 affected=True pre/post=2/0 viol=True dmg=1; B2: comp=693 affected=True pre/post=2/0 viol=True dmg=1; B4b: comp=693 affected=True pre/post=2/0 viol=True dmg=1 |
| site_c_edmonton | F5 | B0: comp=610 affected=False pre/post=2/2 viol=True dmg=0; B1: comp=581 affected=True pre/post=2/1 viol=True dmg=0; B2: comp=581 affected=True pre/post=2/1 viol=True dmg=0; B4b: comp=581 affected=True pre/post=2/1 viol=True dmg=0 |
| site_c_edmonton | F6 | B0: comp=610 affected=False pre/post=2/2 viol=True dmg=0; B1: comp=581 affected=True pre/post=2/1 viol=True dmg=1; B2: comp=581 affected=True pre/post=2/1 viol=True dmg=1; B4b: comp=581 affected=True pre/post=2/1 viol=True dmg=1 |

## Verdict: PASS (48/48 runs pass all smoke checks)

Checks per run: run complete + full artifact contract; failure event fires at the site-adapted failure time; failure trace coherent (family/time/target/candidate counts/local contingency/manager trigger); simulator clock unaffected; critical mission terminal; no silent action substitution (normalized == executed). Superseded v1-smoke cells (pre-adaptation configs) are skipped by the frozen-config hash guard.

## Site-adaptation verification (v2 smoke, measured)

- **Site-B failure-time adaptation WORKS:** with t_failure=322 s (= 300 + floor(44.1/2)), every C2/C3 family now interrupts the AIRBORNE critical chain on Site B (affected=True for B1/B2/B4b across F1/F2/F3/F4/F5/F6) and the backup recovers it by air — F1/F2/F5/F6-C2 complete at 461 s, meeting the 480-s deadline. The canonical t=360 design's completion-before-failure defect (v1 smoke: comp=340, affected=False) is resolved.
- **Site-C geometry re-derivation WORKS:** F5-C2 radius 80 m and F6-C2 half-width 88 m (heading 197 deg, parallel to the V3->V1 recovery leg) pass the geometry audit (recovery segment clear by >= 47 m) and produce the intended C2 behaviour: affected=True, air recovery at 581 s — which MISSES the 480-s deadline (Site-C operating point: the long V3->V1 recovery leg). This is a real site-specific difference, measured, not assumed.
- **Site-C deadline note for the full matrix:** C2 air recovery on Site C (~198 s) exceeds the frozen 180-s slack, so Site-C C2 cells will show recovery success WITH deadline violation — the frozen metrics capture this honestly; no deadline re-tuning.
- **Ground contexts:** Site B MEDIUM = +88.69 %, Site C MEDIUM = +34.76 %; B0 ground completion 541 s (Site B) / 610 s (Site C), deadline violated on both — the frozen ground-side trade-off holds on every site.
- Failure geometry for F2/F5/F6 is derived per site and audited in `outputs/experiment2/cross_site_geometry_audit.json`; F1/F3/F4 configurations are geometry-free and translate 1:1 with the site-adapted failure time.
- **Smoke verdict: 48/48 runs pass all checks** (run complete + artifact contract, failure event at the adapted time, trace coherent, clock sync, mission terminal, no silent substitution).
