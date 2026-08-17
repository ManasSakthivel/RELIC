"""
Regression tests — known contracts that must always be detectable.

These 5 contracts represent ground-truth behavioral obligations.
If any of these fail to be detected, something has regressed in the extraction pipeline.
"""
from __future__ import annotations
import pytest
from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.parsers.cobol_parser import COBOLParser
from legacy_contract.ir.model import IRGraph, EntityType
from legacy_contract.static_analysis.extractor import StaticContractExtractor
from legacy_contract.contracts.model import ContractType, ContractPredicate


# ── Known Contract 1: Sequential step ordering ──────────────────────────────

KC1_JCL = """
//REGRESS1 JOB (ACCT),'REGRESSION 1'
//ALPHA    EXEC PGM=PROGA
//OUTF     DD  DSN=REG.FILE1,DISP=(NEW,CATLG),UNIT=SYSDA
//BETA     EXEC PGM=PROGB
//INF      DD  DSN=REG.FILE1,DISP=OLD
""".strip().splitlines()


def test_kc1_temporal_ordering_detected():
    """ALPHA ≺ BETA must always be detected as a temporal contract."""
    parser = JCLParser()
    _, ir = parser.parse_lines(KC1_JCL, "kc1.jcl")
    extractor = StaticContractExtractor()
    result = extractor.extract(ir)
    temporal = result.temporal_contracts
    assert len(temporal) >= 1, "KC1: Temporal ordering contract not detected"
    # Find ALPHA → BETA
    found = any(
        True for c in temporal
        if c.predicate == ContractPredicate.PRECEDES
    )
    assert found, "KC1: PRECEDES contract not found"


# ── Known Contract 2: Resource dependency ───────────────────────────────────

def test_kc2_resource_dependency_detected():
    """ALPHA produces REG.FILE1; BETA consumes it — resource contract must be detected."""
    parser = JCLParser()
    _, ir = parser.parse_lines(KC1_JCL, "kc1.jcl")
    extractor = StaticContractExtractor()
    result = extractor.extract(ir)
    resource = result.resource_contracts
    assert len(resource) >= 1, "KC2: Resource dependency contract not detected"
    found = any(c.predicate == ContractPredicate.PRODUCES_BEFORE_CONSUMES for c in resource)
    assert found, "KC2: PRODUCES_BEFORE_CONSUMES contract not found"


# ── Known Contract 3: Control-flow / COND ───────────────────────────────────

KC3_JCL = """
//REGRESS3 JOB (ACCT),'REGRESSION 3'
//STEP010  EXEC PGM=EXTRACT
//OUTF     DD  DSN=EXTRACT.OUTPUT,DISP=(NEW,CATLG),UNIT=SYSDA
//STEP020  EXEC PGM=TRANSFORM,COND=(4,GT,STEP010)
//INF      DD  DSN=EXTRACT.OUTPUT,DISP=OLD
""".strip().splitlines()


def test_kc3_control_flow_detected():
    """COND=(4,GT,STEP010) must generate a control-flow contract."""
    parser = JCLParser()
    _, ir = parser.parse_lines(KC3_JCL, "kc3.jcl")
    extractor = StaticContractExtractor()
    result = extractor.extract(ir)
    ctrl = result.control_flow_contracts
    assert len(ctrl) >= 1, "KC3: Control-flow contract not detected"
    found = any(c.predicate == ContractPredicate.MUST_NOT_FOLLOW_ON_ERROR for c in ctrl)
    assert found, "KC3: MUST_NOT_FOLLOW_ON_ERROR contract not found"


# ── Known Contract 4: COBOL CALL relation ───────────────────────────────────

KC4_COBOL = """
      IDENTIFICATION DIVISION.
      PROGRAM-ID. MAINPROG.
      PROCEDURE DIVISION.
      MAIN-PARA.
          CALL 'SUBPROG'.
          STOP RUN.
""".splitlines()


def test_kc4_cobol_call_detected():
    """CALL 'SUBPROG' must create a CALLS relation in IR."""
    from legacy_contract.ir.model import RelationType
    parser = COBOLParser()
    _, ir = parser.parse_lines(KC4_COBOL, "MAINPROG.cbl")
    calls = ir.get_relations_of_type(RelationType.CALLS)
    assert len(calls) >= 1, "KC4: CALLS relation not detected"
    called_names = {r.target.name.upper() for r in calls}
    assert "SUBPROG" in called_names, "KC4: SUBPROG not found in CALLS targets"


# ── Known Contract 5: Multiple steps = multiple ordering contracts ───────────

KC5_JCL = """
//REGRESS5 JOB (ACCT),'REGRESSION 5'
//STEP001  EXEC PGM=PROGA
//STEP002  EXEC PGM=PROGB
//STEP003  EXEC PGM=PROGC
//STEP004  EXEC PGM=PROGD
""".strip().splitlines()


def test_kc5_ordering_chain_detected():
    """4 steps must produce 3 MUST_PRECEDE relations: 001→002, 002→003, 003→004."""
    parser = JCLParser()
    _, ir = parser.parse_lines(KC5_JCL, "kc5.jcl")
    extractor = StaticContractExtractor()
    result = extractor.extract(ir)
    assert len(result.temporal_contracts) >= 3, \
        f"KC5: Expected ≥3 temporal contracts, got {len(result.temporal_contracts)}"
