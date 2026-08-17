"""
Tests — unit tests for JCL parser, COBOL parser, contracts, and reconciliation.
Complete, self-contained, no external fixtures required.
"""
from __future__ import annotations
import copy
from datetime import datetime, timedelta
import pytest

from legacy_contract.ir.model import EntityType, IRGraph, RelationType
from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.parsers.cobol_parser import COBOLParser
from legacy_contract.contracts.model import (
    Contract, ContractPredicate, ContractType,
    ConfidenceVector, ExtractionMethod, ProvenanceRecord,
    ValidationState,
)
from legacy_contract.dynamic_analysis.model import (
    ExecutionEvent, ExecutionTrace, EventSourceType, OperationType
)
from legacy_contract.reconciliation.engine import ReconciliationEngine, ReconciliationOutcome


# ── JCL Parser ──────────────────────────────────────────────────────────────

SIMPLE_JCL = """
//TESTJOB  JOB (ACCT),'TEST JOB',CLASS=A,MSGCLASS=X
//STEP010  EXEC PGM=CBACT01C
//ACCTFILE DD  DSN=ACCT.DATA.FILE,DISP=(NEW,CATLG),
//             UNIT=SYSDA,SPACE=(CYL,(10,5))
//STEP020  EXEC PGM=CBACT02C,COND=(4,GT,STEP010)
//ACCTFILE DD  DSN=ACCT.DATA.FILE,DISP=OLD
//SYSOUT   DD  SYSOUT=*
""".strip().splitlines()


def test_jcl_job_extracted():
    parser = JCLParser()
    result, ir = parser.parse_lines(SIMPLE_JCL, "test.jcl")
    jobs = [e for e in ir.entities.values() if e.entity_type == EntityType.JOB]
    assert len(jobs) == 1
    assert jobs[0].name.upper() in ("TESTJOB", "TEST")


def test_jcl_steps_extracted():
    parser = JCLParser()
    _, ir = parser.parse_lines(SIMPLE_JCL, "test.jcl")
    steps = [e for e in ir.entities.values() if e.entity_type == EntityType.STEP]
    assert len(steps) == 2
    step_names = {s.name.upper() for s in steps}
    assert "STEP010" in step_names
    assert "STEP020" in step_names


def test_jcl_program_exec_extracted():
    parser = JCLParser()
    _, ir = parser.parse_lines(SIMPLE_JCL, "test.jcl")
    programs = [e for e in ir.entities.values() if e.entity_type == EntityType.PROGRAM]
    prog_names = {p.name.upper() for p in programs}
    assert "CBACT01C" in prog_names
    assert "CBACT02C" in prog_names


def test_jcl_dataset_extracted():
    parser = JCLParser()
    _, ir = parser.parse_lines(SIMPLE_JCL, "test.jcl")
    datasets = [e for e in ir.entities.values() if e.entity_type == EntityType.DATASET]
    assert len(datasets) >= 1
    dsn_names = {d.name for d in datasets}
    assert any("ACCT.DATA.FILE" in n for n in dsn_names)


def test_jcl_step_ordering_relation():
    """Sequential steps must generate MUST_PRECEDE relation."""
    parser = JCLParser()
    _, ir = parser.parse_lines(SIMPLE_JCL, "test.jcl")
    precede_rels = ir.get_relations_of_type(RelationType.MUST_PRECEDE)
    assert len(precede_rels) >= 1


def test_jcl_produces_relation():
    """DISP=NEW should create PRODUCES relation."""
    parser = JCLParser()
    _, ir = parser.parse_lines(SIMPLE_JCL, "test.jcl")
    produces = ir.get_relations_of_type(RelationType.PRODUCES)
    assert len(produces) >= 1


def test_jcl_consumes_relation():
    """DISP=OLD should create CONSUMES relation."""
    parser = JCLParser()
    _, ir = parser.parse_lines(SIMPLE_JCL, "test.jcl")
    consumes = ir.get_relations_of_type(RelationType.CONSUMES)
    assert len(consumes) >= 1


def test_jcl_cond_extracted():
    """COND parameter should be stored on step attributes."""
    parser = JCLParser()
    _, ir = parser.parse_lines(SIMPLE_JCL, "test.jcl")
    steps = [e for e in ir.entities.values() if e.entity_type == EntityType.STEP]
    step020 = next((s for s in steps if s.name.upper() == "STEP020"), None)
    assert step020 is not None
    assert "cond" in step020.attributes


def test_jcl_comment_ignored():
    jcl = [
        "//* This is a comment",
        "//MYJOB   JOB (ACCT),'JOB'",
        "//STEP010 EXEC PGM=MYPROG",
    ]
    parser = JCLParser()
    result, ir = parser.parse_lines(jcl, "test.jcl")
    # Comment should not be an entity
    assert not any(e.name == "This" for e in ir.entities.values())


def test_jcl_continuation_merging():
    jcl = [
        "//MYJOB   JOB (ACCT),'JOB'",
        "//STEP010 EXEC PGM=MYPROG",
        "//INFILE  DD  DSN=MY.INPUT,",
        "//             DISP=OLD",
    ]
    parser = JCLParser()
    result, ir = parser.parse_lines(jcl, "test.jcl")
    # Should parse without error despite continuation
    assert len(result.parse_errors) == 0


def test_jcl_empty_input():
    parser = JCLParser()
    result, ir = parser.parse_lines([], "empty.jcl")
    assert ir.entity_count() == 0


# ── COBOL Parser ────────────────────────────────────────────────────────────

SIMPLE_COBOL = """
      IDENTIFICATION DIVISION.
      PROGRAM-ID. CBACT01C.
      ENVIRONMENT DIVISION.
      INPUT-OUTPUT SECTION.
      FILE-CONTROL.
          SELECT ACCTFILE ASSIGN TO "ACCTFILE".
      DATA DIVISION.
      FILE SECTION.
      WORKING-STORAGE SECTION.
      COPY COACTB00.
      PROCEDURE DIVISION.
      MAIN-PARA.
          OPEN INPUT ACCTFILE.
          READ ACCTFILE
              AT END MOVE 'Y' TO WS-EOF
          END-READ.
          CLOSE ACCTFILE.
          CALL 'CBACT02C'.
          PERFORM CLEANUP-PARA.
          STOP RUN.
      CLEANUP-PARA.
          MOVE 0 TO RETURN-CODE.
""".splitlines()


def test_cobol_program_id():
    parser = COBOLParser()
    result, ir = parser.parse_lines(SIMPLE_COBOL, "CBACT01C.cbl")
    assert result.program_name.upper() == "CBACT01C"
    programs = [e for e in ir.entities.values() if e.entity_type == EntityType.PROGRAM
                and e.name.upper() == "CBACT01C"]
    assert len(programs) == 1


def test_cobol_call_extracted():
    parser = COBOLParser()
    result, ir = parser.parse_lines(SIMPLE_COBOL, "CBACT01C.cbl")
    calls = ir.get_relations_of_type(RelationType.CALLS)
    called_names = {r.target.name.upper() for r in calls}
    assert "CBACT02C" in called_names


def test_cobol_perform_extracted():
    parser = COBOLParser()
    result, ir = parser.parse_lines(SIMPLE_COBOL, "CBACT01C.cbl")
    performs = ir.get_relations_of_type(RelationType.PERFORMS)
    assert len(performs) >= 1


def test_cobol_read_extracted():
    parser = COBOLParser()
    result, ir = parser.parse_lines(SIMPLE_COBOL, "CBACT01C.cbl")
    reads = ir.get_relations_of_type(RelationType.READS)
    assert len(reads) >= 1


def test_cobol_copy_extracted():
    parser = COBOLParser()
    result, ir = parser.parse_lines(SIMPLE_COBOL, "CBACT01C.cbl")
    copies = ir.get_relations_of_type(RelationType.COPIES)
    assert len(copies) >= 1
    cb_names = {r.target.name.upper() for r in copies}
    assert "COACTB00" in cb_names


def test_cobol_file_select_extracted():
    parser = COBOLParser()
    result, ir = parser.parse_lines(SIMPLE_COBOL, "CBACT01C.cbl")
    files = [e for e in ir.entities.values() if e.entity_type == EntityType.FILE]
    assert len(files) >= 1
    file_names = {f.name.upper() for f in files}
    assert "ACCTFILE" in file_names


def test_cobol_empty_program():
    cobol = [
        "      IDENTIFICATION DIVISION.",
        "      PROGRAM-ID. EMPTYPROG.",
        "      PROCEDURE DIVISION.",
        "      MAIN-PARA.",
        "          STOP RUN.",
    ]
    parser = COBOLParser()
    result, ir = parser.parse_lines(cobol, "EMPTY.cbl")
    assert result.program_name.upper() == "EMPTYPROG"


# ── Contract Model ──────────────────────────────────────────────────────────

def _make_contract(vstate=ValidationState.STATIC_CANDIDATE) -> Contract:
    prov = ProvenanceRecord(
        source_artifact="test.jcl",
        source_location="10:1",
        extraction_method=ExtractionMethod.DETERMINISTIC,
    )
    cv = ConfidenceVector(
        static_support=0.9,
        dynamic_support=0.0,
        provenance_quality=1.0,
    )
    return Contract(
        contract_type=ContractType.TEMPORAL,
        subject_id="entity_a",
        predicate=ContractPredicate.PRECEDES,
        object_id="entity_b",
        natural_language="A must precede B",
        provenance=prov,
        confidence=cv,
        validation_state=vstate,
    )


def test_contract_creation():
    c = _make_contract()
    assert c.contract_type == ContractType.TEMPORAL
    assert c.predicate == ContractPredicate.PRECEDES
    assert c.validation_state == ValidationState.STATIC_CANDIDATE
    assert c.contract_id  # non-empty UUID


def test_confidence_aggregate_in_range():
    cv = ConfidenceVector(
        static_support=1.0,
        dynamic_support=0.8,
        cross_artifact_support=0.5,
        provenance_quality=1.0,
        human_validation=0.0,
        execution_frequency=0.7,
        ambiguity_penalty=0.1,
    )
    score = cv.aggregate()
    assert 0.0 <= score <= 1.0


def test_confidence_zero_when_no_evidence():
    cv = ConfidenceVector()
    assert cv.aggregate() == 0.0


def test_confidence_max_not_exceeded():
    cv = ConfidenceVector(
        static_support=1.0,
        dynamic_support=1.0,
        cross_artifact_support=1.0,
        provenance_quality=1.0,
        human_validation=1.0,
        execution_frequency=1.0,
        ambiguity_penalty=0.0,
    )
    assert cv.aggregate() <= 1.0


def test_not_observed_not_contradicted():
    """
    SCIENTIFIC PRINCIPLE: NOT_OBSERVED must never equal CONTRADICTED.
    This regression test ensures the distinction is maintained.
    """
    assert ValidationState.NOT_OBSERVED != ValidationState.STATIC_DYNAMIC_CONFLICT
    c = _make_contract(ValidationState.NOT_OBSERVED)
    assert not c.has_conflict()
    assert not c.is_validated()


def test_provenance_evidence_tracking():
    prov = ProvenanceRecord(
        source_artifact="test.jcl",
        source_location="1:1",
        extraction_method=ExtractionMethod.DETERMINISTIC,
    )
    assert not prov.has_dynamic_evidence()
    assert not prov.has_static_evidence()


# ── Reconciliation Engine ────────────────────────────────────────────────────

def _make_temporal_contract(subject_id: str, object_id: str) -> Contract:
    from legacy_contract.contracts.model import EvidenceItem
    prov = ProvenanceRecord(
        source_artifact="test.jcl",
        source_location="1:1",
        extraction_method=ExtractionMethod.DETERMINISTIC,
        static_evidence=[EvidenceItem(
            evidence_type="static_structural",
            content="JCL sequential order",
            extraction_method=ExtractionMethod.DETERMINISTIC,
        )],
    )
    return Contract(
        contract_type=ContractType.TEMPORAL,
        subject_id=subject_id,
        predicate=ContractPredicate.PRECEDES,
        object_id=object_id,
        natural_language=f"{subject_id} precedes {object_id}",
        provenance=prov,
        confidence=ConfidenceVector(static_support=1.0),
        validation_state=ValidationState.STATIC_CANDIDATE,
    )


def _make_trace_with_ordering(a_id: str, b_id: str, a_before_b: bool) -> ExecutionTrace:
    """Create a trace where A and B execute in specified order."""
    now = datetime.utcnow()
    if a_before_b:
        t_a = now
        t_b = now + timedelta(seconds=5)
    else:
        t_a = now + timedelta(seconds=5)
        t_b = now

    ea = ExecutionEvent(
        execution_id="run001",
        artifact_id=a_id,
        operation=OperationType.STEP_START,
        timestamp=t_a,
        source_type=EventSourceType.EXECUTION,
    )
    eb = ExecutionEvent(
        execution_id="run001",
        artifact_id=b_id,
        operation=OperationType.STEP_START,
        timestamp=t_b,
        source_type=EventSourceType.EXECUTION,
    )
    trace = ExecutionTrace(execution_id="run001")
    trace.add_event(ea)
    trace.add_event(eb)
    return trace


def test_reconciliation_temporal_supported():
    """When A executes before B, temporal contract should be SUPPORTED."""
    from legacy_contract.bcg.model import BCG
    from legacy_contract.ir.model import IRGraph

    bcg = BCG(ir=IRGraph())
    contract = _make_temporal_contract("entity_a", "entity_b")
    bcg.add_contract(contract)

    trace = _make_trace_with_ordering("entity_a", "entity_b", a_before_b=True)
    engine = ReconciliationEngine()
    records = engine.reconcile(bcg, [trace])

    assert len(records) == 1
    assert records[0].outcome == ReconciliationOutcome.SUPPORTED
    assert contract.validation_state == ValidationState.STATIC_DYNAMIC_SUPPORTED


def test_reconciliation_temporal_contradicted():
    """When B executes before A, temporal contract should be CONTRADICTED."""
    from legacy_contract.bcg.model import BCG
    from legacy_contract.ir.model import IRGraph

    bcg = BCG(ir=IRGraph())
    contract = _make_temporal_contract("entity_a", "entity_b")
    bcg.add_contract(contract)

    trace = _make_trace_with_ordering("entity_a", "entity_b", a_before_b=False)
    engine = ReconciliationEngine()
    records = engine.reconcile(bcg, [trace])

    assert records[0].outcome == ReconciliationOutcome.CONTRADICTED
    assert contract.validation_state == ValidationState.STATIC_DYNAMIC_CONFLICT


def test_reconciliation_not_observed_when_no_events():
    """No traces → NOT_OBSERVED, never CONTRADICTED."""
    from legacy_contract.bcg.model import BCG
    from legacy_contract.ir.model import IRGraph

    bcg = BCG(ir=IRGraph())
    contract = _make_temporal_contract("entity_x", "entity_y")
    bcg.add_contract(contract)

    engine = ReconciliationEngine()
    records = engine.reconcile(bcg, [])  # empty traces

    assert records[0].outcome == ReconciliationOutcome.NOT_OBSERVED
    # CRITICAL: must be NOT_OBSERVED, not CONTRADICTED
    assert contract.validation_state == ValidationState.NOT_OBSERVED
    assert contract.validation_state != ValidationState.STATIC_DYNAMIC_CONFLICT


def test_reconciliation_confidence_updated():
    """After SUPPORTED reconciliation, dynamic_support should be > 0."""
    from legacy_contract.bcg.model import BCG
    from legacy_contract.ir.model import IRGraph

    bcg = BCG(ir=IRGraph())
    contract = _make_temporal_contract("entity_a", "entity_b")
    assert contract.confidence.dynamic_support == 0.0  # before reconciliation

    bcg.add_contract(contract)
    trace = _make_trace_with_ordering("entity_a", "entity_b", a_before_b=True)
    engine = ReconciliationEngine()
    engine.reconcile(bcg, [trace])

    assert contract.confidence.dynamic_support > 0.0


def test_reconciliation_does_not_downgrade_human_validated():
    """HUMAN_VALIDATED contracts must not be downgraded by execution evidence."""
    from legacy_contract.bcg.model import BCG
    from legacy_contract.ir.model import IRGraph

    bcg = BCG(ir=IRGraph())
    contract = _make_temporal_contract("entity_a", "entity_b")
    contract.validation_state = ValidationState.HUMAN_VALIDATED
    bcg.add_contract(contract)

    # Even if no execution evidence, should stay HUMAN_VALIDATED
    engine = ReconciliationEngine()
    engine.reconcile(bcg, [])
    assert contract.validation_state == ValidationState.HUMAN_VALIDATED
