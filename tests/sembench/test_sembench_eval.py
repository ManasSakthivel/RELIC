"""
Tests of the SemBench evaluation harness (relic_eval.sembench_eval).

* synthetic mini-benchmark (tmp dir): manifest verification, determinism (run twice),
  counts recomputed independently of the metric code, label blindness;
* real results (results/sembench/*, benchmarks/sembench) are checked when present.
"""

import hashlib
import itertools
import json
import math
from pathlib import Path

import pytest

from relic_eval import sembench_eval as se

ROOT = Path(__file__).resolve().parents[2]

JCL = (
    "//J{n} JOB (ACCT),'T',CLASS=A\n"
    "//S1 EXEC PGM=PROGA\n"
    "//OUT DD DSN=T{n}.OUT,DISP=(NEW,CATLG),UNIT=SYSDA,SPACE=(TRK,1)\n"
    "//S2 EXEC PGM=PROGB\n"
    "//IN DD DSN=T{n}.OUT,DISP=SHR\n"
)


def _variants(n):
    base = JCL.format(n=n)
    return {
        ("COSMETIC", "comment"): ("PRESERVING", base.replace("//S2", "//* note\n//S2")),
        ("COSMETIC", "case"): ("PRESERVING", base.replace("EXEC PGM=PROGB", "exec pgm=progb")),
        ("COSMETIC", "operand_order"): ("PRESERVING",
                                       base.replace("DSN=T%d.OUT,DISP=SHR" % n, "DISP=SHR,DSN=T%d.OUT" % n)),
        ("ORDERING", "swap"): ("CHANGING", base.replace(
            "//S1 EXEC PGM=PROGA\n//OUT DD DSN=T%d.OUT,DISP=(NEW,CATLG),UNIT=SYSDA,SPACE=(TRK,1)\n" % n, "")
            + "//S1 EXEC PGM=PROGA\n//OUT DD DSN=T%d.OUT,DISP=(NEW,CATLG),UNIT=SYSDA,SPACE=(TRK,1)\n" % n),
        ("DATASET", "rename"): ("CHANGING", base.replace("DSN=T%d.OUT,DISP=(NEW" % n, "DSN=X%d.OUT,DISP=(NEW" % n)),
    }


def make_bench(root: Path, n_bases=12) -> Path:
    bench = root / "sembench"
    (bench / "cases").mkdir(parents=True)
    manifest, recs = {}, []
    for n in range(n_bases):
        base = JCL.format(n=n)
        for (cat, sub), (outcome, text) in _variants(n).items():
            cid = f"b{n:02d}_{cat}_{sub}"
            d = bench / "cases" / cid
            d.mkdir()
            (d / "original.jcl").write_text(base)
            (d / "transformed.jcl").write_text(text)
            rel_o, rel_t = f"cases/{cid}/original.jcl", f"cases/{cid}/transformed.jcl"
            sha = {k: hashlib.sha256((bench / k).read_bytes()).hexdigest() for k in (rel_o, rel_t)}
            manifest.update(sha)
            disagree = (n == 0 and sub == "swap")
            status = "ORACLE_DISAGREES" if disagree else (
                "UNVALIDATED" if n % 3 == 0 else se.VALIDATED)
            recs.append({
                "id": cid, "base_id": f"b{n:02d}", "category": cat, "subcategory": sub,
                "expected_outcome": outcome,
                "validation_status": status,
                "oracle_verdict": {"label": "EQUIVALENT" if (outcome == "PRESERVING") != disagree else "DIFFERENT"},
                "original_sha256": sha[rel_o], "transformed_sha256": sha[rel_t]})
    (bench / "cases.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    manifest["cases.jsonl"] = hashlib.sha256((bench / "cases.jsonl").read_bytes()).hexdigest()
    (bench / "MANIFEST.sha256").write_text("".join(f"{v}  {k}\n" for k, v in sorted(manifest.items())))
    return bench


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    root = tmp_path_factory.mktemp("synth")
    bench = make_bench(root)
    out1, out2 = root / "out1", root / "out2"
    r1 = se.run(bench, out1)
    se.run(bench, out2)
    return {"bench": bench, "out1": out1, "out2": out2, "res": r1}


def test_manifest_verification_detects_tampering(tmp_path):
    bench = make_bench(tmp_path, n_bases=2)
    assert len(se.verify_manifest(bench)) == 2 * 5 * 2 + 1
    victim = bench / "cases" / "b00_COSMETIC_comment" / "transformed.jcl"
    victim.write_text(victim.read_text() + "//* tampered\n")
    with pytest.raises(se.SemBenchError, match="manifest verification failed"):
        se.load_cases(bench)


def test_missing_manifest_fails_clearly(tmp_path):
    bench = make_bench(tmp_path, n_bases=1)
    (bench / "MANIFEST.sha256").unlink()
    with pytest.raises(se.SemBenchError, match="MANIFEST"):
        se.load_cases(bench)


def test_file_not_in_manifest_is_rejected(tmp_path):
    bench = make_bench(tmp_path, n_bases=1)
    lines = (bench / "MANIFEST.sha256").read_text().splitlines()
    kept = [ln for ln in lines if "b00_ORDERING_swap/transformed" not in ln]
    (bench / "MANIFEST.sha256").write_text("\n".join(kept) + "\n")
    with pytest.raises(se.SemBenchError, match="not covered"):
        se.load_cases(bench)


def test_determinism(synth):
    for name in se.RESULT_FILES:
        assert (synth["out1"] / name).read_bytes() == (synth["out2"] / name).read_bytes(), name
    assert (synth["out1"] / "run_info.json").exists()      # separate, not compared


def _independent_counts(pred_path, det, subset=lambda r: True, drop_abstain=False):
    tp = fp = fn = tn = 0
    for ln in open(pred_path):
        r = json.loads(ln)
        if not subset(r):
            continue
        y = r["expected_outcome"] == "CHANGING"          # recomputed from the benchmark field
        p = r["pred"][det]
        if p is None:
            if drop_abstain:
                continue
            p = False
        tp += y and p
        fn += y and not p
        fp += (not y) and p
        tn += (not y) and not p
    return tp, fp, fn, tn


def test_counts_recomputed_independently(synth):
    m = json.loads((synth["out1"] / "metrics.json").read_text())
    pred = synth["out1"] / "predictions.jsonl"
    subsets = {"ALL": lambda r: True,
               "VALIDATED_BY_ORACLE_AND_ARGUMENT": lambda r: r["validation_status"] == se.VALIDATED,
               "ORACLE_DISAGREES": lambda r: r["oracle_disagrees"]}
    for s, f in subsets.items():
        for mode, drop in (("abstain_as_not_flagged", False), ("abstain_excluded", True)):
            for det, b in m["populations"][s]["modes"][mode]["detectors"].items():
                assert (b["tp"], b["fp"], b["fn"], b["tn"]) == _independent_counts(pred, det, f, drop), (s, mode, det)


def test_metric_formulas_from_counts(synth):
    m = json.loads((synth["out1"] / "metrics.json").read_text())
    for det, b in m["populations"]["ALL"]["modes"]["abstain_as_not_flagged"]["detectors"].items():
        tp, fp, fn, tn = b["tp"], b["fp"], b["fn"], b["tn"]
        if tp + fp and tp + fn:
            assert b["precision"] == round(tp / (tp + fp), 4)
            assert b["recall"] == round(tp / (tp + fn), 4)
        den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
        assert b["mcc"] == (None if den == 0 else round((tp * tn - fp * fn) / den, 4))
        assert b["accuracy"] == round((tp + tn) / (tp + fp + fn + tn), 4)


def test_oracle_disagreement_subset_kept_not_dropped(synth):
    m = json.loads((synth["out1"] / "metrics.json").read_text())
    assert m["populations"]["ALL"]["n_cases"] == 12 * 5
    assert m["populations"]["ORACLE_DISAGREES"]["n_cases"] == 1
    assert m["provenance"]["n_cases"] == 60


def test_mcnemar_and_holm_known_values():
    assert se.mcnemar_exact(0, 0) == 1.0
    assert se.mcnemar_exact(5, 5) == 1.0
    assert se.mcnemar_exact(0, 10) == pytest.approx(2 * 0.5 ** 10)
    assert se.mcnemar_exact(1, 9) == pytest.approx(0.021484375)
    assert se.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert se.holm([0.5]) == [0.5]


def test_paired_discordants_match_manual(synth):
    pred = [json.loads(ln) for ln in open(synth["out1"] / "predictions.jsonl")]
    paired = json.loads((synth["out1"] / "paired_tests.json").read_text())
    fam = paired["subsets"]["ALL"]["abstain_as_not_flagged"]
    assert fam["family_size"] == len(se.PAIRS)
    for t in fam["tests"]:
        a, b = t["a"], t["b"]
        x = sum((r["pred"][a] is True) == r["truth"] and (r["pred"][b] is True) != r["truth"] for r in pred)
        y = sum((r["pred"][a] is True) != r["truth"] and (r["pred"][b] is True) == r["truth"] for r in pred)
        assert (t["a_right_b_wrong"], t["a_wrong_b_right"]) == (x, y)
        assert 0 <= t["p_exact"] <= t["p_holm"] <= 1


def test_labels_never_read_from_detector_output(tmp_path):
    """Flipping / corrupting detector output must not change any label."""
    bench = make_bench(tmp_path, n_bases=2)
    cases = se.load_cases(bench)
    labels = {c.id: c.truth for c in cases}
    seen = []

    class Spy:
        def __init__(self, name, ans):
            self.name, self.ans = name, ans

        def predict(self, original, mutated, path):
            seen.append((original, mutated, path))
            from relic_eval.detectors import Prediction
            return Prediction(self.ans, detail={"label": "CHANGING", "truth": True})

    for ans in (True, False, None):
        dets = {n: Spy(n, ans) for n in se.DETECTORS}
        rows = se.predict_all(cases, dets)
        assert {r["id"]: r["truth"] for r in rows} == labels
    assert all(isinstance(x, str) for t in seen for x in t)       # only texts + path
    assert len(seen[0]) == 3


def test_detector_exception_is_visible_abstention(tmp_path):
    bench = make_bench(tmp_path, n_bases=1)
    cases = se.load_cases(bench)

    class Boom:
        name = "x"

        def predict(self, *a):
            raise RuntimeError("boom")

    dets = {n: Boom() for n in se.DETECTORS}
    rows = se.predict_all(cases, dets)
    assert all(r["pred"][d] is None and r["status"][d] == "ERROR" for r in rows for d in se.DETECTORS)
    b = se.confusion_block([{**r, "cluster": r["base_id"]} for r in rows], "relic_v2", "abstain_as_not_flagged")
    assert b["n_abstain"] == len(rows) and b["coverage"] == 0.0 and b["fp"] == 0
    assert b["fn"] == sum(r["truth"] for r in rows)                # abstain-as-not-flagged: misses
    e = se.confusion_block([{**r, "cluster": r["base_id"]} for r in rows], "relic_v2", "abstain_excluded")
    assert e["n_scored"] == 0 and e["tp"] + e["fn"] == 0


def test_freeze_is_enforced(monkeypatch, tmp_path):
    fake = tmp_path / "BASELINE_FREEZE.json"
    fake.write_text(json.dumps({"text_baselines_sha256": "0" * 64, "rules_in_application_order": []}))
    monkeypatch.setattr(se, "FREEZE", fake)
    with pytest.raises(RuntimeError, match="changed after the freeze"):
        se.verify_freeze()


# ------------------------------------------------------------------ real artefacts

FREEZE = ROOT / "results" / "sembench" / "BASELINE_FREEZE.json"


def test_committed_freeze_matches_source():
    fz = json.loads(FREEZE.read_text())
    assert fz["text_baselines_sha256"] == hashlib.sha256(
        (ROOT / "relic_eval" / "text_baselines.py").read_bytes()).hexdigest()
    assert fz["rules_in_application_order"] == list(se.tb.RULES)


# real SemBench results (results/sembench/*): skipped only if the benchmark itself is absent
BENCH = ROOT / "benchmarks" / "sembench"
RES = ROOT / "results" / "sembench"
needs_bench = pytest.mark.skipif(not (BENCH / "cases.jsonl").exists(), reason="SemBench not present")

# (tp, fp, fn, tn), abstain-as-not-flagged. Pinned from the committed run; verified below
# against predictions.jsonl by code that shares nothing with the metric functions.
PINNED = {
    "ALL": {"raw_text": (78, 77, 15, 10), "textdiff": (78, 60, 15, 27),
            "textdiff_ignore_job_parameters": (78, 49, 15, 38), "normalized_text_A": (78, 35, 15, 52),
            "normalized_text_B": (78, 28, 15, 59), "relic_v1_0": (15, 2, 78, 85),
            "relic_v1_1": (23, 2, 70, 85), "relic_v2": (23, 2, 70, 85)},
    "VALIDATED_BY_ORACLE_AND_ARGUMENT": {
        "raw_text": (67, 74, 0, 10), "textdiff": (67, 57, 0, 27),
        "textdiff_ignore_job_parameters": (67, 46, 0, 38), "normalized_text_A": (67, 32, 0, 52),
        "normalized_text_B": (67, 25, 0, 59), "relic_v1_0": (15, 0, 52, 84),
        "relic_v1_1": (23, 0, 44, 84), "relic_v2": (23, 0, 44, 84)},
    "ORACLE_DISAGREES": {
        "raw_text": (10, 3, 15, 0), "textdiff": (10, 3, 15, 0),
        "textdiff_ignore_job_parameters": (10, 3, 15, 0), "normalized_text_A": (10, 3, 15, 0),
        "normalized_text_B": (10, 3, 15, 0), "relic_v1_0": (0, 2, 25, 1),
        "relic_v1_1": (0, 2, 25, 1), "relic_v2": (0, 2, 25, 1)},
}
SUBSET_FILTER = {
    "ALL": lambda r: True,
    "VALIDATED_BY_ORACLE_AND_ARGUMENT": lambda r: r["validation_status"] == "VALIDATED_BY_ORACLE_AND_ARGUMENT",
    "ORACLE_DISAGREES": lambda r: r["validation_status"] == "ORACLE_DISAGREES",
}


@needs_bench
def test_real_manifest_verifies_and_results_are_not_stale():
    manifest = se.verify_manifest(BENCH)
    assert len(manifest) >= 2 * len(list((BENCH / "cases").iterdir()))
    m = json.loads((RES / "metrics.json").read_text())
    assert m["provenance"]["cases_jsonl_sha256"] == hashlib.sha256((BENCH / "cases.jsonl").read_bytes()).hexdigest(), \
        "benchmarks/sembench/cases.jsonl changed after results/sembench was generated: rerun the harness"
    assert m["provenance"]["manifest_sha256"] == hashlib.sha256((BENCH / "MANIFEST.sha256").read_bytes()).hexdigest()


@needs_bench
def test_real_pinned_counts_from_predictions_jsonl():
    rows = [json.loads(ln) for ln in open(RES / "predictions.jsonl")]
    assert len(rows) == 180 and len({r["id"] for r in rows}) == 180
    for subset, per_det in PINNED.items():
        for det, expected in per_det.items():
            tp = fp = fn = tn = 0
            for r in rows:
                if not SUBSET_FILTER[subset](r):
                    continue
                truth = r["expected_outcome"] == "CHANGING"
                flag = bool(r["pred"][det])                 # abstention (None) counts as not flagged
                tp += truth and flag
                fn += truth and not flag
                fp += (not truth) and flag
                tn += (not truth) and not flag
            assert (tp, fp, fn, tn) == expected, (subset, det)


@needs_bench
def test_real_metrics_json_agrees_with_pins_and_no_abstentions_hidden():
    m = json.loads((RES / "metrics.json").read_text())
    for subset, per_det in PINNED.items():
        got = m["populations"][subset]["modes"]["abstain_as_not_flagged"]["detectors"]
        for det, expected in per_det.items():
            assert (got[det]["tp"], got[det]["fp"], got[det]["fn"], got[det]["tn"]) == expected
    for det, counts in m["status_counts_all_cases"].items():
        assert sum(counts.values()) == 180, det                  # every case accounted for
    assert m["populations"]["ALL"]["n_clusters"] == len({
        json.loads(ln)["base_id"] for ln in open(BENCH / "cases.jsonl")})


@needs_bench
def test_real_run_is_deterministic_and_matches_committed(tmp_path):
    se.run(BENCH, tmp_path / "a")
    for name in se.RESULT_FILES:
        assert (tmp_path / "a" / name).read_bytes() == (RES / name).read_bytes(), name


@needs_bench
def test_real_labels_come_from_benchmark_only():
    cases = {json.loads(ln)["id"]: json.loads(ln) for ln in open(BENCH / "cases.jsonl")}
    for ln in open(RES / "predictions.jsonl"):
        r = json.loads(ln)
        assert r["truth"] == (cases[r["id"]]["expected_outcome"] == "CHANGING")
    src = (ROOT / "relic_eval" / "sembench_eval.py").read_text()
    assert ".detail" not in src.replace("p.detail", "")           # labels never derive from detail
