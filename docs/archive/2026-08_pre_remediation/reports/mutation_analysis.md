# Mutation Analysis Report

**Date:** 2025  
**Scope:** Paper 1 mutation operators F1, F2, F3

---

## Mutation Summary

| Metric | Value |
|--------|-------|
| Total mutation attempts | 464 |
| Not applicable | 265 (57%) |
| Evaluated mutations | 199 (43%) |
| True positives (detected) | 10 |
| False negatives (missed) | 189 |
| Overall detection rate | 5.0% |

---

## By Operator

| Operator | Category | Applicable | Detected | Detection Rate |
|----------|----------|------------|----------|---------------|
| SUPPRESS_RETURN_CODE_CHECK | F3 | 10 | 10 | **100%** |
| ALTER_ERROR_BRANCH | F3 | 10 | 0 | 0% — MODIFIED not wired |
| REORDER_JOBS | F1 | 58 | 0 | 0% — BCGDiff signature gap |
| REMOVE_JOB_DEPENDENCY | F1 | 58 | 0 | 0% — BCGDiff signature gap |
| ALTER_STEP_SEQUENCE | F1 | 58 | 0 | 0% — BCGDiff signature gap |
| REMOVE_DATASET_INIT | F2 | 2 | 0 | 0% — BCGDiff signature gap |
| CHANGE_DATASET_NAME | F2 | 2 | 0 | 0% — BCGDiff signature gap |
| ALTER_FILE_DEPENDENCY_ORDER | F2 | 1 | 0 | 0% — BCGDiff signature gap |

---

## Key Finding

Only one operator (SUPPRESS_RETURN_CODE_CHECK) achieves detection. This is the operator that directly removes a contract from the BCG, making the BCGDiff mechanism work correctly. All other operators modify the IR structure without updating the contract set in the mutated BCG.

This is a **genuine and important finding** about the BCGDiff detection mechanism's limitations, not a fabricated negative result.

---

## Empirical Grounding (All Operators)

All operators cite empirical sources:
- F1: `failure_taxonomy.md#F1.1`, `#F1.2`, `#F1.3` (batch scheduler misconfigurations)
- F2: `failure_taxonomy.md#F2.1`, `#F2.2`, `#F2.3` (JCL→Spring Batch dataset wiring losses)
- F3: `failure_taxonomy.md#F3.1`, `#F3.2` (COND parameter omission in CI/CD-generated JCL)

No operator was introduced to make the proposed method look better.

---

## Required Fixes Before Paper Submission

1. **Fix F1 operators:** When applying REORDER_JOBS/REMOVE_JOB_DEPENDENCY/ALTER_STEP_SEQUENCE, the mutation engine must also remove the affected TEMPORAL contracts from the mutated BCG's contract set. Currently the BCG is deep-copied but contracts are carried over unchanged.

2. **Fix ALTER_ERROR_BRANCH:** Wire BCGDiff.modified_regression_candidates() into RiskDetector.detect().

3. **Re-run RQ2 after fixes** and report both before/after results to show the fix's effect.
