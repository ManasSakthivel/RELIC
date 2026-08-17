"""
Figure 3: Static/Dynamic Reconciliation Flow Diagram.

Illustrates the reconciliation algorithm:
  Static candidate → find events → evaluate predicate → outcome → state update

Shows the five reconciliation outcomes and the four conflict classes.
Emphasizes the NOT_OBSERVED ≠ CONTRADICTED scientific principle.

This is a conceptual (non-empirical) figure and can be generated at any time.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


COLORS = {
    "static":     "#aed6f1",   # Blue — static evidence
    "dynamic":    "#a9dfbf",   # Green — dynamic evidence
    "decision":   "#f9e79f",   # Yellow — decision point
    "supported":  "#d5f5e3",   # Green — SUPPORTED outcome
    "conflict":   "#fadbd8",   # Red — CONTRADICTED outcome
    "not_obs":    "#fdebd0",   # Orange — NOT_OBSERVED outcome
    "partial":    "#e8daef",   # Purple — PARTIALLY_SUPPORTED
    "update":     "#d4e6f1",   # Light blue — state update
    "border":     "#2c3e50",
    "text":       "#1a1a2e",
    "arrow":      "#5d6d7e",
}


def box(ax, x, y, w, h, label, sublabel="", color="#aed6f1", fs=8.5, bold=False):
    patch = mpatches.FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.04",
        facecolor=color,
        edgecolor=COLORS["border"],
        linewidth=0.8,
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
        wrap=True,
    )
    if sublabel:
        ax.text(
            x, y - 0.10,
            sublabel,
            ha="center", va="center",
            fontsize=6.5,
            color="#7f8c8d",
            style="italic",
            zorder=4,
        )


def arr(ax, x1, y1, x2, y2, label="", color="#5d6d7e", ls="-"):
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
    """Generate and save Fig 3: Reconciliation flow."""
    fig, ax = plt.subplots(1, 1, figsize=(9.0, 6.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.5, 7.5)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # -----------------------------------------------------------------------
    # Step 1: Static candidate contract (top center)
    # -----------------------------------------------------------------------
    y_start = 7.0
    box(ax, 5.0, y_start, 4.5, 0.55,
        "Static Candidate Contract c",
        "type=TEMPORAL | predicate=PRECEDES | state=STATIC_CANDIDATE",
        COLORS["static"], fs=8.5, bold=True)

    # -----------------------------------------------------------------------
    # Step 2: Retrieve dynamic events
    # -----------------------------------------------------------------------
    y_retrieve = 6.0
    box(ax, 3.0, y_retrieve, 3.5, 0.55,
        "E_subject = events(c.subject_id)",
        "artifact events from trace D",
        COLORS["dynamic"], fs=8)
    box(ax, 7.0, y_retrieve, 3.5, 0.55,
        "E_object = events(c.object_id)",
        "artifact events from trace D",
        COLORS["dynamic"], fs=8)

    arr(ax, 5.0, y_start - 0.275, 3.0, y_retrieve + 0.275)
    arr(ax, 5.0, y_start - 0.275, 7.0, y_retrieve + 0.275)

    # -----------------------------------------------------------------------
    # Step 3: Decision — any events?
    # -----------------------------------------------------------------------
    y_decision1 = 5.0
    box(ax, 5.0, y_decision1, 3.0, 0.55,
        "E_subject = ∅ ∧ E_object = ∅ ?",
        "(no events for either artifact)",
        COLORS["decision"], fs=8.5)
    arr(ax, 3.0, y_retrieve - 0.275, 5.0, y_decision1 + 0.275)
    arr(ax, 7.0, y_retrieve - 0.275, 5.0, y_decision1 + 0.275)

    # YES branch → NOT_OBSERVED
    y_not_obs = 5.0
    box(ax, 1.3, y_not_obs, 1.8, 0.65,
        "NOT_OBSERVED",
        "state ← NOT_OBSERVED\nNOT ← CONTRADICTED",
        COLORS["not_obs"], fs=8, bold=True)
    arr(ax, 3.5, y_decision1, 2.2, y_not_obs, label="YES")

    # Emphasis annotation
    ax.text(1.3, y_not_obs - 0.45,
            "★ NOT_OBSERVED ≠ CONTRADICTED",
            ha="center", va="center",
            fontsize=7.5,
            color="#c0392b",
            fontweight="bold",
            style="italic")

    # -----------------------------------------------------------------------
    # Step 4: Predicate evaluation (NO branch)
    # -----------------------------------------------------------------------
    y_eval = 3.9
    box(ax, 5.0, y_eval, 3.0, 0.55,
        "Apply predicate semantics",
        "PRECEDES | PRODUCES_BEFORE | MUST_NOT_FOLLOW",
        COLORS["decision"], fs=8)
    arr(ax, 5.0, y_decision1 - 0.275, 5.0, y_eval + 0.275, label="NO")

    # -----------------------------------------------------------------------
    # Step 5: Outcomes (fan out)
    # -----------------------------------------------------------------------
    y_outcomes = 2.7

    outcomes = [
        (1.2,  "SUPPORTED",         "Dynamic obs. consistent\nwith predicate",           COLORS["supported"]),
        (3.2,  "PARTIALLY\nSUPPORTED", "Some events support;\ncoverage incomplete",       COLORS["partial"]),
        (5.0,  "AMBIGUOUS",         "Insufficient evidence\nto classify",                 COLORS["not_obs"]),
        (6.8,  "NOT_OBSERVED",      "No relevant events\nfound for predicate",           COLORS["not_obs"]),
        (8.8,  "CONTRADICTED",      "Observation directly\nviolates predicate",           COLORS["conflict"]),
    ]

    for x_out, label, sublabel, color in outcomes:
        box(ax, x_out, y_outcomes, 1.75, 0.65, label, sublabel, color, fs=7.5, bold=True)
        arr(ax, 5.0, y_eval - 0.275, x_out, y_outcomes + 0.325)

    # -----------------------------------------------------------------------
    # Step 6: State updates (bottom)
    # -----------------------------------------------------------------------
    y_update = 1.5
    state_updates = [
        (1.2,  "STATIC_DYNAMIC\nSUPPORTED",  COLORS["supported"]),
        (3.2,  "UNRESOLVED",                 COLORS["partial"]),
        (5.0,  "UNRESOLVED",                 COLORS["not_obs"]),
        (6.8,  "NOT_OBSERVED",               COLORS["not_obs"]),
        (8.8,  "STATIC_DYNAMIC\nCONFLICT",   COLORS["conflict"]),
    ]
    for (x_out, *_rest), (x_upd, state, color) in zip(outcomes, state_updates):
        box(ax, x_upd, y_update, 1.75, 0.5, state, "", color, fs=7.5)
        arr(ax, x_out, y_outcomes - 0.325, x_upd, y_update + 0.25)

    # -----------------------------------------------------------------------
    # Step 7: Confidence update
    # -----------------------------------------------------------------------
    y_conf = 0.6
    box(ax, 5.0, y_conf, 8.5, 0.5,
        "Update confidence: c.confidence.dynamic_support ← record.dynamic_support_score   |   "
        "Add dynamic evidence to c.provenance",
        "", COLORS["update"], fs=7.5)
    for _, x_upd, _, _ in [(None, x, None, None) for x, _, _ in state_updates]:
        arr(ax, x_upd, y_update - 0.25, 5.0, y_conf + 0.25)

    # Fix: draw arrows from state updates to confidence box
    for x_upd, _, _ in state_updates:
        arr(ax, x_upd, y_update - 0.25, 5.0, y_conf + 0.25)

    # -----------------------------------------------------------------------
    # Title and annotations
    # -----------------------------------------------------------------------
    ax.set_title(
        "Figure 3: Static/Dynamic Reconciliation Algorithm",
        fontsize=11,
        fontweight="bold",
        pad=6,
        color=COLORS["text"],
    )

    # Conflict class annotation
    conflict_text = (
        "Conflict Classes:\n"
        "  STATIC_FALSE_POSITIVE — static infer. incorrect\n"
        "  DYNAMIC_INCOMPLETE — path not covered\n"
        "  HIDDEN_STATE — env. dependency\n"
        "  INSTRUMENTATION_LIMIT — trace missed event\n"
        "  PARSER_LIMIT — parser missed element"
    )
    ax.text(
        9.9, 3.9, conflict_text,
        ha="right", va="center",
        fontsize=6.5,
        color="#5d6d7e",
        style="italic",
        bbox=dict(boxstyle="round", facecolor="#f8f9fa", alpha=0.8, edgecolor="#dee2e6"),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = output_dir / "fig_reconciliation.pdf"
    fig.savefig(out_pdf, format="pdf", bbox_inches="tight")
    fig.savefig(output_dir / "fig_reconciliation.png", format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"    Saved: {out_pdf}")


if __name__ == "__main__":
    generate(Path("paper/figures"))
