"""Figures for the ResponsibleSE 2027 paper. Reads raw inputs only; writes figures/*.pdf.
Run from anywhere: python3 make_figures.py  (needs matplotlib)."""
import json, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "figures"); os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "serif", "font.size": 7.5, "axes.linewidth": 0.6, "pdf.fonttype": 42})

C = {j["id"]: j for j in map(json.loads, open(os.path.join(REPO, "benchmarks/sembench/cases.jsonl")))}
ids = sorted(C)
ident = {i for i in ids if C[i]["original_sha256"] == C[i]["transformed_sha256"]}
unres = {i for i in ids if C[i]["validation_status"] in ("ORACLE_DISAGREES", "ORACLE_ABSTAINS") and i not in ident}

# ---- Figure 1: study pipeline (flowchart) ----
fig, ax = plt.subplots(figsize=(7.2, 2.6)); ax.set_xlim(0, 100); ax.set_ylim(0, 40); ax.axis("off")
def box(x, y, w, h, title, body, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.0", fc=fc, ec="#333333", lw=0.6))
    ax.text(x + w/2, y + h - 2.0, title, ha="center", va="top", fontsize=6.6, weight="bold")
    ax.text(x + w/2, y + (h - 6)/2 - 0.5, body, ha="center", va="center", fontsize=5.5, linespacing=1.3)
def arr(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", lw=0.6, color="#333333"))
TOP, H = 20, 18
box(0, TOP, 18, H, "1 Benchmark", "180 pairs\n93 CHANGING\n87 PRESERVING\n16 base programs", "#e8e8e8")
box(21, TOP, 18, H, "2 Audit", "25 byte-identical\n21 duplicate groups\n28 oracle disagreements\n1 abstention", "#fff3c4")
box(42, TOP, 18, H, "3 Label sets", "L0 original\nL1 no-op-adjusted\nL2 excl. disputed\nL3 oracle-derived", "#d6e6f5")
box(63, TOP, 18, H, "4 Detectors", "RELIC V2 (binary)\nnormalized text B\nfrozen predictions", "#e8e8e8")
box(82, TOP, 18, H, "5 Statistics", "MCC, cluster\nbootstrap, exact\ncluster test, McNemar", "#e8e8e8")
for x1, x2 in [(18.5, 20.5), (39.5, 41.5), (60.5, 62.5), (81.5, 83.5)]:
    arr(x1, TOP + H/2, x2, TOP + H/2)
box(21, 0, 39, 13, "Output for maintainers", "gap size depends on the label set;\npoint-estimate sign unchanged;\nL3 not significant (exact p = 0.089)", "#ffffff")
box(63, 0, 37, 13, "Not performed", "independent practitioner labels;\nheld-out corpus; independent oracle;\nconsequence analysis", "#ffffff")
arr(41.5, TOP - 1.5, 41.5, 13.8)
fig.savefig(os.path.join(OUT, "fig1_pipeline.pdf"), bbox_inches="tight"); plt.close(fig)

# ---- Figure 2: MCC with 95% cluster bootstrap intervals (values from the saved bootstrap run) ----
B = json.load(open(os.path.join(REPO, "results/final_go/bootstrap_original_method.json")))
labels = ["L0 original", "L1 no-op-adj.", "L2 excl. disputed", "L3 oracle-derived"]
keys = ["L0", "L1", "L2", "L3"]
fig, ax = plt.subplots(figsize=(3.45, 2.35))
for off, det, col, name in [(-0.12, "relic_v2", "#1f4e79", "RELIC V2"), (0.12, "normalized_text_B", "#b5651d", "Normalized text B")]:
    ys = [B[k][det]["mcc_point"] for k in keys]
    lo = [B[k][det]["mcc_ci95"][0] for k in keys]; hi = [B[k][det]["mcc_ci95"][1] for k in keys]
    x = [i + off for i in range(4)]
    ax.errorbar(x, ys, yerr=[[y - l for y, l in zip(ys, lo)], [h - y for y, h in zip(ys, hi)]], fmt="o", ms=3.5,
                color=col, capsize=2, lw=0.9, label=name)
ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=5.8, rotation=12)
ax.set_ylabel("MCC (95% cluster bootstrap)", fontsize=6.5); ax.set_ylim(0, 0.9); ax.axhline(0, color="grey", lw=0.5)
ax.legend(frameon=False, fontsize=6, loc="upper left", ncol=2)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig2_mcc_by_label_set.pdf")); plt.close(fig)

# ---- Figure 3: composition of the 180 pairs by mutually exclusive class ----
def klass(i):
    if i in ident: return "Byte-identical (no-op)"
    if C[i]["validation_status"] == "ORACLE_ABSTAINS": return "Oracle abstains"
    if i in unres: return "Oracle disagrees"
    return "Oracle agrees (no dispute)"
cnt = collections.Counter((C[i]["expected_outcome"], klass(i)) for i in ids)
order = ["Oracle agrees (no dispute)", "Oracle disagrees", "Oracle abstains", "Byte-identical (no-op)"]
colors = {"Oracle agrees (no dispute)": "#7f7f7f", "Oracle disagrees": "#c9a227", "Oracle abstains": "#8fb8de", "Byte-identical (no-op)": "#c0392b"}
fig, ax = plt.subplots(figsize=(3.45, 2.1))
for row, outcome in enumerate(["CHANGING", "PRESERVING"]):
    left = 0
    for k in order:
        v = cnt.get((outcome, k), 0)
        if not v: continue
        ax.barh(row, v, left=left, color=colors[k], edgecolor="white", lw=0.4, label=k if row == 0 else None)
        if v >= 6: ax.text(left + v/2, row, str(v), ha="center", va="center", fontsize=6, color="white" if k != "Oracle disagrees" and k != "Oracle abstains" else "black")
        left += v
ax.set_yticks([0, 1]); ax.set_yticklabels(["CHANGING (93)", "PRESERVING (87)"], fontsize=6.3); ax.invert_yaxis()
ax.set_xlabel("Pairs (mutually exclusive classes)", fontsize=6.3)
ax.legend(frameon=False, fontsize=5.4, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.42))
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig3_composition.pdf")); plt.close(fig)
print("composition", {f"{o}/{k}": v for (o, k), v in cnt.items()})
print("figures written:", sorted(os.listdir(OUT)))
