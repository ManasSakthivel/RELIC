"""Unit tests: one block per normalisation rule of relic_eval.text_baselines (+ detectors)."""

import pytest

from relic_eval import text_baselines as tb
from relic_eval.text_baselines import (
    DEFAULT_RULES, RULE_DOCS, RULES, NormalizedTextDetector, RawTextDetector, normalize,
)

BASE = (
    "//JOBA JOB (ACCT),'X',CLASS=A\n"
    "//S1 EXEC PGM=IEFBR14\n"
    "//D1 DD DSN=A.B,DISP=SHR\n"
)


def norm(text, off=(), sort=False):
    return normalize(text, DEFAULT_RULES - set(off), sort)


def same(a, b, **kw):
    return norm(a, **kw) == norm(b, **kw)


def test_every_rule_is_documented_and_switchable():
    for r in list(RULES) + list(tb.OPTIONAL_RULES):
        doc = RULE_DOCS[r]
        assert set(doc) == {"rationale", "excluded", "limitation"} and all(doc.values())
    with pytest.raises(ValueError):
        normalize(BASE, {"no_such_rule"})
    assert normalize(BASE, set()) == BASE.splitlines()     # no rule -> verbatim lines


def test_strip_comment_lines():
    mut = BASE.replace("//S1", "//* hello\n//S1")
    assert same(BASE, mut)
    assert not same(BASE, mut, off={"strip_comment_lines"})


def test_drop_blank_lines():
    mut = BASE.replace("//S1", "\n//S1")
    assert same(BASE, mut)
    assert not same(BASE, mut, off={"drop_blank_lines"})


def test_truncate_col71_and_sequence_numbers():
    line = "//S1 EXEC PGM=IEFBR14"
    a = line.ljust(72) + "00000100\n"
    b = line.ljust(72) + "00000200\n"
    assert same(a, b)
    assert not same(a, b, off={"truncate_col71", "join_continuations"})


def test_text_in_col_71_is_kept_but_72_is_dropped():
    a = "//S1 EXEC PGM=" + "A" * 56 + "X" + "\n"          # col 71 = 'X'
    assert len(a.rstrip()) == 71
    b = a.replace("X\n", "Y\n")
    assert not same(a, b)


def test_rstrip_whitespace():
    mut = BASE.replace("IEFBR14", "IEFBR14   ")
    assert same(BASE, mut)
    assert not same(BASE, mut, off={"rstrip_whitespace", "collapse_whitespace",
                                     "strip_trailing_comment_field"})


def test_join_continuations():
    a = "//S1 EXEC PGM=X,\n//        REGION=0M\n"
    b = "//S1 EXEC PGM=X,REGION=0M\n"
    c = "//S1 EXEC PGM=X,\n//* note\n//   REGION=0M\n"
    assert same(a, b) and same(a, c)
    assert not same(a, b, off={"join_continuations"})


def test_join_does_not_cross_a_non_continuation():
    # trailing comma inside the comment field is NOT a continuation
    a = "//S1 EXEC PGM=X   run it, now,\n//S2 EXEC PGM=Y\n"
    assert normalize(a)[1].startswith("//S2")


def test_quoted_string_continuation_col72():
    first = "//S1 EXEC PGM=X,PARM='" + "A" * 49          # 71 chars
    first = first.ljust(71) + "X"                          # col 72 non-blank
    cont = "//" + " " * 13 + "BBB'"
    assert normalize(first + "\n" + cont + "\n") == ["//S1 EXEC PGM=X,PARM='" + "A" * 49 + "BBB'"]


def test_strip_trailing_comment_field():
    mut = BASE.replace("DISP=SHR", "DISP=SHR   THIS IS A COMMENT")
    assert same(BASE, mut)
    assert not same(BASE, mut, off={"strip_trailing_comment_field"})


def test_comment_field_not_stripped_for_if():
    a = "// IF (RC = 0) THEN\n"
    b = "// IF (RC = 4) THEN\n"
    assert not same(a, b)


def test_collapse_whitespace_keeps_quotes_and_name_presence():
    assert same(BASE, BASE.replace("//S1 EXEC", "//S1    EXEC"))
    # (strip_trailing_comment_field re-serialises fields with single blanks, so switch it off too)
    assert not same(BASE, BASE.replace("//S1 EXEC", "//S1    EXEC"),
                    off={"collapse_whitespace", "strip_trailing_comment_field"})
    q1 = "//S1 EXEC PGM=X,PARM='A  B'\n"
    q2 = "//S1 EXEC PGM=X,PARM='A B'\n"
    assert not same(q1, q2)                               # blanks inside quotes matter
    assert not same("//A EXEC PGM=X\n", "// A EXEC PGM=X\n")  # name vs no name


def test_uppercase_outside_quotes_only():
    assert same(BASE, BASE.replace("EXEC PGM=IEFBR14", "exec pgm=iefbr14"))
    assert not same(BASE, BASE.replace("EXEC PGM=IEFBR14", "exec pgm=iefbr14"),
                    off={"uppercase_outside_quotes"})
    q1 = "//S1 EXEC PGM=X,PARM='abc'\n"
    q2 = "//S1 EXEC PGM=X,PARM='ABC'\n"
    assert not same(q1, q2)


def test_ignore_job_parameters_keeps_name():
    mut = BASE.replace("CLASS=A", "CLASS=B,MSGCLASS=X")
    assert same(BASE, mut)
    assert not same(BASE, mut, off={"ignore_job_parameters"})
    assert not same(BASE, BASE.replace("JOBA", "JOBB"))
    cont = "//JOBA JOB (ACCT),'X',\n//    CLASS=A\n//S1 EXEC PGM=IEFBR14\n"
    assert normalize(cont)[0] == "//JOBA JOB" and normalize(cont)[1].startswith("//S1")


DATA = "//S1 EXEC PGM=X\n//SYSIN DD *\n  Select   a  from T\n/*\n//S2 EXEC PGM=Y\n"


def test_preserve_instream_data():
    mut = DATA.replace("Select   a  from T", "select a from t")
    assert not same(DATA, mut)                            # data is verbatim
    assert same(DATA, mut, off={"preserve_instream_data"})   # rule off -> data is normalised (wrong)
    assert normalize(DATA)[2] == "  Select   a  from T"


def test_instream_data_edges():
    dd = "//SYSIN DD *\n//S2 EXEC PGM=Y\n"                 # empty DD *, '//' ends it
    assert normalize(dd) == ["//SYSIN DD *", "//S2 EXEC PGM=Y"]
    dlm = "//SYSIN DD DATA,DLM=ZZ\n/* x\n//* y\nZZ\n//S2 EXEC PGM=Y\n"
    assert normalize(dlm) == ["//SYSIN DD DATA,DLM=ZZ", "/* x", "//* y", "ZZ", "//S2 EXEC PGM=Y"]


def test_sort_keyword_operands_version_B_only():
    a = "//D1 DD DSN=A.B,DISP=SHR\n"
    b = "//D1 DD DISP=SHR,DSN=A.B\n"
    assert not same(a, b)                                  # version A: order matters
    assert same(a, b, sort=True)                           # version B
    assert not same("//D DD DSN=A,DCB=(RECFM=FB,LRECL=80)\n",
                    "//D DD DSN=A,DCB=(LRECL=80,RECFM=FB)\n", sort=True)   # sub-params untouched


def test_sort_keeps_positional_prefix_and_guards():
    pos = "//S1 EXEC PROCX,B=2,A=1\n"
    assert normalize(pos, sort_operands=True) == ["//S1 EXEC PROCX,A=1,B=2"]
    bad = "//D DD DSN=A,DUMMY\n"                           # positional after keyword: unsorted
    assert normalize(bad, sort_operands=True) == ["//D DD DSN=A,DUMMY"]
    cond1 = "// IF (A=1,B=2) THEN\n"
    assert normalize(cond1, sort_operands=True) == ["// IF (A=1,B=2) THEN"]


def test_detectors_and_names():
    raw, A, B = RawTextDetector(), NormalizedTextDetector(False), NormalizedTextDetector(True)
    assert (raw.name, A.name, B.name) == ("raw_text", "normalized_text_A", "normalized_text_B")
    assert raw.predict(BASE, BASE + " ", "p").flagged and not A.predict(BASE, BASE + " ", "p").flagged
    assert not raw.predict(BASE, BASE, "p").flagged
    reorder = BASE.replace("DSN=A.B,DISP=SHR", "DISP=SHR,DSN=A.B")
    assert A.predict(BASE, reorder, "p").flagged and not B.predict(BASE, reorder, "p").flagged
    swap = ("//JOBA JOB\n//S2 EXEC PGM=B\n//S1 EXEC PGM=A\n")
    orig = ("//JOBA JOB\n//S1 EXEC PGM=A\n//S2 EXEC PGM=B\n")
    assert A.predict(orig, swap, "p").flagged and B.predict(orig, swap, "p").flagged


def test_reuses_existing_detectors_not_copies():
    from relic_eval.detectors import TextDiffDetector
    from relic_eval.v2_eval import TextDiffIgnoreJobCard
    names = {type(d) for d in tb.all_text_baselines()}
    assert TextDiffDetector in names and TextDiffIgnoreJobCard in names
    assert [d.name for d in tb.all_text_baselines()] == [
        "raw_text", "textdiff", "textdiff_ignore_job_parameters",
        "normalized_text_A", "normalized_text_B"]


def test_detector_error_is_visible_not_negative(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(tb, "normalize", boom)
    p = NormalizedTextDetector().predict("a", "b", "p")
    assert p.flagged is None and p.status == "ERROR"
