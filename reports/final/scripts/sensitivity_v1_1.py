# NOTE (final audit): the bootstrap intervals in this script use Python random resampling and are SUPERSEDED.
# Authoritative intervals: results/final_go/bootstrap_original_method.json (reports/final_go/bootstrap_reproduction.py).
# Exact p-values in this script are unaffected.
"""Label-set sensitivity for JCL-SemBench v1.1. Uses only committed predictions and labels.

Label sets:
  L0  original labels (as published)
  L1  C1-corrected (15 byte-identical CHANGING -> PRESERVING)
  L2  L1 excluding the 14 unresolved cases (13 oracle disagreements + 1 abstention)
  L3  L1 with the 14 unresolved relabelled by the oracle verdict (DIFFERENT->CHANGING,
      EQUIVALENT->PRESERVING; the abstention is excluded). Upper-bound sensitivity, not ground truth.
Cluster bootstrap on base_id (16 clusters), 10,000 resamples, seed 20261004 (same as published analysis).
Writes: results/final/statistics/sensitivity_three_way.json and .csv
"""
import json, random, os, csv
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
cases = {json.loads(l)["id"]: json.loads(l) for l in open("benchmarks/sembench/cases.jsonl")}
preds = {json.loads(l)["id"]: json.loads(l) for l in open("results/sembench/predictions.jsonl")}
DETS = sorted(next(iter(preds.values()))["pred"].keys())

unresolved = {i for i, c in cases.items() if c["validation_status"] in ("ORACLE_DISAGREES", "ORACLE_ABSTAINS")
              and c["original_sha256"] != c["transformed_sha256"]}
c1 = {i for i, c in cases.items() if c["original_sha256"] == c["transformed_sha256"] and c["expected_outcome"] == "CHANGING"}

def oracle_label(i):
    v = cases[i]["oracle_verdict"]
    return v.get("label") if isinstance(v, dict) else v

L0 = {i: c["expected_outcome"] for i, c in cases.items()}
L1 = {i: ("PRESERVING" if i in c1 else L0[i]) for i in cases}
L2 = {i: L1[i] for i in cases if i not in unresolved}
L3 = {}
for i in cases:
    if i in unresolved:
        ol = oracle_label(i)
        if ol == "DIFFERENT": L3[i] = "CHANGING"
        elif ol == "EQUIVALENT": L3[i] = "PRESERVING"
    else:
        L3[i] = L1[i]

def confusion(labels, det):
    tp = fp = tn = fn = 0
    for i, y in labels.items():
        yc = y == "CHANGING"; p = bool(preds[i]["pred"][det])
        if yc and p: tp += 1
        elif yc: fn += 1
        elif p: fp += 1
        else: tn += 1
    return tp, fp, tn, fn

def stats(tp, fp, tn, fn):
    def div(a, b): return a / b if b else float("nan")
    prec, rec = div(tp, tp + fp), div(tp, tp + fn)
    f1 = div(2 * prec * rec, prec + rec) if prec == prec and rec == rec else float("nan")
    spec = div(tn, tn + fp)
    den = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    mcc = (tp * tn - fp * fn) / den if den else float("nan")
    return dict(tp=tp, fp=fp, tn=tn, fn=fn, precision=prec, recall=rec, f1=f1, specificity=spec, fpr=1 - spec if spec == spec else float("nan"), mcc=mcc)

clusters = {}
for i in cases: clusters.setdefault(cases[i]["base_id"], []).append(i)
keys = sorted(clusters)
def boot_mcc(labels, det, B=10000, seed=20261004):
    rng = random.Random(seed); vals = []
    for _ in range(B):
        ids = []
        for k in [keys[rng.randrange(len(keys))] for _ in keys]:
            ids += clusters[k]
        sub = {i: labels[i] for i in ids if i in labels}
        s = stats(*confusion(sub, det))
        if s["mcc"] == s["mcc"]: vals.append(s["mcc"])
    vals.sort()
    return [vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]]

out = {"n_unresolved_excluded_in_L2": len(unresolved), "unresolved_ids": sorted(unresolved), "sets": {}}
rows = []
for name, lab in [("L0_original", L0), ("L1_C1_corrected", L1), ("L2_C1_excl_unresolved", L2), ("L3_C1_oracle_relabel_unresolved", L3)]:
    out["sets"][name] = {"n": len(lab), "n_changing": sum(v == "CHANGING" for v in lab.values()), "detectors": {}}
    for d in DETS:
        s = stats(*confusion(lab, d))
        ci = boot_mcc(lab, d, B=10000)
        s["mcc_ci95_cluster_boot"] = ci
        out["sets"][name]["detectors"][d] = s
        rows.append({"label_set": name, "detector": d, "n": len(lab), **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items() if k != "mcc_ci95_cluster_boot"}, "mcc_ci_low": round(ci[0], 4), "mcc_ci_high": round(ci[1], 4)})
    print(name, len(lab), {d: round(out["sets"][name]["detectors"][d]["mcc"], 3) for d in ["relic_v2", "normalized_text_B", "textdiff"]}, flush=True)

json.dump(out, open("results/final/statistics/sensitivity_three_way.json", "w"), indent=2, sort_keys=True)
with open("results/final/statistics/sensitivity_three_way.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("RELIC_v2 minus normalized_text_B MCC, per label set:")
for name in out["sets"]:
    d = out["sets"][name]["detectors"]
    print(" ", name, round(d["relic_v2"]["mcc"] - d["normalized_text_B"]["mcc"], 3))
