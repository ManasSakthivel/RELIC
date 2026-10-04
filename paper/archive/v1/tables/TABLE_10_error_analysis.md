# Table 10 — Error Analysis

| Category | N | Representative Example | Root Cause | Scientific Impact |
|---|---|---|---|---|
| N/A mutations (no applicable structure) | 336 / 440 | REMOVE\_DATASET\_INIT on JCL without PRODUCES relation | Operator requires structural prerequisite absent in most JCL | Expected; not a failure. Recorded as NOT\_APPLICABLE. N/A count increased from 331 to 336 after reflexive-pair guard fix. |
| F2 low sample size | 3 evaluated F2 cases | REMOVE\_DATASET\_INIT, CHANGE\_DATASET\_NAME, ALTER\_FILE\_DEPENDENCY\_ORDER each n=1 | Only 1 JCL file (IMSMQCMP.jcl) has both PRODUCES and CONSUMES relations | F2 F1 scores unreliable with n=1; finding is preliminary |
| Baseline B null result | 104 / 104 evaluated | All mutations: complexity metrics never exceed 0.5 threshold | Complexity metrics detect structural volume but not behavioral obligation violations | Valid scientific null result — complexity insufficient for this task |
| Baseline E confidence-delta gap | 8 FN (ALTER\_ERROR\_BRANCH) | Confidence reduced from 1.0→0.7; not classified as BROKEN | `diff.broken`-only inspection misses MODIFIED contracts | Discriminating finding: proposed `diff.modified` catches these |
| LLM high error rate | 245 errors (C), 241 errors (D) | API errors on Groq llama-3.3-70b-versatile | Groq API timeouts / rate limits during batch evaluation of 248 items | LLM results are lower bound; F1=0.038/0.109 reflects successful calls only |
| Dynamic NOT\_OBSERVED | 4 of 61 contracts | JCL files whose steps have no matching trace events | CardDemo COBOL steps requiring DB2/CICS execution environment | Residual; covered coverage experiment confirms these are NOT\_OBSERVED not CONTRADICTED |
| STATIC\_DYNAMIC\_CONFLICT | 1 of 61 contracts | CONTROL\_FLOW contract: step executes despite COND-bypass condition | Candidate: GnuCOBOL vs. z/OS behavioral divergence; or instrumentation gap | Single case; requires z/OS execution to confirm root cause |
| RQ1 oracle scope | TEMPORAL only (56 contracts) | RESOURCE/CONTROL\_FLOW require human annotation | Independent deterministic oracle covers only TEMPORAL | RESOURCE and CONTROL\_FLOW extraction accuracy not independently validated |

**Most impactful findings from error analysis:**
1. The `diff.modified` (confidence-delta) gap in Baseline E explains the full 4pp F1 difference between Baseline E (0.960) and proposed (1.000). This is the key architectural contribution of the paper.
2. LLM error rates indicate an infrastructure constraint in this evaluation environment; the results are published as-is with full transparency about failure counts, and should not be interpreted as a definitive characterization of LLM capability on this class of task.
