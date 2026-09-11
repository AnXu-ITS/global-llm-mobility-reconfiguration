# Phase 2 Acceptance Tests — Results

**Scenario:** S0 / `S0_3p2km_v1` (3.2 km × 3.2 km, 4-aircraft fleet)
**Manager:** Rule-Based Manager (B1) — no LLM
**Case suite:** C2-A (logistics C2 lost), C2-B (critical support C2 lost), C2-C (no backup)
**Verdict:** NO FAIL across P2-T1..P2-T12

| Test | Result | Evidence |
|------|--------|----------|
| P2-T1 | PASS | Phase-1 regression all PASS (1 WARNING: D1 snap 58.01 m) |
| P2-T2 | PASS | manager=rule_based, llm=None, manager decisions=2 (no deterministic test dispatch) |
| P2-T3 | PASS | validated 12 Global States against schema; errors=none |
| P2-T4 | PASS | manager_inputs.jsonl byte-identical: True (md5 7abd8845..) |
| P2-T5 | PASS | C2_LOST payload -> status=CONTINGENCY, c2=LOST, commandable=False, reassignable=False |
| P2-T6 | PASS | test_c2_local_contingency.py exit=0 |
| P2-T7 | PASS | MISSION_INTERRUPTED -> status=NEEDS_REPLAN (mission M-CRITICAL-001) |
| P2-T8 | PASS | REASSIGN actions=1, MISSION_COMPLETED=True |
| P2-T9 | PASS | ground fallback started=True, completed=True, final mode=GROUND |
| P2-T10 | PASS | all executed checks valid=True; new-type rejections=True |
| P2-T11 | PASS | 900 steps, all sync_ok=True, max clock error=0.000000s |
| P2-T12 | PASS | full Phase-2 replay byte-identical -> events.csv:same; ground_state.csv:same; air_state.csv:same; missions.csv:same; actions.csv:same; clock_sync.csv:same; manager_inputs.jsonl:same; manager_outputs.jsonl:same; feasibility_checks.jsonl:same; snapshots.jsonl:same |

## Key evidence files

- Canonical run: `runs/phase2_rule_manager/C2_B/`
- C2-A run: `runs/phase2_rule_manager/C2_A/`
- C2-C run (ground fallback): `runs/phase2_rule_manager/C2_C/`
- Replay: `runs/phase2_rule_manager/replay_{a,b}/`
- Schema: `schemas/global_state_v1.schema.json`

## Full Phase-2 closed loop (C2-B, canonical)

```
t=300  GD1 (B1 close) -> ground accessibility DEGRADED
t=300  NEW_CRITICAL_MISSION (M-CRITICAL-001, CRITICAL, V2->V1)
t=300  Rule Manager D001 -> DISPATCH M-UAV-02 (air, min ETA 114.5 s)
t=360  C2_LOST on M-UAV-02 -> CONTINGENCY / c2=LOST / commandable=false
t=360  LOCAL_CONTINGENCY -> RETURN to V3 (manager-independent)
t=360  MISSION_INTERRUPTED -> NEEDS_REPLAN
t=360  Rule Manager D002 -> REASSIGN M-UAV-01 (backup, V3->V1, 65.9 s)
t=379  CONTINGENCY_LANDED (M-UAV-02 at V3)
t=420  MISSION_COMPLETED (M-UAV-01)
```
