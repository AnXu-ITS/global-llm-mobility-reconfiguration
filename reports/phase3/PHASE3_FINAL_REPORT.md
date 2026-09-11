# Phase 3 — LLM Manager Integration & Decision Sanity Validation (Final Report)

**Question answered:** 把 Rule Manager 替换成 LLM Manager 后，LLM 是否能够稳定、合法、可执行地
参与同一个管理闭环？ (Can the LLM stably, legally, and executably participate in the same
management loop when swapped in for the Rule Manager?)

**Answer: YES — P3-T1..T14 all PASS (14/14, 0 FAIL).** The LLM Manager, reading the identical
frozen Global State v1 and emitting the identical ManagerAction contract, reproduces the
Phase-2 closed loop in all three live cases and passes every legality/stability/sanity gate.

---

## 1. LLM / model / version
- Backend: local OpenAI-compatible endpoint `http://192.168.27.4:18888/v1` (corp-ai provider).
- Model: `corp-ai/openai/deepseek-v4-pro` (reasoning model).
- `temperature = 0.0`, `response_format = {"type": "json_object"}`, `max_tokens = 8192`.
- `max_tokens = 8192` is **required**: at 2048 the reasoning model exhausts the whole budget on
  reasoning tokens and returns empty `content` (~12 % JSON_ERROR). At 8192 it is 100 % valid.

## 2. Prompt version
- `prompts/manager_v1.txt`, `prompt_version = manager_v1` (frozen).

## 3. Offline validity (25 states from Phase-2 `manager_inputs.jsonl` + audited snapshots)
- JSON validity: **100 %** (25/25). Schema validity: **100 %**. Retry rate: **0 %**.
- First-attempt error distribution: `{}` (no JSON_ERROR / SCHEMA_ERROR).

## 4. Feasibility violation rate
- Feasible-action rate: **100 %** (25/25). Checker/SemanticValidator rejections: **0**.
- No duplicate-assignment, no priority-violation, no unknown-resource/mission.

## 5. Hallucination rate
- Unknown resource: **0**. Unknown mission: **0**. Invented facility/route/state: **0**.
- No fabricated resources, facilities, missions, or aircraft states.

## 6. Counterfactual sanity (9 paired states, one variable changed)
- **7 PASS / 2 OBSERVED / 0 FAIL.** Directionally correct in every pair:
  - P1 C2 NORMAL→LOST: lost M-UAV-02 deselected (DISPATCH M-UAV-01).
  - P2 V1 AVAILABLE→UNAVAILABLE: GROUND_FALLBACK (no dispatch to V1).
  - P4 battery / P7 endurance insufficient: M-UAV-02 deselected.
  - P6 no backup: GROUND_FALLBACK (no preemption of the busy non-reassignable aircraft).
  - P8 non-reassignable: never preempted; P9 V1-incompatible: M-UAV-02 deselected.
  - P3 priority / P5 ground-ETA: OBSERVED (LLM already prefers air; no spurious change).

## 7. Decision stability (same state × 10, temperature = 0)
- **10/10 identical**: action = `DISPATCH`, resource = `M-UAV-02`, fallback = `None`.
- action consistency = 100 %, resource consistency = 100 % (prompt-cache + json_mode).

## 8. Live critical-mission result (SMOKE, no C2)
- B1 ground disruption (t=300) → LLM `DISPATCH M-UAV-02` → BlueSky air → **COMPLETED (AIR)**.

## 9. C2 reconfiguration result (canonical C2-B)
- `DISPATCH M-UAV-02` (t=300) → C2_LOST on M-UAV-02 (t=360) → manager-independent local
  contingency RETURN→V3 → LLM `REASSIGN M-UAV-01` → **COMPLETED (AIR, M-UAV-01)**.
- Identical to the Phase-2 Rule-Manager canonical C2-B decision sequence.

## 10. No-backup result (C2-C)
- `DISPATCH M-UAV-02` (t=300) → C2_LOST, no available backup → LLM `GROUND_FALLBACK` →
  **COMPLETED (GROUND)**. No illegal aircraft dispatch (0 rejected actions).

## 11. Rule vs LLM decision differences (25 offline states)
- Equivalent (same action, or Rule "no-op" ↔ LLM `NO_ACTION`): **22/25**.
- Different-but-feasible: **2** — S04 logistics-C2-lost (Rule REASSIGN medical-UAV→logistics;
  LLM GROUND_FALLBACK, preserving the medical strategic reserve) and S17 needs_replan (Rule
  no-op; LLM GROUND_FALLBACK to free the medical UAV from logistics).
- Different-and-better: **1** — S23 landing-site-unavailable (Rule emitted DISPATCH to
  UNAVAILABLE V1, which the shared checker would reject; LLM GROUND_FALLBACK, correct).
- Different-and-worse: **0**. Invalid: **0**.
- **No "LLM outperforms Rule" claim** — the LLM merely reproduces the same loop within the same
  legality envelope; its only deviation from Rule is more conservative on the reserve.

## 12. Safe to enter Experiment 1?
- **YES.** P3-T1..T14 = 14/14 PASS / 0 FAIL; offline gate (JSON 100 %, schema 100 %,
  unknown-resource 0, duplicate 0, feasible 100 %) exceeded. The LLM Manager is a
  drop-in replacement that is stable, legal, and executable in the frozen closed loop.

---

## Latency / cost (Frozen Simulation Decision Mode)
- Live decision latencies: SMOKE 8.6 s (1 decision); C2-B 24.3 s total (0.076 s cached +
  24.2 s fresh); C2-C 74.6 s total (11.9 s + 62.7 s fresh). Offline fresh calls 8–63 s,
  prompt-cache hits ~0.05–0.08 s.
- Per decision: `prompt_tokens ≈ 2150` (2048 cached), `completion_tokens ≈ 3400–3950`
  (mostly reasoning tokens). Latency is recorded in `llm_metadata` and **never advances sim
  time** (frozen simulation decision mode).

## Acceptance tests (P3-T1..T14)
See `reports/PHASE3_ACCEPTANCE_TESTS.md` — **14/14 PASS / 0 FAIL**.

## Key files
- `managers/llm_manager.py`, `managers/llm_client.py` — LLM Manager (interface ≡ RuleBasedManager).
- `safety/semantic_validator.py` — shared semantic validation (unknown/resource/compat/duplicate/
  priority/site); `config/resource_compatibility.yaml` — aircraft-type × mission-type matrix.
- `schemas/manager_action_v1.schema.json` — frozen ManagerAction contract.
- `orchestrator/phase3_orchestrator.py` — Phase-3 closed loop (semantic + checker + executor),
  additive action executor + `_normalize_action` (route/target derivation, identical to Rule semantics).
- `tools/run_phase3.py|_offline|_counterfactual|_stability.py`, `tools/analyze_phase3_offline.py`.
- Artifacts: `runs/phase3_offline_decisions/`, `runs/phase3_live_{smoke,c2}/`, `runs/phase3_no_backup/`.
