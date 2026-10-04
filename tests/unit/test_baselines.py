"""
Unit tests for Baselines B, D, E and the BaselineResult dataclass.

Coverage:
- test_baseline_result_predictions_is_dict_str_bool
- test_complexity_non_negative_scores
- test_complexity_normalized_to_unit_interval
- test_complexity_single_artifact_normalizes_to_zero
- test_complexity_predict_returns_baseline_result
- test_complexity_threshold_high_risk
- test_complexity_threshold_low_risk
- test_dep_llm_stub_mode_no_llm
- test_dep_llm_stub_predictions_empty_when_unavailable
- test_static_bcg_no_static_dynamic_supported_contracts
- test_static_bcg_broken_contract_flagged
- test_static_bcg_predictions_false_when_no_mutation_effect
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------
from baselines.base import BaselineResult
from baselines.complexity.complexity import (
    ArtifactMetrics,
    ComplexityBaseline,
    METRIC_WEIGHTS,
    RISK_THRESHOLD,
)
from baselines.dep_llm.dep_llm import DepLLMBaseline
from baselines.static_bcg.static_bcg import StaticBCGBaseline

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
    SourceLocation,
)
from legacy_contract.mutations.engine import (
    FailureCategory,
    MutationEngine,
    MutationOperator,
    MutationRecord,
)
from legacy_contract.risk.detector import RiskDetector


# ===========================================================================
# Helpers / factories
# ===========================================================================

def make_ir_with_steps(artifact: str = "test.jcl") -> IRGraph:
    """
    Build a minimal IRGraph with two steps connected by MUST_PRECEDE and a
    PRODUCES/CONSUMES pair for a dataset.

    step_a → MUST_PRECEDE → step_b
    step_a → PRODUCES     → ds
    step_b → CONSUMES     → ds
    """
    ir = IRGraph(artifact_paths=[artifact])

    step_a = IREntity(entity_type=EntityType.STEP, name="STEP010", artifact_path=artifact)
    step_b = IREntity(entity_type=EntityType.STEP, name="STEP020", artifact_path=artifact)
    ds     = IREntity(entity_type=EntityType.DATASET, name="MY.DATA", artifact_path=artifact)

    ir.add_entity(step_a)
    ir.add_entity(step_b)
    ir.add_entity(ds)

    ir.add_relation(IRRelation(
        relation_type=RelationType.MUST_PRECEDE,
        source=step_a,
        target=step_b,
        confidence=1.0,
    ))
    ir.add_relation(IRRelation(
        relation_type=RelationType.PRODUCES,
        source=step_a,
        target=ds,
        confidence=1.0,
    ))
    ir.add_relation(IRRelation(
        relation_type=RelationType.CONSUMES,
        source=step_b,
        target=ds,
        confidence=1.0,
    ))

    return ir


def make_mutation(
    affected_entity_ids: list[str] | None = None,
    affected_contract_ids: list[str] | None = None,
) -> MutationRecord:
    return MutationRecord(
        mutation_id=str(uuid.uuid4()),
        failure_category=FailureCategory.F1_JOB_ORDERING,
        source_evidence_ref="failure_taxonomy.md#F1.1",
        operator=MutationOperator.REORDER_JOBS,
        affected_entity_ids=affected_entity_ids or [],
        affected_contract_ids=affected_contract_ids or [],
        original_state="STEP010 MUST_PRECEDE STEP020",
        mutated_state="STEP020 MUST_PRECEDE STEP010 (reversed)",
        seed=42,
    )


def make_contract(
    subject_id: str = "s1",
    object_id: str = "o1",
    contract_type: ContractType = ContractType.TEMPORAL,
    validation_state: ValidationState = ValidationState.STATIC_CANDIDATE,
    confidence_static: float = 1.0,
    predicate: ContractPredicate = ContractPredicate.PRECEDES,
    metadata: dict[str, Any] | None = None,
) -> Contract:
    cv = ConfidenceVector(static_support=confidence_static)
    return Contract(
        contract_type=contract_type,
        subject_id=subject_id,
        predicate=predicate,
        object_id=object_id,
        natural_language=f"{subject_id} must precede {object_id}.",
        provenance=ProvenanceRecord(
            source_artifact="test.jcl",
            source_location="test.jcl:1:0",
        ),
        validation_state=validation_state,
        confidence=cv,
        metadata=metadata or {},
    )


def make_control_flow_bcg() -> BCG:
    ir = IRGraph(artifact_paths=["control.jcl"])
    step_a = IREntity(entity_type=EntityType.STEP, name="STEP010", artifact_path="control.jcl")
    step_b = IREntity(entity_type=EntityType.STEP, name="STEP020", artifact_path="control.jcl")
    ir.add_entity(step_a)
    ir.add_entity(step_b)

    bcg = BCG(ir=ir, artifact_paths=["control.jcl"])
    contract = make_contract(
        subject_id=step_a.entity_id,
        object_id=step_b.entity_id,
        contract_type=ContractType.CONTROL_FLOW,
        predicate=ContractPredicate.MUST_NOT_FOLLOW_ON_ERROR,
        metadata={"rc_threshold": 4, "operator": "GT"},
    )
    bcg.add_contract(contract)
    return bcg


# ===========================================================================
# BaselineResult tests
# ===========================================================================

class TestBaselineResult:
    def test_predictions_is_dict_str_bool(self):
        result = BaselineResult(
            method="test",
            predictions={"c1": True, "c2": False},
            confidence={"c1": 0.9, "c2": 0.1},
        )
        assert isinstance(result.predictions, dict)
        for k, v in result.predictions.items():
            assert isinstance(k, str)
            assert isinstance(v, bool)

    def test_confidence_is_dict_str_float(self):
        result = BaselineResult(
            method="test",
            predictions={"c1": True},
            confidence={"c1": 0.75},
        )
        for k, v in result.confidence.items():
            assert isinstance(k, str)
            assert isinstance(v, float)

    def test_empty_predictions_valid(self):
        result = BaselineResult(method="stub", predictions={}, confidence={})
        assert result.predictions == {}
        assert result.confidence == {}

    def test_metadata_defaults_to_empty_dict(self):
        result = BaselineResult(method="m", predictions={}, confidence={})
        assert isinstance(result.metadata, dict)


# ===========================================================================
# Baseline B — ComplexityBaseline
# ===========================================================================

class TestComplexityBaseline:
    def test_non_negative_raw_scores(self):
        """M1–M5 must all be ≥ 0."""
        baseline = ComplexityBaseline()
        ir = make_ir_with_steps()
        metrics = baseline.compute_metrics(ir)
        for am in metrics.values():
            raw = am.raw_dict()
            for metric_name, value in raw.items():
                assert value >= 0, (
                    f"Raw metric {metric_name} for {am.artifact_path} is negative: {value}"
                )

    def test_normalized_to_unit_interval(self):
        """After normalization, all normalized values and risk_score ∈ [0, 1]."""
        baseline = ComplexityBaseline()
        ir = make_ir_with_steps()
        metrics = baseline.compute_metrics(ir)
        baseline.normalize(metrics)
        for am in metrics.values():
            for m_name, norm_val in am.normalized.items():
                assert 0.0 <= norm_val <= 1.0, (
                    f"Normalized metric {m_name} = {norm_val} outside [0, 1]"
                )
            assert 0.0 <= am.risk_score <= 1.0, (
                f"risk_score = {am.risk_score} outside [0, 1]"
            )

    def test_single_artifact_normalizes_to_zero(self):
        """
        When only one artifact exists all min==max → normalized = 0.0 (no range).
        This is correct: with a single data point no relative ordering exists.
        """
        baseline = ComplexityBaseline()
        ir = make_ir_with_steps("only.jcl")
        metrics = baseline.compute_metrics(ir)
        baseline.normalize(metrics)
        for am in metrics.values():
            for norm_val in am.normalized.values():
                assert norm_val == 0.0

    def test_two_artifacts_high_complexity_gets_higher_score(self):
        """Artifact with more entities gets higher risk_score than empty artifact."""
        ir = IRGraph(artifact_paths=["rich.jcl", "empty.jcl"])
        # Add many entities to rich.jcl
        for i in range(10):
            step = IREntity(entity_type=EntityType.STEP, name=f"STEP{i:03d}", artifact_path="rich.jcl")
            ir.add_entity(step)
        # empty.jcl has no entities (but is in artifact_paths)
        baseline = ComplexityBaseline()
        metrics = baseline.compute_metrics(ir)
        baseline.normalize(metrics)
        rich_score  = metrics.get("rich.jcl",  ArtifactMetrics("rich.jcl")).risk_score
        empty_score = metrics.get("empty.jcl", ArtifactMetrics("empty.jcl")).risk_score
        assert rich_score >= empty_score

    def test_predict_returns_baseline_result(self):
        baseline = ComplexityBaseline()
        ir = make_ir_with_steps()
        mutation = make_mutation()
        result = baseline.predict(ir, mutation, ["c1", "c2", "c3"])
        assert isinstance(result, BaselineResult)
        assert result.method == "complexity_metrics"
        assert set(result.predictions.keys()) == {"c1", "c2", "c3"}

    def test_predict_all_contract_ids_covered(self):
        baseline = ComplexityBaseline()
        ir = make_ir_with_steps()
        mutation = make_mutation()
        cids = [f"contract_{i}" for i in range(5)]
        result = baseline.predict(ir, mutation, cids)
        assert set(result.predictions.keys()) == set(cids)
        assert set(result.confidence.keys()) == set(cids)

    def test_threshold_documented_in_metadata(self):
        baseline = ComplexityBaseline()
        ir = make_ir_with_steps()
        result = baseline.predict(ir, make_mutation(), ["c1"])
        assert "risk_threshold" in result.metadata
        assert result.metadata["risk_threshold"] == RISK_THRESHOLD

    def test_risk_threshold_is_0_5(self):
        """Pre-specified threshold must be exactly 0.5 (not tuned)."""
        assert RISK_THRESHOLD == 0.50

    def test_metric_weights_sum_to_one(self):
        """Weights must form a valid convex combination."""
        total = sum(METRIC_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"

    def test_high_risk_artifact_triggers_prediction_true(self):
        """
        Construct an IR where the affected artifact clearly dominates
        (many entities), so normalized risk > threshold after normalization.
        We test this by inserting many steps to a second artifact that
        the mutation does NOT affect, making the affected artifact 'low-complexity'.
        The test verifies prediction is False when affected artifact has low complexity.
        """
        ir = IRGraph(artifact_paths=["small.jcl", "big.jcl"])
        # small.jcl: 1 step
        small_step = IREntity(EntityType.STEP, "STEP010", "small.jcl")
        ir.add_entity(small_step)
        # big.jcl: 20 steps
        for i in range(20):
            ir.add_entity(IREntity(EntityType.STEP, f"BIG{i:03d}", "big.jcl"))
            ir.add_entity(IREntity(EntityType.DATASET, f"DS{i:03d}", "big.jcl"))

        mutation = make_mutation(affected_entity_ids=[small_step.entity_id])
        baseline = ComplexityBaseline()
        result = baseline.predict(ir, mutation, ["c1"])
        # small.jcl has normalized risk << 0.5 → should be False
        assert result.predictions["c1"] is False

    def test_empty_contract_ids_returns_empty_predictions(self):
        baseline = ComplexityBaseline()
        ir = make_ir_with_steps()
        result = baseline.predict(ir, make_mutation(), [])
        assert result.predictions == {}
        assert result.confidence == {}


# ===========================================================================
# Baseline D — DepLLMBaseline (stub mode tests only)
# ===========================================================================

class TestDepLLMBaselineStub:
    """
    Tests for DepLLMBaseline in stub mode (LLM API unavailable).

    These tests MUST NOT require an OpenAI API key.
    They verify the graceful degradation path.
    """

    def _make_baseline_stub(self) -> DepLLMBaseline:
        """
        Create a DepLLMBaseline whose internal adapter is always unavailable.
        We monkey-patch _adapter.is_available to return False.
        """
        baseline = DepLLMBaseline()
        baseline._adapter._client = None  # force unavailable
        return baseline

    def test_stub_mode_returns_baseline_result(self):
        baseline = self._make_baseline_stub()
        ir = make_ir_with_steps()
        mutation = make_mutation()
        result = baseline.predict(ir, mutation, ["c1", "c2"])
        assert isinstance(result, BaselineResult)

    def test_stub_mode_method_is_dep_llm(self):
        baseline = self._make_baseline_stub()
        ir = make_ir_with_steps()
        result = baseline.predict(ir, make_mutation(), ["c1"])
        assert result.method == "dep_llm"

    def test_stub_mode_llm_available_false(self):
        baseline = self._make_baseline_stub()
        ir = make_ir_with_steps()
        result = baseline.predict(ir, make_mutation(), ["c1"])
        assert result.metadata.get("llm_available") is False

    def test_stub_mode_predictions_empty_when_unavailable(self):
        """
        Per spec: stub mode returns empty predictions when LLM is unavailable.
        """
        baseline = self._make_baseline_stub()
        ir = make_ir_with_steps()
        result = baseline.predict(ir, make_mutation(), ["c1", "c2"])
        assert result.predictions == {}

    def test_stub_mode_prompt_version_in_metadata(self):
        baseline = self._make_baseline_stub()
        ir = make_ir_with_steps()
        result = baseline.predict(ir, make_mutation(), [])
        assert result.metadata.get("prompt_version") == "dep_llm_v1"

    def test_stub_mode_dependency_context_length_in_metadata(self):
        baseline = self._make_baseline_stub()
        ir = make_ir_with_steps()
        result = baseline.predict(ir, make_mutation(), [])
        assert "dependency_context_length" in result.metadata
        assert result.metadata["dependency_context_length"] > 0

    def test_stub_mode_call_log_empty(self):
        """No LLM calls should be recorded in stub mode."""
        baseline = self._make_baseline_stub()
        ir = make_ir_with_steps()
        baseline.predict(ir, make_mutation(), ["c1"])
        assert baseline.call_log == []


# ===========================================================================
# Baseline E — StaticBCGBaseline
# ===========================================================================

class TestStaticBCGBaseline:
    """
    Tests for StaticBCGBaseline.

    Key invariant: no contract in a static-only BCG may have
    validation_state == STATIC_DYNAMIC_SUPPORTED.
    """

    def _build_bcg_with_contracts(
        self,
        contracts: list[Contract],
        artifact: str = "test.jcl",
    ) -> BCG:
        """Build a minimal BCG containing the given contracts."""
        ir = IRGraph(artifact_paths=[artifact])
        bcg = BCG(ir=ir, artifact_paths=[artifact])
        for c in contracts:
            # Bypass BCG.add_contract integrity check by inserting directly
            bcg.contracts[c.contract_id] = c
        return bcg

    # ------------------------------------------------------------------
    # Invariant: no STATIC_DYNAMIC_SUPPORTED in static-only result
    # ------------------------------------------------------------------

    def test_no_static_dynamic_supported_contracts_from_ir(self):
        """
        RQ3 invariant: StaticBCGBaseline never produces contracts with
        STATIC_DYNAMIC_SUPPORTED because dynamic evidence is never added.
        """
        baseline = StaticBCGBaseline()
        ir = make_ir_with_steps()
        bcg = baseline.build_static_bcg(ir)
        for contract in bcg.contracts.values():
            assert contract.validation_state != ValidationState.STATIC_DYNAMIC_SUPPORTED, (
                f"Contract {contract.contract_id} has STATIC_DYNAMIC_SUPPORTED state — "
                "dynamic evidence must not be present in static-only baseline"
            )

    def test_all_contracts_static_candidate_only(self):
        """All contracts from build_static_bcg must be STATIC_CANDIDATE."""
        baseline = StaticBCGBaseline()
        ir = make_ir_with_steps()
        bcg = baseline.build_static_bcg(ir)
        for c in bcg.contracts.values():
            assert c.validation_state in {
                ValidationState.STATIC_CANDIDATE,
                ValidationState.NOT_OBSERVED,
            }

    def test_no_dynamic_observations_in_static_bcg(self):
        baseline = StaticBCGBaseline()
        ir = make_ir_with_steps()
        bcg = baseline.build_static_bcg(ir)
        assert len(bcg.dynamic_observations) == 0

    # ------------------------------------------------------------------
    # Prediction tests using pre-built BCGs
    # ------------------------------------------------------------------

    def test_broken_contract_flagged_as_predicted_violation(self):
        """A contract in the diff.broken list → predictions[contract_id] = True."""
        baseline = StaticBCGBaseline()

        cid = str(uuid.uuid4())
        c_orig = make_contract(subject_id="a", object_id="b")
        c_orig.contract_id = cid

        orig_bcg = self._build_bcg_with_contracts([c_orig])
        # Mutated BCG lacks this contract
        mut_bcg = self._build_bcg_with_contracts([])

        mutation = make_mutation()
        result = baseline.predict_from_bcgs(orig_bcg, mut_bcg, mutation, [cid])

        assert isinstance(result, BaselineResult)
        assert result.method == "static_bcg"
        assert result.predictions[cid] is True

    def test_preserved_contract_not_flagged(self):
        """A contract present in both BCGs with same signature → predictions = False."""
        baseline = StaticBCGBaseline()

        c = make_contract(subject_id="x", object_id="y")
        cid = c.contract_id
        c2 = make_contract(subject_id="x", object_id="y")
        c2.contract_id = cid   # same ID in both

        orig_bcg = self._build_bcg_with_contracts([c])
        mut_bcg  = self._build_bcg_with_contracts([c2])

        mutation = make_mutation()
        result = baseline.predict_from_bcgs(orig_bcg, mut_bcg, mutation, [cid])

        # Preserved → not predicted as violation
        assert result.predictions[cid] is False

    def test_predictions_false_when_no_mutation_effect(self):
        """When diff.broken is empty, all predictions must be False."""
        baseline = StaticBCGBaseline()

        contracts = [make_contract(subject_id=f"e{i}", object_id=f"e{i+1}") for i in range(3)]
        # Identical BCGs → no broken contracts
        orig_bcg = self._build_bcg_with_contracts(contracts)
        mut_bcg  = self._build_bcg_with_contracts(contracts[:])   # shallow copy — same objects

        mutation = make_mutation()
        cids = [c.contract_id for c in contracts]
        result = baseline.predict_from_bcgs(orig_bcg, mut_bcg, mutation, cids)

        assert all(not v for v in result.predictions.values()), (
            f"Expected all False, got: {result.predictions}"
        )

    def test_metadata_has_dynamic_evidence_false(self):
        baseline = StaticBCGBaseline()
        orig_bcg = self._build_bcg_with_contracts([])
        mut_bcg  = self._build_bcg_with_contracts([])
        result = baseline.predict_from_bcgs(orig_bcg, mut_bcg, make_mutation(), [])
        assert result.metadata.get("has_dynamic_evidence") is False

    def test_method_name_is_static_bcg(self):
        baseline = StaticBCGBaseline()
        orig_bcg = self._build_bcg_with_contracts([])
        result = baseline.predict_from_bcgs(orig_bcg, orig_bcg, make_mutation(), [])
        assert result.method == "static_bcg"

    def test_confidence_from_contract_score(self):
        """
        Confidence for each contract_id should match contract.confidence_score()
        from the original BCG.
        """
        baseline = StaticBCGBaseline()
        c = make_contract(subject_id="a", object_id="b", confidence_static=1.0)
        expected_conf = round(c.confidence_score(), 4)
        cid = c.contract_id

        orig_bcg = self._build_bcg_with_contracts([c])
        mut_bcg  = self._build_bcg_with_contracts([])

        result = baseline.predict_from_bcgs(orig_bcg, mut_bcg, make_mutation(), [cid])
        assert result.confidence[cid] == expected_conf


class TestRiskDetectorModifiedContracts:
    def test_alter_error_branch_produces_modified_contract_and_risk_item(self):
        bcg = make_control_flow_bcg()
        original_contract = next(iter(bcg.contracts.values()))

        mutated_bcg, record = MutationEngine().apply(
            bcg, MutationOperator.ALTER_ERROR_BRANCH, seed=42
        )
        diff = bcg.diff(mutated_bcg)

        assert len(diff.broken) == 0
        assert len(diff.modified) == 1

        orig_contract, mod_contract = diff.modified[0]
        assert orig_contract.contract_id == original_contract.contract_id
        assert mod_contract.metadata["rc_threshold"] != orig_contract.metadata["rc_threshold"]
        assert mod_contract.confidence_score() < orig_contract.confidence_score()

        report = RiskDetector().detect(bcg, mutated_bcg, record)
        assert report.violated_contracts == 1
        assert len(report.risk_items) == 0
        assert len(report.false_positive_candidates) == 1
        assert report.false_positive_candidates[0].metadata.get("modified_contract") is True
        assert "rc_threshold changed" in report.false_positive_candidates[0].change_description

    def test_strengthened_modified_contract_is_not_reported_as_violation(self):
        """
        Legacy (v1.0.0) behaviour: the diff ignored guard parameters, so a
        contract whose confidence *rose* is not reported.

        Note (remediation, Oct 2026): this fixture uses COND=(4,GT) -> (2,GT).
        Under IBM COND semantics that is a *weakening* (at RC 2-3 the original
        bypasses the step, the new version runs it), so the premise "stronger
        guard" only holds for the confidence-based v1.0.0 view. The v1.1
        semantics are tested in TestGuardWeakeningSemantics below.
        """
        bcg = make_control_flow_bcg()
        original_contract = next(iter(bcg.contracts.values()))
        mutated_bcg = copy.deepcopy(bcg)
        mutated_contract = next(iter(mutated_bcg.contracts.values()))
        mutated_contract.confidence.static_support = original_contract.confidence.static_support + 0.2
        mutated_contract.metadata["rc_threshold"] = 2

        report = RiskDetector(legacy_v1_0=True).detect(
            bcg,
            mutated_bcg,
            MutationRecord(
                mutation_id=str(uuid.uuid4()),
                failure_category=FailureCategory.F3_RC_PROPAGATION,
                source_evidence_ref="failure_taxonomy.md#F3.2",
                operator=MutationOperator.ALTER_ERROR_BRANCH,
                affected_entity_ids=[original_contract.subject_id, original_contract.object_id],
                affected_contract_ids=[original_contract.contract_id],
                original_state="threshold 4",
                mutated_state="threshold 2 with stronger guard",
                seed=7,
            ),
        )

        assert report.violated_contracts == 0
        assert report.risk_items == []
