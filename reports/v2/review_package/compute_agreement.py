#!/usr/bin/env python3
"""
Agreement statistics for the RELIC independent-review package.

STATUS: no real reviewer ratings exist (independent review is PENDING).  The only built-in
data are SYNTHETIC and are used solely by ``--self-test`` (clearly labelled in its output);
synthetic data are never read in real mode and real data are never read in self-test mode.

Statistics (per pair of raters over the items both rated):
  * percent agreement                 p_o = (1/n) * sum 1[a_i == b_i]
  * Cohen's kappa                     (p_o - p_e) / (1 - p_e),  p_e = sum_k pA_k * pB_k
  * Gwet's AC1                        (p_o - p_e) / (1 - p_e),  p_e = 1/(q-1) * sum_k pi_k (1 - pi_k),
                                      pi_k = (pA_k + pB_k) / 2,  q = number of categories
  * percentile bootstrap CI           resample ITEMS with replacement (B=2000, fixed seed),
                                      2.5 / 97.5 percentiles; resamples with p_e == 1 are dropped and counted.

Analyses (all on ``--field``, default overall_label):
  A. reviewer vs reviewer             (every pair among the supplied reviewer files)
  B. adjudicated label                (A==B -> that label, else majority of A,B,C; the oracle is
                                       NEVER used to adjudicate)
  C. reviewer vs oracle, adjudicated vs oracle (needs --key and --compare-oracle; run ONLY after
                                       every reviewer has submitted and adjudication is finished)
  Items where either rater answered CANNOT_DETERMINE are excluded from the binary analysis
  (their number is reported); a second analysis keeps all categories.

Usage
  python compute_agreement.py --self-test
  python compute_agreement.py --reviewer-a respA.csv --reviewer-b respB.csv [--reviewer-c respC.csv]
  python compute_agreement.py ... --key KEY_DO_NOT_SHARE.csv --compare-oracle --confirm-reviews-complete
Exit codes: 0 ok, 1 self-test failure, 3 = PENDING (no real ratings supplied).
"""
from __future__ import annotations

import argparse
import csv
import itertools
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ORACLE_CATS = ("EQUIVALENT", "DIFFERENT")
UNDEC = "CANNOT_DETERMINE"


# ------------------------------------------------------------------ core statistics
def _dist(x, cats):
    n = len(x)
    c = Counter(x)
    return {k: c.get(k, 0) / n for k in cats}


def percent_agreement(a, b, cats=None):
    return sum(1 for x, y in zip(a, b) if x == y) / len(a)


def cohen_kappa(a, b, cats=None):
    cats = cats or sorted(set(a) | set(b))
    po = percent_agreement(a, b)
    pa, pb = _dist(a, cats), _dist(b, cats)
    pe = sum(pa[k] * pb[k] for k in cats)
    return float("nan") if pe >= 1 else (po - pe) / (1 - pe)


def gwet_ac1(a, b, cats=None):
    cats = cats or sorted(set(a) | set(b))
    q = len(cats)
    if q < 2:
        return float("nan")
    po = percent_agreement(a, b)
    pa, pb = _dist(a, cats), _dist(b, cats)
    pi = {k: (pa[k] + pb[k]) / 2 for k in cats}
    pe = sum(pi[k] * (1 - pi[k]) for k in cats) / (q - 1)
    return float("nan") if pe >= 1 else (po - pe) / (1 - pe)


STATS = {"percent_agreement": percent_agreement, "cohen_kappa": cohen_kappa, "gwet_ac1": gwet_ac1}


def bootstrap_ci(a, b, stat, cats, n_boot=2000, seed=1, alpha=0.05):
    rng = random.Random(seed)
    n = len(a)
    vals, dropped = [], 0
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        v = stat([a[i] for i in idx], [b[i] for i in idx], cats)
        if math.isnan(v):
            dropped += 1
            continue
        vals.append(v)
    if len(vals) < max(50, n_boot // 10):
        return (float("nan"), float("nan"), dropped)
    vals.sort()
    lo = vals[int((alpha / 2) * len(vals))]
    hi = vals[min(len(vals) - 1, int((1 - alpha / 2) * len(vals)))]
    return (lo, hi, dropped)


def summarize(a, b, cats, n_boot=2000, seed=1):
    out = {"n": len(a)}
    if not a:
        return out
    for name, fn in STATS.items():
        v = fn(a, b, cats)
        lo, hi, dr = bootstrap_ci(a, b, fn, cats, n_boot, seed)
        out[name] = (v, lo, hi)
        if dr:
            out[name + "_boot_dropped"] = dr
    return out


def fmt(s):
    if s["n"] == 0:
        return "n=0 (no paired items)"
    parts = [f"n={s['n']}"]
    for k in STATS:
        v, lo, hi = s[k]
        parts.append(f"{k}={v:.3f} [{lo:.3f},{hi:.3f}]")
    return "  ".join(parts)


# ------------------------------------------------------------------ io
def read_ratings(path, field):
    """-> {case_id: label}; rows with an empty label are ignored (placeholders)."""
    out = {}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            lab = (row.get(field) or "").strip().upper()
            rid = (row.get("reviewer_id") or "").strip()
            if rid.upper().startswith("SYNTHETIC"):
                sys.exit("refusing synthetic reviewer ids in real mode")
            if lab and row.get("case_id"):
                out[row["case_id"].strip()] = lab
    return out


def paired(ra, rb, drop_undec):
    ids = sorted(set(ra) & set(rb))
    if drop_undec:
        ids = [i for i in ids if ra[i] != UNDEC and rb[i] != UNDEC]
    return ids, [ra[i] for i in ids], [rb[i] for i in ids]


def majority(labels):
    c = Counter(labels).most_common()
    if c and (len(c) == 1 or c[0][1] > c[1][1]):
        return c[0][0]
    return "UNRESOLVED"


def confusion(oracle, rater):
    t = Counter(zip(oracle, rater))
    return {f"oracle={o}|rater={r}": t[(o, r)] for o in ORACLE_CATS for r in ORACLE_CATS}


# ------------------------------------------------------------------ real mode
def real_mode(args):
    files = {k: getattr(args, f"reviewer_{k}") for k in "abc"}
    ratings = {}
    for k, p in files.items():
        if p:
            if not Path(p).exists():
                print(f"PENDING: {p} does not exist")
                continue
            ratings[k.upper()] = read_ratings(p, args.field)
    nonempty = {k: v for k, v in ratings.items() if v}
    if len(nonempty) < 2:
        print("PENDING: fewer than two reviewers have submitted non-empty ratings; nothing computed. "
              "(Placeholder/empty templates are ignored; no ratings are fabricated.)")
        return 3
    print(f"field={args.field}  reviewers={sorted(nonempty)}  bootstrap B={args.boot} seed={args.seed}")
    print("== A. reviewer vs reviewer ==")
    for x, y in itertools.combinations(sorted(nonempty), 2):
        ids, a, b = paired(nonempty[x], nonempty[y], drop_undec=True)
        ids3, a3, b3 = paired(nonempty[x], nonempty[y], drop_undec=False)
        n_undec = len(ids3) - len(ids)
        print(f" {x} vs {y} [binary, {n_undec} pairs with CANNOT_DETERMINE excluded]: "
              f"{fmt(summarize(a, b, sorted(set(a) | set(b)), args.boot, args.seed))}")
        print(f" {x} vs {y} [all categories]: "
              f"{fmt(summarize(a3, b3, sorted(set(a3) | set(b3)), args.boot, args.seed))}")
    adjud = {}
    if "A" in nonempty and "B" in nonempty:
        for i in sorted(set(nonempty["A"]) & set(nonempty["B"])):
            if nonempty["A"][i] == nonempty["B"][i]:
                adjud[i] = nonempty["A"][i]
            elif "C" in nonempty and i in nonempty["C"]:
                adjud[i] = majority([nonempty["A"][i], nonempty["B"][i], nonempty["C"][i]])
            else:
                adjud[i] = "UNADJUDICATED"
        print("== B. adjudicated labels (A==B, else majority incl. C; oracle not used) ==")
        print("  ", dict(Counter(adjud.values())))
    if args.compare_oracle:
        if not args.confirm_reviews_complete:
            sys.exit("--compare-oracle requires --confirm-reviews-complete (oracle labels must not "
                     "be consulted before every review and adjudication is finished)")
        if not args.key:
            sys.exit("--compare-oracle requires --key KEY_DO_NOT_SHARE.csv")
        if args.field != "overall_label":
            sys.exit("oracle comparison is defined for --field overall_label only")
        key = {r["case_id"]: r for r in csv.DictReader(open(args.key, newline=""))}
        olabel = {i: r["oracle_label"] for i, r in key.items()}
        print("== C. vs oracle (oracle label from key; oracle positive = DIFFERENT) ==")
        sets = dict(nonempty)
        sets["ADJUDICATED"] = {i: l for i, l in adjud.items() if l in ORACLE_CATS}
        for name, r in sorted(sets.items()):
            ids = [i for i in sorted(r) if i in olabel and r[i] in ORACLE_CATS]
            o = [olabel[i] for i in ids]
            x = [r[i] for i in ids]
            print(f" {name} vs oracle: {fmt(summarize(o, x, list(ORACLE_CATS), args.boot, args.seed))}")
            print(f"    confusion {confusion(o, x)}")
            for col in ("operator", "oracle_tier", "subject", "hard_flags"):
                groups = defaultdict(list)
                for i in ids:
                    for g in (key[i][col].split(";") if col == "hard_flags" else [key[i][col]]):
                        groups[g or "none"].append(i)
                cells = {g: f"{sum(r[i] == olabel[i] for i in m)}/{len(m)}" for g, m in sorted(groups.items())}
                print(f"    agreement by {col}: {cells}")
    return 0


# ------------------------------------------------------------------ SYNTHETIC self-test
def self_test():
    print("=" * 78)
    print("SYNTHETIC SELF-TEST - all ratings below are SIMULATED. They are NOT reviewer")
    print("ratings and say nothing about the oracle or about RELIC.")
    print("=" * 78)
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")

    # 1. textbook 2x2 table: a=20, b=5, c=10, d=15 -> po=.70, pe=.50, kappa=.40; AC1: pe=.495 -> .4059
    A = ["Y"] * 20 + ["Y"] * 5 + ["N"] * 10 + ["N"] * 15
    B = ["Y"] * 20 + ["N"] * 5 + ["Y"] * 10 + ["N"] * 15
    check("percent agreement known table (0.70)", abs(percent_agreement(A, B) - 0.70) < 1e-12)
    check("Cohen kappa known table (0.400)", abs(cohen_kappa(A, B) - 0.40) < 1e-12, f"got {cohen_kappa(A, B):.4f}")
    check("Gwet AC1 known table (0.4059)", abs(gwet_ac1(A, B) - 0.205 / 0.505) < 1e-9, f"got {gwet_ac1(A, B):.4f}")
    # 2. perfect agreement
    P = ["E", "D"] * 20
    check("perfect agreement -> 1,1,1", percent_agreement(P, P) == 1 and abs(cohen_kappa(P, P) - 1) < 1e-12
          and abs(gwet_ac1(P, P) - 1) < 1e-12)
    # 3. kappa paradox: skewed prevalence -> AC1 >= kappa
    X = ["D"] * 95 + ["E"] * 5
    Y = ["D"] * 93 + ["E"] * 2 + ["D"] * 3 + ["E"] * 2
    check("AC1 >= kappa under skewed prevalence", gwet_ac1(X, Y) >= cohen_kappa(X, Y),
          f"kappa={cohen_kappa(X, Y):.3f} AC1={gwet_ac1(X, Y):.3f}")
    # 4. independent random raters -> kappa ~ 0
    rng = random.Random(12345)
    R1 = [rng.choice("ED") for _ in range(3000)]
    R2 = [rng.choice("ED") for _ in range(3000)]
    check("independent synthetic raters: |kappa|<0.06", abs(cohen_kappa(R1, R2)) < 0.06,
          f"kappa={cohen_kappa(R1, R2):.3f}")

    # 5. two noisy copies of a latent truth (10% flip each) -> expected po = 0.82
    def noisy(truth, err):
        return [t if rng.random() > err else ("E" if t == "D" else "D") for t in truth]
    t60 = [rng.choice("ED") for _ in range(60)]
    t600 = [rng.choice("ED") for _ in range(600)]
    a60, b60 = noisy(t60, 0.10), noisy(t60, 0.10)
    a600, b600 = noisy(t600, 0.10), noisy(t600, 0.10)
    s60 = summarize(a60, b60, ["D", "E"], 500, 7)
    s600 = summarize(a600, b600, ["D", "E"], 500, 7)
    print("   synthetic n=60 :", fmt(s60))
    print("   synthetic n=600:", fmt(s600))
    check("point estimates lie inside their own bootstrap CIs",
          all(s[k][1] <= s[k][0] <= s[k][2] for s in (s60, s600) for k in STATS))
    w60 = s60["cohen_kappa"][2] - s60["cohen_kappa"][1]
    w600 = s600["cohen_kappa"][2] - s600["cohen_kappa"][1]
    check("bootstrap CI narrows with n (600 < 60)", w600 < w60, f"width {w60:.2f} -> {w600:.2f}")
    check("expected po ~0.82 for 10% symmetric noise (+-0.06, n=600)", abs(s600["percent_agreement"][0] - 0.82) < 0.06)
    # 6. determinism
    check("bootstrap deterministic for fixed seed",
          bootstrap_ci(a60, b60, cohen_kappa, ["D", "E"], 300, 5) == bootstrap_ci(a60, b60, cohen_kappa, ["D", "E"], 300, 5))
    # 7. adjudication helper
    check("majority([E,D,E])=E; tie -> UNRESOLVED",
          majority(["E", "D", "E"]) == "E" and majority(["E", "D", UNDEC]) == "UNRESOLVED")
    print("SYNTHETIC SELF-TEST RESULT:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true", help="run on SYNTHETIC ratings only")
    for k in "abc":
        ap.add_argument(f"--reviewer-{k}", help=f"responses CSV of reviewer {k.upper()} (blind_review_form.csv columns)")
    ap.add_argument("--field", default="overall_label",
                    choices=["overall_label", "q1_normal_completion", "q2_failure_scenarios"])
    ap.add_argument("--key", help="KEY_DO_NOT_SHARE.csv (only with --compare-oracle)")
    ap.add_argument("--compare-oracle", action="store_true")
    ap.add_argument("--confirm-reviews-complete", action="store_true")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    if args.self_test:
        sys.exit(self_test())
    if not (args.reviewer_a or args.reviewer_b or args.reviewer_c):
        ap.print_help()
        print("\nPENDING: no reviewer files supplied.")
        sys.exit(3)
    sys.exit(real_mode(args))


if __name__ == "__main__":
    main()
