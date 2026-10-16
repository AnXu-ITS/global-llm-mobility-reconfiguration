# Ground–Air Service Reconfiguration

[中文说明](README.zh-CN.md)

Code and simulation studies of ground–air service recovery under transport disruptions.

## ITSAC paper

**A Ground–Low-Altitude Mobility Manager for Service Reconfiguration under Disruptions** studies when low-altitude support can restore time-critical ground services while preserving existing commitments.

- [Paper branch](https://github.com/AnXu-ITS/global-llm-mobility-reconfiguration/tree/itsac-restored-20261016)
- [Final manuscript](https://github.com/AnXu-ITS/global-llm-mobility-reconfiguration/blob/itsac-restored-20261016/itsac/ITSAC_XU_AN.docx)
- [Supplementary material and saved data](https://github.com/AnXu-ITS/global-llm-mobility-reconfiguration/tree/itsac-restored-20261016/itsac/supplement)

The paper branch contains the simulation implementation, experiment configurations, DeepSeek V4 Pro prompts, 11,140 saved per-run metric records and an offline numerical verifier. Complete historical raw trajectories are unavailable; the retained metrics support statistical recomputation.

## Follow-up research on this branch

The `main` branch develops asynchronous runtime supervision with explicit resource reservations, payload custody and physical handoffs. This work is separate from the ITSAC experiments.

The implementation and recorded development checks are described in [research_hscc2027](research_hscc2027/). Historical replays, protocol cases and single-payload physical controls are available. The [R1 v0.3 report](research_hscc2027/design/R1_ACCEPTANCE_v0.3.md) records acceptance within its stated bounded model. This is not a proof of the full deployed system; the planned formal transport experiments have not produced paper results.

| Directory | Contents |
|---|---|
| [research_hscc2027/](research_hscc2027/) | Runtime kernel, experiment protocols, configurations, site inputs and tools |
| [legacy/20260918/](legacy/20260918/) | Earlier platform, analysis and regression records |
| [provenance/hscc2027/](provenance/hscc2027/) | Source inventories, hashes and archive records |

See the [experiment protocol](research_hscc2027/design/EXPERIMENT_PROTOCOL_v0.2.md) for the planned comparisons and the [implementation status](research_hscc2027/IMPLEMENTATION_STATUS.md) for completed checks and remaining limitations.

## License and contact

A license has not yet been assigned. Contact the authors before reuse. Questions about the code can be raised through [GitHub issues](https://github.com/AnXu-ITS/global-llm-mobility-reconfiguration/issues).
