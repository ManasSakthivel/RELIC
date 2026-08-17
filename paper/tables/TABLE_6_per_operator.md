# Table 6 — Per-Operator Detection Results (RQ2)

Run timestamp: 2026-08-16T16:42:41Z, seed=42. N Evaluated = mutations where operator was applicable; N Not Applicable = operator had no valid application site in that JCL file.

*Note: Overall totals updated after reflexive-pair guard fix reduced applicable mutations from 109→104 and N/A from 331→336.*

| Operator | Category | BCG F1 | Struct F1 | Complexity F1 | StaticBCG-E F1 | N Eval | N N/A |
|---|---|---|---|---|---|---|---|
| REORDER\_JOBS | F1 (ordering) | 1.0000 | 0.9825 | 0.0000 | 1.0000 | 29 | 26 |
| REMOVE\_JOB\_DEPENDENCY | F1 (ordering) | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 28 | 27 |
| ALTER\_STEP\_SEQUENCE | F1 (ordering) | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 28 | 27 |
| REMOVE\_DATASET\_INIT | F2 (resource) | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1 | 54 |
| **CHANGE\_DATASET\_NAME** | F2 (resource) | **1.0000** | **0.0000** | **0.0000** | **1.0000** | 1 | 54 |
| **ALTER\_FILE\_DEPENDENCY\_ORDER** | F2 (resource) | **1.0000** | **0.0000** | **0.0000** | **1.0000** | 1 | 54 |
| **SUPPRESS\_RETURN\_CODE\_CHECK** | F3 (RC prop.) | **1.0000** | **0.0000** | **0.0000** | **1.0000** | 8 | 47 |
| **ALTER\_ERROR\_BRANCH** | F3 (RC prop.) | **1.0000** | **0.0000** | **0.0000** | **0.0000** | 8 | 47 |
| **Overall** | | **1.0000** | **0.8995** | **0.0000** | **0.9600** | **104** | **336** |

Bold rows highlight operators where Baseline A (structural) and/or Baseline E (static BCG) score zero.

**ALTER\_ERROR\_BRANCH is the critical discriminating operator:**
- Baseline E F1=0.0 on this operator: the mutation reduces static\_support confidence (1.0→0.7) without removing the contract from the BCG — the contract becomes MODIFIED, not BROKEN. Baseline E only detects BROKEN contracts.
- Proposed method F1=1.0: the RiskDetector also processes `diff.modified` entries, flagging contracts with reduced confidence as risk items.

**Complexity (Baseline B) F1=0.0 across all operators:**
- The pre-specified threshold (0.5) and normalization strategy are never triggered by CardDemo JCL complexity scores. This is not a bug; it is a valid empirical finding that complexity metrics are a poor mutation-detection signal for this benchmark.

**Structural (Baseline A) failure operators:**
- CHANGE\_DATASET\_NAME, ALTER\_FILE\_DEPENDENCY\_ORDER: rename a dataset — no IR edge is added or removed, so structural diff is empty.
- SUPPRESS\_RETURN\_CODE\_CHECK, ALTER\_ERROR\_BRANCH: modify RC-conditional control flow — modeled as CONTROL\_FLOW contracts in BCG, invisible to structural edge analysis.
