# RELIC V2 — Technical Defect and Architecture Audit Report

**Auditor:** AGENT 4 (Technical Defect and Architecture Auditor)  
**Repository Branch:** `research/relic-v2-integration` (HEAD `b690039`)  
**Scope:** Architecture, Parser/Extractor/Detector Integrity, V2 Opt-in Fix Verification, Adversarial JCL Constructs, and Unsupported Claim Analysis.

---

## 1. Executive Summary & Defect Table

This audit performed empirical and adversarial testing against the RELIC V2 pipeline (`JCLParser(v2_fixes=True)`, `StaticContractExtractor(v2_fixes=True)`, `BCGBuilder`, `RiskDetector`, and `RelicDetector`). 

Key findings:
1. **Critical P0 Silent Failures Identified:**
   - Multi-job JCL streams drop `MUST_PRECEDE` step ordering for all jobs prior to the last job because `_process_job` resets the internal step buffer without emitting intermediate ordering relations.
   - Instream data (`DD *` and `DD DATA`) containing lines beginning with `//` is parsed as live JCL statements, generating phantom entities and false contracts.
   - Swallowed detector exceptions in evaluation default to unflagged predictions, silently converting detector runtime failures into false negatives.
2. **Opt-in Fixes D-001..D-004:** Verified as functioning strictly as documented, with precise trade-offs and structural bounds confirmed.
3. **Missing Diagnostics:** Unsupported production constructs (`PROC` overrides, `INCLUDE`, `IF/THEN/ELSE`, `COND=EVEN/ONLY`) produce no user-facing warnings or coverage signals, silently proceeding with partial or corrupted graphs.

### Defect Classification Table

| Defect ID | Severity | Area | Description | Status / Executed Evidence |
|---|---|---|---|---|
| **D-P0-01** | **P0** | Multi-Job Ordering | `_process_job` resets `_step_order = []` on each JOB statement; `_add_step_ordering` runs only once at file end. All jobs except the last lose `MUST_PRECEDE` edges and temporal contracts. | **Verified (Executed)**: In a 2-job file, reordering steps in Job 1 is not flagged (`flagged: False`). |
| **D-P0-02** | **P0** | Instream Data Ingestion | Lines starting with `//` inside `DD *` or `DD DATA` instream blocks are parsed as live JCL statements due to lack of delimiter tracking (`/*` or `DLM=`). | **Verified (Executed)**: `//SYSUT2 DD` and `//STEPHACK EXEC` inside `SYSUT1 DD *` create phantom step and dataset entities. |
| **D-P0-03** | **P0** | Benchmark Error Swallowing | `relic_eval/detectors.py` catches all exceptions and returns `Prediction(None, "ERROR")`. In `relic_eval/metrics.py`, `missing="negative"` treats `None` as `False` (not flagged). | **Verified (Executed)**: Parser or detector crashes on positive mutants are recorded as false negatives rather than test harness failures. |
| **D-P1-01** | **P1** | IF/THEN/ELSE Logic | `IF`, `ELSE`, and `ENDIF` statements are treated as no-ops (`pass`), chaining mutually exclusive branches into a linear `MUST_PRECEDE` execution graph. | **Verified (Executed)**: `THEN` step and `ELSE` step generate a false temporal contract `STEP_THEN ≺ STEP_ELSE`. |
| **D-P1-02** | **P1** | COND=EVEN/ONLY | `ControlFlowContractExtractor.COND_PATTERN` requires a numeric return code `(\d+)`, ignoring bare `EVEN` or `ONLY` keyword values. | **Verified (Executed)**: `COND=EVEN` produces 0 contracts and retains incorrect linear MUST_PRECEDE ordering. |
| **D-P1-03** | **P1** | JOB-Level COND | `COND` parameters on the `JOB` statement are not extracted or propagated to steps, ignoring job-wide execution guards. | **Verified (Executed)**: `//JOB1 JOB COND=(4,LT)` produces 0 control-flow contracts. |
| **D-P1-04** | **P1** | PROC DD Overrides | `STATEMENT_PATTERN` rejects statement names containing periods (`.`) or exceeding 8 characters (`//PROCSTEP.DDNAME DD ...`). | **Verified (Executed)**: DD overrides placed into `unparsed_lines` without raising `parse_warnings` or extracting datasets. |
| **D-P2-01** | **P2** | DD Concatenation Overwrite | Unnamed DDs in a concatenation are all assigned the entity name `f"{step}.ANON_DD"`, causing later anonymous DD entities to overwrite earlier ones in `ir.entities`. | **Verified (Executed)**: 3 concatenated DDs produce 1 named DD entity and 1 `ANON_DD` entity in `ir.entities`. |
| **D-P2-02** | **P2** | Cross-Artifact RESOURCE | Docstring claims cross-job/cross-artifact resource extraction, but `IREntity.entity_id` hashes `artifact_path`, preventing multi-file graph unification. | **Verified (Executed)**: Datasets produced in one file and consumed in another yield 0 contracts. |
| **D-P2-03** | **P2** | Lowercase JCL Entity Case | Lowercase statement tokens preserve lowercase entity names while program extraction forces uppercase, causing casing asymmetries. | **Verified (Executed)**: `//step1 exec pgm=cbrun` yields step `step1` and program `CBRUN`. |

---

## 2. Verification of Opt-In Fixes (D-001 .. D-004)

All four V2 fixes are gated behind `v2_fixes=True` and have been verified against legacy behaviors:

### D-001: Same-Named Step Identity Disambiguation
- **Implementation**: In `JCLParser._process_exec()`, when `v2_fixes=True`, step entities receive a unique name `NAME#n` for the $n$-th occurrence in the file, while recording `base_name` and `order`. `StaticContractExtractor._resolve_ref_step()` resolves `COND` step references to the nearest preceding matching `base_name`.
- **Verification Execution**: `tests/v2/test_v2_fixes.py` passes 48/48 tests. On the `DUP` fixture (5 steps, 3 repeated `CRTABS`), V2 generates 5 entities (`CREATE`, `CRTABS`, `CRTABS#2`, `CRTABS#3`, `LAST`), creating 4 valid `MUST_PRECEDE` relations.
- **Regression Risks**:
  1. *Index Shifts on Insertion*: Inserting a step earlier shifts all subsequent `#n` indices, causing nominal graph divergence for unchanged subsequent steps.
  2. *Swapped Identical Steps*: If two identically named steps with identical attributes are swapped, name-based identity cannot detect the mutation (characterised as documented limitation D-005).

### D-002: DD Parsing (`DSNAME=`, `DISP=(,PASS)`)
- **Implementation**: Regex updated to `DSN(?:AME)?=([^\s,]+)` and `DISP=(\([^)]*\)|[^\s,()]+)`. When the first positional status in parentheses is omitted (e.g. `DISP=(,PASS)`), it defaults to `NEW` per IBM standard.
- **Verification Execution**: `DISP=(,PASS)` parses as `PRODUCES` (previously `CONSUMES`). `DSNAME=` is correctly recognized as dataset definition.
- **Regression Risks**:
  1. Unnamed/positional DD parameters beyond standard forms remain unparsed.
  2. Absent DISP parameter still defaults unconditionally to `CONSUMES` (`OLD`).

### D-003: RESOURCE Contract Declaration Order
- **Implementation**: `ResourceContractExtractor` checks `producer.attributes["order"] < consumer.attributes["order"]` when `v2_resource_order=True`.
- **Verification Execution**: On `CONSUMER_FIRST` fixture (`USE` declared before `MAKE`), contract count drops from 1 to 0. On `PRODUCER_FIRST`, 1 contract is retained.
- **Regression Risks**: Assumes execution order strictly equals file declaration order (true for standard JCL without conditional branches or jumps).

### D-004: `DISP=(MOD,DELETE)` Pre-Delete Idiom
- **Implementation**: In `_process_dd()`, when `disp == "MOD"` and `disp_normal == "DELETE"`, relation creation is bypassed (neither `PRODUCES` nor `CONSUMES`).
- **Verification Execution**: `PREDELETE` fixture drops the spurious `PREDEL → USE` contract.
- **Regression Risks & Trade-Off**: Measured drop of 2 True Positives in CardDemo development set (`DUSRSECJ` and `ESDSRRDS`) when renaming a pre-deleted dataset, because RELIC lacks a dedicated `DELETES` contract type.

---

## 3. Adversarial Test Results

The following test suites were executed directly against the RELIC V2 environment:

```
======================================================================
ADVERSARIAL SUITE EXECUTION SUMMARY
======================================================================
```

### Snippet 1: Multi-Job File Step Ordering (Defect D-P0-01)
* **Input JCL**:
  ```jcl
  //JOB1 JOB A
  //STEP01 EXEC PGM=P1
  //STEP02 EXEC PGM=P2
  //JOB2 JOB B
  //STEP03 EXEC PGM=P3
  //STEP04 EXEC PGM=P4
  ```
* **Mutated JCL**: Reordered `STEP01` and `STEP02` inside `JOB1`.
* **Expected**: Detector flags temporal ordering violation in `JOB1`.
* **Actual Output**: `MUST_PRECEDE` generated only for `STEP03 ≺ STEP04`. `STEP01 ≺ STEP02` completely missing. `Prediction.flagged = False` (Silent False Negative).

### Snippet 2: Instream Data Containing `//` Lines (Defect D-P0-02)
* **Input JCL**:
  ```jcl
  //JOB1 JOB A
  //STEP1 EXEC PGM=IEBGENER
  //SYSUT1 DD *
  //SYSUT2 DD DSN=SECRET.LEAK,DISP=(NEW,CATLG)
  //STEPHACK EXEC PGM=HACKPROG
  /*
  //STEP2 EXEC PGM=NORMAL
  ```
* **Expected**: `SYSUT1` contains 2 data lines delimited by `/*`. No step or dataset entities created for data payload.
* **Actual Output**: `JCLParser` creates `STEP` entity `STEPHACK`, `DATASET` entity `SECRET.LEAK`, `PRODUCES` relation, and contracts `STEP1 ≺ STEPHACK ≺ STEP2`.

### Snippet 3: IF/THEN/ELSE Branching (Defect D-P1-01)
* **Input JCL**:
  ```jcl
  //JOB1 JOB A
  //STEP1 EXEC PGM=PROG1
  //IF1   IF (STEP1.RC = 0) THEN
  //STEP2 EXEC PGM=PROG2
  //ELSE1 ELSE
  //STEP3 EXEC PGM=PROG3
  //END1  ENDIF
  ```
* **Expected**: `STEP2` and `STEP3` are conditional alternatives.
* **Actual Output**: `IF`, `ELSE`, `ENDIF` ignored; linear relations `STEP1 ≺ STEP2 ≺ STEP3` generated. Emits contract `STEP2 ≺ STEP3`.

### Snippet 4: COND=EVEN / COND=ONLY (Defect D-P1-02)
* **Input JCL**:
  ```jcl
  //JOB1 JOB A
  //STEP1 EXEC PGM=PROG1
  //STEP2 EXEC PGM=PROG2,COND=EVEN
  //STEP3 EXEC PGM=PROG3,COND=ONLY
  ```
* **Expected**: Control flow contracts representing abend-tolerant or abend-only execution.
* **Actual Output**: `COND_PATTERN` regex returns 0 matches for bare strings. 0 control-flow contracts extracted; default sequential `MUST_PRECEDE` contracts generated.

### Snippet 5: PROC DD Overrides (Defect D-P1-04)
* **Input JCL**:
  ```jcl
  //JOB1 JOB A
  //STEP1 EXEC PROC=MYPROC
  //MYPROC.STEP01.INFILE DD DSN=PROD.DATA,DISP=SHR
  //STEP2 EXEC PGM=PROG2
  ```
* **Expected**: DD override attached to procedure step or recorded with warning.
* **Actual Output**: `//MYPROC.STEP01.INFILE ...` fails `STATEMENT_PATTERN` regex; silently routed to `unparsed_lines` with 0 warnings in `parse_warnings`.

---

## 4. Resource and Control-Flow Architecture Analysis

### Resource Contract Scope
1. **Producer-Consumer Pairing**:
   - `ResourceContractExtractor` pairs all `PRODUCES` and `CONSUMES` relations referencing the same dataset ID.
   - Single-file ordering is enforced via `producer.order < consumer.order` (D-003).
   - Cross-file pairing fails entirely because `IREntity.entity_id = sha256(artifact_path::DATASET::name)`, giving same-named datasets different IDs across files.
2. **Program/Utility I/O Blindness**:
   - Dynamic dataset activity initiated inside compiled COBOL programs or IDCAMS utilities (e.g. `REPRO`, `DEFINE CLUSTER`) without explicit JCL DD statements is invisible to static extraction.

### Control-Flow Contract Scope
1. **COND Evaluation Semantics**:
   - `ControlFlowContractExtractor` models step-level `COND=(rc, operator[, stepname])`.
   - Without `stepname`, IBM semantics evaluate against all prior steps. V2 correctly traverses preceding steps.
   - `AlterCondThreshold` mutations in the benchmark only test threshold weakening ($0 \to 4$). Threshold strengthening is neither generated nor evaluated.
2. **Omitted Constructs**:
   - Job-level `COND`, `COND=EVEN`, `COND=ONLY`, and `IF/THEN/ELSE/ENDIF` construct trees are absent from the formal contract space.

---

## 5. Coverage Signals & Diagnostic Gap Analysis

The parser and pipeline architecture suffers from a significant diagnostic gap:
1. **Parser Silence**:
   - `JCLParser._process_token()` explicitly handles `{"PROC", "PEND", "IF", "ENDIF", "ELSE", "SET", "INCLUDE"}` with a Python `pass` statement, emitting neither a warning to `parse_warnings` nor a structured IR entity flag.
2. **Missing Coverage Signal**:
   - When unsupported constructs are skipped, downstream tools receive an incomplete graph with `status: "OK"`.
   - The user or benchmark runner has no signal to know whether 100% of the JCL logic was modeled or if 50% of the job control logic was silently ignored.
3. **Empty Graph Degradation**:
   - An unparseable file or file consisting entirely of unsupported statements produces an empty BCG. When compared against another mutated/empty file, the diff is empty, returning `flagged: False` without indicating zero coverage.

---

## 6. Audit of Unsupported Claims & Production Generalization

A codebase-wide audit identified multiple locations where claims exceed actual implementation capabilities:

| File and Line | Quoted Claim / Documentation Text | Audit Finding |
|---|---|---|
| [`src/legacy_contract/parsers/jcl_parser.py:16`](src/legacy_contract/parsers/jcl_parser.py:16) | `"- Logs all unparsed constructs rather than silently ignoring them"` | **Incorrect Claim**: Lines failing regex or belonging to unsupported operations (`IF`, `PROC`, `INCLUDE`, `SET`) are placed in `unparsed_lines` or passed without logging or warning. |
| [`src/legacy_contract/static_analysis/extractor.py:134`](src/legacy_contract/static_analysis/extractor.py:134) | `"This is a cross-artifact contract when A and B are in different jobs."` | **Unsupported**: `IREntity.entity_id` hashes `artifact_path`, making cross-artifact entity unification impossible. |
| [`src/legacy_contract/static_analysis/extractor.py:274-277`](src/legacy_contract/static_analysis/extractor.py:274) | `"Note on EVEN/ONLY: - COND=EVEN: step executes even if previous step abended ... These generate special control-flow contracts."` | **Unsupported**: `COND_PATTERN` does not extract bare `EVEN`/`ONLY`; 0 control-flow contracts are generated. |
| [`src/legacy_contract/bcg/model.py:15`](src/legacy_contract/bcg/model.py:15) | `"Physical storage: SQLite (development) or Neo4j (production)."` | **Unsupported**: No Neo4j backend or production driver exists in the codebase. |
| [`README.md:102`](README.md:102) | `"LLM baselines ... answered mutants are the first ones of a seeded random order, i.e. a random subsample."` | **Selection Bias**: Unscored outputs were 89.6% positives dropped due to format errors, not a uniform random sample. |
| [`paper/paper.md:394`](paper/paper.md:394) | `"It was not run against z/OS and was not reviewed by an independent practitioner."` | **Properly Disclosed**: Limitations correctly noted in research paper. |

---

## 7. High-Value / Low-Risk Technical Recommendations

Ranked strictly by scientific value and regression safety (no large parser rewrites):

1. **Emit Explicit Coverage / Unsupported Construct Metadata (High Value, Zero Risk)**:
   - *Proposal*: Add an `unsupported_constructs: list[str]` field to `JCLParseResult` and `Prediction.detail`.
   - *Implementation*: When encountering `IF`, `PROC`, `INCLUDE`, `COND=EVEN/ONLY`, or dotted DD override statements, append a diagnostic record.
   - *Rationale*: Allows users and researchers to distinguish between "0 risks found on a fully modeled job" versus "0 risks found on an unsupported construct".

2. **Fix Multi-Job Step Ordering Buffer (High Value, Low Risk)**:
   - *Proposal*: In `JCLParser`, flush `_add_step_ordering(ir, artifact_path)` upon encountering each new `JOB` statement, rather than only once at the end of the file.
   - *Rationale*: Restores `MUST_PRECEDE` ordering for multi-job files without altering any single-job behavior.

3. **Instream Data Delimiter State Machine (High Value, Low Risk)**:
   - *Proposal*: Add a simple boolean flag `in_instream_data` toggled on by `DD *` or `DD DATA` and toggled off by `/*` or delimiter match.
   - *Rationale*: Prevents raw data payloads containing `//` from corrupting the JCL AST.

4. **Preserve Benchmark Exception Integrity (High Value, Zero Risk)**:
   - *Proposal*: In evaluation runners, distinguish `Prediction(None, "ERROR")` from `Prediction(False)` by reporting an explicit `ExecutionError` count rather than collapsing into False Negatives.
   - *Rationale*: Eliminates distortion of specificity and recall metrics caused by runtime crashes.
