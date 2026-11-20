"""
Integrity tests for the V2 evaluation records (results/v2/) and its replay harness.

These tests re-run ``relic_eval.v2_eval`` (about 4 s). They check that:
  * the committed results/v2 files equal a fresh deterministic run (apart from
    v2_run_info.json, which holds a timestamp),
  * the replay really uses the historical evidence (mutant hashes verified, v1.1
    recomputation equals the committed predictions - enforced inside the run),
  * the V2 harness writes only to results/v2 (never results/final),
  * the claims made in reports/v2 about V2 (no false positives; the only lost
    true positives are the documented D-004 trade-off) hold.
"""

import json
from pathlib import Path

import pytest

from relic_eval import v2_eval

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "results" / "v2"


@pytest.fixture(scope="module")
def fresh(tmp_path_factory):
    out = tmp_path_factory.mktemp("v2out")
    mp = pytest.MonkeyPatch()
    mp.setattr(v2_eval, "OUT", out)
    try:
        v2_eval.write(v2_eval.run())
    finally:
        mp.undo()
    return out


def test_committed_v2_results_equal_a_fresh_run(fresh):
    for name in ("v2_metrics.json", "v2_predictions.jsonl"):
        assert (fresh / name).read_bytes() == (COMMITTED / name).read_bytes(), name


def test_v2_run_is_deterministic(fresh, tmp_path):
    mp = pytest.MonkeyPatch()
    mp.setattr(v2_eval, "OUT", tmp_path)
    try:
        v2_eval.write(v2_eval.run())
    finally:
        mp.undo()
    for name in ("v2_metrics.json", "v2_predictions.jsonl"):
        assert (fresh / name).read_bytes() == (tmp_path / name).read_bytes(), name


def test_v2_metrics_claims():
    m = json.loads((COMMITTED / "v2_metrics.json").read_text())
    pooled = m["populations"]["pooled"]["detectors"]
    assert pooled["relic_v2"]["fp"] == 0
    assert pooled["relic_v2"]["tp"] + pooled["relic_v2"]["fn"] == 460
    flips = m["flips_v2_vs_v1_1"]
    assert flips["gained_false_positives"] == 0
    # the only lost flags are the D-004 trade-off (see DEFECT_REGISTER D-004)
    assert sorted(flips["lost_flags"]) == [
        "carddemo/app/jcl/DUSRSECJ.jcl/RENAME_OUTPUT_DATASET/0",
        "carddemo/app/jcl/ESDSRRDS.jcl/RENAME_OUTPUT_DATASET/0",
    ]
    assert "EXTERNAL VALIDATION REMAINS PENDING" in m["validation_status"]


def test_v1_1_recomputation_equals_committed_predictions():
    """Committed v1.1 predictions are in results/final; the replay raises if they differ."""
    rows = v2_eval.run()["rows"]
    assert len(rows) == 566
    committed = {}
    with open(v2_eval.RECORDS) as fh:
        for line in fh:
            r = json.loads(line)
            if r["status"] == "EVALUABLE":
                committed[r["mutation_id"]] = r["predictions"]["relic_v1_1"]
    assert {r["mutation_id"]: r["pred"]["relic_v1_1"] for r in rows} == committed


def test_v2_harness_output_directory_is_not_the_historical_one():
    assert v2_eval.OUT == ROOT / "results" / "v2"
    assert v2_eval.OUT != ROOT / "results" / "final"


def _confusion(detector):
    tp = fp = fn = tn = 0
    for line in (COMMITTED / "v2_predictions.jsonl").read_text().splitlines():
        r = json.loads(line)
        p = bool(r["pred"][detector])
        t = bool(r["truth"])
        tp += p and t
        fp += p and not t
        fn += (not p) and t
        tn += (not p) and not t
    return tp, fp, fn, tn


@pytest.mark.parametrize("detector,expected", [
    ("relic_v1_0", (380, 0, 80, 106)),
    ("relic_v1_1", (417, 0, 43, 106)),
    ("relic_v2", (442, 0, 18, 106)),
    ("relic_v2_wo_D001", (419, 0, 41, 106)),
    ("relic_v2_wo_D002", (441, 0, 19, 106)),
    ("relic_v2_wo_D003", (442, 0, 18, 106)),
    ("relic_v2_wo_D004", (444, 0, 16, 106)),
    ("textdiff", (460, 41, 0, 65)),
    ("textdiff_ignore_job_parameters", (460, 2, 0, 104)),
])
def test_pinned_confusion_matrices_recomputed_from_raw_predictions(detector, expected):
    """Independent of v2_eval's metric code: counts come straight from the prediction records."""
    assert _confusion(detector) == expected


def test_pinned_f1_of_relic_v2_is_0_980():
    tp, fp, fn, _tn = _confusion("relic_v2")
    assert round(2 * tp / (2 * tp + fp + fn), 4) == 0.98
