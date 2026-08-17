"""
Unit tests for JCL Parser.

Tests cover:
- Simple 3-step job parsing
- EXEC PGM= extraction
- DD DSN= / DISP= extraction with PRODUCES and CONSUMES semantics
- MUST_PRECEDE relation generation between sequential steps
- COND parameter extraction
- Continuation line merging
- Comment line skipping
- Unparsed construct logging
- Parametrized multi-sample tests
"""

from __future__ import annotations

import textwrap

import pytest

from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.ir.model import EntityType, RelationType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse(jcl: str) -> tuple:
    """Convenience: strip leading indentation and parse."""
    lines = textwrap.dedent(jcl).splitlines()
    parser = JCLParser()
    return parser.parse_lines(lines, artifact_path="test.jcl")


# ---------------------------------------------------------------------------
# 1. Simple three-step job parsing
# ---------------------------------------------------------------------------

THREE_STEP_JCL = """\
//TESTJOB  JOB CLASS=A,MSGCLASS=X
//STEP01   EXEC PGM=PROGONE
//STEP02   EXEC PGM=PROGTWO
//STEP03   EXEC PGM=PROGTHREE
"""


def test_three_step_job_entity_counts():
    """Parsing a 3-step job should produce 1 JOB, 3 STEPs, and 3 PROGRAMs."""
    _, ir = parse(THREE_STEP_JCL)

    jobs = [e for e in ir.entities.values() if e.entity_type == EntityType.JOB]
    steps = [e for e in ir.entities.values() if e.entity_type == EntityType.STEP]
    programs = [e for e in ir.entities.values() if e.entity_type == EntityType.PROGRAM]

    assert len(jobs) == 1, f"Expected 1 JOB, got {len(jobs)}"
    assert len(steps) == 3, f"Expected 3 STEPs, got {len(steps)}"
    assert len(programs) == 3, f"Expected 3 PROGRAMs, got {len(programs)}"


def test_three_step_job_names():
    """Job and step names must match the JCL name fields."""
    _, ir = parse(THREE_STEP_JCL)

    job_names = {e.name for e in ir.entities.values() if e.entity_type == EntityType.JOB}
    step_names = {e.name for e in ir.entities.values() if e.entity_type == EntityType.STEP}

    assert "TESTJOB" in job_names
    assert {"STEP01", "STEP02", "STEP03"} == step_names


def test_three_step_job_step_job_containment():
    """Each STEP should have a CONTAINS relation from the JOB."""
    _, ir = parse(THREE_STEP_JCL)

    contains_rels = [r for r in ir.relations if r.relation_type == RelationType.CONTAINS]
    # 3 steps contained by job
    assert len(contains_rels) == 3


# ---------------------------------------------------------------------------
# 2. EXEC PGM= extraction
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("jcl,expected_program", [
    ("//STEP01   EXEC PGM=COBPROG1\n", "COBPROG1"),
    ("//S1       EXEC PGM=IEFBR14\n", "IEFBR14"),
    ("//RUN      EXEC PGM=SORT,PARM='FIELDS=(1,4,CH,A)'\n", "SORT"),
    ("//STEP02   EXEC PGM=IKJEFT01\n", "IKJEFT01"),
])
def test_exec_pgm_extraction(jcl, expected_program):
    """PGM= value should be extracted and stored as a PROGRAM entity."""
    full_jcl = f"//TESTJOB  JOB\n{jcl}"
    _, ir = parse(full_jcl)
    program_names = {
        e.name for e in ir.entities.values()
        if e.entity_type == EntityType.PROGRAM
    }
    assert expected_program in program_names, (
        f"Expected program '{expected_program}' in {program_names}"
    )


def test_exec_pgm_calls_relation():
    """EXEC PGM= must produce a CALLS relation from STEP to PROGRAM."""
    _, ir = parse("//TESTJOB  JOB\n//STEP01   EXEC PGM=MYPROGRAM\n")

    calls_rels = [r for r in ir.relations if r.relation_type == RelationType.CALLS]
    assert len(calls_rels) == 1

    rel = calls_rels[0]
    assert rel.source.entity_type == EntityType.STEP
    assert rel.target.entity_type == EntityType.PROGRAM
    assert rel.target.name == "MYPROGRAM"
    assert rel.confidence == 1.0


# ---------------------------------------------------------------------------
# 3. DD DSN= extraction — PRODUCES (DISP=NEW) and CONSUMES (DISP=OLD)
# ---------------------------------------------------------------------------

DD_PRODUCES_JCL = """\
//TESTJOB  JOB
//STEP01   EXEC PGM=WRITER
//OUTPUT   DD  DSN=MY.OUTPUT.FILE,DISP=(NEW,CATLG,DELETE)
"""

DD_CONSUMES_JCL = """\
//TESTJOB  JOB
//STEP01   EXEC PGM=READER
//INPUT    DD  DSN=MY.INPUT.FILE,DISP=OLD
"""

DD_SHR_JCL = """\
//TESTJOB  JOB
//STEP01   EXEC PGM=READER
//INPUT    DD  DSN=MY.SHARED.FILE,DISP=SHR
"""


def test_dd_dsn_new_produces_dataset():
    """DISP=NEW should produce a PRODUCES relation to the dataset entity."""
    _, ir = parse(DD_PRODUCES_JCL)

    produces_rels = [r for r in ir.relations if r.relation_type == RelationType.PRODUCES]
    assert len(produces_rels) == 1

    rel = produces_rels[0]
    assert rel.source.entity_type == EntityType.STEP
    assert rel.target.entity_type == EntityType.DATASET
    assert "MY.OUTPUT.FILE" in rel.target.name


def test_dd_dsn_old_consumes_dataset():
    """DISP=OLD should produce a CONSUMES relation to the dataset entity."""
    _, ir = parse(DD_CONSUMES_JCL)

    consumes_rels = [r for r in ir.relations if r.relation_type == RelationType.CONSUMES]
    assert len(consumes_rels) == 1

    rel = consumes_rels[0]
    assert rel.source.entity_type == EntityType.STEP
    assert rel.target.entity_type == EntityType.DATASET
    assert "MY.INPUT.FILE" in rel.target.name


def test_dd_dsn_shr_consumes_dataset():
    """DISP=SHR (shared read) should also produce a CONSUMES relation."""
    _, ir = parse(DD_SHR_JCL)

    consumes_rels = [r for r in ir.relations if r.relation_type == RelationType.CONSUMES]
    assert len(consumes_rels) == 1


@pytest.mark.parametrize("disp,expected_rel_type", [
    ("NEW", RelationType.PRODUCES),
    ("CATLG", RelationType.PRODUCES),
    ("PASS", RelationType.PRODUCES),
    ("MOD", RelationType.PRODUCES),
    ("OLD", RelationType.CONSUMES),
    ("SHR", RelationType.CONSUMES),
])
def test_dd_disp_variations(disp, expected_rel_type):
    """Various DISP values should map to PRODUCES or CONSUMES correctly."""
    jcl = (
        f"//TESTJOB  JOB\n"
        f"//STEP01   EXEC PGM=PROG\n"
        f"//MYFILE   DD  DSN=SOME.DATASET,DISP={disp}\n"
    )
    _, ir = parse(jcl)
    rel_types = {r.relation_type for r in ir.relations}
    assert expected_rel_type in rel_types, (
        f"DISP={disp} should produce {expected_rel_type}, got {rel_types}"
    )


def test_dd_entity_linked_to_step():
    """Each DD statement should produce a JCL_DD entity linked to its step via USES_RESOURCE."""
    _, ir = parse(DD_PRODUCES_JCL)

    uses_rels = [r for r in ir.relations if r.relation_type == RelationType.USES_RESOURCE]
    assert len(uses_rels) >= 1

    dd_entities = [e for e in ir.entities.values() if e.entity_type == EntityType.JCL_DD]
    assert len(dd_entities) == 1
    assert dd_entities[0].name == "STEP01.OUTPUT"


# ---------------------------------------------------------------------------
# 4. MUST_PRECEDE relation between sequential steps
# ---------------------------------------------------------------------------

def test_must_precede_two_steps():
    """Two sequential steps must have a MUST_PRECEDE relation."""
    jcl = "//TESTJOB  JOB\n//STEP01   EXEC PGM=A\n//STEP02   EXEC PGM=B\n"
    _, ir = parse(jcl)

    precede_rels = [r for r in ir.relations if r.relation_type == RelationType.MUST_PRECEDE]
    assert len(precede_rels) == 1

    rel = precede_rels[0]
    assert rel.source.name == "STEP01"
    assert rel.target.name == "STEP02"
    assert rel.confidence == 1.0
    assert rel.attributes.get("basis") == "jcl_sequential_order"


def test_must_precede_three_steps():
    """Three sequential steps must have two MUST_PRECEDE relations: 1→2 and 2→3."""
    _, ir = parse(THREE_STEP_JCL)

    precede_rels = [r for r in ir.relations if r.relation_type == RelationType.MUST_PRECEDE]
    assert len(precede_rels) == 2

    pairs = {(r.source.name, r.target.name) for r in precede_rels}
    assert ("STEP01", "STEP02") in pairs
    assert ("STEP02", "STEP03") in pairs


def test_single_step_no_must_precede():
    """A job with only one step should produce no MUST_PRECEDE relations."""
    jcl = "//TESTJOB  JOB\n//STEP01   EXEC PGM=PROG\n"
    _, ir = parse(jcl)

    precede_rels = [r for r in ir.relations if r.relation_type == RelationType.MUST_PRECEDE]
    assert len(precede_rels) == 0


# ---------------------------------------------------------------------------
# 5. COND parameter extraction
# ---------------------------------------------------------------------------

COND_JCL = """\
//TESTJOB  JOB
//STEP01   EXEC PGM=FIRST
//STEP02   EXEC PGM=SECOND,COND=(4,GT,STEP01)
"""

COND_NO_REF_JCL = """\
//TESTJOB  JOB
//STEP01   EXEC PGM=FIRST
//STEP02   EXEC PGM=SECOND,COND=(0,NE)
"""


def test_cond_parameter_stored_in_attributes():
    """COND parameter must be stored in the step's attributes dict."""
    _, ir = parse(COND_JCL)

    step02_entities = [
        e for e in ir.entities.values()
        if e.entity_type == EntityType.STEP and e.name == "STEP02"
    ]
    assert len(step02_entities) == 1
    assert "cond" in step02_entities[0].attributes
    cond_val = step02_entities[0].attributes["cond"]
    assert "4" in cond_val
    assert "GT" in cond_val.upper()


def test_cond_no_step_reference_stored():
    """COND without a step reference is stored and does not crash the parser."""
    _, ir = parse(COND_NO_REF_JCL)

    step02_entities = [
        e for e in ir.entities.values()
        if e.entity_type == EntityType.STEP and e.name == "STEP02"
    ]
    assert len(step02_entities) == 1
    assert "cond" in step02_entities[0].attributes


def test_step_without_cond_has_no_cond_attribute():
    """Steps without COND should not have a 'cond' key in attributes."""
    _, ir = parse(THREE_STEP_JCL)

    for entity in ir.entities.values():
        if entity.entity_type == EntityType.STEP:
            assert "cond" not in entity.attributes, (
                f"Step {entity.name} should not have cond attribute"
            )


# ---------------------------------------------------------------------------
# 6. Continuation line merging
# ---------------------------------------------------------------------------

CONTINUATION_JCL = (
    "//TESTJOB  JOB\n"
    "//STEP01   EXEC PGM=PROG\n"
    "//INFILE   DD  DSN=LONG.DATASET.NAME,\n"
    "//               DISP=OLD\n"
)


def test_continuation_merging_produces_one_dd():
    """A DD statement split across continuation lines should produce exactly one DD entity."""
    result, ir = parse(CONTINUATION_JCL)

    dd_entities = [e for e in ir.entities.values() if e.entity_type == EntityType.JCL_DD]
    # Should have one DD entity named STEP01.INFILE
    assert len(dd_entities) == 1


def test_continuation_merging_extracts_dsn():
    """DSN from a continuation-merged DD statement should be extracted correctly."""
    _, ir = parse(CONTINUATION_JCL)

    datasets = [e for e in ir.entities.values() if e.entity_type == EntityType.DATASET]
    dataset_names = {e.name for e in datasets}
    assert "LONG.DATASET.NAME" in dataset_names


def test_continuation_merging_produces_consumes_relation():
    """Merged continuation line with DISP=OLD should produce a CONSUMES relation."""
    _, ir = parse(CONTINUATION_JCL)

    consumes_rels = [r for r in ir.relations if r.relation_type == RelationType.CONSUMES]
    assert len(consumes_rels) == 1


# ---------------------------------------------------------------------------
# 7. Comment line skipping
# ---------------------------------------------------------------------------

COMMENT_JCL = """\
//TESTJOB  JOB
//* This is a comment and should be skipped entirely
//STEP01   EXEC PGM=PROG
//* Another comment
//STEP02   EXEC PGM=PROG2
"""


def test_comment_lines_are_skipped():
    """Comment lines (//*) must not produce parse tokens, entities, or relations."""
    result, ir = parse(COMMENT_JCL)

    # Tokens should only be JOB, EXEC, EXEC — not comments
    token_ops = [t.operation for t in result.tokens]
    assert "COMMENT" not in token_ops

    # Still should have 2 steps
    steps = [e for e in ir.entities.values() if e.entity_type == EntityType.STEP]
    assert len(steps) == 2


def test_comment_lines_not_in_unparsed():
    """Comment lines must NOT appear in unparsed_lines (they are intentionally skipped)."""
    result, _ = parse(COMMENT_JCL)

    for line_no, line in result.unparsed_lines:
        assert not line.strip().startswith("//*"), (
            f"Comment line should not appear in unparsed_lines: {line!r}"
        )


# ---------------------------------------------------------------------------
# 8. Unparsed construct logging
# ---------------------------------------------------------------------------

UNPARSED_JCL = """\
//TESTJOB  JOB
//STEP01   EXEC PGM=PROG
THIS IS A FREE-FORMAT LINE NOT IN JCL FORMAT
//STEP02   EXEC PGM=PROG2
"""


def test_non_jcl_lines_logged_as_unparsed():
    """Lines not starting with '//' (and not blank) should appear in unparsed_lines."""
    result, _ = parse(UNPARSED_JCL)

    unparsed_texts = [line for _, line in result.unparsed_lines]
    assert any("FREE-FORMAT" in t for t in unparsed_texts)


def test_unparsed_lines_do_not_cause_crash():
    """Unparsed lines should be silently logged, not raise exceptions."""
    jcl = "//TESTJOB  JOB\nRANDOM NON JCL LINE\n//STEP01 EXEC PGM=X\n"
    # Should not raise
    result, ir = parse(jcl)
    assert result is not None
    assert ir is not None


# ---------------------------------------------------------------------------
# 9. Deterministic entity IDs
# ---------------------------------------------------------------------------

def test_entity_ids_are_deterministic():
    """Parsing the same JCL twice must produce identical entity IDs."""
    _, ir1 = parse(THREE_STEP_JCL)
    _, ir2 = parse(THREE_STEP_JCL)

    ids1 = set(ir1.entities.keys())
    ids2 = set(ir2.entities.keys())
    assert ids1 == ids2


def test_entity_ids_are_stable_hex_strings():
    """Entity IDs should be 16-character hex strings."""
    _, ir = parse(THREE_STEP_JCL)
    for entity_id in ir.entities:
        assert len(entity_id) == 16, f"ID {entity_id!r} is not 16 chars"
        assert all(c in "0123456789abcdef" for c in entity_id), (
            f"ID {entity_id!r} contains non-hex characters"
        )


# ---------------------------------------------------------------------------
# 10. Parametrized multi-sample test: parse result non-empty
# ---------------------------------------------------------------------------

MULTI_SAMPLE_JCL = [
    (
        "minimal_job",
        "//MINJOB   JOB\n//STEP01   EXEC PGM=IEFBR14\n",
        1,  # expected step count
        0,  # expected MUST_PRECEDE count
    ),
    (
        "two_step",
        "//JOB2     JOB\n//S1       EXEC PGM=A\n//S2       EXEC PGM=B\n",
        2,
        1,
    ),
    (
        "four_step",
        (
            "//JOB4     JOB\n"
            "//ST1      EXEC PGM=A\n"
            "//ST2      EXEC PGM=B\n"
            "//ST3      EXEC PGM=C\n"
            "//ST4      EXEC PGM=D\n"
        ),
        4,
        3,
    ),
]


@pytest.mark.parametrize("name,jcl,expected_steps,expected_precede", MULTI_SAMPLE_JCL)
def test_multi_sample_step_count(name, jcl, expected_steps, expected_precede):
    """Parametrized: step count must match expected for each sample."""
    _, ir = parse(jcl)
    steps = [e for e in ir.entities.values() if e.entity_type == EntityType.STEP]
    assert len(steps) == expected_steps, (
        f"[{name}] Expected {expected_steps} steps, got {len(steps)}"
    )


@pytest.mark.parametrize("name,jcl,expected_steps,expected_precede", MULTI_SAMPLE_JCL)
def test_multi_sample_must_precede_count(name, jcl, expected_steps, expected_precede):
    """Parametrized: MUST_PRECEDE count should be (steps-1)."""
    _, ir = parse(jcl)
    precede_rels = [r for r in ir.relations if r.relation_type == RelationType.MUST_PRECEDE]
    assert len(precede_rels) == expected_precede, (
        f"[{name}] Expected {expected_precede} MUST_PRECEDE rels, got {len(precede_rels)}"
    )


# ---------------------------------------------------------------------------
# 11. IR Graph integrity
# ---------------------------------------------------------------------------

def test_ir_artifact_path_recorded():
    """artifact_path must be recorded in the IRGraph."""
    _, ir = parse(THREE_STEP_JCL)
    assert "test.jcl" in ir.artifact_paths


def test_all_entities_have_artifact_path():
    """Every entity must have a non-empty artifact_path."""
    _, ir = parse(THREE_STEP_JCL)
    for entity in ir.entities.values():
        assert entity.artifact_path, f"Entity {entity.name} has no artifact_path"


def test_produces_confidence_is_1():
    """PRODUCES relations extracted from JCL grammar must have confidence=1.0."""
    _, ir = parse(DD_PRODUCES_JCL)
    produces_rels = [r for r in ir.relations if r.relation_type == RelationType.PRODUCES]
    for rel in produces_rels:
        assert rel.confidence == 1.0
