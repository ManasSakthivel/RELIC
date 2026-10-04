#!/usr/bin/env python3
"""
RELIC — Quickstart Example (source-level).

Shows the real use of RELIC on a minimal two-step JCL job:
  1. parse the original JCL and extract behavioural contracts (BCG);
  2. edit the JCL *source* (a migration that loosens a COND guard);
  3. parse the edited JCL, diff the two BCGs, report broken/weakened contracts;
  4. ask the independent oracle (jcl_oracle) whether behaviour really changed.

It runs RELIC v1.0.0 (as released) and v1.1 (post-hoc fixes): v1.0.0 misses this
change because its diff ignored COND thresholds — one of the defects reported in
docs/evaluation/RESULTS.md.

Run from the repository root:
    .venv/bin/python examples/quickstart/run_quickstart.py
"""
from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
sys.path[:0] = [str(repo_root / "src"), str(repo_root)]

from loguru import logger  # noqa: E402

from jcl_oracle.judge import compare_versions  # noqa: E402
from legacy_contract.bcg.builder import BCGBuilder  # noqa: E402
from legacy_contract.parsers.jcl_parser import JCLParser  # noqa: E402
from legacy_contract.risk.detector import RiskDetector  # noqa: E402
from legacy_contract.static_analysis.extractor import StaticContractExtractor  # noqa: E402
from relic_eval.detectors import neutral_record  # noqa: E402

logger.remove()


def build_bcg(text: str, path: str, legacy: bool):
    _res, ir = JCLParser(legacy_v1_0=legacy).parse_lines(text.splitlines(), path)
    return BCGBuilder().build(ir, StaticContractExtractor(legacy_v1_0=legacy).extract(ir))


def name(bcg, entity_id: str) -> str:
    e = bcg.entities.get(entity_id)
    return getattr(e, "name", None) or entity_id


def main() -> None:
    jcl_path = Path(__file__).parent / "SAMPLEJOB.jcl"
    original = jcl_path.read_text()
    # The "migration" weakens the guard on PROCESS. IBM COND semantics: the step is
    # BYPASSED when the test is true. (4,GT,INITFILE) bypasses PROCESS when 4 > RC
    # of INITFILE; (2,GT,INITFILE) bypasses it only when 2 > RC, so PROCESS now
    # runs when INITFILE ends with RC 2 or 3.
    modified = original.replace("COND=(4,GT,INITFILE)", "COND=(2,GT,INITFILE)")
    assert modified != original

    print("=== RELIC Quickstart ===\n")
    print("Change under review:  COND=(4,GT,INITFILE)  ->  COND=(2,GT,INITFILE)\n")

    for legacy, label in ((True, "RELIC v1.0.0 (as released)"), (False, "RELIC v1.1 (post-hoc fixes)")):
        b0 = build_bcg(original, str(jcl_path), legacy)
        b1 = build_bcg(modified, str(jcl_path), legacy)
        print(f"--- {label}")
        print(f"  contracts in original BCG: {len(b0.contracts)}")
        for c in b0.contracts.values():
            extra = ""
            if c.metadata.get("rc_threshold") is not None:
                extra = f"  (RC test: {c.metadata.get('rc_threshold')},{c.metadata.get('operator')})"
            print(f"    [{c.contract_type.value:12s}] {name(b0, c.subject_id)} "
                  f"--{c.predicate.value}--> {name(b0, c.object_id)}{extra}")
        diff = b0.diff(b1, compare_parameters=not legacy)
        report = RiskDetector(legacy_v1_0=legacy).detect(b0, b1, neutral_record())
        items = report.risk_items + report.false_positive_candidates
        print(f"  diff: broken={len(diff.broken)} modified={len(diff.modified)} preserved={len(diff.preserved)}")
        print(f"  verdict: {'RISK — ' + str(len(items)) + ' contract(s) broken or weakened' if items else 'no risk reported'}")
        for it in items:
            print(f"    [{it.risk_level.value}] {it.contract_type.value}: {it.consequence[:100]}")
        print()

    verdict = compare_versions(original, modified)
    print("--- Independent oracle (jcl_oracle)")
    print(f"  label: {verdict.label}  (differing scenarios: {verdict.differing_scenarios} "
          f"of {verdict.scenarios_checked})")
    for e in verdict.evidence[:2]:
        print(f"    {e[:110]}")

    print("\nFull evaluation: make reproduce   |   results: docs/evaluation/RESULTS.md")


if __name__ == "__main__":
    main()
