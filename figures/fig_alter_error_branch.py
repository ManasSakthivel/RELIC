"""
Figure 5: ALTER_ERROR_BRANCH Case Study.

Illustrates the discriminating architectural finding:
BCGDiff confidence-delta detection catches ALTER_ERROR_BRANCH mutations
that are invisible to both structural analysis and static-BCG-only (Baseline E).

This is a conceptual figure showing the mutation flow:
  Original JCL → BCG contract → Mutation → Modified JCL → BCGDiff → Risk Classification

Uses actual operator data from rq2_summary.json:
  ALTER_ERROR_BRANCH: proposed F1=1.00, Baseline E F1=0.00, Baseline A F1=0.00
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

COLORS = {
    "original":  "#d4e6f1",  # Blue — original state
    "mutated":   "#fadbd8",  # Red — mutated state
    "contract":  "#f9e79f",  # Yellow — contract
    "bcgdiff":   "#d5f5e3",  # Green — BCGDiff output
    "missed":    "#fdebd0",  # Orange — missed by baseline
    "detected":  "#d5f5e3",  # Green — detected by proposed
    "border":    "#2c3e50",
    "text":      "#1a1a2e",
}


def box(ax, x, y, w, h, lines, color="#d4e6f1", fs=8.5, bold=False, border_color=None):
    patch = mpatches.FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.04",
        facecolor=color,
        edgecolor=border_color or COLORS["border"],
        linewidth=0.9,
        zorder=3,
    )
    ax.add_patch(patch)
    if isinstance(lines, str):
        lines = [lines]
    step = h / (len(lines) + 1)
    for i, line in enumerate(lines, 1):
        ax.text(
            x, y + h / 2 - step * i,
            line,
            ha="center", va="center",
            fontsize=fs,
            fontweight="bold" if (bold and i == 1) else "normal",
            color=COLORS["text"],
            zorder=4,
        )


def arr(ax, x1, y1, x2, y2, label="", color="#5d6d7e"):
    ax.annotate(
        "",
        xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=1.3,
            mutation_scale=10,
        ),
        zorder=5,
    )
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx + 0.05, my, label, fontsize=7, color=color, va="center", ha="left")


def generate(output_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    fig.patch.set_facecolor("white")

    # ─────────────────────────────────────────────────────────────────
    # Left panel: The mutation flow
    # ─────────────────────────────────────────────────────────────────
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.5, 8.5)
    ax.axis("off")
    ax.set_facecolor("white")

    # Step 1: Original JCL snippet
    box(ax, 2.0, 7.5, 3.5, 1.2, [
        "Original JCL (STEP04)",
        "//STEP04 EXEC PGM=CBACT04C",
        "//        COND=(4,GT,STEP03)",
        "→ IF RC(STEP03) > 4: skip STEP04",
    ], COLORS["original"], fs=7.5, bold=True)

    # Step 2: Extracted BCG contract
    box(ax, 2.0, 5.4, 3.5, 1.4, [
        "BCG Contract (extracted)",
        "type: CONTROL_FLOW",
        "subject: STEP03",
        "pred: MUST_NOT_FOLLOW_ON_ERROR",
        "obj: STEP04  |  rc_threshold=4, op=GT",
        "state: STATIC_CANDIDATE",
        "confidence: static_support=1.0",
    ], COLORS["contract"], fs=7, bold=True)
    arr(ax, 2.0, 6.9, 2.0, 6.1, "BCG extraction")

    # Step 3: Mutation applied
    box(ax, 2.0, 3.4, 3.5, 1.2, [
        "After ALTER_ERROR_BRANCH Mutation",
        "//STEP04 EXEC PGM=CBACT04C",
        "//        COND=(8,GT,STEP03)  ← changed",
        "→ Only skip if RC(STEP03) > 8 (weaker!)",
    ], COLORS["mutated"], fs=7.5, bold=True, border_color="#c0392b")
    arr(ax, 2.0, 4.7, 2.0, 4.0, "ALTER_ERROR_BRANCH", color="#c0392b")

    # Step 4: BCGDiff result
    box(ax, 2.0, 1.5, 3.5, 1.3, [
        "BCGDiff Output",
        "contract state: STATIC_CANDIDATE",
        "diff.modified: True",
        "confidence: static_support=0.70 (−0.30)",
        "delta > 5% threshold → MODIFIED risk",
    ], COLORS["bcgdiff"], fs=7, bold=True)
    arr(ax, 2.0, 2.8, 2.0, 2.15, "BCGDiff")

    # Right side: detection result comparison
    box(ax, 7.5, 7.5, 3.5, 1.0, [
        "Baseline A (Structural)",
        "Structural edges UNCHANGED",
        "Same EXEC PGM=, same DD, same step order",
        "→ FN: mutation INVISIBLE  (F1=0.00)",
    ], COLORS["missed"], fs=7.5, bold=True, border_color="#e67e22")

    box(ax, 7.5, 5.5, 3.5, 1.0, [
        "Baseline E (static BCG, broken-only)",
        "diff.broken: empty (contract still exists!)",
        "Only checks for contract removal",
        "→ FN: mutation INVISIBLE  (F1=0.00)",
    ], COLORS["missed"], fs=7.5, bold=True, border_color="#e67e22")

    box(ax, 7.5, 3.4, 3.5, 1.2, [
        "Proposed: BCG + confidence-delta",
        "diff.modified: [STEP04 contract]",
        "delta static_support = −0.30 > 5% threshold",
        "→ MODIFIED contract detected",
        "→ TP: mutation DETECTED  (F1=1.00)",
    ], COLORS["detected"], fs=7.5, bold=True, border_color="#27ae60")

    # Arrows from BCGDiff to detectors
    arr(ax, 3.75, 1.5, 5.75, 7.5, "", color="#aaa")
    arr(ax, 3.75, 1.5, 5.75, 5.5, "", color="#aaa")
    arr(ax, 3.75, 1.5, 5.75, 3.4, "", color="#27ae60")

    ax.set_title("Fig 5a: ALTER_ERROR_BRANCH — Mutation Flow and Detection", fontsize=10, fontweight="bold", pad=8)

    # ─────────────────────────────────────────────────────────────────
    # Right panel: F1 bar chart for ALTER_ERROR_BRANCH operator
    # ─────────────────────────────────────────────────────────────────
    ax2 = axes[1]

    baselines = ["Baseline A\n(Structural)", "Baseline B\n(Complexity)", "Baseline E\n(BCG\nbroken-only)", "Proposed\n(BCG +\nconfidence-delta)"]
    f1_scores = [0.00, 0.00, 0.00, 1.00]
    colors_bar = ["#f5b041", "#e74c3c", "#e67e22", "#27ae60"]

    bars = ax2.bar(baselines, f1_scores, color=colors_bar, edgecolor="white", linewidth=0.8, zorder=3)
    ax2.set_ylim(0, 1.15)
    ax2.set_ylabel("F1 Score", fontsize=10)
    ax2.set_yticks([0, 0.25, 0.50, 0.75, 1.00])
    ax2.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax2.set_facecolor("white")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    # Value labels on bars
    for bar, val in zip(bars, f1_scores):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{val:.2f}",
            ha="center", va="bottom",
            fontsize=10, fontweight="bold",
            color="#2c3e50",
        )

    # Add note about the discriminating result
    ax2.text(0.5, 1.10,
             "Source: rq2_summary.json → by_operator → ALTER_ERROR_BRANCH\n"
             "n=8 mutations | All conditions use same benchmark",
             ha="center", va="top",
             transform=ax2.transAxes,
             fontsize=7.5,
             color="#7f8c8d",
             style="italic")

    ax2.set_title("Fig 5b: ALTER_ERROR_BRANCH — F1 by Detection Condition\n(n=8 mutations)", fontsize=10, fontweight="bold", pad=8)

    plt.tight_layout(pad=1.5)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = output_dir / "fig_alter_error_branch.pdf"
    fig.savefig(out_pdf, format="pdf", bbox_inches="tight")
    fig.savefig(output_dir / "fig_alter_error_branch.png", format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"    Saved: {out_pdf} (with actual ALTER_ERROR_BRANCH data)")


if __name__ == "__main__":
    generate(Path("paper/figures"))
