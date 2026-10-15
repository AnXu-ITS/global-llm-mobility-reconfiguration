# Claim-to-evidence map

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

## Manuscript and template provenance

The user's source ZIP supplies the original prose, author list, affiliations, references and extended figure assets. Original files are retained unchanged locally. The final user instruction chooses the supplied Springer LNEE template; an intermediate SPIE instruction was superseded before delivery.

The final DOCX reuses the original template's styles, numbering, section geometry and page-number headers. Only the body, its relationships and package content types are replaced or extended. VBA parts are removed for the macro-free DOCX output and were never executed. All two displayed equations and inline mathematical symbols are native Office Math. Main figures have vector SVG content with high-resolution raster fallbacks.

The standard `render_docx.py` renderer was attempted but LibreOffice is not installed. Microsoft Word's native fixed-format PDF export was used, followed by rendered page inspection. Final text and figure placement were checked over all eight pages.

## Reference correction

The original BibTeX misspelled the LLMLight authors' full names and the given name of the fourth Lost in the Middle author. The conference reference initials are consistent with the primary records. Verified primary records: [LLMLight v5](https://arxiv.org/abs/2312.16044v5), [Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/), [Meng et al. author repository](https://research.lancaster-university.uk/en/publications/the-multi-visit-drone-assisted-routing-problem-with-soft-time-win/), and [Jaber et al. publisher record](https://www.sciencedirect.com/science/article/pii/S2210670725001532).

No result was invented or strengthened beyond its experimental scope. No new LLM calls or SUMO–BlueSky experiments were run during the restoration and manuscript compression.
