# Current figure and manuscript checks

The latest revision strengthens the Figure 2 route colors and widths and clarifies the service-level scope and E3 horizons. The preceding flexible layouts are retained. The baseline is commit `4b95159fa6b8bb7e1177c746832ed153a939146b`; corresponding documents and sources are archived under `archive/service_margin_20260914/`.

Figure 2 preserves every route and network coordinate, its common map scale, facility labels, type sizes and layout. Route widths are now 1.6/1.3/1.5/1.0/1.1 pt for primary ground, detour, primary air, auxiliary ground and other air. The legend matches those strokes. Source-data traces and hashes are unchanged. PDF/SVG are vector exports with editable SVG text. Alignment and the 9.5 pt source-font floor pass.

The generic map checker reports 18 text/stroke and 10 fill-edge findings from geometry beneath opaque labels. The separate paint-order check verifies all 19 geographic labels have opaque backings after the underlying geometry, with no later stroke crossing text. No text/text conflicts remain. The map was inspected standalone and at manuscript size. The Times New Roman warning from the validator's sans serif whitelist remains an intentional reference-style exception.

Figure 1 and its PowerPoint, Figures 3–6, and Figures S1–S3 are byte-identical to the baseline. Their previously verified data and layouts are retained. All 36 bar summaries and intervals, 48 heatmap cells, 12 paired contrasts, 240 Site A states, nine choice fractions and 53 timing/token values remain unchanged.

The main manuscript and supplement compile to 25 and 13 pages, without overfull boxes or unresolved references. All pages were checked for printed command fragments; the five oprule occurrences on supplementary pages 7–9 are gone. Table contents and intervals are unchanged. The Python string escape was fixed in the local generator, and a patch accompanies the reproduction files. Affected supplementary tables use 6 pt in-text separation and 3 pt below captions, without shrinking table type.

All 2,880 E3 runs were checked against metrics, individual configurations and site matrices. L1/L2 used 900 s; L3/L4 used 1,200 s. All 4,320 task instances due by their corresponding horizons were completed. No overdue EN_ROUTE or ASSIGNED tasks were omitted from SWL. The original audit already used per-run durations; the inconsistent manuscript summary was corrected. The new audit reads saved files and launches no simulation or LLM calls.

Main-text edits concern the service-level claim, execution waiting, service-chain timing, model scope and E3 horizons. Debugging history and regression results remain in Supplementary S4.1. Author information, citations, bibliography, main tables and display equations are unchanged. Current checks and PDF hashes are in manuscript_preservation.json; per-run E3 records are in the reproduction directory.
