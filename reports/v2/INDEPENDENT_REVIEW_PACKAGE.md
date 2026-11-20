# Independent Review Package — Blind Validation of the `jcl_oracle` Ground Truth

**Status: PENDING. No independent review has been performed. No reviewer ratings exist in this repository, and none have been fabricated.**
Every agreement figure that this package will eventually produce is PENDING. The only numbers computed so far come from `compute_agreement.py --self-test`, which runs on clearly labelled SYNTHETIC ratings and says nothing about the oracle.

Companion report: [`ORACLE_INDEPENDENCE_AUDIT.md`](ORACLE_INDEPENDENCE_AUDIT.md) (findings F-01..F-15, ambiguities U-01..U-10).
Package directory: [`review_package/`](review_package/).

Why this package exists: the oracle (`jcl_oracle`), the mutation generator (`relic_eval/mutate.py`) and the evaluation-unit selection (`relic_eval/subjects.py`) share one lexer, and all of them were written by one author in one commit (audit F-01, F-02). Agreement between the oracle and RELIC is therefore not independent evidence of correctness. A human review that is blind to both the oracle and RELIC is the only available way to test the labels themselves.

---

## 1. Sampling method

**Frame.** The 566 mutants with `evaluable_for_metrics = true` in `results/final/raw/evaluation_records.jsonl`. Of these, 106 are oracle-EQUIVALENT and 460 are oracle-DIFFERENT. Mutants the oracle labelled UNDETERMINED are not in the frame.

**Seed and determinism.** `SEED = 20251120`. Candidates in each cell are sorted by `mutation_id` before sampling with `random.Random(SEED)`. Presentation order (the R001..R060 numbering) is shuffled with `random.Random(SEED + 1)`. Re-running `make_sample.py` reproduces the key, blind form and cards byte for byte.

**Design.** Stratified by oracle label × operator × subject, with fixed per-cell quotas. The label balance is 30 EQUIVALENT and 30 DIFFERENT. A hard-case pool is reserved first in each cell (flags below), and the remainder is drawn at random. Two TXT2PDF1 anchors and two D-004 rename anchors are added.

| Label | Operator | Subject | Quota | Hard flag reserved | Population in cell |
|---|---|---|---|---|---|
| EQUIVALENT | INSERT_COMMENT | carddemo | 5 | H_D004 ×2 | 30 |
| EQUIVALENT | INSERT_COMMENT | genapp | 4 | H_DUP ×2 | 10 |
| EQUIVALENT | INSERT_COMMENT | omp_course | 5 | — | 25 |
| EQUIVALENT | CHANGE_MSGCLASS | carddemo | 7 | H_D004 ×2 | 29 |
| EQUIVALENT | CHANGE_MSGCLASS | genapp | 7 | H_DUP ×2 | 10 |
| DIFFERENT | SWAP_ADJACENT_STEPS | carddemo | 2 | H_ABEND ×1 | 81 |
| DIFFERENT | SWAP_ADJACENT_STEPS | genapp | 3 | H_ABEND ×1, H_DUP ×1 | 81 |
| DIFFERENT | SWAP_ADJACENT_STEPS | omp_course | 2 | H_ABEND ×1 | 4 |
| DIFFERENT | SPLIT_JOB | carddemo | 2 | H_D004 ×1 | 81 |
| DIFFERENT | SPLIT_JOB | genapp | 3 | H_DUP ×1 | 81 |
| DIFFERENT | SPLIT_JOB | omp_course | 1 | — | 4 |
| DIFFERENT | DELETE_PRODUCER_STEP | carddemo | 3 | H_D004 ×1 | 28 |
| DIFFERENT | DELETE_PRODUCER_STEP | genapp | 1 | — | 5 |
| DIFFERENT | RENAME_OUTPUT_DATASET | carddemo | 3 | ANCHOR_D004 ×2 | 11 |
| DIFFERENT | RENAME_OUTPUT_DATASET | genapp | 1 | — | 2 |
| DIFFERENT | MOVE_CONSUMER_BEFORE_PRODUCER | carddemo | 2 | — | 11 |
| DIFFERENT | MOVE_CONSUMER_BEFORE_PRODUCER | genapp | 1 | — | 3 |
| DIFFERENT | REMOVE_COND | carddemo | 1 | — | 21 |
| DIFFERENT | REMOVE_COND | genapp | 1 | H_DUP ×1 | 12 |
| DIFFERENT | REMOVE_COND | omp_course | 1 | — | 1 |
| DIFFERENT | ALTER_COND_THRESHOLD | carddemo | 1 | — | 21 |
| DIFFERENT | ALTER_COND_THRESHOLD | genapp | 1 | H_DUP ×1 | 12 |
| DIFFERENT | ALTER_COND_THRESHOLD | omp_course | 1 | — | 1 |

Source: `CELLS` in [`review_package/make_sample.py`](review_package/make_sample.py:41); populations from [`sampling_frame.json`](review_package/sampling_frame.json). Per-cell population and quota are the only things in `sampling_frame.json` (no per-case labels). Anchors: R012 (REMOVE_COND) and R054 (ALTER_COND_THRESHOLD) are the two COND edits on the single-step job `TXT2PDF1`, whose EQUIVALENT labels depend on the unverified "first-step COND is ignored" assumption (audit F-06, U-01). R044 and R048 are the D-004 rename anchors.

**Resulting sample (n = 60).**

| Dimension | Counts |
|---|---|
| Subject | carddemo 28, genapp 22, omp_course 10 |
| Operator | INSERT_COMMENT 14, CHANGE_MSGCLASS 14, SWAP_ADJACENT_STEPS 7, SPLIT_JOB 6, DELETE_PRODUCER_STEP 4, RENAME_OUTPUT_DATASET 4, REMOVE_COND 4, ALTER_COND_THRESHOLD 4, MOVE_CONSUMER_BEFORE_PRODUCER 3 |
| Oracle failure-injection tier among the 30 DIFFERENT | T0 (differs at baseline) 20, T1 (injected RC only) 5, T2 (abend only) 5 |
| Hard-case flags | H_D004 17, H_DUP 13, H_ABEND 5, ANCHOR_D004 2 (flags may overlap) |

Hard-case flag meanings: **H_D004** — file listed in the D-004 defect register entry; **H_DUP** — file with duplicate step names; **H_ABEND** — oracle label differs only under abend injection (tier T2); **ANCHOR_D004** — D-004 anchor chosen deliberately.

**Choices and caveats of the design.**
- The 30/30 label split is chosen so that Cohen's kappa is stable. It is **not** proportional to the population (106 / 460). Prevalence-weighted estimates (for example the population oracle false-positive rate) need design weights = cell population / cell quota. `sampling_frame.json` has what is needed. The script does not compute weighted estimates; this is a proposed extension.
- `omp_course` is limited by availability (only 25 EQUIVALENT INSERT_COMMENT and a handful of positives), so it is under-represented relative to its file count.
- The positive sample is deliberately enriched for the audit's structurally suspect strata: SPLIT_JOB (36.1% of positives, differing mostly through job names and counts embedded in the termination observable — audit F-04) and the failure-injection-only tiers (34.6% of positives).
- n = 60 gives wide confidence intervals (see section 5). A pass or fail from this sample alone is not a validation of the whole corpus.
- Selection used the oracle label and failure-injection tier, which is allowed (it is the sampler, not a reviewer) but means the key cannot be used to claim an unbiased estimate of overall oracle accuracy without weights.

---

## 2. Files

All paths are relative to `reports/v2/review_package/`.

### Give to reviewers

| File | Purpose |
|---|---|
| `cards/R001.md` … `cards/R060.md` | One self-contained card per case: job file context, unified diff of original vs mutated, the PROC library and program sources that exist, and the questions. Contains no oracle label, no categories, no evidence and no RELIC output (enforced by the leak check in `make_sample.py`; a grep over `cards/` for oracle/RELIC/operator-name strings finds nothing; EQUIVALENT/DIFFERENT occur only as answer options). |
| `cards.jsonl` | Same card content, machine-readable. |
| `blind_review_form.csv` | `case_id, subject, file, card, reviewer_id, q1_normal_completion, q2_failure_scenarios, overall_label, confidence, evidence, minutes_spent`. Response columns are empty. No label or prediction columns. |
| `RUBRIC.md` | What "behaviour-preserving" means, with normal completion and the failure scenarios defined, plus the treatment of several JOB cards in one file and the rating scale. |
| `responses_template.csv` | Placeholder rows (`PENDING_REVIEWER_ID`) in the expected response format. |
| `SHARING.md` | What may and may not be sent to reviewers. |

### Keep internal (do not share until all reviews are complete)

| File | Purpose |
|---|---|
| `KEY_DO_NOT_SHARE.csv` | `case_id, mutation_id, subject, file, operator, site, sampling_cell, selection_reason, hard_flags, oracle_label, oracle_label_no_abend, oracle_tier, oracle_tier_jobname_stripped, oracle_categories, oracle_evidence, oracle_scenarios_checked, oracle_differing_scenarios, relic_v1_0_flagged, relic_v1_1_flagged, textdiff_flagged`. |
| `adjudication_template.csv` | `case_id, reviewer_A_label, reviewer_B_label, third_reviewer_id, third_reviewer_label, final_label, adjudication_rationale`. Filled by the adjudication coordinator from reviewer submissions only. |
| `sampling_frame.json` | Seed, cell populations and quotas, population label counts. |

### Tools and evidence

| File | Purpose |
|---|---|
| `make_sample.py` | Deterministic sampler (internal). Builds the key, form, cards and frame. It has a built-in leak check that fails if a card contains the oracle label, a category name or RELIC output. |
| `compute_agreement.py` | Agreement statistics, with `--self-test` on synthetic data. |
| `experiments/lexer_disagreement.py` (+ `_results.json`) | Oracle lexer vs RELIC parser comparison; 94.5% statement agreement (audit section on experiments). |
| `experiments/feature_census.py` (+ `_results.json`) | Which JCL features the corpus uses; D-004 and duplicate-step file lists. |
| `experiments/mutant_crosscheck.py` (+ `_results.json`) | Mutant-level lexer cross-check and failure-injection tiers. |
| `experiments/split_job_sensitivity.py` (+ `_results.json`) | SPLIT_JOB labels with job names and count stripped from the termination observable. |

Reviewers must not be given `experiments/` or `make_sample.py` (they reveal the operator and tier structure).

---

## 3. Reviewer procedure

1. **Reviewers.** Two independent reviewers (A and B) with working mainframe JCL experience, ideally from outside the author team. A third reviewer C is held in reserve for disagreements. The three never discuss individual cases during rating.
2. **Blindness.** Reviewers receive only the "give to reviewers" files. They are not told the oracle labels, RELIC outputs, the operator list, or the tier structure. Nobody who has seen the key rates cases.
3. **Calibration round.** Before rating, A and B each rate 5–8 non-sampled development items (taken from outside the 60) and discuss the rubric with the coordinator only for rubric wording, not for the sampled cases. Calibration data is not used in statistics.
4. **Per case, per reviewer** (columns in the blind form):
   - `q1_normal_completion` — `SAME` / `DIFFERENT` / `CANNOT_DETERMINE`: does the mutated job produce the same externally visible results as the original when every step completes normally (same datasets created/deleted/catalogued, same data flow between steps, same step execution and condition outcomes)?
   - `q2_failure_scenarios` — `SAME` / `DIFFERENT` / `CANNOT_DETERMINE`: is the behaviour the same in every single-fault scenario (one step ends with a non-zero return code or abends), per the definitions in `RUBRIC.md`?
   - `overall_label` — `EQUIVALENT` only if Q1 and Q2 are both SAME; `DIFFERENT` if either is DIFFERENT; otherwise `CANNOT_DETERMINE`.
   - `confidence` (1–3), free-text `evidence`, `minutes_spent`.
5. **Resources and disclosure.** Reviewers may use IBM manuals and other references. Any use of an LLM or of the RELIC/oracle tooling must be disclosed in `evidence`; use of the oracle or RELIC invalidates that reviewer's ratings.
6. **Return.** Each reviewer returns one CSV in the blind-form format with `reviewer_id` filled in.

---

## 4. Adjudication

1. Compare A and B on `overall_label` per case.
2. A = B → `final_label` = that label.
3. A ≠ B → third reviewer C rates the case blind to A's and B's labels. `final_label` = majority of A, B, C.
4. Three-way disagreement (for example EQUIVALENT / DIFFERENT / CANNOT_DETERMINE) → `final_label` = `UNRESOLVED`. The reviewers discuss and may produce a documented consensus, but UNRESOLVED cases are reported as such and excluded from the primary binary analysis.
5. **The oracle is never an adjudicator.** Neither the oracle label nor RELIC output is shown to anyone before `adjudication_template.csv` is final. The key is released to the analyst only after all reviewer files and the adjudication file are frozen.
6. Rationale for every adjudicated case is written in `adjudication_rationale`.

---

## 5. Agreement statistics

All defined and implemented in `compute_agreement.py`.

- **Percent agreement** `P_o` = matches / n.
- **Cohen's kappa** `κ = (P_o − P_e) / (1 − P_e)`, with `P_e` from the two raters' marginals.
- **Gwet's AC1** `AC1 = (P_o − P_e^γ) / (1 − P_e^γ)`, where `P_e^γ = (1/(q−1)) Σ_k π_k (1 − π_k)` and `π_k` is the mean of the two raters' marginal proportions of category k. AC1 is reported alongside kappa because kappa collapses under skewed marginals (the "kappa paradox"); this sample is balanced by design but real reviewer labels may not be.
- **Bootstrap CI.** Percentile interval, B = 2000, seed 1, cases resampled with replacement; reported for P_o, κ and AC1.
- **Two analyses.** (a) Binary: EQUIVALENT vs DIFFERENT, cases where either rater said `CANNOT_DETERMINE` excluded, with the exclusion count reported. (b) All categories (including `CANNOT_DETERMINE`).
- **Comparisons.** Reviewer A vs B (inter-rater); each reviewer vs the oracle; adjudicated final label vs the oracle. For the oracle comparisons it reports the confusion matrix and the oracle's sensitivity and specificity relative to the reviewer/adjudicated reference.
- **Stratification.** Agreement is also reported by operator, oracle tier (T0/T1/T2), subject and hard flag, with per-stratum n. Strata are small (n between 2 and 14), so these are descriptive only.
- **Q1 vs tier.** Reviewer Q1 answers (normal completion) are cross-tabulated against the oracle's baseline tier: oracle T0 means "differs at baseline without injection" and should correspond to Q1 = changed; T1/T2 should correspond to Q1 = same, Q2 = changed.
- **Guards.** Oracle comparison is refused unless `--key` and `--confirm-reviews-complete` are both passed. If there are no ratings the tool prints PENDING and exits with code 3.
- **Pre-registration proposal (not a result and not an agreed threshold).** Before opening the key, fix in writing the decision rules, for example: inter-rater AC1 and κ lower CI bound ≥ 0.6 for the reviewer pool to be usable; oracle-vs-adjudicated agreement and the lower CI bound of specificity and sensitivity reported without a pass/fail cut-off; any oracle-DIFFERENT case that the adjudicated panel calls EQUIVALENT is individually inspected and traced to a lexer/model assumption in the audit.

---

## 6. Commands

```bash
cd /Users/manassakthivel/Desktop/finalSBG/RELIC

# Rebuild the sample deterministically (internal; reads results/final/raw/evaluation_records.jsonl)
PYTHONPATH=$PWD/src:$PWD .venv/bin/python reports/v2/review_package/make_sample.py

# Self-test of the statistics: SYNTHETIC ratings only, never touches real data
.venv/bin/python reports/v2/review_package/compute_agreement.py --self-test

# Real run, after both reviewers have returned files (inter-rater only; no key needed)
.venv/bin/python reports/v2/review_package/compute_agreement.py \
    --reviewer-a reviewer_A.csv --reviewer-b reviewer_B.csv

# Oracle comparison, only after reviews and adjudication are frozen
.venv/bin/python reports/v2/review_package/compute_agreement.py \
    --reviewer-a reviewer_A.csv --reviewer-b reviewer_B.csv \
    --key reports/v2/review_package/KEY_DO_NOT_SHARE.csv \
    --compare-oracle --confirm-reviews-complete
```

Other options: `--reviewer-c` (third reviewer; the tool then also computes the adjudicated label A==B → that label, else majority of A, B, C), `--field {overall_label,q1_normal_completion,q2_failure_scenarios}`, `--boot` (default 2000) and `--seed` (default 1). Run `compute_agreement.py --help` for the full text.

---

## 7. Limitations of the package

- **Cards leak the operator.** The diff itself shows what was changed (for example the inserted `MIGRATION REVIEW` comment, a `MSGCLASS` edit, a swapped step). Reviewers can infer the operator and guess the oracle's likely stance. Blindness is to the label and the RELIC prediction, not to the mutation.
- **The rubric defines the semantics.** `RUBRIC.md` fixes the observables (O1..O3 etc.), the single-fault failure scenarios and the treatment of several JOB cards in one file (rule 3: each JOB card is scheduled separately, any serial order, compare the set of behaviours), so that reviewers and oracle are judged against comparable definitions. The rubric does **not** state whether job names or the number of jobs are observable. The oracle's SPLIT_JOB positives (36.1% of all positives) differ at baseline largely because job names and count are embedded in its termination observable (audit F-04). Reviewers following the rubric are therefore expected to call many SPLIT_JOB cases EQUIVALENT; that disagreement would be informative, not a reviewer error. The review tests the oracle against a specification written by the same team plus independent reviewers' reading of it, not against real z/OS execution.
- **Small n.** 60 cases, 30 per class, yield wide CIs and no powered subgroup claims.
- **Missing context.** Program sources and PROCs are not available for every step on the cards (28.4% of steps are opaque to the oracle; cards show what exists). Reviewers will often judge from JCL alone and may answer `CANNOT_DETERMINE`.
- **Unverified IBM defaults.** The package cannot settle questions on which the reviewers themselves lack a reference (e.g. TXT2PDF1 first-step COND, U-01). See ambiguities U-01..U-10 in the audit.
- **Size.** The largest cards are about 115 KB.
- **Same-team risk.** If the reviewers are from the author team or use the same tooling, independence is weakened; record reviewer affiliation in the response file.

---

## 8. Unresolved ambiguities

Documented in the audit as U-01..U-10, including: IBM defaults for omitted DISP, COND semantics on the first step (the two TXT2PDF1 EQUIVALENT labels), opaque program models (IDCAMS, SORT, COBOL), SPLIT_JOB observable convention, and no IBM JCL documentation library being available for verification. They are not resolved by this package; independent reviewers may resolve some of them and should note any that they can cite a source for.

---

## 9. Status summary

| Item | Status |
|---|---|
| Sample (60 cards, key, blind form) | READY |
| Rubric, adjudication procedure, statistics tool | READY (self-tested on synthetic data only) |
| Reviewer A ratings | PENDING |
| Reviewer B ratings | PENDING |
| Third-reviewer / adjudication | PENDING |
| Reviewer–reviewer agreement | PENDING |
| Reviewer–oracle agreement | PENDING |
| Any claim that the oracle is independently validated | NOT SUPPORTED |
