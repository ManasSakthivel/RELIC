"""
Dynamic analysis components for the LEGACY-CONTRACT BCG pipeline.

Public API:
    ArtifactMapper        — deterministic program→step mapping (C1 fix, wired)
    ArtifactMappingResult — result of a single resolve() call
    MappingStatus         — EXACT / AMBIGUOUS / MISSING / PROC_EXPANDED / UNMAPPED_EVENT
    ExecutionEvent        — normalized runtime observation
    ExecutionTrace        — collection of events from one run
    EventSourceType       — EXECUTION / EXECUTION_SIMULATED / SYNTHETIC_STATIC / HUMAN
    OperationType         — operation type enum
"""
from legacy_contract.dynamic_analysis.artifact_mapping import (
    ArtifactMapper,
    ArtifactMappingResult,
    MappingStatus,
)
from legacy_contract.dynamic_analysis.model import (
    EventSourceType,
    ExecutionEvent,
    ExecutionTrace,
    OperationType,
)

__all__ = [
    "ArtifactMapper",
    "ArtifactMappingResult",
    "MappingStatus",
    "EventSourceType",
    "ExecutionEvent",
    "ExecutionTrace",
    "OperationType",
]
