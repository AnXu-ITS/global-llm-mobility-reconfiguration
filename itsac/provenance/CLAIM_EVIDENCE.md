# Results and supporting data

This map identifies evidence used by the eight-page conference manuscript. It distinguishes numeric recomputation from historical trace-derived evidence.

| Main-paper claim | Evidence | Check and limit |
|---|---|---|
| 10,960 primary and 180 ablation runs | `manuscript/source/revision_v3/all_metrics.json`, `e4_run_metrics_revised.json` | Counted 11,140 unique panel/scenario/seed/policy records; raw logs not all recovered |
| E1 A: 33.33% to 16.67% deadline violations; B2/B4b damage 0.058/0.133 | `all_metrics.json`, groups `E1_A`, policies B0/B2/B4b | Means and 20-seed-block intervals independently recomputed |
| E1 A service trade-off: −11.95 s, +0.600 damaged services/run | `E1_A`, scenario `E1_H_H_high` | Completion contrast and original 12-scenario Holm family recomputed; recorded issued action summaries retain preemption information |
| E1 candidate information: −13.567 s, −0.383 damage, −38.333 percentage points of air use | Paired B4a/B4b records in `all_metrics.json` | Ten seed blocks, three-endpoint family per site, exact whole-block label swaps for binary air intervention |
| E2: all affected coordinated chains restored, but late outcomes persist | `E2_A/B/C` in `all_metrics.json` | Restoration counts and all-run deadline means recomputed; denominators remain policy-dependent |
| E2 A: +4.525 s B4b vs B2 | E2 paired records and `results_revised.json` | Twelve-endpoint Holm family independently recomputed |
| E3 weighted loss and no significant B4b gain vs B1/B2 | `E3_A/B/C`, `system_weighted_loss_by_priority` | Aggregate means, intervals and compound comparison families recomputed |
| All 4,320 E3 due task instances completed | Archived `details_verified.json` and source supplement audit | Historical registry audit retained; missing complete registries prevent a fresh full audit |
| E4 observation and waiting results | `e4_run_metrics_revised.json` | All 68 policy–arm cells (20 runs each) checked against archived summaries |
| B0 D60 242 s; B4b 302 s | Revised E4 records, archived queue overlay and regression records | Numeric values verified offline; no new simulator rerun in this restoration |
| At B, 80 timely replacements have 19 s margin; +30 s makes them late | `transfer_margins.json`, `transfer_summary.json` | Archived offline trajectory-fixed calculation; no physical-transfer validation |
| Four active aircraft, larger inert input payload | E4 configuration, revised metric records and source supplement | Does not establish larger-fleet scalability |


## Data provenance

The paper branch retains the pre-pivot implementation and the archived derived metrics. [recovery.json](recovery.json) records the source commit, original archive hashes and recovered material. Complete historical raw logs are unavailable. The numerical verifier checks saved metrics; historical trajectory-derived findings remain bounded by the records actually retained.
