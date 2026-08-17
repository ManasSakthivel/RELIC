"""
Unit tests for the Behavioral Contract model.

Tests cover:
- Contract creation with all required fields
- ValidationState transitions and semantics
- ConfidenceVector.aggregate() with known weights
- aggregate() result is clamped to [0, 1]
- ProvenanceRecord evidence tracking
- NOT_OBSERVED ≠ CONTRADICTED (explicit assertion — scientific integrity)
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from legacy_contract.contracts.model import (
    ConfidenceVector,
    Contract,
    ContractPredicate,
    ContractType,
    EvidenceItem,
    ExtractionMethod,
    ProvenanceRecord,
    ValidationState,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_contract(
    contract_type: ContractType = ContractType.TEMPORAL,
    predicate: ContractPredicate = ContractPredicate.PRECEDES,
    validation_state: ValidationState = ValidationState.STATIC_CANDIDATE,
) -> Contract:
    return Contract(
        contract_type=contract_type,
        subject_id="entity_a",
        predicate=predicate,
        object_id="entity_b",
        natural_language="A must precede B.",
        scope="batch_job",
        provenance=ProvenanceRecord(
            source_artifact="test.jcl",
            source_location="test.jcl:5:0",
        ),
        validation_state=validation_state,
    )


def make_provenance(with_static: bool = False, with_dynamic: bool = False) -> ProvenanceRecord:
    prov = ProvenanceRecord(
        source_artifact="test.jcl",
        source_location="test.jcl:10:0",
        extraction_method=ExtractionMethod.DETERMINISTIC,
    )
    if with_static:
        prov.static_evidence.append(
            EvidenceItem(
                evidence_type="static_structural",
                source_artifact="test.jcl",
                content="JCL step ordering",
            )
        )
    if with_dynamic:
        prov.dynamic_evidence.append(
            EvidenceItem(
                evidence_type="dynamic_observation",
                source_artifact="execution_trace",
                extraction_method=ExtractionMethod.EXECUTION,
                content="Observed A before B in run-001",
            )
        )
    return prov


# ---------------------------------------------------------------------------
# 1. Contract creation with all required fields
# ---------------------------------------------------------------------------

def test_contract_creation_minimal():
    """A contract with all required fields must be constructable."""
    c = make_contract()
    assert c.contract_type == ContractType.TEMPORAL
    assert c.subject_id == "entity_a"
    assert c.predicate == ContractPredicate.PRECEDES
    assert c.object_id == "entity_b"
    assert c.natural_language == "A must precede B."
    assert c.validation_state == ValidationState.STATIC_CANDIDATE


def test_contract_has_auto_generated_id():
    """contract_id must be auto-generated and non-empty."""
    c = make_contract()
    assert c.contract_id
    assert isinstance(c.contract_id, str)
    # Validate it's a UUID-like string
    parsed = uuid.UUID(c.contract_id)
    assert str(parsed) == c.contract_id


def test_contract_ids_are_unique():
    """Each contract must receive a distinct contract_id."""
    c1 = make_contract()
    c2 = make_contract()
    assert c1.contract_id != c2.contract_id


def test_contract_created_at_is_datetime():
    """created_at must be a datetime object."""
    c = make_contract()
    assert isinstance(c.created_at, datetime)


def test_contract_all_types_constructable():
    """All ContractType values must be usable as contract_type."""
    for ct in ContractType:
        # Use a compatible predicate for each type
        c = Contract(
            contract_type=ct,
            subject_id="x",
            predicate=ContractPredicate.PRECEDES,
            object_id="y",
            natural_language=f"Test {ct.value}",
        )
        assert c.contract_type == ct


def test_contract_all_predicates_constructable():
    """All ContractPredicate values must be usable."""
    for pred in ContractPredicate:
        c = Contract(
            contract_type=ContractType.TEMPORAL,
            subject_id="x",
            predicate=pred,
            object_id="y",
            natural_language=f"Test {pred.value}",
        )
        assert c.predicate == pred


# ---------------------------------------------------------------------------
# 2. ValidationState transitions and semantics
# ---------------------------------------------------------------------------

def test_validation_state_initial_is_static_candidate():
    """Default validation state for a new contract is STATIC_CANDIDATE."""
    c = make_contract()
    assert c.validation_state == ValidationState.STATIC_CANDIDATE


def test_validation_state_transition_to_supported():
    """Manually setting state to STATIC_DYNAMIC_SUPPORTED must persist."""
    c = make_contract()
    c.validation_state = ValidationState.STATIC_DYNAMIC_SUPPORTED
    assert c.validation_state == ValidationState.STATIC_DYNAMIC_SUPPORTED
    assert c.is_validated() is True


def test_validation_state_transition_to_conflict():
    """State can be set to STATIC_DYNAMIC_CONFLICT."""
    c = make_contract()
    c.validation_state = ValidationState.STATIC_DYNAMIC_CONFLICT
    assert c.has_conflict() is True
    assert c.is_validated() is False


def test_validation_state_not_observed_not_contradicted():
    """
    SCIENTIFIC INTEGRITY: NOT_OBSERVED must NOT be treated as CONTRADICTED.
    The absence of dynamic evidence is not evidence of absence.
    """
    c_not_observed = make_contract(validation_state=ValidationState.NOT_OBSERVED)
    c_contradicted = make_contract(validation_state=ValidationState.STATIC_DYNAMIC_CONFLICT)

    # NOT_OBSERVED ≠ CONTRADICTED — this is a fundamental scientific principle
    assert c_not_observed.validation_state != c_contradicted.validation_state
    assert c_not_observed.validation_state == ValidationState.NOT_OBSERVED
    assert c_contradicted.validation_state == ValidationState.STATIC_DYNAMIC_CONFLICT
    assert c_not_observed.has_conflict() is False


def test_is_validated_states():
    """
    is_validated() must return True only for:
    STATIC_DYNAMIC_SUPPORTED, HUMAN_VALIDATED, GROUND_TRUTH.
    """
    validated_states = {
        ValidationState.STATIC_DYNAMIC_SUPPORTED,
        ValidationState.HUMAN_VALIDATED,
        ValidationState.GROUND_TRUTH,
    }
    not_validated_states = {
        ValidationState.STATIC_CANDIDATE,
        ValidationState.DYNAMICALLY_OBSERVED,
        ValidationState.STATIC_DYNAMIC_CONFLICT,
        ValidationState.UNRESOLVED,
        ValidationState.NOT_OBSERVED,
    }

    for state in validated_states:
        c = make_contract(validation_state=state)
        assert c.is_validated() is True, f"State {state} should be validated"

    for state in not_validated_states:
        c = make_contract(validation_state=state)
        assert c.is_validated() is False, f"State {state} should NOT be validated"


def test_all_validation_states_exist():
    """All eight ValidationState enum values must exist."""
    expected = {
        "STATIC_CANDIDATE",
        "DYNAMICALLY_OBSERVED",
        "STATIC_DYNAMIC_SUPPORTED",
        "STATIC_DYNAMIC_CONFLICT",
        "HUMAN_VALIDATED",
        "GROUND_TRUTH",
        "UNRESOLVED",
        "NOT_OBSERVED",
    }
    actual = {s.value for s in ValidationState}
    assert expected == actual


# ---------------------------------------------------------------------------
# 3. ConfidenceVector.aggregate() with known weights
# ---------------------------------------------------------------------------

def test_confidence_aggregate_all_zero():
    """All-zero ConfidenceVector should aggregate to 0.0."""
    cv = ConfidenceVector()  # all defaults are 0.0
    assert cv.aggregate() == 0.0


def test_confidence_aggregate_all_one_no_penalty():
    """
    With all evidence dimensions at 1.0 and no ambiguity penalty,
    aggregate() must equal the sum of weights (normalized to [0,1]).
    """
    cv = ConfidenceVector(
        static_support=1.0,
        dynamic_support=1.0,
        cross_artifact_support=1.0,
        provenance_quality=1.0,
        human_validation=1.0,
        execution_frequency=1.0,
        ambiguity_penalty=0.0,
    )
    result = cv.aggregate()
    # Default weights sum to: 0.25+0.30+0.15+0.10+0.20+0.10 = 1.10 > 1 → clamped to 1.0
    assert result == pytest.approx(1.0)


def test_confidence_aggregate_known_values():
    """
    Test with a known combination of values and default weights.
    Expected: 0.25*0.8 + 0.30*0.6 + 0.15*0.0 + 0.10*1.0 + 0.20*0.0 + 0.10*0.5 = 0.53
    Then penalized: 0.53 * (1 - 0.0) = 0.53
    """
    cv = ConfidenceVector(
        static_support=0.8,
        dynamic_support=0.6,
        cross_artifact_support=0.0,
        provenance_quality=1.0,
        human_validation=0.0,
        execution_frequency=0.5,
        ambiguity_penalty=0.0,
    )
    expected = 0.25 * 0.8 + 0.30 * 0.6 + 0.15 * 0.0 + 0.10 * 1.0 + 0.20 * 0.0 + 0.10 * 0.5
    assert cv.aggregate() == pytest.approx(expected, abs=1e-6)


def test_confidence_aggregate_with_ambiguity_penalty():
    """
    Ambiguity penalty must multiplicatively reduce the raw score.
    """
    cv = ConfidenceVector(
        static_support=1.0,
        dynamic_support=0.0,
        cross_artifact_support=0.0,
        provenance_quality=1.0,
        human_validation=0.0,
        execution_frequency=0.0,
        ambiguity_penalty=0.5,
    )
    raw = 0.25 * 1.0 + 0.10 * 1.0  # static + provenance
    expected = raw * (1.0 - 0.5)
    assert cv.aggregate() == pytest.approx(expected, abs=1e-6)


def test_confidence_aggregate_custom_weights():
    """update_weights must change how aggregate() computes the score."""
    cv = ConfidenceVector(
        static_support=1.0,
        dynamic_support=0.0,
        ambiguity_penalty=0.0,
    )
    custom_weights = {
        "static_support": 0.5,
        "dynamic_support": 0.5,
        "cross_artifact_support": 0.0,
        "provenance_quality": 0.0,
        "human_validation": 0.0,
        "execution_frequency": 0.0,
    }
    cv.update_weights(custom_weights)
    # Only static_support contributes: 0.5 * 1.0 = 0.5
    assert cv.aggregate() == pytest.approx(0.5, abs=1e-6)


# ---------------------------------------------------------------------------
# 4. aggregate() result is always in [0, 1]
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("static_s,dynamic_s,penalty,description", [
    (0.0, 0.0, 0.0, "all_zero"),
    (1.0, 1.0, 0.0, "all_one"),
    (1.0, 1.0, 1.0, "max_penalty"),
    (0.5, 0.5, 0.5, "mid_with_penalty"),
    (0.0, 0.0, 1.0, "zero_with_max_penalty"),
    (2.0, 2.0, 0.0, "overflow_values"),  # Out-of-range inputs must still clamp
    (-1.0, -1.0, 0.0, "negative_values"),
])
def test_confidence_aggregate_clamped_to_unit_interval(
    static_s, dynamic_s, penalty, description
):
    """aggregate() must always return a value in [0, 1]."""
    cv = ConfidenceVector(
        static_support=static_s,
        dynamic_support=dynamic_s,
        ambiguity_penalty=penalty,
    )
    result = cv.aggregate()
    assert 0.0 <= result <= 1.0, (
        f"[{description}] aggregate()={result} is outside [0, 1]"
    )


# ---------------------------------------------------------------------------
# 5. ProvenanceRecord evidence tracking
# ---------------------------------------------------------------------------

def test_provenance_no_evidence_initial():
    """Fresh ProvenanceRecord has empty evidence lists."""
    prov = make_provenance()
    assert not prov.has_static_evidence()
    assert not prov.has_dynamic_evidence()


def test_provenance_static_evidence_tracked():
    """Adding static evidence must be reflected by has_static_evidence()."""
    prov = make_provenance(with_static=True)
    assert prov.has_static_evidence()
    assert not prov.has_dynamic_evidence()
    assert len(prov.static_evidence) == 1


def test_provenance_dynamic_evidence_tracked():
    """Adding dynamic evidence must be reflected by has_dynamic_evidence()."""
    prov = make_provenance(with_dynamic=True)
    assert not prov.has_static_evidence()
    assert prov.has_dynamic_evidence()
    assert len(prov.dynamic_evidence) == 1


def test_provenance_both_evidence_types():
    """ProvenanceRecord can hold both static and dynamic evidence."""
    prov = make_provenance(with_static=True, with_dynamic=True)
    assert prov.has_static_evidence()
    assert prov.has_dynamic_evidence()


def test_provenance_summary_format():
    """evidence_summary() must include static and dynamic counts."""
    prov = make_provenance(with_static=True, with_dynamic=True)
    summary = prov.evidence_summary()
    assert "static=1" in summary
    assert "dynamic=1" in summary
    assert "method=" in summary


def test_provenance_evidence_item_has_id():
    """Each EvidenceItem must have a non-empty evidence_id."""
    item = EvidenceItem(
        evidence_type="static_structural",
        source_artifact="test.jcl",
        content="step ordering",
    )
    assert item.evidence_id
    parsed = uuid.UUID(item.evidence_id)
    assert str(parsed) == item.evidence_id


def test_provenance_extraction_method_default():
    """Default extraction_method for ProvenanceRecord is DETERMINISTIC."""
    prov = ProvenanceRecord(
        source_artifact="test.jcl",
        source_location="test.jcl:1:0",
    )
    assert prov.extraction_method == ExtractionMethod.DETERMINISTIC


def test_provenance_llm_fields():
    """LLM extraction method should allow LLM-specific fields on EvidenceItem."""
    item = EvidenceItem(
        evidence_type="llm_inference",
        source_artifact="test.jcl",
        extraction_method=ExtractionMethod.LLM,
        llm_model="gpt-4",
        llm_prompt_version="v1.0",
        llm_temperature=0.0,
        llm_input="What contracts exist?",
        llm_output="JOB-A precedes JOB-B.",
    )
    assert item.llm_model == "gpt-4"
    assert item.llm_temperature == 0.0
    assert item.extraction_method == ExtractionMethod.LLM


# ---------------------------------------------------------------------------
# 6. NOT_OBSERVED ≠ CONTRADICTED — explicit scientific integrity assertions
# ---------------------------------------------------------------------------

def test_not_observed_is_distinct_from_contradicted():
    """
    SCIENTIFIC PRINCIPLE: NOT_OBSERVED ≠ CONTRADICTED.

    NOT_OBSERVED means: no dynamic evidence was available for this contract.
    CONTRADICTED means: dynamic evidence directly contradicts the static inference.
    These MUST NEVER be conflated.
    """
    assert ValidationState.NOT_OBSERVED != ValidationState.STATIC_DYNAMIC_CONFLICT
    assert ValidationState.NOT_OBSERVED.value == "NOT_OBSERVED"
    assert ValidationState.STATIC_DYNAMIC_CONFLICT.value == "STATIC_DYNAMIC_CONFLICT"


def test_not_observed_contract_has_no_conflict():
    """A NOT_OBSERVED contract must not be reported as having a conflict."""
    c = make_contract(validation_state=ValidationState.NOT_OBSERVED)
    assert c.has_conflict() is False


def test_not_observed_contract_is_not_validated():
    """A NOT_OBSERVED contract must not be reported as validated."""
    c = make_contract(validation_state=ValidationState.NOT_OBSERVED)
    assert c.is_validated() is False


def test_not_observed_is_not_static_candidate():
    """NOT_OBSERVED is semantically distinct from STATIC_CANDIDATE."""
    assert ValidationState.NOT_OBSERVED != ValidationState.STATIC_CANDIDATE


def test_contract_summary_includes_state():
    """summary() must include the contract type, predicate, and validation state."""
    c = make_contract()
    s = c.summary()
    assert "TEMPORAL" in s
    assert "PRECEDES" in s
    assert "STATIC_CANDIDATE" in s


def test_confidence_score_delegates_to_aggregate():
    """confidence_score() must return the same value as confidence.aggregate()."""
    c = make_contract()
    c.confidence = ConfidenceVector(static_support=0.7, ambiguity_penalty=0.0)
    assert c.confidence_score() == pytest.approx(c.confidence.aggregate())


# ---------------------------------------------------------------------------
# 7. Contract equality and hashing
# ---------------------------------------------------------------------------

def test_contract_equality_by_id():
    """Two contracts with the same contract_id must be equal."""
    c1 = make_contract()
    c2 = make_contract()
    c2.contract_id = c1.contract_id
    assert c1 == c2


def test_contract_inequality_by_different_id():
    """Two contracts with different IDs must not be equal."""
    c1 = make_contract()
    c2 = make_contract()
    assert c1 != c2


def test_contract_hashable():
    """Contracts must be usable in sets and as dict keys."""
    c1 = make_contract()
    c2 = make_contract()
    contract_set = {c1, c2}
    assert len(contract_set) == 2


def test_contract_set_deduplication_by_id():
    """Contracts with the same ID in a set must deduplicate."""
    c1 = make_contract()
    c2 = make_contract()
    c2.contract_id = c1.contract_id
    contract_set = {c1, c2}
    assert len(contract_set) == 1
