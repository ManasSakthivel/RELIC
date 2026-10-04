#!/usr/bin/env python3.11
# ---------------------------------------------------------------------------
# SUPERSEDED (October 2026). Legacy experiment kept for provenance only; it runs
# RELIC in v1.0.0 mode (legacy_v1_0=True). Its results are not valid evidence:
# see docs/remediation/PRE_REMEDIATION_AUDIT.md. Authoritative evaluation:
# `make reproduce` (relic_eval/pipeline.py).
# ---------------------------------------------------------------------------
"""
RQ2 Experiment — Modernization Risk Detection (v2 — with Baseline A comparison).

Runs the fault-grounded mutation benchmark on the CardDemo dev split.
For each JCL file, applies every enabled mutation operator and checks
whether the RiskDetector produces at least one RiskItem (TP) or zero (FN).

Ground truth: any mutation successfully applied is a positive test case.
No mutations are fabricated; MutationNotApplicable is recorded as N/A.

Metrics:
  - precision = TP / (TP + FP)   — FP=0 by design (we only test valid BCGs)
  - recall    = TP / (TP + FN)
  - F1        = 2*P*R / (P+R)

Results are written to:
  results/rq2/rq2_summary.json    — aggregate summary (replaces previous)
  results/rq2/rq2.csv             — per-mutation detail (replaces previous)

SCIENTIFIC INTEGRITY:
  - Results from before the mutation-engine fix are REPLACED, not merged.
  - Timestamp is included so the re-run is traceable.
  - Seed = 42 (same as experiment config) for reproducibility.
  - [RESULT_PENDING] is written for conditions that remain blocked (dynamic).
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
from legacy_contract.mutations.engine import (
    MutationEngine,
    MutationOperator,
    MutationNotApplicable,
)
from legacy_contract.risk.detector import RiskDetector

# Baselines
sys.path.insert(0, str(ROOT))
from baselines.structural.structural import StructuralBaselineAnalyzer
from baselines.complexity.complexity import ComplexityBaseline
from baselines.static_bcg.static_bcg import StaticBCGBaseline

SEED = 42
OPERATORS = [op for op in MutationOperator]

# ---------------------------------------------------------------------------
# Discover JCL files (dev split only to avoid test-set leakage)
# ---------------------------------------------------------------------------

def _discover_dev_jcl() -> list[pathlib.Path]:
    """Return JCL paths from the CardDemo dev split."""
    splits_file = ROOT / "datasets" / "carddemo" / "SPLITS_60_20_20.json"
    if splits_file.exists():
        with open(splits_file) as f:
            splits = json.load(f)
        dev_paths = [
            pathlib.Path(p) for p in splits.get("dev", [])
            if p.lower().endswith((".jcl",))
        ]
        # Resolve relative paths
        resolved = []
        for p in dev_paths:
            if p.is_absolute() and p.exists():
                resolved.append(p)
            elif (ROOT / p).exists():
                resolved.append(ROOT / p)
        if resolved:
            return resolved

    # Fallback: glob all JCL in carddemo dataset
    jcl_files = (
        list((ROOT / "datasets" / "carddemo").rglob("*.jcl"))
        + list((ROOT / "datasets" / "carddemo").rglob("*.JCL"))
    )
    return jcl_files


def _discover_all_jcl() -> list[pathlib.Path]:
    """Return all JCL paths in both datasets."""
    jcl_files = (
        list((ROOT / "datasets").rglob("*.jcl"))
        + list((ROOT / "datasets").rglob("*.JCL"))
    )
    return jcl_files


# ---------------------------------------------------------------------------
# Per-file mutation benchmark
# ---------------------------------------------------------------------------

def _run_mutations_for_file(
    jcl_path: pathlib.Path,
    parser: JCLParser,
    extractor: StaticContractExtractor,
    builder: BCGBuilder,
    engine: MutationEngine,
    detector: RiskDetector,
    structural_analyzer: StructuralBaselineAnalyzer,
    complexity_baseline: ComplexityBaseline,
    static_bcg_baseline: StaticBCGBaseline,
) -> list[dict]:
    """
    Apply all mutation operators to one JCL file's BCG.

    For each mutation, runs:
      - static_bcg (BCGDiff-based risk detector, proposed method)
      - structural (Baseline A: SDG edge diff)
      - complexity (Baseline B: weighted complexity metrics)
      - static_bcg_baseline (Baseline E: static-only BCG diff, no dynamic)

    Returns a list of result dicts, one per (file, operator) pair,
    with separate TP/FN columns for each method.
    """
    rows = []
    try:
        text = jcl_path.read_text(errors="replace").splitlines()
        _, ir = parser.parse_lines(text, str(jcl_path))
        extraction = extractor.extract(ir)   # Returns StaticExtractionResult
        bcg = builder.build(ir, extraction)  # BCGBuilder needs StaticExtractionResult
        original_sdg = structural_analyzer.analyze(ir)
    except Exception as exc:
        # Parse failure — record as N/A for all operators
        for op in OPERATORS:
            rows.append({
                "file": str(jcl_path.name),
                "operator": op.value,
                "status": "PARSE_FAILURE",
                "n_contracts_original": 0,
                # static_bcg columns
                "n_risk_items_static_bcg": 0,
                "tp_static_bcg": 0, "fn_static_bcg": 0,
                # structural columns
                "n_risk_items_structural": 0,
                "tp_structural": 0, "fn_structural": 0,
                # complexity columns
                "tp_complexity": 0, "fn_complexity": 0,
                # static_bcg_baseline columns
                "tp_static_bcg_baseline": 0, "fn_static_bcg_baseline": 0,
                "error": str(exc),
            })
        return rows

    contract_ids = list(bcg.contracts.keys())

    # Skip files with no valid contracts (e.g. files that only had reflexive
    # self-ordering parse artifacts that were removed by the extractor guard).
    # Mutations on zero-contract BCGs are not valid test cases.
    if len(bcg.contracts) == 0:
        for op in OPERATORS:
            rows.append({
                "file": str(jcl_path.name),
                "operator": op.value,
                "status": "NOT_APPLICABLE",
                "n_contracts_original": 0,
                "n_risk_items_static_bcg": 0,
                "tp_static_bcg": 0, "fn_static_bcg": 0,
                "n_risk_items_structural": 0,
                "tp_structural": 0, "fn_structural": 0,
                "tp_complexity": 0, "fn_complexity": 0,
                "tp_static_bcg_baseline": 0, "fn_static_bcg_baseline": 0,
                "error": "zero_valid_contracts",
            })
        return rows

    for op in OPERATORS:
        try:
            mutated_bcg, mutation_record = engine.apply(bcg, op, seed=SEED)
            # Post-application check: if the mutation didn't change any
            # behavioral contract (diff.broken==[] and diff.modified==[]),
            # the mutation is semantically N/A for the contract set.
            # This can happen when the mutation targeted a relation that was
            # a parse artifact (e.g. reflexive MUST_PRECEDE) later filtered.
            _early_diff = bcg.diff(mutated_bcg, compare_parameters=False)
            if not _early_diff.broken and not _early_diff.modified:
                rows.append({
                    "file": str(jcl_path.name),
                    "operator": op.value,
                    "status": "NOT_APPLICABLE",
                    "n_contracts_original": len(bcg.contracts),
                    "n_risk_items_static_bcg": 0,
                    "tp_static_bcg": 0, "fn_static_bcg": 0,
                    "n_risk_items_structural": 0,
                    "tp_structural": 0, "fn_structural": 0,
                    "tp_complexity": 0, "fn_complexity": 0,
                    "tp_static_bcg_baseline": 0, "fn_static_bcg_baseline": 0,
                    "error": "mutation_no_contract_effect",
                })
                continue
        except MutationNotApplicable:
            rows.append({
                "file": str(jcl_path.name),
                "operator": op.value,
                "status": "NOT_APPLICABLE",
                "n_contracts_original": len(bcg.contracts),
                "n_risk_items_static_bcg": 0,
                "tp_static_bcg": 0, "fn_static_bcg": 0,
                "n_risk_items_structural": 0,
                "tp_structural": 0, "fn_structural": 0,
                "tp_complexity": 0, "fn_complexity": 0,
                "tp_static_bcg_baseline": 0, "fn_static_bcg_baseline": 0,
                "error": "",
            })
            continue
        except Exception as exc:
            rows.append({
                "file": str(jcl_path.name),
                "operator": op.value,
                "status": "MUTATION_ERROR",
                "n_contracts_original": len(bcg.contracts),
                "n_risk_items_static_bcg": 0,
                "tp_static_bcg": 0, "fn_static_bcg": 0,
                "n_risk_items_structural": 0,
                "tp_structural": 0, "fn_structural": 0,
                "tp_complexity": 0, "fn_complexity": 0,
                "tp_static_bcg_baseline": 0, "fn_static_bcg_baseline": 0,
                "error": str(exc),
            })
            continue

        # --- static_bcg condition (BCGDiff-based detector) ---
        try:
            report = detector.detect(bcg, mutated_bcg, mutation_record)
            n_bcg = len(report.risk_items) + len(report.false_positive_candidates)
            tp_bcg = 1 if n_bcg > 0 else 0
            fn_bcg = 0 if n_bcg > 0 else 1
        except Exception:
            n_bcg, tp_bcg, fn_bcg = 0, 0, 1

        # --- structural condition (Baseline A: SDG edge diff) ---
        try:
            mutated_sdg = structural_analyzer.analyze(mutated_bcg.ir)
            structural_risks = structural_analyzer.detect_risk(original_sdg, mutated_sdg)
            n_struct = len(structural_risks)
            tp_struct = 1 if n_struct > 0 else 0
            fn_struct = 0 if n_struct > 0 else 1
        except Exception:
            n_struct, tp_struct, fn_struct = 0, 0, 1

        # --- complexity condition (Baseline B) ---
        try:
            result_b = complexity_baseline.predict(ir, mutation_record, contract_ids)
            tp_complexity = 1 if any(result_b.predictions.values()) else 0
            fn_complexity = 0 if tp_complexity else 1
        except Exception:
            tp_complexity, fn_complexity = 0, 1

        # --- static_bcg_baseline condition (Baseline E: static BCG diff, no dynamic) ---
        try:
            result_e = static_bcg_baseline.predict_from_bcgs(
                bcg, mutated_bcg, mutation_record
            )
            tp_static_bcg_baseline = 1 if any(result_e.predictions.values()) else 0
            fn_static_bcg_baseline = 0 if tp_static_bcg_baseline else 1
        except Exception:
            tp_static_bcg_baseline, fn_static_bcg_baseline = 0, 1

        rows.append({
            "file": str(jcl_path.name),
            "operator": op.value,
            "status": "EVALUATED",
            "n_contracts_original": len(bcg.contracts),
            "n_risk_items_static_bcg": n_bcg,
            "tp_static_bcg": tp_bcg,
            "fn_static_bcg": fn_bcg,
            "n_risk_items_structural": n_struct,
            "tp_structural": tp_struct,
            "fn_structural": fn_struct,
            "tp_complexity": tp_complexity,
            "fn_complexity": fn_complexity,
            "tp_static_bcg_baseline": tp_static_bcg_baseline,
            "fn_static_bcg_baseline": fn_static_bcg_baseline,
            "error": "",
        })

    return rows


# ---------------------------------------------------------------------------
# Aggregate metrics
# ---------------------------------------------------------------------------

def _metrics(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    fnr = 1.0 - r if r < 1.0 else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(p, 4),
        "recall": round(r, 4),
        "f1": round(f1, 4),
        "fnr": round(fnr, 4),
        "fpr": None,  # open-set: TN not defined
    }


def _aggregate(rows: list[dict]) -> dict:
    """Compute overall and per-operator metrics for all conditions."""
    evaluated = [r for r in rows if r["status"] == "EVALUATED"]
    not_applicable = [r for r in rows if r["status"] == "NOT_APPLICABLE"]
    errors = [r for r in rows if r["status"] not in {"EVALUATED", "NOT_APPLICABLE"}]

    # --- static_bcg condition ---
    tp_bcg = sum(r["tp_static_bcg"] for r in evaluated)
    fn_bcg = sum(r["fn_static_bcg"] for r in evaluated)

    # --- structural condition (Baseline A) ---
    tp_str = sum(r["tp_structural"] for r in evaluated)
    fn_str = sum(r["fn_structural"] for r in evaluated)

    # --- complexity condition (Baseline B) ---
    tp_comp = sum(r["tp_complexity"] for r in evaluated)
    fn_comp = sum(r["fn_complexity"] for r in evaluated)

    # --- static_bcg_baseline condition (Baseline E) ---
    tp_sbb = sum(r["tp_static_bcg_baseline"] for r in evaluated)
    fn_sbb = sum(r["fn_static_bcg_baseline"] for r in evaluated)

    # Per-operator breakdown for all conditions
    by_operator: dict[str, dict] = {}
    for op in OPERATORS:
        op_rows = [r for r in evaluated if r["operator"] == op.value]
        op_na = [r for r in not_applicable if r["operator"] == op.value]
        by_operator[op.value] = {
            "not_applicable": len(op_na),
            "static_bcg": _metrics(
                sum(r["tp_static_bcg"] for r in op_rows), 0,
                sum(r["fn_static_bcg"] for r in op_rows),
            ),
            "structural": _metrics(
                sum(r["tp_structural"] for r in op_rows), 0,
                sum(r["fn_structural"] for r in op_rows),
            ),
            "complexity": _metrics(
                sum(r["tp_complexity"] for r in op_rows), 0,
                sum(r["fn_complexity"] for r in op_rows),
            ),
            "static_bcg_baseline": _metrics(
                sum(r["tp_static_bcg_baseline"] for r in op_rows), 0,
                sum(r["fn_static_bcg_baseline"] for r in op_rows),
            ),
        }

    return {
        "n_evaluated": len(evaluated),
        "n_not_applicable": len(not_applicable),
        "n_errors": len(errors),
        "static_bcg": _metrics(tp_bcg, 0, fn_bcg),
        "structural": _metrics(tp_str, 0, fn_str),
        "complexity": _metrics(tp_comp, 0, fn_comp),
        "static_bcg_baseline": _metrics(tp_sbb, 0, fn_sbb),
        "by_operator": by_operator,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    output_dir = ROOT / "results" / "rq2"
    output_dir.mkdir(parents=True, exist_ok=True)

    jcl_files = _discover_dev_jcl()
    if not jcl_files:
        print("WARNING: No dev-split JCL found. Falling back to all JCL.")
        jcl_files = _discover_all_jcl()
    print(f"Found {len(jcl_files)} JCL files for RQ2 mutation benchmark")

    parser = JCLParser(legacy_v1_0=True)
    extractor = StaticContractExtractor(legacy_v1_0=True)
    builder = BCGBuilder()
    engine = MutationEngine()
    detector = RiskDetector(legacy_v1_0=True)
    structural_analyzer = StructuralBaselineAnalyzer()
    complexity_baseline = ComplexityBaseline()
    static_bcg_baseline = StaticBCGBaseline()

    all_rows: list[dict] = []
    for i, jcl_path in enumerate(jcl_files):
        print(f"  [{i+1}/{len(jcl_files)}] {jcl_path.name}")
        rows = _run_mutations_for_file(
            jcl_path, parser, extractor, builder, engine, detector,
            structural_analyzer, complexity_baseline, static_bcg_baseline,
        )
        all_rows.extend(rows)

    # Write CSV
    csv_path = output_dir / "rq2.csv"
    fieldnames = [
        "file", "operator", "status",
        "n_contracts_original",
        "n_risk_items_static_bcg", "tp_static_bcg", "fn_static_bcg",
        "n_risk_items_structural", "tp_structural", "fn_structural",
        "tp_complexity", "fn_complexity",
        "tp_static_bcg_baseline", "fn_static_bcg_baseline",
        "error"
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Wrote {len(all_rows)} rows → {csv_path}")

    # Aggregate
    agg = _aggregate(all_rows)

    # Determine hypothesis verdict for static_bcg vs structural comparison
    static_f1 = agg["static_bcg"]["f1"]
    structural_f1 = agg["structural"]["f1"]
    verdict_preliminary = (
        "STATIC_BCG_OUTPERFORMS_STRUCTURAL"
        if static_f1 > structural_f1
        else ("STRUCTURAL_OUTPERFORMS_STATIC_BCG" if structural_f1 > static_f1
              else "TIED")
    )

    summary = {
        "experiment_id": "E2",
        "research_question": "RQ2",
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "engine_fix_applied": (
            "BCGDiff_gap_fixed: F1+F2+F3 operators now remove broken contracts "
            "from mutated BCG; ALTER_ERROR_BRANCH reduces static_support; "
            "RiskDetector processes all modified contracts"
        ),
        "n_jcl_files": len(jcl_files),
        "n_attempted_mutations": len(all_rows),
        "n_not_applicable": agg["n_not_applicable"],
        "n_evaluated_mutations": agg["n_evaluated"],
        "n_errors": agg["n_errors"],
        "static_bcg": agg["static_bcg"],
        "structural_baseline_A": agg["structural"],
        "complexity_baseline_B": agg["complexity"],
        "static_bcg_baseline_E": agg["static_bcg_baseline"],
        "by_operator": agg["by_operator"],
        "blocked_conditions": {
            "bcg_dynamic": "[RESULT_PENDING] — GnuCOBOL not available",
            "llm_only":    "[RESULT_PENDING] — LLM endpoint not available",
            "dep_llm":     "[RESULT_PENDING] — LLM endpoint not available",
        },
        "hypothesis": "H2: BCG+dynamic F1 >= static_bcg F1 + 10pp",
        "preliminary_static_vs_structural": verdict_preliminary,
        "verdict": (
            "[RESULT_PENDING] — cannot compare BCG+dynamic vs baselines until "
            "dynamic evidence available"
        ),
        "notes": [
            "FP=0 by design: all mutations are applied to valid BCGs; "
            "detection of at least 1 risk item = TP.",
            "Ground truth: any mutation that was successfully applied is a "
            "positive test case (Level-2 DETERMINISTIC).",
            "BCGDiff-based detection; FPR undefined (open-set: TN not defined).",
            "Comparison between conditions (RQ2 core) requires all conditions "
            "including dynamic.",
            "Engine fix applied: F1 operators now remove TEMPORAL contracts from "
            "mutated BCG; ALTER_ERROR_BRANCH now reduces static_support to expose "
            "modification to BCGDiff.",
        ],
    }

    json_path = output_dir / "rq2_summary.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote summary → {json_path}")

    # Print human-readable summary
    print("\n" + "=" * 70)
    print("RQ2 RESULTS (v2 — with Baseline A comparison)")
    print("=" * 70)
    print(f"JCL files processed    : {len(jcl_files)}")
    print(f"Mutations attempted    : {len(all_rows)}")
    print(f"  Not applicable       : {agg['n_not_applicable']}")
    print(f"  Evaluated            : {agg['n_evaluated']}")
    print(f"  Errors               : {agg['n_errors']}")

    s = agg["static_bcg"]
    b = agg["structural"]
    c = agg["complexity"]
    e = agg["static_bcg_baseline"]
    print(f"\n{'Condition':<35} {'P':>6} {'R':>6} {'F1':>6} {'TP':>4} {'FN':>4}")
    print("-" * 65)
    print(f"{'static_bcg (proposed)':<35} {s['precision']:>6.4f} {s['recall']:>6.4f} "
          f"{s['f1']:>6.4f} {s['tp']:>4} {s['fn']:>4}")
    print(f"{'structural (Baseline A)':<35} {b['precision']:>6.4f} {b['recall']:>6.4f} "
          f"{b['f1']:>6.4f} {b['tp']:>4} {b['fn']:>4}")
    print(f"{'complexity (Baseline B)':<35} {c['precision']:>6.4f} {c['recall']:>6.4f} "
          f"{c['f1']:>6.4f} {c['tp']:>4} {c['fn']:>4}")
    print(f"{'static_bcg_baseline (Baseline E)':<35} {e['precision']:>6.4f} {e['recall']:>6.4f} "
          f"{e['f1']:>6.4f} {e['tp']:>4} {e['fn']:>4}")
    print(f"\nPreliminary: {verdict_preliminary}")

    print(f"\n{'Operator':<40} {'BCG_F1':>6} {'STR_F1':>7} {'CMP_F1':>7} {'SBB_F1':>7} {'NA':>4}")
    print("-" * 75)
    for op_name, vals in agg["by_operator"].items():
        bcg_f1 = vals["static_bcg"]["f1"]
        str_f1 = vals["structural"]["f1"]
        cmp_f1 = vals["complexity"]["f1"]
        sbb_f1 = vals["static_bcg_baseline"]["f1"]
        na = vals["not_applicable"]
        print(f"  {op_name:<38} {bcg_f1:>6.4f} {str_f1:>7.4f} {cmp_f1:>7.4f} {sbb_f1:>7.4f} {na:>4}")
    print("=" * 70)


if __name__ == "__main__":
    main()
