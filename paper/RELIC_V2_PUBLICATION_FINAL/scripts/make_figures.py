"""Generate paper figures from committed analysis outputs (no hand-typed values).

Inputs : results/recovery/stats_reanalysis.json, benchmarks/sembench/cases.jsonl
Outputs: paper/RELIC_V2_PUBLICATION_FINAL/figures/*.pdf
Run from repo root: python paper/RELIC_V2_PUBLICATION_FINAL/scripts/make_figures.py
"""
import json, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "paper/RELIC_V2_PUBLICATION_FINAL/figures"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.linewidth": 0.6,
                     "pdf.fonttype": 42})

s = json.load(open("results/recovery/stats_reanalysis.json"))
pops = s["sembench"]["populations"]
POP_ORDER = ["ALL_180", "EXCL_25_IDENTICAL", "CLEAN_CORE", "SENS_EXCL_13_NONIDENT_ORACLE_DISAGREES"]
POP_LABEL = {"ALL_180": "All 180", "EXCL_25_IDENTICAL": "Excl. 25\nidentical",
             "CLEAN_CORE": "Clean core\n(n=141)",
             "SENS_EXCL_13_NONIDENT_ORACLE_DISAGREES": "Excl. 13\ndisagreements"}

# ---- Figure 1: MCC with cluster-bootstrap CI, and changing-class overlap ----
fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.5), gridspec_kw={"width_ratios": [1.5, 1]})
for det, col, off, lab in [("relic_v2", "#1f4e79", -0.08, "RELIC V2"),
                           ("normalized_text_B", "#b5651d", 0.08, "Normalized text (B)")]:
    xs, ys, lo, hi = [], [], [], []
    for i, p in enumerate(POP_ORDER):
        d = pops[p]["detectors"][det]
        xs.append(i + off)
        ys.append(d["mcc"])
        lo.append(d["mcc"] - d["boot"]["mcc"]["ci95"][0])
        hi.append(d["boot"]["mcc"]["ci95"][1] - d["mcc"])
    a.errorbar(xs, ys, yerr=[lo, hi], fmt="o", color=col, capsize=2, ms=4, lw=0.9, label=lab)
a.set_xticks(range(len(POP_ORDER)))
a.set_xticklabels([POP_LABEL[p] for p in POP_ORDER], fontsize=6.5)
a.set_ylabel("MCC (95% cluster bootstrap, 16 clusters)")
a.set_ylim(0, 0.9)
a.axhline(0, color="grey", lw=0.5)
a.legend(frameon=False, fontsize=6.5, loc="lower left")
a.set_title("(a) SemBench MCC by population", fontsize=8)

# changing-class overlap, ALL_180, RELIC V2 vs normalized text B
cmp_ = pops["ALL_180"]["comparisons"]["normalized_text_B"]
both = pops["ALL_180"]["detectors"]["relic_v2"]["tp"]
text_only = cmp_["baseline_only_tp"]
relic_only = cmp_["relic_only_tp"]
neither = pops["ALL_180"]["n_changing"] - both - text_only - relic_only
assert both + text_only + relic_only + neither == pops["ALL_180"]["n_changing"]
labels = ["Both", "Text only", "RELIC only", "Neither"]
vals = [both, text_only, relic_only, neither]
cols = ["#4d4d4d", "#b5651d", "#1f4e79", "#dddddd"]
b.barh(labels[::-1], vals[::-1], color=cols[::-1])
for y, v in enumerate(vals[::-1]):
    b.text(v + 1, y, str(v), va="center", fontsize=7)
b.set_xlabel("Changing cases (n = 93)")
b.set_xlim(0, 100)
b.set_title("(b) Which changing cases are caught", fontsize=8)
fig.tight_layout()
fig.savefig(f"{OUT}/fig1_mcc_and_overlap.pdf")

# ---- Figure 2: mutually exclusive benchmark composition ----
cases = [json.loads(l) for l in open("benchmarks/sembench/cases.jsonl")]
ident = {c["id"] for c in cases if c["original_sha256"] == c["transformed_sha256"]}
disagree = {c["id"] for c in cases if c["oracle_agrees_with_expected"] is False}
abstain = {c["id"] for c in cases if c["validation_status"] == "ORACLE_ABSTAINS"}
comp = collections.Counter()
for c in cases:
    chg = c["expected_outcome"] == "CHANGING"
    if c["id"] in ident:
        k = "Byte-identical no-op"
    elif c["id"] in abstain:
        k = "Oracle abstains"
    elif c["id"] in disagree:
        k = "Oracle disagrees"
    else:
        k = "Validated (oracle agrees)"
    comp[(("Changing" if chg else "Preserving"), k)] += 1
assert sum(comp.values()) == 180 and sum(v for (t, _), v in comp.items() if t == "Changing") == 93
assert comp[("Changing", "Byte-identical no-op")] == 15 and comp[("Preserving", "Byte-identical no-op")] == 10

fig, ax = plt.subplots(figsize=(3.4, 1.6))
order = ["Validated (oracle agrees)", "Oracle disagrees", "Oracle abstains", "Byte-identical no-op"]
colors = {"Validated (oracle agrees)": "#4d4d4d", "Oracle disagrees": "#c9a227",
          "Oracle abstains": "#8fb8de", "Byte-identical no-op": "#c0392b"}
for row, t in enumerate(["Changing", "Preserving"]):
    left = 0
    for k in order:
        v = comp.get((t, k), 0)
        if v == 0:
            continue
        ax.barh(row, v, left=left, color=colors[k], edgecolor="white", lw=0.4,
                label=k if row == 0 else None)
        if v >= 8:
            ax.text(left + v / 2, row, str(v), ha="center", va="center", fontsize=6.5,
                    color="white" if k in ("Validated (oracle agrees)", "Byte-identical no-op") else "black")
        left += v
ax.set_yticks([0, 1])
ax.set_yticklabels(["Changing (93)", "Preserving (87)"], fontsize=7)
ax.set_xlabel("Pairs (mutually exclusive; total 180)", fontsize=7)
ax.invert_yaxis()
ax.legend(frameon=False, fontsize=5.8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.45))
fig.tight_layout()
fig.savefig(f"{OUT}/fig2_benchmark_composition.pdf")
print("composition", {f"{t}/{k}": v for (t, k), v in comp.items()})
print("figures written to", OUT)

# ---- Figure 3: evaluation pipeline and evidence status (schematic; labels from verified counts) ----
from matplotlib.patches import FancyBboxPatch
fig, ax = plt.subplots(figsize=(7.2, 2.5))
ax.set_xlim(0, 100)
ax.set_ylim(0, 40)
ax.axis("off")

def box(x, y, w, h, text, fc, ls="-", ec="#333333"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                fc=fc, ec=ec, lw=0.7, ls=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=6.3)

def arrow(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", lw=0.7, color="#333333"))

DEV, EXT, NONE, AUD = "#e8e8e8", "#d6e6f5", "#ffffff", "#fff3c4"
# development row
box(1, 27, 18, 9, "JCL-SemBench\n180 pairs, 93 CHANGING\n(frozen; development)", DEV)
box(24, 27, 18, 9, "Frozen predictions\n6 detectors (binary)", DEV)
box(47, 27, 20, 9, "Paired statistics\nMCC, bootstrap, McNemar, Holm", DEV)
# external row
box(1, 13, 18, 9, "External run\n824 mutants, 7 repos\n(same oracle, not blind)", EXT)
box(24, 13, 18, 9, "Frozen predictions\n5 detectors (binary)", EXT)
box(47, 13, 20, 9, "Paired statistics\nF1/MCC, file and repo clusters", EXT)
# audit
box(1, 1, 66, 8, "Benchmark and oracle audit: 25 byte-identical pairs, 21 duplicate groups, 13 disagreements, 1 abstention", AUD)
box(72, 27, 27, 9, "Sensitivity populations\n(post hoc; reported in full)", AUD)
box(72, 13, 27, 9, "Independent evidence:\nnone (no held-out corpus,\nno human labels, no LLM run)", NONE, ls="--", ec="#c0392b")
arrow(19, 31.5, 24, 31.5); arrow(42, 31.5, 47, 31.5)
arrow(19, 17.5, 24, 17.5); arrow(42, 17.5, 47, 17.5)
arrow(67, 31.5, 72, 31.5)
arrow(34, 1, 34, 9.5)
arrow(67, 30, 72, 22.5)
ax.text(1, 38.5, "Development evidence (same author; same oracle)", fontsize=6.5, weight="bold")
ax.text(1, 24.5, "External evidence (same oracle; not blind)", fontsize=6.5, weight="bold")
ax.text(72, 38.5, "Post hoc and absent evidence", fontsize=6.5, weight="bold")
fig.tight_layout()
fig.savefig(f"{OUT}/fig0_evaluation_pipeline.pdf")
print("pipeline figure written")
