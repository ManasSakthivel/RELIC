"""Versioned label correction for JCL-SemBench (v1.1). Original labels are preserved.

Correction C1: a pair whose original and transformed files are byte-identical
cannot change behaviour, so a CHANGING label on it is wrong. Only C1 is applied.
The 13 non-identical oracle disagreements are NOT corrected: they need adjudication.
Inputs : benchmarks/sembench/cases.jsonl, benchmarks/sembench/cases/*/{original,transformed}.jcl,
         results/sembench/predictions.jsonl
Outputs: benchmarks/final/sembench_v1_1/cases.jsonl, benchmarks/final/label_corrections.csv,
         results/final/statistics/label_correction_metrics.json
"""
import csv, json, os, hashlib
ROOT = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(ROOT, "benchmarks")):
    ROOT = os.path.dirname(ROOT)
os.chdir(ROOT)
cases = [json.loads(l) for l in open("benchmarks/sembench/cases.jsonl")]
os.makedirs("benchmarks/final/sembench_v1_1", exist_ok=True)
os.makedirs("results/final/statistics", exist_ok=True)

corrections, pending = [], []
out = []
for c in cases:
    c = dict(c)
    c["expected_outcome_original"] = c["expected_outcome"]
    c["correction_id"] = None
    byte_same = False
    if c["original_sha256"] == c["transformed_sha256"]:
        a = open(f"benchmarks/sembench/cases/{c['id']}/original.jcl", "rb").read()
        b = open(f"benchmarks/sembench/cases/{c['id']}/transformed.jcl", "rb").read()
        byte_same = a == b
    if c["expected_outcome"] == "CHANGING" and byte_same:
        c["expected_outcome"] = "PRESERVING"
        c["correction_id"] = "C1"
        corrections.append({"id": c["id"], "category": c["category"], "subcategory": c["subcategory"],
            "original_label": "CHANGING", "corrected_label": "PRESERVING", "correction_id": "C1",
            "evidence": "original.jcl and transformed.jcl are byte-identical (sha256 equal and cmp equal); "
                        "oracle verdict EQUIVALENT agrees with the corrected label",
            "confidence": "high", "status": "APPLIED_v1_1",
            "note": "The intended edit described in the rationale is absent from the artefact (generator no-op)"})
    elif c["validation_status"] == "ORACLE_DISAGREES" or c["validation_status"] == "ORACLE_ABSTAINS":
        pending.append({"id": c["id"], "category": c["category"], "subcategory": c["subcategory"],
            "original_label": c["expected_outcome"], "corrected_label": c["expected_outcome"],
            "correction_id": "NONE", "evidence": "oracle verdict " + str(c["oracle_verdict"].get("label") if isinstance(c["oracle_verdict"], dict) else c["oracle_verdict"]),
            "confidence": "unresolved", "status": "NOT_CORRECTED_PENDING_ADJUDICATION",
            "note": "Non-identical files differ; label-versus-oracle conflict needs independent adjudication"})
    out.append(c)

with open("benchmarks/final/sembench_v1_1/cases.jsonl", "w") as f:
    for c in out:
        f.write(json.dumps(c, sort_keys=True) + "\n")
with open("benchmarks/final/label_corrections.csv", "w", newline="") as f:
    rows = corrections + pending
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

# ---- recompute detector metrics on original vs v1.1 labels ----
preds = {json.loads(l)["id"]: json.loads(l) for l in open("results/sembench/predictions.jsonl")}
def metrics(label_of, ids):
    dets = next(iter(preds.values()))["pred"].keys()
    res = {}
    for d in dets:
        tp = fp = tn = fn = 0
        for i in ids:
            y = label_of[i] == "CHANGING"
            p = bool(preds[i]["pred"][d])
            if y and p: tp += 1
            elif y and not p: fn += 1
            elif p: fp += 1
            else: tn += 1
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        den = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
        mcc = (tp * tn - fp * fn) / den if den else 0.0
        res[d] = {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "precision": round(prec, 4),
                  "recall": round(rec, 4), "f1": round(f1, 4), "specificity": round(tn / (tn + fp), 4) if tn + fp else None,
                  "mcc": round(mcc, 4)}
    return res
ids = sorted(preds)
orig = {c["id"]: c["expected_outcome_original"] for c in out}
v11 = {c["id"]: c["expected_outcome"] for c in out}
ident_changing = {c["id"] for c in corrections}
excl = [i for i in ids if i not in ident_changing]
result = {"version": "1.1", "n_corrected": len(corrections),
          "ALL_180_original_labels": metrics(orig, ids),
          "ALL_180_v1_1_labels": metrics(v11, ids),
          "EXCL_15_corrected_pairs": metrics(orig, excl),
          "n_pending_adjudication": len(pending)}
json.dump(result, open("results/final/statistics/label_correction_metrics.json", "w"), indent=2, sort_keys=True)
print("corrections applied:", len(corrections), "| pending adjudication:", len(pending))
for name in ["ALL_180_original_labels", "ALL_180_v1_1_labels"]:
    print(name, {d: result[name][d]["mcc"] for d in ["relic_v2", "normalized_text_B", "textdiff"]})
