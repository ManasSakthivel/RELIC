"""True best/worst-case bounds for the 13 non-identical oracle disagreements (2^13 label assignments),
on the L1 base (C1 applied; abstention kept at its original label), plus a deduplicated analysis that
drops the 25 byte-identical pairs. MCC difference RELIC V2 minus normalized text B.
Writes results/final/statistics/bounds_and_dedup.json
"""
import json, math, itertools, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
cases = {json.loads(l)["id"]: json.loads(l) for l in open("benchmarks/sembench/cases.jsonl")}
P = {json.loads(l)["id"]: json.loads(l)["pred"] for l in open("results/sembench/predictions.jsonl")}
ids = sorted(cases)
ident = {i for i in ids if cases[i]["original_sha256"] == cases[i]["transformed_sha256"]}
c1 = {i for i in ident if cases[i]["expected_outcome"] == "CHANGING"}
disputed = sorted(i for i in ids if cases[i]["validation_status"] == "ORACLE_DISAGREES" and i not in ident)
base = {i: ("PRESERVING" if i in c1 else cases[i]["expected_outcome"]) for i in ids}
def mcc(lab, d, sub):
    tp=fp=tn=fn=0
    for i in sub:
        y = lab[i] == "CHANGING"; p = bool(P[i][d])
        if y and p: tp+=1
        elif y: fn+=1
        elif p: fp+=1
        else: tn+=1
    den = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    return (tp*tn-fp*fn)/den if den else 0.0
def delta(lab, sub): return mcc(lab, "relic_v2", sub) - mcc(lab, "normalized_text_B", sub)
vals = []
for combo in itertools.product(["CHANGING", "PRESERVING"], repeat=len(disputed)):
    lab = dict(base)
    lab.update(dict(zip(disputed, combo)))
    vals.append(delta(lab, ids))
out = {"n_disputed": len(disputed), "assignments": len(vals),
       "delta_mcc_min": round(min(vals), 4), "delta_mcc_max": round(max(vals), 4),
       "delta_mcc_all_disputed_as_CHANGING": round(delta({**base, **{i: "CHANGING" for i in disputed}}, ids), 4),
       "delta_mcc_all_disputed_as_PRESERVING": round(delta({**base, **{i: "PRESERVING" for i in disputed}}, ids), 4),
       "dedup_excl_25_identical_L1_base": round(delta(base, [i for i in ids if i not in ident]), 4),
       "n_dedup": len([i for i in ids if i not in ident])}
print(json.dumps(out, indent=2))
json.dump(out, open("results/final/statistics/bounds_and_dedup.json", "w"), indent=2)
