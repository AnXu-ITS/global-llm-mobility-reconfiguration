# Figure and manuscript verification

The final six revised figures were inspected individually, then checked in the compiled manuscript and supplement. The main manuscript remains 25 pages; the supplement is 13 pages with Figure S3. Both builds have no overfull boxes or unresolved references.

All 36 bar summaries and their intervals agree exactly with the original CSV. All 48 heatmap values, 12 paired contrasts and intervals, 240 Site A matched states, nine matrix counts with denominators, and 53 timing/token values are retained. No observations were excluded. Source hashes and comparison records are in verification.json and source_data_trace.json.

All new figure exports are fully vector PDF/SVG, including map paths and individual heatmap cells. No embedded raster data panels were found. SVG text remains editable. New figure text is at least 6.5 pt at the supplied 510 pt width. Panel plot-area checks pass the 1.5 pt tolerance; the rendered panel-letter baselines also align.

The generic source validator's font check accepts only a short list of sans serif names. Times New Roman intentionally follows the user's Figure 1 reference and is installed and embedded. This is a documented design exception, not an unresolved font problem. PNG files are 300 dpi previews; PDF/SVG are the authoritative outputs. The numeric deadline legend and the sparse Figure 4 callout were reviewed.

Rendered collision checks report no findings for Figures 3–6 and S3. The generic map check reports intersections between labels and underlying road/water paths because it does not account for opaque objects painted later. All 19 geographic labels have opaque white backings after the underlying paths and before the text; a separate paint-order check confirms that no later stroke crosses them. Those map paths remain present in the vector source. Each map label was also inspected visually. No unresolved collision findings remain after that review.

Figure 1's PDF and PowerPoint, the PDFs for S1/S2, the bibliography, and nonfigure main-text content remain unchanged. Existing table contents and citation commands are preserved. Manuscript edits are confined to the affected captions and figure-source documentation, plus the requested new supplementary figure. The previous files are archived before replacement.

The full PowerPoint export branch was not rerun because the retained Figure 1/S1/S2 PDFs are unchanged. Its PowerShell syntax was checked, and its split routine now writes only those retained figures; the current Figures 2–6 are generated from Python. The manuscript compilation and the new Python generation path both ran successfully.
