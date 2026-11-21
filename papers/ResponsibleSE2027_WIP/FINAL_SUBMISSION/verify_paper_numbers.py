"""Paper-specific numerical verifier for ResponsibleSE2027_Final_Manuscript.tex.

Recomputes every number the paper reports from the raw inputs (case file, prediction file) and checks
that the value appears in the final manuscript source. Exits non-zero on any failed assertion.
Run from anywhere:  python3 verify_paper_numbers.py
Writes nothing to the repository. Optional output: verify_paper_numbers_output.txt next to this script.
"""
import json, math, itertools, hashlib, os, re, sys, collections
from decimal import Decimal, ROUND_HALF_UP
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CASES = os.path.join(REPO, "benchmarks/sembench/cases.jsonl")
PREDS = os.path.join(REPO, "results/sembench/predictions.jsonl")
TEX = os.path.join(HERE, "ResponsibleSE2027_Final_Manuscript.tex")
EXPECTED_HASH = {"cases": "fc8e64ba9999cb38", "predictions": "7f1809e42eda1ada"}  # from results/final/llm/matched_subset_v1/manifest.json

fails, passes = [], []
def check(cond, msg):
    (passes if cond else fails).append(msg)

def r(x, nd=3):
    return str(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))

def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]

tex = open(TEX, encoding="utf-8").read()
check(sha16(CASES) == EXPECTED_HASH["cases"], "cases.jsonl hash matches manifest")
check(sha16(PREDS) == EXPECTED_HASH["predictions"], "predictions.jsonl hash matches manifest")

C = {j["id"]: j for j in map(json.loads, open(CASES, encoding="utf-8"))}
P = {j["id"]: j["pred"] for j in map(json.loads, open(PREDS, encoding="utf-8"))}
ids = sorted(C)
check(len(ids) == 180 and set(ids) == set(P), "180 pairs, predictions aligned")

# ---- benchmark integrity counts ----
ident = {i for i in ids if C[i]["original_sha256"] == C[i]["transformed_sha256"]}
ch = [i for i in ids if C[i]["expected_outcome"] == "CHANGING"]
check(len(ch) == 93 and len(ids) - len(ch) == 87, "93 CHANGING / 87 PRESERVING")
check(len(ident) == 25, "25 byte-identical pairs")
check(sum(1 for i in ident if C[i]["expected_outcome"] == "CHANGING") == 15, "15 identical CHANGING")
check(sum(1 for i in ident if C[i]["expected_outcome"] == "PRESERVING") == 10, "10 identical PRESERVING")
grp = collections.defaultdict(list)
for i in ids: grp[(C[i]["original_sha256"], C[i]["transformed_sha256"])].append(i)
dup = [g for g in grp.values() if len(g) > 1]
check(len(dup) == 21 and sum(map(len, dup)) == 46, "21 duplicate groups covering 46 pairs")
check(sum(1 for g in dup if len({C[i]["expected_outcome"] for i in g}) > 1) == 5, "5 duplicate groups with conflicting labels")
def ol(i):
    v = C[i]["oracle_verdict"]; return v.get("label") if isinstance(v, dict) else v
dis = [i for i in ids if C[i]["oracle_agrees_with_expected"] is False and C[i]["validation_status"] == "ORACLE_DISAGREES"]
check(len(dis) == 28, "28 oracle disagreements (ORACLE_DISAGREES)")
check(sum(i in ident for i in dis) == 15 and sum(i not in ident for i in dis) == 13, "28 = 15 identical + 13 non-identical")
abst = [i for i in ids if C[i]["validation_status"] == "ORACLE_ABSTAINS"]
check(len(abst) == 1 and abst[0] == "sembench_172", "one abstention, sembench_172")
eq_chg_nonid = [i for i in ch if ol(i) == "EQUIVALENT" and i not in ident]
check(len(eq_chg_nonid) == 10, "10 non-identical CHANGING labels returned EQUIVALENT")
distinct_edits = len({(C[i]["original_sha256"], C[i]["transformed_sha256"]) for i in eq_chg_nonid})
check(distinct_edits == 8, f"8 distinct edits among the 10 (got {distinct_edits})")
check(sum(C[i]["subcategory"] == "disp_shr_to_old" for i in eq_chg_nonid) == 4, "4 SHR-to-OLD labels")
check(sum(C[i]["subcategory"] == "disp_catlg_to_keep" for i in eq_chg_nonid) == 5, "5 CATLG-to-KEEP labels")

# ---- label sets ----
unres = {i for i in ids if C[i]["validation_status"] in ("ORACLE_DISAGREES", "ORACLE_ABSTAINS") and i not in ident}
L0 = {i: C[i]["expected_outcome"] for i in ids}
L1 = {i: ("PRESERVING" if i in ident and L0[i] == "CHANGING" else L0[i]) for i in ids}
L2 = {i: L1[i] for i in ids if i not in unres}
L3 = {}
for i in ids:
    if i in unres:
        if ol(i) == "DIFFERENT": L3[i] = "CHANGING"
        elif ol(i) == "EQUIVALENT": L3[i] = "PRESERVING"
    else:
        L3[i] = L1[i]
check(len(L2) == 166 and len(L3) == 179, "L2 n=166, L3 n=179")

def conf(lab, det, sub=None):
    tp = fp = tn = fn = 0
    for i in (sub if sub is not None else lab):
        if i not in lab: continue
        y = lab[i] == "CHANGING"; p = bool(P[i][det])
        tp += y and p; fp += (not y) and p; fn += y and (not p); tn += (not y) and (not p)
    return tp, fp, tn, fn
def mcc(c):
    tp, fp, tn, fn = c; d = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    return (tp*tn - fp*fn)/d if d else float("nan")

SETS = {"L0": L0, "L1": L1, "L2": L2, "L3": L3}
mcc_pt = {k: {d: mcc(conf(l, d)) for d in ("relic_v2", "normalized_text_B")} for k, l in SETS.items()}
delta = {k: mcc_pt[k]["relic_v2"] - mcc_pt[k]["normalized_text_B"] for k in SETS}

# printed values must appear in the tex
def printed(x, nd=3):
    s = r(x, nd)
    return "$" + s + "$" if s.startswith("-") else s  # manuscript writes negatives in math mode
for k in SETS:
    for d in ("relic_v2", "normalized_text_B"):
        check(printed(mcc_pt[k][d]) in tex, f"{k} {d} MCC {printed(mcc_pt[k][d])} printed")
    check(printed(delta[k]) in tex, f"{k} delta {printed(delta[k])} printed")

# ---- bootstrap (same scheme as the published run: sorted clusters, default_rng(20261004), 10000x K) ----
SEED, REPS = 20261004, 10000
def boot_ci(lab):
    rows = list(lab); cl = sorted({C[i]["base_id"] for i in rows}); K = len(cl); pos = {c: n for n, c in enumerate(cl)}
    cidx = np.array([pos[C[i]["base_id"]] for i in rows])
    idx = np.random.default_rng(SEED).integers(0, K, size=(REPS, K))
    y = np.array([lab[i] == "CHANGING" for i in rows]); cells = {}
    for d in ("relic_v2", "normalized_text_B"):
        p = np.array([bool(P[i][d]) for i in rows])
        cells[d] = [np.bincount(cidx[m], minlength=K) for m in (y & p, ~y & p, y & ~p, ~y & ~p)]
    def draw(d):
        tp, fp, fn, tn = (c[idx].sum(axis=1).astype(float) for c in cells[d])
        den = np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(den > 0, (tp*tn - fp*fn)/den, np.nan)
    out = {}
    for d in ("relic_v2", "normalized_text_B"):
        x = draw(d); out[d] = np.percentile(x[~np.isnan(x)], [2.5, 97.5])
    dd = draw("relic_v2") - draw("normalized_text_B")
    out["delta"] = np.percentile(dd[~np.isnan(dd)], [2.5, 97.5])
    return out, K
for k, l in SETS.items():
    ci, K = boot_ci(l)
    check(K == 16, f"{k} has 16 clusters")
    for d in ("relic_v2", "normalized_text_B"):
        lo, hi = ci[d]
        check(f"[{printed(lo)}, {printed(hi)}]" in tex, f"{k} {d} CI [{printed(lo)}, {printed(hi)}] printed")
    lo, hi = ci["delta"]
    check(f"[{printed(lo)}, {printed(hi)}]" in tex, f"{k} delta CI [{printed(lo)}, {printed(hi)}] printed")

# ---- exact cluster-swap test (all 2^16 assignments) ----
clusters = sorted({C[i]["base_id"] for i in ids}); K = len(clusters)
bits = np.array(list(itertools.product((0, 1), repeat=K)), dtype=np.int64)
def swap_p(lab):
    def cellvec(which):
        X0 = np.zeros((K, 4)); X1 = np.zeros((K, 4))
        for ci, cl in enumerate(clusters):
            for i in lab:
                if C[i]["base_id"] != cl: continue
                a = bool(P[i]["relic_v2"]); b = bool(P[i]["normalized_text_B"]); y = lab[i] == "CHANGING"
                for bit, (pa, pb), X in ((0, (a, b), X0), (1, (b, a), X1)):
                    p = pa if which == "A" else pb
                    X[ci] += [y and p, (not y) and p, (not y) and (not p), y and (not p)]  # tp, fp, tn, fn
        return X0, X1
    XA0, XA1 = cellvec("A"); XB0, XB1 = cellvec("B")
    SA = bits @ XA1 + (1 - bits) @ XA0; SB = bits @ XB1 + (1 - bits) @ XB0
    def m(S):
        tp, fp, tn, fn = S[:, 0], S[:, 1], S[:, 2], S[:, 3]
        d = np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
        return np.where(d > 0, (tp*tn - fp*fn)/np.where(d > 0, d, 1), np.nan)
    obs = mcc(conf(lab, "relic_v2")) - mcc(conf(lab, "normalized_text_B"))
    dl = m(SA) - m(SB)
    return float(np.mean(np.abs(dl) >= abs(obs) - 1e-12)), len(bits)
PVAL = {}
for k, l in SETS.items():
    p, n = swap_p(l); PVAL[k] = p
    check(n == 65536, f"{k}: 2^16 assignments enumerated")
    check(r(p, 3) in tex and f"{r(p, 3)}" == r(p, 3), f"{k} exact p {r(p, 3)} printed")
check(r(PVAL["L0"], 3) == "0.015" and r(PVAL["L1"], 3) == "0.002" and r(PVAL["L2"], 3) == "0.010" and r(PVAL["L3"], 3) == "0.089", "exact p-values 0.015, 0.002, 0.010, 0.089")
check("$p=0.089$" in tex, "L3 p=0.089 printed in text")

# ---- McNemar (exact binomial, per-pair correctness) ----
def mcnemar(lab):
    b = c = 0
    for i in lab:
        rr = P[i]["relic_v2"] == (lab[i] == "CHANGING"); tt = P[i]["normalized_text_B"] == (lab[i] == "CHANGING")
        b += rr and not tt; c += tt and not rr
    n = b + c
    from math import comb
    return min(1.0, 2*sum(comb(n, k) for k in range(0, min(b, c)+1))/2**n) if n else 1.0
mc = {k: mcnemar(l) for k, l in SETS.items()}
check([r(mc[k], 3) for k in SETS] == ["0.002", "0.002", "0.029", "0.314"], f"McNemar p printed as 0.002/0.002/0.029/0.314 (got {[r(mc[k],3) for k in SETS]})")

# ---- sensitivity: leave-one-program-out and dedup on L1 (4 decimals) ----
loo = {}
for b in clusters:
    sub = [i for i in L1 if C[i]["base_id"] != b]
    loo[b] = mcc(conf(L1, "relic_v2", sub)) - mcc(conf(L1, "normalized_text_B", sub))
lo_min, lo_max = min(loo.values()), max(loo.values())
check(r(lo_min, 4) == "-0.3645" and r(lo_max, 4) == "-0.3134", f"LOO range -0.3645..-0.3134 (got {r(lo_min,4)}..{r(lo_max,4)})")
check("$-0.3645$" in tex and "$-0.3134$" in tex, "LOO values printed")
keep = [g[0] for g in grp.values()]
dedup = mcc(conf(L1, "relic_v2", keep)) - mcc(conf(L1, "normalized_text_B", keep))
check(len(keep) == 155 and r(dedup, 4) == "-0.3375", f"dedup gap -0.3375 on 155 pairs (got {r(dedup,4)})")
check("$-0.3375$" in tex, "dedup gap printed")

# ---- RELIC L1 misses and categories ----
ch1 = [i for i in L1 if L1[i] == "CHANGING"]
miss = [i for i in ch1 if not P[i]["relic_v2"]]
check(len(ch1) == 78 and len(miss) == 55, "L1: 78 CHANGING, 55 RELIC misses")
cats = collections.Counter(C[i]["category"] for i in miss)
check(sorted(cats.values(), reverse=True) == [16, 12, 12, 10, 5], f"miss categories 16/12/12/10/5 (got {sorted(cats.values(), reverse=True)})")
relic_only = [i for k, l in SETS.items() for i in l if l[i] == "CHANGING" and P[i]["relic_v2"] and not P[i]["normalized_text_B"]]
check(len(relic_only) == 0, "no RELIC-only true positives on any label set")

# ---- LLM must not appear as a reported result ----
for bad in ["0.603", "0.890", "gpt-oss", "Groq"]:  # coverage count (155 of 180) is stated as the reason for exclusion, not as a result
    check(bad not in tex, f"LLM figure '{bad}' absent from manuscript")
check("corrected baseline" not in tex.lower() and "corrected ground truth" not in tex.lower(), "no 'corrected baseline/ground truth' wording")
check("fixed before the L3" not in tex, "unverifiable 'fixed before' claim removed")

# ---- built PDFs must match the source (catches stale builds) ----
try:
    import pypdfium2 as pdfium
    def pdf_text(name):
        pdf = pdfium.PdfDocument(os.path.join(HERE, name))
        return " ".join(pdf[i].get_textpage().get_text_range() for i in range(len(pdf))).replace("\r", " ").replace("\n", " ")
    anon_t = pdf_text("ResponsibleSE2027_Anonymous_Submission.pdf")
    auth_t = pdf_text("ResponsibleSE2027_Author_Identified.pdf")
    check("0.666, 0.803" in anon_t and "0.666, 0.803" in auth_t, "PDFs carry corrected L1 text-B interval 0.666")
    check("0.665, 0.803" not in anon_t and "0.665, 0.803" not in auth_t, "PDFs do not carry the stale 0.665")
    for w in ["manas", "sakthivel", "rvce", "bengaluru", "github", "desktop", "users/", "groq", "gpt-oss"]:
        check(w not in anon_t.lower(), f"anonymous PDF free of '{w}'")
    check("manas sakthivel" in auth_t.lower(), "author PDF carries author name")
except ImportError:
    fails.append("pypdfium2 not available: PDF checks not run")

# ---- report ----
lines = [f"PASS {m}" for m in passes] + [f"FAIL {m}" for m in fails]
lines.append(f"\n{len(passes)} passed, {len(fails)} failed")
txt = "\n".join(lines)
print(txt)
try:
    open(os.path.join(HERE, "verify_paper_numbers_output.txt"), "w", encoding="utf-8").write(txt + "\n")
except OSError:
    pass
sys.exit(1 if fails else 0)
