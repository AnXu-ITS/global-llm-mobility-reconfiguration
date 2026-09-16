# Figure style guide

Figure 1 is the visual reference. Figures 2–6 retain quantitative chart forms while sharing its Times New Roman typography, modular organization and blue, ochre, green and purple families. The data-figure colors are less saturated. Figure 1 itself is unchanged.

## Palette and meaning

| Role | Hex | Rule |
|---|---|---|
| Text | `#293038` | Titles, primary labels and matrix counts |
| Secondary text | `#657078` | Units, ticks and short supporting notes |
| Ground transport | `#557A9A` | Ground routes; nonpreemptive candidate markers |
| Air transport / B1 | `#BA8D58` | Air routes, preemptive candidates and B1 |
| B0 | `#858B8D` | Neutral ground-only policy baseline |
| B2 | `#658571` | Fixed hybrid policy |
| B4b | `#887299` | LLM policy with explicit candidate information |
| Fault / deadline | `#AD6B6F` | Closure and deadline boundary; used sparingly |
| Panel header | `#F6F4F0` | Warm, very pale header strip |
| Panel border | `#D0CEC8` | Thin enclosing rule, distinct from plot axes |
| Grid | `#E5E2DC` | Quiet major horizontal guides |
| Roads / water | `#C2C8C9` / `#DDE8EB` | Geographic context below modeled services |

Policy colors identify policy, not performance. In Figure 4 the matrix uses air-color intensity to show the selected fraction; its counts retain the denominator. Green/blue/purple are not reused as arbitrary sequential categories. Marker shape, line style, position and text supplement color.

The SWL scale is linear and common to all sites: **0–400**, preserving the former figure's scale. Stops are `#F7F4ED`, `#E7DDCA`, `#C4B49C`, `#9B8885`, `#71637E`. Higher loss is darker. Cell values below 300 use dark text; higher values use white text. These are configured loss units, not money.

## Typography at final size

All figures are **510 pt wide (179.92 mm)**, matching the approximately 180 mm reference figure. Do not compare font sizes in screen pixels. The new figure heights follow their content: Figure 2 257 pt; Figure 3 261 pt; Figure 4 306 pt; Figure 5 238 pt; Figure 6 302 pt; Figure S3 222 pt.

| Element | Size | Weight |
|---|---:|---|
| Panel letter | 9 pt | Bold |
| Panel title | 8.5 pt | Bold |
| Main labels | 8 pt | Regular |
| Matrix count | 8.5 pt | Bold |
| Heatmap value | 8.1 pt | Regular |
| Shared legend | 7–7.5 pt | Regular |
| Tick label | 7 pt | Regular |
| Supporting note | 6.8–7.2 pt | Regular |
| Bar value / sparse callout | 6.5–7 pt | Regular or bold |

Font: **Times New Roman**, inherited from Figure 1. Avoid substituting the plotting library's default font. PDF text is embedded TrueType; SVG text remains `<text>` rather than outlines. All new rendered glyphs are at least 6.5 pt. Keep the SVG font available when editing elsewhere.

## Panel and spacing rules

- Use lowercase letters at the left of a common header baseline. Put the title 13 pt to the right of the letter. Use sentence case and consistent terminology.
- Three-panel modules are 162 pt wide with 7 pt gaps. Align actual plotting rectangles, not just panel borders. Use equal plotting widths and heights for directly comparable panels.
- Headers are 25 pt high, or 39 pt when one short subtitle is needed. The warm header fill and a thin rule provide grouping. Plot interiors stay white.
- Figure 4 has a larger decision-space module and a compact behavior module. The scatter and the right-hand analytical area have the same vertical extent. The lower outcome block belongs to the behavior module.
- Remove the default plot rectangle. Use a zero baseline, selected gridlines, or meaningful regime boundaries as needed. The pale module border organizes content; it is not an additional data axis.
- Keep annotations in unused space and connect them to the relevant observation. Do not move points, jitter matched states or crop data to make room.
- The alignment check uses final rendered axes, with a 1.5 pt tolerance. Each output has a recorded alignment report.

## Line and mark rules

| Element | Width / size at final size |
|---|---|
| Panel perimeter | 0.45 pt |
| Header rule | 0.5 pt |
| Major grid | 0.4 pt |
| Zero / regime line | 0.6–0.75 pt |
| Bar interval | 0.65 pt; cap size 1.8 pt |
| Paired contrast interval | 0.9 pt; cap size 2 pt |
| Main series / routes | 0.95–1.2 pt |
| Overlapping B2 line | 1.6 pt beneath dashed B4b |
| Background roads | 0.23 pt |
| Cell separators | 1.1 pt, white |

Timing markers: B0 square, B1 hollow triangle, B2 hollow circle, B4b filled diamond. Nested sizes expose coincident B1/B2/B4b values. Do not jitter curves or imply different observations where values coincide. Dashed B4b segments expose the underlying B2 line.

## Legend rules

- One shared policy legend in policy order **B0, B1, B2, B4b**. Omit unused policies from a specific figure. No legend box or repeated panel legends.
- Map routes have one shared transport legend. Ground detours and other air routes are dashed. Geographic labels use small opaque white backings to stay readable over the unchanged road paths.
- The Figure 4 scatter distinguishes preemption by both hue and shape. Repeated coordinates are aggregated for display without dropping observations; the source records all 240 Site A states.
- Label matrix cells as `air selections / matched states`; distinguish “No states” from zero selections.
- Share one SWL colorbar across all three heatmaps. Preserve policy and level order; levels are categorical combinations of disturbance and demand.
- Use one deadline legend for Figure 6a,b. Lines join tested settings. OBS60, OBS120 and D60 annotations do not imply a universal or continuously estimated threshold.

## Figure content contracts

| Figure | Question / panel roles | Source and evidence boundary |
|---|---|---|
| 2 | What transport contexts were compared? Three projected site networks and modeled connections. | All imported roads and water geometry; same metres per point and 500 m scale bars. Facility labels and route roles retained. |
| 3 | How do critical-service benefit and incumbent damage differ? Three complementary zero-based bar panels. | All 36 site–policy–metric means and original 95% seed-block intervals; 240 runs / 20 seed blocks per site and policy. |
| 4 | How does a common decision state relate to choices and outcomes? Site A scatter → policy-choice matrix → late counts. | All 240 matched Site A states, 9 choice counts with denominators, and original late counts. Zero lines and the derived `y=x` boundary are descriptive ETA geometry. |
| 5 | In which compound settings does loss decrease? Three common-scale heatmaps. | All 48 site–level–policy means. Noninteger labels retain the original one-decimal display convention. No significance encoding. |
| 6 | How do observation interval, injected wait and input burden change outcomes? Three aligned sensitivity panels. | All original tested settings, 20 runs per arm and policy. Completion intervals are zero-width in these source summaries. No new interpolation or fitted thresholds. |
| S3 | Where does B4b reduce loss relative to B0? Three site-specific paired-contrast plots. | All 12 original contrasts and 95% seed-block intervals moved from Figure 5. No change to signs, denominators or tests. |

## Editable files and regeneration

`output/Figure2.svg` through `Figure6.svg`, plus `FigureS3.svg`, are the editable vector masters for this redesign. Paths, bars, cells, text and linework remain vector objects. PDF files are the manuscript exports; PNG files are previews. No screenshot is used as a data panel.

Run `python source/build_editorial_figures.py` to regenerate PDF, SVG and PNG files and the alignment/data-trace records. The `source/` folder contains the exact data snapshot and the reusable alignment helper. Editing SVG directly is supported, but those visual edits must also be applied to the Python builder if regeneration is expected to preserve them. Figure 1 and the earlier supplementary PowerPoint sources remain available separately.

The redesign changes presentation and the requested main/SI placement only. It does not change observations, uncertainty estimates, policy definitions, statistical tests or manuscript conclusions.
