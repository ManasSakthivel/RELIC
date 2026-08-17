"""
Benchmark — ground truth management for contract recovery evaluation.

Loads ground truth from benchmark/ground_truth/*.json files.
Supports three levels of evidence quality:
  Level 1 (EXECUTION_ORACLE):         highest-confidence, from execution oracle comparison
  Level 2 (DETERMINISTIC):            mechanically verifiable structural facts from parsers
  Level 3 (HUMAN_ANNOTATED):          expert annotator interpretation of implicit contracts
  Level 4 (RESEARCHER_ADJUDICATED):   used when expert annotations disagree

Ground truth integrity rules:
  - Every benchmark item must record ground_truth_source.
  - Annotator IDs are recorded for every human-annotated item.
  - Inter-annotator agreement (IAA) is computed per contract type using Cohen's kappa.
  - Items with IAA < 0.6 are marked UNRESOLVED pending researcher adjudication.
  - The benchmark must NOT be modified after the first experiment run (leakage prevention).

Reference for kappa: Landis & Koch (1977), Artstein & Poesio (2008).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Ground Truth Level
# ---------------------------------------------------------------------------

class GroundTruthLevel(str, Enum):
    """
    Hierarchy of ground-truth evidence quality.

    Ordering: EXECUTION_ORACLE > DETERMINISTIC > HUMAN_ANNOTATED > RESEARCHER_ADJUDICATED

    NOTE: Higher level does NOT mean more contracts. It means higher confidence
    in the correctness of the annotation.
    """
    EXECUTION_ORACLE = "EXECUTION_ORACLE"
    DETERMINISTIC = "DETERMINISTIC"
    HUMAN_ANNOTATED = "HUMAN_ANNOTATED"
    RESEARCHER_ADJUDICATED = "RESEARCHER_ADJUDICATED"


# ---------------------------------------------------------------------------
# Benchmark Item
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkItem:
    """
    A single benchmark annotation for contract recovery evaluation.

    Each item represents one ground-truth behavioral contract.
    All fields are mandatory for items used in published evaluations.
    """
    contract_id: str
    artifact: str                   # Artifact path or identifier
    location: str                   # line:col or descriptive location
    contract_type: str              # TEMPORAL | RESOURCE | CONTROL_FLOW
    contract_statement: str         # Natural language statement
    formal_statement: str | None    # LTL or formal notation (optional)
    evidence: str                   # What evidence justifies this contract
    ground_truth: bool              # True = contract exists; False = does not
    ground_truth_source: GroundTruthLevel
    annotator_ids: list[str] = field(default_factory=list)   # Empty for deterministic items
    annotation_date: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "artifact": self.artifact,
            "location": self.location,
            "contract_type": self.contract_type,
            "contract_statement": self.contract_statement,
            "formal_statement": self.formal_statement,
            "evidence": self.evidence,
            "ground_truth": self.ground_truth,
            "ground_truth_source": self.ground_truth_source.value,
            "annotator_ids": self.annotator_ids,
            "annotation_date": self.annotation_date,
            "notes": self.notes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkItem":
        # Ground-truth JSON produced by the deterministic benchmark builder uses the
        # key "source" for the artifact path; BenchmarkItem.artifact is the canonical
        # internal name.  Accept both for backward compatibility.
        artifact = data.get("artifact") or data.get("source", "")
        # Similarly, the key "ground_truth_label" is used by the benchmark builder
        # while "ground_truth" is the canonical key. Accept both.
        ground_truth_val = data.get("ground_truth")
        if ground_truth_val is None:
            ground_truth_val = data.get("ground_truth_label", False)
        # "ground_truth_source" may be stored as "ground_truth_level" in older files.
        gt_source_raw = data.get("ground_truth_source") or data.get("ground_truth_level", "DETERMINISTIC")
        # "contract_statement" may be stored as "natural_language" in benchmark builder output.
        contract_statement = data.get("contract_statement") or data.get("natural_language", "")
        # "location" may be stored as "evidence" field.
        location = data.get("location") or data.get("evidence", "")
        return cls(
            contract_id=data["contract_id"],
            artifact=artifact,
            location=location,
            contract_type=data["contract_type"],
            contract_statement=contract_statement,
            formal_statement=data.get("formal_statement"),
            evidence=data.get("evidence", ""),
            ground_truth=bool(ground_truth_val),
            ground_truth_source=GroundTruthLevel(gt_source_raw),
            annotator_ids=data.get("annotator_ids", []),
            annotation_date=data.get("annotation_date", datetime.utcnow().isoformat()),
            notes=data.get("notes", ""),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

class Benchmark:
    """
    Ground truth collection for contract recovery evaluation.

    Manages benchmark items, supports multi-annotator scenarios,
    computes inter-annotator agreement, and exports annotation tasks.

    Leakage prevention: once items are added and experiments begin,
    the benchmark should be treated as read-only. Use Benchmark.is_locked()
    to enforce this in experiment runners.
    """

    def __init__(self) -> None:
        self._items: dict[str, BenchmarkItem] = {}  # contract_id -> item
        self._locked: bool = False
        self._lock_timestamp: str | None = None
        self._created_at: str = datetime.utcnow().isoformat()
        self._metadata: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str) -> "Benchmark":
        """
        Load benchmark from a JSON file.

        Expected format:
        {
            "metadata": {...},
            "locked": false,
            "lock_timestamp": null,
            "items": [<BenchmarkItem.to_dict()>, ...]
        }
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Benchmark file not found: {path}")

        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)

        benchmark = cls()
        benchmark._locked = data.get("locked", False)
        benchmark._lock_timestamp = data.get("lock_timestamp")
        benchmark._created_at = data.get("created_at", benchmark._created_at)
        benchmark._metadata = data.get("metadata", {})

        for item_data in data.get("items", []):
            item = BenchmarkItem.from_dict(item_data)
            benchmark._items[item.contract_id] = item

        return benchmark

    def save(self, path: str) -> None:
        """Save benchmark to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "created_at": self._created_at,
            "locked": self._locked,
            "lock_timestamp": self._lock_timestamp,
            "metadata": self._metadata,
            "items": [item.to_dict() for item in self._items.values()],
        }
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Item management
    # ------------------------------------------------------------------

    def add_item(self, item: BenchmarkItem) -> None:
        """
        Add a benchmark item.

        Raises RuntimeError if the benchmark is locked (leakage prevention).
        """
        if self._locked:
            raise RuntimeError(
                "Benchmark is locked. Items cannot be added after lock. "
                "Unlock intentionally only if adding held-out items before final evaluation."
            )
        self._items[item.contract_id] = item

    def get_item(self, contract_id: str) -> BenchmarkItem | None:
        return self._items.get(contract_id)

    def get_by_type(self, contract_type: str) -> list[BenchmarkItem]:
        """Return all items of the given contract type."""
        return [
            item for item in self._items.values()
            if item.contract_type == contract_type
        ]

    def get_by_level(self, level: GroundTruthLevel) -> list[BenchmarkItem]:
        """Return all items at a given ground truth level."""
        return [
            item for item in self._items.values()
            if item.ground_truth_source == level
        ]

    def get_positives(self) -> list[BenchmarkItem]:
        """Return only ground-truth-positive items."""
        return [item for item in self._items.values() if item.ground_truth]

    def get_negatives(self) -> list[BenchmarkItem]:
        """Return only ground-truth-negative items (confirmed absent contracts)."""
        return [item for item in self._items.values() if not item.ground_truth]

    def get_unannotated(self) -> list[BenchmarkItem]:
        """Return items with no human annotators assigned (DETERMINISTIC or EXECUTION_ORACLE)."""
        return [item for item in self._items.values() if not item.annotator_ids]

    def all_items(self) -> list[BenchmarkItem]:
        return list(self._items.values())

    def item_count(self) -> int:
        return len(self._items)

    # ------------------------------------------------------------------
    # Locking
    # ------------------------------------------------------------------

    def lock(self) -> None:
        """
        Lock the benchmark to prevent further modifications.
        Must be called before running experiments to prevent leakage.
        """
        self._locked = True
        self._lock_timestamp = datetime.utcnow().isoformat()

    def is_locked(self) -> bool:
        return self._locked

    # ------------------------------------------------------------------
    # Inter-Annotator Agreement (IAA)
    # ------------------------------------------------------------------

    def compute_iaa(self) -> dict[str, Any]:
        """
        Compute inter-annotator agreement using Cohen's kappa.

        Only items with ≥ 2 annotators are included.
        Returns IAA per contract type and overall.

        Cohen's kappa = (P_o - P_e) / (1 - P_e)
        where P_o = observed agreement, P_e = expected agreement by chance.

        Reference: Cohen (1960), Landis & Koch (1977) scale:
          κ < 0.20: slight  0.21-0.40: fair  0.41-0.60: moderate
          0.61-0.80: substantial  0.81-1.00: almost perfect

        Returns:
            dict with "overall" and per-type kappa values, plus raw agreement counts.

        SCIENTIFIC NOTE: κ is only meaningful for categorical agreement.
        If annotators use non-binary labels (e.g., confidence scores),
        use weighted kappa instead.
        """
        # Collect multi-annotated items
        multi_items = [
            item for item in self._items.values() if len(item.annotator_ids) >= 2
        ]

        if len(multi_items) < 2:
            return {
                "overall": None,
                "per_type": {},
                "n_items": len(multi_items),
                "warning": "Fewer than 2 multi-annotated items. IAA cannot be computed.",
            }

        # For computing kappa we need per-annotator labels.
        # The benchmark stores a single resolved ground_truth.
        # IAA is estimated from metadata["annotator_labels"] if present,
        # otherwise we cannot compute kappa and return a warning.
        annotator_label_map: dict[str, dict[str, int]] = {}
        # annotator_label_map[item.contract_id][annotator_id] = 0|1

        for item in multi_items:
            if "annotator_labels" in item.metadata:
                annotator_label_map[item.contract_id] = {
                    k: int(v)
                    for k, v in item.metadata["annotator_labels"].items()
                }

        if not annotator_label_map:
            return {
                "overall": None,
                "per_type": {},
                "n_items": len(multi_items),
                "warning": (
                    "No annotator_labels found in item metadata. "
                    "Populate BenchmarkItem.metadata['annotator_labels'] "
                    "as {annotator_id: 0|1} to compute IAA."
                ),
            }

        # Collect all annotator pairs across items
        # For each pair of annotators, collect their binary labels on common items
        all_annotators: set[str] = set()
        for labels in annotator_label_map.values():
            all_annotators.update(labels.keys())

        annotators = sorted(all_annotators)

        # Compute overall kappa using Fleiss' approach reduced to pairwise Cohen's kappa
        # Aggregated across all annotator pairs
        pairwise_kappas: list[float] = []
        for i in range(len(annotators)):
            for j in range(i + 1, len(annotators)):
                a1, a2 = annotators[i], annotators[j]
                agreed: list[tuple[int, int]] = []
                for cid, labels in annotator_label_map.items():
                    if a1 in labels and a2 in labels:
                        agreed.append((labels[a1], labels[a2]))
                if len(agreed) >= 2:
                    k = self._cohens_kappa(agreed)
                    pairwise_kappas.append(k)

        overall_kappa = (
            sum(pairwise_kappas) / len(pairwise_kappas) if pairwise_kappas else None
        )

        # Per-type kappa
        per_type_kappa: dict[str, float | None] = {}
        all_types = sorted({item.contract_type for item in multi_items})
        for ctype in all_types:
            type_items = [item for item in multi_items if item.contract_type == ctype]
            type_pairs: list[tuple[int, int]] = []
            for item in type_items:
                if item.contract_id not in annotator_label_map:
                    continue
                labels = annotator_label_map[item.contract_id]
                for i in range(len(annotators)):
                    for j in range(i + 1, len(annotators)):
                        a1, a2 = annotators[i], annotators[j]
                        if a1 in labels and a2 in labels:
                            type_pairs.append((labels[a1], labels[a2]))
            per_type_kappa[ctype] = (
                self._cohens_kappa(type_pairs) if len(type_pairs) >= 2 else None
            )

        return {
            "overall": overall_kappa,
            "per_type": per_type_kappa,
            "n_items": len(multi_items),
            "n_annotators": len(annotators),
            "n_pairwise_kappas": len(pairwise_kappas),
            "interpretation": self._interpret_kappa(overall_kappa),
        }

    @staticmethod
    def _cohens_kappa(pairs: list[tuple[int, int]]) -> float:
        """
        Compute Cohen's kappa for a list of (annotator_1_label, annotator_2_label) pairs.
        Labels are binary (0 or 1).
        """
        if not pairs:
            return 0.0
        n = len(pairs)

        # Observed agreement
        p_o = sum(1 for a, b in pairs if a == b) / n

        # Expected agreement by chance
        p1_a = sum(a for a, _ in pairs) / n   # P(label=1 from annotator A)
        p1_b = sum(b for _, b in pairs) / n   # P(label=1 from annotator B)
        p0_a = 1.0 - p1_a
        p0_b = 1.0 - p1_b
        p_e = p1_a * p1_b + p0_a * p0_b

        if p_e >= 1.0:
            return 1.0  # Perfect agreement, P_e = 1 edge case
        return (p_o - p_e) / (1.0 - p_e)

    @staticmethod
    def _interpret_kappa(kappa: float | None) -> str:
        if kappa is None:
            return "insufficient data"
        if kappa < 0.0:
            return "poor (less than chance)"
        if kappa < 0.20:
            return "slight"
        if kappa < 0.40:
            return "fair"
        if kappa < 0.60:
            return "moderate"
        if kappa < 0.80:
            return "substantial"
        return "almost perfect"

    # ------------------------------------------------------------------
    # Annotation export
    # ------------------------------------------------------------------

    def export_for_annotation(self, output_path: str) -> None:
        """
        Export unannotated items to a JSON file for human annotation.

        Exported format omits ground_truth to prevent annotator anchoring.
        Each item has an empty annotator_labels field for the annotator to fill.

        Annotation instructions are included in the export.
        """
        unannotated = self.get_unannotated()
        export_items = []
        for item in unannotated:
            export_item = {
                "contract_id": item.contract_id,
                "artifact": item.artifact,
                "location": item.location,
                "contract_type": item.contract_type,
                "contract_statement": item.contract_statement,
                "formal_statement": item.formal_statement,
                "evidence": item.evidence,
                # ground_truth OMITTED intentionally to prevent anchoring
                "annotator_labels": {},      # fill in: {"annotator_id": 0 or 1}
                "annotator_confidence": {},  # fill in: {"annotator_id": 0.0-1.0}
                "annotator_notes": {},       # fill in: {"annotator_id": "..."}
                "metadata": {
                    k: v for k, v in item.metadata.items()
                    if k not in {"annotator_labels"}
                },
            }
            export_items.append(export_item)

        instructions = {
            "annotation_instructions": (
                "For each item, determine whether the stated behavioral contract "
                "genuinely exists in the artifact at the given location. "
                "Set annotator_labels[your_id] = 1 if the contract holds, 0 if not. "
                "Set annotator_confidence[your_id] = your confidence (0.0–1.0). "
                "Add notes in annotator_notes[your_id] for ambiguous cases. "
                "Do NOT look at other annotators' labels before completing yours."
            ),
            "label_schema": {
                "1": "Contract exists and is correct",
                "0": "Contract does not exist or is incorrect",
            },
            "n_items": len(export_items),
            "export_timestamp": datetime.utcnow().isoformat(),
        }

        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(
                {"instructions": instructions, "items": export_items},
                f,
                indent=2,
                ensure_ascii=False,
            )

    def import_annotations(self, annotation_path: str) -> None:
        """
        Import completed annotation file and update items with annotator labels.

        Does not overwrite ground_truth — that requires researcher adjudication.
        """
        if self._locked:
            raise RuntimeError(
                "Benchmark is locked. Cannot import annotations after lock."
            )
        p = Path(annotation_path)
        if not p.exists():
            raise FileNotFoundError(f"Annotation file not found: {annotation_path}")

        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)

        items_data = data.get("items", data)  # support both wrapped and bare lists
        n_updated = 0
        for ann_item in items_data:
            cid = ann_item.get("contract_id")
            if cid and cid in self._items:
                item = self._items[cid]
                labels = ann_item.get("annotator_labels", {})
                if labels:
                    item.metadata.setdefault("annotator_labels", {}).update(labels)
                    item.annotator_ids = sorted(set(item.annotator_ids) | set(labels.keys()))
                n_updated += 1

        return n_updated  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> str:
        type_counts: dict[str, int] = {}
        level_counts: dict[str, int] = {}
        for item in self._items.values():
            type_counts[item.contract_type] = type_counts.get(item.contract_type, 0) + 1
            level_counts[item.ground_truth_source.value] = (
                level_counts.get(item.ground_truth_source.value, 0) + 1
            )
        n_pos = sum(1 for item in self._items.values() if item.ground_truth)
        n_neg = self.item_count() - n_pos
        lines = [
            f"Benchmark: {self.item_count()} items  (+:{n_pos} -:{n_neg})",
            f"Locked: {self._locked}",
            "Types: " + ", ".join(f"{k}={v}" for k, v in sorted(type_counts.items())),
            "Sources: " + ", ".join(f"{k}={v}" for k, v in sorted(level_counts.items())),
        ]
        return "\n".join(lines)
