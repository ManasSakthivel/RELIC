# RED-TEAM AUDIT — RELIC V2 (publication-recovery branch)

Role: hostile peer reviewer. Scope: recompute metrics independently, hunt for confounders, leakage and invalid comparisons, decide whether RELIC's low recall comes from the algorithm or from the operating point, and list overstated claims.
Read-only: no git commands, no edits outside this file. `KEY_DO_NOT_SHARE.csv` was not opened. My scripts lived in the session scratchpad, which is temporary. The logic of each script is restated in Appendix A so anyone can re-derive the results.

Severity levels. **Critical** = voids or reverses a headline claim as it is currently written. **Major** = biases a reported comparison or misstates evidence. **Minor** = wording, hygiene or reporting precision.

---

## 0. Verdict in five lines

1. **Every canonical number I diffed reproduces exactly.** The diffed sections were the identical-pair and disagreement ID sets; TP/FP/FN/TN, F1 and MCC for all 8 detectors × 4 SemBench populations; the 5 external pooled detectors; and `external.per_repo` (relic_v2 and textdiff, all 7 repos). I recomputed from raw `cases.jsonl` and `predictions.jsonl` without importing `canonical_numbers.py`. I also re-ran RELIC V2 on all 180 SemBench pairs: 0 prediction mismatches with the committed file.
2. **"RELIC-only true positives = 0" is confirmed** in every SemBench population against every text detector, and on external. H2 (complementarity) is rejected as pre-registered.
3. **The external benchmark's label is almost exactly the mutation operator.** Predicting "not INSERT_COMMENT/CHANGE_MSGCLASS" gives 821/824 = 99.64% accuracy. External F1 therefore measures recognition of a non-cosmetic operator, not semantic discrimination, for RELIC and the text rule alike (**Critical** for interpretation).
4. **RELIC's low SemBench recall is algorithmic, not an operating-point choice.** The binary flag has no threshold: false-positive candidates are counted as flags. 46/55 non-identical false negatives produce an *empty* contract-graph diff. Exploratory, post hoc: in the categories RELIC models, RELIC ties the text baseline (ΔMCC +0.014, 95% CI [−0.147, 0.133]).
5. **The manuscripts have not caught up with the evidence** (**Critical**). `paper/paper.md` and all of `paper/v2/*.tex` still headline old-benchmark development results and an "independent" oracle, and never mention SemBench or the external run.

---

## 1. Independent recomputation (task 1)

Method: stdlib script. Truth = `expected_outcome == CHANGING` taken from `benchmarks/sembench/cases.jsonl`, cross-checked against `truth` in the predictions (0 mismatches). Identical pairs were found by **byte-comparing `original.jcl` and `transformed.jcl` on disk**; this gives the same 25-ID set as the sha fields. Oracle disagreements come from `oracle_agrees_with_expected` (29). Abstentions = any detector status ≠ OK: **none in the prediction file**, so CLEAN_CORE = 180 − 25 identical − 14 non-identical disagreements = 141, matching the canonical file. (`sembench_172`, listed as the canonical abstention, is also an oracle disagreement, so it is excluded either way.)

### SemBench (TP/FP/FN/TN, MCC). All values match `CANONICAL_NUMBERS.json` to 1e-9.

| Population | n | relic_v2 | normalized_text_B | normalized_text_A | textdiff_ignore_job_parameters |
|---|---|---|---|---|---|
| ALL_180 | 180 | 23/2/70/85, **0.3241** | 78/28/15/59, **0.5249** | 78/35/15/52, 0.4511 | 78/49/15/38, 0.3020 |
| EXCL_25_IDENTICAL | 155 | 23/2/55/75, 0.3655 | 78/28/0/49, 0.6843 | 78/35/0/42, 0.6136 | 78/49/0/28, 0.4726 |
| EXCL_15_NOOP_CHANGING_ONLY | 165 | 23/2/55/85, 0.3786 | 78/28/0/59, 0.7064 | 78/35/0/52, 0.6423 | 78/49/0/38, 0.5179 |
| CLEAN_CORE | 141 | 23/0/44/74, 0.4640 | 67/25/0/49, 0.6944 | 67/32/0/42, 0.6198 | 67/46/0/28, 0.4737 |

F1 values (relic_v2 0.3898 / 0.4466 / 0.4466 / 0.5111; normB 0.7839 / 0.8478 / 0.8478 / 0.8428) also match. raw_text has MCC = undefined on EXCL_25 (TN = 0); the canonical file stores `null`, which is consistent.

### External (EVALUABLE n = 824). All values match.

| Detector | TP/FP/FN/TN | F1 | MCC |
|---|---|---|---|
| relic_v2 | 658/0/33/133 | 0.9755 | 0.8735 |
| textdiff_ignore_job_parameters | 691/3/0/130 | 0.9978 | 0.9865 |
| textdiff | 691/62/0/71 | 0.9571 | 0.6999 |
| relic_v1_1 | 643/0/48/133 | 0.9640 | 0.8269 |
| relic_v1_0 | 612/0/79/133 | 0.9394 | 0.7454 |

Per-repository confusion matrices (`external.per_repo`: relic_v2 and textdiff, 7 repos, plus n) also match, 0 differences. **No discrepancies were found.**

### Paired ΔMCC (relic_v2 − normB), cluster bootstrap on `base_id`, 10,000 resamples, seed 20261004 (my own resampler)

ALL −0.2008 [−0.3014, −0.0956]; EXCL_25 −0.3188 [−0.4314, −0.2267]; EXCL_15 −0.3278 [−0.4374, −0.2395]; CLEAN_CORE −0.2304 [−0.3708, −0.1231]. The committed ALL interval in `results/sembench/paired_tests.json` is [−0.2992, −0.1018]. The small difference comes from a different random stream and is **consistent, not a discrepancy**. **H1 is rejected in every population.** The interval decides it, so Holm correction cannot change the outcome.

### Pre-registered hypotheses, recomputed

| H | Result | Evidence |
|---|---|---|
| H1 | **Rejected** (all 4 SemBench populations) | CIs above |
| H2 | **Rejected** | RELIC-only TP = 0 in every population, against all 5 text detectors, and on external |
| H3 | **Not rejected** under the pre-registered rule | External pooled 658/658, Wilson lower bound 0.9942. Every repo with ≥20 flags has a lower bound ≥0.90: zopeneditor 40/40 → 0.9124, Enumeration 49/49 → 0.9273, brexx 53/53 → 0.9324, zECS 44/44 → 0.9197, yetacp 465/465 → 0.9918. Context, not the test population: SemBench precision is 23/25, Wilson lower bound 0.750. |
| H4 | **Split; the prereg does not fix the population.** | SemBench FAST_TRACK fails everywhere: ALL/EXCL_25/EXCL_15 avoid 25/106 = 23.6% of reviews with 2/25 (8%) wrongly accepted; CLEAN_CORE avoids 23/92 = 25.0% with 0 wrong. All are below 30%. External passes (658/694 = 94.8% avoided, 0 wrong), but see C2: the external negative class is 130/133 cosmetic. **Recommend amending the prereg (labelled as an amendment) to name the population, or reporting H4 as "inconclusive: population-dependent".** |
| H5 | Untested | Binary predictions only |

---

## 2. Findings

### Critical

**C1. The manuscripts still headline superseded evidence and never report SemBench or the external run.**
- `paper/paper.md:1` (title "…Against an Independent Execution-Semantics Oracle"), `:18`, `:23`, `:72`, `:375` and `:424` call the oracle "independent".
- `reports/v2/ORACLE_INDEPENDENCE_AUDIT.md` (F-01, F-02) establishes that the oracle is only *code*-independent of RELIC. It shares the lexer and model with the mutator (`relic_eval/mutate.py:39-40`), and the oracle, mutator and detector have the same author.
- `paper/paper.md:24` keeps "precision 1.000, recall 0.850" (v1.0, CardDemo) as the primary result.
- `grep -ci sembench` returns **0** for `paper/paper.md` and for every `paper/v2/*.tex`. The 824-mutant external run is not reported anywhere in either manuscript. `paper/v2/threats_to_validity.tex:33-37` ("External validity") still describes only the three development corpora and 66 files. `paper/paper.md:125` mentions "external" only to say there is no third-party validation.
- `paper/v2/abstract.tex:14-16` headlines development F1 0.905/0.951/0.980. The decisive negative results (SemBench MCC 0.324 vs 0.525; external F1 0.9755 vs 0.9978; H2 rejected) appear only in `paper/v2/FINAL_RESEARCH_DRAFT.md`.
- `paper/v2/main.tex:19` names a stale branch (`research/relic-v2-integration`).

A reviewer reading either manuscript would not learn the main result.

**C2. External truth is (almost) a function of the operator, so external F1/MCC measure operator recognition.**
- Evaluable negatives by operator: INSERT_COMMENT 71, CHANGE_MSGCLASS 59, and only 3 others (1 each of ALTER_COND_THRESHOLD, REMOVE_COND, SWAP_ADJACENT_STEPS).
- The rule "positive unless operator ∈ {INSERT_COMMENT, CHANGE_MSGCLASS}" reaches **821/824 = 99.64%** accuracy.
- `textdiff_ignore_job_parameters` is, by its own docstring, an operator-shaped rule: `relic_eval/v2_eval.py:116-124` says it was written "post hoc… (both negative operators edit only comments or JOB parameters)". It was written after the *development* benchmark's operator set was known, not after the external data were seen; it is listed in `SUBJECT_FREEZE.json.frozen_detectors` before the external run. So there is no leakage from the external data, but it is tailored to the operator set, which is shared.
- Consequence: neither "RELIC precision 1.000 on external" nor "text 0.9978 > RELIC 0.9755" says anything about behavioural reasoning. Only 3 external negatives are non-cosmetic. RELIC is correct on all 3; the text rule is wrong on all 3. This is the only external evidence of a RELIC specificity advantage, and n = 3.
- Partly disclosed (`FINAL_RESEARCH_DRAFT.md`, A43 "negatives 130/133 cosmetic"), but the 99.6% operator-identity fact and its consequence for H3/H4 are not stated anywhere.

### Major

**M1. The external "scope" is defined by RELIC's capability, and the excluded mutants are almost all RELIC misses.**
- `relic_eval/mutate.py:125` says "non-empty -> out of RELIC's declared scope". `:363-364` sends every RENAME_OUTPUT_DATASET without an in-file consumer to OUT_OF_SCOPE (163 mutants). `:504` does the same for IF-guard removal ("outside RELIC's declared parser scope").
- On the 163 out-of-scope mutants, the oracle says DIFFERENT for 144 and EQUIVALENT for 2 (17 UNDETERMINED). RELIC flags 3 of the 144; the text rule flags all 163.
- Exploratory, adding the 146 decidable mutants back (n = 970):
  - relic_v2: TP 661, FP 0, FN 174, TN 135; recall 0.792, F1 0.884, MCC 0.588.
  - textdiff_ignore_job_parameters: F1 0.997, MCC 0.978.
- SemBench, by contrast, keeps categories RELIC does not model. The scope policies are inconsistent: external scoping favours RELIC (and RELIC still loses there), while SemBench's does not. Disclosed as a count (`EXTERNAL_VALIDATION_RESULTS.md:55,58`). The effect on metrics is not reported.
- This finding widens a gap that already favours the text rule; it does not reverse a conclusion. Hence Major, not Critical.

**M2. The SemBench negative class is half "text-normalisable by construction", and the normalisation rules mirror the category names.**
- normB true negatives by category: comment_edit 17/17, whitespace_and_continuation 15/17, job_card_refactor 12/12. That is 44/46 of the cosmetic negatives.
- On structural negatives normB scores only 15/41: syntax_representation 8/21, independent_statement_reorder 3/14, unreferenced_step_rename 4/6. RELIC is correct on 39/41 of these.
- The rules map one-to-one onto the categories: `strip_comment_lines` ↔ comment_edit, `join_continuations`/`collapse_whitespace` ↔ whitespace_and_continuation, `ignore_job_parameters` ↔ job_card_refactor, `sort_keyword_operands` ↔ syntax_representation. `SEMBENCH_DESIGN.md:13` lists exactly these phenomena.
- The freeze claim (`NORMALIZED_TEXT_BASELINE.md:3`) covers *cases*, not the category taxonomy. File mtimes are identical (checkout artefact) and I ran no git, so **whether the rule author saw the taxonomy is unverifiable**. I am not claiming it happened.
- The hash claim does verify: `sha256(relic_eval/text_baselines.py)` = `1ff51f34…213c6`, equal to `BASELINE_FREEZE.json` and `NORMALIZED_TEXT_BASELINE.md:3`. Spot-checked `SUBJECT_FREEZE.json.frozen_code_sha256` for `detectors.py`, `v2_eval.py`, `mutate.py` and `jcl_oracle/judge.py`: all equal the current files.

**M3. The text baseline's semantic loss is never tested; SemBench has no CHANGING item it could miss.**
- `ignore_job_parameters` documents a real semantic loss (`text_baselines.py:151-154`: COND=, TYPRUN=, TIME=, … on the JOB card). SemBench has 12 PRESERVING job-card edits and **0 CHANGING job-card edits**.
- On non-identical pairs normB recall is 78/78, so no CHANGING pair falls inside any rule's blind spot. The same holds for `sort_keyword_operands` and `uppercase_outside_quotes`.
- The benchmark rewards every normalisation rule for its benefit and never charges its cost. This favours the text baseline. It is an asymmetry, not a leak.

**M4. SemBench generator defect: 5 "consecutive_step_inversion" pairs are actually step *appends*.**
- `benchmarks/sembench/build.py:992-996` falls back to `orig + "\n//EXTRA EXEC PGM=IEFBR14\n"` when its step-name heuristic finds fewer than 2 steps. The label stays `consecutive_step_inversion` (`:1003`).
- Affected pairs: 087, 089, 090, 092, 096 (diffs verified). They are exactly RELIC's 5 step_reorder_dependent false negatives. RELIC detects 9/9 genuine swaps.
- The CHANGING label is arguably defensible (the oracle agrees), but the subcategory and rationale ("Inverting consecutive step execution sequence") are false.
- Also found independently by the concurrent `reports/recovery/ALGORITHM_IMPROVEMENT_REPORT.md` (row 6). Not in `DEFECT_REGISTER.md`.

**M5. "11 repositories" overstates external breadth.**
- `README.md:179` says "824 mutants, 11 repositories". `SUBJECT_FREEZE.json.repos` has 11 entries: 1 is robustness-only (mapa) and 3 have 0 eligible files.
- **Only 7 repositories contribute evaluable mutants**, and yetacp_mvs_sysgen supplies 589/824 (71.5%). Its provenance is unverified: it is "heavily based on Jay Moseley sysgen", while `MVS-sysgen/sysgen` was *excluded* for having no licence. zowe-cli contributes 6 mutants from 2 test-fixture files.
- Disclosed in `EXTERNAL_VALIDATION_RESULTS.md:11`, but not in the README.

**M6. External uncertainty is computed at the wrong cluster level.**
- `SUBJECT_FREEZE.json.analysis_plan.primary` uses a file-level cluster bootstrap for the reported external F1 CI ([0.9559, 0.9892]).
- `reports/v2/EXTERNAL_VALIDATION_PROTOCOL.md:142` says: "file-level cluster bootstrap is inadequate with <10 repos; use repo-level leave-one-repo-out…".
- The reported interval is therefore too narrow for any claim at repository level.

**M7. Overstated or contradictory claims in README (all outside the V2 section).**
- `README.md:3-4` "with an independent, execution-semantics evaluation"; `:39`, `:96`, `:230` "independent … oracle". These conflict with `ORACLE_INDEPENDENCE_AUDIT.md` F-01/F-02 and with `README.md:180` ("same oracle… not blind").
- `README.md:86-87` "It shares no code with RELIC". True, but it omits that the oracle shares its lexer/model with the *mutator* that creates the positives (`mutate.py:39-40`; audit F-01, F-03).
- `README.md:102` (generated block) calls the LLM-answered subset "a random subsample". `README.md:132-135` says it is "**not** a random subsample… 89.6% positive versus 77.3%". The page contradicts itself, and the false version sits in the headline block.
- `README.md:120-123` says "RELIC's advantage over that reference is specificity on harmless edits". The reference chosen is the weakest one. On the pooled old benchmark (566), `textdiff_ignore_job_parameters` and normA/B reach specificity 0.9811 with recall 1.0 (`NORMALIZED_TEXT_BASELINE.md:112-118`). On CardDemo the diagnostic's F1 is 0.9961, against RELIC v1.0's 0.9191 (`FINAL_RESEARCH_DRAFT.md:204`). The "advantage" therefore does not survive a slightly stronger trivial rule.
- `README.md:97` presents v1.0 CardDemo "precision 1.000" as the **primary result**. The page's own V2 section (`:177-180`) says the trivial text rule beats RELIC.

**M8. "No false positive among 84 validated preserving pairs" is a selection artefact.**
- Source: `paper/v2/FINAL_RESEARCH_DRAFT.md:360`, repeated in spirit at `:466`.
- The 84 are the PRESERVING pairs with `validation_status = VALIDATED_BY_ORACLE_AND_ARGUMENT`. The 3 excluded (036, 078, 079) include **both** of RELIC's false positives (078, 079).
- "Validated" here means agreement with the same-author oracle, which contradicts the draft's own line 5 ("no pair is independently validated").
- Rewrite as: "both false positives are on the two `unreferenced_step_rename` pairs where the oracle and the author label disagree."

**M9. High specificity is presented as a strength without noting it is the flip side of rarely flagging.**
- `FINAL_RESEARCH_DRAFT.md:279` contrasts RELIC's FPR 0.023 with text-rule FPR 0.32–0.89. RELIC flags 25/180 items, and its flagged set is a **strict subset** of normB's flagged set on both classes (overlap: only_A = 0 for positives and negatives).
- As a triage layer it can only *suppress* text flags. FAST_TRACK on SemBench avoids 23.6% of reviews and puts 2 wrong items among 25 accepted (H4 fails).
- `FINAL_RESEARCH_DRAFT.md:394` ("Triage aid") should cite that H4 result, not recall alone.

### Minor

- **m1.** "Normalized text baseline" means two different detectors: normB on SemBench, `textdiff_ignore_job_parameters` on external. normA/B were never run on external (not in `results/external/predictions.jsonl`). Defensible, since on the development benchmark normA/B equal textdiff_ignore_job_parameters (`NORMALIZED_TEXT_BASELINE.md:114-118`). Tables should say so explicitly.
- **m2.** `EXTERNAL_VALIDATION_RESULTS.md:112` "ranking… preserved" holds only inside the RELIC-scoped 824 (see M1).
- **m3.** SemBench has 16 `base_id` clusters (15 after exclusions) and 173/180 handwritten pairs. With so few clusters, bootstrap CIs are themselves unstable. Report the cluster count next to every CI (the draft partly does).
- **m4.** Counting zero RELIC-only detections against `raw_text`/`textdiff` is trivial: any CHANGING pair with a file difference is flagged by them. The stronger form of H2 (versus normB) also holds.
- **m5.** `README.md:244` "391 passing tests": not verified by me in either direction.

### Checked and found clean (no finding)

- **Information asymmetry between detectors.** All detectors receive only `(original, mutated, path)` (`relic_eval/detectors.py:1-7`, `text_baselines.py:4-6`). None receives the operator, label or oracle verdict. RELIC's `neutral_record()` (`detectors.py:47-64`) carries no mutation information.
- **RELIC–oracle code sharing.** `grep -rn jcl_oracle src/` finds nothing, so RELIC does not import the oracle. The reverse direction is also clean (below).
- **Baseline–oracle code sharing.** `_normalise_job_parameters` (`v2_eval.py:95-113`) is pure string processing and does not call `jcl_oracle`, although `v2_eval.py` imports `jcl_oracle.judge.describe_file` at module level for other purposes. `jcl_oracle/*` does not import `legacy_contract`.
- **Prediction-file integrity.** No `ERROR`/`NOT_RUN` status in either prediction file, so "errors scored as negatives" does not apply here.

---

## 3. Low recall: algorithm or operating point? (task 3)

**There is no operating point to move.**
- `relic_eval/detectors.py:103-106` flags when `len(risk_items) + len(false_positive_candidates) > 0`. The only threshold-like constant, `RiskDetector.FALSE_POSITIVE_THRESHOLD = 0.30` (`src/legacy_contract/risk/detector.py:306`), only decides which list an item goes into, so it never changes the binary output.
- The decision rule is one-directional by design. It flags contracts that are *broken* (present in the original, absent in the changed version) or *weakened* (`detector.py:383-395`, guard weakened). `diff.added` (`bcg/model.py:205`) is computed but never read.

Exploratory diagnostic: I re-ran RELIC V2 read-only on all 180 pairs (0 mismatches with the committed predictions) and computed the BCG diff for each.

| Non-identical CHANGING false negatives (n = 55) | count | categories |
|---|---|---|
| **Empty contract-graph diff** (no broken/added/modified contract) | **46** | disp_change 16, return_code_effect 12, dataset_dependency_change 10, cond_logic_change 8 |
| Non-empty diff, but only `added` or a strengthening `modified` | 9 | 5 appended-step pairs (M4: +1 TEMPORAL contract added); 2 `cond_always_bypass` (COND=(0,LE) *added* to a step that had none, so it creates a contract rather than weakening one); 2 `cond_strictness_tightening` (guard made *stricter*, so `guard_weakened` is false by design) |

- No false negative has 0 contracts in the original. None looks like a crash or parse failure.
- The 46 empty-diff cases are **outside the representation**. The extractor (`static_analysis/extractor.py:61-120, 148-249, 288-370`) models step order, in-file producer→consumer pairs and COND tests only. DISP value changes (CATLG→KEEP, SHR→OLD), PGM= substitution, IDCAMS/utility parameters and redirection of an input DSN that nothing in the file produces cannot produce a contract change.
- The 9 cases are **construct mismatches**. RELIC asks "was a contract the original guaranteed broken or weakened?"; the label asks "does behaviour differ?".
- Most permissive variant RELIC's graph supports (flag on *any* broken/added/modified contract; exploratory, never pre-registered): EXCL_25 TP 32, FP 2, FN 46, TN 75, MCC 0.464, F1 0.571, against normB's 0.684/0.848. Relaxing the direction recovers 9 TP and costs no FP, but leaves most of the gap. **The recall deficit is mainly algorithmic (coverage of the contract vocabulary).**

**In-scope comparison** (exploratory and post hoc: the category subset was chosen after seeing results). The subset is positives from RELIC's modelled categories (step_reorder_dependent, cond_logic_change, producer_consumer_change) plus all negatives.
- ALL (n = 131, 44 pos): relic_v2 MCC 0.564 vs normB 0.512.
- EXCL_25 (n = 115, 38 pos): relic_v2 0.619 vs normB 0.605. ΔMCC +0.014, 95% CI [−0.147, 0.133] (16-cluster bootstrap). F1 is still lower for RELIC (0.689 vs 0.731).
- The 5 mislabelled appended-step pairs (M4) count as in-scope positives, which makes this comparison slightly *harder* for RELIC.
- Reading: **inside its declared scope RELIC is statistically indistinguishable from the best normalised text rule.** It loses on SemBench because SemBench is mostly out of scope. That makes "RELIC is worse" partly a statement about scope. It is not evidence that RELIC is better in-scope, and it does not rescue H2 (RELIC-only TP is still 0 in-scope).

---

## 4. Recommended actions

1. **Rewrite `paper/v2/*.tex` and `paper/paper.md`, or mark them superseded.** Make the abstract lead with: H1 rejected on SemBench (ΔMCC −0.20, CI excludes 0), H2 rejected (0 RELIC-only TPs in any population), external F1 0.9755 < 0.9978, and external labels ≈ operator identity. Remove "independent" from the title and every oracle mention; use "code-independent, same-author, unvalidated" (C1, M7).
2. **Report the external results three ways:** scoped (824), scope-inclusive (970: RELIC F1 0.884, MCC 0.588), and non-cosmetic negatives only (n = 3, stated as uninformative). Add repo-level leave-one-out and pooled-excluding-yetacp as the primary uncertainty, per the protocol (M1, M6, C2).
3. **Fix README:** "11 repositories" → "7 contributing repositories (one supplies 71.5%)"; delete "random subsample" at `:102`; demote the v1.0 "primary result" block below the V2 negative result; replace "specificity advantage" with the 0.9811 trivial-rule comparison (M5, M7).
4. **Register SemBench defect M4** (5 appended-step pairs) in `DEFECT_REGISTER.md`, and add a sensitivity row excluding them. Do not edit the frozen files.
5. **Add CHANGING SemBench items that fall inside each normalisation rule's documented blind spot** (JOB-card COND/TYPRUN/TIME, positional/ordered operands, case-significant unquoted text). This tests the text baseline's cost, not only its benefit (M3). New items must be labelled as post-freeze.
6. **Amend the prereg** (dated, as an amendment): fix the H4 population, and record that the in-scope comparison of §3 is exploratory. Count in the stated comparison total the comparisons I ran: 4 ΔMCC bootstraps, 1 in-scope bootstrap, the any-BCG-change variant, the scope-inclusive external recompute, and the operator-identity accuracy.
7. **Replace the "84 validated preserving pairs" sentence** (M8), and tie the triage framing to the H4 failure (M9).

---

## 5. Tests and checks run

- Script R1 (independent recompute, stdlib): confusion/F1/MCC for 8 detectors × 4 populations and 5 external detectors plus per-repo; diffed against `CANONICAL_NUMBERS.json` (0 differences); byte-level identical-pair detection; RELIC-only TP search; FN breakdown by category; external operator/negative analysis.
- Script R2 (prereg hypotheses, stdlib): H3 Wilson bounds (pooled and per repo), H4 FAST_TRACK per population, 10k cluster bootstrap ΔMCC.
- Script R3 (exploratory; venv Python 3.11, `PYTHONPATH=src`, read-only import of `relic_eval.detectors`): re-ran RELIC V2 on 180 pairs (0 mismatches); per-pair BCG diff sizes; any-BCG-change variant.
- Script R4 (exploratory): in-scope SemBench subset with bootstrap; per-case detail of the 9 non-empty-diff FNs; manual `diff` of 8 case pairs.
- External scope-inclusive recompute (stdlib).
- `sha256` of `text_baselines.py`, `detectors.py`, `v2_eval.py`, `mutate.py` and `jcl_oracle/judge.py` against the freeze records: all match.
- Not run: `pytest` (I did not want cache or bytecode written into the repo), git history.

## 6. Remaining uncertainty

- Without git history I cannot establish the order of events (taxonomy → rules → freeze) or whether the SemBench author knew RELIC's blind spots when choosing categories (32/93 CHANGING pairs are `disp_change` or `return_code_effect`, which RELIC cannot represent; RELIC recall there is 1/32). Either direction of bias is possible.
- The in-scope analysis (§3) uses a category subset I chose after seeing results, on 16 clusters. Its CI is wide and it must not become a headline.
- All truth labels come from the same-author oracle or author arguments. Every number here, including mine, is conditional on that oracle (zero returned human labels in `review_package`).
- Whether the 144 out-of-scope "DIFFERENT" renames are real behaviour changes depends on the oracle's single-file observable (renaming an output with no in-file consumer). A human might call some of them cross-file-only.
- The external H3 pass rests on positives dominated by two operators (SPLIT_JOB 274, SWAP_ADJACENT_STEPS 268) from one repository.

---

## Appendix A — logic of the scripts (re-derivable)

- **Populations.** ALL = 180. EXCL_25 = drop IDs whose `original.jcl` bytes equal their `transformed.jcl` bytes. EXCL_15 = drop only those with truth CHANGING. CLEAN_CORE = drop identical ∪ `oracle_agrees_with_expected == false` ∪ any non-OK status (empty set).
- **Metrics.** F1 = 2TP/(2TP+FP+FN). MCC = (TP·TN − FP·FN)/√((TP+FP)(TP+FN)(TN+FP)(TN+FN)), undefined when the denominator is 0.
- **Bootstrap.** `random.Random(20261004)`; per resample, draw |clusters| `base_id`s with replacement and concatenate their items; drop resamples where either MCC is undefined (none were); percentile 2.5/97.5.
- **Wilson lower bound.** z = 1.96.
- **FAST_TRACK.** text = normB (SemBench) or textdiff_ignore_job_parameters (external); accepted = RELIC ∧ text; avoided = |accepted|/|text|; wrong = accepted with truth false.
- **BCG diagnostic.** For each pair, `_bcg(text, 'x.jcl', legacy=False, v2=True)` on both files, then `b0.diff(b1)`; count `broken`, `added`, `modified`. "Any change" = sum > 0.
- **External scope-inclusive.** EVALUABLE ∪ {OUT_OF_SCOPE with `oracle_label` ∈ {DIFFERENT, EQUIVALENT}}; truth = `truth` for EVALUABLE, `oracle_label == DIFFERENT` otherwise.
