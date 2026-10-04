# Final Results — RELIC Paper 1

All numbers below are sourced from `FINAL_RESULTS_MANIFEST.json` (v1.6, frozen=true).
Authoritative reproduction command: `make reproduce-paper1`

---

## RQ1 — Contract Recovery (TEMPORAL only, independent oracle)

**File:** `rq1/rq1_independent.json`
**Oracle:** Independent regex-based implementation — shares JCL spec, no shared code
**Scope:** TEMPORAL contracts only (RESOURCE/CONTROL_FLOW require human annotation)
**Dataset:** 11 held-out JCL files (CardDemo `held_out` split — ZERO overlap with dev/validation)
**Split fix note:** Prior version used `splits["test"]` key (does not exist); corrected to `splits["held_out"]`.

| Metric | Value |
|---|---|
| Micro-Precision | 1.0000 |
| Micro-Recall | 1.0000 |
| Micro-F1 | 1.0000 |
| Macro-F1 | 0.5455 |
| 95% Bootstrap CI (macro-F1) | [0.2727, 0.8182] |
| Total TP | 21 |
| Total FP | 0 |
| Total FN | 0 |
| H1 verdict | SUPPORTED |

**Interpretation:** Micro-F1=1.00 indicates the extractor and oracle agree exactly on all 21
TEMPORAL contracts across 11 held-out files (zero dev overlap). Macro-F1=0.5455 reflects that
6 of 11 files have zero TEMPORAL contracts (single-step JCL), producing F1=0.0 per convention
for those files. Wide CI [0.27, 0.82] reflects per-file variance in contract density (n=11 files).
Evaluation is limited to TEMPORAL contracts; RESOURCE/CONTROL_FLOW require human annotation.

---

## RQ2 — Modernization Risk Detection

**File:** `rq2/rq2_summary.json` (static baselines), `rq2/llm_c_results.json`, `rq2/llm_d_results.json` (LLM)  
**Dataset:** 55 JCL files, 440 mutation attempts, 104 evaluated (336 N/A), 144 negative  
**Ground truth:** Level-2 mutation benchmark (closed-set; FP=0 by design)

### Positive Benchmark (104 evaluated mutations)

| Condition | F1 | TP | FN | FPR |
|---|---|---|---|---|
| **BCG proposed (static + confidence-delta)** | **1.0000** | **104** | **0** | — |
| Baseline E — Static BCG, no confidence-delta | 0.9600 | 96 | 8 | — |
| Baseline A — Structural dependency analysis | 0.8995 | 85 | 19 | — |
| Baseline D — Dependency + LLM (Groq, blinded)† | 0.1091 | 6 | 98 | 0.000 |
| Baseline C — LLM-only (Groq, blinded)† | 0.0377 | 2 | 102 | 0.000 |
| Baseline B — Complexity metrics | 0.0000 | 0 | 104 | — |

† Lower bounds: 245/248 (C) and 241/248 (D) API calls errored. Model: Groq
`llama-3.3-70b-versatile`, temperature=0, v2_blinded prompts, seed=42.

### Negative Benchmark (144 semantics-preserving mutations)

| Metric | Value |
|---|---|
| TN | 144 |
| FP | 0 |
| FPR | 0.0000 |
| Specificity | 1.0000 |

**Note:** FPR=0 is a consequence of the closed-set benchmark design (semantics-preserving
operators by construction), not an independently measured open-world false-alarm rate.

### Per-Operator Results (BCG proposed vs Baseline A)

| Operator | Category | BCG F1 | Baseline A F1 | BCG TP | A TP |
|---|---|---|---|---|---|
| REORDER_JOBS | F1 | 1.000 | 0.983 | 29 | 28 |
| REMOVE_JOB_DEPENDENCY | F1 | 1.000 | 1.000 | 28 | 28 |
| ALTER_STEP_SEQUENCE | F1 | 1.000 | 1.000 | 28 | 28 |
| REMOVE_DATASET_INIT | F2 | 1.000 | 1.000 | 1 | 1 |
| CHANGE_DATASET_NAME | F2 | 1.000 | 0.000 | 1 | 0 |
| ALTER_FILE_DEPENDENCY_ORDER | F2 | 1.000 | 0.000 | 1 | 0 |
| SUPPRESS_RETURN_CODE_CHECK | F3 | 1.000 | 0.000 | 8 | 0 |
| ALTER_ERROR_BRANCH | F3 | 1.000 | 0.000 | 8 | 0 |

**Key finding:** `ALTER_ERROR_BRANCH` is the discriminating operator. BCG detects all 8 via
`diff.modified` (confidence-delta). Baseline A, Baseline E, and Baseline B all miss all 8.

---

## RQ3 — Dynamic Evidence

**File:** `rq3/rq3_dynamic_results.json`  
**Traces:** 40 total (2 real GnuCOBOL EXECUTION + 38 EXECUTION_SIMULATED JCL ordering)  
**Environment:** GnuCOBOL 3.2.0 on macOS arm64 — **NOT z/OS**

| State | Count | Rate |
|---|---|---|
| STATIC_DYNAMIC_SUPPORTED | 56 | 91.8% |
| STATIC_DYNAMIC_CONFLICT | 1 | 1.6% |
| NOT_OBSERVED | 4 | 6.6% |
| Total evaluated | 61 | — |

### Coverage Experiment

**File:** `rq3/coverage_experiment.json`

| Trace coverage | Supported | Validation rate |
|---|---|---|
| 10% (4 traces) | 1 | 1.6% |
| 25% (10 traces) | 15 | 24.6% |
| 50% (20 traces) | 26 | 42.6% |
| 75% (30 traces) | 39 | 63.9% |
| 100% (40 traces) | 56 | 91.8% |

**Finding:** Validation rate increases monotonically. NOT_OBSERVED contracts do not
become CONTRADICTED as traces are added — confirming absence of evidence ≠ contradiction.

---

## Limitations on All Results

1. All results are on the AWS CardDemo closed-set benchmark.
2. GnuCOBOL traces are not z/OS production execution.
3. 38/40 traces are JCL-ordering simulations, not real program execution.
4. RQ1 covers TEMPORAL contracts only.
5. FPR=0 is a closed-set design consequence, not an open-world measurement.
6. LLM results are lower bounds due to high API error rates.
7. Confidence scores are not calibrated probabilities.

See `docs/limitations.md` for full detail.
