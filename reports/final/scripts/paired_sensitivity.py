"""Paired comparison RELIC V2 vs normalized_text_B on each label set (frozen v1.1 analysis).
Cluster bootstrap of the MCC difference (base_id clusters, 10,000 resamples, seed 20261004) and
exact McNemar test on per-case correctness. Reuses label sets from sensitivity_v1_1.py logic.
Writes results/final/statistics/paired_sensitivity.json
"""
import json, random, os, math
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
cases = {json.loads(l)["id"]: json.loads(l) for l in open("benchmarks/sembench/cases.jsonl")}
preds = {json.loads(l)["id"]: json.loads(l) for l in open("results/sembench/predictions.jsonl")}
unres = {i for i, c in cases.items() if c["validation_status"] in ("ORACLE_DISAGREES", "ORACLE_ABSTAINS") and c["original_sha256"] != c["transformed_sha256"]}
c1 = {i for i, c in cases.items() if c["original_sha256"] == c["transformed_sha256"] and c["expected_outcome"] == "CHANGING"}
def ol(i):
    v = cases[i]["oracle_verdict"]; return v.get("label") if isinstance(v, dict) else v
L0 = {i: c["expected_outcome"] for i, c in cases.items()}
L1 = {i: ("PRESERVING" if i in c1 else L0[i]) for i in cases}
L2 = {i: L1[i] for i in cases if i not in unres}
L3 = {}
for i in cases:
    if i in unres:
        if ol(i) == "DIFFERENT": L3[i] = "CHANGING"
        elif ol(i) == "EQUIVALENT": L3[i] = "PRESERVING"
    else: L3[i] = L1[i]
def mcc(lab, d, ids):
    tp=fp=tn=fn=0
    for i in ids:
        y = lab[i] == "CHANGING"; p = bool(preds[i]["pred"][d])
        if y and p: tp+=1
        elif y: fn+=1
        elif p: fp+=1
        else: tn+=1
    den = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    return (tp*tn-fp*fn)/den if den else float("nan")
clusters = {}
for i in cases: clusters.setdefault(cases[i]["base_id"], []).append(i)
keys = sorted(clusters)
out = {}
for name, lab in [("L0_original", L0), ("L1_C1_corrected", L1), ("L2_C1_excl_unresolved", L2), ("L3_C1_oracle_relabel_unresolved", L3)]:
    ids = sorted(lab)
    a, b = "relic_v2", "normalized_text_B"
    point = mcc(lab, a, ids) - mcc(lab, b, ids)
    rng = random.Random(20261004); deltas = []
    for _ in range(10000):
        sample = []
        for k in [keys[rng.randrange(len(keys))] for _ in keys]:
            sample += [i for i in clusters[k] if i in lab]
        if not sample: continue
        d = mcc(lab, a, sample) - mcc(lab, b, sample)
        if d == d: deltas.append(d)
    deltas.sort()
    # exact McNemar on per-case correctness
    n01 = n10 = 0
    for i in ids:
        ca = (lab[i] == "CHANGING") == bool(preds[i]["pred"][a])
        cb = (lab[i] == "CHANGING") == bool(preds[i]["pred"][b])
        if ca and not cb: n10 += 1
        elif cb and not ca: n01 += 1
    m = n01 + n10
    p = min(1.0, 2 * sum(math.comb(m, k) for k in range(0, min(n01, n10) + 1)) / 2**m) if m else 1.0
    out[name] = {"n": len(ids), "mcc_relic_v2": round(mcc(lab, a, ids), 4), "mcc_text_B": round(mcc(lab, b, ids), 4),
                 "delta_mcc": round(point, 4), "delta_mcc_ci95": [round(deltas[int(0.025*len(deltas))], 4), round(deltas[int(0.975*len(deltas))], 4)],
                 "mcnemar_relic_only_correct": n10, "mcnemar_text_only_correct": n01, "mcnemar_exact_p": round(p, 6)}
    print(name, out[name])
json.dump(out, open("results/final/statistics/paired_sensitivity.json", "w"), indent=2)
