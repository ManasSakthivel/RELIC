# Source-Level Mutation Benchmark

Implementation: `relic_eval/mutate.py`, `relic_eval/pipeline.py`.
Raw output: `results/final/raw/evaluation_records.jsonl` (one record per candidate
mutant, including the unified diff, oracle verdict and evidence, and every
detector's prediction). Manifest: `results/final/evaluation_manifest.csv`.

## 1. Unit of analysis

One JCL file containing at least one JOB statement, from one subject system
(`relic_eval/subjects.py`). Files that only define procedures form the subject's
PROC library. RELIC and every baseline analyse one file at a time (as in the
legacy harness); effects that only show up in *other* files are out of scope.

## 2. Operators

Each operator rewrites JCL **text** to simulate one documented failure class
(`docs/failure_taxonomy.md`). Every applicable site is enumerated; there is no
sampling and no random seed. Edits are made in place, keeping columns and
sequence numbers of untouched text.

| Operator | Failure class | Targets contract type | Site rule | Legacy operator it replaces |
|---|---|---|---|---|
| `SWAP_ADJACENT_STEPS` | F1 ordering | TEMPORAL | every pair of consecutive steps in the same IF context with no statement between them | REORDER_JOBS, ALTER_STEP_SEQUENCE |
| `SPLIT_JOB` | F1 ordering | TEMPORAL | before every step except the first: insert a copy of the JOB card and job-level SET/JCLLIB/JOBLIB (the remaining steps become an independently scheduled job) | REMOVE_JOB_DEPENDENCY |
| `DELETE_PRODUCER_STEP` | F2 dataset | RESOURCE | every step whose output (DISP NEW/MOD, IDCAMS DEFINE) is an input of a later step | REMOVE_DATASET_INIT |
| `RENAME_OUTPUT_DATASET` | F2 dataset | RESOURCE | every DD with DISP NEW/MOD: append `.MIG` to the DSN on the producer side only | CHANGE_DATASET_NAME |
| `MOVE_CONSUMER_BEFORE_PRODUCER` | F2 dataset | RESOURCE | producer/consumer pairs at distance ≥ 2 (distance 1 is a swap) | ALTER_FILE_DEPENDENCY_ORDER |
| `REMOVE_COND` | F3 return code | CONTROL_FLOW | every EXEC with `COND=` | SUPPRESS_RETURN_CODE_CHECK |
| `ALTER_COND_THRESHOLD` | F3 return code | CONTROL_FLOW | every EXEC with a numeric COND test: first code c → 2c (c > 0) or 4 (c = 0), max 4095. For the common `(c,LT)` form this weakens the guard; the direction is not varied (see limitations L9) | ALTER_ERROR_BRANCH |
| `REMOVE_IF_GUARD` | F3 return code | CONTROL_FLOW | every IF construct: delete IF/ELSE/ENDIF lines | — (new) |
| `INSERT_COMMENT` | refactoring (expected negative) | — | one per job with ≥ 2 steps: comment statement before the second step | (legacy negatives edited the BCG) |
| `CHANGE_MSGCLASS` | refactoring (expected negative) | — | one per job with ≥ 2 steps whose JOB card has MSGCLASS | |

"Producer"/"consumer" for site selection is purely syntactic (DSN and DISP, IDCAMS
`NAME()`); it only decides where to mutate. Labels come from the oracle.

## 3. Scope rules (declared before results were computed)

A mutant is `OUT_OF_SCOPE` when it targets behaviour outside RELIC's documented scope:

* `REMOVE_IF_GUARD` — RELIC's parser documents IF/THEN/ELSE as "noted but not deeply parsed";
* `RENAME_OUTPUT_DATASET` where no later step of the same file reads the dataset —
  the only consequence is for other jobs (cross-file), outside the per-file unit.

Out-of-scope mutants are still labelled by the oracle and run through every
detector; they appear in the sensitivity analysis "+ OUT_OF_SCOPE mutants".

## 4. Accounting statuses

Every candidate mutant receives exactly one status (checked by
`tests/evaluation/test_results_integrity.py`):

| Status | Meaning |
|---|---|
| `EVALUABLE` | valid, in scope, oracle verdict DIFFERENT or EQUIVALENT — used for metrics |
| `OUT_OF_SCOPE` | §3 |
| `INVALID_MUTATION` | the operator cannot produce valid JCL at this site (DSN length limit, split point inside IF/THEN/ELSE, mutant identical to original, oracle reports a malformed file) |
| `INFRASTRUCTURE_FAILURE` | generator or oracle crashed (none occurred) |
| `OTHER` | `ORACLE_UNDETERMINED` (opaque step affected, no modelled difference) or `DUPLICATE` (identical mutant text to an earlier mutant of the same file) |

Detector errors are not a status: a detector that raises is recorded with
`status: ERROR` and scored as "not flagged" (none occurred in the reported run).

## 5. Ground truth and predictions

* Ground truth: oracle `full` scenario set (`docs/evaluation/ORACLE_SPECIFICATION.md`).
* Prediction: a detector *flags* a mutant. For RELIC this means
  `RiskDetector.detect(original_bcg, mutated_bcg)` returns at least one risk item
  (including the items it marks as false-positive candidates — same rule as the
  legacy harness). Both BCGs are built by the full RELIC pipeline from the two texts.
* Positive class: behaviour-changing mutant.

## 6. Metrics

`relic_eval/metrics.py`: TP, FP, FN, TN; precision, recall (detection rate), F1,
specificity, FPR; undefined ratios are reported as n/a. Wilson 95% intervals for
proportions; 95% percentile intervals for F1 and F1 differences from a file-level
cluster bootstrap (10,000 resamples, seed 20261004). Coverage = scored / candidates.
Every confusion matrix passes hard consistency assertions, and the committed
metrics are recomputed from the raw records in the test suite.
