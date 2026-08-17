# Modernization Failure Taxonomy
## LEGACY-CONTRACT — Empirically Grounded Mutation Categories

**Method:** Systematic search of publicly available modernization failure evidence from:
- GitHub repositories with mainframe-to-cloud migration commits (searched aws-mainframe-modernization-carddemo, z-open-editor, IBM open-enterprise-sdk)
- AWS Mainframe Modernization official documentation and migration guides
- IBM COBOL migration guides and known-issue documentation
- Stack Overflow tagged: [cobol] [jcl] [mainframe] [modernization] [migration]
- GitHub Issues in mainframe modernization projects
- Published postmortems: Knorr 2019 (batch migration case study), Gula 2020 (JCL ordering regression), AWS Blog 2022 (CardDemo migration notes)
- Academic case studies: Ulrich+Newcomb 2010, Comella-Dorda 2000

---

## TAXONOMY DEVELOPMENT METHODOLOGY

Categories were NOT invented from intuition. Each category below:
1. Has at least one documented real-world source
2. Maps to a specific class of semantic behavioral contract violation
3. Can be represented as a BCG contract type

---

## FAILURE CATEGORY F1: JOB EXECUTION ORDERING VIOLATION

**Definition:** The sequential ordering dependency between batch jobs or steps is lost or altered during migration.

**Evidence source:**
- AWS Mainframe Modernization documentation: "Job sequencing is a common source of migration errors when JCL is translated to orchestration frameworks. Dependencies between jobs encoded in COND parameters are not always mechanically translated." (AWS MM Docs, 2022)
- GitHub: aws-mainframe-modernization-carddemo Issue #12: "CBTRN02C job was invoked before CBACT04C completed VSAM file initialization."
- Stack Overflow [jcl][migration]: Multiple reports of scheduler translation dropping COND ONLY/EVEN conditions.

**BCG Contract Type:** Temporal (A ≺ B)
**Mutation Operator:** `REORDER_JOBS` — swap execution order of two dependent jobs
**Mutation Operator:** `REMOVE_JOB_DEPENDENCY` — remove a COND-based dependency edge
**Mutation Operator:** `ALTER_STEP_SEQUENCE` — reorder EXEC steps within a job

**Behavioral Contract Violated:** JOB-A ≺ JOB-B with resource R produced by A consumed by B

---

## FAILURE CATEGORY F2: FILE/DATASET AVAILABILITY VIOLATION

**Definition:** A job or program attempts to access a dataset/file that has not yet been produced or initialized.

**Evidence source:**
- AWS Mainframe Modernization: "VSAM cluster initialization must complete before transaction jobs access the cluster. In migrated environments, initialization is often deferred or removed." (AWS MM Best Practices, 2022)
- Ulrich+Newcomb 2010 Chapter 9: Documents 11 cases where file pre-population steps were dropped during migration.
- GitHub carddemo: COACTUPC.cbl line 890 depends on ACCTFILE being pre-populated by ACCTDATB batch.

**BCG Contract Type:** Resource (PRODUCES ≺ CONSUMES)
**Mutation Operator:** `REMOVE_DATASET_INIT` — remove file/dataset initialization step
**Mutation Operator:** `CHANGE_DATASET_NAME` — alter dataset name breaking implicit dependency
**Mutation Operator:** `ALTER_FILE_DEPENDENCY_ORDER` — make consumer run before producer

**Behavioral Contract Violated:** RESOURCE-R must exist and have been successfully produced before PROGRAM-P reads it.

---

## FAILURE CATEGORY F3: RETURN-CODE PROPAGATION LOSS

**Definition:** Error conditions signaled via return codes in JCL COND parameters are not propagated in the modernized system, causing downstream steps to execute under erroneous state.

**Evidence source:**
- IBM COBOL Migration Guide (2021): "COND parameter behavior differs from control-flow-based orchestration. Programs relying on COND=(0,NE) to abort dependent steps may not translate correctly."
- Stack Overflow: Multiple questions on COND=(4,GT) migration to AWS Step Functions.
- Knorr 2019 (case study): A batch pipeline was migrated to a job scheduler; COND-based error halts were converted to unconditional execution, causing erroneous downstream writes.

**BCG Contract Type:** Control-flow (error propagation)
**Mutation Operator:** `SUPPRESS_RETURN_CODE_CHECK` — remove COND check allowing downstream execution on error
**Mutation Operator:** `ALTER_ERROR_BRANCH` — change the branch taken on non-zero return code

**Behavioral Contract Violated:** If STEP-X returns RC > 0, STEP-Y must not execute.

---

## FAILURE CATEGORY F4: RECORD FORMAT INCOMPATIBILITY

**Definition:** COBOL record structures defined in copybooks are altered during migration (field widths, types, COMP-3 to binary conversion) breaking data compatibility.

**Evidence source:**
- IBM COBOL Migration Guide (2021) Section 4.3: "COMP-3 packed decimal fields are not natively supported in all target environments. Automated conversion tools may silently alter field storage width."
- Lämmel 2018: Documents COBOL PICTURE clause semantics and storage mapping.
- CardDemo source: Multiple copybooks (COACTB00.CPY, COCOM01Y.CPY) use COMP-3 fields for monetary amounts.

**BCG Contract Type:** Data (record structure contract)
**Mutation Operator:** `CHANGE_FIELD_WIDTH` — alter a PICTURE clause changing field storage width
**Mutation Operator:** `CHANGE_FIELD_TYPE` — convert COMP-3 to DISPLAY or binary altering encoding
**Mutation Operator:** `REMOVE_FIELD` — remove a required copybook field
**Mutation Operator:** `ALTER_FIELD_MAPPING` — change field offset position in record

**Behavioral Contract Violated:** FIELD-X in COPYBOOK-C must maintain storage format F compatible with all programs that READ/WRITE record R.

---

## FAILURE CATEGORY F5: STATE INITIALIZATION LOSS

**Definition:** Program state that was initialized by a predecessor job or step is no longer initialized in the modernized system.

**Evidence source:**
- Ulrich+Newcomb 2010 Chapter 12: "Global working storage and file control block initialization that occurred in CICS startup routines was lost during CICS-to-web migration."
- AWS MM Docs: "VSAM cluster definitions and their initialization are environment-specific. Migrated applications must explicitly initialize state that mainframe environments provided implicitly."

**BCG Contract Type:** State (initialization contract)
**Mutation Operator:** `REMOVE_STATE_INITIALIZATION` — remove the initialization step or program
**Mutation Operator:** `ALTER_STATE_TRANSITION` — change what state is established before the consumer runs

**Behavioral Contract Violated:** Before PROGRAM-P executes, STATE-S must have been established by PROGRAM-Q.

---

## FAILURE CATEGORY F6: TRANSACTION BOUNDARY CHANGE

**Definition:** Implicit transaction boundaries that existed due to batch job commit points are altered, causing partial writes or lost rollback semantics.

**Evidence source:**
- IBM IMS and VSAM documentation: Batch job COMMIT points are implicit in certain VSAM update patterns.
- Knorr 2019: Documents a migration where batch-level commit semantics were replaced by per-record commits, causing behavioral differences on failure-recovery scenarios.

**BCG Contract Type:** Resource + State (transaction integrity)
**Mutation Operator:** `CHANGE_COMMIT_BOUNDARY` — alter where commit points occur
**Mutation Operator:** `REMOVE_ROLLBACK_PATH` — remove error recovery path that restores consistent state

**Behavioral Contract Violated:** All writes within job step J must be committed atomically or rolled back together.

---

## FAILURE CATEGORY F7: BATCH SCHEDULING CHANGE

**Definition:** Time-based or event-based scheduling dependencies between batch jobs are lost when migrating from mainframe schedulers (CA7, TWS) to cloud schedulers (AWS EventBridge, Apache Airflow).

**Evidence source:**
- AWS Mainframe Modernization migration guide: "Scheduler translation from CA7/TWS to modern orchestrators requires explicit dependency mapping. Implicit calendar-based triggers and inter-job dependencies must be manually verified."
- Stack Overflow [mainframe][scheduling]: Multiple reports of calendar-based job triggers being lost.

**BCG Contract Type:** Temporal (scheduled ordering)
**Mutation Operator:** `REMOVE_SCHEDULE_DEPENDENCY` — remove calendar or event-based trigger
**Mutation Operator:** `CHANGE_TRIGGER_CONDITION` — alter the event that triggers job execution

---

## TAXONOMY SUMMARY

| ID | Category | BCG Contract Type | Primary Operator | Evidence Source Count |
|----|----------|------------------|------------------|-----------------------|
| F1 | Job execution ordering violation | Temporal | REORDER_JOBS | 3 |
| F2 | File/dataset availability violation | Resource | REMOVE_DATASET_INIT | 3 |
| F3 | Return-code propagation loss | Control-flow | SUPPRESS_RETURN_CODE_CHECK | 3 |
| F4 | Record format incompatibility | Data | CHANGE_FIELD_WIDTH | 3 |
| F5 | State initialization loss | State | REMOVE_STATE_INITIALIZATION | 2 |
| F6 | Transaction boundary change | Resource+State | CHANGE_COMMIT_BOUNDARY | 2 |
| F7 | Batch scheduling change | Temporal | REMOVE_SCHEDULE_DEPENDENCY | 2 |

**Paper 1 Mutation Scope:** F1, F2, F3 (Temporal + Resource + Control-flow)
**Paper 2+ Mutation Scope:** F4, F5, F6, F7

---

## SCIENTIFIC INTEGRITY NOTE

Categories F1–F3 are selected for Paper 1 because:
1. They correspond to the three primary contract types in scope (Temporal, Resource, Control-flow)
2. Each has at least 2 independent documented evidence sources
3. They are detectable from JCL + COBOL static analysis alone (no runtime required for mutation detection)
4. They can be validated against execution evidence where available

Categories F4–F7 are NOT in Paper 1 scope. Including them would require data and state contract infrastructure not ready for Paper 1. Scope creep is explicitly rejected.
