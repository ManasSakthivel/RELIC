"""
Copybook Parser — Extracts record and field definitions from COBOL copybooks.

Copybooks define shared data structures used by multiple COBOL programs.
They are a critical source of DATA contracts (Paper 2 scope) and
cross-artifact FIELD relationships (important for PRODUCES/CONSUMES compatibility).

Extracts:
- Record structure (01-level items)
- Field definitions (05/10/15/etc level items)
- PICTURE clauses (field widths and types)
- COMP-3, COMP, BINARY usage
- REDEFINES (alternative record layouts)
- OCCURS (repeating groups)

These are structural facts used to:
1. Identify shared record formats between programs
2. Detect field-layout incompatibilities introduced by modernization
3. Paper 1: cross-artifact copybook dependency (COPIES relation)
4. Paper 2: data contract extraction
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from legacy_contract.ir.model import (
    EntityType,
    IREntity,
    IRGraph,
    IRRelation,
    RelationType,
    SourceLocation,
)


@dataclass
class FieldDefinition:
    """Parsed COBOL data item / field definition."""
    level: int
    name: str
    picture: str | None = None  # PICTURE clause
    usage: str | None = None    # COMP-3, BINARY, DISPLAY, etc.
    occurs: int | None = None   # OCCURS count
    redefines: str | None = None
    line_number: int = 0
    raw: str = ""

    def storage_bytes(self) -> int | None:
        """Estimate storage bytes from PICTURE clause. Returns None if unknown."""
        if not self.picture:
            return None
        usage = (self.usage or "").upper()
        pic = self.picture.upper()

        # Count digits/characters
        # X(n) or X...X
        x_match = re.search(r"X\((\d+)\)", pic)
        if x_match:
            count = int(x_match.group(1))
            return count
        x_chars = len(re.findall(r"X", pic))
        if x_chars:
            return x_chars

        # 9(n) or 9...9
        nine_match = re.search(r"9\((\d+)\)", pic)
        if nine_match:
            count = int(nine_match.group(1))
            if "COMP-3" in usage or "PACKED" in usage:
                return (count + 2) // 2
            if "COMP" in usage or "BINARY" in usage:
                if count <= 4:
                    return 2
                elif count <= 9:
                    return 4
                else:
                    return 8
            return count  # DISPLAY
        nine_chars = len(re.findall(r"9", pic))
        if nine_chars:
            return nine_chars

        return None


@dataclass
class CopybookParseResult:
    artifact_path: str
    copybook_name: str = ""
    fields: list[FieldDefinition] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)


class CopybookParser:
    """
    Parses COBOL copybooks to extract record/field structure.
    """

    LEVEL_NAME_PATTERN = re.compile(
        r"^\s*(\d{2})\s+([A-Z0-9-]+|FILLER)\s*(.*?)(?:\.\s*)?$", re.IGNORECASE
    )
    PIC_PATTERN = re.compile(
        r"PIC(?:TURE)?\s+(?:IS\s+)?([^\s.]+)", re.IGNORECASE
    )
    USAGE_PATTERN = re.compile(
        r"USAGE\s+(?:IS\s+)?([^\s.]+)|COMP-3|COMP|BINARY|DISPLAY|PACKED-DECIMAL",
        re.IGNORECASE,
    )
    OCCURS_PATTERN = re.compile(r"OCCURS\s+(\d+)\s+TIMES?", re.IGNORECASE)
    REDEFINES_PATTERN = re.compile(r"REDEFINES\s+([A-Z0-9-]+)", re.IGNORECASE)

    def parse_file(self, artifact_path: str) -> tuple[CopybookParseResult, IRGraph]:
        path = Path(artifact_path)
        if not path.exists():
            raise FileNotFoundError(f"Copybook not found: {artifact_path}")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return self.parse_lines(lines, artifact_path)

    def parse_lines(
        self, lines: list[str], artifact_path: str
    ) -> tuple[CopybookParseResult, IRGraph]:
        result = CopybookParseResult(
            artifact_path=artifact_path,
            copybook_name=Path(artifact_path).stem.upper(),
        )
        ir = IRGraph()
        ir.artifact_paths.append(artifact_path)

        copybook_entity = IREntity(
            entity_type=EntityType.COPYBOOK,
            name=result.copybook_name,
            artifact_path=artifact_path,
            location=SourceLocation(artifact_path=artifact_path, line_start=1, line_end=1),
        )
        ir.add_entity(copybook_entity)

        current_record: IREntity | None = None

        for line_no, raw_line in enumerate(lines, 1):
            line = self._normalize_line(raw_line)
            if not line.strip():
                continue

            loc = SourceLocation(
                artifact_path=artifact_path,
                line_start=line_no,
                line_end=line_no,
                context=raw_line[:80],
            )

            m = self.LEVEL_NAME_PATTERN.match(line)
            if not m:
                continue

            level = int(m.group(1))
            name = m.group(2).strip().upper()
            rest = m.group(3).strip()

            # Extract PIC, USAGE, OCCURS, REDEFINES from rest
            pic = None
            pic_m = self.PIC_PATTERN.search(rest)
            if pic_m:
                pic = pic_m.group(1).upper()

            usage = None
            usage_m = self.USAGE_PATTERN.search(rest)
            if usage_m:
                usage = (usage_m.group(1) or usage_m.group(0)).upper()

            occurs = None
            occ_m = self.OCCURS_PATTERN.search(rest)
            if occ_m:
                occurs = int(occ_m.group(1))

            redefines = None
            red_m = self.REDEFINES_PATTERN.search(rest)
            if red_m:
                redefines = red_m.group(1).upper()

            fd = FieldDefinition(
                level=level,
                name=name,
                picture=pic,
                usage=usage,
                occurs=occurs,
                redefines=redefines,
                line_number=line_no,
                raw=raw_line.strip(),
            )
            result.fields.append(fd)

            if level == 1 or level == 77:
                # New record
                rec_entity = IREntity(
                    entity_type=EntityType.RECORD,
                    name=name,
                    artifact_path=artifact_path,
                    location=loc,
                    attributes={"level": level},
                )
                ir.add_entity(rec_entity)
                ir.add_relation(IRRelation(
                    relation_type=RelationType.DEFINES,
                    source=copybook_entity,
                    target=rec_entity,
                    confidence=1.0,
                    location=loc,
                ))
                current_record = rec_entity
            elif level >= 2 and pic is not None and current_record is not None:
                # Leaf field
                field_entity = IREntity(
                    entity_type=EntityType.FIELD,
                    name=name,
                    artifact_path=artifact_path,
                    location=loc,
                    attributes={
                        "level": level,
                        "picture": pic,
                        "usage": usage,
                        "occurs": occurs,
                        "redefines": redefines,
                        "storage_bytes": fd.storage_bytes(),
                    },
                )
                ir.add_entity(field_entity)
                ir.add_relation(IRRelation(
                    relation_type=RelationType.DEFINES,
                    source=current_record,
                    target=field_entity,
                    confidence=1.0,
                    location=loc,
                ))

        return result, ir

    def _normalize_line(self, raw_line: str) -> str:
        """Strip sequence numbers and indicator from fixed-format COBOL."""
        if len(raw_line) >= 7:
            indicator = raw_line[6] if len(raw_line) > 6 else " "
            if indicator in {"*", "/", "D"}:
                return ""
            return raw_line[7:72] if len(raw_line) > 72 else raw_line[7:]
        return raw_line
