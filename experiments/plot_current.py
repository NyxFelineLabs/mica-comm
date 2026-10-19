"""Build the current bilingual figure collection from verified mission records.

The figure numbers and names describe measured quantities, not legacy filenames.
All observations are retained, including missions that reached the time horizon.
"""

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from experiments.team_analysis import (
    MODEL_LABELS,
    analyze,
    load_campaign,
    mean_interval,
    write_source_csv,
)
from mica_comm.evaluation.campaign import load_current
from mica_comm.visualization.style import export_figure, publication_style

POLICIES = ("sem", "mica", "genie")
COLORS = {"sem": "#4776A8", "mica": "#D5653C", "genie": "#51866C"}
MARKERS = {"sem": "o", "mica": "s", "genie": "^"}
LABELS = {
    "zh": {
        "sem": "定时状态共享（SYNC）",
        "mica": "任务价值调度（MICA）",
        "genie": "即时共享参考（IDEAL）",
    },
    "en": {
        "sem": "Timed state sharing (SYNC)",
        "mica": "Task-value scheduling (MICA)",
        "genie": "Instant sharing (IDEAL)",
    },
}
CATALOG = (
    ("01", "任务完成时长与上行开销", "Mission time and uplink cost"),
    ("02", "目标确认进度", "Target confirmation progress"),
    ("03", "团队规模影响", "Team size"),
    ("04", "上行预算影响", "Per-agent uplink budget"),
    ("05", "链路信噪比与任务时长", "SNR and mission time"),
    ("06", "链路信噪比与上行开销", "SNR and uplink cost"),
    ("07", "链路条件下的配对时长差异", "Paired time differences by SNR"),
    ("08", "广播丢失影响", "Broadcast loss"),
    ("09", "广播延迟影响", "Broadcast delay"),
    ("10", "共享预算与总通信开销", "Shared budget and total communication cost"),
    ("11", "有限码长传输影响", "Finite-blocklength transmission"),
    ("12", "截止时间下的救援完成比例", "Rescue fraction before deadlines"),
    ("13", "任务时长与通信开销权衡", "Mission time versus uplink cost"),
    ("14", "任务价值调度模块分析", "Task-value scheduler components"),
    ("15", "多智能体搜索轨迹", "Multiagent search trajectories"),
    ("16", "语言模型任务表现与上行开销", "Language-model mission outcomes"),
    ("17", "语言模型同种子任务差异", "Paired language-model time differences"),
    ("18", "语义价值估计扰动", "Semantic-value estimation noise"),
)


def _read(root):
    """Use raw results locally or the identical public JSON snapshot after cloning."""
    if not (root / "records.json").exists():
        return load_current(root)
    # The same cohort validator serves both encodings; no alternate selection path.
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        shutil.copyfile(root / "manifest.json", directory / "manifest.json")
        rows = json.loads((root / "records.json").read_text(encoding="utf-8"))
        (directory / "missions.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
        )
        return load_current(directory)


class Figures:
    """Small plotting helpers with consistent units, colors, and interval rules."""

    def __init__(self, rows, language, output):
        self.rows, self.language, self.output = rows, language, output
        self.labels = LABELS[language]

    def text(self, zh, en):
        return zh if self.language == "zh" else en

    @property
    def time_label(self):
        return self.text("任务完成时长（时隙）", "Mission time (slots)")

    @property
    def cost_label(self):
        return self.text("上行信道用量（千符号）", "Uplink cost (thousand symbols)")

    def select(self, experiment, policy, parameter=None):
        return [
            r
            for r in self.rows
            if r["experiment"] == experiment
            and r["scheme"] == policy
            and (parameter is None or r["parameter"] == parameter)
        ]

    def canvas(self, number, columns=1, height=3.7):
        fig, axes = plt.subplots(1, columns, figsize=(8.2, height), squeeze=False)
        fig.subplots_adjust(left=0.12, right=0.98, bottom=0.27, top=0.82, wspace=0.38)
        entry = next(c for c in CATALOG if c[0] == number)
        fig.suptitle(entry[1 if self.language == "zh" else 2], y=0.96, fontsize=12)
        return fig, axes[0]

    def save(self, fig, number, legend=True):
        if legend:
            entries = {}
            for ax in fig.axes:
                handles, labels = ax.get_legend_handles_labels()
                entries.update(zip(labels, handles))
            if entries:
                fig.legend(
                    entries.values(),
                    entries.keys(),
                    loc="lower center",
                    bbox_to_anchor=(0.54, 0.015),
                    ncol=min(3, len(entries)),
                    frameon=False,
                    fontsize=9,
                )
        entry = next(c for c in CATALOG if c[0] == number)
        name = entry[1] if self.language == "zh" else entry[2].lower().replace(" ", "_")
        export_figure(fig, self.output / f"{number}_{name}.pdf", fixed_size=True)
        plt.close(fig)

    def estimate(self, rows, metric, scale=1):
        result = mean_interval([r[metric] / scale for r in rows])
        return result["mean"], result["mean"] - result["low"], result["high"] - result["mean"]

    def bars(self, ax, experiment, metric, policies=POLICIES, scale=1):
        for i, policy in enumerate(policies):
            mean, low, high = self.estimate(self.select(experiment, policy), metric, scale)
            ax.bar(i, mean, color=COLORS[policy], width=0.6, label=self.labels[policy])
            ax.errorbar(i, mean, yerr=[[low], [high]], color="#333333", capsize=3, fmt="none", lw=1)
        ax.set_xticks(range(len(policies)))
        ax.set_xticklabels([{"sem": "SYNC", "mica": "MICA", "genie": "IDEAL"}[p] for p in policies])
        ax.set_ylim(bottom=0)

    def sweep(
        self,
        number,
        experiment,
        xlabels,
        metric="completion_time",
        ylabel=None,
        scale=1,
        policies=POLICIES,
    ):
        fig, (ax,) = self.canvas(number)
        values = sorted({r["parameter"] for r in self.rows if r["experiment"] == experiment})
        for policy in policies:
            estimates = [
                self.estimate(self.select(experiment, policy, v), metric, scale) for v in values
            ]
            mean, low, high = np.array(estimates).T
            ax.plot(
                values,
                mean,
                color=COLORS[policy],
                marker=MARKERS[policy],
                label=self.labels[policy],
            )
            ax.fill_between(
                values, mean - low, mean + high, color=COLORS[policy], alpha=0.12, linewidth=0
            )
        ax.set(xlabel=self.text(*xlabels), ylabel=ylabel or self.time_label, xticks=values)
        if metric == "saved_fraction":
            ax.set_ylim(0, 1.02)
        self.save(fig, number)

    def standard(self):
        fig, axes = self.canvas("01", 2)
        self.bars(axes[0], "default", "completion_time")
        self.bars(axes[1], "default", "symbols", ("sem", "mica"), 1000)
        axes[0].set_ylabel(self.time_label)
        axes[1].set_ylabel(self.cost_label)
        self.save(fig, "01")

        fig, (ax,) = self.canvas("02")
        for policy in POLICIES:
            curves = np.array([r["curve"] for r in self.select("default", policy)])
            horizon = max(r["completion_time"] for r in self.rows if r["experiment"] == "default")
            curves = curves[:, :horizon]
            times = np.arange(curves.shape[1])
            rng = np.random.default_rng(5821)
            indices = rng.integers(0, len(curves), (2000, len(curves)))
            low, high = np.percentile(curves[indices].mean(axis=1), [2.5, 97.5], axis=0)
            ax.plot(times, curves.mean(axis=0), color=COLORS[policy], label=self.labels[policy])
            ax.fill_between(times, low, high, color=COLORS[policy], alpha=0.12, linewidth=0)
        ax.set(
            xlabel=self.text("任务时隙", "Mission slot"),
            ylabel=self.text("已确认目标数", "Confirmed targets"),
            ylim=(0, 8.2),
        )
        self.save(fig, "02")

        self.sweep("03", "agents", ("智能体数量", "Number of agents"))
        self.sweep("04", "budget", ("每智能体每时隙符号预算", "Symbols per agent per slot"))
        self.sweep("05", "snr", ("参考信噪比（dB）", "Reference SNR (dB)"))
        self.sweep(
            "06",
            "snr",
            ("参考信噪比（dB）", "Reference SNR (dB)"),
            "symbols",
            self.cost_label,
            1000,
            ("sem", "mica"),
        )
        fig, (ax,) = self.canvas("07")
        values = sorted({r["parameter"] for r in self.rows if r["experiment"] == "snr"})
        estimates = []
        for value in values:
            sync = {r["seed"]: r["completion_time"] for r in self.select("snr", "sem", value)}
            mica = {r["seed"]: r["completion_time"] for r in self.select("snr", "mica", value)}
            estimates.append(mean_interval([mica[s] - sync[s] for s in sorted(sync)]))
        means = np.array([r["mean"] for r in estimates])
        ax.errorbar(
            values,
            means,
            yerr=[means - [r["low"] for r in estimates], [r["high"] for r in estimates] - means],
            fmt="s-",
            color=COLORS["mica"],
            capsize=3,
        )
        ax.axhline(0, color="#777777", lw=0.8, ls="--")
        ax.set(
            xlabel=self.text("参考信噪比（dB）", "Reference SNR (dB)"),
            ylabel=self.text("MICA − SYNC 时长（时隙）", "MICA − SYNC time (slots)"),
            xticks=values,
        )
        self.save(fig, "07", False)
        self.sweep("08", "downlink_loss", ("广播丢失概率", "Broadcast loss probability"))
        self.sweep("09", "downlink_delay", ("广播延迟（时隙）", "Broadcast delay (slots)"))
        self.sweep(
            "10",
            "shared",
            ("每时隙团队共享符号预算", "Shared symbols per slot"),
            "total_symbols",
            self.text("总信道用量（千符号）", "Total cost (thousand symbols)"),
            1000,
            ("sem", "mica"),
        )
        self.sweep(
            "11", "fbl", ("参考信噪比（dB）", "Reference SNR (dB)"), policies=("sem", "mica")
        )
        self.sweep(
            "12",
            "rescue",
            ("每智能体每时隙符号预算", "Symbols per agent per slot"),
            "saved_fraction",
            self.text("截止前救援完成比例", "Rescued before deadline (fraction)"),
        )

        fig, (ax,) = self.canvas("13")
        for policy in ("sem", "mica"):
            rows = self.select("budget", policy)
            values = sorted({r["parameter"] for r in rows})
            means = np.array(
                [
                    (
                        np.mean([r["symbols"] for r in rows if r["parameter"] == v]) / 1000,
                        np.mean([r["completion_time"] for r in rows if r["parameter"] == v]),
                    )
                    for v in values
                ]
            )
            ax.plot(
                *means.T, color=COLORS[policy], marker=MARKERS[policy], label=self.labels[policy]
            )
            for index, (budget, (x, y)) in enumerate(zip(values, means)):
                ax.annotate(
                    str(budget),
                    (x, y),
                    xytext=(5, 9 if index % 2 == 0 else -13),
                    textcoords="offset points",
                    fontsize=8,
                )
        ax.set(xlabel=self.cost_label, ylabel=self.time_label)
        self.save(fig, "13")

        fig, axes = self.canvas("14", 2, 4.1)
        variants = ("mica", "mica_nofilter", "mica_bits", "mica_aoi")
        names = self.text(
            ["MICA", "关闭过滤", "比特量赋值", "信息年龄赋值"],
            ["MICA", "No filter", "Bit value", "Age value"],
        )
        for ax, metric, ylabel, scale in zip(
            axes, ("completion_time", "symbols"), (self.time_label, self.cost_label), (1, 1000)
        ):
            for i, policy in enumerate(variants):
                mean, low, high = self.estimate(self.select("ablation", policy), metric, scale)
                ax.bar(i, mean, color=["#D5653C", "#4776A8", "#51866C", "#9577A8"][i], width=0.65)
                ax.errorbar(i, mean, yerr=[[low], [high]], color="#333333", fmt="none", capsize=3)
            ax.set(xticks=range(4), ylabel=ylabel, ylim=(0, None))
            ax.set_xticklabels(names, rotation=25, ha="right", fontsize=8)
        self.save(fig, "14", False)

        fig, axes = self.canvas("15", 3, 4.2)
        fig.subplots_adjust(left=0.06, right=0.98, bottom=0.22, wspace=0.22)
        first_seed = min(r["seed"] for r in self.rows)
        palette = ["#4776A8", "#D5653C", "#51866C", "#9577A8", "#AE8640", "#65A2AF"]
        for ax, policy in zip(axes, POLICIES):
            row = next(r for r in self.select("default", policy) if r["seed"] == first_seed)
            for i, trajectory in enumerate(row["trajectories"]):
                points = np.asarray(trajectory)
                ax.plot(points[:, 1], points[:, 0], color=palette[i], linewidth=0.9, alpha=0.85)
                ax.scatter(points[0, 1], points[0, 0], color=palette[i], marker="o", s=15, zorder=3)
            x, y = np.divmod(row["victims"], row["config"]["grid"])
            ax.scatter(y, x, marker="*", color="#222222", s=32, zorder=4)
            ax.set(
                xlim=(-1, 32),
                ylim=(32, -1),
                aspect="equal",
                xticks=(0, 15, 31),
                yticks=(0, 15, 31),
                title={"sem": "SYNC", "mica": "MICA", "genie": "IDEAL"}[policy],
                xlabel=self.text("网格列", "Grid column"),
            )
        axes[0].set_ylabel(self.text("网格行", "Grid row"))
        fig.text(
            0.52,
            0.05,
            self.text(
                f"固定种子 {first_seed}；星形为目标，圆点为起点",
                f"Fixed seed {first_seed}; stars: targets, circles: starts",
            ),
            ha="center",
            fontsize=9,
        )
        self.save(fig, "15", False)
        self.sweep(
            "18",
            "noise",
            ("对数正态扰动标准差", "Lognormal noise standard deviation"),
            policies=("mica",),
        )

    def llm(self, summary):
        models = list(summary["absolute"])
        x = np.arange(len(models))
        fig, axes = self.canvas("16", 2, 4.0)
        for ax, metric, scale, ylabel in zip(
            axes, ("completion_time", "symbols"), (1, 1000), (self.time_label, self.cost_label)
        ):
            policies = POLICIES if metric == "completion_time" else ("sem", "mica")
            for i, policy in enumerate(policies):
                estimates = [summary["absolute"][m][policy][metric] for m in models]
                means = np.array([e["mean"] / scale for e in estimates])
                errors = [
                    [(e["mean"] - e["low"]) / scale for e in estimates],
                    [(e["high"] - e["mean"]) / scale for e in estimates],
                ]
                ax.bar(
                    x + (i - (len(policies) - 1) / 2) * 0.24,
                    means,
                    width=0.23,
                    color=COLORS[policy],
                    label=self.labels[policy],
                    yerr=errors,
                    capsize=2,
                    error_kw={"elinewidth": 0.8},
                )
            ax.set(xticks=x, ylabel=ylabel, ylim=(0, None))
            ax.set_xticklabels([MODEL_LABELS[m].replace(" ", "\n", 1) for m in models], fontsize=9)
        self.save(fig, "16")
        fig, axes = self.canvas("17", 3, 4.8)
        fig.subplots_adjust(left=0.08, right=0.98, bottom=0.42, wspace=0.3)
        all_differences = [d for contrast in summary["contrasts"] for d in contrast["differences"]]
        limits = min(all_differences) - 12, max(all_differences) + 12
        for ax, policy in zip(axes, POLICIES):
            comparisons = [c for c in summary["contrasts"] if c["policy"] == policy]
            for i, contrast in enumerate(comparisons):
                values = contrast["differences"]
                ax.scatter(
                    np.full(len(values), i) + np.linspace(-0.12, 0.12, len(values)),
                    values,
                    color=COLORS[policy],
                    alpha=0.35,
                    s=12,
                )
                mean = contrast["mean"]
                ax.errorbar(
                    i,
                    mean,
                    yerr=[[mean - contrast["low"]], [contrast["high"] - mean]],
                    fmt="D",
                    color="#222222",
                    capsize=3,
                )
            ax.axhline(0, lw=0.8, color="#777777", ls="--")
            ax.set(
                title={"sem": "SYNC", "mica": "MICA", "genie": "IDEAL"}[policy],
                xticks=range(len(comparisons)),
                ylim=limits,
            )
            ax.set_xticklabels(
                [f"{MODEL_LABELS[c['first']]}\n− {MODEL_LABELS[c['second']]}" for c in comparisons],
                rotation=45,
                ha="right",
                fontsize=8,
            )
        axes[0].set_ylabel(self.text("前者 − 后者时长（时隙）", "First − second time (slots)"))
        self.save(fig, "17", False)


def publish(rows, manifest, model_rows, model_manifests, summary, destination):
    """Publish self-contained outcomes; caches and model weights remain local."""
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "records.json").write_text(
        json.dumps(rows, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    standard_summary = {
        policy: {
            "n": len(group),
            "completion_rate": float(np.mean([r["completed"] for r in group])),
            "completion_time": mean_interval([r["completion_time"] for r in group]),
            "symbols": mean_interval([r["symbols"] for r in group]),
            "total_symbols": mean_interval([r["total_symbols"] for r in group]),
        }
        for policy in POLICIES
        for group in [[r for r in rows if r["experiment"] == "default" and r["scheme"] == policy]]
    }
    (destination / "summary.json").write_text(
        json.dumps(standard_summary, indent=2) + "\n", encoding="utf-8"
    )
    fields = [
        "experiment",
        "parameter",
        "scheme",
        "seed",
        "completion_time",
        "completed",
        "symbols",
        "total_symbols",
        "saved_fraction",
    ]
    with (destination / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    llm_dir = destination / "llm"
    llm_dir.mkdir(exist_ok=True)
    write_source_csv(model_rows, llm_dir / "missions.csv")
    for model, metadata in model_manifests.items():
        folder = llm_dir / model.replace(":", "_")
        folder.mkdir(exist_ok=True)
        (folder / "manifest.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
    (llm_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/current_20261019"))
    parser.add_argument("--llm-input", type=Path, default=Path("results/team_replay_20261019"))
    parser.add_argument("--output", type=Path, default=Path("figures/current"))
    parser.add_argument("--report", type=Path, default=Path("reports/current"))
    parser.add_argument("--language", choices=("zh", "en", "both"), default="both")
    args = parser.parse_args()
    rows, manifest = _read(args.input)
    model_rows, model_manifests = load_campaign(args.llm_input)
    summary = analyze(model_rows, model_manifests)
    publish(rows, manifest, model_rows, model_manifests, summary, args.report)
    args.output.mkdir(parents=True, exist_ok=True)
    for language in ("zh", "en") if args.language == "both" else (args.language,):
        os.environ["MICA_FIGURE_LANGUAGE"] = language
        with (
            publication_style(),
            plt.rc_context(
                {
                    "font.size": 10,
                    "axes.labelsize": 10,
                    "xtick.labelsize": 9,
                    "ytick.labelsize": 9,
                    "axes.titlesize": 10,
                    "axes.unicode_minus": False,
                }
            ),
        ):
            collection = Figures(rows, language, args.output / language)
            collection.standard()
            collection.llm(summary)
        print(f"Exported 18 figures: {language}", flush=True)
        preview_dir = args.report / "previews"
        preview_dir.mkdir(exist_ok=True)
        for number, label in (("01", "standard"), ("16", "llm")):
            source = next((args.output / language / "png").glob(f"{number}_*.png"))
            with Image.open(source) as preview:
                preview.thumbnail((1400, 850), Image.Resampling.LANCZOS)
                preview.save(preview_dir / f"{language}_{label}.png", optimize=True)
    guide = [
        "# Current figure collection / 当前图表",
        "",
        "每张图均导出 PDF、SVG 和 600 dpi PNG。阴影和误差线为按任务种子重采样的探索性 95% bootstrap 区间（未校正多重比较）。",
        "",
        "Each figure has PDF, SVG and 600 dpi PNG exports. Bands/bars show exploratory mission-seed bootstrap 95% intervals (unadjusted).",
        "",
        "| 编号 | 中文名称 | English name |",
        "| --- | --- | --- |",
    ]
    guide.extend(
        f"| {number} | [{zh}](../../figures/current/zh/{number}_{zh}.pdf) | [{en}](../../figures/current/en/{number}_{en.lower().replace(' ', '_')}.pdf) |"
        for number, zh, en in CATALOG
    )
    guide.extend(
        [
            "",
            "图 13 标注各预算点的均值，不声称全局 Pareto 最优；图 15 固定采用首个种子，属于示例。IDEAL 不受实际投递约束，其零符号记账不代表零物理成本。",
            "",
            "Figure 13 labels mean outcomes by budget, without claiming global Pareto optimality. Figure 15 uses the first seed as an example. IDEAL's zero uplink accounting does not imply zero physical cost.",
        ]
    )
    (args.report / "README.md").write_text("\n".join(guide) + "\n", encoding="utf-8")
    inputs = {
        "standard_source_sha256": manifest["source_sha256"],
        "standard_missions": len(rows),
        "llm_missions": len(model_rows),
        "llm_execution": "offline replay of our own measured responses",
        "records_sha256": hashlib.sha256((args.report / "records.json").read_bytes()).hexdigest(),
    }
    (args.report / "provenance.json").write_text(
        json.dumps(inputs, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
