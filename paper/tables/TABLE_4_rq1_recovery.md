# Table 4 — Contract Recovery Performance (RQ1)

**Evaluation type:** INDEPENDENT ORACLE — independently implemented regex-based oracle shares only the JCL specification with the extractor; zero shared code.
**Scope:** TEMPORAL contracts only (33 held-out JCL files from CardDemo test split).
**Oracle source:** `scripts/run_rq1_independent.py`

| Scope | TP | FP | FN | Micro-Precision | Micro-Recall | Micro-F1 |
|---|---|---|---|---|---|---|
| TEMPORAL (independent oracle) | 56 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |

**Macro-F1:** 0.5758  
**95% CI (bootstrap, n=10,000, seed=42):** [0.39, 0.73]  
**Files with FP:** 0 of 33  
**Files with FN:** 0 of 33  
**H1 verdict:** SUPPORTED (threshold: Micro-F1 ≥ 0.70, Precision ≥ 0.75)

**Macro-F1 interpretation:** The macro-F1 is lower than micro-F1 because 17 of 33 held-out files have zero TEMPORAL contracts (single-step files or COBOL-only files). By convention, a file where neither oracle nor system produces any contract scores F1=0.0 (not 1.0). This is not an extraction failure; it is a property of the dataset. On files with at least one contract, performance is perfect.

**Scope limitation:** This evaluation is limited to TEMPORAL contracts. RESOURCE (n=3 in full corpus) and CONTROL\_FLOW (n=23) cannot be validated against an independent oracle without sharing DD/COND= parsing logic. Level-3 human annotation (per `docs/annotation_protocol_final.md`) is required for complete RQ1 coverage.

---
**DEPRECATED result (preserved for audit trail, MUST NOT be cited):**  
The Level-2 DETERMINISTIC GT result (F1=1.00 from extractor vs. its own prior output, 139 TP across all types) is superseded by this independent oracle evaluation. The deprecated result is preserved in `results/rq1/rq1_summary.json` with the explicit warning: `"DO NOT cite F1=1.0 from this experiment as evidence of extraction accuracy in any publication."`
