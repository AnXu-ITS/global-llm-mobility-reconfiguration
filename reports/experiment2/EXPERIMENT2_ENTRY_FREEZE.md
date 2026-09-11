# Experiment 2 — Entry Freeze

Protocol §2. Records the exact state of every object Experiment 2 inherits from
the frozen Experiment-1 platform. **After the formal primary run starts, none of
these objects may be modified.** All Experiment-2 additions live in NEW files /
new config blocks and are separately frozen in
`EXPERIMENT2_PROTOCOL_EXTENSIONS.md` and `config/experiment2_matrix.yaml`.

**Date:** 2026-09-05
**Full hash manifest:** `outputs/experiment2_entry_freeze_hashes.json`

## 0. Frozen identifiers

| component | identifier / value |
|---|---|
| canonical testbed | `S0_3p2km_v1` |
| study area | 3.2 km × 3.2 km, center 31.30377 N / 120.59981 E, EPSG:4326 |
| fleet | frozen 4 aircraft (`L-UAV-01`, `EVTOL-01`, `M-UAV-01`, `M-UAV-02`) — NOT expanded |
| simulation step | 1 s |
| Global State | v1 (`schema_version` 1.0.0) |
| Action Contract | v2 (`ManagerAction v1` schema; LLM-facing `prompts/manager_v2.txt`) |
| Candidate Table | v2.0.0 (Experiment 2 uses an additive 2.1.0 extension — see protocol extensions; 2.0.0 itself untouched) |
| Prompt | `manager_v2` |
| B2 objective | frozen (`config/experiment1_b2_weights.yaml`) |
| Managers | B0, B1, B2, B4b (primary); B4a NOT an Experiment-2 arm |

## 1. SHA-256 hashes (selected frozen objects; complete list in the JSON manifest)

| file | SHA-256 |
|---|---|
| `config/scenario_config.yaml` | `f8adb1a2353d93c3b9b6b3062f1293dcf540f2c419203533d06728e0bef5d434` |
| `config/resource_compatibility.yaml` | `e45baf107ee9ba7806fea1ecd7747c9a93ad4a8bfd87fd77dace829cb738ea1f` |
| `config/experiment1_b2_weights.yaml` | `a6e880f3c8e7398bcc2c25568141bd141be24d04eab7a8d0989cc72cacc673f6` |
| `config/experiment1_final_matrix.yaml` | `9b75a17729ad6e19e3755396a2f7148a2723c7f427a65a3576df329eefbab8b9` |
| `config/experiment1_final_seeds.yaml` | `8790101bb4cc03e061537ad4429b8be48f8c2f92c6705a5c07cbbe1d74b5d677` |
| `config/phase3_config.yaml` | `3ecc08809821d87097f504af43b6d2578110f1eb254f59da1c8dd630692379e5` |
| `schemas/global_state_v1.schema.json` | `007246eb44c125d7a407e52e3d3909fd20aa8a94de18d9b02f4cbbbf98a1743c` |
| `schemas/manager_action_v1.schema.json` | `f07937e8db896d616e4042b6c28f9610089cabbf67d104fc9746188d2c3ae689` |
| `prompts/manager_v2.txt` | `cf3a550761718d4b5ba53cd004980d795cc8e0ac9708f4284fe0f22be94f279c` |
| `orchestrator/candidate_info.py` (v2.0.0) | `4ebef494ab76ae03814b86e2cd1ed39afa2e850cd072234a7805d51279a7adc2` |
| `orchestrator/phase2_orchestrator.py` | `da2b1590d032a6aa7dccedf60deb56f691db1b2673f097a1935c9b5be430b4a8` |
| `orchestrator/phase3_orchestrator.py` | `8609d6dcbf5281931dc8fb9db81df5369fb8ea0d920dcb16f668cca780997512` |
| `orchestrator/experiment1_runner.py` | `9ba6b8d153e52596aa749fc13fbdab0988db5513e7ded789929920e2931363f7` |
| `orchestrator/registry.py` | `94acd6563594b008a250bc620d67a766956e30f675ea7fb4cfb6ebb76551baa5` |
| `orchestrator/fleet.py` | `b706cc1b6560a3fb08987f18168667d45ecaefd70c4182a1641bfcf28de2d030` |
| `orchestrator/geo.py` | `bb554c570a101923b0b1c222b5ba2a4336d7b61cc0cd40c35ab19a2ed99c2502` |
| `orchestrator/sumo_adapter.py` | `b700f7153b38d8f016b22429b7cf5f8fd0aa27dc0e35577061526f5923052437` |
| `orchestrator/bluesky_adapter.py` | `df066d6f5e21a645f633c3b01e0bd499e3d8f03822886f912eb1115d44b18278` |
| `orchestrator/config.py` | `6f0fedddecabb93834805770840fb81312df2a93a9a7e86bcae3a580e03ca08a` |
| `state/global_state.py` | `d19eafb0a122528907f3a7b258b1b67c905192bf32640d9e8443f1472c448254` |
| `managers/rule_based.py` | `024c9d4e7d9f1e3c1961589557e6c876eb239ffaf2b57c6dbd122dabf4a1f758` |
| `managers/optimization.py` | `8886d5d7529ccf8f87cfc112b509afdd8bf892f09f43f3a5413cce83e40f58bc` |
| `managers/no_cross_layer.py` | `d5d60e46ba5d53de21b14927c88c2a80a03005569b034faffd01fa1e66c92cc1` |
| `managers/llm_manager.py` | `90446c181323d223e121b1fcb6e2c8a672ff26986a8cea382270201ad84135e5` |
| `managers/llm_client.py` | `5680201eef2b5c9a495903c2cab2417013581c18750e4168ab290106b25a2567` |
| `safety/feasibility_checker.py` | `9ff8554d37c1020a8e1c65d9e6a8f06457de3bcb1996688bc7fd1a3ebb66f19e` |
| `safety/semantic_validator.py` | `e237ff7e63cafaea0e50464dc2bf26b60068df4cbfced5b1933255aadfe40062` |
| `failures/c2_lost.py` | `dd41342d66efea69696106b9656435617370918a826d3be69af25b0d7e7facc9` |
| `sim/sumo/canonical.sumocfg` | `25b62eebd7e560f9b1b2eafd1ad75c0e4d22b74f88682e6694beeb197d6ff032` |
| `sim/sumo/network.net.xml` | `c34caea7f89f77c820aba915db4bd8a03e093f57aa46edc51a769499df67ff2d` |
| `sim/sumo/routes.rou.xml` | `be80df7b27da7c42956b7f0ed4a60b43fde7c9cae5195731b6945d0474e6199c` |
| `sim/sumo/additional.add.xml` | `a82ce23a19a6a40709d5598ef47cda792c7d6ab53cead6afecbf468193820b1d` |
| `sim/bluesky/canonical_s0.scn` | `b57da4038e34a5315a3dba3b94f4bc2ed2670b616893fe298cc843f6e1b7908c` |

## 2. Inherited frozen protocol constants (not re-defined by Experiment 2)

- Ground disruption family used by Experiment 2 = **B1 critical-link closure**
  (E1 `MEDIUM` severity): D1→H1 ETA 131.838 s → 181.763 s, **+37.87 %**.
- Critical mission = `M-CRITICAL-001`, `medical_blood`, **CRITICAL**, V2→V1,
  released at t = 300 s, `ground_fallback: true`.
- B1 link closure at t = 300 s; simulation duration 900 s; 1 s step.
- Periodic re-decision 30 s (frozen E1 policy), event-triggered decisions.
- LLM: `corp-ai/openai/deepseek-v4-pro`, temperature 0, `json_object`,
  max_tokens 8192, prompt `manager_v2` (hash above). Real API latency recorded,
  never injected into simulation time (Frozen Simulation Decision Mode).
- B2 objective: frozen weights from `config/experiment1_b2_weights.yaml` —
  **no re-tuning for Experiment 2**.
- 20-seed set: Experiment 2 reuses the frozen Experiment-1 20 seeds
  (`config/experiment1_final_seeds.yaml`), subject to a seed-independence audit
  under the Experiment-2 scenarios.

## 3. Experiment-2 additions (new files only — frozen objects untouched)

| new object | purpose |
|---|---|
| `config/experiment2_matrix.yaml` | 16 failure×context scenario classes (2 documented SCENARIO_DESIGN_LIMITATIONs) |
| `config/experiment2_seeds.yaml` | frozen 20-seed list |
| `failures/state_ext.py` | additive aircraft state transitions (AVAILABLE→DEGRADED / AVAILABLE→CONTINGENCY) |
| `failures/e2_failures.py` | F1–F6 injectors + risk-zone geometry |
| `orchestrator/candidate_info_e2.py` | candidate table 2.1.0 (additive, manager-agnostic) |
| `safety/feasibility_checker_e2.py` | E2 hard-constraint checker extension |
| `safety/semantic_validator_e2.py` | E2 semantic validator extension |
| `orchestrator/experiment2_runner.py` | Experiment-2 runner (reuses the frozen Phase-2/3 machinery) |
| `tools/run_experiment2.py` + analysis/audit tools | harness, audits, statistics, figures |

All extensions are documented in `EXPERIMENT2_PROTOCOL_EXTENSIONS.md` with
CHANGELOG entries and comparability notes before any formal run.

## 4. Experiment-2 freeze (post-pilot, pre-primary — protocol §25)

Pilot: 6 scenarios × 3 seeds × 4 managers = 72 runs, **22/22 checks PASS**
(`EXPERIMENT2_PILOT_REPORT.md`). The following are frozen for the formal
primary run (`outputs/experiment2/experiment2_freeze_hashes.json`):

| file | SHA-256 |
|---|---|
| `config/experiment2_matrix.yaml` | `b8bcc40bd3cf39d233ca15991beb64fda79eedcb88fa68f05dbb57c8d66e9620` |
| `config/experiment2_seeds.yaml` | `f4fe6d590e20adcb28f051c1f10c262ba7c19b8c4ffdc9b5de58f3f5b45756dd` |
| `orchestrator/experiment2_runner.py` | `e768a5d125db8c8c1c6e302885291f901f40360d638c87a790739e5200898341` |
| `failures/e2_failures.py` | `a3d8dd99215def9ce78b87e395cbb436404b6d6ea3777dab600905d88eb8d760` |
| `orchestrator/candidate_info_e2.py` | `b03147cce6421135c01aa8256c83f0768a459cb6136441a5ac5c68bf15b03619` |
| `safety/feasibility_checker_e2.py` | `f0354a8beb7bd94954f4d5e1ad3311f06fd377207b3c413e422487a36b8fbe7c` |
| `safety/semantic_validator_e2.py` | `b07ded9d02743a20f38037f45a59f33471a4ecdcbf97072171a64d55e298fd41` |

The run harness (`tools/run_experiment2.py`) additionally refuses to treat any
cell as current unless its `failure_config_hash` matches the frozen matrix —
a permanent guard against pre-freeze stale cells.

## 5. Post-E1 re-freeze note (2026-09-06, user-approved)

`tools/analyze_ablation.py` and `tools/analyze_experiment1_final.py` were
refactored externally on 2026-09-06 (loader reuse) after the E2 primary
completed. The refactor is accepted as an intentional post-E1 change:
`outputs/file_hashes_final.json` was formally re-frozen to the new hashes
(`5f96ad3f1ade4caf85bb7d8d25e7391310348f3e668cc17c35f859a4923e4683` /
`32a13d8128d269a0913f43e0fa4c352318ead759ee13257fd7aa72c9acda6340`).
Impact on comparability: none — the frozen Experiment-1 dataset and all its
analysis outputs are unchanged; only the two post-hoc analysis tools were
refactored. CHANGELOG entry added. E2-T2 compares against the re-frozen
manifest (26/26).


