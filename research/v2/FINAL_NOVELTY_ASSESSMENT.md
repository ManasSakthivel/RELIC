# JCL-SemBench and the RELIC evaluation methodology — final novelty and contribution assessment (Agent 5)

Scope: focused primary-literature assessment for the final sprint. Companion files:
[`RESPONSIBLESE_POSITIONING.md`](RESPONSIBLESE_POSITIONING.md) and
[`final_verified_references.bib`](final_verified_references.bib). This file builds on, and does not repeat,
[`LITERATURE_AND_NOVELTY_ASSESSMENT.md`](LITERATURE_AND_NOVELTY_ASSESSMENT.md) (Agent 2; entries cited as "A2-R#").
No file outside these three was edited.

**Evidence status of RELIC used here (from the repository, not re-measured by me):**
RELIC V2 F1 0.980 (TP 442 / FP 0 / FN 18 / TN 106) is a development-set result; a normalised text diff that
ignores JOB-card parameters scores F1 0.998 (2 FP, 0 FN) because 104 of 106 negatives are comment/MSGCLASS edits and all
460 positives are non-cosmetic text edits ([`AGENT_1_METRICS_AUDIT.md`](../../reports/v2/AGENT_1_METRICS_AUDIT.md) §4);
oracle and mutator share a lexer, one author wrote oracle, mutator and detector
([`ORACLE_SPECIFICATION.md`](../../docs/evaluation/ORACLE_SPECIFICATION.md) §6); the LLM comparison is selection-biased
([`INTEGRATION_REPORT.md`](../../reports/v2/INTEGRATION_REPORT.md) Q&A G). JCL-SemBench is described to me only in the sprint
brief (matched behaviour-preserving / behaviour-changing pairs, documented semantics, oracle checks, PENDING independent review,
baselines, external-corpus run, oracle-independence audit). **No SemBench file exists in the repository at the time of writing
(glob `**/*SemBench*` returned nothing), so every statement about SemBench below is about the design as briefed, not about an artefact I inspected.**

---

## 1. Verification method and limits

* A reference is "verified" only if title, authors, year, venue and DOI/arXiv id were returned by Crossref, the arXiv API, or (for
  authors of one record) an OpenAlex DOI lookup during this session. Entries carried from Agent 2 were reused, not re-queried.
* **Metadata only.** I did not open any full text. I read the abstracts of: Yefet et al., EvalPlus, SWE-bench, SWE-Bench+,
  ReCode, Empirical Standards, Hasselbring, Jacobs & Wallach, Raji et al. (arXiv API). Every other characterisation of what a paper
  does comes from background knowledge and is marked "(bk)". Re-check against the full text before use in related work.
* Verified entries are in [`final_verified_references.bib`](final_verified_references.bib) (NEW vs CARRIED marked per entry).

### 1.1 Source availability this session

| Source | Result |
|---|---|
| Crossref `api.crossref.org/works?query.bibliographic=…` | Worked when run strictly one at a time (30 queries, no 429). One direct DOI lookup with `select=` returned HTTP 400; repeated without `select` (OK). |
| arXiv API | Worked (10 queries, some in parallel with other hosts, no failures). |
| OpenAlex API | First call 429 (issued in parallel with Semantic Scholar); later serial calls worked (3 calls). Secondary aggregator: used for one author list and for JCL prior-art recall only. Free daily budget is shared; not relied on. |
| **DBLP** search API | **Blocked again** (Anubis proof-of-work page, no JSON). Retried once as instructed. |
| **Semantic Scholar** Graph API | **HTTP 429** again. Retried once as instructed. |
| ScienceDirect landing page | HTTP 403 (not verified there). |
| `acm.org/code-of-ethics` | HTTP 403 (Code text itself not verified; only the CACM article about it, via Crossref). |
| ICSME 2025 registered-reports track URL on conf.researchr.org (a guessed URL) | HTTP 404. No CFP/track page was verified. |

### 1.2 Queries run this session (in order; all HTTP 200 unless noted)

Crossref `query.bibliographic` (one at a time): (1) `Compiler validation via equivalence modulo inputs Le Afshari Su`;
(2) `Metamorphic testing a review of challenges and opportunities Chen Kuo Liu Poon Towey Tse Zhou`;
(3) `The Oracle Problem in Software Testing A Survey Barr Harman McMinn Shahbaz Yoo`; (4) direct `works/10.1016/bs.adcom.2018.03.015` (400 with `select`, then 200; no author list in Crossref);
(5) `Using benchmarking to advance research … Sim Easterbrook Holt` (returned a 2021 duplicate-titled record by other authors; flagged in the bib);
(6) `Leakage and the reproducibility crisis … Kapoor Narayanan`; (7) `Registered reports in software engineering Ernst Baldassarre`;
(8) `Trivial Compiler Equivalence … Papadakis`; (9) `Are mutation scores correlated with real fault detection …`;
(10) `Mutations how close are they to real faults Gopinath Jensen Groce`; (11) `An experimental evaluation of the assumption of independence in multiversion programming Knight Leveson`;
(12) `Complacency and bias in human use of automation … Parasuraman Manzey`; (13) `Automation bias a systematic review … Goddard`;
(14) `The adverse effects of code duplication … Allamanis`; (15) `Datasheets for datasets Gebru …`; (16) `Adversarial examples for models of code Yefet Alon Yahav`;
(17) `Evaluation of Generalizability of Neural Program Analyzers under Semantic-Preserving Transformations Rabin Alipour` (matched the IST 2021 paper and Statfier, not the exact query title);
(18) `JCL job control language static analysis`; (19) `z/OS batch job dependency analysis JCL mainframe scheduling`; (20) `query.title=JCL` with `from-pub-date:1990` (rows 10);
(21) `COBOL to Java migration behavioral equivalence verification testing legacy`; (22) `Migrating from COBOL to Java Sneed 2010 …`;
(23) `Overcoming the equivalent mutant problem … Madeyski`; (24) `Hints on test data selection … DeMillo Lipton Sayward`;
(25) `The N-Version Approach to Fault-Tolerant Software Avizienis`; (26) `Validity threats in empirical software engineering research an initial survey Feldt Magazinius` (**target not found**);
(27) `Identifying categorizing and mitigating threats to validity … Ampatzoglou` (found; secondary-study focus, not used);
(28) `ACM Code of Ethics and Professional Conduct Gotterbarn Brinkman Flick`; (29) `A survey of code-based change impact analysis techniques Li Sun Leung Zhang`;
(30) `batch job stream change impact analysis mainframe legacy COBOL JCL dependencies`.

arXiv API: (a) `ti:"Adversarial Examples for Models of Code"`; (b) `ti:"Is Your Code Generated by ChatGPT Really Correct"`; (c) `ti:"SWE-bench"` (34 hits; 6 read);
(d) `ti:"Empirical Standards" AND abs:software`; (e) `ti:ReCode AND abs:robustness AND abs:code` (found ReCode); (f) `all:"job control language"` → **0**;
(g) `all:JCL AND all:z/OS` → **0**; (h) `all:mainframe AND all:batch AND (all:modernization OR all:migration)` → **0**; (i) `ti:"Measurement and Fairness" AND au:Jacobs`; (j) `ti:"everything in the whole wide world benchmark"`.

OpenAlex: (α) `works/doi:10.1016/bs.adcom.2018.03.015` (authors); (β) `search="job control language"` (full-text, 1,274 hits, top 15 read);
(γ) `filter=title_and_abstract.search:JCL, publication_year>1989` (1,225 hits, top 25 read).

DBLP (blocked) and Semantic Scholar (429): one retry each, both failed.

**Not queried this session** (no verification, see §8): Kitchenham (any), Hamlet 1977, McKeeman 1998, Chen et al. 1998 original report, Pesic/DECLARE, Sadiq, Hou et al. LLM4SE survey, Fluri/GumTree, CodeBERT-specific robustness papers beyond those listed.

---

## 2. Prior-art search for JCL (targeted)

| Topic | Queries | Result |
|---|---|---|
| JCL benchmark | (18)(20)(f)(g)(β)(γ) | **No prior art found in the sources searched.** |
| JCL semantic equivalence / behaviour-preservation | (18)(f)(g)(β) | **No prior art found in the sources searched.** |
| JCL static analysis | (18)(20)(β)(γ) | None found. Hits are encyclopaedia/reference entries, practitioner books (e.g. "MVS/ESA JCL" 1999, "zOS JCL" 2002), historical language-design papers (1970–1981, e.g. "The evolution of job control languages", 1972), a 1990 German book chapter "Prüfung von JCL-Standards" (title only; authors/content not retrieved, not read), and a 2014 dissertation "Eclipse IDE plug-in for JCL support" (title only, not read). None is a semantic-analysis or evaluation paper *by title*. |
| z/OS job dependency analysis | (19)(h)(30) | None found; Crossref returned unrelated scheduling-theory and SSRN/low-visibility items. |
| Batch-job change impact | (29)(30) | General code-based change-impact survey exists (Li et al. 2012, verified) but nothing for JCL/batch streams. Adjacent: Van Geet & Demeyer ICSM 2009 (feature location in COBOL mainframe systems; verified metadata, content bk). |

**Caveats that bound every "no prior art" statement.** (i) DBLP and Semantic Scholar were unavailable twice; (ii) title/abstract matching on a three-letter acronym is
noisy ("JCL" also names a journal and a linguistics field), so true hits may be buried in OpenAlex's 1,225; I read only the top 25; (iii) grey literature (IBM Z DevOps
products, schedulers such as Control-M, vendor impact-analysis tools, patents, theses in non-indexed repositories) was **not searched at all** and commercial JCL impact analysis tools very probably exist;
(iv) Google Scholar, ACM DL and IEEE Xplore search were not available to me.

---

## 3. Focused literature assessment (what the verified work says, and what it means for SemBench)

All content statements are (bk) unless marked (abs). Metadata verified.

**3.1 Mutation-benchmark validity.**
Just et al. (FSE 2014) and Papadakis et al. (ICSE 2018, "Are mutation scores correlated with real fault detection?") examine whether detecting mutants predicts detecting real faults;
Gopinath et al. (ISSRE 2014; ICST 2017 "Theory of composite faults") study how close mutants are to real faults and why the coupling effect (Offutt 1992) holds for simple faults (bk).
Papadakis et al. 2019 (Advances in Computers) is the survey. The equivalent-mutant problem: Madeyski et al. (TSE 2014) review it; Papadakis et al. (ICSE 2015) and Kintis et al. (TSE 2018) detect trivially equivalent mutants by compiler optimisation (bk).
*Implication:* every issue they raise—mutants as proxies for real defects, equivalent mutants poisoning labels—transfers to SemBench. SemBench's twist is that the equivalence side is
*deliberately constructed* (behaviour-preserving transformations) and labelled by an oracle rather than discovered by luck, which mirrors the "equivalent mutant" problem but only *relative to the oracle's model*. No evidence that mutants *of JCL* correlate with real production JCL defects exists in anything I found (and L6 in the repository says the taxonomy is unverified).

**3.2 Semantic-preserving transformation, metamorphic testing, EMI.**
Le, Afshari & Su (PLDI 2014) generate equivalence-modulo-inputs variants of programs to test compilers; Chen et al. (ACM CSUR 2018) survey metamorphic testing (bk).
Statfier (Zhang et al., ESEC/FSE 2023) applies semantic-preserving transformations to test *static analysers* (title verified; content bk) — the closest *methodological* neighbour to using semantics-preserving rewrites to test a static change detector.
Rabin et al. (IST 2021) test generalisation of neural program models under semantic-preserving transformations; Yefet et al. (OOPSLA 2020) show code models are vulnerable to semantics-preserving perturbations (abs read);
ReCode (arXiv 2022) provides 30+ code transformations and reports human verification that over 90% of perturbed prompts keep their meaning (abs read) — a direct precedent for *human-verified semantic preservation* of generated variants, which is what SemBench's PENDING review would supply.
EquiBench (arXiv 2025, carried) benchmarks LLM equivalence checking (abs read by A2).
*Implication:* "matched equivalent/non-equivalent transformation pairs with an equivalence-by-construction argument" is **established** methodology. The contribution can only be the JCL domain, its semantics documentation, and the oracle audit.

**3.3 Oracle problem and independence.**
Barr et al. (TSE 2015) survey the oracle problem (bk): oracles are partial, costly and fallible. Avizienis (TSE 1985) and Knight & Leveson (TSE 1986) bear on independence: N-version programming assumes independent failures, and Knight & Leveson's experiment is titled as a test of exactly that assumption (title verified; finding bk — that independently written versions failed on the same inputs more often than independence predicts).
*Implication:* "independent oracle" must never be asserted from code-level independence; correlated misreadings of the IBM reference by one author are the relevant risk. The supporting evidence for SemBench must therefore be (a) an independent human review and (b) at least a second, separately written semantic model for a sample, with disagreement reported — not import-isolation tests.

**3.4 Benchmark design and validity in SE / LLM evaluation.**
Sim, Easterbrook & Holt (ICSE 2003) argue for community benchmarks; Hasselbring (EASE 2021, abs read) notes the SIGSOFT Empirical Standards lacked a benchmarking checklist and discusses requirements for one.
EvalPlus (arXiv 2023, abs read): weak tests mis-rank models (pass@k drops 19.3–28.9% with more tests). SWE-bench (abs read; ICLR 2024 per arXiv comment) and SWE-Bench+ (arXiv 2024, abs read): reported 32.67% solution leakage and 31.08% suspicious patches due to weak tests among passed patches; resolution rate of the studied agent fell from 12.47% to 3.97% after filtering.
Kapoor & Narayanan (Patterns 2023) catalogue leakage in ML-based science; Allamanis (Onward! 2019) shows duplication inflates ML-of-code results; Sallou et al. (carried) list LLM threats; Raji et al. (arXiv/NeurIPS D&B comment) and Jacobs & Wallach (FAccT 2021) argue benchmarks need construct validity (abs read).
*Implication:* the repository's own finding (label ≈ "non-cosmetic text edit", trivial rule F1 0.998) is an instance of a well-documented class — weak/shortcut-prone benchmarks mis-rank systems — so the *finding* is established-pattern; its *instance* in JCL is new-in-search.

**3.5 Regression / semantic differencing.** Jackson & Ladd 1994, SymDiff 2012, Godlin & Strichman 2012, Evans & Savoia 2007 (A2-R7–R10): prove or summarise equivalence of imperative programs. Rehearsal (PLDI 2016) verifies configuration scripts (A2-R14). None is for JCL; none supplies a benchmark of equivalent vs non-equivalent *edits* (bk, unverified beyond titles).

**3.6 Legacy modernisation and behaviour preservation.** Sneed (ICSM 2010, COBOL→Java), Schnappinger & Streit (ICSME 2021, transpilation), Deknop et al. (ICSME 2022), Van Geet & Demeyer (ICSM 2009) are mainframe/COBOL maintenance work (titles verified; content bk); XMainframe and COBOL-Coder are COBOL LLM preprints (abs read by A2). I found **no** paper on verifying behavioural equivalence of migrated **JCL/batch streams** in the sources searched (§2).

**3.7 Responsible-SE and reporting** — see [`RESPONSIBLESE_POSITIONING.md`](RESPONSIBLESE_POSITIONING.md).

---

## 4. Is JCL-SemBench + the evaluation methodology a defensible contribution?

**Verdict: conditionally defensible as a benchmark-and-methodology contribution; not defensible as a tool-effectiveness or "validated oracle" contribution in its present state.**

Why it *can* be defended:
1. The repository's own audit gives a concrete, quantified motivation: on the old benchmark the label coincided with a text-edit predicate on 564/566 mutants, so the benchmark could not separate semantic reasoning from text diffing. A matched-pair design whose pairs share surface-edit cost directly addresses this *specific* construct-validity defect. This is the same *kind* of repair EvalPlus/SWE-Bench+ perform for other benchmarks (abs read), so the reasoning is recognisable to reviewers.
2. No JCL benchmark or JCL semantic-equivalence study was found in the sources searched (§2), within the stated caveats.
3. The evaluation protocol (trivial baselines first, full accounting, cluster CIs, refutation criteria) is publishable as method even if RELIC does poorly — which is exactly the property a benchmark paper needs.

Why it can **not yet** be defended as strong:
1. **Labels are author-only.** BP/BC classification, semantic documentation and oracle are all the same team's reading of the IBM reference; "PENDING independent review" means construct validity of the key label is unestablished. An EMI-style guarantee ("equivalent by construction") is only as good as the semantic model; here the model is unvalidated against z/OS (ORACLE_SPECIFICATION §6.1, §6.6).
2. **"Equivalent" means "equivalent modulo the oracle's scenarios".** Scenario sets are finite (single fault, RC set, SMS assumption); opaque programs yield UNDETERMINED and are dropped, which can bias BP towards modelled programs. This is the JCL analogue of the equivalent-mutant problem (Madeyski 2014; Papadakis 2015) and must be quantified (UNDETERMINED rate by transformation family).
3. **Template fingerprints.** If every BP/BC transformation comes from a small set of generator templates, a surface classifier can learn the template (shortcut), reproducing the original defect at one remove (cf. Allamanis 2019 on duplication/leakage; Kapoor & Narayanan 2023). A "matched" pair removes edit-size shortcuts, not template shortcuts. Needs a template-aware baseline and held-out transformation families.
4. **Shared lexer** (mutator↔oracle) still affects *which* pairs exist; the independence audit must show label stability under an independent tokenizer.
5. **External validity.** ≈4 external repos (INTEGRATION_REPORT Q&A E), demonstration code, none production; none blind (screened by aggregate).
6. **Real defects.** Nothing links SemBench transformations to real migration defects (L6); Just et al./Papadakis et al. 2018 warn against assuming such links.

---

## 5. Proposed contribution structure

**Primary contribution (P).** *JCL-SemBench*: a matched-pair benchmark of behaviour-preserving vs behaviour-changing JCL transformations, with a documented-semantics specification per transformation family, executable-oracle labels, explicit UNDETERMINED accounting, and independent human review of a stratified label sample, designed so that surface baselines (normalised text diff, step-multiset diff, template-fingerprint classifier) are *expected and tested* to be non-discriminative.

**Supporting contributions (exactly three).**
* **S1 — Evaluation protocol with oracle-independence audit.** Trivial-baselines-first reporting, full candidate accounting, cluster-bootstrap CIs, pre-declared refutation criteria, a layered independence audit (import isolation → shared-lexer ablation → independently written second semantic model on a sample → human review) with disagreement reported.
* **S2 — A quantified construct-validity diagnosis of the earlier benchmark.** The label≈text-edit result (564/566 agreement; F1 0.998 vs 0.980), the V2 development-fit caveat, and a validity-threat catalogue, offered as a case study in how mutation benchmarks for configuration-like languages overstate detector quality.
* **S3 — A frozen reference detector and baseline suite with an external-corpus run.** RELIC V2 frozen before first look, plus text, structural, template-fingerprint and (fair, multi-model, contamination-caveated) LLM baselines, evaluated on SemBench and on screened external repositories, reported whatever the outcome.

Not claimed: a new detection algorithm; superiority over text diff or LLMs; validated oracle; production relevance.

---

## 6. Research questions and falsifiable hypotheses

All numeric thresholds below are **proposed defaults chosen by me for the pre-registered protocol; they are not derived from the literature and must be frozen before first look at held-out data.** Primary metric: MCC (matched pairs make classes balanced, but MCC also exposes constant-flagger behaviour); also report F1, specificity, recall, UNDETERMINED rate. Uncertainty: paired cluster bootstrap (cluster = source file; sensitivity: cluster = repository), 95% CI. Each hypothesis has three outcomes: **supported / refuted / inconclusive** (CI spans the threshold).

| RQ | Question | Hypothesis | Refutation criterion (hypothesis refuted if…) |
|---|---|---|---|
| RQ1 | Does SemBench discriminate semantic detectors from surface baselines? | **H1:** On SemBench pairs, RELIC V2 exceeds the normalised text diff by a margin: ΔMCC = MCC(RELIC) − MCC(textdiff) > 0.10. | Normalised text diff achieves MCC within 0.10 of RELIC (upper 95% CI of ΔMCC < 0.10 → refuted; lower CI > 0.10 → supported; otherwise inconclusive). Also refuted if a template-fingerprint or step-multiset baseline reaches MCC ≥ 0.9 × RELIC's, which would show the *benchmark* (not the detector) is shortcut-prone. |
| RQ2 | Are SemBench labels valid? | **H2:** Independent reviewer(s), blind to oracle output, agree with oracle labels on a stratified random sample: Cohen's κ (or Gwet AC1 if prevalence is skewed) ≥ 0.80. | Lower 95% CI of κ < 0.60, **or** any transformation family with oracle–reviewer disagreement > 10% (min. n per family pre-declared). Refutation → relabel/withdraw affected families, report. |
| RQ3 | How much does the oracle's own construction drive the results? | **H3:** Re-labelling with (a) an independent tokenizer and (b) a second independently written semantic model on a sample changes ≤ 1% of labels, and the detector ranking is unchanged. | Label change > 2% under either variant, or the order of any two detectors flips (rank correlation Kendall τ < 0.8 across oracle variants incl. `no_abend` vs `full`). |
| RQ4 | Does frozen RELIC V2 generalise beyond its development files? | **H4:** On a sealed external set, RELIC V2's MCC falls by ≤ 0.10 relative to its development-subset MCC. | Drop > 0.10, or the external set's cluster-CI lower bound for MCC is below the best surface baseline's MCC (the external result is then reported as "no demonstrated advantage"). With ≈4 repositories the CI is expected to be wide: "inconclusive" is a likely, acceptable outcome and must be reported as such. |
| RQ5 | Are LLM comparisons stable under behaviour-preserving transformations? | **H5:** A fixed, documented LLM prompt flags behaviour-preserving variants at a higher rate than RELIC (LLM FPR on BP > RELIC FPR), i.e. LLMs are sensitive to surface form (cf. Rabin 2021, EquiBench abstract). | LLM FPR on BP ≤ RELIC FPR + paired CI covering 0 across ≥ 2 models, all pairs attempted, invalid outputs counted explicitly (not dropped). |

Pre-declared "kill" statement: if H1 and H2 are both refuted, the paper's primary contribution (P) is not supported and the work should be reported only as a negative-results/validity case study (S2).

---

## 7. Closest competing studies and novelty-boundary table

### 7.1 Closest competing studies (metadata verified; content bk unless noted)

| Study | Why close | What it does *not* cover |
|---|---|---|
| Statfier, ESEC/FSE 2023 | Semantic-preserving transformations to test static analysers | Not JCL; tests analyser bugs, not change-detector benchmark validity |
| EquiBench (arXiv 2025; abs read) | Equivalence-checking benchmark with equivalent / non-equivalent pairs | LLM reasoning on mainstream languages; not batch/job languages |
| Le, Afshari & Su, PLDI 2014 (EMI) | Equivalent-variant generation with semantics-based guarantee | Compilers/C; guarantee from program semantics + inputs, not a hand-written model |
| ReCode (arXiv 2022; abs read) | Transformation suite + human check that meaning is preserved | Prompts for code generation, not version-pair change detection |
| Rabin et al., IST 2021; Yefet et al., OOPSLA 2020 (abs read) | Semantic-preserving transformations expose model brittleness | Neural models of code, not rule/contract detectors; no JCL |
| SWE-Bench+ (arXiv 2024; abs read); EvalPlus (arXiv 2023; abs read) | Benchmark-validity critiques that re-evaluate a benchmark and show mis-ranking | Python issue-resolution/code-gen |
| Just et al., FSE 2014; Papadakis et al., ICSE 2018 | Validity of mutants as stand-ins for real faults | Java/real-fault studies; not equivalence-by-construction pairs |
| Rehearsal, PLDI 2016; SymDiff 2012; Regression verification 2012 | Ordering/determinism and semantic-difference checking | Single version (Rehearsal) or imperative languages; no JCL |
| Sneed 2010; Schnappinger & Streit 2021 | Mainframe/COBOL migration | COBOL focus; no JCL semantic-equivalence benchmark found |
| RELIC V1/V2 (this repo) | Predecessor benchmark and detector | Label≈text-edit (S2) |

### 7.2 Novelty-boundary table

| Element | Status | Evidence | Caveat |
|---|---|---|---|
| Matched-pair / metamorphic design with equivalent and non-equivalent variants | **Established** | EMI (PLDI 2014), metamorphic testing survey (CSUR 2018), Statfier (FSE 2023), ReCode, EquiBench | Design pattern is not the contribution. |
| Benchmark-validity critique (weak tests/labels mis-rank systems) | **Established** | EvalPlus, SWE-Bench+, Raji et al., Jacobs & Wallach, Sim et al. | The critique of *RELIC's own* old benchmark is new evidence, not a new idea. |
| Trivial-baseline-first reporting | **Established** | Fu & Menzies 2017 (carried); Empirical Standards (abs) | — |
| A JCL benchmark with BP/BC pairs, documented semantics | **No prior art found in the sources searched (candidate novel)** | §2: 0 arXiv hits (f)(g)(h); Crossref/OpenAlex JCL hits are books, 1970s language design, tooling | Search incomplete (no DBLP/S2, no grey literature). **Do not write "first".** |
| Executable-semantics model of JCL as test oracle | **No prior art found in the sources searched (candidate novel)** | same | Model unvalidated vs z/OS; if prior simulators exist in vendor tooling, claim collapses. |
| Layered oracle-independence audit (import isolation → shared-lexer ablation → second implementation → human sample) | **Incremental** | N-version independence literature (Avizienis 1985; Knight & Leveson 1986) motivates it; oracle problem survey (Barr 2015) | Whether other SE benchmark papers do this was not systematically checked (unknown). |
| Pre-declared refutation criteria for a benchmark paper | **Incremental / established practice** | Registered reports (Ernst & Baldassarre 2023); Empirical Standards | Novel only as applied here. |
| Contract extraction from JCL (TEMPORAL/RESOURCE/CONTROL_FLOW) | **Incremental** | Def-use/dependency analysis; Rehearsal, Licker & Rice (A2) | Per A2 §5. |
| Version-to-version contract differencing for JCL | **Incremental / unknown** | Semantic-diff tools exist for other languages (A2-R7–R9) | No prior art found for JCL, search incomplete. |
| COND/return-code guard contracts | **Unknown** | not found in any checked reference | Could be too narrow to have been published. |
| RELIC V2 outperforms a normalised text diff | **Refuted on the old benchmark; unknown on SemBench** | 0.980 vs 0.998 (AGENT_1 §4) | H1 tests this. |
| RELIC outperforms LLMs | **Unknown** | current LLM comparison selection-biased (183 invalid outputs; INTEGRATION_REPORT) | H5 addresses a different, narrower question. |
| Generalisation to production JCL / relevance to real defects | **Unknown** | no production data; L6 | — |

---

## 8. Unverified — do not cite

| Item | Reason |
|---|---|
| Feldt & Magazinius, "Validity threats in empirical software engineering research — an initial survey" (SEKE 2010) | Query (26) did not find it in Crossref; may have no DOI. Not verified by any primary source. |
| Chen, Cheung & Yiu 1998 metamorphic-testing technical report (original MT paper) | Not queried; cite the verified Chen et al. CSUR 2018 survey instead. |
| McKeeman 1998 "Differential testing for software"; Hamlet 1977 mutation; DECLARE (Pesic & van der Aalst); Sadiq & Orlowska data-flow validation; Fluri/GumTree; Hou et al. LLM4SE survey | Not queried (or failed earlier per A2 §8). |
| Any Kitchenham guideline/paper | Not queried this session. |
| ACM Code of Ethics (the Code text) | `acm.org/code-of-ethics` HTTP 403. Only the CACM article about it (Gotterbarn et al.) is verified, and only as Crossref returned it. |
| ACM SIGSOFT Empirical Standards website/checklists | Only the arXiv overview (abs read) was verified; the standards repository was not fetched. |
| Any RENE / registered-reports track names, scopes, dates, page limits | One guessed URL returned 404; no CFP was fetched. |
| ICLR 2024 acceptance of SWE-bench; NeurIPS 2023 acceptance of EvalPlus; ACL/other venue of ReCode; NeurIPS 2021 D&B for Raji et al.; FAccT 2021 for Jacobs & Wallach | Venue taken only from arXiv comments (or absent); not checked against the venue's record. Cite as arXiv unless confirmed. |
| Papadakis et al. 2019 author list and year | Crossref has no authors; authors from OpenAlex (aggregator) only; year 2019 (Crossref) vs 2018 (OpenAlex online). Confirm on the publisher page. |
| Jackson & Ladd 1994 given names | Crossref gives family names only (carried from A2). |
| "Prüfung von JCL-Standards" (1990), "Eclipse IDE plug-in for JCL support" (2014) | Surfaced by OpenAlex; authors/content not retrieved or read; mentioned only as "found, not assessed". |
| Crossref record 10.46243/jst.2021.v6.i06.pp139-149 | Same title as Sim et al. 2003 under different authors/venue (2021); looks like a re-publication. **Never cite.** |
| All (bk) content statements in §3 and §7.1 | Titles/authors/years/venues verified; paper contents not read except where "abs read". |
| The 8 repository-bib items (Lorenzoli 2008, Leucker 2009, Flanagan 2001, Felsing 2014, Naik 2006, Fan 2023, Mens 2004, Andrews 2005) | Not re-verified by me (A2 §2 note). |
