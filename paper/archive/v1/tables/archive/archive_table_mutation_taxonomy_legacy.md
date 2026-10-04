# Table 7: Mutation Taxonomy

Mutation operators derived exclusively from documented real-world modernization failures.
All sources were collected and the taxonomy was finalized BEFORE mutation operators
were implemented, to prevent circular evaluation design.

## Methodology

Sources searched:
- AWS Mainframe Modernization official documentation (2022)
- GitHub: aws-mainframe-modernization-carddemo issue tracker
- IBM COBOL Migration Guide (2021)
- Stack Overflow tagged [jcl][cobol][mainframe][migration]
- Knorr (2019): batch-to-cloud migration postmortem
- Gula (2020): JCL ordering regression postmortem
- Comella-Dorda et al. (2000): CMU SEI survey
- Ulrich and Newcomb (2010): Chapter 9 case studies

## Taxonomy

| ID | Category | Operator | Contract Type Violated | Evidence Source | Evidence Strength |
|----|----------|----------|:---------------------:|-----------------|:-----------------:|
| F1-M1 | Job Execution Ordering Violation | REORDER_JOBS | TEMPORAL | AWS MM Docs 2022; carddemo Issue #12 | Strong (documented) |
| F1-M2 | Job Execution Ordering Violation | REMOVE_JOB_DEPENDENCY | TEMPORAL | AWS MM Docs 2022; multiple Stack Overflow reports | Strong (documented) |
| F1-M3 | Job Execution Ordering Violation | ALTER_STEP_SEQUENCE | TEMPORAL | Gula 2020 postmortem | Medium (one source) |
| F2-M1 | File/Dataset Availability Violation | REMOVE_DATASET_INIT | RESOURCE | AWS MM Best Practices 2022; Ulrich+Newcomb 2010 Ch.9 (11 cases) | Strong (multiple) |
| F2-M2 | File/Dataset Availability Violation | CHANGE_DATASET_NAME | RESOURCE | carddemo COACTUPC.cbl:890 dependency | Medium (one project) |
| F2-M3 | File/Dataset Availability Violation | ALTER_FILE_DEPENDENCY_ORDER | RESOURCE | AWS MM Best Practices 2022 | Strong (documented) |
| F3-M1 | Return-Code Propagation Loss | SUPPRESS_RETURN_CODE_CHECK | CONTROL_FLOW | IBM COBOL Migration Guide 2021; Knorr 2019; multiple SO reports | Strong (multiple) |
| F3-M2 | Return-Code Propagation Loss | ALTER_ERROR_BRANCH | CONTROL_FLOW | IBM COBOL Migration Guide 2021 | Strong (documented) |

## Operator Definitions

### F1-M1: REORDER_JOBS
Swaps the execution order of two jobs that have a documented dependency.
Violates: TEMPORAL contract A ≺ B.
Applied to: JCL job scheduling configuration in modernized system.

### F1-M2: REMOVE_JOB_DEPENDENCY
Removes a COND-based or explicit ordering constraint between jobs.
Violates: TEMPORAL contract A ≺ B.
Applied to: Workflow orchestration DAG (e.g., AWS Step Functions definition).

### F1-M3: ALTER_STEP_SEQUENCE
Reorders EXEC steps within a single JCL job.
Violates: TEMPORAL contract STEP-A ≺ STEP-B.
Applied to: Job step ordering in migrated JCL or workflow.

### F2-M1: REMOVE_DATASET_INIT
Removes a file/dataset initialization step from the job stream.
Violates: RESOURCE contract produces(INIT-STEP, DS) ≺ consumes(PROC-STEP, DS).
Applied to: JCL step removal in modernized batch configuration.

### F2-M2: CHANGE_DATASET_NAME
Alters a dataset name in the consumer step without updating the producer.
Violates: RESOURCE contract (producer and consumer no longer reference same resource).
Applied to: Dataset name in DD statement of migrated JCL.

### F2-M3: ALTER_FILE_DEPENDENCY_ORDER
Makes a consumer job run before its producer in the workflow.
Violates: RESOURCE contract produces ≺ consumes.
Applied to: Workflow dependency configuration.

### F3-M1: SUPPRESS_RETURN_CODE_CHECK
Removes the COND parameter check, allowing downstream steps to execute on error.
Violates: CONTROL_FLOW contract RC(A) op T → ¬execute(B).
Applied to: COND parameter removal in migrated job step.

### F3-M2: ALTER_ERROR_BRANCH
Changes the condition in a COND parameter (e.g., GT to EQ), altering when bypass occurs.
Violates: CONTROL_FLOW contract semantics.
Applied to: COND parameter value in migrated JCL step.

## Categories Not Included in Paper 1

The following failure categories exist in the empirical record but are excluded from
Paper 1 scope:

| Category | Reason for Exclusion |
|----------|---------------------|
| Record format incompatibility (F4) | Requires DATA contracts (Paper 2 scope) |
| State initialization loss (F5) | Requires STATE contracts (Paper 2 scope) |
| Transaction boundary change (F6) | Requires cross-system transaction analysis (Paper 3 scope) |
| Batch scheduling change (F7) | Partially covered by F1; deeper analysis is future work |

These categories are documented in docs/failure_taxonomy.md and reserved for Papers 2–4.
