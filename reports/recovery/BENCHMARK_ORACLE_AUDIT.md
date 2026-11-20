# Benchmark and oracle integrity audit (SemBench v1, oracle, 60-case review package)

Scope: read-only audit. Nothing in `benchmarks/`, `results/`, `datasets/`, `src/` or existing reports was modified; no git was run. Python: scratchpad venv with `PYTHONPATH=src`. Pre-registered rules in `reports/recovery/PREREGISTRATION.md` were followed (populations, H1/H2). Bootstrap here is cluster-on-`base_id` with seed 20261004 but **2,000 resamples** (pre-registration says 10,000), so CIs are indicative; rerun with 10,000 before citing.

**Status of the oracle:** same-author, never compared with real z/OS or any human. The 60-case package has **zero returned responses** and is **not** completed validation; nothing below changes that.

## 0. Headline findings

1. **MANIFEST is intact** (360/360 hashes verified; `validate.py` passes: 180 pairs, 87 PRESERVING / 93 CHANGING, statuses 151/28/1; recorded `original_sha256`/`transformed_sha256` in `cases.jsonl` also match the files). Integrity of the frozen files is not in question; their *validity* is.
2. **25 byte-identical pairs, 15 of them labelled CHANGING.** The 15 are generator no-ops (root cause in section 2) and every one is an `ORACLE_DISAGREES` row. The 10 identical PRESERVING pairs are correctly labelled but are free true negatives.
3. **The 29 vs 13 discrepancy reconciles exactly** (section 3): 29 = 15 no-ops + 13 genuine disagreements + 1 abstain. The "28 disagreements" figure = 29 minus the abstain.
4. **The no-ops favour RELIC relative to the text baseline**, not the reverse: removing them widens the RELIC-minus-normalized_text_B MCC gap from -0.201 to -0.319. H1 is rejected in every population, and H2 (RELIC-only true positives) is 0 in every population.
5. **Further defects found:** 21 groups of exact duplicate pairs (46 cases, 25 redundant); 5 duplicate groups carry *contradictory* labels (same bytes labelled PRESERVING and CHANGING); only 16 distinct base programs; 59 of 87 PRESERVING negatives are handled by a trivial text normalizer; at least one PRESERVING label (sembench_036) is probably wrong; several CHANGING labels rest on observables the benchmark's own rubric excludes.
6. **The 60-case review package does not cover SemBench at all.** It samples the older corpus-mutation benchmark (`results/final/raw/evaluation_records.jsonl`). It is a sound blind design for that population, but a reviewer verdict on it says nothing about the 13 contested SemBench labels.

## 1. SemBench inspection (evidence)

| Check | Result |
|---|---|
| Manifest | 360 entries, 0 mismatches, 0 missing. `validate.py` re-runs the oracle on all cases: no drift. |
| Categories | 17/17/21/12/14/6 PRESERVING (87) and 14/17/19/18/12/13 CHANGING (93). "12 balanced categories" in `README.md` overstates balance (6 to 21 per category). |
| Source | 173 handwritten, 7 corpus. Only **16 distinct originals** (12 handwritten bases = 173 cases; 4 corpus jobs = 7 cases). Largest base `base_hw_01_etl` has 30 cases. The effective number of independent units is 16. |
| Oracle vs label | PRESERVING: 84 EQUIVALENT, 3 DIFFERENT (036, 078, 079). CHANGING: 67 DIFFERENT, 25 EQUIVALENT, 1 UNDETERMINED (172). |
| Predictions | `results/sembench/predictions.jsonl`: all 8 detectors x 180 cases have status OK; every detector predicts "unchanged" on all 25 identical pairs (as it must). |

### 1a. The 25 byte-identical pairs
PRESERVING (10, labelled correctly, `VALIDATED_BY_ORACLE_AND_ARGUMENT`): sembench_041, 058, 068, 072, 074, 080, 081, 082, 083, 180.
CHANGING (15, all `ORACLE_DISAGREES`, labels provably wrong because nothing changed): 100, 103, 108, 111, 112, 123, 128, 153, 154, 156, 158, 160, 161, 170, 175.

By subcategory of the 15: `stage_source_alteration` 5 (100, 103, 108, 111, 112), `omit_pipeline_producer` 6 (153, 154, 156, 158, 160, 161), `disp_shr_to_new` 2 (123, 128), `program_substitution` 1 (170), `corpus_input_dsn_alteration` 1 (175). This matches `CANONICAL_NUMBERS.json` `identical_pair_ids` exactly (verified by recomputation from file bytes).
The 10 PRESERVING no-ops: `step_name_refactoring` 4 (rename anchor absent in base), `iefbr14_dd_reorder` 3, `disp_parens` 1, `job_class_change` 1, `corpus_carddemo_indentation` 1.

### 1b. Generator bug (benchmarks/sembench/build.py)
Single root cause: **`str.replace(old, new)` is applied to a base text that does not contain `old`; Python returns the unchanged string, and no code asserts `mod != orig`.** It is aggravated by a cyclic dispatch `bkey = bases_keys[i % len(bases_keys)]` that picks a base first and then a transformation by `if "<anchor>" in orig / elif ... / else`, so the transformation is chosen by what string happens to be present, not by design intent.

* `build.py:1046-1092` (cases 100-113; no-op replace at 1089): the final `else` does `orig.replace("STAGE.DATA.SOURCE", ...)`, which most bases do not contain. The generator's own text at `build.py:1092` says "In single-job simulation ... the oracle reports EQUIVALENT, but z/OS catalog resolution alters input dataflow": the author saw the oracle say EQUIVALENT and wrote a justification for a transformation that did not happen. i % 12 also cycles 14 iterations over 12 bases, so 100 and 112 are the same pair.
* `build.py:1160-1182` (disp cases; no-op replace at 1180): the `else` fallback `orig.replace("DISP=SHR", "DISP=(NEW,CATLG,DELETE)")` is a no-op on bases without `DISP=SHR` (123, 128).
* `build.py:1334-1360` (151-161 `omit_pipeline_producer`): step deletion keyed on `//STEP`, `//ST`, `//CP`, `//IDC` prefixes and `" EXEC "` with `"IEFBR14" not in line`; for several bases nothing matches so nothing is deleted. The same loop is cyclic over bases, producing exact duplicate pairs (158 = 160).
* `build.py:1439` (170): `orig.replace("PGM=IEBGENER", "PGM=IEFBR14")` on a base with no IEBGENER.
* `build.py:1491` (175): `ctext.replace(".DATA", ".DATA.MODIFIED")` on a corpus job that lacks `.DATA`.
* PRESERVING analogues: `build.py:846-862` (rename anchors), `638-656` (`disp_parens`, `DISP=SHR` absent), `718-730` (job class), `build.py:1570` (corpus indentation).

Why the oracle reporting EQUIVALENT with empty evidence on identical files was not caught: `build.py` records `ORACLE_DISAGREES` as a status and moves on; nothing treats "oracle disagrees on a CHANGING case" as a defect to be investigated, and `validate.py` checks only hash drift and oracle-label drift, never `original != transformed` for CHANGING cases.

## 2. Reconciliation of the 29 / 28 / 14 / 13 counts

`cases.jsonl` has 29 rows whose status is not `VALIDATED_BY_ORACLE_AND_ARGUMENT`: 28 `ORACLE_DISAGREES` + 1 `ORACLE_ABSTAINS`. `CANONICAL_NUMBERS.json` calls all 29 "disagree" (`n_disagree_all` = 29, includes the abstain); `oracle_validation.json` and `SEMBENCH_DESIGN.md` call 28 disagreements + 1 abstain. These are the same set.

| Group | n | IDs |
|---|---:|---|
| Generator no-ops (CHANGING, identical files) | 15 | 100, 103, 108, 111, 112, 123, 128, 153, 154, 156, 158, 160, 161, 170, 175 |
| **Genuine** non-identical disagreements, PRESERVING label vs oracle DIFFERENT | 3 | 036, 078, 079 |
| **Genuine** non-identical disagreements, CHANGING label vs oracle EQUIVALENT | 10 | 117, 118, 120, 121, 124, 126, 127, 129, 130, 165 |
| Abstain (CHANGING, oracle UNDETERMINED) | 1 | 172 |
| **Total** | **29** | |

Non-identical total = 3 + 10 + 1 = 14 (`oracle_disagree_non_identical_ids`), of which 13 genuine (excluding the abstain). 28 disagreements = 29 - 1 abstain. All three counts in the brief are consistent once the abstain and the no-ops are separated.

Caveat on "13 genuine": they are 11 distinct *pairs*: 117 = 129 and 118 = 130 are byte-identical duplicate cases (also 119/131, which are validated).

Reading of the 13 (all author-argued, none independently reviewed):
* **036** (`PARM='A,B,C'` vs `PARM=(A,B,C)`): benchmark says PRESERVING; oracle says DIFFERENT. From memory, IBM passes the parentheses of a parenthesised PARM list to the program, whereas apostrophes are stripped, so the strings differ and the oracle may be right. **Not verified against the IBM manual in this audit; treat as a probable mislabel until checked.** Note the design report's wording ("the simulator hashes PARM text") already admits the oracle sees different text.
* **078, 079** (step renames): RELIC and every text detector flag them; label PRESERVING is plausible if step names are not an observable; the oracle keys steps by name, so it is a model limit, not a clear label error. These two are RELIC's only false positives (2 of 2).
* **117, 120, 126, 129** (`SHR` -> `OLD`): difference is enqueue exclusivity, which is not an observable under the review rubric's O1-O4 (`RUBRIC.md` section 1). Under that rubric these would be EQUIVALENT. The label depends on which observables are admitted.
* **118, 121, 124, 127, 130** (`CATLG` -> `KEEP` on a NEW dataset): the `equivalence_argument` says "SMS-managed" in the rationale and "non-SMS volumes" in the argument; for SMS-managed datasets the system catalogs regardless, so the argument is internally inconsistent. Doubtful.
* **165** (`COUNT(100)` -> `COUNT(10)` in IDCAMS PRINT): changes SYSPRINT content only; SYSPRINT/SYSOUT is excluded by the rubric. Doubtful.

Net: of 29 non-validated rows, 15 are certain label errors; of the other 14, between roughly 1 and 13 are label errors depending on the observable definition. Nobody has adjudicated them.

## 3. Effect of identical pairs on reported comparisons

Identical pairs **were included** in all headline SemBench numbers (ALL_180: `CANONICAL_NUMBERS.json` `populations.ALL_180`; `results/sembench/metrics.json`). Excluded only in the pre-declared sensitivity populations. Recomputed (matches canonical values to all digits shown):

| Detector | MCC ALL_180 | MCC EXCL_25 | MCC EXCL_15 (CHANGING no-ops) | MCC CLEAN_CORE (n=141) |
|---|---:|---:|---:|---:|
| relic_v2 | 0.324 | 0.366 | 0.379 | 0.464 |
| normalized_text_B | 0.525 | 0.684 | 0.706 | 0.694 |
| normalized_text_A | 0.451 | 0.614 | 0.642 | 0.620 |
| textdiff_ignore_job_parameters | 0.302 | 0.473 | 0.518 | 0.474 |
| textdiff | 0.176 | 0.353 | 0.419 | 0.352 |
| raw_text | -0.067 | undefined (TN = 0) | 0.241 | undefined |

Mechanism: the 15 CHANGING no-ops are the **only** false negatives of every text detector (FN = 15, recall 0.839 vs 1.000 once removed). Text recall is therefore an artefact of the label errors; on valid CHANGING cases every text variant has recall 1.000. RELIC loses recall too (0.247 -> 0.295 after removal) but proportionally less. The 10 PRESERVING no-ops add 10 free TNs to every detector (all 10 of `raw_text`'s TNs).

**Gap RELIC v2 minus normalized_text_B (MCC), cluster bootstrap on `base_id`, 2,000 resamples:**

| Population | n | gap | 95% CI |
|---|---:|---:|---|
| ALL_180 (as reported) | 180 | -0.201 | [-0.300, -0.092] |
| EXCL_25_IDENTICAL | 155 | -0.319 | [-0.432, -0.230] |
| EXCL_15_NOOP_CHANGING | 165 | -0.328 | [-0.439, -0.240] |
| exact-duplicate pairs collapsed to one (n=155, 75 positive) | 155 | -0.280 | [-0.376, -0.194] |
| duplicates collapsed and identical removed | 143 | -0.327 | [-0.445, -0.237] |
| CLEAN_CORE (also drops 13 genuine disagreements + abstain) | 141 | -0.230 | [-0.374, -0.123] |
| oracle verdict as truth (drops abstain only; circular, see below) | 179 | -0.170 | [-0.337, -0.043] |
| oracle verdict as truth, identical removed | 154 | -0.141 | [-0.312, -0.016] |

Interpretation: **the label errors flatter RELIC, they do not hurt it.** The sign of H1 (RELIC MCC > text) is rejected in every population, with every CI below zero. H2 is rejected too: RELIC-only TPs = 0 in ALL_180 and EXCL_25 (text-only TPs 55 in both). The magnitude of the gap is population-dependent (-0.14 to -0.33), so no single number should be quoted without naming the population. Caveats: (i) CLEAN_CORE removes RELIC's two false positives (078, 079), so it is not a neutral population; (ii) "oracle as truth" is circular because RELIC was developed against the same oracle model; it is a sensitivity bound, not a result; (iii) with 16 clusters the cluster bootstrap is itself fragile.

Duplicates: collapsing exact-duplicate pairs reduces RELIC TPs 23 -> 20 and text TPs 78 -> 70, i.e. the cyclic generator double-counts. Also reported per-detector CIs (cluster bootstrap) are conditional on 16 clusters, not 180 cases.

## 4. Other defects found

| ID | Finding | Evidence |
|---|---|---|
| D1 | **21 groups of exact duplicate (original, transformed) pairs, 46 cases (25 redundant).** E.g. 019/031, 037/049, 038/050, 039/051, 086/091, 101/113, 117/129, 118/130, 119/131, 135/147, 136/148, 137/149, 158/160. | same hash pair in `cases.jsonl`; cyclic `i % len(bases_keys)` in build.py |
| D2 | **5 duplicate groups carry contradictory labels.** The identical-bytes pair {041, 072, 123, 170} is labelled PRESERVING (041, 072) and CHANGING (123, 170); {068, 080, 153}, {074, 108}, {081, 103, 154}, {083, 156} likewise. The same bytes cannot be both. | direct from hashes |
| D3 | Only 16 distinct original programs; 12 handwritten bases generate 173 of 180 cases; per-case CIs overstate independence. | section 1 |
| D4 | PRESERVING negatives are dominated by what a text normalizer handles: of 87, 10 are no-ops and **49 more** (comment 17, whitespace 14, job-card 11, syntax 7) are non-identical pairs that raw text flags but `normalized_text_B` correctly calls unchanged. Only **28 of 87 (32%)** are genuine tests of a semantic detector (B false positives: syntax 13, reorder 11, whitespace 2, rename 2). `README.md` claims the negatives are not trivial; for two thirds they are. Comment edits (17) and job-card refactors (12) are every text baseline's easy cases. | `predictions.jsonl` |
| D5 | Class/difficulty asymmetry: no CHANGING case is ever missed by any text detector (after no-ops), so the CHANGING side does not discriminate between text variants either; it only discriminates RELIC (23/78). The benchmark mostly measures "does RELIC model this category", which was designed by the same author. | metrics above |
| D6 | Several CHANGING labels depend on observables excluded by the independent-review rubric (SHR vs OLD enqueue, SYSPRINT content, KEEP vs CATLG). The benchmark has no declared observable set, so label validity is undefined. | section 2 |
| D7 | Documentation inconsistencies: README says "12 balanced categories"; "validation_status" `VALIDATED_BY_ORACLE_AND_ARGUMENT` counts the 10 trivial identical PRESERVING pairs as validated (the design report footnotes this); `SEMBENCH_DESIGN.md` text still says "Mar 2025"/AGENT 1 authorship. `oracle_confidence` is HIGH on all 28 disagreements, including the no-ops where the oracle is simply right. | cases.jsonl |
| D8 | `validate.py` checks hashes and oracle-label drift only. It never checks (a) transformed != original, (b) pair uniqueness, (c) label-vs-oracle consistency beyond recording a status. These are the checks that would have caught D1/D2/section 1b. | `validate.py:57-108` |
| D9 | Identical-pair predictions: `raw_text` has TN = 0 after removal so its MCC is undefined in EXCL_25 and CLEAN_CORE (canonical file records `null`). Do not report that as 0. | section 3 |

No malformed JSON, missing files, or hash mismatches were found. Near-duplicate base programs: the 12 handwritten bases are structurally different (utility, sort, compile/link, GDG, IF/THEN/ELSE), so base-level near-duplication is low; the redundancy is at the *case* level (D1).

## 5. The 60-case blind review package

Directory: `reports/v2/review_package`. I opened `KEY_DO_NOT_SHARE.csv` once for structural checks only. Structural statements only (no per-case labels are reproduced here):

| Check | Result |
|---|---|
| Population | Corpus mutants from `results/final/raw/evaluation_records.jsonl` (566 EVALUABLE = 460 oracle-DIFFERENT + 106 oracle-EQUIVALENT), **not SemBench**. `INDEPENDENT_REVIEW_PACKAGE.md` has no SemBench reference. |
| Stratification | Holds as designed: 23 sampling cells; per-cell quotas in `sampling_frame.json` sum to 58 and match the key exactly; plus 2 mandatory anchors = 60. Labels 30/30; subjects carddemo 28 / genapp 22 / omp_course 10; 9 operators; 34 distinct files, with 13 files contributing more than one card (non-independent items). `make_sample.py` is deterministic (fixed seed) and has an automated leak check. |
| Prevalence | Sample is 50% oracle-EQUIVALENT vs 19% in the population; the 106 EQUIVALENT strata are 104 comment/MSGCLASS edits plus the 2 anchors (all equivalent by construction, per audit F-06). No sampling weights are provided, so sample agreement rates cannot be generalised to the 566 without weighting. Hard-case picks (H_DUP, H_D004, H_ABEND) are deliberate oversamples, flagged in the key. |
| Blindness on cards | Cards contain: subject, file path, unified diff, both full texts, referenced PROCs, the question text. No oracle verdict, RELIC prediction, operator name, or mutation id. The only occurrences of "EQUIVALENT"/"DIFFERENT" are the answer options in the boilerplate question (60/60 cards). The reviewer-facing `blind_review_form.csv` has empty response columns. `cards.jsonl` has keys `case_id, diff, file, modified, original, procedures, subject` only. Card order is shuffled; label order in the key shows no run pattern (28 runs over 60, no ordering leak). |
| Residual leakage | (a) The diff itself reveals the mutation operator (a comment line added, a step swapped), so reviewers are blind to labels but not to the mutation type; unavoidable but should be stated. (b) The file path discloses the corpus and job name; harmless. (c) `RUBRIC.md` Q2 defines scenarios as "any single step with non-zero RC or abend", identical to the oracle's scenario model, and its ground rules 1-2 reproduce the oracle's assumptions. Agreement with the oracle on this rubric therefore partly measures reviewers adopting the oracle's definition. Rule 7 ("record real z/OS behaviour") partly offsets this. |
| Key leakage | `SHARING.md` correctly lists the key, `make_sample.py`, `sampling_frame.json`, `experiments/` as never-share. `make_sample.py` and `sampling_frame.json` would leak the strata and the oracle-dependent selection (they enumerate operators and population counts); the key has oracle label, categories, evidence and RELIC v1.0/v1.1 and textdiff flags, but **no relic_v2 flag**, so a v2 comparison would need the key regenerated. Nothing in cards/forms references the key. |
| Agreement script | Works on the template and on test data (all tests in scratchpad, SYNTHETIC/TEST ids only): `--self-test` ALL PASS; empty `responses_template.csv` pair -> "PENDING", exit code 3; no args -> exit 3; real mode on 3 randomised test files (reviewer ids `TESTREV-*`) computes pairwise percent agreement, Cohen kappa, Gwet AC1 with bootstrap CIs and adjudication; ids beginning `SYNTHETIC` are refused; `--compare-oracle` without `--confirm-reviews-complete` is refused. No fabricated ratings were written anywhere in the repo. |
| Script limitations | Bootstrap resamples items, not files (13 files have several cards); CANNOT_DETERMINE pairs are dropped from the binary statistic (the number is reported); with n=60 and 30/30 balance the CI on kappa is wide (self-test: width 0.38 at n=60). Adjudication takes a majority over A, B, C and marks ties `UNRESOLVED`; there is no discussion-based consensus step. |

Verdict: sound pre-registration-style design for the corpus-mutation oracle; fully PENDING. It cannot validate or invalidate any SemBench label.

## 6. Independent adjudication protocol (proposal)

Purpose: decide, independent of the author and of any detector, the true label of the contested SemBench cases and a sample of the validated ones, and thereby whether the oracle can be called validated.

1. **Items.** (a) All 14 non-identical non-validated cases (13 genuine + abstain) deduplicated to 12 pairs; (b) the 10 identical PRESERVING pairs as sanity items (expected EQUIVALENT, a reviewer who answers otherwise is flagged); (c) 3 of the 15 no-ops as attention checks (expected EQUIVALENT in terms of bytes; label "CHANGING" is untenable); (d) a stratified random sample of 40 oracle-validated, non-identical, deduplicated pairs, stratified by category and by base program (at most 3 per base), seed pre-registered. Then separately the existing 60-case corpus package. Cards generated as in `make_sample.py` (diff, both texts), with no oracle verdict, no expected label, no `rationale`/`equivalence_argument`, no subcategory name.
2. **Who.** At least 3 reviewers with professional z/OS JCL experience, none of whom is the benchmark/oracle/RELIC author, wrote any prompt, or has seen RELIC output. At least one should be a mainframe operations/scheduling practitioner. Reviewers are recruited and paid outside the project; conflicts declared in writing. Reviewers do not use LLMs or tools on the cases (state this; LLM reviewers may only be reported as a separate, clearly labelled column).
3. **Blinding.** Case ids re-randomised per reviewer; reviewers get the rubric, cards and a response form only; they work alone until all submit. Coordinator is a person who did not author the benchmark and holds the key.
4. **Rubric.** Fix the observable set *before* review and publish it with the benchmark: execution (steps run/bypassed, RC), data read, final catalog, termination, plus a declared list of non-observables (enqueue contention, SYSPRINT text, print class). Ask Q1 (normal completion) and Q2 (single fault), as in `RUBRIC.md`, and add Q3 "would an operator or scheduler observe a difference of any kind in production (including contention or output content)?" so that D6-type cases are recorded under both definitions rather than forced into one. `CANNOT_DETERMINE` allowed with a stated missing fact.
5. **Disagreement resolution.** Two reviewers label independently; if they differ, the third labels independently (majority); if all three differ or the majority is CANNOT_DETERMINE, a structured discussion with a documented rationale; if still unresolved the case is `INDETERMINATE` and removed from scored populations and **counted in the report**. The oracle is never consulted during adjudication (`compute_agreement.py` already enforces this).
6. **Statistics.** Per pair of reviewers: percent agreement, Cohen kappa, Gwet AC1 (existing script), item-bootstrap CI; report CANNOT_DETERMINE counts; Fleiss kappa or Krippendorff alpha across three raters (needs a small addition). Oracle vs adjudicated label: confusion matrix, sensitivity and specificity of the oracle for DIFFERENT, with Wilson intervals, reported per stratum and weighted back to the sampling frame (weights are required; sample is deliberately non-proportional).
7. **What would count as "oracle validated".** All three must hold, declared in advance: (i) inter-reviewer agreement kappa >= 0.6 and AC1 >= 0.7 on the binary label (otherwise the ground truth itself is unreliable); (ii) among adjudicated items, oracle-vs-adjudicated agreement >= 0.90 with Wilson lower bound >= 0.80 on each of the DIFFERENT and EQUIVALENT classes; (iii) every adjudicated disagreement is explained and either fixed in the oracle or documented as a scoped limitation. "Validated" would then mean "validated against the declared observable set on the sampled population", never "correct". Anything weaker is reported as "partially reviewed". Because the reviewers' observables are taken from this project's rubric, this validates the oracle against a *definition*, not against real execution; a real-z/OS differential run on a subset would be a stronger and separate result.
8. **Reporting.** Publish blinded responses, key, adjudications, and the script output; state that the oracle was designed before review and that detectors were not tuned on the reviewed items.

## 7. Proposed corrected benchmark (SemBench v2): proposal only, frozen v1 untouched

Warranted: yes. The no-ops, contradictory duplicates and undefined observable set mean v1 cannot be repaired by exclusion alone. Proposal, to live in a new directory (e.g. `benchmarks/sembench_v2/`) with its own build script and manifest:

* **Versioning.** v1 stays frozen as `sembench-v1` (labelled "known defects: see this audit"); v2 gets a distinct name and manifest; every v1 result stays reportable under its population names; any v2 result is reported separately and never merged into a v1 number. Record the generator commit and a `v1_id -> v2_id` map.
* **Generator fixes.** (1) Every transformation function returns `(mod, applied: bool)`; the builder asserts `mod != orig` and raises otherwise; (2) choose transformation per (base, category) by explicit table, not by `if substring in text` fallbacks and `i % len(bases)`; (3) dedupe on `(original_sha256, transformed_sha256)` and fail on collisions; (4) `validate.py` additions: `transformed != original`; unique pairs; for CHANGING cases require either oracle DIFFERENT or an explicit `oracle_blind_spot` tag with a written, reviewed argument; for PRESERVING require identical oracle verdict or the same tag.
* **What to regenerate.** The 15 CHANGING no-ops (100, 103, 108, 111, 112, 123, 128, 153, 154, 156, 158, 160, 161, 170, 175) get real transformations whose anchors exist in their bases (the intended `STAGE.DATA.SOURCE`, producer-step removal, `SHR` -> `NEW`, `IEBGENER` -> `IEFBR14`, a real `.DATA` DSN in the corpus job). The 10 PRESERVING no-ops (041, 058, 068, 072, 074, 080, 081, 082, 083, 180) likewise get a real preserving transformation or are dropped, not retained as free negatives. The 25 redundant duplicates (D1) are regenerated against different bases or removed.
* **What to replace or relabel.** 036 (PARM parenthesisation) after the IBM manual check: relabel CHANGING if parentheses are passed, otherwise keep and add the oracle caveat. The SHR->OLD, CATLG->KEEP and COUNT(100)->COUNT(10) cases (117-130, 165): tag with the observable they depend on (`enqueue`, `catalog_on_nonSMS`, `sysout_content`) and place them in a separate "extended observables" stratum, not in the primary scored set, unless the adjudicated observable set includes them. 078/079 keep as PRESERVING with an `oracle_step_identity` tag (these are legitimately detector-hard rather than label errors, but must be adjudicated). 172: keep as ORACLE_ABSTAINS.
* **Rebalance and broaden.** Increase corpus-derived originals (4 now) to at least 20 distinct base jobs; cap at 5 cases per base; raise preserving cases that a text normalizer cannot trivially handle (reorderings, step/DD renames with references, symbolic and PROC refactors, equivalent COND/IF rewrites, DD concatenation order where safe) so those exceed 50% of PRESERVING instead of 32%; add CHANGING cases that only a semantic tool can see versus text (e.g. changes inside PROC overrides, symbolic values), because currently text recall is perfect and the benchmark cannot show RELIC's advantage if it exists.
* **Process.** Freeze a rubric first (observable list), then have an independent person author at least a third of the cases, then adjudicate per section 6 before any detector is run, then freeze. Pre-register populations before the first detector run (the v1 populations were declared after seeing results).
* **Not claimed:** v2 does not exist; nothing here is a result.

## 8. Recommended actions (priority order)

1. Report every SemBench figure with its population name; never quote ALL_180 alone. State that 15 CHANGING pairs are no-ops and that text recall 0.839 is an artefact (true: 1.000).
2. Add the dedup/duplicate and contradictory-label findings (D1-D2) to the defect register and the paper's limitations; cite the effective cluster count of 16.
3. Verify 036 against the IBM z/OS MVS JCL Reference and record the outcome as a sourced note, not an assertion.
4. Do not describe the 60-case package as validation, and do not use it to support any SemBench claim. If SemBench oracle validation is wanted, build a SemBench review package (section 6, items a to d).
5. Rerun the paired bootstrap with 10,000 resamples as pre-registered before quoting CIs; the 2,000-resample values here are indicative.
6. Add the validate.py checks of D8 as a CI test for any v2 benchmark; do not modify v1.

## 9. Tests run

* `benchmarks/sembench/validate.py` (PYTHONPATH=src): manifest 360/360, no oracle drift, 180 pairs.
* Independent manifest and JSONL hash recomputation; byte-identity scan; duplicate-pair and label-contradiction scan (scratchpad `a1.py`).
* Recomputation of populations, MCCs, and cluster-bootstrap gaps from `predictions.jsonl` (scratchpad `a2.py`); matches `CANONICAL_NUMBERS.json`.
* `compute_agreement.py --self-test` (all pass); template -> exit 3 (PENDING); no args -> exit 3; real mode with 3 randomised test response files in the scratchpad (ids `TESTREV-*`, discarded; not ratings); synthetic-id refusal; oracle-comparison guard.
* Structural checks of the key against `sampling_frame.json` and cards (counts and leak greps only).

## 10. Remaining uncertainty

* The IBM behaviour for PARM parentheses (036) and for KEEP on SMS datasets is from memory and unverified.
* "13 genuine" depends on counting the oracle's DIFFERENT verdict on 036/078/079 and EQUIVALENT on the 10 CHANGING rows as disagreement; their true labels are unknown until adjudicated.
* Cluster bootstrap on 16 clusters understates uncertainty; CIs are approximate (2,000 resamples).
* I did not re-run `make_sample.py` to confirm byte-for-byte reproducibility of the package or inspect all 60 cards individually for subtle leakage (spot checks and regex scans only).
* Whether the corpus-mutation oracle labels in the 60-case package are right is untested; zero reviews exist.
