# Scientific figures

The plotting layer follows the Python route of
[nature-figure](https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-figure)
(reference revision `f8797feed6405035e7d57f59cb8ba393c6a98802`). Its guidance
informs our original plotting code; no third-party plotting implementation is
vendored. This is a visual and reproducibility convention, not a claim of
compliance with a particular journal's submission rules.

## Figure contract

The team benchmark asks whether a model's mission performance can be ranked
independently of the communication policy. The bounded claim is that observed
rankings depend on the policy, and twelve paired seeds leave substantial
uncertainty. All scheduled missions, including capped failures, remain in the
analysis. Seed is the resampling unit; individual LLM decisions are not
independent mission replicates.

Two quantitative figures answer complementary questions:

1. **Mission outcomes:** completion slots establish task performance; uplink
   symbols establish its communication cost. Means, raw seed observations and
   95% percentile-bootstrap intervals use the same definition in both panels.
   Ideal delivery has no comparable physical symbol cost.
2. **Model contrasts:** within-seed completion differences directly check model
   rankings under each policy. Negative differences favour the first model.
   Intervals are exploratory and unadjusted for multiple comparisons; no
   significance stars or general model-quality claims are made.

The Python/matplotlib workflow uses sans-serif fonts, editable SVG text,
TrueType PDF fonts, restrained colours with distinct markers, and 89/183 mm
column widths. PNG previews use 600 dpi. Fixed final page dimensions are used
for the new benchmark figures; older plots retain tight export to accommodate
their existing external legends.

## Rebuild

```bash
python -m experiments.plot_team_benchmark
```

This reads local mission records and manifests, validates all model/policy/seed
cells, and writes figures, source CSV, statistical JSON and provenance below
`figures/team_benchmark/`. It does not contact Ollama. A public, compact source
snapshot is also available in `docs/data/team_benchmark/` so a fresh checkout can
rebuild the documented figures without model weights or response caches:

```bash
python -m experiments.plot_team_benchmark --input docs/data/team_benchmark
```

Legacy entry points remain `experiments.plot`, `experiments.plot_robustness`
and `experiments.plot_realistic`. They share the same style and export helper;
their statistical estimators are unchanged. Historical input files must be
provided through `MICA_RESULTS_DIR`; these scripts never substitute example
data for missing experiments.

## Quality checks

Every export measures final axes rectangles and checks comparable grid edges
within 1.5 pt, recording an alignment JSON. For the upstream Nature audits, clone
`nature-skills` separately and set `MICA_FIGURE_AUDIT_SCRIPTS` to its
`skills/nature-figure/scripts` directory before plotting. This additionally calls
`require_matplotlib_panel_alignment()` before export. Then run the upstream
source, PDF-text and PDF-collision audits on the final scripts/PDF files. The
collision auditor requires PyMuPDF only for QA, not normal plotting.

```bash
export MICA_FIGURE_AUDIT_SCRIPTS=/path/to/nature-skills/skills/nature-figure/scripts
python -m experiments.plot_team_benchmark --input docs/data/team_benchmark
python scripts/audit_figures.py --nature-scripts "$MICA_FIGURE_AUDIT_SCRIPTS"
```

Review raw observations, interval extents, legends, panel spacing and the full
figure at final size even after automated checks pass. Review notes for the
published snapshot are in [figure QA](figure_qa.md).
