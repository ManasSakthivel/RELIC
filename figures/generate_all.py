"""
Figure generation orchestrator.

Run after experiments complete:
    python figures/generate_all.py

Reads from results/ directory, generates PDF figures for the paper.
All figures use matplotlib with publication-quality settings.

Usage:
    python figures/generate_all.py [--results-dir results/] [--output-dir paper/figures/]
    python figures/generate_all.py --dry-run   # generate placeholder figures only

Scientific integrity: figures that require experimental results will generate
placeholder figures annotated "RESULTS NOT YET AVAILABLE" until results exist.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Publication-quality matplotlib configuration
# ---------------------------------------------------------------------------

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for script use
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Publication settings
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "text.usetex": False,  # Set True if LaTeX is available
    "figure.figsize": (6.5, 4.0),
    "lines.linewidth": 1.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
})

RESULTS_PLACEHOLDER_ANNOTATION = (
    "RESULTS NOT YET AVAILABLE\n"
    "Run experiments before generating this figure.\n"
    "See experiments/ directory."
)


def add_placeholder_annotation(ax, message: str = RESULTS_PLACEHOLDER_ANNOTATION) -> None:
    """Overlay a prominent placeholder annotation on an axes object."""
    ax.text(
        0.5, 0.5, message,
        transform=ax.transAxes,
        fontsize=11,
        color="red",
        alpha=0.6,
        ha="center",
        va="center",
        style="italic",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.4),
    )


# ---------------------------------------------------------------------------
# Figure registry
# ---------------------------------------------------------------------------

FIGURES = [
    ("fig_architecture",       "Fig 1: System Architecture",        "figures/fig_architecture.py"),
    ("fig_bcg_formal",         "Fig 2: BCG Formal Model",           "figures/fig_bcg_formal.py"),
    ("fig_reconciliation",     "Fig 3: Reconciliation Flow",        "figures/fig_reconciliation.py"),
    ("fig_baseline_comparison","Fig 4: Baseline Comparison",        "figures/fig_baseline_comparison.py"),
]


def load_results(results_dir: Path) -> dict:
    """
    Load experimental results from results/ directory.
    Returns empty dict if results are not yet available.
    """
    results: dict = {}

    # RQ1 — contract recovery
    rq1_file = results_dir / "rq1" / "contract_recovery.csv"
    if rq1_file.exists():
        import csv
        with open(rq1_file) as f:
            reader = csv.DictReader(f)
            results["rq1"] = list(reader)
    else:
        results["rq1"] = None

    # RQ2 — modernization risk detection
    rq2_file = results_dir / "rq2" / "risk_detection.csv"
    if rq2_file.exists():
        import csv
        with open(rq2_file) as f:
            reader = csv.DictReader(f)
            results["rq2"] = list(reader)
    else:
        results["rq2"] = None

    # RQ3 — static vs dynamic
    rq3_file = results_dir / "rq3" / "static_vs_dynamic.csv"
    if rq3_file.exists():
        import csv
        with open(rq3_file) as f:
            reader = csv.DictReader(f)
            results["rq3"] = list(reader)
    else:
        results["rq3"] = None

    return results


def generate_fig_architecture(output_dir: Path, results: dict) -> None:
    """Generate Fig 1: System architecture diagram."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fig_architecture", Path(__file__).parent / "fig_architecture.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.generate(output_dir)


def generate_fig_bcg_formal(output_dir: Path, results: dict) -> None:
    """Generate Fig 2: BCG formal model diagram."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fig_bcg_formal", Path(__file__).parent / "fig_bcg_formal.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.generate(output_dir)


def generate_fig_reconciliation(output_dir: Path, results: dict) -> None:
    """Generate Fig 3: Reconciliation flow diagram."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fig_reconciliation", Path(__file__).parent / "fig_reconciliation.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.generate(output_dir)


def generate_fig_baseline_comparison(output_dir: Path, results: dict) -> None:
    """Generate Fig 4: Baseline comparison bar chart."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fig_baseline_comparison", Path(__file__).parent / "fig_baseline_comparison.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.generate(output_dir, results)


FIGURE_GENERATORS = {
    "fig_architecture":        generate_fig_architecture,
    "fig_bcg_formal":          generate_fig_bcg_formal,
    "fig_reconciliation":      generate_fig_reconciliation,
    "fig_baseline_comparison": generate_fig_baseline_comparison,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate all LEGACY-CONTRACT paper figures."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Path to results directory (default: results/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("paper/figures"),
        help="Output directory for figures (default: paper/figures/)",
    )
    parser.add_argument(
        "--figure",
        type=str,
        default=None,
        help="Generate only this figure (by name). Omit to generate all.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate placeholder figures only (no results required).",
    )
    parser.add_argument(
        "--format",
        choices=["pdf", "png", "svg"],
        default="pdf",
        help="Output format (default: pdf).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {} if args.dry_run else load_results(args.results_dir)

    available_results = {k: v for k, v in results.items() if v is not None}
    missing_results = {k: v for k, v in results.items() if v is None}

    if missing_results:
        print(
            f"WARNING: Results not yet available for: {list(missing_results.keys())}. "
            f"Figures requiring these results will show placeholder annotations."
        )

    figures_to_generate = (
        [args.figure] if args.figure else list(FIGURE_GENERATORS.keys())
    )

    success = 0
    failure = 0
    for fig_name in figures_to_generate:
        if fig_name not in FIGURE_GENERATORS:
            print(f"ERROR: Unknown figure name: {fig_name!r}")
            failure += 1
            continue
        try:
            print(f"  Generating {fig_name} ...")
            FIGURE_GENERATORS[fig_name](output_dir, results)
            success += 1
            print(f"  ✓ {fig_name} → {output_dir / fig_name}")
        except Exception as e:
            print(f"  ✗ {fig_name} FAILED: {e}")
            failure += 1

    print(f"\nFigure generation complete: {success} succeeded, {failure} failed.")
    return 0 if failure == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
