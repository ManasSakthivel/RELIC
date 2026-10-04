# Error Analysis Report

**Date:** 2025  
**Scope:** All evaluated experiments (RQ1, RQ2, ablation, generalization)

---

## Summary Table

| Error Category | Experiment | Count | Severity | Root Cause |
|----------------|------------|-------|----------|-----------|
| Ground truth circularity | RQ1 | All 139 positives | CRITICAL | GT built by same extractor as evaluated |
| Detection mechanism gap (F1 operators) | RQ2 | 174/189 FN | HIGH | BCGDiff misses structural reordering |
| MODIFIED category unused | RQ2 | 10 FN (ALTER_ERROR_BRANCH) | MEDIUM | RiskDetector not wired to BCGDiff.modified |
| Dynamic evidence unavailable | RQ2, RQ3 | All dynamic conditions | HIGH | GnuCOBOL not installed |
| Sample size insufficient | RQ2 | 199 mutations | HIGH | Too few for statistical comparison |
| Generalization GT mismatch | Generalization | 34 FP | MEDIUM | OMP contracts not in GT positive set |
| RESOURCE underrepresentation | RQ1 | 3/139 positives | MEDIUM | Dataset has few resource-type contracts |

---

## Detailed Error Analysis

### EA-01: Ground Truth Circularity (CRITICAL)

**Category:** Ground truth uncertainty  
**Experiments affected:** RQ1, Ablation  
**Description:** The Level-2 DETERMINISTIC ground truth was constructed by running StaticContractExtractor on 58 JCL files and recording every extracted contract as a positive. Evaluation then runs the same extractor and measures precision/recall.  
**Evidence:** F1=1.0 with zero FP and zero FN  
**Root cause:** The evaluation is tautological — it proves determinism, not correctness  
**Correction required:** Level-3 human annotation of implicit contracts  
**Paper impact:** Must be disclosed prominently in threats to validity; RQ1 headline must be qualified  

---

### EA-02: BCGDiff Detection Gap for F1 Structural Mutations (HIGH)

**Category:** BCG representation limitation  
**Experiments affected:** RQ2 (F1 operators)  
**Operators affected:** REORDER_JOBS, REMOVE_JOB_DEPENDENCY, ALTER_STEP_SEQUENCE  
**Detection rate:** 0/174 applicable mutations (0%)  
**Description:** F1 mutations restructure the IR ordering of steps. TEMPORAL contracts have signatures `(TEMPORAL, subject_id, PRECEDES, object_id)`. When steps are reordered, the mutation engine creates a new IR with swapped step positions, but the original contracts are still stored in the BCG with their original signatures. BCGDiff cannot detect that "A PRECEDES B was valid before and B PRECEDES A is asserted after" unless both contracts are in the system.  
**Root cause:** Mutation operators for F1 modify the IR structure but do not update the contract set in the mutated BCG to reflect the new (broken) ordering.  
**Fix:** F1 mutation operators should:
1. Remove the affected TEMPORAL contracts from the mutated BCG
2. Optionally add reversed-ordering contracts with a "VIOLATED" flag
3. Then BCGDiff will correctly report them as BROKEN  
**Status:** Unfixed in current implementation. Must be fixed before paper submission.  
**Paper impact:** Report as a finding in error analysis; note that SUPPRESS_RETURN_CODE_CHECK works correctly as a control case  

---

### EA-03: BCGDiff.modified Not Wired to RiskDetector (MEDIUM)

**Category:** BCG representation limitation  
**Experiments affected:** RQ2 (ALTER_ERROR_BRANCH)  
**Detection rate:** 0/10 applicable mutations (0%)  
**Description:** ALTER_ERROR_BRANCH changes the RC threshold in a CONTROL_FLOW contract's metadata (from e.g., GT=4 to GT=0). The contract signature `(CONTROL_FLOW, subject, MUST_NOT_FOLLOW_ON_ERROR, object)` is unchanged. BCGDiff.diff() correctly classifies this as a MODIFIED contract (same signature, different confidence/metadata). However, RiskDetector.detect() only processes BCGDiff.broken — it does not iterate over BCGDiff.modified.  
**Fix:** Add a loop in RiskDetector.detect() that processes modified contracts as potential violations when confidence drops significantly  
**Status:** BCGDiff.modified_regression_candidates() exists but is unused  

---

### EA-04: Dynamic Evidence Unavailable (HIGH)

**Category:** Environment dependency  
**Experiments affected:** RQ2 (BCG+dynamic), RQ3 (all)  
**Description:** GnuCOBOL is not installed in the execution environment. All dynamic conditions are BLOCKED.  
**Not a fabricated result:** All blocked conditions correctly report [RESULT_PENDING] rather than estimated values  
**Fix:** `brew install gnucobol` then re-run Subagent C + RQ2/RQ3  

---

### EA-05: Generalization Ground Truth Mismatch (MEDIUM)

**Category:** Ground truth limitation  
**Experiments affected:** Generalization  
**Description:** The 43 OMP COBOL JCL files produce 34 contracts. However, those contracts are not in the Level-2 GT positive set (GT was built from 58 specific source files). The generalization evaluation therefore reports FP=34, precision=0, F1=0 — but this does not mean the extractor is wrong; it means the GT doesn't cover these files.  
**Fix:** Rebuild GT to include OMP COBOL sources in the positive set, or separate GT by dataset and evaluate in-distribution vs out-of-distribution separately  

---

### EA-06: RESOURCE Contract Underrepresentation (MEDIUM)

**Category:** Dataset limitation  
**Experiments affected:** RQ1, Ablation  
**Description:** Only 3 RESOURCE ground truth positives from 1 JCL file (IMSMQCMP.jcl). Most JCL files do not use temporary datasets with both DISP=(NEW,...) and DISP=OLD for the same DSN name within the same file.  
**Impact:** RESOURCE type results (P=1.0, R=1.0) are not statistically meaningful with n=3  
**Paper note:** Report RESOURCE results with raw counts only, not percentages  

---

## Failure Mode Summary by Research Area

### Parser limitations
- JCL parser does not handle GDG (Generation Data Group) base definitions
- JCL COND inheritance (COND on JOB card applying to all steps) not fully parsed
- Multi-volume dataset specifications not fully handled

### Static analysis limitations
- BCGDiff does not detect metadata changes (EA-03)
- F1 structural reordering not detected (EA-02)
- Cross-JCL dependencies (chains of jobs) not captured in single-file analysis

### Dynamic evidence limitations
- GnuCOBOL unavailable (EA-04)
- Even when available: VSAM, ABEND codes, mainframe I/O not representable

### Ground truth limitations
- Level-2 circularity (EA-01)
- OMP mismatch (EA-05)
- RESOURCE underrepresentation (EA-06)
- No Level-3 human annotation completed
