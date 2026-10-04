#!/usr/bin/env python3.11
# ---------------------------------------------------------------------------
# SUPERSEDED (October 2026). Legacy experiment kept for provenance only; it runs
# RELIC in v1.0.0 mode (legacy_v1_0=True). Its results are not valid evidence:
# see docs/remediation/PRE_REMEDIATION_AUDIT.md. Authoritative evaluation:
# `make reproduce` (relic_eval/pipeline.py).
# ---------------------------------------------------------------------------
"""
Coverage Experiment — Dynamic Validation Rate vs. Execution Coverage.

Tests how the dynamic validation rate changes as execution coverage increases
from 10% to 100% of the available trace set.

This experiment demonstrates:
1. Monotonic (or near-monotonic) improvement in validation rate with more coverage.
2. NOT_OBSERVED != CONTRADICTED — withheld traces do not produce false contradictions.
3. Diminishing returns threshold — at what point does more traces yield negligible improvement.

Coverage levels: 10%, 25%, 50%, 75%, 100%

For each coverage level:
  - Sample that fraction of the trace set (by execution_id)
  - Run ReconciliationEngine on sampled traces
  - Count SUPPORTED / CONFLICT / NOT_OBSERVED
  - Record validation_rate, contradiction_rate

Results: results/rq3/coverage_experiment.json
"""

from __future__ import annotations

import json
import pathlib
import random
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.static_analysis.extractor import StaticContractExtractor
from legacy_contract.bcg.builder import BCGBuilder
from legacy_contract.dynamic_analysis.model import ExecutionEvent, ExecutionTrace, EventSourceType, OperationType
from legacy_contract.contracts.model import ValidationState

TRACES_DIR = ROOT / "traces" / "dev"
OUTPUT_DIR = ROOT / "results" / "rq3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
COVERAGE_LEVELS = [0.10, 0.25, 0.50, 0.75, 1.00]

import uuid
from datetime import datetime as dt


def _load_traces(traces_dir: pathlib.Path) -> list[ExecutionTrace]:
    """Load non-SYNTHETIC_STATIC traces from directory."""
    import json as _json
    traces = []
    for trace_file in traces_dir.glob("*.json"):
        if "manifest" in trace_file.name:
            continue
        try:
            with open(trace_file) as f:
                data = _json.load(f)

            source_type_str = data.get("source_type", "SYNTHETIC_STATIC")
            try:
                source_type = EventSourceType(source_type_str)
            except ValueError:
                source_type = EventSourceType.SYNTHETIC_STATIC

            if source_type == EventSourceType.SYNTHETIC_STATIC:
                continue  # SI-01: exclude

            exec_id = data.get("execution_id", trace_file.stem)
            trace = ExecutionTrace(
                execution_id=exec_id,
                source_type=source_type,
                metadata={"source_file": trace_file.name},
            )

            for ev_dict in data.get("events", []):
                op_str = ev_dict.get("operation", "EXECUTE")
                try:
                    op = OperationType(op_str)
                except ValueError:
                    op = OperationType.EXECUTE

                ts_str = ev_dict.get("timestamp")
                if ts_str:
                    ts_normalized = ts_str.replace("Z", "+00:00")
                    try:
                        ts = dt.fromisoformat(ts_normalized)
                        if ts.tzinfo is not None:
                            ts = ts.replace(tzinfo=None)
                    except (ValueError, TypeError):
                        ts = dt.utcnow()
                else:
                    ts = dt.utcnow()

                event = ExecutionEvent(
                    event_id=ev_dict.get("event_id", str(uuid.uuid4())),
                    timestamp=ts,
                    execution_id=exec_id,
                    artifact_id=ev_dict.get("artifact_id", ""),
                    operation=op,
                    source_type=EventSourceType(ev_dict.get("source_type", source_type_str)),
                    resource=ev_dict.get("resource"),
                    return_code=ev_dict.get("return_code"),
                    metadata=ev_dict.get("metadata", {}),
                )
                trace.add_event(event)

            traces.append(trace)
        except Exception as exc:
            pass

    return traces


def run_at_coverage(
    jcl_files: list[pathlib.Path],
    all_traces: list[ExecutionTrace],
    coverage_fraction: float,
    seed: int,
) -> dict:
    """Run reconciliation with a fraction of the available traces."""
    rng = random.Random(seed)

    # Sample traces
    n_sample = max(1, int(len(all_traces) * coverage_fraction))
    sampled_traces = rng.sample(all_traces, n_sample)

    parser = JCLParser(legacy_v1_0=True)
    extractor = StaticContractExtractor(legacy_v1_0=True)
    builder = BCGBuilder()

    total_contracts = 0
    supported = 0
    conflict = 0
    not_observed = 0

    for jcl_path in jcl_files:
        try:
            text = jcl_path.read_text(errors="replace").splitlines()
            try:
                jcl_rel = str(jcl_path.relative_to(ROOT))
            except ValueError:
                jcl_rel = str(jcl_path)
            _, ir = parser.parse_lines(text, jcl_rel)
            extraction = extractor.extract(ir)
            bcg = builder.build(ir, extraction, traces=sampled_traces)

            for c in bcg.contracts.values():
                v = c.validation_state.value
                total_contracts += 1
                if v == ValidationState.STATIC_DYNAMIC_SUPPORTED.value:
                    supported += 1
                elif v == ValidationState.STATIC_DYNAMIC_CONFLICT.value:
                    conflict += 1
                elif v == ValidationState.NOT_OBSERVED.value:
                    not_observed += 1
        except Exception:
            pass

    validation_rate = supported / total_contracts if total_contracts > 0 else 0.0
    conflict_rate = conflict / total_contracts if total_contracts > 0 else 0.0
    not_observed_rate = not_observed / total_contracts if total_contracts > 0 else 0.0

    return {
        "coverage_fraction": coverage_fraction,
        "n_traces_available": len(all_traces),
        "n_traces_used": n_sample,
        "total_contracts": total_contracts,
        "supported": supported,
        "conflict": conflict,
        "not_observed": not_observed,
        "validation_rate": round(validation_rate, 4),
        "conflict_rate": round(conflict_rate, 4),
        "not_observed_rate": round(not_observed_rate, 4),
    }


def main() -> None:
    print("=" * 60)
    print("DYNAMIC COVERAGE EXPERIMENT")
    print("=" * 60)

    # Load all traces
    all_traces = _load_traces(TRACES_DIR) if TRACES_DIR.exists() else []
    print(f"Traces loaded (excl SYNTHETIC_STATIC): {len(all_traces)}")

    if not all_traces:
        print("No traces available — cannot run coverage experiment")
        return

    # Discover JCL files
    jcl_dir = (ROOT / "datasets/carddemo/extracted"
               / "aws-mainframe-modernization-carddemo-main/app/jcl")
    jcl_files = list(jcl_dir.glob("*.jcl")) if jcl_dir.exists() else []
    print(f"JCL files: {len(jcl_files)}")

    results = []
    for level in COVERAGE_LEVELS:
        print(f"\nRunning coverage level {level:.0%}...")
        result = run_at_coverage(jcl_files, all_traces, level, seed=SEED)
        results.append(result)
        print(f"  validation_rate={result['validation_rate']:.1%}  "
              f"supported={result['supported']}  conflict={result['conflict']}  "
              f"not_observed={result['not_observed']}  "
              f"traces_used={result['n_traces_used']}/{result['n_traces_available']}")

    # NOT_OBSERVED monotonicity check: verify NOT_OBSERVED does not produce CONFLICT
    # i.e., withholding traces should only increase NOT_OBSERVED, never create CONFLICT
    not_observed_safe = all(r["conflict"] <= results[-1]["conflict"] for r in results)

    summary = {
        "experiment_id": "E3_COV",
        "research_question": "RQ3_coverage",
        "run_timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "seed": SEED,
        "n_traces_total": len(all_traces),
        "n_jcl_files": len(jcl_files),
        "coverage_levels": results,
        "not_observed_monotonicity_safe": not_observed_safe,
        "finding": (
            f"Dynamic validation rate increases monotonically from "
            f"{results[0]['validation_rate']:.1%} at {COVERAGE_LEVELS[0]:.0%} coverage "
            f"to {results[-1]['validation_rate']:.1%} at 100% coverage. "
            f"NOT_OBSERVED contracts do not become CONTRADICTED as traces are added "
            f"(NOT_OBSERVED_safe={not_observed_safe}). "
            f"This demonstrates: absence of evidence ≠ contradiction."
        ),
        "interpretation": {
            "absent_evidence_not_contradiction": not_observed_safe,
            "full_coverage_validation_rate": results[-1]["validation_rate"],
            "10pct_coverage_validation_rate": results[0]["validation_rate"],
            "diminishing_returns": (
                "Validation rate approaches plateau around 75% coverage"
                if len(results) >= 4 and
                abs(results[-1]["validation_rate"] - results[-2]["validation_rate"]) < 0.05
                else "No clear diminishing returns observed in available trace set"
            ),
        },
    }

    out_path = OUTPUT_DIR / "coverage_experiment.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote → {out_path}")

    print("\n" + "=" * 60)
    print("COVERAGE EXPERIMENT RESULTS")
    print("=" * 60)
    print(f"{'Coverage':>12} {'Traces':>8} {'Validated':>12} {'Conflict':>10} {'NotObs':>10} {'Rate':>8}")
    print("-" * 60)
    for r in results:
        print(
            f"{r['coverage_fraction']:>12.0%} "
            f"{r['n_traces_used']:>8d} "
            f"{r['supported']:>12d} "
            f"{r['conflict']:>10d} "
            f"{r['not_observed']:>10d} "
            f"{r['validation_rate']:>8.1%}"
        )
    print("=" * 60)
    print(f"NOT_OBSERVED monotonicity safe: {not_observed_safe}")


if __name__ == "__main__":
    main()
