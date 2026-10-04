"""
JCL Parser — Extracts structural IR entities and relations from JCL source.

Supported JCL constructs:
- JOB card (job name, parameters)
- EXEC PGM= (program execution in a step)
- EXEC PROC= (procedure invocation)
- DD DSN= (dataset definitions, file dependencies)
- DD DISP= (dataset creation/consumption disposition)
- COND= (conditional execution — control-flow contracts)
- Return code references

Design principles:
- Produces deterministic IREntity and IRRelation objects
- Never produces contract objects — that is static_analysis responsibility
- Logs all unparsed constructs rather than silently ignoring them
- All entity IDs are deterministic (stable across re-runs)

Grammar reference: IBM JCL Reference, SA22-7597
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from legacy_contract.ir.model import (
    EntityType,
    IREntity,
    IRGraph,
    IRRelation,
    RelationType,
    SourceLocation,
)


# ---------------------------------------------------------------------------
# JCL Token Types
# ---------------------------------------------------------------------------

class JCLTokenType:
    JOB = "JOB"
    EXEC = "EXEC"
    DD = "DD"
    PROC = "PROC"
    PEND = "PEND"
    IF = "IF"
    ENDIF = "ENDIF"
    ELSE = "ELSE"
    SET = "SET"
    INCLUDE = "INCLUDE"
    COMMENT = "COMMENT"
    CONTINUATION = "CONTINUATION"
    UNKNOWN = "UNKNOWN"


@dataclass
class JCLToken:
    token_type: str
    name: str
    operation: str
    operands: str
    line_number: int
    raw_line: str


@dataclass
class JCLParseResult:
    """Result of parsing one JCL file."""
    artifact_path: str
    tokens: list[JCLToken] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)
    unparsed_lines: list[tuple[int, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# JCL Parser
# ---------------------------------------------------------------------------

class JCLParser:
    """
    Parses JCL source into IR entities and relations.

    Extraction strategy:
    1. Tokenize JCL into statements
    2. For each statement, extract structural facts deterministically
    3. Build IR entities (JOB, STEP, DATASET, JCL_DD, JCL_PROC)
    4. Build IR relations (CONTAINS, PRODUCES, CONSUMES, DEPENDS_ON)

    Control-flow facts (COND parameters) are extracted as IRRelation
    of type MUST_PRECEDE; the static_analysis module promotes these to contracts.
    """

    # JCL statement pattern: //[name] operation [operands] [comment]
    STATEMENT_PATTERN = re.compile(
        r"^//([A-Z@#$][A-Z0-9@#$]{0,7})?\s+([A-Z]+)\s*(.*?)(?:\s+/\*.*)?$",
        re.IGNORECASE,
    )
    COMMENT_PATTERN = re.compile(r"^//\*")
    # v1.0.0 rule (kept for legacy mode): a continuation line needed >= 15
    # blanks after '//'. IBM JCL allows the continued operand to start in any
    # column 4-16, so this rule merged none of CardDemo's 296 continuation lines.
    CONTINUATION_PATTERN = re.compile(r"^//\s{15}")
    # IBM rule: the operand field of the current statement ends with a comma
    # and the next line is '//' followed by a blank in column 3.
    IBM_CONTINUATION_PATTERN = re.compile(r"^//\s+\S")
    STATEMENT_COLUMNS = 71
    COND_PATTERN_LEGACY = re.compile(r"COND=(\([^)]+\)|\w+)", re.IGNORECASE)
    COND_PATTERN_BALANCED = re.compile(r"COND=(\((?:[^()]|\([^()]*\))*\)|\w+)", re.IGNORECASE)

    def __init__(self, legacy_v1_0: bool = False) -> None:
        """
        Parameters
        ----------
        legacy_v1_0:
            Reproduce the as-released v1.0.0 behaviour exactly (non-standard
            continuation rule, sequence columns 73-80 kept, COND captured up to
            the first ')'). Used only to evaluate the released version; the
            default follows the IBM JCL statement-format rules.
        """
        self.legacy_v1_0 = legacy_v1_0
        self._current_job: IREntity | None = None
        self._current_step: IREntity | None = None
        self._step_order: list[IREntity] = []

    def parse_file(self, artifact_path: str) -> tuple[JCLParseResult, IRGraph]:
        """Parse a JCL file and return parse result + IR graph."""
        path = Path(artifact_path)
        if not path.exists():
            raise FileNotFoundError(f"JCL file not found: {artifact_path}")

        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return self.parse_lines(lines, artifact_path)

    def parse_lines(
        self, lines: list[str], artifact_path: str
    ) -> tuple[JCLParseResult, IRGraph]:
        """Parse JCL lines into parse result + IR graph."""
        result = JCLParseResult(artifact_path=artifact_path)
        ir = IRGraph()
        ir.artifact_paths.append(artifact_path)

        self._current_job = None
        self._current_step = None
        self._step_order = []

        # Merge continuation lines before tokenizing
        merged_lines = self._merge_continuations(lines, artifact_path, result)

        for line_no, line in merged_lines:
            if not line.strip():
                continue
            if self.COMMENT_PATTERN.match(line):
                continue
            if not line.startswith("//"):
                result.unparsed_lines.append((line_no, line))
                continue

            token = self._tokenize_statement(line, line_no, artifact_path)
            if token is None:
                result.unparsed_lines.append((line_no, line))
                continue
            result.tokens.append(token)
            self._process_token(token, artifact_path, ir, result)

        # Add step ordering relations
        self._add_step_ordering(ir, artifact_path)

        return result, ir

    def _merge_continuations(
        self,
        lines: list[str],
        artifact_path: str,
        result: JCLParseResult,
    ) -> list[tuple[int, str]]:
        """
        Merge continuation lines.
        Returns list of (original_line_number, merged_line).

        Default (IBM) mode: columns 73-80 are dropped; a statement whose
        operand field ends with ',' continues on the next '//' line whose
        column 3 is blank; the continued operand field is appended directly.
        Legacy v1.0 mode: only lines with >= 15 blanks after '//' are merged.
        """
        if not self.legacy_v1_0:
            return self._merge_continuations_ibm(lines)
        merged: list[tuple[int, str]] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            line_no = i + 1
            if i + 1 < len(lines) and self.CONTINUATION_PATTERN.match(lines[i + 1]):
                # Merge continuation
                combined = line.rstrip()
                while i + 1 < len(lines) and self.CONTINUATION_PATTERN.match(lines[i + 1]):
                    i += 1
                    combined += " " + lines[i].strip()
                merged.append((line_no, combined))
            else:
                merged.append((line_no, line))
            i += 1
        return merged

    @staticmethod
    def _operand_field(text: str) -> str:
        """Operand text up to the first blank outside quotes / parentheses."""
        out: list[str] = []
        in_quote = False
        depth = 0
        for ch in text:
            if ch == "'":
                in_quote = not in_quote
            elif not in_quote:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth = max(0, depth - 1)
                elif ch == " " and depth == 0:
                    break
            out.append(ch)
        return "".join(out)

    def _merge_continuations_ibm(self, lines: list[str]) -> list[tuple[int, str]]:
        merged: list[tuple[int, str]] = []
        cols = self.STATEMENT_COLUMNS
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i][:cols].rstrip() if lines[i].startswith("//") else lines[i]
            line_no = i + 1
            m = re.match(r"^//(\S*)\s+(\S+)\s*(.*)$", line)
            if (
                m is None
                or line.startswith("//*")
                or m.group(2).upper() == "IF"
            ):
                merged.append((line_no, line))
                i += 1
                continue
            field = self._operand_field(m.group(3))
            if not field.endswith(","):
                merged.append((line_no, line))
                i += 1
                continue
            combined = f"//{m.group(1)} {m.group(2)} {field}"
            while field.endswith(",") and i + 1 < n:
                nxt = lines[i + 1][:cols].rstrip()
                if nxt.startswith("//*"):
                    i += 1          # comment statements may be interleaved
                    continue
                if not self.IBM_CONTINUATION_PATTERN.match(nxt):
                    break
                i += 1
                field = self._operand_field(nxt[2:].lstrip())
                combined += field
            merged.append((line_no, combined))
            i += 1
        return merged

    def _tokenize_statement(
        self, line: str, line_no: int, artifact_path: str
    ) -> JCLToken | None:
        """Extract name, operation, and operands from a JCL statement."""
        m = self.STATEMENT_PATTERN.match(line)
        if not m:
            return None
        name = (m.group(1) or "").strip()
        operation = (m.group(2) or "").strip().upper()
        operands = (m.group(3) or "").strip()
        return JCLToken(
            token_type=operation,
            name=name,
            operation=operation,
            operands=operands,
            line_number=line_no,
            raw_line=line,
        )

    def _process_token(
        self,
        token: JCLToken,
        artifact_path: str,
        ir: IRGraph,
        result: JCLParseResult,
    ) -> None:
        loc = SourceLocation(
            artifact_path=artifact_path,
            line_start=token.line_number,
            line_end=token.line_number,
            context=token.raw_line[:80],
        )

        if token.operation == "JOB":
            self._process_job(token, artifact_path, ir, loc)
        elif token.operation == "EXEC":
            self._process_exec(token, artifact_path, ir, loc, result)
        elif token.operation == "DD":
            self._process_dd(token, artifact_path, ir, loc, result)
        elif token.operation in {"PROC", "PEND", "IF", "ENDIF", "ELSE", "SET", "INCLUDE"}:
            pass  # Noted but not deeply parsed in Paper 1
        else:
            result.parse_warnings.append(
                f"Line {token.line_number}: Unknown operation '{token.operation}'"
            )

    def _process_job(
        self,
        token: JCLToken,
        artifact_path: str,
        ir: IRGraph,
        loc: SourceLocation,
    ) -> None:
        job_name = token.name or Path(artifact_path).stem
        job_entity = IREntity(
            entity_type=EntityType.JOB,
            name=job_name,
            artifact_path=artifact_path,
            location=loc,
            attributes={"operands": token.operands},
        )
        ir.add_entity(job_entity)
        self._current_job = job_entity
        self._step_order = []

    def _process_exec(
        self,
        token: JCLToken,
        artifact_path: str,
        ir: IRGraph,
        loc: SourceLocation,
        result: JCLParseResult,
    ) -> None:
        # Extract PGM= or PROC=
        pgm_match = re.search(r"PGM=([A-Z0-9@#$]+)", token.operands, re.IGNORECASE)
        proc_match = re.search(r"PROC=([A-Z0-9@#$]+)", token.operands, re.IGNORECASE)
        # Also handle positional proc name: EXEC PROCNAME
        positional_proc = None
        if not pgm_match and not proc_match and token.name:
            positional_proc = token.operands.split(",")[0].strip() if token.operands else None

        step_name = token.name or f"STEP_{len(self._step_order) + 1:03d}"
        step_entity = IREntity(
            entity_type=EntityType.STEP,
            name=step_name,
            artifact_path=artifact_path,
            location=loc,
            attributes={"operands": token.operands},
        )
        ir.add_entity(step_entity)
        self._step_order.append(step_entity)

        # Link step to job
        if self._current_job:
            ir.add_relation(IRRelation(
                relation_type=RelationType.CONTAINS,
                source=self._current_job,
                target=step_entity,
                confidence=1.0,
                location=loc,
            ))

        # Link step to program or proc
        if pgm_match:
            pgm_name = pgm_match.group(1).upper()
            pgm_entity = IREntity(
                entity_type=EntityType.PROGRAM,
                name=pgm_name,
                artifact_path=artifact_path,
                location=loc,
            )
            ir.add_entity(pgm_entity)
            ir.add_relation(IRRelation(
                relation_type=RelationType.CALLS,
                source=step_entity,
                target=pgm_entity,
                confidence=1.0,
                location=loc,
            ))
            self._current_step = step_entity
        elif proc_match or positional_proc:
            proc_name = (proc_match.group(1) if proc_match else positional_proc or "").upper()
            proc_entity = IREntity(
                entity_type=EntityType.JCL_PROC,
                name=proc_name,
                artifact_path=artifact_path,
                location=loc,
            )
            ir.add_entity(proc_entity)
            ir.add_relation(IRRelation(
                relation_type=RelationType.CALLS,
                source=step_entity,
                target=proc_entity,
                confidence=1.0,
                location=loc,
            ))
            self._current_step = step_entity

        # Extract COND parameter for control-flow contract candidates
        cond_pattern = self.COND_PATTERN_LEGACY if self.legacy_v1_0 else self.COND_PATTERN_BALANCED
        cond_match = cond_pattern.search(token.operands)
        if cond_match:
            step_entity.attributes["cond"] = cond_match.group(1).strip()

    def _process_dd(
        self,
        token: JCLToken,
        artifact_path: str,
        ir: IRGraph,
        loc: SourceLocation,
        result: JCLParseResult,
    ) -> None:
        if not self._current_step:
            return

        # Extract DSN (dataset name)
        dsn_match = re.search(r"DSN=([^\s,]+)", token.operands, re.IGNORECASE)
        # Extract DISP (disposition — tells us if file is created or consumed)
        disp_match = re.search(r"DISP=\(?([^,)]+)", token.operands, re.IGNORECASE)

        dd_name = token.name or "ANON_DD"
        dd_entity = IREntity(
            entity_type=EntityType.JCL_DD,
            name=f"{self._current_step.name}.{dd_name}",
            artifact_path=artifact_path,
            location=loc,
            attributes={"operands": token.operands},
        )
        ir.add_entity(dd_entity)
        ir.add_relation(IRRelation(
            relation_type=RelationType.USES_RESOURCE,
            source=self._current_step,
            target=dd_entity,
            confidence=1.0,
            location=loc,
        ))

        if dsn_match:
            dsn = dsn_match.group(1).strip("'")
            dataset_entity = IREntity(
                entity_type=EntityType.DATASET,
                name=dsn,
                artifact_path=artifact_path,
                location=loc,
                attributes={"dsn": dsn},
            )
            ir.add_entity(dataset_entity)
            dd_entity.attributes["dsn"] = dsn

            # DISP: NEW or CATLG or PASS = producing; OLD/SHR = consuming
            disp = (disp_match.group(1).upper() if disp_match else "OLD")
            if disp in {"NEW", "CATLG", "PASS", "MOD"}:
                ir.add_relation(IRRelation(
                    relation_type=RelationType.PRODUCES,
                    source=self._current_step,
                    target=dataset_entity,
                    confidence=1.0,
                    location=loc,
                    attributes={"disp": disp},
                ))
            else:  # OLD, SHR, MOD with existing
                ir.add_relation(IRRelation(
                    relation_type=RelationType.CONSUMES,
                    source=self._current_step,
                    target=dataset_entity,
                    confidence=1.0,
                    location=loc,
                    attributes={"disp": disp},
                ))

    def _add_step_ordering(self, ir: IRGraph, artifact_path: str) -> None:
        """
        Add MUST_PRECEDE relations between consecutive steps.
        JCL step ordering is deterministic: steps execute in declared order.
        """
        for i in range(len(self._step_order) - 1):
            a = self._step_order[i]
            b = self._step_order[i + 1]
            ir.add_relation(IRRelation(
                relation_type=RelationType.MUST_PRECEDE,
                source=a,
                target=b,
                confidence=1.0,
                location=a.location,
                attributes={"basis": "jcl_sequential_order"},
            ))
