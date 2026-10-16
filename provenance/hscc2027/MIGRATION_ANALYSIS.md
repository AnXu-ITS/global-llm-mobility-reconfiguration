# Platform migration

The earlier platform is retained under `legacy/20260918/`, based on commit `3078ffb60d58952b4c193b2edb1de7d85375bbab`. The follow-up runtime uses separately versioned copies of selected modules in `research_hscc2027/vendor/legacy_platform/`.

The earlier runner invokes `manager.decide()` synchronously. The follow-up design separates proposal generation from simulation ownership and adds explicit resource and payload state. Results from the two implementations are not pooled.

## Reused evidence

- The E4 queue correction is retained in `legacy/20260918/manuscript/source/revision_v3/queue_fix.py`.
- The saved regression directory contains 27 runs: the default script's 20 corrected seeds and six controls, plus an additional uncorrected B1 control.
- `correction_map.csv` links the 20 original and corrected B0 D60 units. Corrections replace the affected values rather than add independent replicates.
- E4C increases input records while retaining four active aircraft. It is not evidence of a larger operational fleet.

The archive inventories describe available files and source hashes. They do not establish completeness of a logical experimental matrix. Complete historical raw trajectories are not included in the public repository. See [archive records](REPOSITORY_AUDIT.md) and the [ITSAC supplement](https://github.com/AnXu-ITS/global-llm-mobility-reconfiguration/tree/itsac-restored-20261016/itsac/supplement).
