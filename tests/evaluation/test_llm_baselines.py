"""
Protocol tests for the corrected LLM baselines (relic_eval/llm_baselines.py).
No network access: the client is never called.
"""

import json

import pytest

from relic_eval import llm_baselines as L
from relic_eval.mutate import ALL_OPERATORS

ORIG = """//JOB1    JOB (ACCT),'X',CLASS=A,MSGCLASS=X
//STEP05  EXEC PGM=IEFBR14
//OUT     DD DSN=A.B.C,DISP=(NEW,CATLG,DELETE),
//           SPACE=(TRK,(1,1))
//STEP10  EXEC PGM=SORT,COND=(4,LT)
//SORTIN  DD DSN=A.B.C,DISP=SHR
"""
MOD = ORIG.replace("COND=(4,LT)", "COND=(8,LT)")


@pytest.mark.parametrize("baseline", ["C", "D"])
def test_prompt_contains_code_but_no_label_or_operator(baseline):
    p = L.build_prompt(baseline, ORIG, MOD, "datasets/x/SECRETPATH.jcl")
    assert "COND=(4,LT)" in p and "COND=(8,LT)" in p
    for op in ALL_OPERATORS:
        assert op not in p
    for leak in ("SECRETPATH", "mutation", "Mutation", "violat", "expected", "ground truth", "oracle"):
        assert leak not in p


def test_dependency_baseline_adds_summary_and_merges_continuations():
    p = L.build_prompt("D", ORIG, MOD, "x.jcl")
    assert "DEPENDENCY SUMMARY" in p
    # DISP on a continuation line must be seen (v1.0 parser lost it)
    assert "creates A.B.C" in p
    assert "DEPENDENCY SUMMARY" not in L.build_prompt("C", ORIG, MOD, "x.jcl")


@pytest.mark.parametrize("text,expected", [
    ('{"behavior_changed": true, "confidence": 0.9, "reason": "r"}', (True, 0.9, "r")),
    ('Sure.\n```json\n{"behavior_changed": false, "confidence": 1, "reason": "x"}\n```', (False, 1.0, "x")),
    ('{"behavior_changed": "yes"}', (None, None, "behavior_changed missing or not boolean")),
    ("no json here", (None, None, "no JSON object in response")),
    ("{not json}", (None, None, "invalid JSON")),
])
def test_parse_answer(text, expected):
    assert L.parse_answer(text) == expected


def test_population_order_is_seeded_and_input_order_independent():
    pop = [{"mutation_id": f"m{i}"} for i in range(50)]
    a = [r["mutation_id"] for r in L.population_order(pop)]
    b = [r["mutation_id"] for r in L.population_order(list(reversed(pop)))]
    assert a == b and a != sorted(a)


def test_failed_and_unparsed_answers_are_never_scored(tmp_path, monkeypatch):
    recs = [
        {"mutation_id": "m1", "baseline": "llm_C", "status": "OK", "flagged": True},
        {"mutation_id": "m1", "baseline": "llm_D", "status": "ERROR", "flagged": None},
        {"mutation_id": "m2", "baseline": "llm_C", "status": "INVALID_OUTPUT", "flagged": None},
        {"mutation_id": "m2", "baseline": "llm_D", "status": "NOT_RUN", "flagged": None},
        {"mutation_id": "m3", "baseline": "llm_C", "status": "OK", "flagged": False},
    ]
    path = tmp_path / "llm_records.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in recs))
    monkeypatch.setattr(L, "RECORDS", path)
    monkeypatch.setattr(L, "STATUS", tmp_path / "missing.json")
    preds = L.load_llm_predictions()["predictions"]
    assert preds["m1"] == {"llm_C": True, "llm_D": None}
    assert preds["m2"] == {"llm_C": None, "llm_D": None}
    assert preds["m3"] == {"llm_C": False}


def test_metrics_compare_llm_and_relic_on_common_population():
    from relic_eval import report
    base = {"status": "EVALUABLE", "subject_system": "carddemo", "mutation_type": "REMOVE_COND",
            "contract_type": "CONTROL_FLOW"}
    all_true = {d: True for d in report.DETECTORS}
    recs = [dict(base, file="f1.jcl", mutation_id="a", ground_truth=True, predictions=all_true),
            dict(base, file="f2.jcl", mutation_id="b", ground_truth=False, predictions=all_true),
            dict(base, file="f3.jcl", mutation_id="c", ground_truth=True, predictions=all_true)]
    llm = {"status": {}, "predictions": {"a": {"llm_C": True, "llm_D": True},
                                         "b": {"llm_C": False, "llm_D": None},
                                         "c": {"llm_C": None, "llm_D": None}}}
    res = report.llm_section(recs, llm)["results"]["carddemo"]
    assert res["n_population"] == 3 and res["n_common"] == 1
    assert res["n_answered"] == {"llm_C": 2, "llm_D": 1}
    # b and c are excluded for EVERY detector, not only for the LLM that failed
    assert all(res["common"][d]["n"] == 1 for d in report.LLM_COMPARISON)
    assert res["own_answered"]["llm_C"]["n"] == 2 and res["own_answered"]["llm_C"]["tn"] == 1


def test_no_llm_answers_means_no_llm_results():
    from relic_eval import report
    assert report.llm_section([], {"status": {}, "predictions": {"a": {"llm_C": None}}})["results"] == {}


def test_retry_after_parsing():
    class E:
        headers = {}
    assert L.Client._retry_after(E(), "Please try again in 5.3475s. Need more") == pytest.approx(5.3475)
    assert L.Client._retry_after(E(), "Please try again in 1h2m3s.") == pytest.approx(3723)
    assert L.Client._retry_after(E(), "nothing") is None
