import pytest

from relic_eval.metrics import Confusion, check_consistency, cluster_bootstrap, confusion, wilson


def recs(pairs, cluster="f"):
    return [{"truth": y, "pred": {"d": p}, "cluster": cluster} for y, p in pairs]


def test_confusion_and_formulas():
    c = confusion(recs([(True, True), (True, False), (False, True), (False, False), (True, True)]), "d")
    d = c.as_dict()
    assert (d["tp"], d["fn"], d["fp"], d["tn"]) == (2, 1, 1, 1)
    assert d["precision"] == round(2 / 3, 4)
    assert d["recall"] == round(2 / 3, 4)
    assert d["f1"] == round(4 / 6, 4)
    assert d["specificity"] == 0.5


def test_undefined_ratios_are_none_not_zero_or_one():
    d = Confusion(tp=0, fp=0, fn=0, tn=5).as_dict()
    assert d["precision"] is None and d["recall"] is None and d["f1"] is None
    assert d["specificity"] == 1.0


def test_missing_prediction_policies():
    rs = [{"truth": True, "pred": {"d": None}, "cluster": "f"}, {"truth": True, "pred": {"d": True}, "cluster": "f"}]
    assert confusion(rs, "d", "negative").fn == 1
    c = confusion(rs, "d", "exclude")
    assert c.n == 1 and c.no_prediction == 1


def test_consistency_check_rejects_inconsistent_f1():
    d = Confusion(tp=3, fp=1, fn=1, tn=0).as_dict()
    d["f1"] = 0.99
    with pytest.raises(AssertionError):
        check_consistency(d)


def test_wilson_bounds():
    lo, hi = wilson(10, 10)
    assert hi == 1.0 and 0.6 < lo < 0.75
    assert wilson(0, 0) is None


def test_cluster_bootstrap_is_deterministic_and_resamples_files():
    rs = recs([(True, True), (True, False)], "a") + recs([(True, True), (False, False)], "b") + \
        recs([(True, True), (False, True)], "c")
    b1 = cluster_bootstrap(rs, ["d"], [], reps=500)
    b2 = cluster_bootstrap(rs, ["d"], [], reps=500)
    assert b1 == b2 and b1["n_clusters"] == 3
    lo, hi = b1["f1_ci95"]["d"]
    assert 0 <= lo <= hi <= 1
