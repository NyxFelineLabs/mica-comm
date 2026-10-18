"""Run nature-figure source/text/collision audits on a rendered figure bundle.

The source validator is file-local, so inspect the plotting entry point together
with its shared style/export module. The combined file is QA input only.
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nature-scripts", required=True, type=Path)
    parser.add_argument("--source", type=Path, nargs="+")
    parser.add_argument("--figures", type=Path, default=ROOT / "figures")
    args = parser.parse_args()
    audit = args.figures / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    sources = [ROOT / "experiments/figure_style.py"] + (
        args.source or [ROOT / "experiments" / name for name in
                        ("plot.py", "plot_robustness.py", "plot_realistic.py")]
    )
    combined = audit / "source-preflight.py"
    combined.write_text(
        "\n".join(
            p.read_text(encoding="utf-8").replace("from __future__ import annotations", "")
            for p in sources
        ),
        encoding="utf-8",
    )
    commands = [("validate_figure.py", [str(combined)])]
    for pdf in sorted(args.figures.glob("*.pdf")):
        if pdf.stem.endswith(".collision-audit"):
            continue
        commands.extend(
            [
                ("audit_pdf_text.py", [str(pdf), "--min-pt", "5"]),
                (
                    "audit_figure_collisions.py",
                    [
                        str(pdf),
                        "--json-out",
                        str(audit / f"{pdf.stem}.collision-audit.json"),
                        "--overlay-pdf",
                        str(audit / f"{pdf.stem}.collision-audit.pdf"),
                    ],
                ),
            ]
        )
    if len(commands) == 1:
        raise FileNotFoundError("No rendered PDF figures found")
    for script, arguments in commands:
        subprocess.run([sys.executable, str(args.nature_scripts / script), *arguments], check=True)


if __name__ == "__main__":
    main()
