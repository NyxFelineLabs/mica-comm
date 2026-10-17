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

W1 = 89 / 25.4
W2 = 183 / 25.4

STYLE = {
    "mica": dict(color="#0F4D92", marker="o", label="MICA"),
    "sem": dict(color="#767676", marker="s", label="Periodic semantic"),
    "raw": dict(color="#42949E", marker="^", label="Raw sensor data"),
    "nl": dict(color="#9A4D8E", marker="D", label="Natural language"),
    "report": dict(color="#B64342", marker="v", label="Report only"),
    "mica_novoi": dict(color="#42949E", marker="P", label="MICA w/o VoI"),
    "mica_tv": dict(color="#9A4D8E", marker="X", label="MICA, belief-div. VoI"),
    "genie": dict(color="#B64342", marker="^", label="Ideal reference", linestyle="--"),
}

RCPARAMS = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
    "font.size": 7,
    "axes.titlesize": 8,
    "axes.labelsize": 7,
    "legend.fontsize": 6.5,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "axes.edgecolor": "#4D4D4D",
    "axes.grid": False,
    "legend.frameon": False,
    "lines.linewidth": 1.2,
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
    _check_grid_alignment(fig, Path(f"{stem}.layout.json"))
    audit_dir = os.environ.get("MICA_FIGURE_AUDIT_SCRIPTS")
    if audit_dir:
        source = Path(audit_dir) / "audit_panel_alignment.py"
        spec = importlib.util.spec_from_file_location("mica_nature_alignment", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.require_matplotlib_panel_alignment(
            fig, json_out=f"{stem}.alignment.json", tolerance_pt=1.5, strict=True
        )
    options = {"bbox_inches": None if fixed_size else "tight", "dpi": 600}
    fig.savefig(f"{stem}.pdf", **options)
    fig.savefig(f"{stem}.svg", **options)
    fig.savefig(f"{stem}.png", **options)
