# Experiments

## LEGACY-CONTRACT — Paper 1 Experiment Documentation

This document describes the exact configuration of each experiment in the paper.
All experiment configurations are frozen in `experiments/*/config.yaml`.

---

## Overview

| Experiment | ID | Research Question | Script | Result |
|---|---|---|---|---|
| Contract Recovery | E1_INDEP | RQ1 | `scripts/run_rq1_independent.py` | `results/rq1/rq1_independent.json` |
| Risk Detection (positive) | E2 | RQ2 | `scripts/run_rq2.py` | `results/rq2/rq2_summary.json` |
| Risk Detection (negative) | E2_NEG | RQ2 | `scripts/run_negative_mutations.py` | `results/rq2/negative_summary.json` |
| LLM Baselines | E_LLM | RQ2 | `scripts/run_llm_baselines.py` | `results/rq2/llm_c_results.json`, `llm_d_results.json` |
| Dynamic Reconciliation | E3 | RQ3 | `scripts/run_dynamic_reconciliation.py` | `results/rq3/rq3_dynamic_results.json` |
| Coverage Experiment | E3_COV | RQ3 | `scripts/run_coverage_experiment.py` | `results/rq3/coverage_experiment.json` |
| Ablation | E4 | Ablation | — | `results/ablation/ablation_summary.json` |

---

## E1_INDEP — Contract Recovery (RQ1)

**Configuration:** `experiments/rq1/config.yaml`

### Design

Evaluates how accurately the static extractor recovers behavioral contracts by
comparing it against an **independently implemented oracle**.

The oracle is a separate regex-based implementation in `scripts/run_rq1_independent.py`
that reads raw JCL text and extracts step-ordering obligations without calling any
code from `src/legacy_contract/static_analysis/`. The oracle and the extractor share
the JCL specification but no code — eliminating the circular evaluation problem.

### Scope

**TEMPORAL contracts only.** RESOURCE and CONTROL_FLOW contracts require DD disposition
and COND= analysis that cannot be validated without sharing more implementation logic
with the oracle. This is a deliberate scientific constraint, not a limitation that can
be papered over.

### Dataset

CardDemo test split: 33 held-out JCL files (`datasets/carddemo/SPLITS_60_20_20.json`).

### Metrics

- Micro-precision, micro-recall, micro-F1 (primary)
- Macro-F1 (per-file F1 averaged)
- Bootstrap 95% CI (n=10,000, seed=42)
- TP / FP / FN per file

### Key Caveat

The deprecated `results/rq1/rq1_summary.json` used the same extractor family to
generate ground truth — making F1=1.0 a mathematical identity (idempotency), not
an accuracy measurement. **Do not cite rq1_summary.json.** Use `rq1_independent.json`.

---

## E2 — Modernization Risk Detection (RQ2, Positive Benchmark)

**Configuration:** `experiments/rq2/config.yaml`

### Design

Applies 8 fault-grounded mutation operators to 55 CardDemo JCL files and measures
whether each detection method correctly identifies each applied mutation.

**Mutation application:** For each file, each of the 8 operators is attempted.
440 total attempts; 336 not applicable (the operator's precondition is not met
in that file); 104 evaluated cases.

**Ground truth:** Any successfully applied mutation is a positive test case
(Level-2 DETERMINISTIC — the mutation is verifiably applied, so detection should fire).
FP is defined as detection on a case where the mutation was NOT applied (impossible
in the positive benchmark by design — FP is measured in E2_NEG).

### Detection Methods Compared

| ID | Method | Key information used |
|---|---|---|
| Proposed | BCG + confidence-delta | Contracts, provenance, confidence, structural edges |
| Baseline A | Structural dependency | Call graph, data flow, file dependency graph |
| Baseline B | Complexity metrics | McCabe complexity, coupling, cohesion, delta |
| Baseline C | LLM-only | Source code + mutation description (no structural analysis) |
| Baseline D | Dependency + LLM | Source code + structural dependency graph + mutation description |
| Baseline E | Static BCG, no delta | Contracts, structural edges (broken contracts only, not modified) |

**Fairness note:** Each baseline receives exactly the information described above.
LLM baselines receive artifact source code and a blinded mutation description (v2_blinded
prompts — neutral language, no semantics-preserving/violating hint). v1 prompts were
discarded because they inadvertently leaked semantic context for negative mutations.

### Operators

| Operator | Category | Failure type | Empirical grounding |
|---|---|---|---|
| REORDER_JOBS | F1 | Temporal ordering violation | JCL→Airflow scheduler reordering |
| REMOVE_JOB_DEPENDENCY | F1 | Temporal ordering violation | Dependency pruning during migration |
| ALTER_STEP_SEQUENCE | F1 | Temporal ordering violation | Step consolidation in cloud batch |
| REMOVE_DATASET_INIT | F2 | Resource availability violation | JCL→Spring Batch dataset wiring |
| CHANGE_DATASET_NAME | F2 | Resource availability violation | DD name renaming during re-host |
| ALTER_FILE_DEPENDENCY_ORDER | F2 | Resource availability violation | Consumer-before-producer inversion |
| SUPPRESS_RETURN_CODE_CHECK | F3 | Control-flow loss | COND= removal in CI/CD translation |
| ALTER_ERROR_BRANCH | F3 | Control-flow weakening | RC threshold change during simplification |

All operators are derived from documented real-world modernization failures.
See `docs/failure_taxonomy.md` for the full empirical grounding.

---

## E2_NEG — Negative Benchmark (RQ2, False-Positive Rate)

**Configuration:** `scripts/run_negative_mutations.py`

### Design

Applies 5 **semantics-preserving** mutation operators to generate cases where
detection should NOT fire (true negatives). Measures FPR = FP / (FP + TN).

### Negative Operators

| Operator | Semantics preserved how |
|---|---|
| RENAME_STEP_COMMENT | Comment-only change — no structural or behavioral effect |
| ADD_REDUNDANT_DEPENDENCY | Adds a dependency that was already implied — no new obligation |
| REORDER_INDEPENDENT_STEPS | Reorders steps with no ordering obligation between them |
| CHANGE_ACCOUNTING_PARAMETERS | Changes JCL accounting fields — no execution effect |
| RENAME_PROC_LABEL | Renames a PROC label consistently — structural rename, no behavioral change |

### Result

TN=144, FP=0, FPR=0.000, Specificity=1.000.

**Interpretation:** FPR=0 is a consequence of the closed-set benchmark design
(operators are semantics-preserving by construction). It should not be interpreted
as an independently measured open-world false-alarm rate.

---

## E_LLM — LLM Baseline Evaluation

**Script:** `scripts/run_llm_baselines.py`  
**Configuration:** `results/rq2/llm_config.json`

### Design

Evaluates Baselines C and D using the Groq API with `llama-3.3-70b-versatile`.
Prompts are v2_blinded: neutral descriptions of operators, no leakage of
semantics-preserving/violating context.

### Key Result

| Baseline | F1 | TP | API errors | Total calls |
|---|---|---|---|---|
| C (LLM-only) | 0.0377 | 2 | 245 | 248 |
| D (Dep+LLM) | 0.1091 | 6 | 241 | 248 |

**These are lower bounds.** 97–98% of API calls failed during the run.
The results reflect the infrastructure constraints of that specific run, not
a definitive ceiling on LLM capability for this task.

**Reproducibility:** LLM results are not bit-for-bit reproducible across
model updates or infrastructure changes. The model version, prompt version,
temperature, and seed are documented in `results/rq2/llm_config.json`.

**Requirement:** `GROQ_API_KEY` environment variable must be set.

---

## E3 — Dynamic Reconciliation (RQ3)

**Configuration:** `experiments/rq3/config.yaml`

### Design

Loads 40 execution traces (2 real GnuCOBOL, 38 JCL-ordering simulation),
runs the ReconciliationEngine on the extracted contracts, and measures
what fraction of contracts are promoted to STATIC_DYNAMIC_SUPPORTED.

### Trace Types

| Type | Count | Source |
|---|---|---|
| EXECUTION (real GnuCOBOL) | 2 | EMPPAY.cbl, DEPTPAY.cbl via GnuCOBOL 3.2.0 |
| EXECUTION_SIMULATED (JCL ordering) | 38 | JCL step-ordering simulation |
| SYNTHETIC_STATIC (excluded per SI-01) | 3 | Excluded — would promote with zero real evidence |

**Environment:** GnuCOBOL 3.2.0 on macOS arm64. **NOT z/OS production execution.**

### Scientific Integrity Check SI-01

SYNTHETIC_STATIC traces (generated from static contract assertions, not real execution)
are explicitly excluded from reconciliation. If included, they would trivially promote
contracts to STATIC_DYNAMIC_SUPPORTED with zero real dynamic evidence — a scientific
integrity violation. SI-01 guard is enforced in `ReconciliationEngine` and verified
by 18 test variants in `tests/scientific/test_si01_synthetic_guard.py`.

---

## E3_COV — Coverage Experiment (RQ3)

**Script:** `scripts/run_coverage_experiment.py`

### Design

Subsamples the 40 execution traces at 5 coverage levels (10%, 25%, 50%, 75%, 100%)
and measures the dynamic validation rate at each level. Uses the same random seed (42)
for reproducible subsampling.

### Finding

Validation rate increases monotonically from 1.6% (4 traces) to 91.8% (40 traces).
NOT_OBSERVED contracts do not transition to CONTRADICTED as traces are added.
This empirically confirms the design principle: absence of evidence ≠ contradiction.

---

## E4 — Ablation Study

**Configuration:** `experiments/ablation/config.yaml`

### Conditions

| Condition | Description | F1 |
|---|---|---|
| A1 (Full BCG) | Full proposed system | 1.000 |
| A3 (Structural only) | Structural edges only — equivalent to Baseline A | 0.888 |
| A4 (Complexity only) | Complexity metrics only — equivalent to Baseline B | 0.000 |
| A5 (BCG, no delta) | BCG without confidence-delta — equivalent to Baseline E | 0.962 |
| A2, A7 (Dynamic) | Dynamic-evidence conditions — blocked (CardDemo DB2/CICS) | — |

The single architectural difference between A1 (F1=1.00) and A5 (F1=0.96) is
`diff.modified` detection for `ALTER_ERROR_BRANCH`. This is the minimal
discriminating component of the proposed system.
