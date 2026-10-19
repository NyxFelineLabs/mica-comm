"""Filesystem locations shared by the simulator and experiment runners.

The source tree is installed in editable mode during development, so deriving
paths from the current working directory is fragile.  These locations are
anchored at the project root and can be redirected for CI or large campaigns
with environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "PROJECT_ROOT",
    "RESULTS_DIR",
    "FIGURES_DIR",
    "CACHE_DIR",
    "ensure_output_dirs",
    "result_path",
    "figure_path",
]


def _path_from_env(name: str, default: Path) -> Path:
    """Return a normalized path from an environment variable or a default."""
    return Path(os.environ.get(name, default)).expanduser().resolve()


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = _path_from_env("MICA_RESULTS_DIR", PROJECT_ROOT / "results")
FIGURES_DIR = _path_from_env("MICA_FIGURES_DIR", PROJECT_ROOT / "figures")
CACHE_DIR = _path_from_env("MICA_CACHE_DIR", RESULTS_DIR / "llm_cache")


def ensure_output_dirs() -> None:
    """Create the standard output directories used by experiments."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def result_path(filename: str) -> Path:
    """Return a path below :data:`RESULTS_DIR` without creating it."""
    return RESULTS_DIR / filename


def figure_path(filename: str) -> Path:
    """Return a path below :data:`FIGURES_DIR` without creating it."""
    return FIGURES_DIR / filename
