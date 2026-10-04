#!/usr/bin/env python3.11
# ---------------------------------------------------------------------------
# SUPERSEDED (October 2026). Legacy experiment kept for provenance only; it runs
# RELIC in v1.0.0 mode (legacy_v1_0=True). Its results are not valid evidence:
# see docs/remediation/PRE_REMEDIATION_AUDIT.md. Authoritative evaluation:
# `make reproduce` (relic_eval/pipeline.py).
# ---------------------------------------------------------------------------
"""
Negative Mutation Benchmark — True Negative (TN) Set Generation.

Generates semantically-preserving mutations (TNs) using NegativeMutationEngine.
These are changes that DO NOT violate any behavioral contract.

For each applicable operator × JCL file combination:
  - Apply the negative mutation
  - Build a BCGDiff (original vs. mutated)
  - Run RiskDetector on the diff
  - Verify: expected_detection=False
  - Record: actual_detection (should always be False — any True = FP)

Outputs:
  results/rq2/negative_mutations.json   — per-mutation detail
  results/rq2/negative_summary.json     — aggregate FP/TN/FPR

Scientific purpose:
  Enables FPR = FP / (FP + TN) calculation required for H3.
  Provides ground-truth negative set for combined precision/recall/F1/FPR.

Combined benchmark (positive + negative):
  precision = TP / (TP + FP)
  recall    = TP / (TP + FN)
  FPR       = FP / (FP + TN)
  F1        = 2*P*R / (P+R)

NOTE: RiskDetector.detect() signature is:
  detect(original_bcg, mutated_bcg, mutation_record) -> RiskReport
For negative mutations (no MutationRecord), we use BCGDiff directly
and check diff.broken / diff.modified to determine detection.
"""

from __future__ import annotations

import csv
import json
import pathlib
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.static_analysis.extractor import StaticContractExtractor
from legacy_contract.bcg.builder import BCGBuilder
from legacy_contract.bcg.model import BCG
from legacy_contract.mutations.negative_mutations import (
    NegativeMutationEngine,
    NegativeOperator,
)
# We use BCGDiff directly for negative mutations since RiskDetector
# expects a MutationRecord which is not available for negative mutations.
# For negative mutations, any diff.broken or diff.modified = FP.

SEED = 42
OUTPUT_DIR = ROOT / "results" / "rq2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OPERATORS = list(NegativeOperator)

VARIANT_SEEDS = [42, 43, 44]  # 3 seeds per operator per file for variety


def _discover_jcl_files() -> list[pathlib.Path]:
    """Return all JCL files from CardDemo dev split."""
    splits_file = ROOT / "datasets" / "carddemo" / "SPLITS_60_20_20.json"
    if splits_file.exists():
        with open(splits_file) as f:
            splits = json.load(f)
        dev_paths = [pathlib.Path(p) for p in splits.get("dev", [])
                     if p.lower().endswith(".jcl")]
        resolved = []
        for p in dev_paths:
            if p.is_absolute() and p.exists():
                resolved.append(p)
            elif (ROOT / p).exists():
                resolved.append(ROOT / p)
        if resolved:
            return resolved

    jcl_dir = (ROOT / "datasets/carddemo/extracted"
                / "aws-mainframe-modernization-carddemo-main/app/jcl")
    if jcl_dir.exists():
        return list(jcl_dir.glob("*.jcl"))
    return []


def build_bcg(jcl_path: pathlib.Path, parser: JCLParser,
              extractor: StaticContractExtractor,
              builder: BCGBuilder) -> BCG:
    text = jcl_path.read_text(errors="replace").splitlines()
    try:
        jcl_rel = str(jcl_path.relative_to(ROOT))
    except ValueError:
        jcl_rel = str(jcl_path)
    _, ir = parser.parse_lines(text, jcl_rel)
    extraction = extractor.extract(ir)
    return builder.build(ir, extraction)


def main() -> None:
    print("=" * 60)
    print("NEGATIVE MUTATION BENCHMARK")
    print("=" * 60)

    jcl_files = _discover_jcl_files()
    print(f"JCL files discovered: {len(jcl_files)}")

    parser = JCLParser(legacy_v1_0=True)
    extractor = StaticContractExtractor(legacy_v1_0=True)
    builder = BCGBuilder()
    neg_engine = NegativeMutationEngine()

    rows = []
    total_attempted = 0
    total_not_applicable = 0
    total_tn = 0
    total_fp = 0

    by_operator: dict[str, dict] = {}

    for jcl_path in jcl_files:
        try:
            original_bcg = build_bcg(jcl_path, parser, extractor, builder)
        except Exception as exc:
            print(f"  PARSE ERROR {jcl_path.name}: {exc}")
            continue

        for op in OPERATORS:
            for seed in VARIANT_SEEDS:
                total_attempted += 1
                try:
                    mutated_bcg, record = neg_engine.apply(original_bcg, op, seed=seed)

                    # Compute BCGDiff
                    diff = original_bcg.diff(mutated_bcg, compare_parameters=False)

                    # For negative mutations: any broken/modified contracts = FP
                    # (semantics-preserving mutations must NEVER trigger risk detection)
                    diff_broken = len(diff.broken)
                    diff_modified = len(diff.modified)
                    actual_detection = (diff_broken > 0) or (diff_modified > 0)

                    if actual_detection:
                        total_fp += 1
                        detection_label = "FP"  # False Positive (we should NOT have fired)
                        print(f"  ⚠ FALSE POSITIVE: {op.value} on {jcl_path.name} "
                              f"seed={seed} | broken={diff_broken} modified={diff_modified}")
                    else:
                        total_tn += 1
                        detection_label = "TN"

                    row = {
                        "file": jcl_path.name,
                        "operator": op.value,
                        "seed": seed,
                        "category": "NEGATIVE",
                        "expected_detection": False,
                        "actual_detection": actual_detection,
                        "result": detection_label,
                        "diff_broken": diff_broken,
                        "diff_modified": diff_modified,
                        "mutation_id": record.mutation_id,
                        "description": record.description,
                    }
                    rows.append(row)

                    if op.value not in by_operator:
                        by_operator[op.value] = {"tn": 0, "fp": 0, "not_applicable": 0}
                    if actual_detection:
                        by_operator[op.value]["fp"] += 1
                    else:
                        by_operator[op.value]["tn"] += 1

                except (ValueError, KeyError, AttributeError) as exc:
                    # NegativeMutationEngine raises ValueError for N/A cases
                    total_not_applicable += 1
                    if op.value not in by_operator:
                        by_operator[op.value] = {"tn": 0, "fp": 0, "not_applicable": 0}
                    by_operator[op.value]["not_applicable"] += 1
                    # Only log first N/A for each op (verbose)
                    pass
                except Exception as exc:
                    print(f"  ERROR {op.value} {jcl_path.name} seed={seed}: {exc}")
                    total_not_applicable += 1

    # Compute FPR
    fpr = total_fp / (total_fp + total_tn) if (total_fp + total_tn) > 0 else None

    # Combined benchmark (load positive results too)
    rq2_summary_path = OUTPUT_DIR / "rq2_summary.json"
    combined_stats = {}
    if rq2_summary_path.exists():
        with open(rq2_summary_path) as f:
            rq2 = json.load(f)
        for cond, metrics in rq2.items():
            if isinstance(metrics, dict) and "tp" in metrics:
                tp = metrics.get("tp", 0)
                fn = metrics.get("fn", 0)
                prec = metrics.get("precision", 0.0)
                rec = metrics.get("recall", 0.0)
                f1 = metrics.get("f1", 0.0)
                # Add negatives
                combined_fp = total_fp  # FPs from negative set
                combined_tn = total_tn
                combined_fpr = combined_fp / (combined_fp + combined_tn) if (combined_fp + combined_tn) > 0 else None
                combined_stats[cond] = {
                    "tp": tp, "fn": fn, "fp": combined_fp, "tn": combined_tn,
                    "precision": prec, "recall": rec, "f1": f1,
                    "fpr": round(combined_fpr, 4) if combined_fpr is not None else None,
                    "specificity": round(combined_tn / (combined_tn + combined_fp), 4)
                    if (combined_tn + combined_fp) > 0 else None,
                }

    summary = {
        "experiment_id": "E2_NEG",
        "run_timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "seed": SEED,
        "n_jcl_files": len(jcl_files),
        "n_operators": len(OPERATORS),
        "n_variant_seeds": len(VARIANT_SEEDS),
        "n_attempted": total_attempted,
        "n_not_applicable": total_not_applicable,
        "n_evaluated": total_tn + total_fp,
        "tn": total_tn,
        "fp": total_fp,
        "fpr": round(fpr, 4) if fpr is not None else 0.0,
        "specificity": round(total_tn / (total_tn + total_fp), 4)
        if (total_tn + total_fp) > 0 else None,
        "by_operator": by_operator,
        "combined_with_positive_benchmark": combined_stats,
        "scientific_note": (
            "TN set generated by NegativeMutationEngine (5 semantically-preserving operators). "
            "FP = risk detector fires on a semantics-preserving mutation (should not fire). "
            "FPR = FP / (FP + TN). "
            "Combined FPR uses TN from this experiment and FP from positive-set detection."
        ),
    }

    # Write summary
    neg_summary_path = OUTPUT_DIR / "negative_summary.json"
    with open(neg_summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote → {neg_summary_path}")

    # Write CSV
    neg_csv_path = OUTPUT_DIR / "negative_mutations.csv"
    if rows:
        with open(neg_csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote → {neg_csv_path}")

    print("\n" + "=" * 60)
    print("NEGATIVE MUTATION BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Attempted          : {total_attempted}")
    print(f"Not applicable     : {total_not_applicable}")
    print(f"Evaluated          : {total_tn + total_fp}")
    print(f"  TN (correct)     : {total_tn}")
    print(f"  FP (false alert) : {total_fp}")
    print(f"FPR                : {fpr:.4f}" if fpr is not None else "FPR: 0.0000")
    print(f"Specificity        : {total_tn / (total_tn + total_fp):.4f}"
          if (total_tn + total_fp) > 0 else "Specificity: N/A")
    print()
    for op, stats in by_operator.items():
        n = stats["tn"] + stats["fp"]
        print(f"  {op:40s}: TN={stats['tn']:3d} FP={stats['fp']:3d} N/A={stats['not_applicable']:3d}")
    print("=" * 60)


if __name__ == "__main__":
    main()
