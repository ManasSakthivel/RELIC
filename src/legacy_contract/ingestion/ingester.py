"""
Artifact Ingester — discovers and ingests JCL, COBOL, and copybook artifacts.

Accepts a directory path, walks it, identifies artifact types by extension
and content heuristics, and routes each to the appropriate parser.

Returns an ArtifactInventory with all parsed IRGraphs merged into a single
combined IRGraph ready for BCG construction.

Artifact type detection:
- .jcl, .JCL → JCL parser
- .cbl, .cob, .CBL, .COB → COBOL parser
- .cpy, .CPY, .copy → Copybook parser

Merges all per-artifact IRGraphs into one combined IRGraph.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from loguru import logger

from legacy_contract.ir.model import IRGraph
from legacy_contract.parsers.cobol_parser import COBOLParser
from legacy_contract.parsers.copybook_parser import CopybookParser
from legacy_contract.parsers.jcl_parser import JCLParser


# ---------------------------------------------------------------------------
# Artifact type classification
# ---------------------------------------------------------------------------

class ArtifactType(str, Enum):
    """Classified legacy artifact types supported by the ingestion pipeline."""
    JCL = "JCL"
    COBOL = "COBOL"
    COPYBOOK = "COPYBOOK"
    UNKNOWN = "UNKNOWN"


# Extension → type map (lower-cased at lookup time)
_EXT_MAP: dict[str, ArtifactType] = {
    ".jcl": ArtifactType.JCL,
    ".cbl": ArtifactType.COBOL,
    ".cob": ArtifactType.COBOL,
    ".copy": ArtifactType.COPYBOOK,
    ".cpy": ArtifactType.COPYBOOK,
}

# Content heuristics: lines to scan, keyword → type
_CONTENT_HEURISTICS: list[tuple[bytes, ArtifactType]] = [
    (b"//", ArtifactType.JCL),                    # JCL statements start with //
    (b"IDENTIFICATION DIVISION", ArtifactType.COBOL),
    (b"PROGRAM-ID", ArtifactType.COBOL),
    (b"       01 ", ArtifactType.COPYBOOK),        # Copybook 01-level items
    (b"      01 ", ArtifactType.COPYBOOK),
]
_HEURISTIC_SCAN_BYTES = 4096


def _sha256_file(path: str) -> str:
    """Return hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ArtifactRecord:
    """Metadata record for a single ingested artifact."""
    path: str
    artifact_type: ArtifactType
    checksum: str                           # SHA-256 hex
    size_bytes: int
    parse_warnings: list[str] = field(default_factory=list)


@dataclass
class ArtifactInventory:
    """
    Complete inventory of all ingested artifacts, together with the merged
    IRGraph ready for BCG construction.
    """
    artifacts: list[ArtifactRecord] = field(default_factory=list)
    combined_ir: IRGraph = field(default_factory=IRGraph)
    parse_errors: list[tuple[str, str]] = field(default_factory=list)
    # path → str error message

    def artifact_count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in self.artifacts:
            counts[a.artifact_type.value] = counts.get(a.artifact_type.value, 0) + 1
        return counts

    def summary(self) -> str:
        counts = self.artifact_count_by_type()
        return (
            f"ArtifactInventory: {len(self.artifacts)} artifacts "
            f"({counts}) | "
            f"{self.combined_ir.entity_count()} entities | "
            f"{self.combined_ir.relation_count()} relations | "
            f"{len(self.parse_errors)} parse errors"
        )


# ---------------------------------------------------------------------------
# Ingester
# ---------------------------------------------------------------------------

class ArtifactIngester:
    """
    Discovers and ingests legacy artifacts from a directory tree.

    Parser instances are reused across calls for efficiency.
    """

    def __init__(self) -> None:
        self._jcl_parser = JCLParser()
        self._cobol_parser = COBOLParser()
        self._copybook_parser = CopybookParser()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest_directory(self, path: str) -> ArtifactInventory:
        """
        Walk *path* recursively, detect and parse all supported legacy
        artifacts, and return a merged ArtifactInventory.

        Files of UNKNOWN type are logged and skipped.
        Parse errors for individual files are captured in
        ArtifactInventory.parse_errors without aborting the ingestion run.

        Parameters
        ----------
        path:
            Root directory to scan.  Must exist and be readable.

        Returns
        -------
        ArtifactInventory
            Merged inventory with combined IRGraph.
        """
        root = Path(path)
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        inventory = ArtifactInventory()
        graphs: list[IRGraph] = []

        candidates = sorted(root.rglob("*"))
        files = [p for p in candidates if p.is_file()]

        logger.info(
            f"ArtifactIngester: scanning {len(files)} files in {path!r}"
        )

        for file_path in files:
            artifact_type = self._detect_type(str(file_path))
            if artifact_type == ArtifactType.UNKNOWN:
                logger.debug(
                    f"ArtifactIngester: skipping unknown file {file_path.name}"
                )
                continue

            try:
                record, ir_graph = self.ingest_file(str(file_path))
                inventory.artifacts.append(record)
                graphs.append(ir_graph)
            except Exception as exc:  # noqa: BLE001
                msg = f"{type(exc).__name__}: {exc}"
                logger.error(
                    f"ArtifactIngester: parse error in {file_path} — {msg}"
                )
                inventory.parse_errors.append((str(file_path), msg))

        inventory.combined_ir = self._merge_ir(graphs)
        logger.info(inventory.summary())
        return inventory

    def ingest_file(self, path: str) -> tuple[ArtifactRecord, IRGraph]:
        """
        Parse a single file and return its ArtifactRecord + IRGraph.

        The correct parser is selected based on ArtifactType detection.
        Warnings from the parser are captured in the ArtifactRecord.

        Parameters
        ----------
        path:
            Absolute or relative path to the artifact file.

        Returns
        -------
        tuple[ArtifactRecord, IRGraph]
            Metadata record + per-artifact IR graph.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        ValueError
            If the file type is UNKNOWN and cannot be parsed.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")

        artifact_type = self._detect_type(path)
        if artifact_type == ArtifactType.UNKNOWN:
            raise ValueError(
                f"Cannot determine artifact type for: {path} "
                f"(extension: {p.suffix!r})"
            )

        checksum = _sha256_file(path)
        size_bytes = p.stat().st_size
        warnings: list[str] = []
        ir_graph: IRGraph

        if artifact_type == ArtifactType.JCL:
            parse_result, ir_graph = self._jcl_parser.parse_file(path)
            warnings.extend(parse_result.parse_warnings)
            if parse_result.parse_errors:
                warnings.extend(
                    [f"PARSE_ERROR: {e}" for e in parse_result.parse_errors]
                )
            logger.debug(
                f"ArtifactIngester: JCL {p.name} → "
                f"{ir_graph.entity_count()} entities"
            )

        elif artifact_type == ArtifactType.COBOL:
            parse_result, ir_graph = self._cobol_parser.parse_file(path)
            warnings.extend(parse_result.parse_warnings)
            if parse_result.parse_errors:
                warnings.extend(
                    [f"PARSE_ERROR: {e}" for e in parse_result.parse_errors]
                )
            logger.debug(
                f"ArtifactIngester: COBOL {p.name} → "
                f"{ir_graph.entity_count()} entities"
            )

        elif artifact_type == ArtifactType.COPYBOOK:
            parse_result, ir_graph = self._copybook_parser.parse_file(path)
            warnings.extend(parse_result.parse_warnings)
            logger.debug(
                f"ArtifactIngester: Copybook {p.name} → "
                f"{ir_graph.entity_count()} entities"
            )

        else:
            # Should never reach here; guarded above.
            raise RuntimeError(f"Unhandled artifact type: {artifact_type}")  # pragma: no cover

        record = ArtifactRecord(
            path=path,
            artifact_type=artifact_type,
            checksum=checksum,
            size_bytes=size_bytes,
            parse_warnings=warnings,
        )
        return record, ir_graph

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_type(self, path: str) -> ArtifactType:
        """
        Determine artifact type from file extension first, then content
        heuristics for ambiguous or extension-less files.

        Detection order
        ---------------
        1. Extension lookup (fast, deterministic).
        2. Content scan of first ``_HEURISTIC_SCAN_BYTES`` bytes.
        3. UNKNOWN if neither method resolves the type.

        Parameters
        ----------
        path:
            Path to the file to classify.
        """
        suffix = Path(path).suffix.lower()
        if suffix in _EXT_MAP:
            return _EXT_MAP[suffix]

        # Content heuristics for extension-less or non-standard files
        try:
            with open(path, "rb") as fh:
                head = fh.read(_HEURISTIC_SCAN_BYTES).upper()
            for keyword, detected_type in _CONTENT_HEURISTICS:
                if keyword.upper() in head:
                    logger.debug(
                        f"ArtifactIngester._detect_type: "
                        f"content heuristic matched {keyword!r} → "
                        f"{detected_type.value} for {Path(path).name}"
                    )
                    return detected_type
        except OSError:
            logger.warning(
                f"ArtifactIngester._detect_type: "
                f"could not read {path!r} for content detection"
            )

        return ArtifactType.UNKNOWN

    def _merge_ir(self, graphs: list[IRGraph]) -> IRGraph:
        """
        Merge a list of per-artifact IRGraphs into a single combined IRGraph.

        Deduplication strategy
        ----------------------
        - Entities: deduplicated by entity_id (deterministic hash).
          The first occurrence wins for attribute conflicts.
        - Relations: deduplicated by relation_id (deterministic hash).
        - artifact_paths: union of all paths (no duplicates).

        Parameters
        ----------
        graphs:
            Sequence of IRGraphs produced by individual parser runs.

        Returns
        -------
        IRGraph
            A single merged IRGraph containing all unique entities and
            relations from every input graph.
        """
        merged = IRGraph()
        entity_count_before = 0
        entity_count_after = 0
        relation_count_before = 0
        relation_count_after = 0

        seen_paths: set[str] = set()

        for graph in graphs:
            entity_count_before += len(graph.entities)
            relation_count_before += len(graph.relations)

            for entity in graph.entities.values():
                merged.add_entity(entity)

            for relation in graph.relations:
                merged.add_relation(relation)

            for p in graph.artifact_paths:
                if p not in seen_paths:
                    merged.artifact_paths.append(p)
                    seen_paths.add(p)

        entity_count_after = len(merged.entities)
        relation_count_after = len(merged.relations)

        dedup_entities = entity_count_before - entity_count_after
        dedup_relations = relation_count_before - relation_count_after

        logger.info(
            f"ArtifactIngester._merge_ir: merged {len(graphs)} graphs → "
            f"{entity_count_after} entities "
            f"({dedup_entities} deduplicated), "
            f"{relation_count_after} relations "
            f"({dedup_relations} deduplicated)"
        )
        return merged
