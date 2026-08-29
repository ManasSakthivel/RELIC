# Mutation N/A Criteria — Formal Documentation

**Document:** `docs/mutation_na_criteria.md`
**Version:** 1.0
**Status:** AUTHORITATIVE — required for RQ2 reproducibility and reviewer response

---

## Overview

The RELIC fault-grounded mutation benchmark attempted **440 mutations** across
8 operators on 55 JCL files from AWS CardDemo. Of these, **336 were marked
`NOT_APPLICABLE` (N/A)** and excluded from the evaluated set.

This document formalises the exact criteria under which a mutation is marked N/A,
provides per-operator counts, and identifies the reviewer risk each criterion
creates. Every criterion was determined **before experiment execution** from the
structural properties of the subject JCL files, not from observed results.

---

## Formal N/A Criteria

A mutation is marked `NOT_APPLICABLE` when applying the operator to the target
artifact would produce a syntactically invalid JCL object or would produce a
mutant that is **semantically identical** to the original (i.e., no behavioral
contract is actually changed). Specific per-operator criteria are defined below.

### Criterion NA-1 — Single-Step Job (REORDER_JOBS, ALTER_STEP_SEQUENCE)

**Applies to:** REORDER_JOBS, ALTER_STEP_SEQUENCE  
**Condition:** The target JCL job or job stream contains only one executable step.  
**Justification:** Reordering or sequence-altering requires at least two steps.
A single-step job cannot be mutated by these operators without creating an
invalid artifact.  
**Count:** Contributes ≈26–27 N/A per operator.

### Criterion NA-2 — No External Job Dependency (REMOVE_JOB_DEPENDENCY)

**Applies to:** REMOVE_JOB_DEPENDENCY  
**Condition:** The target JCL job has no explicit `JCLLIB` or job-stream ordering
dependency on another job in the same batch stream.  
**Justification:** Removing a dependency that does not exist is a no-op.  
**Count:** Contributes ≈27 N/A.

### Criterion NA-3 — Dataset Not Shared Between Steps/Jobs
(REMOVE_DATASET_INIT, CHANGE_DATASET_NAME, ALTER_FILE_DEPENDENCY_ORDER)

**Applies to:** REMOVE_DATASET_INIT, CHANGE_DATASET_NAME, ALTER_FILE_DEPENDENCY_ORDER  
**Condition:** The dataset referenced in the target DD statement is not consumed
by any other step or job in the evaluated corpus. A resource contract
(`PRODUCES_BEFORE_CONSUMES`) exists only when a dataset produced by step A
is consumed by step B. If the dataset has no downstream consumer within the
evaluated scope, mutation of its DD statement does not affect any resource contract.  
**Justification:** These operators are designed to violate resource-dependency
contracts. When no cross-step/cross-job resource dependency exists for the
targeted DD, the mutation is structurally valid but behaviorally neutral —
it changes no behavioral contract.  
**Count:** Contributes ≈54 N/A each (highest N/A rate: only 1 of 55 evaluated per operator).  
**Note:** The high N/A rate for these operators reflects a genuine characteristic
of the CardDemo dataset: most DD statements reference independent output
datasets that are not consumed downstream within the same batch stream.
This is a scope limitation, not a defect in the mutation engine.

### Criterion NA-4 — No COND Parameter on Step
(SUPPRESS_RETURN_CODE_CHECK, ALTER_ERROR_BRANCH)

**Applies to:** SUPPRESS_RETURN_CODE_CHECK, ALTER_ERROR_BRANCH  
**Condition:** The target JCL step does not contain a `COND` parameter
(or equivalent `IF/THEN/ELSE` condition) governing conditional execution.  
**Justification:** These operators mutate control-flow contracts by altering
or removing return-code-dependent execution guards. When no such guard exists
on the target step, no control-flow contract is in scope for mutation.  
**Count:** Contributes ≈47 N/A each.

---

## Per-Operator Summary

| Operator | Attempted | N/A | Evaluated | Primary N/A Criterion |
|----------|-----------|-----|-----------|----------------------|
| REORDER_JOBS | 55 | 26 | 29 | NA-1 (single-step) |
| REMOVE_JOB_DEPENDENCY | 55 | 27 | 28 | NA-2 (no dependency) |
| ALTER_STEP_SEQUENCE | 55 | 27 | 28 | NA-1 (single-step) |
| REMOVE_DATASET_INIT | 55 | 54 | 1 | NA-3 (dataset not shared) |
| CHANGE_DATASET_NAME | 55 | 54 | 1 | NA-3 (dataset not shared) |
| ALTER_FILE_DEPENDENCY_ORDER | 55 | 54 | 1 | NA-3 (dataset not shared) |
| SUPPRESS_RETURN_CODE_CHECK | 55 | 47 | 8 | NA-4 (no COND param) |
| ALTER_ERROR_BRANCH | 55 | 47 | 8 | NA-4 (no COND param) |
| **TOTAL** | **440** | **336** | **104** | |

---

## Proportion Discussion

76.4% of mutations are N/A (336/440). This is high and will attract reviewer
attention. The explanation is:

1. **Dataset characteristics**: CardDemo is a banking demonstration system designed
   for pedagogical purposes. Many of its JCL jobs are standalone batch jobs that
   do not share datasets with other jobs in the same stream. This limits the
   evaluable scope of resource-contract operators.

2. **Evaluation scope**: The N/A designation is not a defect in the BCG system —
   the extractor correctly identifies *when* a contract is present and *when* it
   is not. A mutation that would not change any contract is genuinely not
   applicable to the evaluation of contract detection.

3. **Implications for claim scope**: The RQ2 results (F1=1.000 for BCG) are
   valid for the 104 mutations where a contract violation was introduced.
   The claim **must not** be stated as "BCG detects all mutation types" — it
   must be stated as "BCG detects all evaluated mutation instances" with the
   N/A rate explicitly reported.

4. **Temporal contracts dominate**: The evaluated set is heavily weighted toward
   temporal ordering contracts (REORDER_JOBS, REMOVE_JOB_DEPENDENCY,
   ALTER_STEP_SEQUENCE: 85/104 = 81.7% of evaluated mutations). Resource and
   control-flow operators have extremely limited evaluation coverage (3 and 16
   mutations respectively).

---

## Reviewer Risk Assessment

| Risk | Description | Mitigation |
|------|-------------|------------|
| R1 | "76.4% N/A is cherry-picking" | Criteria pre-defined; structural, not result-driven |
| R2 | "Resource operators essentially not evaluated (1 each)" | Acknowledged as L3 limitation; second subject needed |
| R3 | "F1=1.000 only on TEMPORAL contracts effectively" | Paper must report per-type F1; headline must scope claim |
| R4 | "CardDemo is too simple/pedagogical" | Acknowledge; note second subject system planned |

---

## Action Items

- [x] Formal N/A criteria documented here
- [ ] Paper Section 5 (RQ2) must state N/A count, criteria, and scope limitation
- [ ] Table in Appendix must show per-operator TP/FP/FN/N/A
- [ ] Second subject system must include more inter-job resource dependencies
      to improve coverage of NA-3 operators

---

*Document created: P0 Baseline Freeze phase*
*Authorised by: RELIC Research Program Lead*
