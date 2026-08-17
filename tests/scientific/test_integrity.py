"""
tests/scientific/test_integrity.py
===================================
Scientific integrity tests for the legacy-contract BCG pipeline.

These tests enforce *scientific guarantees*, not implementation details.
Each test corresponds to a claim made in the paper or in the methodology docs.
Failing any of these tests means the software can no longer be used to support
the paper's experimental results without further justification.

Coverage:
  SI-01  SYNTHETIC_STATIC evidence cannot upgrade a contract to STATIC_DYNAMIC_SUPPORTED
  SI-02  Provenance survives BCGDiff (broken + preserved contracts keep their provenance)
  SI-03  ConfidenceVector weight sum is pinned to the documented ~1.10 invariant
  SI-04  ConfidenceVector YAML weights match in-code defaults
  SI-05  ambiguity_penalty=1.0 collapses the confidence score to 0.0 regardless of evidence
  SI-06  NOT_OBSERVED ≠ CONTRADICTED — parametrized over all ContractType values
  SI-07  HUMAN_VALIDATED state is not silently overwritten by a CONTRADICTED outcome
         (HUMAN_VALIDATED + contradiction → conflict flag, not silent demotion)
  SI-08  Duplicate extraction: semantically identical contracts are not stored twice
  SI-09  All static-extracted contracts carry provenance.extraction_method == DETERMINISTIC
  SI-10  IREntity IDs are deterministic and stable: same (artifact, type, name) → same ID
  SI-11  (bonus) return_code=None means "not captured", NOT zero — NOT_OBSERVED result
  SI-12  (bonus) GROUND_TRUTH state is never downgraded by reconciliation
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta

import pytest

# ── imports from the package under test ──────────────────────────────────────
from legacy_contract.contracts.model import (
    Contract,
    ContractPredicate,
    ContractType,
    ConfidenceVector,
    EvidenceItem,
    ExtractionMethod,
    ProvenanceRecord,
    ValidationState,
)
from legacy_contract.dynamic_analysis.model import (
    EventSourceType,
    ExecutionEvent,
    ExecutionTrace,
    OperationType,
)
from legacy_contract.ir.model import (
    EntityType,
    IREntity,
    IRGraph,
    RelationType,
    IRRelation,
)
from legacy_contract.bcg.model import BCG, BCGDiff
from legacy_contract.reconciliation.engine import ReconciliationEngine, ReconciliationOutcome
from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.static_analysis.extractor import StaticContractExtractor


# ═══════════════════════════════════════════════════════════════════════════
# Shared fixtures / helpers
# ═══════════════════════════════════════════════════════════════════════════

def _make_provenance(method: ExtractionMethod = ExtractionMethod.DETERMINISTIC) -> ProvenanceRecord:
    return ProvenanceRecord(
        source_artifact="integrity_test.jcl",
        source_location="1:1",
        extraction_method=method,
        static_evidence=[
            EvidenceItem(
                evidence_type="static_structural",
                content="test evidence",
                extraction_method=method,
            )
        ],
    )


def _make_contract(
    *,
    subject_id: str = "entity_a",
    object_id: str = "entity_b",
    contract_type: ContractType = ContractType.TEMPORAL,
    predicate: ContractPredicate = ContractPredicate.PRECEDES,
    validation_state: ValidationState = ValidationState.STATIC_CANDIDATE,
    extraction_method: ExtractionMethod = ExtractionMethod.DETERMINISTIC,
) -> Contract:
    return Contract(
        contract_type=contract_type,
        subject_id=subject_id,
        predicate=predicate,
        object_id=object_id,
        natural_language=f"{subject_id} → {object_id}",
        provenance=_make_provenance(extraction_method),
        confidence=ConfidenceVector(static_support=1.0, provenance_quality=1.0),
        validation_state=validation_state,
    )


def _make_event(
    artifact_id: str,
    *,
    timestamp: datetime,
    operation: OperationType = OperationType.STEP_START,
    source_type: EventSourceType = EventSourceType.EXECUTION,
    return_code: int | None = None,
) -> ExecutionEvent:
    return ExecutionEvent(
        execution_id="run_sci_001",
        artifact_id=artifact_id,
        operation=operation,
        timestamp=timestamp,
        source_type=source_type,
        return_code=return_code,
    )


def _trace_with_ordering(
    a_id: str,
    b_id: str,
    a_before_b: bool,
    source_type: EventSourceType = EventSourceType.EXECUTION,
) -> ExecutionTrace:
    now = datetime(2024, 1, 1, 12, 0, 0)
    if a_before_b:
        t_a, t_b = now, now + timedelta(seconds=5)
    else:
        t_a, t_b = now + timedelta(seconds=5), now

    trace = ExecutionTrace(execution_id="run_sci_001", source_type=source_type)
    trace.add_event(_make_event(a_id, timestamp=t_a, source_type=source_type))
    trace.add_event(_make_event(b_id, timestamp=t_b, source_type=source_type))
    return trace


# ═══════════════════════════════════════════════════════════════════════════
# SI-01  SYNTHETIC_STATIC cannot upgrade state to STATIC_DYNAMIC_SUPPORTED
# ═══════════════════════════════════════════════════════════════════════════

class TestSyntheticStaticEnforcement:
    """
    SI-01 — Scientific principle: SYNTHETIC_STATIC evidence is NOT execution.
    Upgrading a contract to STATIC_DYNAMIC_SUPPORTED on the basis of synthetic
    evidence would conflate static derivation with dynamic observation, which is
    the central methodological distinction in the paper.

    NOTE: The current ReconciliationEngine does NOT enforce this guard.
    This test is written as a *contract* test — it documents what MUST be true
    and will FAIL until the guard is added to ReconciliationEngine._update_contract.
    """

    def _bcg_with_contract(self, subject: str, obj: str) -> tuple[BCG, Contract]:
        bcg = BCG(ir=IRGraph())
        contract = _make_contract(subject_id=subject, object_id=obj)
        bcg.add_contract(contract)
        return bcg, contract

    def test_synthetic_static_cannot_upgrade_to_supported(self):
        """
        A trace composed entirely of SYNTHETIC_STATIC events must not cause
        a contract to transition to STATIC_DYNAMIC_SUPPORTED.
        """
        bcg, contract = self._bcg_with_contract("s1", "s2")

        # Build a trace with SYNTHETIC_STATIC source type (correct ordering)
        trace = _trace_with_ordering(
            "s1", "s2", a_before_b=True,
            source_type=EventSourceType.SYNTHETIC_STATIC,
        )
        engine = ReconciliationEngine()
        engine.reconcile(bcg, [trace])

        assert contract.validation_state != ValidationState.STATIC_DYNAMIC_SUPPORTED, (
            "SCIENTIFIC INTEGRITY VIOLATION: A SYNTHETIC_STATIC trace upgraded the contract "
            "to STATIC_DYNAMIC_SUPPORTED. Only real execution (EXECUTION or "
            "EXECUTION_SIMULATED) may trigger this transition. "
            "Fix: add source_type guard in ReconciliationEngine._update_contract."
        )

    def test_real_execution_can_upgrade_to_supported(self):
        """
        Positive control: a real EXECUTION trace with correct ordering SHOULD
        produce STATIC_DYNAMIC_SUPPORTED.
        """
        bcg, contract = self._bcg_with_contract("r1", "r2")
        trace = _trace_with_ordering(
            "r1", "r2", a_before_b=True,
            source_type=EventSourceType.EXECUTION,
        )
        engine = ReconciliationEngine()
        engine.reconcile(bcg, [trace])

        assert contract.validation_state == ValidationState.STATIC_DYNAMIC_SUPPORTED, (
            "Positive control failed: real EXECUTION trace did not produce "
            "STATIC_DYNAMIC_SUPPORTED."
        )

    def test_is_real_execution_flag_is_false_for_synthetic(self):
        """
        ExecutionEvent.is_real_execution() must return False for SYNTHETIC_STATIC.
        This is the boolean predicate the engine guard should use.
        """
        event = _make_event(
            "any",
            timestamp=datetime.utcnow(),
            source_type=EventSourceType.SYNTHETIC_STATIC,
        )
        assert event.is_real_execution() is False, (
            "is_real_execution() returned True for SYNTHETIC_STATIC."
        )


# ═══════════════════════════════════════════════════════════════════════════
# SI-02  Provenance survives BCGDiff
# ═══════════════════════════════════════════════════════════════════════════

class TestProvenanceSurvivesBCGDiff:
    """
    SI-02 — Every contract in BCGDiff.broken and BCGDiff.preserved must have
    non-None provenance. Provenance is the audit trail; losing it during diff
    makes regression analysis non-reproducible.
    """

    def _make_bcg(self, *contract_specs: tuple[str, str]) -> BCG:
        """Create a BCG with one TEMPORAL contract per (subject, object) spec."""
        bcg = BCG(ir=IRGraph())
        for subj, obj in contract_specs:
            bcg.add_contract(_make_contract(subject_id=subj, object_id=obj))
        return bcg

    def test_provenance_preserved_in_broken_contracts(self):
        """Contracts that appear only in the original BCG (broken) keep their provenance."""
        orig = self._make_bcg(("a", "b"), ("c", "d"))
        mod = self._make_bcg(("a", "b"))  # ("c","d") is broken

        diff = orig.diff(mod)
        assert len(diff.broken) >= 1, "Expected at least one broken contract."
        for c in diff.broken:
            assert c.provenance is not None, (
                f"Broken contract {c.contract_id} has provenance=None after BCGDiff."
            )
            assert c.provenance.source_artifact != "", (
                f"Broken contract {c.contract_id} has empty source_artifact in provenance."
            )

    def test_provenance_preserved_in_preserved_contracts(self):
        """Contracts present in both BCGs (preserved) keep their provenance."""
        orig = self._make_bcg(("a", "b"), ("c", "d"))
        mod = self._make_bcg(("a", "b"))

        diff = orig.diff(mod)
        assert len(diff.preserved) >= 1, "Expected at least one preserved contract."
        for c in diff.preserved:
            assert c.provenance is not None, (
                f"Preserved contract {c.contract_id} has provenance=None after BCGDiff."
            )

    def test_provenance_static_evidence_not_empty_after_diff(self):
        """
        Static evidence items must survive the diff (they are not deep-copied,
        but must still be reachable through the contract reference).
        """
        orig = self._make_bcg(("x", "y"))
        mod = BCG(ir=IRGraph())  # everything is broken

        diff = orig.diff(mod)
        for c in diff.broken:
            assert c.provenance is not None
            assert len(c.provenance.static_evidence) >= 1, (
                f"Broken contract {c.contract_id}: static evidence lost after diff."
            )


# ═══════════════════════════════════════════════════════════════════════════
# SI-03  ConfidenceVector weight sum invariant
# ═══════════════════════════════════════════════════════════════════════════

class TestConfidenceWeightInvariant:
    """
    SI-03 — The documented design decision is that weights sum to ~1.10, NOT 1.0.
    This is intentional (see config/confidence_weights.yaml, line 28-30).
    Pinning this invariant as a test prevents accidental renormalization.
    """

    EXPECTED_WEIGHT_SUM = 1.10
    TOLERANCE = 0.005  # allow minor floating-point rounding

    def test_weight_sum_is_not_one(self):
        """
        Weights must NOT sum to 1.0 — this would silently change the score semantics.
        The architecture document explicitly states the overcount is intentional.
        """
        cv = ConfidenceVector()
        total = sum(cv._weights.values())
        assert abs(total - 1.0) > 0.05, (
            f"Weights sum to {total:.4f}, which is too close to 1.0. "
            "The weight sum should be ~1.10 by design (see confidence_weights.yaml)."
        )

    def test_weight_sum_matches_documented_value(self):
        """Weight sum must be within tolerance of the documented 1.10 value."""
        cv = ConfidenceVector()
        total = sum(cv._weights.values())
        assert abs(total - self.EXPECTED_WEIGHT_SUM) <= self.TOLERANCE, (
            f"Weight sum is {total:.4f}; expected ~{self.EXPECTED_WEIGHT_SUM}. "
            "If weights were intentionally changed, update this test AND "
            "docs/research_decisions.md D-004 and rerun ALL experiments."
        )

    def test_all_weight_keys_are_present(self):
        """All six evidence dimensions must have a weight."""
        expected_keys = {
            "static_support", "dynamic_support", "cross_artifact_support",
            "provenance_quality", "human_validation", "execution_frequency",
        }
        cv = ConfidenceVector()
        assert set(cv._weights.keys()) == expected_keys, (
            f"Weight keys differ: got {set(cv._weights.keys())}, "
            f"expected {expected_keys}."
        )


# ═══════════════════════════════════════════════════════════════════════════
# SI-04  YAML weights match in-code defaults
# ═══════════════════════════════════════════════════════════════════════════

class TestYAMLWeightsMatchCode:
    """
    SI-04 — The governance document (confidence_weights.yaml) and the in-code
    default weights must agree. Drift between them would mean experiments run
    with different weights than the ones documented in the paper.
    """

    @pytest.fixture
    def yaml_weights(self) -> dict[str, float]:
        """Load weights from the authoritative config file."""
        import pathlib, yaml  # type: ignore[import-untyped]
        config_path = (
            pathlib.Path(__file__)
            .parent.parent.parent  # tests/scientific/ → legacy-contract/
            / "config" / "confidence_weights.yaml"
        )
        if not config_path.exists():
            pytest.skip(f"confidence_weights.yaml not found at {config_path}")
        with config_path.open() as f:
            data = yaml.safe_load(f)
        return {k: float(v) for k, v in data["weights"].items()}

    def test_yaml_weights_match_code_defaults(self, yaml_weights: dict[str, float]):
        """
        Every weight in confidence_weights.yaml must match the corresponding
        default in ConfidenceVector._weights.
        """
        cv = ConfidenceVector()
        for key, yaml_val in yaml_weights.items():
            assert key in cv._weights, (
                f"Weight key '{key}' is in YAML but missing from ConfidenceVector._weights."
            )
            code_val = cv._weights[key]
            assert abs(code_val - yaml_val) < 1e-6, (
                f"Weight mismatch for '{key}': YAML={yaml_val}, code={code_val}. "
                "Update one to match the other and document the change in "
                "docs/research_decisions.md D-004."
            )


# ═══════════════════════════════════════════════════════════════════════════
# SI-05  ambiguity_penalty=1.0 collapses confidence to 0.0
# ═══════════════════════════════════════════════════════════════════════════

class TestAmbiguityPenalty:
    """
    SI-05 — Maximum ambiguity must render a contract's confidence score zero
    regardless of evidence strength. This enforces the semantics that the
    penalty is multiplicative: raw * (1 - penalty).
    """

    def test_full_ambiguity_collapses_score(self):
        """
        A contract with all evidence dimensions at 1.0 but ambiguity_penalty=1.0
        must yield aggregate() == 0.0.
        """
        cv = ConfidenceVector(
            static_support=1.0,
            dynamic_support=1.0,
            cross_artifact_support=1.0,
            provenance_quality=1.0,
            human_validation=1.0,
            execution_frequency=1.0,
            ambiguity_penalty=1.0,
        )
        assert cv.aggregate() == 0.0, (
            f"Expected 0.0 with ambiguity_penalty=1.0, got {cv.aggregate()}."
        )

    def test_zero_ambiguity_does_not_reduce_score(self):
        """
        ambiguity_penalty=0.0 must leave the score unmodified.
        """
        cv_base = ConfidenceVector(
            static_support=0.8,
            dynamic_support=0.6,
            ambiguity_penalty=0.0,
        )
        cv_explicit = ConfidenceVector(
            static_support=0.8,
            dynamic_support=0.6,
        )  # default ambiguity_penalty=0.0
        assert cv_base.aggregate() == cv_explicit.aggregate()

    def test_aggregate_clamped_to_unit_interval(self):
        """aggregate() must always return a value in [0.0, 1.0]."""
        cv = ConfidenceVector(
            static_support=1.0,
            dynamic_support=1.0,
            cross_artifact_support=1.0,
            provenance_quality=1.0,
            human_validation=1.0,
            execution_frequency=1.0,
            ambiguity_penalty=0.0,
        )
        score = cv.aggregate()
        assert 0.0 <= score <= 1.0, f"Score {score} is outside [0, 1]."


# ═══════════════════════════════════════════════════════════════════════════
# SI-06  NOT_OBSERVED ≠ CONTRADICTED — parametrized over all ContractType values
# ═══════════════════════════════════════════════════════════════════════════

class TestNotObservedVsContradicted:
    """
    SI-06 — The paper's core scientific claim:
    "Absence of dynamic evidence ≠ contradiction of the contract."
    This distinction must hold for every ContractType, not just TEMPORAL.
    """

    @pytest.mark.parametrize("contract_type", list(ContractType))
    def test_not_observed_is_distinct_from_contradicted(self, contract_type: ContractType):
        """
        ValidationState.NOT_OBSERVED must not equal ValidationState.STATIC_DYNAMIC_CONFLICT
        for any ContractType value.
        """
        assert ValidationState.NOT_OBSERVED != ValidationState.STATIC_DYNAMIC_CONFLICT, (
            "NOT_OBSERVED and STATIC_DYNAMIC_CONFLICT are the same enum value — "
            "this is a critical model error."
        )

    @pytest.mark.parametrize("contract_type", list(ContractType))
    def test_contract_not_observed_does_not_have_conflict(self, contract_type: ContractType):
        """
        A contract in NOT_OBSERVED state must not report has_conflict() == True
        for any ContractType.
        """
        contract = _make_contract(
            contract_type=contract_type,
            predicate=ContractPredicate.PRECEDES,
            validation_state=ValidationState.NOT_OBSERVED,
        )
        assert not contract.has_conflict(), (
            f"Contract of type {contract_type.value} in NOT_OBSERVED state "
            "incorrectly reports has_conflict()=True."
        )

    @pytest.mark.parametrize("contract_type", list(ContractType))
    def test_contract_not_observed_is_not_validated(self, contract_type: ContractType):
        """
        A contract in NOT_OBSERVED state must not report is_validated() == True.
        NOT_OBSERVED is not evidence of validity.
        """
        contract = _make_contract(
            contract_type=contract_type,
            predicate=ContractPredicate.PRECEDES,
            validation_state=ValidationState.NOT_OBSERVED,
        )
        assert not contract.is_validated(), (
            f"Contract of type {contract_type.value} in NOT_OBSERVED state "
            "incorrectly reports is_validated()=True."
        )

    def test_reconciliation_with_no_events_yields_not_observed(self):
        """
        Reconciliation of a temporal contract against empty traces must produce
        NOT_OBSERVED, never STATIC_DYNAMIC_CONFLICT.
        """
        bcg = BCG(ir=IRGraph())
        contract = _make_contract(subject_id="nx", object_id="ny")
        bcg.add_contract(contract)

        engine = ReconciliationEngine()
        records = engine.reconcile(bcg, [])

        assert len(records) == 1
        assert records[0].outcome == ReconciliationOutcome.NOT_OBSERVED, (
            f"Expected NOT_OBSERVED, got {records[0].outcome}."
        )
        assert contract.validation_state == ValidationState.NOT_OBSERVED, (
            f"Expected NOT_OBSERVED state, got {contract.validation_state}."
        )
        assert contract.validation_state != ValidationState.STATIC_DYNAMIC_CONFLICT, (
            "SCIENTIFIC INTEGRITY VIOLATION: empty trace set produced CONTRADICTION."
        )


# ═══════════════════════════════════════════════════════════════════════════
# SI-07  HUMAN_VALIDATED is not silently overwritten by CONTRADICTED outcome
# ═══════════════════════════════════════════════════════════════════════════

class TestHumanValidatedProtection:
    """
    SI-07 — HUMAN_VALIDATED is a higher epistemic class than any automated
    observation. A single contradicting trace must not silently demote it.

    Current engine.py behaviour (line 417):
        elif outcome == ReconciliationOutcome.CONTRADICTED:
            contract.validation_state = ValidationState.STATIC_DYNAMIC_CONFLICT

    This unconditionally overwrites HUMAN_VALIDATED, which is incorrect.
    The expected behaviour is one of:
      (a) HUMAN_VALIDATED → UNRESOLVED with a conflict note, or
      (b) HUMAN_VALIDATED is preserved and the conflict is recorded in metadata.

    This test documents the REQUIRED behaviour. It will fail against the current
    implementation, indicating the guard needs to be added.
    """

    def test_human_validated_not_silently_demoted_by_contradiction(self):
        """
        A HUMAN_VALIDATED contract that receives a CONTRADICTED reconciliation
        outcome must NOT end up in STATIC_DYNAMIC_CONFLICT state.
        The human annotation has higher authority than a single execution trace.
        """
        bcg = BCG(ir=IRGraph())
        contract = _make_contract(
            subject_id="hv_a",
            object_id="hv_b",
            validation_state=ValidationState.HUMAN_VALIDATED,
        )
        bcg.add_contract(contract)

        # Trace that contradicts the ordering (b before a)
        trace = _trace_with_ordering(
            "hv_a", "hv_b", a_before_b=False,
            source_type=EventSourceType.EXECUTION,
        )
        engine = ReconciliationEngine()
        engine.reconcile(bcg, [trace])

        assert contract.validation_state != ValidationState.STATIC_DYNAMIC_CONFLICT, (
            "HUMAN_VALIDATED was silently overwritten to STATIC_DYNAMIC_CONFLICT by a "
            "contradicting execution trace. Human annotation must take precedence. "
            "Fix: add 'if current == ValidationState.HUMAN_VALIDATED: return' guard "
            "in the CONTRADICTED branch of ReconciliationEngine._update_contract, "
            "then record the conflict in contract.metadata."
        )

    def test_human_validated_not_downgraded_by_not_observed(self):
        """
        Positive control (already tested in unit tests): empty traces must
        not downgrade HUMAN_VALIDATED.
        """
        bcg = BCG(ir=IRGraph())
        contract = _make_contract(
            validation_state=ValidationState.HUMAN_VALIDATED,
        )
        bcg.add_contract(contract)

        engine = ReconciliationEngine()
        engine.reconcile(bcg, [])

        assert contract.validation_state == ValidationState.HUMAN_VALIDATED, (
            "HUMAN_VALIDATED was downgraded by empty trace set."
        )

    def test_ground_truth_not_overwritten_by_contradiction(self):
        """
        GROUND_TRUTH is the highest epistemic class. It must survive any
        reconciliation outcome. (Extension of SI-07.)
        """
        bcg = BCG(ir=IRGraph())
        contract = _make_contract(
            subject_id="gt_a",
            object_id="gt_b",
            validation_state=ValidationState.GROUND_TRUTH,
        )
        bcg.add_contract(contract)

        trace = _trace_with_ordering(
            "gt_a", "gt_b", a_before_b=False,
            source_type=EventSourceType.EXECUTION,
        )
        engine = ReconciliationEngine()
        engine.reconcile(bcg, [trace])

        assert contract.validation_state == ValidationState.GROUND_TRUTH, (
            "GROUND_TRUTH state was overwritten by a contradicting execution trace. "
            "GROUND_TRUTH is deterministic / oracle-verified and must never be demoted."
        )


# ═══════════════════════════════════════════════════════════════════════════
# SI-08  Duplicate extraction: same structural fact → no duplicate contracts
# ═══════════════════════════════════════════════════════════════════════════

class TestNoDuplicateExtraction:
    """
    SI-08 — Calling StaticContractExtractor.extract() twice on the same IR
    must not produce duplicate semantic contracts. Duplicates inflate the
    denominator in precision/recall calculation and contaminate experiment results.

    NOTE: The current implementation uses random UUIDs for contract_id, meaning
    two extractions of the same fact will produce two different IDs and both
    will be accepted by BCG.add_contract. This test documents the REQUIRED
    behaviour (uniqueness by semantic signature, not UUID).
    """

    TWO_STEP_JCL = """
//DUPTEST  JOB (ACCT),'DUP TEST'
//STEP010  EXEC PGM=PROGA
//OUTF     DD  DSN=DUP.FILE,DISP=(NEW,CATLG),UNIT=SYSDA
//STEP020  EXEC PGM=PROGB
//INF      DD  DSN=DUP.FILE,DISP=OLD
""".strip().splitlines()

    def _extract_contracts(self) -> list[Contract]:
        parser = JCLParser()
        _, ir = parser.parse_lines(self.TWO_STEP_JCL, "dup_test.jcl")
        extractor = StaticContractExtractor()
        return extractor.extract(ir).all_contracts

    def test_single_extraction_has_no_semantic_duplicates(self):
        """
        A single call to extract() on a clean IR must not produce two contracts
        with the same (contract_type, subject_id, predicate, object_id) signature.
        """
        contracts = self._extract_contracts()
        signatures = [
            (c.contract_type, c.subject_id, c.predicate.value, c.object_id)
            for c in contracts
        ]
        unique_signatures = set(signatures)
        assert len(unique_signatures) == len(signatures), (
            f"Duplicate semantic contracts found in a single extraction. "
            f"Total: {len(signatures)}, unique: {len(unique_signatures)}. "
            "Each structural fact must appear in at most one contract."
        )

    def test_double_extraction_produces_same_count(self):
        """
        Calling extract() twice on the same IR must produce the same number of
        contracts with the same semantic signatures (idempotency).
        """
        parser = JCLParser()
        _, ir = parser.parse_lines(self.TWO_STEP_JCL, "dup_test.jcl")
        extractor = StaticContractExtractor()

        first_result = extractor.extract(ir).all_contracts
        second_result = extractor.extract(ir).all_contracts

        first_sigs = {
            (c.contract_type, c.subject_id, c.predicate.value, c.object_id)
            for c in first_result
        }
        second_sigs = {
            (c.contract_type, c.subject_id, c.predicate.value, c.object_id)
            for c in second_result
        }
        assert first_sigs == second_sigs, (
            "Two calls to extract() on the same IR produced different semantic contract sets. "
            "Extraction must be idempotent."
        )
        assert len(first_result) == len(second_result), (
            f"First extraction: {len(first_result)} contracts; "
            f"second extraction: {len(second_result)} contracts. "
            "Idempotency violated — duplicate contracts produced on second call."
        )


# ═══════════════════════════════════════════════════════════════════════════
# SI-09  Static-extracted contracts have extraction_method = DETERMINISTIC
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractionMethodInProvenance:
    """
    SI-09 — Every contract produced by StaticContractExtractor must carry
    provenance with extraction_method == DETERMINISTIC. This is a factual
    claim about how the contracts were obtained and is used to compute the
    evidence-strength score (static_support weight applies only to deterministic
    extractions). Mislabelling as LLM or HUMAN would corrupt evaluation results.
    """

    SAMPLE_JCL = """
//PROVTEST JOB (ACCT),'PROV TEST'
//STEP010  EXEC PGM=PROGA
//OUTF     DD  DSN=PROV.FILE,DISP=(NEW,CATLG),UNIT=SYSDA
//STEP020  EXEC PGM=PROGB,COND=(4,GT,STEP010)
//INF      DD  DSN=PROV.FILE,DISP=OLD
""".strip().splitlines()

    def test_all_extracted_contracts_have_deterministic_provenance(self):
        """
        All contracts from static extraction must have
        provenance.extraction_method == ExtractionMethod.DETERMINISTIC.
        """
        parser = JCLParser()
        _, ir = parser.parse_lines(self.SAMPLE_JCL, "prov_test.jcl")
        extractor = StaticContractExtractor()
        contracts = extractor.extract(ir).all_contracts

        assert len(contracts) > 0, "No contracts extracted — test precondition failed."

        for c in contracts:
            assert c.provenance is not None, (
                f"Contract {c.contract_id} ({c.natural_language!r}) "
                "has no provenance record."
            )
            assert c.provenance.extraction_method == ExtractionMethod.DETERMINISTIC, (
                f"Contract {c.contract_id} has extraction_method="
                f"{c.provenance.extraction_method.value!r}; expected DETERMINISTIC. "
                "Static extraction must always be labelled as deterministic."
            )

    def test_all_extracted_contracts_have_non_empty_provenance_artifact(self):
        """
        provenance.source_artifact must not be empty for statically extracted contracts.
        An empty source_artifact means the contract cannot be traced back to its origin.
        """
        parser = JCLParser()
        _, ir = parser.parse_lines(self.SAMPLE_JCL, "prov_test.jcl")
        extractor = StaticContractExtractor()
        contracts = extractor.extract(ir).all_contracts

        for c in contracts:
            assert c.provenance is not None
            assert c.provenance.source_artifact != "", (
                f"Contract {c.contract_id} has empty provenance.source_artifact. "
                "Every contract must be traceable to a source file."
            )

    def test_all_extracted_contracts_have_static_evidence(self):
        """
        provenance.static_evidence must contain at least one EvidenceItem for
        every statically extracted contract.
        """
        parser = JCLParser()
        _, ir = parser.parse_lines(self.SAMPLE_JCL, "prov_test.jcl")
        extractor = StaticContractExtractor()
        contracts = extractor.extract(ir).all_contracts

        for c in contracts:
            assert c.provenance is not None
            assert c.provenance.has_static_evidence(), (
                f"Contract {c.contract_id} ({c.contract_type.value}) has no "
                "static evidence items. At least one EvidenceItem is required."
            )


# ═══════════════════════════════════════════════════════════════════════════
# SI-10  IREntity IDs are deterministic and stable
# ═══════════════════════════════════════════════════════════════════════════

class TestEntityIDDeterminism:
    """
    SI-10 — IREntity IDs must be deterministic: the same (artifact_path,
    entity_type, name) triple always produces the same entity_id across
    instantiations, Python sessions, and platforms.

    This is critical for reconciliation: if entity IDs change between the run
    that builds the BCG and the run that supplies execution traces, all events
    will be unmatched and every contract will be NOT_OBSERVED (false negatives).
    """

    def test_same_inputs_produce_same_entity_id(self):
        """
        Two IREntity instances with identical (artifact_path, entity_type, name)
        must have identical entity_id values.
        """
        e1 = IREntity(
            entity_type=EntityType.STEP,
            name="STEP010",
            artifact_path="stable.jcl",
        )
        e2 = IREntity(
            entity_type=EntityType.STEP,
            name="STEP010",
            artifact_path="stable.jcl",
        )
        assert e1.entity_id == e2.entity_id, (
            f"Same inputs produced different IDs: {e1.entity_id!r} ≠ {e2.entity_id!r}. "
            "Entity IDs must be deterministic."
        )

    def test_different_artifact_paths_produce_different_ids(self):
        """
        Two entities with the same (type, name) but different artifact_paths
        must have different entity_ids to prevent cross-artifact merging.
        """
        e1 = IREntity(
            entity_type=EntityType.PROGRAM,
            name="CBACT01C",
            artifact_path="job_a.jcl",
        )
        e2 = IREntity(
            entity_type=EntityType.PROGRAM,
            name="CBACT01C",
            artifact_path="CBACT01C.cbl",
        )
        assert e1.entity_id != e2.entity_id, (
            "Same program name in different artifacts produced the same entity_id. "
            "This would cause unintended entity merging across artifacts."
        )

    def test_different_names_produce_different_ids(self):
        """Two different names (same artifact, same type) must yield different IDs."""
        e1 = IREntity(
            entity_type=EntityType.DATASET,
            name="MY.FILE.A",
            artifact_path="test.jcl",
        )
        e2 = IREntity(
            entity_type=EntityType.DATASET,
            name="MY.FILE.B",
            artifact_path="test.jcl",
        )
        assert e1.entity_id != e2.entity_id

    def test_entity_id_is_hexadecimal_string(self):
        """Entity ID must be a non-empty lowercase hexadecimal string."""
        e = IREntity(
            entity_type=EntityType.JOB,
            name="TESTJOB",
            artifact_path="test.jcl",
        )
        assert len(e.entity_id) > 0
        assert all(c in "0123456789abcdef" for c in e.entity_id), (
            f"entity_id {e.entity_id!r} contains non-hex characters."
        )

    def test_irgraph_deduplicates_on_entity_id(self):
        """
        IRGraph.add_entity must return the existing entity when the same ID is
        added twice, without creating duplicates.
        """
        ir = IRGraph()
        e1 = IREntity(entity_type=EntityType.STEP, name="S1", artifact_path="t.jcl")
        e2 = IREntity(entity_type=EntityType.STEP, name="S1", artifact_path="t.jcl")

        returned1 = ir.add_entity(e1)
        returned2 = ir.add_entity(e2)

        assert ir.entity_count() == 1, (
            f"IRGraph contains {ir.entity_count()} entities after adding the same "
            "entity twice — deduplication failed."
        )
        assert returned1.entity_id == returned2.entity_id


# ═══════════════════════════════════════════════════════════════════════════
# SI-11 (bonus)  return_code=None means "not captured", not zero
# ═══════════════════════════════════════════════════════════════════════════

class TestReturnCodeSemantics:
    """
    SI-11 — The model doc states: "return_code = None means 'not captured', NOT zero."
    This semantic distinction is important for control-flow reconciliation:
    a step with RC=None should not be treated as RC=0 (success).
    """

    def test_none_return_code_yields_not_observed(self):
        """
        A control-flow contract where the subject step has events but no
        return code (return_code=None) must yield NOT_OBSERVED, not CONTRADICTED.
        """
        from legacy_contract.contracts.model import ContractPredicate, ContractType

        bcg = BCG(ir=IRGraph())
        contract = _make_contract(
            subject_id="ctrl_a",
            object_id="ctrl_b",
            contract_type=ContractType.CONTROL_FLOW,
            predicate=ContractPredicate.MUST_NOT_FOLLOW_ON_ERROR,
        )
        contract.metadata["rc_threshold"] = 4
        contract.metadata["operator"] = "GT"
        bcg.add_contract(contract)

        # Add a STEP_END event for the subject with NO return code
        now = datetime(2024, 1, 1, 12, 0, 0)
        trace = ExecutionTrace(execution_id="rc_test")
        trace.add_event(ExecutionEvent(
            execution_id="rc_test",
            artifact_id="ctrl_a",
            operation=OperationType.STEP_END,
            timestamp=now,
            source_type=EventSourceType.EXECUTION,
            return_code=None,   # ← explicitly "not captured"
        ))

        engine = ReconciliationEngine()
        records = engine.reconcile(bcg, [trace])

        assert len(records) == 1
        # With no return code captured, the condition can never be evaluated →
        # the reconciliation result must be NOT_OBSERVED, not CONTRADICTED.
        assert records[0].outcome == ReconciliationOutcome.NOT_OBSERVED, (
            f"Expected NOT_OBSERVED for return_code=None, got {records[0].outcome}. "
            "return_code=None must be treated as 'not captured', not as RC=0."
        )


# ═══════════════════════════════════════════════════════════════════════════
# SI-12 (bonus)  GROUND_TRUTH is never downgraded by reconciliation
# ═══════════════════════════════════════════════════════════════════════════
# (Tested above in TestHumanValidatedProtection.test_ground_truth_not_overwritten)
# Kept here as a direct standalone test for clarity.

class TestGroundTruthProtection:
    """
    SI-12 — GROUND_TRUTH represents oracle-verified or deterministically proven
    contracts. No execution observation can invalidate ground truth — if execution
    contradicts it, the trace instrumentation or execution setup is wrong, not the
    contract. The reconciliation engine must preserve GROUND_TRUTH state.
    """

    def test_ground_truth_survives_supported_reconciliation(self):
        """GROUND_TRUTH should not be changed even if evidence is SUPPORTED."""
        bcg = BCG(ir=IRGraph())
        contract = _make_contract(
            subject_id="g1", object_id="g2",
            validation_state=ValidationState.GROUND_TRUTH,
        )
        bcg.add_contract(contract)

        trace = _trace_with_ordering("g1", "g2", a_before_b=True)
        engine = ReconciliationEngine()
        engine.reconcile(bcg, [trace])

        assert contract.validation_state == ValidationState.GROUND_TRUTH, (
            "GROUND_TRUTH was overwritten by a SUPPORTED outcome. "
            "GROUND_TRUTH is terminal — no reconciliation outcome should change it."
        )

    def test_ground_truth_survives_contradicted_reconciliation(self):
        """GROUND_TRUTH must be preserved even when execution appears to contradict it."""
        bcg = BCG(ir=IRGraph())
        contract = _make_contract(
            subject_id="g3", object_id="g4",
            validation_state=ValidationState.GROUND_TRUTH,
        )
        bcg.add_contract(contract)

        trace = _trace_with_ordering("g3", "g4", a_before_b=False)  # contradiction
        engine = ReconciliationEngine()
        engine.reconcile(bcg, [trace])

        assert contract.validation_state == ValidationState.GROUND_TRUTH, (
            "GROUND_TRUTH was overwritten by a CONTRADICTED outcome. "
            "See SI-12: ground truth is oracle-verified and must be preserved."
        )
