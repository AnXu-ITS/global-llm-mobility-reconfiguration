# Phase 3 Entry Baseline

Phase 3 integrates an LLM Manager into the SAME management loop as the Rule-Based
Manager. This file freezes the Phase-2 assets that must not be bent to accommodate
the LLM, and records the additive Phase-3 contract.

## Canonical testbed (frozen, NOT reverted)

- Scenario: `S0` / `S0_3p2km_v1` — **3.2 km x 3.2 km**.
- Fleet: **4 aircraft** (L-UAV-01 logistics, EVTOL-01 passenger eVTOL,
  M-UAV-01 medical standby, M-UAV-02 medical standby). No expansion, no 12-aircraft
  normative reference, no 5 km revert.

## Frozen Phase-2 components (SHA-256, first 16 hex chars)

| component | file | sha256[:16] |
|-----------|------|-------------|
| Global State v1 schema | `schemas/global_state_v1.schema.json` | `007246eb44c125d7` |
| ManagerAction schema (formalized) | `schemas/manager_action_v1.schema.json` | `f07937e8db896d61` |
| Feasibility checker | `safety/feasibility_checker.py` | `fd37dfe40e38578f` |
| Executor (Phase-2 orchestrator) | `orchestrator/phase2_orchestrator.py` | `f9da7a6e5b02d7ac` |
| Registries | `orchestrator/registry.py` | `15a3dec72e03dc36` |
| Fleet | `orchestrator/fleet.py` | `b706cc1b6560a3fb` |
| Rule Manager | `managers/rule_based.py` | `ef108f72be6c3edf` |
| C2 Lost Link + local contingency | `failures/c2_lost.py` | `dd41342d66efea69` |
| Global State builder | `state/global_state.py` | `b2c2cf8d020eff81` |
| Scenario config (frozen) | `config/scenario_config.yaml` | `f8adb1a2353d93c3` |
| Phase-2 runner | `tools/run_phase2.py` | `d6e5148b26b02c6a` |

### Additive checker extension (documented)

`safety/feasibility_checker.py` was extended **additively only** for the expanded
Phase-3 action space: `REROUTE` now routes through the air-mission gate (like
`DIVERT`), and `RETURN`/`LAND` get a new `_check_aircraft_only` gate. **No
existing Phase-2 action handling (DISPATCH/REASSIGN/DIVERT/RESERVE/CANCEL/
GROUND_FALLBACK/DELAY) changed.** Phase-1/2 regression is re-verified by P3-T1.

## New Phase-3 components (additive)

| component | file |
|-----------|------|
| Resource compatibility (shared) | `config/resource_compatibility.yaml` |
| Semantic validator (shared) | `safety/semantic_validator.py` |
| LLM Manager | `managers/llm_manager.py` |
| LLM HTTP client | `managers/llm_client.py` |
| Phase-3 orchestrator | `orchestrator/phase3_orchestrator.py` |
| Phase-3 runner | `tools/run_phase3.py` |
| Prompt (frozen) | `prompts/manager_v1.txt` |
| Phase-3 config | `config/phase3_config.yaml` |

## Fairness constraints (contract)

- LLM Manager and Rule Manager read the **byte-identical Global State v1**.
- LLM is denied: raw SUMO/BlueSky state, hidden simulator variables, GUI
  screenshots, future state, the Rule Manager's candidate ranking, baseline answer.
- Both managers share: FeasibilityChecker, Executor, Mission/Aircraft/
  Infrastructure registries, and the Semantic Validator + resource compatibility.
- Only the manager module differs; everything downstream is identical.

## LLM backend

- Model: `corp-ai/openai/deepseek-v4-pro` (OpenAI-compatible `corp-ai` endpoint).
- Endpoint: `http://192.168.27.4:18888/v1`; key via `CORP_AI_API_KEY`.
- temperature = 0 (determinism preferred); `max_tokens=2048`; timeout 180 s.
- Prompt: `manager_v1` (frozen). Frozen Simulation Decision Mode: real wall-clock
  latency is recorded but never affects simulation time.

## Not modified / out of scope

- No LLM API calls in Phase 1/2 paths.
- No Experiment 1–4, no Monte Carlo, no fleet expansion, no 5 km revert.
- C2 local contingency remains manager-independent (does not wait for the LLM).
