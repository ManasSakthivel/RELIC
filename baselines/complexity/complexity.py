"""
Baseline B — Complexity Metrics.

Computes per-artifact complexity metrics from the IR graph and uses a
pre-specified weighted sum to assign a risk_score to each artifact.
A mutation is flagged HIGH risk (predicted_violated=True) if the
affected artifact's normalized risk_score exceeds RISK_THRESHOLD.

Scientific purpose: tests whether raw structural complexity alone
(without any behavioral semantics or contract abstraction) can predict
which artifacts are most likely to be affected by a mutation.

Metric definitions (frozen before evaluation — no post-hoc tuning):
  M1  structural_complexity   = number of IR entities in the artifact
  M2  dependency_count        = number of PRODUCES/CONSUMES/CALLS relations
  M3  step_count              = number of STEP entities
  M4  dataset_reference_count = number of DATASET entities
  M5  condition_count         = number of COND parameters found on STEP entities

Weights (pre-specified, not tuned on any evaluation data):
  w1=0.20, w2=0.30, w3=0.20, w4=0.15, w5=0.15
  Rationale: dependency relations (w2) are weighted highest because coupling
  is the primary driver of blast-radius in JCL/COBOL systems; step count and
  structural complexity share second tier; dataset refs and conditions are
  weighted slightly lower due to higher parser noise on public JCL corpora.

Risk threshold: 0.5 (normalized score ∈ [0, 1])
  Rationale: mid-point threshold avoids any bias toward recall or precision
  before observing results. This is the pre-specified value as required by
  the experimental protocol (see docs/baseline_final_specification.md).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from legacy_contract.ir.model import (
    EntityType,
    IRGraph,
    RelationType,
)
from baselines.base import BaselineResult

# ---------------------------------------------------------------------------
# Pre-specified metric weights (frozen — do NOT change after evaluation)
# ---------------------------------------------------------------------------

METRIC_WEIGHTS: dict[str, float] = {
    "structural_complexity":    0.20,
    "dependency_count":         0.30,
    "step_count":               0.20,
    "dataset_reference_count":  0.15,
    "condition_count":          0.15,
}

# Pre-specified risk threshold (frozen — do NOT change after seeing results)
RISK_THRESHOLD: float = 0.50

# Relation types that count as "dependency" for M2
_DEPENDENCY_RELATION_TYPES = {
    RelationType.PRODUCES,
    RelationType.CONSUMES,
    RelationType.CALLS,
}


# ---------------------------------------------------------------------------
# Per-artifact metrics container
# ---------------------------------------------------------------------------

class ArtifactMetrics:
    """Raw and normalized complexity metrics for one artifact."""

    def __init__(self, artifact_path: str) -> None:
        self.artifact_path = artifact_path
        # Raw counts
        self.structural_complexity: int = 0
        self.dependency_count: int = 0
        self.step_count: int = 0
        self.dataset_reference_count: int = 0
        self.condition_count: int = 0
        # Normalized scores (set by ComplexityBaseline after seeing all artifacts)
        self.normalized: dict[str, float] = {}
        self.risk_score: float = 0.0

    def raw_dict(self) -> dict[str, int]:
        return {
            "structural_complexity": self.structural_complexity,
            "dependency_count":      self.dependency_count,
            "step_count":            self.step_count,
            "dataset_reference_count": self.dataset_reference_count,
            "condition_count":       self.condition_count,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_path": self.artifact_path,
            "raw": self.raw_dict(),
            "normalized": self.normalized,
            "risk_score": self.risk_score,
        }


# ---------------------------------------------------------------------------
# Complexity Baseline
# ---------------------------------------------------------------------------

class ComplexityBaseline:
    """
    Baseline B: Complexity Metrics.

    Usage::

        baseline = ComplexityBaseline()
        # Supply an already-parsed IRGraph covering all artifacts
        result = baseline.predict(ir, mutation, contract_ids)

    If you have raw artifact paths but no IR, use ComplexityBaseline.from_paths()
    which will invoke the JCL/COBOL parsers internally.
    """

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------

    def compute_metrics(self, ir: IRGraph) -> dict[str, ArtifactMetrics]:
        """
        Compute per-artifact complexity metrics from an IRGraph.

        Returns a dict mapping artifact_path -> ArtifactMetrics.
        """
        metrics: dict[str, ArtifactMetrics] = {}

        # Initialise one ArtifactMetrics per known artifact path
        for path in ir.artifact_paths:
            metrics[path] = ArtifactMetrics(path)

        # M1: structural_complexity — count all entities per artifact
        for entity in ir.entities.values():
            ap = entity.artifact_path
            if ap not in metrics:
                metrics[ap] = ArtifactMetrics(ap)
            metrics[ap].structural_complexity += 1

            # M3: step_count
            if entity.entity_type == EntityType.STEP:
                metrics[ap].step_count += 1

            # M4: dataset_reference_count
            if entity.entity_type in {EntityType.DATASET, EntityType.FILE}:
                metrics[ap].dataset_reference_count += 1

            # M5: condition_count — COND attributes on STEP entities
            if entity.entity_type == EntityType.STEP and entity.attributes.get("cond"):
                # Count comma-separated COND clauses as individual conditions
                cond_str = str(entity.attributes["cond"])
                # Simple heuristic: each occurrence of a digit followed by a
                # comparison operator is one condition
                import re
                condition_hits = re.findall(
                    r"\d+,\s*(?:GT|LT|EQ|NE|GE|LE|EVEN|ONLY)",
                    cond_str,
                    re.IGNORECASE,
                )
                metrics[ap].condition_count += max(1, len(condition_hits))

        # M2: dependency_count — count PRODUCES/CONSUMES/CALLS relations per
        #     source artifact.  We attribute each relation to the source entity's
        #     artifact so that the artifact that "owns" a dependency bears its cost.
        for relation in ir.relations:
            if relation.relation_type in _DEPENDENCY_RELATION_TYPES:
                ap = relation.source.artifact_path
                if ap not in metrics:
                    metrics[ap] = ArtifactMetrics(ap)
                metrics[ap].dependency_count += 1

        return metrics

    def normalize(
        self, metrics: dict[str, ArtifactMetrics]
    ) -> dict[str, ArtifactMetrics]:
        """
        Min-max normalize each metric dimension across all artifacts.

        Sets ArtifactMetrics.normalized and ArtifactMetrics.risk_score in place.
        Returns the same dict for convenience.
        """
        if not metrics:
            return metrics

        metric_names = list(METRIC_WEIGHTS.keys())

        # Compute per-dimension min and max
        min_vals: dict[str, float] = {m: float("inf") for m in metric_names}
        max_vals: dict[str, float] = {m: float("-inf") for m in metric_names}

        for am in metrics.values():
            raw = am.raw_dict()
            for m in metric_names:
                v = float(raw[m])
                if v < min_vals[m]:
                    min_vals[m] = v
                if v > max_vals[m]:
                    max_vals[m] = v

        # Normalize and compute weighted risk_score
        for am in metrics.values():
            raw = am.raw_dict()
            for m in metric_names:
                lo, hi = min_vals[m], max_vals[m]
                if hi > lo:
                    am.normalized[m] = (float(raw[m]) - lo) / (hi - lo)
                else:
                    # All artifacts have the same value → normalized = 0
                    am.normalized[m] = 0.0

            am.risk_score = sum(
                METRIC_WEIGHTS[m] * am.normalized[m]
                for m in metric_names
            )

        return metrics

    def predict(
        self,
        ir: IRGraph,
        mutation: Any,          # MutationRecord — typed as Any to avoid hard import
        contract_ids: list[str],
    ) -> BaselineResult:
        """
        Predict which contracts are violated given a mutation.

        Strategy: flag all contract_ids as predicted_violated if the artifact
        affected by the mutation has risk_score > RISK_THRESHOLD.

        Parameters
        ----------
        ir:
            Parsed IR covering all artifacts.
        mutation:
            A MutationRecord (from legacy_contract.mutations.engine).
        contract_ids:
            All contract IDs that exist in the BCG; the baseline must produce
            a prediction for each one.

        Returns
        -------
        BaselineResult
        """
        run_id = str(uuid.uuid4())[:12]
        timestamp = datetime.now(tz=timezone.utc).isoformat()

        metrics = self.compute_metrics(ir)
        self.normalize(metrics)

        # Determine which artifact paths are "affected" by this mutation.
        # We do this by mapping affected_entity_ids → their artifact_paths.
        affected_artifact_paths: set[str] = set()
        for eid in mutation.affected_entity_ids:
            entity = ir.get_entity(eid)
            if entity:
                affected_artifact_paths.add(entity.artifact_path)

        # If we cannot map any entity to an artifact, fall back to all artifacts
        if not affected_artifact_paths:
            affected_artifact_paths = set(metrics.keys())

        # Determine HIGH risk flag based on max risk_score among affected artifacts
        max_risk = max(
            (metrics[ap].risk_score for ap in affected_artifact_paths if ap in metrics),
            default=0.0,
        )
        is_high_risk = max_risk > RISK_THRESHOLD

        predictions: dict[str, bool] = {}
        confidence: dict[str, float] = {}

        for cid in contract_ids:
            predictions[cid] = is_high_risk
            # Confidence = normalized risk score of the most complex affected artifact
            confidence[cid] = round(max_risk, 4)

        return BaselineResult(
            method="complexity_metrics",
            predictions=predictions,
            confidence=confidence,
            metadata={
                "risk_threshold":           RISK_THRESHOLD,
                "metric_weights":           METRIC_WEIGHTS,
                "affected_artifact_paths":  list(affected_artifact_paths),
                "max_risk_score":           round(max_risk, 4),
                "is_high_risk":             is_high_risk,
                "per_artifact_metrics": {
                    ap: am.to_dict() for ap, am in metrics.items()
                },
            },
            run_id=run_id,
            timestamp=timestamp,
        )
