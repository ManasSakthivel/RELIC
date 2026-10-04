"""
Figures generated from results/final/metrics.json (never from hand-typed numbers).

  figures/final/f1_carddemo.svg        F1 with file-bootstrap 95% CI per detector (CardDemo)
  figures/final/accounting.svg         candidate-mutant accounting per subject
  figures/final/operator_recall.svg    recall per fault operator, RELIC v1.0.0 vs v1.1 (CardDemo)
  docs/assets/relic-results.svg        copy of f1_carddemo.svg used by README.md
"""

from __future__ import annotations

import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from relic_eval.subjects import ROOT  # noqa: E402

OUT = ROOT / "figures" / "final"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]   # reference palette, fixed order
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "svg.hashsalt": "relic", "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
})


def _save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, format="svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)


def f1_plot(m: dict) -> None:
    from relic_eval.report import DETECTOR_LABELS, DETECTORS
    r = m["results"]["carddemo"]
    dets = list(reversed(DETECTORS))
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    for i, d in enumerate(dets):
        f1 = r["detectors"][d]["f1"] or 0.0
        lo_hi = r["bootstrap"]["f1_ci95"].get(d)
        if lo_hi:
            ax.plot(lo_hi, [i, i], color=SERIES[0], lw=2, solid_capstyle="round", alpha=0.45)
        ax.plot([f1], [i], "o", ms=8, color=SERIES[0], mec=SURFACE, mew=2)
        ax.text(1.02, i, f"{f1:.3f}", va="center", color=INK, fontsize=9, transform=ax.get_yaxis_transform())
    ax.set_yticks(range(len(dets)), [DETECTOR_LABELS[d] for d in dets])
    ax.set_xlim(0, 1)
    ax.set_xlabel("F1 (dot) with 95% file-level bootstrap interval (line)")
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_title(f"CardDemo source-level benchmark, n = {r['n']} "
                 f"({r['positives']} behaviour-changing / {r['negatives']} preserving)",
                 loc="left", color=INK, fontsize=10)
    _save(fig, "f1_carddemo.svg")


def accounting_plot(m: dict) -> None:
    from relic_eval.pipeline import STATUSES
    from relic_eval.subjects import SUBJECTS
    pops = ["carddemo", "omp_course", "genapp"]
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    for i, p in enumerate(reversed(pops)):
        left = 0
        for j, s in enumerate(STATUSES):
            v = m["accounting"][p]["by_status"][s]
            if v:
                ax.barh(i, v, left=left, color=SERIES[j], edgecolor=SURFACE, linewidth=2, height=0.6,
                        label=s if i == 0 else None)
            left += v
        ax.text(left + 4, i, str(left), va="center", color=INK, fontsize=9)
    ax.set_yticks(range(len(pops)), [SUBJECTS[p].title for p in reversed(pops)])
    ax.set_xlabel("candidate mutants")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    handles, labels = ax.get_legend_handles_labels()
    order = [labels.index(s) for s in STATUSES if s in labels]
    ax.legend([handles[k] for k in order], [labels[k] for k in order], ncol=3, frameon=False,
              loc="upper left", bbox_to_anchor=(0, -0.35), fontsize=8)
    ax.set_title("Accounting of every candidate mutant", loc="left", color=INK, fontsize=10)
    _save(fig, "accounting.svg")


def operator_plot(m: dict) -> None:
    from relic_eval.mutate import FAULT_OPERATORS
    block = m["per_operator"]["carddemo"]
    ops = [o for o in FAULT_OPERATORS if o in block and block[o]["relic_v1_0"]["positives"] > 0]
    fig, ax = plt.subplots(figsize=(7.2, 0.45 * len(ops) + 1.0))
    h = 0.36
    for k, (det, label) in enumerate((("relic_v1_0", "RELIC v1.0.0"), ("relic_v1_1", "RELIC v1.1 (post-hoc)"))):
        for i, op in enumerate(reversed(ops)):
            rec = block[op][det]["recall"] or 0.0
            y = i + (h / 2 if k == 0 else -h / 2)
            ax.barh(y, rec, height=h, color=SERIES[k], edgecolor=SURFACE, linewidth=2,
                    label=label if i == 0 else None)
    for i, op in enumerate(reversed(ops)):
        ax.text(1.02, i, f"n+={block[op]['relic_v1_0']['positives']}", va="center", color=INK2,
                fontsize=8, transform=ax.get_yaxis_transform())
    ax.set_yticks(range(len(ops)), list(reversed(ops)))
    ax.set_xlim(0, 1)
    ax.set_xlabel("recall on behaviour-changing mutants")
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.12 - 0.6 / len(ops)), ncol=2, fontsize=8)
    ax.set_title("Recall per fault operator (CardDemo)", loc="left", color=INK, fontsize=10)
    _save(fig, "operator_recall.svg")


def main(m: dict) -> None:
    f1_plot(m)
    accounting_plot(m)
    operator_plot(m)
    shutil.copyfile(OUT / "f1_carddemo.svg", ROOT / "docs" / "assets" / "relic-results.svg")
