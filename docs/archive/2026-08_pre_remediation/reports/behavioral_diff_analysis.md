# Behavioral Diff Analysis

**Date:** 2025

---

## BCGDiff Structure

The BCGDiff mechanism compares two BCGs:
- **preserved**: contracts present in both with equivalent signature AND confidence (< 5% delta)
- **broken**: contracts in original but not in modernized (regression candidates)
- **added**: contracts in modernized but not in original (new obligations)
- **modified**: same signature, different confidence or validation state

---

## Results from RQ2 Mutation Evaluation

From 199 evaluated mutation instances:

| BCGDiff Category | Count | Detection |
|------------------|-------|-----------|
| broken (SUPPRESS_RETURN_CODE_CHECK) | 10 | ALL detected as risk |
| broken (REORDER_JOBS, etc.) | 0 | 0 detected — mutations don't break contract signatures |
| modified (ALTER_ERROR_BRANCH) | 10 | NOT wired to detector yet |
| preserved | varies | Correctly not flagged as risks |

---

## Key Finding: MODIFIED Contracts Not Used

The `BCGDiff.modified_regression_candidates()` method exists and is tested, but `RiskDetector.detect()` does not process `diff.modified`. This means:

- ALTER_ERROR_BRANCH mutations change contract metadata (RC threshold) but not signature
- These appear in `diff.modified` but are never returned as risk items
- **Fix required:** Wire modified contracts through the risk detector

---

## MODIFIED Category Research Value

The MODIFIED category captures an important class of semantic regression:
> "The contract still exists but its behavioral obligation has weakened"

Examples:
- A COND=(4,GT) changed to COND=(99,GT) — the guard is now much weaker
- A temporal contract's confidence drops below threshold after modernization

This is distinct from a broken contract and should be reported separately in the risk report.

---

## Recommendation

Before paper submission:
1. Wire `BCGDiff.modified_regression_candidates()` into `RiskDetector.detect()`
2. Add a `modified_risk_items` list to `RiskReport`
3. Re-run RQ2 with ALTER_ERROR_BRANCH to verify detection improves
