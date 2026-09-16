# Figure style guide

Revision: 14 September 2026, flexible layouts and larger text.

Figure 1 remains the visual reference and is unchanged. Figures 2–6 share its Times New Roman typography and restrained blue, ochre, green and purple families. They share design rules, not a repeated panel template. Quantitative marks, maps and scales remain quantitative graphics.

## Palette and meaning

| Role | Hex | Use |
|---|---|---|
| Primary text | `#293038` | Titles, labels, counts |
| Secondary text | `#657078` | Units, ticks, supporting notes |
| Ground transport | `#557A9A` | Ground routes; nonpreemptive candidate markers |
| Air transport / B1 | `#BA8D58` | Air routes, preemptive candidates, B1 |
| B0 | `#858B8D` | Ground-only baseline |
| B2 | `#658571` | Fixed hybrid policy |
| B4b | `#887299` | LLM policy with explicit candidate information |
| Fault / deadline | `#AD6B6F` | Closure, deadline and selected timing annotations |
| Warm neutral | `#F6F4F0` | Occasional grouping background; no mandatory header strip |
| Divider | `#D0CEC8` | Thin separators and zero baseline |
| Grid | `#E5E2DC` | Selected horizontal guides |
| Roads / water | `#C2C8C9` / `#DDE8EB` | Geographic context |

Policy color identifies policy, not performance. Figure 4 uses air-color intensity for the air-selection fraction and retains each denominator. Shapes and line styles supplement hue. Do not change these meanings for visual variety.

Figure 2 uses stronger shades and heavier strokes so modeled services remain visible over the road network. These are transport-route overrides; the muted policy colors in Figures 3–6 are unchanged.

| Figure 2 route | Hex | Line width |
|---|---|---:|
| Primary ground | `#236B9A` | 1.6 pt |
| Ground detour | `#236B9A` | 1.3 pt, dashed |
| Primary air | `#C57C28` | 1.5 pt |
| Auxiliary ground | `#617E8E` | 1.0 pt |
| Other air | `#A56E2D` | 1.1 pt, dashed |

Closure markers and labels use `#B84F59`. Background roads and water retain their quieter context colors, while the route legend matches the plotted strokes exactly.

The common linear SWL scale is **0–400**, with stops `#F7F4ED`, `#E7DDCA`, `#C4B49C`, `#9B8885`, `#71637E`. Higher loss is darker. Use dark cell text below 300 and white text otherwise. These are configured loss units, not money.

## Typography and manuscript scale

All main figure exports are **510 pt wide (179.92 mm)**. Heights follow the evidence: Figure 2 **260 pt**, Figure 3 **286 pt**, Figure 4 **350 pt**, Figure 5 **254 pt**, Figure 6 **380 pt**. Supplementary Figure S3 retains its earlier 222 pt layout.

| Main-figure element | Export size | Weight |
|---|---:|---|
| Panel letter and title | 12 pt | Bold |
| Heatmap value / matrix count | 11.5 pt | Regular / bold |
| Axis title / common label | 10.5 pt | Regular |
| Tick label | 10 pt | Regular |
| Shared legend | 9.5–10.5 pt | Regular |
| Site subtitle / map label | 9.5 pt | Regular; primary facility labels bold |
| Bar value / short annotation | 9.5–10 pt | Regular or bold |

Font: **Times New Roman**. Main Figures 2–6 have no text below **9.5 pt at export size**, compared with 6.5–7 pt minima in the preceding set. PDF fonts are embedded; SVG text remains editable `<text>`. The supplementary contrast graphic retains its previous smaller type hierarchy.

The current manuscript places these exports at approximately 406 pt width, a scale factor of about 0.797. Thus 9.5, 10.5 and 12 pt become approximately **7.6, 8.4 and 9.6 pt on the manuscript page**. Inspect the compiled PDF, not just enlarged PNG previews. At a different journal width, recalculate the effective sizes before export; do not claim source sizes are final print sizes.

## Flexible composition rules

Lowercase panel letters and sentence-case titles share a baseline within a row. Put the title 18 pt to the right of its letter. Align actual plotting rectangles where panels are directly compared. A second row may use a different width when its role differs.

| Figure | Composition | Main grouping device |
|---|---|---|
| 2 | Three open maps, common scale and route legend | City headings and site subtitles; no enclosing cards |
| 3 | Three compact bar panels | First two grouped as “Critical mission”; third as “Incumbent service”, with a pale background |
| 4 | Large decision scatter → compact choice matrix; full-width outcome strip below | Regime backgrounds, meaningful boundaries and one linking arrow |
| 5 | Three contiguous heatmaps with one shared set of level labels | Policy headers, narrow site separators and one colorbar |
| 6 | Two timing plots above one wide input-burden plot | Shared policy/deadline legend; aligned upper axes and a thin row divider |

Avoid repeating outer boxes, filled title bars or identical card dimensions across the set. Use white space, proximity, a pale region or one rule to express an actual grouping. No decorative icons or pictorial substitutes for results.

Keep each panel focused on its question. Statistics and source attribution already in the manuscript caption need not be repeated as small print inside the artwork. Preserve those details in the caption. Place callouts in unused space without shifting data or fitting an untested threshold.

The alignment tolerance is 1.5 pt. Figure 6a,b share plot dimensions and vertical bounds; 6c shares their combined outside edges. Figure 4's scatter and matrix share their vertical analytical extent. Their different widths are intentional.

## Lines and marks

| Element | Export size |
|---|---|
| Grouping divider | 0.5–0.7 pt |
| Major grid | 0.4 pt |
| Zero / regime boundary | 0.6–0.8 pt |
| Bar interval | 0.65 pt; 1.8 pt caps |
| Main series | 1.2–1.5 pt |
| B2 under coincident B4b | 1.8 pt |
| Dashed B4b series | 1.2 pt |
| Map ground / air primary route | 1.6 / 1.5 pt |
| Background roads | 0.23 pt |
| Map scale bar | 1 pt |
| Callout leader | 0.65 pt |

Remove default axis rectangles. Keep zero-based bars and meaningful selected guides. Intervals are the original intervals, not redrawn standard errors. Timing markers: B0 square, B1 hollow triangle (7.5 pt), B2 hollow circle (5.5 pt), B4b filled diamond (3.1 pt). Nested markers and dashed B4b expose coincident values without jitter. Map labels use opaque white backing over the unchanged road geometry.

## Legend and annotation rules

- Use one shared policy legend in order **B0, B1, B2, B4b**. No frame or repeated panel legends.
- Figure 2 has one transport legend; detours and other air routes are dashed. Facility labels stay close to their locations, with sufficient separation from other labels.
- Figure 4 uses shape and hue for preemption. Its repeated coordinates are aggregated for display, retaining all 240 Site A states. Matrix cells show air selections / matched states. “No states” is distinct from zero selections.
- Figure 5 uses one common colorbar. Preserve site, level and policy order. L1–L4 are categorical settings; no significance encoding is added.
- Figure 6 uses one 180 s deadline legend for its upper pair. Lines join tested settings. OBS60, OBS120 and D60 annotations describe those measured settings, not a general or continuously estimated threshold.
- Direct bar labels show the original B4b means at the original display precision. Sparse endpoint labels on Figure 6 retain token values in tokens, while the axis is explicitly in thousands.

## Evidence and editable sources

All 36 bar means and original 95% seed-block intervals, 48 heatmap means, 240 Site A matched states, nine choice counts with denominators, and 53 timing/token values are retained. No observations are excluded. S3 retains all 12 original paired contrasts and intervals. Figure 2 retains the full imported road/water geometry and a common metres-per-point scale with 500 m bars. Interpretation and evidence boundaries remain in the manuscript captions and text.

`output/Figure2.svg` through `Figure6.svg` are the current editable vector masters. PDF files are manuscript exports; 300 dpi PNG files are previews. `FigureS3.svg` and PDF retain the supplementary differences. No data panel is a screenshot.

Run `python source/build_editorial_figures.py` with NumPy, Matplotlib and PyMuPDF installed. The exact data snapshot and alignment helper are supplied. SVG edits must also be transferred to the Python builder if they should survive regeneration. The prior boxed set and its manuscript documents are archived in the Overleaf repository at `archive/figures_boxed_20260914/`.
