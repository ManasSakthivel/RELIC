"""Exact stepwise decomposition of the L1 -> L3 change in the MCC gap (RELIC V2 minus normalized text B).
Each step applies one group of relabellings cumulatively, in a fixed order, so the steps sum exactly
to the total change. Oracle verdicts are used only as the scenario definition, not as ground truth.
Writes results/final/statistics/l3_decomposition.json
"""
import json, math, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
cases = {json.loads(l)["id"]: json.loads(l) for l in open("benchmarks/sembench/cases.jsonl")}
P = {json.loads(l)["id"]: json.loads(l) for l in open("results/sembench/predictions.jsonl")}
ids = sorted(cases)
ident = {i for i in ids if cases[i]["original_sha256"] == cases[i]["transformed_sha256"]}
disp = {i for i in ids if cases[i]["validation_status"] in ("ORACLE_DISAGREES", "ORACLE_ABSTAINS") and i not in ident}
def ol(i):
    v = cases[i]["oracle_verdict"]; return v.get("label") if isinstance(v, dict) else v
L1 = {i: ("PRESERVING" if (i in ident and cases[i]["expected_outcome"] == "CHANGING") else cases[i]["expected_outcome"]) for i in ids}
def mcc(lab, d):
    tp=fp=tn=fn=0
    for i in ids:
        if i not in lab: continue
        y = lab[i] == "CHANGING"; p = bool(P[i]["pred"][d])
        if y and p: tp+=1
        elif y: fn+=1
        elif p: fp+=1
        else: tn+=1
    den = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    return (tp*tn-fp*fn)/den if den else 0.0
def gap(lab): return mcc(lab, "relic_v2") - mcc(lab, "normalized_text_B")
# Step groups, in order
g_oracle_diff_pres = sorted(i for i in disp if cases[i]["expected_outcome"] == "PRESERVING" and ol(i) == "DIFFERENT")       # 036, 078, 079
g_oracle_diff_chg  = sorted(i for i in disp if cases[i]["expected_outcome"] == "CHANGING" and ol(i) == "DIFFERENT")         # none expected
g_oracle_eq_chg    = sorted(i for i in disp if cases[i]["expected_outcome"] == "CHANGING" and ol(i) == "EQUIVALENT")         # 10
abst = sorted(i for i in disp if ol(i) == "UNDETERMINED")                                                                 # 172
lab = dict(L1); steps = [("L1 (C1 applied)", None, gap(lab))]
def apply(name, mapping, drop=()):
    for i, v in mapping.items(): lab[i] = v
    for i in drop: lab.pop(i, None)
    steps.append((name, sorted(mapping) + sorted(drop), gap(lab)))
apply("+ PRESERVING disputed, oracle DIFFERENT -> CHANGING (036,078,079)", {i: "CHANGING" for i in g_oracle_diff_pres})
apply("+ CHANGING disputed, oracle EQUIVALENT -> PRESERVING (10)", {i: "PRESERVING" for i in g_oracle_eq_chg})
apply("+ abstention excluded (172)", {}, drop=abst)
out = []
prev = None
for name, changed, g in steps:
    out.append({"step": name, "cases": changed, "gap": round(g, 4), "delta_from_previous": None if prev is None else round(g - prev, 4)})
    prev = g
print(json.dumps(out, indent=2))
print("sum of steps:", round(sum(s["delta_from_previous"] for s in out[1:]), 4), " total L1->L3:", round(out[-1]["gap"] - out[0]["gap"], 4))
json.dump({"steps": out, "L3_recomputed_gap": round(gap({i: L1[i] for i in ids}), 4)}, open("results/final/statistics/l3_decomposition.json", "w"), indent=2)
