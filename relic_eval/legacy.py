"""
Accounting of the legacy (pre-remediation) BCG-level mutation benchmark.

Reads the preserved raw output of ``scripts/run_rq2.py`` (results/rq2/rq2.csv,
440 rows = 55 JCL files x 8 operators) and classifies every row, so that the
"104 evaluated / 336 N/A" figures of earlier versions are fully explained.
Nothing in results/rq2/ is modified.

For every N/A row caused by a missing operator target it also re-checks the
file with the IBM-conformant parser (RELIC v1.1) to quantify how many
"not applicable" decisions were caused by the continuation-line defect.

Output: results/legacy/legacy_mutation_accounting.csv
        results/legacy/legacy_accounting_summary.json
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from loguru import logger

from legacy_contract.contracts.model import ContractType
from legacy_contract.ir.model import RelationType
from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.static_analysis.extractor import StaticContractExtractor
from relic_eval.subjects import ROOT, SUBJECTS

logger.remove()

LEGACY_CSV = ROOT / "results" / "rq2" / "rq2.csv"
LEGACY_NEG = ROOT / "results" / "rq2" / "negative_summary.json"
OUT_DIR = ROOT / "results" / "legacy"

LEGACY_TO_SOURCE_OPERATOR = {
    "REORDER_JOBS": "SWAP_ADJACENT_STEPS",
    "ALTER_STEP_SEQUENCE": "SWAP_ADJACENT_STEPS",
    "REMOVE_JOB_DEPENDENCY": "SPLIT_JOB",
    "REMOVE_DATASET_INIT": "DELETE_PRODUCER_STEP",
    "CHANGE_DATASET_NAME": "RENAME_OUTPUT_DATASET",
    "ALTER_FILE_DEPENDENCY_ORDER": "MOVE_CONSUMER_BEFORE_PRODUCER",
    "SUPPRESS_RETURN_CODE_CHECK": "REMOVE_COND",
    "ALTER_ERROR_BRANCH": "ALTER_COND_THRESHOLD",
}
LEGACY_CONTRACT_TYPE = {
    "REORDER_JOBS": "TEMPORAL", "ALTER_STEP_SEQUENCE": "TEMPORAL",
    "REMOVE_JOB_DEPENDENCY": "TEMPORAL", "REMOVE_DATASET_INIT": "RESOURCE",
    "CHANGE_DATASET_NAME": "RESOURCE", "ALTER_FILE_DEPENDENCY_ORDER": "RESOURCE",
    "SUPPRESS_RETURN_CODE_CHECK": "CONTROL_FLOW", "ALTER_ERROR_BRANCH": "CONTROL_FLOW",
}


def _has_target_v11(path: Path, operator: str) -> bool:
    """Would the operator have a target in this file under the IBM-conformant parser?"""
    _r, ir = JCLParser(legacy_v1_0=False).parse_lines(
        path.read_text(errors="replace").splitlines(), str(path))
    res = StaticContractExtractor(legacy_v1_0=False).extract(ir)
    rels = {r.relation_type for r in ir.relations}
    ctypes = {c.contract_type for c in res.all_contracts}
    if operator in {"REORDER_JOBS", "REMOVE_JOB_DEPENDENCY", "ALTER_STEP_SEQUENCE"}:
        return RelationType.MUST_PRECEDE in rels and ContractType.TEMPORAL in ctypes
    if operator in {"REMOVE_DATASET_INIT", "CHANGE_DATASET_NAME", "ALTER_FILE_DEPENDENCY_ORDER"}:
        return ContractType.RESOURCE in ctypes
    return ContractType.CONTROL_FLOW in ctypes


def main() -> None:
    files = {p.name: p for p in SUBJECTS["carddemo"].root.rglob("*") if p.suffix.lower() == ".jcl"}
    rows_out = []
    with open(LEGACY_CSV) as fh:
        for r in csv.DictReader(fh):
            op = r["operator"]
            status_legacy = r["status"]
            err = r["error"]
            if status_legacy == "EVALUATED":
                status = "OTHER"
                reason = ("CIRCULAR_HARNESS: contract deleted/edited directly in RELIC's own BCG; "
                          "detection guaranteed by construction; no independent label")
            elif err == "zero_valid_contracts":
                status = "OTHER"
                reason = ("NO_SITE: file has no RELIC v1.0 contracts (single-step job, or duplicate "
                          "step names collapsed into one entity)")
            elif err == "mutation_no_contract_effect":
                status = "OTHER"
                reason = ("POST_HOC_EXCLUSION: operator targeted a reflexive ordering relation "
                          "(two steps named STEP05R) that has no contract; row was dropped after "
                          "RELIC's own diff showed no effect")
            else:
                status = "OTHER"
                reason = "NO_SITE: operator target (MUST_PRECEDE / PRODUCES / COND contract) absent in v1.0 IR"
                p = files.get(r["file"])
                if p is not None and _has_target_v11(p, op):
                    reason += "; target EXISTS under the IBM-conformant parser (continuation defect)"
            rows_out.append({
                "mutation_id": f"legacy/{r['file']}/{op}",
                "mutation_type": op,
                "contract_type": LEGACY_CONTRACT_TYPE[op],
                "subject_system": "carddemo",
                "legacy_status": status_legacy,
                "status": status,
                "status_reason": reason,
                "expected_violation": "TRUE",
                "relic_result": "FLAGGED" if r["tp_static_bcg"] == "1" else ("NOT_FLAGGED" if status_legacy == "EVALUATED" else ""),
                "oracle_result": "NONE (legacy harness had no oracle)",
                "evaluable_for_metrics": "FALSE",
                "repaired_as": LEGACY_TO_SOURCE_OPERATOR[op],
            })
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "legacy_mutation_accounting.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)

    by_reason = Counter(r["status_reason"].split(":")[0] + (
        " (continuation defect)" if "continuation defect" in r["status_reason"] else "")
        for r in rows_out)
    neg = json.loads(LEGACY_NEG.read_text())
    summary = {
        "positive_benchmark": {
            "total_rows": len(rows_out),
            "legacy_evaluated": sum(1 for r in rows_out if r["legacy_status"] == "EVALUATED"),
            "legacy_not_applicable": sum(1 for r in rows_out if r["legacy_status"] == "NOT_APPLICABLE"),
            "legacy_errors": sum(1 for r in rows_out if r["legacy_status"] not in {"EVALUATED", "NOT_APPLICABLE"}),
            "by_reason": dict(sorted(by_reason.items())),
            "legacy_evaluated_by_contract_type": dict(Counter(
                r["contract_type"] for r in rows_out if r["legacy_status"] == "EVALUATED")),
            "methodologically_valid_rows": 0,
        },
        "negative_benchmark": {
            "attempted": neg["n_attempted"],
            "not_applicable": neg["n_not_applicable"],
            "evaluated_tn": neg["tn"],
            "note": ("All five legacy negative operators edit RELIC's BCG without touching any "
                     "contract (one is a no-op the graph de-duplicates); TN is guaranteed. Only the "
                     "144 TN rows were saved by the legacy script; N/A rows exist only as a count."),
        },
        "operator_mapping": LEGACY_TO_SOURCE_OPERATOR,
    }
    with open(OUT_DIR / "legacy_accounting_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
