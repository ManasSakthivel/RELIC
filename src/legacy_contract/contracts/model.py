"""
Behavioral Contract types, provenance, confidence model, and validation states.

SCIENTIFIC PRINCIPLES ENFORCED HERE:
1. STATIC_CANDIDATE ≠ DYNAMICALLY_OBSERVED ≠ GROUND_TRUTH
2. Confidence is NOT probability — it is a normalized evidence-strength score
3. Every contract has mandatory provenance
4. NOT_OBSERVED ≠ CONTRADICTED
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Contract Classification
# ---------------------------------------------------------------------------

class ContractType(str, Enum):
    """Behavioral contract types. Paper 1 scope: TEMPORAL, RESOURCE, CONTROL_FLOW."""
    TEMPORAL = "TEMPORAL"             # A must occur before B
    RESOURCE = "RESOURCE"             # A must produce R before B consumes R
    CONTROL_FLOW = "CONTROL_FLOW"     # If condition C then X must/must-not execute
    DATA = "DATA"                     # Field-level compatibility (Paper 2)
    STATE = "STATE"                   # State initialization obligations (Paper 2)
    ERROR = "ERROR"                   # Error propagation obligations (Paper 2)


class ContractPredicate(str, Enum):
    """Semantic predicate for the contract relationship."""
    PRECEDES = "PRECEDES"                           # TEMPORAL: A ≺ B
    PRODUCES_BEFORE_CONSUMES = "PRODUCES_BEFORE_CONSUMES"  # RESOURCE: A produces R before B consumes R
    MUST_NOT_FOLLOW_ON_ERROR = "MUST_NOT_FOLLOW_ON_ERROR"  # CONTROL: B must not run if A returns RC > threshold
    REQUIRES_INITIALIZATION = "REQUIRES_INITIALIZATION"   # STATE: S must be initialized before P uses it
    FIELD_COMPATIBLE = "FIELD_COMPATIBLE"           # DATA: field format must be compatible
    MUST_PRECEDE_FOR_RESOURCE = "MUST_PRECEDE_FOR_RESOURCE"  # RESOURCE+TEMPORAL combined


# ---------------------------------------------------------------------------
# Validation States
# ---------------------------------------------------------------------------

class ValidationState(str, Enum):
    """
    Every contract has an explicit validation state.
    NEVER confuse inference with observation with verification.
    """
    STATIC_CANDIDATE = "STATIC_CANDIDATE"       # Inferred from static analysis only
    DYNAMICALLY_OBSERVED = "DYNAMICALLY_OBSERVED"  # Observed in execution but not statically extracted
    STATIC_DYNAMIC_SUPPORTED = "STATIC_DYNAMIC_SUPPORTED"  # Both static and dynamic agree
    STATIC_DYNAMIC_CONFLICT = "STATIC_DYNAMIC_CONFLICT"    # Static and dynamic disagree
    HUMAN_VALIDATED = "HUMAN_VALIDATED"         # Expert annotator confirmed
    GROUND_TRUTH = "GROUND_TRUTH"               # Deterministic or execution-oracle verified
    UNRESOLVED = "UNRESOLVED"                   # Ambiguous; needs investigation
    NOT_OBSERVED = "NOT_OBSERVED"               # No dynamic evidence available (≠ CONTRADICTED)


# ---------------------------------------------------------------------------
# Extraction Methods
# ---------------------------------------------------------------------------

class ExtractionMethod(str, Enum):
    """Source of a contract or evidence item."""
    DETERMINISTIC = "DETERMINISTIC"     # Mechanically verifiable from grammar
    LLM = "LLM"                         # LLM inference
    HUMAN = "HUMAN"                     # Human annotation
    EXECUTION = "EXECUTION"             # Real execution (GnuCOBOL)
    EXECUTION_SIMULATED = "EXECUTION_SIMULATED"  # JCL batch simulation
    SYNTHETIC_STATIC = "SYNTHETIC_STATIC"  # Statically derived synthetic trace
    COMBINED = "COMBINED"               # Multiple methods combined


# ---------------------------------------------------------------------------
# Provenance Record
# ---------------------------------------------------------------------------

@dataclass
class EvidenceItem:
    """A single piece of evidence supporting or contradicting a contract."""
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    evidence_type: str = ""           # "static_structural", "dynamic_observation", etc.
    source_artifact: str = ""
    source_location: str = ""         # line:col or descriptive
    extraction_method: ExtractionMethod = ExtractionMethod.DETERMINISTIC
    content: str = ""                 # Human-readable evidence description
    formal_content: str = ""          # Formal notation if available
    timestamp: datetime = field(default_factory=datetime.utcnow)
    # LLM-specific fields (required if extraction_method = LLM)
    llm_model: str | None = None
    llm_prompt_version: str | None = None
    llm_temperature: float | None = None
    llm_input: str | None = None
    llm_output: str | None = None


@dataclass
class ProvenanceRecord:
    """
    Complete provenance for a behavioral contract.
    Every contract must have a ProvenanceRecord.
    """
    source_artifact: str
    source_location: str
    static_evidence: list[EvidenceItem] = field(default_factory=list)
    dynamic_evidence: list[EvidenceItem] = field(default_factory=list)
    extraction_method: ExtractionMethod = ExtractionMethod.DETERMINISTIC
    model: str | None = None
    prompt_version: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""

    def has_static_evidence(self) -> bool:
        return len(self.static_evidence) > 0

    def has_dynamic_evidence(self) -> bool:
        return len(self.dynamic_evidence) > 0

    def evidence_summary(self) -> str:
        return (
            f"static={len(self.static_evidence)}, "
            f"dynamic={len(self.dynamic_evidence)}, "
            f"method={self.extraction_method.value}"
        )


# ---------------------------------------------------------------------------
# Confidence Model
# ---------------------------------------------------------------------------

@dataclass
class ConfidenceVector:
    """
    Multi-dimensional evidence-strength score.

    SCIENTIFIC WARNING: This is NOT a probability.
    It is a normalized evidence-strength score in [0, 1].
    Do not interpret aggregate_confidence as P(contract is valid).

    Dimensions:
    - static_support: quality of static evidence [0, 1]
    - dynamic_support: quality of dynamic evidence [0, 1]
    - cross_artifact_support: evidence from multiple artifact types [0, 1]
    - provenance_quality: completeness of provenance record [0, 1]
    - human_validation: human annotator confidence [0, 1]
    - execution_frequency: how often the pattern was observed in traces [0, 1]
    - ambiguity_penalty: deduct for ambiguous extraction [0, 1] (subtracted)

    Weights are loaded from config/confidence_weights.yaml and must be
    set BEFORE evaluation begins (not tuned to maximize reported metrics).
    """
    static_support: float = 0.0
    dynamic_support: float = 0.0
    cross_artifact_support: float = 0.0
    provenance_quality: float = 0.0
    human_validation: float = 0.0
    execution_frequency: float = 0.0
    ambiguity_penalty: float = 0.0

    # Weights (loaded from config; not optimized on test data)
    _weights: dict[str, float] = field(default_factory=lambda: {
        "static_support": 0.25,
        "dynamic_support": 0.30,
        "cross_artifact_support": 0.15,
        "provenance_quality": 0.10,
        "human_validation": 0.20,
        "execution_frequency": 0.10,
    })

    def aggregate(self) -> float:
        """
        Compute normalized evidence-strength score.
        NOT a probability. See class docstring.
        """
        raw = (
            self._weights["static_support"] * self.static_support
            + self._weights["dynamic_support"] * self.dynamic_support
            + self._weights["cross_artifact_support"] * self.cross_artifact_support
            + self._weights["provenance_quality"] * self.provenance_quality
            + self._weights["human_validation"] * self.human_validation
            + self._weights["execution_frequency"] * self.execution_frequency
        )
        penalized = raw * (1.0 - self.ambiguity_penalty)
        return max(0.0, min(1.0, penalized))

    def update_weights(self, weights: dict[str, float]) -> None:
        """Update weights from configuration. Call before evaluation, not after."""
        self._weights = weights


# ---------------------------------------------------------------------------
# Behavioral Contract
# ---------------------------------------------------------------------------

@dataclass
class Contract:
    """
    A behavioral contract in the BCG.

    A contract asserts a behavioral obligation that must hold
    for the system to preserve its intended behavior.

    Subject and object are entity_ids referencing IREntity objects.
    """
    contract_type: ContractType
    subject_id: str        # BCG entity_id
    predicate: ContractPredicate
    object_id: str         # BCG entity_id
    natural_language: str  # Human-readable statement
    scope: str = ""        # Execution context where this applies
    preconditions: list[str] = field(default_factory=list)
    formal_statement: str | None = None  # Optional LTL or formal notation
    provenance: ProvenanceRecord | None = None
    confidence: ConfidenceVector = field(default_factory=ConfidenceVector)
    validation_state: ValidationState = ValidationState.STATIC_CANDIDATE
    contract_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.contract_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Contract):
            return self.contract_id == other.contract_id
        return False

    def confidence_score(self) -> float:
        """Aggregate evidence-strength score. NOT a probability."""
        return self.confidence.aggregate()

    def is_validated(self) -> bool:
        return self.validation_state in {
            ValidationState.STATIC_DYNAMIC_SUPPORTED,
            ValidationState.HUMAN_VALIDATED,
            ValidationState.GROUND_TRUTH,
        }

    def has_conflict(self) -> bool:
        return self.validation_state == ValidationState.STATIC_DYNAMIC_CONFLICT

    def summary(self) -> str:
        return (
            f"[{self.contract_type.value}] "
            f"{self.subject_id} --{self.predicate.value}--> {self.object_id} "
            f"| state={self.validation_state.value} "
            f"| confidence={self.confidence_score():.2f}"
        )
