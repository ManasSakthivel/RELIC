"""
GnuCOBOL Trace Adapter.

Reads execution event logs produced by GnuCOBOL-instrumented COBOL programs
and normalizes them to the ExecutionEvent schema.

Expected log format (one JSON line per event):
{
  "timestamp": "ISO8601",
  "program": "CBACT01C",
  "operation": "READ|WRITE|CALL|OPEN|CLOSE|RETURN",
  "resource": "ACCTFILE",
  "return_code": 0,
  "metadata": {}
}

Also handles JCL batch simulation log format:
{
  "timestamp": "ISO8601",
  "job": "CBACT01C",
  "step": "STEP010",
  "event": "JOB_START|STEP_START|STEP_END|JOB_END",
  "return_code": 0
}

Outputs: ExecutionTrace with normalized ExecutionEvent objects.

IMPORTANT: Sets source_type = EXECUTION for real gnucobol logs,
           EXECUTION_SIMULATED for JCL simulation logs.
           Never uses SYNTHETIC_STATIC for real trace files.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from legacy_contract.dynamic_analysis.model import (
    EventSourceType,
    ExecutionEvent,
    ExecutionTrace,
    OperationType,
)


# ---------------------------------------------------------------------------
# Operation string → OperationType mapping
# ---------------------------------------------------------------------------

_GNUCOBOL_OP_MAP: dict[str, OperationType] = {
    "READ": OperationType.READ,
    "WRITE": OperationType.WRITE,
    "CALL": OperationType.CALL,
    "PERFORM": OperationType.PERFORM,
    "OPEN": OperationType.OPEN,
    "CLOSE": OperationType.CLOSE,
    "RETURN": OperationType.RETURN,
    "EXECUTE": OperationType.EXECUTE,
    "INITIALIZE": OperationType.INITIALIZE,
    "ERROR": OperationType.ERROR,
    "FILE_ACCESS": OperationType.FILE_ACCESS,
    "DATABASE_ACCESS": OperationType.DATABASE_ACCESS,
    "PRODUCE": OperationType.PRODUCE,
    "CONSUME": OperationType.CONSUME,
}

_JCL_EVENT_MAP: dict[str, OperationType] = {
    "JOB_START": OperationType.JOB_START,
    "JOB_END": OperationType.JOB_END,
    "STEP_START": OperationType.STEP_START,
    "STEP_END": OperationType.STEP_END,
}


def _parse_timestamp(raw: str | None) -> datetime:
    """
    Parse an ISO 8601 timestamp string, returning UTC datetime.
    Falls back to utcnow() on any parse failure so that a bad timestamp
    in one event never aborts the entire trace load.
    """
    if not raw:
        return datetime.now(tz=timezone.utc)
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    logger.warning(f"GnuCOBOLTraceAdapter: unparseable timestamp {raw!r} — using utcnow()")
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# GnuCOBOL Trace Adapter
# ---------------------------------------------------------------------------

class GnuCOBOLTraceAdapter:
    """
    Parses execution event logs produced by GnuCOBOL-instrumented COBOL programs.

    Log format: one JSON object per line (JSON Lines / NDJSON).

    Each line must contain at minimum:
    - ``"operation"``: string matching an OperationType name (case-insensitive)
    - ``"program"``:   COBOL program name (maps to artifact_id)

    Optional fields:
    - ``"timestamp"``: ISO 8601 string
    - ``"resource"``:  file or dataset name
    - ``"return_code"``: integer (absent → None, not zero)
    - ``"metadata"``:  arbitrary JSON object

    Malformed lines are logged at WARNING level and skipped.
    The trace is returned even if all lines are malformed (empty event list).

    PROVENANCE: source_type is always set to EXECUTION.
    This adapter MUST NOT be used to load synthetic or simulated traces.
    """

    def parse_file(self, path: str, execution_id: str = "") -> ExecutionTrace:
        """
        Parse a GnuCOBOL NDJSON log file into an ExecutionTrace.

        Parameters
        ----------
        path:
            Path to the log file.
        execution_id:
            Identifier for this execution run.  If empty, derived from the
            filename stem.

        Returns
        -------
        ExecutionTrace
            All successfully parsed events, ordered as they appear in the file.
            source_type = EXECUTION.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Trace file not found: {path}")

        exec_id = execution_id or p.stem
        trace = ExecutionTrace(
            execution_id=exec_id,
            source_type=EventSourceType.EXECUTION,
            metadata={"source_file": str(p), "adapter": "GnuCOBOLTraceAdapter"},
        )

        malformed = 0
        loaded = 0

        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            for line_no, raw_line in enumerate(fh, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue  # empty or comment line

                event = self._parse_gnucobol_line(
                    line, line_no, exec_id, str(p)
                )
                if event is None:
                    malformed += 1
                    continue
                trace.add_event(event)
                loaded += 1

        logger.info(
            f"GnuCOBOLTraceAdapter: {p.name} → "
            f"{loaded} events loaded, {malformed} malformed lines skipped"
        )
        return trace

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_gnucobol_line(
        self,
        line: str,
        line_no: int,
        execution_id: str,
        source_file: str,
    ) -> ExecutionEvent | None:
        """Parse one JSON line into an ExecutionEvent.  Returns None on failure."""
        try:
            obj: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning(
                f"GnuCOBOLTraceAdapter: JSON parse error at line {line_no} "
                f"in {source_file!r}: {exc} — skipping"
            )
            return None

        op_raw = obj.get("operation", "")
        if not op_raw:
            logger.warning(
                f"GnuCOBOLTraceAdapter: missing 'operation' at line {line_no} "
                f"in {source_file!r} — skipping"
            )
            return None

        operation = _GNUCOBOL_OP_MAP.get(op_raw.upper())
        if operation is None:
            logger.warning(
                f"GnuCOBOLTraceAdapter: unknown operation {op_raw!r} "
                f"at line {line_no} — skipping"
            )
            return None

        program = obj.get("program", "")
        if not program:
            logger.warning(
                f"GnuCOBOLTraceAdapter: missing 'program' at line {line_no} "
                f"in {source_file!r} — skipping"
            )
            return None

        rc_raw = obj.get("return_code")
        return_code: int | None = None
        if rc_raw is not None:
            try:
                return_code = int(rc_raw)
            except (TypeError, ValueError):
                logger.warning(
                    f"GnuCOBOLTraceAdapter: invalid return_code {rc_raw!r} "
                    f"at line {line_no} — treating as None (not captured)"
                )

        return ExecutionEvent(
            timestamp=_parse_timestamp(obj.get("timestamp")),
            execution_id=execution_id,
            artifact_id=program.upper(),
            operation=operation,
            resource=obj.get("resource") or None,
            return_code=return_code,
            source_type=EventSourceType.EXECUTION,
            metadata={
                "source_file": source_file,
                "source_line": line_no,
                **(obj.get("metadata") or {}),
            },
        )


# ---------------------------------------------------------------------------
# JCL Simulator Adapter
# ---------------------------------------------------------------------------

class JCLSimulatorAdapter:
    """
    Parses JCL batch simulation logs into an ExecutionTrace.

    These logs are produced by batch-simulation scripts that run COBOL
    programs locally (e.g., via GnuCOBOL) and emit structured JCL-level
    lifecycle events.

    Log format: one JSON object per line.

    Each line must contain at minimum:
    - ``"event"``: one of JOB_START / JOB_END / STEP_START / STEP_END
    - ``"job"``:   JCL job name  OR  ``"step"`` for step-level events

    Optional fields:
    - ``"step"``:        JCL step name (for STEP_* events)
    - ``"timestamp"``:   ISO 8601 string
    - ``"return_code"``: integer
    - any additional keys are stored in metadata

    PROVENANCE: source_type is always set to EXECUTION_SIMULATED.
    This adapter MUST NOT be used for real mainframe SMF or GnuCOBOL logs.
    """

    def parse_file(self, path: str, execution_id: str = "") -> ExecutionTrace:
        """
        Parse a JCL simulation NDJSON log file into an ExecutionTrace.

        Parameters
        ----------
        path:
            Path to the simulation log file.
        execution_id:
            Identifier for this execution run.  If empty, derived from filename stem.

        Returns
        -------
        ExecutionTrace
            All successfully parsed events.
            source_type = EXECUTION_SIMULATED.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Simulation log not found: {path}")

        exec_id = execution_id or p.stem
        trace = ExecutionTrace(
            execution_id=exec_id,
            source_type=EventSourceType.EXECUTION_SIMULATED,
            metadata={
                "source_file": str(p),
                "adapter": "JCLSimulatorAdapter",
            },
        )

        malformed = 0
        loaded = 0

        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            for line_no, raw_line in enumerate(fh, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                event = self._parse_jcl_sim_line(
                    line, line_no, exec_id, str(p)
                )
                if event is None:
                    malformed += 1
                    continue
                trace.add_event(event)
                loaded += 1

        logger.info(
            f"JCLSimulatorAdapter: {p.name} → "
            f"{loaded} events loaded, {malformed} malformed lines skipped"
        )
        return trace

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_jcl_sim_line(
        self,
        line: str,
        line_no: int,
        execution_id: str,
        source_file: str,
    ) -> ExecutionEvent | None:
        """Parse one JSON line from a JCL simulation log."""
        try:
            obj: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning(
                f"JCLSimulatorAdapter: JSON parse error at line {line_no} "
                f"in {source_file!r}: {exc} — skipping"
            )
            return None

        event_raw = obj.get("event", "")
        if not event_raw:
            logger.warning(
                f"JCLSimulatorAdapter: missing 'event' at line {line_no} "
                f"in {source_file!r} — skipping"
            )
            return None

        operation = _JCL_EVENT_MAP.get(event_raw.upper())
        if operation is None:
            logger.warning(
                f"JCLSimulatorAdapter: unknown event type {event_raw!r} "
                f"at line {line_no} — skipping"
            )
            return None

        job = obj.get("job", "")
        step = obj.get("step", "")

        # artifact_id: prefer step name for step events, fall back to job name
        if step and operation in {OperationType.STEP_START, OperationType.STEP_END}:
            artifact_id = step.upper()
        elif job:
            artifact_id = job.upper()
        else:
            logger.warning(
                f"JCLSimulatorAdapter: missing both 'job' and 'step' "
                f"at line {line_no} in {source_file!r} — skipping"
            )
            return None

        rc_raw = obj.get("return_code")
        return_code: int | None = None
        if rc_raw is not None:
            try:
                return_code = int(rc_raw)
            except (TypeError, ValueError):
                logger.warning(
                    f"JCLSimulatorAdapter: invalid return_code {rc_raw!r} "
                    f"at line {line_no} — treating as None"
                )

        # Build metadata: everything except reserved top-level keys
        _reserved = {"timestamp", "job", "step", "event", "return_code"}
        extra_meta: dict[str, Any] = {
            k: v for k, v in obj.items() if k not in _reserved
        }

        return ExecutionEvent(
            timestamp=_parse_timestamp(obj.get("timestamp")),
            execution_id=execution_id,
            artifact_id=artifact_id,
            operation=operation,
            resource=obj.get("resource") or None,
            return_code=return_code,
            source_type=EventSourceType.EXECUTION_SIMULATED,
            metadata={
                "source_file": source_file,
                "source_line": line_no,
                "job": job,
                "step": step,
                **extra_meta,
            },
        )
