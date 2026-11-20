"""Statistical reanalysis of RELIC V2 vs text baselines (recovery sprint).

Reads only committed files:
  results/sembench/predictions.jsonl, benchmarks/sembench/cases.jsonl,
  results/external/predictions.jsonl (status == EVALUABLE),
  published results/sembench/{metrics,paired_tests}.json, results/external/metrics.json
Writes results/recovery/stats_reanalysis.json. No hybrids (owned by the complementarity analysis).
Predictions are binary: there is no score, so no PR curve / threshold analysis is possible.
Run from repo root:  python reports/recovery/scripts/stats_reanalysis.py
"""
import json, math, random, collections, hashlib
from pathlib import Path
import numpy as np
from scipy.stats import binomtest

SEED, REPS, Z = 20261004, 10_000, 1.959963984540054
OUT = Path("results/recovery/stats_reanalysis.json")
SB_BASE = ["normalized_text_B", "normalized_text_A", "textdiff_ignore_job_parameters", "textdiff", "raw_text"]
EX_BASE = ["textdiff_ignore_job_parameters", "textdiff"]   # first = pre-registered primary


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def r4(x, k=4):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), k)


def wilson(k, n):
    if n == 0:
        return None
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def vec(tp, fp, fn, tn):
    """Vectorised metrics on float arrays; nan when undefined."""
    with np.errstate(divide="ignore", invalid="ignore"):
        rec, spec = tp / (tp + fn), tn / (tn + fp)
        den = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
        return {"mcc": (tp * tn - fp * fn) / den, "f1": 2 * tp / (2 * tp + fp + fn),
                "balanced_accuracy": (rec + spec) / 2, "accuracy": (tp + tn) / (tp + fp + fn + tn)}


def arrays(rows, det):
    t = np.array([bool(r["truth"]) for r in rows])
    f = np.array([bool(r["pred"][det]) for r in rows])   # asserted non-None below
    return t, f


def confusion(rows, det):
    t, f = arrays(rows, det)
    tp, fp, fn, tn = int((t & f).sum()), int((~t & f).sum()), int((t & ~f).sum()), int((~t & ~f).sum())
    ratio = lambda a, b: None if b == 0 else a / b
    m = {k: r4(v) for k, v in vec(*(np.float64(x) for x in (tp, fp, fn, tn))).items()}
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": len(rows),
            "precision": r4(ratio(tp, tp + fp)), "recall": r4(ratio(tp, tp + fn)),
            "specificity": r4(ratio(tn, tn + fp)), **m,
            "precision_wilson95": wilson(tp, tp + fp), "recall_wilson95": wilson(tp, tp + fn),
            "specificity_wilson95": wilson(tn, tn + fp)}


class Boot:
    """Cluster bootstrap identical in method to relic_eval/sembench_eval.Bootstrap:
    sorted clusters, default_rng(SEED).integers(0,K,(REPS,K)), percentile 95%, nan reps dropped,
    one shared index matrix so paired differences are paired."""

    def __init__(self, rows, key):
        cl = sorted({r[key] for r in rows})
        self.K = len(cl)
        pos = {c: i for i, c in enumerate(cl)}
        self.cidx = np.array([pos[r[key]] for r in rows], dtype=np.int64)
        self.idx = np.random.default_rng(SEED).integers(0, self.K, size=(REPS, self.K))
        self.rows = rows

    def _b(self, det):
        t, f = arrays(self.rows, det)
        cc = [np.bincount(self.cidx[m], minlength=self.K) for m in (t & f, ~t & f, t & ~f, ~t & ~f)]
        return vec(*(c[self.idx].sum(axis=1).astype(float) for c in cc))

    @staticmethod
    def pct(x):
        ok = x[~np.isnan(x)]
        if not len(ok):
            return {"ci95": None, "n_undefined_reps": int(len(x))}
        lo, hi = np.percentile(ok, [2.5, 97.5])
        return {"ci95": [r4(lo), r4(hi)], "n_undefined_reps": int(len(x) - len(ok))}

    def single(self, det):
        b = self._b(det)
        return {m: self.pct(b[m]) for m in ("mcc", "f1", "balanced_accuracy")}

    def pair(self, a, b_):
        ba, bb = self._b(a), self._b(b_)
        return {m: self.pct(ba[m] - bb[m]) for m in ("mcc", "f1", "balanced_accuracy")}


def mcnemar(b, c):
    return 1.0 if b + c == 0 else float(binomtest(min(b, c), b + c, 0.5).pvalue)


def signflip(d):
    """Cluster-level exact sign-flip test of sum(b_k - c_k) = 0 (exact enumeration if <=20 non-zero
    clusters, else 100k seeded Monte Carlo). Robust to within-cluster correlation."""
    d = np.array([x for x in d if x != 0], dtype=float)
    if len(d) == 0:
        return 1.0, "no_discordant_clusters"
    obs = abs(d.sum())
    if len(d) <= 20:
        signs = ((np.arange(2 ** len(d))[:, None] >> np.arange(len(d))) & 1) * 2 - 1
        return float((np.abs(signs @ d) >= obs - 1e-9).mean()), f"exact_2^{len(d)}"
    s = np.random.default_rng(SEED).choice([-1.0, 1.0], size=(100_000, len(d)))
    return float(((np.abs(s @ d) >= obs - 1e-9).sum() + 1) / 100_001), f"monte_carlo_100000_{len(d)}"


def holm_distinct(sigs, ps):
    """Holm over distinct tests: entries sharing a signature are one test (same cases, same p)."""
    first = {}
    for s, p in zip(sigs, ps):
        assert abs(first.setdefault(s, p) - p) < 1e-9, "same signature, different p"
    keys = list(first)
    adj = dict(zip(keys, holm([first[k] for k in keys])))
    return [adj[s] for s in sigs], len(keys)


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def compare(rows, a, b, key, boot=None):
    """Paired comparison a vs b: McNemar on per-case correctness, cluster sign-flip, bootstrap deltas."""
    t, fa = arrays(rows, a)
    _, fb = arrays(rows, b)
    oka, okb = fa == t, fb == t
    bw, cw = oka & ~okb, ~oka & okb
    boot = boot or Boot(rows, key)
    dk = np.bincount(boot.cidx[bw], minlength=boot.K) - np.bincount(boot.cidx[cw], minlength=boot.K)
    sp, sm = signflip(dk)
    ids = np.array([r.get("id") or r["mutation_id"] for r in rows])
    # same discordant case sets (either orientation) == the same test; used to deduplicate Holm families
    sig = "NULL" if not (bw.any() or cw.any()) else \
        hashlib.sha1(repr(sorted([sorted(ids[bw].tolist()), sorted(ids[cw].tolist())])).encode()).hexdigest()[:12]
    raw = lambda f: vec(*(np.float64(x) for x in ((t & f).sum(), (~t & f).sum(), (t & ~f).sum(), (~t & ~f).sum())))
    pa, pb = raw(fa), raw(fb)   # unrounded, as the repo does, before differencing
    return {"a": a, "b": b, "n": len(rows), "cluster_key": key, "n_clusters": boot.K,
            "a_right_b_wrong": int(bw.sum()), "a_wrong_b_right": int(cw.sum()),
            "a_right_b_wrong_on_changing": int((bw & t).sum()), "a_wrong_b_right_on_changing": int((cw & t).sum()),
            "a_right_b_wrong_on_preserving": int((bw & ~t).sum()), "a_wrong_b_right_on_preserving": int((cw & ~t).sum()),
            "relic_only_tp": int((fa & ~fb & t).sum()), "baseline_only_tp": int((~fa & fb & t).sum()),
            "p_mcnemar_exact": mcnemar(int(bw.sum()), int(cw.sum())),
            "p_cluster_signflip": sp, "signflip_method": sm, "_sig": sig,
            "diff_point": {m: r4(pa[m] - pb[m])
                           for m in ("mcc", "f1", "balanced_accuracy")},
            "diff_boot": boot.pair(a, b)}


def block(rows, key, baselines, detectors=None):
    boot = Boot(rows, key)
    dets = detectors or ["relic_v2"] + baselines
    return {"n": len(rows), "n_changing": int(sum(bool(r["truth"]) for r in rows)), "n_clusters": boot.K,
            "detectors": {d: {**confusion(rows, d), "boot": boot.single(d)} for d in dets},
            "comparisons": {b: compare(rows, "relic_v2", b, key, boot) for b in baselines}}


def main():
    out = {"meta": {"seed": SEED, "reps": REPS, "interval": "percentile 95%", "wilson_z": Z,
                    "note": "binary predictions only: no PR curve, ROC, AUC or threshold analysis is computable"}}
    # ---------------- SemBench
    cases = {c["id"]: c for c in jl("benchmarks/sembench/cases.jsonl")}
    sb = jl("results/sembench/predictions.jsonl")
    assert len(sb) == 180 and all(v is not None for r in sb for v in r["pred"].values()), "None prediction"
    for r in sb:
        c = cases[r["id"]]
        assert bool(r["truth"]) == (c["expected_outcome"] == "CHANGING")
        r["identical"] = c["original_sha256"] == c["transformed_sha256"]
        r["disagree"] = c["oracle_agrees_with_expected"] is False      # canonical definition (29 incl. abstain)
        r["abstain"] = c["validation_status"] == "ORACLE_ABSTAINS"
    ident = {r["id"] for r in sb if r["identical"]}
    nonid_dis14 = {r["id"] for r in sb if r["disagree"] and not r["identical"]}
    nonid_dis13 = {r["id"] for r in sb if r["validation_status"] == "ORACLE_DISAGREES" and not r["identical"]}
    pops = {
        "ALL_180": sb,
        "EXCL_25_IDENTICAL": [r for r in sb if not r["identical"]],
        "EXCL_15_NOOP_CHANGING_ONLY": [r for r in sb if not (r["identical"] and r["truth"])],
        "CLEAN_CORE": [r for r in sb if not r["identical"] and not r["disagree"] and not r["abstain"]],
        "SENS_EXCL_14_NONIDENT_DISAGREE_INCL_ABSTAIN": [r for r in sb if r["id"] not in nonid_dis14],
        "SENS_EXCL_13_NONIDENT_ORACLE_DISAGREES": [r for r in sb if r["id"] not in nonid_dis13],
    }
    out["sembench"] = {"n_clusters_base_id": len({r["base_id"] for r in sb}),
                       "flags_on_identical_pairs": {d: sum(bool(r["pred"][d]) for r in sb if r["identical"])
                                                    for d in ["relic_v2"] + SB_BASE},
                       "nonident_disagree_14_ids": sorted(nonid_dis14), "nonident_disagree_13_ids": sorted(nonid_dis13),
                       "populations": {k: block(v, "base_id", SB_BASE) for k, v in pops.items()}}
    canon = json.load(open("reports/recovery/CANONICAL_NUMBERS.json"))["sembench"]["populations"]
    cmap = {"ALL_180": "ALL_180", "EXCL_25_IDENTICAL": "EXCL_25_IDENTICAL",
            "EXCL_15_NOOP_CHANGING_ONLY": "EXCL_15_NOOP_CHANGING_ONLY",
            "CLEAN_CORE": "CLEAN_CORE_(no identical, no disagree, no abstain)"}
    for k, ck in cmap.items():
        for d in ["relic_v2"] + SB_BASE:
            mine = out["sembench"]["populations"][k]["detectors"][d]
            assert all(mine[x] == canon[ck]["detectors"][d][x] for x in ("tp", "fp", "fn", "tn")), (k, d)
    cats = collections.defaultdict(list)
    for r in sb:
        cats[r["category"]].append(r)
    out["sembench"]["per_category_ALL_180"] = {k: block(v, "base_id", ["normalized_text_B"]) for k, v in sorted(cats.items())}

    # ---------------- External
    ex = [r for r in jl("results/external/predictions.jsonl") if r["status"] == "EVALUABLE"]
    assert len(ex) == 824 and all(v is not None for r in ex for v in r["pred"].values())
    for r in ex:
        r["file_cluster"] = f"{r['repo']}/{r['file']}"
    e = {"n": len(ex), "repos_with_evaluable": sorted({r["repo"] for r in ex})}
    e["pooled_file_cluster"] = block(ex, "file_cluster", EX_BASE)
    e["pooled_repo_cluster"] = block(ex, "repo", EX_BASE)
    e["pooled_excl_yetacp_file_cluster"] = block([r for r in ex if r["repo"] != "yetacp_mvs_sysgen"], "file_cluster", EX_BASE)
    for name, field in (("per_repo", "repo"), ("per_failure_category", "failure_category"), ("per_operator", "operator")):
        g = collections.defaultdict(list)
        for r in ex:
            g[r[field]].append(r)
        e[name] = {k: block(v, "file_cluster", EX_BASE) for k, v in sorted(g.items())}
    out["external"] = e

    # ---------------- Global Holm family: every McNemar / sign-flip test run above
    fam = []
    for k, b in out["sembench"]["populations"].items():
        fam += [("sembench/" + k, c) for c in b["comparisons"].values()]
    for k, b in out["sembench"]["per_category_ALL_180"].items():
        fam += [("sembench/category/" + k, c) for c in b["comparisons"].values()]
    for k in ("pooled_file_cluster", "pooled_excl_yetacp_file_cluster"):
        fam += [("external/" + k, c) for c in e[k]["comparisons"].values()]
    for g in ("per_repo", "per_failure_category", "per_operator"):
        for k, b in e[g].items():
            fam += [(f"external/{g}/{k}", c) for c in b["comparisons"].values()]
    # pooled_repo_cluster has the same McNemar as pooled_file_cluster (same cases): not a new test
    e["pooled_repo_cluster"]["comparisons_note"] = "same cases as pooled_file_cluster; McNemar not re-counted in the family"
    for key in ("p_mcnemar_exact", "p_cluster_signflip"):
        adj, m_distinct = holm_distinct([c["_sig"] for _, c in fam], [c[key] for _, c in fam])
        for (_, c), p in zip(fam, adj):
            c[key.replace("p_", "p_holm_global_")] = p
        for (_, c), p in zip(fam, holm([c[key] for _, c in fam])):
            c[key.replace("p_", "p_holm_rawm_")] = p
    out["holm_global"] = {"family_size_raw": len(fam), "family_size_distinct": m_distinct,
                          "dedup_rule": "tests with identical discordant case-id sets (either orientation) are one test; "
                                        "all zero-discordance tests are one null test",
                          "definition": "every relic_v2-vs-baseline paired test computed by this script "
                                        "(6 SemBench populations x 5 baselines, 12 categories x normalized_text_B, "
                                        "external pooled + pooled-excl-yetacp + 7 repos + 4 failure categories + "
                                        "9 operators, each x 2 baselines). Separate Holm for McNemar and sign-flip p.",
                          "n_raw_p_below_0.05": sum(c["p_mcnemar_exact"] < 0.05 for _, c in fam),
                          "n_holm_below_0.05": sum(c["p_holm_global_mcnemar_exact"] < 0.05 for _, c in fam),
                          "significant": [f"{s}: relic_v2 vs {c['b']}" for s, c in fam if c["p_holm_global_mcnemar_exact"] < 0.05],
                          "significant_signflip": [f"{s}: relic_v2 vs {c['b']}" for s, c in fam if c["p_holm_global_cluster_signflip"] < 0.05]}

    # ---------------- Reproduction of published numbers
    rep = {}
    P = json.load(open("results/sembench/paired_tests.json"))
    sub = {"ALL": sb, "VALIDATED_BY_ORACLE_AND_ARGUMENT": [r for r in sb if r["validation_status"] == "VALIDATED_BY_ORACLE_AND_ARGUMENT"],
           "ORACLE_DISAGREES": [r for r in sb if r["oracle_disagrees"]]}
    rep["sembench_paired"] = {}
    for s, rows in sub.items():
        pub = P["subsets"][s]["abstain_as_not_flagged"]["tests"]
        boot = Boot(rows, "base_id")
        mine = [compare(rows, t["a"], t["b"], "base_id", boot) for t in pub]
        hp = holm([round(m["p_mcnemar_exact"], 6) for m in mine])   # repo rounds to 6dp before Holm
        diffs = []
        for t, m, h in zip(pub, mine, hp):
            ok = (t["a_right_b_wrong"], t["a_wrong_b_right"]) == (m["a_right_b_wrong"], m["a_wrong_b_right"]) \
                and abs(t["p_exact"] - m["p_mcnemar_exact"]) < 1e-6 and abs(t["p_holm"] - h) < 1e-6 \
                and t["diff_mcc"]["ci95"] == m["diff_boot"]["mcc"]["ci95"] and t["diff_mcc"]["point"] == m["diff_point"]["mcc"]
            if not ok:
                diffs.append({"pair": f"{t['a']} vs {t['b']}", "published": [t["a_right_b_wrong"], t["a_wrong_b_right"], t["p_exact"], t["p_holm"], t["diff_mcc"]],
                              "reproduced": [m["a_right_b_wrong"], m["a_wrong_b_right"], m["p_mcnemar_exact"], h, m["diff_point"]["mcc"], m["diff_boot"]["mcc"]]})
        rep["sembench_paired"][s] = {"n_tests": len(pub), "n_mismatch": len(diffs), "mismatches": diffs}
        if s == "ALL":
            t = next(m for m in mine if m["b"] == "normalized_text_B" and m["a"] == "relic_v2")
            rep["headline_relic_vs_textB"] = {"a_right_b_wrong": t["a_right_b_wrong"], "a_wrong_b_right": t["a_wrong_b_right"],
                                              "p_exact": t["p_mcnemar_exact"], "p_holm_14": hp[[m is t for m in mine].index(True)],
                                              "diff_mcc": t["diff_point"]["mcc"], "diff_mcc_ci": t["diff_boot"]["mcc"]["ci95"]}
    # abstain modes identical?
    rep["abstain_modes_identical_on_sembench"] = all(
        P["subsets"][s]["abstain_as_not_flagged"] == P["subsets"][s]["abstain_excluded"] for s in sub)
    # Holm across ALL published (deduplicated) families: old(14) + ALL + VALIDATED + DISAGREES (14 each) = 56
    # Old benchmark raw data is not re-read: identity of its tests is inferred from 0:0 pairs
    # (zero discordance on per-case correctness <=> identical binary predictions).
    old = P["old_benchmark"]["abstain_as_not_flagged"]["tests"]
    par = {}
    find = lambda x: x if par.setdefault(x, x) == x else find(par[x])
    for t in old:
        if t["a_right_b_wrong"] == t["a_wrong_b_right"] == 0:
            par[find(t["a"])] = find(t["b"])
    pubp = [("old/" + t["a"] + "~" + t["b"], t["p_exact"],
             "NULL" if t["a_right_b_wrong"] == t["a_wrong_b_right"] == 0 else "old:" + "~".join(sorted([find(t["a"]), find(t["b"])])))
            for t in old]
    for s in sub:
        rows = sub[s]
        boot = Boot(rows, "base_id")
        for t in P["subsets"][s]["abstain_as_not_flagged"]["tests"]:
            pubp.append((s + "/" + t["a"] + "~" + t["b"], t["p_exact"], compare(rows, t["a"], t["b"], "base_id", boot)["_sig"]))
    hh = holm([p for _, p, _ in pubp])
    hd, md = holm_distinct([g for _, _, g in pubp], [p for _, p, _ in pubp])
    i = [n for n, _, _ in pubp].index("ALL/relic_v2~normalized_text_B")
    rep["published_tests_holm_across_all_4_families"] = {
        "m_raw": len(pubp), "m_distinct": md, "p_exact": pubp[i][1], "p_holm_raw_m": hh[i], "p_holm_distinct": hd[i],
        "n_p_zero_after_rounding": sum(p == 0.0 for _, p, _ in pubp),
        "note": "abstain modes are byte-identical so only one is counted; old-benchmark identity inferred from 0:0 pairs"}
    # SemBench single-detector metrics/bootstrap vs published metrics.json
    M = json.load(open("results/sembench/metrics.json"))["populations"]["ALL"]["modes"]["abstain_as_not_flagged"]["detectors"]
    mineALL = out["sembench"]["populations"]["ALL_180"]["detectors"]
    rep["sembench_metrics_ALL"] = {d: {"mcc_pub": M[d]["mcc"], "mcc_mine": mineALL[d]["mcc"],
                                       "mcc_ci_pub": M[d]["bootstrap"]["mcc"]["ci95"], "mcc_ci_mine": mineALL[d]["boot"]["mcc"]["ci95"],
                                       "f1_ci_pub": M[d]["bootstrap"]["f1"]["ci95"], "f1_ci_mine": mineALL[d]["boot"]["f1"]["ci95"],
                                       "match": M[d]["mcc"] == mineALL[d]["mcc"] and M[d]["bootstrap"]["mcc"]["ci95"] == mineALL[d]["boot"]["mcc"]["ci95"]
                                       and M[d]["bootstrap"]["f1"]["ci95"] == mineALL[d]["boot"]["f1"]["ci95"]
                                       and M[d]["bootstrap"]["balanced_accuracy"]["ci95"] == mineALL[d]["boot"]["balanced_accuracy"]["ci95"]}
                                   for d in ["relic_v2"] + SB_BASE}
    # External: replicate the repo's python-random file bootstrap of F1 (relic_eval/metrics.cluster_bootstrap)
    EM = json.load(open("results/external/metrics.json"))["populations"]

    def py_boot(rows):
        by = collections.defaultdict(list)
        for r in rows:
            by[r["file_cluster"]].append(r)
        files = sorted(by)
        dets = ["relic_v2", "textdiff_ignore_job_parameters", "textdiff"]
        cnt = {d: [(sum(r["truth"] and r["pred"][d] for r in by[f]), sum((not r["truth"]) and r["pred"][d] for r in by[f]),
                    sum(r["truth"] and not r["pred"][d] for r in by[f])) for f in files] for d in dets}
        rng, nf = random.Random(SEED), len(files)
        f1s, dif = {d: [] for d in dets}, {b: [] for b in dets[1:]}
        for _ in range(REPS):
            idx = [rng.randrange(nf) for _k in range(nf)]
            v = {}
            for d in dets:
                tp = sum(cnt[d][i][0] for i in idx); fp = sum(cnt[d][i][1] for i in idx); fn = sum(cnt[d][i][2] for i in idx)
                v[d] = None if 2 * tp + fp + fn == 0 else 2 * tp / (2 * tp + fp + fn)
            for d in dets:
                if v[d] is not None:
                    f1s[d].append(v[d])
            for b in dets[1:]:
                if v["relic_v2"] is not None and v[b] is not None:
                    dif[b].append(v["relic_v2"] - v[b])
        pc = lambda xs: (lambda s: [round(s[int(0.025 * (len(s) - 1))], 4), round(s[int(0.975 * (len(s) - 1))], 4)])(sorted(xs))
        return {"f1_ci95": {d: pc(x) for d, x in f1s.items()}, "diff_ci95": {f"relic_v2-{b}": pc(x) for b, x in dif.items()}}

    rep["external"] = {}
    for name, rows, pubk in (("pooled", ex, EM["pooled_effectiveness"]),
                             ("excl_yetacp", [r for r in ex if r["repo"] != "yetacp_mvs_sysgen"], EM["pooled_excluding_yetacp_mvs_sysgen"])):
        pb = py_boot(rows)
        pubb = pubk["bootstrap"]
        rep["external"][name] = {
            "f1_point_pub": {d: pubk["detectors"][d]["f1"] for d in ("relic_v2", "textdiff_ignore_job_parameters", "textdiff")},
            "f1_point_mine": {d: confusion(rows, d)["f1"] for d in ("relic_v2", "textdiff_ignore_job_parameters", "textdiff")},
            "f1_ci_pub": {d: pubb["f1_ci95"][d] for d in pb["f1_ci95"]}, "f1_ci_mine_pyrandom": pb["f1_ci95"],
            "diff_ci_pub": {k: pubb["diff_ci95"][k] for k in pb["diff_ci95"]}, "diff_ci_mine_pyrandom": pb["diff_ci95"],
            "match": all(pubb["f1_ci95"][d] == pb["f1_ci95"][d] for d in pb["f1_ci95"]) and all(pubb["diff_ci95"][k] == pb["diff_ci95"][k] for k in pb["diff_ci95"])}
    out["reproduction"] = rep

    # ---------------- Pre-registered hypotheses
    a = out["sembench"]["populations"]["ALL_180"]["comparisons"]["normalized_text_B"]
    ci = a["diff_boot"]["mcc"]["ci95"]
    h3 = {"external_pooled": out["external"]["pooled_file_cluster"]["detectors"]["relic_v2"]["precision_wilson95"]}
    for k, b in e["per_repo"].items():
        d = b["detectors"]["relic_v2"]
        if d["tp"] + d["fp"] >= 20:
            h3[k] = {"flagged": d["tp"] + d["fp"], "precision": d["precision"], "wilson95": d["precision_wilson95"]}
    lbs = [v[0] if isinstance(v, list) else v["wilson95"][0] for v in h3.values()]
    out["hypotheses"] = {
        "H1": {"population": "ALL_180", "comparator": "normalized_text_B", "diff_mcc_point": a["diff_point"]["mcc"], "diff_mcc_ci95": ci,
               "rejected": a["diff_point"]["mcc"] < 0 or (ci is not None and ci[1] < 0),
               "by_population": {k: {"point": b["comparisons"]["normalized_text_B"]["diff_point"]["mcc"],
                                     "ci95": b["comparisons"]["normalized_text_B"]["diff_boot"]["mcc"]["ci95"]}
                                 for k, b in out["sembench"]["populations"].items()}},
        "H2": {"relic_only_tp": {**{f"sembench/{k}": b["comparisons"]["normalized_text_B"]["relic_only_tp"] for k, b in out["sembench"]["populations"].items()},
                                 **{f"external/pooled vs {x}": e["pooled_file_cluster"]["comparisons"][x]["relic_only_tp"] for x in EX_BASE}}},
        "H3": {"rule": "rejected if Wilson lower bound < 0.90 in external pooled or any repo with >=20 RELIC-flagged",
               "values": h3, "min_lower_bound": min(lbs), "rejected": min(lbs) < 0.90},
        "H4": "not computed here (hybrid/fast-track: complementarity analysis)",
        "H5": "untested (needs explanation-fidelity audit)"}
    out["hypotheses"]["H2"]["rejected"] = all(v == 0 for k, v in out["hypotheses"]["H2"]["relic_only_tp"].items()
                                               if k.startswith("sembench/") and k.split("/")[1] in cmap)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    print(json.dumps({"reproduction": {k: v for k, v in rep.items()}, "holm": out["holm_global"], "hyp": out["hypotheses"]}, indent=1, default=str)[:12000])


if __name__ == "__main__":
    main()
