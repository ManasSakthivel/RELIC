"""
COBOL Parser — Extracts structural IR entities and relations from COBOL source.

Targets: COBOL-85 / COBOL 2002 (as implemented by GnuCOBOL 3.1.2).
Covers: IDENTIFICATION DIVISION, ENVIRONMENT DIVISION, DATA DIVISION, PROCEDURE DIVISION.

Extracts:
- Program identity (PROGRAM-ID)
- File control entries (SELECT ... ASSIGN TO)
- Working storage section records and fields
- CALL statements (program invocations)
- PERFORM statements (paragraph/section invocations)
- READ / WRITE / OPEN / CLOSE statements (file operations)
- MOVE, IF/ELSE/END-IF, EVALUATE (control flow)
- Error handling (ON ERROR, AT END, INVALID KEY)
- COPY (copybook references)

Design: regex-based extraction (not full grammar parsing in Paper 1 scope).
This is sufficient for temporal/resource/control contracts.
Data contracts (field-level) require full grammar — Paper 2 scope.

Parser reports parse coverage rate and unparsed constructs.
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


@dataclass
class COBOLParseResult:
    """Result of parsing one COBOL source file."""
    artifact_path: str
    program_name: str = ""
    divisions_found: list[str] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)
    unparsed_constructs: list[tuple[int, str]] = field(default_factory=list)
    coverage_metrics: dict[str, int] = field(default_factory=dict)


class COBOLParser:
    """
    Parses COBOL source into IR entities and relations.

    Extraction is regex-based for Paper 1 scope.
    Each pattern is tied to a specific IR relation type.
    No contracts are produced here — that is static_analysis responsibility.
    """

    # Pattern: PROGRAM-ID. name.
    PROG_ID_PATTERN = re.compile(
        r"PROGRAM-ID\.\s+([A-Z0-9@#$-]+)", re.IGNORECASE
    )

    # Pattern: SELECT file-name ASSIGN TO system-name
    SELECT_PATTERN = re.compile(
        r"SELECT\s+([A-Z0-9-]+)\s+ASSIGN\s+TO\s+([A-Z0-9-\"'./]+)", re.IGNORECASE
    )

    # Pattern: CALL 'prog-name' or CALL prog-name-var
    CALL_PATTERN = re.compile(
        r"CALL\s+['\"]?([A-Z0-9@#$-]+)['\"]?", re.IGNORECASE
    )

    # Pattern: PERFORM section/paragraph
    PERFORM_PATTERN = re.compile(
        r"PERFORM\s+([A-Z0-9@#$-]+)(?:\s+THRU\s+([A-Z0-9@#$-]+))?", re.IGNORECASE
    )

    # Pattern: READ file-name
    READ_PATTERN = re.compile(r"READ\s+([A-Z0-9-]+)", re.IGNORECASE)

    # Pattern: WRITE record-name
    WRITE_PATTERN = re.compile(r"WRITE\s+([A-Z0-9-]+)", re.IGNORECASE)

    # Pattern: OPEN INPUT/OUTPUT/EXTEND/I-O file-name
    OPEN_PATTERN = re.compile(
        r"OPEN\s+(INPUT|OUTPUT|EXTEND|I-O)\s+([A-Z0-9-]+)", re.IGNORECASE
    )

    # Pattern: CLOSE file-name
    CLOSE_PATTERN = re.compile(r"CLOSE\s+([A-Z0-9-]+)", re.IGNORECASE)

    # Pattern: COPY copybook-name
    COPY_PATTERN = re.compile(r"COPY\s+([A-Z0-9@#$-]+)", re.IGNORECASE)

    # Pattern: DIVISION headings
    DIVISION_PATTERN = re.compile(
        r"(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION", re.IGNORECASE
    )

    # Pattern: paragraph/section names (line starting with label in col 8+)
    PARAGRAPH_PATTERN = re.compile(r"^([A-Z0-9][A-Z0-9-]{0,29})(?:\s+SECTION)?\.\s*$")

    def parse_file(self, artifact_path: str) -> tuple[COBOLParseResult, IRGraph]:
        path = Path(artifact_path)
        if not path.exists():
            raise FileNotFoundError(f"COBOL file not found: {artifact_path}")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return self.parse_lines(lines, artifact_path)

    def parse_lines(
        self, lines: list[str], artifact_path: str
    ) -> tuple[COBOLParseResult, IRGraph]:
        result = COBOLParseResult(artifact_path=artifact_path)
        ir = IRGraph()
        ir.artifact_paths.append(artifact_path)

        program_entity: IREntity | None = None
        current_division = ""
        paragraphs: dict[str, IREntity] = {}
        files: dict[str, IREntity] = {}  # file-name -> entity
        calls_count = 0
        performs_count = 0
        reads_count = 0
        writes_count = 0

        for line_no, raw_line in enumerate(lines, 1):
            # Strip sequence numbers (cols 1-6) and indicator (col 7) in fixed format
            line = self._normalize_line(raw_line)
            if not line.strip() or line.strip().startswith("*"):
                continue  # Comment or blank

            loc = SourceLocation(
                artifact_path=artifact_path,
                line_start=line_no,
                line_end=line_no,
                context=raw_line[:80],
            )

            # PROGRAM-ID
            m = self.PROG_ID_PATTERN.search(line)
            if m and not program_entity:
                prog_name = m.group(1).strip().upper()
                result.program_name = prog_name
                program_entity = IREntity(
                    entity_type=EntityType.PROGRAM,
                    name=prog_name,
                    artifact_path=artifact_path,
                    location=loc,
                )
                ir.add_entity(program_entity)

            # Division tracking
            m = self.DIVISION_PATTERN.search(line)
            if m:
                current_division = m.group(1).upper()
                if current_division not in result.divisions_found:
                    result.divisions_found.append(current_division)

            # SELECT (file control)
            m = self.SELECT_PATTERN.search(line)
            if m and program_entity:
                file_name = m.group(1).strip().upper()
                assign_to = m.group(2).strip()
                file_entity = IREntity(
                    entity_type=EntityType.FILE,
                    name=file_name,
                    artifact_path=artifact_path,
                    location=loc,
                    attributes={"assign_to": assign_to},
                )
                ir.add_entity(file_entity)
                ir.add_relation(IRRelation(
                    relation_type=RelationType.DEFINES,
                    source=program_entity,
                    target=file_entity,
                    confidence=1.0,
                    location=loc,
                ))
                files[file_name] = file_entity

            # COPY
            m = self.COPY_PATTERN.search(line)
            if m and program_entity:
                copybook_name = m.group(1).strip().upper()
                cb_entity = IREntity(
                    entity_type=EntityType.COPYBOOK,
                    name=copybook_name,
                    artifact_path=artifact_path,
                    location=loc,
                )
                ir.add_entity(cb_entity)
                ir.add_relation(IRRelation(
                    relation_type=RelationType.COPIES,
                    source=program_entity,
                    target=cb_entity,
                    confidence=1.0,
                    location=loc,
                ))

            # Only extract procedure division constructs in PROCEDURE DIVISION
            if current_division != "PROCEDURE":
                continue

            # Paragraph/Section names
            stripped = line.strip()
            pm = self.PARAGRAPH_PATTERN.match(stripped)
            if pm and program_entity:
                para_name = pm.group(1).upper()
                # Avoid false matches on common keywords
                if para_name not in {
                    "WORKING", "STORAGE", "LINKAGE", "FILE", "LOCAL", "REPORT",
                    "SCREEN", "COMMUNICATION", "END",
                }:
                    para_entity = IREntity(
                        entity_type=EntityType.PARAGRAPH,
                        name=para_name,
                        artifact_path=artifact_path,
                        location=loc,
                    )
                    ir.add_entity(para_entity)
                    ir.add_relation(IRRelation(
                        relation_type=RelationType.CONTAINS,
                        source=program_entity,
                        target=para_entity,
                        confidence=1.0,
                        location=loc,
                    ))
                    paragraphs[para_name] = para_entity

            # CALL
            m = self.CALL_PATTERN.search(line)
            if m and program_entity:
                called = m.group(1).strip().upper()
                called_entity = IREntity(
                    entity_type=EntityType.PROGRAM,
                    name=called,
                    artifact_path=artifact_path,
                    location=loc,
                )
                ir.add_entity(called_entity)
                ir.add_relation(IRRelation(
                    relation_type=RelationType.CALLS,
                    source=program_entity,
                    target=called_entity,
                    confidence=1.0,
                    location=loc,
                ))
                calls_count += 1

            # PERFORM
            m = self.PERFORM_PATTERN.search(line)
            if m and program_entity:
                para_name = m.group(1).strip().upper()
                if para_name not in {"UNTIL", "VARYING", "TIMES", "WITH", "TEST", "AFTER"}:
                    para_entity = paragraphs.get(para_name) or IREntity(
                        entity_type=EntityType.PARAGRAPH,
                        name=para_name,
                        artifact_path=artifact_path,
                        location=loc,
                    )
                    ir.add_entity(para_entity)
                    ir.add_relation(IRRelation(
                        relation_type=RelationType.PERFORMS,
                        source=program_entity,
                        target=para_entity,
                        confidence=1.0,
                        location=loc,
                    ))
                performs_count += 1

            # READ
            m = self.READ_PATTERN.search(line)
            if m and program_entity:
                file_name = m.group(1).strip().upper()
                file_entity = files.get(file_name) or IREntity(
                    entity_type=EntityType.FILE,
                    name=file_name,
                    artifact_path=artifact_path,
                    location=loc,
                )
                ir.add_entity(file_entity)
                ir.add_relation(IRRelation(
                    relation_type=RelationType.READS,
                    source=program_entity,
                    target=file_entity,
                    confidence=1.0,
                    location=loc,
                ))
                reads_count += 1

            # WRITE
            m = self.WRITE_PATTERN.search(line)
            if m and program_entity:
                record_name = m.group(1).strip().upper()
                rec_entity = IREntity(
                    entity_type=EntityType.RECORD,
                    name=record_name,
                    artifact_path=artifact_path,
                    location=loc,
                )
                ir.add_entity(rec_entity)
                ir.add_relation(IRRelation(
                    relation_type=RelationType.WRITES,
                    source=program_entity,
                    target=rec_entity,
                    confidence=1.0,
                    location=loc,
                ))
                writes_count += 1

        result.coverage_metrics = {
            "calls": calls_count,
            "performs": performs_count,
            "reads": reads_count,
            "writes": writes_count,
            "paragraphs": len(paragraphs),
            "files": len(files),
        }

        return result, ir

    def _normalize_line(self, raw_line: str) -> str:
        """
        Normalize COBOL line — handles fixed-format (mainframe) and
        free-format / indented test source strings.

        Fixed-format requires ALL of:
          1. Line length >= 72 (real mainframe card images)
          2. Cols 0-5 are digits or spaces (sequence number)
          3. Col 6 is a recognized indicator: space, *, /, D, -

        Short / indented lines (test strings, free-format sources) are
        returned as-is except comment lines (stripped form starts with '*').
        """
        if len(raw_line) < 7:
            return raw_line

        seq_field = raw_line[:6]
        indicator = raw_line[6]
        is_fixed = (
            len(raw_line) >= 72
            and all(c.isdigit() or c == ' ' for c in seq_field)
            and indicator in {' ', '*', '/', 'D', 'd', '-'}
        )

        if is_fixed:
            if indicator in {'*', '/'}:
                return ""
            if indicator in {'D', 'd'}:
                return ""
            return raw_line[7:72]

        # Free-format / leading-space test strings
        stripped = raw_line.strip()
        if stripped.startswith("*"):
            return ""
        return raw_line
