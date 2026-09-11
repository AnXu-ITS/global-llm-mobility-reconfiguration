# Rule Manager Decision Trace (Phase 2)

Every manager decision is fully explainable and replayable. Each decision records
its trigger, the per-candidate feasibility evaluation, the ground fallback
option, the selection, and the reason — serialised to
`runs/phase2_rule_manager/<case>/manager_outputs.jsonl`.

The rule engine is `managers/rule_based.py` (B1). Rules, in strict order:

1. CRITICAL > HIGH > NORMAL > LOW
2. resource must be AVAILABLE or explicitly reassignable
3. never interrupt a higher-priority mission for a lower-priority one
4. must satisfy feasibility constraints (battery / endurance / C2 / commandability / landing)
5. among feasible resources choose the minimum estimated mission completion time
6. tie → largest battery / endurance margin
7. no feasible air → ground fallback
8. air and ground both infeasible → DELAY / CANCEL

---

## Canonical case C2-B (critical support aircraft loses C2)

### DECISION D001 (t = 300) — B1 closure + new CRITICAL mission

**trigger:** `["B1 closure (ground disruption)", "new CRITICAL mission"]`

**target mission:** `M-CRITICAL-001` — medical_blood, CRITICAL, V2 → V1, deadline 900 s

**candidate resources:**

| resource | type | verdict | detail |
|----------|------|---------|--------|
| EVTOL-01 | AIR | ❌ rejected | busy non-reassignable (passenger service V2↔V1) |
| L-UAV-01 | AIR | ❌ rejected | busy non-reassignable (logistics service V2↔V3) |
| M-UAV-01 | AIR | ✅ feasible | ETA **229.1 s** (V1 → V2 → V1) |
| M-UAV-02 | AIR | ✅ feasible | ETA **114.5 s** (at V2, direct V2 → V1) |
| GROUND   | GROUND | ✅ feasible | ETA **181.8 s** (B1-closed detour) |

**selected:** `M-UAV-02` (AIR)

**reason:** minimum feasible estimated mission completion time (114.5 s < 181.8 s ground, < 229.1 s M-UAV-01).

**action:** `DISPATCH M-UAV-02 → M-CRITICAL-001 (V2 → V1)`, passed FeasibilityChecker (`valid=true`).

---

### DECISION D002 (t = 360) — after C2 Lost Link on M-UAV-02

**trigger:** `["C2 lost link", "mission interrupted -> NEEDS_REPLAN"]`

**target mission:** `M-CRITICAL-001` — now NEEDS_REPLAN

**candidate resources:**

| resource | type | verdict | detail |
|----------|------|---------|--------|
| EVTOL-01 | AIR | ❌ rejected | busy non-reassignable |
| L-UAV-01 | AIR | ❌ rejected | busy non-reassignable |
| M-UAV-02 | AIR | ❌ rejected | **C2 status LOST (not commandable)** |
| M-UAV-01 | AIR | ✅ feasible | ETA **65.9 s** (V1 → V3 recover cargo → V1 deliver) |
| GROUND   | GROUND | ✅ feasible | ETA **181.8 s** |

**selected:** `M-UAV-01` (AIR backup)

**reason:** minimum feasible estimated mission completion time (65.9 s < 181.8 s ground). The lost aircraft is not commandable and is excluded.

**action:** `REASSIGN M-UAV-01 → M-CRITICAL-001 (route V3 → V1)`, passed FeasibilityChecker (`valid=true`).

**terminal state:** mission COMPLETED at t=420 by M-UAV-01 (backup); M-UAV-02 landed at V3 (contingency) at t=379.

---

## Case C2-A (ordinary logistics aircraft loses C2)

- D001 (t=300): identical to C2-B — `DISPATCH M-UAV-02 → M-CRITICAL-001 (V2 → V1)`.
- D002 (t=360): C2 lost on **L-UAV-01** (logistics). Its mission `M-L-001` → NEEDS_REPLAN. Manager **REASSIGNS** `M-L-001 → M-UAV-01` (route `[V3]`, resume at the recovery site). The CRITICAL mission is **unaffected** and completes normally at t=410 on M-UAV-02.

**Distinct system response:** a C2 loss on a NORMAL-priority logistics aircraft only triggers reconfiguration of the logistics mission; the CRITICAL medical mission continues untouched.

---

## Case C2-C (critical support aircraft loses C2, no backup)

- D001 (t=300): identical — `DISPATCH M-UAV-02 → M-CRITICAL-001`.
- D002 (t=360): C2 lost on M-UAV-02. `M-UAV-01` is **committed to a HIGH-priority medical transfer and non-reassignable** (no backup air). Manager has **no feasible air candidate** → rule 7 → **GROUND_FALLBACK** (ETA 181.8 s), completing at t=542.

**Distinct system response:** with no backup air resource, the manager correctly switches the CRITICAL mission to ground fallback (final mode = GROUND).

---

## Determinism note

For the same `scenario + seed + simulation_time`, the decision sequence is
deterministic: the manager is a pure function of the Global State, candidates
are iterated in sorted aircraft order, and ties are broken by a fixed key
(completion time, then endurance margin). `manager_outputs.jsonl` is
byte-identical across replays (see P2-T12).
