"""
Fast checks for the external-validation harness (relic_eval/external_eval.py).

* the freeze file is well-formed and records SHAs / hashes / criteria;
* no frozen external file duplicates a development-corpus file (raw or normalised sha256);
* the per-file evaluation is deterministic and agrees with relic_eval.pipeline.run_benchmark
  on a tiny JCL fixture generated in tmp_path;
* detector errors are surfaced as ERROR, never silently negative.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from relic_eval import external_eval as ee

FREEZE = ee.FREEZE_PATH

TINY = """\
//TINYJOB  JOB (ACCT),'TINY',CLASS=A,MSGCLASS=X
//STEP1    EXEC PGM=IEFBR14
//OUT1     DD DSN=EXT.TINY.DATA,DISP=(NEW,CATLG),UNIT=SYSDA,SPACE=(TRK,1)
//STEP2    EXEC PGM=SORT,COND=(4,LT,STEP1)
//SORTIN   DD DSN=EXT.TINY.DATA,DISP=SHR
//SORTOUT  DD SYSOUT=*
//STEP3    EXEC PGM=IEFBR14
//DEL      DD DSN=EXT.TINY.DATA,DISP=(OLD,DELETE)
"""


@pytest.fixture(scope="module")
def freeze() -> dict:
    assert FREEZE.exists(), "results/external/SUBJECT_FREEZE.json must be committed before results"
    return json.loads(FREEZE.read_text())


def test_freeze_well_formed(freeze):
    assert freeze["schema"] == ee.SCHEMA
    assert re.fullmatch(r"[0-9a-f]{40}", freeze["relic_commit"])
    for key in ("design_decision_before_results", "criteria", "exposure_statement", "analysis_plan",
                "frozen_code_sha256", "repos", "repos_not_acquired", "development_corpus"):
        assert freeze[key]
    assert "blind" in freeze["exposure_statement"].lower()
    assert "NOT blind" in freeze["exposure_statement"] or "No external repository is blind" in freeze["exposure_statement"]
    assert freeze["criteria"]["max_lines"] == ee.MAX_LINES
    assert freeze["criteria"]["min_exec_steps"] == ee.MIN_EXEC_STEPS


def test_freeze_repos_have_sha_license_and_exposure(freeze):
    keys = [r["key"] for r in freeze["repos"]]
    assert len(keys) == len(set(keys))
    for r in freeze["repos"]:
        assert re.fullmatch(r"[0-9a-f]{40}", r["pinned_sha"]), r["key"]
        assert re.fullmatch(r"[0-9a-f]{64}", r["license_file_sha256"]), r["key"]
        assert r["license_spdx"] and r["license_first_line"], r["key"]
        assert "NOT blind" in r["exposure"], r["key"]
        assert r["role"] in (ee.ROLE_EFFECTIVENESS, ee.ROLE_ROBUSTNESS)
        assert r["n_jcl_files"] == len(r["files"])
        assert r["n_eligible"] == sum(f["eligible"] for f in r["files"])


def test_freeze_files_hashed_and_eligibility_consistent(freeze):
    seen_norm = set()
    for r in freeze["repos"]:
        for f in r["files"]:
            assert re.fullmatch(r"[0-9a-f]{64}", f["sha256"])
            assert re.fullmatch(r"[0-9a-f]{64}", f["normalised_sha256"])
            assert f["eligible"] == (not f["exclusion_reasons"])
            if f["eligible"]:
                assert r["role"] == ee.ROLE_EFFECTIVENESS
                assert f["n_job"] >= 1 and ee.MIN_EXEC_STEPS <= f["n_exec"] <= ee.MAX_EXEC_STEPS
                assert f["lines"] <= ee.MAX_LINES
                assert f["normalised_sha256"] not in seen_norm      # no within-pool duplicates
                seen_norm.add(f["normalised_sha256"])
    assert freeze["totals"]["effectiveness_eligible_files"] == sum(
        f["eligible"] for r in freeze["repos"] if r["role"] == ee.ROLE_EFFECTIVENESS for f in r["files"])


def test_mapa_is_robustness_only(freeze):
    mapa = next(r for r in freeze["repos"] if r["key"] == "cschneid-the-elder_mapa")
    assert mapa["role"] == ee.ROLE_ROBUSTNESS and mapa["n_eligible"] == 0


@pytest.mark.skipif(not ee.DEV_DATASETS.exists(), reason="datasets/ not present")
def test_no_overlap_with_development_corpora(freeze):
    dev = ee.dev_hashes()
    assert len(dev["raw"]) > 100
    for r in freeze["repos"]:
        for f in r["files"]:
            if f["eligible"]:
                assert f["sha256"] not in dev["raw"], (r["key"], f["path"])
                assert f["normalised_sha256"] not in dev["norm"], (r["key"], f["path"])
    assert freeze["development_corpus"]["raw_hash_set_sha256"] == ee.sha256_text("\n".join(sorted(dev["raw"])))


def test_frozen_code_hashes_cover_detectors_and_oracle(freeze):
    names = set(freeze["frozen_code_sha256"])
    for must in ("relic_eval/detectors.py", "relic_eval/mutate.py", "relic_eval/v2_eval.py",
                 "jcl_oracle/judge.py", "jcl_oracle/lexer.py"):
        assert must in names


def test_external_eval_deterministic_on_tiny_fixture(tmp_path):
    f = tmp_path / "tiny.jcl"
    f.write_text(TINY)
    text = f.read_text()
    from jcl_oracle.model import ProcLibrary
    a = ee.evaluate_text("tiny", "tiny.jcl", text, ProcLibrary.from_texts({}), {})
    b = ee.evaluate_text("tiny", "tiny.jcl", text, ProcLibrary.from_texts({}), {})
    assert a == b and a
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    status = {r["status"] for r in a}
    assert status <= {"EVALUABLE", "OUT_OF_SCOPE", "INVALID_MUTATION", "INFRASTRUCTURE_FAILURE", "OTHER"}
    assert any(r["status"] == "EVALUABLE" for r in a)
    for r in a:
        if r["status"] == "EVALUABLE":
            assert set(r["pred"]) == set(ee.DETECTORS)
            assert all(s == "OK" for s in r["pred_status"].values())
            assert isinstance(r["truth"], bool)


def test_matches_pipeline_run_benchmark_on_tiny_subject(tmp_path, monkeypatch):
    """The harness' accounting/labels equal relic_eval.pipeline.run_benchmark for the same files."""
    from relic_eval import pipeline, subjects
    from jcl_oracle.model import ProcLibrary

    class TmpSubject(subjects.Subject):
        def artifact_path(self, p):          # tmp_path is outside the RELIC repo
            return f"tiny/{self.rel(p)}"

    (tmp_path / "tiny.jcl").write_text(TINY)
    subj = TmpSubject(key="tiny", title="t", root=tmp_path, url="", license="", pinned="", role="external")
    monkeypatch.setitem(subjects.SUBJECTS, "tiny", subj)
    ref = pipeline.run_benchmark(["tiny"], verbose=False)
    mine = ee.evaluate_text("tiny", "tiny.jcl", TINY, ProcLibrary.from_texts({}), {})
    key = lambda r: (r.get("mutation_type") or r["operator"], r["site"])  # noqa: E731
    ref_by = {key(r): r for r in ref}
    mine_by = {key(r): r for r in mine}
    assert set(ref_by) == set(mine_by)
    for k, r in mine_by.items():
        p = ref_by[k]
        assert r["status"] == p["status"], k
        assert r["oracle_label"] == p["oracle_result"], k
        assert r["truth"] == p["ground_truth"], k
        for d in ("relic_v1_0", "relic_v1_1", "textdiff"):
            assert r["pred"].get(d) == p["predictions"].get(d), (k, d)


def test_detector_error_is_visible_not_silent():
    class Boom:
        name = "boom"

        def predict(self, original, mutated, path):
            from relic_eval.detectors import Prediction
            return Prediction(None, "ERROR", {"error": "x"})

    from jcl_oracle.model import ProcLibrary
    recs = ee.evaluate_text("tiny", "tiny.jcl", TINY, ProcLibrary.from_texts({}), {}, detectors=[Boom()])
    ev = [r for r in recs if r["status"] == "EVALUABLE"]
    assert ev and all(r["pred"]["boom"] is None and r["pred_status"]["boom"] == "ERROR" for r in ev)
    from relic_eval.metrics import confusion
    rows = [{"truth": bool(r["truth"]), "pred": r["pred"], "cluster": "x"} for r in ev]
    assert confusion(rows, "boom").no_prediction == len(ev)


def test_syntax_feature_detection():
    text = (
        "//J1 JOB (A),'X'\n//S1 EXEC MYPROC\n//S2 EXEC PGM=IEFBR14,COND=(4,LT)\n"
        "//D DD DSN=A.B(+1),DISP=SHR\n//E DD DSN=&SYM.X,DISP=SHR\n// INCLUDE MEMBER=X\n"
        "// IF RC = 0 THEN\n// ENDIF\n//J2 JOB (A),'Y'\n"
    )
    feats = ee.syntax_features(text)
    assert {"PROC_USE", "COND_PARAMETER", "GDG_REFERENCE", "SYMBOLIC_PARAMETERS", "INCLUDE",
            "IF_THEN_ELSE", "MULTI_JOB"} <= feats


def test_normalised_text_ignores_sequence_and_comments():
    a = "//A JOB X\n//* hello\n" + "//S1 EXEC PGM=X".ljust(72) + "12345678\n"
    b = "//A JOB X\n//S1 EXEC PGM=X\n"
    assert ee.normalised_text(a) == ee.normalised_text(b)


def test_outputs_if_present_are_consistent():
    out = ee.OUT
    if not (out / "metrics.json").exists():
        pytest.skip("run not executed yet")
    m = json.loads((out / "metrics.json").read_text())
    lines = [json.loads(x) for x in (out / "predictions.jsonl").read_text().splitlines()]
    ev = [r for r in lines if r["status"] == "EVALUABLE" and r["repo"] != "cschneid-the-elder_mapa"]
    pooled = m["populations"]["pooled_effectiveness"]
    assert pooled["n"] == len(ev)
    assert pooled["positives"] == sum(1 for r in ev if r["truth"])
    for d in ee.DETECTORS:
        c = pooled["detectors"][d]
        assert c["tp"] + c["fp"] + c["fn"] + c["tn"] == len(ev)
    info = json.loads((out / "run_info.json").read_text())
    assert info["n_candidate_mutants"] == len(lines)
