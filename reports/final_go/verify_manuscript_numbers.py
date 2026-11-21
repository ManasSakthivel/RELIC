"""Independent check of headline numbers in paper/RELIC_V2_PUBLICATION_FINAL/main.tex.
Recomputes point estimates from saved predictions and checks stored bootstrap/exact-test outputs.
Prints PASS/FAIL per item and exits non-zero on any failure. Read-only.
"""
import json, math, os, sys, hashlib
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
fails = []
def check(name, got, want, tol=5e-4):
    ok = (abs(got - want) <= tol) if isinstance(want, float) else (got == want)
    print(("PASS " if ok else "FAIL ") + f"{name}: got {got} want {want}")
    if not ok: fails.append(name)

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
L3 = {i: (("CHANGING" if ol(i) == "DIFFERENT" else "PRESERVING") if i in unres and ol(i) in ("DIFFERENT", "EQUIVALENT") else L1[i]) for i in ids if not (i in unres and ol(i) not in ("DIFFERENT", "EQUIVALENT"))}
def mcc(lab, det):
    tp = sum(1 for i in lab if lab[i] == "CHANGING" and P[i][det]); tn = sum(1 for i in lab if lab[i] == "PRESERVING" and not P[i][det])
    fp = sum(1 for i in lab if lab[i] == "PRESERVING" and P[i][det]); fn = sum(1 for i in lab if lab[i] == "CHANGING" and not P[i][det])
    den = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)); return (tp*tn-fp*fn)/den if den else 0.0
print("denominators:", {k: len(v) for k, v in {"L0": L0, "L1": L1, "L2": L2, "L3": L3}.items()})
check("L0 n", len(L0), 180); check("L2 n", len(L2), 166); check("L3 n", len(L3), 179)
check("unresolved count", len(unres), 14); check("byte-identical count", len(ident), 25)
for name, lab, rel, txt, dlt in [("L0", L0, 0.324, 0.525, -0.201), ("L1", L1, 0.394, 0.731, -0.336),
                                 ("L2", L2, 0.488, 0.738, -0.250), ("L3", L3, 0.503, 0.673, -0.170)]:
    r, t = mcc(lab, "relic_v2"), mcc(lab, "normalized_text_B")
    check(f"{name} RELIC MCC", round(r, 3), rel); check(f"{name} text B MCC", round(t, 3), txt)
    check(f"{name} delta MCC", round(r - t, 3), dlt, tol=6e-4)

B = json.load(open("results/final_go/bootstrap_original_method.json"))
check("bootstrap reproduces published L0 check", B["check_vs_published_L0"]["match"], True)
pub = json.load(open("results/recovery/stats_reanalysis.json"))["hypotheses"]["H1"]["diff_mcc_ci95"]
check("L0 delta CI lower (manuscript -0.299)", round(B["L0"]["delta_relic_minus_textB"]["ci95"][0], 3), -0.299)
check("L0 delta CI upper (manuscript -0.102)", round(B["L0"]["delta_relic_minus_textB"]["ci95"][1], 3), -0.102)
check("L3 delta CI lower (manuscript -0.344)", round(B["L3"]["delta_relic_minus_textB"]["ci95"][0], 3), -0.344)

R = json.load(open("results/final/statistics/robustness_checks.json"))["cluster_swap"]
for L, p in [("L0", 0.015), ("L1", 0.002), ("L2", 0.010), ("L3", 0.089)]:
    check(f"{L} exact cluster-swap p", round(R[L]["p_two_sided_exact"], 3), p)

S = json.load(open("results/final/llm/matched_subset_v1/matched_subset_scores.json"))
M = json.load(open("results/final/llm/matched_subset_v1/manifest.json"))
check("subset size", S["subset_n"], 155); check("subset clusters", S["clusters_in_subset"], 12)
check("missing from LLM", len(M["missing_from_llm_run"]), 25)
check("frozen LLM sha", hashlib.sha256(open("results/final/llm/matched_subset_v1/frozen_raw_snapshot.jsonl", "rb").read()).hexdigest(), M["frozen_raw_sha256"])
check("L1 LLM MCC", round(S["metrics"]["L1"]["LLM"]["mcc"], 3), 0.870)
check("L3 LLM-vs-text p", round(S["paired"]["L3"]["LLM_minus_TEXT_B"]["p_exact_cluster_swap"], 3), 0.031)
check("L3 LLM-vs-RELIC p", round(S["paired"]["L3"]["LLM_minus_RELIC_V2"]["p_exact_cluster_swap"], 3), 0.132)
for L in ("L0", "L1", "L2", "L3"):
    m = B["matched_subset"][L]
    print("subset", L, "LLM-RELIC CI", m["LLM_minus_relic_v2"], "LLM-text CI", m["LLM_minus_normalized_text_B"])
print("\nFAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
