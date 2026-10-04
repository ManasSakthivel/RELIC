# Table 3: Contract Taxonomy

| Type | Formal | Example (natural language) | Evidence Source | Extraction |
|:---|:---|:---|:---|:---|
| TEMPORAL | A ≺ B | "STEP05 must complete before STEP10" | JCL step order | Deterministic |
| RESOURCE | PRODUCES_BEFORE_CONSUMES(A,B) | "STEP05 must produce FILE-X before STEP10 consumes it" | DD names | Deterministic |
| CONTROL_FLOW | MUST_NOT_FOLLOW_ON_ERROR(A,B) | "STEP10 must not execute if STEP05 RC≠0" | COND parameter | Deterministic |
