# Table 3 — Contract Taxonomy (Paper 1 Scope)

| Type | Formal Notation | Natural Language Example | Evidence Source | Extraction Method |
|---|---|---|---|---|
| TEMPORAL | A ≺ B | "STEP05 must complete before STEP10 begins" | JCL step order (sequential stmt ordering) | Deterministic |
| RESOURCE | PRODUCES\_BEFORE\_CONSUMES(A, B) | "STEP05 must produce FILE-X before STEP10 consumes it" | JCL DD name producer/consumer pairs | Deterministic |
| CONTROL\_FLOW | MUST\_NOT\_FOLLOW\_ON\_ERROR(A, B, rc) | "STEP10 must not execute if STEP05 returns RC≠0" | JCL COND parameter | Deterministic |

**Note:** All three contract types are extracted deterministically from JCL structural features. No LLM inference is used for contract extraction in Paper 1. Future work (Paper 2) extends to COBOL-level data and state contracts requiring cross-artifact analysis.
