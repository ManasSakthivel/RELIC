# RELIC V2 algorithm and architecture error analysis

Scope: error analysis only. Every SemBench and external result here is post-hoc development data (the aggregates were known before this analysis; see PREREGISTRATION.md). No change proposed below can support an "outperforms text diff" claim. No file under src/, benchmarks/, results/, datasets/ or existing reports was modified. Added files: this report and two probe scripts in `reports/recovery/scripts/` (`algo_fn_trace.py`, `algo_mechanism_tests.py`). Python: venv python, `PYTHONPATH=src:.`.

## 1. What the detector actually computes (code evidence)

Binary output = "at least one contract was lost or a COND guard was weakened", nothing else.

- `relic_eval/detectors.py:RelicDetector.predict` parses both texts, builds a BCG, runs `RiskDetector.detect`, returns `Prediction(n > 0)` with `n = len(risk_items) + len(false_positive_candidates)`.
- Only three contract families are extracted (`src/legacy_contract/static_analysis/extractor.py`):
  - TEMPORAL: one contract per pair of consecutive steps in declared order (`parsers/jcl_parser.py:_add_step_ordering`, last method of the file).
  - RESOURCE: producer step -> consumer step of a shared DSN; role is decided from the FIRST DISP status only (`jcl_parser._process_dd`). The dataset is NOT in the contract signature.
  - CONTROL_FLOW: COND `(rc,op[,step])` (`extractor.py` COND_PATTERN; only the first `COND=` match on an EXEC is stored, `jcl_parser._process_exec`).
- Diff (`bcg/model.py:BCG.diff`): signature = (type, subject, predicate, object). Flags: `broken` (signature absent in mutated) and `modified`. `diff.added` is never read by `RiskDetector.detect` (`risk/detector.py`).
- "modified" can only fire on an `rc_threshold`/`operator` change (`CONTRACT_PARAMETER_KEYS`, `bcg/model.py:238`) AND `guard_weakened` (`risk/detector.py:55`). The confidence-delta branch (`abs(conf diff) > 0.05`, validation_state change) cannot fire on source diffs: every extractor assigns constant ConfidenceVectors and `STATIC_CANDIDATE`, identical for the same signature in both files.
- Parser blind spots: PROC/PEND/IF/ELSE/ENDIF/SET/INCLUDE are `pass` in `_process_token`; in-stream `DD *` is not tracked (D-021); COND `EVEN`/`ONLY` yields no contract (D-009); step ordering is reset per JOB (D-020).

### (b) Operating point: confirmed there is no lever
There is no score. `FALSE_POSITIVE_THRESHOLD = 0.30` (`risk/detector.py`, class attribute of `RiskDetector`) only moves an item between `risk_items` and `false_positive_candidates`, and `RelicDetector.predict` sums both lists into `n`, so it cannot change a verdict. Confidence values are constants, so no threshold on them would separate anything. Therefore all 70 + 33 misses below are class (a): the relevant semantics are not modelled, or a diff rule ignores them. None is an operating-point issue.

## 2. SemBench: 70 FN, 2 FP (relic_v2: TP 23, FN 70, FP 2, TN 85; recomputed from results/sembench/predictions.jsonl)

Per-case trace: `reports/recovery/scripts/algo_fn_trace.py` (original vs transformed contract signatures, JCL diff). Mechanism probes on synthetic JCL: `algo_mechanism_tests.py` (14 probes, results in section 6).

| # | Category (FN) | n | Root cause (code) | Defect | Probe | Fixable in existing architecture? | Case ids (sembench_) |
|---|---|---|---|---|---|---|---|
| 0 | Generator no-op (original byte-identical to transformed, label CHANGING) | 15 | Nobody can detect; the label is wrong, not a detector gap | D-025 / oracle | - | n/a (relabel) | 100,103,108,111,112,123,128,153,154,156,158,160,161,170,175 |
| 1 | DISP changes | 16 | DISP = 3-way role from the first status only. Second/third sub-parameters (CATLG/KEEP/DELETE) dropped: 7. SHR->OLD both "consumer", exclusivity unmodelled: 5. NEW->OLD / SHR->NEW flips a role but forms or breaks no producer-consumer pair: 4. | none exact (nearest D-004, D-012) | T1, T2 | Partly. Sub-params/exclusivity are a small extension of the contract parameters; role flips need a per-DD access-mode fact. | sub-param: 115,116,118,121,124,127,130; SHR/OLD: 117,120,126,129,177; role flip: 114,119,125,131 |
| 2 | COND family | 12 | (a) duplicate `COND=` keyword on one EXEC, only the first captured: 6. (b) COND added where none existed: only an "added" contract, never flagged: 2. (c) tightening (4,LT)->(0,NE) is not "weakened": 2. (d) `COND=EVEN` has no contract: 1. (e) `IF (RC=0)` -> `<=4`: IF not parsed: 1. | (a),(b) not registered; (c) D-010; (d) D-009; (e) D-006 | T3, T4, T13 | (a)-(d) yes, small rule changes. (e) needs an IF/THEN model (new semantic model). | 138-143; 145,146; 137,149; 134; 144 |
| 3 | Dataset-name redirect that neither forms nor breaks a producer-consumer pair | 9 | RESOURCE needs both a producer and a consumer of the same DSN in the file, and the key is (producer step, consumer step) without the dataset. Changing an input-only or output-only DD's DSN, or one of two datasets linking the same step pair, leaves the signature set unchanged. | D-007/D-011 partially; signature design not registered | T6, T7 | Yes for the key (put DSN in the signature); FP cost unmeasurable (D-014). | 098,101,102,104,105,107,109,110,113 |
| 4 | Program substitution (PGM=IEBGENER -> IEFBR14) | 5 | Program is an IR relation (CALLS) but no contract family uses it. | D-007 | T8 | Needs a program-semantics table or a PGM-changed rule (the latter is just a text rule on one token). | 167,168,169,171,173 |
| 5 | In-stream utility control statements (IDCAMS DEFINE/DELETE/PRINT, SORT FIELDS, IEBCOPY SELECT, binder NAME, INDATASET) | 8 | `SYSIN DD *` content is not parsed. | D-021, D-007 | T12b | No: needs per-utility command models (new semantic model). | 106,162,163,164,165,166,172,179 |
| 6 | Appended step instead of a swap (generator quirk, label questionable) | 5 | Case files contain only `+//EXTRA EXEC PGM=IEFBR14`; no inversion. The mutated BCG has one extra TEMPORAL contract, which is `added` and never read. | new (generator/label), D-025 | T9 | Yes: "added contract => flag" (section 5, item 1). | 087,089,090,092,096 |
| | Total FN | 70 | | | | | |

Sum check: 15 + 16 + 12 + 9 + 5 + 8 + 5 = 70. Of the 55 real-change FNs, 11 are cases the benchmark's own oracle labels EQUIVALENT (117,118,120,121,124,126,127,129,130,165,172; CANONICAL_NUMBERS `oracle_disagree_non_identical_ids`), so up to 11 of the 55 are label disputes, not clean detector failures (9 of them in the DISP category). Seven FN in total have a strictly larger contract set in the mutated file (087,089,090,092,096,145,146).

SemBench FPs (2): sembench_078, 079 (`step_name_refactoring`). Cause: entity id = hash(artifact::STEP::name) (`ir/model.py:118-123`); renaming a step makes every contract naming it "broken" (probe T10). Identity is name-based, not position- or content-based (D-001/D-005 family). Normalised text B also false-positives both, so they are shared errors, and the oracle disagrees with both labels (CANONICAL list).

Structural split of the 55 real FN:
- No model of the semantics (new semantic model needed): categories 4, 5 and 2(e) = 14.
- Feature present in the IR but unused by any contract or diff rule (extractor/diff extension only): categories 1, 3, 6 and 2(a)-(d) = 41.
These 41 are architecturally fixable, but see section 5: no independent data exists to show any fix generalises.

## 3. External: 33 FN, 0 FP of 691 positives (824 evaluable)

relic_v2 TP 658 / FN 33 / FP 0 / TN 133; `textdiff_ignore_job_parameters` TP 691 / FN 0 / FP 3 / TN 130. RELIC-only TP: 0 (the text rule catches all 33 misses). FN by operator (positives in parentheses): SPLIT_JOB 14 (274), SWAP_ADJACENT_STEPS 8 (268), RENAME_OUTPUT_DATASET 6 (29), REMOVE_COND 3 (28), ALTER_COND_THRESHOLD 2 (27). Concentration: 13 files carry all 33 FN; 29 of them are in `yetacp_mvs_sysgen`, 3 in zowe-cli, 1 in mainframed_Enumeration; `duplicate_steps.jcl` has 0 of 2 positives detected.

The external clones are not in the repo, so the FN files could not be re-run. The per-FN causes below combine metadata (operator, site) with mechanism probes on synthetic JCL; file-level attribution is HYPOTHESIS, not verified.

| Category | n | Probable root cause | Defect | Verified how |
|---|---|---|---|---|
| SWAP/SPLIT where the site names are identical (`SORT<->SORT`, `UNPK50<->UNPK50`, `duplicate_steps.jcl`) | ~5 | Same-named steps: swap leaves the name sequence unchanged | D-005 | ad hoc probe (identical-name swap unflagged); files not re-run |
| SWAP/SPLIT in multi-job or PROC-calling files (`10_rakf_recv_ptfs`, `sysgen00/01`, `multiple_procs`) | ~17 | Per-job step-order reset (only the last job's chain kept), PROC/IF steps not expanded | D-020, D-006 | hypothesis only; SPLIT in a simple single-job file IS detected (ad hoc probe) |
| REMOVE_COND / ALTER_COND in `fdz1d02`, `mvs00` (SPLIT_JOB at the same step also missed) | 4-5 | A COND without a step name on the FIRST step has no preceding step to bind to, so no contract exists; a SPLIT before the first step breaks no adjacent pair | not registered | mechanism verified on synthetic JCL (REMOVE_COND, ALTER, SPLIT on the first step all unflagged); applicability to these files unverified. IBM ignores COND on a first step, so these labels may be oracle artefacts: unchecked |
| REMOVE_COND `PRINT COND=EVEN` (`SRCHLIST.jcl`) | 1 | EVEN not extracted | D-009 | site text and code |
| RENAME_OUTPUT_DATASET: `&&OBJ` temporaries (MAKEFTPD, 4), `ALLOC.*` (rpf184, 2) | 6 | `&&TEMP` and symbolic names are treated as artifact-wide names; pairing across steps/PROCs | D-011 | hypothesis |

### Scope exclusion that matters more than the 33
The freeze drops 163 RENAME_OUTPUT_DATASET mutants as `OUT_OF_SCOPE` ("no consumer of this dataset inside the analysed JCL file (cross-file effect only)"; 105 yetacp, 54 zopeneditor, 3 mainframed, 1 brexx) and 14 as INVALID. Of the 163, 144 have oracle label DIFFERENT; relic_v2 flags 3 of them, `textdiff_ignore_job_parameters` flags all 144. This is the structural limit of RESOURCE (needs an in-file consumer) written into the benchmark as an exclusion. Post-hoc sensitivity on the same predictions: recall including the exclusion = (658+3)/(691+144) = 0.792, versus the reported 0.952. Exploratory; the exclusion was declared in the freeze, but it removes exactly the class RELIC cannot do.

## 4. Cost and architecture-justification judgement

Cost (measured): 180 SemBench pairs through `RelicDetector(False, True).predict` in 0.063 s total (0.35 ms per pair; the original BCG is `lru_cache`d, so this is about one parse + extract + diff of the mutated file); the largest corpus file (db2cre.jcl, 1249 lines) took 2.9 ms. Text diff is microseconds. Computation is not a constraint; value is.

Measured benefit in the data:
- RELIC-only true positives: 0 on SemBench (55 text-only vs 0 RELIC-only) and 0 on external (33 text-only vs 0). H2 (complementarity) fails on both.
- The only measurable advantage is specificity on harmless edits: 26 of the 28 SemBench false positives of `normalized_text_B` are avoided by RELIC (7 SYSPRINT/SYSIN reorders, 5 `DSN`/`DSNAME` synonyms, 4 explicit DISP defaults, the rest other reorders/quoting/continuation). Each is a syntactic normalisation (DD order, keyword synonym, DISP default) that a larger deterministic normaliser could absorb without a contract model. The normaliser was frozen before the data, so this is an observation about baseline strength, not an extra comparison. The price of RELIC's specificity is recall 0.247 vs 0.839 on all 93 positives (0.295 vs 1.000 on the 78 non-identical ones). MCC (ALL_180): RELIC V2 0.324 vs normalized_text_B 0.525; CLEAN_CORE 0.464 vs 0.694 (CANONICAL_NUMBERS).
- External: RELIC FP 0 vs text 3; FN 33 vs 0; post-hoc, including the 163 excluded renames, RELIC misses 141 more.
- Explanatory value (H5) is untested (binary predictions only).

Judgement: on current evidence the contract/BCG/diff machinery is not justified by detection benefit. The surviving claim is "fewer false alarms on cosmetic edits than a frozen text rule, at a large recall cost", and a benchmark whose negatives are almost all cosmetic (D-014, D-025) cannot test whether RELIC reasons about behaviour at all.

### V1.0 / V1.1 / V2 improvements and their credibility
SemBench (180 cases): v1.0 TP 15 / FN 78 / FP 2; v1.1 TP 23 / FN 70 / FP 2; v2 identical to v1.1 on every case (0 discordant). Gain v1.0->v1.1 = 8 TP (6 COND-parameter comparisons, 1 GDG relative generation, 1 SHR->NEW), 0 losses; v1.1->v2 = 0.
External (824 evaluable): v1.0 FN 79; v1.1 FN 48 (+31 TP, 0 losses); v2 FN 33 (+15 TP, 0 losses); FP 0 for all three. v1.1->v2 by operator: RENAME 17->6, SPLIT 15->14, SWAP 11->8, REMOVE_COND 3->3, ALTER 2->2.

Credibility:
- The v1.0->v1.1 changes (COND parameter comparison, continuation merging, COND regex) are post-hoc spec-conformance fixes made after failures on the development families (detectors.py docstring; D-018). The gain is in-sample.
- D-001..D-004 were all diagnosed by inspecting the same CardDemo/OMP/GenApp files used to score them (DEFECT_REGISTER header: all inspected during diagnosis, none held out). The quoted dev improvements (F1 0.951 -> 0.980; recall on repeated-name files 0.391 -> 0.766) are therefore in-sample and selected on failure. D-004 even costs 2 TP on dev. They show the bugs were real, not that V2 generalises.
- The external v1.1->v2 gain (+15 TP, no FP) is the least contaminated figure: other repositories, detector frozen before external results per SUBJECT_FREEZE (not independently verifiable here). But (i) oracle and mutators are same-author (D-013), (ii) the operators are those the detector was co-designed with (D-010), (iii) there is no per-defect ablation on the external set, so the 15 cannot be attributed to D-001..D-004, and (iv) V2 still trails a one-line text rule on every external operator.
- Zero effect on SemBench means the V2 "improvement" is a property of the dev/external corpora (repeated step names, DSNAME, pre-delete idiom), not of the hand-written benchmark.

## 5. Proposed improvements, only where backed by error counts

None of these can change the comparative claim; they target specific evidenced gaps. Effect sizes are in-sample upper bounds on SemBench FN converted, with the checked negative-side exposure.

1. Treat `diff.added` (new contract) as a change. Evidence: 7 SemBench FN (087,089,090,092,096,145,146) have only added contracts. Checked: the only SemBench negatives with added contracts are the two existing rename FPs, so +7 TP and +0 FP in-sample. Needs independent negatives that legitimately add a step or guard. Existing architecture.
2. Capture all COND keywords on an EXEC, extract EVEN/ONLY, flag tightening as well as weakening. Evidence: 6 + 1 + 2 = 9 SemBench FN; external 1 EVEN FN. Caveat: a duplicate `COND=` keyword is invalid JCL, so the 6 may be generator errors (verify before counting). Tightening needs the D-010 mutator/detector co-design fixed first. Needs real COND edits from change histories.
3. Add DISP sub-parameters and SHR/OLD exclusivity. Evidence: 12 FN, of which 9 are oracle-disputed, so the confirmed gain is at most 3. Needs the independent review of those cases (the 60-case package has zero returned labels). Existing architecture.
4. Put the DSN in the RESOURCE signature and track input-only DDs. Evidence: 9 SemBench FN, 6 external RENAME FN; collapse shown by probes T6/T7. Risk: more FP on benign DSN synonyms/symbolics (D-011), unmeasured. Needs benign DSN-change negatives on independent files.
5. Position/content-based step alignment (rename FP, same-name swaps). Evidence: 2 SemBench FP, D-005 (13 dev FN), about 5 external FN. D-005 states no step-content negatives exist to price the FP cost. Needs benign step-rename/reorder negatives from real repositories.
6. IF/THEN/ELSE, PROC expansion, in-stream utility commands, program semantics: 14 SemBench FN plus the 144 excluded renames. These are new semantic models and large efforts; nothing in the data shows they would beat a normalised text rule. Do not pursue without a use case that needs behavioural explanation (H5) and an independent labelled corpus.
7. Instrumentation, no detection change: per-file unsupported-construct report (D-023) to partition FN automatically; fix per-job step ordering (D-020) and first-step COND handling after a dedicated ablation.

Data needed to validate any of the above: a corpus never opened during development (none exists), an independent oracle, and negatives that are not comment/MSGCLASS edits (D-014, D-025). Without these, any improvement is fitting to the known error set.

## 6. Tests run
- Recomputed confusion matrices for relic_v1_0/v1_1/v2, normalized_text_B, textdiff_ignore_job_parameters and discordant pairs from `results/sembench/predictions.jsonl` and `results/external/predictions.jsonl`.
- `algo_fn_trace.py`: all 72 SemBench errors, original vs transformed contract signatures plus JCL diff (output in the session scratchpad, `algo_trace.json`).
- `algo_mechanism_tests.py`, 14 synthetic probes. Flagged: COND weakening (T5), benign step rename (T10, a false positive). Not flagged: DISP sub-parameter (T1), SHR->OLD (T2), added second COND (T3), COND tightening (T4), consumer reads another DSN with a second link surviving (T6), producer rename with a surviving link (T7), PGM swap (T8), appended step (T9), IF widening (T13), in-stream utility change (T12b), DSN->DSNAME (T11, correctly). Ad hoc probes (not saved): COND on the first step (REMOVE, ALTER) and SPLIT before the first step unflagged; SPLIT before a later step flagged; identical-name swap unflagged. T12 (a degenerate in-stream probe) is not informative; T12b is the valid one.
- Timing: 180 pairs 0.063 s; db2cre.jcl (1249 lines) 2.9 ms.

## 7. Remaining uncertainty
- External FN file-level causes are hypotheses (clones absent); only mechanisms were verified on synthetic JCL.
- Some SemBench misses are label problems, not detector gaps: 15 no-ops plus 11 oracle-disputed positives, so up to 26 of 70 FN are not clean detector failures.
- The 6 duplicate-`COND=` cases and first-step COND cases may be invalid or semantically null JCL; not checked against IBM semantics or the oracle.
- Cost was measured with the original-BCG cache warm; cold per-file cost is about double.
- No independent or held-out data exists, so none of the section 5 effect sizes is validated.
