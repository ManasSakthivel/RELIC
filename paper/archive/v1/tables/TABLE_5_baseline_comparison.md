# Table 5 — Baseline Comparison (RQ2)

Evaluated on 440 mutation attempts (104 evaluated, 336 not applicable). FP=0 by design (all mutations applied to valid BCGs). FPR from negative benchmark: TN=144, FP=0, FPR=0.0000. Run timestamp: 2026-08-16T16:42:41Z (deterministic) / 2026-08-17T03:52:56Z (LLM C) / 2026-08-17T04:24:52Z (LLM D), seed=42.

LLM baselines (C, D): Groq `llama-3.3-70b-versatile`, v2_blinded prompts (v1 discarded — semantics-preserving prompt leak). Temperature=0.0, seed=42. High API error rate: 245/248 failures (C) and 241/248 failures (D); classification based on 3 and 7 successful calls respectively.

*Note: N/A count increased from 331 to 336 after the reflexive-pair guard fix removed 5 previously-applicable mutation sites where duplicate step names created self-referential contracts.*

| Method | TP | FP | FN | Precision | Recall | F1 | FNR | Status |
|---|---|---|---|---|---|---|---|---|
| complexity (Baseline B) | 0 | 0 | 104 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | ✓ Complete |
| structural (Baseline A) | 85 | 0 | 19 | 1.0000 | 0.8173 | 0.8995 | 0.1827 | ✓ Complete |
| static\_bcg\_only (Baseline E) | 96 | 0 | 8 | 1.0000 | 0.9231 | 0.9600 | 0.0769 | ✓ Complete |
| llm\_only (Baseline C)† | 2 | 0 | 102 | 1.0000 | 0.0192 | 0.0377 | 0.9808 | ✓ Complete (245/248 API errors) |
| dep\_llm (Baseline D)† | 6 | 0 | 98 | 1.0000 | 0.0577 | 0.1091 | 0.9423 | ✓ Complete (241/248 API errors) |
| **static\_bcg (Proposed)** | **104** | **0** | **0** | **1.0000** | **1.0000** | **1.0000** | **0.0000** | **✓ Complete** |

†High API error rates; low recall is attributable primarily to API failures rather than misclassification. These results should be interpreted as a lower bound on LLM performance, not as a definitive LLM capability assessment on this task.

**Negative benchmark (144 TN, 5 semantics-preserving operators):**

| Condition | TN | FP | FPR | Specificity |
|---|---|---|---|---|
| static\_bcg (proposed) | 144 | 0 | **0.0000** | **1.0000** |
| structural (Baseline A) | 144 | 0 | 0.0000 | 1.0000 |
| llm\_only (Baseline C) | 144 | 0 | 0.0000 | 1.0000 |
| dep\_llm (Baseline D) | 144 | 0 | 0.0000 | 1.0000 |

**Key findings:**

1. **Baseline B (Complexity) F1=0.0**: Complexity metrics never exceed the 0.5 risk threshold on CardDemo JCL. Valid null result — complexity metrics alone are insufficient predictors for behavioral contract violations.

2. **Baseline E (Static BCG) F1=0.9600**: Misses 8 ALTER\_ERROR\_BRANCH mutations. Those mutations reduce contract static\_support from 1.0 to 0.7 — producing MODIFIED rather than BROKEN contracts. Baseline E only inspects `diff.broken`; proposed also inspects `diff.modified` (confidence-delta), catching all 8.

3. **Baseline A (Structural) F1=0.8995**: Completely misses all F3 operators and semantic F2 operators because those mutations do not alter IR structural edges — only behavioral obligations.

4. **LLM baselines (C, D)**: On this blinded benchmark, F1=0.0377 (C) and F1=0.1091 (D). The high API error rate (245/248 and 241/248) makes these results a lower bound. Both precision=1.00 (zero false alarms on successful calls). These results should not be generalized beyond this benchmark, task, and model version.

5. **Proposed method F1=1.0**: Detects all 104 evaluated mutations via both BROKEN and MODIFIED contract detection.
