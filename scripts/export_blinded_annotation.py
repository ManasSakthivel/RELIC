#!/usr/bin/env python3
"""
export_blinded_annotation.py

Exports a blinded annotation package from the Level-2 benchmark.

The exported package contains:
  - Artifact identifier (JCL filename)
  - Relevant source excerpt (lines around the contract)
  - Surrounding context (±20 lines)
  - Annotation instructions reference
  - Contract candidate fields (subject_id, predicate, object_id, natural_language)
    WITHOUT any ground_truth_label, confidence_score, or validation_state

The exported package DOES NOT contain:
  - ground_truth_label (the expected answer)
  - contract_id in the BCG namespace (could anchor annotator)
  - confidence_score
  - validation_state
  - source_label (DETERMINISTIC, LLM, etc.)
  - annotator field from Level-2 (which would reveal the extraction algorithm)
  - BCG output JSON

Usage:
    python scripts/export_blinded_annotation.py [--output DIR] [--sample N]

The output directory will contain:
    annotation_items.json   — blinded items for annotation
    README.md               — instructions for annotators
    annotation_form.json    — blank form template

SCIENTIFIC INTEGRITY:
    This script enforces blinding by construction.
    Any field that could reveal the system's prediction is stripped.
    This script must NOT be modified to include system predictions.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import textwrap
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).parent.parent
GROUND_TRUTH_PATH = ROOT / "benchmark" / "ground_truth" / "level2_deterministic.json"
DEFAULT_OUTPUT_DIR = ROOT / "benchmark" / "annotation_package"

# Fields from level2 items that must be STRIPPED (would reveal system output)
STRIP_FIELDS = {
    "ground_truth_label",
    "ground_truth_level",
    "source_label",
    "annotator",
    "adjudication_status",
    "note",
    "contract_id",   # BCG-namespace ID could anchor annotator
}

# Fields that are safe to include (help annotator understand the artifact)
SAFE_FIELDS = {
    "contract_type",  # included so annotator understands the question being asked
    "subject_id",     # step/entity name — artifact-level, not system output
    "predicate",      # observable from JCL syntax
    "object_id",      # step/entity name
    "natural_language",  # human-readable description of the contract candidate
    "evidence",       # source excerpt — the JCL/COBOL text itself
    "source",         # JCL filename
}


def _load_ground_truth() -> list[dict]:
    if not GROUND_TRUTH_PATH.exists():
        print(f"ERROR: Ground truth file not found: {GROUND_TRUTH_PATH}")
        sys.exit(1)
    with open(GROUND_TRUTH_PATH) as f:
        data = json.load(f)
    return data.get("items", [])


def _make_blinded_item(item: dict, item_index: int) -> dict:
    """
    Create a blinded annotation item from a Level-2 ground truth item.

    Strips all fields that could reveal the system's prediction.
    Assigns a neutral annotation_item_id that does not reveal the contract_id.
    """
    blinded = {
        "annotation_item_id": f"ITEM-{item_index:04d}",
        # Reveal only safe fields
        "artifact": item.get("source", ""),
        "contract_type_prompt": item.get("contract_type", ""),
        "subject": item.get("subject_id", ""),
        "predicate": item.get("predicate", ""),
        "object": item.get("object_id", ""),
        "description": item.get("natural_language", ""),
        "source_excerpt": item.get("evidence", ""),

        # Annotation fields — left blank for annotator to fill
        "annotator_id": "",
        "contract_exists": None,
        "annotated_contract_type": None,
        "annotated_subject": "",
        "annotated_predicate": "",
        "annotated_object": "",
        "evidence_span": "",
        "confidence": None,
        "notes": "",
        "uncertainty_flag": False,
        "uncertainty_reason": "",
    }

    # Verify no forbidden fields leaked through
    for forbidden in STRIP_FIELDS:
        assert forbidden not in blinded, f"Blinding violation: '{forbidden}' in blinded item"

    return blinded


def _write_readme(output_dir: pathlib.Path) -> None:
    readme = textwrap.dedent("""
    # Annotation Package — LEGACY-CONTRACT Level-3 Ground Truth

    ## Your Task

    You are asked to annotate behavioral contracts in JCL (Job Control Language) source excerpts.

    For each item in `annotation_items.json`:
    1. Read the `source_excerpt` field — this is the JCL or COBOL text
    2. Determine whether the excerpt contains a behavioral contract
    3. Fill in the annotation fields using the annotation form

    ## Blinding Notice

    **This package does not contain any automated system predictions.**
    Your judgments must be formed independently from the source text alone.
    Do not consult other annotators until you have submitted your completed form.

    ## Contract Types

    - **TEMPORAL**: An obligation that one step/action must occur before another
      - Example: "STEP01 must complete before STEP02 reads CUSTFILE"
    - **RESOURCE**: An obligation that a resource must exist/be ready before use
      - Example: "Dataset ACCTFILE must be initialized before CBACT02C reads it"
    - **CONTROL_FLOW**: An obligation governing execution based on return codes
      - Example: "If STEP01 returns RC > 4, then STEP02 must not execute"

    ## Confidence Scale

    - 1 = Low (ambiguous; the contract may or may not exist)
    - 2 = Medium (likely a contract but with some uncertainty)
    - 3 = High (clearly a contract with strong textual evidence)

    ## Submitting Your Annotations

    Fill in the `annotation_items.json` file and return it to the protocol coordinator.
    Do NOT share your responses with the other annotator before submission.

    ## Questions

    Contact the protocol coordinator with any questions about the annotation schema.
    Do NOT contact the research team as they have knowledge of system predictions.
    """).strip()

    (output_dir / "README.md").write_text(readme + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export blinded annotation package")
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for annotation package"
    )
    parser.add_argument(
        "--sample", type=int, default=0,
        help="Sample N items (0 = all items)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for sampling"
    )
    args = parser.parse_args()

    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    items = _load_ground_truth()
    print(f"Loaded {len(items)} items from Level-2 ground truth")

    if args.sample > 0:
        rng = random.Random(args.seed)
        items = rng.sample(items, min(args.sample, len(items)))
        print(f"Sampled {len(items)} items (seed={args.seed})")

    blinded_items = []
    for i, item in enumerate(items):
        blinded_items.append(_make_blinded_item(item, i + 1))

    # Write annotation items
    output_path = output_dir / "annotation_items.json"
    with open(output_path, "w") as f:
        json.dump({
            "export_timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "n_items": len(blinded_items),
            "blinding_protocol": "docs/annotation_blinding_protocol.md",
            "annotation_protocol": "docs/annotation_protocol_final.md",
            "items": blinded_items,
        }, f, indent=2)

    # Write blank form template
    form_template = {
        "annotation_item_id": "ITEM-XXXX",
        "annotator_id": "<your anonymized ID>",
        "annotation_timestamp": "<ISO8601 timestamp>",
        "contract_exists": "<true | false | uncertain>",
        "if_contract_exists": {
            "contract_type": "<TEMPORAL | RESOURCE | CONTROL_FLOW>",
            "subject": "<step or entity name>",
            "predicate": "<MUST_PRECEDE | PRODUCES_BEFORE_CONSUMES | MUST_NOT_FOLLOW_ON_ERROR | other>",
            "object": "<step, entity, or resource name>",
            "evidence_span": "<exact text from source_excerpt>",
            "confidence": "<1 | 2 | 3>"
        },
        "notes": "",
        "uncertainty_flag": False,
        "uncertainty_reason": ""
    }
    with open(output_dir / "annotation_form.json", "w") as f:
        json.dump(form_template, f, indent=2)

    _write_readme(output_dir)

    print(f"\nBlinded annotation package written to: {output_dir}/")
    print(f"  annotation_items.json  ({len(blinded_items)} items)")
    print(f"  annotation_form.json   (blank template)")
    print(f"  README.md              (annotator instructions)")
    print("\nBlinding verification: no ground_truth_label, confidence_score, or")
    print("system prediction fields appear in the exported items.")


if __name__ == "__main__":
    main()
