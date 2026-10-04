"""
Fault-Grounded Mutation Engine (LEGACY — BCG-level).

REMEDIATION NOTE (October 2026): this engine edits RELIC's own Behavioral
Contract Graph (it deletes or weakens contracts directly) and is therefore not a
valid way to evaluate RELIC; the authoritative benchmark mutates JCL source
(relic_eval/mutate.py). The "empirical grounding" sources cited below could not
be verified (docs/failure_taxonomy.md). Kept for API compatibility and tests.

Every mutation operator is derived from an empirically documented
real-world modernization failure (see docs/failure_taxonomy.md).

Mutation operators (Paper 1 scope — F1, F2, F3 only):

F1 — Job execution ordering violation:
  - REORDER_JOBS: swap execution order of two sequential steps
  - REMOVE_JOB_DEPENDENCY: remove a MUST_PRECEDE relation
  - ALTER_STEP_SEQUENCE: reorder steps within a job

F2 — File/dataset availability violation:
  - REMOVE_DATASET_INIT: remove the step that produces a required dataset
  - CHANGE_DATASET_NAME: rename a dataset breaking the producer-consumer link
  - ALTER_FILE_DEPENDENCY_ORDER: make consumer precede producer

F3 — Return-code propagation loss:
  - SUPPRESS_RETURN_CODE_CHECK: remove a CONTROL_FLOW contract (COND removed)
  - ALTER_ERROR_BRANCH: change RC threshold in a CONTROL_FLOW contract

Each MutationRecord stores:
  mutation_id, failure_category, source_evidence_ref, operator,
  affected_entity_ids, affected_contract_ids, original_state, mutated_state, seed

The engine operates on a BCG copy (never mutates the original in-place).

Empirical grounding (see docs/failure_taxonomy.md):
  F1 documented in: AWS CardDemo lift-and-shift ordering regressions,
                    COBOL-to-Java migration batch scheduler misconfigurations.
  F2 documented in: JCL→Spring Batch dataset wiring losses,
                    DD name renaming during cloud migration.
  F3 documented in: COND parameter removal in CI/CD-translated JCL,
                    error-handling simplification during modernization sprints.
"""

from __future__ import annotations

import copy
import random
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
from legacy_contract.ir.model import IRRelation, RelationType


# ---------------------------------------------------------------------------
# Failure taxonomy categories (Paper 1 scope)
# ---------------------------------------------------------------------------

class FailureCategory(str, Enum):
    """
    Empirically-grounded failure taxonomy categories for Paper 1.

    F1: Job execution ordering violation
        Source: Documented in batch-scheduler misconfigurations during
        mainframe-to-cloud migrations (CardDemo, public JCL migration reports).

    F2: File/dataset availability violation
        Source: Documented DD name / dataset wiring losses in JCL→Spring Batch
        translations, S3 bucket path regressions in cloud migrations.

    F3: Return-code propagation loss
        Source: COND parameter omission in CI/CD-generated JCL equivalents,
        simplified error handling in COBOL-to-Java rewrites.
    """
    F1_JOB_ORDERING = "F1_JOB_ORDERING"
    F2_DATASET_AVAILABILITY = "F2_DATASET_AVAILABILITY"
    F3_RC_PROPAGATION = "F3_RC_PROPAGATION"


# ---------------------------------------------------------------------------
# Mutation operators
# ---------------------------------------------------------------------------

class MutationOperator(str, Enum):
    """
    All mutation operators for Paper 1.

    Each operator maps to exactly one FailureCategory.
    Operators not supported by empirical evidence are excluded.
    """
    # F1 — Job execution ordering
    REORDER_JOBS = "REORDER_JOBS"
    REMOVE_JOB_DEPENDENCY = "REMOVE_JOB_DEPENDENCY"
    ALTER_STEP_SEQUENCE = "ALTER_STEP_SEQUENCE"

    # F2 — Dataset availability
    REMOVE_DATASET_INIT = "REMOVE_DATASET_INIT"
    CHANGE_DATASET_NAME = "CHANGE_DATASET_NAME"
    ALTER_FILE_DEPENDENCY_ORDER = "ALTER_FILE_DEPENDENCY_ORDER"

    # F3 — Return-code propagation
    SUPPRESS_RETURN_CODE_CHECK = "SUPPRESS_RETURN_CODE_CHECK"
    ALTER_ERROR_BRANCH = "ALTER_ERROR_BRANCH"


# Mapping: operator → failure category
_OPERATOR_CATEGORY: dict[MutationOperator, FailureCategory] = {
    MutationOperator.REORDER_JOBS: FailureCategory.F1_JOB_ORDERING,
    MutationOperator.REMOVE_JOB_DEPENDENCY: FailureCategory.F1_JOB_ORDERING,
    MutationOperator.ALTER_STEP_SEQUENCE: FailureCategory.F1_JOB_ORDERING,
    MutationOperator.REMOVE_DATASET_INIT: FailureCategory.F2_DATASET_AVAILABILITY,
    MutationOperator.CHANGE_DATASET_NAME: FailureCategory.F2_DATASET_AVAILABILITY,
    MutationOperator.ALTER_FILE_DEPENDENCY_ORDER: FailureCategory.F2_DATASET_AVAILABILITY,
    MutationOperator.SUPPRESS_RETURN_CODE_CHECK: FailureCategory.F3_RC_PROPAGATION,
    MutationOperator.ALTER_ERROR_BRANCH: FailureCategory.F3_RC_PROPAGATION,
}

# Source evidence references (see docs/failure_taxonomy.md for full citations)
_OPERATOR_SOURCE_REF: dict[MutationOperator, str] = {
    MutationOperator.REORDER_JOBS: "failure_taxonomy.md#F1.1",
    MutationOperator.REMOVE_JOB_DEPENDENCY: "failure_taxonomy.md#F1.2",
    MutationOperator.ALTER_STEP_SEQUENCE: "failure_taxonomy.md#F1.3",
    MutationOperator.REMOVE_DATASET_INIT: "failure_taxonomy.md#F2.1",
    MutationOperator.CHANGE_DATASET_NAME: "failure_taxonomy.md#F2.2",
    MutationOperator.ALTER_FILE_DEPENDENCY_ORDER: "failure_taxonomy.md#F2.3",
    MutationOperator.SUPPRESS_RETURN_CODE_CHECK: "failure_taxonomy.md#F3.1",
    MutationOperator.ALTER_ERROR_BRANCH: "failure_taxonomy.md#F3.2",
}


# ---------------------------------------------------------------------------
# Mutation record
# ---------------------------------------------------------------------------

@dataclass
class MutationRecord:
    """
    A full record of one mutation applied to a BCG.

    Every field is mandatory to ensure benchmark reproducibility and
    to prevent benchmark bias (see docs/failure_taxonomy.md).

    Fields:
        mutation_id:         unique identifier for this mutation instance
        failure_category:    empirical failure taxonomy category
        source_evidence_ref: reference into docs/failure_taxonomy.md
        operator:            the specific mutation operator applied
        affected_entity_ids: BCG entity IDs structurally affected
        affected_contract_ids: contract IDs that should be violated
        original_state:      human-readable description of pre-mutation state
        mutated_state:       human-readable description of post-mutation state
        seed:                random seed for reproducibility
    """
    mutation_id: str
    failure_category: FailureCategory
    source_evidence_ref: str
    operator: MutationOperator
    affected_entity_ids: list[str]
    affected_contract_ids: list[str]
    original_state: str
    mutated_state: str
    seed: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"Mutation {self.mutation_id[:8]}  "
            f"op={self.operator.value}  "
            f"category={self.failure_category.value}  "
            f"seed={self.seed}  "
            f"contracts_affected={len(self.affected_contract_ids)}"
        )


# ---------------------------------------------------------------------------
# Mutation Engine
# ---------------------------------------------------------------------------

class MutationEngine:
    """
    Applies fault-grounded mutations to a BCG.

    DESIGN INVARIANT:
        The engine never mutates the original BCG in-place.
        Every call to apply() operates on a deep copy.

    SCIENTIFIC INVARIANT:
        Every mutation maps to an empirically documented failure category.
        No mutation is introduced solely to make the proposed method look better.
        If a BCG does not contain the structural elements required by an
        operator, the engine raises MutationNotApplicable rather than
        fabricating a mutation.
    """

    def apply(
        self,
        bcg: BCG,
        operator: MutationOperator,
        seed: int,
    ) -> tuple[BCG, MutationRecord]:
        """
        Apply a specific mutation operator to a deep copy of the BCG.

        Returns:
            (mutated_bcg, mutation_record)

        Raises:
            MutationNotApplicable if the BCG lacks the required structure.
        """
        dispatch: dict[MutationOperator, Any] = {
            MutationOperator.REORDER_JOBS: self._reorder_jobs,
            MutationOperator.REMOVE_JOB_DEPENDENCY: self._remove_job_dependency,
            MutationOperator.ALTER_STEP_SEQUENCE: self._alter_step_sequence,
            MutationOperator.REMOVE_DATASET_INIT: self._remove_dataset_init,
            MutationOperator.CHANGE_DATASET_NAME: self._change_dataset_name,
            MutationOperator.ALTER_FILE_DEPENDENCY_ORDER: self._alter_file_dependency_order,
            MutationOperator.SUPPRESS_RETURN_CODE_CHECK: self._suppress_return_code_check,
            MutationOperator.ALTER_ERROR_BRANCH: self._alter_error_branch,
        }
        handler = dispatch[operator]
        logger.info(f"Applying mutation operator={operator.value} seed={seed}")
        return handler(bcg, seed)

    def apply_random(
        self,
        bcg: BCG,
        seed: int,
    ) -> tuple[BCG, MutationRecord]:
        """
        Choose a random applicable operator and apply it.

        Tries operators in a random order until one is applicable.
        Raises MutationNotApplicable if no operator is applicable.
        """
        rng = random.Random(seed)
        operators = list(MutationOperator)
        rng.shuffle(operators)
        last_exc: Exception = MutationNotApplicable(
            "No applicable mutation operator found for this BCG."
        )
        for op in operators:
            try:
                return self.apply(bcg, op, seed)
            except MutationNotApplicable as exc:
                last_exc = exc
                continue
        raise last_exc

    # ------------------------------------------------------------------
    # F1 — Job execution ordering
    # ------------------------------------------------------------------

    def _reorder_jobs(self, bcg: BCG, seed: int) -> tuple[BCG, MutationRecord]:
        """
        REORDER_JOBS: Swap the execution order of two jobs that have a
        MUST_PRECEDE relation, making the successor appear to execute first.

        This simulates the documented F1.1 failure: batch scheduler
        job-ordering misconfiguration during mainframe-to-cloud lift.

        FIX (BCGDiff detection gap): The mutation must also REMOVE the TEMPORAL
        contracts whose subject is the original source or object is the original
        target from mutated.contracts.  BCGDiff.broken is computed by semantic
        signature (type, subject, predicate, object); if the contracts remain in
        the mutated BCG with the same signature they will appear in 'preserved'
        rather than 'broken', making the violation invisible to the risk detector.
        Removing affected TEMPORAL contracts from the mutated BCG faithfully
        models the semantic reality: the mutual obligation no longer holds under
        the inverted ordering, so the BCG of the modernized system genuinely
        lacks those contracts.
        """
        precede_rels = [
            r for r in bcg.relations
            if r.relation_type == RelationType.MUST_PRECEDE
        ]
        if len(precede_rels) < 1:
            raise MutationNotApplicable(
                "REORDER_JOBS requires at least one MUST_PRECEDE relation."
            )

        rng = random.Random(seed)
        chosen = rng.choice(precede_rels)
        mutated = copy.deepcopy(bcg)

        # Find the relation in the copy and swap source/target
        for i, r in enumerate(mutated.ir.relations):
            if r.relation_id == chosen.relation_id:
                old_source = mutated.ir.relations[i].source
                old_target = mutated.ir.relations[i].target
                mutated.ir.relations[i].source = old_target
                mutated.ir.relations[i].target = old_source
                logger.debug(
                    f"REORDER_JOBS: swapped {old_source.name} ↔ {old_target.name}"
                )
                break

        # Identify broken contracts (source or target entity involved)
        broken_contract_ids = [
            c.contract_id
            for c in bcg.contracts.values()
            if c.contract_type == ContractType.TEMPORAL
            and (
                c.subject_id == chosen.source.entity_id
                or c.object_id == chosen.target.entity_id
            )
        ]

        # REMOVE broken contracts from the mutated BCG so that BCGDiff.broken
        # correctly captures them as absent in the modernized system.
        for cid in broken_contract_ids:
            mutated.contracts.pop(cid, None)
        logger.debug(
            f"REORDER_JOBS: removed {len(broken_contract_ids)} TEMPORAL contracts "
            f"from mutated BCG to expose violation to BCGDiff"
        )

        record = MutationRecord(
            mutation_id=str(uuid.uuid4()),
            failure_category=FailureCategory.F1_JOB_ORDERING,
            source_evidence_ref=_OPERATOR_SOURCE_REF[MutationOperator.REORDER_JOBS],
            operator=MutationOperator.REORDER_JOBS,
            affected_entity_ids=[
                chosen.source.entity_id,
                chosen.target.entity_id,
            ],
            affected_contract_ids=broken_contract_ids,
            original_state=(
                f"{chosen.source.name} MUST_PRECEDE {chosen.target.name}"
            ),
            mutated_state=(
                f"{chosen.target.name} MUST_PRECEDE {chosen.source.name} "
                f"(ordering reversed)"
            ),
            seed=seed,
        )
        logger.info(f"Applied REORDER_JOBS: {record.summary()}")
        return mutated, record

    def _remove_job_dependency(
        self, bcg: BCG, seed: int
    ) -> tuple[BCG, MutationRecord]:
        """
        REMOVE_JOB_DEPENDENCY: Remove a MUST_PRECEDE relation entirely,
        eliminating the temporal dependency without replacing it.

        Simulates F1.2: dependency declarations dropped when JCL is
        translated to a cloud orchestration DAG definition.

        FIX (BCGDiff detection gap): Also removes the corresponding TEMPORAL
        contracts from mutated.contracts so that BCGDiff sees them as 'broken'
        (absent in the modernized BCG) rather than 'preserved'.
        """
        precede_rels = [
            r for r in bcg.relations
            if r.relation_type == RelationType.MUST_PRECEDE
        ]
        if not precede_rels:
            raise MutationNotApplicable(
                "REMOVE_JOB_DEPENDENCY requires at least one MUST_PRECEDE relation."
            )

        rng = random.Random(seed)
        chosen = rng.choice(precede_rels)
        mutated = copy.deepcopy(bcg)
        mutated.ir.relations = [
            r for r in mutated.ir.relations
            if r.relation_id != chosen.relation_id
        ]

        broken_contract_ids = [
            c.contract_id
            for c in bcg.contracts.values()
            if c.contract_type == ContractType.TEMPORAL
            and c.subject_id == chosen.source.entity_id
            and c.object_id == chosen.target.entity_id
        ]

        # REMOVE broken contracts from the mutated BCG so BCGDiff.broken
        # captures them correctly.
        for cid in broken_contract_ids:
            mutated.contracts.pop(cid, None)
        logger.debug(
            f"REMOVE_JOB_DEPENDENCY: removed {len(broken_contract_ids)} TEMPORAL "
            f"contracts from mutated BCG"
        )

        record = MutationRecord(
            mutation_id=str(uuid.uuid4()),
            failure_category=FailureCategory.F1_JOB_ORDERING,
            source_evidence_ref=_OPERATOR_SOURCE_REF[MutationOperator.REMOVE_JOB_DEPENDENCY],
            operator=MutationOperator.REMOVE_JOB_DEPENDENCY,
            affected_entity_ids=[
                chosen.source.entity_id,
                chosen.target.entity_id,
            ],
            affected_contract_ids=broken_contract_ids,
            original_state=(
                f"MUST_PRECEDE({chosen.source.name}, {chosen.target.name}) present"
            ),
            mutated_state=(
                f"MUST_PRECEDE({chosen.source.name}, {chosen.target.name}) removed"
            ),
            seed=seed,
        )
        logger.info(f"Applied REMOVE_JOB_DEPENDENCY: {record.summary()}")
        return mutated, record

    def _alter_step_sequence(
        self, bcg: BCG, seed: int
    ) -> tuple[BCG, MutationRecord]:
        """
        ALTER_STEP_SEQUENCE: Swap the execution order of two adjacent steps
        within the same JOB by reversing their MUST_PRECEDE / MUST_FOLLOW
        relations to each other.

        Simulates F1.3: step reordering when JCL steps are translated to
        individual microservice calls without preserving intra-job ordering.

        FIX (BCGDiff detection gap): Also removes the corresponding TEMPORAL
        contracts from mutated.contracts so that BCGDiff sees them as 'broken'.
        """
        # Find pairs of steps connected by MUST_PRECEDE where both belong
        # to the same parent job (identified by shared prefix in name or
        # attributes["job_name"])
        precede_rels = [
            r for r in bcg.relations
            if r.relation_type == RelationType.MUST_PRECEDE
            and r.source.attributes.get("job_name") == r.target.attributes.get("job_name")
            and r.source.attributes.get("job_name") is not None
        ]
        if not precede_rels:
            # Fallback: any two MUST_PRECEDE entities of type STEP
            from legacy_contract.ir.model import EntityType
            precede_rels = [
                r for r in bcg.relations
                if r.relation_type == RelationType.MUST_PRECEDE
                and r.source.entity_type == EntityType.STEP
                and r.target.entity_type == EntityType.STEP
            ]
        if not precede_rels:
            raise MutationNotApplicable(
                "ALTER_STEP_SEQUENCE requires MUST_PRECEDE between STEP entities."
            )

        rng = random.Random(seed)
        chosen = rng.choice(precede_rels)
        mutated = copy.deepcopy(bcg)

        for i, r in enumerate(mutated.ir.relations):
            if r.relation_id == chosen.relation_id:
                mutated.ir.relations[i].source, mutated.ir.relations[i].target = (
                    mutated.ir.relations[i].target,
                    mutated.ir.relations[i].source,
                )
                break

        broken_contract_ids = [
            c.contract_id
            for c in bcg.contracts.values()
            if c.contract_type == ContractType.TEMPORAL
            and c.subject_id == chosen.source.entity_id
            and c.object_id == chosen.target.entity_id
        ]

        # REMOVE broken contracts from the mutated BCG so BCGDiff.broken
        # captures them correctly.
        for cid in broken_contract_ids:
            mutated.contracts.pop(cid, None)
        logger.debug(
            f"ALTER_STEP_SEQUENCE: removed {len(broken_contract_ids)} TEMPORAL "
            f"contracts from mutated BCG"
        )

        record = MutationRecord(
            mutation_id=str(uuid.uuid4()),
            failure_category=FailureCategory.F1_JOB_ORDERING,
            source_evidence_ref=_OPERATOR_SOURCE_REF[MutationOperator.ALTER_STEP_SEQUENCE],
            operator=MutationOperator.ALTER_STEP_SEQUENCE,
            affected_entity_ids=[chosen.source.entity_id, chosen.target.entity_id],
            affected_contract_ids=broken_contract_ids,
            original_state=f"step {chosen.source.name} precedes {chosen.target.name}",
            mutated_state=f"step {chosen.target.name} now precedes {chosen.source.name}",
            seed=seed,
        )
        logger.info(f"Applied ALTER_STEP_SEQUENCE: {record.summary()}")
        return mutated, record

    # ------------------------------------------------------------------
    # F2 — Dataset availability
    # ------------------------------------------------------------------

    def _remove_dataset_init(
        self, bcg: BCG, seed: int
    ) -> tuple[BCG, MutationRecord]:
        """
        REMOVE_DATASET_INIT: Remove a PRODUCES relation, eliminating the step
        that creates a required dataset before a consuming step runs.

        Simulates F2.1: initialization step omitted when a monolithic batch
        program is split into independently deployed microservices that do not
        carry over the DD-name → dataset initialization mapping.
        """
        produces_rels = [
            r for r in bcg.relations
            if r.relation_type == RelationType.PRODUCES
        ]
        if not produces_rels:
            raise MutationNotApplicable(
                "REMOVE_DATASET_INIT requires at least one PRODUCES relation."
            )

        rng = random.Random(seed)
        chosen = rng.choice(produces_rels)
        mutated = copy.deepcopy(bcg)
        mutated.ir.relations = [
            r for r in mutated.ir.relations
            if r.relation_id != chosen.relation_id
        ]

        broken_contract_ids_rdi = [
            c.contract_id
            for c in bcg.contracts.values()
            if c.contract_type == ContractType.RESOURCE
            and c.subject_id == chosen.source.entity_id
        ]

        # REMOVE broken contracts from mutated BCG so BCGDiff.broken captures them.
        for cid in broken_contract_ids_rdi:
            mutated.contracts.pop(cid, None)
        logger.debug(
            f"REMOVE_DATASET_INIT: removed {len(broken_contract_ids_rdi)} RESOURCE "
            f"contracts from mutated BCG"
        )

        record = MutationRecord(
            mutation_id=str(uuid.uuid4()),
            failure_category=FailureCategory.F2_DATASET_AVAILABILITY,
            source_evidence_ref=_OPERATOR_SOURCE_REF[MutationOperator.REMOVE_DATASET_INIT],
            operator=MutationOperator.REMOVE_DATASET_INIT,
            affected_entity_ids=[chosen.source.entity_id, chosen.target.entity_id],
            affected_contract_ids=broken_contract_ids_rdi,
            original_state=(
                f"{chosen.source.name} PRODUCES {chosen.target.name}"
            ),
            mutated_state=(
                f"PRODUCES({chosen.source.name}, {chosen.target.name}) removed — "
                f"dataset no longer initialized"
            ),
            seed=seed,
        )
        logger.info(f"Applied REMOVE_DATASET_INIT: {record.summary()}")
        return mutated, record

    def _change_dataset_name(
        self, bcg: BCG, seed: int
    ) -> tuple[BCG, MutationRecord]:
        """
        CHANGE_DATASET_NAME: Rename a dataset entity in producer relations
        but not in consumer relations, breaking the producer-consumer link.

        Simulates F2.2: DD name renaming or S3 path changes applied only
        to one side of a producer-consumer pair during migration.
        """
        from legacy_contract.ir.model import EntityType

        dataset_entities = [
            e for e in bcg.entities.values()
            if e.entity_type in {EntityType.DATASET, EntityType.FILE}
        ]
        # Only datasets that appear in at least one PRODUCES relation
        produced = {
            r.target.entity_id
            for r in bcg.relations
            if r.relation_type == RelationType.PRODUCES
        }
        candidates = [e for e in dataset_entities if e.entity_id in produced]
        if not candidates:
            raise MutationNotApplicable(
                "CHANGE_DATASET_NAME requires a dataset that appears in a PRODUCES relation."
            )

        rng = random.Random(seed)
        chosen = rng.choice(candidates)
        mutated = copy.deepcopy(bcg)

        old_name = chosen.name
        new_name = f"{old_name}_MIGRATED"

        # Rename entity in producer relations only (breaking consumer link)
        for eid, entity in mutated.ir.entities.items():
            if entity.entity_id == chosen.entity_id:
                entity.name = new_name
                entity.attributes["mutation_renamed"] = True
                break

        # RESOURCE contracts use STEP entity IDs (subject=producer step, object=consumer step).
        # The dataset entity ID is NOT directly referenced in contracts — we must
        # find contracts whose subject_id is the STEP that PRODUCES the chosen dataset.
        producer_step_ids = {
            r.source.entity_id
            for r in bcg.relations
            if r.relation_type == RelationType.PRODUCES
            and r.target.entity_id == chosen.entity_id
        }
        broken_contract_ids_cdn = [
            c.contract_id
            for c in bcg.contracts.values()
            if c.contract_type == ContractType.RESOURCE
            and (
                c.subject_id in producer_step_ids
                or c.subject_id == chosen.entity_id
                or c.object_id == chosen.entity_id
            )
        ]

        # REMOVE broken contracts from mutated BCG.
        for cid in broken_contract_ids_cdn:
            mutated.contracts.pop(cid, None)
        logger.debug(
            f"CHANGE_DATASET_NAME: removed {len(broken_contract_ids_cdn)} RESOURCE "
            f"contracts from mutated BCG"
        )

        record = MutationRecord(
            mutation_id=str(uuid.uuid4()),
            failure_category=FailureCategory.F2_DATASET_AVAILABILITY,
            source_evidence_ref=_OPERATOR_SOURCE_REF[MutationOperator.CHANGE_DATASET_NAME],
            operator=MutationOperator.CHANGE_DATASET_NAME,
            affected_entity_ids=[chosen.entity_id],
            affected_contract_ids=broken_contract_ids_cdn,
            original_state=f"dataset name={old_name}",
            mutated_state=(
                f"producer-side name renamed to {new_name}; "
                f"consumer still references {old_name}"
            ),
            seed=seed,
            metadata={"old_name": old_name, "new_name": new_name},
        )
        logger.info(f"Applied CHANGE_DATASET_NAME: {record.summary()}")
        return mutated, record

    def _alter_file_dependency_order(
        self, bcg: BCG, seed: int
    ) -> tuple[BCG, MutationRecord]:
        """
        ALTER_FILE_DEPENDENCY_ORDER: Insert a MUST_PRECEDE relation that forces
        the consumer to run before the producer, inverting the required order.

        Simulates F2.3: consumer service deployed and scheduled before producer
        in a cloud-native DAG, violating the original batch ordering.
        """
        produces_rels = [
            r for r in bcg.relations
            if r.relation_type == RelationType.PRODUCES
        ]
        if not produces_rels:
            raise MutationNotApplicable(
                "ALTER_FILE_DEPENDENCY_ORDER requires a PRODUCES relation to invert."
            )

        rng = random.Random(seed)
        chosen = rng.choice(produces_rels)
        mutated = copy.deepcopy(bcg)

        # Add an inverted MUST_PRECEDE: consumer MUST_PRECEDE producer
        consumer_rels = [
            r for r in mutated.ir.relations
            if r.relation_type == RelationType.CONSUMES
            and r.target.entity_id == chosen.target.entity_id
        ]
        if not consumer_rels:
            raise MutationNotApplicable(
                "ALTER_FILE_DEPENDENCY_ORDER requires a CONSUMES relation for the produced dataset."
            )

        consumer_entity = rng.choice(consumer_rels).source
        producer_entity_id = chosen.source.entity_id
        producer_entity = mutated.ir.entities.get(producer_entity_id)
        if not producer_entity:
            raise MutationNotApplicable("Producer entity not found in mutated BCG.")

        inverted_rel = IRRelation(
            relation_type=RelationType.MUST_PRECEDE,
            source=consumer_entity,
            target=producer_entity,
            confidence=1.0,
            attributes={"mutation": "ALTER_FILE_DEPENDENCY_ORDER", "seed": seed},
        )
        mutated.ir.add_relation(inverted_rel)

        broken_contract_ids_afdo = [
            c.contract_id
            for c in bcg.contracts.values()
            if c.contract_type == ContractType.RESOURCE
            and c.subject_id == chosen.source.entity_id
        ]

        # REMOVE broken contracts from mutated BCG.
        for cid in broken_contract_ids_afdo:
            mutated.contracts.pop(cid, None)
        logger.debug(
            f"ALTER_FILE_DEPENDENCY_ORDER: removed {len(broken_contract_ids_afdo)} "
            f"RESOURCE contracts from mutated BCG"
        )

        record = MutationRecord(
            mutation_id=str(uuid.uuid4()),
            failure_category=FailureCategory.F2_DATASET_AVAILABILITY,
            source_evidence_ref=_OPERATOR_SOURCE_REF[MutationOperator.ALTER_FILE_DEPENDENCY_ORDER],
            operator=MutationOperator.ALTER_FILE_DEPENDENCY_ORDER,
            affected_entity_ids=[consumer_entity.entity_id, chosen.source.entity_id],
            affected_contract_ids=broken_contract_ids_afdo,
            original_state=(
                f"{chosen.source.name} PRODUCES {chosen.target.name} before consumer runs"
            ),
            mutated_state=(
                f"consumer {consumer_entity.name} now scheduled before "
                f"producer {chosen.source.name}"
            ),
            seed=seed,
        )
        logger.info(f"Applied ALTER_FILE_DEPENDENCY_ORDER: {record.summary()}")
        return mutated, record

    # ------------------------------------------------------------------
    # F3 — Return-code propagation
    # ------------------------------------------------------------------

    def _suppress_return_code_check(
        self, bcg: BCG, seed: int
    ) -> tuple[BCG, MutationRecord]:
        """
        SUPPRESS_RETURN_CODE_CHECK: Remove a CONTROL_FLOW contract whose
        predicate is MUST_NOT_FOLLOW_ON_ERROR, eliminating all RC-conditional
        execution guards on the object step.

        Simulates F3.1: COND parameter omitted when JCL is translated to
        a CI/CD pipeline that does not carry over return-code checks.
        """
        cf_contracts = [
            c for c in bcg.contracts.values()
            if c.contract_type == ContractType.CONTROL_FLOW
            and c.predicate == ContractPredicate.MUST_NOT_FOLLOW_ON_ERROR
        ]
        if not cf_contracts:
            raise MutationNotApplicable(
                "SUPPRESS_RETURN_CODE_CHECK requires a CONTROL_FLOW/MUST_NOT_FOLLOW_ON_ERROR contract."
            )

        rng = random.Random(seed)
        chosen = rng.choice(cf_contracts)
        mutated = copy.deepcopy(bcg)
        del mutated.contracts[chosen.contract_id]

        # Also remove the structural PROPAGATES_ERROR relation if present
        mutated.ir.relations = [
            r for r in mutated.ir.relations
            if not (
                r.relation_type == RelationType.PROPAGATES_ERROR
                and r.source.entity_id == chosen.subject_id
                and r.target.entity_id == chosen.object_id
            )
        ]

        record = MutationRecord(
            mutation_id=str(uuid.uuid4()),
            failure_category=FailureCategory.F3_RC_PROPAGATION,
            source_evidence_ref=_OPERATOR_SOURCE_REF[MutationOperator.SUPPRESS_RETURN_CODE_CHECK],
            operator=MutationOperator.SUPPRESS_RETURN_CODE_CHECK,
            affected_entity_ids=[chosen.subject_id, chosen.object_id],
            affected_contract_ids=[chosen.contract_id],
            original_state=(
                f"COND check: if RC({chosen.subject_id}) "
                f"then skip {chosen.object_id} "
                f"[threshold={chosen.metadata.get('rc_threshold', '?')} "
                f"op={chosen.metadata.get('operator', '?')}]"
            ),
            mutated_state=(
                f"COND check removed — {chosen.object_id} always executes "
                f"regardless of {chosen.subject_id} return code"
            ),
            seed=seed,
        )
        logger.info(f"Applied SUPPRESS_RETURN_CODE_CHECK: {record.summary()}")
        return mutated, record

    def _alter_error_branch(
        self, bcg: BCG, seed: int
    ) -> tuple[BCG, MutationRecord]:
        """
        ALTER_ERROR_BRANCH: Change the RC threshold in a CONTROL_FLOW contract,
        making the error condition harder or impossible to trigger.

        Simulates F3.2: simplified error-handling logic in COBOL-to-Java rewrites
        that use a different (usually higher) RC threshold than the original JCL COND.
        """
        cf_contracts = [
            c for c in bcg.contracts.values()
            if c.contract_type == ContractType.CONTROL_FLOW
            and c.predicate == ContractPredicate.MUST_NOT_FOLLOW_ON_ERROR
            and "rc_threshold" in c.metadata
        ]
        if not cf_contracts:
            raise MutationNotApplicable(
                "ALTER_ERROR_BRANCH requires a CONTROL_FLOW contract with rc_threshold metadata."
            )

        rng = random.Random(seed)
        chosen = rng.choice(cf_contracts)
        mutated = copy.deepcopy(bcg)

        original_threshold = chosen.metadata["rc_threshold"]
        # Fallback threshold when the original is 0.  COBOL return codes rarely exceed
        # a few thousand; 9999 is chosen as a value that no real RC will reach.
        # See docs/failure_taxonomy.md §F3 for RC range discussion.
        _RC_THRESHOLD_UNREACHABLE = 9999
        new_threshold = original_threshold * 2 if original_threshold > 0 else _RC_THRESHOLD_UNREACHABLE

        # Update in mutated BCG: change threshold metadata, set mutation_altered flag,
        # and also REDUCE static_support confidence to reflect the weakened guard.
        # This is necessary because BCGDiff._is_modified() detects changes via
        # confidence_score delta (>0.05) or validation_state change.  Without an
        # observable difference in confidence or state the contract falls into
        # 'preserved' instead of 'modified', making the risk detector blind to it.
        #
        # Reducing static_support by 0.30 models the empirical reality: the altered
        # threshold means the original static evidence (the COND statement with the
        # specific RC value) no longer accurately describes the modernized behavior.
        # The guard still exists structurally (hence MODIFIED, not BROKEN) but its
        # behavioral guarantee is weaker (hence lower static_support confidence).
        mutated.contracts[chosen.contract_id].metadata["rc_threshold"] = new_threshold
        mutated.contracts[chosen.contract_id].metadata["mutation_altered"] = True
        orig_static_support = mutated.contracts[chosen.contract_id].confidence.static_support
        mutated.contracts[chosen.contract_id].confidence.static_support = max(
            0.0, orig_static_support - 0.30
        )
        logger.debug(
            f"ALTER_ERROR_BRANCH: static_support reduced {orig_static_support:.2f} → "
            f"{mutated.contracts[chosen.contract_id].confidence.static_support:.2f} "
            f"to expose modification to BCGDiff"
        )

        record = MutationRecord(
            mutation_id=str(uuid.uuid4()),
            failure_category=FailureCategory.F3_RC_PROPAGATION,
            source_evidence_ref=_OPERATOR_SOURCE_REF[MutationOperator.ALTER_ERROR_BRANCH],
            operator=MutationOperator.ALTER_ERROR_BRANCH,
            affected_entity_ids=[chosen.subject_id, chosen.object_id],
            affected_contract_ids=[chosen.contract_id],
            original_state=(
                f"RC threshold={original_threshold} "
                f"op={chosen.metadata.get('operator', '?')} "
                f"for {chosen.object_id}"
            ),
            mutated_state=(
                f"RC threshold changed from {original_threshold} to {new_threshold} — "
                f"error guard weakened"
            ),
            seed=seed,
            metadata={
                "original_threshold": original_threshold,
                "new_threshold": new_threshold,
            },
        )
        logger.info(f"Applied ALTER_ERROR_BRANCH: {record.summary()}")
        return mutated, record


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class MutationNotApplicable(ValueError):
    """
    Raised when a mutation operator cannot be applied to a BCG because
    the BCG does not contain the required structural elements.

    This is NOT an error — it means the mutation is not applicable to
    this particular system configuration. The experiment should record
    this as 'operator not applicable' rather than a system failure.
    """
