"""Complementarity / utility analysis (PREREGISTRATION.md rules only: UNION, INTERSECTION, FAST_TRACK).
Run from repo root: python reports/recovery/scripts/complementarity.py  -> results/recovery/complementarity.json
Binary predictions only: no PR curve / threshold sweep exists. Cluster bootstrap seed 20261004."""
import json, math, collections, random

SEED, NB = 20261004, 10000
def jl(p): return [json.loads(l) for l in open(p)]

def wilson(k, n, z=1.959964):
    if n == 0: return None
    p = k/n; d = 1+z*z/n; c = p+z*z/(2*n); h = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))
    return [(c-h)/d, (c+h)/d]
def frac(k, n): return {"k": k, "n": n, "value": (k/n if n else None), "wilson95": wilson(k, n)}

def counts(rows, R, T):
    c = collections.Counter()
    for r in rows:
        t = bool(r["truth"]); a = bool(r["pred"][R]); b = bool(r["pred"][T])
        c[("pos" if t else "neg", ("R" if a else "-")+("T" if b else "-"))] += 1
    return c

def analyse(rows, R, T):
    c = counts(rows, R, T); g = lambda t, k: c[(t, k)]
    P = sum(g("pos", k) for k in ("RT", "R-", "-T", "--")); N = len(rows)-P
    ov = {t: {"both": g(t, "RT"), "relic_only": g(t, "R-"), "text_only": g(t, "-T"), "neither": g(t, "--")} for t in ("pos", "neg")}
    ro_tp, ro_fp = g("pos", "R-"), g("neg", "R-")
    def hyb(name, tp, fp):
        return {"tp": tp, "fp": fp, "fn": P-tp, "tn": N-fp, "recall": frac(tp, P), "precision": frac(tp, tp+fp), "fpr": frac(fp, N)}
    rt = g("pos", "RT"), g("neg", "RT")
    textflag = sum(g(t, k) for t in ("pos", "neg") for k in ("RT", "-T"))
    relicflag = sum(g(t, k) for t in ("pos", "neg") for k in ("RT", "R-"))
    acc, wrong = rt[0]+rt[1], rt[1]
    q_pos = g("pos", "-T"); q = g("pos", "-T")+g("neg", "-T")
    return {
      "n": N+P, "n_truth_positive": P, "n_truth_negative": N,
      "overlap_by_truth": ov,
      "relic_only_precision": dict(frac(ro_tp, ro_tp+ro_fp), tp=ro_tp, fp=ro_fp, note=("DENOMINATOR ZERO: RELIC flags nothing text does not" if ro_tp+ro_fp == 0 else "")),
      "relic_flagged_precision": frac(g("pos", "RT")+ro_tp, relicflag),
      "text_flagged_precision": frac(g("pos", "RT")+g("pos", "-T"), textflag),
      "relic_only_true_positives_(H2)": ro_tp,
      "UNION": hyb("U", P-g("pos", "--"), N-g("neg", "--")),
      "INTERSECTION": hyb("I", rt[0], rt[1]),
      "FAST_TRACK": {"text_flagged": textflag, "accepted_without_review": acc,
         "reviews_avoided": frac(acc, textflag), "wrongly_accepted": wrong,
         "wrongly_accepted_share_of_accepted": frac(wrong, acc),
         "wrongly_accepted_share_of_text_flagged": frac(wrong, textflag),
         "review_queue": q, "review_queue_true_changes": q_pos,
         "true_changes_text_misses_(unchanged_by_scheme)": g("pos", "R-")+g("pos", "--")},
    }

def verdicts(a):
    ft = a["FAST_TRACK"]; ra = ft["reviews_avoided"]["value"]
    s1, s2 = ft["wrongly_accepted_share_of_accepted"], ft["wrongly_accepted_share_of_text_flagged"]
    ok = lambda s: (ra is not None and ra >= .30 and s["value"] is not None and s["value"] <= .01)
    return {"H2_rejected_if_relic_only_TP==0": a["relic_only_true_positives_(H2)"] == 0,
            "H4_avoided>=30%": (ra is not None and ra >= .30),
            "H4_pass_wrongly_accepted_as_share_of_accepted<=1%": ok(s1),
            "H4_pass_wrongly_accepted_as_share_of_text_flagged<=1%": ok(s2)}

def boot(rows, key, R, T):
    """Cluster bootstrap (resample clusters with replacement) of key stats; percentile 95% CI."""
    cl = collections.defaultdict(lambda: [0]*6)
    for r in rows:
        v = cl[r[key]]; t = bool(r["truth"]); a = bool(r["pred"][R]); b = bool(r["pred"][T])
        v[0] += a and not b and t; v[1] += a and not b and not t   # relic-only tp / fp
        v[2] += a and b; v[3] += b; v[4] += a and b and not t; v[5] += 1
    ks = list(cl); rnd = random.Random(SEED); res = collections.defaultdict(list)
    for _ in range(NB):
        s = [0]*6
        for k in (rnd.choice(ks) for _ in ks):
            for i in range(6): s[i] += cl[k][i]
        if s[0]+s[1]: res["relic_only_precision"].append(s[0]/(s[0]+s[1]))
        if s[3]: res["reviews_avoided"].append(s[2]/s[3]); res["wrongly_accepted_share_of_text_flagged"].append(s[4]/s[3])
        if s[2]: res["wrongly_accepted_share_of_accepted"].append(s[4]/s[2])
    pct = lambda x: ([sorted(x)[int(.025*len(x))], sorted(x)[int(.975*len(x))-1]] if x else None)
    return {"cluster_key": key, "n_clusters": len(ks), "resamples": NB, "seed": SEED,
            **{k: {"ci95": pct(v), "n_valid_resamples": len(v)} for k, v in res.items()}}

def split(rows, key, R, T, dets):
    d = collections.defaultdict(list)
    for r in rows: d[r[key]].append(r)
    out = {}
    for k, v in sorted(d.items()):
        c = counts(v, R, T); pos = [r for r in v if r["truth"]]
        out[k] = {"n": len(v), "n_truth_positive": len(pos), "relic_flags": sum(r["pred"][R] for r in v),
                  "text_flags": sum(r["pred"][T] for r in v),
                  "pos_both": c[("pos", "RT")], "pos_relic_only": c[("pos", "R-")], "pos_text_only": c[("pos", "-T")], "pos_neither": c[("pos", "--")],
                  "neg_both(FP both)": c[("neg", "RT")], "neg_relic_only": c[("neg", "R-")], "neg_text_only": c[("neg", "-T")],
                  "relic_recall": frac(c[("pos", "RT")]+c[("pos", "R-")], len(pos)),
                  "relic_precision": frac(c[("pos", "RT")]+c[("pos", "R-")], sum(r["pred"][R] for r in v))}
    return out

def easiness(rows, R, dets):
    """Among true changes: how many OTHER detectors flag it; RELIC-caught vs RELIC-missed (exploratory)."""
    o = [d for d in dets if d != R]
    f = lambda grp: {"n": len(grp), "mean_other_detectors_flagging": (sum(sum(r["pred"][d] for d in o) for r in grp)/len(grp) if grp else None),
                     "n_other_detectors": len(o)}
    pos = [r for r in rows if r["truth"]]
    caught = [r for r in pos if r["pred"][R]]; missed = [r for r in pos if not r["pred"][R]]
    nobody_else = [r for r in caught if not any(r["pred"][d] for d in o)]
    return {"relic_caught": f(caught), "relic_missed": f(missed), "caught_by_relic_but_by_no_other_detector": len(nobody_else),
            "relic_caught_also_flagged_by_every_other_detector": sum(all(r["pred"][d] for d in o) for r in caught)}

out = {"note": "Binary predictions only; no PR curve/operating-point sweep computable. Only pre-registered hybrids UNION/INTERSECTION/FAST_TRACK are in the confirmatory-style tables.",
       "exploratory_items_added": ["per-category/operator splits", "mean-other-detectors easiness", "reverse review-queue stats", "sensitivity baselines (counted as same 3 rules on extra baselines)", "cluster bootstrap CIs (descriptive)"]}

# ---------- SemBench
cases = {c["id"]: c for c in jl("benchmarks/sembench/cases.jsonl")}
sb = jl("results/sembench/predictions.jsonl")
for r in sb:
    c = cases[r["id"]]
    r["identical"] = c["original_sha256"] == c["transformed_sha256"]
    r["disagrees"] = c["oracle_agrees_with_expected"] is False
    r["abstains"] = c["validation_status"] == "ORACLE_ABSTAINS"
    assert r["truth"] == (c["expected_outcome"] != "PRESERVING"), r["id"]
pops = {"ALL_180": sb,
        "EXCL_25_IDENTICAL": [r for r in sb if not r["identical"]],
        "EXCL_15_NOOP_CHANGING_ONLY": [r for r in sb if not (r["identical"] and r["truth"])],
        "CLEAN_CORE": [r for r in sb if not r["identical"] and not r["disagrees"] and not r["abstains"]]}
assert [len(v) for v in pops.values()] == [180, 155, 165, len(pops["CLEAN_CORE"])]
sdets = sorted(sb[0]["pred"])
out["sembench"] = {"population_sizes": {k: len(v) for k, v in pops.items()}, "populations": {}}
for pn, rows in pops.items():
    e = {}
    for T in ("normalized_text_B", "normalized_text_A", "textdiff"):
        a = analyse(rows, "relic_v2", T); a["verdicts"] = verdicts(a)
        if T == "normalized_text_B": a["bootstrap_by_base_id"] = boot(rows, "base_id", "relic_v2", T)
        e[T + ("  [PRIMARY]" if T == "normalized_text_B" else "  [sensitivity]")] = a
    out["sembench"]["populations"][pn] = e
rows = pops["ALL_180"]
out["sembench"]["per_category_vs_normalized_text_B_ALL_180_(exploratory)"] = split(rows, "category", "relic_v2", "normalized_text_B", sdets)
out["sembench"]["easiness_ALL_180_(exploratory)"] = easiness(rows, "relic_v2", sdets)
out["sembench"]["easiness_CLEAN_CORE_(exploratory)"] = easiness(pops["CLEAN_CORE"], "relic_v2", sdets)

# ---------- External
ex = [r for r in jl("results/external/predictions.jsonl") if r["status"] == "EVALUABLE"]
assert len(ex) == 824
edets = sorted(ex[0]["pred"]); TP = "textdiff_ignore_job_parameters"
out["external"] = {"n": len(ex), "note": "External run was not blind; oracle same-author. Only 6 repos: repo-cluster bootstrap is very coarse.", "pooled": {}, "per_repo": {}}
for T in (TP, "textdiff"):
    a = analyse(ex, "relic_v2", T); a["verdicts"] = verdicts(a)
    if T == TP: a["bootstrap_by_repo"] = boot(ex, "repo", "relic_v2", T)
    out["external"]["pooled"][T + ("  [PRIMARY]" if T == TP else "  [sensitivity]")] = a
h3 = {}
rp = analyse(ex, "relic_v2", TP)["relic_flagged_precision"]
h3["pooled"] = {"relic_flagged": rp["n"], "precision": rp["value"], "wilson95": rp["wilson95"], "rejected": rp["wilson95"][0] < .90}
byrepo = collections.defaultdict(list)
for r in ex: byrepo[r["repo"]].append(r)
for k, v in sorted(byrepo.items()):
    a = analyse(v, "relic_v2", TP); a["verdicts"] = verdicts(a); out["external"]["per_repo"][k] = a
    p = a["relic_flagged_precision"]
    h3[k] = {"relic_flagged": p["n"], "precision": p["value"], "wilson95": p["wilson95"],
             "applies_(>=20_flagged)": p["n"] >= 20, "rejected": (p["wilson95"][0] < .90) if p["n"] >= 20 else None}
out["external"]["H3_triage_precision_(vs_relic_v2_flagged_set)"] = dict(h3, overall_rejected=any(x.get("rejected") for x in h3.values()))
out["external"]["per_failure_category_(exploratory)"] = split(ex, "failure_category", "relic_v2", TP, edets)
out["external"]["per_operator_(exploratory)"] = split(ex, "operator", "relic_v2", TP, edets)
out["external"]["per_contract_type_(exploratory)"] = split(ex, "contract_type", "relic_v2", TP, edets)
out["external"]["easiness_(exploratory)"] = easiness(ex, "relic_v2", edets)
json.dump(out, open("results/recovery/complementarity.json", "w"), indent=1, default=str)
print("ok")
