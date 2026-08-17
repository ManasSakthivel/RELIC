"""
Figure 1: System Architecture Diagram.

Generates a clean box-and-arrow diagram of the RELIC pipeline:
Artifacts → Parsers → IR → Static Extraction → BCG → Reconciliation → Risk Detection

This is a structural (non-empirical) figure and can be generated at any time.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch


# ---------------------------------------------------------------------------
# Color palette (grayscale-friendly for print)
# ---------------------------------------------------------------------------

COLORS = {
    "input":       "#d4e6f1",   # Light blue — input artifacts
    "parser":      "#d5f5e3",   # Light green — parsers
    "ir":          "#fdebd0",   # Light orange — IR layer
    "analysis":    "#e8daef",   # Light purple — analysis
    "bcg":         "#fdedec",   # Light red — BCG
    "output":      "#fdfefe",   # White — outputs
    "arrow":       "#5d6d7e",   # Dark gray — arrows
    "border":      "#2c3e50",   # Dark — borders
    "text":        "#1a1a2e",   # Near-black — text
    "highlight":   "#c0392b",   # Red — key component
}


def make_box(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    sublabel: str = "",
    color: str = "#d4e6f1",
    fontsize: int = 9,
    bold: bool = False,
) -> None:
    """Draw a rounded rectangle with text label."""
    box = mpatches.FancyBboxPatch(
        (x - width / 2, y - height / 2),
        width,
        height,
        boxstyle="round,pad=0.02",
        facecolor=color,
        edgecolor=COLORS["border"],
        linewidth=0.8,
        zorder=2,
    )
    ax.add_patch(box)
    weight = "bold" if bold else "normal"
    ax.text(
        x, y + (0.03 if sublabel else 0),
        label,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=weight,
        color=COLORS["text"],
        zorder=3,
    )
    if sublabel:
        ax.text(
            x, y - 0.07,
            sublabel,
            ha="center",
            va="center",
            fontsize=7,
            color="#7f8c8d",
            style="italic",
            zorder=3,
        )


def make_arrow(
    ax: plt.Axes,
    x1: float, y1: float,
    x2: float, y2: float,
    label: str = "",
) -> None:
    """Draw an arrow between two points."""
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="-|>",
            color=COLORS["arrow"],
            lw=1.2,
            mutation_scale=12,
        ),
        zorder=4,
    )
    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        ax.text(
            mx + 0.02, my,
            label,
            fontsize=7,
            color=COLORS["arrow"],
            ha="left",
            va="center",
        )


def generate(output_dir: Path) -> None:
    """Generate and save Fig 1: System Architecture."""
    fig, ax = plt.subplots(1, 1, figsize=(7.5, 5.0))
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 6)
    ax.axis("off")

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # -----------------------------------------------------------------------
    # Row 1: Input artifacts (y = 5.2)
    # -----------------------------------------------------------------------
    y_input = 5.2
    make_box(ax, 1.2, y_input, 1.4, 0.45, "JCL Files", ".jcl artifacts", COLORS["input"])
    make_box(ax, 2.9, y_input, 1.4, 0.45, "COBOL Programs", ".cbl artifacts", COLORS["input"])
    make_box(ax, 4.6, y_input, 1.4, 0.45, "Copybooks", ".cpy artifacts", COLORS["input"])
    make_box(ax, 6.5, y_input, 1.6, 0.45, "Execution Traces", "GnuCOBOL / simulated", COLORS["input"])

    # -----------------------------------------------------------------------
    # Row 2: Parsers (y = 4.2)
    # -----------------------------------------------------------------------
    y_parser = 4.2
    make_box(ax, 1.2, y_parser, 1.4, 0.45, "JCL Parser", "", COLORS["parser"])
    make_box(ax, 2.9, y_parser, 1.4, 0.45, "COBOL Parser", "", COLORS["parser"])
    make_box(ax, 4.6, y_parser, 1.4, 0.45, "Copybook Parser", "", COLORS["parser"])
    make_box(ax, 6.5, y_parser, 1.6, 0.45, "Dynamic Evidence\nAdapter", "", COLORS["parser"])

    # Arrows input → parsers
    for x in [1.2, 2.9, 4.6, 6.5]:
        make_arrow(ax, x, y_input - 0.225, x, y_parser + 0.225)

    # -----------------------------------------------------------------------
    # Row 3: IR Graph (y = 3.2)
    # -----------------------------------------------------------------------
    y_ir = 3.2
    make_box(ax, 3.4, y_ir, 3.6, 0.55, "Intermediate Representation (IR)",
             "IRGraph: entities + relations (deterministic, stable IDs)", COLORS["ir"])
    make_box(ax, 6.5, y_ir, 1.6, 0.55, "ExecutionEvent\nStream",
             "Normalized events\n(source_type labeled)", COLORS["ir"])

    # Arrows parsers → IR
    for x in [1.2, 2.9, 4.6]:
        make_arrow(ax, x, y_parser - 0.225, 3.4, y_ir + 0.275)
    # Adapter → event stream
    make_arrow(ax, 6.5, y_parser - 0.225, 6.5, y_ir + 0.275)

    # -----------------------------------------------------------------------
    # Row 4: Static extraction and BCG builder (y = 2.2)
    # -----------------------------------------------------------------------
    y_extract = 2.2
    make_box(ax, 2.2, y_extract, 2.8, 0.55, "Static Contract Extractor",
             "Temporal | Resource | Control-flow", COLORS["analysis"])
    make_box(ax, 5.5, y_extract, 2.2, 0.55, "BCG Builder",
             "Adds V, E, C, P from IR + contracts", COLORS["analysis"])

    make_arrow(ax, 3.4, y_ir - 0.275, 2.2, y_extract + 0.275)
    make_arrow(ax, 3.4, y_ir - 0.275, 5.5, y_extract + 0.275)

    # -----------------------------------------------------------------------
    # Row 5: BCG (center, y = 1.3)
    # -----------------------------------------------------------------------
    y_bcg = 1.3
    make_box(ax, 4.0, y_bcg, 4.2, 0.6, "Behavioral Contract Graph (BCG)",
             "BCG = (V, E, C, P, D, Γ)  |  provenance + confidence + validation states",
             COLORS["bcg"], bold=True)

    make_arrow(ax, 2.2, y_extract - 0.275, 4.0, y_bcg + 0.3)
    make_arrow(ax, 5.5, y_extract - 0.275, 4.0, y_bcg + 0.3)
    # Dynamic events → BCG
    make_arrow(ax, 6.5, y_ir - 0.275, 6.1, y_bcg + 0.3)

    # -----------------------------------------------------------------------
    # Row 6: Reconciliation + outputs (y = 0.4)
    # -----------------------------------------------------------------------
    y_out = 0.45
    make_box(ax, 1.5, y_out, 1.8, 0.5, "Reconciliation\nEngine",
             "static/dynamic\nevidence merge", COLORS["analysis"])
    make_box(ax, 3.5, y_out, 1.8, 0.5, "Mutation\nEngine",
             "fault-grounded\noperators", COLORS["analysis"])
    make_box(ax, 5.5, y_out, 1.8, 0.5, "Risk Detector",
             "contract violation\n+ explanation", COLORS["output"])
    make_box(ax, 7.3, y_out, 1.2, 0.5, "UI / API",
             "", COLORS["output"])

    make_arrow(ax, 4.0, y_bcg - 0.3, 1.5, y_out + 0.25)
    make_arrow(ax, 4.0, y_bcg - 0.3, 3.5, y_out + 0.25)
    make_arrow(ax, 4.0, y_bcg - 0.3, 5.5, y_out + 0.25)
    make_arrow(ax, 5.5, y_out, 7.3 - 0.6, y_out)

    # -----------------------------------------------------------------------
    # Title and legend
    # -----------------------------------------------------------------------
    ax.set_title(
        "Figure 1: RELIC System Architecture",
        fontsize=11,
        fontweight="bold",
        pad=8,
        color=COLORS["text"],
    )

    legend_handles = [
        mpatches.Patch(facecolor=COLORS["input"],    label="Artifacts"),
        mpatches.Patch(facecolor=COLORS["parser"],   label="Parsers"),
        mpatches.Patch(facecolor=COLORS["ir"],       label="IR / Events"),
        mpatches.Patch(facecolor=COLORS["analysis"], label="Analysis"),
        mpatches.Patch(facecolor=COLORS["bcg"],      label="BCG (core)"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="lower left",
        fontsize=7,
        framealpha=0.8,
        ncol=5,
        bbox_to_anchor=(0, -0.02),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "fig_architecture.pdf"
    fig.savefig(out_path, format="pdf", bbox_inches="tight")
    # Also save PNG for quick preview
    fig.savefig(output_dir / "fig_architecture.png", format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"    Saved: {out_path}")


if __name__ == "__main__":
    generate(Path("paper/figures"))
