# Statistical reanalysis: RELIC V2 vs text baselines

Script: `reports/recovery/scripts/stats_reanalysis.py`. Output: `results/recovery/stats_reanalysis.json`.
Run it from the repo root with `PYTHONPATH=src python reports/recovery/scripts/stats_reanalysis.py`. It takes about 2 s, is deterministic, and uses seed 20261004 with 10,000 resamples.
Inputs (all committed, none modified): `results/sembench/predictions.jsonl` plus `benchmarks/sembench/cases.jsonl`, `results/external/predictions.jsonl` (rows with `status == EVALUABLE`), and the published `results/sembench/{metrics,paired_tests}.json` and `results/external/metrics.json`.
This analysis computes no hybrid, union, intersection or fast-track result. H4 belongs to the complementarity analysis.

## 0. Status of every analysis here

**Nothing in this document is confirmatory.** The pre-registration was written after the aggregate SemBench and external results were already known, and it says so itself. It fixes the analysis rules but cannot make tests on already-seen data confirmatory.

The status of each analysis:
- **H1–H3 under their stated rules:** rule-bound but post hoc. They are the closest thing here to a confirmatory reading.
- **Everything else:** exploratory. This covers the sensitivity populations, per-category, per-repo and per-operator strata, the cluster sign-flip test, repo-level clustering and the global Holm family.

**What cannot be computed.** Every detector emits a binary flag only. There is no score, rank or confidence, so each detector has exactly one operating point. As a result:
- No precision–recall curve, ROC curve, AUC, average precision or threshold sweep exists, and none can be drawn.
- No calibration analysis is possible.
- No "RELIC at matched recall" comparison is possible.

Anyone wanting these would have to change the detectors to emit scores and re-run them on held-out data.

## 1. Reproduction of the published numbers

The script uses its own implementation, written independently of `relic_eval`.

| Published claim | Source | Reproduced | Match |
|---|---|---|---|
| SemBench ALL, MCC: relic_v2 0.3241 vs normalized_text_B 0.5249 | metrics.json | 0.3241 vs 0.5249 | exact |
| Same, cluster-bootstrap MCC CIs [0.248, 0.3816] / [0.4201, 0.629]; F1, BA and all 6 detectors | metrics.json | identical to 4 dp | exact |
| relic_v2 vs normalized_text_B: discordant 26:55, exact McNemar p = 0.001689, **Holm p = 0.020268**, ΔMCC −0.2008 [−0.2992, −0.1018] | paired_tests.json | 26:55, p = 0.0016886, Holm(14) = 0.020268, −0.2008 [−0.2992, −0.1018] | exact |
| All 42 SemBench paired tests (ALL, VALIDATED, ORACLE_DISAGREES × 14 pairs) | paired_tests.json | 42/42 | exact (counts, p, Holm, ΔMCC point and CI) |
| External pooled F1: relic_v2 0.9755, textdiff_ignore_job_parameters 0.9978, textdiff 0.9571 | ext metrics.json | same | exact |
| External file-cluster F1 CIs [0.9559, 0.9892] / [0.9939, 1.0]; ΔF1 vs ignore-params [−0.0422, −0.0081] | ext metrics.json | same, using the repo's `random.Random` method | exact |
| External excluding yetacp_mvs_sysgen (n = 235): F1 0.9897 / 0.9949; ΔF1 [−0.0265, 0.0096] | ext metrics.json | same | exact |
| CANONICAL_NUMBERS.json confusion matrices (4 populations × 6 detectors) | canonical | asserted in the script | exact |

**Every published number reproduces from the raw predictions, so there are no numerical discrepancies.** The problems are in how the numbers are specified and reported (§5), not in the arithmetic.

Two reporting facts need correcting, because they describe the published numbers inaccurately:
1. **"MCC 0.525 vs 0.324" is the text baseline beating RELIC,** not the reverse. 0.525 is normalized_text_B and 0.324 is relic_v2.
2. **"External F1 0.9978 vs 0.9755" is also the text baseline beating RELIC.** 0.9978 is textdiff_ignore_job_parameters and 0.9755 is relic_v2. The published paired ΔF1 CI [−0.042, −0.008] excludes 0 in the baseline's favour.

## 2. SemBench: four pre-registered populations plus two sensitivity populations

There are 16 `base_id` clusters in all; the bootstrap resamples `base_id`. The confusion cells are TP/FP/FN/TN. Proportion intervals are Wilson 95%, which ignore clustering. MCC, F1 and balanced-accuracy (BA) intervals are cluster-bootstrap percentile 95%.

### 2.1 Detector metrics: relic_v2 vs the primary comparator normalized_text_B

| Population | n (chg) | Detector | TP/FP/FN/TN | Precision [Wilson] | Recall [Wilson] | Specificity [Wilson] | F1 [boot] | MCC [boot] | BA [boot] |
|---|---|---|---|---|---|---|---|---|---|
| ALL_180 | 180 (93) | relic_v2 | 23/2/70/85 | 0.920 [0.750, 0.978] | 0.247 [0.171, 0.344] | 0.977 [0.920, 0.994] | 0.390 [0.232, 0.493] | 0.324 [0.248, 0.382] | 0.612 [0.564, 0.649] |
| | | text_B | 78/28/15/59 | 0.736 [0.645, 0.810] | 0.839 [0.751, 0.900] | 0.678 [0.574, 0.767] | 0.784 [0.729, 0.833] | 0.525 [0.420, 0.629] | 0.758 [0.707, 0.810] |
| EXCL_25_IDENTICAL | 155 (78) | relic_v2 | 23/2/55/75 | 0.920 [0.750, 0.978] | 0.295 [0.205, 0.404] | 0.974 [0.910, 0.993] | 0.447 [0.281, 0.543] | 0.365 [0.284, 0.424] | 0.634 [0.580, 0.672] |
| | | text_B | 78/28/0/49 | 0.736 [0.645, 0.810] | 1.000 [0.953, 1.000] | 0.636 [0.525, 0.735] | 0.848 [0.804, 0.892] | 0.684 [0.604, 0.764] | 0.818 [0.770, 0.865] |
| EXCL_15_NOOP_CHANGING_ONLY | 165 (78) | relic_v2 | 23/2/55/85 | 0.920 [0.750, 0.978] | 0.295 [0.205, 0.404] | 0.977 [0.920, 0.994] | 0.447 [0.281, 0.544] | 0.379 [0.293, 0.440] | 0.636 [0.580, 0.675] |
| | | text_B | 78/28/0/59 | 0.736 [0.645, 0.810] | 1.000 [0.953, 1.000] | 0.678 [0.574, 0.767] | 0.848 [0.804, 0.891] | 0.706 [0.636, 0.784] | 0.839 [0.800, 0.883] |
| CLEAN_CORE | 141 (67) | relic_v2 | 23/0/44/74 | 1.000 [0.857, 1.000] | 0.343 [0.241, 0.463] | 1.000 [0.951, 1.000] | 0.511 [0.314, 0.638] | 0.464 [0.327, 0.563] | 0.672 [0.593, 0.734] |
| | | text_B | 67/25/0/49 | 0.728 [0.630, 0.809] | 1.000 [0.946, 1.000] | 0.662 [0.549, 0.759] | 0.843 [0.794, 0.889] | 0.694 [0.614, 0.772] | 0.831 [0.783, 0.875] |
| SENS: excl 14 non-identical disagreements (incl. oracle abstain 172) | 166 (82) | relic_v2 | 23/0/59/84 | 1.000 [0.857, 1.000] | 0.281 [0.195, 0.386] | 1.000 [0.956, 1.000] | 0.438 [0.253, 0.571] | 0.406 [0.280, 0.503] | 0.640 [0.572, 0.700] |
| | | text_B | 67/25/15/59 | 0.728 [0.630, 0.809] | 0.817 [0.720, 0.886] | 0.702 [0.598, 0.790] | 0.770 [0.709, 0.823] | 0.522 [0.408, 0.630] | 0.760 [0.703, 0.813] |
| SENS: excl 13 non-identical ORACLE_DISAGREES | 167 (83) | relic_v2 | 23/0/60/84 | 1.000 [0.857, 1.000] | 0.277 [0.192, 0.382] | 1.000 [0.956, 1.000] | 0.434 [0.250, 0.567] | 0.402 [0.276, 0.499] | 0.639 [0.571, 0.698] |
| | | text_B | 68/25/15/59 | 0.731 [0.633, 0.811] | 0.819 [0.723, 0.887] | 0.702 [0.598, 0.790] | 0.773 [0.711, 0.825] | 0.525 [0.410, 0.632] | 0.761 [0.704, 0.814] |

Metrics for the other baselines (normalized_text_A, textdiff_ignore_job_parameters, textdiff, raw_text) in every population are in the JSON under `sembench.populations.*.detectors`.

raw_text has undefined MCC in EXCL_25 and CLEAN_CORE, because it flags every case there and so has TN = 0. That shows as `null` with 10,000 undefined bootstrap reps.

### 2.2 Paired comparisons: relic_v2 minus baseline

The columns are:
- **Disc a:b:** RELIC right and baseline wrong : RELIC wrong and baseline right, counted per case.
- **McNemar p:** exact, unadjusted.
- **Holm (m = 42 distinct):** the global Holm family, deduplicated; see §4.
- **Sign-flip p:** an exact cluster-level permutation test over `base_id` (§5).
- **ΔMCC, ΔF1:** point estimate with paired cluster-bootstrap 95% CI.

| Population | Baseline | Disc a:b | McNemar p | Holm (m = 42 distinct) | Sign-flip p | ΔMCC [95%] | ΔF1 [95%] |
|---|---|---|---|---|---|---|---|
| ALL_180 | **text_B** | 26:55 | 0.0017 | 0.054 | 0.0020 | **−0.201 [−0.299, −0.102]** | −0.394 [−0.533, −0.307] |
| ALL_180 | text_A | 33:55 | 0.025 | 0.62 | 0.0049 | −0.127 [−0.219, −0.033] | −0.367 [−0.508, −0.278] |
| ALL_180 | textdiff_ignore_job_params | 47:55 | 0.49 | 1 | 0.24 | +0.022 [−0.077, 0.120] | −0.319 [−0.464, −0.226] |
| ALL_180 | textdiff | 58:55 | 0.85 | 1 | 0.76 | +0.148 [0.038, 0.247] | −0.285 [−0.432, −0.192] |
| ALL_180 | raw_text | 75:55 | 0.095 | 1 | 0.020 | +0.391 [0.254, 0.526] | −0.239 [−0.383, −0.145] |
| EXCL_25_IDENTICAL | **text_B** | 26:55 | 0.0017 | 0.054 (same test) | 0.0020 | **−0.319 [−0.431, −0.230]** | −0.401 [−0.562, −0.307] |
| EXCL_25_IDENTICAL | textdiff_ignore_job_params | 47:55 | 0.49 | 1 | 0.24 | −0.107 [−0.206, −0.024] | −0.314 [−0.479, −0.214] |
| EXCL_25_IDENTICAL | textdiff | 58:55 | 0.85 | 1 | 0.76 | +0.012 [−0.086, 0.083] | −0.276 [−0.441, −0.176] |
| EXCL_15_NOOP_CHANGING_ONLY | **text_B** | 26:55 | 0.0017 | 0.054 (same test) | 0.0020 | **−0.328 [−0.435, −0.245]** | −0.401 [−0.562, −0.305] |
| CLEAN_CORE | **text_B** | 25:44 | 0.030 | 0.71 | 0.0098 | **−0.230 [−0.370, −0.129]** | −0.332 [−0.518, −0.212] |
| CLEAN_CORE | textdiff_ignore_job_params | 46:44 | 0.92 | 1 | 0.89 | −0.010 [−0.161, 0.100] | −0.233 [−0.431, −0.102] |
| CLEAN_CORE | textdiff | 57:44 | 0.23 | 1 | 0.19 | +0.112 [−0.036, 0.216] | −0.191 [−0.390, −0.058] |
| SENS excl 14 | **text_B** | 25:44 | 0.030 | 0.71 (same test as CLEAN_CORE) | 0.0098 | **−0.117 [−0.231, −0.017]** | −0.332 [−0.494, −0.218] |
| SENS excl 13 | **text_B** | 25:45 | 0.023 | 0.58 | 0.0093 | **−0.123 [−0.239, −0.022]** | −0.339 [−0.501, −0.224] |

The full 6 × 5 grid, including ΔBA and the class-wise discordant counts, is in the JSON. Four points about this table:

- **Discordances split perfectly by class.** Against every baseline, in every population, all cases where the baseline is right and RELIC is wrong are *changing* cases: RELIC misses changes that the text baseline catches. All cases where RELIC is right are *preserving* cases: the text baseline raises false alarms that RELIC avoids. RELIC never catches a change the baseline misses (RELIC-only TP = 0 everywhere). The comparison is therefore purely "baseline recall vs RELIC specificity". Accuracy-based McNemar weights these by class prevalence (§5).
- **Identical pairs cannot change McNemar.** No detector flags any of the 25 byte-identical pairs. Those pairs are therefore concordant for every pair of detectors, so the discordant counts and p-values in ALL_180, EXCL_25 and EXCL_15 are the same test, not three independent confirmations. Only MCC, F1 and the bootstrap move.
- **Excluding the 25 identical pairs widens RELIC's deficit.** ΔMCC moves from −0.20 to −0.32. The 15 identical pairs labelled CHANGING are false negatives for *every* detector, so removing them helps the high-recall text baseline more.
- **Excluding the 13–14 non-identical oracle disagreements roughly halves the deficit,** from −0.20 to about −0.12, but the CI still excludes 0. RELIC's 2 SemBench false positives are both inside that set, and its precision becomes 23/23.

### 2.3 Per category (ALL_180, relic_v2 vs normalized_text_B; exploratory)

Most categories contain only one class, so MCC and specificity, or recall, are undefined and are reported as NA rather than 0.

| Category | n (chg) | relic TP/FP/FN/TN | text_B TP/FP/FN/TN | Disc a:b | McNemar p | Holm (42) |
|---|---|---|---|---|---|---|
| cond_logic_change | 18 (18) | 6/0/12/0 | 18/0/0/0 | 0:12 | 0.00049 | 0.017 |
| dataset_dependency_change | 17 (17) | 1/0/16/0 | 11/0/6/0 | 0:10 | 0.0020 | 0.061 |
| disp_change | 19 (19) | 1/0/18/0 | 17/0/2/0 | 0:16 | 3.1e-5 | 0.0012 |
| producer_consumer_change | 12 (12) | 6/0/6/0 | 6/0/6/0 | 0:0 | 1 | 1 |
| return_code_effect | 13 (13) | 0/0/13/0 | 12/0/1/0 | 0:12 | 0.00049 | 0.017 |
| step_reorder_dependent | 14 (14) | 9/0/5/0 | 14/0/0/0 | 0:5 | 0.062 | 1 |
| comment_edit | 17 (0) | 0/0/0/17 | 0/0/0/17 | 0:0 | 1 | 1 |
| independent_statement_reorder | 14 (0) | 0/0/0/14 | 0/11/0/3 | 11:0 | 0.00098 | 0.032 |
| job_card_refactor | 12 (0) | 0/0/0/12 | 0/0/0/12 | 0:0 | 1 | 1 |
| syntax_representation | 21 (0) | 0/0/0/21 | 0/13/0/8 | 13:0 | 0.00024 | 0.0088 |
| unreferenced_step_rename | 6 (0) | 0/2/0/4 | 0/2/0/4 | 0:0 | 1 | 1 |
| whitespace_and_continuation | 17 (0) | 0/0/0/17 | 0/2/0/15 | 2:0 | 0.5 | 1 |

## 3. External (EVALUABLE, n = 824, 691 positive / 133 negative)

**Repository count.** The external data covers **7 repositories with evaluable mutants, not 11.** The other repositories contributed zero evaluable mutants:
- **MartinPacker_Db2-DDF-Analysis-Tool, zosconnect_zosconnect-sample-wola-batch, zowe_zowe-install-packaging:** 0 eligible files, because of `NO_JOB_STATEMENT` or `FEWER_THAN_2_EXEC_STEPS` (per `metrics.json → accounting`).
- **cschneid-the-elder_mapa:** appears only in `robustness` and `unsupported_syntax_prevalence`, with no accounting or mutation rows.

No per-repository statistics exist for these four, and none are reported here.

**Concentration.** yetacp_mvs_sysgen supplies 589 of the 824 rows (71%) and 29 of RELIC's 33 false negatives.

### 3.1 Pooled results and clustering choice

The primary clustering is the source file (71 clusters), which matches the repo. Mutants of the same file share structure, so file is the smallest defensible independent unit.

Repository clustering (7 clusters) is reported as well, because repositories differ systematically: yetacp alone drives the result. With only 7 very unequal clusters, though, the repo bootstrap is *descriptive only*. Its percentile CIs are unreliable and its sign-flip test has at most 2^4 sign patterns.

| Set | Detector | TP/FP/FN/TN | Precision [Wilson] | Recall [Wilson] | Specificity [Wilson] | F1 [file boot] | F1 [repo boot] | MCC [file boot] | MCC [repo boot] |
|---|---|---|---|---|---|---|---|---|---|
| Pooled 824 | relic_v2 | 658/0/33/133 | 1.000 [0.994, 1.000] | 0.952 [0.934, 0.966] | 1.000 [0.972, 1.000] | 0.976 [0.956, 0.989] | [0.967, 0.998] | 0.874 [0.807, 0.937] | [0.839, 0.989] |
| | text_ignore_job_params | 691/3/0/130 | 0.996 [0.987, 0.999] | 1.000 [0.995, 1.000] | 0.977 [0.936, 0.992] | 0.998 [0.994, 1.000] | [0.989, 1.000] | 0.987 [0.965, 1.000] | [0.935, 1.000] |
| | textdiff | 691/62/0/71 | 0.918 [0.896, 0.935] | 1.000 [0.995, 1.000] | 0.534 [0.449, 0.617] | 0.957 [0.943, 0.967] | [0.942, 0.988] | 0.700 [0.675, 0.725] | [0.668, 0.884] |
| Excl. yetacp 235 | relic_v2 | 193/0/4/38 | 1.000 [0.981, 1.000] | 0.980 [0.949, 0.992] | 1.000 [0.908, 1.000] | 0.990 [0.971, 1.000] | – | 0.942 [0.867, 1.000] | – |
| | text_ignore_job_params | 197/2/0/36 | 0.990 [0.964, 0.997] | 1.000 [0.981, 1.000] | 0.947 [0.827, 0.985] | 0.995 [0.984, 1.000] | – | 0.968 [0.910, 1.000] | – |

The F1 and MCC point estimates are the same under both clusterings. The file-cluster CIs here use the numpy method, which differs slightly from the repo's `random.Random` method; that is a method difference, not a discrepancy. The repo-method values are reproduced exactly in §1.

| Comparison (relic_v2 − baseline) | Disc a:b | McNemar p | Holm (42) | Sign-flip p (file) | Sign-flip p (repo) | ΔMCC file boot | ΔMCC repo boot | ΔF1 file boot | ΔF1 repo boot |
|---|---|---|---|---|---|---|---|---|---|
| Pooled vs **ignore_job_params** | 3:33 | 2.3e-7 | <0.001 | 0.0040 | 0.50 | −0.113 [−0.183, −0.044] | [−0.151, 0.023] | −0.022 [−0.042, −0.008] | [−0.032, 0.004] |
| Pooled vs textdiff | 62:33 | 0.0038 | 0.12 | 0.011 | 0.25 | +0.174 [0.102, 0.245] | [−0.008, 0.274] | +0.018 [0.001, 0.036] | [−0.007, 0.048] |
| Excl. yetacp vs ignore_job_params | 2:4 | 0.69 | 1 | 0.75 | – | −0.027 [−0.123, 0.060] | – | −0.005 [−0.027, 0.010] | – |
| Excl. yetacp vs textdiff | 14:4 | 0.031 | 0.71 | 0.060 | – | +0.174 [0.046, 0.278] | – | +0.024 [0.002, 0.050] | – |

**Reading.** Pooled with file clustering, the pre-registered comparator is better than RELIC; ΔF1 and ΔMCC both have CIs below 0. Three things weaken that result:
- With repository clustering, the CIs include 0.
- Excluding yetacp, the difference disappears.
- The cluster sign-flip p (0.004) is roughly 10^4 times larger than the per-mutant McNemar p (2.3e-7).

The external evidence is dominated by one repository. Mutants are not independent of each other: many are generated from the same file.

### 3.2 Per repository (7), per failure category (4), per operator (9)

The table gives relic_v2 against the pre-registered comparator textdiff_ignore_job_parameters. Results against textdiff are in the JSON.

| Stratum | n (pos) | Files | relic TP/FP/FN/TN | relic precision [Wilson] | relic F1 / MCC | ignore-params TP/FP/FN/TN | Disc a:b | McNemar p | Holm (42) | Sign-flip p |
|---|---|---|---|---|---|---|---|---|---|---|
| IBM_dbb | 8 (6) | 2 | 6/0/0/2 | 1.000 [0.610, 1.000] | 1.000 / 1.000 | 6/0/0/2 | 0:0 | 1 | 1 | 1 |
| IBM_zopeneditor-sample | 54 (40) | 7 | 40/0/0/14 | 1.000 [0.912, 1.000] | 1.000 / 1.000 | 40/0/0/14 | 0:0 | 1 | 1 | 1 |
| mainframed_Enumeration | 62 (50) | 5 | 49/0/1/12 | 1.000 [0.927, 1.000] | 0.990 / 0.951 | 50/2/0/10 | 2:1 | 1 | 1 | 1 |
| vlachoudis_brexx | 56 (53) | 3 | 53/0/0/3 | 1.000 [0.932, 1.000] | 1.000 / 1.000 | 53/0/0/3 | 0:0 | 1 | 1 | 1 |
| walmartlabs_zECS | 49 (44) | 5 | 44/0/0/5 | 1.000 [0.920, 1.000] | 1.000 / 1.000 | 44/0/0/5 | 0:0 | 1 | 1 | 1 |
| yetacp_mvs_sysgen | 589 (494) | 47 | 465/0/29/95 | 1.000 [0.992, 1.000] | 0.970 / 0.849 | 494/1/0/94 | 1:29 | 5.8e-8 | 2.3e-6 | 0.0049 |
| zowe_zowe-cli | 6 (4) | 2 | 1/0/3/2 | 1.000 [0.206, 1.000] | 0.400 / 0.316 | 4/0/0/2 | 0:3 | 0.25 | 1 | 0.5 |
| F1_ORDERING | 543 (542) | 71 | 520/0/22/1 | 1.000 [0.993, 1.000] | 0.979 / 0.204 | 542/1/0/0 | 1:22 | 5.7e-6 | 0.0002 | 0.0078 |
| F2_DATASET | 94 (94) | 23 | 88/0/6/0 | 1.000 [0.958, 1.000] | 0.967 / NA | 94/0/0/0 | 0:6 | 0.031 | 0.71 | 0.5 |
| F3_RETURN_CODE | 57 (55) | 18 | 50/0/5/2 | 1.000 [0.929, 1.000] | 0.952 / 0.510 | 55/2/0/0 | 2:5 | 0.45 | 1 | 0.62 |
| NEGATIVE_REFACTOR | 130 (0) | 71 | 0/0/0/130 | NA | NA | 0/0/0/130 | 0:0 | 1 | 1 | 1 |
| ALTER_COND_THRESHOLD | 28 (27) | 18 | 25/0/2/1 | 1.000 [0.867, 1.000] | 0.962 / 0.556 | 27/1/0/0 | 1:2 | 1 | 1 | 1 |
| CHANGE_MSGCLASS | 59 (0) | 59 | 0/0/0/59 | NA | NA | 0/0/0/59 | 0:0 | 1 | 1 | 1 |
| DELETE_PRODUCER_STEP | 40 (40) | 23 | 40/0/0/0 | 1.000 [0.912, 1.000] | 1.000 / NA | 40/0/0/0 | 0:0 | 1 | 1 | 1 |
| INSERT_COMMENT | 71 (0) | 71 | 0/0/0/71 | NA | NA | 0/0/0/71 | 0:0 | 1 | 1 | 1 |
| MOVE_CONSUMER_BEFORE_PRODUCER | 25 (25) | 9 | 25/0/0/0 | 1.000 [0.867, 1.000] | 1.000 / NA | 25/0/0/0 | 0:0 | 1 | 1 | 1 |
| REMOVE_COND | 29 (28) | 18 | 25/0/3/1 | 1.000 [0.867, 1.000] | 0.943 / 0.472 | 28/1/0/0 | 1:3 | 0.62 | 1 | 0.62 |
| RENAME_OUTPUT_DATASET | 29 (29) | 16 | 23/0/6/0 | 1.000 [0.857, 1.000] | 0.885 / NA | 29/0/0/0 | 0:6 | 0.031 | 0.71 | 0.5 |
| SPLIT_JOB | 274 (274) | 71 | 260/0/14/0 | 1.000 [0.985, 1.000] | 0.974 / NA | 274/0/0/0 | 0:14 | 0.00012 | 0.0045 | 0.0078 |
| SWAP_ADJACENT_STEPS | 269 (268) | 70 | 260/0/8/1 | 1.000 [0.985, 1.000] | 0.985 / 0.328 | 268/1/0/0 | 1:8 | 0.039 | 0.82 | 0.16 |

**RELIC has zero false positives in every external stratum.** Its only errors are 33 missed changes, and textdiff_ignore_job_parameters misses none of them.

Against raw textdiff, RELIC's advantage comes entirely from two negative classes:
- CHANGE_MSGCLASS: textdiff flags 59/59 of these harmless edits.
- NEGATIVE_REFACTOR: 59 FP for textdiff.

The pre-registered ignore-params baseline is designed to remove exactly that advantage.

## 4. Multiple comparisons

**This reanalysis.** One Holm family covers every relic_v2-vs-baseline paired test the script runs. That is 86 test entries:
- 6 SemBench populations × 5 baselines (30);
- 12 SemBench categories × normalized_text_B (12);
- external pooled and pooled-excluding-yetacp, plus 7 repos, 4 failure categories and 9 operators, each against 2 baselines (44).

**Many of these entries are the same test.** Entries with identical discordant case sets, in either orientation, are counted once. Examples:
- ALL_180, EXCL_25 and EXCL_15, because no detector flags an identical pair;
- CLEAN_CORE and SENS-excl-14;
- external strata where ignore-params and textdiff predict identically;
- CHANGE_MSGCLASS and NEGATIVE_REFACTOR against textdiff;
- all zero-discordance entries, which count as one null test.

That leaves **m = 42 distinct tests (raw m = 86)**. Each entry carries the adjusted p of its distinct test.

The pooled repo-cluster block uses the same cases as the file-cluster block and is not counted again. Holm is applied separately to the McNemar p-values and to the cluster sign-flip p-values.

Results (raw-m values are in the JSON as `p_holm_rawm_*`):
- **McNemar:** 36 of 86 entries have raw p < 0.05, and 13 have Holm-adjusted (m = 42) p < 0.05. Those 13 are listed under `holm_global.significant`. They are mostly single-class strata: SemBench change categories where text_B wins, and external F1_ORDERING / SPLIT_JOB / yetacp where ignore-params wins.
- **Sign-flip (cluster-robust), Holm-adjusted (m = 42) p < 0.05 in 4 entries.** There are 3 distinct tests:
  - text_B beats RELIC on cond_logic_change and on return_code_effect, adjusted p = 0.040 each;
  - RELIC beats raw textdiff on the 59 CHANGE_MSGCLASS (= NEGATIVE_REFACTOR) cases, adjusted p = 0.0004.

**Headline SemBench test (relic_v2 vs normalized_text_B, ALL_180; McNemar p = 0.001689):**

| Correction family | m distinct (raw) | Holm p |
|---|---|---|
| Published: one 14-pair family (ALL subset only) | 14 | **0.020** |
| All published paired tests (old benchmark + ALL + VALIDATED + ORACLE_DISAGREES), deduplicated | 27 (56) | **0.029** (0.069 if duplicates counted) |
| This reanalysis, global family | 42 (86) | **0.054** (0.123 if duplicates counted) |
| This reanalysis, cluster sign-flip p = 0.00195 | 42 (86) | 0.076 |

How the published family was deduplicated:
- The two abstain modes are byte-identical on SemBench, so only one is counted.
- SemBench subset tests are compared by their actual discordant case IDs.
- Old-benchmark test identity is *inferred* from its 0:0 pairs. Zero discordance on correctness implies identical binary predictions, so for example v2-vs-text_A, v2-vs-text_B and v2-vs-ignore-params are one test there. The old benchmark's raw data was not re-read.

**Reading.** The published "Holm p = 0.020" is family-sensitive. It **survives (0.029) across every test the repo actually published**, once duplicate tests are collapsed. It does **not** survive this reanalysis's wider family, which adds sensitivity populations and strata (0.054). Nor does it survive the cluster-robust test (0.076). Both of those fall just above 0.05.

This does not affect H1. H1 is decided by the bootstrap ΔMCC rule, not by Holm, and the ΔMCC CI excludes 0 in every population.

## 5. Are the repo's paired tests correctly specified?

The arithmetic is correct and fully reproducible. The specification has six problems.

1. **The test does not match the hypothesis.** The repo's McNemar test is on per-case *correctness*, which is accuracy and weights a false negative and a false positive equally. H1 and the headline are about **MCC**. The two disagree in practice:
   - relic_v2 vs textdiff: ΔMCC +0.148 [0.038, 0.247] but McNemar p = 0.85.
   - relic_v2 vs textdiff_ignore_job_parameters in EXCL_25: ΔMCC −0.107 [−0.206, −0.024] but p = 0.49.

   Because discordances split perfectly by class (§2.2), McNemar here just compares "#changes the baseline catches and RELIC misses" with "#harmless edits RELIC ignores and the baseline flags". Its verdict depends on class prevalence in the benchmark. The paired cluster-bootstrap ΔMCC or ΔBA is the inference that matches the stated hypothesis.
2. **Clustering is ignored.**
   - SemBench: 180 cases come from **16** base programs.
   - External: 824 mutants come from 71 files in 7 repositories.

   McNemar treats cases as independent. A cluster-level exact sign-flip test on per-cluster (b_k − c_k) gives similar p-values for SemBench (0.0017 vs 0.0020), but external p-values are about 10^4 larger (2.3e-7 vs 0.004). At the repository level (7 clusters, only 3–4 with any discordance), the smallest attainable sign-flip p is 0.125–0.25, so the test has no power there. The repo-cluster bootstrap CIs (§3.1) are the only repository-level evidence.
3. **The Holm family is too narrow** (§4). The pre-registration requires correction over all comparisons run. The repo corrected within each 14-pair family, although it ran 4 families, plus a duplicated abstain mode. Within those families, several entries are duplicates of one another. Across the 27 distinct published tests the headline still holds (Holm 0.029). Across this reanalysis's 42 distinct tests it is 0.054.
4. **P-values are rounded before Holm.** They are rounded to 6 dp, so 7 of the 56 published p-values are stored as exactly 0.0. That has no practical effect here, but `p = 0.0` is not a valid p-value and should be reported as `< 1e-6`.
5. **The bootstrap rests on few clusters.** Percentile cluster-bootstrap CIs with 16 clusters, and especially with 7 repositories, are known to under-cover. The SemBench MCC CIs should be read as optimistic.
6. **The external analysis has no paired significance test.** The repo reports only paired F1-difference CIs, which is defensible. Its caveats admit that file-level CIs are "optimistic regarding repository heterogeneity", and §3.1 confirms they are: with repository clustering, the CI for ΔF1 against ignore-params includes 0.

## 6. Pre-registered hypotheses under their stated rules

| Hypothesis | Rule | Evidence | Verdict |
|---|---|---|---|
| **H1** RELIC MCC > normalized text baseline | Rejected if paired ΔMCC (cluster bootstrap on base_id) has a CI entirely < 0 **or** a negative point estimate in the primary population | ALL_180: ΔMCC = −0.201 [−0.299, −0.102]. Negative with the CI below 0 in **all six** populations (−0.117 to −0.328). | **Rejected** |
| **H2** RELIC detects true changes the text baseline misses | Rejected if RELIC-only TP = 0 in the primary populations | RELIC-only TP = 0 in all six SemBench populations (vs text_B; also vs every other baseline) and 0 externally vs both baselines | **Rejected** (a count only; interpretation belongs to the complementarity report) |
| **H3** RELIC flagged-set precision ≥ 0.95 | Rejected if Wilson lower bound < 0.90 in external pooled or any repo with ≥ 20 RELIC-flagged | Pooled 658/658 gives LB 0.994. Repos with ≥ 20 flagged: zopeneditor 40/40 (LB 0.912), zECS 44/44 (0.920), Enumeration 49/49 (0.927), brexx 53/53 (0.932), yetacp 465/465 (0.992). | **Not rejected**, but narrowly: the minimum LB is 0.912, against a threshold of 0.90 |
| H4 fast-track saving | (complementarity analysis) | not computed here | – |
| H5 explanatory value | needs an explanation-fidelity audit | not testable from binary predictions | **Untested** |

The H3 verdict has three caveats:
- The Wilson interval ignores file clustering. With 0 false positives the bootstrap gives no extra information, because every resample has precision 1.
- On SemBench, outside the H3 rule, RELIC's precision is 23/25 = 0.92, with Wilson LB 0.750.
- The labels come from the same unvalidated oracle used in development.

## 7. Problems found

1. **The headline direction is easy to misread.** Both "headline" numbers favour the text baseline: MCC 0.525 > 0.324, and F1 0.9978 > 0.9755. Any text presenting them as RELIC wins is wrong.
2. **The published Holm p = 0.020 depends on the family chosen.**
   - Over all distinct published tests (m = 27) it is 0.029, so it survives.
   - Over this reanalysis's distinct family (m = 42) it is 0.054.
   - With the cluster sign-flip test it is 0.076.
   - Counting duplicate tests as separate comparisons inflates these to 0.069 and 0.123; that would be wrong.
3. **There are 7 external repositories, not 11.** Four repositories contribute nothing evaluable, and one repository supplies 71% of the external data and 88% of RELIC's misses.
4. **McNemar on accuracy is the wrong test for an MCC hypothesis,** and it ignores clustering.
5. **ORACLE_DISAGREES counts are inconsistent across files.** The repo's `ORACLE_DISAGREES` subset has n = 28 (by validation_status). CANONICAL's disagreement list has 29, because it uses `oracle_agrees_with_expected is False` and so includes the oracle-abstain case sembench_172. The "13–14 non-identical" range comes from that difference; both versions are reported in §2.
6. **No scores exist,** so threshold, PR or ROC analysis is impossible (§0).

## 8. Recommended actions

- Report H1 as rejected, H2 as rejected (count), H3 as not rejected (narrowly), H4 by the complementarity analysis, and H5 as untested. Label every result as exploratory or post hoc relative to data already seen.
- Use the paired cluster-bootstrap ΔMCC as the primary inferential statement. Present McNemar, if at all, as a secondary accuracy test, and give the cluster sign-flip p next to it. Replace "Holm p = 0.020" with the global-family value, or state m explicitly.
- For the external set, present repository-clustered and excluding-yetacp results next to the file-clustered pooled result. Call it "7 repositories (4 further repositories had no evaluable mutants)".
- Describe RELIC's measured profile plainly: high precision and specificity, low recall on SemBench, and no change detected that a normalised text diff misses.
- Any confirmatory claim needs a held-out corpus, a frozen detector and independently validated labels (see the pre-registration). None exist today.

## 9. Tests run and remaining uncertainty

**Tests run.** The script runs in-script assertions on:
- the 4 × 6 confusion matrices against CANONICAL;
- duplicate tests in a Holm family must carry identical p-values;
- no `None` predictions in either dataset;
- n = 180 and n = 824.

**Reproduction checks.** Matches are exact for:
- the 42 published SemBench paired tests;
- the 6 SemBench detectors' MCC, F1 and BA bootstrap CIs;
- external pooled and excluding-yetacp F1 points and CIs, and ΔF1 CIs.

**Remaining uncertainty.**
- All labels come from a same-author, unvalidated oracle; the 60-case review package has no returned labels. Every number here inherits that limitation.
- Only 16 SemBench clusters and 7 external repositories exist, so interval estimates are fragile.
- The old (development) benchmark tests were not recomputed. Their published p-values were used only in the published-family Holm recount. Their test identity was inferred from 0:0 pairs.
- The family (m = 42 distinct, 86 raw) is itself a judgement. A smaller family (for example, the 4 pre-registered populations × primary comparator) would give a different adjusted p. The pre-registration's wording ("all comparisons actually run") is what drives the choice here.
