# RELIC V2 complementarity and practical utility

Source of every number: `results/recovery/complementarity.json`, produced by `reports/recovery/scripts/complementarity.py` from `results/sembench/predictions.jsonl`, `benchmarks/sembench/cases.jsonl` and `results/external/predictions.jsonl` (EVALUABLE, n = 824). Rules are exactly those of `PREREGISTRATION.md` (UNION, INTERSECTION, FAST_TRACK; H2, H3, H4). H1 and Holm statistics are owned by another agent and are not repeated.

Limits that apply to everything below:
- Predictions are binary. There is one operating point per detector, so no PR curve, threshold sweep or "recall at fixed precision" exists, and none is shown.
- The oracle is same-author and unvalidated; the external run is not blind; aggregate results were known before the pre-registration was written. Nothing here is confirmatory.
- CIs are Wilson (proportions) and a percentile cluster bootstrap (10,000 resamples, seed 20261004; `base_id` for SemBench, 15-16 clusters; `repo` for external, 7 clusters, so very coarse). No p-values are computed.

## 1. Headline

1. **H2 is rejected.** RELIC-only true positives = 0 in all four SemBench populations and in the external set, against every text baseline. RELIC's flagged set is a strict subset of the text-flagged set everywhere. There is no case in this data where RELIC detects a true change that text misses.
2. **H3 is not rejected on the external data** (pooled 658/658, Wilson lower bound 0.994; every repo with >= 20 flagged items has lower bound >= 0.912, which is above the 0.90 threshold). H3 is silent about SemBench, where RELIC precision is 23/25 = 0.92 (Wilson 0.75-0.98) on ALL_180 and 23/23 on CLEAN_CORE.
3. **H4 is rejected on SemBench in all four populations and met on the external set.** SemBench FAST_TRACK avoids 23.6% of reviews (25/106; bootstrap 95% CI 0.12-0.33), below the 30% bar, with 2 wrongly accepted items. External FAST_TRACK avoids 94.8% (658/694) with 0 wrongly accepted. The external pass depends on a non-blind run and a same-author oracle (section 6).
4. Where RELIC adds something over the text baseline it is **precision, not detection**: it removes text false positives (SemBench 26 of 28 normalized_text_B false positives; external 3 of 3), at the price of missing most true changes on SemBench (INTERSECTION recall 0.247 on ALL_180, 0.343 on CLEAN_CORE).

## 2. Overlap, RELIC V2 vs normalized text baseline (by oracle truth)

Primary baselines: SemBench `normalized_text_B`; external `textdiff_ignore_job_parameters`.

| Population | Truth | Both | RELIC-only | Text-only | Neither |
|---|---|---:|---:|---:|---:|
| SemBench ALL_180 (93 changing / 87 preserving) | changing | 23 | 0 | 55 | 15 |
| | preserving | 2 | 0 | 26 | 59 |
| SemBench EXCL_25_IDENTICAL (155; 78 / 77) | changing | 23 | 0 | 55 | 0 |
| | preserving | 2 | 0 | 26 | 49 |
| SemBench EXCL_15_NOOP_CHANGING_ONLY (165; 78 / 87) | changing | 23 | 0 | 55 | 0 |
| | preserving | 2 | 0 | 26 | 59 |
| SemBench CLEAN_CORE (141; 67 / 74) | changing | 23 | 0 | 44 | 0 |
| | preserving | 0 | 0 | 25 | 49 |
| External EVALUABLE (824; 691 / 133) | changing | 658 | 0 | 33 | 0 |
| | preserving | 0 | 0 | 3 | 130 |

The 15 "neither" changing items in ALL_180 are the 15 byte-identical pairs labelled CHANGING, which `PREREGISTRATION.md` calls provably mislabelled. They disappear in the other populations. They are the only reason ALL_180 text recall is below 1.

Sensitivity (normalized_text_A, textdiff; external textdiff) gives the same RELIC-only counts (0 and 0) and the same RELIC columns. Only the text-only-preserving cells grow (SemBench: 33 for A, 58 for textdiff; external textdiff: 62). Full tables are in the JSON.

**Precision of the RELIC-only subset: undefined. The denominator is 0** (RELIC-only true positives 0, RELIC-only false positives 0) in every population and every baseline. No precision, CI or bootstrap exists for it; the bootstrap field is absent for the same reason.

Per-repo overlap (external): in all seven repos RELIC-only = 0. Text-only true changes are concentrated in `yetacp_mvs_sysgen` (29 of 33), `mainframed_Enumeration` (1) and `zowe_zowe-cli` (3 of 4 positives); in the other four repos RELIC and text agree on every item.

## 3. Hybrid rules (pre-registered)

Recall is over changing items, precision over flagged items; Wilson 95% in brackets.

| Population | UNION recall / precision | INTERSECTION recall / precision |
|---|---|---|
| SemBench ALL_180 | 0.839 [0.75, 0.90] / 0.736 [0.65, 0.81] | 0.247 [0.17, 0.34] / 0.920 [0.75, 0.98] |
| SemBench EXCL_25_IDENTICAL | 1.000 [0.95, 1] / 0.736 | 0.295 [0.21, 0.40] / 0.920 |
| SemBench EXCL_15_NOOP_CHANGING_ONLY | 1.000 / 0.736 | 0.295 / 0.920 |
| SemBench CLEAN_CORE | 1.000 [0.95, 1] / 0.728 [0.63, 0.81] | 0.343 [0.24, 0.46] / 1.000 [0.86, 1] |
| External pooled | 1.000 [0.994, 1] / 0.9957 [0.987, 0.999] | 0.952 [0.934, 0.966] / 1.000 [0.994, 1] |

UNION equals the text baseline in every population (RELIC adds no detections), so it is never better than text alone. INTERSECTION trades 65-75% of SemBench recall for precision. On the external set it loses 33 true changes (4.8%) to remove 3 false positives. An INTERSECTION with recall 0.25-0.34 on SemBench is not acceptable as a change-safety gate.

### FAST_TRACK (text flags all; RELIC-confirmed items accepted unreviewed; the rest reviewed by an assumed-correct human)

Two readings of "wrongly accepted <= 1%" are reported because the pre-registration does not fix the denominator; both give the same H4 verdict everywhere.

| Population | Text-flagged | Accepted w/o review | Reviews avoided | Wrongly accepted | Wrong / accepted | Wrong / text-flagged | H4 (>= 30% and <= 1%) |
|---|---:|---:|---|---:|---|---|---|
| SemBench ALL_180 | 106 | 25 | 23.6% [16.5, 32.5]; boot [12.0, 33.1] | 2 | 8.0% [2.2, 25.0] | 1.9% [0.5, 6.6] | rejected |
| SemBench EXCL_25_IDENTICAL | 106 | 25 | 23.6% | 2 | 8.0% | 1.9% | rejected |
| SemBench EXCL_15_NOOP_CHANGING_ONLY | 106 | 25 | 23.6% | 2 | 8.0% | 1.9% | rejected |
| SemBench CLEAN_CORE | 92 | 23 | 25.0% [17.3, 34.7]; boot [13.0, 35.1] | 0 | 0.0% [0, 14.3] | 0.0% [0, 4.0] | rejected (saving < 30%) |
| External pooled | 694 | 658 | 94.8% [92.9, 96.2]; boot [92.8, 99.1] | 0 | 0.0% [0, 0.6] | 0.0% [0, 0.6] | met |

Notes:
- SemBench CLEAN_CORE has 0 wrongly accepted but a 95% upper bound of 14.3% (of accepted), so "0%" is weak evidence. The saving point estimate (25%) is below 30%; the bootstrap upper bound (35%) touches the bar, so the SemBench saving is not decisively below 30%, but nothing in the data supports reaching it.
- The 2 wrongly accepted SemBench items are `sembench_078` and `sembench_079` (`unreferenced_step_rename`), both flagged `oracle_disagrees = true`. The "false positives" are the cases where the oracle disagrees with the expected label, so they may not be RELIC errors at all.
- Per repo (external): met in every repo with a non-trivial queue except `zowe_zowe-cli` (1 of 4 avoided, n = 6, uninformative). Per-repo values are in the JSON.
- FAST_TRACK does not change what the pipeline misses. Items text does not flag are never reviewed, so FAST_TRACK recall equals text recall by construction (SemBench ALL_180: 15 changing items unseen, all mislabelled identical pairs).
- Review queue left for humans: SemBench 81 items (55 truly changing, 26 preserving); external 36 items (33 truly changing, 3 preserving).

### Pre-registered verdicts

| Hypothesis | Verdict | Evidence |
|---|---|---|
| H2 complementarity | **Rejected** (RELIC-only TP = 0) | 0 in all 4 SemBench populations and external, for all text baselines |
| H3 triage precision >= 0.95 (external only) | **Not rejected** | pooled 658/658, LB 0.994; repos with >= 20 flagged: zopeneditor 40 (LB 0.912), Enumeration 49 (0.927), brexx 53 (0.932), zECS 44 (0.920), sysgen 465 (0.992); dbb (6) and zowe (1) are below the 20-item threshold and do not count |
| H4 FAST_TRACK >= 30% avoided, <= 1% wrong | **Rejected on SemBench; met on external** | see table; the pre-registration does not say which population is primary for H4 |

## 4. Where RELIC fires (exploratory)

SemBench ALL_180, by category (RELIC flags / changing items): `step_reorder_dependent` 9/14, `cond_logic_change` 6/18, `producer_consumer_change` 6/12, `dataset_dependency_change` 1/17, `disp_change` 1/19, `return_code_effect` 0/13. RELIC never flags comment, whitespace, syntax-representation, job-card or independent-reorder variants (all preserving), apart from the two `unreferenced_step_rename` false positives noted above.

RELIC-easy on SemBench = dependent step order, producer/consumer removal and COND logic. RELIC-hard = dataset-disposition, DISP and return-code effects (0-1 detections of 13-19 each). The text baseline flags 12/13 return-code and 16/19 DISP items that RELIC misses.

External, by operator (RELIC flags / true changes): `DELETE_PRODUCER_STEP` 40/40, `MOVE_CONSUMER_BEFORE_PRODUCER` 25/25, `ALTER_COND_THRESHOLD` 25/27, `REMOVE_COND` 25/28, `SWAP_ADJACENT_STEPS` 260/268, `SPLIT_JOB` 260/274, `RENAME_OUTPUT_DATASET` 23/29. The 33 misses are spread across operators (by failure category: F1_ORDERING 22, F2_DATASET 6, F3_RETURN_CODE 5). The negative-refactor operators (comment, MSGCLASS; 130 items) are flagged by neither detector.

**Are RELIC's flags the easy items for any detector?** Largely yes. For each changing item I counted how many of the *other* detectors flag it. RELIC-caught items: mean 6.65 of 7 other SemBench detectors, vs 3.93 for RELIC-missed (5.00 on CLEAN_CORE). External: 3.91 of 4 for RELIC-caught vs 2.00 for RELIC-missed. 15 of 23 SemBench and 612 of 658 external RELIC detections are flagged by every other detector. No RELIC detection is missed by all other detectors (0 in both sets), consistent with H2. RELIC fires on items that are easy for everyone and abstains on the harder ones.

The exploratory splits are descriptive, small-cell (many cells have n < 20 or no changing items), and not tested.

## 5. Could RELIC be a second-stage semantic verifier?

What the data allow:
- As a *filter on text flags* (the only direction the data support), RELIC removes 26 of 28 SemBench text false positives and all 3 external ones, and its flagged set has precision 0.92 (SemBench) and 1.0 (external). It never contributes a detection.
- The hard part is the other side of the filter: 55 of 78 SemBench true changes (70.5%) fall in the text-only cell, so a pipeline that accepts only RELIC-confirmed items loses most true changes (recall 0.25 / 0.34). On the external set the loss is 33 of 691 (4.8%).
- A *verifier* is useful only if it would auto-accept without human review. Under FAST_TRACK the SemBench saving is 24-25% with an uncertainty range that includes the 30% bar but is centred below it, and the value comes from accepting 25 items whose label noise (2 oracle-disagreement cases) is part of the error budget. The external saving (94.8%) is on a corpus where text is already 99.6% precise against the oracle (694 flagged, 3 wrong), so the human review being avoided is almost entirely of true positives; the practical value of removing that review is small and entirely rests on trusting RELIC's development-set precision.

**Conclusion supported by the data:** at most "RELIC's agreement with a text change is a high-precision signal on this oracle's labels". The data do not show an operational benefit: SemBench denominators for the accepted set are 23-25 items, the saving is below the pre-registered bar, and external results are not blind. I do not claim operational utility.

## 6. What a skeptic would say

1. **RELIC's flagged set is a strict subset of the text-flagged set**, so every "saving" is the decision to trust RELIC's precision without review. That precision (0.92-1.0) is measured on data RELIC was developed against, with an oracle written by the same author. The savings are an estimate of "how often RELIC and the oracle agree", not of independent error rates.
2. **The oracle may share RELIC's semantics.** External "truth" is dominated by mutation operators that always edit the text, so text recall is 1.0 by construction there. High external RELIC precision is then close to a statement that RELIC's contract model and the oracle's execution model coincide on mutations designed by the same author. Neither the SemBench labels nor the external labels were independently validated (60-case package: zero returned human labels).
3. **No held-out data.** External was run after development and was not blind; none of the results qualify as confirmatory.
4. **H2 failure is robust, H4 pass is fragile.** H2 fails against four populations and three text baselines. The external H4 pass has a 95% bootstrap interval from 7 repo clusters, 589 of 824 items coming from one repo (`yetacp_mvs_sysgen`), so it is mostly one repo's result.
5. **Small denominators.** The SemBench accepted set is 23-25 items from 15-16 base programs; the 0 wrongly accepted on CLEAN_CORE has a Wilson upper bound of 14.3%. The 2 SemBench false positives are on oracle-disagreement cases, which can be read both ways (RELIC wrong, or label wrong); I have not resolved that.
6. **Fewer false alarms is the only measurable advantage**, and the comparison baseline is a text diff after normalization. A trivial baseline that suppresses well-known benign edits (whitespace, comments, independent-statement reorder, formatting) would also remove many of the 26 SemBench text false positives (e.g. 11 independent-reorder and 13 syntax-representation false positives); I did not test such a baseline. The advantage might disappear against it.
7. **Intersection loses most real changes on SemBench.** A reviewer cannot use RELIC alone as a gate (recall 0.25 of all, 0.34 on CLEAN_CORE).

## 7. Comparison count and what is exploratory

- Pre-registered rule tables: 3 rules (UNION, INTERSECTION, FAST_TRACK) x primary baseline x (4 SemBench populations + external pooled + 7 external repos) = 36 cells; each is reported, none selected.
- Sensitivity baselines (same 3 rules): 2 extra SemBench baselines x 4 populations + 1 extra external baseline = 9 table blocks; labelled sensitivity.
- Exploratory (labelled in JSON): per-category splits (12), per-failure-category (4), per-operator (9), per-contract-type (4), easiness (3 runs), cluster bootstrap CIs (5 intervals families). No hypothesis test beyond H2, H3, H4; no p-values.
- H5 (explanatory value): not testable from binary predictions; untested.

## 8. Not done
- No threshold/PR analysis (impossible, binary predictions).
- No test against a stronger rule-based non-text baseline (see 6.6).
- No investigation of whether `sembench_078/079` or the 33 external RELIC misses are RELIC bugs or label errors.
- Cluster bootstrap on repo uses only 7 clusters; treat as indicative.
