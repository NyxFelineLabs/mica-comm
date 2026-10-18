# Figure review - 2026-10-18

## Scope and provenance

All **17 primary PDFs** have been rebuilt in the existing WSL environment
(matplotlib 3.10.9, NumPy 1.26.4). They use the complete historical records
imported from the existing reference checkout: 30 source files, with numeric
observations preserved. This restoration performs no new simulation or LLM
inference. The importer records original and translated SHA256 hashes and
marks `fresh_inference: false`. See the tracked
[provenance manifest](assets/figure_suite/provenance.json).

The two three-model benchmark plots remain separate under
`figures/supplemental/team_benchmark/`. They use our 108 measured missions,
including all twelve seeds per model/policy cell and zero backend fallbacks.
Their bootstrap analysis is unchanged. Moving and redrawing these plots does
not add new observations or establish a general model ranking.

## Visual changes and review

The reference PDFs and source plotting routines were inspected before revision.
All 17 filenames, comparisons, curve coordinates and metric definitions are
retained. Distinct categorical colours and markers have been restored. Figure
legends are measured and placed below the axes, away from data. Typography and
unit labels are consistent; the SNR pair has a wider inter-panel gutter.
Pareto parameter labels use explicit offsets and leader lines where needed.
The shared-budget single-column triptych is stacked vertically; the horizontal
version remains available as `fig_shared.pdf`.

The full gallery and individual panels were visually reviewed for curves,
uncertainty bands, axis labels, parameter labels and legends. Overlapping data
curves remain where the measurements coincide. No data were jittered to improve
policy separation. The trajectory example still shows its particular seed's
outcomes and does not imply that one policy always wins.

Previous local outputs are preserved in `figures/_archive/before-restoration/`;
unchanged reference PDFs are in `figures/_archive/reference-original/`.

## Final checks

- All **17/17 primary PDFs** passed the final PDF text audit. The smallest
  detected glyph is **5.25 pt**, above the 5 pt floor.
- All **17/17 primary PDFs** passed collision checks with **zero failures and
  zero warnings** after the final annotation/layout changes.
- Final rendered comparable panels passed the upstream alignment gate at
  **1.5 pt** tolerance. Single-axis figures are marked not applicable.
- Both supplemental benchmark PDFs passed text and collision checks, with
  zero collision failures or warnings.
- All **110 tests** passed, including observation-preserving imports,
  provenance hashes, key-collision rejection and overwrite prevention.
  Black and Ruff passed.

The committed [QA snapshot](assets/figure_suite/qa.json) contains per-PDF
hashes, glyph sizes, collision summaries and final panel-alignment records.
Local detailed reports remain in `figures/audit/`. PDFs use TrueType fonts,
SVG text stays editable and PNG previews use 600 dpi.

The combined primary-source preflight reported **16 passes, 5 warnings and no
failures**. Each warning was reviewed:

- Mathtext can shrink glyphs: the final PDF audits establish the actual
  minimum size; compact unit superscripts use Unicode where appropriate.
- TIFF is absent: PNG is a preview and PDF/SVG are the vector deliverables.
- The static scanner cannot resolve the export helper's DPI dictionary:
  the helper sets 600 dpi for PNG exports.
- The noise figure uses 116.8 mm width to accommodate its seven conditions.
  This is intentional; no specific journal width compliance is claimed.
- Random generators are used for bootstrap statistics, not fabricated data.
  Every plotted campaign is loaded from explicit result files.

These checks follow the Python route of
[nature-figure](https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-figure)
at revision `f8797feed6405035e7d57f59cb8ba393c6a98802`. Automated geometric
checks supplement visual review and do not validate scientific conclusions.

## Recheck

```bash
export MICA_FIGURE_AUDIT_SCRIPTS=/path/to/nature-skills/skills/nature-figure/scripts
python -m experiments.plot_suite --input results/restored_suite
python scripts/audit_figures.py --nature-scripts "$MICA_FIGURE_AUDIT_SCRIPTS"
```

Repeat rendered checks after changing data, layout, text, fonts or annotations.
The audit wrapper's combined source file is non-executable QA input only.
