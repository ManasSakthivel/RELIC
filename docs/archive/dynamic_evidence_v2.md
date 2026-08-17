# Dynamic Evidence Model v2
## Audited and Strengthened Dynamic Evidence Framework

**Version:** 0.2.0  
**Basis:** Dynamic analysis audit (subagent 3) + formal methods audit (subagent 2)

---

## PART 1: CRITICAL FIXES FROM AUDIT

Three critical issues were identified in v0.1:

### Issue 1: Asymmetric Evidence Misclassification

In `ReconciliationEngine._reconcile_precedes()`, when B has execution events but A does not, the outcome was NOT_OBSERVED. This conflates two distinct scenarios:

- **Scenario A:** A ran but events were missed by instrumentation → NOT_OBSERVED (appropriate)
- **Scenario B:** A never ran and B did → possible contract violation → should be AMBIGUOUS with investigation flag

**Fix:** Separate logic for each asymmetric case (see Part 3).

### Issue 2: No Guard Against Synthetic Trace Contamination

`ReconciliationEngine.reconcile()` did not check `source_type` before processing traces. A SYNTHETIC_STATIC trace could cause a contract to reach `STATIC_DYNAMIC_SUPPORTED` state.

**Fix:** Add `allow_synthetic=False` parameter to reconcile(). When False, raises ValueError on synthetic traces. Implemented as part of scientific integrity tests.

### Issue 3: No Formal Coverage Semantics

The system reported `dynamic_coverage_rate` but had no formal definition of what "coverage" means at different levels of granularity.

**Fix:** Formal coverage model defined in Part 4.

---

## PART 2: EXECUTION ENVIRONMENT EQUIVALENCE MATRIX

GnuCOBOL is not z/OS. This matrix formally characterizes which COBOL behaviors are equivalent for the three Paper 1 contract types. This characterization is required to justify claims made from GnuCOBOL-generated execution evidence.

### For TEMPORAL contracts (A ≺ B):

| Behavior | GnuCOBOL | z/OS | Equivalence | TEMPORAL Risk |
|---|---|---|---|---|
| Program execution sequence | Single-process ordering | JES multi-process | ✓ Equivalent for batch sequential | **LOW** |
| Timestamp precision | Microsecond (wall clock) | SMF records (variable) | ✓ Relative order preserved | **LOW** |
| CALL statement execution | COBOL dynamic linking | Linkage editor, static | ✓ Same semantics | **LOW** |
| Return codes (RC 0-4) | Standard COBOL codes | IBM COBOL codes | ✓ Equivalent for 0,4 | **LOW** |
| Return codes (RC > 4) | Runtime-specific | IBM-specific mappings | ✗ May differ | **MEDIUM** |
| ABEND handling | Runtime exception | z/OS ABEND codes | ✗ Not comparable | **HIGH** |
| STOP RUN | Process termination | Step termination | ✓ Equivalent for observability | **LOW** |

**TEMPORAL contracts conclusion:** GnuCOBOL evidence is **REPRESENTATIVE** for temporal ordering contracts that do not depend on specific return codes > 4. Contracts that depend on z/OS ABEND semantics must be marked `ENVIRONMENT_DEPENDENT`.

### For RESOURCE contracts (produces/consumes):

| Behavior | GnuCOBOL | z/OS | Equivalence | RESOURCE Risk |
|---|---|---|---|---|
| Sequential file OPEN/READ/WRITE | Standard UNIX file ops | z/OS sequential datasets | ✓ **Mostly equivalent** | **LOW** |
| File availability check | File exists on UNIX FS | Dataset allocated via JCL | ✗ Different allocation model | **MEDIUM** |
| VSAM access | Not supported | Native VSAM clusters | ✗ **Not testable** | **CRITICAL** |
| GDG (Generation Data Group) | Not supported | DSN=X.GDG(+1) | ✗ **Not testable** | **HIGH** |
| Dataset locking | UNIX fcntl locks | z/OS ENQ/DEQ | ✗ Different model | **HIGH** |
| COMP-3 field integrity | C-compatible storage | IBM packed decimal | ✗ Edge case differences | **MEDIUM** |

**RESOURCE contracts conclusion:** GnuCOBOL evidence is **REPRESENTATIVE** for sequential file I/O ordering. VSAM-dependent and GDG-dependent resource contracts must be marked `ENVIRONMENT_DEPENDENT`.

### For CONTROL_FLOW contracts (COND parameter):

| Behavior | GnuCOBOL | z/OS | Equivalence | CONTROL_FLOW Risk |
|---|---|---|---|---|
| Return codes 0,4 | Standard | Standard | ✓ Equivalent | **LOW** |
| Return codes 8+ | GnuCOBOL-specific | IBM COBOL-specific | ✗ Different mappings | **HIGH** |
| COND=(n,GT/LT/EQ/NE/GE/LE) | Simulated in test | Native JCL | ✓ If RC semantics match | **MEDIUM** |
| COND=EVEN / COND=ONLY | Simulated | Native JCL | ✓ If simulated correctly | **MEDIUM** |
| CICS interactions | Not available (batch) | CICS transactions | N/A (not in batch) | N/A |
| IMS interactions | Not available (batch) | IMS calls | N/A (not in batch) | N/A |
| ABEND-based branching | Not available | z/OS ABEND codes | ✗ Not testable | **HIGH** |

**CONTROL_FLOW contracts conclusion:** GnuCOBOL evidence is **REPRESENTATIVE** for COND parameters using return codes 0-4. Contracts using higher RC values or ABEND-based conditions must be marked `ENVIRONMENT_DEPENDENT`.

### Summary — Paper 1 Scope

For the three Paper 1 contract types on CardDemo batch programs (no CICS, no IMS, no VSAM, no GDG):

| Contract Type | GnuCOBOL Fidelity | Environment Validity |
|---|---|---|
| TEMPORAL | ~90% equivalent | REPRESENTATIVE |
| RESOURCE (sequential files only) | ~80% equivalent | REPRESENTATIVE |
| CONTROL_FLOW (RC 0-4 only) | ~75% equivalent | REPRESENTATIVE with caveats |

**Disclosure required in paper (Threats to Validity §2.4):**  
All dynamic evidence from this study uses GnuCOBOL execution on Linux. Evidence is labeled `EXECUTION (GnuCOBOL environment)`. For Paper 1's contract types and CardDemo's batch-only programs, GnuCOBOL provides representative behavioral evidence. VSAM-dependent and ABEND-dependent contracts are excluded from dynamic validation or marked `ENVIRONMENT_DEPENDENT`.

---

## PART 3: CORRECTED RECONCILIATION LOGIC

### Asymmetric Evidence Handling

The previous reconciliation logic incorrectly treated three different scenarios identically as NOT_OBSERVED. The corrected logic:

```python
# For TEMPORAL: A ≺ B

if not a_exec and not b_exec:
    → NOT_OBSERVED (neither executed; no evidence)

if a_exec and not b_exec:
    → PARTIALLY_SUPPORTED (A executed but B not observed)
      notes: "A executed but B not observed. Ordering is vacuously satisfied
              (B never ran). Coverage is incomplete; cannot fully validate."
      conflict_class: DYNAMIC_INCOMPLETE

if not a_exec and b_exec:
    → AMBIGUOUS
      notes: "B executed but A not observed. Cannot distinguish: 
              (1) A ran but events missed by instrumentation, 
              (2) B executed before or without A (potential violation).
              Investigation required."
      conflict_class: INSTRUMENTATION_LIMIT

if a_exec and b_exec:
    → compare timestamps → SUPPORTED or CONTRADICTED
```

This correctly captures that "B ran but A didn't" is a different epistemic situation from "neither ran."

### New Reconciliation States (v2)

```python
class ReconciliationOutcome(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_OBSERVED = "NOT_OBSERVED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    AMBIGUOUS = "AMBIGUOUS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # NEW: events at wrong granularity
    ENVIRONMENT_DEPENDENT = "ENVIRONMENT_DEPENDENT"  # NEW: z/OS-specific behavior
    EXECUTION_ERROR = "EXECUTION_ERROR"              # NEW: corrupted trace
```

**INSUFFICIENT_EVIDENCE:** Events for the artifacts exist, but they are at a coarser granularity than the contract requires. Example: JOB_START events exist but no STEP-level events for a step-level temporal contract.

**ENVIRONMENT_DEPENDENT:** Contract may hold on GnuCOBOL but depends on z/OS-specific behavior (VSAM, ABEND codes, high RC values). Dynamic evidence is present but not generalizable.

**EXECUTION_ERROR:** Trace contains ERROR-type events or abnormal termination indicating corrupted capture. Evidence from this trace is unreliable.

---

## PART 4: FORMAL DYNAMIC EVIDENCE COVERAGE MODEL

### Definitions

**Definition 1 — Event Coverage:**
```
EventCoverage(C, T) = 
  |{c ∈ C | ∃ e ∈ ⋃_{t ∈ T} t.events: 
     e.artifact_id ∈ {c.subject_id, c.object_id}}| 
  / |C|
```
Fraction of contracts for which at least one relevant event was observed.

**Definition 2 — Qualified Coverage:**
```
QualifiedCoverage(C, T) =
  |{c ∈ C | reconcile(c, T).outcome ∈ 
     {SUPPORTED, CONTRADICTED, PARTIALLY_SUPPORTED}}| 
  / |C|
```
Fraction of contracts for which sufficient evidence exists to make a determination.

**Definition 3 — Type-Specific Coverage:**
For each τ ∈ {TEMPORAL, RESOURCE, CONTROL_FLOW}:
```
Coverage_τ(C_τ, T) =
  |{c ∈ C_τ | reconcile(c, T).outcome ≠ NOT_OBSERVED}| 
  / |C_τ|
```

**Definition 4 — Coverage Quality Classification:**
```
CoverageQuality(C, T) =
  COMPREHENSIVE   if EventCoverage(C, T) ≥ 0.80
  ADEQUATE        if 0.60 ≤ EventCoverage(C, T) < 0.80
  MINIMAL         if 0.40 ≤ EventCoverage(C, T) < 0.60
  SPARSE          if 0.20 ≤ EventCoverage(C, T) < 0.40
  INSUFFICIENT    if EventCoverage(C, T) < 0.20
```

### Dynamic Coverage Experiment (RQ3)

The coverage experiment varies coverage levels from 10% to 100% by subsampling traces:

```
For each coverage level k ∈ {0.0, 0.10, 0.25, 0.50, 0.75, 1.00}:
  T_k = subsample(T_full, k, seed=42)
  BCG_k = reconcile(BCG_static, T_k)
  metrics_k = evaluate(BCG_k, ground_truth, mutations)
  Record: Coverage_τ(C, T_k) for each τ, FPR_k, F1_k, Precision_k, Recall_k
```

**Research question:** At what coverage level do additional traces provide diminishing returns?

---

## PART 5: NOT_OBSERVED ≠ FALSE — FORMAL PRINCIPLE

This principle is fundamental and must be enforced at all levels.

### Formal Statement

```
∀ c ∈ C, ∀ T (trace set):
  (∀ e ∈ ⋃T: ¬(e is a violation event for c)) 
  ⟹ c.validation_state ≠ STATIC_DYNAMIC_CONFLICT

Equivalently:
  CONTRADICTED requires ∃ e ∈ D: e explicitly violates c's predicate
  NOT_OBSERVED requires only ¬∃ relevant events
```

### Operational Enforcement

1. `ReconciliationEngine.reconcile()` returns `NOT_OBSERVED` only when no relevant events exist — never when events exist but don't support
2. `BCG.add_observation()` does not change validation_state directly
3. Only `ReconciliationEngine._update_contract()` may change validation_state
4. Scientific integrity tests enforce this invariant (see tests/scientific/test_integrity.py)

---

## PART 6: EVIDENCE SOURCE HIERARCHY

```
Confidence ordering (highest to lowest):

GROUND_TRUTH (execution oracle)
  > HUMAN_VALIDATED (expert annotation, κ ≥ 0.70)
  > STATIC_DYNAMIC_SUPPORTED (both static and real execution agree)
  > DYNAMICALLY_OBSERVED (observed in real execution, no static)
  > UNRESOLVED / PARTIALLY_SUPPORTED (mixed or incomplete evidence)
  > STATIC_CANDIDATE (static analysis only, no dynamic validation)
  > NOT_OBSERVED (static candidate with no dynamic evidence)
  > ENVIRONMENT_DEPENDENT (evidence present but non-portable)
  > INSUFFICIENT_EVIDENCE (events exist but wrong granularity)
```

**Key rule:** No position in this hierarchy is reachable from SYNTHETIC_STATIC evidence alone. SYNTHETIC_STATIC can only contribute to contract discovery (STATIC_CANDIDATE), never to validation.
