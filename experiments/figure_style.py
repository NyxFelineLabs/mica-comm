"""Shared publication style and export, without changing global rcParams on import.

Use ``@publication_style()`` on plotting entry points. Optional upstream audits
are loaded from MICA_FIGURE_AUDIT_SCRIPTS; normal plots need only matplotlib.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import matplotlib as mpl

W1 = 3.45
W2 = 7.0

STYLE = {
    "mica": dict(color="#2a78d6", marker="o", label="MICA"),
    "sem": dict(color="#eb6834", marker="s", label="Semantic, periodic"),
    "raw": dict(color="#1baf7a", marker="^", label="Raw sensor data"),
    "nl": dict(color="#eda100", marker="D", label="Natural language"),
    "report": dict(color="#e87ba4", marker="v", label="Report only"),
    "mica_novoi": dict(color="#008300", marker="P", label="MICA w/o VoI"),
    "mica_tv": dict(color="#4a3aa7", marker="X", label="MICA, belief-div. VoI"),
    "genie": dict(color="#7a7974", marker="", label="Ideal reference", linestyle="--"),
}

RCPARAMS = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "legend.fontsize": 7,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "axes.edgecolor": "#4D4D4D",
    "axes.grid": True,
    "grid.color": "#e4e3de",
    "grid.linewidth": 0.5,
    "axes.axisbelow": True,
    "legend.frameon": False,
    "lines.linewidth": 1.4,
    "lines.markersize": 4,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.dpi": 600,
    "savefig.pad_inches": 0.06,
}


def publication_style():
    """Scope typography and export defaults to a plotting call or context."""
    return mpl.rc_context(RCPARAMS)


def panel_label(ax, label):
    """Place panel letters at a fixed physical offset from the axes corner."""
    ax.annotate(
        label,
        xy=(0, 1),
        xycoords="axes fraction",
        xytext=(-26, 12),
        textcoords="offset points",
        fontsize=8,
        fontweight="bold",
        annotation_clip=False,
    )


def _readable_legend(fig):
    """Keep the original comparisons and place one legend below the plot area.

    Measure the actual legend width rather than assuming a fixed column count
    fits. Descriptive method names are retained in the surrounding figure guide.
    """
    aliases = {
        "Ideal-communication reference (genie)": "Ideal communication",
        "Ideal reference": "Ideal communication",
        "MICA, theory-of-mind value": "MICA (ToM value)",
        "MICA transport, throughput value": "Throughput value",
        "MICA transport, AoI value": "Age-of-information value",
        "Belief-divergence value": "Belief-divergence value",
        "Periodic aggregated, interval $k$": "Periodic aggregated ($k$ swept)",
        "Periodic semantic (default setting)": "Semantic periodic (default)",
        "Periodic, rate-aware ($k$ swept)": "Periodic, rate-aware",
        "Periodic, rate-aware + filter ($k$ swept)": "Periodic, rate-aware + filter",
        "Periodic, suppressing (best envelope over $k$, $\\theta$)": "Periodic, suppressing envelope",
        "Periodic, suppressing (best envelope)": "Periodic, suppressing envelope",
        "MICA, price-coordinated (each $\\eta$)": "MICA (price swept)",
        "Periodic family, best envelope (fair grants)": "Periodic family, envelope",
        "MICA, belief-div. VoI": "Belief-divergence VoI",
    }
    entries = {}
    for legend in fig.legends:
        handles = getattr(legend, "legend_handles", None)
        if handles is None:
            handles = legend.legendHandles
        for handle, text in zip(handles, legend.get_texts()):
            entries.setdefault(text.get_text(), handle)
    for ax in fig.axes:
        handles, labels = ax.get_legend_handles_labels()
        for handle, label in zip(handles, labels):
            entries.setdefault(label, handle)
        legend = ax.get_legend()
        if legend is not None:
            legend.remove()
    for legend in list(fig.legends):
        legend.remove()
    if not entries:
        return
    labels = [aliases.get(label, label) for label in entries]
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    # The lowest tight axes extent includes tick labels and axis titles.
    bottom = min(ax.get_tightbbox(renderer).y0 for ax in fig.axes)
    anchor = fig.transFigure.inverted().transform((0, bottom - 10 * fig.dpi / 72))[1]
    max_columns = 3 if fig.get_figwidth() < 4 else 4
    for columns in range(min(max_columns, len(labels)), 0, -1):
        legend = fig.legend(
            list(entries.values()),
            labels,
            ncol=columns,
            fontsize=8,
            loc="upper center",
            bbox_to_anchor=(0.52, anchor),
            frameon=False,
            columnspacing=1.3,
            handlelength=2.0,
            handletextpad=0.55,
            labelspacing=0.5,
            borderaxespad=0,
        )
        fig.canvas.draw()
        if legend.get_window_extent(renderer).width <= fig.bbox.width * 0.98 or columns == 1:
            break
        legend.remove()


def _check_grid_alignment(fig, path):
    """Measure rendered plot areas; block shifted edges in simple subplot grids.

    This lightweight gate covers our rectangular subplot layouts. The optional
    upstream gate additionally audits unequal spans, panel labels and gutters.
    """
    fig.canvas.draw()
    rectangles = []
    for ax in fig.axes:
        box = ax.get_position()
        spec = ax.get_subplotspec() if hasattr(ax, "get_subplotspec") else None
        rectangles.append(
            {
                "bounds_pt": [
                    box.x0 * fig.get_figwidth() * 72,
                    box.y0 * fig.get_figheight() * 72,
                    box.x1 * fig.get_figwidth() * 72,
                    box.y1 * fig.get_figheight() * 72,
                ],
                "row": [spec.rowspan.start, spec.rowspan.stop] if spec else None,
                "column": [spec.colspan.start, spec.colspan.stop] if spec else None,
            }
        )
    failures = []
    for index, first in enumerate(rectangles):
        for second in rectangles[index + 1 :]:
            for group, coordinates in (("row", (1, 3)), ("column", (0, 2))):
                if first[group] is not None and first[group] == second[group]:
                    if any(
                        abs(first["bounds_pt"][k] - second["bounds_pt"][k]) > 1.5
                        for k in coordinates
                    ):
                        failures.append(f"Misaligned {group}: {first[group]}")
    report = {
        "status": "FAIL" if failures else "PASS" if len(rectangles) > 1 else "NOT APPLICABLE",
        "scope": "Equal-span subplot row/column edges",
        "tolerance_pt": 1.5,
        "panels": rectangles,
        "failures": failures,
    }
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise ValueError("; ".join(failures))


def export_figure(fig, path, *, fixed_size=False):
    """Write editable PDF/SVG, a 600-dpi PNG, and final-layout audit records.

    A suffix in an old call site is accepted; all three formats are exported.
    Fixed-size pages preserve the specified physical dimensions. Legacy tight
    pages accommodate external legends without clipping them.
    """
    path = Path(path)
    stem = path.with_suffix("") if path.suffix.lower() in {".pdf", ".svg", ".png"} else path
    stem.parent.mkdir(parents=True, exist_ok=True)
    if stem.name.startswith("fig_"):
        for ax in fig.axes:
            for getter, setter in ((ax.get_xlabel, ax.set_xlabel), (ax.get_ylabel, ax.set_ylabel)):
                label = getter()
                label = label.replace(" ($\\times 10^3$, log scale)", " (×10³)")
                label = label.replace(" ($\\times 10^3$, log)", " (×10³)")
                label = label.replace(" ($\\times 10^3$)", " (×10³)")
                label = label.replace(" ($\\times10^3$)", " (×10³)")
                label = label.replace("Uplink channel uses per mission", "Uplink channel uses")
                setter(label)
        _readable_legend(fig)
    audit = stem.parent / "audit"
    audit.mkdir(exist_ok=True)
    _check_grid_alignment(fig, audit / f"{stem.name}.layout.json")
    audit_dir = os.environ.get("MICA_FIGURE_AUDIT_SCRIPTS")
    if audit_dir:
        source = Path(audit_dir) / "audit_panel_alignment.py"
        spec = importlib.util.spec_from_file_location("mica_nature_alignment", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.require_matplotlib_panel_alignment(
            fig, json_out=audit / f"{stem.name}.alignment.json", tolerance_pt=1.5, strict=True
        )
    options = {"bbox_inches": None if fixed_size else "tight", "dpi": 600}
    fig.savefig(f"{stem}.pdf", **options)
    for extension in ("svg", "png"):
        directory = stem.parent / extension
        directory.mkdir(exist_ok=True)
        fig.savefig(directory / f"{stem.name}.{extension}", **options)
