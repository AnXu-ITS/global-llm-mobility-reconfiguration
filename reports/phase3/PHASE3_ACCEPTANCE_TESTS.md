# Phase 3 Acceptance Tests — Results

**Manager:** LLM Manager (`corp-ai/openai/deepseek-v4-pro`, prompt `manager_v1`, temperature=0)
**Shared path:** Global State v1 -> Manager -> Semantic Validator -> FeasibilityChecker -> Executor
**Verdict:** NO FAIL across P3-T1..P3-T14

| Test | Result | Evidence |
|------|--------|----------|
| P3-T1 | PASS | Phase-1/2 regression PASS |
| P3-T2 | PASS | Phase-3 LLM manager_inputs byte-identical to Phase-2 Rule manager_inputs: True |
| P3-T3 | PASS | Rule keys=['action', 'decision_id', 'mission_id', 'reason', 'selected'], LLM keys=['action', 'decision_id', 'mission_id', 'reason', 'selected'] (both expose the ManagerAction contract) |
| P3-T4 | PASS | structured output schema-valid on 25 states; SCHEMA_ERROR=0 |
| P3-T5 | PASS | unknown-resource hallucination after retry = 0 |
| P3-T6 | PASS | checker blocks unknown resource (['AIRCRAFT_NOT_FOUND']) and insufficient battery (['INSUFFICIENT_ENDURANCE', 'INSUFFICIENT_BATTERY']) |
| P3-T7 | PASS | 9 pairs: 7 PASS, 2 OBSERVED, 0 FAIL |
| P3-T8 | PASS | 10 repeats, action consistency=100% (mode=DISPATCH) |
| P3-T9 | PASS | ground->LLM->air chain: dispatched=True, completed=True, final=COMPLETED |
| P3-T10 | PASS | C2->LLM reconfiguration: c2_lost=True, reconfigure=True, terminal=True, final=COMPLETED |
| P3-T11 | PASS | no-backup handled legally: final=COMPLETED, rejected_actions=0 |
| P3-T12 | PASS | local contingency fires immediately after C2_LOST (order=['MISSION_STARTED', 'C2_LOST', 'LOCAL_CONTINGENCY', 'MISSION_INTERRUPTED']), mode=RETURN target=V3 |
| P3-T13 | PASS | SUMO/BlueSky/orchestrator synchronized across all live runs |
| P3-T14 | PASS | manager_inputs.jsonl and manager_outputs.jsonl present and paired in all live runs |
