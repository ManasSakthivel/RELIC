# AGENT 1 — Benchmark and Metrics Audit (RELIC V2)

Branch `research/relic-v2-integration`, HEAD `b690039`. Audit performed with independent code
(`/tmp/a1/a.py`, `b.py`, `c.py`, not committed) on the raw records
`results/final/raw/evaluation_records.jsonl` (656 rows, 566 EVALUABLE) and `results/v2/v2_predictions.jsonl`
(566 rows). `v2_eval.py` was **not** executed; no tracked file or `results/` was modified (`git status --short results` is empty).
Anything marked **[UNVERIFIED]** was not executed. Time budget was 7 minutes, so some items are shallow and flagged as such.

## 1. Verdict

* **Arithmetic is correct.** Every TP/FP/FN/TN for all 12 detectors × 4 populations (carddemo, genapp, omp_course, pooled)
  recomputed from raw records equals `results/v2/v2_metrics.json` and the pooled/per-subject entries of
  `reports/v2/BASELINE_METRICS.json` that exist there (0 discrepancies). F1 equal to 4 d.p.
  The v2 predictions file has the same 566 ids, the same truth label and operator as the raw records, and the 5 "committed"
  detectors in it are identical to `evaluation_records.jsonl` predictions (0 mismatches). No `None` predictions.
* **RELIC V2 F1 0.9800 (TP 442 FP 0 FN 18 TN 106) is verified** as an arithmetic fact on this benchmark.
* **It is not evidence of generality.** The benchmark's 460 positives are all produced by text edits that a
  comment/JOB-parameter-normalised text diff flags perfectly; that diagnostic gets F1 0.9978 (> V2) with zero understanding of JCL.
  Specificity measures "does not fire on comments/MSGCLASS", not semantic reasoning. The V2 fixes were derived by inspecting
  the same files (development set, labelled as such in the repo). The V2 − v1.1 gain is real on this benchmark
  but concentrated in 7 files with duplicate step names (mostly GenApp).
* Claims about "V2 vs v1.1" should be narrowed to "on the development benchmark, driven by D-001 on repeated-step-name files".

## 2. Recomputed table (pooled, n = 566; 460 pos / 106 neg) — independent recompute

| Detector | TP | FP | FN | TN | P | R | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| relic_v1_0 | 380 | 0 | 80 | 106 | 1.0000 | 0.8261 | 0.9048 |
| relic_v1_1 | 417 | 0 | 43 | 106 | 1.0000 | 0.9065 | 0.9510 |
| relic_v2 | 442 | 0 | 18 | 106 | 1.0000 | 0.9609 | 0.9800 |
| relic_v2_wo_D001 | 419 | 0 | 41 | 106 | 1.0000 | 0.9109 | 0.9534 |
| relic_v2_wo_D002 | 441 | 0 | 19 | 106 | 1.0000 | 0.9587 | 0.9789 |
| relic_v2_wo_D003 | 442 | 0 | 18 | 106 | 1.0000 | 0.9609 | 0.9800 |
| relic_v2_wo_D004 | 444 | 0 | 16 | 106 | 1.0000 | 0.9652 | 0.9823 |
| textdiff | 460 | 41 | 0 | 65 | 0.9182 | 1.0000 | 0.9573 |
| textdiff_ignore_job_parameters | 460 | 2 | 0 | 104 | 0.9957 | 1.0000 | 0.9978 |
| structural_A | 368 | 0 | 92 | 106 | 1.0000 | 0.8000 | 0.8889 |
| static_bcg_E | 380 | 0 | 80 | 106 | 1.0000 | 0.8261 | 0.9048 |
| complexity_B | 162 | 33 | 298 | 73 | 0.8308 | 0.3522 | 0.4947 |

Per subject (TP/FP/FN/TN → F1):

| Detector | CardDemo (254 pos / 61 neg) | GenApp (196 / 20) | OMP course (10 / 25) |
|---|---|---|---|
| relic_v1_0 | 216/0/38/61 → 0.9191 | 155/0/41/20 → 0.8832 | 9/0/1/25 → 0.9474 |
| relic_v1_1 | 245/0/9/61 → 0.9820 | 162/0/34/20 → 0.9050 | 10/0/0/25 → 1.0000 |
| relic_v2 | 249/0/5/61 → 0.9901 | 183/0/13/20 → 0.9657 | 10/0/0/25 → 1.0000 |
| v2 wo D001 | 245/0/9/61 → 0.9820 | 164/0/32/20 → 0.9111 | 10/0/0/25 → 1.0000 |
| v2 wo D002 | 250/0/4/61 → 0.9921 | 181/0/15/20 → 0.9602 | 10/0/0/25 → 1.0000 |
| v2 wo D003 | 249/0/5/61 → 0.9901 | 183/0/13/20 → 0.9657 | 10/0/0/25 → 1.0000 |
| v2 wo D004 | 251/0/3/61 → 0.9941 | 183/0/13/20 → 0.9657 | 10/0/0/25 → 1.0000 |
| textdiff | 254/31/0/30 → 0.9425 | 196/10/0/10 → 0.9751 | 10/0/0/25 → 1.0000 |
| textdiff_ignore_job_parameters | 254/2/0/59 → 0.9961 | 196/0/0/20 → 1.0000 | 10/0/0/25 → 1.0000 |
| structural_A | 206/0/48/61 → 0.8957 | 154/0/42/20 → 0.8800 | 8/0/2/25 → 0.8889 |
| static_bcg_E | 216/0/38/61 → 0.9191 | 155/0/41/20 → 0.8832 | 9/0/1/25 → 0.9474 |
| complexity_B | 93/9/161/52 → 0.5225 | 60/2/136/18 → 0.4651 | 9/22/1/3 → 0.4390 |

Micro (pooled) vs macro (mean of 3 subject F1): v1.1 0.9510 vs 0.9623; V2 0.9800 vs 0.9853; textdiff-ignore 0.9978 vs 0.9987.
Pooling is dominated by CardDemo (315) and GenApp (216); OMP contributes only 10 positives.

## 3. Discrepancies

* **Numerical discrepancies: none** between my recompute and `v2_metrics.json`, `EVALUATION_SUMMARY.md` (pooled table, subject F1s,
  flip counts 27/2, duplicate-step recall 0.391→0.766 / 0.990→0.992) or the `BASELINE_METRICS.json` entries for v1.0/v1.1/A/B/E/textdiff.
  (`BASELINE_METRICS.json` has no entries for V2/ablations/ignore-JP; it is a baseline file. OMP/GenApp blocks of that file
  were only compared if present — the automated comparison produced no mismatches.)
* Interpretive issues (not arithmetic):
  1. `static_bcg_E` is *byte-identical in confusion* to `relic_v1_0` pooled (380/0/80/106) and per subject — it is the same
     computation under another name, not an independent baseline.
  2. `EVALUATION_SUMMARY.md` does not disclose that 38 positives are labelled DIFFERENT only under failure injection (see §5/P1).
  3. v1.0 "legacy mode" and static_bcg_E are indistinguishable; counting both as separate systems overstates the baseline set.

## 4. Text-diff diagnostic explained (`textdiff_ignore_job_parameters`, F1 0.9978)

Implementation (`relic_eval/v2_eval.py::_normalise_job_parameters`): drops `//*` comment lines; reduces every JOB statement (and its
continuations) to `//NAME JOB`; flags iff the normalised line lists differ.

* **The 2 FPs** (both CardDemo `app/jcl/TXT2PDF1.JCL`): `.../ALTER_COND_THRESHOLD/0` (`COND=(0,NE)` → `COND=(4,NE)` on step TXT2PDF)
  and `.../REMOVE_COND/0` (COND deleted). The oracle labels both EQUIVALENT (9 and 7 scenarios checked; the guarded step cannot be
  bypassed in any modelled scenario). RELIC v1.1 and V2 do **not** flag these (so RELIC does beat the diagnostic on these 2).
* **Why it works:** negatives are 104/106 pure-cosmetic edits (65 `INSERT_COMMENT` + 39 `CHANGE_MSGCLASS`, the latter an edit of a JOB
  parameter) — exactly what the normaliser erases. The only other negatives are those 2 COND edits.
  The 460 positives come from 7 operators; each rewrites non-comment, non-JOB-parameter text:

| Operator | n eval | positives | textdiff-ignore flagged | v1.1 | V2 |
|---|---:|---:|---:|---:|---:|
| SPLIT_JOB | 166 | 166 | 166 | 158 | 166 |
| SWAP_ADJACENT_STEPS | 166 | 166 | 166 | 149 | 152 |
| ALTER_COND_THRESHOLD | 35 | 34 | 35 | 28 | 34 |
| REMOVE_COND | 35 | 34 | 35 | 28 | 34 |
| DELETE_PRODUCER_STEP | 33 | 33 | 33 | 32 | 33 |
| MOVE_CONSUMER_BEFORE_PRODUCER | 14 | 14 | 14 | 14 | 14 |
| RENAME_OUTPUT_DATASET | 13 | 13 | 13 | 8 | 9 |
| INSERT_COMMENT | 65 | 0 | 0 | 0 | 0 |
| CHANGE_MSGCLASS | 39 | 0 | 0 | 0 | 0 |

* **Quantification:** 460/460 positives (100 %) coincide with "a non-cosmetic text edit occurred" (every positive-generating operator
  always edits non-comment/non-JOB-parameter text; I verified the flag outcome per mutant, not the generator source — **[UNVERIFIED]**
  that the generator can never emit a cosmetic positive, but the empirical result is 460/460). 332 of those (SWAP + SPLIT = 332) are
  structural reorderings that change text *by construction*, and 332/460 = 72.2 % of all positives are SWAP/SPLIT.
  Label DIFFERENT ≡ "non-cosmetic text edit happened" in this benchmark with 2 exceptions out of 566 (precision 0.9957, recall 1.0000, i.e.
  agreement 564/566 = 99.6 %). The label is therefore *nearly equivalent* to the text-edit predicate; V2 is **less** accurate than it
  (18 FN vs 2 FP; boot CI of V2 − diagnostic is [−0.037, −0.003], i.e. V2 is significantly *worse* than the trivial rule on this benchmark).
* All 18 V2 FNs are positives that the trivial rule catches (18/18). Remaining V2 FNs: 13 GenApp SWAP, 1 CardDemo SWAP, 4 CardDemo RENAME_OUTPUT_DATASET.
* Caveat: the diagnostic was designed post hoc after inspecting the benchmark; it is a ceiling for a "no-semantics" rule, not a competitor.

## 5. Validity threats (ranked)

### P0
1. **Label/predicate near-identity (construct validity).** Positives = non-cosmetic structural edits; negatives = comments/MSGCLASS. The
   benchmark cannot distinguish semantic contract reasoning from textual edit detection (§4). A tool that flags any non-cosmetic
   edit reaches F1 0.9978. No negative class exercises semantically-neutral *non-trivial* edits (renaming a step consistently,
   reordering independent steps, equivalent DD rewrites). Only 2 of 106 negatives are non-cosmetic, and both come from one file.
2. **Development-time inspection / circularity.** V2 fixes D-001…D-004 were chosen by inspecting these very files (the repo says so).
   The 566-mutant result is a development fit, not a generalisation estimate. Gains are concentrated: 27 gained flags are in the
   same 7 duplicate-step files + GenApp-heavy (21 GenApp, 6 CardDemo gained; D-001 alone accounts for 23 of the flips, see §6).
3. **Shared lexer / oracle–detector coupling.** `jcl_oracle` (labels) and `legacy_contract` (detector) share the project's JCL
   handling; `v2_eval.py` imports `jcl_oracle.judge.describe_file` for contract recovery next to RELIC. I did not audit the shared
   lexer code — **[UNVERIFIED]** the degree of code sharing; the risk is that tokenisation errors are correlated between oracle and
   detector so they agree for the wrong reason. The oracle is a model-based simulation (scenario set), not real z/OS execution.

### P1
4. **38 positives are failure-injection-only.** 38 SWAP_ADJACENT_STEPS positives (33 GenApp, 5 CardDemo, all `F1_ORDERING`) have
   `oracle_result_no_abend == EQUIVALENT` but ground truth DIFFERENT (only under injected abends). A further 43 SWAP positives are
   `UNDETERMINED` without abends. So 81/166 SWAP positives (49 %) have weaker-than-normal oracle support. V2 flags 37/38 of the FI-only group (computed).
5. **SWAP and SPLIT are always labelled DIFFERENT** (166 + 166 = 332 / 460 = 72 % of positives, no negative SWAP/SPLIT). Non-independent
   of operator: recall is largely a function of two operators; there is no EQUIVALENT swap of independent steps in the benchmark.
6. **Non-independence of mutants within a file.** 566 mutants come from 66 files (median 5, max 62 per file; every file contributes
   negatives). The bootstrap resamples files (good), but pooled counts such as "566 evaluated" overstate the effective n. 7 files hold 64 positives
   (14 % of positives) and 62 of the 77 mutants in them are GenApp.
7. **Selection by non-evaluable exclusion.** 90 of 656 candidates were excluded: 41 `RENAME_OUTPUT_DATASET` OUT_OF_SCOPE (no consumer in the
   JCL), 23 `REMOVE_IF_GUARD` OUT_OF_SCOPE (IF/THEN/ELSE out of scope — the operator has zero evaluable mutants), 23 `SPLIT_JOB`
   INVALID (split inside IF/THEN/ELSE; all OMP), 3 `RENAME` INVALID (DSN too long). By subject: carddemo 38 OOS + 3 invalid; omp_course 26 OOS + 23 invalid
   (only 35 of 84 OMP candidates evaluable); genapp 0 excluded. Exclusions are determined by RELIC's declared scope, so IF/ELSE is silently out of the headline.
   RENAME_OUTPUT_DATASET: 13 evaluable of 57 (23 %).
8. **Negative class composition.** 106 negatives: 65 INSERT_COMMENT, 39 CHANGE_MSGCLASS, 1+1 COND edits. OMP: 25 negatives vs 10 positives (OMP F1 is on 10 positives).
9. **Baseline equivalence/under-spec.** `static_bcg_E` equals `relic_v1_0` in every cell (listed under §3); `complexity_B` is a weak baseline.

### P2
10. Pooled micro metrics vs per-subject: pooled weights CardDemo and GenApp; OMP effectively ignored (10 positives). Macro F1 gives slightly higher numbers.
11. V2 − v1.1 bootstrap lower CI bound 0.0034 is barely > 0 and does not account for fix-selection on the same files.
12. LLM comparison (not re-run) is selection-biased (per repo's own documentation; I did not re-verify `llm_records.jsonl` beyond reading its schema — **[UNVERIFIED]**).

## 6. D-004 ablation verification

* Pooled: V2 442 TP; V2 without D-004 444 TP (FN 16), FP 0 in both. **Verified.**
* The 2 mutants that flip (flagged by wo_D004, not by V2) are exactly the two V2 `lost_flags` and are the only differences:
  `carddemo/app/jcl/DUSRSECJ.jcl/RENAME_OUTPUT_DATASET/0` and `carddemo/app/jcl/ESDSRRDS.jcl/RENAME_OUTPUT_DATASET/0`.
  Both rename `DD01 DD DSN=...(PS)` to `...PS.MIG` in a `DISP=(MOD,DELETE,DELETE)` pre-delete step (`PREDEL.DD01`); the oracle labels them
  DIFFERENT (categories dataflow/execution/final_catalog/termination). D-004 treats the `(MOD,DELETE)` idiom as non-producing, so V2
  does not flag them. So D-004 trades 2 true positives for 0 benchmark-level false-positive reduction (FP is 0 with and without D-004);
  its benefit is in `contract_recovery` RESOURCE precision (CardDemo FP) only. The recorded F1 impact: 0.9800 vs 0.9823 (V2 lower).
  Per-subject: only CardDemo changes (249 vs 251 TP).
* Other ablations, computed: D-001 off → 23 positives lost (SPLIT 8, ALTER_COND 6, REMOVE_COND 6, SWAP 2, DELETE_PRODUCER 1); D-002 off → 5 differ
  (3 RENAME flagged only by V2, 2 flagged only by the ablation, net −1); **D-003 off → 0 predictions differ** (D-003 has no effect on any
  mutant detection — its justification is in RESOURCE contract recovery only).
* The v1.1→V2 gain is +25 TP net (27 gained, 2 lost). One-at-a-time ablation deltas are D-001 +23, D-002 +1, D-003 0, D-004 −2 (sum +22); the remaining +3 are interaction/baseline effects not decomposed (**[UNVERIFIED]** which). **D-001 is the only fix with material benchmark effect.**

## 7. Bootstrap verification

* Own implementation: file-clustered (66 clusters, resample files with replacement, sum per-file TP/FP/FN, F1 per rep), paired by using the same resampled index for
  both detectors, 10 000 reps, percentile CI using the same index rule as `relic_eval/metrics.py`:
  * V2 − v1.1, seed 20261004: **[0.0034, 0.0688]** (mean 0.0295; fraction of reps ≤ 0: 0.0078) — **identical to stored/`EVALUATION_SUMMARY.md`**.
  * seeds 1 and 7: [0.0038, 0.0687] and [0.0039, 0.0684] (robust to seed).
  * V2 − V2 wo D-004: [−0.0060, 0.0] (matches the stored value). V2 − textdiff_ignore: [−0.0373, −0.0032] (V2 significantly *worse*).
* Per-subject paired bootstrap of V2 − v1.1 (own code): CardDemo (31 files) [−0.0063, 0.0309] (includes 0; frac ≤ 0 = 0.235); GenApp (10 files)
  [0.0070, 0.1929]. OMP not computable (division by zero when v1.1 and V2 have no TP in a resample of 3 tiny files — my script crashed there; **not run to completion**).
  Interpretation: the "significant" pooled improvement is carried by GenApp's 10 files (7 of them duplicate-step files).
* The CI is a **sampling-of-files** CI only; it ignores that fixes were chosen on the same data, and the pooled micro F1 weights subjects by size. Pooling vs per-subject:
  pooled V2−v1.1 ΔF1 = +0.0290; CardDemo +0.0081; GenApp +0.0607; OMP 0.

## 8. LOSO view and duplicate-step stratification (reporting only, no tuning)

Leave-one-subject-out *report* (V2 was not retrained; only the pooled-rest vs held-out F1 shown). V2 is a fixed rule set, so the LOSO view is a presentation, not a validation.

| Held out | Rest-of-benchmark F1 v1.1 / V2 | Held-out F1 v1.1 / V2 |
|---|---|---|
| carddemo | 0.9101 / 0.9674 | 0.9820 / 0.9901 |
| genapp | 0.9827 / 0.9904 | 0.9050 / 0.9657 |
| omp_course | 0.9498 / 0.9796 | 1.0000 / 1.0000 |

V2 ≥ v1.1 in every held-out subject; the gap is much larger on GenApp (+0.061) than CardDemo (+0.008) and nil on OMP.

Files with duplicate step names (my regex on `//NAME EXEC`, matches parser-based counts in `v2_metrics.json`: 7 files, 64 positives):

| Stratum | files | n | pos / neg | v1.1 TP/FN → F1 | V2 TP/FN → F1 | textdiff-ignore |
|---|---:|---:|---|---|---|---|
| duplicate step names | 7 (62 GenApp, 14 CardDemo, 1 OMP mutants) | 77 | 64 / 13 | 25/39 → 0.5618 | 49/15 → 0.8673 | 64/0 (FP 0) → 1.0 |
| no duplicate names | 59 | 489 | 396 / 93 | 392/4 → 0.9949 | 393/3 → 0.9962 | 396/0, FP 2 → 0.9975 |

Outside the 7 duplicate-name files V1.1 and V2 are nearly identical (1 TP difference net). The V2 headline improvement is a 7-file effect (v1.1 recall 0.391 → V2 0.766 there).

## 9. Weaknesses of `tests/v2/test_v2_results.py` (read, **not executed**)

1. `test_committed_v2_results_equal_a_fresh_run` / `test_v2_run_is_deterministic` only prove that regenerating results with the same
   code gives the same bytes; they are circular — a bug in `confusion()`, `replay()` or the label read would be reproduced and pass.
2. No independent recomputation of TP/FP/FN/TN or F1; the only numeric assertions are `fp == 0`, `tp+fn == 460`, `gained_false_positives == 0`. It would not detect
   F1 0.980 turning into 0.97 or TN/FP drift in any other detector, nor ablation numbers (442/444).
3. No assertion on `textdiff_ignore_job_parameters` (caveat of D-014 is untested) nor on bootstrap CI values/seed/replicates or that the CI excludes 0.
4. No check that `reports/v2/EVALUATION_SUMMARY.md` numbers match `v2_metrics.json`; docs can drift.
5. `lost_flags` list is hard-coded and consistent with the current run only; tests the historical claim rather than invariants (e.g. gained/lost partition).
6. `test_v2_harness_output_directory_is_not_the_historical_one` only compares a constant, it does not detect writes to `results/final`.
7. Depends on datasets being present and re-runs the entire harness three times (slow, ~4 s each per the docstring); no test for missing-data handling.
8. No test that labels in `v2_predictions.jsonl` equal raw `ground_truth`, that exclusions (90) are the documented ones, or the 38 failure-injection positives.
9. The v1.1 equality is enforced *inside* `v2_eval.replay` (RuntimeError), but `v2_run_info.json` rewriting by the run is not guarded (running `v2_eval` modifies a tracked file).

## 10. Recommendations (claims to narrow)

1. Replace "V2 improves F1 from 0.951 to 0.980" with "on the development benchmark V2 improves recall on 7 duplicate-step-name files
   (v1.1 0.391 → 0.766); elsewhere ΔTP = +1". Report per-subject numbers first, pooled second; drop "significant" unless fix-selection is accounted for.
2. State prominently that a normalised text diff (F1 0.9978) beats V2 on this benchmark and that DIFFERENT ≈ "non-cosmetic edit" (564/566 agreement). Do not claim the benchmark measures semantic discrimination.
3. Disclose: 38 failure-injection-only + 43 UNDETERMINED SWAP positives; SWAP/SPLIT (72 % of positives) are always DIFFERENT; 90 candidates excluded by scope (IF/ELSE, no consumer).
4. Remove `static_bcg_E` as an independent baseline (identical to v1.0) or explain.
5. Describe D-003 as having zero effect on mutant detection, and D-004 as a net −2 TP trade-off on this benchmark.
6. Keep "development only; external validation pending"; any generalisation claim requires held-out JCL, a negative class with semantically-neutral structural edits, and an oracle independent of the detector's lexer.
7. Strengthen tests: add an independent confusion recomputation from `evaluation_records.jsonl`, pin the key numbers, and test the bootstrap.

## 11. Executed vs unverified summary

Executed: raw-record recompute of all confusion matrices; v2_predictions vs raw consistency; per-operator flag rates; ablation flip sets; textdiff-ignore FP identification;
failure-injection counts; exclusion accounting; paired file-cluster bootstrap (V2−v1.1 three seeds, V2−ignore, V2−wo_D004, per-subject CardDemo/GenApp); duplicate-step stratification (regex).
Unverified: shared-lexer degree; mutator generator source claims; LLM records beyond schema; OMP bootstrap; the test suite was not run; `v2_eval.py` was not re-run.
