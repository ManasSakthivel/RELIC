"""
Figure 2: BCG Formal Model Diagram.

Illustrates the six components of BCG = (V, E, C, P, D, Γ):
- V: entity set (typed nodes)
- E: structural relations (typed edges)
- C: behavioral contracts (with predicate and natural language)
- P: provenance records (evidence chains)
- D: dynamic observations (execution events)
- Γ: validation metadata (confidence + validation state)

This is a conceptual (non-empirical) figure and can be generated at any time.
Uses a small concrete example from CardDemo to illustrate the model.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D


COLORS = {
    "V": "#aed6f1",   # Blue — entities
    "E": "#a9dfbf",   # Green — relations
    "C": "#f9e79f",   # Yellow — contracts
    "P": "#d7bde2",   # Purple — provenance
    "D": "#f5cba7",   # Orange — dynamic
    "Gamma": "#fadbd8",  # Pink — validation metadata
    "border": "#2c3e50",
    "text": "#1a1a2e",
    "edge": "#5d6d7e",
    "contract_edge": "#c0392b",
}


def box(ax, x, y, w, h, label, sublabel="", color="#aed6f1", fs=8.5, bold=False):
    patch = mpatches.FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.03",
        facecolor=color,
        edgecolor=COLORS["border"],
        linewidth=0.9,
        zorder=3,
    )
    ax.add_patch(patch)
    ax.text(
        x, y + (0.04 if sublabel else 0),
        label,
        ha="center", va="center",
        fontsize=fs,
        fontweight="bold" if bold else "normal",
        color=COLORS["text"],
        zorder=4,
    )
    if sublabel:
        ax.text(
            x, y - 0.09,
            sublabel,
            ha="center", va="center",
            fontsize=7,
            color="#626567",
            style="italic",
            zorder=4,
        )


def arrow(ax, x1, y1, x2, y2, color="#5d6d7e", label="", ls="-"):
    ax.annotate(
        "",
        xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=1.1,
            linestyle=ls,
            mutation_scale=10,
        ),
        zorder=5,
    )
    if label:
        mx, my = (x1 + x2) / 2 + 0.03, (y1 + y2) / 2
        ax.text(mx, my, label, fontsize=7, color=color, ha="left", va="center")


def generate(output_dir: Path) -> None:
    """Generate and save Fig 2: BCG formal model."""
    fig, ax = plt.subplots(1, 1, figsize=(8.5, 5.5))
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 6)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # -----------------------------------------------------------------------
    # Section labels for the six BCG components
    # -----------------------------------------------------------------------
    label_kw = dict(fontsize=9, fontweight="bold", va="center")

    # -----------------------------------------------------------------------
    # V — Entity nodes (left column, y center ~4.5)
    # -----------------------------------------------------------------------
    ax.text(0.1, 5.5, "V (Entities)", color=COLORS["V"], **label_kw)
    box(ax, 1.3, 5.1, 1.5, 0.45, "JOB: RC3JOB",    "type=JOB",    COLORS["V"])
    box(ax, 1.3, 4.5, 1.5, 0.45, "STEP: STEP01",   "type=STEP",   COLORS["V"])
    box(ax, 1.3, 3.9, 1.5, 0.45, "STEP: STEP02",   "type=STEP",   COLORS["V"])
    box(ax, 1.3, 3.3, 1.5, 0.45, "DS: SYNTH.FILE", "type=DATASET",COLORS["V"])

    # -----------------------------------------------------------------------
    # E — Structural relations (connecting entities)
    # -----------------------------------------------------------------------
    ax.text(0.1, 2.9, "E (Relations)", color=COLORS["E"], **label_kw)
    # CONTAINS: JOB → STEP01
    arrow(ax, 1.3, 4.85, 1.3, 4.725, color=COLORS["E"])
    ax.text(1.45, 4.79, "CONTAINS", fontsize=6.5, color=COLORS["E"])
    # CONTAINS: JOB → STEP02
    ax.annotate("", xy=(1.3, 4.15), xytext=(1.3, 4.85),
                arrowprops=dict(arrowstyle="-|>", color=COLORS["E"], lw=1.0, mutation_scale=9),
                zorder=5)
    ax.text(1.45, 4.50, "CONTAINS", fontsize=6.5, color=COLORS["E"])
    # MUST_PRECEDE: STEP01 → STEP02
    arrow(ax, 1.3, 4.28, 1.3, 4.15, color=COLORS["E"])
    ax.text(1.45, 4.21, "MUST_PRECEDE", fontsize=6.5, color=COLORS["E"])
    # PRODUCES: STEP01 → DATASET
    arrow(ax, 1.3, 3.68, 1.3, 3.52, color=COLORS["E"])
    ax.text(1.45, 3.60, "PRODUCES", fontsize=6.5, color=COLORS["E"])
    # CONSUMES: STEP02 → DATASET (curved)
    ax.annotate("", xy=(1.05, 3.52), xytext=(1.05, 4.15),
                arrowprops=dict(arrowstyle="-|>", color=COLORS["E"], lw=1.0,
                                connectionstyle="arc3,rad=0.4", mutation_scale=9),
                zorder=5)
    ax.text(0.15, 3.83, "CONSUMES", fontsize=6.5, color=COLORS["E"])

    # -----------------------------------------------------------------------
    # C — Behavioral contracts (center)
    # -----------------------------------------------------------------------
    ax.text(3.2, 5.6, "C (Contracts)", color="#8b7d00", **label_kw)

    # Contract C1: TEMPORAL
    box(ax, 4.3, 5.1, 2.9, 0.55,
        "C1: TEMPORAL",
        "STEP01 ≺ STEP02 (PRECEDES)",
        COLORS["C"], fs=8)

    # Contract C2: RESOURCE
    box(ax, 4.3, 4.3, 2.9, 0.55,
        "C2: RESOURCE",
        "produces(STEP01,DS) ≺ consumes(STEP02,DS)",
        COLORS["C"], fs=8)

    # Contract C3: CONTROL-FLOW
    box(ax, 4.3, 3.5, 2.9, 0.55,
        "C3: CONTROL_FLOW",
        "RC(STEP01) GT 4 → ¬execute(STEP02)",
        COLORS["C"], fs=8)

    # Arrows: entity nodes → contracts
    arrow(ax, 2.05, 4.5, 2.85, 5.1, color=COLORS["contract_edge"], ls="--")
    arrow(ax, 2.05, 3.9, 2.85, 4.3, color=COLORS["contract_edge"], ls="--")
    arrow(ax, 2.05, 4.5, 2.85, 3.5, color=COLORS["contract_edge"], ls="--")

    # -----------------------------------------------------------------------
    # P — Provenance (bottom left)
    # -----------------------------------------------------------------------
    ax.text(0.1, 2.6, "P (Provenance)", color="#5b2c6f", **label_kw)
    box(ax, 1.7, 2.0, 3.0, 0.8,
        "ProvenanceRecord for C1",
        "source=synth.jcl:3 | method=DETERMINISTIC\n"
        "static_evidence: [JCL sequential order, MUST_PRECEDE]\n"
        "dynamic_evidence: [] (pre-reconciliation)",
        COLORS["P"], fs=7.5)

    arrow(ax, 4.3, 4.82, 2.5, 2.4, color="#7d3c98", ls="--")

    # -----------------------------------------------------------------------
    # D — Dynamic observations (bottom center)
    # -----------------------------------------------------------------------
    ax.text(3.8, 2.6, "D (Dynamic Observations)", color="#935116", **label_kw)
    box(ax, 5.1, 2.0, 3.0, 0.8,
        "ExecutionEvent E1",
        "artifact=STEP01 | op=STEP_START | t=08:00:10\n"
        "source_type=SYNTHETIC_STATIC | rc=None",
        COLORS["D"], fs=7.5)

    arrow(ax, 4.3, 4.82, 5.0, 2.4, color="#a04000", ls="--")

    # -----------------------------------------------------------------------
    # Γ — Validation metadata (bottom right)
    # -----------------------------------------------------------------------
    ax.text(6.7, 2.6, "Γ (Validation Metadata)", color="#943126", **label_kw)
    box(ax, 7.7, 2.0, 2.2, 0.8,
        "C1 Validation",
        "state=STATIC_CANDIDATE\n"
        "static_support=1.0 | dynamic=0.0\n"
        "aggregate=0.35",
        COLORS["Gamma"], fs=7.5)

    arrow(ax, 4.3 + 1.45, 4.82, 7.2, 2.4, color="#943126", ls="--")

    # -----------------------------------------------------------------------
    # Formal definition box
    # -----------------------------------------------------------------------
    definition_box = mpatches.FancyBboxPatch(
        (0.08, 0.08), 8.84, 0.70,
        boxstyle="round,pad=0.04",
        facecolor="#f8f9fa",
        edgecolor="#dee2e6",
        linewidth=0.8,
        zorder=2,
    )
    ax.add_patch(definition_box)
    ax.text(
        4.5, 0.43,
        "BCG = (V, E, C, P, D, Γ)   where   "
        "V=entities   E=relations   C=contracts   P=provenance   D=dynamic observations   Γ=validation metadata",
        ha="center", va="center",
        fontsize=8,
        fontfamily="monospace",
        color="#2c3e50",
        zorder=3,
    )

    # -----------------------------------------------------------------------
    # Legend
    # -----------------------------------------------------------------------
    legend_handles = [
        mpatches.Patch(facecolor=COLORS["V"],     edgecolor=COLORS["border"], label="V: Entities"),
        mpatches.Patch(facecolor=COLORS["E"],     edgecolor=COLORS["border"], label="E: Relations"),
        mpatches.Patch(facecolor=COLORS["C"],     edgecolor=COLORS["border"], label="C: Contracts"),
        mpatches.Patch(facecolor=COLORS["P"],     edgecolor=COLORS["border"], label="P: Provenance"),
        mpatches.Patch(facecolor=COLORS["D"],     edgecolor=COLORS["border"], label="D: Dynamic Obs."),
        mpatches.Patch(facecolor=COLORS["Gamma"], edgecolor=COLORS["border"], label="Γ: Validation"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper right",
        fontsize=7.5,
        framealpha=0.9,
        ncol=3,
        bbox_to_anchor=(8.95, 6.05),
    )

    ax.set_title(
        "Figure 2: BCG = (V, E, C, P, D, Γ) — Concrete Example from CardDemo",
        fontsize=10.5,
        fontweight="bold",
        pad=6,
        color=COLORS["text"],
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = output_dir / "fig_bcg_formal.pdf"
    fig.savefig(out_pdf, format="pdf", bbox_inches="tight")
    fig.savefig(output_dir / "fig_bcg_formal.png", format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"    Saved: {out_pdf}")


if __name__ == "__main__":
    generate(Path("paper/figures"))
