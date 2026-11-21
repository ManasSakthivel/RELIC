"""Effect of the step-name scope decision on the RELIC V2 vs normalized text B comparison.
Compares L1 with L1 where only sembench_078/079 (PRESERVING, step renames, oracle DIFFERENT) are
relabelled CHANGING, plus the oracle-relabel of all 14 unresolved (L3) for reference.
Writes results/final/statistics/step_name_sensitivity.json
"""
import json, math, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
cases = {json.loads(l)["id"]: json.loads(l) for l in open("benchmarks/sembench/cases.jsonl")}
P = {json.loads(l)["id"]: json.loads(l) for l in open("results/sembench/predictions.jsonl")}
ids = sorted(cases)
ident = {i for i in ids if cases[i]["original_sha256"] == cases[i]["transformed_sha256"]}
base = {i: ("PRESERVING" if (i in ident and cases[i]["expected_outcome"] == "CHANGING") else cases[i]["expected_outcome"]) for i in ids}
def mcc(lab, d):
    tp=fp=tn=fn=0
    for i in ids:
        y = lab[i] == "CHANGING"; p = bool(P[i]["pred"][d])
        if y and p: tp+=1
        elif y: fn+=1
        elif p: fp+=1
        else: tn+=1
    den = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    return (tp*tn-fp*fn)/den if den else 0.0
def row(name, lab):
    r, t = mcc(lab, "relic_v2"), mcc(lab, "normalized_text_B")
    return {"scenario": name, "mcc_relic_v2": round(r, 4), "mcc_text_B": round(t, 4), "delta_mcc": round(r - t, 4)}
steps = ["sembench_078", "sembench_079"]
out = [row("L1 (C1 only)", base),
       row("L1 + 078,079 relabelled CHANGING (oracle verdict DIFFERENT)", {**base, **{i: "CHANGING" for i in steps}})]
changing_disputed = [i for i in ids if cases[i]["validation_status"] == "ORACLE_DISAGREES" and cases[i]["expected_outcome"] == "CHANGING" and i not in ident]
out.append(row(f"L1 + {len(changing_disputed)} disputed CHANGING relabelled PRESERVING (oracle EQUIVALENT)", {**base, **{i: "PRESERVING" for i in changing_disputed}}))
out.append(row("L1 + both of the above (decomposes L3 approx.)", {**base, **{i: "CHANGING" for i in steps}, **{i: "PRESERVING" for i in changing_disputed}}))
for r in out: print(r)
json.dump(out, open("results/final/statistics/step_name_sensitivity.json", "w"), indent=2)
