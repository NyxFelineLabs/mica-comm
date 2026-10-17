# Figure review — 2026-10-18

## Scope and provenance

The two benchmark figures were rendered with the existing WSL Python environment
(matplotlib 3.10.9, NumPy 1.26.4) from all **108 measured missions**: three
models, three policies and twelve seeds (`8000..8011`). No observations were
discarded. No LLM inference was rerun for these figures. The public CSV and
original manifests reproduce the same analysis as the local JSONL records.
Statistics resample mission seeds 10,000 times with generator seed 5821.

This is an original implementation using style and integrity guidance from
`nature-figure` at revision `f8797feed6405035e7d57f59cb8ba393c6a98802`.
Existing scripts receive style/export changes; their analysis estimators are
preserved. New benchmark contrasts are implemented separately and do not
replace historical policy-comparison summaries.

## Evidence and rendered review

| Figure / panel | Role | Summary / uncertainty | Review |
| --- | --- | --- | --- |
| Mission outcomes, a | Establish task performance under three policies | All seed points, means, 95% percentile-bootstrap intervals | All 108 outcomes shown, zero-based axis, canonical model labels, no clipped intervals |
| Mission outcomes, b | Bound task performance by physical resource use | All applicable seed points, means, same interval definition | All 72 wireless-policy outcomes shown; 36 ideal-delivery costs are inapplicable and explicitly disclosed |
| Model contrasts | Directly check ranking and policy dependence | Mean paired difference and 95% seed-bootstrap interval | All nine model/policy contrasts shown; sign and exploratory scope stated; intervals include zero |

Both complete previews and each panel were visually inspected. Marker shapes
distinguish policies in addition to colour. Large mean markers intentionally
overlay the lighter raw observations; no observations are masked by a white
annotation box. Within-model offsets have no metric meaning.

Final page dimensions are **183 × 90 mm** for mission outcomes and
**183 × 85 mm** for model contrasts. PDF text is embedded TrueType; SVG text
remains editable. PNG previews are 600 dpi. There is no logarithmic transform,
normalization or interpolation; symbol counts are divided by 1,000 solely for
axis units. Ideal-delivery resource values remain in source data but are `null`
in physical-cost summaries.

## Automated checks

The upstream `require_matplotlib_panel_alignment()` ran before export:
mission outcomes **PASS**, no findings, tolerance 1.5 pt; the single-axis model
contrast figure was **NOT APPLICABLE**. Measured rectangles and reports remain
alongside local figures. The repository's lightweight row/column gate also ran.

Both final PDFs passed the upstream text audit: minimum glyph size **6.5 pt**,
above the 5 pt floor. Both passed the final PDF collision audit with **zero
failures and zero warnings**. Audit overlays are diagnostics, not publication
assets.

Source preflight passed with zero failures after inspecting the shared style
module and plotting entry point together. Its three warnings were reviewed:

- PNG is a preview, while editable PDF/SVG are the primary outputs; no journal
  TIFF requirement is claimed.
- The static scanner cannot resolve the export helper's `dpi` dictionary;
  runtime PNG dimensions confirm the configured 600 dpi.
- The scanner cannot resolve imported widths; rendered page dimensions and
  alignment reports confirm 183 mm.

All **106 tests** passed, including new checks for paired model differences,
missing/duplicate cells, backend fallbacks, incompatible configurations, capped
failures and identical statistics from the compact source snapshot. Black and
Ruff passed. A separate smoke check generated eighteen fresh classical
missions and rendered the legacy completion curve, trajectories and default
table. The complete robustness/realistic plotting campaigns were not rerun:
their full current-format input datasets are absent from this checkout.

## Recheck after changes

```bash
export MICA_FIGURE_AUDIT_SCRIPTS=/path/to/nature-skills/skills/nature-figure/scripts
python -m experiments.plot_team_benchmark --input docs/data/team_benchmark
python scripts/audit_figures.py --nature-scripts "$MICA_FIGURE_AUDIT_SCRIPTS"
```

The audit wrapper builds a non-executable combined source file for file-local
static inspection; the real entry point still imports the shared module.
Repeat rendered checks after any layout, text, data or font changes.
