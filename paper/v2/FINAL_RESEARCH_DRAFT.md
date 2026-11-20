# Beyond Textual Change: Evaluating Behavioural Preservation in Legacy Batch Modernization

**Status of this document.** Research draft, not peer reviewed. Prepared by Agent 6 (Integration and Paper) of the RELIC final sprint from repository artefacts on branch `research/relic-v2-final-sprint`.
**Evidence rule.** Every number is copied from a machine-readable file whose path is given beside it and was read by the author of this draft. Numbers marked *(derived)* were computed by the draft's author from committed raw records (`predictions.jsonl`, `cases/*.jcl`, confusion matrices) and are not stored in any committed JSON; the derivation is stated. Numbers that exist only in a prose report are marked *(report)*. Where evidence was not available the text says `[PENDING EXPERIMENT]` and names the blocker. Nothing is estimated.
**Validation status.** All RELIC V2 figures on the old benchmark are **development-set** figures. All JCL-SemBench labels are **author-only** (every case has `independent_review_status = PENDING`); every SemBench table below carries the tag *labels author-only*. No independent review, no independent oracle validation and no blind evaluation exist at the time of writing.

---

## Abstract

Automated checks for legacy batch modernization are usually evaluated by asking whether a tool notices that a job changed. That is a *textual* question. The question that matters to a migration team is *behavioural*: does the new job still do what the old one did? We study how far the first can stand in for the second, using z/OS JCL batch jobs as a case study.

We first examine an oracle-labelled mutation benchmark built over three public JCL corpora (656 candidate mutants; 566 evaluable; 66 files). A static behavioural-contract extractor (RELIC) reaches pooled F1 0.9048 (v1.0), 0.9510 (v1.1) and 0.9800 (V2) (`results/v2/v2_metrics.json`). A *post-hoc* text rule that drops comments and JOB-card parameters reaches F1 0.9978, because 104 of the 106 behaviour-preserving mutants are comment or MSGCLASS edits; the benchmark label agrees with "a non-cosmetic text edit occurred" on 564 of 566 mutants, and the paired F1 difference V2 minus that rule is [−0.0373, −0.0032] (file-level cluster bootstrap). A RELIC-only report would have given false assurance that the benchmark tests behavioural reasoning.

We then built JCL-SemBench, 180 matched (original, transformed) pairs in 12 categories (87 behaviour-preserving, 93 behaviour-changing, 16 base programs) designed so that text change and behaviour change dissociate. On SemBench (`results/sembench/metrics.json`, labels author-only) RELIC V2 has specificity 0.977 and recall 0.2473 (MCC 0.3241, 95 % CI [0.248, 0.3816]); a frozen normalised-text rule (variant B) has MCC 0.5249 [0.4201, 0.629], and the pre-specified paired test finds the text rule better (ΔMCC −0.2008, CI [−0.2992, −0.1018], Holm p = 0.0203). The hypothesis that RELIC beats a normalised text diff by a margin is refuted on SemBench. V2's defect fixes make no difference on SemBench (0 discordant cases against v1.1). Oracle–author label disagreement affects 28 of 180 pairs, and 25 pairs (15 of them labelled behaviour-changing) have byte-identical original and transformed files, which we report as a construction defect. A frozen-detector run on seven further public repositories (824 evaluable mutants, 71 files; `results/external/metrics.json`) gives RELIC V2 F1 0.9755 against 0.9978 for the same trivial rule; its labels come from the same non-independent oracle and 130 of 133 negatives are again comment/MSGCLASS edits. Independent review of SemBench labels is **[PENDING]** (a 60-case blind review package exists; no responses). An oracle independence audit report exists and concludes that the oracle is code-independent only (shared lexer, single author, no z/OS comparison). We make no claim that RELIC outperforms a text rule or a language model, and no claim of independent validation, blind evaluation or production compatibility. The contribution that the evidence supports is the benchmark-and-protocol one: a concrete demonstration that trivial text rules must be reported before a modernization checker's score is read as behavioural assurance.

---

## 1. Introduction

Re-implementing a JCL job stream on another platform is risky in a specific way: the new job usually runs, but behaves differently in situations the migration did not consider. A step that used to be bypassed after a failure now runs, a consumer reads a dataset before its producer has rewritten it, or a renamed output is no longer found downstream. These rules are implicit in JCL semantics [`ibm_jcl_reference`]. Tools that compare versions of such jobs are evaluated, in practice, on whether they flag a change. A flagged change is not necessarily a changed behaviour, and an unflagged one is not necessarily preserved behaviour.

This paper asks how far *textual change* can stand in for *behavioural change* when evaluating modernization checks, and what a benchmark must contain for the two to be separable. RELIC, a static extractor of behavioural contracts (temporal, resource, control-flow) from JCL with a contract-level diff, serves as the system under evaluation, not as the claimed contribution.

### 1.1 Contributions and their evidence status

Agent 5 (`research/v2/FINAL_NOVELTY_ASSESSMENT.md` §5) proposes one primary contribution (P) and exactly three supporting ones (S1–S3). The sprint brief's candidate list (C1–C5) maps onto them as follows; each is stated only as far as the evidence reaches.

| # | Candidate contribution | Maps to | Evidence status at time of writing |
|---|---|---|---|
| C1 | A semantically grounded JCL benchmark (JCL-SemBench) | P | **Narrowed.** The benchmark exists (180 pairs, per-pair written equivalence argument, oracle verdict recorded; `benchmarks/sembench/cases.jsonl`). Label validity is **not established**: labels are author-only (review PENDING), the oracle disagrees with the author label on 28 pairs, and 25 pairs have identical original/transformed files (§4.2, §6.5). "Semantically grounded" is therefore a design intent backed by written arguments, not a validated property. |
| C2 | A methodology that separates textual from behavioural change | S1/S2 | **Supported as a protocol.** Normalised-text ceiling, label–predicate agreement, paired cluster bootstrap with a pre-specified decision rule are implemented and applied to both benchmarks (§5.3, §6.2, §6.6). |
| C3 | An assessment of oracle dependence and benchmark leakage | S1 | **Narrowed.** Code-independence by import check; shared lexer, same author, no z/OS comparison documented (D-013). Oracle/author disagreement on SemBench quantified (28/180). Audit report (`ORACLE_INDEPENDENCE_AUDIT.md`) concludes "code-independent only"; tokenizer ablation, second semantic model and independent review are **[PENDING]** (§6.8). |
| C4 | An empirical study of false assurance in automated modernization evaluation | S2 | **Supported on two benchmarks, one language.** Old benchmark: trivial rule F1 0.9978 vs V2 0.9800. External mutation run: 0.9978 vs 0.9755. SemBench: normalised text rules MCC above V2's. Not a general study. |
| C5 | Explicit uncertainty and evidence reporting | S1 | **Supported.** Complete mutant accounting, cluster-bootstrap CIs, Holm-corrected paired tests, both invalid-output policies for LLM bounds, claims register (Appendix A). |

### 1.2 What we do not claim

That RELIC outperforms a normalised text diff or a language model (on SemBench the evidence points the other way); that the mutants or SemBench pairs represent real migration defects; that the oracle matches z/OS; that V2 figures generalise beyond inspected public corpora; that any corpus used was blind (CardDemo, OMP course and GenApp were inspected during defect diagnosis; the external repositories were screened by aggregate counts and fragments); that the work has been independently validated or reviewed; or that RELIC is compatible with production JCL. We never use "first" about any element of this work.

---

## 2. Related Work

Scope note. Only references present in `paper/v2/references.bib`, `research/v2/literature_candidates.bib` or `research/v2/final_verified_references.bib` are cited. Bibliographic metadata of these was verified against Crossref or arXiv (`research/v2/LITERATURE_AND_NOVELTY_ASSESSMENT.md`; `research/v2/FINAL_NOVELTY_ASSESSMENT.md` §1). Descriptions of what each work does were generally *not* re-checked against full texts; Agent 5 marks which were read at abstract level. `papadakis2019advances` is not cited (author list unverified).

**Behavioural specifications and spec mining.** Design by contract [`meyer1992applying`] makes obligations explicit. Daikon [`ernst2007daikon`], automata mining [`ammons2002mining`, `lorenzoli2008automatic`], temporal-rule mining [`lo2008mining`] and spec-mining quality work [`legoues2012measuring`] derive specifications from executions. RELIC's contracts are template-instantiated syntactic patterns over job text; nothing is learned. We claim no advance over this literature.

**Semantic differencing and regression verification.** Semantic Diff [`jackson1994semantic`], SymDiff [`lahiri2012symdiff`], differential assertion checking [`lahiri2013differential`], differential symbolic execution [`person2008differential`] and regression verification [`godlin2012regression`, `felsing2014automating`] compare versions with formal program models. RELIC's contract diff is far weaker; it applies to a language for which we had no such model. Differential testing [`evans2007differential`] is closest to our oracle: compare two versions by executing a model of each.

**Equivalence-preserving transformations and metamorphic testing.** Generating equivalent variants of a program to test a tool is established: equivalence modulo inputs for compilers [`le2014emi`], the metamorphic-testing survey [`chen2018metamorphic`], semantics-preserving transformations to test static analysers [`zhang2023statfier`], robustness of neural code models under semantics-preserving transformations [`rabin2021generalizability`, `yefet2020adversarial`], a transformation suite with human verification that meaning is preserved [`wang2022recode`], and an LLM equivalence-checking benchmark [`wei2025equibench`]. A matched equivalent/non-equivalent pair design is therefore **not** our contribution; only its application to JCL and the construct-validity diagnosis that motivated it are specific to this work.

**Mutation analysis and its validity.** Mutation originates in [`hamlet1977testing`, `demillo1978hints`] and is surveyed in [`jia2011mutation`]; the coupling effect is discussed in [`offutt1992coupling`]; whether mutants stand in for real faults is contested [`andrews2005mutation`, `just2014mutants`, `papadakis2018correlated`, `gopinath2014close`, `gopinath2017composite`]; equivalent mutants are a known problem [`madeyski2014equivalent`, `papadakis2015tce`, `kintis2018trivial`]. We use mutation to generate change pairs for a change detector; the behaviour-preserving mutants are the negatives. The oracle problem [`barr2015oracle`] applies directly: ground truth here is a model of JCL, not an execution. Independence of separately written artefacts cannot be assumed from code isolation [`avizienis1985nversion`, `knight1986independence`].

**Benchmark validity.** Weak tests or shortcut-prone labels mis-rank systems in code-generation and issue-resolution benchmarks [`liu2023evalplus`, `jimenez2023swebench`, `aleithan2024swebenchplus`]; benchmarks need construct validity [`raji2021everything`, `jacobs2021measurement`]; leakage and duplication inflate results [`kapoor2023leakage`, `allamanis2019duplication`, `sallou2024breaking`]; simple baselines should be checked against sophisticated methods [`fu2017easy`]; community benchmarks and their requirements are discussed in [`sim2003benchmarking`, `hasselbring2021benchmarking`], and reporting standards in [`ralph2020empirical`]. Our old-benchmark finding is an instance of this pattern; it is new evidence, not a new idea.

**Ordering and dependency analysis in operations languages.** Rehearsal [`shambaugh2016rehearsal`] checks Puppet manifests for determinism and idempotence; incorrect build rules are detected from observed accesses in [`licker2019incorrect`]; build-system dependency vocabulary is formalised in [`mokhov2020build`]; program dependence graphs are in [`ferrante1987pdg`]; infrastructure-as-code research is mapped in [`rahman2019mapping`]. These are the structurally nearest neighbours of RELIC's TEMPORAL and RESOURCE contracts.

**Legacy-language analysis and migration.** Control-flow extraction by semi-parsing [`deknop2022semiparsing`], transpilation-based mainframe migration [`schnappinger2021platform`], COBOL-to-Java migration [`sneed2010migrating`, `sneed2010cobol`] and feature location in COBOL systems [`vangeet2009feature`] share the industrial setting. LLM work for mainframe code [`dau2024xmainframe`, `dau2026cobolcoder`] (preprints) targets COBOL rather than JCL change detection.

**Responsible-engineering references.** Registered reports [`ernst2023registered`], datasheets for datasets [`gebru2021datasheets`], automation complacency [`parasuraman2010complacency`] and the professional ethics code [`gotterbarn2017acm`] inform §9; metadata verified, content not re-read.

**What the search did and did not establish.** In targeted queries (Agent 2: 28 Crossref and 10 arXiv; Agent 5: further OpenAlex, Crossref and arXiv queries, `FINAL_NOVELTY_ASSESSMENT.md` §1–2) we found no peer-reviewed work on JCL change-risk detection or a JCL behavioural-change benchmark. DBLP and Semantic Scholar were unavailable, grey literature and commercial JCL impact-analysis tools were **not** searched, and commercial tools "very probably exist" (Agent 5 §2). This is absence of evidence from an incomplete search, not a novelty finding. **[PENDING EXPERIMENT: systematic literature search]**.

### 2.1 Novelty boundary (Agent 5, `FINAL_NOVELTY_ASSESSMENT.md` §7.2)

| Element | Status | Allowed wording |
|---|---|---|
| Matched-pair / metamorphic design with equivalent and non-equivalent variants | **Established** | Cite [`le2014emi`, `chen2018metamorphic`, `zhang2023statfier`, `wang2022recode`, `wei2025equibench`]; not a contribution. |
| Benchmark-validity critique | **Established** | Cite [`liu2023evalplus`, `aleithan2024swebenchplus`, `raji2021everything`, `jacobs2021measurement`, `sim2003benchmarking`]; our old-benchmark finding is new evidence, not a new idea. |
| Trivial-baseline-first reporting | **Established** | Cite [`fu2017easy`]. |
| A JCL benchmark with preserving/changing pairs and documented semantics | No prior art found in the sources searched (candidate novel) | Search incomplete; **do not write "first"**. |
| Executable-semantics model of JCL as test oracle | No prior art found in the sources searched (candidate novel) | Model unvalidated against z/OS; if prior simulators exist in vendor tooling the claim collapses. |
| Layered oracle-independence audit | Incremental | Motivated by [`avizienis1985nversion`, `knight1986independence`, `barr2015oracle`]; audit report exists (`ORACLE_INDEPENDENCE_AUDIT.md`) but covers lexer-agreement and census experiments only; ablation, second model and human review **[PENDING]**. |
| Pre-declared refutation criteria for a benchmark paper | Incremental / established | [`ernst2023registered`]; here thresholds are proposed defaults, not registered before the first look (§3). |
| Contract extraction from JCL | Incremental | Def-use and ordering analysis applied to JCL. |
| Version-to-version contract diff for JCL | Incremental / unknown | No prior art found for JCL, search incomplete. |
| COND/return-code guard contracts | Unknown | Not found in any checked reference. |
| RELIC V2 outperforms a normalised text diff | **Refuted on the old benchmark and on SemBench** (§6.2, §6.6) | Not claimed. |
| RELIC outperforms LLMs | Unknown | Prior LLM comparison selection-biased (§6.4). |
| Generalisation to production JCL / real defects | Unknown | Not claimed. |

---

## 3. Research Questions and Falsifiable Hypotheses

Hypotheses are Agent 5's (`research/v2/FINAL_NOVELTY_ASSESSMENT.md` §6), quoted in compact form. **All numeric thresholds are Agent 5's proposed defaults; they were not pre-registered before the first look at SemBench or external results**, so the verdicts below are exploratory applications of pre-stated criteria, not registered tests. Primary metric: MCC. Outcomes: supported / refuted / inconclusive.

| RQ | Hypothesis (Agent 5) | Refuted if | Outcome here |
|---|---|---|---|
| RQ1 | **H1:** on SemBench pairs ΔMCC = MCC(RELIC V2) − MCC(normalised text diff) > 0.10 | Upper 95 % CI of ΔMCC < 0.10 (refuted); lower CI > 0.10 (supported); else inconclusive. Also refuted if a template-fingerprint or step-multiset baseline reaches MCC ≥ 0.9 × RELIC's | **Refuted** against both frozen normalised-text rules: ΔMCC vs A −0.1270 [−0.2187, −0.0328]; vs B −0.2008 [−0.2992, −0.1018] (`results/sembench/paired_tests.json`, ALL). Against the plain JOB-parameter-ignoring rule +0.0221 [−0.0774, 0.12] and plain textdiff +0.148 [0.0385, 0.2469]: upper CI ≥ 0.10 and lower CI < 0.10, i.e. inconclusive for the 0.10 margin, and "not distinguishable" under Agent 4's rule. The template-fingerprint and step-multiset baselines were **not run** **[PENDING EXPERIMENT]** (§6.6). Labels author-only. |
| RQ2 | **H2:** independent reviewers blind to oracle output agree with oracle labels, κ ≥ 0.80 | Lower 95 % CI of κ < 0.60, or any family with disagreement > 10 % | **[PENDING EXPERIMENT]** No completed review exists (§6.8). Observation only: the author's own labels differ from the oracle verdict on 28/180 (15.6 %) pairs, in 6 of 12 categories. |
| RQ3 | **H3:** re-labelling with an independent tokenizer and a second independently written semantic model changes ≤ 1 % of labels; detector ranking unchanged | Label change > 2 % or ranking flips | **Not tested — [PENDING EXPERIMENT].** No label-change rate under an independent tokenizer and no second semantic model exist. Agent 2's audit measured only *agreement* between the shared lexer and RELIC's own tokenizer (EXEC sequences 630/630; statements 1436/1519; §6.8), which informs F-01 but is not the H3 measurement. |
| RQ4 | **H4:** on a sealed external set RELIC V2's MCC falls by ≤ 0.10 relative to development | Drop > 0.10, or the external CI lower bound for MCC is below the best surface baseline's MCC ("no demonstrated advantage") | **Mixed / inconclusive.** Point estimate drop 0.9063 *(derived from the old-benchmark confusion matrix, §6.1; consistent with the ΔMCC of −0.0821 in `results/sembench/old_benchmark_ablation.json`)* → 0.8735 (`results/external/metrics.json` `pooled_effectiveness`) = 0.033 ≤ 0.10, but the trivial rule has MCC 0.9865 > 0.8735, so the "no demonstrated advantage" branch applies. The external set uses the same generator and the same oracle and was not sealed or blind (§6.7), so this tests parser/detector generalisation only. |
| RQ5 | **H5:** a documented LLM prompt flags behaviour-preserving variants at a higher rate than RELIC | LLM FPR ≤ RELIC FPR across ≥ 2 models with all pairs attempted | **[PENDING EXPERIMENT]** No LLM was run on SemBench; the earlier LLM data are selection-biased and invalid for this purpose (§6.4). |

**Kill condition (Agent 5):** if H1 and H2 are both refuted, the primary contribution is not supported and the work should be reported only as a negative-results/validity case study. H1 is refuted on SemBench; H2 is untested. The kill condition is therefore **unresolved**, and this paper is deliberately framed so that the supported content (S1, S2, S3, C4, C5) stands without H2.

---

## 4. Benchmark Design

### 4.1 Predecessor benchmark: mutation of three public corpora

*Source: `results/final/metrics.json` (accounting, subjects, labels); `results/v2/v2_metrics.json` (benchmark_adequacy).*

* **Subjects** (all demonstration/teaching code): AWS CardDemo (Apache-2.0; 55 job files), IBM CICS GenApp (EPL-2.0; 29 files; commit `f6f3f4b2…`), Open Mainframe Project COBOL course (CC-BY-4.0 / Apache-2.0; 37 files). After scope filtering, 66 files contribute evaluable mutants (31 CardDemo, 10 GenApp, 25 OMP).
* **Operators**: ten defined; nine yield evaluable mutants (`REMOVE_IF_GUARD`: 23 candidates, 0 evaluable, because IF/THEN/ELSE is outside the parser's scope).
* **Accounting**: 656 candidates → 566 EVALUABLE (86.3 %), 64 OUT_OF_SCOPE (41 no consumer inside the file; 23 IF/THEN/ELSE), 26 INVALID_MUTATION (23 split inside IF/THEN/ELSE, all in OMP; 3 renamed DSN too long), 0 infrastructure failures. By subject: CardDemo 315/356 evaluable, GenApp 216/216, OMP 35/84 (41.7 %).
* **Labels**: 460 DIFFERENT (positive), 106 EQUIVALENT (negative).

| Operator | Evaluable | Positives | Negatives |
|---|---:|---:|---:|
| SWAP_ADJACENT_STEPS | 166 | 166 | 0 |
| SPLIT_JOB | 166 | 166 | 0 |
| ALTER_COND_THRESHOLD | 35 | 34 | 1 |
| REMOVE_COND | 35 | 34 | 1 |
| DELETE_PRODUCER_STEP | 33 | 33 | 0 |
| MOVE_CONSUMER_BEFORE_PRODUCER | 14 | 14 | 0 |
| RENAME_OUTPUT_DATASET | 13 | 13 | 0 |
| INSERT_COMMENT | 65 | 0 | 65 |
| CHANGE_MSGCLASS | 39 | 0 | 39 |

(Source: `results/v2/v2_metrics.json` → `benchmark_adequacy.positives_by_operator`, `.negatives_by_operator`; evaluable counts: `results/final/metrics.json` → `accounting.pooled.by_operator`.)

**Design properties that matter for the paper's argument:** 104 of 106 negatives are comment or MSGCLASS edits; the other two are COND edits in one file whose guarded step cannot be bypassed in any modelled scenario; 332 of 460 positives (72.2 %) come from two reordering operators that are *always* labelled DIFFERENT; there is no negative that is a non-cosmetic behaviour-preserving restructuring. 38 positives are labelled DIFFERENT only under injected abends (`results/final/metrics.json` → `labels.pooled.positives_only_failure_observable` = 38).

### 4.2 JCL-SemBench

*Sources: `benchmarks/sembench/cases.jsonl` (sha256 `fc8e64ba…b162d`, recorded in `results/sembench/metrics.json` → `provenance`), `benchmarks/sembench/oracle_validation.json`, per-pair files `benchmarks/sembench/cases/<id>/{original,transformed}.jcl`, `reports/v2/SEMBENCH_DESIGN.md` (Agent 1). Labels author-only.*

* **Size and composition.** 180 pairs: 87 PRESERVING, 93 CHANGING, 12 categories, 16 base programs (`oracle_validation.json`: `total_pairs`, `preserving_count`, `changing_count`; `metrics.json` `populations.ALL`). 173 pairs come from 12 handwritten base jobs; 7 are derived from public corpus jobs (CardDemo `CBPAUP0J` ×2 and `DBPAUTP0` ×1, OMP `CBL0001J` ×2, GenApp `adef121` ×2; `cases.jsonl` `source`). Each pair carries a written equivalence or divergence argument (`equivalence_argument`) and a reference to the IBM JCL reference semantics (`relevant_jcl_semantics`), which we have not independently checked.
* **Categories** (`oracle_validation.json` → `category_counts`): *preserving* — `comment_edit` 17, `whitespace_and_continuation` 17, `syntax_representation` 21, `job_card_refactor` 12, `independent_statement_reorder` 14, `unreferenced_step_rename` 6; *changing* — `step_reorder_dependent` 14, `dataset_dependency_change` 17, `disp_change` 19, `cond_logic_change` 18, `producer_consumer_change` 12, `return_code_effect` 13. The "balance" in the design report is a balance of category counts (6 + 6), not a design guarantee of independence between categories.
* **Oracle comparison** (`oracle_validation.json` → `validation_status_counts`): 151 `VALIDATED_BY_ORACLE_AND_ARGUMENT`, 28 `ORACLE_DISAGREES`, 1 `ORACLE_ABSTAINS`, 0 `ARGUMENT_ONLY`. Of the 28 disagreements, 25 are CHANGING pairs the oracle calls EQUIVALENT and 3 are PRESERVING pairs it calls DIFFERENT; the abstaining pair (`sembench_172`, `return_code_effect`) is UNDETERMINED (`cases.jsonl` `oracle_verdict.label`). By category (from `cases.jsonl` `validation_status`): `disp_change` 11/19, `dataset_dependency_change` 6/17, `producer_consumer_change` 6/12, `return_code_effect` 2/13 (+1 abstain), `unreferenced_step_rename` 2/6, `syntax_representation` 1/21; zero for the other six categories. Disagreeing cases keep the author's label (they are not relabelled), so the author's reading, not the oracle, is ground truth for these 28.
* **Discrepancy with the design report (resolved).** The first version of `reports/v2/SEMBENCH_DESIGN.md` §3 and §5.1 tabulated the 28 disagreements differently (e.g. 6 `unreferenced_step_rename`, 9 `disp_change`, 0 `return_code_effect`, 7 PRESERVING disagreements); the machine-readable files give 2, 11, 2 and 3. In the final sprint the report's §5.1 table was regenerated from `cases.jsonl` and now agrees with it (totals unchanged; the frozen benchmark files were not edited). We use the machine-readable files throughout. The report also describes the comparison as a "systematic audit" and the oracle as an "independence" safeguard; no independent audit of SemBench labels exists (the oracle audit in §6.8 concerns the old-benchmark oracle, not SemBench labels), and we do not adopt that wording.
* **Construction defect: no-op pairs.** Comparing the actual files, **25 of 180 pairs have byte-identical `original.jcl` and `transformed.jcl`** *(derived by the draft's author from `benchmarks/sembench/cases/*/`; the `original_sha256`/`transformed_sha256` fields in `cases.jsonl` agree)*. 15 of them are labelled CHANGING (`dataset_dependency_change` 6, `producer_consumer_change` 6, `disp_change` 2, `return_code_effect` 1), all 15 are `ORACLE_DISAGREES` with oracle verdict EQUIVALENT, and their `equivalence_argument` text asserts a difference that the pair of files does not contain (e.g. `sembench_100`: "In single-job simulation without initial catalog distinction between stage files, the oracle reports EQUIVALENT, but z/OS catalog resolution alters input dataflow"). Ten are labelled PRESERVING (`unreferenced_step_rename` 4, `independent_statement_reorder` 3, `syntax_representation`, `job_card_refactor`, `whitespace_and_continuation` 1 each) and are trivially preserving. No detector that reads only the two files can flag the 15 CHANGING no-op pairs; they depress every detector's recall by construction and the label is not recoverable from the pair. We have not altered the benchmark; we report results on the full set and, as a sensitivity analysis, on the 155 pairs whose files differ (§6.5).
* **Provenance and integrity.** `MANIFEST.sha256` has 360 entries and all were verified before scoring (`results/sembench/metrics.json` → `provenance.manifest_entries_verified` = 360; `manifest_sha256` `e73db790…`). The README is consistent with the JSON (180/87/93).

### 4.3 Oracle

`jcl_oracle` simulates original and transformed jobs under a baseline scenario, injected return codes per step, and per-step abends; it compares executed steps, return codes, the data version each read observes, the final catalogue and job termination. Programs it cannot model (DB2, IMS, CICS, TSO) are opaque; a case whose only possible difference involves an opaque step is `UNDETERMINED` and not scored. Properties: imports nothing from RELIC (import-checked, enforced by tests) and never receives the operator name. Limits: written by the same team as RELIC and the mutator; shares a lexer with the mutator and subjects; one author; no comparison with z/OS; no independent reviewer (D-013); it keys steps by name (hence `unreferenced_step_rename` disagreements) and treats `DISP=SHR`/`OLD` as non-mutating within a single job (hence 11 `disp_change` disagreements). "Behaviour-preserving" in this paper means *equivalent modulo the oracle's observables and scenario set* (cf. equivalence modulo inputs [`le2014emi`]), not equivalent on a mainframe. **"Independent" means code-independent only** (the weakest layer of the independence ladder in `RESPONSIBLESE_POSITIONING.md` §2).

---

## 5. Methodology

### 5.1 Detectors

| Detector | Description | Notes |
|---|---|---|
| RELIC v1.0 | Legacy-mode code path in current tree | **Not** a checkout of the release commit (D-018). |
| RELIC v1.1 | v1.0 plus post-hoc fixes (continuation rule, COND semantics, parameter-aware diff) | Fixes chosen after inspecting the benchmark files. |
| RELIC V2 | v1.1 + D-001 same-name step identity, D-002 DD parsing, D-003 producer-before-consumer order, D-004 `DISP=(MOD,DELETE)` idiom | Fixes chosen by inspecting the old-benchmark files: development result. Frozen at commit `f435029…` for the SemBench and external runs (`results/sembench/run_info.json`; `results/external/run_info.json` → `relic_commit_at_freeze` = `relic_commit_at_run`, `frozen_code_unchanged_since_freeze` = true). |
| `raw_text` | Flags any byte difference | Degenerate reference. |
| `textdiff` | Flags any non-comment change | |
| `textdiff_ignore_job_parameters` | Drops `//*` comment lines; reduces each JOB statement to `//NAME JOB` | **Constructed post hoc on the old benchmark**; has real semantic loss (JOB-card COND/TYPRUN/REGION/RESTART can matter). |
| `normalized_text_A`, `normalized_text_B` | Frozen normalisation rules in `relic_eval/text_baselines.py` (collapse blanks, drop blank lines, ignore JOB parameters; B additionally sorts keyword operands) | Rules frozen (sha256 `1ff51f34…`) **before any SemBench case was loaded** (`results/sembench/BASELINE_FREEZE.json`). No JCL semantics. |
| Structural A / complexity B / `static_bcg_E` | Old-benchmark baselines | `static_bcg_E` duplicates v1.0 (D-024). |
| LLM C / LLM D | `openai/gpt-oss-20b` via `nvidia`, prompt `source_diff_v4`, one sample, T = 0 | Old benchmark only; partial coverage (§6.4). |

### 5.2 Metrics and uncertainty

Positive class = behaviour-changing ("flagged"). Primary metric on SemBench: MCC (Agent 5). Also precision, recall, specificity, F1 and accuracy. 95 % percentile intervals from a cluster bootstrap: old benchmark clustered by file (66 clusters), SemBench clustered by `base_id` (16 clusters), external by file (71 clusters); 10 000 replicates, seed 20261004 (`results/sembench/metrics.json` → `populations.*.bootstrap`; `results/external/metrics.json`). Paired differences use identical resamples. SemBench paired tests (`results/sembench/paired_tests.json`): exact McNemar on discordant pairs, Holm–Bonferroni over a family of 14 comparisons, and ΔMCC cluster-bootstrap CI. **Decision rule (Agent 4, `metrics.json` → `headline.rule`):** RELIC detector *a* is called distinguishable from trivial rule *b* only if the Holm-adjusted p < 0.05 **and** the ΔMCC CI excludes 0 in the same direction. Intervals describe sampling variation over *these* files and base programs only; with 16 base programs the SemBench intervals are wide and may be optimistic, and none accounts for selection of fixes on the development files.

### 5.3 Methodology for separating textual from behavioural change

1. **Normalised-text ceiling.** Build the best rule that uses no JCL semantics and score it as a detector. If it matches the benchmark label, the benchmark cannot test behavioural reasoning.
2. **Label–predicate agreement.** Report the fraction of items on which the benchmark label equals the text predicate (old benchmark 564/566; external mutation set 821/824, *derived* from `results/external/metrics.json` TP 691 + TN 130).
3. **Paired comparison against the ceiling** with a cluster bootstrap and an exact paired test, reporting the *direction* of the difference.
4. **Class-composition disclosure.** Report negatives and positives by operator or category in the main text.
5. **Confound-breaking classes.** Include items where text change and behaviour change dissociate: behaviour-preserving non-cosmetic edits (SemBench: `syntax_representation`, `independent_statement_reorder`, `whitespace_and_continuation`, `job_card_refactor`, `unreferenced_step_rename`) and behaviour-changing edits that survive naive normalisation. One structural limit: for pairs that consist only of JCL text, a behaviour change *requires* a text change, so a text rule can attain recall 1.0 on any pair whose files differ. The dissociation that a benchmark can create is therefore on the **preserving** side. This is observed in §6.5.

### 5.4 Oracle-dependence and leakage assessment

(a) Code-independence by import checks and tests (done). (b) Shared-component inventory: lexer shared with mutator; shared reference document; same team (documented, D-013). (c) Development-time inspection of the corpora (documented; none of the three old corpora is blind; external repositories screened by aggregate counts). (d) Agreement between the author's label and the oracle verdict on SemBench (done, §4.2). (e) Observation that RELIC's output coincides with the oracle's (§6.5). (f) Audit findings and tokenizer-agreement cross-check (done, `ORACLE_INDEPENDENCE_AUDIT.md`, §6.8); tokenizer ablation with re-labelling, second semantic model and blinded human review **[PENDING EXPERIMENT]** (the 60-case review package exists; no responses). (g) LLM contamination: all corpora are public; training-data overlap not assessed [`sallou2024breaking`, `kapoor2023leakage`].

### 5.5 Protocol status

No pre-registration. No frozen detector on the old benchmark. For SemBench and the external run the detector and (for SemBench) the text baselines were frozen and hashed before the run. SemBench cases were authored in the same sprint and by a team that knows RELIC; we cannot show that RELIC's behaviour did not influence case design. V2 replays the committed old benchmark and aborts unless each regenerated mutant matches its committed SHA-256 (0 mismatches) (`reports/v2/EVALUATION_SUMMARY.md` §1).

---

## 6. Results

### 6.1 Old benchmark: detector performance (pooled, n = 566; 460 positive, 106 negative)

Source: `results/v2/v2_metrics.json` → `populations.pooled.detectors`; 95 % file-level bootstrap CIs from `…bootstrap.f1_ci95`. *Development set.*

| Detector | TP | FP | FN | TN | Precision | Recall | Specificity | F1 | F1 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| RELIC v1.0 (legacy mode) | 380 | 0 | 80 | 106 | 1.0000 | 0.8261 | 1.0000 | 0.9048 | [0.8365, 0.9524] |
| RELIC v1.1 | 417 | 0 | 43 | 106 | 1.0000 | 0.9065 | 1.0000 | 0.9510 | [0.8937, 0.9884] |
| RELIC V2 | 442 | 0 | 18 | 106 | 1.0000 | 0.9609 | 1.0000 | 0.9800 | [0.9608, 0.9936] |
| V2 without D-001 | 419 | 0 | 41 | 106 | 1.0000 | 0.9109 | 1.0000 | 0.9534 | [0.8964, 0.9894] |
| V2 without D-002 | 441 | 0 | 19 | 106 | 1.0000 | 0.9587 | 1.0000 | 0.9789 | [0.9597, 0.9929] |
| V2 without D-003 | 442 | 0 | 18 | 106 | 1.0000 | 0.9609 | 1.0000 | 0.9800 | [0.9608, 0.9936] |
| V2 without D-004 | 444 | 0 | 16 | 106 | 1.0000 | 0.9652 | 1.0000 | 0.9823 | [0.9632, 0.9956] |
| Structural A | 368 | 0 | 92 | 106 | 1.0000 | 0.8000 | 1.0000 | 0.8889 | [0.8135, 0.9454] |
| Complexity B | 162 | 33 | 298 | 73 | 0.8308 | 0.3522 | 0.6887 | 0.4947 | [0.2068, 0.6912] |
| `static_bcg_E` | 380 | 0 | 80 | 106 | 1.0000 | 0.8261 | 1.0000 | 0.9048 | [0.8365, 0.9524] |
| Text change (any non-comment) | 460 | 41 | 0 | 65 | 0.9182 | 1.0000 | 0.6132 | 0.9573 | [0.9397, 0.9691] |
| **Diagnostic: text diff ignoring JOB parameters** | 460 | 2 | 0 | 104 | 0.9957 | 1.0000 | 0.9811 | **0.9978** | [0.9920, 1.0000] |

Per subject F1 (v1.0 / v1.1 / V2 / diagnostic): CardDemo 0.9191 / 0.9820 / 0.9901 / 0.9961; GenApp 0.8832 / 0.9050 / 0.9657 / 1.0000; OMP course 0.9474 / 1.0000 / 1.0000 / 1.0000 (`populations.<subject>.detectors`). Plain text-change F1 on GenApp is 0.9751, above V2's 0.9657.

**Reading.** All RELIC versions have zero false positives on all three subjects; the gain from v1.1 to V2 is recall only. Every F1 is a development figure and probably optimistic.

### 6.2 The trivial rule and false assurance (C2, C4)

* The diagnostic's two false positives are both COND edits in one CardDemo file (`TXT2PDF1.JCL`; `ALTER_COND_THRESHOLD/0` and `REMOVE_COND/0`), both labelled EQUIVALENT by the oracle; RELIC v1.1 and V2 do not flag them *(report: `reports/v2/AGENT_1_METRICS_AUDIT.md` §4)*. The FP count (2) is in the JSON; the file attribution is from the audit.
* Label–predicate agreement: (460 + 104)/566 = 564/566 *(derived from the diagnostic's confusion matrix)*.
* **Frozen normalised-text rules reproduce the diagnostic.** `normalized_text_A` and `normalized_text_B` (frozen before SemBench) score TP 460, FP 2, FN 0, TN 104, F1 0.9978, MCC 0.9884 (95 % CI [0.9623, 1.0]) on the old benchmark (`results/sembench/metrics.json` → `old_benchmark_context`; `results/sembench/old_benchmark_ablation.json`). The post-hoc origin of the diagnostic is therefore not what drives the result.
* **Paired differences on the old benchmark** (95 % file-cluster bootstrap, 66 clusters, 10 000 reps, seed 20261004):

| Comparison | Statistic | Source |
|---|---|---|
| V2 − diagnostic, F1 | **[−0.0373, −0.0032]** | *(derived)* calling `relic_eval.metrics.cluster_bootstrap` on `results/v2/v2_predictions.jsonl` (same function and seed as stored values; reproduces the stored V2 − v1.1 interval exactly). Also *(report)* `AGENT_1_METRICS_AUDIT.md` §7. Not stored in any committed JSON. |
| v1.1 − diagnostic, F1 | [−0.1040, −0.0090] | same recomputation |
| V2 − normalised text (A and B), MCC | −0.0821 [−0.1536, −0.0153]; discordant 2 (V2 right, text wrong) vs 18 (text right, V2 wrong); Holm p = 0.002412; verdict B_BETTER | `results/sembench/metrics.json` → `headline.relic_v2_vs_trivial.old_benchmark` |
| V2 − plain text change, MCC | +0.156 [0.0808, 0.2244]; discordant 41 vs 18; Holm p = 0.011382; verdict A_BETTER (RELIC better) | same |
| V2 − text change, F1 | [0.0039, 0.0432] | `results/v2/v2_metrics.json` `populations.pooled.bootstrap.diff_ci95` |
| v1.0 − text change (pooled), F1 | [−0.1183, −0.0048] | `results/final/metrics.json` `results.pooled.bootstrap.diff_ci95` |
| v1.1 − text change (pooled), F1 | [−0.0619, 0.0345] | same |
| V2 − text change, GenApp only, F1 | [−0.0574, 0.0199] | `results/v2/v2_metrics.json` `populations.genapp.bootstrap.diff_ci95` |

**Interpretation.** On this benchmark RELIC V2 beats a *naive* text diff on cosmetic edits (the only reason is that the naive diff flags 41 comment/MSGCLASS mutants), but not a text rule that normalises exactly the cosmetic classes the benchmark contains. The benchmark therefore measures whether a detector ignores cosmetic edits, not whether it reasons about behaviour. A RELIC-only report ("F1 0.98, zero false positives") would have conveyed an assurance about behavioural reasoning that the benchmark cannot support.

### 6.3 V2 development gain and ablations

* V2 − v1.1 paired F1: [0.0034, 0.0688]; V2 − v1.0: [0.0379, 0.1273]; V2 − V2 w/o D-001: [0.0035, 0.0654]; V2 − V2 w/o D-004: [−0.0060, 0.0]; V2 − V2 w/o D-003: [0.0, 0.0] (`populations.pooled.bootstrap.diff_ci95`).
* Flips v2 vs v1.1: 27 gained true positives, 0 gained false positives, 2 lost true positives (`flips_v2_vs_v1_1`).
* **The gain is a duplicate-step-name effect.** Recall on files with duplicate step names (6 files, 64 positives): v1.1 0.3906 → V2 0.7656; on files without (37 files, 396 positives): 0.9899 → 0.9924 (`recall_by_duplicate_step_names`). D-003 changes no mutant decision. **D-004 slightly lowers F1** (0.9823 without it vs 0.9800 with it); it is kept on semantic grounds.
* Per-subject V2 − v1.1 intervals: CardDemo [−0.0063, 0.0309] (includes 0); GenApp [0.0070, 0.1929]; OMP [0.0, 0.0]. The pooled gain is carried by GenApp's 10 files.
* The 18 remaining V2 false negatives: 13 swaps of identically-named steps in GenApp (D-005), 1 CardDemo swap of in-stream blocks, 2 D-004 trade-off renames, 2 PROC-internal overrides (D-006) *(report: `DEFECT_REGISTER.md` D-005)*. All 18 are caught by the diagnostic.
* Contract recovery against oracle facts (`contract_recovery`): TEMPORAL and CONTROL_FLOW on CardDemo exact (P = R = 1.0; 79 and 55 facts). RESOURCE on CardDemo, v1.1 → V2: 9 TP / 9 FP / 13 FN → 11 / 0 / 11. RESOURCE on OMP course: 0 TP / 23 FN in all versions. RESOURCE truth includes program/utility I/O invisible to JCL parsing (D-007), so these are not extraction-accuracy figures for JCL-visible facts.

### 6.4 Language-model baselines (not interpretable)

Source: `results/v2/v2_metrics.json` → `llm_selection_analysis`; `results/final/metrics.json` → `llm.status`.

* One model (`openai/gpt-oss-20b`, provider `nvidia`), one prompt (`source_diff_v4`), one sample per mutant. All 566 mutants were attempted; 148 (LLM C) and 103 (LLM D) returned `INVALID_OUTPUT`. 183 mutants lack a valid output from at least one baseline; they are 89.62 % positive vs 77.28 % for the 383 scored on both. (Earlier prose describing a "quota-limited random subsample" and a Groq `gpt-oss-120b` model is **wrong** and is withdrawn.)
* On the selection-biased 383-mutant common subset: LLM C F1 0.9846, LLM D 0.9671, v1.0 0.9077, v1.1 0.9577, V2 0.9793, text change 0.9442.
* Bounds over all 566: LLM C 0.8083 (invalid = not flagged) to 0.9717 (invalid = flagged); LLM D 0.8468 to 0.9536.
* **Conclusion: no comparison can be drawn.** No LLM was run on SemBench or on the external set. **[PENDING EXPERIMENT: credentialed full-coverage multi-model re-run with a retry policy, contamination caveats and provider-term checks]**.

### 6.5 JCL-SemBench results (labels author-only)

Source: `results/sembench/metrics.json` → `populations.<population>.modes.abstain_as_not_flagged.detectors` (all 8 detectors returned a prediction for all 180 cases: `status_counts_all_cases` = OK 180 each; `n_abstain` = 0). Mode `abstain_excluded` gives identical results because there are no abstentions. RELIC extracted no contracts from the original job in two cases for each RELIC version (`relic_no_contracts_extracted_in_original` = 2). Provenance: `run_info.json` git commit `f4350292…`.

**ALL (n = 180; 93 changing, 87 preserving; 16 base-program clusters).** Positive = flagged as behaviour-changing.

| Detector | TP | FP | FN | TN | Recall | Specificity | MCC | MCC 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `raw_text` | 78 | 77 | 15 | 10 | 0.8387 | 0.1149 | −0.0670 | [−0.2114, 0.0752] |
| `textdiff` | 78 | 60 | 15 | 27 | 0.8387 | 0.3103 | 0.1761 | [0.0731, 0.2861] |
| `textdiff_ignore_job_parameters` | 78 | 49 | 15 | 38 | 0.8387 | 0.4368 | 0.3020 | [0.1995, 0.3917] |
| `normalized_text_A` | 78 | 35 | 15 | 52 | 0.8387 | 0.5977 | 0.4511 | [0.3532, 0.5408] |
| `normalized_text_B` | 78 | 28 | 15 | 59 | 0.8387 | 0.6782 | 0.5249 | [0.4201, 0.6290] |
| RELIC v1.0 | 15 | 2 | 78 | 85 | 0.1613 | 0.9770 | 0.2363 | [0.1513, 0.3162] |
| RELIC v1.1 | 23 | 2 | 70 | 85 | 0.2473 | 0.9770 | 0.3241 | (identical predictions to V2) |
| RELIC V2 | 23 | 2 | 70 | 85 | 0.2473 | 0.9770 | 0.3241 | [0.2480, 0.3816] |

**Validated subset (151 pairs `VALIDATED_BY_ORACLE_AND_ARGUMENT`; 67 changing, 84 preserving; 16 clusters).**

| Detector | TP | FP | FN | TN | Recall | Specificity | MCC | MCC 95 % CI |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `raw_text` | 67 | 74 | 0 | 10 | 1.0000 | 0.1190 | 0.2378 | [0.1494, 0.3203] |
| `textdiff` | 67 | 57 | 0 | 27 | 1.0000 | 0.3214 | 0.4167 | [0.3642, 0.4844] |
| `textdiff_ignore_job_parameters` | 67 | 46 | 0 | 38 | 1.0000 | 0.4524 | 0.5179 | [0.4667, 0.5804] |
| `normalized_text_A` | 67 | 32 | 0 | 52 | 1.0000 | 0.6190 | 0.6473 | [0.5918, 0.7143] |
| `normalized_text_B` | 67 | 25 | 0 | 59 | 1.0000 | 0.7024 | 0.7152 | [0.6438, 0.7904] |
| RELIC v1.0 | 15 | 0 | 52 | 84 | 0.2239 | 1.0000 | 0.3719 | [0.2680, 0.4469] |
| RELIC V2 (= v1.1) | 23 | 0 | 44 | 84 | 0.3433 | 1.0000 | 0.4746 | [0.3375, 0.5722] |

**`ORACLE_DISAGREES` subset (n = 28; 25 changing, 3 preserving; 13 clusters; author label vs oracle disagree).** RELIC (all versions): TP 0, FP 2, FN 25, TN 1, MCC −0.8006. All text rules: TP 10, FP 3, FN 15, TN 0, MCC −0.3721. Interpret with caution: ground truth in this subset is the author's reading, and 15 of the 25 changing pairs are the no-op pairs of §4.2 on which no file-based detector can succeed.

**Findings, stated plainly.**

1. **RELIC V2 is a high-precision, low-recall detector on SemBench**: specificity 0.977 (FPR 0.023) against FPR 0.32–0.89 for every text rule, but recall 0.2473 against 0.8387. Its two false positives are `unreferenced_step_rename` pairs (the same pairs where the oracle keys steps by name).
2. **On the pre-specified rule RELIC V2 is not shown to be better than any trivial rule on SemBench, and is worse than one.** ΔMCC = MCC(V2) − MCC(text), `results/sembench/paired_tests.json`, ALL (exact McNemar, Holm over 14): vs `normalized_text_B` −0.2008 [−0.2992, −0.1018], discordant 26 (V2 right) vs 55 (text right), Holm p = 0.020268 → **text better**; vs `normalized_text_A` −0.1270 [−0.2187, −0.0328], 33 vs 55, Holm p = 0.172361 → not distinguishable; vs `textdiff_ignore_job_parameters` +0.0221 [−0.0774, 0.1200], 47 vs 55, Holm p = 1.0 → not distinguishable; vs `textdiff` +0.1480 [0.0385, 0.2469], 58 vs 55, Holm p = 1.0 → not distinguishable; vs `raw_text` +0.3911 [0.2535, 0.5262], 75 vs 55, Holm p = 0.476265 → not distinguishable. On the validated subset all five comparisons are "not distinguishable" (e.g. vs B: −0.2406 [−0.3827, −0.1358], Holm p = 0.235944; vs `raw_text`: +0.2368 [0.0639, 0.3907], Holm p = 0.08796).
3. **The fixes in V2 do not matter on SemBench**: V2 and v1.1 have 0 discordant cases (`paired_tests.json` ALL: `a_right_b_wrong` = `a_wrong_b_right` = 0; ΔMCC 0.0, CI [0, 0]). V2 vs v1.0: 8 vs 0 discordant, ΔMCC +0.0878 [0.0145, 0.1674], Holm p = 0.07812 (not significant after correction).
4. **The text-vs-behaviour confound is broken on the preserving side only.** Text rules reach recall 0.8387 on ALL (1.0 on the validated subset), because for file-only pairs a behaviour change implies a text change; their specificity is poor (0.1149–0.6782). Per category (`per_category`, ALL; TP/FP/FN/TN for V2 | `normalized_text_B`):

| Category | n | V2 | normalized B |
|---|---:|---|---|
| comment_edit | 17 pres. | 0/0/0/17 | 0/0/0/17 |
| whitespace_and_continuation | 17 pres. | 0/0/0/17 | 0/2/0/15 |
| syntax_representation | 21 pres. | 0/0/0/21 | 0/13/0/8 |
| job_card_refactor | 12 pres. | 0/0/0/12 | 0/0/0/12 |
| independent_statement_reorder | 14 pres. | 0/0/0/14 | 0/11/0/3 |
| unreferenced_step_rename | 6 pres. | 0/2/0/4 | 0/2/0/4 |
| step_reorder_dependent | 14 chg. | 9/0/5/0 | 14/0/0/0 |
| dataset_dependency_change | 17 chg. | 1/0/16/0 | 11/0/6/0 |
| disp_change | 19 chg. | 1/0/18/0 | 17/0/2/0 |
| cond_logic_change | 18 chg. | 6/0/12/0 | 18/0/0/0 |
| producer_consumer_change | 12 chg. | 6/0/6/0 | 6/0/6/0 |
| return_code_effect | 13 chg. | 0/0/13/0 | 12/0/1/0 |

   RELIC is silent on every category it does not model (`disp_change`, `return_code_effect`, most of `dataset_dependency_change`) and its recall there is near 0; text rules flag nearly all of them *because the files differ*, not because they understand the difference. `normalized_text_A` flags 20/21 `syntax_representation` and 11/14 `independent_statement_reorder` preserving pairs, which is where behavioural reasoning would be needed and is the one place RELIC's silence is correct.
5. **Sensitivity: excluding the 25 no-op pairs** *(derived from `results/sembench/predictions.jsonl` and `benchmarks/sembench/cases/*/`; bootstrap CIs and uncorrected McNemar p-values are in `results/sembench/noop_sensitivity.json`, script `noop_sensitivity.py`; clustered by `base_id`, 16 clusters)*. On the 155 pairs with differing files (78 changing, 77 preserving): `normalized_text_B` TP 78 / FP 28 / FN 0 / TN 49, recall 1.0, specificity 0.6364, MCC 0.6843; `normalized_text_A` MCC 0.6136; `textdiff_ignore_job_parameters` 0.4726; `textdiff` 0.3533; RELIC V2 (= v1.1) TP 23 / FP 2 / FN 55 / TN 75, recall 0.2949, specificity 0.9740, MCC 0.3655; RELIC v1.0 MCC 0.2661; `raw_text` MCC undefined (flags everything). V2 − `normalized_text_B` ΔMCC = −0.43 to −0.23 (95% cluster-bootstrap CI; discordant 26 vs 55; uncorrected exact McNemar p = 0.0017). Also excluding the 13 non-identical `ORACLE_DISAGREES` pairs and the 1 `ORACLE_ABSTAINS` pair (n = 141): ΔMCC CI [−0.37, −0.12], uncorrected p = 0.029, V2 MCC 0.464 vs 0.694. The qualitative conclusion is unchanged.
6. **RELIC's verdict coincides with the oracle's** *(derived from `predictions.jsonl`: RELIC V2 flagged = oracle DIFFERENT)*: on the 179 cases with a determinate oracle verdict, they coincide on 134 (107 of the 151 validated cases and 27 of the 28 `ORACLE_DISAGREES` cases). On the disagreement cases RELIC sides with the oracle in 27 of 28. This is consistent with two explanations we cannot separate without independent review: (i) the author's label is wrong for those pairs (including the 15 no-ops); (ii) RELIC and the oracle share modelling assumptions (both were written by the same author, e.g. step identity by name, `DISP=SHR`/`OLD` treated alike). It is a reason not to read agreement with the oracle as validation.

**What SemBench shows and does not show.** It shows that a benchmark containing behaviour-preserving non-cosmetic edits separates trivial text rules from each other (e.g. A vs `textdiff_ignore_job_parameters`: 14 vs 0 discordant, Holm p = 0.001708) and exposes RELIC's high-precision / low-recall profile. It does not show that RELIC reasons about behaviour better than text, that SemBench labels are valid (author-only), or that either result transfers to production jobs.

### 6.6 Baselines and statistical analysis

* **Frozen before use.** Text-baseline rules and their documented limitations are in `results/sembench/BASELINE_FREEZE.json` and `reports/v2/NORMALIZED_TEXT_BASELINE.md`; the freeze hash is recorded in `metrics.json` → `provenance.text_baselines_sha256`.
* **Family of tests.** 14 paired comparisons per subset, Holm–Bonferroni; effect sizes (discordant odds ratio, Cohen's g) and exploratory splits by changing/preserving are in `paired_tests.json`. The old-benchmark comparisons (§6.2) were added as the `old_benchmark` entry of `metrics.json` → `headline`.
* **Baselines not run.** Agent 5 lists a step-multiset diff and a template-fingerprint classifier as required checks on whether SemBench itself is shortcut-prone (`RESPONSIBLESE_POSITIONING.md` §6; H1's second refutation criterion). Neither exists in `results/sembench/` **[PENDING EXPERIMENT]**. Template-based shortcuts therefore cannot be excluded: all pairs derive from 12 handwritten base jobs and a small set of generator templates (`benchmarks/sembench/build.py`).
* **Limits of the statistics.** Sixteen base-program clusters; the CI on ΔMCC is a percentile interval; the exact McNemar test treats pairs as independent within clusters (it ignores the clustering, so its p-values are optimistic); Holm correction is over 14 comparisons chosen by Agent 4 before running.
* **Agreement with `reports/v2/BASELINE_AND_STATISTICAL_ANALYSIS.md`.** At the time of the final check the report's headline numbers (180 cases, V2 MCC 0.324, Holm p 0.020 for V2 vs rule B) are consistent with `results/sembench/metrics.json` and `paired_tests.json`; all numbers here are nevertheless taken from the JSON files.

### 6.7 External corpus run

Source: `results/external/metrics.json`, `run_info.json`, `exclusions.json`, `SUBJECT_FREEZE.json`. The corresponding prose report `reports/v2/EXTERNAL_VALIDATION_RESULTS.md` (Agent 3) exists and its headline conclusion (trivial rule F1 0.9978 above V2 F1 0.9755; the V2 − rule bootstrap CI excludes 0) agrees with the JSON; all numbers below are read from the JSON.

* **Design.** RELIC (v1.0, v1.1, V2), `textdiff` and `textdiff_ignore_job_parameters` were run unchanged (`frozen_code_unchanged_since_freeze` = true; commit `f4350292…`; harness hash identical at freeze and run) on mutants generated by the *same* operators and labelled by the *same* oracle as the old benchmark, on public repositories not used in development. **Labels are not independent ground truth** (`metrics.json` → `caveats[0]`). Repositories are "screened by aggregate counts/fragments, never blind" (`caveats[1]`). The run tests whether the parser/detector generalise to unseen files, not whether the labels are right, and it does not use SemBench pairs.
* **Accounting** (`accounting._total`): 182 JCL files from the screened repositories, 76 frozen-eligible, 71 with at least one evaluable mutant; 1005 candidate mutants → 824 EVALUABLE (82.0 %), 163 OUT_OF_SCOPE, 17 INVALID_MUTATION, 1 OTHER (oracle undetermined), 0 infrastructure failures, 0 run exceptions or timeouts, 0 detector errors. A further repository (`cschneid-the-elder_mapa`, 216 files) is robustness-only. Three repositories contribute no evaluable file. `yetacp_mvs_sysgen` contributes 589 of 824 mutants (71.5 %) and 47 of 71 files; its upstream licence was unverified in the sprint's earlier audit (`RESPONSIBLESE_POSITIONING.md` §5), and Agent 5 advises not to use it as evidence until resolved, so the table also gives the pooled result excluding it.
* **Pooled result** (`populations.pooled_effectiveness`; n = 824; 691 positive, 133 negative; 71 file clusters; 95 % CIs on F1):

| Detector | TP | FP | FN | TN | Recall | Specificity | F1 | F1 95 % CI | MCC |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| RELIC v1.0 | 612 | 0 | 79 | 133 | 0.8857 | 1.0000 | 0.9394 | [0.9110, 0.9610] | 0.7454 |
| RELIC v1.1 | 643 | 0 | 48 | 133 | 0.9305 | 1.0000 | 0.9640 | [0.9431, 0.9806] | 0.8269 |
| RELIC V2 | 658 | 0 | 33 | 133 | 0.9522 | 1.0000 | 0.9755 | [0.9559, 0.9892] | 0.8735 |
| `textdiff` | 691 | 62 | 0 | 71 | 1.0000 | 0.5338 | 0.9571 | [0.9432, 0.9671] | 0.6999 |
| `textdiff_ignore_job_parameters` | 691 | 3 | 0 | 130 | 1.0000 | 0.9774 | 0.9978 | [0.9939, 1.0000] | 0.9865 |

  Paired F1 differences (`bootstrap.diff_ci95`): V2 − `textdiff` [0.0010, 0.0356]; V2 − `textdiff_ignore_job_parameters` **[−0.0422, −0.0081]** (the trivial rule is better); V2 − v1.1 [0.0038, 0.0209]; V2 − v1.0 [0.0232, 0.0526].
* **Excluding `yetacp_mvs_sysgen`** (`pooled_excluding_yetacp_mvs_sysgen`; n = 235; 197 positive, 38 negative; 24 clusters): RELIC V2 and v1.1 TP 193 / FP 0 / FN 4 / TN 38, F1 0.9897 [0.9709, 1.0], MCC 0.9415; `textdiff_ignore_job_parameters` TP 197 / FP 2 / FN 0 / TN 36, F1 0.9949, MCC 0.9684; V2 − trivial rule F1 [−0.0265, 0.0096] (includes 0).
* **Same confound again.** Negatives by operator (`per_operator_pooled`): `INSERT_COMMENT` 71, `CHANGE_MSGCLASS` 59, one each of `ALTER_COND_THRESHOLD`, `REMOVE_COND`, `SWAP_ADJACENT_STEPS` → 130 of 133 (97.7 %) negatives are cosmetic; label–text-predicate agreement 821/824 *(derived: TP 691 + TN 130)*. The external run replicates, with unseen files, the construct-validity problem of the old benchmark; it does **not** test behavioural reasoning.
* **Per repository** (`populations.per_repo`): V2 F1 is 1.0 on IBM `dbb` (n = 8, 2 files), `zopeneditor-sample` (54, 7 files), `brexx` (56, 3 files) and `zECS` (49, 5 files); 0.9899 on `mainframed_Enumeration` (62, 5); 0.9698 on `yetacp_mvs_sysgen` (589, 47); 0.4000 on `zowe-cli` (6 pairs, 2 files; V2 − trivial F1 CI [−1.0, −0.3333]). Cells with ≤ 8 mutants carry no weight. Leave-one-repo-out V2 F1 ranges 0.9735–0.9897 (`leave_one_repo_out`).
* **Outcome for H4:** see §3 (point-estimate MCC drop 0.033; no advantage over the trivial rule; inconclusive for generalisation, since external sample, labels and operators are not independent of development).
* **Unsupported-syntax prevalence** (`unsupported_syntax_prevalence`) is reported per repository (PROC, INCLUDE, IF/THEN/ELSE, GDG, symbolic parameters, multi-job); `IF_THEN_ELSE` appears in none of the effectiveness repositories' eligible files, and the 2 000-line / 40-step / ≥ 2-step eligibility rules exclude 106 of 182 files, so the evaluable files are biased towards simple jobs.

### 6.8 Oracle independence audit status

* **Audit report (Agent 2): `reports/v2/ORACLE_INDEPENDENCE_AUDIT.md`.** Its own headline is that the oracle is **code-independent only**: it is not independent of the mutation generator, the subject selection or the author. There is no comparison with z/OS and no independent review. Findings relevant to this paper (all *(report: audit)* unless a JSON is named):
  * **F-01 shared lexer.** Oracle, mutator, subject selection and PROC library share one lexer, so a lexer bug moves mutation sites and labels together; the only mutant-validity gate (`INVALID`) is computed by the same lexer. Measured mitigation: RELIC's own tokenizer agrees with the shared lexer on the EXEC-name sequence of 630/630 mutants and on the expected structural effect of 607/607 checked mutants (`reports/v2/review_package/experiments/mutant_crosscheck_results.json`; I re-read the tier counts in that file). At statement level the two lexers agree on 1436 of 1519 statements (anchored agreement 0.9454; `lexer_disagreement_results.json`); RELIC sees no statement the oracle lexer misses, and the 83 oracle-only statements are 81 `stepname.ddname` overrides and 2 `<PLACEHOLDER>` JOB cards (`feature_census_results.json` → `gap`). This measures **agreement of two tokenizers, not the change in labels under an independent tokenizer.**
  * **F-02 single author.** Oracle, mutator and parser fixes landed in one commit by one author.
  * **F-03 construction-determined positives.** 60 of 460 positives (13.0 %) follow from the DISP abstraction by construction.
  * **F-04 `SPLIT_JOB`.** 166 of 460 positives (36.1 %). The termination observable embeds job names and job count, so every split differs. With those removed, the same 166 stay DIFFERENT but only 72 differ at baseline, 21 need an injected return code and 73 need an abend (`split_job_sensitivity_results.json`, re-counted by me from the 166 `SPLIT_JOB` entries). No split is ever EQUIVALENT, so the operator never tests whether the oracle can say "equivalent".
  * **F-05 failure-injection-only positives.** 159 of 460 positives (34.6 %) differ only under injected failures (tiers T0 301, T1 78, T2 81; RELIC v1.0 recall T0 0.870, T1 0.577, T2 0.901, *report: audit*). The audit recommends reporting these strata separately; this paper has **not** recomputed headline metrics by stratum **[PENDING EXPERIMENT]**.
  * **F-06 negatives.** 104 of 106 negatives are cosmetic. The other two (TXT2PDF1 `COND` edits) depend on the unverified assumption U-01, "z/OS ignores `COND` on the first EXEC".
  * **F-08 opaque steps.** 120 of 423 steps (28.4 %) in 66 of 121 files are modelled by a fallback that coincides with RELIC's own DD-disposition model, so oracle/RELIC agreement on those steps is weak evidence.
* **Review package (`reports/v2/INDEPENDENT_REVIEW_PACKAGE.md`, `reports/v2/review_package/`).** A 60-case blind package (30 oracle-EQUIVALENT, 30 oracle-DIFFERENT; sampling frame 566 evaluable mutants, seed 20251120), with rubric, blind form, agreement script, an answer-key file marked do-not-share, and response/adjudication templates. Its own first line states: *"Status: PENDING. No independent review has been performed."* `responses_template.csv` is a template; the only agreement numbers produced so far come from a self-test on synthetic ratings and say nothing about the oracle. **Independent review: PENDING.** A review package is a request for review, not a review. **[PENDING EXPERIMENT: completed reviewer responses and `compute_agreement.py` on them]**
* Facts that stand: code-independent by import check; shared lexer, same team, no z/OS comparison (D-013); v2 replay left all old-benchmark labels unchanged (0 SHA-256 mismatches); on SemBench the author's labels and oracle verdicts disagree on 28 of 180 pairs (`oracle_validation.json`), 25 pairs are no-ops, and RELIC's verdict follows the oracle's on 27 of those 28 (§6.5).
* Independence layer achieved (`RESPONSIBLESE_POSITIONING.md` §2 ladder): **import isolation only**, plus a measured tokenizer-agreement cross-check. A tokenizer ablation that re-labels with an independent lexer, a second independently written semantic model and human review are **not** done.

---

## 7. Discussion

**Textual change is a strong but misleading proxy, and the first thing to measure.** On the old benchmark, behaviour change and non-cosmetic text change coincide for 564 of 566 mutants; on the external mutation run for 821 of 824. Any detector with a "was anything non-cosmetic edited?" feature looks excellent. This is a statement about the benchmark's construction, not about JCL in the field.

**What a de-confounded benchmark does to the ranking.** When behaviour-preserving non-cosmetic edits are present (SemBench), text rules lose specificity (0.1149–0.6782), but they keep the recall advantage that file-only pairs give them, and the best normalised rule still has the higher MCC than RELIC V2 by a margin whose CI excludes zero after Holm correction. RELIC's contribution on SemBench is conservatism: it almost never cries wolf (FPR 0.023) and misses most behaviour changes (recall 0.2473). Whether that trade-off is useful depends on the cost model of a migration team; we do not have one.

**Why RELIC's recall is low.** RELIC models steps, ordering, dataset producer/consumer relations and COND; it does not model `DISP` semantics (recall 1/19), return-code effects (0/13), or most dataset redirection (1/17). The categories it models (`step_reorder_dependent` 9/14, `cond_logic_change` 6/18, `producer_consumer_change` 6/12) are detected incompletely. The benchmark therefore identifies the contract classes missing from RELIC; it is a coverage map more than a ranking.

**What RELIC's numbers do and do not show.** On the old benchmark: no cosmetic mutant flagged, exact TEMPORAL and CONTROL_FLOW recovery on CardDemo, and recall that improves when step identity respects repeated names. On SemBench: no false positive among 84 validated preserving pairs. Not shown: behavioural reasoning beyond what the modelled categories imply; explanation quality (RELIC's naming of the violated contract is not evaluated); better performance than text.

**Why the false assurance arose.** Three design choices compound: cosmetic-only negatives; positives from always-DIFFERENT reorder operators; and a labelling scheme (oracle on mutants of the same files) that is largely a function of whether the program text changed. The external mutation run reproduces this because it reuses the generator. A benchmark cannot repair this by adding more files from the same generator.

**The oracle is a model; SemBench shows where that bites.** 28 of 180 pairs show author–oracle disagreement, at least partly because the oracle keys steps by name, treats `SHR`/`OLD` as equal, and (for the 15 no-op pairs) cannot see a difference that is not in the files. RELIC follows the oracle on 27 of those 28. Shared modelling is plausible but unproven; only independent review can separate "labels wrong" from "models share a blind spot".

**Negative and mixed findings, reported plainly.** (i) The trivial normalised rule beats RELIC V2 on the old benchmark (F1 and MCC), on SemBench (`normalized_text_B`, Holm p = 0.0203) and on the external mutation run (F1 CI [−0.0422, −0.0081]). (ii) V2's fixes yield no change on SemBench (0 discordant). (iii) D-004 lowers F1 on the old benchmark; D-003 has no effect. (iv) GenApp's plain text-change F1 exceeds V2's. (v) The LLM comparison failed on coverage. (vi) 25 SemBench pairs are no-ops; the oracle disagrees with the author label on 28; the design report's disagreement table is inconsistent with the machine-readable data. (vii) H1 is refuted; H2–H3 and H5 untested. (viii) The step-multiset and template-fingerprint baselines were not run.

**On the V2 gain.** It is real on the old benchmark and concentrated in six duplicate-step-name files; it was developed on these files. External run: V2 − v1.1 [0.0038, 0.0209] pooled, but 0 on all small repositories and 0.0 on the pooled set excluding `yetacp_mvs_sysgen`. We treat it as a defect-fix result, not evidence of generality.

---

## 8. Threats to Validity

**Construct validity.** Old benchmark: label ≈ text predicate (D-025, D-014). SemBench: labels author-only; "equivalent" means equivalent modulo the oracle; 15 CHANGING no-op pairs; 28 oracle disagreements; template shortcuts untested; for JCL-only pairs behaviour change implies text change, which gives text rules recall 1.0 on any pair with differing files. Mutants and SemBench pairs are synthetic and not linked to real migration defects [`just2014mutants`, `papadakis2018correlated`]; taxonomy sources could not be verified; guard strengthening is never exercised (D-010).
**Internal validity.** Fixes D-001…D-004 were chosen on the same files that score them. The old-benchmark diagnostic was built after inspecting the benchmark (mitigated by frozen A/B rules reproducing it). v1.0 is a legacy-mode code path, not the release checkout (D-018). SemBench authors knew RELIC; influence on case design cannot be excluded. 90 of 656 old candidates were excluded by RELIC's own scope, and 163 of 1005 external candidates (OUT_OF_SCOPE) plus 106 of 182 external files were ineligible, so unsupported constructs sit outside the headlines (D-022: exceptions would be scored "not flagged"; none occurred in the V2 predictions or the external run).
**Oracle validity.** Model-based simulation with opaque programs; shared lexer; same team; no z/OS comparison; 38 old-benchmark positives labelled DIFFERENT only under injected abends *(report: `AGENT_1_METRICS_AUDIT.md` §5.4)*; single-job scope (no JES contention); 18 external candidate mutants carry an UNDETERMINED oracle label (all in `yetacp_mvs_sysgen`; 17 were already OUT_OF_SCOPE, 1 is counted as OTHER; *report: `EXTERNAL_VALIDATION_RESULTS.md` §3*). Independent validation not claimed.
**External validity.** Public teaching/demo and tooling repositories; no production JCL; single-file analysis; PROC/INCLUDE/IF-THEN-ELSE largely unsupported (D-006); 0 of 121 old-corpus files contain more than one JOB while mutated SPLIT_JOB files do (D-020), and 166 of 460 old positives (36.1 %) are SPLIT_JOB, so a parser artefact may contribute (a parser artefact is not isolated; Agent 2's sensitivity run shows every split stays DIFFERENT with job names and count removed from the termination observable, but 72/21/73 differ at baseline / need an injected RC / need an abend, §6.8, F-04).
**Statistical validity.** Mutants within a file and SemBench pairs within a base program are not independent; 16 SemBench clusters; exact McNemar ignores clustering; seven external repositories contribute unevenly (one supplies 71.5 %); repository-level generalisation cannot be claimed; thresholds for H1–H5 were not registered before the first look; intervals exclude selection effects.
**Contamination.** All corpora are public; LLM training-data overlap not assessed.
**Reproducibility.** Old-benchmark replay is byte-identical except `run_info.json` timestamps; SemBench and external runs record commit, harness hash and platform; LLM numbers reproduce from cached records only. Prose that asserted "every number generated from metrics.json" is withdrawn; the only report found inconsistent with the machine-readable files is `SEMBENCH_DESIGN.md`'s disagreement tables (§4.2), and the JSON governs.
**Literature.** Search limited (§2); no systematic review; grey literature not searched.

---

## 9. Responsible Engineering Implications

Aligned with `research/v2/RESPONSIBLESE_POSITIONING.md` §2–§6.

* **Report the trivial-baseline score next to the tool's.** Report the normalised-text ceiling and the label–predicate agreement with any change-detector result; if they coincide with the tool's, the benchmark has not discriminated. A high score on a cosmetic-heavy benchmark is easily mistaken for behavioural assurance [`parasuraman2010complacency`].
* **Name the independence layer.** "Independent" must not be used without the layer achieved. Here: *import isolation only*; shared-lexer ablation, second semantic model and human review are pending. Every SemBench table carries "labels author-only".
* **Define "behaviour-preserving" honestly.** Equivalent modulo the oracle's observables and scenario set, not equivalent on z/OS.
* **Match the claim to the evidence tier.** Development results are not validation; screened repositories are not blind; the external mutation run tests generalisation of the parser, not label validity.
* **Report coverage and uncertainty.** Show accounting of exclusions, CIs, no-op pairs, undetermined verdicts, and both invalid-output policies for LLM baselines. RELIC "not flagged" is **not** "safe": on SemBench it misses 70 of 93 behaviour-changing pairs.
* **Triage aid, not a compliance control.** Recall 0.2473 on SemBench means RELIC output cannot replace review, testing or a mainframe run. A static contract check can also miss PROC-internal overrides, cross-file effects and swaps of identically named steps. Humans remain in the modernization decision.
* **Data and licensing.** All corpora are public; licences are partly unverified (`yetacp_mvs_sysgen` upstream licence unresolved; release audit R-6). Redistribute transformation scripts and hashes rather than third-party files where redistribution is unclear; record licence, commit and retrieval date per repository (`gebru2021datasheets`).
* **Third-party LLMs.** Sending repository text to a hosted model is a disclosure to a third party; record model, provider, version, date and prompt version; treat contamination as likely [`sallou2024breaking`, `kapoor2023leakage`]. The earlier model/provider inconsistency is the cautionary example (§6.4).
* **Human reviewers.** The pending review involves expert annotators: consent, blindness to detector output, compensation/acknowledgement and any institutional ethics requirement must be settled before use (`RESPONSIBLESE_POSITIONING.md` §5.5; the ACM code context is [`gotterbarn2017acm`], text not re-read).
* **Negative results.** Reported as results. Registered-report practice [`ernst2023registered`] recommended for the next iteration: freeze hypotheses and thresholds before first look.

---

## 10. Conclusion

On an oracle-labelled mutation benchmark of three public JCL corpora, a contract-based detector reaches pooled F1 0.9800 on development data while a text rule that ignores comments and JOB-card parameters reaches 0.9978, and the paired difference favours the rule; the benchmark label agrees with a non-cosmetic text edit on 564 of 566 mutants. A purpose-built benchmark (JCL-SemBench, 180 pairs, labels author-only) separates trivial text rules from one another and shows that RELIC V2 is a conservative detector (specificity 0.977, recall 0.2473, MCC 0.3241) that is not distinguishable from, and in one comparison worse than, normalised text rules on the pre-specified test; the hypothesis that it beats a normalised text diff by a margin is refuted. A frozen-detector run on seven further public repositories reproduces the old benchmark's ranking, with the same cosmetic-dominated negatives. The benchmark itself has defects we report (25 no-op pairs, 28 author–oracle disagreements, an inconsistent design report) and untested ones (template shortcuts). Whether the SemBench labels hold under independent review, whether the oracle's labels survive a tokenizer-ablation, a second semantic model and blind human review (the audit found it code-independent only), whether any detector beats a text rule once labels are validated, how LLMs behave under a fair protocol, and whether results transfer to production jobs are **[PENDING EXPERIMENT]**. The supported contribution is a protocol and a cautionary case: report the trivial baseline and the label–predicate agreement before reading a modernization checker's score as behavioural assurance. No superiority, independent validation, blind evaluation or production-compatibility claim is made.

---

## Appendix A. Claims register

Status: **supported** (evidence in repo supports the claim as worded), **narrowed** (a weaker form is supported), **pending** (evidence not available), **removed** (withdrawn or contradicted). *(derived)* = computed by the author of this draft from committed raw records, not stored in a committed JSON.

| ID | Claim | Evidence path | Status |
|---|---|---|---|
| A1 | Old benchmark: 656 candidates, 566 evaluable, 66 files, 460 pos / 106 neg | `results/final/metrics.json` `accounting.pooled`, `labels.pooled`; `results/v2/v2_metrics.json` `populations.pooled` | supported |
| A2 | RELIC v1.0 / v1.1 / V2 pooled F1 0.9048 / 0.9510 / 0.9800 | `results/v2/v2_metrics.json` `populations.pooled.detectors` | supported (development set only) |
| A3 | RELIC V2 has zero false positives on the old benchmark | same (FP = 0) | supported, but uninformative: 104/106 negatives cosmetic |
| A4 | Text diff ignoring JOB parameters reaches F1 0.9978 | same; frozen A/B reproduce it: `results/sembench/old_benchmark_ablation.json` | supported |
| A5 | Old-benchmark label ≈ text predicate (564/566) | derived from A4 confusion matrix | supported |
| A6 | V2 − diagnostic paired F1 CI [−0.0373, −0.0032] | recomputed from `results/v2/v2_predictions.jsonl`; `AGENT_1_METRICS_AUDIT.md` §7 | supported (derived; not in any JSON) |
| A7 | "RELIC's advantage is specificity over trivial change detection" | refuted by A4/A6 | **removed** |
| A8 | "RELIC outperforms text diff / LLM" | A4, A6, §6.4, A34 | **removed** (never claimed here) |
| A9 | V2 improves on v1.1 (old benchmark) | `populations.pooled.bootstrap.diff_ci95["relic_v2-relic_v1_1"]` = [0.0034, 0.0688]; CardDemo includes 0 | **narrowed**: development set; carried by duplicate-step-name files |
| A10 | D-004 is an improvement | `relic_v2_wo_D004` F1 0.9823 > V2 0.9800 | **removed** |
| A11 | Oracle is "independent" | D-013 | **narrowed** to "code-independent (import isolation only), same team, not validated against z/OS" |
| A12 | Oracle independently validated / independent review performed | no completed review; `reports/v2/INDEPENDENT_REVIEW_PACKAGE.md` states "Status: PENDING"; `reports/v2/review_package/responses_template.csv` is a template | **pending** (not claimed) |
| A13 | LLM baseline: "quota-limited random subsample, Groq gpt-oss-120b" | `results/final/metrics.json` `llm.status` | **removed** |
| A14 | LLM vs RELIC comparison | `v2_metrics.json` `llm_selection_analysis` | **narrowed** to "no conclusion possible" |
| A15 | Fair, full-coverage LLM re-run | none | **pending** |
| A16 | Ten operators evaluated | `benchmark_adequacy.operators_with_zero_evaluable_mutants` = [REMOVE_IF_GUARD] | **narrowed** to ten defined, nine evaluable |
| A17 | "v1.0.0 as released, blind" | D-018 | **narrowed** to "v1.0 legacy-mode configuration" |
| A18 | CardDemo/OMP/GenApp (or external repos) are blind or held out | `v2_metrics.json` `validation_status`; `results/external/metrics.json` `caveats[1]` | **removed** |
| A19 | JCL-SemBench is a semantically grounded benchmark (C1) | `benchmarks/sembench/cases.jsonl`, `oracle_validation.json`; labels author-only; 28 disagreements; 25 no-op pairs | **narrowed**: exists with written arguments; label validity unestablished |
| A20 | Methodology separates textual from behavioural change (C2) | §5.3; A4–A6; A32–A36 | **supported as protocol**; dissociation achieved on the preserving side only |
| A21 | Oracle dependence/leakage assessed (C3) | D-013; `oracle_validation.json`; `reports/v2/ORACLE_INDEPENDENCE_AUDIT.md` (F-01…F-08; "code-independent only"); `review_package/experiments/*_results.json` | **narrowed** (dependence characterised and partly quantified; no independent validation; no label-change measurement) |
| A22 | False assurance in automated evaluation (C4) | A4–A6; A34; §6.7 | **supported** on two benchmarks and one external replication; generality not shown |
| A23 | Explicit uncertainty/evidence reporting (C5) | accounting, CIs, Holm tests, LLM bounds, this register | supported |
| A24 | Generalisation to unseen JCL | `results/external/metrics.json` | **narrowed**: unseen files, same generator and oracle; V2 F1 0.9755 [0.9559, 0.9892]; trivial rule 0.9978; not independent ground truth |
| A25 | Production JCL compatibility | none | **removed** |
| A26 | Explanation correctness ("names the violated contract") | not measured | **pending** |
| A27 | RELIC cost/determinism advantage | not measured | **removed** |
| A28 | Novelty: first JCL behavioural-change benchmark / contract extraction | `FINAL_NOVELTY_ASSESSMENT.md` §2, §7.2 | **narrowed** to "no prior art found in the sources searched; search incomplete"; systematic search **pending** |
| A29 | Mutants / SemBench pairs represent real migration defects | taxonomy unverified (D-010) | **removed** |
| A30 | Every number generated from `metrics.json` | prose/records inconsistencies found | **removed** |
| A31 | RESOURCE recovery figures = extraction accuracy | D-007 | **narrowed** |
| A32 | SemBench: 180 pairs, 87 preserving / 93 changing, 12 categories, 16 base programs | `oracle_validation.json`; `results/sembench/metrics.json` `populations.ALL` | supported |
| A33 | SemBench oracle comparison: 151 validated / 28 disagree / 1 abstain; 0 reviewed | `oracle_validation.json`; `cases.jsonl` `independent_review_status` = PENDING for all 180 | supported |
| A34 | RELIC V2 does not outperform normalised text rules on SemBench; text B better (ΔMCC −0.2008 [−0.2992, −0.1018], Holm p 0.020268) | `results/sembench/paired_tests.json` ALL; `metrics.json` `headline` | supported (labels author-only) |
| A35 | RELIC V2 on SemBench: specificity 0.9770, recall 0.2473, MCC 0.3241 [0.2480, 0.3816] | `results/sembench/metrics.json` `populations.ALL…relic_v2` | supported (labels author-only) |
| A36 | V2 fixes give no SemBench gain over v1.1 (0 discordant) | `results/sembench/paired_tests.json` ALL | supported |
| A37 | H1 (ΔMCC > 0.10 vs normalised text) is refuted | A34; Agent 5 §6 criteria | supported as exploratory (thresholds not pre-registered) |
| A38 | 25 SemBench pairs have identical original/transformed files, 15 of them labelled CHANGING | `benchmarks/sembench/cases/*/` *(derived)*; `cases.jsonl` hashes | supported (benchmark defect, unfixed) |
| A39 | RELIC verdict equals oracle verdict in 27/28 `ORACLE_DISAGREES` cases | `results/sembench/predictions.jsonl` *(derived)* | supported as observation; causal reading **pending** review |
| A40 | SemBench is free of template shortcuts | step-multiset / template-fingerprint baselines not run | **pending** |
| A41 | Layered oracle-independence audit complete | `reports/v2/ORACLE_INDEPENDENCE_AUDIT.md` exists; tokenizer agreement measured (630/630 EXEC sequences; 1436/1519 statements) but no re-labelling ablation, no second semantic model, no human review | **narrowed** (audit report exists; layers beyond import isolation and tokenizer agreement pending) |
| A42 | `SEMBENCH_DESIGN.md` disagreement breakdown and "systematic audit" wording | contradicts `cases.jsonl` (§4.2) | **removed** (JSON used; design report subsequently corrected) |
| A43 | External run: V2 − trivial rule F1 CI [−0.0422, −0.0081]; negatives 130/133 cosmetic | `results/external/metrics.json` `populations.pooled_effectiveness`, `per_operator_pooled` | supported (labels from the non-independent oracle) |
| A44 | H4 (external MCC drop ≤ 0.10) | MCC 0.9063 *(derived)* → 0.8735 | **narrowed**: point estimate within threshold, no advantage over trivial rule, inconclusive |
| A45 | H2, H3, H5 | no review, no audit, no LLM run on SemBench | **pending** |

## Appendix B. What the benchmark measures / does not measure / what RELIC demonstrates / what remains unvalidated

| | Old mutation benchmark | JCL-SemBench (labels author-only) |
|---|---|---|
| **Measures** | Whether a detector flags 460 structural/COND/rename edits and stays silent on 104 comment/MSGCLASS edits (plus 2 COND edits whose guarded step cannot be bypassed in any modelled scenario), relative to a model-based JCL simulator. | Whether a detector flags 93 behaviour-changing pairs and stays silent on 87 behaviour-preserving ones across 12 JCL transformation categories, relative to the author's written arguments (151 pairs also agree with the oracle). |
| **Does not measure** | Reasoning about behavioural equivalence; tolerance of behaviour-preserving non-cosmetic edits (none present); explanation quality; real migration defects; PROC/INCLUDE/IF-THEN-ELSE; cross-file effects; production JCL. | Label validity (review pending); behaviour changes that are not visible in the two files (15 no-op pairs); real migration defects; PROC/INCLUDE; JES contention; dynamic allocation; production JCL; explanation quality; resistance to template shortcuts (untested). |
| **RELIC demonstrates** | (Development set) no false positive on cosmetic edits; exact TEMPORAL/CONTROL_FLOW recovery on CardDemo; recall 0.9609 after fixes chosen on those files; same-named-step identity was a material defect (recall 0.3906 → 0.7656 on affected files). | A conservative profile: specificity 0.977, recall 0.2473, no false positive on 84 validated preserving pairs; detects only the contract classes it models; not distinguishable from, and in one comparison worse than, normalised text rules. External mutation run (same generator and oracle): V2 F1 0.9755, no false positive in 133 negatives, trivial rule 0.9978. |
| **Remains unvalidated** | Superiority over any baseline (contradicted for normalised text); fair LLM comparison **[PENDING]**; oracle correctness vs z/OS and independent review **[PENDING]**; systematic novelty position **[PENDING]**. | Independent review of labels **[PENDING]**; layered oracle-independence audit **[PENDING]**; template-fingerprint and step-multiset baselines **[PENDING]**; LLM behaviour on SemBench **[PENDING]**; explanation correctness; production relevance; RELIC performance after the label defects are fixed and re-reviewed. |

## Appendix C. `[PENDING EXPERIMENT]` register

| ID | Item | Blocker / expected artefact |
|---|---|---|
| P1 | Independent review of the 60-case oracle package and of SemBench labels (H2) | no completed review; `reports/v2/review_package/responses_template.csv` is a blank template; the package itself says "Status: PENDING" |
| P2 | Tokenizer ablation that re-labels with an independent lexer; second independently written semantic model (H3); headline metrics stratified by T0/T1/T2, SPLIT_JOB and DISP-by-construction positives (audit recommendation) | not performed; only tokenizer *agreement* and a SPLIT_JOB observable sensitivity exist (`ORACLE_INDEPENDENCE_AUDIT.md`) |
| P3 | Reconciliation of `reports/v2/EXTERNAL_VALIDATION_RESULTS.md` with `results/external/metrics.json` line by line | headline numbers in §6.7 were read from the JSON; the report's prose conclusion (trivial rule F1 0.9978 beats V2 F1 0.9755) agrees; remaining prose tables not re-verified |
| P4 | Step-multiset and template-fingerprint baselines (H1 second criterion; shortcut test) | not run (`results/sembench/` has none) |
| P5 | Repair or removal of the 25 no-op SemBench pairs and re-run | `benchmarks/sembench/` owned by Agent 1; no fix made in this sprint |
| P6 | ~~Reconcile `SEMBENCH_DESIGN.md` disagreement tables with `cases.jsonl`~~ **Done** (final sprint, §5.1 regenerated from JSON) | — |
| P7 | Pre-registered thresholds for H1–H5 and a sealed external/held-out set | thresholds are proposed defaults; external set screened by aggregate |
| P8 | Fair full-coverage multi-model LLM run on SemBench and external data (H5) | needs credentials, licence and provider-term checks |
| P9 | Systematic literature search incl. grey literature and commercial JCL tooling | not performed |
| P10 | Explanation-correctness study | not performed |
| P11 | Real-defect / change-history mutants | not performed |
| P12 | Production-like JCL | not available |
| P13 | Resolution of `yetacp_mvs_sysgen` upstream licence | unresolved |
| P14 | Holm-corrected paired test for the no-op sensitivity analysis | CIs clustered by base_id exist (`noop_sensitivity.json`); the McNemar p-values there are uncorrected |

## Appendix D. Evidence index

| File | Used for |
|---|---|
| `results/v2/v2_metrics.json` | old-benchmark confusion matrices, bootstrap CIs, ablations, benchmark adequacy, recall by duplicate step names, flips, LLM selection analysis, contract recovery |
| `results/v2/v2_predictions.jsonl` | recomputation of V2/v1.1 − diagnostic paired CIs (derived) |
| `results/final/metrics.json` | accounting, labels, subjects, LLM status, pooled v1.0/v1.1/text-change paired CIs |
| `results/sembench/metrics.json` | SemBench confusion matrices, MCC CIs, per-category results, provenance, old-benchmark context for the frozen text rules, `headline` paired verdicts |
| `results/sembench/paired_tests.json` | exact McNemar + Holm p-values and ΔMCC CIs, V2 vs v1.1/v1.0 |
| `results/sembench/predictions.jsonl`, `benchmarks/sembench/cases/*/` | derived analyses: oracle agreement, no-op pairs, 155-pair sensitivity |
| `results/sembench/BASELINE_FREEZE.json`, `old_benchmark_ablation.json`, `run_info.json` | baseline freeze, old-benchmark reproduction, commit/platform |
| `benchmarks/sembench/cases.jsonl`, `oracle_validation.json`, `README.md`, `MANIFEST.sha256` | SemBench composition, oracle comparison, review status, manifest |
| `reports/v2/SEMBENCH_DESIGN.md` | design narrative (§5.1 table regenerated from `cases.jsonl` in the final sprint) |
| `results/external/metrics.json`, `run_info.json` | external accounting, pooled and per-repository results, caveats, freeze evidence |
| `reports/v2/DEFECT_REGISTER.md`, `EVALUATION_SUMMARY.md`, `AGENT_1_METRICS_AUDIT.md`, `INTEGRATION_REPORT.md`, `NORMALIZED_TEXT_BASELINE.md`, `BASELINE_AND_STATISTICAL_ANALYSIS.md` | defect descriptions, prose-only facts marked *(report)*; baseline rules |
| `research/v2/FINAL_NOVELTY_ASSESSMENT.md`, `RESPONSIBLESE_POSITIONING.md`, `final_verified_references.bib`, `LITERATURE_AND_NOVELTY_ASSESSMENT.md`, `literature_candidates.bib`, `paper/v2/references.bib` | related work, hypotheses, novelty boundary, responsible-engineering checklist |
| `reports/v2/ORACLE_INDEPENDENCE_AUDIT.md` (Agent 2) | audit findings F-01…F-08, tier counts, U-01; marked *(report: audit)* unless re-read from JSON |
| `reports/v2/review_package/experiments/{mutant_crosscheck,lexer_disagreement,feature_census,split_job_sensitivity}_results.json` | tokenizer agreement, `gap` census, SPLIT_JOB 72/21/73 re-count (the last by my own count of the JSON) |
| `reports/v2/INDEPENDENT_REVIEW_PACKAGE.md`, `reports/v2/review_package/` | status of the review package only (no review results) |
| `reports/v2/EXTERNAL_VALIDATION_RESULTS.md` (Agent 3) | prose cross-check of §6.7 (frozen subjects, 76 eligible of 182 files, caveats); numbers in the draft come from `results/external/*.json` |
