"""Figure: MCC by label set with cluster-bootstrap 95% CI (from results/final/statistics/sensitivity_three_way.json)."""
import json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
s = json.load(open("results/final/statistics/sensitivity_three_way.json"))["sets"]
sets = ["L0_original", "L1_C1_corrected", "L2_C1_excl_unresolved", "L3_C1_oracle_relabel_unresolved"]
labels = ["L0\noriginal\n(n=180)", "L1\nC1-corrected\n(n=180)", "L2\nC1, excl. 14\nunresolved (n=166)", "L3\nC1 + oracle\nrelabel (n=179)*"]
dets = [("relic_v2", "RELIC V2", "#1f4e79", -0.12), ("normalized_text_B", "Normalized text B", "#b5651d", 0.12)]
plt.rcParams.update({"font.family": "serif", "font.size": 8, "pdf.fonttype": 42})
fig, ax = plt.subplots(figsize=(3.5, 2.4))
for d, name, col, off in dets:
    xs = [i + off for i in range(len(sets))]
    ys = [s[k]["detectors"][d]["mcc"] for k in sets]
    lo = [s[k]["detectors"][d]["mcc"] - s[k]["detectors"][d]["mcc_ci95_cluster_boot"][0] for k in sets]
    hi = [s[k]["detectors"][d]["mcc_ci95_cluster_boot"][1] - s[k]["detectors"][d]["mcc"] for k in sets]
    ax.errorbar(xs, ys, yerr=[lo, hi], fmt="o", color=col, capsize=2, ms=4, lw=0.9, label=name)
ax.set_xticks(range(len(sets))); ax.set_xticklabels(labels, fontsize=5.8)
ax.set_ylabel("MCC (95% cluster bootstrap)", fontsize=7); ax.set_ylim(0, 1)
ax.axhline(0, color="grey", lw=0.5); ax.legend(frameon=False, fontsize=6.5, loc="upper left")
fig.tight_layout(); os.makedirs("paper/RELIC_V2_PUBLICATION_FINAL/figures", exist_ok=True)
fig.savefig("paper/RELIC_V2_PUBLICATION_FINAL/figures/fig_sensitivity_mcc.pdf"); print("figure written")
