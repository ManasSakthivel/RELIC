"""
Dynamic evidence model.

ExecutionEvent is the normalized representation of any runtime observation,
regardless of source (GnuCOBOL, JCL simulation, synthetic).

SCIENTIFIC INTEGRITY RULES:
- source_type must be set correctly — NEVER use EXECUTION for synthetic traces
- predecessor_events / successor_events capture observed ordering (not inferred)
- return_code = None means "not captured", NOT "zero / success"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class OperationType(str, Enum):
    """Types of operations that can appear in execution events."""
    READ = "READ"
    WRITE = "WRITE"
    CALL = "CALL"
    PERFORM = "PERFORM"
    PRODUCE = "PRODUCE"       # File/dataset created
    CONSUME = "CONSUME"       # File/dataset read by consumer
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    EXECUTE = "EXECUTE"       # Program execution start
    RETURN = "RETURN"         # Program/step return
    INITIALIZE = "INITIALIZE"
    ERROR = "ERROR"
    JOB_START = "JOB_START"
    JOB_END = "JOB_END"
    STEP_START = "STEP_START"
    STEP_END = "STEP_END"
    FILE_ACCESS = "FILE_ACCESS"
    DATABASE_ACCESS = "DATABASE_ACCESS"


class EventSourceType(str, Enum):
    """
    Source of the execution event.
    MUST be accurate — never label SYNTHETIC_STATIC as EXECUTION.
    """
    EXECUTION = "EXECUTION"                     # Real execution (GnuCOBOL)
    EXECUTION_SIMULATED = "EXECUTION_SIMULATED" # JCL batch simulation
    SYNTHETIC_STATIC = "SYNTHETIC_STATIC"       # Statically derived
    HUMAN = "HUMAN"                             # Human trace reconstruction


@dataclass
class ExecutionEvent:
    """
    Normalized execution event from any dynamic evidence source.

    Schema justification:
    - event_id: unique per event for deduplication
    - execution_id: groups events from the same execution run
    - artifact_id: links to BCG entity_id
    - predecessor_events: observed ordering (not inferred)
    - source_type: mandatory provenance for dynamic evidence
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    execution_id: str = ""              # Groups events from same run
    artifact_id: str = ""              # BCG entity_id of the artifact
    operation: OperationType = OperationType.EXECUTE
    resource: str | None = None        # File, dataset, program, or None
    predecessor_events: list[str] = field(default_factory=list)   # event_ids
    successor_events: list[str] = field(default_factory=list)     # event_ids
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    return_code: int | None = None     # None = not captured, NOT zero
    source_type: EventSourceType = EventSourceType.EXECUTION
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.event_id)

    def is_real_execution(self) -> bool:
        """True only for real or simulated execution, not synthetic."""
        return self.source_type in {
            EventSourceType.EXECUTION,
            EventSourceType.EXECUTION_SIMULATED,
        }

    def summary(self) -> str:
        return (
            f"[{self.source_type.value}] "
            f"{self.operation.value} {self.artifact_id} "
            f"resource={self.resource} rc={self.return_code} "
            f"t={self.timestamp.isoformat()}"
        )


# ---------------------------------------------------------------------------
# Execution Trace (collection of events from one run)
# ---------------------------------------------------------------------------

@dataclass
class ExecutionTrace:
    """
    A complete execution trace from a single run.
    Multiple traces can be associated with a BCG for coverage analysis.
    """
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = ""
    source_type: EventSourceType = EventSourceType.EXECUTION
    events: list[ExecutionEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_event(self, event: ExecutionEvent) -> None:
        self.events.append(event)

    def get_events_for_artifact(self, artifact_id: str) -> list[ExecutionEvent]:
        return [e for e in self.events if e.artifact_id == artifact_id]

    def get_events_by_operation(self, op: OperationType) -> list[ExecutionEvent]:
        return [e for e in self.events if e.operation == op]

    def event_count(self) -> int:
        return len(self.events)

    def ordered_events(self) -> list[ExecutionEvent]:
        """Events sorted by timestamp."""
        return sorted(self.events, key=lambda e: e.timestamp)

    def artifacts_observed(self) -> set[str]:
        """Set of artifact_ids that appear in this trace."""
        return {e.artifact_id for e in self.events if e.artifact_id}
