"""
Intermediate Representation (IR) — Core entity and relation types.

The IR is the structural representation produced by parsers.
The BCG is built ON TOP of the IR by adding behavioral contracts, provenance,
dynamic observations, and validation metadata.

Design principles:
- Parser-agnostic: all parsers produce IREntity / IRRelation objects
- Stable identifiers: entity IDs are deterministic (artifact_path + local_name + type)
- Immutable after construction (dataclass with frozen=False but modification discouraged)
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Entity Types
# ---------------------------------------------------------------------------

class EntityType(str, Enum):
    """All entity types that can appear in the BCG."""
    PROGRAM = "PROGRAM"
    PROCEDURE = "PROCEDURE"
    JOB = "JOB"
    STEP = "STEP"
    DATASET = "DATASET"
    FILE = "FILE"
    RECORD = "RECORD"
    FIELD = "FIELD"
    DATABASE = "DATABASE"
    TABLE = "TABLE"
    STATE = "STATE"
    RESOURCE = "RESOURCE"
    CONFIGURATION = "CONFIGURATION"
    ARTIFACT = "ARTIFACT"
    OPERATION = "OPERATION"
    ERROR_CONDITION = "ERROR_CONDITION"
    EXECUTION_EVENT = "EXECUTION_EVENT"
    COPYBOOK = "COPYBOOK"
    SECTION = "SECTION"
    PARAGRAPH = "PARAGRAPH"
    JCL_PROC = "JCL_PROC"
    JCL_DD = "JCL_DD"


# ---------------------------------------------------------------------------
# Relation Types
# ---------------------------------------------------------------------------

class RelationType(str, Enum):
    """All structural relationship types in the BCG."""
    CALLS = "CALLS"
    PERFORMS = "PERFORMS"
    READS = "READS"
    WRITES = "WRITES"
    PRODUCES = "PRODUCES"
    CONSUMES = "CONSUMES"
    DEFINES = "DEFINES"
    MAPS_TO = "MAPS_TO"
    TRANSFORMS = "TRANSFORMS"
    DEPENDS_ON = "DEPENDS_ON"
    REQUIRES_STATE = "REQUIRES_STATE"
    ESTABLISHES_STATE = "ESTABLISHES_STATE"
    MUST_PRECEDE = "MUST_PRECEDE"
    MUST_FOLLOW = "MUST_FOLLOW"
    PROPAGATES_ERROR = "PROPAGATES_ERROR"
    USES_RESOURCE = "USES_RESOURCE"
    INVALIDATES = "INVALIDATES"
    OBSERVED_BEFORE = "OBSERVED_BEFORE"
    OBSERVED_AFTER = "OBSERVED_AFTER"
    CONTAINS = "CONTAINS"
    REFERENCES = "REFERENCES"
    COPIES = "COPIES"


# ---------------------------------------------------------------------------
# Source Location
# ---------------------------------------------------------------------------

@dataclass
class SourceLocation:
    """Precise source location within an artifact."""
    artifact_path: str
    line_start: int
    line_end: int
    column_start: int = 0
    column_end: int = 0
    context: str = ""  # surrounding text for human readability

    def __str__(self) -> str:
        return f"{self.artifact_path}:{self.line_start}:{self.column_start}"


# ---------------------------------------------------------------------------
# IR Entity
# ---------------------------------------------------------------------------

@dataclass
class IREntity:
    """
    A typed entity in the Behavioral Contract Graph.

    Entity IDs are deterministic: derived from artifact_path + name + type.
    This ensures stable IDs across runs for the same artifact.
    """
    entity_type: EntityType
    name: str
    artifact_path: str
    location: SourceLocation | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    entity_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic ID: stable across runs for the same artifact
        key = f"{self.artifact_path}::{self.entity_type.value}::{self.name}"
        self.entity_id = hashlib.sha256(key.encode()).hexdigest()[:16]

    def __hash__(self) -> int:
        return hash(self.entity_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, IREntity):
            return self.entity_id == other.entity_id
        return False


# ---------------------------------------------------------------------------
# IR Relation
# ---------------------------------------------------------------------------

@dataclass
class IRRelation:
    """
    A typed directed relationship between two IR entities.

    Relations have confidence scores reflecting extraction certainty.
    """
    relation_type: RelationType
    source: IREntity
    target: IREntity
    confidence: float = 1.0  # 1.0 = deterministic; < 1.0 = inferred
    location: SourceLocation | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    relation_id: str = field(init=False)

    def __post_init__(self) -> None:
        key = f"{self.source.entity_id}::{self.relation_type.value}::{self.target.entity_id}"
        self.relation_id = hashlib.sha256(key.encode()).hexdigest()[:16]

    def __hash__(self) -> int:
        return hash(self.relation_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, IRRelation):
            return self.relation_id == other.relation_id
        return False


# ---------------------------------------------------------------------------
# IR Graph
# ---------------------------------------------------------------------------

@dataclass
class IRGraph:
    """
    The complete intermediate representation graph for a set of artifacts.

    Entities and relations extracted by parsers are stored here before
    being processed into BCG contracts.
    """
    entities: dict[str, IREntity] = field(default_factory=dict)  # entity_id -> entity
    relations: list[IRRelation] = field(default_factory=list)
    artifact_paths: list[str] = field(default_factory=list)

    def add_entity(self, entity: IREntity) -> IREntity:
        """Add entity; return existing entity if already present (stable IDs)."""
        if entity.entity_id in self.entities:
            return self.entities[entity.entity_id]
        self.entities[entity.entity_id] = entity
        return entity

    def add_relation(self, relation: IRRelation) -> None:
        """Add relation; skip if duplicate."""
        for existing in self.relations:
            if existing.relation_id == relation.relation_id:
                return
        self.relations.append(relation)

    def get_entity(self, entity_id: str) -> IREntity | None:
        return self.entities.get(entity_id)

    def get_relations_from(self, entity_id: str) -> list[IRRelation]:
        return [r for r in self.relations if r.source.entity_id == entity_id]

    def get_relations_to(self, entity_id: str) -> list[IRRelation]:
        return [r for r in self.relations if r.target.entity_id == entity_id]

    def get_relations_of_type(self, rel_type: RelationType) -> list[IRRelation]:
        return [r for r in self.relations if r.relation_type == rel_type]

    def entity_count(self) -> int:
        return len(self.entities)

    def relation_count(self) -> int:
        return len(self.relations)

    def summary(self) -> str:
        type_counts: dict[str, int] = {}
        for e in self.entities.values():
            type_counts[e.entity_type.value] = type_counts.get(e.entity_type.value, 0) + 1
        rel_counts: dict[str, int] = {}
        for r in self.relations:
            rel_counts[r.relation_type.value] = rel_counts.get(r.relation_type.value, 0) + 1
        lines = [
            f"IRGraph: {self.entity_count()} entities, {self.relation_count()} relations",
            f"Artifacts: {self.artifact_paths}",
            "Entity types: " + ", ".join(f"{k}={v}" for k, v in sorted(type_counts.items())),
            "Relation types: " + ", ".join(f"{k}={v}" for k, v in sorted(rel_counts.items())),
        ]
        return "\n".join(lines)
