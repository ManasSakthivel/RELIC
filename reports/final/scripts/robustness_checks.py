"""Robustness checks for the four label sets (L0-L3, definitions as in complementarity_checks.py).
1. MCC of every detector on every label set (no intervals; point estimates only).
2. Exact cluster-level paired randomisation test for MCC(relic_v2) - MCC(normalized_text_B):
   for each of the 16 base_id clusters, the two detectors' predictions are swapped or not (2^16 assignments).
   Two-sided p = share of assignments with |delta| >= |observed delta|.
Writes results/final/statistics/robustness_checks.json
"""
import json, os, math, itertools
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
L3 = {i: (("CHANGING" if ol(i) == "DIFFERENT" else "PRESERVING" if ol(i) == "EQUIVALENT" else None) if i in unres else L1[i]) for i in ids}
L3 = {i: v for i, v in L3.items() if v is not None}
SETS = {"L0": L0, "L1": L1, "L2": L2, "L3": L3}

def mcc(lab, flag):
    tp = sum(1 for i in lab if lab[i] == "CHANGING" and flag[i]); tn = sum(1 for i in lab if lab[i] == "PRESERVING" and not flag[i])
    fp = sum(1 for i in lab if lab[i] == "PRESERVING" and flag[i]); fn = sum(1 for i in lab if lab[i] == "CHANGING" and not flag[i])
    den = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    return 0.0 if den == 0 else (tp*tn - fp*fn) / den

detectors = sorted(P[ids[0]].keys())
out = {"mcc": {}, "cluster_swap": {}}
for d in detectors:
    out["mcc"][d] = {k: round(mcc(lab, {i: P[i][d] for i in ids}), 4) for k, lab in SETS.items()}
print("MCC by detector:")
for d in detectors: print(f"  {d:28s}", out["mcc"][d])

A, B = "relic_v2", "normalized_text_B"
clusters = sorted({cases[i]["base_id"] for i in ids})
assert len(clusters) == 16, len(clusters)
out["cluster_swap"]["n_clusters"] = len(clusters)
for k, lab in SETS.items():
    members = {c: [i for i in lab if cases[i]["base_id"] == c] for c in clusters}
    def delta(swap):
        fa = {}; fb = {}
        for c, bit in zip(clusters, swap):
            for i in members[c]:
                a, b = P[i][A], P[i][B]
                fa[i], fb[i] = (b, a) if bit else (a, b)
        return mcc(lab, fa) - mcc(lab, fb)
    obs = delta((0,)*16)
    cnt = 0; total = 0
    for swap in itertools.product((0, 1), repeat=16):
        total += 1
        if abs(delta(swap)) >= abs(obs) - 1e-12: cnt += 1
    out["cluster_swap"][k] = {"observed_delta": round(obs, 4), "p_two_sided_exact": round(cnt/total, 5), "assignments": total}
    print(k, "observed dMCC", round(obs, 4), "exact cluster-swap p", round(cnt/total, 5))
json.dump(out, open("results/final/statistics/robustness_checks.json", "w"), indent=2)
print("written")
