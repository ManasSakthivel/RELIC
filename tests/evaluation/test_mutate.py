from relic_eval.mutate import analyse, generate

JOB = """//J JOB 1,'T',CLASS=A,MSGCLASS=X
//MAKE EXEC PGM=IEBGENER
//SYSUT1 DD DSN=IN.A,DISP=SHR
//SYSUT2 DD DSN=WORK.A,DISP=(NEW,CATLG,DELETE)
//MID  EXEC PGM=IEFBR14
//USE  EXEC PGM=IEBGENER,COND=(4,LT)
//SYSUT1 DD DSN=WORK.A,DISP=SHR
//SYSUT2 DD DSN=OUT.A,DISP=(NEW,CATLG,DELETE)
"""


def by_op(ms):
    out = {}
    for m in ms:
        out.setdefault(m.operator, []).append(m)
    return out


def test_sites_are_enumerated_exhaustively_and_deterministically():
    a, b = generate(JOB), generate(JOB)
    assert [(m.operator, m.site, m.text) for m in a] == [(m.operator, m.site, m.text) for m in b]
    ops = by_op(a)
    assert len(ops["SWAP_ADJACENT_STEPS"]) == 2
    assert len(ops["SPLIT_JOB"]) == 2
    assert len(ops["DELETE_PRODUCER_STEP"]) == 1
    assert len(ops["MOVE_CONSUMER_BEFORE_PRODUCER"]) == 1
    assert len(ops["REMOVE_COND"]) == 1 and len(ops["ALTER_COND_THRESHOLD"]) == 1


def test_cond_edits_are_minimal():
    ops = by_op(generate(JOB))
    assert "//USE  EXEC PGM=IEBGENER\n" in ops["REMOVE_COND"][0].text
    assert "COND=(8,LT)" in ops["ALTER_COND_THRESHOLD"][0].text
    assert ops["ALTER_COND_THRESHOLD"][0].text.count("\n") == JOB.count("\n")


def test_rename_scope_depends_on_in_file_consumer():
    ops = by_op(generate(JOB))
    renames = {m.site: m for m in ops["RENAME_OUTPUT_DATASET"]}
    assert renames["MAKE.SYSUT2 WORK.A"].scope_note == ""
    assert "cross-file" in renames["USE.SYSUT2 OUT.A"].scope_note
    assert "DSN=WORK.A.MIG," in renames["MAKE.SYSUT2 WORK.A"].text


def test_negative_operators_are_marked_expected_negative():
    ops = by_op(generate(JOB))
    assert ops["INSERT_COMMENT"][0].expected_violation is False
    assert "MSGCLASS=Y" in ops["CHANGE_MSGCLASS"][0].text
    assert ops["CHANGE_MSGCLASS"][0].expected_violation is False


def test_split_inside_if_is_invalid_not_dropped():
    text = """//J JOB A
//S1 EXEC PGM=IEFBR14
// IF RC = 0 THEN
//S2 EXEC PGM=IEFBR14
//S3 EXEC PGM=IEFBR14
// ENDIF
"""
    ops = by_op(generate(text))
    invalid = [m for m in ops["SPLIT_JOB"] if m.text is None]
    assert invalid and all("IF" in m.invalid_reason for m in invalid)
    assert ops["REMOVE_IF_GUARD"][0].scope_note


def test_proc_bodies_are_not_job_steps():
    text = """//J JOB A
//P PROC
//PS1 EXEC PGM=IEFBR14
// PEND
//S1 EXEC P
//S2 EXEC PGM=IEFBR14
"""
    jobs, _ifs, _lines = analyse(text)
    assert [b.name for b in jobs[0].blocks] == ["S1", "S2"]
