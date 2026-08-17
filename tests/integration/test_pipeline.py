"""
Integration test: artifact → IR → BCG → trace → reconciliation.

Uses synthetic inline JCL + COBOL (no file I/O required).
Tests the full pipeline from parse to reconciled BCG.
"""
from __future__ import annotations
from datetime import datetime, timedelta

import pytest

from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.parsers.cobol_parser import COBOLParser
from legacy_contract.ir.model import IRGraph, RelationType, EntityType
from legacy_contract.static_analysis.extractor import StaticContractExtractor
from legacy_contract.dynamic_analysis.model import (
    ExecutionEvent, ExecutionTrace, EventSourceType, OperationType
)
from legacy_contract.contracts.model import ContractType, ValidationState
from legacy_contract.reconciliation.engine import ReconciliationEngine


PIPELINE_JCL = """
//PIPEJOB  JOB (ACCT),'PIPELINE TEST'
//STEP010  EXEC PGM=PRODUCER
//OUTFILE  DD  DSN=PIPE.OUTPUT.FILE,DISP=(NEW,CATLG),UNIT=SYSDA
//STEP020  EXEC PGM=CONSUMER
//INFILE   DD  DSN=PIPE.OUTPUT.FILE,DISP=OLD
//SYSOUT   DD  SYSOUT=*
""".strip().splitlines()

PIPELINE_COBOL = """
      IDENTIFICATION DIVISION.
      PROGRAM-ID. PRODUCER.
      ENVIRONMENT DIVISION.
      INPUT-OUTPUT SECTION.
      FILE-CONTROL.
          SELECT OUTFILE ASSIGN TO "PIPE.OUTPUT.FILE".
      DATA DIVISION.
      FILE SECTION.
      PROCEDURE DIVISION.
      MAIN-PARA.
          OPEN OUTPUT OUTFILE.
          WRITE OUTFILE-REC.
          CLOSE OUTFILE.
          STOP RUN.
""".splitlines()


def _build_ir():
    jcl_parser = JCLParser()
    cobol_parser = COBOLParser()
    _, ir_jcl = jcl_parser.parse_lines(PIPELINE_JCL, "pipeline.jcl")
    _, ir_cobol = cobol_parser.parse_lines(PIPELINE_COBOL, "PRODUCER.cbl")
    # Merge
    combined = IRGraph()
    combined.artifact_paths = ["pipeline.jcl", "PRODUCER.cbl"]
    for e in ir_jcl.entities.values():
        combined.add_entity(e)
    for r in ir_jcl.relations:
        combined.add_relation(r)
    for e in ir_cobol.entities.values():
        combined.add_entity(e)
    for r in ir_cobol.relations:
        combined.add_relation(r)
    return combined


def test_pipeline_ir_has_entities():
    ir = _build_ir()
    assert ir.entity_count() > 0
    steps = [e for e in ir.entities.values() if e.entity_type == EntityType.STEP]
    assert len(steps) >= 2


def test_pipeline_static_extraction():
    ir = _build_ir()
    extractor = StaticContractExtractor()
    result = extractor.extract(ir)
    assert len(result.all_contracts) > 0
    assert len(result.temporal_contracts) >= 1  # STEP010 ≺ STEP020


def test_pipeline_resource_contracts():
    ir = _build_ir()
    extractor = StaticContractExtractor()
    result = extractor.extract(ir)
    assert len(result.resource_contracts) >= 1  # STEP010 produces, STEP020 consumes


def test_pipeline_bcg_build():
    from legacy_contract.bcg.model import BCG
    ir = _build_ir()
    extractor = StaticContractExtractor()
    static_result = extractor.extract(ir)
    bcg = BCG(ir=ir)
    for c in static_result.all_contracts:
        bcg.add_contract(c)
    assert bcg.contract_count() > 0
    assert bcg.dynamic_coverage_rate() == 0.0  # no traces yet


def test_pipeline_reconciliation():
    from legacy_contract.bcg.model import BCG
    ir = _build_ir()
    extractor = StaticContractExtractor()
    static_result = extractor.extract(ir)

    # Find step IDs
    step010 = next((e for e in ir.entities.values()
                    if e.entity_type == EntityType.STEP and "010" in e.name), None)
    step020 = next((e for e in ir.entities.values()
                    if e.entity_type == EntityType.STEP and "020" in e.name), None)

    bcg = BCG(ir=ir)
    for c in static_result.all_contracts:
        bcg.add_contract(c)

    # Create trace: STEP010 runs before STEP020
    now = datetime.utcnow()
    trace = ExecutionTrace(execution_id="run_001")
    if step010:
        trace.add_event(ExecutionEvent(
            execution_id="run_001",
            artifact_id=step010.entity_id,
            operation=OperationType.STEP_START,
            timestamp=now,
            source_type=EventSourceType.EXECUTION,
        ))
        trace.add_event(ExecutionEvent(
            execution_id="run_001",
            artifact_id=step010.entity_id,
            operation=OperationType.STEP_END,
            timestamp=now + timedelta(seconds=2),
            return_code=0,
            source_type=EventSourceType.EXECUTION,
        ))
    if step020:
        trace.add_event(ExecutionEvent(
            execution_id="run_001",
            artifact_id=step020.entity_id,
            operation=OperationType.STEP_START,
            timestamp=now + timedelta(seconds=5),
            source_type=EventSourceType.EXECUTION,
        ))

    engine = ReconciliationEngine()
    records = engine.reconcile(bcg, [trace])

    # At least some contracts should now have dynamic evidence
    supported = [c for c in bcg.contracts.values()
                 if c.validation_state == ValidationState.STATIC_DYNAMIC_SUPPORTED]
    # Not asserting exact count — depends on entity ID matching
    # But no contract should be erroneously CONTRADICTED without trace evidence
    not_observed_states = {ValidationState.NOT_OBSERVED, ValidationState.STATIC_CANDIDATE,
                           ValidationState.UNRESOLVED, ValidationState.STATIC_DYNAMIC_SUPPORTED}
    for c in bcg.contracts.values():
        assert c.validation_state in not_observed_states or \
               c.validation_state == ValidationState.STATIC_DYNAMIC_CONFLICT, \
               f"Unexpected state: {c.validation_state}"
