"""
Parser Coverage Metrics — CardDemo Dataset.

Measures how many JCL and COBOL files in the CardDemo dataset parse
successfully and which constructs are recognised.

Usage:
    python scripts/measure_parser_coverage.py

Output:
    results/parser_coverage.json
    reports/parser_coverage_summary.md
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

try:
    from legacy_contract.parsers.jcl_parser import JCLParser
    from legacy_contract.parsers.cobol_parser import COBOLParser
except ImportError as e:
    print(f"[ERROR] Cannot import parsers: {e}")
    print("Ensure the package is installed: pip install -e .")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main measurement
# ---------------------------------------------------------------------------

def measure(dataset_root: Path) -> dict:
    """Walk dataset_root and collect parser coverage stats."""

    jcl_attempted = 0
    jcl_succeeded = 0
    jcl_construct_counts: dict[str, int] = {
        "JOB": 0, "EXEC": 0, "DD": 0, "PROC": 0, "PEND": 0,
        "IF": 0, "ENDIF": 0, "SET": 0, "INCLUDE": 0,
    }
    jcl_errors: list[dict] = []

    cobol_attempted = 0
    cobol_succeeded = 0
    cobol_division_counts: dict[str, int] = {
        "IDENTIFICATION": 0, "ENVIRONMENT": 0, "DATA": 0, "PROCEDURE": 0
    }
    cobol_errors: list[dict] = []

    jcl_parser = JCLParser()
    cobol_parser = COBOLParser()

    for path in sorted(dataset_root.rglob("*")):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        name_lower = path.name.lower()

        # Classify by extension / name
        is_jcl = suffix in {".jcl", ".jclproc"} or name_lower.endswith(".jcl")
        is_cobol = suffix in {".cbl", ".cob", ".cobol"} or name_lower.endswith((".cbl", ".cob"))

        if is_jcl:
            jcl_attempted += 1
            try:
                result, ir = jcl_parser.parse_file(str(path))
                jcl_succeeded += 1
                # Count constructs by token type
                for tok in result.tokens:
                    tok_type = getattr(tok, "token_type", None)
                    if tok_type is not None:
                        name = str(tok_type).split(".")[-1]  # strip enum prefix
                        if name in jcl_construct_counts:
                            jcl_construct_counts[name] += 1
                # Count entities by type as fallback when tokens are unavailable
                if not result.tokens:
                    for entity in ir.entities.values():
                        etype = entity.entity_type.value
                        if etype in jcl_construct_counts:
                            jcl_construct_counts[etype] += 1
            except Exception as e:
                jcl_errors.append({"file": str(path.relative_to(dataset_root)), "error": str(e)[:120]})

        elif is_cobol:
            cobol_attempted += 1
            try:
                result, ir = cobol_parser.parse_file(str(path))
                cobol_succeeded += 1
                for div in result.divisions_found:
                    div_upper = div.upper()
                    for key in cobol_division_counts:
                        if key in div_upper:
                            cobol_division_counts[key] += 1
            except Exception as e:
                cobol_errors.append({"file": str(path.relative_to(dataset_root)), "error": str(e)[:120]})

    jcl_rate = round(jcl_succeeded / jcl_attempted, 4) if jcl_attempted > 0 else None
    cobol_rate = round(cobol_succeeded / cobol_attempted, 4) if cobol_attempted > 0 else None

    return {
        "jcl": {
            "files_attempted": jcl_attempted,
            "files_parsed_successfully": jcl_succeeded,
            "parse_success_rate": jcl_rate,
            "construct_counts": jcl_construct_counts,
            "files_with_errors": jcl_errors[:20],  # cap at 20 for readability
        },
        "cobol": {
            "files_attempted": cobol_attempted,
            "files_parsed_successfully": cobol_succeeded,
            "parse_success_rate": cobol_rate,
            "division_counts": cobol_division_counts,
            "files_with_errors": cobol_errors[:20],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset": "carddemo",
        "note": (
            "Parser coverage metrics for CardDemo JCL and COBOL artifacts. "
            "Files with parse errors are logged but do not indicate incorrect extraction: "
            "partial parsing still produces valid IR entities for recognised constructs."
        ),
    }


def write_markdown_summary(data: dict, out_path: Path) -> None:
    jcl = data["jcl"]
    cob = data["cobol"]

    def fmt(v):
        if v is None:
            return "N/A"
        if isinstance(v, float):
            return f"{v:.1%}"
        return str(v)

    lines = [
        "# Parser Coverage Summary — CardDemo Dataset",
        "",
        f"**Generated:** {data['timestamp']}  ",
        f"**Dataset:** {data['dataset']}  ",
        "",
        "## Summary",
        "",
        "| Metric | JCL | COBOL |",
        "|--------|-----|-------|",
        f"| Files attempted | {jcl['files_attempted']} | {cob['files_attempted']} |",
        f"| Files parsed successfully | {jcl['files_parsed_successfully']} | {cob['files_parsed_successfully']} |",
        f"| Parse success rate | {fmt(jcl['parse_success_rate'])} | {fmt(cob['parse_success_rate'])} |",
        "",
        "## JCL Construct Counts",
        "",
        "| Construct | Count |",
        "|-----------|-------|",
    ]
    for k, v in jcl["construct_counts"].items():
        lines.append(f"| {k} | {v} |")

    lines += [
        "",
        "## COBOL Division Counts",
        "",
        "| Division | Count |",
        "|----------|-------|",
    ]
    for k, v in cob["division_counts"].items():
        lines.append(f"| {k} | {v} |")

    lines += [
        "",
        "## Notes",
        "",
        data["note"],
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written: {out_path}")


def main() -> None:
    dataset_root = REPO_ROOT / "datasets" / "carddemo" / "extracted"
    if not dataset_root.exists():
        # Try zip-extracted subdirectory
        candidates = list((REPO_ROOT / "datasets" / "carddemo").glob("*/app"))
        if candidates:
            dataset_root = candidates[0].parent
        else:
            print(f"[WARN] Dataset not found at {dataset_root}")
            result = {
                "status": "DATASET_UNAVAILABLE",
                "searched": str(dataset_root),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            out = REPO_ROOT / "results" / "parser_coverage.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, indent=2))
            print(f"Written: {out}")
            return

    print(f"Scanning: {dataset_root}")
    data = measure(dataset_root)

    out_json = REPO_ROOT / "results" / "parser_coverage.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(data, indent=2))
    print(f"Written: {out_json}")

    out_md = REPO_ROOT / "reports" / "parser_coverage_summary.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    write_markdown_summary(data, out_md)


if __name__ == "__main__":
    main()
