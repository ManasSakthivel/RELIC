"""
Pydantic v2 response models for the LEGACY-CONTRACT FastAPI backend.

Every model includes field-level documentation so API consumers understand
the scientific semantics — especially the distinction between validation
states and the meaning of 'confidence_score'.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums (mirrored as string literals for API consumers)
# ---------------------------------------------------------------------------

class EntityTypeOut(str):
    pass


class ValidationStateOut(str):
    pass


class ContractTypeOut(str):
    pass


# ---------------------------------------------------------------------------
# Source Location
# ---------------------------------------------------------------------------

class SourceLocationOut(BaseModel):
    artifact_path: str
    line_start: int
    line_end: int
    column_start: int = 0
    column_end: int = 0
    context: str = ""

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

class EvidenceItemOut(BaseModel):
    evidence_id: str
    evidence_type: str
    source_artifact: str
    source_location: str
    extraction_method: str
    content: str
    formal_content: str = ""
    timestamp: datetime
    llm_model: str | None = None
    llm_prompt_version: str | None = None

    model_config = {"from_attributes": True}


class ProvenanceOut(BaseModel):
    source_artifact: str
    source_location: str
    extraction_method: str
    static_evidence: list[EvidenceItemOut] = Field(
        default_factory=list,
        description="Evidence items extracted from static artifact analysis.",
    )
    dynamic_evidence: list[EvidenceItemOut] = Field(
        default_factory=list,
        description="Evidence items from dynamic execution traces.",
    )
    model: str | None = None
    prompt_version: str | None = None
    timestamp: datetime
    notes: str = ""

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Confidence Vector
# ---------------------------------------------------------------------------

class ConfidenceVectorOut(BaseModel):
    static_support: float = Field(
        ge=0.0,
        le=1.0,
        description="Evidence strength from static analysis [0,1]. NOT a probability.",
    )
    dynamic_support: float = Field(
        ge=0.0,
        le=1.0,
        description="Evidence strength from dynamic observations [0,1].",
    )
    cross_artifact_support: float = Field(ge=0.0, le=1.0)
    provenance_quality: float = Field(ge=0.0, le=1.0)
    human_validation: float = Field(ge=0.0, le=1.0)
    execution_frequency: float = Field(ge=0.0, le=1.0)
    ambiguity_penalty: float = Field(ge=0.0, le=1.0)
    aggregate_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Aggregated evidence-strength score in [0,1]. "
            "WARNING: This is NOT a probability. It is a normalized "
            "weighted sum of evidence dimensions."
        ),
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------

class EntityOut(BaseModel):
    entity_id: str
    name: str
    entity_type: str
    artifact_path: str
    location: SourceLocationOut | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Relation
# ---------------------------------------------------------------------------

class RelationOut(BaseModel):
    relation_id: str
    relation_type: str
    source_id: str
    target_id: str
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Extraction confidence: 1.0 = deterministic parse; <1.0 = inferred.",
    )
    attributes: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------

class ContractSummaryOut(BaseModel):
    """Lightweight contract record for list endpoints."""
    contract_id: str
    contract_type: str
    subject_id: str
    predicate: str
    object_id: str
    natural_language: str
    validation_state: str = Field(
        description=(
            "STATIC_CANDIDATE | DYNAMICALLY_OBSERVED | STATIC_DYNAMIC_SUPPORTED | "
            "STATIC_DYNAMIC_CONFLICT | HUMAN_VALIDATED | GROUND_TRUTH | "
            "UNRESOLVED | NOT_OBSERVED. "
            "STATIC_CANDIDATE ≠ GROUND_TRUTH. NOT_OBSERVED ≠ CONTRADICTED."
        )
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Evidence-strength score in [0,1]. "
            "NOT a probability of contract validity."
        ),
    )
    has_conflict: bool = Field(
        description="True when static and dynamic evidence disagree (STATIC_DYNAMIC_CONFLICT)."
    )
    created_at: datetime

    model_config = {"from_attributes": True}


class ContractDetailOut(BaseModel):
    """Full contract with provenance and evidence chains."""
    contract_id: str
    contract_type: str
    subject_id: str
    predicate: str
    object_id: str
    natural_language: str
    formal_statement: str | None = Field(
        default=None,
        description="LTL or semi-formal notation for the contract obligation, if available.",
    )
    scope: str = Field(
        default="",
        description="Execution context within which this contract applies.",
    )
    preconditions: list[str] = Field(default_factory=list)
    validation_state: str
    confidence: ConfidenceVectorOut
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Aggregate evidence-strength score. NOT a probability.",
    )
    has_conflict: bool
    conflict_explanation: str | None = Field(
        default=None,
        description=(
            "Present only when has_conflict=True. "
            "Describes exactly what the static analysis expected vs. what was observed."
        ),
    )
    provenance: ProvenanceOut | None = None
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Execution Event
# ---------------------------------------------------------------------------

class ExecutionEventOut(BaseModel):
    event_id: str
    timestamp: datetime
    execution_id: str
    artifact_id: str
    operation: str
    resource: str | None = None
    predecessor_events: list[str] = Field(default_factory=list)
    successor_events: list[str] = Field(default_factory=list)
    return_code: int | None = Field(
        default=None,
        description="Return code from execution. None means 'not captured', NOT zero/success.",
    )
    source_type: str = Field(
        description=(
            "EXECUTION | EXECUTION_SIMULATED | SYNTHETIC_STATIC | HUMAN. "
            "SYNTHETIC_STATIC traces are never labeled as real execution evidence."
        )
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# BCG Summary
# ---------------------------------------------------------------------------

class BCGSummaryOut(BaseModel):
    bcg_id: str
    created_at: str
    artifact_paths: list[str]
    entity_count: int
    relation_count: int
    contract_count: int
    observation_count: int
    dynamic_coverage_rate: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Fraction of contracts that have at least one dynamic observation. "
            "Contracts with zero dynamic evidence are NOT_OBSERVED, not CONTRADICTED."
        ),
    )
    contracts_by_type: dict[str, int] = Field(default_factory=dict)
    contracts_by_state: dict[str, int] = Field(default_factory=dict)
    conflict_count: int
    validated_count: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------

class RiskEvidenceChainOut(BaseModel):
    """
    Full evidence chain for a single risk finding.
    Each link is required — no unexplained risk scores are returned.
    """
    change_description: str = Field(
        description="What changed between original and modernized artifact."
    )
    affected_contract_id: str
    affected_contract_natural_language: str
    static_evidence_summary: str
    dynamic_evidence_summary: str
    reconciliation_outcome: str = Field(
        description="SUPPORTED | CONTRADICTED | UNOBSERVED | PARTIALLY_SUPPORTED | AMBIGUOUS"
    )
    affected_artifact_ids: list[str]
    potential_consequence: str
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Evidence-strength score for this risk finding. NOT a probability.",
    )
    validation_state: str


class RiskReportOut(BaseModel):
    bcg_id: str
    generated_at: datetime
    total_risks: int
    high_confidence_risks: int = Field(
        description="Risks with confidence_score >= 0.7 (threshold set pre-evaluation)."
    )
    evidence_chains: list[RiskEvidenceChainOut]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Modernization Diff
# ---------------------------------------------------------------------------

class ContractDiffItemOut(BaseModel):
    contract_id: str
    contract_type: str
    natural_language: str
    validation_state: str
    confidence_score: float
    diff_category: str = Field(
        description="PRESERVED | BROKEN | ADDED. BROKEN contracts are regression CANDIDATES."
    )

    model_config = {"from_attributes": True}


class ModernizationDiffOut(BaseModel):
    bcg_id: str
    original_artifact_count: int
    modernized_artifact_count: int
    preserved_count: int
    broken_count: int
    added_count: int
    regression_candidate_count: int = Field(
        description=(
            "Subset of BROKEN contracts that were previously validated "
            "(STATIC_DYNAMIC_SUPPORTED | HUMAN_VALIDATED | GROUND_TRUTH). "
            "These are the highest-priority review items."
        )
    )
    contracts: list[ContractDiffItemOut]
    warning: str = Field(
        default=(
            "BROKEN contracts are CANDIDATES for semantic regression. "
            "They require execution oracle or human validation to confirm actual regression."
        )
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Ingest Request / Response
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    artifact_paths: list[str] = Field(
        description="Paths to legacy artifact files (JCL, COBOL, copybooks) to ingest."
    )
    trace_paths: list[str] = Field(
        default_factory=list,
        description="Optional paths to execution trace files (JSON lines format).",
    )
    bcg_id: str | None = Field(
        default=None,
        description="Optional stable BCG ID. Auto-generated if not provided.",
    )


class IngestResponse(BaseModel):
    bcg_id: str
    status: str
    entity_count: int
    relation_count: int
    contract_count: int
    observation_count: int
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthOut(BaseModel):
    status: str
    version: str
    bcg_store_count: int
    description: str = "LEGACY-CONTRACT Research API — execution-grounded behavioral contract analysis"
