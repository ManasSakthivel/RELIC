"""
Behavioral Contract Graph (BCG).

Formal definition:
    BCG = (V, E, C, P, D, Γ)

Where:
    V = entities (dict entity_id -> IREntity)
    E = structural relations (list IRRelation)
    C = behavioral contracts (dict contract_id -> Contract)
    P = provenance (embedded in Contract.provenance)
    D = dynamic observations (dict event_id -> ExecutionEvent)
    Γ = validation metadata (embedded in Contract.validation_state + Contract.confidence)

Physical storage: SQLite (development) or Neo4j (production).
This module provides the in-memory BCG model and query interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from legacy_contract.ir.model import IREntity, IRGraph, IRRelation, RelationType
from legacy_contract.contracts.model import (
    Contract,
    ContractType,
    ValidationState,
)
from legacy_contract.dynamic_analysis.model import ExecutionEvent


# ---------------------------------------------------------------------------
# BCG
# ---------------------------------------------------------------------------

@dataclass
class BCG:
    """
    Behavioral Contract Graph.

    The BCG is built on top of an IRGraph by the BCGBuilder.
    It adds behavioral contracts, dynamic observations, and validation state.
    """
    # V — entity set (inherited from IR)
    ir: IRGraph = field(default_factory=IRGraph)

    # C — behavioral contract set
    contracts: dict[str, Contract] = field(default_factory=dict)

    # D — dynamic observation set
    dynamic_observations: dict[str, ExecutionEvent] = field(default_factory=dict)

    # BCG-level metadata
    artifact_paths: list[str] = field(default_factory=list)
    bcg_id: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # --- Entity access (V) ---

    @property
    def entities(self) -> dict[str, IREntity]:
        return self.ir.entities

    @property
    def relations(self) -> list[IRRelation]:
        return self.ir.relations

    # --- Contract operations (C) ---

    def add_contract(self, contract: Contract) -> None:
        """
        Add a behavioral contract to the BCG.

        Referential integrity check: warns if the subject_id or object_id do not
        correspond to known entities in the IR.  This is a WARNING not an error
        because contracts may reference entities from artifacts not yet ingested
        (cross-artifact incremental loading).  The warning is logged so that
        researchers can identify provenance gaps during evaluation.
        """
        from loguru import logger  # local import avoids circular deps at module level
        if contract.subject_id not in self.ir.entities:
            logger.warning(
                f"BCG.add_contract: contract {contract.contract_id[:8]} "
                f"subject_id={contract.subject_id!r} not found in IR entities. "
                "This may indicate a cross-artifact reference or a parser gap."
            )
        if contract.object_id not in self.ir.entities:
            logger.warning(
                f"BCG.add_contract: contract {contract.contract_id[:8]} "
                f"object_id={contract.object_id!r} not found in IR entities. "
                "This may indicate a cross-artifact reference or a parser gap."
            )
        self.contracts[contract.contract_id] = contract

    def get_contract(self, contract_id: str) -> Contract | None:
        return self.contracts.get(contract_id)

    def get_contracts_by_type(self, contract_type: ContractType) -> list[Contract]:
        return [c for c in self.contracts.values() if c.contract_type == contract_type]

    def get_contracts_involving(self, entity_id: str) -> list[Contract]:
        return [
            c for c in self.contracts.values()
            if c.subject_id == entity_id or c.object_id == entity_id
        ]

    def get_contracts_by_state(self, state: ValidationState) -> list[Contract]:
        return [c for c in self.contracts.values() if c.validation_state == state]

    def get_conflicts(self) -> list[Contract]:
        return self.get_contracts_by_state(ValidationState.STATIC_DYNAMIC_CONFLICT)

    def get_unobserved(self) -> list[Contract]:
        return self.get_contracts_by_state(ValidationState.NOT_OBSERVED)

    # --- Dynamic observations (D) ---

    def add_observation(self, event: ExecutionEvent) -> None:
        self.dynamic_observations[event.event_id] = event

    def get_observations_for_artifact(self, artifact_id: str) -> list[ExecutionEvent]:
        return [
            e for e in self.dynamic_observations.values()
            if e.artifact_id == artifact_id
        ]

    # --- Query methods ---

    def contract_count(self) -> int:
        return len(self.contracts)

    def observation_count(self) -> int:
        return len(self.dynamic_observations)

    def validated_contracts(self) -> list[Contract]:
        return [c for c in self.contracts.values() if c.is_validated()]

    def dynamic_coverage_rate(self) -> float:
        """
        Fraction of contracts that have at least one dynamic observation.
        """
        if not self.contracts:
            return 0.0
        covered = sum(
            1 for c in self.contracts.values()
            if c.validation_state not in {
                ValidationState.STATIC_CANDIDATE,
                ValidationState.NOT_OBSERVED,
            }
        )
        return covered / len(self.contracts)

    def diff(self, other: "BCG", compare_parameters: bool = True) -> "BCGDiff":
        """
        Compute contract-level diff: self = original, other = modernized.
        Returns contracts broken, preserved, added, and modified.

        MODIFIED contracts have the same semantic signature (type, subject,
        predicate, object) in both BCGs but differ in confidence, validation
        state or (when ``compare_parameters``) in their behavioural parameters
        (``rc_threshold`` / ``operator`` of a CONTROL_FLOW guard) — i.e. an
        obligation that changed but was not dropped entirely.

        v1.0.0 did not compare parameters, so a source-level change such as
        COND=(4,LT) -> COND=(8,LT) was classified as *preserved*.
        ``compare_parameters=False`` reproduces that behaviour.
        """
        # Semantic equivalence: compare by (type, subject, predicate, object) not by UUID
        def contract_signature(c: Contract) -> tuple[str, str, str, str]:
            return (c.contract_type.value, c.subject_id, c.predicate.value, c.object_id)

        orig_sigs = {contract_signature(c): c for c in self.contracts.values()}
        mod_sigs = {contract_signature(c): c for c in other.contracts.values()}

        preserved_or_modified: list[tuple[Contract, Contract]] = []
        for sig in orig_sigs:
            if sig in mod_sigs:
                preserved_or_modified.append((orig_sigs[sig], mod_sigs[sig]))

        # Classify preserved vs modified: same signature but different confidence
        # or validation state is a MODIFIED contract (weakened or strengthened obligation).
        def _is_modified(orig_c: Contract, mod_c: Contract) -> bool:
            orig_conf = round(orig_c.confidence_score(), 4)
            mod_conf = round(mod_c.confidence_score(), 4)
            return (
                orig_c.validation_state != mod_c.validation_state
                or abs(orig_conf - mod_conf) > 0.05
                or (
                    compare_parameters
                    and contract_parameters(orig_c) != contract_parameters(mod_c)
                )
            )

        preserved_list: list[Contract] = []
        modified_list: list[tuple[Contract, Contract]] = []
        for orig_c, mod_c in preserved_or_modified:
            if _is_modified(orig_c, mod_c):
                modified_list.append((orig_c, mod_c))
            else:
                preserved_list.append(orig_c)

        broken_list = [orig_sigs[sig] for sig in orig_sigs if sig not in mod_sigs]
        added_list = [mod_sigs[sig] for sig in mod_sigs if sig not in orig_sigs]

        return BCGDiff(
            preserved=preserved_list,
            broken=broken_list,
            added=added_list,
            modified=modified_list,
        )

    def summary(self) -> str:
        state_counts: dict[str, int] = {}
        for c in self.contracts.values():
            state_counts[c.validation_state.value] = (
                state_counts.get(c.validation_state.value, 0) + 1
            )
        type_counts: dict[str, int] = {}
        for c in self.contracts.values():
            type_counts[c.contract_type.value] = (
                type_counts.get(c.contract_type.value, 0) + 1
            )
        lines = [
            f"BCG: {self.ir.entity_count()} entities, {self.ir.relation_count()} relations",
            f"Contracts: {self.contract_count()} | "
            f"Observations: {self.observation_count()} | "
            f"Coverage: {self.dynamic_coverage_rate():.1%}",
            "Contract types: " + ", ".join(f"{k}={v}" for k, v in sorted(type_counts.items())),
            "Validation states: " + ", ".join(f"{k}={v}" for k, v in sorted(state_counts.items())),
        ]
        return "\n".join(lines)


# Behavioural parameters that are part of a contract's meaning but not of its
# signature (type, subject, predicate, object).
CONTRACT_PARAMETER_KEYS = ("rc_threshold", "operator")


def contract_parameters(contract: Contract) -> tuple[tuple[str, Any], ...]:
    return tuple((k, contract.metadata.get(k)) for k in CONTRACT_PARAMETER_KEYS)


# ---------------------------------------------------------------------------
# BCG Diff
# ---------------------------------------------------------------------------

@dataclass
class BCGDiff:
    """
    Result of comparing two BCGs (original vs. modernized).

    preserved:  contracts present in both BCGs with equivalent state/confidence
                (behavioral preservation — these are not regression candidates)
    broken:     contracts in original but not in modernized
                (semantic regression candidates — obligation dropped)
    added:      contracts in modernized but not in original
                (new behavioral obligations introduced)
    modified:   contracts with same semantic signature (type/subject/predicate/object)
                in both BCGs but differing in validation_state or confidence score by > 5%
                (weakened or strengthened obligations — warrant human review)

    NOTE: 'broken' and 'modified' contracts are CANDIDATES for semantic regressions.
    They require validation (execution oracle, human review) to confirm regression.
    """
    preserved: list[Contract]
    broken: list[Contract]
    added: list[Contract]
    modified: list[tuple[Contract, Contract]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.modified is None:
            self.modified = []

    def regression_candidates(self) -> list[Contract]:
        """Broken contracts that were validated (not just STATIC_CANDIDATE)."""
        return [c for c in self.broken if c.is_validated()]

    def modified_regression_candidates(self) -> list[tuple[Contract, Contract]]:
        """Modified contracts where the original was validated and confidence dropped."""
        result = []
        for orig, mod in self.modified:
            if orig.is_validated() and orig.confidence_score() > mod.confidence_score():
                result.append((orig, mod))
        return result

    def summary(self) -> str:
        return (
            f"BCGDiff: preserved={len(self.preserved)}, "
            f"broken={len(self.broken)}, "
            f"added={len(self.added)}, "
            f"modified={len(self.modified)}\n"
            f"Regression candidates (validated broken): {len(self.regression_candidates())}\n"
            f"Modified regression candidates: {len(self.modified_regression_candidates())}"
        )
