# Claim-Evidence Matrix

**Date:** 2025
**Policy:** A claim may only be marked SAFE_TO_CLAIM if actual experimental evidence supports it.
**Scale:** SAFE_TO_CLAIM | PARTIALLY_SUPPORTED | NOT_YET_TESTABLE | UNSUPPORTED

---

| # | Claim | Evidence | Experiment Result | Confidence | Safe to Claim? |
|---|-------|----------|-------------------|-----------|----------------|
| C1 | BCG static extractor recovers behavioral contracts from JCL artifacts with measurable precision/recall | Level-3 human annotation (PENDING) | RQ1 = BLOCKED_FOR_INDEPENDENT_VALIDATION. Level-2 self-consistency F1=1.0 is not independent evidence. | BLOCKED | **NOT_YET_TESTABLE** — requires Level-3 human annotation; Level-2 result is self-consistency only |
| C2 | Extraction is deterministic and reproducible | SI-08, SI-10; same inputs → same outputs | Both tests pass | HIGH | **SAFE_TO_CLAIM** — "the BCG extractor is deterministic" |
| C3 | Entity IDs are stable across Python sessions | SI-10 (deterministic hex ID) | 5/5 subtests pass | HIGH | **SAFE_TO_CLAIM** |
| C4 | SYNTHETIC_STATIC evidence cannot upgrade contracts | SI-01 | Pass | HIGH | **SAFE_TO_CLAIM** |
| C5 | HUMAN_VALIDATED/GROUND_TRUTH states are protected | SI-07, SI-12 | Pass | HIGH | **SAFE_TO_CLAIM** |
| C6 | BCGDiff detects F3 (SUPPRESS_RETURN_CODE_CHECK) violations | RQ2 mutation evaluation | F1=1.0 for SUPPRESS_RETURN_CODE_CHECK | HIGH | **SAFE_TO_CLAIM** — with caveat: only one operator type |
| C7 | BCGDiff fails to detect F1 structural reordering | RQ2 mutation evaluation | F1=0.0 for all F1 operators | HIGH | **SAFE_TO_CLAIM** — as a finding/limitation |
| C8 | Dynamic evidence improves modernization risk detection | RQ2 BCG+dynamic condition | [RESULT_PENDING] — GnuCOBOL unavailable | N/A | **NOT_YET_TESTABLE** |
| C9 | BCG+dynamic F1 ≥ static-only F1 + 10pp (H2) | RQ2 pairwise comparison | [RESULT_PENDING] | N/A | **NOT_YET_TESTABLE** |
| C10 | Dynamic evidence reduces false positives (H3) | RQ3 coverage sweep | [RESULT_PENDING] — blocked | N/A | **NOT_YET_TESTABLE** |
| C11 | Coverage threshold exists with diminishing returns | RQ3 | [RESULT_PENDING] | N/A | **NOT_YET_TESTABLE** |
| C12 | BCG generalizes to unseen COBOL systems | Generalization experiment | F1=0.0 for OMP (GT mismatch) | LOW | **NOT_YET_TESTABLE** — GT needs to be rebuilt for OMP |
| C13 | Mutation operators are empirically grounded | docs/failure_taxonomy.md; source_evidence_ref in all MutationRecords | All operators have citations | HIGH | **SAFE_TO_CLAIM** |
| C14 | Provenance is preserved through BCGDiff | SI-02 | Pass | HIGH | **SAFE_TO_CLAIM** |
| C15 | The BCG is cross-artifact (JCL+COBOL) | JCL parser + COBOL parser both ingest into unified IRGraph | Architecture + code review | MEDIUM | **SAFE_TO_CLAIM** — "the BCG architecture supports cross-artifact" (but evaluations used JCL-only) |
| C16 | BCG is novel vs GIST | Prior art audit | GIST has no static evidence, no provenance, no JCL support | HIGH (but "to our knowledge") | **PARTIALLY_SUPPORTED** — hedged with "to our knowledge" |
| C17 | ConfidenceVector is calibrated | Brier score measurement | [RESULT_PENDING] — not yet computed | N/A | **NOT_YET_TESTABLE** |
| C18 | Explanation chain makes risk interpretable | Qualitative assessment | Present in RiskItem for all detected risks | MEDIUM | **PARTIALLY_SUPPORTED** — structural evidence present; user study not done |

---

## Summary Statistics

| Status | Count |
|--------|-------|
| SAFE_TO_CLAIM | 7 |
| PARTIALLY_SUPPORTED | 3 |
| NOT_YET_TESTABLE | 7 |
| UNSUPPORTED | 0 |

---

## High-Priority Claims to Resolve

1. **C8/C9** — Dynamic evidence improvement: requires GnuCOBOL installation + RQ2 re-run
2. **C10/C11** — FPR reduction: requires GnuCOBOL + RQ3 
3. **C12** — Generalization: requires GT rebuild for OMP sources
4. **C7** — BCGDiff F1 gap: should be framed as a finding, not just a limitation
5. **C1** — RQ1 non-circular evaluation: requires Level-3 human annotation

---

## Claims That Are Safe to Publish Now

> 1. "The BCG static extractor produces deterministic, provenance-aware behavioral contracts from JCL artifacts."
> 2. "Provenance survives across the BCG pipeline, enabling complete audit traceability."
> 3. "BCGDiff correctly detects CONTROL_FLOW contract violations introduced by SUPPRESS_RETURN_CODE_CHECK mutations."
> 4. "The mutation framework is empirically grounded: all operators cite documented real-world modernization failures."
> 5. "The static/dynamic reconciliation engine enforces the scientific principle NOT_OBSERVED ≠ CONTRADICTED."
> 6. "HUMAN_VALIDATED and GROUND_TRUTH states are terminal and cannot be demoted by automated analysis."
> 7. "To our knowledge, no prior system jointly represents temporal, resource, and control-flow obligations across JCL and COBOL artifacts in a provenance-aware formal graph."
