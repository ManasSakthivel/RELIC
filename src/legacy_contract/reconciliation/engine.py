"""
Static/Dynamic Reconciliation Engine.

This module is a CORE RESEARCH COMPONENT.

For each static candidate contract, it checks all available dynamic observations
and determines a reconciled validation state and updated confidence.

Reconciliation outcomes per contract:
- SUPPORTED: dynamic observations are consistent with the contract
- CONTRADICTED: at least one observation violates the contract predicate
- NOT_OBSERVED: no relevant dynamic observations found
- PARTIALLY_SUPPORTED: some observations support, but coverage is incomplete
- AMBIGUOUS: insufficient evidence to determine support or contradiction

Conflict taxonomy:
- STATIC_FALSE_POSITIVE: inferred contract contradicted by execution
- DYNAMIC_INCOMPLETE: contract may be real but path not covered in traces
- HIDDEN_STATE: environment dependency
- INSTRUMENTATION_LIMIT: trace capture missed the event
- PARSER_LIMIT: static parser missed a structural element

SCIENTIFIC PRINCIPLE: NOT_OBSERVED ≠ CONTRADICTED
If no dynamic evidence is available for a contract, the contract is NOT_OBSERVED,
not CONTRADICTED. The absence of evidence is not evidence of absence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from loguru import logger

from legacy_contract.contracts.model import (
    Contract,
    ContractPredicate,
    ContractType,
    EvidenceItem,
    ExtractionMethod,
    ValidationState,
)
from legacy_contract.dynamic_analysis.model import (
    ExecutionEvent,
    ExecutionTrace,
    OperationType,
)
from legacy_contract.bcg.model import BCG


# ---------------------------------------------------------------------------
# Reconciliation outcome
# ---------------------------------------------------------------------------

class ReconciliationOutcome(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_OBSERVED = "NOT_OBSERVED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    AMBIGUOUS = "AMBIGUOUS"
    # --- Extended states (Phase 3 additions) ---
    # INSUFFICIENT_EVIDENCE: events were found but too few to make any determination
    # (e.g. a single event for a contract requiring a pair)
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    # ENVIRONMENT_DEPENDENT: reconciliation result depends on non-observable
    # environmental state (e.g. shared files, external triggers)
    ENVIRONMENT_DEPENDENT = "ENVIRONMENT_DEPENDENT"
    # EXECUTION_ERROR: the execution trace itself contains an error marker that
    # prevents reliable reconciliation (instrumentation fault, abend, etc.)
    EXECUTION_ERROR = "EXECUTION_ERROR"


class ConflictClass(str, Enum):
    STATIC_FALSE_POSITIVE = "STATIC_FALSE_POSITIVE"
    DYNAMIC_INCOMPLETE = "DYNAMIC_INCOMPLETE"
    HIDDEN_STATE = "HIDDEN_STATE"
    INSTRUMENTATION_LIMIT = "INSTRUMENTATION_LIMIT"
    PARSER_LIMIT = "PARSER_LIMIT"
    UNKNOWN = "UNKNOWN"
    # --- Extended classes (Phase 3 additions) ---
    INSUFFICIENT_EVENTS = "INSUFFICIENT_EVENTS"
    EXECUTION_FAULT = "EXECUTION_FAULT"


@dataclass
class ReconciliationRecord:
    """Full reconciliation result for one contract."""
    contract_id: str
    outcome: ReconciliationOutcome
    supporting_events: list[str] = field(default_factory=list)   # event_ids
    violating_events: list[str] = field(default_factory=list)    # event_ids
    conflict_class: ConflictClass | None = None
    dynamic_support_score: float = 0.0
    execution_frequency: float = 0.0
    notes: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    # metadata carries flags such as all_synthetic=True for integrity guards
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Reconciliation Engine
# ---------------------------------------------------------------------------

class ReconciliationEngine:
    """
    Reconciles static contract candidates against dynamic execution observations.

    Algorithm per contract c:
    1. Find dynamic events relevant to c (events for subject and object artifacts)
    2. Evaluate events against c.predicate semantics
    3. Determine reconciliation outcome
    4. Update c.validation_state and c.confidence.dynamic_support
    5. Produce ReconciliationRecord
    """

    def reconcile(
        self,
        bcg: BCG,
        traces: list[ExecutionTrace],
    ) -> list[ReconciliationRecord]:
        """
        Run reconciliation for all contracts in BCG against provided traces.
        Modifies BCG contracts in-place (updates validation_state, confidence).
        Returns list of ReconciliationRecord for analysis.
        """
        records: list[ReconciliationRecord] = []

        # Build lookup: artifact_id -> list of events
        # Also track whether every event for each artifact_id is synthetic.
        artifact_events: dict[str, list[ExecutionEvent]] = {}
        # artifact_id -> True if ALL events for it came from non-real sources
        artifact_all_synthetic: dict[str, bool] = {}
        for trace in traces:
            for event in trace.events:
                if event.artifact_id:
                    artifact_events.setdefault(event.artifact_id, []).append(event)
                    prev = artifact_all_synthetic.get(event.artifact_id, True)
                    artifact_all_synthetic[event.artifact_id] = (
                        prev and not event.is_real_execution()
                    )

        total_events = sum(len(v) for v in artifact_events.values())
        logger.info(
            f"Reconciliation: {len(bcg.contracts)} contracts, "
            f"{len(traces)} traces, {total_events} events"
        )

        for contract in bcg.contracts.values():
            # SCIENTIFIC INTEGRITY (SI-01): pre-compute whether ALL contributing
            # events for this contract are synthetic BEFORE running reconciliation.
            # This flag is passed into _reconcile_contract so the reconciliation
            # logic itself can gate SUPPORTED outcomes, not just _update_contract.
            subj_synthetic = artifact_all_synthetic.get(contract.subject_id, True)
            obj_synthetic = artifact_all_synthetic.get(contract.object_id, True)
            all_synthetic_pre = subj_synthetic and obj_synthetic
            record = self._reconcile_contract(
                contract, artifact_events, traces, all_synthetic=all_synthetic_pre
            )
            records.append(record)
            self._update_contract(contract, record)

        # Summary
        outcome_counts: dict[str, int] = {}
        for r in records:
            outcome_counts[r.outcome.value] = outcome_counts.get(r.outcome.value, 0) + 1
        logger.info(f"Reconciliation results: {outcome_counts}")

        return records

    def _reconcile_contract(
        self,
        contract: Contract,
        artifact_events: dict[str, list[ExecutionEvent]],
        traces: list[ExecutionTrace],
        *,
        all_synthetic: bool = False,
    ) -> ReconciliationRecord:
        """Reconcile a single contract.

        Args:
            all_synthetic: If True, ALL events for this contract's subject and
                object artifacts are from synthetic sources (SYNTHETIC_STATIC).
                In that case a SUPPORTED outcome is demoted to NOT_OBSERVED per
                SI-01 (synthetic traces must not promote contracts to
                STATIC_DYNAMIC_SUPPORTED).
        """
        subject_events = artifact_events.get(contract.subject_id, [])
        object_events = artifact_events.get(contract.object_id, [])

        if not subject_events and not object_events:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.NOT_OBSERVED,
                notes="No dynamic observations for either subject or object artifact.",
                conflict_class=ConflictClass.DYNAMIC_INCOMPLETE,
            )

        if contract.predicate == ContractPredicate.PRECEDES:
            record = self._reconcile_precedes(
                contract, subject_events, object_events
            )
        elif contract.predicate == ContractPredicate.PRODUCES_BEFORE_CONSUMES:
            record = self._reconcile_produces_before_consumes(
                contract, subject_events, object_events
            )
        elif contract.predicate == ContractPredicate.MUST_NOT_FOLLOW_ON_ERROR:
            record = self._reconcile_must_not_follow_on_error(
                contract, subject_events, object_events
            )
        else:
            record = ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.AMBIGUOUS,
                notes=f"No reconciliation logic for predicate {contract.predicate.value}",
            )

        # SCIENTIFIC INTEGRITY (SI-01): if every event was from a synthetic
        # source, a SUPPORTED outcome must NOT be treated as dynamic validation.
        # Demote to NOT_OBSERVED and record the reason so reviewers can audit.
        if all_synthetic and record.outcome == ReconciliationOutcome.SUPPORTED:
            record.outcome = ReconciliationOutcome.NOT_OBSERVED
            record.metadata["all_synthetic"] = True
            record.notes = (
                "[SI-01] All contributing events are synthetic (SYNTHETIC_STATIC). "
                "SUPPORTED outcome demoted to NOT_OBSERVED — synthetic traces "
                "cannot promote a contract to STATIC_DYNAMIC_SUPPORTED. "
                f"Original note: {record.notes}"
            )
            record.conflict_class = ConflictClass.DYNAMIC_INCOMPLETE

        return record

    def _reconcile_precedes(
        self,
        contract: Contract,
        subject_events: list[ExecutionEvent],
        object_events: list[ExecutionEvent],
    ) -> ReconciliationRecord:
        """
        TEMPORAL: A ≺ B
        Check: all A-execution events precede all B-execution events in timestamp order.
        """
        a_exec = [
            e for e in subject_events
            if e.operation in {OperationType.JOB_START, OperationType.STEP_START, OperationType.EXECUTE}
        ]
        b_exec = [
            e for e in object_events
            if e.operation in {OperationType.JOB_START, OperationType.STEP_START, OperationType.EXECUTE}
        ]

        if not a_exec or not b_exec:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.NOT_OBSERVED,
                notes="Execution events for subject or object not observed.",
                conflict_class=ConflictClass.DYNAMIC_INCOMPLETE,
            )

        a_last = max(e.timestamp for e in a_exec)
        b_first = min(e.timestamp for e in b_exec)

        supporting = [e.event_id for e in a_exec] + [e.event_id for e in b_exec]

        if a_last < b_first:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.SUPPORTED,
                supporting_events=supporting,
                dynamic_support_score=1.0,
                execution_frequency=1.0,
                notes=f"A last at {a_last}, B first at {b_first} — ordering satisfied.",
            )
        else:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.CONTRADICTED,
                violating_events=supporting,
                conflict_class=ConflictClass.STATIC_FALSE_POSITIVE,
                notes=(
                    f"CONFLICT: A last at {a_last}, B first at {b_first} — "
                    f"ordering violated. Static contract contradicted by execution."
                ),
            )

    def _reconcile_produces_before_consumes(
        self,
        contract: Contract,
        subject_events: list[ExecutionEvent],
        object_events: list[ExecutionEvent],
    ) -> ReconciliationRecord:
        """
        RESOURCE: produces(A, R) ≺ consumes(B, R)
        Check: A's PRODUCE event for resource R precedes B's CONSUME event for R.
        """
        dataset_id = contract.metadata.get("dataset", "")

        produce_events = [
            e for e in subject_events
            if e.operation in {OperationType.PRODUCE, OperationType.WRITE, OperationType.JOB_END, OperationType.STEP_END}
            and (not dataset_id or e.resource == dataset_id or e.resource is None)
        ]
        consume_events = [
            e for e in object_events
            if e.operation in {OperationType.CONSUME, OperationType.READ, OperationType.OPEN, OperationType.STEP_START}
            and (not dataset_id or e.resource == dataset_id or e.resource is None)
        ]

        if not produce_events and not consume_events:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.NOT_OBSERVED,
                notes="No produce/consume events observed for this resource.",
                conflict_class=ConflictClass.DYNAMIC_INCOMPLETE,
            )

        if not produce_events:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.PARTIALLY_SUPPORTED,
                supporting_events=[e.event_id for e in consume_events],
                notes="Consume observed but produce not observed — incomplete coverage.",
                conflict_class=ConflictClass.DYNAMIC_INCOMPLETE,
            )

        if not consume_events:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.PARTIALLY_SUPPORTED,
                supporting_events=[e.event_id for e in produce_events],
                notes="Produce observed but consume not observed — incomplete coverage.",
                conflict_class=ConflictClass.DYNAMIC_INCOMPLETE,
            )

        prod_last = max(e.timestamp for e in produce_events)
        cons_first = min(e.timestamp for e in consume_events)
        supporting = [e.event_id for e in produce_events + consume_events]

        if prod_last < cons_first:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.SUPPORTED,
                supporting_events=supporting,
                dynamic_support_score=1.0,
                execution_frequency=1.0,
                notes=f"Producer completes at {prod_last}, consumer starts at {cons_first}.",
            )
        else:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.CONTRADICTED,
                violating_events=supporting,
                conflict_class=ConflictClass.STATIC_FALSE_POSITIVE,
                notes=(
                    f"CONFLICT: Consumer attempted access at {cons_first} "
                    f"before producer completed at {prod_last}."
                ),
            )

    def _reconcile_must_not_follow_on_error(
        self,
        contract: Contract,
        subject_events: list[ExecutionEvent],
        object_events: list[ExecutionEvent],
    ) -> ReconciliationRecord:
        """
        CONTROL-FLOW: If RC(A) OP threshold → ¬execute(B)
        Check: whenever A returns with error, B does not execute.
        """
        rc_threshold = contract.metadata.get("rc_threshold", 0)
        operator = contract.metadata.get("operator", "NE")

        a_returns = [
            e for e in subject_events
            if e.operation in {OperationType.RETURN, OperationType.STEP_END, OperationType.JOB_END}
            and e.return_code is not None
        ]

        if not a_returns:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.NOT_OBSERVED,
                notes="No return events with return codes observed for subject.",
                conflict_class=ConflictClass.DYNAMIC_INCOMPLETE,
            )

        b_executes = [
            e for e in object_events
            if e.operation in {OperationType.EXECUTE, OperationType.STEP_START, OperationType.JOB_START}
        ]

        violations: list[str] = []
        supports: list[str] = []

        for ret_event in a_returns:
            rc = ret_event.return_code
            assert rc is not None
            condition_true = self._evaluate_cond(rc, operator, rc_threshold)
            if condition_true:
                # Check if B executed after this return
                b_after = [
                    e for e in b_executes
                    if e.timestamp > ret_event.timestamp
                ]
                if b_after:
                    # VIOLATION: B executed when it should not have
                    violations.extend([e.event_id for e in b_after])
                    violations.append(ret_event.event_id)
                else:
                    supports.append(ret_event.event_id)

        if not violations and not supports:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.NOT_OBSERVED,
                notes="Error condition never triggered in observed executions.",
                conflict_class=ConflictClass.DYNAMIC_INCOMPLETE,
            )
        elif violations:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.CONTRADICTED,
                violating_events=violations,
                conflict_class=ConflictClass.STATIC_FALSE_POSITIVE,
                notes=(
                    f"CONFLICT: Object step executed after subject returned "
                    f"RC {operator} {rc_threshold} — COND bypass not respected."
                ),
            )
        else:
            return ReconciliationRecord(
                contract_id=contract.contract_id,
                outcome=ReconciliationOutcome.SUPPORTED,
                supporting_events=supports,
                dynamic_support_score=1.0,
                notes="Error condition triggered and object step correctly bypassed.",
            )

    @staticmethod
    def _evaluate_cond(rc: int, operator: str, threshold: int) -> bool:
        """Evaluate JCL COND condition: returns True if condition is met (step bypassed)."""
        op = operator.upper()
        if op == "GT":
            return rc > threshold
        elif op == "LT":
            return rc < threshold
        elif op == "EQ":
            return rc == threshold
        elif op == "NE":
            return rc != threshold
        elif op == "GE":
            return rc >= threshold
        elif op == "LE":
            return rc <= threshold
        else:
            return False

    def _update_contract(
        self, contract: Contract, record: ReconciliationRecord
    ) -> None:
        """Update contract validation state and confidence from reconciliation result."""
        outcome = record.outcome
        current = contract.validation_state

        # SCIENTIFIC INTEGRITY: HUMAN_VALIDATED and GROUND_TRUTH are terminal states.
        # No automated reconciliation outcome may demote them. If a contradiction
        # is observed against a human-validated or oracle-verified contract, the
        # conflict is recorded in metadata for human review rather than overwriting
        # the validation state.
        if current in {ValidationState.HUMAN_VALIDATED, ValidationState.GROUND_TRUTH}:
            if outcome == ReconciliationOutcome.CONTRADICTED:
                contract.metadata["reconciliation_conflict"] = {
                    "outcome": outcome.value,
                    "notes": record.notes,
                    "violating_events": record.violating_events,
                    "requires_human_review": True,
                }
                logger.warning(
                    f"Contract {contract.contract_id} is {current.value} but received "
                    f"CONTRADICTED reconciliation. Conflict recorded in metadata; "
                    "state preserved. Human review required."
                )
            # For all other outcomes (SUPPORTED, NOT_OBSERVED, etc.) on a
            # terminal-state contract: update confidence but do not change state.
            contract.confidence.dynamic_support = record.dynamic_support_score
            contract.confidence.execution_frequency = record.execution_frequency
            if record.supporting_events or record.violating_events:
                dyn_evidence = EvidenceItem(
                    evidence_type="dynamic_observation",
                    source_artifact="execution_trace",
                    source_location=f"events:{','.join((record.supporting_events + record.violating_events)[:5])}",
                    extraction_method=ExtractionMethod.EXECUTION,
                    content=record.notes,
                )
                if contract.provenance:
                    contract.provenance.dynamic_evidence.append(dyn_evidence)
            return

        # Update validation state
        if outcome == ReconciliationOutcome.SUPPORTED:
            # SCIENTIFIC INTEGRITY (SI-01): synthetic-source demotion is applied
            # upstream in _reconcile_contract before this method is called.
            # By the time we reach here, any synthetic-only SUPPORTED outcome has
            # already been demoted to NOT_OBSERVED.  No additional all_synthetic
            # check is needed; we can promote unconditionally.
            if current in {ValidationState.STATIC_CANDIDATE, ValidationState.STATIC_DYNAMIC_SUPPORTED}:
                contract.validation_state = ValidationState.STATIC_DYNAMIC_SUPPORTED
            # Don't change HUMAN_VALIDATED or GROUND_TRUTH (handled above)
        elif outcome == ReconciliationOutcome.CONTRADICTED:
            contract.validation_state = ValidationState.STATIC_DYNAMIC_CONFLICT
        elif outcome == ReconciliationOutcome.NOT_OBSERVED:
            if current == ValidationState.STATIC_CANDIDATE:
                contract.validation_state = ValidationState.NOT_OBSERVED
        elif outcome == ReconciliationOutcome.PARTIALLY_SUPPORTED:
            if current == ValidationState.STATIC_CANDIDATE:
                contract.validation_state = ValidationState.UNRESOLVED
        elif outcome == ReconciliationOutcome.AMBIGUOUS:
            if current == ValidationState.STATIC_CANDIDATE:
                contract.validation_state = ValidationState.UNRESOLVED

        # Update confidence
        contract.confidence.dynamic_support = record.dynamic_support_score
        contract.confidence.execution_frequency = record.execution_frequency

        # Add dynamic evidence to provenance
        if record.supporting_events or record.violating_events:
            dyn_evidence = EvidenceItem(
                evidence_type="dynamic_observation",
                source_artifact="execution_trace",
                source_location=f"events:{','.join((record.supporting_events + record.violating_events)[:5])}",
                extraction_method=ExtractionMethod.EXECUTION,
                content=record.notes,
            )
            if contract.provenance:
                contract.provenance.dynamic_evidence.append(dyn_evidence)
