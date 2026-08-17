# BCG Formalization v2
## Audited and Strengthened Formal Model

**Version:** 0.2.0  
**Status:** Revised after formal methods audit  
**Basis:** Audit findings from subagents 2 (formal methods), 3 (dynamic analysis), 6 (SE research)

---

## PART 1: SYNTHESIS OF AUDIT FINDINGS

The formal methods audit identified seven implementation problems with the current BCG:

1. **Confidence weights sum to 1.10, not 1.0** — the aggregate() function uses a clamping hack
2. **ValidationState transition machine is implicit and scattered** — no defined diagram
3. **Contract referential integrity unenforced** — a contract can reference non-existent entity_ids
4. **BCGDiff uses entity IDs that are artifact-path-dependent** — semantic behavioral diff is broken by refactoring
5. **Γ component lacks evidence cardinality** — how many events support or contradict each contract is not stored
6. **HUMAN_VALIDATED contracts could be overwritten by CONTRADICTED** — this is a scientific integrity bug (fixed in v0.1 audit)
7. **No formal contract semantics** — predicate semantics are defined operationally in code, not specified

This document presents the v2 formalization addressing these issues.

---

## PART 2: REVISED FORMAL MODEL

### BCG Definition (v2)

```
BCG = (V, E, C, P, D, Γ)
```

**V — Entity Set**
```
V ⊆ Entity
Entity = (
  entity_id : Identifier,          -- deterministic: SHA256(artifact_path ∥ type ∥ name)[0:16]
  entity_type : EntityType,         -- JOB | STEP | DATASET | FILE | PROGRAM | RECORD | FIELD | ...
  artifact_path : Path,             -- source artifact
  name : string,                    -- human-readable name
  location : SourceLocation | ⊥,   -- optional line:col
  attributes : Map[string, Value]   -- type-specific metadata
)
EntityType = {JOB, STEP, DATASET, FILE, RECORD, FIELD, PROGRAM, PARAGRAPH, SECTION, COPYBOOK, JCL_DD, JCL_PROC}
```

**Known limitation:** `entity_id = SHA256(artifact_path ∥ type ∥ name)` is path-dependent. If a program is moved to a different file path during modernization, its entity_id changes even if its behavioral role is unchanged. BCGDiff may report false-positive contract breakage for structurally equivalent but path-different systems. See Section 4.1 for threat characterization.

**E — Structural Relation Set**
```
E ⊆ Entity × RelationType × Entity × ℝ × Map
Each e = (source, type, target, confidence, attributes)
where confidence ∈ [0,1], confidence=1.0 for deterministic structural facts

RelationType = {CALLS, PERFORMS, READS, WRITES, PRODUCES, CONSUMES, DEFINES, MAPS_TO,
                TRANSFORMS, DEPENDS_ON, REQUIRES_STATE, ESTABLISHES_STATE, MUST_PRECEDE,
                MUST_FOLLOW, PROPAGATES_ERROR, USES_RESOURCE, INVALIDATES,
                OBSERVED_BEFORE, OBSERVED_AFTER, CONTAINS, REFERENCES, COPIES}
```

**C — Behavioral Contract Set**
```
C ⊆ Contract
Contract = (
  contract_id : UUID,
  contract_type : ContractType,
  subject_id : Identifier,          -- references entity in V
  predicate : ContractPredicate,
  object_id : Identifier,           -- references entity in V
  scope : string,                   -- execution context where contract applies
  preconditions : list[Condition],  -- conditions under which contract holds
  formal_statement : string | ⊥,   -- optional formal notation
  natural_language : string,        -- required human-readable statement
  provenance_id : UUID              -- references record in P
)
ContractType = {TEMPORAL, RESOURCE, CONTROL_FLOW, DATA, STATE, ERROR}
ContractPredicate = {PRECEDES, PRODUCES_BEFORE_CONSUMES, MUST_NOT_FOLLOW_ON_ERROR,
                     REQUIRES_INITIALIZATION, FIELD_COMPATIBLE, MUST_PRECEDE_FOR_RESOURCE}
```

**Referential Integrity Invariant (NEW in v2):**
```
∀ c ∈ C: c.subject_id ∈ dom(V) ∧ c.object_id ∈ dom(V)
```
This must be enforced at contract insertion time. BCG.add_contract() must validate both entity IDs before inserting.

**P — Provenance Map**
```
P : C → ProvenanceRecord
ProvenanceRecord = (
  source_artifact : Path,
  source_location : string,
  static_evidence : list[EvidenceItem],
  dynamic_evidence : list[EvidenceItem],
  extraction_method : ExtractionMethod,
  model : string | ⊥,
  prompt_version : string | ⊥,
  timestamp : datetime
)
EvidenceItem = (
  evidence_id : UUID,
  evidence_type : string,
  source_artifact : Path,
  source_location : string,
  extraction_method : ExtractionMethod,
  content : string,
  formal_content : string | ⊥,
  timestamp : datetime,
  llm_model : string | ⊥,
  llm_prompt_version : string | ⊥,
  llm_temperature : float | ⊥
)
ExtractionMethod = {DETERMINISTIC, LLM, HUMAN, EXECUTION, EXECUTION_SIMULATED, SYNTHETIC_STATIC, COMBINED}
```

**D — Dynamic Observation Set**
```
D ⊆ ExecutionEvent
ExecutionEvent = (
  event_id : UUID,
  timestamp : datetime,
  execution_id : string,
  artifact_id : Identifier,          -- references entity in V (may be ⊥ if unlinked)
  operation : OperationType,
  resource : string | ⊥,
  predecessor_events : list[UUID],
  successor_events : list[UUID],
  input_data : Value | ⊥,
  output_data : Value | ⊥,
  return_code : int | ⊥,             -- ⊥ means NOT CAPTURED, not zero
  source_type : EventSourceType,     -- EXECUTION | EXECUTION_SIMULATED | SYNTHETIC_STATIC | HUMAN
  metadata : Map[string, Value]
)
EventSourceType = {EXECUTION, EXECUTION_SIMULATED, SYNTHETIC_STATIC, HUMAN}
```

**Scientific constraint on D:**
```
∀ e ∈ D: e.return_code = ⊥ ⟹ "return code was not captured" (not "return code was zero")
∀ e ∈ D: e.source_type = SYNTHETIC_STATIC ⟹ e may NOT update ValidationState to STATIC_DYNAMIC_SUPPORTED
```

**Γ — Validation Metadata Map (STRENGTHENED in v2)**
```
Γ : C → ValidationMetadata
ValidationMetadata = (
  validation_state : ValidationState,    -- current state
  confidence : ConfidenceVector,         -- evidence strength
  evidence_cardinality : EvidenceCount,  -- NEW in v2: counts of supporting/violating events
  coverage_quality : CoverageQuality,    -- NEW in v2: quality of dynamic coverage
  environment_validity : EnvironmentValidity  -- NEW in v2: GnuCOBOL/z/OS equivalence
)

EvidenceCount = (             -- NEW: cardinality of evidence observations
  supporting_events : ℕ,     -- number of dynamic events supporting the contract
  violating_events : ℕ,      -- number of dynamic events contradicting the contract
  runs_observed : ℕ,         -- number of distinct execution runs with relevant events
  runs_supporting : ℕ        -- number of runs where contract was satisfied
)

CoverageQuality = COMPREHENSIVE | ADEQUATE | MINIMAL | SPARSE | INSUFFICIENT
EnvironmentValidity = PORTABLE | REPRESENTATIVE | RISKY | INVALID | UNKNOWN
```

---

## PART 3: VALIDATION STATE MACHINE (FORMALIZED in v2)

The ValidationState machine was implicit in v0.1. This section formalizes all transitions.

### States

```
ValidationState = {
  STATIC_CANDIDATE,          -- inferred from static analysis; not yet validated
  DYNAMICALLY_OBSERVED,      -- observed in execution; not statically extracted
  STATIC_DYNAMIC_SUPPORTED,  -- static + dynamic evidence agree
  STATIC_DYNAMIC_CONFLICT,   -- static and dynamic evidence contradict each other
  HUMAN_VALIDATED,           -- expert annotator confirmed
  GROUND_TRUTH,              -- deterministic or execution-oracle verified
  UNRESOLVED,                -- ambiguous; needs investigation
  NOT_OBSERVED,              -- no dynamic evidence (≠ CONTRADICTED)
  INSUFFICIENT_EVIDENCE,     -- NEW: evidence exists but wrong granularity
  ENVIRONMENT_DEPENDENT      -- NEW: valid on GnuCOBOL but may not hold on z/OS
}
```

### Transition Table

| From State | Trigger | To State | Condition |
|---|---|---|---|
| STATIC_CANDIDATE | dynamic SUPPORTED | STATIC_DYNAMIC_SUPPORTED | source_type ≠ SYNTHETIC_STATIC |
| STATIC_CANDIDATE | dynamic CONTRADICTED | STATIC_DYNAMIC_CONFLICT | source_type ≠ SYNTHETIC_STATIC |
| STATIC_CANDIDATE | dynamic NOT_OBSERVED | NOT_OBSERVED | no relevant events |
| STATIC_CANDIDATE | dynamic PARTIALLY_SUPPORTED | UNRESOLVED | |
| STATIC_CANDIDATE | dynamic AMBIGUOUS | UNRESOLVED | |
| STATIC_CANDIDATE | dynamic INSUFFICIENT_EVIDENCE | INSUFFICIENT_EVIDENCE | granularity mismatch |
| STATIC_CANDIDATE | dynamic ENVIRONMENT_DEPENDENT | ENVIRONMENT_DEPENDENT | z/OS-specific feature |
| STATIC_CANDIDATE | human annotation VALID | HUMAN_VALIDATED | κ ≥ 0.70 required |
| STATIC_CANDIDATE | execution oracle | GROUND_TRUTH | Level-1 ground truth |
| NOT_OBSERVED | new traces provided | see STATIC_CANDIDATE transitions | re-evaluated |
| HUMAN_VALIDATED | dynamic CONTRADICTED | HUMAN_VALIDATED + metadata note | terminal; contradiction logged but state preserved |
| GROUND_TRUTH | any | GROUND_TRUTH | terminal; ground truth is immutable |

### Critical Invariants

**I1 (NOT_OBSERVED ≠ CONTRADICTED):**
```
∀ c ∈ C: c.validation_state = NOT_OBSERVED ⟹
  ¬∃ e ∈ D: e contradicts c's predicate semantics
  (i.e., the state reflects absence of evidence, not contrary evidence)
```

**I2 (Synthetic evidence cannot promote):**
```
∀ c ∈ C, ∀ e ∈ D:
  (e.source_type = SYNTHETIC_STATIC ∧ e supports c)
  ⟹ c.validation_state ≠ STATIC_DYNAMIC_SUPPORTED
```

**I3 (Ground truth is terminal):**
```
∀ c ∈ C: c.validation_state = GROUND_TRUTH ⟹
  no reconciliation event changes c.validation_state
```

**I4 (Referential integrity):**
```
∀ c ∈ C: c.subject_id ∈ dom(V) ∧ c.object_id ∈ dom(V)
```

---

## PART 4: CONFIDENCE MODEL (CORRECTED in v2)

### Problem with v0.1

The v0.1 confidence weights summed to 1.10, not 1.0:
```
static_support: 0.25
dynamic_support: 0.30
cross_artifact_support: 0.15
provenance_quality: 0.10
human_validation: 0.20
execution_frequency: 0.10
Sum = 1.10  ← INCORRECT
```

### Corrected weights (v2)

```yaml
# config/confidence_weights.yaml (v2)
weights:
  static_support: 0.25
  dynamic_support: 0.30
  cross_artifact_support: 0.10   # reduced from 0.15
  provenance_quality: 0.10
  human_validation: 0.20
  execution_frequency: 0.05      # reduced from 0.10
  # Sum = 1.00 ✓
```

### Aggregate formula (v2)

```
aggregate(cv, w) = (
    w.static_support        × cv.static_support
  + w.dynamic_support       × cv.dynamic_support
  + w.cross_artifact        × cv.cross_artifact_support
  + w.provenance_quality    × cv.provenance_quality
  + w.human_validation      × cv.human_validation
  + w.execution_frequency   × cv.execution_frequency
) × (1 − cv.ambiguity_penalty)

where sum(w) = 1.00
and aggregate(cv, w) ∈ [0, 1]  -- guaranteed by construction if all cv dimensions ∈ [0,1]
```

**Scientific integrity note:** `aggregate(cv, w)` is a normalized evidence-strength score, NOT a probability. It must never be interpreted as P(contract is valid). Calibration study required before probabilistic interpretation is possible.

### Monotonicity property

```
∀ cv₁, cv₂:
  (∀ dim: cv₁.dim ≥ cv₂.dim) ⟹ aggregate(cv₁, w) ≥ aggregate(cv₂, w)
```
This is trivially satisfied by the weighted-sum formula. More evidence never decreases the score.

---

## PART 5: CONTRACT SEMANTICS (LIGHTWEIGHT FORMAL DEFINITION)

Rather than full LTL, we use a restricted predicate language sufficient for the three Paper 1 contract types.

### TEMPORAL: A ≺ B

**Informal:** In every valid execution satisfying scope and preconditions, entity A's execution-relevant events must all precede entity B's execution-relevant events in timestamp ordering.

**Formal:**
```
TEMPORAL(A, B, scope, precond) is satisfied by trace T iff:
  applicable(scope, T) ∧ satisfied(precond, T) ⟹
  ∀ e_A ∈ relevant_events(A, T), ∀ e_B ∈ relevant_events(B, T):
    timestamp(e_A) < timestamp(e_B)

where:
  relevant_events(X, T) = {e ∈ T | e.artifact_id = X.entity_id 
                                    ∧ e.operation ∈ {EXECUTE, STEP_START, JOB_START}}
  applicable(scope, T) = the execution context in T falls within scope
  satisfied(precond, T) = all preconditions are met in T
```

**Violation condition:**
```
TEMPORAL(A, B) is VIOLATED in trace T iff:
  ∃ e_A ∈ relevant_events(A, T), ∃ e_B ∈ relevant_events(B, T):
    timestamp(e_B) ≤ timestamp(e_A)
```

**NOT_OBSERVED condition:**
```
TEMPORAL(A, B) is NOT_OBSERVED in trace T iff:
  relevant_events(A, T) = ∅ ∨ relevant_events(B, T) = ∅
  (absence of evidence, NOT evidence of absence)
```

### RESOURCE: produces(A, R) ≺ consumes(B, R)

```
RESOURCE(A, B, R) is satisfied by trace T iff:
  ∃ e_prod ∈ T: e_prod.artifact_id = A.entity_id
               ∧ e_prod.operation ∈ {PRODUCE, WRITE, JOB_END}
               ∧ e_prod.resource = R
  ∧ ∃ e_cons ∈ T: e_cons.artifact_id = B.entity_id
               ∧ e_cons.operation ∈ {CONSUME, READ, OPEN}
               ∧ e_cons.resource = R
  ∧ timestamp(e_prod) < timestamp(e_cons)
```

**Violation:** Consumer event precedes producer event for resource R.

### CONTROL_FLOW: RC(A) OP threshold → ¬execute(B)

```
CONTROL_FLOW(A, B, operator, threshold) is satisfied by trace T iff:
  ∀ e_ret ∈ T: (e_ret.artifact_id = A.entity_id
               ∧ e_ret.operation ∈ {RETURN, STEP_END}
               ∧ e_ret.return_code ≠ ⊥
               ∧ eval(e_ret.return_code, operator, threshold) = true)
  ⟹ ¬∃ e_exec ∈ T: e_exec.artifact_id = B.entity_id
                    ∧ e_exec.operation ∈ {EXECUTE, STEP_START}
                    ∧ timestamp(e_exec) > timestamp(e_ret)

where eval(rc, op, t) = (op = "GT" ∧ rc > t) ∨ (op = "LT" ∧ rc < t) ∨ ...
```

**NOT_OBSERVED for CONTROL_FLOW:** Error condition never triggered in observed traces. This is expected in happy-path testing; explicitly not a violation.

---

## PART 6: BCG INVARIANTS (COMPLETE LIST)

```
I1: ∀ c ∈ C: c.subject_id ∈ dom(V) ∧ c.object_id ∈ dom(V)
    [Referential integrity]

I2: ∀ c ∈ C: P(c) ≠ ⊥
    [Every contract has provenance]

I3: ∀ c ∈ C: Γ(c) ≠ ⊥
    [Every contract has validation metadata]

I4: ∀ e ∈ D: e.source_type ≠ SYNTHETIC_STATIC →
      reconciliation may use e as real evidence
    ∀ e ∈ D: e.source_type = SYNTHETIC_STATIC →
      reconciliation flags e as degraded; cannot produce STATIC_DYNAMIC_SUPPORTED
    [Synthetic trace non-contamination]

I5: ∀ c ∈ C: Γ(c).validation_state = NOT_OBSERVED →
      ¬(∃ e ∈ D: e is a violation event for c)
    [NOT_OBSERVED ≠ CONTRADICTED]

I6: ∀ c ∈ C: Γ(c).validation_state ∈ {GROUND_TRUTH, HUMAN_VALIDATED} →
      no reconciliation event changes validation_state
    [Terminal states are immutable]

I7: sum(confidence_weights) = 1.0
    [Weight normalization]

I8: ∀ c ∈ C: Γ(c).confidence.aggregate() ∈ [0, 1]
    [Confidence is bounded]
```

---

## PART 7: BEHAVIORAL DIFF SEMANTICS (v2)

### Contract Signature

```
signature(c) = (c.contract_type, c.subject_id, c.predicate, c.object_id)
```

**Known issue:** Subject_id and object_id are path-dependent (see Part 2). For Paper 1 (CardDemo with stable paths), this is acceptable.

### BCGDiff Categories (EXTENDED in v2)

```
BCGDiff = (preserved, broken, added, modified)

preserved: {c ∈ C_orig | signature(c) ∈ signatures(C_mod)
                         ∧ equiv(c, counterpart(c, C_mod))}

broken: {c ∈ C_orig | signature(c) ∉ signatures(C_mod)}

added: {c ∈ C_mod | signature(c) ∉ signatures(C_orig)}

modified: {(c₁, c₂) | c₁ ∈ C_orig, c₂ ∈ C_mod,
                       signature(c₁) = signature(c₂),
                       ¬equiv(c₁, c₂)}

where:
  equiv(c₁, c₂) = (c₁.scope = c₂.scope 
                  ∧ c₁.preconditions ≅ c₂.preconditions
                  ∧ |Γ(c₁).confidence.aggregate() - Γ(c₂).confidence.aggregate()| < ε)
```

**Semantic regression classification:**
```
semantic_regression_candidates = {c ∈ broken | c.is_validated()}
potential_regressions = {c ∈ broken | Γ(c).confidence.aggregate() ≥ confidence_threshold}
unvalidated_breaks = {c ∈ broken | c.validation_state = STATIC_CANDIDATE}
```

Only `semantic_regression_candidates` (validated, broken contracts) should be reported as high-confidence regressions. `unvalidated_breaks` should be flagged as lower-confidence candidates.

---

## PART 8: LIMITATIONS OF THE FORMALIZATION

1. **Path-dependent entity IDs** — semantic behavioral equivalence across renamed artifacts is not captured. Future work: semantic canonicalization via entity role mapping.

2. **Informal preconditions** — preconditions are currently stored as strings, not as formal predicates. This limits automated reasoning over contract scopes.

3. **No contract lattice** — the formalization does not define a partial order on contracts (e.g., whether one contract implies another). Future work: contract subsumption relation.

4. **No formal specification of "sufficient evidence"** — CoverageQuality thresholds (COMPREHENSIVE/ADEQUATE/MINIMAL) are defined heuristically, not derived from formal information-theoretic criteria.

5. **Confidence is not probability** — until a calibration study is conducted, aggregate confidence cannot be interpreted as P(contract is valid).

6. **MODIFIED contract semantics** — the equivalence function `equiv(c₁, c₂)` uses a simple threshold comparison; a richer semantic equivalence notion would be needed for complex behavioral modifications.
