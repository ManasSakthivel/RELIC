"""
Regression tests for generated documentation blocks.

The first version of the block regex required a newline on both sides of the
block body, so an empty block ("BEGIN\\nEND") never matched: the pipeline could
not fill it and check_consistency accepted it without looking.
"""

import pytest

from relic_eval import check_consistency, report

EMPTY = "intro\n<!-- BEGIN GENERATED:table-a -->\n<!-- END GENERATED:table-a -->\noutro\n"
FILLED = "intro\n<!-- BEGIN GENERATED:table-a -->\n| x |\n|---|\n| 1 |\n<!-- END GENERATED:table-a -->\noutro\n"
BLOCKS = {"table-a": "| x |\n|---|\n| 1 |"}


def test_empty_block_is_detected():
    assert report.find_blocks(EMPTY) == [("table-a", "")]


def test_populated_block_is_detected():
    assert report.find_blocks(FILLED) == [("table-a", BLOCKS["table-a"])]


def test_content_is_inserted_into_empty_block():
    assert report.render_into(EMPTY, BLOCKS) == FILLED


def test_rendering_is_idempotent_and_touches_nothing_outside_blocks():
    once = report.render_into(EMPTY, BLOCKS)
    assert report.render_into(once, BLOCKS) == once
    assert once.startswith("intro\n") and once.endswith("outro\n")


def test_stale_content_is_replaced():
    stale = FILLED.replace("| 1 |", "| 0.999 |")
    assert report.render_into(stale, BLOCKS) == FILLED


def test_multiple_blocks_do_not_swallow_each_other():
    text = EMPTY + EMPTY.replace("table-a", "table-b")
    out = report.render_into(text, {"table-a": "A", "table-b": "B"})
    assert report.find_blocks(out) == [("table-a", "A"), ("table-b", "B")]


def test_unmatched_begin_marker_is_an_error():
    with pytest.raises(ValueError):
        report.find_blocks("<!-- BEGIN GENERATED:table-a -->\ntext\n")


def test_unknown_block_name_is_an_error():
    with pytest.raises(KeyError):
        report.render_into(EMPTY, {"table-b": "B"})


def test_strip_blocks_removes_only_block_bodies():
    assert report.strip_blocks(FILLED) == EMPTY


@pytest.fixture
def doc(tmp_path):
    return tmp_path / "doc.md"


def test_check_flags_empty_block(doc):
    doc.write_text(EMPTY)
    errors = check_consistency.check_generated_docs(BLOCKS, [doc])
    assert any("is empty" in e for e in errors)


def test_check_flags_stale_block(doc):
    doc.write_text(FILLED.replace("| 1 |", "| 2 |"))
    errors = check_consistency.check_generated_docs(BLOCKS, [doc])
    assert any("differs from metrics.json" in e for e in errors)


def test_check_flags_missing_doc_and_doc_without_blocks(doc, tmp_path):
    doc.write_text("no markers here\n")
    errors = check_consistency.check_generated_docs(BLOCKS, [doc, tmp_path / "missing.md"])
    assert any("contains no generated block" in e for e in errors)
    assert any("is missing" in e for e in errors)


def test_check_accepts_current_block(doc):
    doc.write_text(FILLED)
    assert check_consistency.check_generated_docs(BLOCKS, [doc]) == []


def test_stale_number_scan_ignores_generated_blocks_only():
    text = FILLED.replace("| 1 |", "| F1 = 1.000 |") + "F1 = 1.000 outside\n"
    stripped = report.strip_blocks(text)
    assert "outside" in stripped and stripped.count("1.000") == 1


def test_rendering_does_not_depend_on_metrics_key_order():
    """metrics.json is written with sorted keys; tables must render identically."""
    import json
    from pathlib import Path
    path = Path(report.OUT) / "metrics.json"
    if not path.exists():
        pytest.skip("pipeline not run")
    m = json.loads(path.read_text())

    def reorder(x):
        if isinstance(x, dict):
            return {k: reorder(x[k]) for k in reversed(list(x))}
        return [reorder(v) for v in x] if isinstance(x, list) else x
    assert report.generated_blocks(reorder(m)) == report.generated_blocks(m)


def test_figure_check_detects_figures_that_do_not_match_metrics():
    import copy
    import json
    from pathlib import Path
    path = Path(report.OUT) / "metrics.json"
    if not path.exists():
        pytest.skip("pipeline not run")
    m = json.loads(path.read_text())
    assert check_consistency.check_figures(m) == []
    tampered = copy.deepcopy(m)
    tampered["results"]["carddemo"]["detectors"]["relic_v1_0"]["f1"] = 0.5
    assert any("f1_carddemo.svg" in e for e in check_consistency.check_figures(tampered))
