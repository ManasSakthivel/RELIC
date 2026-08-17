"""
FastAPI Research API for LEGACY-CONTRACT.

Serves Behavioral Contract Graph (BCG) data to the React research UI.

Endpoints
---------
GET  /api/health                         Health check
GET  /api/bcg/{bcg_id}/summary           BCG overview statistics
GET  /api/bcg/{bcg_id}/entities          All entities (V component of BCG)
GET  /api/bcg/{bcg_id}/contracts         All contracts (C component) with provenance
GET  /api/bcg/{bcg_id}/contracts/{id}    Single contract detail with full evidence chain
GET  /api/bcg/{bcg_id}/observations      Dynamic observations (D component)
GET  /api/bcg/{bcg_id}/conflicts         All STATIC_DYNAMIC_CONFLICT contracts
GET  /api/bcg/{bcg_id}/risk              Modernization risk report
GET  /api/bcg/{bcg_id}/diff              Modernization diff (original vs. modernized)
POST /api/ingest                         Ingest artifacts and build BCG

Scientific Integrity Notes
--------------------------
- No endpoint returns a bare numeric risk score without an evidence chain.
- Confidence scores are labeled as evidence-strength scores, NOT probabilities.
- NOT_OBSERVED contracts are never returned as CONTRADICTED.
- STATIC_DYNAMIC_CONFLICT is always surfaced explicitly.
- Every BCG stored in memory retains full provenance.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from legacy_contract.api.models import (
    BCGSummaryOut,
    ContractDetailOut,
    ContractDiffItemOut,
    ContractSummaryOut,
    ConfidenceVectorOut,
    EntityOut,
    ExecutionEventOut,
    EvidenceItemOut,
    HealthOut,
    IngestRequest,
    IngestResponse,
    ModernizationDiffOut,
    ProvenanceOut,
    RelationOut,
    RiskEvidenceChainOut,
    RiskReportOut,
    SourceLocationOut,
)
from legacy_contract.bcg.model import BCG, BCGDiff
from legacy_contract.contracts.model import (
    Contract,
    ContractType,
    ConfidenceVector,
    ValidationState,
)
from legacy_contract.dynamic_analysis.model import ExecutionEvent, EventSourceType, OperationType
from legacy_contract.ir.model import EntityType, IREntity, IRGraph, IRRelation, RelationType, SourceLocation

# ---------------------------------------------------------------------------
# Application State
# ---------------------------------------------------------------------------

# In-memory BCG store: bcg_id -> BCG
# For production, this would be replaced by a proper persistence layer
# (SQLite / Neo4j), but the API interface remains identical.
_bcg_store: dict[str, BCG] = {}

VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Populate the store with a demo BCG on startup so the UI has data."""
    logger.info("LEGACY-CONTRACT API starting — populating demo BCG…")
    demo = _build_demo_bcg()
    _bcg_store[demo.bcg_id] = demo
    logger.info(f"Demo BCG ready: {demo.bcg_id} — {demo.summary()}")
    yield
    logger.info("LEGACY-CONTRACT API shutting down.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LEGACY-CONTRACT Research API",
    description=(
        "Execution-Grounded Behavioral Contract Recovery for Safe Legacy Software Modernization. "
        "Research API — BCG data, contract provenance, static/dynamic reconciliation, "
        "and modernization risk analysis."
    ),
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper: BCG lookup
# ---------------------------------------------------------------------------

def _get_bcg(bcg_id: str) -> BCG:
    bcg = _bcg_store.get(bcg_id)
    if bcg is None:
        raise HTTPException(
            status_code=404,
            detail=f"BCG '{bcg_id}' not found. Call POST /api/ingest to build one.",
        )
    return bcg


# ---------------------------------------------------------------------------
# Helper: Model converters
# ---------------------------------------------------------------------------

def _entity_to_out(e: IREntity) -> EntityOut:
    loc = None
    if e.location:
        loc = SourceLocationOut(
            artifact_path=e.location.artifact_path,
            line_start=e.location.line_start,
            line_end=e.location.line_end,
            column_start=e.location.column_start,
            column_end=e.location.column_end,
            context=e.location.context,
        )
    return EntityOut(
        entity_id=e.entity_id,
        name=e.name,
        entity_type=e.entity_type.value,
        artifact_path=e.artifact_path,
        location=loc,
        attributes=e.attributes,
    )


def _relation_to_out(r: IRRelation) -> RelationOut:
    return RelationOut(
        relation_id=r.relation_id,
        relation_type=r.relation_type.value,
        source_id=r.source.entity_id,
        target_id=r.target.entity_id,
        confidence=r.confidence,
        attributes=r.attributes,
    )


def _evidence_item_to_out(ev: Any) -> EvidenceItemOut:
    return EvidenceItemOut(
        evidence_id=ev.evidence_id,
        evidence_type=ev.evidence_type,
        source_artifact=ev.source_artifact,
        source_location=ev.source_location,
        extraction_method=ev.extraction_method.value,
        content=ev.content,
        formal_content=ev.formal_content,
        timestamp=ev.timestamp,
        llm_model=ev.llm_model,
        llm_prompt_version=ev.llm_prompt_version,
    )


def _provenance_to_out(p: Any) -> ProvenanceOut:
    return ProvenanceOut(
        source_artifact=p.source_artifact,
        source_location=p.source_location,
        extraction_method=p.extraction_method.value,
        static_evidence=[_evidence_item_to_out(e) for e in p.static_evidence],
        dynamic_evidence=[_evidence_item_to_out(e) for e in p.dynamic_evidence],
        model=p.model,
        prompt_version=p.prompt_version,
        timestamp=p.timestamp,
        notes=p.notes,
    )


def _confidence_to_out(c: ConfidenceVector) -> ConfidenceVectorOut:
    return ConfidenceVectorOut(
        static_support=c.static_support,
        dynamic_support=c.dynamic_support,
        cross_artifact_support=c.cross_artifact_support,
        provenance_quality=c.provenance_quality,
        human_validation=c.human_validation,
        execution_frequency=c.execution_frequency,
        ambiguity_penalty=c.ambiguity_penalty,
        aggregate_score=c.aggregate(),
    )


def _contract_conflict_explanation(c: Contract) -> str | None:
    if not c.has_conflict():
        return None
    prov = c.provenance
    static_desc = "Static analysis expected: " + (
        "; ".join(e.content for e in prov.static_evidence) if prov and prov.static_evidence else "no static evidence recorded"
    )
    dynamic_desc = "Dynamic execution observed: " + (
        "; ".join(e.content for e in prov.dynamic_evidence) if prov and prov.dynamic_evidence else "no dynamic evidence recorded"
    )
    return f"{static_desc} | {dynamic_desc}"


def _contract_to_summary(c: Contract) -> ContractSummaryOut:
    return ContractSummaryOut(
        contract_id=c.contract_id,
        contract_type=c.contract_type.value,
        subject_id=c.subject_id,
        predicate=c.predicate.value,
        object_id=c.object_id,
        natural_language=c.natural_language,
        validation_state=c.validation_state.value,
        confidence_score=c.confidence_score(),
        has_conflict=c.has_conflict(),
        created_at=c.created_at,
    )


def _contract_to_detail(c: Contract) -> ContractDetailOut:
    return ContractDetailOut(
        contract_id=c.contract_id,
        contract_type=c.contract_type.value,
        subject_id=c.subject_id,
        predicate=c.predicate.value,
        object_id=c.object_id,
        natural_language=c.natural_language,
        formal_statement=c.formal_statement,
        scope=c.scope,
        preconditions=c.preconditions,
        validation_state=c.validation_state.value,
        confidence=_confidence_to_out(c.confidence),
        confidence_score=c.confidence_score(),
        has_conflict=c.has_conflict(),
        conflict_explanation=_contract_conflict_explanation(c),
        provenance=_provenance_to_out(c.provenance) if c.provenance else None,
        created_at=c.created_at,
        metadata=c.metadata,
    )


def _event_to_out(e: ExecutionEvent) -> ExecutionEventOut:
    return ExecutionEventOut(
        event_id=e.event_id,
        timestamp=e.timestamp,
        execution_id=e.execution_id,
        artifact_id=e.artifact_id,
        operation=e.operation.value,
        resource=e.resource,
        predecessor_events=e.predecessor_events,
        successor_events=e.successor_events,
        return_code=e.return_code,
        source_type=e.source_type.value,
        metadata=e.metadata,
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthOut, tags=["meta"])
async def health() -> HealthOut:
    return HealthOut(
        status="ok",
        version=VERSION,
        bcg_store_count=len(_bcg_store),
    )


# ---------------------------------------------------------------------------
# BCG Summary
# ---------------------------------------------------------------------------

@app.get("/api/bcg/{bcg_id}/summary", response_model=BCGSummaryOut, tags=["bcg"])
async def get_bcg_summary(bcg_id: str) -> BCGSummaryOut:
    """Return high-level statistics for the BCG."""
    bcg = _get_bcg(bcg_id)

    contracts_by_type: dict[str, int] = {}
    contracts_by_state: dict[str, int] = {}
    for c in bcg.contracts.values():
        contracts_by_type[c.contract_type.value] = contracts_by_type.get(c.contract_type.value, 0) + 1
        contracts_by_state[c.validation_state.value] = contracts_by_state.get(c.validation_state.value, 0) + 1

    return BCGSummaryOut(
        bcg_id=bcg.bcg_id,
        created_at=bcg.created_at,
        artifact_paths=bcg.artifact_paths,
        entity_count=bcg.ir.entity_count(),
        relation_count=bcg.ir.relation_count(),
        contract_count=bcg.contract_count(),
        observation_count=bcg.observation_count(),
        dynamic_coverage_rate=bcg.dynamic_coverage_rate(),
        contracts_by_type=contracts_by_type,
        contracts_by_state=contracts_by_state,
        conflict_count=len(bcg.get_conflicts()),
        validated_count=len(bcg.validated_contracts()),
    )


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

@app.get("/api/bcg/{bcg_id}/entities", response_model=list[EntityOut], tags=["bcg"])
async def get_entities(
    bcg_id: str,
    entity_type: str | None = Query(default=None, description="Filter by entity type (e.g. JOB, STEP, DATASET)."),
) -> list[EntityOut]:
    """Return all entities (V component) from the BCG."""
    bcg = _get_bcg(bcg_id)
    entities = list(bcg.entities.values())
    if entity_type:
        entities = [e for e in entities if e.entity_type.value == entity_type.upper()]
    return [_entity_to_out(e) for e in entities]


@app.get("/api/bcg/{bcg_id}/relations", response_model=list[RelationOut], tags=["bcg"])
async def get_relations(
    bcg_id: str,
    relation_type: str | None = Query(default=None, description="Filter by relation type (e.g. CALLS, PRODUCES)."),
) -> list[RelationOut]:
    """Return all structural relations (E component) from the BCG."""
    bcg = _get_bcg(bcg_id)
    relations = list(bcg.relations)
    if relation_type:
        relations = [r for r in relations if r.relation_type.value == relation_type.upper()]
    return [_relation_to_out(r) for r in relations]


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------

@app.get("/api/bcg/{bcg_id}/contracts", response_model=list[ContractSummaryOut], tags=["contracts"])
async def get_contracts(
    bcg_id: str,
    contract_type: str | None = Query(default=None, description="Filter by contract type (TEMPORAL, RESOURCE, CONTROL_FLOW)."),
    validation_state: str | None = Query(default=None, description="Filter by validation state."),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0, description="Minimum evidence-strength score (NOT a probability filter)."),
) -> list[ContractSummaryOut]:
    """
    Return all behavioral contracts (C component) with summary provenance.

    NOTE on confidence_score: This is a normalized evidence-strength score [0,1],
    NOT a probability of contract validity. See the ConfidenceVector model.
    """
    bcg = _get_bcg(bcg_id)
    contracts = list(bcg.contracts.values())

    if contract_type:
        contracts = [c for c in contracts if c.contract_type.value == contract_type.upper()]
    if validation_state:
        contracts = [c for c in contracts if c.validation_state.value == validation_state.upper()]
    if min_confidence is not None:
        contracts = [c for c in contracts if c.confidence_score() >= min_confidence]

    return [_contract_to_summary(c) for c in contracts]


@app.get(
    "/api/bcg/{bcg_id}/contracts/{contract_id}",
    response_model=ContractDetailOut,
    tags=["contracts"],
)
async def get_contract_detail(bcg_id: str, contract_id: str) -> ContractDetailOut:
    """
    Return full contract detail including complete evidence chain.

    If has_conflict=True, conflict_explanation contains the exact
    static expectation vs. dynamic observation that disagrees.
    """
    bcg = _get_bcg(bcg_id)
    contract = bcg.get_contract(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=404,
            detail=f"Contract '{contract_id}' not found in BCG '{bcg_id}'.",
        )
    return _contract_to_detail(contract)


# ---------------------------------------------------------------------------
# Dynamic Observations
# ---------------------------------------------------------------------------

@app.get(
    "/api/bcg/{bcg_id}/observations",
    response_model=list[ExecutionEventOut],
    tags=["dynamic"],
)
async def get_observations(
    bcg_id: str,
    artifact_id: str | None = Query(default=None, description="Filter by artifact_id."),
    operation: str | None = Query(default=None, description="Filter by operation type."),
    source_type: str | None = Query(default=None, description="Filter by source type (EXECUTION, SYNTHETIC_STATIC, …)."),
) -> list[ExecutionEventOut]:
    """
    Return dynamic execution observations (D component).

    IMPORTANT: SYNTHETIC_STATIC events are clearly labeled — they must
    never be treated as real execution evidence.
    """
    bcg = _get_bcg(bcg_id)
    events = list(bcg.dynamic_observations.values())

    if artifact_id:
        events = [e for e in events if e.artifact_id == artifact_id]
    if operation:
        events = [e for e in events if e.operation.value == operation.upper()]
    if source_type:
        events = [e for e in events if e.source_type.value == source_type.upper()]

    return [_event_to_out(e) for e in sorted(events, key=lambda e: e.timestamp)]


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------

@app.get(
    "/api/bcg/{bcg_id}/conflicts",
    response_model=list[ContractDetailOut],
    tags=["contracts", "reconciliation"],
)
async def get_conflicts(bcg_id: str) -> list[ContractDetailOut]:
    """
    Return all STATIC_DYNAMIC_CONFLICT contracts.

    Each conflict is returned with full evidence chains so the UI can
    display exactly what static analysis expected versus what was observed.
    These are first-class research findings — not errors to be silently resolved.
    """
    bcg = _get_bcg(bcg_id)
    return [_contract_to_detail(c) for c in bcg.get_conflicts()]


# ---------------------------------------------------------------------------
# Risk Report
# ---------------------------------------------------------------------------

@app.get(
    "/api/bcg/{bcg_id}/risk",
    response_model=RiskReportOut,
    tags=["risk"],
)
async def get_risk_report(
    bcg_id: str,
    min_confidence: float = Query(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum evidence-strength threshold for risk inclusion.",
    ),
) -> RiskReportOut:
    """
    Return the modernization risk report.

    Every risk entry includes a full evidence chain:
    CHANGE → CONTRACT → STATIC EVIDENCE → DYNAMIC EVIDENCE →
    CONFLICT/SUPPORT → AFFECTED ARTIFACTS → CONSEQUENCE → CONFIDENCE

    No bare numeric scores are returned without an evidence chain.
    """
    bcg = _get_bcg(bcg_id)
    chains = _build_risk_chains(bcg, min_confidence)
    high_confidence = [c for c in chains if c.confidence_score >= 0.7]

    return RiskReportOut(
        bcg_id=bcg_id,
        generated_at=datetime.utcnow(),
        total_risks=len(chains),
        high_confidence_risks=len(high_confidence),
        evidence_chains=chains,
    )


def _build_risk_chains(bcg: BCG, min_confidence: float) -> list[RiskEvidenceChainOut]:
    """
    Build risk evidence chains from BCG contracts.

    Risk sources:
    1. STATIC_DYNAMIC_CONFLICT contracts — known disagreement between static and dynamic evidence.
    2. High-confidence STATIC_CANDIDATE contracts with no dynamic support — unvalidated obligations.
    3. Validated contracts involving a dataset/file relationship (resource risk).
    """
    chains: list[RiskEvidenceChainOut] = []

    for contract in bcg.contracts.values():
        score = contract.confidence_score()
        if score < min_confidence:
            continue

        prov = contract.provenance
        static_summary = (
            "; ".join(e.content for e in prov.static_evidence)
            if prov and prov.static_evidence
            else "No static evidence recorded."
        )
        dynamic_summary = (
            "; ".join(e.content for e in prov.dynamic_evidence)
            if prov and prov.dynamic_evidence
            else "No dynamic evidence recorded (NOT_OBSERVED ≠ CONTRADICTED)."
        )

        if contract.has_conflict():
            chains.append(RiskEvidenceChainOut(
                change_description=(
                    f"Behavioral obligation '{contract.natural_language}' "
                    "is present in static analysis but contradicted by dynamic execution evidence."
                ),
                affected_contract_id=contract.contract_id,
                affected_contract_natural_language=contract.natural_language,
                static_evidence_summary=static_summary,
                dynamic_evidence_summary=dynamic_summary,
                reconciliation_outcome="CONTRADICTED",
                affected_artifact_ids=[contract.subject_id, contract.object_id],
                potential_consequence=(
                    "If this contract is violated during modernization, "
                    "the system may produce incorrect outputs or fail silently. "
                    "Requires human review to confirm whether static or dynamic evidence is authoritative."
                ),
                confidence_score=score,
                validation_state=contract.validation_state.value,
            ))

        elif contract.validation_state == ValidationState.STATIC_CANDIDATE and score >= 0.4:
            chains.append(RiskEvidenceChainOut(
                change_description=(
                    f"Behavioral obligation '{contract.natural_language}' "
                    "was inferred statically but has not been confirmed by execution evidence."
                ),
                affected_contract_id=contract.contract_id,
                affected_contract_natural_language=contract.natural_language,
                static_evidence_summary=static_summary,
                dynamic_evidence_summary="NOT_OBSERVED — no execution evidence available for this contract.",
                reconciliation_outcome="UNOBSERVED",
                affected_artifact_ids=[contract.subject_id, contract.object_id],
                potential_consequence=(
                    "Modernization of these artifacts may silently violate this unvalidated obligation. "
                    "Execution traces are needed to confirm or refute this contract before modernizing."
                ),
                confidence_score=score,
                validation_state=contract.validation_state.value,
            ))

        elif contract.validation_state == ValidationState.STATIC_DYNAMIC_SUPPORTED and score >= 0.6:
            chains.append(RiskEvidenceChainOut(
                change_description=(
                    f"Validated behavioral obligation '{contract.natural_language}' "
                    "must be preserved during modernization."
                ),
                affected_contract_id=contract.contract_id,
                affected_contract_natural_language=contract.natural_language,
                static_evidence_summary=static_summary,
                dynamic_evidence_summary=dynamic_summary,
                reconciliation_outcome="SUPPORTED",
                affected_artifact_ids=[contract.subject_id, contract.object_id],
                potential_consequence=(
                    "Any modernization change that alters the relationship between "
                    f"'{contract.subject_id}' and '{contract.object_id}' must preserve this contract."
                ),
                confidence_score=score,
                validation_state=contract.validation_state.value,
            ))

    chains.sort(key=lambda c: c.confidence_score, reverse=True)
    return chains


# ---------------------------------------------------------------------------
# Modernization Diff
# ---------------------------------------------------------------------------

@app.get(
    "/api/bcg/{bcg_id}/diff",
    response_model=ModernizationDiffOut,
    tags=["diff"],
)
async def get_modernization_diff(
    bcg_id: str,
    modernized_bcg_id: str | None = Query(
        default=None,
        description=(
            "BCG ID of the modernized system. If not provided, "
            "the endpoint returns the current BCG's contract inventory "
            "without comparison (no diff computed)."
        ),
    ),
) -> ModernizationDiffOut:
    """
    Return the modernization diff between original and modernized BCGs.

    BROKEN contracts are CANDIDATES for semantic regression.
    They require execution oracle or human validation to confirm actual regression.
    """
    bcg = _get_bcg(bcg_id)

    if modernized_bcg_id is None:
        # Return current BCG contracts labeled as PRESERVED (baseline view)
        items = [
            ContractDiffItemOut(
                contract_id=c.contract_id,
                contract_type=c.contract_type.value,
                natural_language=c.natural_language,
                validation_state=c.validation_state.value,
                confidence_score=c.confidence_score(),
                diff_category="PRESERVED",
            )
            for c in bcg.contracts.values()
        ]
        return ModernizationDiffOut(
            bcg_id=bcg_id,
            original_artifact_count=len(bcg.artifact_paths),
            modernized_artifact_count=0,
            preserved_count=len(items),
            broken_count=0,
            added_count=0,
            regression_candidate_count=0,
            contracts=items,
        )

    modernized_bcg = _bcg_store.get(modernized_bcg_id)
    if modernized_bcg is None:
        raise HTTPException(
            status_code=404,
            detail=f"Modernized BCG '{modernized_bcg_id}' not found.",
        )

    diff: BCGDiff = bcg.diff(modernized_bcg)
    items: list[ContractDiffItemOut] = []

    for c in diff.preserved:
        items.append(ContractDiffItemOut(
            contract_id=c.contract_id,
            contract_type=c.contract_type.value,
            natural_language=c.natural_language,
            validation_state=c.validation_state.value,
            confidence_score=c.confidence_score(),
            diff_category="PRESERVED",
        ))
    for c in diff.broken:
        items.append(ContractDiffItemOut(
            contract_id=c.contract_id,
            contract_type=c.contract_type.value,
            natural_language=c.natural_language,
            validation_state=c.validation_state.value,
            confidence_score=c.confidence_score(),
            diff_category="BROKEN",
        ))
    for c in diff.added:
        items.append(ContractDiffItemOut(
            contract_id=c.contract_id,
            contract_type=c.contract_type.value,
            natural_language=c.natural_language,
            validation_state=c.validation_state.value,
            confidence_score=c.confidence_score(),
            diff_category="ADDED",
        ))

    return ModernizationDiffOut(
        bcg_id=bcg_id,
        original_artifact_count=len(bcg.artifact_paths),
        modernized_artifact_count=len(modernized_bcg.artifact_paths),
        preserved_count=len(diff.preserved),
        broken_count=len(diff.broken),
        added_count=len(diff.added),
        regression_candidate_count=len(diff.regression_candidates()),
        contracts=items,
    )


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

@app.post("/api/ingest", response_model=IngestResponse, status_code=201, tags=["ingest"])
async def ingest_artifacts(request: IngestRequest) -> IngestResponse:
    """
    Ingest legacy artifacts and build a BCG.

    In the research prototype, this endpoint invokes the ingestion pipeline.
    For MVP, it builds a BCG from the specified artifact paths using the
    static analysis and dynamic trace adapters.

    Returns the BCG ID for subsequent API calls.
    """
    bcg_id = request.bcg_id or str(uuid.uuid4())[:8]
    warnings: list[str] = []
    errors: list[str] = []

    # In a full pipeline integration this would call:
    #   from legacy_contract.ingestion.pipeline import IngestionPipeline
    #   pipeline = IngestionPipeline(...)
    #   bcg = pipeline.run(artifact_paths, trace_paths)
    # For MVP we build a skeleton BCG to confirm the API is wired up.
    try:
        bcg = _build_bcg_from_paths(bcg_id, request.artifact_paths, request.trace_paths)
        _bcg_store[bcg_id] = bcg
        if not request.artifact_paths:
            warnings.append("No artifact paths provided; empty BCG created.")
        if not request.trace_paths:
            warnings.append(
                "No execution trace paths provided. All contracts will be STATIC_CANDIDATE. "
                "Dynamic evidence is required for STATIC_DYNAMIC_SUPPORTED validation."
            )
        logger.info(f"Ingested BCG {bcg_id}: {bcg.summary()}")
    except Exception as exc:
        logger.exception(f"Ingestion failed for BCG {bcg_id}: {exc}")
        errors.append(str(exc))
        return IngestResponse(
            bcg_id=bcg_id,
            status="error",
            entity_count=0,
            relation_count=0,
            contract_count=0,
            observation_count=0,
            warnings=warnings,
            errors=errors,
        )

    return IngestResponse(
        bcg_id=bcg_id,
        status="ok",
        entity_count=bcg.ir.entity_count(),
        relation_count=bcg.ir.relation_count(),
        contract_count=bcg.contract_count(),
        observation_count=bcg.observation_count(),
        warnings=warnings,
        errors=errors,
    )


def _build_bcg_from_paths(
    bcg_id: str,
    artifact_paths: list[str],
    trace_paths: list[str],
) -> BCG:
    """
    Minimal BCG builder for the ingest endpoint.

    Creates artifact-level entities for each provided path.
    In the full pipeline, parsers would extract granular entities and contracts.
    """
    from legacy_contract.ir.model import IRGraph
    graph = IRGraph(artifact_paths=artifact_paths)

    for path in artifact_paths:
        entity = IREntity(
            entity_type=EntityType.ARTIFACT,
            name=path.split("/")[-1],
            artifact_path=path,
        )
        graph.add_entity(entity)

    bcg = BCG(
        ir=graph,
        bcg_id=bcg_id,
        created_at=datetime.utcnow().isoformat(),
        artifact_paths=artifact_paths,
    )
    return bcg


# ---------------------------------------------------------------------------
# Demo BCG builder (startup data)
# ---------------------------------------------------------------------------

def _build_demo_bcg() -> BCG:
    """
    Build a realistic CardDemo-inspired demo BCG so the UI renders on first load.

    Simulates: CBACT04C (account file generation) → ACCTFILE.DAT → CBACT02C (billing)
    with one STATIC_DYNAMIC_CONFLICT to demonstrate the conflict visualization.
    """
    from legacy_contract.contracts.model import (
        ContractPredicate,
        EvidenceItem,
        ExtractionMethod,
        ProvenanceRecord,
    )

    graph = IRGraph(artifact_paths=[
        "datasets/carddemo/jcl/ACCTGEN.jcl",
        "datasets/carddemo/cobol/CBACT04C.cbl",
        "datasets/carddemo/cobol/CBACT02C.cbl",
        "datasets/carddemo/cobol/CBACT01C.cbl",
        "datasets/carddemo/cobol/COACTUPC.cbl",
    ])

    # Entities
    job_acctgen = IREntity(
        entity_type=EntityType.JOB,
        name="ACCTGEN",
        artifact_path="datasets/carddemo/jcl/ACCTGEN.jcl",
        location=SourceLocation("datasets/carddemo/jcl/ACCTGEN.jcl", 1, 1),
        attributes={"description": "Account data generation job"},
    )
    step_cbact04c = IREntity(
        entity_type=EntityType.STEP,
        name="STEP010",
        artifact_path="datasets/carddemo/jcl/ACCTGEN.jcl",
        location=SourceLocation("datasets/carddemo/jcl/ACCTGEN.jcl", 5, 5),
        attributes={"pgm": "CBACT04C"},
    )
    prog_cbact04c = IREntity(
        entity_type=EntityType.PROGRAM,
        name="CBACT04C",
        artifact_path="datasets/carddemo/cobol/CBACT04C.cbl",
        location=SourceLocation("datasets/carddemo/cobol/CBACT04C.cbl", 1, 1),
        attributes={"description": "Account file creation program"},
    )
    ds_acctfile = IREntity(
        entity_type=EntityType.DATASET,
        name="ACCTFILE.DAT",
        artifact_path="datasets/carddemo/jcl/ACCTGEN.jcl",
        location=SourceLocation("datasets/carddemo/jcl/ACCTGEN.jcl", 12, 12),
        attributes={"dsn": "CARDDEMO.ACCTFILE.DAT", "disp": "NEW,CATLG,DELETE"},
    )
    step_cbact02c = IREntity(
        entity_type=EntityType.STEP,
        name="STEP020",
        artifact_path="datasets/carddemo/jcl/ACCTGEN.jcl",
        location=SourceLocation("datasets/carddemo/jcl/ACCTGEN.jcl", 20, 20),
        attributes={"pgm": "CBACT02C"},
    )
    prog_cbact02c = IREntity(
        entity_type=EntityType.PROGRAM,
        name="CBACT02C",
        artifact_path="datasets/carddemo/cobol/CBACT02C.cbl",
        location=SourceLocation("datasets/carddemo/cobol/CBACT02C.cbl", 1, 1),
        attributes={"description": "Account balance reporting program"},
    )
    prog_cbact01c = IREntity(
        entity_type=EntityType.PROGRAM,
        name="CBACT01C",
        artifact_path="datasets/carddemo/cobol/CBACT01C.cbl",
        location=SourceLocation("datasets/carddemo/cobol/CBACT01C.cbl", 1, 1),
        attributes={"description": "Account data initialization"},
    )
    prog_coactupc = IREntity(
        entity_type=EntityType.PROGRAM,
        name="COACTUPC",
        artifact_path="datasets/carddemo/cobol/COACTUPC.cbl",
        location=SourceLocation("datasets/carddemo/cobol/COACTUPC.cbl", 1, 1),
        attributes={"description": "Account update processor"},
    )
    record_acct = IREntity(
        entity_type=EntityType.RECORD,
        name="ACCOUNT-RECORD",
        artifact_path="datasets/carddemo/cobol/CBACT04C.cbl",
        attributes={"copybook": "CVACT01Y"},
    )
    field_acct_id = IREntity(
        entity_type=EntityType.FIELD,
        name="ACCT-ID",
        artifact_path="datasets/carddemo/cobol/CBACT04C.cbl",
        attributes={"pic": "9(11)", "level": "05"},
    )
    error_rc8 = IREntity(
        entity_type=EntityType.ERROR_CONDITION,
        name="RC-8-OPEN-FAILED",
        artifact_path="datasets/carddemo/cobol/CBACT04C.cbl",
        attributes={"return_code": 8},
    )

    for e in [
        job_acctgen, step_cbact04c, prog_cbact04c, ds_acctfile,
        step_cbact02c, prog_cbact02c, prog_cbact01c, prog_coactupc,
        record_acct, field_acct_id, error_rc8,
    ]:
        graph.add_entity(e)

    # Relations
    graph.add_relation(IRRelation(RelationType.CONTAINS, job_acctgen, step_cbact04c))
    graph.add_relation(IRRelation(RelationType.CONTAINS, job_acctgen, step_cbact02c))
    graph.add_relation(IRRelation(RelationType.CALLS, step_cbact04c, prog_cbact04c))
    graph.add_relation(IRRelation(RelationType.CALLS, step_cbact02c, prog_cbact02c))
    graph.add_relation(IRRelation(RelationType.PRODUCES, prog_cbact04c, ds_acctfile))
    graph.add_relation(IRRelation(RelationType.CONSUMES, prog_cbact02c, ds_acctfile))
    graph.add_relation(IRRelation(RelationType.MUST_PRECEDE, step_cbact04c, step_cbact02c))
    graph.add_relation(IRRelation(RelationType.DEFINES, prog_cbact04c, record_acct))
    graph.add_relation(IRRelation(RelationType.DEFINES, record_acct, field_acct_id))
    graph.add_relation(IRRelation(RelationType.PROPAGATES_ERROR, prog_cbact04c, error_rc8))
    graph.add_relation(IRRelation(RelationType.CALLS, prog_cbact01c, prog_cbact04c, confidence=0.9))
    graph.add_relation(IRRelation(RelationType.READS, prog_coactupc, ds_acctfile))

    bcg = BCG(
        ir=graph,
        bcg_id="demo-carddemo-v1",
        created_at=datetime.utcnow().isoformat(),
        artifact_paths=graph.artifact_paths,
    )

    # ---- Contract 1: Temporal — STEP010 must precede STEP020 ----
    prov1 = ProvenanceRecord(
        source_artifact="datasets/carddemo/jcl/ACCTGEN.jcl",
        source_location="ACCTGEN.jcl:5–25",
        extraction_method=ExtractionMethod.DETERMINISTIC,
        static_evidence=[
            EvidenceItem(
                evidence_type="static_structural",
                source_artifact="datasets/carddemo/jcl/ACCTGEN.jcl",
                source_location="line 5",
                extraction_method=ExtractionMethod.DETERMINISTIC,
                content="STEP010 declared before STEP020 in JCL job card. JCL sequential step ordering implies STEP010 ≺ STEP020.",
                formal_content="STEP010 ≺ STEP020",
            )
        ],
        dynamic_evidence=[
            EvidenceItem(
                evidence_type="dynamic_observation",
                source_artifact="traces/carddemo/ACCTGEN_run001.jsonl",
                source_location="event_seq=1,2",
                extraction_method=ExtractionMethod.EXECUTION_SIMULATED,
                content="Observed STEP010 JOB_START at T=0ms, STEP020 JOB_START at T=1240ms. Ordering confirmed.",
                formal_content="obs(STEP010) < obs(STEP020)",
            )
        ],
        timestamp=datetime.utcnow(),
        notes="CardDemo ACCTGEN job. Deterministically extracted from JCL step sequencing.",
    )
    c1_conf = ConfidenceVector(
        static_support=1.0, dynamic_support=1.0,
        cross_artifact_support=0.9, provenance_quality=1.0,
        execution_frequency=0.8, ambiguity_penalty=0.0,
    )
    from legacy_contract.contracts.model import Contract, ContractType, ContractPredicate, ValidationState
    contract1 = Contract(
        contract_type=ContractType.TEMPORAL,
        subject_id=step_cbact04c.entity_id,
        predicate=ContractPredicate.PRECEDES,
        object_id=step_cbact02c.entity_id,
        natural_language=(
            "STEP010 (CBACT04C) must complete before STEP020 (CBACT02C) begins execution "
            "within ACCTGEN job. This ordering is required because STEP020 consumes ACCTFILE.DAT "
            "which is produced by STEP010."
        ),
        formal_statement="∀ exec e: exec(STEP010, e) ≺ exec(STEP020, e)",
        scope="ACCTGEN batch job execution",
        preconditions=["ACCTGEN job is executing", "ACCTFILE.DAT does not exist at job start"],
        provenance=prov1,
        confidence=c1_conf,
        validation_state=ValidationState.STATIC_DYNAMIC_SUPPORTED,
        metadata={"extraction_phase": "Phase 6 — Static Baseline"},
    )
    bcg.add_contract(contract1)

    # ---- Contract 2: Resource — CBACT04C must produce ACCTFILE before CBACT02C consumes it ----
    prov2 = ProvenanceRecord(
        source_artifact="datasets/carddemo/jcl/ACCTGEN.jcl",
        source_location="ACCTGEN.jcl:12 (DD ACCTFILE)",
        extraction_method=ExtractionMethod.DETERMINISTIC,
        static_evidence=[
            EvidenceItem(
                evidence_type="static_structural",
                source_artifact="datasets/carddemo/jcl/ACCTGEN.jcl",
                source_location="line 12",
                extraction_method=ExtractionMethod.DETERMINISTIC,
                content=(
                    "DD ACCTFILE DISP=(NEW,CATLG,DELETE) in STEP010 creates CARDDEMO.ACCTFILE.DAT. "
                    "STEP020 DD ACCTFILE DISP=(OLD,KEEP) requires pre-existing dataset. "
                    "Static dependency: STEP010 produces ACCTFILE → STEP020 consumes ACCTFILE."
                ),
                formal_content="PRODUCES(CBACT04C, ACCTFILE) ∧ CONSUMES(CBACT02C, ACCTFILE)",
            ),
            EvidenceItem(
                evidence_type="static_structural",
                source_artifact="datasets/carddemo/cobol/CBACT04C.cbl",
                source_location="CBACT04C.cbl:WRITE ACCOUNT-RECORD",
                extraction_method=ExtractionMethod.DETERMINISTIC,
                content="CBACT04C contains WRITE ACCOUNT-RECORD to ACCTFILE in PROCEDURE DIVISION.",
                formal_content="WRITE(CBACT04C, ACCOUNT-RECORD, ACCTFILE)",
            ),
        ],
        dynamic_evidence=[],
        timestamp=datetime.utcnow(),
        notes="Resource dependency extracted from JCL DD statements and COBOL WRITE verb.",
    )
    c2_conf = ConfidenceVector(
        static_support=1.0, dynamic_support=0.0,
        cross_artifact_support=1.0, provenance_quality=0.9,
        execution_frequency=0.0, ambiguity_penalty=0.0,
    )
    contract2 = Contract(
        contract_type=ContractType.RESOURCE,
        subject_id=prog_cbact04c.entity_id,
        predicate=ContractPredicate.PRODUCES_BEFORE_CONSUMES,
        object_id=prog_cbact02c.entity_id,
        natural_language=(
            "CBACT04C must successfully produce ACCTFILE.DAT before CBACT02C attempts to consume it. "
            "If CBACT04C fails (RC ≥ 4) and ACCTFILE.DAT is not produced, CBACT02C must not execute."
        ),
        formal_statement="PRODUCES(CBACT04C, ACCTFILE.DAT) ≺ CONSUMES(CBACT02C, ACCTFILE.DAT)",
        scope="ACCTGEN batch job — within a single job execution",
        preconditions=["CBACT04C returns RC=0"],
        provenance=prov2,
        confidence=c2_conf,
        validation_state=ValidationState.NOT_OBSERVED,
        metadata={"extraction_phase": "Phase 6 — Static Baseline"},
    )
    bcg.add_contract(contract2)

    # ---- Contract 3: STATIC_DYNAMIC_CONFLICT — demonstrates conflict visualization ----
    prov3 = ProvenanceRecord(
        source_artifact="datasets/carddemo/cobol/CBACT01C.cbl",
        source_location="CBACT01C.cbl:PROCEDURE DIVISION",
        extraction_method=ExtractionMethod.COMBINED,
        static_evidence=[
            EvidenceItem(
                evidence_type="static_structural",
                source_artifact="datasets/carddemo/cobol/CBACT01C.cbl",
                source_location="CBACT01C.cbl:155",
                extraction_method=ExtractionMethod.DETERMINISTIC,
                content=(
                    "CBACT01C CALL 'CBACT04C' found at line 155. "
                    "Static analysis infers CBACT01C must complete initialization before CBACT04C is called."
                ),
                formal_content="PRECEDES(CBACT01C-INIT, CBACT04C-CALL)",
            ),
        ],
        dynamic_evidence=[
            EvidenceItem(
                evidence_type="dynamic_observation",
                source_artifact="traces/carddemo/CBACT01C_run002.jsonl",
                source_location="event_seq=3",
                extraction_method=ExtractionMethod.EXECUTION_SIMULATED,
                content=(
                    "EXECUTION TRACE: CBACT04C invoked at T=120ms before CBACT01C "
                    "initialization paragraph completed (T=340ms). "
                    "Observed ordering contradicts static expectation."
                ),
                formal_content="obs(CBACT04C-CALL) < obs(CBACT01C-INIT-COMPLETE)",
            ),
        ],
        timestamp=datetime.utcnow(),
        notes=(
            "CONFLICT: This contract was inferred statically from a CALL statement, "
            "but execution traces show the called program ran before the caller's "
            "initialization completed. Possible causes: (1) parser misidentified the "
            "initialization paragraph boundary, (2) the execution trace captured a "
            "different execution path, (3) the CALL is conditional. Requires human review."
        ),
    )
    c3_conf = ConfidenceVector(
        static_support=0.7, dynamic_support=0.6,
        cross_artifact_support=0.5, provenance_quality=0.8,
        execution_frequency=0.5, ambiguity_penalty=0.3,
    )
    contract3 = Contract(
        contract_type=ContractType.CONTROL_FLOW,
        subject_id=prog_cbact01c.entity_id,
        predicate=ContractPredicate.PRECEDES,
        object_id=prog_cbact04c.entity_id,
        natural_language=(
            "CBACT01C initialization must complete before CBACT04C is invoked. "
            "[CONFLICT] Static analysis found a CALL at line 155 implying this ordering, "
            "but execution traces observed CBACT04C running before CBACT01C initialization completed."
        ),
        formal_statement="PRECEDES(CBACT01C-INIT-COMPLETE, CALL(CBACT04C))",
        scope="CBACT01C PROCEDURE DIVISION",
        provenance=prov3,
        confidence=c3_conf,
        validation_state=ValidationState.STATIC_DYNAMIC_CONFLICT,
        metadata={
            "conflict_category": "static_false_positive_candidate",
            "requires_human_review": True,
            "extraction_phase": "Phase 8 — Reconciliation",
        },
    )
    bcg.add_contract(contract3)

    # ---- Contract 4: Control-flow — error propagation ----
    prov4 = ProvenanceRecord(
        source_artifact="datasets/carddemo/jcl/ACCTGEN.jcl",
        source_location="ACCTGEN.jcl:STEP010 COND=",
        extraction_method=ExtractionMethod.DETERMINISTIC,
        static_evidence=[
            EvidenceItem(
                evidence_type="static_structural",
                source_artifact="datasets/carddemo/jcl/ACCTGEN.jcl",
                source_location="line 22",
                extraction_method=ExtractionMethod.DETERMINISTIC,
                content=(
                    "JCL COND=(4,LT,STEP010) on STEP020: if STEP010 return code < 4 is false "
                    "(i.e. RC ≥ 4), STEP020 is bypassed. "
                    "Error propagation: STEP010 failure must suppress STEP020 execution."
                ),
                formal_content="RC(STEP010) >= 4 → ¬EXECUTE(STEP020)",
            ),
        ],
        dynamic_evidence=[
            EvidenceItem(
                evidence_type="dynamic_observation",
                source_artifact="traces/carddemo/ACCTGEN_rc4_run003.jsonl",
                source_location="event_seq=5",
                extraction_method=ExtractionMethod.EXECUTION_SIMULATED,
                content="Injected RC=8 for STEP010; STEP020 was correctly bypassed. Error propagation confirmed.",
                formal_content="obs(RC(STEP010)=8) → ¬obs(STEP020-EXECUTE)",
            ),
        ],
        timestamp=datetime.utcnow(),
    )
    c4_conf = ConfidenceVector(
        static_support=1.0, dynamic_support=0.9,
        cross_artifact_support=0.8, provenance_quality=1.0,
        execution_frequency=0.6, ambiguity_penalty=0.0,
    )
    contract4 = Contract(
        contract_type=ContractType.CONTROL_FLOW,
        subject_id=step_cbact04c.entity_id,
        predicate=ContractPredicate.MUST_NOT_FOLLOW_ON_ERROR,
        object_id=step_cbact02c.entity_id,
        natural_language=(
            "If STEP010 (CBACT04C) returns RC ≥ 4, STEP020 (CBACT02C) must NOT execute. "
            "This error-propagation contract prevents consuming a potentially corrupt ACCTFILE.DAT."
        ),
        formal_statement="RC(STEP010) ≥ 4 → ¬EXECUTE(STEP020)",
        scope="ACCTGEN batch job error handling",
        preconditions=["STEP010 is executing"],
        provenance=prov4,
        confidence=c4_conf,
        validation_state=ValidationState.STATIC_DYNAMIC_SUPPORTED,
        metadata={"extraction_phase": "Phase 6"},
    )
    bcg.add_contract(contract4)

    # ---- Contract 5: Static candidate — account update ordering ----
    prov5 = ProvenanceRecord(
        source_artifact="datasets/carddemo/cobol/COACTUPC.cbl",
        source_location="COACTUPC.cbl:READ ACCTFILE",
        extraction_method=ExtractionMethod.DETERMINISTIC,
        static_evidence=[
            EvidenceItem(
                evidence_type="static_structural",
                source_artifact="datasets/carddemo/cobol/COACTUPC.cbl",
                source_location="COACTUPC.cbl:READ ACCTFILE",
                extraction_method=ExtractionMethod.DETERMINISTIC,
                content=(
                    "COACTUPC opens and reads ACCTFILE.DAT. "
                    "ACCTFILE.DAT must be present (produced by CBACT04C) before COACTUPC runs."
                ),
                formal_content="REQUIRES(COACTUPC, ACCTFILE.DAT) ← PRODUCES(CBACT04C, ACCTFILE.DAT)",
            ),
        ],
        dynamic_evidence=[],
        timestamp=datetime.utcnow(),
        notes="Static candidate — no execution trace available for COACTUPC. NOT_OBSERVED ≠ CONTRADICTED.",
    )
    c5_conf = ConfidenceVector(
        static_support=0.8, dynamic_support=0.0,
        cross_artifact_support=0.6, provenance_quality=0.7,
        execution_frequency=0.0, ambiguity_penalty=0.1,
    )
    contract5 = Contract(
        contract_type=ContractType.RESOURCE,
        subject_id=prog_cbact04c.entity_id,
        predicate=ContractPredicate.MUST_PRECEDE_FOR_RESOURCE,
        object_id=prog_coactupc.entity_id,
        natural_language=(
            "CBACT04C must produce ACCTFILE.DAT before COACTUPC (account update processor) "
            "attempts to read it. No execution evidence is available to validate this ordering. "
            "NOT_OBSERVED — this contract is a static candidate only."
        ),
        formal_statement="PRODUCES(CBACT04C, ACCTFILE.DAT) ≺ READ(COACTUPC, ACCTFILE.DAT)",
        scope="Any execution involving COACTUPC",
        preconditions=["CBACT04C has run successfully"],
        provenance=prov5,
        confidence=c5_conf,
        validation_state=ValidationState.STATIC_CANDIDATE,
        metadata={"extraction_phase": "Phase 6"},
    )
    bcg.add_contract(contract5)

    # ---- Dynamic observations ----
    t0 = datetime(2024, 1, 15, 9, 0, 0)
    events = [
        ExecutionEvent(
            event_id="evt-001",
            timestamp=datetime(2024, 1, 15, 9, 0, 0),
            execution_id="run-001",
            artifact_id=step_cbact04c.entity_id,
            operation=OperationType.STEP_START,
            resource="ACCTGEN.STEP010",
            predecessor_events=[],
            successor_events=["evt-002"],
            return_code=None,
            source_type=EventSourceType.EXECUTION_SIMULATED,
            metadata={"job": "ACCTGEN", "step": "STEP010"},
        ),
        ExecutionEvent(
            event_id="evt-002",
            timestamp=datetime(2024, 1, 15, 9, 0, 1),
            execution_id="run-001",
            artifact_id=prog_cbact04c.entity_id,
            operation=OperationType.EXECUTE,
            resource="CBACT04C",
            predecessor_events=["evt-001"],
            successor_events=["evt-003"],
            return_code=None,
            source_type=EventSourceType.EXECUTION_SIMULATED,
        ),
        ExecutionEvent(
            event_id="evt-003",
            timestamp=datetime(2024, 1, 15, 9, 0, 2),
            execution_id="run-001",
            artifact_id=prog_cbact04c.entity_id,
            operation=OperationType.PRODUCE,
            resource="ACCTFILE.DAT",
            predecessor_events=["evt-002"],
            successor_events=["evt-004"],
            return_code=None,
            source_type=EventSourceType.EXECUTION_SIMULATED,
            metadata={"records_written": 1000},
        ),
        ExecutionEvent(
            event_id="evt-004",
            timestamp=datetime(2024, 1, 15, 9, 0, 3),
            execution_id="run-001",
            artifact_id=step_cbact04c.entity_id,
            operation=OperationType.STEP_END,
            resource="ACCTGEN.STEP010",
            predecessor_events=["evt-003"],
            successor_events=["evt-005"],
            return_code=0,
            source_type=EventSourceType.EXECUTION_SIMULATED,
        ),
        ExecutionEvent(
            event_id="evt-005",
            timestamp=datetime(2024, 1, 15, 9, 0, 4),
            execution_id="run-001",
            artifact_id=step_cbact02c.entity_id,
            operation=OperationType.STEP_START,
            resource="ACCTGEN.STEP020",
            predecessor_events=["evt-004"],
            successor_events=["evt-006"],
            return_code=None,
            source_type=EventSourceType.EXECUTION_SIMULATED,
        ),
        ExecutionEvent(
            event_id="evt-006",
            timestamp=datetime(2024, 1, 15, 9, 0, 5),
            execution_id="run-001",
            artifact_id=prog_cbact02c.entity_id,
            operation=OperationType.CONSUME,
            resource="ACCTFILE.DAT",
            predecessor_events=["evt-005"],
            successor_events=["evt-007"],
            return_code=None,
            source_type=EventSourceType.EXECUTION_SIMULATED,
            metadata={"records_read": 1000},
        ),
        ExecutionEvent(
            event_id="evt-007",
            timestamp=datetime(2024, 1, 15, 9, 0, 6),
            execution_id="run-001",
            artifact_id=step_cbact02c.entity_id,
            operation=OperationType.STEP_END,
            resource="ACCTGEN.STEP020",
            predecessor_events=["evt-006"],
            successor_events=[],
            return_code=0,
            source_type=EventSourceType.EXECUTION_SIMULATED,
        ),
        # Conflict-related event
        ExecutionEvent(
            event_id="evt-101",
            timestamp=datetime(2024, 1, 15, 9, 2, 0),
            execution_id="run-002",
            artifact_id=prog_cbact04c.entity_id,
            operation=OperationType.EXECUTE,
            resource="CBACT04C",
            predecessor_events=[],
            successor_events=["evt-102"],
            return_code=None,
            source_type=EventSourceType.EXECUTION_SIMULATED,
            metadata={"note": "CBACT04C invoked before CBACT01C init complete — conflict event"},
        ),
        ExecutionEvent(
            event_id="evt-102",
            timestamp=datetime(2024, 1, 15, 9, 2, 2),
            execution_id="run-002",
            artifact_id=prog_cbact01c.entity_id,
            operation=OperationType.INITIALIZE,
            resource="CBACT01C-INIT",
            predecessor_events=["evt-101"],
            successor_events=[],
            return_code=0,
            source_type=EventSourceType.EXECUTION_SIMULATED,
            metadata={"note": "CBACT01C init completed AFTER CBACT04C call — static/dynamic conflict"},
        ),
    ]

    for evt in events:
        bcg.add_observation(evt)

    return bcg
