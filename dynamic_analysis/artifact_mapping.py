"""
artifact_mapping.py — Deterministic mapping layer for dynamic execution artifacts.

Resolves the C1 issue: execution traces carry artifact_id = program_name,
but BCG contracts are indexed by JCL step_id.

Mapping chain:
    execution artifact_id (program name)
        ↓
    program entity in IR
        ↓
    JCL EXEC step(s) that invoke that program
        ↓
    canonical IR entity IDs used in BCG contracts

Rules:
- NEVER use fuzzy matching if deterministic metadata is available.
- If a program maps to exactly one step → deterministic, return that step.
- If a program maps to multiple steps → AMBIGUOUS, report all candidates.
- If a program maps to zero steps → MISSING, report with explanation.
- PROC invocations are resolved by expanding the PROC and finding the EXEC step.
- Duplicate program invocations (same program in multiple steps) → AMBIGUOUS.

All AMBIGUOUS mappings produce an ArtifactMappingResult with status=AMBIGUOUS and
candidate_ids populated. Callers MUST NOT guess between candidates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Operand parsing helpers
# ---------------------------------------------------------------------------

def _extract_pgm_from_operands(operands: str) -> str | None:
    """
    Extract program name from a JCL EXEC operand string such as
    'PGM=CBACT01C' or 'PGM=CBACT01C,PARM=...' .
    Returns the program name (upper-cased) or None if not present.
    """
    if not operands:
        return None
    m = re.search(r'\bPGM\s*=\s*([A-Za-z0-9@#$]{1,8})', operands, re.IGNORECASE)
    return m.group(1).upper() if m else None


def _extract_proc_from_operands(operands: str) -> str | None:
    """
    Extract proc name from a JCL EXEC operand string such as 'PROC=MYPRC' or
    a bare proc name ('MYPRC') without PGM=.
    Returns the proc name (upper-cased) or None if not present.
    """
    if not operands:
        return None
    # Explicit PROC=name
    m = re.search(r'\bPROC\s*=\s*([A-Za-z0-9@#$]{1,8})', operands, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # Bare proc invocation: no PGM= and no PROC= keyword — first word is proc name
    stripped = operands.strip()
    if stripped and '=' not in stripped:
        candidate = stripped.split()[0].split(',')[0].upper()
        # Sanity check: valid JCL name
        if re.fullmatch(r'[A-Za-z@#$][A-Za-z0-9@#$]{0,7}', candidate):
            return candidate
    return None


class MappingStatus(str, Enum):
    """Result classification for a single program → step resolution."""
    EXACT = "EXACT"
    AMBIGUOUS = "AMBIGUOUS"
    MISSING = "MISSING"
    PROC_EXPANDED = "PROC_EXPANDED"
    UNMAPPED_EVENT = "UNMAPPED_EVENT"


@dataclass
class ArtifactMappingResult:
    """Result of resolving one execution artifact_id to BCG contract entity IDs."""

    program_name: str
    status: MappingStatus

    # Populated for EXACT or PROC_EXPANDED
    resolved_step_id: str | None = None
    resolved_entity_id: str | None = None

    # Populated for AMBIGUOUS
    candidate_ids: list[str] = field(default_factory=list)

    # Populated for MISSING or AMBIGUOUS — human-readable explanation
    reason: str = ""

    # Provenance: which JCL file and step name were matched
    source_jcl: str = ""
    step_name: str = ""

    def is_resolvable(self) -> bool:
        """True only if status is EXACT or PROC_EXPANDED (single deterministic target)."""
        return self.status in (MappingStatus.EXACT, MappingStatus.PROC_EXPANDED)


class ArtifactMapper:
    """
    Maps execution artifact IDs (program names) to BCG contract entity IDs.

    Built from an IRGraph: scans EXEC PGM= and EXEC PROC= step declarations
    to build a deterministic program → step index.

    Usage:
        mapper = ArtifactMapper.from_ir(ir_graph)
        result = mapper.resolve("CBACT01C")
        if result.is_resolvable():
            entity_id = result.resolved_entity_id
        elif result.status == MappingStatus.AMBIGUOUS:
            # report ambiguity, do not guess
            ...
    """

    def __init__(self) -> None:
        # program_name (upper) → list[(step_entity_id, step_name, jcl_file)]
        self._program_to_steps: dict[str, list[tuple[str, str, str]]] = {}
        # proc_name (upper) → list[(step_entity_id, step_name, jcl_file)]
        self._proc_to_steps: dict[str, list[tuple[str, str, str]]] = {}
        # entity_id → step_name (for display)
        self._entity_to_step: dict[str, str] = {}

    @classmethod
    def from_ir(cls, ir_graph: Any) -> "ArtifactMapper":
        """
        Build the mapping index from a populated IRGraph.

        Scans all IR entities of type STEP and inspects their metadata for:
        - exec_pgm: program name (EXEC PGM=...)
        - exec_proc: proc name (EXEC PROC=... or EXEC procname)
        """
        mapper = cls()
        try:
            from legacy_contract.ir.model import EntityType
        except ImportError:
            EntityType = None

        for entity_id, entity in ir_graph.entities.items():
            step_type_matches = False
            if EntityType is not None:
                step_type_matches = (entity.entity_type == EntityType.STEP)
            else:
                # Fallback: check string representation
                step_type_matches = (str(entity.entity_type).upper().endswith("STEP"))

            if not step_type_matches:
                continue

            # IREntity uses 'attributes' (not 'metadata') for structured fields.
            # The JCL parser stores the raw EXEC operand string in attributes['operands']
            # (e.g. "PGM=CBACT01C" or "PROC=MYPRC").  We also check for pre-parsed
            # 'exec_pgm' / 'exec_proc' / 'pgm' / 'proc' keys in attributes for
            # compatibility with alternative parsers.
            attrs = getattr(entity, "attributes", None) or {}
            # Also check metadata for backward compatibility
            meta = getattr(entity, "metadata", None) or {}
            combined = {**meta, **attrs}  # attrs takes precedence

            jcl_file = combined.get(
                "source_file",
                combined.get("jcl_file", getattr(entity, "artifact_path", "")),
            )
            step_name = entity.name or entity_id

            mapper._entity_to_step[entity_id] = step_name

            # Try pre-parsed keys first, then parse 'operands' string
            pgm = (
                combined.get("exec_pgm")
                or combined.get("pgm")
                or _extract_pgm_from_operands(combined.get("operands", ""))
            )
            if pgm:
                key = pgm.strip().upper()
                mapper._program_to_steps.setdefault(key, []).append(
                    (entity_id, step_name, jcl_file)
                )

            proc = (
                combined.get("exec_proc")
                or combined.get("proc")
                or _extract_proc_from_operands(combined.get("operands", ""))
            )
            if proc:
                key = proc.strip().upper()
                mapper._proc_to_steps.setdefault(key, []).append(
                    (entity_id, step_name, jcl_file)
                )

        return mapper

    def resolve(self, artifact_id: str) -> ArtifactMappingResult:
        """
        Resolve an execution artifact_id (program name from a trace event) to
        a BCG contract entity ID.

        artifact_id is the program name as it appears in the execution trace,
        e.g. "CBACT01C" or "DEPTPAY".

        Returns an ArtifactMappingResult with:
        - EXACT:          single unambiguous program→step match
        - PROC_EXPANDED:  artifact resolved via PROC invocation chain
        - AMBIGUOUS:      multiple steps invoke the same program (no guess made)
        - MISSING:        no step invokes this program in the IR
        - UNMAPPED_EVENT: artifact_id is empty or not a valid program name
        """
        if not artifact_id or not artifact_id.strip():
            return ArtifactMappingResult(
                program_name=artifact_id,
                status=MappingStatus.UNMAPPED_EVENT,
                reason="artifact_id is empty or whitespace",
            )

        key = artifact_id.strip().upper()

        # --- 1. Try direct program match ---
        if key in self._program_to_steps:
            candidates = self._program_to_steps[key]
            if len(candidates) == 1:
                eid, sname, jcl = candidates[0]
                return ArtifactMappingResult(
                    program_name=artifact_id,
                    status=MappingStatus.EXACT,
                    resolved_step_id=sname,
                    resolved_entity_id=eid,
                    source_jcl=jcl,
                    step_name=sname,
                )
            else:
                # Multiple steps invoke same program → AMBIGUOUS, never guess
                return ArtifactMappingResult(
                    program_name=artifact_id,
                    status=MappingStatus.AMBIGUOUS,
                    candidate_ids=[c[0] for c in candidates],
                    reason=(
                        f"Program '{artifact_id}' is invoked by {len(candidates)} steps: "
                        + ", ".join(f"{c[1]} in {c[2]}" for c in candidates)
                        + ". Cannot deterministically resolve without step context."
                    ),
                )

        # --- 2. Try PROC match (program name == proc name) ---
        if key in self._proc_to_steps:
            candidates = self._proc_to_steps[key]
            if len(candidates) == 1:
                eid, sname, jcl = candidates[0]
                return ArtifactMappingResult(
                    program_name=artifact_id,
                    status=MappingStatus.PROC_EXPANDED,
                    resolved_step_id=sname,
                    resolved_entity_id=eid,
                    source_jcl=jcl,
                    step_name=sname,
                    reason=f"Resolved via PROC invocation in {jcl}",
                )
            else:
                return ArtifactMappingResult(
                    program_name=artifact_id,
                    status=MappingStatus.AMBIGUOUS,
                    candidate_ids=[c[0] for c in candidates],
                    reason=(
                        f"PROC '{artifact_id}' invoked by {len(candidates)} steps — "
                        "ambiguous PROC expansion."
                    ),
                )

        # --- 3. Not found ---
        return ArtifactMappingResult(
            program_name=artifact_id,
            status=MappingStatus.MISSING,
            reason=(
                f"Program/PROC '{artifact_id}' does not appear as EXEC PGM= or "
                "EXEC PROC= in the loaded IR graph. Either the JCL was not parsed, "
                "the program name differs from the trace, or the program is not "
                "part of the evaluated JCL corpus."
            ),
        )

    def all_programs(self) -> list[str]:
        """Return all program names known to the mapper (upper-cased)."""
        return sorted(self._program_to_steps.keys())

    def all_procs(self) -> list[str]:
        """Return all proc names known to the mapper (upper-cased)."""
        return sorted(self._proc_to_steps.keys())
