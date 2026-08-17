"""
Baseline A — Structural Dependency Analysis.

Extracts structural dependencies (call graph, data flow, file dependencies)
from JCL+COBOL via the IRGraph and flags mutations that alter dependency
structure. No behavioral contract abstraction is applied.

This baseline answers: can simple structural reachability analysis detect
the same risks as the behavioral-contract-based BCG approach?

Scientific purpose: provides a fair lower-bound baseline to test whether
the BCG representation adds value beyond what a dependency graph alone can detect.

Reference: Tip (1995) "A Survey of Program Slicing Techniques", JPLP 3(3).
           Reps, Horwitz & Sagiv (1995) for precise interprocedural slicing.

BASELINE LIMITATIONS (by design — do not fix):
- No behavioral semantics: treats all dependency edges as equivalent.
- No contract types: cannot distinguish temporal from resource dependencies.
- No confidence: structural edges have binary presence/absence.
- No provenance: cannot trace why a dependency was inferred.
- No dynamic grounding: purely static.
These limitations exist so the BCG comparison is scientifically meaningful.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from legacy_contract.ir.model import IRGraph, IREntity, IRRelation, RelationType


# ---------------------------------------------------------------------------
# Structural Dependency Graph
# ---------------------------------------------------------------------------

@dataclass
class StructuralDependencyNode:
    """A node in the structural dependency graph."""
    entity_id: str
    name: str
    entity_type: str
    artifact_path: str


@dataclass
class StructuralDependencyEdge:
    """A directed edge in the structural dependency graph."""
    source_id: str
    target_id: str
    relation_type: str
    artifact_path: str
    line: int = 0


@dataclass
class StructuralDependencyGraph:
    """
    Structural dependency graph extracted from IRGraph.

    Nodes = entities; edges = structural relations.
    No behavioral semantics — this is purely structural.
    """
    nodes: dict[str, StructuralDependencyNode] = field(default_factory=dict)
    edges: list[StructuralDependencyEdge] = field(default_factory=list)
    artifact_paths: list[str] = field(default_factory=list)

    def successors(self, entity_id: str) -> list[str]:
        """Return all direct successors of entity_id."""
        return [e.target_id for e in self.edges if e.source_id == entity_id]  # type: ignore[union-attr]

    def predecessors(self, entity_id: str) -> list[str]:
        """Return all direct predecessors of entity_id."""
        return [e.source_id for e in self.edges if e.target_id == entity_id]  # type: ignore[union-attr]

    def reachable_from(self, start_id: str) -> set[str]:
        """BFS: return all entity_ids reachable from start_id."""
        visited: set[str] = set()
        queue = [start_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self.successors(current))
        return visited - {start_id}

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return len(self.edges)  # type: ignore[arg-type]

    def summary(self) -> str:
        type_counts: dict[str, int] = {}
        for e in self.edges:  # type: ignore[union-attr]
            type_counts[e.relation_type] = type_counts.get(e.relation_type, 0) + 1
        return (
            f"StructuralDependencyGraph: {self.node_count()} nodes, "
            f"{self.edge_count()} edges\n"
            + "Edge types: "
            + ", ".join(f"{k}={v}" for k, v in sorted(type_counts.items()))
        )


# ---------------------------------------------------------------------------
# Structural Risk Item
# ---------------------------------------------------------------------------

@dataclass
class StructuralRiskItem:
    """
    A structural risk detected by the baseline.

    Structural risks are changes that break direct dependency edges.
    No semantic interpretation is provided (by design).
    """
    item_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    source_entity: str = ""
    target_entity: str = ""
    missing_edge_type: str = ""
    risk_description: str = ""
    artifact_path: str = ""
    confidence: float = 1.0   # Always 1.0 for structural baseline (binary)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "missing_edge_type": self.missing_edge_type,
            "risk_description": self.risk_description,
            "artifact_path": self.artifact_path,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# Structural Baseline Analyzer
# ---------------------------------------------------------------------------

class StructuralBaselineAnalyzer:
    """
    Baseline A: Structural Dependency Analysis.

    Builds a structural dependency graph from an IRGraph and detects
    dependency-breaking changes between original and mutated versions.

    By design this baseline:
    - Does NOT recover behavioral contracts
    - Does NOT distinguish contract types (temporal / resource / control)
    - Does NOT have provenance
    - Does NOT use dynamic execution evidence
    - Does NOT compute calibrated confidence scores

    These are deliberate omissions to provide a fair lower-bound comparison.
    """

    # Relations considered structurally significant by this baseline
    STRUCTURAL_RELATIONS = {
        RelationType.CALLS,
        RelationType.PERFORMS,
        RelationType.READS,
        RelationType.WRITES,
        RelationType.PRODUCES,
        RelationType.CONSUMES,
        RelationType.DEPENDS_ON,
        RelationType.MUST_PRECEDE,
        RelationType.MUST_FOLLOW,
        RelationType.USES_RESOURCE,
        RelationType.REQUIRES_STATE,
        RelationType.ESTABLISHES_STATE,
    }

    def analyze(self, ir: IRGraph) -> StructuralDependencyGraph:
        """
        Build a StructuralDependencyGraph from an IRGraph.

        Only structural relations are extracted (see STRUCTURAL_RELATIONS).
        Behavioral semantics are deliberately ignored.

        Arguments:
            ir: the intermediate representation graph.

        Returns:
            StructuralDependencyGraph with all structural dependencies.
        """
        sdg = StructuralDependencyGraph(artifact_paths=list(ir.artifact_paths))
        sdg.edges = []  # type: ignore[assignment]

        # Add all entities as nodes
        for entity_id, entity in ir.entities.items():
            sdg.nodes[entity_id] = StructuralDependencyNode(
                entity_id=entity_id,
                name=entity.name,
                entity_type=entity.entity_type.value,
                artifact_path=entity.artifact_path,
            )

        # Add structural edges
        for relation in ir.relations:
            if relation.relation_type in self.STRUCTURAL_RELATIONS:
                edge = StructuralDependencyEdge(
                    source_id=relation.source.entity_id,
                    target_id=relation.target.entity_id,
                    relation_type=relation.relation_type.value,
                    artifact_path=(
                        relation.location.artifact_path
                        if relation.location else ""
                    ),
                    line=(
                        relation.location.line_start
                        if relation.location else 0
                    ),
                )
                sdg.edges.append(edge)  # type: ignore[union-attr]

        return sdg

    def detect_risk(
        self,
        original_sdg: StructuralDependencyGraph,
        mutated_sdg: StructuralDependencyGraph,
    ) -> list[StructuralRiskItem]:
        """
        Detect structural risks by comparing two dependency graphs.

        A risk is flagged when an edge present in original_sdg is absent in mutated_sdg.
        This is the structural equivalent of a "broken contract" — but without any
        behavioral interpretation.

        Arguments:
            original_sdg: dependency graph of the original system.
            mutated_sdg:  dependency graph of the modernized/mutated system.

        Returns:
            list of StructuralRiskItem, one per missing edge.

        NOTE: This baseline will produce false positives for intentional refactors
        (e.g., renaming a function changes node IDs but preserves behavior).
        This is an inherent limitation of structural analysis without semantic grounding.
        """
        risks: list[StructuralRiskItem] = []

        # Build edge fingerprints for mutated graph (source_id, target_id, relation_type)
        mutated_edges: set[tuple[str, str, str]] = {
            (e.source_id, e.target_id, e.relation_type)
            for e in mutated_sdg.edges  # type: ignore[union-attr]
        }

        for edge in original_sdg.edges:  # type: ignore[union-attr]
            fingerprint = (edge.source_id, edge.target_id, edge.relation_type)
            if fingerprint not in mutated_edges:
                src_name = original_sdg.nodes.get(edge.source_id, {})
                tgt_name = original_sdg.nodes.get(edge.target_id, {})
                src_str = (
                    src_name.name if isinstance(src_name, StructuralDependencyNode)
                    else edge.source_id
                )
                tgt_str = (
                    tgt_name.name if isinstance(tgt_name, StructuralDependencyNode)
                    else edge.target_id
                )
                risk = StructuralRiskItem(
                    source_entity=edge.source_id,
                    target_entity=edge.target_id,
                    missing_edge_type=edge.relation_type,
                    risk_description=(
                        f"Structural dependency broken: {src_str} "
                        f"--[{edge.relation_type}]--> {tgt_str}"
                    ),
                    artifact_path=edge.artifact_path,
                )
                risks.append(risk)

        return risks

    def transitive_impact(
        self,
        sdg: StructuralDependencyGraph,
        changed_entity_id: str,
    ) -> set[str]:
        """
        Compute transitive structural impact of a change at changed_entity_id.

        Returns all entity IDs reachable from the changed entity via dependency edges.
        This is the structural baseline's approximation of "impact analysis".

        NOTE: This overestimates impact (no semantic pruning) — which is why
        the BCG comparison tests whether behavioral semantics reduce false positives.
        """
        return sdg.reachable_from(changed_entity_id)
