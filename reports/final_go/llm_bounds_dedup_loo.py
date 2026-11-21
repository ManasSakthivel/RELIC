"""Worst/best-case bounds for the LLM subset on all 180 pairs (unanswered pairs scored as wrong / right),
deduplicated L1 gap (one copy per byte-identical (original, transformed) pair), and leave-one-program-out L1 gap.
Writes results/final_go/llm_bounds_dedup_loo.json
"""
import json, math, os, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
cases = {json.loads(l)["id"]: json.loads(l) for l in open("benchmarks/sembench/cases.jsonl")}
P = {json.loads(l)["id"]: json.loads(l)["pred"] for l in open("results/sembench/predictions.jsonl")}
M = json.load(open("results/final/llm/matched_subset_v1/manifest.json"))
llm = {json.loads(l)["id"]: json.loads(l)["verdict"] for l in open("results/final/llm/matched_subset_v1/frozen_raw_snapshot.jsonl")}
ids = sorted(cases)
ident = {i for i in ids if cases[i]["original_sha256"] == cases[i]["transformed_sha256"]}
L1 = {i: ("PRESERVING" if (i in ident and cases[i]["expected_outcome"] == "CHANGING") else cases[i]["expected_outcome"]) for i in ids}
def mcc(lab, flag, sub):
    tp = sum(1 for i in sub if lab[i] == "CHANGING" and flag[i]); tn = sum(1 for i in sub if lab[i] == "PRESERVING" and not flag[i])
    fp = sum(1 for i in sub if lab[i] == "PRESERVING" and flag[i]); fn = sum(1 for i in sub if lab[i] == "CHANGING" and not flag[i])
    d = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)); return (tp*tn-fp*fn)/d if d else 0.0
miss = M["missing_from_llm_run"]
worst = {i: (llm[i] == "CHANGING") if i in llm else (L1[i] != "CHANGING") for i in ids}
best = {i: (llm[i] == "CHANGING") if i in llm else (L1[i] == "CHANGING") for i in ids}
txt = {i: bool(P[i]["normalized_text_B"]) for i in ids}; rel = {i: bool(P[i]["relic_v2"]) for i in ids}
out = {"llm_worst_L1": round(mcc(L1, worst, ids), 3), "llm_best_L1": round(mcc(L1, best, ids), 3),
       "text_B_L1_180": round(mcc(L1, txt, ids), 3), "relic_L1_180": round(mcc(L1, rel, ids), 3)}
seen, uniq = set(), []
for i in ids:
    k = (cases[i]["original_sha256"], cases[i]["transformed_sha256"])
    if k not in seen: seen.add(k); uniq.append(i)
out["dedup_n"] = len(uniq)
out["dedup_L1_gap"] = round(mcc(L1, rel, uniq) - mcc(L1, txt, uniq), 3)
progs = sorted({cases[i]["base_id"] for i in ids})
loo = {p: round(mcc(L1, rel, [i for i in ids if cases[i]["base_id"] != p]) - mcc(L1, txt, [i for i in ids if cases[i]["base_id"] != p]), 3) for p in progs}
out["leave_one_program_out_L1"] = {"min": min(loo.values()), "max": max(loo.values()), "by_program": loo}
print(json.dumps({k: v for k, v in out.items() if k != "leave_one_program_out_L1"}, indent=1))
print("leave-one-program-out L1 gap: min", out["leave_one_program_out_L1"]["min"], "max", out["leave_one_program_out_L1"]["max"])
json.dump(out, open("results/final_go/llm_bounds_dedup_loo.json", "w"), indent=2)
