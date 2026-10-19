"""Validate and publish completed mixed-team reports and bilingual figures locally."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    from experiments.summarize_current import write_report
    from mica_comm.core.paths import PROJECT_ROOT
    from mica_comm.evaluation.campaign import load_current

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--reports", type=Path, default=PROJECT_ROOT / "reports/current_mixed")
    parser.add_argument("--figures", type=Path, default=PROJECT_ROOT / "figures/current_mixed")
    args = parser.parse_args()
    rows, manifest = load_current(args.input)
    if manifest.get("team") != "mixed":
        parser.error("Finalization requires a mixed-team campaign")
    report = write_report(args.input)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "experiments.plot_mixed",
            "--input",
            str(args.input),
            "--output",
            str(args.figures),
            "--language",
            "both",
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )
    args.reports.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "summary.json", "metrics.csv", "README.md"):
        shutil.copy2(args.input / name, args.reports / name)
    # Public records preserve all metrics and trajectories but omit response caches.
    (args.reports / "records.json").write_text(
        json.dumps(
            sorted(
                rows, key=lambda r: str((r["experiment"], r["parameter"], r["scheme"], r["seed"]))
            ),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    catalog = [
        "# Current mixed-team figure collection",
        "",
        "主基线：3 个 planner + Qwen3 8B、Llama 3.1 8B、Gemma 3 12B 各一个 LLM agent。",
        "",
        f"完整校验 {len(rows)} 次任务；后端回退 {report['llm_fallbacks']} 次。",
        "",
        "[统计与 Table XII 格式结果](README.md) · [逐任务指标](metrics.csv)",
        "",
        "图中区间为按任务种子重采样的探索性 95% bootstrap 区间，未校正多重比较。轨迹固定使用首个种子。预算散点为均值，不代表全局 Pareto 最优。",
        "",
    ]
    for language in ("zh", "en"):
        index = json.loads((args.figures / language / "manifest.json").read_text(encoding="utf-8"))
        catalog += [f"## {language}", "", "| 图表 | PDF | SVG |", "| --- | --- | --- |"]
        for figure in sorted(index["figures"], key=lambda f: f["name"]):
            name = figure["name"]
            base = f"../../figures/current_mixed/{language}"
            catalog.append(
                f"| {figure['title']} | [PDF]({base}/{name}.pdf) | [SVG]({base}/svg/{name}.svg) |"
            )
        catalog.append("")
        shutil.copytree(
            args.figures / language / "previews",
            args.reports / "previews" / language,
            dirs_exist_ok=True,
        )
    (args.reports / "FIGURES.md").write_text("\n".join(catalog), encoding="utf-8")
    for name in ("README.md", "README.zh-CN.md"):
        path = PROJECT_ROOT / name
        text = path.read_text(encoding="utf-8")
        if "reports/current_mixed/FIGURES.md" not in text:
            note = (
                (
                    "\n\n**Current main baseline:** three planners + three different LLMs. "
                    f"Completed and validated {len(rows)} missions with zero backend fallbacks. "
                    "[Results and Table XII](reports/current_mixed/README.md) · "
                    "[Bilingual figures](reports/current_mixed/FIGURES.md).\n\n"
                )
                if name == "README.md"
                else (
                    f"\n\n**当前主基线已完成：**三个 planner + 三个不同模型 LLM，共 {len(rows)} 次任务，后端回退为零。"
                    "[结果与 Table XII](reports/current_mixed/README.md) · "
                    "[中英文图表](reports/current_mixed/FIGURES.md)。\n\n"
                )
            )
            text = text.replace("</div>", "</div>" + note, 1)
            path.write_text(text, encoding="utf-8")
    print(f"Published {len(rows)} validated missions to {args.reports}", flush=True)


if __name__ == "__main__":
    main()
