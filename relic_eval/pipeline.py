"""
Authoritative evaluation pipeline.

    python -m relic_eval.pipeline [--subjects carddemo,omp_course,genapp]

Stages
  1. generate source-level mutants for every JCL job file of every subject
  2. label every mutant with the independent oracle (full + no-abend scenarios)
  3. run every detector blind on (original, mutant)
  4. assign each mutant exactly one accounting status
  5. write raw records, the evaluation manifest and metrics

Outputs (all deterministic — no timestamps or random IDs inside):
  results/final/raw/evaluation_records.jsonl   one record per candidate mutant
  results/final/evaluation_manifest.csv        one row per candidate mutant
  results/final/metrics.json                   every reported number
  results/final/run_info.json                  environment + timestamp of the run

Accounting statuses (exactly one per candidate mutant):
  EVALUABLE               in scope, valid, oracle says DIFFERENT or EQUIVALENT
  OUT_OF_SCOPE            targets behaviour outside RELIC's declared scope
  INVALID_MUTATION        operator could not produce valid JCL at this site
  INFRASTRUCTURE_FAILURE  oracle or generator crashed
  OTHER                   ORACLE_UNDETERMINED or DUPLICATE (reason recorded)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from jcl_oracle.judge import compare_versions
from relic_eval.detectors import ComplexityDetector, all_detectors
from relic_eval.mutate import (
    ALL_OPERATORS,
    NEGATIVE_OPERATORS,
    OPERATOR_CATEGORY,
    OPERATOR_CONTRACT_TYPE,
    generate,
)
from relic_eval.subjects import ROOT, get_subjects

OUT = ROOT / "results" / "final"
RAW = OUT / "raw"

STATUSES = ["EVALUABLE", "OUT_OF_SCOPE", "INVALID_MUTATION", "INFRASTRUCTURE_FAILURE", "OTHER"]
PRIMARY_DETECTOR = "relic_v1_0"

MANIFEST_COLUMNS = [
    "mutation_id", "subject_system", "file", "mutation_type", "failure_category",
    "contract_type", "site", "status", "status_reason", "expected_violation",
    "oracle_result", "oracle_result_no_abend", "ground_truth", "relic_result",
    "relic_v1_1_result", "evaluable_for_metrics",
]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def run_benchmark(subject_keys: list[str] | None = None, verbose: bool = True) -> list[dict]:
    detectors = all_detectors()
    complexity = next(d for d in detectors if isinstance(d, ComplexityDetector))
    records: list[dict] = []
    for subject in get_subjects(subject_keys):
        corpus = {subject.artifact_path(f): f.read_text(errors="replace") for f in subject.jcl_files}
        complexity.set_corpus(subject.key, corpus)
        if verbose:
            print(f"[{subject.key}] {len(subject.jcl_files)} JCL job files", flush=True)
        for f in subject.jcl_files:
            original = f.read_text(errors="replace")
            rel = subject.rel(f)
            ap = subject.artifact_path(f)
            try:
                mutants = generate(original)
            except Exception as exc:  # generator crash: one record for the file
                records.append({
                    "mutation_id": f"{subject.key}/{rel}/GENERATOR/0",
                    "subject_system": subject.key, "file": rel, "artifact_path": ap,
                    "mutation_type": "GENERATOR", "failure_category": "", "contract_type": "",
                    "site": "", "expected_violation": None, "status": "INFRASTRUCTURE_FAILURE",
                    "status_reason": f"generator crashed: {exc!r}"[:300],
                    "oracle_result": None, "oracle_result_no_abend": None, "ground_truth": None,
                    "evaluable_for_metrics": False, "predictions": {}, "prediction_details": {},
                })
                continue
            per_op_index: dict[str, int] = {}
            seen: dict[str, str] = {}
            for mu in mutants:
                idx = per_op_index.get(mu.operator, 0)
                per_op_index[mu.operator] = idx + 1
                mid = f"{subject.key}/{rel}/{mu.operator}/{idx}"
                rec: dict = {
                    "mutation_id": mid,
                    "subject_system": subject.key,
                    "file": rel,
                    "artifact_path": ap,
                    "mutation_type": mu.operator,
                    "failure_category": OPERATOR_CATEGORY[mu.operator],
                    "contract_type": OPERATOR_CONTRACT_TYPE[mu.operator],
                    "site": mu.site,
                    "expected_violation": mu.expected_violation,
                    "scope": "OUT_OF_SCOPE" if mu.scope_note else "IN_SCOPE",
                    "scope_reason": mu.scope_note,
                    "diff": mu.diff(original, rel),
                    "mutant_sha256": _sha(mu.text) if mu.text is not None else None,
                    "oracle_result": None,
                    "oracle_result_no_abend": None,
                    "oracle": None,
                    "ground_truth": None,
                    "predictions": {},
                    "prediction_details": {},
                }
                status, reason = None, ""
                if mu.text is None:
                    status, reason = "INVALID_MUTATION", mu.invalid_reason
                elif mu.text in seen:
                    status, reason = "OTHER", f"DUPLICATE of {seen[mu.text]} (identical mutant text)"
                if mu.text is not None and mu.text not in seen:
                    seen[mu.text] = mid
                if status is None:
                    try:
                        v = compare_versions(original, mu.text, subject.proclib, subject.cobol_sources)
                        v2 = compare_versions(original, mu.text, subject.proclib, subject.cobol_sources,
                                              scenario_set="no_abend")
                        rec["oracle"] = v.to_dict()
                        rec["oracle_result"] = v.label
                        rec["oracle_result_no_abend"] = v2.label
                    except Exception:
                        status = "INFRASTRUCTURE_FAILURE"
                        reason = "oracle crashed: " + traceback.format_exc(limit=2)[-300:]
                if status is None:
                    for d in detectors:
                        if isinstance(d, ComplexityDetector):
                            p = d.predict(original, mu.text, ap, subject.key)
                        else:
                            p = d.predict(original, mu.text, ap)
                        rec["predictions"][d.name] = p.flagged
                        rec["prediction_details"][d.name] = {"status": p.status, **p.detail}
                    label = rec["oracle_result"]
                    if label == "INVALID":
                        status = "INVALID_MUTATION"
                        reason = "mutant is not well-formed JCL: " + "; ".join(rec["oracle"]["model_errors"])
                    elif mu.scope_note:
                        status, reason = "OUT_OF_SCOPE", mu.scope_note
                    elif label == "UNDETERMINED":
                        status = "OTHER"
                        reason = ("ORACLE_UNDETERMINED: no modelled observable differs, but opaque "
                                  "step(s) changed context: " + ", ".join(rec["oracle"]["opaque_touched"]))
                    else:
                        status = "EVALUABLE"
                        reason = f"oracle={label}"
                if rec["oracle_result"] in ("DIFFERENT", "EQUIVALENT"):
                    rec["ground_truth"] = rec["oracle_result"] == "DIFFERENT"
                rec["status"] = status
                rec["status_reason"] = reason
                rec["evaluable_for_metrics"] = status == "EVALUABLE"
                records.append(rec)
        if verbose:
            n = sum(1 for r in records if r["subject_system"] == subject.key)
            print(f"[{subject.key}] {n} candidate mutants", flush=True)
    records.sort(key=lambda r: r["mutation_id"])
    return records


def write_records(records: list[dict]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with open(RAW / "evaluation_records.jsonl", "w") as fh:
        for r in records:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    with open(OUT / "evaluation_manifest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in records:
            row = dict(r)
            row["relic_result"] = _fmt_pred(r["predictions"].get("relic_v1_0"))
            row["relic_v1_1_result"] = _fmt_pred(r["predictions"].get("relic_v1_1"))
            row["ground_truth"] = "" if r["ground_truth"] is None else ("VIOLATION" if r["ground_truth"] else "NO_VIOLATION")
            row["expected_violation"] = "" if r["expected_violation"] is None else str(r["expected_violation"]).upper()
            w.writerow(row)


def _fmt_pred(p) -> str:
    if p is None:
        return "NO_PREDICTION"
    return "FLAGGED" if p else "NOT_FLAGGED"


def load_records() -> list[dict]:
    with open(RAW / "evaluation_records.jsonl") as fh:
        return [json.loads(line) for line in fh]


def write_run_info(extra: dict | None = None) -> None:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                text=True, check=False).stdout.strip() or None
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                                    text=True, check=False).stdout.strip())
    except OSError:
        commit, dirty = None, None
    info = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_commit": commit,
        "git_dirty": dirty,
        "operators": ALL_OPERATORS,
        "negative_operators": NEGATIVE_OPERATORS,
    }
    info.update(extra or {})
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "run_info.json", "w") as fh:
        json.dump(info, fh, indent=2, sort_keys=True)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subjects", default="", help="comma-separated subject keys (default: all)")
    ap.add_argument("--skip-benchmark", action="store_true",
                    help="reuse results/final/raw/evaluation_records.jsonl; recompute metrics only")
    args = ap.parse_args(argv)
    keys = [k for k in args.subjects.split(",") if k] or None

    from relic_eval import contract_recovery, legacy, llm_baselines, report
    if not args.skip_benchmark:
        records = run_benchmark(keys)
        write_records(records)
        contract_recovery.main()
        legacy.main()
        write_run_info({"subjects": keys or "all"})
    records = load_records()
    llm = llm_baselines.load_llm_predictions()
    metrics = report.compute_all(records, llm)
    report.write_all(metrics)
    print(report.headline(metrics))


if __name__ == "__main__":
    main()
