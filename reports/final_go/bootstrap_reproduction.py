"""Re-implements the ORIGINAL cluster bootstrap (reports/recovery/scripts/stats_reanalysis.py, class Boot):
sorted base_id clusters, one shared numpy index matrix default_rng(20261004).integers(0,K,(10000,K)),
percentile 95%, undefined reps dropped. Applied to the four label sets L0-L3 for RELIC V2 and text B.
Checks the L0 numbers against the published values before using them for any label set.
Outputs: results/final_go/bootstrap_original_method.json
"""
import json, math, os
import numpy as np
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SEED, REPS = 20261004, 10000
cases = {json.loads(l)["id"]: json.loads(l) for l in open("benchmarks/sembench/cases.jsonl")}
P = {json.loads(l)["id"]: json.loads(l)["pred"] for l in open("results/sembench/predictions.jsonl")}
ids = sorted(cases)
ident = {i for i in ids if cases[i]["original_sha256"] == cases[i]["transformed_sha256"]}
unres = {i for i in ids if cases[i]["validation_status"] in ("ORACLE_DISAGREES", "ORACLE_ABSTAINS") and i not in ident}
def ol(i):
    v = cases[i]["oracle_verdict"]; return v.get("label") if isinstance(v, dict) else v
L0 = {i: cases[i]["expected_outcome"] for i in ids}
L1 = {i: ("PRESERVING" if (i in ident and L0[i] == "CHANGING") else L0[i]) for i in ids}
L2 = {i: L1[i] for i in ids if i not in unres}
L3 = {}
for i in ids:
    if i in unres:
        if ol(i) == "DIFFERENT": L3[i] = "CHANGING"
        elif ol(i) == "EQUIVALENT": L3[i] = "PRESERVING"
    else: L3[i] = L1[i]
SETS = {"L0": L0, "L1": L1, "L2": L2, "L3": L3}

def mcc_from(tp, fp, tn, fn):
    den = np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(den > 0, (tp*tn - fp*fn) / den, np.nan)

def pct(x):
    ok = x[~np.isnan(x)]
    lo, hi = np.percentile(ok, [2.5, 97.5])
    return [round(float(lo), 4), round(float(hi), 4)], int(len(x) - len(ok))

out = {}
for name, lab in SETS.items():
    rows = list(lab)                       # ids in this label set
    cl = sorted({cases[i]["base_id"] for i in rows}); K = len(cl)
    pos = {c: k for k, c in enumerate(cl)}
    cidx = np.array([pos[cases[i]["base_id"]] for i in rows])
    idx = np.random.default_rng(SEED).integers(0, K, size=(REPS, K))
    y = np.array([lab[i] == "CHANGING" for i in rows])
    res = {}
    cells = {}
    for det in ("relic_v2", "normalized_text_B"):
        p = np.array([bool(P[i][det]) for i in rows])
        cc = [np.bincount(cidx[m], minlength=K) for m in (y & p, ~y & p, y & ~p, ~y & ~p)]
        cells[det] = cc
        tp, fp, fn, tn = (c[idx].sum(axis=1).astype(float) for c in cc)   # cell order: TP, FP, FN, TN
        point = mcc_from(np.array([cc[0].sum()]), np.array([cc[1].sum()]), np.array([cc[3].sum()]), np.array([cc[2].sum()]))[0]
        ci, und = pct(mcc_from(tp, fp, tn, fn))
        res[det] = {"mcc_point": round(float(point), 4), "mcc_ci95": ci, "undefined_reps": und}
    # paired difference on the same index matrix
    def sums(det):
        return [c[idx].sum(axis=1).astype(float) for c in cells[det]]
    a = sums("relic_v2"); b = sums("normalized_text_B")
    dif = mcc_from(a[0], a[1], a[3], a[2]) - mcc_from(b[0], b[1], b[3], b[2])   # (TP, FP, TN, FN)
    dpoint = res["relic_v2"]["mcc_point"] - res["normalized_text_B"]["mcc_point"]
    dci, dund = pct(dif)
    res["delta_relic_minus_textB"] = {"point": round(dpoint, 4), "ci95": dci, "undefined_reps": dund}
    res["n_items"] = len(rows); res["n_clusters"] = K
    out[name] = res
    print(name, "n", len(rows), "K", K, "RELIC", res["relic_v2"], "TEXT", res["normalized_text_B"], "DELTA", res["delta_relic_minus_textB"], sep="\n  ")

# check against the published L0 values (stats_reanalysis.json, population ALL_180)
_pub = json.load(open("results/recovery/stats_reanalysis.json"))["sembench"]["populations"]["ALL_180"]["detectors"]
pub = {"relic_mcc_ci": _pub["relic_v2"]["boot"]["mcc"]["ci95"], "text_mcc_ci": _pub["normalized_text_B"]["boot"]["mcc"]["ci95"], "delta_ci": json.load(open("results/recovery/stats_reanalysis.json"))["hypotheses"]["H1"]["diff_mcc_ci95"]}
ok = (out["L0"]["relic_v2"]["mcc_ci95"] == pub["relic_mcc_ci"]) and (out["L0"]["normalized_text_B"]["mcc_ci95"] == pub["text_mcc_ci"]) and (out["L0"]["delta_relic_minus_textB"]["ci95"] == pub["delta_ci"])
out["check_vs_published_L0"] = {"published": pub, "match": ok}
print("MATCH WITH PUBLISHED L0:", ok)
os.makedirs("results/final_go", exist_ok=True)
json.dump(out, open("results/final_go/bootstrap_original_method.json", "w"), indent=2)

# ---- matched LLM subset (K = clusters present in the subset), same original scheme ----
M = json.load(open("results/final/llm/matched_subset_v1/manifest.json"))
SUB = M["subset_ids"]
llm = {json.loads(l)["id"]: json.loads(l)["verdict"] for l in open("results/final/llm/matched_subset_v1/frozen_raw_snapshot.jsonl")}
def sub_scheme(name, lab_all, ids_sub):
    rows = [i for i in ids_sub if i in lab_all]
    cl = sorted({cases[i]["base_id"] for i in rows}); K = len(cl); pos = {c: k for k, c in enumerate(cl)}
    cidx = np.array([pos[cases[i]["base_id"]] for i in rows])
    idx = np.random.default_rng(SEED).integers(0, K, size=(REPS, K))
    y = np.array([lab_all[i] == "CHANGING" for i in rows])
    flagsets = {"LLM": np.array([llm[i] == "CHANGING" for i in rows]),
                "relic_v2": np.array([bool(P[i]["relic_v2"]) for i in rows]),
                "normalized_text_B": np.array([bool(P[i]["normalized_text_B"]) for i in rows])}
    cells = {}
    for k_, p in flagsets.items():
        cells[k_] = [np.bincount(cidx[m], minlength=K) for m in (y & p, ~y & p, y & ~p, ~y & ~p)]
    def draw(k_):
        a = [c[idx].sum(axis=1).astype(float) for c in cells[k_]]   # TP, FP, FN, TN
        return mcc_from(a[0], a[1], a[3], a[2])                      # (TP, FP, TN, FN)
    sec = {"n_items": len(rows), "n_clusters": K}
    for k_ in flagsets:
        sec[k_] = pct(draw(k_))[0]
    for a_, b_ in [("LLM", "relic_v2"), ("LLM", "normalized_text_B"), ("relic_v2", "normalized_text_B")]:
        ci, und = pct(draw(a_) - draw(b_))
        sec[f"{a_}_minus_{b_}"] = ci
    return sec
out["matched_subset"] = {}
for name, lab in SETS.items():
    out["matched_subset"][name] = sub_scheme(name, lab, SUB)
    print("SUBSET", name, out["matched_subset"][name])
json.dump(out, open("results/final_go/bootstrap_original_method.json", "w"), indent=2)
