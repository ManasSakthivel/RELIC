#!/usr/bin/env python3
"""
JCL-SemBench Validator.

Validates the integrity and oracle results of benchmarks/sembench:
1. Verifies SHA-256 manifest against case files on disk.
2. Re-runs jcl_oracle.judge.compare_versions across all cases in cases.jsonl.
3. Asserts consistency between JSONL records and runtime oracle evaluations.
4. Prints a summary table of benchmark metrics and validation statuses.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

from jcl_oracle.judge import compare_versions
from relic_eval.subjects import get_subjects

SEMBENCH_DIR = ROOT_DIR / "benchmarks" / "sembench"
MANIFEST_FILE = SEMBENCH_DIR / "MANIFEST.sha256"
CASES_JSONL = SEMBENCH_DIR / "cases.jsonl"


def check_manifest() -> tuple[int, int]:
    if not MANIFEST_FILE.is_file():
        raise FileNotFoundError(f"Missing manifest file: {MANIFEST_FILE}")

    passed = 0
    failed = 0
    for line in MANIFEST_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        expected_sha, rel_path = line.split(maxsplit=1)
        file_path = SEMBENCH_DIR / rel_path
        if not file_path.is_file():
            print(f"[ERROR] Missing file: {file_path}")
            failed += 1
            continue
        actual_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_sha != expected_sha:
            print(f"[ERROR] Checksum mismatch for {rel_path}: expected {expected_sha}, got {actual_sha}")
            failed += 1
        else:
            passed += 1
    return passed, failed


def validate_cases() -> bool:
    print(f"=== Validating JCL-SemBench ({CASES_JSONL}) ===")
    
    # 1. Manifest verification
    m_pass, m_fail = check_manifest()
    print(f"[Manifest Check] Passed: {m_pass}, Failed: {m_fail}")
    if m_fail > 0:
        print("[FAIL] Manifest checksums failed.")
        return False

    # 2. Case execution check
    if not CASES_JSONL.is_file():
        print(f"[ERROR] Missing {CASES_JSONL}")
        return False

    subjects = {s.key: s for s in get_subjects()}
    records = []
    with open(CASES_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    total = len(records)
    preserving = sum(1 for r in records if r["expected_outcome"] == "PRESERVING")
    changing = sum(1 for r in records if r["expected_outcome"] == "CHANGING")
    
    status_counts: dict[str, int] = {}
    mismatches = 0
    
    for r in records:
        cid = r["id"]
        case_dir = SEMBENCH_DIR / "cases" / cid
        orig_text = (case_dir / "original.jcl").read_text(encoding="utf-8")
        trans_text = (case_dir / "transformed.jcl").read_text(encoding="utf-8")
        
        proclib = None
        cobol_sources = None
        if r["source"].startswith("corpus:"):
            for skey, sub in subjects.items():
                if skey in r["source"]:
                    proclib = sub.proclib
                    cobol_sources = sub.cobol_sources
                    break

        verdict = compare_versions(
            orig_text,
            trans_text,
            proclib=proclib,
            cobol_sources=cobol_sources,
            scenario_set="full",
        )
        
        # Verify recorded verdict matches re-run
        if verdict.label != r["oracle_verdict"]["label"]:
            print(f"[FAIL] Oracle verdict drift for {cid}: recorded {r['oracle_verdict']['label']}, live {verdict.label}")
            mismatches += 1
            
        status = r["validation_status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    print("\n--- Summary ---")
    print(f"Total Pairs: {total}")
    print(f"  - Preserving: {preserving}")
    print(f"  - Changing:   {changing}")
    print("Validation Statuses:")
    for st, count in sorted(status_counts.items()):
        print(f"  - {st:<36}: {count}")

    if mismatches > 0:
        print(f"\n[FAIL] Found {mismatches} oracle result drift mismatches.")
        return False

    print("\n[SUCCESS] JCL-SemBench verification passed completely.")
    return True


if __name__ == "__main__":
    success = validate_cases()
    sys.exit(0 if success else 1)
