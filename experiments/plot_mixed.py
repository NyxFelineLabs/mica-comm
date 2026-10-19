"""Render a complete mixed-team campaign, with no historical experiment inputs."""

import argparse
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from experiments.team_analysis import mean_interval
from mica_comm.evaluation.campaign import load_current
from mica_comm.visualization.style import export_figure, publication_style

COLORS = {"sem": "#EB6834", "mica": "#2A78D6", "genie": "#7A7974"}
MARKERS = {"sem": "s", "mica": "o", "genie": "^"}
POLICIES = ("sem", "mica", "genie")
LABELS = {"sem": "SYNC", "mica": "MICA", "genie": "IDEAL"}


class Figures:
    def __init__(self, rows, output, language):
        self.rows, self.output, self.language = rows, Path(output), language
        self.groups = defaultdict(list)
        for row in rows:
            self.groups[row["experiment"], row["parameter"], row["scheme"]].append(row)
        self.catalog = []

    def text(self, en, zh):
        return zh if self.language == "zh" else en

    def metric_label(self, metric):
        return {
            "completion_time": self.text("Mission time (slots)", "任务时长（时隙）"),
            "symbols": self.text("Uplink symbols (×10³)", "上行符号（×10³）"),
            "total_symbols": self.text("Total symbols (×10³)", "总通信符号（×10³）"),
            "saved_fraction": self.text("Survivors rescued before deadline", "截止时间前获救比例"),
        }[metric]

    def save(self, fig, name, title):
        fig.suptitle(title, fontsize=9)
        fig.tight_layout(pad=1.2)
        export_figure(fig, self.output / name)
        plt.close(fig)
        preview = self.output / "previews"
        preview.mkdir(exist_ok=True)
        with Image.open(self.output / "png" / f"{name}.png") as image:
            image.thumbnail((1600, 900))
            image.save(preview / f"{name}.png")
        self.catalog.append({"name": name, "title": title})

    def bar(self, experiment, name, title):
        if not any(k[0] == experiment for k in self.groups):
            return
        fig, axes = plt.subplots(1, 3, figsize=(8.2, 2.9))
        for ax, metric in zip(axes, ("completion_time", "symbols", "total_symbols")):
            policies = [p for p in POLICIES if (experiment, 0, p) in self.groups]
            if metric != "completion_time":
                policies = [p for p in policies if p != "genie"]
            for i, policy in enumerate(policies):
                interval = mean_interval([r[metric] for r in self.groups[experiment, 0, policy]])
                scale = 1000 if "symbols" in metric else 1
                y, lo, hi = (interval[k] / scale for k in ("mean", "low", "high"))
                ax.bar(
                    i,
                    y,
                    color=COLORS[policy],
                    edgecolor="#333333",
                    linewidth=0.6,
                    hatch="//" if policy == "sem" else None,
                )
                ax.errorbar(i, y, yerr=[[y - lo], [hi - y]], fmt="none", color="#333333", capsize=3)
            ax.set_xticks(range(len(policies)), [LABELS[p] for p in policies])
            ax.set_ylabel(self.metric_label(metric))
            ax.set_ylim(bottom=0)
            ax.grid(axis="x", visible=False)
        self.save(fig, name, title)

    def trend(self, experiment, name, title, xlabel, metrics=("completion_time", "symbols")):
        parameters = sorted({k[1] for k in self.groups if k[0] == experiment})
        if not parameters:
            return
        fig, axes = plt.subplots(1, len(metrics), figsize=(7.0, 2.9), squeeze=False)
        for ax, metric in zip(axes[0], metrics):
            for policy in POLICIES:
                if metric != "completion_time" and policy == "genie":
                    continue
                points = [
                    (x, self.groups[experiment, x, policy])
                    for x in parameters
                    if (experiment, x, policy) in self.groups
                ]
                if not points:
                    continue
                intervals = [mean_interval([r[metric] for r in group]) for _, group in points]
                scale = 1000 if "symbols" in metric else 1
                x = [p[0] for p in points]
                y = [p["mean"] / scale for p in intervals]
                ax.plot(
                    x,
                    y,
                    marker=MARKERS[policy],
                    color=COLORS[policy],
                    label=LABELS[policy],
                    linestyle="--" if policy == "genie" else "-",
                )
                ax.fill_between(
                    x,
                    [p["low"] / scale for p in intervals],
                    [p["high"] / scale for p in intervals],
                    color=COLORS[policy],
                    alpha=0.13,
                )
            ax.set_xlabel(xlabel)
            ax.set_ylabel(self.metric_label(metric))
            if metric == "saved_fraction":
                ax.set_ylim(0, 1.05)
            ax.legend()
        self.save(fig, name, title)

    def defaults(self):
        self.bar(
            "default",
            "01_primary",
            self.text("Three planners + three different LLMs", "三个 planner + 三个不同模型 LLM"),
        )
        group = [r for r in self.rows if r["experiment"] == "default"]
        if not group:
            return
        fig, ax = plt.subplots(figsize=(7, 2.9))
        for policy in POLICIES:
            values = []
            for row in group:
                if row["scheme"] != policy:
                    continue
                curve = np.array(row["curve"], dtype=float)
                # The simulator stops filling a curve at completion.
                curve[row["completion_time"] :] = curve[row["completion_time"] - 1]
                values.append(curve)
            if not values:
                continue
            values = np.array(values)
            idx = np.random.default_rng(5821).integers(0, len(values), (2000, len(values)))
            boot = values[idx].mean(axis=1)
            lo, hi = np.percentile(boot, [2.5, 97.5], axis=0)
            x = np.arange(1, values.shape[1] + 1)
            ax.plot(x, values.mean(axis=0), color=COLORS[policy], label=LABELS[policy])
            ax.fill_between(x, lo, hi, color=COLORS[policy], alpha=0.13)
        ax.set_xlabel(self.text("Simulation slot", "仿真时隙"))
        ax.set_ylabel(self.text("Located survivors", "已确认幸存者数"))
        ax.legend()
        self.save(fig, "02_progress", self.text("Search progress", "搜索进度"))
        # Fixed first seed for the illustration; no outcome-based selection.
        first = min(r["seed"] for r in group)
        selected = next(r for r in group if r["seed"] == first and r["scheme"] == "mica")
        fig, ax = plt.subplots(figsize=(4.2, 4.0))
        palette = plt.get_cmap("tab10")
        for i, trajectory in enumerate(selected["trajectories"]):
            xy = np.array(trajectory)
            model = selected["llm_by_agent"].get(str(i), {}).get("model", "planner")
            ax.plot(
                xy[:, 1],
                xy[:, 0],
                color=palette(i % 10),
                linewidth=1,
                label=f"{i}: {model}",
                linestyle="-" if model != "planner" else "--",
            )
            ax.scatter(xy[0, 1], xy[0, 0], color=palette(i % 10), marker="o", s=12)
        n = selected["config"]["grid"]
        vx, vy = np.divmod(selected["victims"], n)
        ax.scatter(
            vy,
            vx,
            marker="*",
            color="black",
            s=48,
            label=self.text("Survivors", "幸存者"),
            zorder=4,
        )
        ax.set(xlim=(-0.5, n - 0.5), ylim=(n - 0.5, -0.5), aspect="equal")
        ax.set_xlabel(self.text("Grid column", "网格列"))
        ax.set_ylabel(self.text("Grid row", "网格行"))
        ax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=6)
        self.save(
            fig,
            "15_trajectory",
            self.text(f"MICA trajectory, seed {first}", f"MICA 轨迹，种子 {first}"),
        )
        fig, axes = plt.subplots(1, 2, figsize=(7, 2.9))
        for policy in POLICIES:
            subset = [r for r in group if r["scheme"] == policy]
            for offset, (agent, model) in enumerate(
                zip(("0", "2", "4"), ("Qwen3 8B", "Llama 3.1 8B", "Gemma 3 12B"))
            ):
                x = offset + (POLICIES.index(policy) - 1) * 0.23
                decisions = [r["llm_by_agent"][agent]["decisions"] for r in subset]
                agreements = [
                    r["llm_by_agent"][agent]["agree_with_planner"]
                    / max(r["llm_by_agent"][agent]["decisions"], 1)
                    for r in subset
                ]
                for ax, values in zip(axes, (decisions, agreements)):
                    ci = mean_interval(values)
                    ax.bar(
                        x,
                        ci["mean"],
                        width=0.21,
                        color=COLORS[policy],
                        label=LABELS[policy] if offset == 0 else None,
                    )
                    ax.errorbar(
                        x,
                        ci["mean"],
                        yerr=[[ci["mean"] - ci["low"]], [ci["high"] - ci["mean"]]],
                        fmt="none",
                        color="black",
                        capsize=2,
                    )
            for ax in axes:
                ax.set_xticks(range(3), ["Qwen3 8B", "Llama 3.1 8B", "Gemma 3 12B"])
                ax.legend()
        axes[0].set_ylabel(self.text("LLM decisions per mission", "每任务 LLM 决策次数"))
        axes[1].set_ylabel(self.text("Agreement with planner candidate", "与 planner 候选的一致率"))
        axes[1].set_ylim(0, 1)
        self.save(
            fig,
            "17_agent_behavior",
            self.text("Model behavior within the mixed team", "混编团队内的模型行为"),
        )

    def paired_snr(self):
        parameters = sorted({k[1] for k in self.groups if k[0] == "snr"})
        if not parameters:
            return
        fig, ax = plt.subplots(figsize=(7, 2.9))
        for snr in parameters:
            periodic = {r["seed"]: r for r in self.groups["snr", snr, "sem"]}
            differences = [
                periodic[r["seed"]]["completion_time"] - r["completion_time"]
                for r in self.groups["snr", snr, "mica"]
            ]
            ci = mean_interval(differences)
            ax.errorbar(
                snr,
                ci["mean"],
                yerr=[[ci["mean"] - ci["low"]], [ci["high"] - ci["mean"]]],
                fmt="o",
                color=COLORS["mica"],
                capsize=3,
            )
        ax.axhline(0, color="#777777", linestyle="--", linewidth=0.8)
        ax.set_xlabel("SNR (dB)")
        ax.set_ylabel(self.text("Periodic − MICA time (slots)", "定时共享 − MICA 时长（时隙）"))
        self.save(
            fig,
            "07_paired_snr",
            self.text(
                "Paired time differences; positive favors MICA", "配对时长差：正值表示 MICA 更快"
            ),
        )

    def components(self):
        group = [r for r in self.rows if r["experiment"] == "ablation"]
        if not group:
            return
        policies = ("mica", "mica_nofilter", "mica_bits", "mica_aoi")
        names = (
            ("MICA", "No filter", "Bits value", "Age value")
            if self.language == "en"
            else ("MICA", "无源过滤", "比特价值", "信息年龄价值")
        )
        fig, axes = plt.subplots(1, 2, figsize=(7, 2.9))
        for ax, metric in zip(axes, ("completion_time", "total_symbols")):
            for i, policy in enumerate(policies):
                ci = mean_interval([r[metric] for r in group if r["scheme"] == policy])
                scale = 1000 if "symbols" in metric else 1
                ax.bar(
                    i,
                    ci["mean"] / scale,
                    color=COLORS["mica"],
                    alpha=1 - 0.17 * i,
                    edgecolor="#333333",
                    linewidth=0.6,
                )
                ax.errorbar(
                    i,
                    ci["mean"] / scale,
                    yerr=[[(ci["mean"] - ci["low"]) / scale], [(ci["high"] - ci["mean"]) / scale]],
                    fmt="none",
                    color="black",
                    capsize=3,
                )
            ax.set_xticks(range(len(policies)), names, rotation=15)
            ax.set_ylabel(self.metric_label(metric))
            ax.set_ylim(bottom=0)
        self.save(fig, "14_components", self.text("Scheduler ablations", "调度器消融"))

    def coordinators(self):
        if not any(k[0] == "coordinator" for k in self.groups):
            return
        fig, axes = plt.subplots(1, 3, figsize=(8.2, 2.9))
        modes = ("static", "price", "central")
        for task in ("search", "rescue"):
            for ax, metric in zip(axes, ("completion_time", "total_symbols", "saved_fraction")):
                if metric == "saved_fraction" and task != "rescue":
                    continue
                intervals = [
                    mean_interval(
                        [r[metric] for r in self.groups["coordinator", f"{task}_{mode}", "mica"]]
                    )
                    for mode in modes
                ]
                scale = 1000 if "symbols" in metric else 1
                y = [ci["mean"] / scale for ci in intervals]
                ax.errorbar(
                    range(3),
                    y,
                    yerr=[
                        [(ci["mean"] - ci["low"]) / scale for ci in intervals],
                        [(ci["high"] - ci["mean"]) / scale for ci in intervals],
                    ],
                    label=task,
                    marker="o",
                    capsize=3,
                )
                ax.set_xticks(range(3), modes)
                ax.set_ylabel(self.metric_label(metric))
                ax.legend()
        self.save(fig, "19_coordinator", self.text("Uplink coordination modes", "上行协调模式"))

    def render(self):
        self.defaults()
        specifications = (
            (
                "agents",
                "03_team_size",
                self.text("Team size", "团队规模"),
                self.text("Agents (three fixed LLMs)", "智能体数（固定三个 LLM）"),
                ("completion_time", "symbols"),
            ),
            (
                "budget",
                "04_budget",
                self.text("Static shared uplink budget", "静态共享上行预算"),
                self.text("Symbols reserved per agent per slot", "每 agent 每时隙预留符号"),
                ("completion_time", "symbols"),
            ),
            (
                "snr",
                "05_snr_time",
                self.text("SNR and mission time", "SNR 与任务时长"),
                "SNR (dB)",
                ("completion_time",),
            ),
            (
                "snr",
                "06_snr_cost",
                self.text("SNR and communication cost", "SNR 与通信开销"),
                "SNR (dB)",
                ("symbols", "total_symbols"),
            ),
            (
                "downlink_loss",
                "08_broadcast_loss",
                self.text("Broadcast loss", "广播丢失"),
                self.text("Broadcast loss probability", "广播丢失概率"),
                ("completion_time", "symbols"),
            ),
            (
                "downlink_delay",
                "09_broadcast_delay",
                self.text("Broadcast delay", "广播延迟"),
                self.text("Broadcast delay (slots)", "广播延迟（时隙）"),
                ("completion_time", "symbols"),
            ),
            (
                "shared",
                "10_shared_budget",
                self.text("Price-coordinated shared uplink", "价格协调的共享上行"),
                self.text("Total uplink budget per slot", "每时隙总上行预算"),
                ("completion_time", "total_symbols"),
            ),
            (
                "fbl",
                "11_finite_blocklength",
                self.text("Finite-blocklength channel", "有限码长信道"),
                "SNR (dB)",
                ("completion_time", "symbols"),
            ),
            (
                "rescue",
                "12_rescue",
                self.text("Rescue before deadlines", "截止时间前救援"),
                self.text("Per-agent symbol cap per slot", "每 agent 每时隙符号上限"),
                ("saved_fraction", "total_symbols"),
            ),
            (
                "noise",
                "18_value_noise",
                self.text("Semantic value noise", "语义价值噪声"),
                self.text("Lognormal noise standard deviation", "对数正态噪声标准差"),
                ("completion_time", "symbols"),
            ),
        )
        for args in specifications:
            self.trend(*args)
        self.paired_snr()
        self.components()
        self.coordinators()
        self.bar(
            "table_xii",
            "16_table_xii",
            self.text(
                "Table XII extension: three models in one team",
                "Table XII 扩展：三个模型在同一团队",
            ),
        )
        parameters = sorted({k[1] for k in self.groups if k[0] == "budget"})
        if parameters:
            fig, ax = plt.subplots(figsize=(7, 2.9))
            for policy in ("sem", "mica"):
                for budget in parameters:
                    rows = self.groups["budget", budget, policy]
                    x = np.mean([r["symbols"] for r in rows]) / 1000
                    y = np.mean([r["completion_time"] for r in rows])
                    ax.scatter(
                        x,
                        y,
                        marker=MARKERS[policy],
                        color=COLORS[policy],
                        label=LABELS[policy] if budget == parameters[0] else None,
                    )
                    ax.annotate(
                        str(budget), (x, y), xytext=(4, 4), textcoords="offset points", fontsize=7
                    )
            ax.set_xlabel(self.metric_label("symbols"))
            ax.set_ylabel(self.metric_label("completion_time"))
            ax.legend()
            self.save(
                fig,
                "13_budget_tradeoff",
                self.text(
                    "Budget means; labels are per-agent symbol shares",
                    "预算点均值：标注为每 agent 符号份额",
                ),
            )
        return self.catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", choices=("en", "zh", "both"), default="both")
    args = parser.parse_args()
    rows, manifest = load_current(args.input)
    if manifest.get("team") != "mixed":
        parser.error("This figure collection requires the three-model mixed team")
    languages = ("en", "zh") if args.language == "both" else (args.language,)
    for language in languages:
        os.environ["MICA_FIGURE_LANGUAGE"] = language
        output = args.output / language
        with publication_style():
            catalog = Figures(rows, output, language).render()
        audit = {
            "input": str(args.input.resolve()),
            "source_sha256": manifest["source_sha256"],
            "missions": len(rows),
            "language": language,
            "figures": catalog,
            "records_sha256": hashlib.sha256(
                (args.input / "missions.jsonl").read_bytes()
            ).hexdigest(),
            "plot_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }
        (output / "manifest.json").write_text(
            json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        lines = [
            "# Mixed-team experiment figures",
            "",
            "Three planners + Qwen3 8B + Llama 3.1 8B + Gemma 3 12B.",
            "",
            f"All {len(rows)} missions validated against the configuration manifest. No historical results are included.",
            "",
            "Exploratory 95% mission-seed bootstrap intervals; unadjusted for multiple comparisons. IDEAL bypasses delivery constraints; its zero uplink accounting is not a physical zero-cost claim.",
            "",
        ]
        for figure in sorted(catalog, key=lambda f: f["name"]):
            name = figure["name"]
            lines += [
                f"## {figure['title']}",
                "",
                f"[PDF]({name}.pdf) · [SVG](svg/{name}.svg)",
                "",
                f"![{figure['title']}](previews/{name}.png)",
                "",
            ]
        (output / "README.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"{language}: {len(catalog)} figures in {output}", flush=True)


if __name__ == "__main__":
    main()
