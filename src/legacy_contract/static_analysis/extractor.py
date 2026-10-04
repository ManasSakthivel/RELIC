"""
Static Analysis — Contract Extraction from IR.

Three extractors:
1. TemporalContractExtractor — A ≺ B contracts from JCL step ordering
2. ResourceContractExtractor — PRODUCES_BEFORE_CONSUMES contracts
3. ControlFlowContractExtractor — MUST_NOT_FOLLOW_ON_ERROR contracts from COND params

Design principles:
- Extraction is deterministic; no LLM calls here
- Every extracted contract is tagged STATIC_CANDIDATE
- Every contract has a ProvenanceRecord with extraction_method = DETERMINISTIC
- Extractors log all extraction decisions for reproducibility
- Confidence.static_support = 1.0 for deterministic extractions
- Confidence.dynamic_support = 0.0 until reconciliation runs
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from legacy_contract.ir.model import (
    EntityType,
    IREntity,
    IRGraph,
    IRRelation,
    RelationType,
)
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


# ---------------------------------------------------------------------------
# 1. Temporal Contract Extractor
# ---------------------------------------------------------------------------

class TemporalContractExtractor:
    """
    Extracts temporal ordering contracts from IR.

    Primary source: JCL MUST_PRECEDE relations between steps.
    Secondary source: JCL job-level ordering when jobs have cross-dependencies.

    Contract form: STEP-A PRECEDES STEP-B
    Justification: JCL steps execute in declared sequential order.
    This is a deterministic fact from the JCL grammar.
    """

    def extract(self, ir: IRGraph) -> list[Contract]:
        contracts: list[Contract] = []

        # Extract from MUST_PRECEDE relations (JCL sequential steps)
        precede_relations = ir.get_relations_of_type(RelationType.MUST_PRECEDE)
        for rel in precede_relations:
            # Guard: skip reflexive self-ordering relations (A must precede A)
            # These are parse artifacts and would produce CONTRADICTED by any trace
            # since a step cannot be observed both before and after itself.
            if rel.source.entity_id == rel.target.entity_id:
                logger.warning(
                    f"Skipping reflexive MUST_PRECEDE({rel.source.name} → {rel.source.name}) "
                    f"— self-ordering parse artifact, not a valid behavioral contract."
                )
                continue
            evidence = EvidenceItem(
                evidence_type="static_structural",
                source_artifact=rel.source.artifact_path,
                source_location=str(rel.location) if rel.location else "",
                extraction_method=ExtractionMethod.DETERMINISTIC,
                content=(
                    f"JCL step {rel.source.name} is declared before "
                    f"{rel.target.name} in the same job — sequential execution order"
                ),
                formal_content=f"{rel.source.name} ≺ {rel.target.name}",
            )
            provenance = ProvenanceRecord(
                source_artifact=rel.source.artifact_path,
                source_location=str(rel.location) if rel.location else "",
                static_evidence=[evidence],
                extraction_method=ExtractionMethod.DETERMINISTIC,
            )
            confidence = ConfidenceVector(
                static_support=1.0,
                dynamic_support=0.0,
                cross_artifact_support=0.0,
                provenance_quality=1.0,
                human_validation=0.0,
                execution_frequency=0.0,
                ambiguity_penalty=0.0,
            )
            contract = Contract(
                contract_type=ContractType.TEMPORAL,
                subject_id=rel.source.entity_id,
                predicate=ContractPredicate.PRECEDES,
                object_id=rel.target.entity_id,
                natural_language=(
                    f"Step {rel.source.name} must execute and complete "
                    f"before step {rel.target.name} begins."
                ),
                formal_statement=f"{rel.source.name} ≺ {rel.target.name}",
                provenance=provenance,
                confidence=confidence,
                validation_state=ValidationState.STATIC_CANDIDATE,
                metadata={"basis": rel.attributes.get("basis", "jcl_sequential_order")},
            )
            contracts.append(contract)
            logger.debug(f"Temporal contract: {contract.natural_language}")

        return contracts


# ---------------------------------------------------------------------------
# 2. Resource Contract Extractor
# ---------------------------------------------------------------------------

class ResourceContractExtractor:
    """
    Extracts resource dependency contracts from IR.

    Pattern: Step A PRODUCES dataset D; Step B CONSUMES dataset D.
    Contract: A must produce D before B consumes D.

    This is a cross-artifact contract when A and B are in different jobs.
    It is a single-artifact contract when A and B are in the same job.
    """

    def extract(self, ir: IRGraph) -> list[Contract]:
        contracts: list[Contract] = []

        # Find all producer steps (PRODUCES relation)
        producers: dict[str, list[IRRelation]] = {}  # dataset_id -> [produce_relations]
        for rel in ir.get_relations_of_type(RelationType.PRODUCES):
            ds_id = rel.target.entity_id
            producers.setdefault(ds_id, []).append(rel)

        # Find all consumer steps (CONSUMES relation)
        consumers: dict[str, list[IRRelation]] = {}  # dataset_id -> [consume_relations]
        for rel in ir.get_relations_of_type(RelationType.CONSUMES):
            ds_id = rel.target.entity_id
            consumers.setdefault(ds_id, []).append(rel)

        # For each dataset with both producers and consumers, create contracts
        shared_datasets = set(producers.keys()) & set(consumers.keys())
        for ds_id in shared_datasets:
            dataset_entity = ir.get_entity(ds_id)
            if not dataset_entity:
                continue

            for prod_rel in producers[ds_id]:
                for cons_rel in consumers[ds_id]:
                    producer_step = prod_rel.source
                    consumer_step = cons_rel.source

                    # Avoid self-contracts
                    if producer_step.entity_id == consumer_step.entity_id:
                        continue

                    cross_artifact = (
                        producer_step.artifact_path != consumer_step.artifact_path
                    )

                    evidence = EvidenceItem(
                        evidence_type="static_structural",
                        source_artifact=producer_step.artifact_path,
                        source_location=str(prod_rel.location) if prod_rel.location else "",
                        extraction_method=ExtractionMethod.DETERMINISTIC,
                        content=(
                            f"Step {producer_step.name} declares DISP=NEW/CATLG for "
                            f"dataset {dataset_entity.name}; "
                            f"step {consumer_step.name} declares DISP=OLD/SHR for the same dataset"
                        ),
                        formal_content=(
                            f"produces({producer_step.name}, {dataset_entity.name}) ≺ "
                            f"consumes({consumer_step.name}, {dataset_entity.name})"
                        ),
                    )
                    provenance = ProvenanceRecord(
                        source_artifact=producer_step.artifact_path,
                        source_location=str(prod_rel.location) if prod_rel.location else "",
                        static_evidence=[evidence],
                        extraction_method=ExtractionMethod.DETERMINISTIC,
                        notes=f"Consumer at: {consumer_step.artifact_path}",
                    )
                    confidence = ConfidenceVector(
                        static_support=1.0,
                        dynamic_support=0.0,
                        cross_artifact_support=1.0 if cross_artifact else 0.5,
                        provenance_quality=1.0,
                        human_validation=0.0,
                        execution_frequency=0.0,
                        ambiguity_penalty=0.0,
                    )
                    contract = Contract(
                        contract_type=ContractType.RESOURCE,
                        subject_id=producer_step.entity_id,
                        predicate=ContractPredicate.PRODUCES_BEFORE_CONSUMES,
                        object_id=consumer_step.entity_id,
                        natural_language=(
                            f"Step {producer_step.name} must successfully produce dataset "
                            f"{dataset_entity.name} before step {consumer_step.name} consumes it."
                        ),
                        formal_statement=(
                            f"produces({producer_step.name}, {dataset_entity.name}) ≺ "
                            f"consumes({consumer_step.name}, {dataset_entity.name})"
                        ),
                        provenance=provenance,
                        confidence=confidence,
                        validation_state=ValidationState.STATIC_CANDIDATE,
                        metadata={
                            "dataset": dataset_entity.name,
                            "dataset_id": ds_id,
                            "cross_artifact": cross_artifact,
                        },
                    )
                    contracts.append(contract)
                    logger.debug(f"Resource contract: {contract.natural_language}")

        return contracts


# ---------------------------------------------------------------------------
# 3. Control Flow Contract Extractor
# ---------------------------------------------------------------------------

# Matches COND value with or without the "COND=" prefix,
# because the extractor iterates over step.attributes["cond"]
# which stores just the captured value: "(4,GT,STEP010)" or "4,GT"
COND_PATTERN = re.compile(
    r"(?:COND=)?\(?(\d+),\s*(GT|LT|EQ|NE|GE|LE|EVEN|ONLY)(?:,\s*([A-Z0-9]+))?\)?",
    re.IGNORECASE,
)


class ControlFlowContractExtractor:
    """
    Extracts control-flow contracts from JCL COND parameters.

    COND parameter semantics:
    COND=(rc, operator[, stepname]) — step is bypassed if condition is true.

    Contract form: If STEP-X returns RC > threshold, STEP-Y must not execute.

    Note on EVEN/ONLY:
    - COND=EVEN: step executes even if previous step abended
    - COND=ONLY: step executes only if previous step abended
    These generate special control-flow contracts.

    COND without a step name: IBM semantics test the return code of *every*
    previous step. v1.0.0 bound such a test only to the immediately preceding
    step (``legacy_v1_0=True`` reproduces that behaviour).
    """

    def __init__(self, legacy_v1_0: bool = False) -> None:
        self.legacy_v1_0 = legacy_v1_0

    def extract(self, ir: IRGraph) -> list[Contract]:
        contracts: list[Contract] = []

        steps = [
            e for e in ir.entities.values()
            if e.entity_type == EntityType.STEP and "cond" in e.attributes
        ]

        for step in steps:
            cond_str = step.attributes.get("cond", "")
            if not cond_str:
                continue

            for m in COND_PATTERN.finditer(cond_str):
                rc_threshold = int(m.group(1))
                operator = m.group(2).upper()
                ref_step = m.group(3)

                # Find the step this condition references (or applies to all previous steps)
                if ref_step:
                    ref_entities = [
                        e for e in ir.entities.values()
                        if e.entity_type == EntityType.STEP
                        and e.name.upper() == ref_step.upper()
                    ]
                else:
                    # Applies to all preceding steps
                    if self.legacy_v1_0:
                        ref_entities = self._get_preceding_steps(step, ir)
                    else:
                        ref_entities = self._get_all_preceding_steps(step, ir)

                for ref_entity in ref_entities:
                    evidence = EvidenceItem(
                        evidence_type="static_structural",
                        source_artifact=step.artifact_path,
                        source_location=str(step.location) if step.location else "",
                        extraction_method=ExtractionMethod.DETERMINISTIC,
                        content=(
                            f"COND=({rc_threshold},{operator}) on step {step.name} "
                            f"referencing {ref_entity.name}: "
                            f"step {step.name} is bypassed if "
                            f"RC({ref_entity.name}) {operator} {rc_threshold}"
                        ),
                        formal_content=(
                            f"RC({ref_entity.name}) {operator} {rc_threshold} → "
                            f"bypass({step.name})"
                        ),
                    )
                    provenance = ProvenanceRecord(
                        source_artifact=step.artifact_path,
                        source_location=str(step.location) if step.location else "",
                        static_evidence=[evidence],
                        extraction_method=ExtractionMethod.DETERMINISTIC,
                    )
                    confidence = ConfidenceVector(
                        static_support=1.0,
                        dynamic_support=0.0,
                        cross_artifact_support=0.3,
                        provenance_quality=1.0,
                        human_validation=0.0,
                        execution_frequency=0.0,
                        ambiguity_penalty=0.1,  # COND semantics can be inverted
                    )
                    contract = Contract(
                        contract_type=ContractType.CONTROL_FLOW,
                        subject_id=ref_entity.entity_id,
                        predicate=ContractPredicate.MUST_NOT_FOLLOW_ON_ERROR,
                        object_id=step.entity_id,
                        natural_language=(
                            f"Step {step.name} must not execute if step {ref_entity.name} "
                            f"returns return code {operator} {rc_threshold}."
                        ),
                        formal_statement=(
                            f"RC({ref_entity.name}) {operator} {rc_threshold} → "
                            f"¬execute({step.name})"
                        ),
                        provenance=provenance,
                        confidence=confidence,
                        validation_state=ValidationState.STATIC_CANDIDATE,
                        metadata={
                            "rc_threshold": rc_threshold,
                            "operator": operator,
                            "ref_step": ref_entity.name,
                        },
                    )
                    contracts.append(contract)
                    logger.debug(f"Control-flow contract: {contract.natural_language}")

        return contracts

    def _get_preceding_steps(
        self, step: IREntity, ir: IRGraph
    ) -> list[IREntity]:
        """Find all steps that precede this step via MUST_PRECEDE relations."""
        preceding = []
        for rel in ir.get_relations_to(step.entity_id):
            if rel.relation_type == RelationType.MUST_PRECEDE:
                preceding.append(rel.source)
        return preceding

    def _get_all_preceding_steps(
        self, step: IREntity, ir: IRGraph
    ) -> list[IREntity]:
        """All steps that transitively precede this step (IBM COND semantics)."""
        seen: dict[str, IREntity] = {}
        frontier = [step.entity_id]
        while frontier:
            current = frontier.pop()
            for rel in ir.get_relations_to(current):
                if (
                    rel.relation_type == RelationType.MUST_PRECEDE
                    and rel.source.entity_id not in seen
                    and rel.source.entity_id != step.entity_id
                ):
                    seen[rel.source.entity_id] = rel.source
                    frontier.append(rel.source.entity_id)
        return list(seen.values())


# ---------------------------------------------------------------------------
# Combined Static Extractor
# ---------------------------------------------------------------------------

@dataclass
class StaticExtractionResult:
    """All contracts extracted from static analysis of an IR graph."""
    temporal_contracts: list[Contract] = field(default_factory=list)
    resource_contracts: list[Contract] = field(default_factory=list)
    control_flow_contracts: list[Contract] = field(default_factory=list)

    @property
    def all_contracts(self) -> list[Contract]:
        return (
            self.temporal_contracts
            + self.resource_contracts
            + self.control_flow_contracts
        )

    def summary(self) -> str:
        return (
            f"Static extraction: "
            f"temporal={len(self.temporal_contracts)}, "
            f"resource={len(self.resource_contracts)}, "
            f"control_flow={len(self.control_flow_contracts)}, "
            f"total={len(self.all_contracts)}"
        )


class StaticContractExtractor:
    """
    Orchestrates all static contract extractors.
    Call .extract(ir) to get all static candidate contracts.
    """

    def __init__(self, legacy_v1_0: bool = False) -> None:
        self._temporal = TemporalContractExtractor()
        self._resource = ResourceContractExtractor()
        self._control = ControlFlowContractExtractor(legacy_v1_0=legacy_v1_0)

    def extract(self, ir: IRGraph) -> StaticExtractionResult:
        result = StaticExtractionResult(
            temporal_contracts=self._temporal.extract(ir),
            resource_contracts=self._resource.extract(ir),
            control_flow_contracts=self._control.extract(ir),
        )
        logger.info(result.summary())
        return result
