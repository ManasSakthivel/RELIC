#!/usr/bin/env python3
"""
import_annotation_results.py

Imports completed human annotation results into the Level-3 ground truth.

Usage:
    python scripts/import_annotation_results.py \
        --annotator-a results/annotator_a.json \
        --annotator-b results/annotator_b.json \
        [--output benchmark/ground_truth/level3_human.json]

What this script does:
    1. Loads both annotators' completed annotation files
    2. Computes inter-annotator agreement (Cohen's κ for binary contract_exists,
       and per-contract-type κ)
    3. Identifies items with disagreement (different contract_exists verdict)
    4. Flags disagreements as requiring adjudication
    5. Writes a Level-3 ground truth JSON with:
       - Items agreed by both annotators (high confidence)
       - Items flagged for adjudication (pending)
       - Inter-annotator statistics

SCIENTIFIC INTEGRITY:
    This script must NOT:
    - Automatically resolve disagreements by majority vote
    - Use the Level-2 ground truth to resolve disagreements
    - Silently discard disagreed items
    All disagreements must go through human adjudication.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).parent.parent
DEFAULT_OUTPUT = ROOT / "benchmark" / "ground_truth" / "level3_human.json"


def _load_annotations(path: str) -> list[dict]:
    p = pathlib.Path(path)
    if not p.exists():
        print(f"ERROR: Annotation file not found: {p}")
        sys.exit(1)
    with open(p) as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("items", data.get("annotations", []))
    return data


def _cohen_kappa(a_labels: list, b_labels: list) -> float:
    """Compute Cohen's κ for binary (True/False) annotations."""
    if len(a_labels) != len(b_labels):
        return float("nan")
    n = len(a_labels)
    if n == 0:
        return float("nan")

    agree = sum(1 for a, b in zip(a_labels, b_labels) if a == b)
    p_o = agree / n

    # Expected agreement by chance
    a_true = sum(1 for a in a_labels if a is True or a == "true")
    b_true = sum(1 for b in b_labels if b is True or b == "true")
    p_e = (a_true / n) * (b_true / n) + ((n - a_true) / n) * ((n - b_true) / n)

    if p_e == 1.0:
        return 1.0
    return (p_o - p_e) / (1.0 - p_e)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import annotation results")
    parser.add_argument("--annotator-a", required=True, help="Annotator A results JSON")
    parser.add_argument("--annotator-b", required=True, help="Annotator B results JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output path")
    args = parser.parse_args()

    items_a = _load_annotations(args.annotator_a)
    items_b = _load_annotations(args.annotator_b)

    print(f"Annotator A: {len(items_a)} items")
    print(f"Annotator B: {len(items_b)} items")

    # Build lookup by annotation_item_id
    a_by_id = {item["annotation_item_id"]: item for item in items_a}
    b_by_id = {item["annotation_item_id"]: item for item in items_b}

    common_ids = sorted(set(a_by_id) & set(b_by_id))
    print(f"Common items: {len(common_ids)}")

    # Compute overall κ
    a_exists = [a_by_id[i]["contract_exists"] for i in common_ids]
    b_exists = [b_by_id[i]["contract_exists"] for i in common_ids]
    kappa = _cohen_kappa(a_exists, b_exists)
    print(f"Overall Cohen's κ (contract_exists): {kappa:.3f}")

    if kappa < 0.60:
        print(
            f"WARNING: κ = {kappa:.3f} < 0.60 — annotation task may be underspecified. "
            "Review annotation guidelines before using this ground truth."
        )

    # Categorize items
    agreed_positive = []
    agreed_negative = []
    disagreed = []
    uncertain = []

    for item_id in common_ids:
        a = a_by_id[item_id]
        b = b_by_id[item_id]
        a_exists = a.get("contract_exists")
        b_exists = b.get("contract_exists")

        if a_exists == "uncertain" or b_exists == "uncertain":
            uncertain.append({
                "annotation_item_id": item_id,
                "status": "UNCERTAIN",
                "annotator_a": a,
                "annotator_b": b,
            })
        elif a_exists == b_exists:
            item = {
                "annotation_item_id": item_id,
                "status": "AGREED",
                "ground_truth_label": bool(a_exists),
                "ground_truth_level": "LEVEL3_HUMAN",
                "adjudicated": False,
                "annotator_a": {"contract_exists": a_exists, "contract_type": a.get("annotated_contract_type")},
                "annotator_b": {"contract_exists": b_exists, "contract_type": b.get("annotated_contract_type")},
            }
            if a_exists:
                agreed_positive.append(item)
            else:
                agreed_negative.append(item)
        else:
            disagreed.append({
                "annotation_item_id": item_id,
                "status": "REQUIRES_ADJUDICATION",
                "ground_truth_label": None,  # MUST be resolved by adjudicator
                "ground_truth_level": "LEVEL3_HUMAN_PENDING_ADJUDICATION",
                "adjudicated": False,
                "annotator_a": {"contract_exists": a_exists},
                "annotator_b": {"contract_exists": b_exists},
                "note": (
                    "Disagreement between annotators. "
                    "A third annotator must adjudicate before this item can be used in evaluation."
                ),
            })

    print(f"\nAgreed positive: {len(agreed_positive)}")
    print(f"Agreed negative: {len(agreed_negative)}")
    print(f"Disagreed (requires adjudication): {len(disagreed)}")
    print(f"Uncertain: {len(uncertain)}")

    # Build output
    all_items = agreed_positive + agreed_negative + disagreed + uncertain
    output = {
        "ground_truth_level": "LEVEL3_HUMAN",
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "benchmark_version": "v1.0-level3-human-pending",
        "source_type": "HUMAN_ANNOTATION",
        "annotators": {
            "annotator_a": args.annotator_a,
            "annotator_b": args.annotator_b,
        },
        "inter_annotator_agreement": {
            "cohens_kappa_overall": round(kappa, 4) if kappa == kappa else None,
            "kappa_threshold_met": bool(kappa >= 0.60),
            "n_common_items": len(common_ids),
        },
        "summary": {
            "agreed_positive": len(agreed_positive),
            "agreed_negative": len(agreed_negative),
            "disagreed_pending_adjudication": len(disagreed),
            "uncertain": len(uncertain),
            "usable_for_evaluation": len(agreed_positive) + len(agreed_negative),
        },
        "status": (
            "READY_FOR_EVALUATION"
            if not disagreed and kappa >= 0.60
            else "REQUIRES_ADJUDICATION"
        ),
        "items": all_items,
    }

    output_path = pathlib.Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nLevel-3 ground truth written to: {output_path}")
    if disagreed:
        print(
            f"\nNOTE: {len(disagreed)} items require adjudication before the evaluation "
            "can be considered complete. See the adjudication protocol in "
            "docs/annotation_protocol_final.md §8."
        )


if __name__ == "__main__":
    main()
