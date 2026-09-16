# B1 Disruption Validity — Amsterdam, Netherlands (site_b_amsterdam)

Re-confirms the site's B1 is a legitimate critical ground-disruption point,
following the Site-A method (`site_a_suzhou/validation/B1_POST_RESIZE_VALIDATION.md`).
Source: `tools/cross_site_b1_validation.py` + the canonical site config +
candidate analysis (`outputs/cross_site/candidates/…/analysis.json`).

## Results

| Metric | Value |
|--------|-------|
| B1 edge | `379148751#2` |
| B1 description | Berlagebrug (Amstel river crossing, embankment) |
| ETA baseline (D1→H1 free-flow) | 127.475 s |
| ETA B1 closed | 240.537 s |
| **relative increase** | **+88.69 %** |
| has detour | True (25 edges) |
| H1 reachable after closure | True |
| B1 interior to bbox (min side margin) | 635.4 m (>= 300 m) |
| detour boundary share | 0.000 (<= 0.30) |

## Four required checks

1. **Detour exists after B1 closure** — ✓ post-closure ETA rises
   from 127.475 s to 240.537 s (a +113.1 s detour), i.e. the
   router finds an alternative route.
2. **H1 never becomes unreachable** — ✓ `ETA_B1_closed =
   240.537 s` (finite, positive), the hospital remains reachable.
3. **ETA clearly increases** — ✓ +88.69 % >= 15 %
   warning threshold.
4. **Not an artificial bbox-boundary effect** — ✓ B1 sits >=
   635 m from every bbox side (>= 300 m) and the detour
   keeps 0.000 of its length in the boundary band
   (<= 0.30).

## Verdict

**PASS** — the site's B1 is a valid critical ground-disruption point for the
cross-site Experiment-1 reproduction
(`tools/run_experiment1_cross_site.py`).
