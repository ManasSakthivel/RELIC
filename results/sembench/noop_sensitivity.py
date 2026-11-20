"""
Sensitivity analysis (lead-authored, detector-independent exclusion rule).

JCL-SemBench v1 contains 25 pairs whose original and transformed files are
byte-identical (a generator no-op). The exclusion criterion is purely
`original_sha256 == transformed_sha256`; it uses no detector output.
The frozen benchmark and results/sembench/metrics.json are NOT altered; this
script only re-scores results/sembench/predictions.jsonl on the remaining cases.

Run: python results/sembench/noop_sensitivity.py   (from the repo root)
"""
import json, math, random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
cases = {c["id"]: c for c in map(json.loads, open(ROOT / "benchmarks/sembench/cases.jsonl"))}
preds = [json.loads(l) for l in open(ROOT / "results/sembench/predictions.jsonl")]
DET = ["raw_text", "textdiff", "textdiff_ignore_job_parameters", "normalized_text_A",
       "normalized_text_B", "relic_v1_0", "relic_v1_1", "relic_v2"]


def conf(rows, d):
    tp = fp = fn = tn = 0
    for r in rows:
        p, t = bool(r["pred"][d]), bool(r["truth"])
        tp += p and t; fp += p and not t; fn += (not p) and t; tn += (not p) and not t
    return tp, fp, fn, tn


def mcc(c):
    tp, fp, fn, tn = c
    den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return round((tp * tn - fp * fn) / den, 4) if den else None


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n * 2
    return round(min(1.0, p), 6)


def boot_delta(rows, a, b, reps=10000, seed=20261004):
    groups = defaultdict(list)
    for r in rows:
        groups[r["base_id"]].append(r)
    keys = sorted(groups)
    rng = random.Random(seed)
    out = []
    for _ in range(reps):
        s = [x for k in (rng.choice(keys) for _ in keys) for x in groups[k]]
        ma, mb = mcc(conf(s, a)), mcc(conf(s, b))
        if ma is not None and mb is not None:
            out.append(ma - mb)
    out.sort()
    if not out:
        return None
    return [round(out[int(0.025 * len(out))], 4), round(out[int(0.975 * len(out)) - 1], 4)]


def analyse(rows):
    res = {"n": len(rows), "positives": sum(r["truth"] for r in rows), "detectors": {}}
    for d in DET:
        c = conf(rows, d)
        res["detectors"][d] = {"tp": c[0], "fp": c[1], "fn": c[2], "tn": c[3], "mcc": mcc(c),
                               "recall": round(c[0] / (c[0] + c[2]), 4) if c[0] + c[2] else None,
                               "specificity": round(c[3] / (c[3] + c[1]), 4) if c[3] + c[1] else None}
    res["paired_vs_relic_v2"] = {}
    for d in DET:
        if d == "relic_v2":
            continue
        b = sum(1 for r in rows if bool(r["pred"]["relic_v2"]) == bool(r["truth"]) and bool(r["pred"][d]) != bool(r["truth"]))
        c = sum(1 for r in rows if bool(r["pred"]["relic_v2"]) != bool(r["truth"]) and bool(r["pred"][d]) == bool(r["truth"]))
        res["paired_vs_relic_v2"][d] = {"v2_right_other_wrong": b, "v2_wrong_other_right": c,
                                        "mcnemar_exact_p_uncorrected": mcnemar_exact(b, c),
                                        "delta_mcc_v2_minus_other_ci95_cluster_bootstrap": boot_delta(rows, "relic_v2", d, reps=2000)}
    return res


noop = {i for i, c in cases.items() if c["original_sha256"] == c["transformed_sha256"]}
out = {
    "note": "Exclusion rule: byte-identical original/transformed (detector-independent). Frozen benchmark/metrics unchanged. "
            "p-values are uncorrected; bootstrap 2000 reps clustered by base_id, seed 20261004.",
    "noop_pairs": {"n": len(noop), "by_expected": {k: sum(1 for i in noop if cases[i]["expected_outcome"] == k)
                                                    for k in ("PRESERVING", "CHANGING")}},
    "all_cases": analyse(preds),
    "excluding_noop": analyse([r for r in preds if r["id"] not in noop]),
    "excluding_noop_and_oracle_disagreements": analyse(
        [r for r in preds if r["id"] not in noop and r["validation_status"] == "VALIDATED_BY_ORACLE_AND_ARGUMENT"]),
}
(ROOT / "results/sembench/noop_sensitivity.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
for k in ("all_cases", "excluding_noop", "excluding_noop_and_oracle_disagreements"):
    v = out[k]
    print(k, v["n"], "pos", v["positives"])
    for d in ("normalized_text_B", "textdiff_ignore_job_parameters", "relic_v1_1", "relic_v2"):
        x = v["detectors"][d]; print("  ", d, (x["tp"], x["fp"], x["fn"], x["tn"]), "MCC", x["mcc"])
    p = v["paired_vs_relic_v2"]["normalized_text_B"]; print("   V2 vs normB:", p)
