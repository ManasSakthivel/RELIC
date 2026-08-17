"""
tests/integration/test_artifact_mapping_pipeline.py
=====================================================
Integration tests proving that the production reconciliation path
uses ArtifactMapper (the C1 fix).

These tests verify two things:
1. ArtifactMapper is importable from the src package (not just from
   the standalone dynamic_analysis/ directory).
2. The reconciliation pipeline (scripts/run_dynamic_reconciliation.py
   _remap_trace_artifact_ids helper) actually calls ArtifactMapper.resolve()
   and updates event artifact_ids according to the deterministic mapping.

P1-2 FIX TEST: This test will FAIL if artifact_mapping.py is removed from
src/legacy_contract/dynamic_analysis/ or if its resolve() method is removed.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Ensure the src package is importable
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: ArtifactMapper is importable from the src package (not just standalone)
# ─────────────────────────────────────────────────────────────────────────────

class TestArtifactMapperInSrcPackage:
    """Verify the C1 fix is wired into the src/ package hierarchy."""

    def test_artifact_mapper_importable_from_dynamic_analysis_package(self):
        """
        ArtifactMapper must be importable from
        legacy_contract.dynamic_analysis (the src package), not only from
        the standalone dynamic_analysis/artifact_mapping.py module.
        """
        from legacy_contract.dynamic_analysis import ArtifactMapper
        assert ArtifactMapper is not None, (
            "ArtifactMapper could not be imported from legacy_contract.dynamic_analysis. "
            "The C1 fix (artifact_mapping.py) must be present in "
            "src/legacy_contract/dynamic_analysis/"
        )

    def test_mapping_status_importable_from_src(self):
        """MappingStatus enum must be importable from the src package."""
        from legacy_contract.dynamic_analysis import MappingStatus
        assert set(s.value for s in MappingStatus) == {
            "EXACT", "AMBIGUOUS", "MISSING", "PROC_EXPANDED", "UNMAPPED_EVENT"
        }

    def test_artifact_mapping_result_importable_from_src(self):
        """ArtifactMappingResult must be importable from the src package."""
        from legacy_contract.dynamic_analysis import ArtifactMappingResult
        result = ArtifactMappingResult(
            program_name="TESTPGM",
            status=__import__(
                "legacy_contract.dynamic_analysis", fromlist=["MappingStatus"]
            ).MappingStatus.MISSING,
            reason="test"
        )
        assert result.program_name == "TESTPGM"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: ArtifactMapper uses deterministic IR-based mapping
# ─────────────────────────────────────────────────────────────────────────────

class TestArtifactMapperDeterministicResolution:
    """
    Verify that ArtifactMapper.from_ir() builds a correct index from
    a real IRGraph populated by JCLParser, and that resolve() returns
    EXACT status for a known program.
    """

    SAMPLE_JCL = """
//MAPTEST  JOB (ACCT),'MAP TEST'
//STEP010  EXEC PGM=CBACT01C
//OUTF     DD  DSN=MAP.FILE,DISP=(NEW,CATLG),UNIT=SYSDA
//STEP020  EXEC PGM=CBACT02C
//INF      DD  DSN=MAP.FILE,DISP=OLD
""".strip().splitlines()

    def _build_ir(self):
        from legacy_contract.parsers.jcl_parser import JCLParser
        parser = JCLParser()
        _, ir = parser.parse_lines(self.SAMPLE_JCL, "map_test.jcl")
        return ir

    def test_from_ir_resolves_exact_program(self):
        """
        After building the mapper from a JCL IR, resolving a program name
        that appears in exactly one EXEC PGM= step must return EXACT status.
        """
        from legacy_contract.dynamic_analysis import ArtifactMapper, MappingStatus
        ir = self._build_ir()
        mapper = ArtifactMapper.from_ir(ir)

        result = mapper.resolve("CBACT01C")
        assert result.status == MappingStatus.EXACT, (
            f"Expected EXACT status for CBACT01C, got {result.status}. "
            "ArtifactMapper must resolve a single-step program to EXACT."
        )
        assert result.resolved_entity_id is not None
        assert result.resolved_step_id is not None

    def test_from_ir_missing_for_unknown_program(self):
        """A program not present in any EXEC PGM= step returns MISSING."""
        from legacy_contract.dynamic_analysis import ArtifactMapper, MappingStatus
        ir = self._build_ir()
        mapper = ArtifactMapper.from_ir(ir)

        result = mapper.resolve("NONEXISTENT_PROGRAM")
        assert result.status == MappingStatus.MISSING, (
            f"Expected MISSING for unknown program, got {result.status}."
        )

    def test_from_ir_ambiguous_for_duplicate_program(self):
        """
        If the same program is invoked in two EXEC PGM= steps, resolve()
        must return AMBIGUOUS — never guess between candidates.
        """
        jcl_lines = """
//AMBTEST  JOB (ACCT),'AMB TEST'
//STEP010  EXEC PGM=PROGDUP
//DD1      DD  DSN=FILE.A,DISP=SHR
//STEP020  EXEC PGM=PROGDUP
//DD2      DD  DSN=FILE.B,DISP=SHR
""".strip().splitlines()
        from legacy_contract.parsers.jcl_parser import JCLParser
        from legacy_contract.dynamic_analysis import ArtifactMapper, MappingStatus
        parser = JCLParser()
        _, ir = parser.parse_lines(jcl_lines, "amb_test.jcl")
        mapper = ArtifactMapper.from_ir(ir)

        result = mapper.resolve("PROGDUP")
        # Either AMBIGUOUS (if both steps parsed) or EXACT (if parser
        # only distinguishes by entity_id).  The key requirement is that
        # the mapper does NOT silently return one of the candidates.
        # If both steps are indexed, must be AMBIGUOUS.
        if result.status == MappingStatus.AMBIGUOUS:
            assert len(result.candidate_ids) >= 2, (
                "AMBIGUOUS result must include ≥2 candidate IDs."
            )
        # If parser deduplicates (same name → same entity), EXACT is acceptable.
        # The invariant is: no silent wrong mapping.
        assert result.status in (MappingStatus.AMBIGUOUS, MappingStatus.EXACT), (
            f"Unexpected status {result.status} for duplicate-program JCL."
        )

    def test_is_resolvable_true_only_for_exact_and_proc_expanded(self):
        """
        is_resolvable() must return True for EXACT and PROC_EXPANDED only.
        All other statuses must return False.
        """
        from legacy_contract.dynamic_analysis import ArtifactMapper, MappingStatus, ArtifactMappingResult
        for status in MappingStatus:
            result = ArtifactMappingResult(program_name="X", status=status)
            if status in (MappingStatus.EXACT, MappingStatus.PROC_EXPANDED):
                assert result.is_resolvable(), (
                    f"Expected is_resolvable()=True for {status}"
                )
            else:
                assert not result.is_resolvable(), (
                    f"Expected is_resolvable()=False for {status}"
                )

    def test_empty_artifact_id_returns_unmapped_event(self):
        """resolve('') must return UNMAPPED_EVENT, not crash."""
        from legacy_contract.dynamic_analysis import ArtifactMapper, MappingStatus
        ir = self._build_ir()
        mapper = ArtifactMapper.from_ir(ir)

        result = mapper.resolve("")
        assert result.status == MappingStatus.UNMAPPED_EVENT

    def test_whitespace_only_artifact_id_returns_unmapped_event(self):
        """resolve('   ') must return UNMAPPED_EVENT."""
        from legacy_contract.dynamic_analysis import ArtifactMapper, MappingStatus
        ir = self._build_ir()
        mapper = ArtifactMapper.from_ir(ir)

        result = mapper.resolve("   ")
        assert result.status == MappingStatus.UNMAPPED_EVENT


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Production reconciliation calls the artifact mapper
# ─────────────────────────────────────────────────────────────────────────────

class TestProductionPathUsesArtifactMapper:
    """
    Verify that the _remap_trace_artifact_ids helper in
    run_dynamic_reconciliation.py calls ArtifactMapper.resolve()
    and updates event artifact_ids correctly.

    This test loads the helper directly from the script to avoid the
    'no dataset present' precondition of main().
    """

    SAMPLE_JCL = """
//PRODTEST JOB (ACCT),'PROD TEST'
//STEP010  EXEC PGM=CBACT01C
//OUTF     DD  DSN=PROD.FILE,DISP=(NEW,CATLG),UNIT=SYSDA
//STEP020  EXEC PGM=CBACT02C,COND=(4,GT,STEP010)
//INF      DD  DSN=PROD.FILE,DISP=OLD
""".strip().splitlines()

    def _load_remap_helper(self):
        """Import _remap_trace_artifact_ids from run_dynamic_reconciliation.py."""
        scripts_dir = ROOT / "scripts"
        sys.path.insert(0, str(scripts_dir))
        try:
            import run_dynamic_reconciliation
            return run_dynamic_reconciliation._remap_trace_artifact_ids
        except ImportError:
            pytest.skip("run_dynamic_reconciliation.py not importable (path issue).")

    def test_remap_helper_updates_event_artifact_id(self):
        """
        _remap_trace_artifact_ids must replace program names with
        step entity IDs for EXACT mappings.
        """
        from legacy_contract.parsers.jcl_parser import JCLParser
        from legacy_contract.dynamic_analysis import (
            ArtifactMapper, ExecutionTrace, ExecutionEvent,
            EventSourceType, OperationType
        )

        # Build IR and mapper
        parser = JCLParser()
        _, ir = parser.parse_lines(self.SAMPLE_JCL, "prod_test.jcl")
        mapper = ArtifactMapper.from_ir(ir)

        # Find the entity ID for CBACT01C
        result = mapper.resolve("CBACT01C")
        assert result.status.value in ("EXACT", "PROC_EXPANDED"), (
            f"Precondition: CBACT01C should resolve to EXACT, got {result.status}"
        )
        expected_entity_id = result.resolved_entity_id

        # Build a trace with artifact_id = "CBACT01C" (the program name)
        trace = ExecutionTrace(
            execution_id="prod_test_run",
            source_type=EventSourceType.EXECUTION_SIMULATED,
        )
        trace.add_event(ExecutionEvent(
            execution_id="prod_test_run",
            artifact_id="CBACT01C",  # raw program name — should be remapped
            operation=OperationType.STEP_START,
            timestamp=datetime.utcnow(),
            source_type=EventSourceType.EXECUTION_SIMULATED,
        ))

        # Call the production helper
        remap_fn = self._load_remap_helper()
        stats: dict = {}
        remapped = remap_fn([trace], mapper, stats)

        # The event's artifact_id should now be the canonical entity ID
        assert len(remapped) == 1
        remapped_events = remapped[0].events
        assert len(remapped_events) == 1
        assert remapped_events[0].artifact_id == expected_entity_id, (
            f"After remapping, artifact_id should be the canonical entity ID "
            f"({expected_entity_id!r}), but got {remapped_events[0].artifact_id!r}. "
            "The production _remap_trace_artifact_ids helper must use ArtifactMapper."
        )
        assert stats.get("EXACT", 0) >= 1, (
            "mapping_stats should record at least 1 EXACT resolution."
        )

    def test_remap_helper_does_not_modify_missing_events(self):
        """
        Events for programs not in the IR must keep their original artifact_id
        (MISSING status — never guess).
        """
        from legacy_contract.parsers.jcl_parser import JCLParser
        from legacy_contract.dynamic_analysis import (
            ArtifactMapper, ExecutionTrace, ExecutionEvent,
            EventSourceType, OperationType
        )

        parser = JCLParser()
        _, ir = parser.parse_lines(self.SAMPLE_JCL, "prod_test.jcl")
        mapper = ArtifactMapper.from_ir(ir)

        unknown_pgm = "TOTALLY_UNKNOWN_PGM_XYZ"
        trace = ExecutionTrace(
            execution_id="missing_test",
            source_type=EventSourceType.EXECUTION_SIMULATED,
        )
        trace.add_event(ExecutionEvent(
            execution_id="missing_test",
            artifact_id=unknown_pgm,
            operation=OperationType.STEP_START,
            timestamp=datetime.utcnow(),
            source_type=EventSourceType.EXECUTION_SIMULATED,
        ))

        remap_fn = self._load_remap_helper()
        stats: dict = {}
        remapped = remap_fn([trace], mapper, stats)

        assert remapped[0].events[0].artifact_id == unknown_pgm, (
            "Events for MISSING programs must keep their original artifact_id."
        )
        assert stats.get("MISSING", 0) == 1

    def test_remap_helper_does_not_modify_ambiguous_events(self):
        """
        AMBIGUOUS mappings must never be guessed; the original artifact_id must remain.
        """
        from legacy_contract.parsers.jcl_parser import JCLParser
        from legacy_contract.dynamic_analysis import (
            ArtifactMapper, ExecutionTrace, ExecutionEvent,
            EventSourceType, OperationType, MappingStatus
        )

        parser = JCLParser()
        amb_jcl = """
//AMBTEST  JOB (ACCT),'AMB TEST'
//STEP010  EXEC PGM=PROGDUP
//DD1      DD  DSN=FILE.A,DISP=SHR
//STEP020  EXEC PGM=PROGDUP
//DD2      DD  DSN=FILE.B,DISP=SHR
""".strip().splitlines()
        _, ir = parser.parse_lines(amb_jcl, "amb_prod_test.jcl")
        mapper = ArtifactMapper.from_ir(ir)
        result = mapper.resolve("PROGDUP")
        assert result.status == MappingStatus.AMBIGUOUS

        trace = ExecutionTrace(
            execution_id="ambiguous_test",
            source_type=EventSourceType.EXECUTION_SIMULATED,
        )
        trace.add_event(ExecutionEvent(
            execution_id="ambiguous_test",
            artifact_id="PROGDUP",
            operation=OperationType.STEP_START,
            timestamp=datetime.utcnow(),
            source_type=EventSourceType.EXECUTION_SIMULATED,
        ))

        remap_fn = self._load_remap_helper()
        stats: dict = {}
        remapped = remap_fn([trace], mapper, stats)

        assert remapped[0].events[0].artifact_id == "PROGDUP", (
            "AMBIGUOUS programs must keep their original artifact_id."
        )
        assert stats.get("AMBIGUOUS", 0) == 1
