# Dynamic Evidence Strategy
## LEGACY-CONTRACT — Evidence Normalization, Reconciliation, and Coverage

---

## 1. EVIDENCE SOURCES

The system recognizes four classes of dynamic evidence source:

| Source class | Examples | Extraction method tag | Trust level |
|-------------|----------|----------------------|-------------|
| Instrumented execution | GnuCOBOL execution logs | EXECUTION | High |
| Batch simulation | JCL step simulation scripts | EXECUTION_SIMULATED | Medium |
| Synthetic generation | Statically-derived traces | SYNTHETIC_STATIC | Low |
| Human annotation | Expert trace reconstruction | HUMAN | High |

Evidence source is mandatory provenance. Never mix SYNTHETIC_STATIC evidence into DYNAMICALLY_OBSERVED status.

---

## 2. NORMALIZED EXECUTION EVENT SCHEMA

All evidence sources must normalize to:

```python
@dataclass
class ExecutionEvent:
    event_id: str          # UUID
    timestamp: datetime    # Wall clock or relative epoch
    execution_id: str      # Unique run identifier
    artifact_id: str       # BCG entity reference
    operation: str         # READ, WRITE, CALL, PRODUCE, CONSUME, OPEN, CLOSE, EXECUTE, RETURN
    resource: str | None   # File, dataset, program, or None
    predecessor_events: list[str]   # event_ids observed immediately before
    successor_events: list[str]     # event_ids observed immediately after
    input: dict | None     # Input parameters or file content metadata
    output: dict | None    # Output values or file content metadata
    return_code: int | None
    metadata: dict         # Source-specific metadata
    source_type: str       # EXECUTION | EXECUTION_SIMULATED | SYNTHETIC_STATIC | HUMAN
```

**Schema justification:**
- `execution_id` allows grouping events by run for multi-run analysis
- `predecessor_events` / `successor_events` capture observed ordering directly
- `return_code` captures error conditions
- `source_type` is mandatory provenance field

---

## 3. STATIC/DYNAMIC RECONCILIATION ALGORITHM

For each contract c ∈ C:

```
1. Retrieve static evidence: static_ev = P(c).static_evidence
2. Retrieve matching dynamic events: obs = {d ∈ D | d.artifact_id ∈ {c.subject, c.object}}
3. If obs = ∅:
     Γ(c).validation_state = NOT_OBSERVED
     Γ(c).confidence.dynamic_support = 0.0
   Else:
     Evaluate obs against c.predicate semantics:
     - PRECEDES: Check ∀ pair (e_subj, e_obj) ∈ obs: timestamp(e_subj) < timestamp(e_obj)
     - PRODUCES_BEFORE_CONSUMES: Check produce event precedes consume event for resource
     - MUST_NOT_FOLLOW_ON_ERROR: Check no execution of obj follows subj with return_code > 0
4. If all observations support the contract: outcome = SUPPORTED
   If any observation violates: outcome = CONTRADICTED
   If partial support: outcome = PARTIALLY_SUPPORTED
   If insufficient evidence to determine: outcome = AMBIGUOUS
5. Set Γ(c).validation_state:
     static_candidate + SUPPORTED      → STATIC_DYNAMIC_SUPPORTED
     static_candidate + CONTRADICTED   → STATIC_DYNAMIC_CONFLICT
     static_candidate + NOT_OBSERVED   → STATIC_CANDIDATE (no change)
     static_candidate + AMBIGUOUS      → UNRESOLVED
```

---

## 4. CONFLICT TAXONOMY

When static expectation ≠ dynamic observation:

| Conflict class | Description | Research action |
|---------------|-------------|-----------------|
| STATIC_FALSE_POSITIVE | Static analysis inferred non-existent contract | Report as false positive |
| DYNAMIC_INCOMPLETE | Contract real but execution didn't cover the path | NOT_OBSERVED, not CONTRADICTED |
| HIDDEN_STATE | Contract depends on environment/config not visible | Document as environment-dependent |
| INSTRUMENTATION_LIMIT | Trace capture missed the relevant event | Document in threats to validity |
| PARSER_LIMIT | JCL/COBOL parser missed a structural element | Report as parser gap |

Never resolve a conflict by silently dropping one piece of evidence.

---

## 5. DYNAMIC COVERAGE MODEL

Coverage is measured per execution run and per contract type:

```
coverage(c, run_set) = |{c ∈ C | ∃ d ∈ D_run_set: d covers c}| / |C|
```

The system must report:
- `dynamic_coverage_rate` per contract type per run set
- `unobserved_contracts` list
- `coverage_gap` = contracts with no dynamic evidence

The dynamic coverage experiment (RQ3 support) varies coverage from 10% to 100% and measures precision/recall change.

---

## 6. NOT_OBSERVED ≠ DOES_NOT_EXIST

This is a fundamental scientific principle enforced throughout the codebase.

If a contract has no dynamic evidence:
- ValidationState = NOT_OBSERVED (never = CONTRADICTED)
- The contract remains in the BCG
- Confidence.dynamic_support = 0.0
- The contract is flagged for human review or additional execution

A contract is only CONTRADICTED if at least one execution event explicitly violates its predicate semantics.
