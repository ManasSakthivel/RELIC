"""
JCL-SemBench evaluation of RELIC and transparent text baselines (Agent 4).

Part 1 - rule-by-rule ablation of the normalised-text baseline on the OLD benchmark
(results/v2/v2_predictions.jsonl labels + mutant regeneration of relic_eval.v2_eval).
Report only: no rule is tuned from it.
Part 2 - JCL-SemBench: manifest-verified load, 8 detectors, abstention accounting,
metrics with Wilson / cluster-bootstrap CIs, paired exact McNemar + Holm.

Run:  python -m relic_eval.sembench_eval                     (SemBench evaluation)
      python -m relic_eval.sembench_eval --old-benchmark-ablation
Outputs (results/sembench/, deterministic apart from run_info.json):
      metrics.json  predictions.jsonl  paired_tests.json  run_info.json
Labels come ONLY from the benchmark's expected_outcome; detectors receive only
(original text, transformed text, original path).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
from scipy.stats import binomtest

from relic_eval import text_baselines as tb
from relic_eval.metrics import confusion, wilson
from relic_eval.subjects import ROOT

OUT = ROOT / "results" / "sembench"
V2_PRED = ROOT / "results" / "v2" / "v2_predictions.jsonl"
SEMBENCH = ROOT / "benchmarks" / "sembench"
FREEZE = OUT / "BASELINE_FREEZE.json"


def _load_old_mutants() -> tuple[list[tuple[str, str, str, str]], dict[str, dict]]:
    from relic_eval import v2_eval
    muts = [(r["mutation_id"], o, m, p) for r, o, m, p in v2_eval.iter_mutants(v2_eval.load_records())]
    with open(V2_PRED) as fh:
        truth = {d["mutation_id"]: d for d in map(json.loads, fh)}
    missing = [i for i, *_ in muts if i not in truth]
    if missing or len(muts) != len(truth):
        raise RuntimeError("old-benchmark regeneration does not match results/v2/v2_predictions.jsonl")
    return muts, truth


def _conf(muts, truth, det) -> dict:
    rows = [{"truth": truth[i]["truth"], "pred": {"d": det.predict(o, m, p).flagged}}
            for i, o, m, p in muts]
    c = confusion(rows, "d").as_dict()
    return {k: c[k] for k in ("tp", "fp", "fn", "tn", "precision", "recall", "specificity", "f1",
                              "no_prediction")}


def old_benchmark_ablation() -> dict:
    muts, truth = _load_old_mutants()
    n_pos = sum(truth[i]["truth"] for i, *_ in muts)
    out: dict = {"n": len(muts), "positives": n_pos, "negatives": len(muts) - n_pos,
                 "note": ("Report only. Labels = results/v2/v2_predictions.jsonl 'truth'. Rules "
                          "were frozen before SemBench; this table did not alter them."),
                 "reference": {}, "full": {}, "leave_one_out": {}, "add_one_in": {}}
    for d in tb.all_text_baselines():
        out["reference"][d.name] = _conf(muts, truth, d)
    for label, sort in (("A", False), ("B", True)):
        out["full"][f"normalized_text_{label}"] = _conf(muts, truth, tb.NormalizedTextDetector(sort))
    fp_ids = [i for i, o, m, p in muts if not truth[i]["truth"]
              and tb.NormalizedTextDetector(False).predict(o, m, p).flagged]
    out["normalized_text_A_false_positive_ids"] = fp_ids
    for r in tb.RULES:
        out["leave_one_out"][r] = _conf(
            muts, truth, tb.NormalizedTextDetector(False, tb.DEFAULT_RULES - {r}))
        out["add_one_in"][r] = _conf(muts, truth, tb.NormalizedTextDetector(False, {r}))
    out["leave_one_out"]["sort_keyword_operands(B minus sort = A)"] = out["full"]["normalized_text_A"]
    out["add_one_in"]["(no rule = raw lines)"] = _conf(muts, truth, tb.NormalizedTextDetector(False, set()))
    return out


def baseline_sha256() -> str:
    return hashlib.sha256((ROOT / "relic_eval" / "text_baselines.py").read_bytes()).hexdigest()


def write_freeze() -> dict:
    """Freeze the normalisation rules BEFORE any SemBench case is loaded. Refuses to
    overwrite an existing freeze (a re-freeze would defeat its purpose)."""
    if FREEZE.exists():
        raise RuntimeError(f"{FREEZE} already exists; the freeze is write-once")
    cases_present = (SEMBENCH / "cases.jsonl").exists()
    spec = {
        "schema": "relic-baseline-freeze/1",
        "purpose": ("Normalisation rules of relic_eval/text_baselines.py frozen before any "
                    "JCL-SemBench case was loaded by Agent 4; no rule may change afterwards."),
        "text_baselines_sha256": baseline_sha256(),
        "sembench_cases_jsonl_present_at_freeze": cases_present,
        "sembench_cases_loaded_by_agent4_before_freeze": False,
        **tb.frozen_rule_spec(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    with open(FREEZE, "w") as fh:
        json.dump(spec, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return spec


def verify_freeze() -> None:
    if not FREEZE.exists():
        raise RuntimeError("BASELINE_FREEZE.json missing: freeze must exist before SemBench is loaded")
    frozen = json.loads(FREEZE.read_text())
    if frozen["text_baselines_sha256"] != baseline_sha256():
        raise RuntimeError("relic_eval/text_baselines.py changed after the freeze")
    if frozen["rules_in_application_order"] != list(tb.RULES):
        raise RuntimeError("normalisation rule list differs from the freeze")


# ===========================================================================
# Part 2 - JCL-SemBench evaluation
# ===========================================================================

BOOTSTRAP_REPS = 10_000
BOOTSTRAP_SEED = 20261004          # same fixed seed as relic_eval.metrics
MODES = ("abstain_as_not_flagged", "abstain_excluded")
VALIDATED = "VALIDATED_BY_ORACLE_AND_ARGUMENT"
SUBSETS = ("ALL", "VALIDATED_BY_ORACLE_AND_ARGUMENT", "ORACLE_DISAGREES")
DETECTORS = ["raw_text", "textdiff", "textdiff_ignore_job_parameters",
             "normalized_text_A", "normalized_text_B",
             "relic_v1_0", "relic_v1_1", "relic_v2"]
PAIRS = [
    ("relic_v2", "relic_v1_1"), ("relic_v2", "relic_v1_0"), ("relic_v1_1", "relic_v1_0"),
    ("relic_v2", "normalized_text_A"), ("relic_v2", "normalized_text_B"),
    ("relic_v2", "textdiff_ignore_job_parameters"), ("relic_v2", "textdiff"), ("relic_v2", "raw_text"),
    ("relic_v1_1", "normalized_text_A"), ("relic_v1_1", "textdiff_ignore_job_parameters"),
    ("relic_v1_0", "normalized_text_A"),
    ("normalized_text_A", "textdiff_ignore_job_parameters"), ("normalized_text_B", "normalized_text_A"),
    ("textdiff_ignore_job_parameters", "textdiff"),
]
TRIVIAL = ["normalized_text_A", "normalized_text_B", "textdiff_ignore_job_parameters", "textdiff", "raw_text"]
OUTCOMES = {"PRESERVING": False, "CHANGING": True}   # expected_outcome -> "behaviour changed"
RESULT_FILES = ("metrics.json", "predictions.jsonl", "paired_tests.json")


def make_detectors() -> dict:
    """The fixed detector set. RELIC detectors are frozen (relic_eval.detectors, untouched)."""
    from relic_eval.detectors import RelicDetector
    dets = {d.name: d for d in tb.all_text_baselines()}
    dets["relic_v1_0"] = RelicDetector(legacy_v1_0=True)
    dets["relic_v1_1"] = RelicDetector(legacy_v1_0=False)
    dets["relic_v2"] = RelicDetector(legacy_v1_0=False, v2=True)
    assert set(dets) == set(DETECTORS)
    return dets


# ---------------------------------------------------------------------------
# cases + manifest
# ---------------------------------------------------------------------------

class SemBenchError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest(bench: Path) -> dict[str, str]:
    mf = bench / "MANIFEST.sha256"
    if not mf.exists():
        raise SemBenchError(f"{mf} not found")
    out: dict[str, str] = {}
    for ln in mf.read_text().splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        sha, _, rel = ln.strip().partition(" ")
        rel = rel.strip().lstrip("*").strip()
        if len(sha) != 64 or not rel:
            raise SemBenchError(f"malformed manifest line: {ln!r}")
        out[rel[2:] if rel.startswith("./") else rel] = sha.lower()
    return out


def verify_manifest(bench: Path) -> dict[str, str]:
    """Every manifest entry must exist and hash to the recorded SHA-256."""
    manifest = read_manifest(bench)
    bad = []
    for rel, sha in manifest.items():
        f = bench / rel
        if not f.is_file() or _sha256_file(f) != sha:
            bad.append(rel)
    if bad:
        raise SemBenchError(f"manifest verification failed for {len(bad)} file(s): {bad[:5]}")
    return manifest


@dataclass
class Case:
    id: str
    base_id: str
    category: str
    subcategory: str
    expected_outcome: str
    validation_status: str
    oracle_verdict: str
    original_rel: str
    transformed_rel: str
    original: str | None = None
    transformed: str | None = None
    unsupported: str | None = None

    @property
    def truth(self) -> bool:                     # label comes ONLY from the benchmark
        return OUTCOMES[self.expected_outcome]


def _file_field(rec: dict, which: str) -> tuple[str, str | None]:
    """(path relative to benchmarks/sembench, sha256) of a case's original/transformed file.
    Layout: cases/<id>/{original,transformed}.jcl; sha256 in '<which>_sha256'."""
    return f"cases/{rec['id']}/{which}.jcl", rec.get(f"{which}_sha256")


def oracle_label(rec: dict) -> str:
    v = rec.get("oracle_verdict")
    return str(v.get("label", "")) if isinstance(v, dict) else str(v or "")


def oracle_disagrees(rec: dict) -> bool:
    """The independent oracle contradicts the expected outcome (kept, never dropped)."""
    return rec.get("validation_status") == "ORACLE_DISAGREES"


def load_cases(bench: Path) -> list[Case]:
    manifest = verify_manifest(bench)
    cj = bench / "cases.jsonl"
    if not cj.exists():
        raise SemBenchError(f"{cj} not found")
    if "cases.jsonl" in manifest and manifest["cases.jsonl"] != _sha256_file(cj):
        raise SemBenchError("cases.jsonl hash differs from manifest")
    cases: list[Case] = []
    with open(cj) as fh:
        for ln in fh:
            if not ln.strip():
                continue
            rec = json.loads(ln)
            if rec["expected_outcome"] not in OUTCOMES:
                raise SemBenchError(f"case {rec['id']}: bad expected_outcome {rec['expected_outcome']!r}")
            o_rel, o_sha = _file_field(rec, "original")
            t_rel, t_sha = _file_field(rec, "transformed")
            c = Case(id=rec["id"], base_id=rec["base_id"], category=rec["category"],
                     subcategory=rec.get("subcategory") or "", expected_outcome=rec["expected_outcome"],
                     validation_status=rec.get("validation_status", ""),
                     oracle_verdict=oracle_label(rec),
                     original_rel=o_rel, transformed_rel=t_rel)
            c._oracle_disagrees = oracle_disagrees(rec)   # type: ignore[attr-defined]
            for rel, sha, attr in ((o_rel, o_sha, "original"), (t_rel, t_sha, "transformed")):
                f = bench / rel
                if not f.is_file():
                    raise SemBenchError(f"case {c.id}: missing file {rel}")
                actual = _sha256_file(f)
                if sha and sha.lower() != actual:
                    raise SemBenchError(f"case {c.id}: {rel} sha256 differs from cases.jsonl")
                if manifest.get(rel) != actual:
                    raise SemBenchError(f"case {c.id}: {rel} not covered by / differs from MANIFEST.sha256")
                try:
                    text = f.read_bytes().decode("utf-8")
                    if not text.strip():
                        c.unsupported = c.unsupported or f"empty {attr} file"
                    setattr(c, attr, text)
                except UnicodeDecodeError:
                    c.unsupported = c.unsupported or f"{attr} file is not valid UTF-8"
            cases.append(c)
    ids = [c.id for c in cases]
    if len(set(ids)) != len(ids):
        raise SemBenchError("duplicate case ids")
    return sorted(cases, key=lambda c: c.id)


# ---------------------------------------------------------------------------
# predictions
# ---------------------------------------------------------------------------

def predict_all(cases: list[Case], dets: dict) -> list[dict]:
    """One row per case. Detectors receive ONLY (original, transformed, path)."""
    rows = []
    for c in cases:
        pred: dict = {}
        status: dict = {}
        diag: dict = {}
        for name in DETECTORS:
            if c.unsupported:
                pred[name], status[name] = None, "UNSUPPORTED"
                continue
            try:
                p = dets[name].predict(c.original, c.transformed, c.original_rel)
            except Exception as exc:   # visible, never silently negative
                pred[name], status[name] = None, "ERROR"
                diag[name] = {"error": repr(exc)[:200]}
                continue
            pred[name] = p.flagged
            status[name] = p.status if p.flagged is not None or p.status != "OK" else "ABSTAIN"
            if name.startswith("relic") and "n_contracts_original" in p.detail:
                diag[name] = {"n_contracts_original": p.detail["n_contracts_original"]}
            elif p.status != "OK" and p.detail:
                diag[name] = {"error": str(p.detail.get("error", ""))[:200]}
        rows.append({
            "id": c.id, "base_id": c.base_id, "category": c.category, "subcategory": c.subcategory,
            "expected_outcome": c.expected_outcome, "truth": c.truth,
            "validation_status": c.validation_status, "oracle_verdict": c.oracle_verdict,
            "oracle_disagrees": bool(getattr(c, "_oracle_disagrees", False)),
            "pred": pred, "status": status, "diag": diag,
        })
    return rows


# ---------------------------------------------------------------------------
# statistics (rows: {"truth": bool, "cluster": str, "pred": {det: bool|None}})
# ---------------------------------------------------------------------------

def _r(x, k=4):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), k)


def derive(tp: int, fp: int, fn: int, tn: int) -> dict:
    def ratio(a, b):
        return None if b == 0 else a / b
    p, r, spec = ratio(tp, tp + fp), ratio(tp, tp + fn), ratio(tn, tn + fp)
    den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": _r(p), "recall": _r(r), "specificity": _r(spec),
        "fpr": _r(None if spec is None else 1 - spec),
        "f1": _r(ratio(2 * tp, 2 * tp + fp + fn)),
        "mcc": _r(None if den == 0 else (tp * tn - fp * fn) / den),
        "balanced_accuracy": _r(None if r is None or spec is None else (r + spec) / 2),
        "accuracy": _r(ratio(tp + tn, tp + fp + fn + tn)),
        "precision_ci95": wilson(tp, tp + fp), "recall_ci95": wilson(tp, tp + fn),
        "specificity_ci95": wilson(tn, tn + fp), "fpr_ci95": wilson(fp, fp + tn),
        "accuracy_ci95": wilson(tp + tn, tp + fp + fn + tn),
    }


def _arrays(rows: list[dict], det: str, mode: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    truth = np.array([r["truth"] for r in rows], dtype=bool)
    flag = np.array([bool(r["pred"][det]) if r["pred"][det] is not None else False for r in rows])
    used = np.array([(r["pred"][det] is not None) or mode == "abstain_as_not_flagged" for r in rows])
    return truth, flag, used


def confusion_block(rows: list[dict], det: str, mode: str) -> dict:
    truth, flag, used = _arrays(rows, det, mode)
    n_abst = sum(r["pred"][det] is None for r in rows)
    out = derive(int((truth & flag & used).sum()), int((~truth & flag & used).sum()),
                 int((truth & ~flag & used).sum()), int((~truth & ~flag & used).sum()))
    out.update({"n_cases": len(rows), "n_scored": int(used.sum()), "n_abstain": n_abst,
                "coverage": _r(1 - n_abst / len(rows)) if rows else None})
    return out


def _vec(counts: np.ndarray) -> dict[str, np.ndarray]:
    """counts (..., 4) = tp, fp, fn, tn  ->  vectorised metrics (nan when undefined)."""
    tp, fp, fn, tn = (counts[..., i].astype(float) for i in range(4))
    with np.errstate(divide="ignore", invalid="ignore"):
        rec = tp / (tp + fn)
        spec = tn / (tn + fp)
        den = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
        return {"f1": 2 * tp / (2 * tp + fp + fn), "mcc": (tp * tn - fp * fn) / den,
                "balanced_accuracy": (rec + spec) / 2, "accuracy": (tp + tn) / (tp + fp + fn + tn)}


def _cluster_counts(truth, flag, used, cidx, n_clusters) -> np.ndarray:
    out = np.zeros((n_clusters, 4), dtype=np.int64)
    for k, m in enumerate((truth & flag, ~truth & flag, truth & ~flag, ~truth & ~flag)):
        out[:, k] = np.bincount(cidx[m & used], minlength=n_clusters)
    return out


def _pct(x: np.ndarray) -> dict:
    ok = x[~np.isnan(x)]
    if len(ok) == 0:
        return {"ci95": None, "n_undefined_reps": int(len(x))}
    lo, hi = np.percentile(ok, [2.5, 97.5])
    return {"ci95": [_r(lo), _r(hi)], "n_undefined_reps": int(len(x) - len(ok))}


class Bootstrap:
    """Cluster bootstrap (clusters = base_id); one resample index matrix shared by
    all detectors and pairs, so paired differences are computed on identical resamples."""

    def __init__(self, rows: list[dict], reps: int = BOOTSTRAP_REPS, seed: int = BOOTSTRAP_SEED):
        self.rows = rows
        clusters = sorted({r["cluster"] for r in rows})
        self.n_clusters = len(clusters)
        pos = {c: i for i, c in enumerate(clusters)}
        self.cidx = np.array([pos[r["cluster"]] for r in rows], dtype=np.int64)
        self.reps, self.seed = reps, seed
        if self.n_clusters:
            self.idx = np.random.default_rng(seed).integers(0, self.n_clusters, size=(reps, self.n_clusters))

    def _boot(self, cc: np.ndarray) -> dict[str, np.ndarray]:
        total = np.stack([cc[:, k][self.idx].sum(axis=1) for k in range(4)], axis=-1)
        return _vec(total)

    def single(self, det: str, mode: str) -> dict:
        if not self.n_clusters:
            return {}
        t, f, u = _arrays(self.rows, det, mode)
        cc = _cluster_counts(t, f, u, self.cidx, self.n_clusters)
        b = self._boot(cc)
        return {m: _pct(b[m]) for m in ("f1", "mcc", "balanced_accuracy", "accuracy")}

    def pair(self, a: str, b_: str, mode: str) -> dict:
        if not self.n_clusters:
            return {}
        ta, fa, ua = _arrays(self.rows, a, mode)
        tb_, fb, ub = _arrays(self.rows, b_, mode)
        used = ua & ub                                   # jointly covered cases only
        cca = _cluster_counts(ta, fa, used, self.cidx, self.n_clusters)
        ccb = _cluster_counts(tb_, fb, used, self.cidx, self.n_clusters)
        ba, bb = self._boot(cca), self._boot(ccb)
        pa, pb = _vec(cca.sum(axis=0)), _vec(ccb.sum(axis=0))
        out = {}
        for m in ("mcc", "accuracy", "balanced_accuracy", "f1"):
            d = {"point": _r(pa[m] - pb[m])}
            d.update(_pct(ba[m] - bb[m]))
            out[f"diff_{m}"] = d
        return out


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar p-value (binomial test on the discordant pairs)."""
    n = b + c
    return 1.0 if n == 0 else float(binomtest(min(b, c), n, 0.5, alternative="two-sided").pvalue)


def holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj


def paired_test(rows: list[dict], a: str, b: str, mode: str, boot: Bootstrap) -> dict:
    """Exact McNemar on correctness (pred == truth) + effect sizes + paired cluster-bootstrap CIs."""
    ta, fa, ua = _arrays(rows, a, mode)
    _t, fb, ub = _arrays(rows, b, mode)
    used = ua & ub
    ok_a, ok_b = (fa == ta) & used, (fb == ta) & used
    bw = ok_a & ~ok_b            # a right, b wrong
    cw = ~ok_a & ok_b & used     # a wrong, b right

    def disc(mask):
        x, y = int((bw & mask).sum()), int((cw & mask).sum())
        return {"a_right_b_wrong": x, "a_wrong_b_right": y, "p_exact": _r(mcnemar_exact(x, y), 6)}

    x, y = int(bw.sum()), int(cw.sum())
    out = {
        "a": a, "b": b, "n_paired": int(used.sum()),
        "a_right_b_wrong": x, "a_wrong_b_right": y,
        "both_right": int((ok_a & ok_b).sum()), "both_wrong": int((~ok_a & ~ok_b & used).sum()),
        "p_exact": _r(mcnemar_exact(x, y), 6),
        "exploratory_on_changing": disc(ta), "exploratory_on_preserving": disc(~ta),
        "effect_size": {
            "cohens_g": _r(abs(x / (x + y) - 0.5) if x + y else 0.0),
            "discordant_odds_ratio_haldane": _r((x + 0.5) / (y + 0.5)),
            "note": "odds ratio > 1 favours a; Haldane-Anscombe 0.5 correction",
        },
    }
    out.update(boot.pair(a, b, mode))
    return out


def paired_family(rows: list[dict], mode: str, boot: Bootstrap, pairs=PAIRS) -> dict:
    tests = [paired_test(rows, a, b, mode, boot) for a, b in pairs]
    for t, p in zip(tests, holm([t["p_exact"] for t in tests])):
        t["p_holm"] = _r(p, 6)
    return {"family_size": len(tests), "correction": "Holm-Bonferroni over this family", "tests": tests}


def verdict(t: dict) -> str:
    """Pre-specified reading rule for a (RELIC a vs trivial b) test."""
    dm = t.get("diff_mcc", {}).get("ci95")
    sig = t["p_holm"] is not None and t["p_holm"] < 0.05
    if t["a_right_b_wrong"] == t["a_wrong_b_right"]:
        return "NOT_DISTINGUISHABLE"
    a_better = t["a_right_b_wrong"] > t["a_wrong_b_right"]
    if sig and a_better and dm and dm[0] > 0:
        return "A_BETTER"
    if sig and not a_better and dm and dm[1] < 0:
        return "B_BETTER"
    if sig:
        return "A_BETTER_p_only" if a_better else "B_BETTER_p_only"
    return "NOT_DISTINGUISHABLE"


def population_block(rows: list[dict], with_groups: bool = True) -> tuple[dict, dict]:
    """(metrics block, paired-tests block) for one subset of rows."""
    boot = Bootstrap(rows)
    block: dict = {
        "n_cases": len(rows), "n_changing": sum(r["truth"] for r in rows),
        "n_preserving": sum(not r["truth"] for r in rows), "n_clusters": boot.n_clusters,
        "bootstrap": {"reps": BOOTSTRAP_REPS, "seed": BOOTSTRAP_SEED, "cluster": "base_id",
                      "interval": "percentile 95%"},
        "modes": {},
    }
    paired: dict = {}
    for mode in MODES:
        dets = {}
        for d in DETECTORS:
            b = confusion_block(rows, d, mode)
            b["bootstrap"] = boot.single(d, mode) if rows else {}
            dets[d] = b
        block["modes"][mode] = {"detectors": dets}
        paired[mode] = paired_family(rows, mode, boot) if rows else {}
        if with_groups:
            for key, field in (("per_category", "category"), ("per_subcategory", "subcategory")):
                grp = {}
                for v in sorted({r[field] for r in rows}):
                    sub = [r for r in rows if r[field] == v]
                    grp[v] = {"n_cases": len(sub), "n_changing": sum(r["truth"] for r in sub),
                              "detectors": {d: confusion_block(sub, d, mode) for d in DETECTORS}}
                block["modes"][mode][key] = grp
    return block, paired


# ---------------------------------------------------------------------------
# old benchmark context (development set; RELIC predictions are the committed v2 ones)
# ---------------------------------------------------------------------------

def old_benchmark_rows() -> list[dict]:
    muts, truth = _load_old_mutants()
    live = {d.name: d for d in tb.all_text_baselines() if d.name in
            ("raw_text", "normalized_text_A", "normalized_text_B")}
    rows = []
    for i, o, m, p in muts:
        t = truth[i]
        pred = {k: t["pred"][k] for k in ("relic_v1_0", "relic_v1_1", "relic_v2", "textdiff",
                                         "textdiff_ignore_job_parameters")}
        for k, d in live.items():
            pred[k] = d.predict(o, m, p).flagged
        rows.append({"id": i, "truth": bool(t["truth"]), "cluster": i.rsplit("/", 2)[0],
                     "category": t["operator"], "subcategory": "", "pred": pred})
    return sorted(rows, key=lambda r: r["id"])


def old_benchmark_context() -> tuple[dict, dict]:
    rows = old_benchmark_rows()
    boot = Bootstrap(rows)
    dets = ["raw_text", "textdiff", "textdiff_ignore_job_parameters", "normalized_text_A",
            "normalized_text_B", "relic_v1_0", "relic_v1_1", "relic_v2"]
    assert dets == DETECTORS
    mode = MODES[0]
    block = {
        "note": ("DEVELOPMENT benchmark (results/final records, results/v2/v2_predictions.jsonl); all "
                 "subjects were inspected while fixing RELIC, so this is context, not validation. "
                 "Clusters = source file."),
        "n_cases": len(rows), "n_changing": sum(r["truth"] for r in rows),
        "n_preserving": sum(not r["truth"] for r in rows), "n_clusters": boot.n_clusters,
        "detectors": {d: {**confusion_block(rows, d, mode), "bootstrap": boot.single(d, mode)} for d in DETECTORS},
    }
    return block, {mode: paired_family(rows, mode, boot)}


def headline(paired: dict, old_paired: dict) -> dict:
    out: dict = {"rule": ("RELIC detector 'a' is called distinguishable from a trivial rule 'b' only if "
                          "Holm-adjusted exact McNemar p < 0.05 AND the paired cluster-bootstrap 95% CI "
                          "of the MCC difference excludes 0 in the same direction."),
                 "relic_v2_vs_trivial": {}}
    def pick(fam):
        return {t["b"]: t for t in fam.get("tests", []) if t["a"] == "relic_v2" and t["b"] in TRIVIAL}
    srcs = {f"sembench/{s}": paired[s][MODES[0]] for s in paired if paired[s]}
    srcs["old_benchmark"] = old_paired[MODES[0]]
    for name, fam in srcs.items():
        out["relic_v2_vs_trivial"][name] = {
            b: {"verdict": verdict(t), "a_right_b_wrong": t["a_right_b_wrong"],
                "a_wrong_b_right": t["a_wrong_b_right"], "p_holm": t["p_holm"],
                "diff_mcc": t.get("diff_mcc")} for b, t in pick(fam).items()}
    return out


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def _cluster_rows(rows: list[dict]) -> list[dict]:
    return [{**r, "cluster": r["base_id"]} for r in rows]


def subset_rows(rows: list[dict], subset: str) -> list[dict]:
    if subset == "ALL":
        return rows
    if subset == "VALIDATED_BY_ORACLE_AND_ARGUMENT":
        return [r for r in rows if r["validation_status"] == VALIDATED]
    if subset == "ORACLE_DISAGREES":
        return [r for r in rows if r["oracle_disagrees"]]
    raise ValueError(subset)


def run(bench: Path = SEMBENCH, out: Path = OUT, dets: dict | None = None) -> dict:
    verify_freeze()                                   # BEFORE any case is loaded
    cases = load_cases(bench)
    rows = predict_all(cases, dets or make_detectors())
    crow = _cluster_rows(rows)
    populations: dict = {}
    paired: dict = {}
    for s in SUBSETS:
        populations[s], paired[s] = population_block(subset_rows(crow, s))
    status = {d: dict(Counter(r["status"][d] for r in rows)) for d in DETECTORS}
    relic_zero = {d: sum(1 for r in rows if r["diag"].get(d, {}).get("n_contracts_original") == 0)
                  for d in ("relic_v1_0", "relic_v1_1", "relic_v2")}
    old_block, old_paired = old_benchmark_context()
    paired_out = {"schema": "relic-sembench-paired/1",
                  "test": "exact two-sided McNemar (binomial) on per-case correctness",
                  "subsets": paired, "old_benchmark": old_paired}
    metrics = {
        "schema": "relic-sembench-metrics/1",
        "provenance": {
            "n_cases": len(cases),
            "cases_jsonl_sha256": _sha256_file(bench / "cases.jsonl"),
            "manifest_sha256": _sha256_file(bench / "MANIFEST.sha256"),
            "manifest_entries_verified": len(read_manifest(bench)),
            "text_baselines_sha256": baseline_sha256(),
            "detectors": DETECTORS,
            "scoring": {"abstain_as_not_flagged": "no prediction counts as 'not flagged'",
                        "abstain_excluded": "cases without a prediction are dropped (coverage reported); "
                                            "paired tests use jointly covered cases"},
        },
        "status_counts_all_cases": status,
        "relic_no_contracts_extracted_in_original": relic_zero,
        "populations": populations,
        "old_benchmark_context": old_block,
        "headline": headline(paired, old_paired),
    }
    write_results(out, metrics, rows, paired_out)
    return {"metrics": metrics, "rows": rows, "paired": paired_out}


def write_results(out: Path, metrics: dict, rows: list[dict], paired: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "metrics.json", "w") as fh:
        json.dump(metrics, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(out / "paired_tests.json", "w") as fh:
        json.dump(paired, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(out / "predictions.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                text=True, check=False).stdout.strip() or None
    except OSError:
        commit = None
    with open(out / "run_info.json", "w") as fh:
        json.dump({"timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "python": sys.version.split()[0], "platform": platform.platform(),
                   "numpy": np.__version__, "scipy": scipy.__version__, "git_commit": commit},
                  fh, indent=2, sort_keys=True)
        fh.write("\n")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--old-benchmark-ablation", action="store_true")
    ap.add_argument("--freeze", action="store_true", help="write results/sembench/BASELINE_FREEZE.json")
    ap.add_argument("--bench", type=Path, default=SEMBENCH)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    if args.freeze:
        print(write_freeze()["text_baselines_sha256"])
        return
    if args.old_benchmark_ablation:
        res = old_benchmark_ablation()
        OUT.mkdir(parents=True, exist_ok=True)
        with open(OUT / "old_benchmark_ablation.json", "w") as fh:
            json.dump(res, fh, indent=2, sort_keys=True)
            fh.write("\n")
        for k, v in res["reference"].items():
            print(f"{k:34s} TP {v['tp']} FP {v['fp']} FN {v['fn']} TN {v['tn']} spec {v['specificity']}")
        return
    try:
        res = run(args.bench, args.out)
    except SemBenchError as exc:
        sys.exit(f"SEMBENCH EVALUATION CANNOT RUN: {exc}")
    for s in SUBSETS:
        p = res["metrics"]["populations"][s]
        print(f"== {s}: n={p['n_cases']} changing={p['n_changing']} clusters={p['n_clusters']}")
        for d, b in p["modes"][MODES[0]]["detectors"].items():
            print(f"  {d:32s} TP {b['tp']:4d} FP {b['fp']:4d} FN {b['fn']:4d} TN {b['tn']:4d} "
                  f"MCC {b['mcc']} F1 {b['f1']} abst {b['n_abstain']}")


if __name__ == "__main__":
    main()
