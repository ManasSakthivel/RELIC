# Dynamic Validity Final Report

**Date:** 2025

---

## Status

Dynamic evidence is **unavailable** in this experimental run. GnuCOBOL is not installed. All traces in `traces/dev/` are labeled `SYNTHETIC_STATIC` and are prohibited from promoting contracts.

---

## What Was Tested

The reconciliation engine was tested extensively in the test suite:
- SI-01: SYNTHETIC_STATIC cannot upgrade validation state
- SI-06: NOT_OBSERVED ≠ CONTRADICTED (6 contract types × 3 subtests = 18 tests)
- SI-07: HUMAN_VALIDATED protected from contradiction
- SI-11: return_code=None treated as NOT_OBSERVED not RC=0
- SI-12: GROUND_TRUTH never downgraded

All 48 scientific integrity tests pass.

---

## Reconciliation Outcomes Available in Production

When real execution traces are available, the reconciliation engine will produce:

| Outcome | Meaning | Promotion |
|---------|---------|-----------|
| SUPPORTED | Dynamic observations consistent with contract | → STATIC_DYNAMIC_SUPPORTED |
| CONTRADICTED | Dynamic observation violates contract | → STATIC_DYNAMIC_CONFLICT |
| NOT_OBSERVED | No execution evidence found | → NOT_OBSERVED |
| PARTIALLY_SUPPORTED | Some events support but coverage incomplete | → UNRESOLVED |
| AMBIGUOUS | Insufficient evidence to determine | → UNRESOLVED |
| INSUFFICIENT_EVIDENCE | Too few events to evaluate | → UNRESOLVED |
| ENVIRONMENT_DEPENDENT | Result depends on external state | → UNRESOLVED |
| EXECUTION_ERROR | Instrumentation fault | → UNRESOLVED |

---

## Expected Research Finding (Hypothesis Not Yet Tested)

H3 predicts that with ≥50% execution coverage, the BCG+dynamic condition will reduce FPR by ≥15pp compared to static-only.

**This cannot be confirmed or denied without real traces.** The report [RESULT_PENDING].

---

## Conflict Taxonomy (Available but Not Triggered)

The engine distinguishes conflict causes:
- STATIC_FALSE_POSITIVE: inferred contract contradicted by execution
- DYNAMIC_INCOMPLETE: path not covered in traces
- HIDDEN_STATE: environment dependency
- INSTRUMENTATION_LIMIT: trace capture missed event
- PARSER_LIMIT: static parser missed structural element
- INSUFFICIENT_EVENTS: too few events
- EXECUTION_FAULT: instrumentation error

These classes will be populated when GnuCOBOL traces are available.
