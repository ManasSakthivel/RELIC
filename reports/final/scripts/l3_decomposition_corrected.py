"""Exact stepwise decomposition of the L1 -> L3 change in the MCC gap (RELIC V2 minus normalized text B).
Each step applies one group of relabellings cumulatively, in a fixed order, so the steps sum exactly
to the total change. Oracle verdicts are used only as the scenario definition, not as ground truth.
CORRECTED version of l3_decomposition.py. The original wrote the L1 gap into the field
L3_recomputed_gap (line 48 of the original). This version writes L1_gap and L3_gap separately to
results/final/statistics/l3_decomposition_corrected.json and asserts the regression.
The original file and its output are kept unchanged as historical evidence.
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
L3 = {i: L1[i] for i in ids}
# independent L3 construction, not taken from the step chain
for i in disp:
    if ol(i) == "DIFFERENT": L3[i] = "CHANGING"
    elif ol(i) == "EQUIVALENT": L3[i] = "PRESERVING"
L3.pop(sorted(abst)[0], None) if len(abst) == 1 else None
L3_gap = round(gap(L3), 4)
L1_gap = round(gap(L1), 4)
assert L3_gap == out[-1]["gap"], ("chain end != independent L3", L3_gap, out[-1]["gap"])
assert L1_gap == out[0]["gap"]
assert abs(round(sum(s["delta_from_previous"] for s in out[1:]), 4) - round(L3_gap - L1_gap, 4)) <= 0.0002
assert len(L3) == 179, len(L3)
print("L1_gap", L1_gap, "L3_gap", L3_gap, "n_L3", len(L3))
json.dump({"steps": out, "L1_gap": L1_gap, "L3_gap": L3_gap, "n_L3": len(L3)},
          open("results/final/statistics/l3_decomposition_corrected.json", "w"), indent=2)
print("regression checks passed")
