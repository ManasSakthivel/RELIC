"""
Counterfactual Contract Restoration Engine.

Given an original BCG, a mutation, and a set of violated contracts,
suggests minimal structural changes that would restore the violated contracts.

IMPORTANT DISCLAIMER: This module produces STRUCTURAL SUGGESTIONS only.
It does NOT produce executable code. It does NOT claim automated program repair.
Engineers must review, validate, and implement any suggested restoration.
No generated suggestion should be applied to a production system without
expert review and testing.

Design rationale:
    The restoration engine is grounded in the counterfactual reasoning
    framework described in the research methodology. For each violated
    contract it asks: "What is the minimal structural change to the mutated
    BCG that would restore this contract?" The answer is always a *suggestion*,
    not a verified fix, because:

    1. The BCG represents static/dynamic evidence, not executable code.
    2. Restoring a structural relation does not guarantee the change will
       compile, deploy, or behave correctly in the target environment.
    3. Multiple competing restorations may exist; the engine selects the
       minimal one (fewest structural changes) but cannot evaluate which is
       semantically correct without further human or oracle validation.

Restoration types:
    ORDERING_RESTORATION: re-insert a MUST_PRECEDE relation
    DEPENDENCY_RESTORATION: re-add a PRODUCES/CONSUMES dataset link
    RESOURCE_RESTORATION: re-create the dataset initialization step
    CONDITION_RESTORATION: re-add the COND parameter / control-flow check
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from legacy_contract.bcg.model import BCG
from legacy_contract.contracts.model import (
    Contract,
    ContractPredicate,
    ContractType,
    ValidationState,
)


# ---------------------------------------------------------------------------
# Restoration type taxonomy
# ---------------------------------------------------------------------------

class RestorationType(str, Enum):
    """
    Types of structural restoration that can be suggested.

    Each type corresponds to the inverse of a mutation operator:

    ORDERING_RESTORATION:   Inverse of REORDER_JOBS / REMOVE_JOB_DEPENDENCY /
                            ALTER_STEP_SEQUENCE.
                            Action: re-establish a MUST_PRECEDE relation with
                            the correct direction.

    DEPENDENCY_RESTORATION: Inverse of REMOVE_DATASET_INIT /
                            ALTER_FILE_DEPENDENCY_ORDER.
                            Action: re-add a PRODUCES or PRODUCES_BEFORE_CONSUMES
                            link between the producer and the dataset.

    RESOURCE_RESTORATION:   Inverse of CHANGE_DATASET_NAME.
                            Action: restore the original dataset name or add a
                            name-mapping alias so producer and consumer agree.

    CONDITION_RESTORATION:  Inverse of SUPPRESS_RETURN_CODE_CHECK /
                            ALTER_ERROR_BRANCH.
                            Action: re-introduce the COND parameter / error-guard
                            with the original RC threshold.
    """
    ORDERING_RESTORATION = "ORDERING_RESTORATION"
    DEPENDENCY_RESTORATION = "DEPENDENCY_RESTORATION"
    RESOURCE_RESTORATION = "RESOURCE_RESTORATION"
    CONDITION_RESTORATION = "CONDITION_RESTORATION"


# ---------------------------------------------------------------------------
# Restoration candidate
# ---------------------------------------------------------------------------

@dataclass
class RestorationCandidate:
    """
    A single structural restoration suggestion for a violated contract.

    Every candidate carries a mandatory disclaimer field. The disclaimer
    is included in all reports and UI panels to prevent engineers from
    treating suggestions as automated fixes.

    Fields:
        restoration_id:          unique identifier for this suggestion
        violated_contract_id:    the contract this suggestion targets
        restoration_type:        the category of structural change suggested
        description:             human-readable description of the suggestion
        rationale:               why this restoration was chosen
        structural_change:       machine-readable description of the proposed
                                 structural change (entity IDs and relation types)
        affected_artifacts:      entity IDs of artifacts involved in the change
        confidence:              evidence-strength that this restoration would
                                 repair the violation [0.0, 1.0]
                                 NOT a probability; see ConfidenceVector docs
        estimated_completeness:  fraction of the violated contract that this
                                 suggestion addresses (1.0 = full restoration)
        requires_human_review:   always True (design invariant)
        disclaimer:              mandatory warning about limitations
        validation_notes:        hints for how to validate the suggestion
    """
    restoration_id: str
    violated_contract_id: str
    restoration_type: RestorationType
    description: str
    rationale: str
    structural_change: dict[str, Any]
    affected_artifacts: list[str]
    confidence: float
    estimated_completeness: float
    requires_human_review: bool
    disclaimer: str
    validation_notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"[{self.restoration_type.value}] "
            f"contract={self.violated_contract_id[:8]} "
            f"confidence={self.confidence:.2f} "
            f"complete={self.estimated_completeness:.2f}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "restoration_id": self.restoration_id,
            "violated_contract_id": self.violated_contract_id,
            "restoration_type": self.restoration_type.value,
            "description": self.description,
            "rationale": self.rationale,
            "structural_change": self.structural_change,
            "affected_artifacts": self.affected_artifacts,
            "confidence": self.confidence,
            "estimated_completeness": self.estimated_completeness,
            "requires_human_review": self.requires_human_review,
            "disclaimer": self.disclaimer,
            "validation_notes": self.validation_notes,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Disclaimer constant
# ---------------------------------------------------------------------------

_STANDARD_DISCLAIMER = (
    "DISCLAIMER: This is a structural suggestion only. "
    "It does NOT constitute automated program repair, does NOT produce "
    "executable code, and has NOT been verified to be correct, complete, "
    "or safe for the target environment. "
    "An engineer with knowledge of the original and modernized system MUST "
    "review, validate, and implement any change before it is applied. "
    "The suggestion is based on static BCG evidence; dynamic execution "
    "evidence should be used to validate the restoration independently."
)


# ---------------------------------------------------------------------------
# Restoration Engine
# ---------------------------------------------------------------------------

class RestorationEngine:
    """
    Suggests minimal structural restorations for violated behavioral contracts.

    The engine examines each violated contract, infers from its type and
    predicate which mutation category likely caused the violation, and
    proposes the minimal inverse structural change.

    All suggestions are annotated with:
    - the standard disclaimer
    - a rationale referencing the contract's provenance and evidence
    - validation notes for how the engineer could verify the suggestion

    SCIENTIFIC NOTE: The engine does NOT implement automated code generation
    or program synthesis. Restoration suggestions are conceptual, not executable.
    This boundary is intentional and must be preserved to make defensible
    claims in the research paper.
    """

    def suggest(
        self,
        original_bcg: BCG,
        mutated_bcg: BCG,
        violated_contracts: list[Contract],
    ) -> list[RestorationCandidate]:
        """
        Generate restoration suggestions for all violated contracts.

        For each violated contract, attempts to generate a candidate using
        the contract's type and predicate to select the appropriate strategy.
        Contracts for which no strategy applies yield no candidate (logged).

        Returns:
            list of RestorationCandidate, one per restorable violated contract,
            sorted by confidence descending.
        """
        candidates: list[RestorationCandidate] = []

        for contract in violated_contracts:
            candidate = self._suggest_for_contract(
                contract, original_bcg, mutated_bcg
            )
            if candidate is not None:
                candidates.append(candidate)
                logger.debug(f"Restoration candidate: {candidate.summary()}")
            else:
                logger.debug(
                    f"No restoration candidate for contract {contract.contract_id[:8]} "
                    f"type={contract.contract_type.value}"
                )

        # Sort by confidence descending so highest-confidence suggestions appear first
        candidates.sort(key=lambda c: c.confidence, reverse=True)
        logger.info(
            f"RestorationEngine: {len(violated_contracts)} violated contracts, "
            f"{len(candidates)} restoration candidates generated"
        )
        return candidates

    def _suggest_for_contract(
        self,
        contract: Contract,
        original_bcg: BCG,
        mutated_bcg: BCG,
    ) -> RestorationCandidate | None:
        """
        Generate a single restoration candidate for one violated contract.

        Dispatch strategy:
        - TEMPORAL / PRECEDES              → ordering restoration
        - RESOURCE / PRODUCES_BEFORE_CONSUMES → dependency restoration
        - RESOURCE / MUST_PRECEDE_FOR_RESOURCE → resource restoration
        - CONTROL_FLOW / MUST_NOT_FOLLOW_ON_ERROR → condition restoration

        Returns None if no strategy applies.
        """
        predicate = contract.predicate
        ctype = contract.contract_type

        if ctype == ContractType.TEMPORAL and predicate == ContractPredicate.PRECEDES:
            return self._ordering_restoration(contract, original_bcg, mutated_bcg)

        if ctype == ContractType.RESOURCE:
            if predicate == ContractPredicate.PRODUCES_BEFORE_CONSUMES:
                return self._dependency_restoration(contract, original_bcg, mutated_bcg)
            if predicate == ContractPredicate.MUST_PRECEDE_FOR_RESOURCE:
                return self._resource_restoration(contract, original_bcg, mutated_bcg)

        if ctype == ContractType.CONTROL_FLOW:
            if predicate == ContractPredicate.MUST_NOT_FOLLOW_ON_ERROR:
                return self._condition_restoration(contract, original_bcg, mutated_bcg)

        logger.debug(
            f"No restoration strategy for "
            f"type={ctype.value} predicate={predicate.value}"
        )
        return None

    # ------------------------------------------------------------------
    # Ordering restoration (TEMPORAL contracts)
    # ------------------------------------------------------------------

    def _ordering_restoration(
        self,
        contract: Contract,
        original_bcg: BCG,
        mutated_bcg: BCG,
    ) -> RestorationCandidate:
        """
        Suggest re-establishing a MUST_PRECEDE relation from subject to object.

        The original BCG is inspected to confirm the relation existed.
        Confidence is highest if the contract is GROUND_TRUTH or
        STATIC_DYNAMIC_SUPPORTED; lower for STATIC_CANDIDATE.
        """
        from legacy_contract.ir.model import RelationType

        original_has_relation = any(
            r.relation_type == RelationType.MUST_PRECEDE
            and r.source.entity_id == contract.subject_id
            and r.target.entity_id == contract.object_id
            for r in original_bcg.relations
        )

        confidence = self._estimate_restoration_confidence(
            contract,
            evidence_present=original_has_relation,
        )

        subject_name = _entity_label(contract.subject_id, original_bcg)
        object_name = _entity_label(contract.object_id, original_bcg)

        structural_change = {
            "action": "ADD_RELATION",
            "relation_type": "MUST_PRECEDE",
            "source_entity_id": contract.subject_id,
            "target_entity_id": contract.object_id,
            "source_label": subject_name,
            "target_label": object_name,
        }

        validation_notes = [
            f"Verify that {subject_name} completes before {object_name} is scheduled.",
            "Run the execution oracle with the original and modernized systems "
            "on matching inputs to confirm ordering is preserved after the change.",
            f"Check batch scheduler configuration: "
            f"{subject_name} must be listed as a predecessor of {object_name}.",
        ]
        if contract.provenance:
            validation_notes.append(
                f"Original evidence location: "
                f"{contract.provenance.source_artifact}:"
                f"{contract.provenance.source_location}"
            )

        return RestorationCandidate(
            restoration_id=str(uuid.uuid4()),
            violated_contract_id=contract.contract_id,
            restoration_type=RestorationType.ORDERING_RESTORATION,
            description=(
                f"Re-establish execution ordering: "
                f"{subject_name} MUST PRECEDE {object_name}. "
                f"Ensure the batch scheduler / orchestration DAG declares "
                f"{subject_name} as a predecessor of {object_name}."
            ),
            rationale=(
                f"Contract [{contract.contract_type.value}] asserts "
                f"{subject_name} ≺ {object_name} (state={contract.validation_state.value}). "
                f"{'Original BCG confirms MUST_PRECEDE relation was present. ' if original_has_relation else ''}"
                f"The mutation removed or inverted this ordering; "
                f"restoring the predecessor declaration resolves the violation."
            ),
            structural_change=structural_change,
            affected_artifacts=[contract.subject_id, contract.object_id],
            confidence=confidence,
            estimated_completeness=1.0,
            requires_human_review=True,
            disclaimer=_STANDARD_DISCLAIMER,
            validation_notes=validation_notes,
            metadata={
                "original_has_relation": original_has_relation,
                "contract_validation_state": contract.validation_state.value,
            },
        )

    # ------------------------------------------------------------------
    # Dependency restoration (RESOURCE / PRODUCES_BEFORE_CONSUMES)
    # ------------------------------------------------------------------

    def _dependency_restoration(
        self,
        contract: Contract,
        original_bcg: BCG,
        mutated_bcg: BCG,
    ) -> RestorationCandidate:
        """
        Suggest re-adding a PRODUCES relation from subject to the shared dataset.

        This addresses F2.1 (REMOVE_DATASET_INIT) and F2.3
        (ALTER_FILE_DEPENDENCY_ORDER) mutation patterns.
        """
        from legacy_contract.ir.model import RelationType

        dataset_id = contract.metadata.get("dataset", "")
        subject_name = _entity_label(contract.subject_id, original_bcg)
        object_name = _entity_label(contract.object_id, original_bcg)
        dataset_label = (
            _entity_label(dataset_id, original_bcg) if dataset_id else "shared dataset"
        )

        # Check whether the PRODUCES relation is present in mutated BCG
        mutated_has_produces = any(
            r.relation_type == RelationType.PRODUCES
            and r.source.entity_id == contract.subject_id
            for r in mutated_bcg.relations
        )

        confidence = self._estimate_restoration_confidence(
            contract,
            evidence_present=not mutated_has_produces,  # missing = clear fix needed
        )

        structural_change: dict[str, Any] = {
            "action": "ADD_RELATION",
            "relation_type": "PRODUCES",
            "source_entity_id": contract.subject_id,
            "target_entity_id": dataset_id or contract.object_id,
            "source_label": subject_name,
            "target_label": dataset_label,
        }
        if not mutated_has_produces:
            structural_change["secondary_action"] = {
                "action": "ENSURE_ORDERING",
                "note": (
                    f"Ensure {subject_name} is scheduled and completes "
                    f"before {object_name} begins execution."
                ),
            }

        validation_notes = [
            f"Confirm {subject_name} is deployed and invoked before {object_name}.",
            f"Verify {dataset_label} is correctly written by {subject_name}.",
            f"Run the execution oracle: check {dataset_label} exists and is "
            f"non-empty before {object_name} starts.",
        ]

        return RestorationCandidate(
            restoration_id=str(uuid.uuid4()),
            violated_contract_id=contract.contract_id,
            restoration_type=RestorationType.DEPENDENCY_RESTORATION,
            description=(
                f"Re-establish dataset dependency: "
                f"{subject_name} must PRODUCE {dataset_label} "
                f"before {object_name} CONSUMES it. "
                f"{'The PRODUCES relation was removed in the mutated system.' if not mutated_has_produces else 'Correct the execution ordering so producer completes first.'}"
            ),
            rationale=(
                f"Contract [{contract.contract_type.value}] requires "
                f"{subject_name} to produce {dataset_label} "
                f"before {object_name} consumes it. "
                f"The mutation broke this by "
                f"{'removing the PRODUCES relation' if not mutated_has_produces else 'inverting the ordering'}."
            ),
            structural_change=structural_change,
            affected_artifacts=list({
                contract.subject_id,
                contract.object_id,
                *([dataset_id] if dataset_id else []),
            }),
            confidence=confidence,
            estimated_completeness=1.0 if not mutated_has_produces else 0.8,
            requires_human_review=True,
            disclaimer=_STANDARD_DISCLAIMER,
            validation_notes=validation_notes,
        )

    # ------------------------------------------------------------------
    # Resource restoration (RESOURCE / MUST_PRECEDE_FOR_RESOURCE)
    # ------------------------------------------------------------------

    def _resource_restoration(
        self,
        contract: Contract,
        original_bcg: BCG,
        mutated_bcg: BCG,
    ) -> RestorationCandidate:
        """
        Suggest restoring the original dataset name or adding a name mapping
        to reconcile producer-consumer dataset identity.

        This addresses F2.2 (CHANGE_DATASET_NAME) where the dataset was
        renamed on the producer side but not the consumer side.
        """
        subject_name = _entity_label(contract.subject_id, original_bcg)
        object_name = _entity_label(contract.object_id, original_bcg)
        dataset_id = contract.metadata.get("dataset", "")
        dataset_label = (
            _entity_label(dataset_id, original_bcg) if dataset_id else "dataset"
        )

        # Detect if the dataset entity has a mutation_renamed attribute
        renamed_in_mutated = False
        old_name: str | None = None
        new_name: str | None = None
        if dataset_id:
            mutated_entity = mutated_bcg.entities.get(dataset_id)
            if mutated_entity and mutated_entity.attributes.get("mutation_renamed"):
                renamed_in_mutated = True
                old_name = contract.metadata.get("original_dataset_name")
                new_name = mutated_entity.name

        confidence = self._estimate_restoration_confidence(
            contract, evidence_present=renamed_in_mutated
        )

        if renamed_in_mutated and old_name:
            structural_change = {
                "action": "RENAME_ENTITY",
                "entity_id": dataset_id,
                "old_name": new_name,
                "restore_to_name": old_name,
                "note": (
                    "Revert the dataset name on the producer side to match "
                    "the consumer's reference, OR update the consumer to "
                    "reference the new name — but not both."
                ),
            }
        else:
            structural_change = {
                "action": "VERIFY_DATASET_IDENTITY",
                "subject_entity_id": contract.subject_id,
                "object_entity_id": contract.object_id,
                "dataset_id": dataset_id or "unknown",
                "note": (
                    "Verify that both producer and consumer reference the "
                    "same physical dataset / file path / S3 key."
                ),
            }

        validation_notes = [
            f"Confirm {subject_name} writes to the same dataset path that "
            f"{object_name} reads from.",
            "Check DD names in JCL / environment-specific configuration.",
            "If a cloud migration introduced an S3 path change, ensure both "
            "producer and consumer use the same bucket and key prefix.",
        ]

        return RestorationCandidate(
            restoration_id=str(uuid.uuid4()),
            violated_contract_id=contract.contract_id,
            restoration_type=RestorationType.RESOURCE_RESTORATION,
            description=(
                f"Restore dataset identity between {subject_name} and {object_name}. "
                f"{'Rename the dataset from ' + str(new_name) + ' back to ' + str(old_name) + ' on the producer side, or update the consumer reference.' if renamed_in_mutated and old_name else 'Verify that producer and consumer reference the same dataset.'}"
            ),
            rationale=(
                f"Contract [{contract.contract_type.value}] requires that "
                f"{subject_name} and {object_name} share a common dataset identity. "
                f"{'A name mutation introduced a mismatch.' if renamed_in_mutated else 'Dataset identity could not be confirmed from available evidence.'}"
            ),
            structural_change=structural_change,
            affected_artifacts=list({
                contract.subject_id,
                contract.object_id,
                *([dataset_id] if dataset_id else []),
            }),
            confidence=confidence,
            estimated_completeness=0.9 if renamed_in_mutated else 0.6,
            requires_human_review=True,
            disclaimer=_STANDARD_DISCLAIMER,
            validation_notes=validation_notes,
            metadata={
                "renamed_in_mutated": renamed_in_mutated,
                "old_name": old_name,
                "new_name": new_name,
            },
        )

    # ------------------------------------------------------------------
    # Condition restoration (CONTROL_FLOW contracts)
    # ------------------------------------------------------------------

    def _condition_restoration(
        self,
        contract: Contract,
        original_bcg: BCG,
        mutated_bcg: BCG,
    ) -> RestorationCandidate:
        """
        Suggest restoring the COND parameter / return-code check that was
        suppressed or weakened by a F3 mutation.

        Handles both SUPPRESS_RETURN_CODE_CHECK (contract removed) and
        ALTER_ERROR_BRANCH (threshold changed).
        """
        subject_name = _entity_label(contract.subject_id, original_bcg)
        object_name = _entity_label(contract.object_id, original_bcg)
        original_threshold = contract.metadata.get("rc_threshold", "?")
        operator = contract.metadata.get("operator", "?")

        mutated_contract = mutated_bcg.contracts.get(contract.contract_id)

        if mutated_contract is None:
            # Contract was completely removed (SUPPRESS)
            change_type = "SUPPRESSED"
            new_threshold: Any = "REMOVED"
            action = "RESTORE_COND_PARAMETER"
            description = (
                f"Re-introduce the COND parameter on step {object_name}: "
                f"COND=({original_threshold},{operator},{subject_name}). "
                f"The return-code guard was completely removed in the modernized system."
            )
        else:
            # Contract exists but threshold was altered (ALTER_ERROR_BRANCH)
            change_type = "ALTERED"
            new_threshold = mutated_contract.metadata.get("rc_threshold", "?")
            action = "RESTORE_RC_THRESHOLD"
            description = (
                f"Restore the original RC threshold for the COND guard on {object_name}. "
                f"Original: COND=({original_threshold},{operator}); "
                f"Current: COND=({new_threshold},{operator}). "
                f"The weakened threshold allows {object_name} to run on errors "
                f"that should have aborted it."
            )

        structural_change = {
            "action": action,
            "subject_entity_id": contract.subject_id,
            "object_entity_id": contract.object_id,
            "original_rc_threshold": original_threshold,
            "new_rc_threshold": new_threshold,
            "rc_operator": operator,
            "change_type": change_type,
        }

        confidence = self._estimate_restoration_confidence(
            contract, evidence_present=(change_type == "SUPPRESSED")
        )

        validation_notes = [
            f"Verify that {object_name} should not execute when "
            f"{subject_name} returns RC {operator} {original_threshold}.",
            "Review original JCL COND parameters for this step.",
            "Test error paths: introduce a controlled failure in "
            f"{subject_name} and confirm {object_name} does not execute.",
            "If the threshold was intentionally changed, add an explicit "
            "exception record with justification to the contract registry.",
        ]

        return RestorationCandidate(
            restoration_id=str(uuid.uuid4()),
            violated_contract_id=contract.contract_id,
            restoration_type=RestorationType.CONDITION_RESTORATION,
            description=description,
            rationale=(
                f"Contract [{contract.contract_type.value}] requires that "
                f"{object_name} does not execute when {subject_name} returns "
                f"RC {operator} {original_threshold}. "
                f"The {change_type.lower()} COND guard broke this obligation."
            ),
            structural_change=structural_change,
            affected_artifacts=[contract.subject_id, contract.object_id],
            confidence=confidence,
            estimated_completeness=1.0 if change_type == "SUPPRESSED" else 0.85,
            requires_human_review=True,
            disclaimer=_STANDARD_DISCLAIMER,
            validation_notes=validation_notes,
            metadata={
                "change_type": change_type,
                "original_threshold": original_threshold,
                "current_threshold": new_threshold,
            },
        )

    # ------------------------------------------------------------------
    # Confidence estimation
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_restoration_confidence(
        contract: Contract,
        evidence_present: bool,
    ) -> float:
        """
        Estimate confidence that this restoration suggestion is correct.

        This is a transparent heuristic, not a learned model.
        Rules (pre-specified, not tuned on test data):

        Base score from validation state:
            GROUND_TRUTH             → 0.90
            HUMAN_VALIDATED          → 0.85
            STATIC_DYNAMIC_SUPPORTED → 0.75
            STATIC_CANDIDATE         → 0.50
            NOT_OBSERVED / UNRESOLVED → 0.35

        Modifier:
            + 0.10 if structural evidence_present (confirms the mutation)
            - 0.10 if contract has a STATIC_DYNAMIC_CONFLICT
            contract.confidence_score() used as a secondary weight

        Result is clipped to [0.0, 1.0].

        SCIENTIFIC CAVEAT: This is NOT a probability of correctness.
        Do not report it as such in the paper.
        """
        state_base: dict[ValidationState, float] = {
            ValidationState.GROUND_TRUTH: 0.90,
            ValidationState.HUMAN_VALIDATED: 0.85,
            ValidationState.STATIC_DYNAMIC_SUPPORTED: 0.75,
            ValidationState.STATIC_CANDIDATE: 0.50,
            ValidationState.DYNAMICALLY_OBSERVED: 0.65,
            ValidationState.NOT_OBSERVED: 0.35,
            ValidationState.UNRESOLVED: 0.35,
            ValidationState.STATIC_DYNAMIC_CONFLICT: 0.30,
        }
        base = state_base.get(contract.validation_state, 0.40)
        modifier = 0.10 if evidence_present else 0.0
        if contract.validation_state == ValidationState.STATIC_DYNAMIC_CONFLICT:
            modifier -= 0.10

        # Blend with contract's own evidence-strength score
        blended = 0.70 * base + 0.30 * contract.confidence_score() + modifier
        return max(0.0, min(1.0, blended))


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _entity_label(entity_id: str, bcg: BCG) -> str:
    """Return the entity name for an ID, or the first 8 chars of the ID if not found."""
    entity = bcg.entities.get(entity_id)
    if entity:
        return entity.name
    return entity_id[:8]
