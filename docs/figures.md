# Experiment figures

The primary entry point rebuilds the complete **17-figure suite**, preserving
reference curves, metrics, uncertainty calculations and policy distinctions.
Changes address typography, external legends, panel spacing and annotation
placement. The narrow shared-budget triptych is stacked vertically in
`fig_shared_col`; `fig_shared` retains the horizontal comparison.

## Complete catalogue

[Browse all 17 committed PDFs](assets/figure_suite/README.md).
These are **replots of historical experiment records**, not newly measured
MICA or LLM results. Attribution remains in [NOTICE](../NOTICE.md).

| PDF | Content |
| --- | --- |
| `fig_agents.pdf` | Team-size sweep |
| `fig_budget.pdf` | Per-agent uplink budget |
| `fig_curve.pdf` | Search progress over time |
| `fig_downlink.pdf` | Broadcast loss and delay |
| `fig_efficiency.pdf` | Task performance versus uplink resources |
| `fig_fbl.pdf` | Finite-blocklength channel assumptions |
| `fig_frontier.pdf` | Value-rule resource frontiers |
| `fig_noise.pdf` | Sensitivity to value-estimation errors |
| `fig_pareto.pdf` | Communication-price trade-off |
| `fig_rescue.pdf` | Rescue success versus uplink use |
| `fig_shared_col.pdf` | Shared-budget frontiers, stacked |
| `fig_shared.pdf` | Shared-budget frontiers, horizontal |
| `fig_snr_pair.pdf` | SNR versus completion and resource use |
| `fig_snr_sym.pdf` | SNR versus channel use |
| `fig_snr.pdf` | SNR versus completion |
| `fig_traj.pdf` | Example agent trajectories |
| `fig_where_tom.pdf` | Larger teams and clustered survivors |

## Restore and rebuild

Use the existing historical results directory:

```bash
python scripts/import_plot_results.py --source ../gosc-agentic-teams/results --output results/restored_suite
python -m experiments.plot_suite --input results/restored_suite
```

The importer preserves numerical observations, translates method IDs and
`rev_` filenames to the current namespace, and records source/imported SHA256
hashes in `provenance.json`. It refuses overwrites and does not import model
response caches or run inference. Historical raw datasets are not bundled in
Git. Select a complete new campaign's result directory explicitly to plot its
measurements. Required inputs are checked before drawing; missing records are
never replaced with historical or synthetic observations.

For an individual figure:

```bash
python -m experiments.plot_suite --input results/restored_suite --only fig_snr_pair
```

`--only` writes an index and manifest for that selection. Run without it to
rebuild the complete gallery and manifest.

```text
figures/
├── index.html          Local preview gallery with PDF/SVG links
├── fig_*.pdf           All 17 primary figures
├── png/                600 dpi previews
├── svg/                Editable vector exports
├── audit/              Input provenance, layout and QA reports
├── tables/             Tables emitted by plotting routines
├── supplemental/       Separate three-model benchmark analysis
└── _archive/           Preserved earlier outputs and reference PDFs (local)
```

## Three-model benchmark

These separate figures use **our 108 measured missions** and do not replace the
17-figure suite. Rebuild offline from the compact tracked snapshot:

```bash
python -m experiments.plot_team_benchmark --input docs/data/team_benchmark
```

Outputs go to `figures/supplemental/team_benchmark/`, with source CSV and
bootstrap statistics under `analysis/`. All capped failures remain in the
analysis. Resampling uses mission seeds, not individual LLM decisions. Ideal
delivery has no comparable physical wireless cost. See [model selection](model_selection.md).

## Style and checks

The Python/matplotlib workflow follows adaptation and QA guidance in
[nature-figure](https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-figure)
at revision `f8797feed6405035e7d57f59cb8ba393c6a98802`. It uses distinct
colours and markers, sans-serif text, TrueType PDF fonts and editable SVG text.
This is not a journal acceptance claim.

```bash
export MICA_FIGURE_AUDIT_SCRIPTS=/path/to/nature-skills/skills/nature-figure/scripts
python -m experiments.plot_suite --input results/restored_suite
python scripts/audit_figures.py --nature-scripts "$MICA_FIGURE_AUDIT_SCRIPTS"
```

The environment variable enables the upstream final panel-alignment gate before
export. The audit command checks source conventions, PDF text and collisions.
Inspect curves, uncertainty, annotations and legends visually as well.
See [review notes](figure_qa.md).
