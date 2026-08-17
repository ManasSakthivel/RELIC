#!/usr/bin/env python3.11
"""
Build Level-2 DETERMINISTIC ground truth from available JCL artifacts.

Execution path:
  1. Attempt to find real JCL files under datasets/
  2. If none found, create and parse 3 hand-crafted synthetic test cases
     (CardDemo-like batch sequences).
  3. For every extracted contract (positive), generate at least one
     structural negative example (non-relationship pair from the same JCL).
  4. Write benchmark/ground_truth/level2_deterministic.json
  5. Write results/ground_truth_manifest.json

SCIENTIFIC RULES:
  - No contract labels are fabricated; all positives come from deterministic
    structural extraction (TEMPORAL ordering, RESOURCE produce/consume pairs,
    CONTROL_FLOW COND parameters).
  - Negatives are structural non-relationships, not behaviourally validated.
  - Level-1, Level-3, Level-4 items are NOT generated here; they are marked
    PENDING_EXECUTION and PENDING_ANNOTATION respectively in the manifest.
"""

from __future__ import annotations

import json
import sys
import pathlib
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.static_analysis.extractor import StaticContractExtractor
from legacy_contract.ir.model import EntityType, RelationType

# ---------------------------------------------------------------------------
# Synthetic JCL content (Step 3 fallback — CardDemo-like batch sequences)
# Each string is a complete, minimal, syntactically valid JCL job.
# ---------------------------------------------------------------------------

SYNTHETIC_JCL: dict[str, str] = {
    "ACCTFIL1": """\
//ACCTFIL1 JOB (ACCT),'ACCOUNT FILE PROC',CLASS=A,MSGCLASS=X
//STEP010  EXEC PGM=SORTPGM
//SORTIN   DD DSN=ACCT.MASTER.INPUT,DISP=SHR
//SORTOUT  DD DSN=ACCT.SORTED.WORK,DISP=(NEW,CATLG,DELETE)
//STEP020  EXEC PGM=CBACT01C
//INFILE   DD DSN=ACCT.SORTED.WORK,DISP=OLD
//OUTFILE  DD DSN=ACCT.PROCESSED.OUTPUT,DISP=(NEW,CATLG,DELETE)
//STEP030  EXEC PGM=CBACT04C
//INPUT    DD DSN=ACCT.PROCESSED.OUTPUT,DISP=OLD
//REPORT   DD DSN=ACCT.FINAL.REPORT,DISP=(NEW,CATLG,DELETE)
""",
    "CBTRN01": """\
//CBTRN01  JOB (ACCT),'CARD TRANS BATCH',CLASS=A,MSGCLASS=X
//STEP010  EXEC PGM=CBTRN01C
//TRANSIN  DD DSN=CARD.TRANS.INPUT,DISP=SHR
//TRANSOUT DD DSN=CARD.TRANS.WORK,DISP=(NEW,CATLG,DELETE)
//STEP020  EXEC PGM=CBTRN02C,COND=(4,GT,STEP010)
//TRANSIN  DD DSN=CARD.TRANS.WORK,DISP=OLD
//REPORT   DD DSN=CARD.TRANS.REPORT,DISP=(NEW,CATLG,DELETE)
""",
    "RPTGEN1": """\
//RPTGEN1  JOB (ACCT),'REPORT GENERATION',CLASS=A,MSGCLASS=X
//STEP010  EXEC PGM=DATEXTRC
//EXTRACT  DD DSN=RPT.EXTRACT.FILE,DISP=(NEW,CATLG,DELETE)
//SRCDATA  DD DSN=ACCT.MASTER.INPUT,DISP=SHR
//STEP020  EXEC PGM=RPTFMT01
//INDATA   DD DSN=RPT.EXTRACT.FILE,DISP=OLD
//OUTRPT   DD DSN=RPT.FORMATTED.OUTPUT,DISP=(NEW,CATLG,DELETE)
""",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialise_contract(c: Any, source_path: str, source_label: str) -> dict:
    """Convert a Contract object to a ground-truth item dict (positive label)."""
    provenance_loc = ""
    if c.provenance and c.provenance.source_location:
        provenance_loc = c.provenance.source_location
    return {
        "contract_id": c.contract_id,
        "contract_type": c.contract_type.value,
        "subject_id": c.subject_id,
        "predicate": c.predicate.value,
        "object_id": c.object_id,
        "natural_language": c.natural_language,
        "ground_truth_label": True,
        "ground_truth_level": "DETERMINISTIC",
        "source": source_path,
        "source_label": source_label,
        "evidence": provenance_loc,
        "annotator": "deterministic_extractor",
        "adjudication_status": "NOT_REQUIRED",
        "note": (
            "Synthetic benchmark for pipeline validation only — "
            "not for headline RQ metrics"
        ) if source_label == "hand_crafted_test_case" else "",
    }


def _make_negatives(
    contracts: list[dict],
    ir: Any,
    source_path: str,
    source_label: str,
) -> list[dict]:
    """
    Construct structural negative examples for a given IR graph.

    Strategy (in order of preference):
      1. For every TEMPORAL positive (A PRECEDES B), add a negative for
         (B PRECEDES A) — the reverse direction does NOT hold.
      2. For every RESOURCE positive (A PRODUCES_BEFORE_CONSUMES B),
         add a negative for (B PRODUCES_BEFORE_CONSUMES A).
      3. Add a self-relationship negative: (A PRECEDES A) is never true.
    """
    import uuid

    negatives: list[dict] = []

    # Collect step entities from IR
    steps = [
        e for e in ir.entities.values()
        if e.entity_type == EntityType.STEP
    ]

    for c in contracts:
        if c["contract_type"] == "TEMPORAL":
            # Reverse direction: B PRECEDES A is NOT a fact (A came first in JCL)
            negatives.append({
                "contract_id": str(uuid.uuid4()),
                "contract_type": "TEMPORAL",
                "subject_id": c["object_id"],
                "predicate": "PRECEDES",
                "object_id": c["subject_id"],
                "natural_language": (
                    "Negative example: reverse temporal order does not hold "
                    f"(pair derived from positive {c['contract_id']})."
                ),
                "ground_truth_label": False,
                "ground_truth_level": "DETERMINISTIC",
                "source": source_path,
                "source_label": source_label,
                "evidence": "structural_non_relationship:reverse_ordering",
                "annotator": "deterministic_extractor",
                "adjudication_status": "NOT_REQUIRED",
                "note": (
                    "Synthetic benchmark for pipeline validation only — "
                    "not for headline RQ metrics"
                ) if source_label == "hand_crafted_test_case" else "",
            })

        elif c["contract_type"] == "RESOURCE":
            # Reverse direction: consumer PRODUCES_BEFORE_CONSUMES producer is false
            negatives.append({
                "contract_id": str(uuid.uuid4()),
                "contract_type": "RESOURCE",
                "subject_id": c["object_id"],
                "predicate": "PRODUCES_BEFORE_CONSUMES",
                "object_id": c["subject_id"],
                "natural_language": (
                    "Negative example: consumer step does not produce for the "
                    f"producer step (pair derived from positive {c['contract_id']})."
                ),
                "ground_truth_label": False,
                "ground_truth_level": "DETERMINISTIC",
                "source": source_path,
                "source_label": source_label,
                "evidence": "structural_non_relationship:reverse_resource_flow",
                "annotator": "deterministic_extractor",
                "adjudication_status": "NOT_REQUIRED",
                "note": (
                    "Synthetic benchmark for pipeline validation only — "
                    "not for headline RQ metrics"
                ) if source_label == "hand_crafted_test_case" else "",
            })

    # Self-PRECEDES negative: for each step, (step PRECEDES step) is never true
    for step in steps:
        negatives.append({
            "contract_id": str(uuid.uuid4()),
            "contract_type": "TEMPORAL",
            "subject_id": step.entity_id,
            "predicate": "PRECEDES",
            "object_id": step.entity_id,
            "natural_language": (
                f"Negative example: step {step.name} does not precede itself."
            ),
            "ground_truth_label": False,
            "ground_truth_level": "DETERMINISTIC",
            "source": source_path,
            "source_label": source_label,
            "evidence": "structural_non_relationship:self_precedence_impossible",
            "annotator": "deterministic_extractor",
            "adjudication_status": "NOT_REQUIRED",
            "note": (
                "Synthetic benchmark for pipeline validation only — "
                "not for headline RQ metrics"
            ) if source_label == "hand_crafted_test_case" else "",
        })

    return negatives


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    datasets_dir = ROOT / "datasets"
    output_file = ROOT / "benchmark" / "ground_truth" / "level2_deterministic.json"
    manifest_file = ROOT / "results" / "ground_truth_manifest.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.parent.mkdir(parents=True, exist_ok=True)

    # Step 1 — discover real JCL files
    real_jcl = (
        list(datasets_dir.rglob("*.jcl"))
        + list(datasets_dir.rglob("*.JCL"))
    )
    print(f"Found {len(real_jcl)} real JCL files in datasets/")

    parser = JCLParser()
    extractor = StaticContractExtractor()

    ground_truth: list[dict] = []
    files_processed: list[str] = []
    source_label = "real_jcl" if real_jcl else "hand_crafted_test_case"

    # Step 2 / Step 3 — parse whichever source we have
    if real_jcl:
        jobs_to_parse = [(str(p), p.read_text(errors="replace").splitlines()) for p in real_jcl]
        print("Using real JCL files.")
    else:
        print("No real JCL found — using 3 hand-crafted synthetic test cases.")
        jobs_to_parse = [(name, content.splitlines()) for name, content in SYNTHETIC_JCL.items()]

    for source_path, lines in jobs_to_parse:
        try:
            _, ir = parser.parse_lines(lines, source_path)
            extraction = extractor.extract(ir)
            contracts_raw = extraction.all_contracts

            positives = [
                _serialise_contract(c, source_path, source_label)
                for c in contracts_raw
            ]
            negatives = _make_negatives(positives, ir, source_path, source_label)

            ground_truth.extend(positives)
            ground_truth.extend(negatives)
            files_processed.append(source_path)
            print(
                f"  {source_path}: "
                f"{len(positives)} positives, {len(negatives)} negatives "
                f"(temporal={len(extraction.temporal_contracts)}, "
                f"resource={len(extraction.resource_contracts)}, "
                f"control_flow={len(extraction.control_flow_contracts)})"
            )
        except Exception as exc:
            print(f"  ERROR {source_path}: {exc}")
            raise

    # Step 5 counts
    positives_all = [i for i in ground_truth if i["ground_truth_label"] is True]
    negatives_all = [i for i in ground_truth if i["ground_truth_label"] is False]

    def _by_type(items: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = {"TEMPORAL": 0, "RESOURCE": 0, "CONTROL_FLOW": 0}
        for item in items:
            ct = item.get("contract_type", "")
            if ct in counts:
                counts[ct] += 1
        return counts

    pos_by_type = _by_type(positives_all)
    neg_by_type = _by_type(negatives_all)

    # Write level2_deterministic.json
    level2_payload = {
        "ground_truth_level": "DETERMINISTIC",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_version": "v1.0-level2-deterministic",
        "source_type": source_label,
        "total": len(ground_truth),
        "positive_items": len(positives_all),
        "negative_items": len(negatives_all),
        "items": ground_truth,
    }
    with open(output_file, "w") as f:
        json.dump(level2_payload, f, indent=2)
    print(f"\nWrote {len(ground_truth)} ground-truth items → {output_file}")

    # Step 5 — manifest
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_version": "v1.0-level2-deterministic",
        "locked": False,
        "total_items": len(ground_truth),
        "positive_items": len(positives_all),
        "negative_items": len(negatives_all),
        "by_contract_type": {
            "TEMPORAL": {"positive": pos_by_type["TEMPORAL"], "negative": neg_by_type["TEMPORAL"]},
            "RESOURCE": {"positive": pos_by_type["RESOURCE"], "negative": neg_by_type["RESOURCE"]},
            "CONTROL_FLOW": {"positive": pos_by_type["CONTROL_FLOW"], "negative": neg_by_type["CONTROL_FLOW"]},
        },
        "ground_truth_levels_used": ["DETERMINISTIC"],
        "human_annotation_status": "NOT_ATTEMPTED",
        "inter_annotator_agreement": None,
        "level1_execution_oracle_status": "PENDING_EXECUTION",
        "level3_expert_annotation_status": "PENDING_ANNOTATION",
        "level4_adjudication_status": "PENDING_ANNOTATION",
        "files": {
            "level2_deterministic": "benchmark/ground_truth/level2_deterministic.json",
        },
        "sources": files_processed,
        "source_type": source_label,
        "jcl_files_processed": len(files_processed),
        "limitations": [
            "Level-2 DETERMINISTIC only — no human annotation yet.",
            "Negative examples are structural non-relationships, not behaviourally validated.",
            "If dataset download failed, items come from synthetic test cases only.",
            (
                "Synthetic JCL cases represent CardDemo-like batch patterns "
                "and are labelled hand_crafted_test_case — exclude from headline RQ metrics."
            ) if source_label == "hand_crafted_test_case" else
            "Dataset is real JCL; apply headline RQ metrics with care pending Level-3 annotation.",
        ],
    }
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote manifest → {manifest_file}")

    # Summary
    print(f"\n{'='*60}")
    print("GROUND TRUTH BUILD COMPLETE")
    print(f"{'='*60}")
    print(f"Source type          : {source_label}")
    print(f"JCL files processed  : {len(files_processed)}")
    print(f"Total GT items       : {len(ground_truth)}")
    print(f"  Positives          : {len(positives_all)}")
    print(f"  Negatives          : {len(negatives_all)}")
    print(f"By type (positives)  : {pos_by_type}")
    print(f"By type (negatives)  : {neg_by_type}")
    print(f"Level-1 (oracle)     : PENDING_EXECUTION — requires GnuCOBOL traces")
    print(f"Level-3 (expert)     : PENDING_ANNOTATION — requires human annotators")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
