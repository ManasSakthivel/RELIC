"""RQ2 checks under each label set: RELIC-only true positives, and whether every RELIC flag is a text flag.
Writes results/final/statistics/complementarity_checks.json
"""
import json, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
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
out = {}
for name, lab in [("L0", L0), ("L1", L1), ("L2", L2), ("L3", L3)]:
    rel_only_tp = sorted(i for i in lab if lab[i] == "CHANGING" and P[i]["relic_v2"] and not P[i]["normalized_text_B"])
    flags_not_in_text = sorted(i for i in lab if P[i]["relic_v2"] and not P[i]["normalized_text_B"])
    out[name] = {"n": len(lab), "relic_only_true_positives": rel_only_tp, "relic_flags_not_text_flags": flags_not_in_text,
                 "text_recall": round(sum(1 for i in lab if lab[i] == "CHANGING" and P[i]["normalized_text_B"]) / max(1, sum(1 for i in lab if lab[i] == "CHANGING")), 4)}
    print(name, "RELIC-only TP:", len(rel_only_tp), "| RELIC flags not text flags:", len(flags_not_in_text), "| text recall:", out[name]["text_recall"])
json.dump(out, open("results/final/statistics/complementarity_checks.json", "w"), indent=2)
