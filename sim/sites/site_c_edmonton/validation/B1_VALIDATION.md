# B1 Disruption Validity — Edmonton, Alberta, Canada (site_c_edmonton)

Re-confirms the site's B1 is a legitimate critical ground-disruption point,
following the Site-A method (`site_a_suzhou/validation/B1_POST_RESIZE_VALIDATION.md`).
Source: `tools/cross_site_b1_validation.py` + the canonical site config +
candidate analysis (`outputs/cross_site/candidates/…/analysis.json`).

## Results

| Metric | Value |
|--------|-------|
| B1 edge | `471736601#0-AddedOnRampEdge` |
| B1 description | ranked critical road link (road) |
| ETA baseline (D1→H1 free-flow) | 230.137 s |
| ETA B1 closed | 310.135 s |
| **relative increase** | **+34.76 %** |
| has detour | True (23 edges) |
| H1 reachable after closure | True |
| B1 interior to bbox (min side margin) | 1565.5 m (>= 300 m) |
| detour boundary share | 0.000 (<= 0.30) |

## Four required checks

1. **Detour exists after B1 closure** — ✓ post-closure ETA rises
   from 230.137 s to 310.135 s (a +80.0 s detour), i.e. the
   router finds an alternative route.
2. **H1 never becomes unreachable** — ✓ `ETA_B1_closed =
   310.135 s` (finite, positive), the hospital remains reachable.
3. **ETA clearly increases** — ✓ +34.76 % >= 15 %
   warning threshold.
4. **Not an artificial bbox-boundary effect** — ✓ B1 sits >=
   1565 m from every bbox side (>= 300 m) and the detour
   keeps 0.000 of its length in the boundary band
   (<= 0.30).

## Verdict

**PASS** — the site's B1 is a valid critical ground-disruption point for the
cross-site Experiment-1 reproduction
(`tools/run_experiment1_cross_site.py`).
