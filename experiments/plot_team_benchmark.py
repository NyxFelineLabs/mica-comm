"""Render measured team outcomes and paired model contrasts, without LLM calls.

python -m experiments.plot_team_benchmark --input docs/data/team_benchmark
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from experiments.run_team_benchmark import POLICIES  # noqa: E402
from experiments.team_analysis import (  # noqa: E402
    MODEL_LABELS,
    analyze,
    load_campaign,
    write_source_csv,
)
from mica_comm.core.paths import FIGURES_DIR, RESULTS_DIR  # noqa: E402
from mica_comm.visualization.language import chinese  # noqa: E402
from mica_comm.visualization.style import (  # noqa: E402
    STYLE as POLICY_STYLE,
)
from mica_comm.visualization.style import (  # noqa: E402
    W2,
    export_figure,
    panel_label,
    publication_style,
)

# Ideal delivery needs a marker in these categorical plots, while line sweeps
# retain the reference suite's neutral dashed line without repeated markers.
STYLE = {
    **POLICY_STYLE,
    "sem": {**POLICY_STYLE["sem"], "label": "Fixed-cycle sharing (SYNC)"},
    "mica": {**POLICY_STYLE["mica"], "label": "MICA"},
    "genie": {
        **POLICY_STYLE["genie"],
        "label": "Instant, reliable sharing reference (IDEAL)",
        "marker": "^",
    },
}


def _legend(fig):
    handles = [
        Line2D(
            [],
            [],
            color=STYLE[p]["color"],
            marker=STYLE[p]["marker"],
            linestyle="none",
            label=STYLE[p]["label"],
        )
        for p in POLICIES
    ]
    fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.55, 0.99),
        ncol=3,
        columnspacing=2,
        handletextpad=0.5,
    )


def outcomes(rows, report, output):
    """Establish task outcomes and the physical communication cost together."""
    fig, axes = plt.subplots(1, 2, figsize=(W2, 90 / 25.4))
    fig.subplots_adjust(left=0.085, right=0.98, bottom=0.24, top=0.79, wspace=0.36)
    models = list(report["absolute"])
    for ax, metric, scale, title, ylabel, letter in (
        (axes[0], "completion_time", 1, "Task progress", "Completion time (slots)", "a"),
        (axes[1], "symbols", 1000, "Communication cost", "Uplink symbols (thousands)", "b"),
    ):
        policies = POLICIES if metric == "completion_time" else ("sem", "mica")
        for model_index, model in enumerate(models):
            for policy, offset in zip(policies, np.linspace(-0.22, 0.22, len(policies))):
                stats = report["absolute"][model][policy][metric]
                group = sorted(
                    (
                        r
                        for r in rows
                        if r["model"] == model
                        and r["scheme"] == policy
                        and r["scenario"] == report["scenario"]
                    ),
                    key=lambda r: r["seed"],
                )
                # Deterministic horizontal offsets only; every seed is drawn.
                x = model_index + offset
                ax.scatter(
                    x + np.linspace(-0.045, 0.045, len(group)),
                    [r[metric] / scale for r in group],
                    s=8,
                    color=STYLE[policy]["color"],
                    marker=STYLE[policy]["marker"],
                    alpha=0.28,
                    linewidths=0,
                    zorder=2,
                )
                mean = stats["mean"] / scale
                ax.errorbar(
                    x,
                    mean,
                    yerr=[
                        [max(0, mean - stats["low"] / scale)],
                        [max(0, stats["high"] / scale - mean)],
                    ],
                    fmt=STYLE[policy]["marker"],
                    color=STYLE[policy]["color"],
                    markersize=4,
                    capsize=2,
                    elinewidth=1,
                    zorder=3,
                )
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels(
            [MODEL_LABELS[m].replace(" 8B", "\n8B").replace(" 12B", "\n12B") for m in models]
        )
        ax.set_xlim(-0.5, len(models) - 0.5)
        ax.set_ylim(bottom=0)
        ax.set_title(title, loc="left", pad=12)
        ax.set_ylabel(ylabel)
        ax.yaxis.grid(True, color="#E8E8E8", linewidth=0.4, zorder=0)
        panel_label(ax, letter)
    _legend(fig)
    caption = (
        f"点：逐任务观测；大标记：均值；误差线：95% bootstrap 区间；n = {len(report['seeds'])} 个种子。\n"
        "IDEAL 为零时延、无误差参考，不计物理链路成本。所有任务均纳入统计。"
        if chinese()
        else f"Points: individual missions; large markers: means; bars: 95% bootstrap CIs; n = {len(report['seeds'])} seeds.\n"
        "IDEAL is a zero-delay, error-free reference without a physical link cost. All missions are included."
    )
    fig.text(
        0.5,
        0.045,
        caption,
        ha="center",
        va="bottom",
        fontsize=6.5,
        linespacing=1.5,
    )
    export_figure(fig, output / "mission_outcomes", fixed_size=True)
    plt.close(fig)


def contrasts(report, output):
    """Check whether one model ranking holds across communication policies."""
    fig, ax = plt.subplots(figsize=(W2, 85 / 25.4))
    fig.subplots_adjust(left=0.29, right=0.97, bottom=0.25, top=0.83)
    pairs = list(dict.fromkeys((r["first"], r["second"]) for r in report["contrasts"]))
    for index, (first, second) in enumerate(pairs):
        for policy, offset in zip(POLICIES, (-0.23, 0, 0.23)):
            stats = next(
                r
                for r in report["contrasts"]
                if (r["first"], r["second"], r["policy"]) == (first, second, policy)
            )
            ax.errorbar(
                stats["mean"],
                index + offset,
                xerr=[
                    [max(0, stats["mean"] - stats["low"])],
                    [max(0, stats["high"] - stats["mean"])],
                ],
                fmt=STYLE[policy]["marker"],
                color=STYLE[policy]["color"],
                markersize=4,
                capsize=2,
                elinewidth=1,
            )
    ax.axvline(0, color="#A0A0A0", linestyle="--", linewidth=0.7, zorder=0)
    ax.set_yticks(range(len(pairs)))
    pair_labels = [
        f"{MODEL_LABELS[a]}\n{'减去' if chinese() else 'minus'} {MODEL_LABELS[b]}" for a, b in pairs
    ]
    ax.set_yticklabels(pair_labels, linespacing=1.6)
    ax.set_ylim(len(pairs) - 0.5, -0.5)
    ax.set_xlabel("Paired completion-time difference (slots; first minus second)")
    _legend(fig)
    caption = (
        f"均值与 95% 配对 bootstrap 区间；n = {len(report['seeds'])} 对种子。\n"
        "负值表示前者更快。区间为探索性估计，未经多重比较校正。"
        if chinese()
        else f"Means and 95% paired bootstrap CIs; n = {len(report['seeds'])} seed pairs.\n"
        "Negative: first model faster. Intervals are exploratory and unadjusted."
    )
    fig.text(
        0.63,
        0.04,
        caption,
        ha="center",
        va="bottom",
        fontsize=6.5,
        linespacing=1.5,
    )
    export_figure(fig, output / "model_contrasts", fixed_size=True)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=RESULTS_DIR / "team_benchmark")
    parser.add_argument("--output", type=Path, default=FIGURES_DIR / "supplemental/team_benchmark")
    parser.add_argument("--scenario", default="default")
    parser.add_argument("--language", choices=("en", "zh", "both"), default="en")
    args = parser.parse_args()
    if args.language == "both":
        for language in ("en", "zh"):
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "experiments.plot_team_benchmark",
                    "--input",
                    str(args.input),
                    "--output",
                    str(args.output),
                    "--scenario",
                    args.scenario,
                    "--language",
                    language,
                ],
                check=True,
            )
        return
    os.environ["MICA_FIGURE_LANGUAGE"] = args.language
    if args.language == "zh":
        args.output = args.output / "zh"
    rows, manifests = load_campaign(args.input)
    report = analyze(rows, manifests, args.scenario)
    args.output.mkdir(parents=True, exist_ok=True)
    analysis = args.output / "analysis"
    analysis.mkdir(exist_ok=True)
    write_source_csv(rows, analysis / "source_data.csv")
    report["manifests"] = manifests
    (analysis / "statistics.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with publication_style():
        outcomes(rows, report, args.output)
        contrasts(report, args.output)
    print(f"Rendered {report['rows_selected']}/{report['rows_total']} missions to {args.output}")


if __name__ == "__main__":
    main()
