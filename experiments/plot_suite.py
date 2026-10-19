"""Rebuild the complete 17-figure suite from explicit experiment records.

python -m experiments.plot_suite --input results/restored_suite
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import subprocess
import sys
from pathlib import Path

FIGURES = {
    "fig_agents": ("Team-size sweep", ("agents.json",)),
    "fig_budget": ("Per-agent communication budget", ("budget.json",)),
    "fig_curve": ("Search progress over time", ("default.json",)),
    "fig_downlink": ("Downlink loss and delay", ("robustness_downlink.json",)),
    "fig_efficiency": (
        "Task performance versus uplink resources",
        (
            "robustness_frontier.json",
            "robustness_rate_aware.json",
            "robustness_rescue.json",
            "robustness_filtered_periodic.json",
            "robustness_suppress_periodic.json",
            "robustness_genie_ref.json",
        ),
    ),
    "fig_fbl": ("Finite-blocklength channel model", ("robustness_fbl.json",)),
    "fig_frontier": ("Value-rule resource frontiers", ("robustness_frontier.json",)),
    "fig_noise": (
        "Sensitivity to value-estimation errors",
        (
            "validate_noise.json",
            "robustness_validation.json",
            "noise.jsonl",
            "robustness_genie_ref.json",
            "robustness_rescue.json",
        ),
    ),
    "fig_pareto": (
        "Communication price trade-off",
        ("pareto.json", "pareto_tv.json", "default.json"),
    ),
    "fig_rescue": (
        "Rescue success versus uplink resources",
        (
            "robustness_rescue.json",
            "robustness_filtered_periodic.json",
            "robustness_suppress_periodic.json",
        ),
    ),
    "fig_shared_col": (
        "Shared-budget frontiers, single column",
        (
            "shared.jsonl",
            "robustness_genie_ref.json",
            "robustness_rescue.json",
        ),
    ),
    "fig_shared": (
        "Shared-budget frontiers",
        (
            "validate_shared.json",
            "shared.jsonl",
            "robustness_genie_ref.json",
            "robustness_rescue.json",
        ),
    ),
    "fig_snr_pair": ("SNR: task performance and channel use", ("snr.json",)),
    "fig_snr_sym": ("SNR: channel use", ("snr.json",)),
    "fig_snr": ("SNR: task performance", ("snr.json",)),
    "fig_traj": ("Example agent trajectories", ("trajectories.json",)),
    "fig_where_tom": ("Larger teams and clustered survivors", ("robustness_where_tom.json",)),
}


def gallery(output, selected, provenance):
    """Create a compact local index; keep preview and diagnostic files off the root."""
    cards = []
    for name in selected:
        title = html.escape(FIGURES[name][0])
        cards.append(
            f'<article><h2>{title}</h2><a href="{name}.pdf"><img src="png/{name}.png" '
            f'alt="{name}"></a><p><a href="{name}.pdf">PDF</a> · '
            f'<a href="svg/{name}.svg">SVG</a> · <code>{name}</code></p></article>'
        )
    note = "Historical experiment records; figures rerendered, no new experiments."
    if not provenance:
        note = (
            "Figures rendered from the explicitly selected input directory; see audit/suite.json."
        )
    page = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>MICA figures</title>'
        "<style>body{font:16px Arial,sans-serif;max-width:1450px;margin:32px auto;padding:0 20px;"
        "color:#252525;background:#fafafa}main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));"
        "gap:24px}article{background:white;padding:18px;border:1px solid #ddd;border-radius:8px}"
        "img{width:100%;height:300px;object-fit:contain}h2{font-size:18px}a{color:#2164aa}"
        "@media(max-width:800px){main{grid-template-columns:1fr}}</style>"
        f"<h1>MICA · experiment figures</h1><p>{html.escape(note)}</p><main>"
        + "".join(cards)
        + "</main></html>"
    )
    (output / "index.html").write_text(page, encoding="utf-8")


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=root / "results/restored_suite")
    parser.add_argument("--output", type=Path, default=root / "figures")
    parser.add_argument("--only", nargs="+", choices=FIGURES)
    parser.add_argument("--language", choices=("en", "zh", "both"), default="en")
    args = parser.parse_args()
    if args.language == "both":
        for language in ("en", "zh"):
            command = [
                sys.executable,
                "-m",
                "experiments.plot_suite",
                "--input",
                str(args.input),
                "--output",
                str(args.output),
                "--language",
                language,
            ]
            if args.only:
                command += ["--only", *args.only]
            subprocess.run(command, check=True)
        return
    os.environ["MICA_FIGURE_LANGUAGE"] = args.language
    if args.language == "zh":
        args.output = args.output / "zh"
    selected = args.only or list(FIGURES)
    needed = sorted({name for figure in selected for name in FIGURES[figure][1]})
    missing = [name for name in needed if not (args.input / name).is_file()]
    if missing:
        parser.error(f"Missing experiment inputs: {', '.join(missing)}")
    # Resolve paths before importing the plotting modules, which read these settings.
    os.environ["MICA_RESULTS_DIR"] = str(args.input.resolve())
    os.environ["MICA_FIGURES_DIR"] = str(args.output.resolve())
    from experiments import plot, plot_realistic, plot_robustness
    from experiments.validate_realistic import load_jsonl
    from mica_comm.visualization.style import publication_style

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "tables").mkdir(exist_ok=True)
    (args.output / "audit").mkdir(exist_ok=True)
    jobs = {
        "fig_agents": lambda: plot.sweep_plot(
            "agents", "Number of agents, $K$", "fig_agents.pdf", xticks=[2, 4, 6, 8, 10]
        ),
        "fig_budget": lambda: plot.sweep_plot(
            "budget",
            "Channel uses per agent per slot, $W$",
            "fig_budget.pdf",
            xlog=True,
            xticks=[25, 50, 100, 200, 400],
        ),
        "fig_curve": plot.curve_plot,
        "fig_downlink": plot_robustness.downlink,
        "fig_efficiency": plot_robustness.efficiency_plot,
        "fig_fbl": plot_robustness.fbl,
        "fig_frontier": lambda: plot_robustness.frontier(with_statistics=False),
        "fig_noise": plot_realistic.noise,
        "fig_pareto": plot.pareto_plot,
        "fig_rescue": lambda: plot_robustness.rescue(with_statistics=False),
        "fig_shared_col": lambda: plot_realistic.shared_column(load_jsonl("shared")),
        "fig_shared": plot_realistic.shared,
        "fig_snr_pair": lambda: plot.sweep_pair_plot(
            "snr", "Reference SNR at 100 m (dB)", "fig_snr_pair.pdf"
        ),
        "fig_snr_sym": lambda: plot.sweep_bits_plot(
            "snr", "Reference SNR at 100 m (dB)", "fig_snr_sym.pdf"
        ),
        "fig_snr": lambda: plot.sweep_plot("snr", "Reference SNR at 100 m (dB)", "fig_snr.pdf"),
        "fig_traj": plot.traj_plot,
        "fig_where_tom": lambda: plot_robustness.where_tom(with_statistics=False),
    }
    with publication_style():
        for index, name in enumerate(selected, 1):
            print(f"[{index}/{len(selected)}] {name}", flush=True)
            jobs[name]()
    absent = [name for name in selected if not (args.output / f"{name}.pdf").is_file()]
    if absent:
        raise RuntimeError(f"Incomplete figure suite: {absent}")
    provenance_path = args.input / "provenance.json"
    provenance = (
        json.loads(provenance_path.read_text(encoding="utf-8"))
        if provenance_path.exists()
        else None
    )
    report = {
        "language": args.language,
        "input_provenance": provenance,
        "inputs": {
            name: hashlib.sha256((args.input / name).read_bytes()).hexdigest() for name in needed
        },
        "figures": {
            name: {"title": FIGURES[name][0], "inputs": list(FIGURES[name][1])} for name in selected
        },
    }
    (args.output / "audit/suite.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    gallery(args.output, selected, provenance)
    print(f"Complete: {len(selected)} PDFs; previews in png/; editable vectors in svg/", flush=True)


if __name__ == "__main__":
    main()
