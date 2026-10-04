"""
Semantics tests for the independent JCL oracle (jcl_oracle).

Each fixture is small enough to check by hand against the IBM z/OS MVS JCL
Reference; the expected verdicts were written from the JCL rules, not by
running the oracle.
"""

from __future__ import annotations

from jcl_oracle.judge import compare_versions, describe_file
from jcl_oracle.lexer import lex
from jcl_oracle.model import build_model
from jcl_oracle.programs import analyse_cobol
from jcl_oracle.simulate import Scenario, Simulator, first_access_creates, parse_cond


def run(text: str, scenario: Scenario = Scenario()):
    model = build_model(text)
    sim = Simulator(model, {}, first_access_creates(model, {}))
    beh, state = sim.run(scenario)
    return {ident: (status, rc) for ident, status, rc in beh.steps}, beh


INDEPENDENT = """//J1 JOB CLASS=A,MSGCLASS=X
//S1 EXEC PGM=IEBGENER
//SYSUT1 DD DSN=IN.A,DISP=SHR
//SYSUT2 DD DSN=OUT.A,DISP=(NEW,CATLG,DELETE)
//S2 EXEC PGM=IEBGENER
//SYSUT1 DD DSN=IN.B,DISP=SHR
//SYSUT2 DD DSN=OUT.B,DISP=(NEW,CATLG,DELETE)
"""

SWAPPED = """//J1 JOB CLASS=A,MSGCLASS=X
//S2 EXEC PGM=IEBGENER
//SYSUT1 DD DSN=IN.B,DISP=SHR
//SYSUT2 DD DSN=OUT.B,DISP=(NEW,CATLG,DELETE)
//S1 EXEC PGM=IEBGENER
//SYSUT1 DD DSN=IN.A,DISP=SHR
//SYSUT2 DD DSN=OUT.A,DISP=(NEW,CATLG,DELETE)
"""

PRODUCER_CONSUMER = """//J2 JOB CLASS=A
//MAKE EXEC PGM=IEBGENER
//SYSUT1 DD DSN=IN.A,DISP=SHR
//SYSUT2 DD DSN=WORK.A,DISP=(NEW,CATLG,DELETE)
//USE  EXEC PGM=IEBGENER
//SYSUT1 DD DSN=WORK.A,DISP=SHR
//SYSUT2 DD DSN=OUT.A,DISP=(NEW,CATLG,DELETE)
"""


# --- lexer -------------------------------------------------------------------------

def test_continuation_columns_4_to_16_are_merged():
    text = "//S1 EXEC PGM=X\n//DD1 DD DSN=A.B,\n//         DISP=(NEW,CATLG)\n"
    stmts = [s for s in lex(text) if s.kind == "STMT"]
    assert stmts[1].operands == "DSN=A.B,DISP=(NEW,CATLG)"


def test_sequence_columns_ignored():
    text = "//S1 EXEC PGM=IEFBR14,COND=(0,NE)".ljust(72) + "00500019\n"
    st = [s for s in lex(text) if s.kind == "STMT"][0]
    assert st.operands == "PGM=IEFBR14,COND=(0,NE)"


def test_instream_data_with_dlm():
    text = "//S1 EXEC PGM=X\n//IN DD DATA,DLM=@@\n// not a statement\n@@\n//OUT DD SYSOUT=*\n"
    stmts = [s for s in lex(text) if s.kind == "STMT"]
    assert stmts[1].data == ["// not a statement"]
    assert stmts[2].name == "OUT"


# --- COND / IF -------------------------------------------------------------------------

def test_parse_cond_forms():
    assert parse_cond("(4,LT)") == ([(4, "LT", None)], False, False)
    assert parse_cond("((0,NE),(8,LT,STEP1),EVEN)") == ([(0, "NE", None), (8, "LT", "STEP1")], True, False)


def test_cond_without_stepname_tests_every_previous_step():
    text = """//J JOB A
//S1 EXEC PGM=IEFBR14
//S2 EXEC PGM=IEFBR14
//S3 EXEC PGM=IEFBR14,COND=(4,LT)
"""
    steps, _ = run(text, Scenario("S1", 8))           # 4 < 8 -> bypass, although S1 is not adjacent
    assert steps["S3"][0] == "BYPASS"
    steps, _ = run(text, Scenario("S2", 4))           # 4 < 4 false -> runs
    assert steps["S3"][0] == "RUN"


def test_cond_with_stepname_ignores_steps_that_did_not_run():
    text = """//J JOB A
//S0 EXEC PGM=IEFBR14
//S1 EXEC PGM=IEFBR14,COND=(0,LE)
//S2 EXEC PGM=IEFBR14,COND=(0,EQ,S1)
"""
    steps, _ = run(text)
    assert steps["S1"][0] == "BYPASS"   # 0 <= RC(S0)=0 is true
    assert steps["S2"][0] == "RUN"      # S1 did not run, so the test on S1 is ignored


def test_first_step_cond_has_no_effect():
    text = """//J JOB A
//S1 EXEC PGM=IEFBR14,COND=(0,NE)
"""
    steps, _ = run(text)
    assert steps["S1"] == ("RUN", 0)


def test_abend_bypasses_later_steps_unless_even():
    text = """//J JOB A
//S1 EXEC PGM=IEFBR14
//S2 EXEC PGM=IEFBR14
//S3 EXEC PGM=IEFBR14,COND=EVEN
"""
    steps, _ = run(text, Scenario("S1", "ABEND"))
    assert steps["S1"][0] == "ABEND"
    assert steps["S2"][0] == "BYPASS"
    assert steps["S3"][0] == "RUN"


def test_if_rc_semantics():
    text = """//J JOB A
//S1 EXEC PGM=IEFBR14
// IF RC = 0 THEN
//S2 EXEC PGM=IEFBR14
// ELSE
//S3 EXEC PGM=IEFBR14
// ENDIF
"""
    steps, _ = run(text)
    assert steps["S2"][0] == "RUN" and steps["S3"][0] == "BYPASS"
    steps, _ = run(text, Scenario("S1", 4))
    assert steps["S2"][0] == "BYPASS" and steps["S3"][0] == "RUN"


# --- datasets ---------------------------------------------------------------------------

def test_reading_a_dataset_before_it_is_created_is_a_jcl_error():
    # The initial catalog always comes from the ORIGINAL job (WORK.A is created
    # there, so it does not exist beforehand); the swapped job runs against it.
    lines = PRODUCER_CONSUMER.splitlines()
    swapped = "\n".join([lines[0]] + lines[4:7] + lines[1:4]) + "\n"
    init = first_access_creates(build_model(PRODUCER_CONSUMER), {})
    beh, _ = Simulator(build_model(swapped), {}, init).run(Scenario())
    steps = {i: s for i, s, _rc in beh.steps}
    assert steps["USE"] == "JCLERR"
    assert steps["MAKE"] == "NOTRUN"
    assert beh.termination[0][1] == "JCLERR"


def test_new_dataset_defaults_to_delete():
    text = "//J JOB A\n//S1 EXEC PGM=IEFBR14\n//D DD DSN=TMP.X,DISP=NEW\n"
    _steps, beh = run(text)
    assert all(k != "TMP.X" for k, _v in beh.final)


def test_idcams_delete_missing_dataset_gives_rc8_and_set_maxcc_resets():
    text = """//J JOB A
//S1 EXEC PGM=IDCAMS
//SYSIN DD *
  DELETE NOT.THERE CLUSTER
/*
//S2 EXEC PGM=IDCAMS
//SYSIN DD *
  DELETE NOT.THERE CLUSTER
  SET MAXCC = 0
/*
"""
    model = build_model(text)
    init = {"NOT.THERE": False}
    sim = Simulator(model, {}, init)
    beh, _ = sim.run(Scenario())
    steps = {i: (s, rc) for i, s, rc in beh.steps}
    assert steps["S1"] == ("RUN", 8)
    assert steps["S2"] == ("RUN", 0)


def test_idcams_conditional_reset():
    text = """//J JOB A
//S1 EXEC PGM=IDCAMS
//SYSIN DD *
  DELETE NOT.THERE CLUSTER
  IF MAXCC LE 08 THEN SET MAXCC = 0
/*
"""
    model = build_model(text)
    beh, _ = Simulator(model, {}, {"NOT.THERE": False}).run(Scenario())
    assert {(i, s, rc) for i, s, rc in beh.steps} == {("S1", "RUN", 0)}


def test_cobol_open_modes():
    src = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. P1.
       ENVIRONMENT DIVISION.
       FILE-CONTROL.
           SELECT IN-F ASSIGN TO INFILE.
           SELECT OUT-F ASSIGN TO UT-S-OUTFILE.
       PROCEDURE DIVISION.
           OPEN INPUT IN-F OUTPUT OUT-F.
"""
    info = analyse_cobol(src)
    assert info.dd_modes == {"INFILE": "R", "OUTFILE": "W"}
    assert info.opaque_reasons == []


# --- verdicts -----------------------------------------------------------------------------

def test_identical_text_is_equivalent():
    assert compare_versions(INDEPENDENT, INDEPENDENT).label == "EQUIVALENT"


def test_comment_insertion_is_equivalent():
    mutated = INDEPENDENT.replace("//S2 EXEC", "//* a comment\n//S2 EXEC")
    assert compare_versions(INDEPENDENT, mutated).label == "EQUIVALENT"


def test_msgclass_change_is_equivalent():
    assert compare_versions(INDEPENDENT, INDEPENDENT.replace("MSGCLASS=X", "MSGCLASS=Y")).label == "EQUIVALENT"


def test_independent_swap_differs_only_under_abend():
    full = compare_versions(INDEPENDENT, SWAPPED)
    no_abend = compare_versions(INDEPENDENT, SWAPPED, scenario_set="no_abend")
    assert full.label == "DIFFERENT"          # if S1 abends, S2 is bypassed only in the original
    assert no_abend.label == "EQUIVALENT"     # under normal completion the order is unobservable


def test_dependent_swap_differs_under_normal_completion():
    lines = PRODUCER_CONSUMER.splitlines()
    swapped = "\n".join([lines[0]] + lines[4:7] + lines[1:4]) + "\n"
    v = compare_versions(PRODUCER_CONSUMER, swapped, scenario_set="no_abend")
    assert v.label == "DIFFERENT"
    assert "termination" in v.categories


def test_cond_threshold_change_is_detected_at_boundary():
    orig = "//J JOB A\n//S1 EXEC PGM=IEFBR14\n//S2 EXEC PGM=IEFBR14,COND=(4,LT)\n"
    mut = orig.replace("(4,LT)", "(8,LT)")
    v = compare_versions(orig, mut, scenario_set="no_abend")
    assert v.label == "DIFFERENT"            # at RC 5..8 the original bypasses S2, the mutant runs it


def test_swap_of_same_named_steps_is_not_hidden():
    orig = """//J JOB A
//S EXEC PGM=IEBGENER
//SYSUT1 DD DSN=A,DISP=SHR
//SYSUT2 DD DSN=B,DISP=(NEW,CATLG)
//S EXEC PGM=IEBGENER
//SYSUT1 DD DSN=B,DISP=SHR
//SYSUT2 DD DSN=C,DISP=(NEW,CATLG)
"""
    lines = orig.splitlines()
    swapped = "\n".join([lines[0]] + lines[4:7] + lines[1:4]) + "\n"
    assert compare_versions(orig, swapped).label == "DIFFERENT"


def test_opaque_swap_is_undetermined_without_abends():
    orig = """//J JOB A
//T1 EXEC PGM=IKJEFT01
//SYSTSPRT DD SYSOUT=*
//T2 EXEC PGM=IKJEFT01
//SYSTSPRT DD SYSOUT=*
"""
    lines = orig.splitlines()
    swapped = "\n".join([lines[0]] + lines[3:5] + lines[1:3]) + "\n"
    v = compare_versions(orig, swapped, scenario_set="no_abend")
    assert v.label == "UNDETERMINED"
    assert set(v.opaque_touched) == {"T1", "T2"}


def test_split_job_loses_ordering_guarantee():
    lines = PRODUCER_CONSUMER.splitlines()
    split = "\n".join(lines[:4] + ["//J2B JOB CLASS=A"] + lines[4:]) + "\n"
    v = compare_versions(PRODUCER_CONSUMER, split, scenario_set="no_abend")
    assert v.label == "DIFFERENT"
    assert "job_orders" in v.categories or "termination" in v.categories


def test_describe_file_dataflow():
    facts = describe_file(PRODUCER_CONSUMER)
    assert facts.order_pairs == {("MAKE", "USE")}
    assert facts.dataflow_pairs == {("MAKE", "USE")}
