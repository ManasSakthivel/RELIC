"""
Figure 4: Baseline Comparison Bar Chart.

Compares F1 scores for all baselines vs. the proposed BCG+dynamic system
on the modernization-risk detection task (RQ2).

When experimental results are available (results/rq2/risk_detection.csv),
loads actual values. Otherwise, displays a prominent placeholder annotation.

Scientific integrity: placeholder data is clearly labeled as synthetic.
Results will never be fabricated; placeholder values are purely for layout.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


PLACEHOLDER_ANNOTATION = (
    "RESULTS NOT YET AVAILABLE\n\n"
    "Run experiments before generating this figure.\n"
    "Command: python experiments/rq2/run_rq2.py\n\n"
    "This figure shows placeholder layout only.\n"
    "DO NOT use placeholder values in the paper."
)

BASELINES = [
    ("Baseline A\n(Structural\nDep.)", "#aed6f1"),
    ("Baseline B\n(Complexity\nMetrics)",   "#a9dfbf"),
    ("Baseline C\n(LLM Only)",   "#f9e79f"),
    ("Baseline D\n(Dep.+LLM)",   "#d7bde2"),
    ("Baseline E\n(Static BCG)", "#f5cba7"),
    ("Proposed\n(BCG+Dynamic)", "#fadbd8"),
]

METRICS = ["Precision", "Recall", "F1"]


def _load_results(results: dict | None) -> dict[str, list[float]] | None:
    """
    Load actual experimental results if available.
    Returns dict mapping baseline_name -> [precision, recall, f1], or None.
    """
    if results is None:
        return None
    rq2 = results.get("rq2")
    if not rq2:
        return None

    # Expected CSV columns: baseline,precision,recall,f1
    baseline_data: dict[str, list[float]] = {}
    for row in rq2:
        try:
            name = row["baseline"]
            precision = float(row["precision"])
            recall = float(row["recall"])
            f1 = float(row["f1"])
            baseline_data[name] = [precision, recall, f1]
        except (KeyError, ValueError):
            continue

    return baseline_data if baseline_data else None


def _placeholder_data() -> dict[str, list[float]]:
    """
    Placeholder data — clearly marked as synthetic for layout purposes only.
    These values must NEVER appear in the paper.
    """
    return {
        "Baseline A": [0.50, 0.45, 0.47],
        "Baseline B": [0.52, 0.40, 0.45],
        "Baseline C": [0.63, 0.58, 0.60],
        "Baseline D": [0.68, 0.62, 0.65],
        "Baseline E": [0.71, 0.65, 0.68],
        "Proposed":   [0.80, 0.75, 0.77],
    }


def generate(output_dir: Path, results: dict | None = None) -> None:
    """Generate and save Fig 4: Baseline comparison bar chart."""
    loaded = _load_results(results)
    is_placeholder = loaded is None
    data = loaded if not is_placeholder else _placeholder_data()

    # -----------------------------------------------------------------------
    # Map baseline display names to data keys
    # -----------------------------------------------------------------------
    key_map = {
        "Baseline A\n(Structural\nDep.)": "Baseline A",
        "Baseline B\n(Complexity\nMetrics)":   "Baseline B",
        "Baseline C\n(LLM Only)":   "Baseline C",
        "Baseline D\n(Dep.+LLM)":   "Baseline D",
        "Baseline E\n(Static BCG)": "Baseline E",
        "Proposed\n(BCG+Dynamic)": "Proposed",
    }

    # -----------------------------------------------------------------------
    # Build grouped bar chart
    # -----------------------------------------------------------------------
    n_baselines = len(BASELINES)
    n_metrics = len(METRICS)
    bar_width = 0.22
    group_spacing = 1.0

    x_groups = np.arange(n_baselines) * group_spacing
    metric_offsets = [
        (-bar_width, "#4a90d9"),   # Precision — blue
        (0,          "#5cb85c"),   # Recall — green
        (bar_width,  "#d9534f"),   # F1 — red
    ]

    fig, ax = plt.subplots(1, 1, figsize=(8.5, 4.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    bars_by_metric = []
    for i, (metric, (offset, mcolor)) in enumerate(zip(METRICS, metric_offsets)):
        values = []
        for display_name, bg_color in BASELINES:
            key = key_map[display_name]
            row = data.get(key, [0.0, 0.0, 0.0])
            values.append(row[i])

        bars = ax.bar(
            x_groups + offset,
            values,
            width=bar_width - 0.02,
            color=mcolor,
            alpha=0.75,
            edgecolor="white",
            linewidth=0.5,
            label=metric,
            zorder=3,
        )
        bars_by_metric.append(bars)

    # -----------------------------------------------------------------------
    # Highlight proposed system
    # -----------------------------------------------------------------------
    proposed_x = x_groups[-1]
    ax.axvspan(
        proposed_x - 0.45, proposed_x + 0.45,
        color="#ffe0e0",
        alpha=0.5,
        zorder=1,
        label="_nolegend_",
    )
    ax.axvline(
        proposed_x - 0.45,
        color="#c0392b",
        linewidth=1.0,
        linestyle="--",
        alpha=0.5,
        zorder=2,
    )

    # -----------------------------------------------------------------------
    # Axes formatting
    # -----------------------------------------------------------------------
    ax.set_xticks(x_groups)
    ax.set_xticklabels(
        [name for name, _ in BASELINES],
        fontsize=8.5,
        ha="center",
    )
    ax.set_ylabel("Score (0–1)", fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)

    # Legend
    metric_handles = [
        mpatches.Patch(facecolor="#4a90d9", alpha=0.75, label="Precision"),
        mpatches.Patch(facecolor="#5cb85c", alpha=0.75, label="Recall"),
        mpatches.Patch(facecolor="#d9534f", alpha=0.75, label="F1"),
    ]
    ax.legend(
        handles=metric_handles,
        loc="upper left",
        fontsize=8.5,
        framealpha=0.9,
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # -----------------------------------------------------------------------
    # Placeholder overlay
    # -----------------------------------------------------------------------
    if is_placeholder:
        ax.text(
            0.5, 0.60,
            PLACEHOLDER_ANNOTATION,
            transform=ax.transAxes,
            fontsize=10,
            color="#c0392b",
            alpha=0.75,
            ha="center",
            va="center",
            style="italic",
            fontweight="bold",
            bbox=dict(
                boxstyle="round",
                facecolor="#fdf5e6",
                alpha=0.85,
                edgecolor="#c0392b",
                linewidth=1.5,
            ),
            zorder=10,
        )
        title_suffix = " [PLACEHOLDER — RESULTS NOT AVAILABLE]"
    else:
        title_suffix = ""

    ax.set_title(
        f"Figure 4: Modernization Risk Detection — Baseline Comparison (RQ2){title_suffix}",
        fontsize=9.5,
        fontweight="bold",
        pad=8,
        color="#1a1a2e",
    )

    # Proposed label
    ax.text(
        proposed_x, 0.97,
        "★ Proposed",
        ha="center",
        va="top",
        fontsize=8,
        color="#c0392b",
        fontweight="bold",
        transform=ax.transData,
        zorder=11,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = output_dir / "fig_baseline_comparison.pdf"
    fig.savefig(out_pdf, format="pdf", bbox_inches="tight")
    fig.savefig(output_dir / "fig_baseline_comparison.png", format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"    Saved: {out_pdf} ({'PLACEHOLDER' if is_placeholder else 'with results'})")


if __name__ == "__main__":
    generate(Path("paper/figures"), results=None)
