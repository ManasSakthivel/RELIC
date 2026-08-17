#!/usr/bin/env python3.11
"""
RELIC — Quickstart Example.

Demonstrates the core pipeline on a minimal two-step JCL job:
  1. Parse JCL artifact
  2. Extract TEMPORAL and CONTROL_FLOW contracts
  3. Build Behavioral Contract Graph (BCG)
  4. Apply ALTER_ERROR_BRANCH mutation
  5. Detect contract violation via BCGDiff

Run from repository root:
    python3.11 examples/quickstart/run_quickstart.py

Or from this directory:
    python3.11 run_quickstart.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on the Python path regardless of working directory
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.ir.model import IRGraph
from legacy_contract.ingestion.ingester import ArtifactIngester
from legacy_contract.static_analysis.extractor import StaticContractExtractor
from legacy_contract.bcg.builder import BCGBuilder
from legacy_contract.mutations.engine import MutationEngine
from legacy_contract.risk.detector import RiskDetector


def main() -> None:
    jcl_path = Path(__file__).parent / "SAMPLEJOB.jcl"

    print("=== RELIC Quickstart ===\n")

    # -----------------------------------------------------------------------
    # Step 1: Parse JCL
    # -----------------------------------------------------------------------
    print("Step 1: Parsing SAMPLEJOB.jcl...")
    ingester = ArtifactIngester()
    records = ingester.ingest([str(jcl_path)])

    parser = JCLParser()
    parse_results = [parser.parse(r.content, r.artifact_id) for r in records]
    print(f"  Found job: SAMPLEJOB")

    # -----------------------------------------------------------------------
    # Step 2: Build IR and extract contracts
    # -----------------------------------------------------------------------
    print("\nStep 2: Extracting contracts and building BCG...")
    from legacy_contract.ir.model import IRGraph
    ir = IRGraph()
    for pr in parse_results:
        ir.merge(pr.to_ir())

    extractor = StaticContractExtractor()
    static_result = extractor.extract(ir)

    builder = BCGBuilder()
    original_bcg = builder.build(ir, static_result)

    n_contracts = original_bcg.contract_count()
    print(f"  Entities (V): {len(original_bcg.entities)}")
    print(f"  Contracts (C): {n_contracts}")
    for c in original_bcg.contracts.values():
        src = c.provenance.source_artifact if c.provenance else "unknown"
        conf = c.confidence_score()
        print(f"    [{c.contract_type.value:15s}] {c.subject_id[:20]:20s} "
              f"--{c.predicate.value}--> {c.object_id[:20]:20s}  "
              f"confidence={conf:.3f}")

    # -----------------------------------------------------------------------
    # Step 3: Apply ALTER_ERROR_BRANCH mutation
    # -----------------------------------------------------------------------
    print("\nStep 3: Applying ALTER_ERROR_BRANCH mutation...")
    engine = MutationEngine(seed=42)
    mutations = engine.apply_all(original_bcg, operators=["ALTER_ERROR_BRANCH"])

    if not mutations:
        print("  No ALTER_ERROR_BRANCH mutation applicable to this artifact.")
        print("  (The example JCL may not have a parseable COND= parameter in this environment.)")
        print("\n  Demonstrating BCGDiff structure instead...")
        mutated_bcg = original_bcg  # diff will show no changes
    else:
        mutation = mutations[0]
        mutated_bcg = mutation.mutated_bcg
        print(f"  Applied: {mutation.operator}  "
              f"(affected contract: {mutation.affected_contract_ids})")

    # -----------------------------------------------------------------------
    # Step 4: BCGDiff — detect broken/modified contracts
    # -----------------------------------------------------------------------
    print("\nStep 4: Running BCGDiff...")
    diff = original_bcg.diff(mutated_bcg)
    print(f"  BROKEN contracts:   {len(diff.broken)}")
    print(f"  MODIFIED contracts: {len(diff.modified)}")
    print(f"  PRESERVED:          {len(diff.preserved)}")

    # -----------------------------------------------------------------------
    # Step 5: Risk detection
    # -----------------------------------------------------------------------
    print("\nStep 5: Risk detection...")
    detector = RiskDetector()
    report = detector.detect(original_bcg, mutated_bcg)

    if report.risk_items:
        print(f"\n=== RISK DETECTED: {len(report.risk_items)} item(s) ===")
        for item in report.risk_items:
            print(f"  [{item.risk_level.value}] {item.contract_id[:16]}... "
                  f"— {item.explanation[:80]}")
    else:
        print("\n  No risks detected (expected for a PRESERVED diff).")

    print("\n=== RELIC Quickstart complete ===")
    print("For full benchmark reproduction: make reproduce-paper1")
    print("For documentation: docs/architecture.md, docs/methodology.md")


if __name__ == "__main__":
    main()
