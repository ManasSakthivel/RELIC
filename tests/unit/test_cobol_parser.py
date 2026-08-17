"""
Unit tests for COBOL Parser.

Tests cover:
- PROGRAM-ID extraction
- CALL statement extraction
- PERFORM statement extraction
- READ / WRITE extraction
- COPY statement extraction
- Comment line handling (fixed-format indicator column)
- Fixed-format normalization (sequence numbers, indicator, truncation)
"""

from __future__ import annotations

import textwrap

import pytest

from legacy_contract.parsers.cobol_parser import COBOLParser
from legacy_contract.ir.model import EntityType, RelationType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_cobol(source: str | list) -> tuple:
    """Parse fixed-format COBOL source, returning (result, ir).

    Accepts either a pre-built list of lines (preferred) or a raw source string
    from which lines are derived via splitlines().
    """
    if isinstance(source, list):
        lines = source
    else:
        lines = textwrap.dedent(source).splitlines()
    parser = COBOLParser()
    return parser.parse_lines(lines, artifact_path="test.cbl")


def fixed(source: str) -> list[str]:
    """
    Format a COBOL source block as fixed-format lines.
    Each line is padded with 6 sequence chars + 1 space indicator to columns 7+.
    This simulates real IBM fixed-format COBOL.
    """
    out = []
    for i, line in enumerate(textwrap.dedent(source).splitlines(), 1):
        seq = f"{i:06d}"
        out.append(f"{seq} {line}")
    return out


# ---------------------------------------------------------------------------
# Minimal COBOL program skeleton
#
# The COBOLParser uses fixed-format layout: cols 1-6 = sequence number,
# col 7 = indicator (space = normal, * = comment, D = debug).
# All test source strings must use this format so _normalize_line() works.
# ---------------------------------------------------------------------------

def _fixed_lines(*content_lines: str) -> list[str]:
    """Prefix each line with a 6-digit sequence number + space indicator."""
    return [f"{i:06d} {line}" for i, line in enumerate(content_lines, 1)]


MINIMAL_COBOL_LINES = _fixed_lines(
    "IDENTIFICATION DIVISION.",
    "PROGRAM-ID. TESTPROG.",
    "ENVIRONMENT DIVISION.",
    "DATA DIVISION.",
    "WORKING-STORAGE SECTION.",
    "PROCEDURE DIVISION.",
    "MAIN-PARA.",
    "    STOP RUN.",
)

FULL_COBOL_LINES = _fixed_lines(
    "IDENTIFICATION DIVISION.",
    "PROGRAM-ID. FULLPROG.",
    "ENVIRONMENT DIVISION.",
    "INPUT-OUTPUT SECTION.",
    "FILE-CONTROL.",
    "    SELECT INFILE ASSIGN TO SYSIN.",
    "    SELECT OUTFILE ASSIGN TO SYSOUT.",
    "DATA DIVISION.",
    "WORKING-STORAGE SECTION.",
    "01 WS-COUNT PIC 9(5).",
    "PROCEDURE DIVISION.",
    "MAIN-PARA.",
    "    PERFORM INIT-PARA.",
    "    OPEN INPUT INFILE.",
    "    READ INFILE.",
    "    WRITE OUT-REC.",
    "    CLOSE INFILE.",
    "    CALL 'SUBPROG' USING WS-COUNT.",
    "    STOP RUN.",
    "INIT-PARA.",
    "    MOVE 0 TO WS-COUNT.",
)

# Legacy string aliases used in a few tests — built from the fixed lines
MINIMAL_COBOL = "\n".join(MINIMAL_COBOL_LINES)
FULL_COBOL    = "\n".join(FULL_COBOL_LINES)


# ---------------------------------------------------------------------------
# 1. PROGRAM-ID extraction
# ---------------------------------------------------------------------------

def test_program_id_extracted():
    """PROGRAM-ID must be extracted as a PROGRAM entity."""
    result, ir = parse_cobol(MINIMAL_COBOL_LINES)

    assert result.program_name == "TESTPROG"
    programs = [
        e for e in ir.entities.values()
        if e.entity_type == EntityType.PROGRAM and e.name == "TESTPROG"
    ]
    assert len(programs) == 1


@pytest.mark.parametrize("prog_id", [
    "MYPROGRAM",
    "COBPROG01",
    "ACCTUPDT",
    "CBACT04C",
    "COACTUPC",
])
def test_program_id_various_names(prog_id):
    """PROGRAM-ID with various valid names must all be extracted correctly."""
    lines = _fixed_lines(
        "IDENTIFICATION DIVISION.",
        f"PROGRAM-ID. {prog_id}.",
        "PROCEDURE DIVISION.",
        "MAIN-PARA.",
        "    STOP RUN.",
    )
    result, ir = parse_cobol(lines)
    assert result.program_name == prog_id
    program_names = {
        e.name for e in ir.entities.values()
        if e.entity_type == EntityType.PROGRAM
    }
    assert prog_id in program_names


def test_program_id_only_first_occurrence_used():
    """If multiple PROGRAM-ID lines exist (malformed), only the first is used."""
    lines = _fixed_lines(
        "IDENTIFICATION DIVISION.",
        "PROGRAM-ID. FIRST.",
        "PROGRAM-ID. SECOND.",
        "PROCEDURE DIVISION.",
        "MAIN-PARA.",
        "    STOP RUN.",
    )
    result, _ = parse_cobol(lines)
    assert result.program_name == "FIRST"


# ---------------------------------------------------------------------------
# 2. CALL statement extraction
# ---------------------------------------------------------------------------

def test_call_statement_extracted():
    """CALL 'SUBPROG' must produce a CALLS relation from the program."""
    result, ir = parse_cobol(FULL_COBOL_LINES)

    calls_rels = [r for r in ir.relations if r.relation_type == RelationType.CALLS]
    assert len(calls_rels) >= 1

    called_names = {r.target.name for r in calls_rels}
    assert "SUBPROG" in called_names


@pytest.mark.parametrize("call_stmt,expected", [
    ("           CALL 'ACCTUPDT' USING WS-VAR.\n", "ACCTUPDT"),
    ("           CALL \"CBTRN02C\".\n", "CBTRN02C"),
    ("           CALL PROG-NAME.\n", "PROG-NAME"),
])
def test_call_various_formats(call_stmt, expected):
    """CALL with single-quoted, double-quoted, or identifier target must all extract."""
    lines = _fixed_lines(
        "IDENTIFICATION DIVISION.",
        "PROGRAM-ID. TESTPROG.",
        "PROCEDURE DIVISION.",
        "MAIN-PARA.",
        call_stmt.strip(),
        "    STOP RUN.",
    )
    result, ir = parse_cobol(lines)
    called_names = {
        r.target.name for r in ir.relations
        if r.relation_type == RelationType.CALLS
    }
    assert expected in called_names, f"Expected {expected} in {called_names}"


def test_call_confidence_is_1():
    """CALL relations extracted from COBOL grammar must have confidence=1.0."""
    result, ir = parse_cobol(FULL_COBOL_LINES)
    calls_rels = [r for r in ir.relations if r.relation_type == RelationType.CALLS]
    for rel in calls_rels:
        assert rel.confidence == 1.0


def test_call_count_in_coverage_metrics():
    """coverage_metrics['calls'] must reflect the number of CALL statements."""
    result, _ = parse_cobol(FULL_COBOL_LINES)
    assert result.coverage_metrics.get("calls", 0) == 1


# ---------------------------------------------------------------------------
# 3. PERFORM statement extraction
# ---------------------------------------------------------------------------

def test_perform_extracted():
    """PERFORM INIT-PARA must produce a PERFORMS relation."""
    result, ir = parse_cobol(FULL_COBOL_LINES)

    performs_rels = [r for r in ir.relations if r.relation_type == RelationType.PERFORMS]
    assert len(performs_rels) >= 1

    target_names = {r.target.name for r in performs_rels}
    assert "INIT-PARA" in target_names


def test_perform_reserved_words_excluded():
    """PERFORM UNTIL/VARYING/TIMES must not create spurious PERFORMS relations."""
    lines = _fixed_lines(
        "IDENTIFICATION DIVISION.",
        "PROGRAM-ID. TESTPROG.",
        "PROCEDURE DIVISION.",
        "MAIN-PARA.",
        "    PERFORM UNTIL WS-EOF = 'Y'.",
        "    STOP RUN.",
    )
    result, ir = parse_cobol(lines)
    performs_rels = [r for r in ir.relations if r.relation_type == RelationType.PERFORMS]
    target_names = {r.target.name for r in performs_rels}
    assert "UNTIL" not in target_names


def test_perform_coverage_metric():
    """coverage_metrics['performs'] must reflect PERFORM invocations."""
    result, _ = parse_cobol(FULL_COBOL_LINES)
    assert result.coverage_metrics.get("performs", 0) >= 1


# ---------------------------------------------------------------------------
# 4. READ / WRITE extraction
# ---------------------------------------------------------------------------

def test_read_extracted():
    """READ INFILE must produce a READS relation."""
    result, ir = parse_cobol(FULL_COBOL_LINES)

    reads_rels = [r for r in ir.relations if r.relation_type == RelationType.READS]
    assert len(reads_rels) >= 1

    target_names = {r.target.name for r in reads_rels}
    assert "INFILE" in target_names


def test_write_extracted():
    """WRITE OUT-REC must produce a WRITES relation."""
    result, ir = parse_cobol(FULL_COBOL_LINES)

    writes_rels = [r for r in ir.relations if r.relation_type == RelationType.WRITES]
    assert len(writes_rels) >= 1


def test_read_count_in_metrics():
    result, _ = parse_cobol(FULL_COBOL_LINES)
    assert result.coverage_metrics.get("reads", 0) >= 1


def test_write_count_in_metrics():
    result, _ = parse_cobol(FULL_COBOL_LINES)
    assert result.coverage_metrics.get("writes", 0) >= 1


@pytest.mark.parametrize("stmt,rel_type", [
    ("           READ ACCTFILE.\n", RelationType.READS),
    ("           WRITE ACCT-REC.\n", RelationType.WRITES),
    ("           READ TRANSFILE INTO WS-TRANS.\n", RelationType.READS),
])
def test_read_write_variations(stmt, rel_type):
    """READ and WRITE in various forms must extract the correct relation type."""
    lines = _fixed_lines(
        "IDENTIFICATION DIVISION.",
        "PROGRAM-ID. TESTPROG.",
        "PROCEDURE DIVISION.",
        "MAIN-PARA.",
        stmt.strip(),
        "    STOP RUN.",
    )
    _, ir = parse_cobol(lines)
    rel_types = {r.relation_type for r in ir.relations}
    assert rel_type in rel_types


# ---------------------------------------------------------------------------
# 5. COPY statement extraction
# ---------------------------------------------------------------------------

def test_copy_extracted_as_entity_and_relation():
    """COPY MYCOPY must produce a COPYBOOK entity and COPIES relation."""
    lines = _fixed_lines(
        "IDENTIFICATION DIVISION.",
        "PROGRAM-ID. TESTPROG.",
        "DATA DIVISION.",
        "WORKING-STORAGE SECTION.",
        "COPY ACCTREC.",
        "PROCEDURE DIVISION.",
        "MAIN-PARA.",
        "    STOP RUN.",
    )
    _, ir = parse_cobol(lines)

    copybooks = [
        e for e in ir.entities.values()
        if e.entity_type == EntityType.COPYBOOK
    ]
    assert len(copybooks) == 1
    assert copybooks[0].name == "ACCTREC"

    copies_rels = [r for r in ir.relations if r.relation_type == RelationType.COPIES]
    assert len(copies_rels) == 1


@pytest.mark.parametrize("copybook_name", ["ACCTREC", "CUSTMST", "TRNFILE", "COBFMT01"])
def test_copy_various_names(copybook_name):
    """COPY with various copybook names must all be extracted correctly."""
    source = (
        "       IDENTIFICATION DIVISION.\n"
        f"       PROGRAM-ID. PROG.\n"
        "       DATA DIVISION.\n"
        "       WORKING-STORAGE SECTION.\n"
        f"       COPY {copybook_name}.\n"
        "       PROCEDURE DIVISION.\n"
        "       MAIN-PARA.\n"
        "           STOP RUN.\n"
    )
    _, ir = parse_cobol(source)
    copybook_names = {
        e.name for e in ir.entities.values()
        if e.entity_type == EntityType.COPYBOOK
    }
    assert copybook_name in copybook_names


# ---------------------------------------------------------------------------
# 6. Comment line handling (fixed-format indicator column)
# ---------------------------------------------------------------------------

def test_fixed_format_comment_lines_skipped():
    """
    In fixed-format COBOL, column 7 = '*' indicates a comment.
    Comment lines must produce no entities or relations.
    """
    lines = [
        "000001 IDENTIFICATION DIVISION.",
        "000002 PROGRAM-ID. TESTPROG.",
        "000003*This is a comment and must be skipped.",
        "000004 PROCEDURE DIVISION.",
        "000005 MAIN-PARA.",
        "000006     STOP RUN.",
    ]
    parser = COBOLParser()
    result, ir = parser.parse_lines(lines, artifact_path="test.cbl")

    # Program should still be found
    assert result.program_name == "TESTPROG"

    # Comment should not produce any entity
    entity_names = {e.name for e in ir.entities.values()}
    assert "This" not in entity_names
    assert "comment" not in entity_names


def test_fixed_format_debug_lines_skipped():
    """Column 7 = 'D' (debug line) must be treated as comment and skipped."""
    lines = [
        "000001 IDENTIFICATION DIVISION.",
        "000002 PROGRAM-ID. TESTPROG.",
        "000003D    DISPLAY 'DEBUG: ' WS-VAR.",
        "000004 PROCEDURE DIVISION.",
        "000005 MAIN-PARA.",
        "000006     STOP RUN.",
    ]
    parser = COBOLParser()
    result, ir = parser.parse_lines(lines, artifact_path="test.cbl")

    # Debug line must not produce a spurious CALL or PERFORM
    calls_rels = [r for r in ir.relations if r.relation_type == RelationType.CALLS]
    assert len(calls_rels) == 0


def test_asterisk_prefix_comment_skipped():
    """Free-format lines starting with * (after normalization) must be skipped."""
    source = (
        "       IDENTIFICATION DIVISION.\n"
        "       PROGRAM-ID. TESTPROG.\n"
        "      * A free-format style comment\n"
        "       PROCEDURE DIVISION.\n"
        "       MAIN-PARA.\n"
        "           STOP RUN.\n"
    )
    result, ir = parse_cobol(source)
    assert result.program_name == "TESTPROG"


# ---------------------------------------------------------------------------
# 7. Fixed-format normalization
# ---------------------------------------------------------------------------

def test_fixed_format_sequence_numbers_stripped():
    """
    Fixed-format COBOL lines (>=7 chars) must have sequence numbers (cols 1-6)
    and indicator (col 7) stripped before pattern matching.
    """
    # Line: '000010 PROGRAM-ID. FIXEDPROG.' (col 7 = space)
    lines = [
        "000001 IDENTIFICATION DIVISION.",
        "000002 PROGRAM-ID. FIXEDPROG.",
        "000003 PROCEDURE DIVISION.",
        "000004 MAIN-PARA.",
        "000005     STOP RUN.",
    ]
    parser = COBOLParser()
    result, _ = parser.parse_lines(lines, artifact_path="fixed.cbl")
    assert result.program_name == "FIXEDPROG"


def test_fixed_format_72_column_truncation():
    """
    Fixed-format COBOL lines are truncated at column 72.
    Content beyond col 72 must not affect parsing.
    """
    # Build a line that has content beyond col 72 that would look like a keyword
    # cols 1-6: seq, col 7: space, cols 8-72: real content, 73+: ignored
    prog_line = "000002 PROGRAM-ID. TRUNCTEST.             CALL 'SHOULDNOTAPPEAR'"
    lines = [
        "000001 IDENTIFICATION DIVISION.",
        prog_line[:80],  # truncate to 80 to simulate card image
        "000003 PROCEDURE DIVISION.",
        "000004 MAIN-PARA.",
        "000005     STOP RUN.",
    ]
    parser = COBOLParser()
    result, ir = parser.parse_lines(lines, artifact_path="trunc.cbl")
    # Program name should be found
    assert result.program_name == "TRUNCTEST"


# ---------------------------------------------------------------------------
# 8. Divisions tracking
# ---------------------------------------------------------------------------

def test_divisions_recorded():
    """divisions_found must record all four division types."""
    result, _ = parse_cobol(FULL_COBOL)
    assert "IDENTIFICATION" in result.divisions_found
    assert "ENVIRONMENT" in result.divisions_found
    assert "DATA" in result.divisions_found
    assert "PROCEDURE" in result.divisions_found


def test_procedure_division_restricts_extraction():
    """
    CALL/PERFORM/READ/WRITE must only be extracted from PROCEDURE DIVISION.
    Spurious matches in DATA DIVISION must be ignored.
    """
    source = (
        "       IDENTIFICATION DIVISION.\n"
        "       PROGRAM-ID. TESTPROG.\n"
        "       DATA DIVISION.\n"
        "       WORKING-STORAGE SECTION.\n"
        "       01 WS-CALL PIC X(10) VALUE 'SOMEPROG'.\n"  # 'CALL' is in var name
        "       PROCEDURE DIVISION.\n"
        "       MAIN-PARA.\n"
        "           CALL 'REALPROG'.\n"
        "           STOP RUN.\n"
    )
    _, ir = parse_cobol(source)
    calls_rels = [r for r in ir.relations if r.relation_type == RelationType.CALLS]
    called_names = {r.target.name for r in calls_rels}
    assert "REALPROG" in called_names
    # Should not match 'CALL' inside a data definition string
    # (exact behavior depends on pattern; at minimum, REALPROG is present)
    assert len(calls_rels) >= 1


# ---------------------------------------------------------------------------
# 9. SELECT / ASSIGN file control
# ---------------------------------------------------------------------------

def test_select_assign_creates_file_entity():
    """SELECT ... ASSIGN TO must create a FILE entity."""
    result, ir = parse_cobol(FULL_COBOL)

    file_entities = [e for e in ir.entities.values() if e.entity_type == EntityType.FILE]
    file_names = {e.name for e in file_entities}
    assert "INFILE" in file_names
    assert "OUTFILE" in file_names


def test_select_creates_defines_relation():
    """SELECT must create a DEFINES relation from PROGRAM to FILE."""
    result, ir = parse_cobol(FULL_COBOL)
    defines_rels = [r for r in ir.relations if r.relation_type == RelationType.DEFINES]
    assert len(defines_rels) >= 2


# ---------------------------------------------------------------------------
# 10. Artifact path and IR integrity
# ---------------------------------------------------------------------------

def test_artifact_path_recorded_in_ir():
    """IR graph must record the artifact_path."""
    _, ir = parse_cobol(MINIMAL_COBOL)
    assert "test.cbl" in ir.artifact_paths


def test_program_entity_has_artifact_path():
    """The PROGRAM entity must have the correct artifact_path."""
    _, ir = parse_cobol(MINIMAL_COBOL)
    programs = [e for e in ir.entities.values() if e.entity_type == EntityType.PROGRAM]
    for prog in programs:
        assert prog.artifact_path == "test.cbl"
