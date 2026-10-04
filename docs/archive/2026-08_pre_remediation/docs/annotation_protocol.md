# Annotation Protocol
## LEGACY-CONTRACT — Ground-Truth Strategy and Human Annotation

---

## GROUND-TRUTH HIERARCHY

### Level 1 — Execution Oracle (Highest confidence)

When both original and modernized (mutated) systems are executable:
1. Run original: collect execution trace T_orig
2. Apply mutation: produce modernized system
3. Run modernized: collect execution trace T_mod
4. Compare: divergence in ordering, resource access, return codes = objective behavioral difference

This is the strongest ground-truth source. Every mutation-benchmark item should have an execution oracle result where possible.

### Level 2 — Deterministic Structural Facts

Facts mechanically verifiable from artifact grammar:
- JCL: EXEC PGM= declares which program runs in which step
- JCL: DD DSN= declares file dependencies
- COBOL: CALL 'X' declares a program invocation
- COBOL: READ/WRITE file declarations
- Copybook: PICTURE clause field widths

These require no human judgment. They are extracted deterministically and tagged `extraction_method = DETERMINISTIC`.

### Level 3 — Expert Annotation

Contracts that require semantic interpretation:
- Implicit ordering obligations not explicit in COND parameters
- Behavioral contracts inferred from naming conventions
- Semantic relationships across artifacts

**Process:**
1. System generates candidate contracts (STATIC_CANDIDATE)
2. Filter: remove deterministically verified contracts
3. Sample 100 representative candidates stratified by contract type
4. 2 expert annotators per item (independent)
5. Annotation form captures: valid/invalid, contract type, confidence, evidence
6. Calculate inter-annotator agreement (Cohen's κ)
7. For κ < 0.6: adjudication by third researcher
8. Final: HUMAN_VALIDATED status

### Level 4 — Researcher Adjudication

Used only when expert annotators disagree (< 60% agreement on an item). Third researcher with mainframe background reviews evidence and makes final call.

---

## HUMAN ANNOTATION EFFICIENCY

Humans should NOT annotate deterministically verifiable contracts. Use humans only for:
- Implicit contracts (no direct syntactic evidence)
- Cross-artifact contracts spanning JCL + COBOL
- Ambiguous cases where static evidence is incomplete

Target annotation load: ≤ 150 items per annotator for Paper 1.

---

## ANNOTATION FORM SCHEMA

```json
{
  "contract_id": "uuid",
  "artifact": "path/to/artifact",
  "location": "line:col",
  "contract_type": "TEMPORAL|RESOURCE|CONTROL_FLOW",
  "contract_statement": "natural language description",
  "formal_statement": "formal notation or null",
  "evidence_shown": ["evidence item 1", "evidence item 2"],
  "annotator_id": "anonymized",
  "valid": true | false | "uncertain",
  "confidence": 1 | 2 | 3,
  "notes": "free text",
  "timestamp": "ISO8601"
}
```

---

## INTER-ANNOTATOR AGREEMENT MEASUREMENT

For categorical judgments (valid/invalid):
- Cohen's κ for 2 annotators
- Fleiss' κ for 3+ annotators
- Target: κ ≥ 0.7 (substantial agreement)
- Report κ per contract type

If κ < 0.6 for a contract type, that type's human-annotated contracts are flagged as LOW_AGREEMENT and reported separately in error analysis.

---

## BENCHMARK SCHEMA

Each benchmark item:

```json
{
  "contract_id": "B-001",
  "artifact": "datasets/carddemo/jcl/CBACT01C.jcl",
  "location": "step:STEP010:cond",
  "contract_type": "TEMPORAL",
  "contract_statement": "CBACT01C must complete before CBACT02C consumes ACCTFILE",
  "evidence": ["DD DSN=ACCTFILE in CBACT02C step", "ACCTFILE produced in CBACT01C step"],
  "ground_truth_source": "DETERMINISTIC",
  "ground_truth": true
}
```
