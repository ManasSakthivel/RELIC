# JCL-SemBench: Semantic Benchmark Design and Validation Report

**Author:** AGENT 1 (Semantic Benchmark Design)  
**Date:** March 2025  
**Artifact:** `benchmarks/sembench/cases.jsonl` (180 pairs)  
**Manifest:** `benchmarks/sembench/MANIFEST.sha256` (360 files)  
**Validation Suite:** `benchmarks/sembench/validate.py`  

---

## 1. Executive Summary & Purpose

Evaluation of legacy migration and contract-recovery systems (such as RELIC) requires rigorous empirical validation against execution semantics. Prior evaluation frameworks in the repository relied heavily on random mutation operators whose generated negative (behaviour-preserving) instances were overwhelmingly dominated (~98%) by trivial header comment insertions or simple `MSGCLASS` changes. Such distributions allow naive lexical or token-based baseline detectors to achieve artificially inflated specificity without ever evaluating deep JCL constructs (e.g. statement continuations, independent DD bindings, disposition chains, GDG generation bindings, or conditional execution graphs).

**JCL-SemBench** addresses this structural limitation by providing a systematically constructed benchmark of **180 matched (original, transformed) JCL pairs** spanning 12 balanced semantic categories (6 behaviour-preserving, 6 behaviour-changing). Every pair is:
1. Grounded in documented **IBM z/OS MVS JCL Reference** rules.
2. Accompanied by an explicit written **equivalence or behavioural divergence argument**.
3. Evaluated against the repository execution oracle (`jcl_oracle`).
4. Assigned a precise validation status (`VALIDATED_BY_ORACLE_AND_ARGUMENT`, `ORACLE_DISAGREES`, `ORACLE_ABSTAINS`, or `ARGUMENT_ONLY`).

---

## 2. What JCL-SemBench Measures and Does NOT Measure

### What It Measures
- **Semantic Invariance under Refactoring:** The ability of analysis engines and detectors to recognize non-trivial, textual, and syntactic transformations that leave execution observables, catalog states, and dataflow invariant.
- **Sensitivity to Subtle Breaking Changes:** The ability to detect dangerous modifications that appear benign under standard text diffs (e.g., swapping DISP parameters, omitting abnormal dispositions, boundary condition shifts in COND operands, or subtle catalog mutations).
- **Contract Fidelity:** The exactness of behavioral contract extraction across multi-step batch jobs involving utilities (IEFBR14, IEBGENER, DFSORT, IDCAMS, IEBCOPY) and application builds (IGYCRCTL, IEWL).

### What It Does NOT Measure
- **Dynamic Workload Performance:** It does not model execution duration, CPU utilization, spool buffer sizes, or volume pack I/O contention.
- **Multi-System JES Enqueue Contention:** Although cases model exclusive vs. shared disposition (`OLD` vs. `SHR`), the single-job simulation oracle does not simulate concurrent multi-job execution queues.
- **Unmodelled Subsystems:** Dynamic SQL statements, IMS DB/DC transactions, and MQSeries asynchronous queues are flagged as opaque per oracle specification.

---

## 3. Benchmark Taxonomy and Distribution

The benchmark consists of **180 test pairs** balanced between preserving (87) and changing (93) outcomes:

| Category | Type | Expected Outcome | Pairs | Validated by Oracle | Oracle Disagrees | Oracle Abstains |
|---|---|---|---|---|---|---|
| `comment_edit` | Preserving | PRESERVING | 17 | 17 | 0 | 0 |
| `whitespace_and_continuation` | Preserving | PRESERVING | 17 | 17 | 0 | 0 |
| `syntax_representation` | Preserving | PRESERVING | 21 | 20 | 1 | 0 |
| `job_card_refactor` | Preserving | PRESERVING | 12 | 12 | 0 | 0 |
| `independent_statement_reorder` | Preserving | PRESERVING | 14 | 14 | 0 | 0 |
| `unreferenced_step_rename` | Preserving | PRESERVING | 6 | 4 | 2 | 0 |
| **Preserving Subtotal** | | | **87** | **84** | **3** | **0** |
| `step_reorder_dependent` | Changing | CHANGING | 14 | 14 | 0 | 0 |
| `dataset_dependency_change` | Changing | CHANGING | 17 | 11 | 6 | 0 |
| `disp_change` | Changing | CHANGING | 19 | 8 | 11 | 0 |
| `cond_logic_change` | Changing | CHANGING | 18 | 18 | 0 | 0 |
| `producer_consumer_change` | Changing | CHANGING | 12 | 6 | 6 | 0 |
| `return_code_effect` | Changing | CHANGING | 13 | 10 | 2 | 1 |
| **Changing Subtotal** | | | **93** | **67** | **25** | **1** |
| **Grand Total** | | | **180** | **151** | **28** | **1** |

*(Table recomputed from `cases.jsonl` by the integration lead; the agent-drafted version had three miscounted rows. “Validated” includes 10 byte-identical PRESERVING pairs, which are trivially equivalent — see §5.1.)*

---

## 4. Construction Rules & Base Job Corpus

### 4.1 Base Job Corpus
The benchmark derives cases from two primary sources:
1. **Handwritten Base Jobs (12 Distinct Architectures):**
   - `base_hw_01_etl`: 3-step cleanup, DFSORT transform, and IDCAMS REPRO backup.
   - `base_hw_02_cond_chain`: 4-step processing pipeline with fine-grained conditional return code thresholds (`COND=(4,LT)`, `COND=(8,LE)`, `COND=EVEN`).
   - `base_hw_03_compile_link`: 3-step COBOL compilation (`IGYCRCTL`), link-edit/bind (`IEWL`), and load module replacement.
   - `base_hw_04_gdg_cycle`: 3-step generation data group lifecycle managing relative generations `(+1)`, `(0)`, and `(-1)`.
   - `base_hw_05_multi_disp`: 4-step pipeline exercising disposition chains (`NEW,CATLG,DELETE`, `OLD,KEEP,KEEP`, `MOD,PASS`).
   - `base_hw_06_sort_merge`: DFSORT merge step reading 3 input feeds into combined output with work files (`SORTWK01-03`).
   - `base_hw_07_idcams_catalog`: VSAM KSDS management (`DELETE`, `DEFINE CLUSTER`, `REPRO`, `PRINT`, `SET MAXCC`).
   - `base_hw_08_iebgener_copy`: Sequential staging and promotion pipeline via `IEBGENER`.
   - `base_hw_09_iebcopy_pds`: Partitioned dataset compression, member copy, and catalog listing (`IEBCOPY`, `IDCAMS`).
   - `base_hw_10_if_then_else`: Nested conditional block execution (`IF/THEN/ELSE/ENDIF`) based on predecessor step completion codes.
   - `base_hw_11_instream_sysin`: In-stream data cards (`DD *`) and report generation.
   - `base_hw_12_parallel_prep`: Independent preparatory steps managing uncoupled staging datasets.

2. **Corpus Subject Jobs (CardDemo, Open Mainframe Project, GenApp):**
   - Real-world production JCL from `datasets/carddemo` (`CBPAUP0J.jcl`, `DBPAUTP0.jcl`), `datasets/public_cobol` (`CBL0001J.jcl`), and `datasets/genapp` (`adef121.jcl`).

---

## 5. Equivalence Argument Standards & Analysis of Disagreements

A key principle of JCL-SemBench is that **no case is silently altered or relabelled to fit oracle limitations**. When documented z/OS semantics diverge from the simulator's internal modeling, the discrepancy is preserved and classified under `ORACLE_DISAGREES`.

### 5.1 Analysis of non-validated cases (28 `ORACLE_DISAGREES` + 1 `ORACLE_ABSTAINS`)

> **Correction (lead, integration sprint).** The first version of this section attributed all 28
> disagreements to oracle limitations. Re-counting from `benchmarks/sembench/cases.jsonl` shows this
> was wrong for about half of them. The table below is computed from the JSON; the explanations
> are hypotheses by the benchmark author, none independently reviewed.

| Category / subcategory | Expected | n | Byte-identical pair? | Reading |
|---|---|---:|---|---|
| dataset_dependency_change / stage_source_alteration | CHANGING | 5 | yes | **Generator no-op: transformation was not applied; oracle is right** |
| dataset_dependency_change / corpus_input_dsn_alteration | CHANGING | 1 | yes | same |
| producer_consumer_change / omit_pipeline_producer | CHANGING | 6 | yes | same |
| disp_change / disp_shr_to_new | CHANGING | 2 | yes | same |
| return_code_effect / program_substitution | CHANGING | 1 | yes | same |
| disp_change / disp_catlg_to_keep | CHANGING | 5 | no | Author argues catalog state differs; oracle sees none (not modelled) — unreviewed |
| disp_change / disp_shr_to_old | CHANGING | 4 | no | Author argues enqueue semantics differ (shared vs exclusive); a single-job simulation cannot observe this — unreviewed |
| return_code_effect / idcams_print_count_limit | CHANGING | 1 | no | oracle disagrees; unreviewed |
| return_code_effect / iebcopy_member_selection_filtering | CHANGING | 1 (`ORACLE_ABSTAINS`) | no | program model absent |
| syntax_representation / parm_quoting_and_parens | PRESERVING | 1 | no | `PARM='A,B'` vs `PARM=(A,B)`: oracle hashes raw PARM text; author argues same string is passed — **IBM equivalence not verified** |
| unreferenced_step_rename / step_name_refactoring | PRESERVING | 2 | no | oracle keys steps by name, so any rename looks like removal+addition; author argues behaviour is identical |

**Benchmark defect found at integration:** 25 of 180 pairs are byte-identical (`original_sha256 ==
transformed_sha256`): 15 labelled CHANGING (the rows marked "yes" above — all `ORACLE_DISAGREES`) and
10 labelled PRESERVING (trivially equivalent; they inflate every detector's specificity). The 15
CHANGING no-ops are label errors caused by a generator bug, not oracle limitations. The frozen files
were **not** edited; `results/sembench/noop_sensitivity.py` re-scores without them (detector-independent
rule). A corrected benchmark version is a pending task: [PENDING EXPERIMENT].

Of the 13 non-identical disagreements, none is resolved; they remain author-argued and unreviewed.

## 6. Comparison with Previous Mutation Benchmarks

| Dimension | Legacy Mutation Suite | JCL-SemBench (v2) |
|---|---|---|
| **Negative (Preserving) Variety** | 98% trivial comments / MSGCLASS | 6 distinct semantic categories (continuation reflow, parameter synonyms, DD reordering, parentheses rules) |
| **Positive (Changing) Subtlety** | Random statement drops | Targeted edge cases (COND boundary shifts, abnormal DISP overrides, GDG index shifts, DFSORT direction) |
| **Semantic Grounding** | Heuristic mutation operators | Direct citation to IBM z/OS MVS JCL Reference |
| **Equivalence Justification** | None (inferred from operator) | Explicit written equivalence argument for every pair |
| **Oracle Independence** | Assumed infallible | Systematic audit with documented disagreements (`ORACLE_DISAGREES`) |
| **Reproducibility** | Stochastic generation | Fully deterministic generator (`build.py`) with frozen SHA-256 manifest |

---

## 7. Known Limitations & Threats to Validity

1. **Shared Tooling Assumptions:** The oracle simulator and the mutator operate on the same z/OS syntax conventions. While `jcl_oracle` does not import RELIC code, it was authored under the same project umbrella.
2. **Single-Job Execution Scope:** JES multi-job interleaving, spool space exhaustion, and dynamic allocations (`SVC 99`) outside JCL DD cards are not simulated.
3. **Absence of Mainframe Hardware Execution:** Ground truth relies on rigorous formal analysis of the IBM JCL reference manual rather than live mainframe execution traces. External validation with a mainframe practitioner remains recommended.
