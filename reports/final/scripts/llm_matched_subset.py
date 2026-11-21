# NOTE (final audit): the bootstrap intervals in this script use Python random resampling and are SUPERSEDED.
# Authoritative intervals: results/final_go/bootstrap_original_method.json (reports/final_go/bootstrap_reproduction.py).
# Exact p-values in this script are unaffected.
"""Matched-subset comparison: LLM (gpt-oss-120b, Groq) vs RELIC V2 vs normalized text B on the
exact pairs that have a parsed LLM verdict in the frozen snapshot. Exploratory, partial coverage.
Inputs : results/final/llm/matched_subset_v1/frozen_raw_snapshot.jsonl (frozen copy of the raw run)
         results/sembench/predictions.jsonl, benchmarks/sembench/cases.jsonl (frozen RELIC and text predictions)
Outputs: results/final/llm/matched_subset_v1/manifest.json, matched_subset_scores.json
"""
import json, math, hashlib, itertools, random, os, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
D = "results/final/llm/matched_subset_v1"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

llm = {}
for l in open(f"{D}/frozen_raw_snapshot.jsonl"):
    r = json.loads(l); assert r["id"] not in llm; llm[r["id"]] = r
assert all(r["verdict"] in ("CHANGING", "PRESERVING") for r in llm.values())
SUB = sorted(llm)
assert len(SUB) == 155

cases = {json.loads(l)["id"]: json.loads(l) for l in open("benchmarks/sembench/cases.jsonl")}
P = {json.loads(l)["id"]: json.loads(l)["pred"] for l in open("results/sembench/predictions.jsonl")}
missing_rel = [i for i in SUB if i not in P]
assert not missing_rel, missing_rel
ALL = sorted(cases)
ident = {i for i in ALL if cases[i]["original_sha256"] == cases[i]["transformed_sha256"]}
unres = {i for i in ALL if cases[i]["validation_status"] in ("ORACLE_DISAGREES", "ORACLE_ABSTAINS") and i not in ident}
def ol(i):
    v = cases[i]["oracle_verdict"]; return v.get("label") if isinstance(v, dict) else v
L0 = {i: cases[i]["expected_outcome"] for i in ALL}
L1 = {i: ("PRESERVING" if (i in ident and L0[i] == "CHANGING") else L0[i]) for i in ALL}
L2 = {i: L1[i] for i in ALL if i not in unres}
L3 = {}
for i in ALL:
    if i in unres:
        if ol(i) == "DIFFERENT": L3[i] = "CHANGING"
        elif ol(i) == "EQUIVALENT": L3[i] = "PRESERVING"
    else: L3[i] = L1[i]
SETS = {"L0": L0, "L1": L1, "L2": L2, "L3": L3}

def flags(name):
    if name == "LLM": return {i: llm[i]["verdict"] == "CHANGING" for i in SUB}
    return {i: bool(P[i][name]) for i in SUB}
F = {"LLM": flags("LLM"), "RELIC_V2": flags("relic_v2"), "TEXT_B": flags("normalized_text_B")}

def confusion(lab, f, ids):
    c = dict(tp=0, fp=0, tn=0, fn=0)
    for i in ids:
        y = lab[i] == "CHANGING"; p = f[i]
        c["tp" if y and p else "fn" if y else "fp" if p else "tn"] += 1
    return c
def metrics(c):
    tp, fp, tn, fn = c["tp"], c["fp"], c["tn"], c["fn"]
    d = lambda a, b: a / b if b else float("nan")
    den = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    return dict(c, n=tp+fp+tn+fn, precision=d(tp, tp+fp), recall=d(tp, tp+fn), specificity=d(tn, tn+fp),
                f1=d(2*tp, 2*tp+fp+fn), mcc=(tp*tn-fp*fn)/den if den else 0.0)

out = {"subset_n": len(SUB), "clusters_in_subset": len({cases[i]["base_id"] for i in SUB}),
       "missing_from_llm": [i for i in ALL if i not in llm], "metrics": {}, "paired": {}}
for ln, lab in SETS.items():
    ids = [i for i in SUB if i in lab]          # abstention 172 excluded from L3 by construction
    out["metrics"][ln] = {s: metrics(confusion(lab, F[s], ids)) for s in F}
    out["metrics"][ln]["denominator"] = len(ids)
    out["metrics"][ln]["unlabelled_in_subset"] = len(SUB) - len(ids)
    # cluster-level paired inference (clusters = base_id, present in subset)
    cl = sorted({cases[i]["base_id"] for i in ids})
    members = {c: [i for i in ids if cases[i]["base_id"] == c] for c in cl}
    for a, b in [("LLM", "RELIC_V2"), ("LLM", "TEXT_B"), ("RELIC_V2", "TEXT_B")]:
        def dm(sel):
            fa = {}; fb = {}
            for c, bit in zip(cl, sel):
                for i in members[c]:
                    x, y = F[a][i], F[b][i]
                    fa[i], fb[i] = (y, x) if bit else (x, y)
            return metrics(confusion(lab, fa, ids))["mcc"] - metrics(confusion(lab, fb, ids))["mcc"]
        obs = dm((0,)*len(cl))
        # exact cluster-swap test (2^k) when k <= 16
        k = len(cl); cnt = tot = 0
        for sel in itertools.product((0, 1), repeat=k):
            tot += 1
            if abs(dm(sel)) >= abs(obs) - 1e-12: cnt += 1
        # cluster bootstrap CI (10,000, seed 20261004)
        rng = random.Random(20261004); bs = []
        for _ in range(10000):
            pick = [rng.randrange(k) for _ in range(k)]
            # duplicated clusters are kept as repeated units (standard cluster bootstrap)
            ids_b = [i for c_idx in pick for i in members[cl[c_idx]]]
            bs.append(metrics(confusion(lab, F[a], ids_b))["mcc"] - metrics(confusion(lab, F[b], ids_b))["mcc"])
        bs.sort()
        out["paired"].setdefault(ln, {})[f"{a}_minus_{b}"] = dict(
            delta_mcc=round(obs, 4), ci95=[round(bs[249], 4), round(bs[9749], 4)],
            p_exact_cluster_swap=round(cnt/tot, 5), n_clusters=k, n_items=len(ids))
json.dump(out, open(f"{D}/matched_subset_scores.json", "w"), indent=2, default=float)
man = {"subset": "exact pairs with a parsed LLM verdict in the frozen snapshot",
       "subset_ids": SUB, "n": len(SUB),
       "missing_from_llm_run": out["missing_from_llm"],
       "llm": {"provider": "Groq OpenAI-compatible endpoint", "model": "openai/gpt-oss-120b", "temperature": 0,
               "max_completion_tokens": 4000, "one_request_per_pair": True, "both_files_in_prompt": True,
               "runner": "reports/final/scripts/llm_baseline_groq.py", "runner_sha256": sha("reports/final/scripts/llm_baseline_groq.py"),
               "reasoning_setting": "not set by request (provider default); max_completion_tokens 4000 chosen after a 300-token attempt truncated outputs (superseded file kept)"},
       "frozen_raw_sha256": sha(f"{D}/frozen_raw_snapshot.jsonl"),
       "relic_and_text_source": {"file": "results/sembench/predictions.jsonl", "sha256": sha("results/sembench/predictions.jsonl")},
       "label_source": {"file": "benchmarks/sembench/cases.jsonl", "sha256": sha("benchmarks/sembench/cases.jsonl")},
       "selection_note": "Pairs were processed in ID order under a rate limit; the 25 missing pairs are not a random sample. Subset is not claimed representative."}
json.dump(man, open(f"{D}/manifest.json", "w"), indent=2)
print("subset", len(SUB), "clusters", out["clusters_in_subset"], "missing", len(out["missing_from_llm"]))
print("base programs with no LLM pair:", sorted({cases[i]["base_id"] for i in ALL} - {cases[i]["base_id"] for i in SUB}))
print("missing pair IDs:", out["missing_from_llm"])
for ln in SETS:
    m = out["metrics"][ln]
    print(ln, "denominator", m["denominator"])
    for s in ("LLM", "RELIC_V2", "TEXT_B"):
        x = m[s]; print(f"  {s:9s} TP{x['tp']} FP{x['fp']} TN{x['tn']} FN{x['fn']} P{x['precision']:.3f} R{x['recall']:.3f} Spec{x['specificity']:.3f} F1{x['f1']:.3f} MCC{x['mcc']:.3f}")
    for k, v in out["paired"][ln].items(): print("  ", k, v)
