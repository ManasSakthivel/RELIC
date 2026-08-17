"""
Tests for dynamic_analysis/artifact_mapping.py

Covers:
- exact program → step mapping
- multiple steps invoking same program (AMBIGUOUS)
- missing program (MISSING)
- ambiguous mapping never guesses
- PROC invocation (PROC_EXPANDED)
- duplicate program invocation across JCL files
- empty artifact_id (UNMAPPED_EVENT)
"""
from __future__ import annotations

import sys
import pathlib

# Allow running directly or via pytest from legacy-contract/
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from dynamic_analysis.artifact_mapping import ArtifactMapper, MappingStatus, ArtifactMappingResult


# ---------------------------------------------------------------------------
# Minimal IR stub for testing
# ---------------------------------------------------------------------------

class _FakeEntity:
    def __init__(self, entity_id, name, entity_type="STEP", metadata=None):
        self.entity_id = entity_id
        self.name = name
        self.entity_type = entity_type
        self.metadata = metadata or {}


class _FakeIR:
    """Minimal IR stub that exposes .entities dict."""
    def __init__(self, entities):
        # dict[entity_id → _FakeEntity]
        self.entities = {e.entity_id: e for e in entities}


def _make_step(entity_id, step_name, pgm=None, proc=None, jcl_file="TEST.jcl"):
    meta = {"source_file": jcl_file}
    if pgm:
        meta["exec_pgm"] = pgm
    if proc:
        meta["exec_proc"] = proc
    return _FakeEntity(entity_id, step_name, entity_type="STEP", metadata=meta)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_exact_program_to_step():
    """Single EXEC PGM= invocation resolves deterministically."""
    ir = _FakeIR([
        _make_step("eid_001", "STEP01", pgm="CBACT01C", jcl_file="CARDFILE.jcl"),
    ])
    mapper = ArtifactMapper.from_ir(ir)
    result = mapper.resolve("CBACT01C")
    assert result.status == MappingStatus.EXACT, f"Expected EXACT, got {result.status}"
    assert result.resolved_entity_id == "eid_001"
    assert result.step_name == "STEP01"
    assert result.is_resolvable()


def test_exact_mapping_case_insensitive():
    """Program name lookup is case-insensitive."""
    ir = _FakeIR([
        _make_step("eid_002", "STEP02", pgm="CBACT02C"),
    ])
    mapper = ArtifactMapper.from_ir(ir)
    result = mapper.resolve("cbact02c")
    assert result.status == MappingStatus.EXACT
    assert result.resolved_entity_id == "eid_002"


def test_multiple_steps_invoking_same_program_is_ambiguous():
    """
    If two steps EXEC the same PGM, result must be AMBIGUOUS.
    The mapper MUST NOT pick one — that would be a guess.
    """
    ir = _FakeIR([
        _make_step("eid_010", "STEP01", pgm="SORTPGM", jcl_file="JOB1.jcl"),
        _make_step("eid_011", "STEP02", pgm="SORTPGM", jcl_file="JOB1.jcl"),
    ])
    mapper = ArtifactMapper.from_ir(ir)
    result = mapper.resolve("SORTPGM")
    assert result.status == MappingStatus.AMBIGUOUS, f"Expected AMBIGUOUS, got {result.status}"
    assert len(result.candidate_ids) == 2
    assert "eid_010" in result.candidate_ids
    assert "eid_011" in result.candidate_ids
    assert not result.is_resolvable()
    assert result.resolved_entity_id is None  # Must not guess


def test_missing_program():
    """Program not found in IR returns MISSING."""
    ir = _FakeIR([
        _make_step("eid_020", "STEP01", pgm="KNOWNPGM"),
    ])
    mapper = ArtifactMapper.from_ir(ir)
    result = mapper.resolve("UNKNOWNPGM")
    assert result.status == MappingStatus.MISSING
    assert not result.is_resolvable()
    assert "UNKNOWNPGM" in result.reason


def test_empty_artifact_id():
    """Empty or whitespace artifact_id returns UNMAPPED_EVENT."""
    ir = _FakeIR([_make_step("eid_030", "STEP01", pgm="MYPGM")])
    mapper = ArtifactMapper.from_ir(ir)

    r1 = mapper.resolve("")
    assert r1.status == MappingStatus.UNMAPPED_EVENT

    r2 = mapper.resolve("   ")
    assert r2.status == MappingStatus.UNMAPPED_EVENT


def test_proc_invocation():
    """EXEC PROC= resolves to PROC_EXPANDED when unambiguous."""
    ir = _FakeIR([
        _make_step("eid_040", "PROCINV", proc="MYRPTPRC", jcl_file="REPORT.jcl"),
    ])
    mapper = ArtifactMapper.from_ir(ir)
    result = mapper.resolve("MYRPTPRC")
    assert result.status == MappingStatus.PROC_EXPANDED
    assert result.resolved_entity_id == "eid_040"
    assert result.is_resolvable()


def test_duplicate_program_invocation_across_jcl_files():
    """
    Same program invoked in two different JCL files →
    AMBIGUOUS (no cross-file heuristic).
    """
    ir = _FakeIR([
        _make_step("eid_050", "SORT1", pgm="DFSORT", jcl_file="JOBALPHA.jcl"),
        _make_step("eid_051", "SORT2", pgm="DFSORT", jcl_file="JOBBETA.jcl"),
    ])
    mapper = ArtifactMapper.from_ir(ir)
    result = mapper.resolve("DFSORT")
    assert result.status == MappingStatus.AMBIGUOUS
    assert len(result.candidate_ids) == 2


def test_unmapped_execution_event_not_in_ir():
    """Execution event for program that exists nowhere in any JCL → MISSING."""
    ir = _FakeIR([
        _make_step("eid_060", "STEP01", pgm="CBCMP01"),
    ])
    mapper = ArtifactMapper.from_ir(ir)
    result = mapper.resolve("PHANTOM_PGM")
    assert result.status == MappingStatus.MISSING


def test_ambiguous_never_returns_resolved_entity():
    """AMBIGUOUS result must have resolved_entity_id=None to prevent silent guessing."""
    ir = _FakeIR([
        _make_step("eid_070", "STPA", pgm="SHARED"),
        _make_step("eid_071", "STPB", pgm="SHARED"),
    ])
    mapper = ArtifactMapper.from_ir(ir)
    result = mapper.resolve("SHARED")
    assert result.status == MappingStatus.AMBIGUOUS
    assert result.resolved_entity_id is None
    assert result.resolved_step_id is None


def test_all_programs_list():
    """all_programs() returns all known program names in upper-case."""
    ir = _FakeIR([
        _make_step("e1", "S1", pgm="PGMA"),
        _make_step("e2", "S2", pgm="PGMB"),
        _make_step("e3", "S3", proc="MYPROC"),
    ])
    mapper = ArtifactMapper.from_ir(ir)
    programs = mapper.all_programs()
    assert "PGMA" in programs
    assert "PGMB" in programs
    assert "MYPROC" not in programs  # procs are separate


def test_all_procs_list():
    """all_procs() returns all known proc names in upper-case."""
    ir = _FakeIR([
        _make_step("e1", "S1", pgm="PGMA"),
        _make_step("e2", "S2", proc="PROCX"),
    ])
    mapper = ArtifactMapper.from_ir(ir)
    procs = mapper.all_procs()
    assert "PROCX" in procs
    assert "PGMA" not in procs


if __name__ == "__main__":
    tests = [
        test_exact_program_to_step,
        test_exact_mapping_case_insensitive,
        test_multiple_steps_invoking_same_program_is_ambiguous,
        test_missing_program,
        test_empty_artifact_id,
        test_proc_invocation,
        test_duplicate_program_invocation_across_jcl_files,
        test_unmapped_execution_event_not_in_ir,
        test_ambiguous_never_returns_resolved_entity,
        test_all_programs_list,
        test_all_procs_list,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except Exception as exc:
            print(f"  FAIL: {t.__name__} — {exc}")
            failed += 1
    print(f"\n{passed}/{passed+failed} passed")
    if failed:
        sys.exit(1)
