"""
Semantically-Preserving Negative Mutation Engine.

This module implements mutation operators that do NOT violate behavioral contracts.
These mutations are structural/label changes with zero semantic contract effect and
serve as the ground-truth TN (true negative) set for H3 FPR baseline construction.

Design principles:
  - All 5 operators are provably semantically preserving (documented in docstrings)
  - Each operator applies to a BCG deep copy (never in-place)
  - Applicability is guarded: raises ValueError when not applicable rather than
    silently creating a non-semantics-preserving mutation
  - NegativeMutationRecord.expected_detection is always False

Scientific purpose:
  FPR = FP / (FP + TN)

  The existing mutation benchmark is closed-set (all 109 mutations violate contracts),
  making FP=0 and FPR undefined. By generating ~50 TN cases using these operators,
  H3 FPR reduction becomes testable without fabricating data or importing external GT.

IMPORTANT: Do not use these operators to manufacture artificial TN results.
Every negative mutation must be applied to a REAL CardDemo BCG and the
BCGDiff result (expected: no broken/modified contracts) must be verified.
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
from legacy_contract.ir.model import EntityType, IREntity, IRRelation, RelationType


# ---------------------------------------------------------------------------
# Negative Mutation Operators
# ---------------------------------------------------------------------------

class NegativeOperator(str, Enum):
    """
    Semantically-preserving mutation operators.

    None of these operators add, remove, or alter any behavioral contract.
    BCGDiff.broken and BCGDiff.modified MUST be empty on every application.
    """
    RENAME_STEP_COMMENT = "RENAME_STEP_COMMENT"
    ADD_REDUNDANT_DEPENDENCY = "ADD_REDUNDANT_DEPENDENCY"
    REORDER_INDEPENDENT_STEPS = "REORDER_INDEPENDENT_STEPS"
    CHANGE_ACCOUNTING_PARAMETERS = "CHANGE_ACCOUNTING_PARAMETERS"
    RENAME_PROC_LABEL = "RENAME_PROC_LABEL"


# ---------------------------------------------------------------------------
# Negative Mutation Record
# ---------------------------------------------------------------------------

@dataclass
class NegativeMutationRecord:
    """
    Record of a semantically-preserving mutation applied to a BCG.
    expected_detection is always False — BCGDiff MUST NOT fire on these.
    """
    mutation_id: str
    operator: NegativeOperator
    category: str = "NEGATIVE_SEMANTICS_PRESERVING"
    source_bcg_id: str = ""
    expected_detection: bool = False   # INVARIANT: always False
    seed: int = 0
    description: str = ""
    affected_entity_ids: list[str] = field(default_factory=list)
    original_state: str = ""
    mutated_state: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.expected_detection is not False:
            raise ValueError(
                "NegativeMutationRecord.expected_detection must be False. "
                "Use MutationRecord (engine.py) for contract-violating mutations."
            )

    def summary(self) -> str:
        return (
            f"NegativeMutation {self.mutation_id[:8]}  "
            f"op={self.operator.value}  "
            f"expected_detection={self.expected_detection}  "
            f"seed={self.seed}"
        )


# ---------------------------------------------------------------------------
# Negative Mutation Engine
# ---------------------------------------------------------------------------

class NegativeMutationEngine:
    """
    Applies semantically-preserving mutations to a BCG copy.

    DESIGN INVARIANT: Every mutation preserves all behavioral contracts.
    BCGDiff.broken == [] and BCGDiff.modified == [] on every output.

    Usage:
        engine = NegativeMutationEngine()
        mutated_bcg, record = engine.apply(bcg, NegativeOperator.RENAME_STEP_COMMENT, seed=42)
        assert record.expected_detection == False
        diff = original_bcg.diff(mutated_bcg)
        assert len(diff.broken) == 0
        assert len(diff.modified) == 0
    """

    def apply(
        self,
        bcg: BCG,
        operator: NegativeOperator,
        seed: int,
    ) -> tuple[BCG, NegativeMutationRecord]:
        """
        Apply a semantically-preserving mutation to a BCG deep copy.

        Returns:
            (mutated_bcg, record)  — both always produced together

        Raises:
            ValueError if the BCG lacks the required structure for this operator.
        """
        dispatch = {
            NegativeOperator.RENAME_STEP_COMMENT: self._rename_step_comment,
            NegativeOperator.ADD_REDUNDANT_DEPENDENCY: self._add_redundant_dependency,
            NegativeOperator.REORDER_INDEPENDENT_STEPS: self._reorder_independent_steps,
            NegativeOperator.CHANGE_ACCOUNTING_PARAMETERS: self._change_accounting_parameters,
            NegativeOperator.RENAME_PROC_LABEL: self._rename_proc_label,
        }
        return dispatch[operator](bcg, seed)

    # ------------------------------------------------------------------
    # Operator 1: RENAME_STEP_COMMENT
    # ------------------------------------------------------------------

    def _rename_step_comment(self, bcg: BCG, seed: int) -> tuple[BCG, NegativeMutationRecord]:
        """
        Change a JCL step comment attribute.

        WHY SEMANTICALLY PRESERVING:
        JCL step comments are purely informational text.  They do not affect:
        - Step execution order (MUST_PRECEDE relations)
        - Resource availability (PRODUCES/CONSUMES relations)
        - Return-code propagation (CONTROL_FLOW contracts)
        BCGDiff uses (type, subject_id, predicate, object_id) as contract signature.
        Comments are not part of any contract dimension; no signature changes.
        """
        candidates = [
            e for e in bcg.entities.values()
            if e.entity_type == EntityType.STEP and "comment" in e.attributes
        ]
        if not candidates:
            raise ValueError(
                "RENAME_STEP_COMMENT requires at least one STEP entity with a "
                "'comment' attribute. BCG has none."
            )
        rng = random.Random(seed)
        chosen = rng.choice(candidates)
        old_comment = chosen.attributes.get("comment", "")

        mutated = copy.deepcopy(bcg)
        for entity in mutated.ir.entities.values():
            if entity.entity_id == chosen.entity_id:
                entity.attributes["comment"] = f"{old_comment}_RENAMED_{seed}"
                break

        return mutated, NegativeMutationRecord(
            mutation_id=str(uuid.uuid4()),
            operator=NegativeOperator.RENAME_STEP_COMMENT,
            source_bcg_id=bcg.bcg_id,
            seed=seed,
            description=f"Step '{chosen.name}' comment renamed. Zero behavioral effect.",
            affected_entity_ids=[chosen.entity_id],
            original_state=f"comment={old_comment!r}",
            mutated_state=f"comment='{old_comment}_RENAMED_{seed}'",
        )

    # ------------------------------------------------------------------
    # Operator 2: ADD_REDUNDANT_DEPENDENCY
    # ------------------------------------------------------------------

    def _add_redundant_dependency(self, bcg: BCG, seed: int) -> tuple[BCG, NegativeMutationRecord]:
        """
        Add A->B MUST_PRECEDE when A->B already exists (idempotent).

        WHY SEMANTICALLY PRESERVING:
        Adding a duplicate MUST_PRECEDE(A, B) when one already exists does not
        change the semantic ordering: B still must follow A.  IRGraph.add_relation()
        skips duplicates by relation_id hash, so no new relation is inserted.
        No contract signature (type, subject, predicate, object) changes.
        """
        precede_rels = [
            r for r in bcg.relations if r.relation_type == RelationType.MUST_PRECEDE
        ]
        if not precede_rels:
            raise ValueError(
                "ADD_REDUNDANT_DEPENDENCY requires at least one MUST_PRECEDE relation."
            )
        rng = random.Random(seed)
        chosen = rng.choice(precede_rels)

        mutated = copy.deepcopy(bcg)
        new_rel = IRRelation(
            relation_type=RelationType.MUST_PRECEDE,
            source=chosen.source,
            target=chosen.target,
            confidence=chosen.confidence,
            attributes={"negative_mutation": "ADD_REDUNDANT_DEPENDENCY", "seed": seed},
        )
        # add_relation skips by relation_id; same source+target+type → same hash → skipped
        mutated.ir.add_relation(new_rel)

        return mutated, NegativeMutationRecord(
            mutation_id=str(uuid.uuid4()),
            operator=NegativeOperator.ADD_REDUNDANT_DEPENDENCY,
            source_bcg_id=bcg.bcg_id,
            seed=seed,
            description=(
                f"Redundant MUST_PRECEDE({chosen.source.name},{chosen.target.name}) added. "
                "Idempotent — ordering semantics unchanged."
            ),
            affected_entity_ids=[chosen.source.entity_id, chosen.target.entity_id],
            original_state=f"MUST_PRECEDE({chosen.source.name},{chosen.target.name}) x1",
            mutated_state=f"MUST_PRECEDE({chosen.source.name},{chosen.target.name}) attempted x2 (skipped by graph)",
        )

    # ------------------------------------------------------------------
    # Operator 3: REORDER_INDEPENDENT_STEPS
    # ------------------------------------------------------------------

    def _reorder_independent_steps(self, bcg: BCG, seed: int) -> tuple[BCG, NegativeMutationRecord]:
        """
        Flag two steps that have NO ordering contract as cosmetically reordered.

        WHY SEMANTICALLY PRESERVING:
        If steps A and B have NO MUST_PRECEDE between them (independent), either
        execution order is behaviorally valid.  We add a metadata attribute flag;
        no contract (type, subject, predicate, object) is changed.
        """
        steps = [e for e in bcg.entities.values() if e.entity_type == EntityType.STEP]
        if len(steps) < 2:
            raise ValueError(
                "REORDER_INDEPENDENT_STEPS requires at least 2 STEP entities."
            )

        # Find a pair with NO MUST_PRECEDE between them in either direction
        rng = random.Random(seed)
        independent_pairs = []
        for i, s_a in enumerate(steps):
            for s_b in steps[i + 1:]:
                has_order = any(
                    r.relation_type == RelationType.MUST_PRECEDE
                    and (
                        (r.source.entity_id == s_a.entity_id and r.target.entity_id == s_b.entity_id)
                        or (r.source.entity_id == s_b.entity_id and r.target.entity_id == s_a.entity_id)
                    )
                    for r in bcg.relations
                )
                if not has_order:
                    independent_pairs.append((s_a, s_b))

        if not independent_pairs:
            raise ValueError(
                "REORDER_INDEPENDENT_STEPS: all step pairs have MUST_PRECEDE constraints; "
                "no independent pair found."
            )

        step_a, step_b = rng.choice(independent_pairs)
        mutated = copy.deepcopy(bcg)
        for entity in mutated.ir.entities.values():
            if entity.entity_id in {step_a.entity_id, step_b.entity_id}:
                entity.attributes["negative_reorder_flag"] = True

        return mutated, NegativeMutationRecord(
            mutation_id=str(uuid.uuid4()),
            operator=NegativeOperator.REORDER_INDEPENDENT_STEPS,
            source_bcg_id=bcg.bcg_id,
            seed=seed,
            description=(
                f"Independent steps {step_a.name} and {step_b.name} flagged as reordered. "
                "No MUST_PRECEDE exists between them; semantics unchanged."
            ),
            affected_entity_ids=[step_a.entity_id, step_b.entity_id],
            original_state=f"[{step_a.name}, {step_b.name}] original order",
            mutated_state=f"[{step_b.name}, {step_a.name}] cosmetic flag (no contract change)",
        )

    # ------------------------------------------------------------------
    # Operator 4: CHANGE_ACCOUNTING_PARAMETERS
    # ------------------------------------------------------------------

    def _change_accounting_parameters(self, bcg: BCG, seed: int) -> tuple[BCG, NegativeMutationRecord]:
        """
        Modify a JCL ACCT= or accounting attribute.

        WHY SEMANTICALLY PRESERVING:
        JCL accounting parameters (ACCT=) are billing/chargeback codes.
        They have zero effect on execution order, resource availability,
        or return-code propagation.  No contract references billing codes.
        """
        candidates = [
            e for e in bcg.entities.values()
            if e.entity_type in {EntityType.JOB, EntityType.STEP}
            and ("acct" in e.attributes or "accounting" in e.attributes)
        ]
        if not candidates:
            raise ValueError(
                "CHANGE_ACCOUNTING_PARAMETERS requires at least one JOB or STEP entity "
                "with an 'acct' or 'accounting' attribute."
            )
        rng = random.Random(seed)
        chosen = rng.choice(candidates)
        key = "acct" if "acct" in chosen.attributes else "accounting"
        old_val = chosen.attributes[key]

        mutated = copy.deepcopy(bcg)
        for entity in mutated.ir.entities.values():
            if entity.entity_id == chosen.entity_id:
                entity.attributes[key] = f"ACCT_NEG_MUTATION_{seed}"
                break

        return mutated, NegativeMutationRecord(
            mutation_id=str(uuid.uuid4()),
            operator=NegativeOperator.CHANGE_ACCOUNTING_PARAMETERS,
            source_bcg_id=bcg.bcg_id,
            seed=seed,
            description=(
                f"Accounting code for '{chosen.name}' changed. "
                "Billing metadata only; zero behavioral contract effect."
            ),
            affected_entity_ids=[chosen.entity_id],
            original_state=f"{key}={old_val!r}",
            mutated_state=f"{key}='ACCT_NEG_MUTATION_{seed}'",
        )

    # ------------------------------------------------------------------
    # Operator 5: RENAME_PROC_LABEL
    # ------------------------------------------------------------------

    def _rename_proc_label(self, bcg: BCG, seed: int) -> tuple[BCG, NegativeMutationRecord]:
        """
        Rename an internal PROC step label that no other step/contract references.

        WHY SEMANTICALLY PRESERVING:
        If a STEP entity is NOT the target of any MUST_PRECEDE relation AND is not
        the subject_id/object_id of any behavioral contract, renaming its name
        attribute has zero semantic effect.  All contract signatures
        (type, subject_id, predicate, object_id) use entity_id (deterministic hash),
        not the human-readable name — so renaming the name field cannot alter a
        contract signature.
        """
        steps = [e for e in bcg.entities.values() if e.entity_type == EntityType.STEP]
        if not steps:
            raise ValueError("RENAME_PROC_LABEL requires at least one STEP entity.")

        unreferenced = []
        for step in steps:
            # Check no MUST_PRECEDE targets this step
            is_target = any(
                r.target.entity_id == step.entity_id
                and r.relation_type == RelationType.MUST_PRECEDE
                for r in bcg.relations
            )
            # Check no contract references this step as subject or object
            in_contract = any(
                c.subject_id == step.entity_id or c.object_id == step.entity_id
                for c in bcg.contracts.values()
            )
            if not is_target and not in_contract:
                unreferenced.append(step)

        if not unreferenced:
            raise ValueError(
                "RENAME_PROC_LABEL: no unreferenced STEP entity found. "
                "All steps are either targets of MUST_PRECEDE or appear in contracts."
            )

        rng = random.Random(seed)
        chosen = rng.choice(unreferenced)
        old_name = chosen.name

        mutated = copy.deepcopy(bcg)
        for entity in mutated.ir.entities.values():
            if entity.entity_id == chosen.entity_id:
                entity.name = f"{old_name}_LABEL_RENAMED"
                break

        return mutated, NegativeMutationRecord(
            mutation_id=str(uuid.uuid4()),
            operator=NegativeOperator.RENAME_PROC_LABEL,
            source_bcg_id=bcg.bcg_id,
            seed=seed,
            description=(
                f"Unreferenced step label '{old_name}' renamed. "
                "Not a MUST_PRECEDE target, not in any contract subject/object. "
                "Contract signatures use entity_id (hash), not name; zero effect."
            ),
            affected_entity_ids=[chosen.entity_id],
            original_state=f"name={old_name!r}",
            mutated_state=f"name='{old_name}_LABEL_RENAMED'",
        )
