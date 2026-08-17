# Table 3: Contract Taxonomy

Paper 1 scope: TEMPORAL, RESOURCE, CONTROL_FLOW contracts only.
Papers 2–4 will extend to DATA, STATE, and ERROR contracts.

| Type | Predicate | Formal Statement | Example | Detection Method | Ground Truth Level | Paper Scope |
|------|-----------|-----------------|---------|-----------------|:-----------------:|:-----------:|
| TEMPORAL | PRECEDES | `A ≺ B` | STEP01 must execute before STEP02 | JCL step sequential order (MUST_PRECEDE relation from grammar) | 2 (deterministic) | Paper 1 |
| RESOURCE | PRODUCES_BEFORE_CONSUMES | `produces(A,R) ≺ consumes(B,R)` | STEP01 must produce SYNTH.FILE before STEP02 consumes it | DD DISP=NEW/CATLG → PRODUCES; DISP=OLD/SHR → CONSUMES | 2 (deterministic) | Paper 1 |
| CONTROL_FLOW | MUST_NOT_FOLLOW_ON_ERROR | `RC(A) op T → ¬execute(B)` | STEP02 must not execute if STEP01 returns RC > 4 | JCL COND=(rc,operator,stepname) parameter | 2 + 3 (annotation for semantics) | Paper 1 |
| DATA | FIELD_COMPATIBLE | `field(F,W) ∼ field(G,W′)` | ACCT-NUM (PIC 9(11)) must be compatible with receiving field | Copybook PICTURE clause comparison | 3 (expert annotation) | Paper 2 |
| STATE | REQUIRES_INITIALIZATION | `init(S) ≺ use(P,S)` | WS-COUNTER must be initialized before PROCESS-PARA uses it | Working-storage MOVE/INITIALIZE pattern analysis | 3 (expert annotation) | Paper 2 |
| ERROR | MUST_PROPAGATE_ERROR | `err(A) → handle(B)` | AT END condition in READPARA must trigger error path in caller | COBOL ON ERROR / AT END / INVALID KEY clause analysis | 3 (expert annotation) | Paper 2 |

## Ground Truth Levels

| Level | Name | Description |
|-------|------|-------------|
| 1 | Execution Oracle | Highest confidence: behavioral divergence detected by comparing outputs of original and modernized systems |
| 2 | Deterministic Structural Fact | Mechanically verifiable from JCL/COBOL grammar rules without interpretation |
| 3 | Expert Annotation | Human interpretation for implicit or cross-artifact contracts; requires Cohen's κ ≥ 0.70 |
| 4 | Researcher Adjudication | Applied when annotators disagree on Level 3 cases |

## Contract Predicate Semantics (Paper 1)

### PRECEDES (Temporal)

```
∀ valid executions e satisfying preconditions:
  timestamp(completion(A, e)) < timestamp(start(B, e))
```

Scope: the enclosing JCL job stream.
Preconditions: the job stream is eligible for execution.
Exceptions: COND parameters may bypass B regardless of A.

### PRODUCES_BEFORE_CONSUMES (Resource)

```
∀ valid executions e:
  complete(produce(A, R), e) ∧ return_code(A, e) = 0
  →  start(consume(B, R), e) after complete(produce(A, R), e)
```

Scope: a JCL job stream or cross-job dependency.
Note: production success (RC=0) is required; partial production does not satisfy.

### MUST_NOT_FOLLOW_ON_ERROR (Control-flow)

```
∀ executions e, ∀ return events r(A, e):
  cond_satisfied(r(A,e), op, threshold)  →  ¬executed(B, e)
```

Where `cond_satisfied(rc, op, T)` follows JCL COND semantics:
- GT: rc > T → bypass B
- LT: rc < T → bypass B
- EQ: rc = T → bypass B
- NE: rc ≠ T → bypass B
- GE: rc ≥ T → bypass B
- LE: rc ≤ T → bypass B
