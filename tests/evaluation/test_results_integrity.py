"""
Integrity checks on the committed evaluation outputs (results/final). These
guard against hand edits and against an inconsistent pipeline.
"""

import csv
import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "results" / "final"
STATUSES = {"EVALUABLE", "OUT_OF_SCOPE", "INVALID_MUTATION", "INFRASTRUCTURE_FAILURE", "OTHER"}

pytestmark = pytest.mark.skipif(not (FINAL / "metrics.json").exists(), reason="pipeline not run")


def records():
    return [json.loads(l) for l in open(FINAL / "raw" / "evaluation_records.jsonl")]


def test_every_candidate_has_exactly_one_known_status():
    rs = records()
    assert len({r["mutation_id"] for r in rs}) == len(rs)
    for r in rs:
        assert r["status"] in STATUSES
        assert r["evaluable_for_metrics"] == (r["status"] == "EVALUABLE")
        assert r["status_reason"]
        if r["status"] == "EVALUABLE":
            assert r["oracle_result"] in {"DIFFERENT", "EQUIVALENT"}
            assert r["ground_truth"] == (r["oracle_result"] == "DIFFERENT")


def test_manifest_matches_records_and_accounting():
    rs = records()
    with open(FINAL / "evaluation_manifest.csv") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["mutation_id"] for r in rows] == [r["mutation_id"] for r in rs]
    m = json.loads((FINAL / "metrics.json").read_text())
    counts = Counter(r["status"] for r in rs)
    assert m["accounting"]["pooled"]["total"] == len(rs)
    for s in STATUSES:
        assert m["accounting"]["pooled"]["by_status"][s] == counts.get(s, 0)


def test_metrics_recomputable_from_records():
    from relic_eval.metrics import confusion
    rs = records()
    m = json.loads((FINAL / "metrics.json").read_text())
    for pop in ("carddemo", "omp_course", "genapp", "pooled"):
        ev = [r for r in rs if r["status"] == "EVALUABLE" and (pop == "pooled" or r["subject_system"] == pop)]
        scored = [{"truth": r["ground_truth"], "pred": r["predictions"], "cluster": r["file"]} for r in ev]
        for det, block in m["results"][pop]["detectors"].items():
            assert confusion(scored, det).as_dict() == block, (pop, det)


def test_no_detector_errors_unaccounted():
    for r in records():
        for det, d in r.get("prediction_details", {}).items():
            if d.get("status") == "ERROR":
                assert r["predictions"][det] is None
