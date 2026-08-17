"""
Unit tests for semantically-preserving negative mutations.

Tests verify that:
1. All 5 negative mutation operators apply successfully to a minimal BCG
2. BCGDiff shows zero broken/modified contracts after each mutation
3. NegativeMutationRecord.expected_detection == False for all operators
4. ValueError is raised when a BCG lacks required structure

These mutations provide ground-truth TN (true negative) cases for H3 FPR baseline.
"""

from __future__ import annotations

import pytest

from legacy_contract.bcg.model import BCG
from legacy_contract.contracts.model import (
    ConfidenceVector,
    Contract,
    ContractPredicate,
    ContractType,
    ProvenanceRecord,
    ValidationState,
)
from legacy_contract.ir.model import (
    EntityType,
    IREntity,
    IRGraph,
    IRRelation,
    RelationType,
)
from legacy_contract.mutations.negative_mutations import (
    NegativeMutationEngine,
    NegativeMutationRecord,
    NegativeOperator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_bcg_with_three_steps() -> BCG:
    """
    Minimal BCG:
      STEP010 --MUST_PRECEDE--> STEP020
      STEP010 has comment + acct attributes
      STEP020 has acct attribute
      STEP030 is isolated (no MUST_PRECEDE, not in any contract) — for RENAME_PROC_LABEL
      STEP010 and STEP030 have no ordering constraint between them — for REORDER_INDEPENDENT
      One TEMPORAL contract: STEP010 PRECEDES STEP020
    """
    ir = IRGraph()

    step_a = IREntity(
        entity_type=EntityType.STEP,
        name="STEP010",
        artifact_path="TEST.JCL",
        attributes={"comment": "First step", "acct": "ACCT001"},
    )
    step_b = IREntity(
        entity_type=EntityType.STEP,
        name="STEP020",
        artifact_path="TEST.JCL",
        attributes={"acct": "ACCT001"},
    )
    # STEP030 is truly unreferenced: not a target of any MUST_PRECEDE,
    # not involved in any contract — valid for RENAME_PROC_LABEL.
    # Also has no ordering relation to STEP010 — valid for REORDER_INDEPENDENT_STEPS.
    step_c = IREntity(
        entity_type=EntityType.STEP,
        name="STEP030",
        artifact_path="TEST.JCL",
        attributes={},
    )

    ir.add_entity(step_a)
    ir.add_entity(step_b)
    ir.add_entity(step_c)

    # Only A -> B; STEP030 is not a target of any MUST_PRECEDE
    rel_ab = IRRelation(
        relation_type=RelationType.MUST_PRECEDE,
        source=step_a,
        target=step_b,
    )
    ir.add_relation(rel_ab)

    bcg = BCG(ir=ir, bcg_id="test-bcg-001")

    # TEMPORAL contract: STEP010 PRECEDES STEP020
    c = Contract(
        contract_type=ContractType.TEMPORAL,
        subject_id=step_a.entity_id,
        predicate=ContractPredicate.PRECEDES,
        object_id=step_b.entity_id,
        natural_language="STEP010 must precede STEP020",
        scope="batch",
        provenance=ProvenanceRecord(
            source_artifact="TEST.JCL",
            source_location="TEST.JCL:5:0",
        ),
        validation_state=ValidationState.STATIC_CANDIDATE,
        confidence=ConfidenceVector(static_support=1.0),
    )
    bcg.add_contract(c)
    return bcg


# ---------------------------------------------------------------------------
# Helper: verify negative mutation invariants
# ---------------------------------------------------------------------------

def _assert_no_detection(original_bcg: BCG, mutated_bcg: BCG, record: NegativeMutationRecord) -> None:
    """Assert all invariants that must hold for every negative mutation."""
    assert isinstance(record, NegativeMutationRecord)
    assert record.expected_detection is False, (
        f"Operator {record.operator} must have expected_detection=False"
    )
    assert record.category == "NEGATIVE_SEMANTICS_PRESERVING"
    diff = original_bcg.diff(mutated_bcg)
    assert len(diff.broken) == 0, (
        f"{record.operator}: expected 0 broken contracts, got {len(diff.broken)}"
    )
    assert len(diff.modified) == 0, (
        f"{record.operator}: expected 0 modified contracts, got {len(diff.modified)}"
    )
    assert len(diff.preserved) == len(original_bcg.contracts), (
        f"{record.operator}: expected all {len(original_bcg.contracts)} contracts preserved"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_rename_step_comment_no_detection():
    """RENAME_STEP_COMMENT must preserve all contracts (diff.broken == 0)."""
    engine = NegativeMutationEngine()
    bcg = _make_bcg_with_three_steps()
    mutated, record = engine.apply(bcg, NegativeOperator.RENAME_STEP_COMMENT, seed=42)
    _assert_no_detection(bcg, mutated, record)
    assert record.operator == NegativeOperator.RENAME_STEP_COMMENT


def test_add_redundant_dependency_no_detection():
    """ADD_REDUNDANT_DEPENDENCY is idempotent — all contracts preserved."""
    engine = NegativeMutationEngine()
    bcg = _make_bcg_with_three_steps()
    mutated, record = engine.apply(bcg, NegativeOperator.ADD_REDUNDANT_DEPENDENCY, seed=42)
    _assert_no_detection(bcg, mutated, record)
    assert record.operator == NegativeOperator.ADD_REDUNDANT_DEPENDENCY


def test_reorder_independent_steps_no_detection():
    """REORDER_INDEPENDENT_STEPS swaps steps with no ordering contract — no detection."""
    engine = NegativeMutationEngine()
    bcg = _make_bcg_with_three_steps()
    # STEP010 and STEP030 have no MUST_PRECEDE between them (A->B->C, not A->C)
    mutated, record = engine.apply(bcg, NegativeOperator.REORDER_INDEPENDENT_STEPS, seed=42)
    _assert_no_detection(bcg, mutated, record)
    assert record.operator == NegativeOperator.REORDER_INDEPENDENT_STEPS


def test_change_accounting_parameters_no_detection():
    """CHANGE_ACCOUNTING_PARAMETERS alters billing metadata only — no detection."""
    engine = NegativeMutationEngine()
    bcg = _make_bcg_with_three_steps()
    mutated, record = engine.apply(bcg, NegativeOperator.CHANGE_ACCOUNTING_PARAMETERS, seed=42)
    _assert_no_detection(bcg, mutated, record)
    assert record.operator == NegativeOperator.CHANGE_ACCOUNTING_PARAMETERS


def test_rename_proc_label_no_detection():
    """RENAME_PROC_LABEL renames unreferenced STEP030 — no detection."""
    engine = NegativeMutationEngine()
    bcg = _make_bcg_with_three_steps()
    mutated, record = engine.apply(bcg, NegativeOperator.RENAME_PROC_LABEL, seed=42)
    _assert_no_detection(bcg, mutated, record)
    assert record.operator == NegativeOperator.RENAME_PROC_LABEL


def test_all_operators_expected_detection_false():
    """All 5 operators must produce NegativeMutationRecord with expected_detection=False."""
    engine = NegativeMutationEngine()
    bcg = _make_bcg_with_three_steps()
    results: list[NegativeMutationRecord] = []
    for op in NegativeOperator:
        try:
            _, record = engine.apply(bcg, op, seed=1)
            results.append(record)
        except ValueError:
            # Operator not applicable to this minimal BCG — that is acceptable
            pass
    assert len(results) > 0, "At least one operator must be applicable to minimal BCG"
    for record in results:
        assert record.expected_detection is False, (
            f"{record.operator}: expected_detection must be False, got {record.expected_detection}"
        )


def test_rename_step_comment_not_applicable_without_attribute():
    """RENAME_STEP_COMMENT raises ValueError when no STEP has a comment attribute."""
    ir = IRGraph()
    step = IREntity(entity_type=EntityType.STEP, name="S1", artifact_path="x.jcl", attributes={})
    ir.add_entity(step)
    bcg = BCG(ir=ir, bcg_id="no-comment")
    engine = NegativeMutationEngine()
    with pytest.raises(ValueError, match="comment"):
        engine.apply(bcg, NegativeOperator.RENAME_STEP_COMMENT, seed=1)
