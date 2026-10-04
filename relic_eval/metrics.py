"""
Metric computation for the authoritative evaluation.

All metrics are computed from per-mutant records (ground truth + prediction).
Formulas:

    precision   = TP / (TP + FP)
    recall      = TP / (TP + FN)          (= detection rate)
    F1          = 2 * P * R / (P + R)     (= 2TP / (2TP + FP + FN))
    specificity = TN / (TN + FP)
    FPR         = FP / (FP + TN)

Undefined ratios (0/0) are reported as ``None``, never as 0 or 1.

Uncertainty:
  * Wilson 95% intervals for precision, recall and specificity (binomial
    proportions; they ignore the clustering of mutants within files and are
    therefore optimistic).
  * File-level cluster bootstrap (10,000 resamples, fixed seed) for F1 and for
    paired F1 differences between detectors. Mutants derived from the same JCL
    file are not independent, so files — not mutants — are resampled.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

BOOTSTRAP_REPS = 10_000
BOOTSTRAP_SEED = 20261004


@dataclass
class Confusion:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    no_prediction: int = 0     # detector returned no prediction (error / not run)

    @property
    def n(self) -> int:
        return self.tp + self.fp + self.fn + self.tn

    def as_dict(self) -> dict:
        p = ratio(self.tp, self.tp + self.fp)
        r = ratio(self.tp, self.tp + self.fn)
        f1 = ratio(2 * self.tp, 2 * self.tp + self.fp + self.fn)
        spec = ratio(self.tn, self.tn + self.fp)
        d = {
            "tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn,
            "n": self.n, "positives": self.tp + self.fn, "negatives": self.tn + self.fp,
            "no_prediction": self.no_prediction,
            "precision": rnd(p), "recall": rnd(r), "f1": rnd(f1),
            "specificity": rnd(spec), "fpr": rnd(None if spec is None else 1 - spec),
            "precision_ci95": wilson(self.tp, self.tp + self.fp),
            "recall_ci95": wilson(self.tp, self.tp + self.fn),
            "specificity_ci95": wilson(self.tn, self.tn + self.fp),
        }
        check_consistency(d)
        return d


def ratio(a: float, b: float) -> float | None:
    return None if b == 0 else a / b


def rnd(x: float | None, k: int = 4) -> float | None:
    return None if x is None else round(x, k)


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def check_consistency(d: dict) -> None:
    """Hard invariants: any violation is a pipeline bug, never a reportable result."""
    assert d["tp"] >= 0 and d["fp"] >= 0 and d["fn"] >= 0 and d["tn"] >= 0
    assert d["n"] == d["tp"] + d["fp"] + d["fn"] + d["tn"]
    assert d["positives"] + d["negatives"] == d["n"]
    p, r, f1 = d["precision"], d["recall"], d["f1"]
    if p is not None and r is not None and (p + r) > 0 and f1 is not None:
        f1_pr = 2 * p * r / (p + r)
        assert abs(f1_pr - f1) < 2e-4, (f1_pr, f1)
    if d["tp"] == 0 and (d["fp"] + d["fn"]) > 0:
        assert f1 == 0.0
    for key in ("precision", "recall", "f1", "specificity", "fpr"):
        v = d[key]
        assert v is None or 0.0 <= v <= 1.0, (key, v)


def confusion(records: list[dict], detector: str, missing: str = "negative") -> Confusion:
    """
    records: dicts with 'truth' (bool) and 'pred' (dict detector -> bool|None).
    missing: how to score a missing prediction —
       "negative": as "not flagged" (used for RELIC/baselines: an error is a miss)
       "exclude":  drop the record (used for LLM baselines; coverage reported)
    """
    c = Confusion()
    for r in records:
        y = r["truth"]
        p = r["pred"].get(detector)
        if p is None:
            c.no_prediction += 1
            if missing == "exclude":
                continue
            p = False
        if y and p:
            c.tp += 1
        elif y:
            c.fn += 1
        elif p:
            c.fp += 1
        else:
            c.tn += 1
    return c


def _counts(records: list[dict], detector: str, missing: str) -> tuple[int, int, int]:
    c = confusion(records, detector, missing)
    return c.tp, c.fp, c.fn


def cluster_bootstrap(records: list[dict], detectors: list[str], pairs: list[tuple[str, str]],
                      missing: str = "negative", reps: int = BOOTSTRAP_REPS,
                      seed: int = BOOTSTRAP_SEED) -> dict:
    """Percentile 95% CIs for F1 and paired F1 differences, resampling files."""
    by_file: dict[str, list[dict]] = {}
    for r in records:
        by_file.setdefault(r["cluster"], []).append(r)
    files = sorted(by_file)
    if len(files) < 2:
        return {"n_clusters": len(files), "f1_ci95": {}, "diff_ci95": {}}
    rng = random.Random(seed)
    all_dets = sorted(set(detectors) | {x for p in pairs for x in p})
    # per-file (tp, fp, fn) for each detector; resampling then only sums counts
    counts = {d: [_counts(by_file[f], d, missing) for f in files] for d in all_dets}
    f1s: dict[str, list[float]] = {d: [] for d in detectors}
    diffs: dict[str, list[float]] = {f"{a}-{b}": [] for a, b in pairs}
    nf = len(files)
    for _ in range(reps):
        idx = [rng.randrange(nf) for _k in range(nf)]
        cache: dict[str, float | None] = {}
        for d in all_dets:
            tp = fp = fn = 0
            cd = counts[d]
            for i in idx:
                a, b, c = cd[i]
                tp += a
                fp += b
                fn += c
            cache[d] = ratio(2 * tp, 2 * tp + fp + fn)
        for d in detectors:
            if cache[d] is not None:
                f1s[d].append(cache[d])
        for a, b in pairs:
            if cache[a] is not None and cache[b] is not None:
                diffs[f"{a}-{b}"].append(cache[a] - cache[b])

    def pct(xs: list[float]) -> list[float] | None:
        if not xs:
            return None
        xs = sorted(xs)
        lo = xs[int(0.025 * (len(xs) - 1))]
        hi = xs[int(0.975 * (len(xs) - 1))]
        return [round(lo, 4), round(hi, 4)]

    return {
        "n_clusters": len(files),
        "reps": reps,
        "seed": seed,
        "f1_ci95": {d: pct(v) for d, v in f1s.items()},
        "diff_ci95": {k: pct(v) for k, v in diffs.items()},
    }
