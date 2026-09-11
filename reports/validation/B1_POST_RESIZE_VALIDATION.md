# B1 Post-Resize Validity

Re-confirms B1 remains a legitimate critical ground-disruption point after the
3.2 km crop. Source: `tools/validate_b1.py` →
`outputs/b1_post_resize_validation.csv`.

## Results

| Metric | Value |
|--------|-------|
| B1 edge | `148377677#0` |
| ETA baseline (D1→H1 free-flow) | 131.838 s |
| ETA B1 closed | 181.763 s |
| **relative increase** | **+37.87 %** |
| has detour | ✅ True |
| H1 reachable after closure | ✅ True |
| B1 on baseline D1→H1 route | ✅ True |
| B1 interior to bbox (min side margin) | ✅ True (860.3 m) |

## Four required checks

1. **Detour exists after B1 closure** — ✅ post-closure ETA rises from 131.838 s
   to 181.763 s (a +49.9 s detour), i.e. the router finds an alternative route.
2. **H1 never becomes unreachable** — ✅ `ETA_B1_closed = 181.763 s` (finite,
   positive), the hospital remains reachable.
3. **ETA clearly increases** — ✅ +37.87 % ≫ 15 % warning threshold.
4. **Not an artificial crop-boundary effect** — ✅ B1 is interior to the bbox
   (≥ 860 m from every side) and is **the same edge** (`148377677#0`) that was the
   bottleneck in the pre-crop 5×5 network (unchanged by the crop).

## Verdict

**PASS** — B1 is a valid critical ground-disruption point. Note: the +37.87 %
increase is a *medium* accessibility degradation, intentionally **below** the
GD3 2.0× threshold (GD3 is not triggered; the smoke test uses the explicit
B1-closure event GD1 at t=300, per spec §12.3). Per instruction, B1 was not
replaced merely to chase the 2× bar.
