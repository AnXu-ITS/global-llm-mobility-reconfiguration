# Prompt Freeze (Finalization §5)

- **Frozen prompt file**: `prompts/manager_v2.txt` (B4a / B4b both use this prompt).
- **SHA-256**: `cf3a550761718d4b5ba53cd004980d795cc8e0ac9708f4284fe0f22be94f279c`
- **Retired prompt**: `prompts/manager_v1.txt` (Phase-3 only; SHA-256 `85bb3f798848d53596025ecbb06e02407d41c28fe6295540806efbea6e88bd76`).

## Freeze contract

1. `prompts/manager_v2.txt` is **frozen for the corrected primary rerun**. It MUST NOT
   be edited based on formal rerun results (no "prompt tuning to make the LLM win").
2. If the file changes **after** the primary run begins, the run is a **different
   experiment version** and must be re-labelled (prompt hash is recorded in every
   run's provenance).
3. The prompt's `{CANDIDATE_SECTION}` placeholder is the *only* difference between
   B4a (section rendered as empty) and B4b (section rendered with the shared
   candidate table). The rest of the prompt text is byte-identical for both arms.

## What the frozen prompt fixes vs v1

- States the REASSIGN preemption contract (busy + reassignable + strictly-lower
  priority) that the v1 prompt omitted (review §3).
- States the full 12-type action space with preconditions.
- States the shared resource-compatibility matrix.
- Instructs "decide using ONLY the supplied Global State" and "NEVER invent
  resources/facilities/missions".

## Provenance

- Prompt template is read by `managers/llm_manager.py` from
  `prompts/manager_v2.txt` (set via `phase3_config.prompt`), with
  `temperature=0`, `response_format=json_object`, `max_tokens=8192`.
- The prompt hash is recorded in `reports/experiment1_final/EXPERIMENT1_FINAL_ENTRY_FREEZE.md`
  and is re-verifiable at any time via `Get-FileHash prompts/manager_v2.txt`.
