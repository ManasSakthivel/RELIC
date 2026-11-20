# Baseline fairness and literature audit (RELIC V2)

Scope: read-only audit. No git was run, nothing outside this file and `LITERATURE_MATRIX_V2.csv` was written. Evidence is cited as file paths. Where a claim is my inference rather than something a file states, it is marked **(inference)**.

## Summary

1. `normalized_text_B` is not a "trivial" baseline. It is a JCL-syntax-normalised diff with ten hand-written rules, two of them JCL-specific (`ignore_job_parameters`, `sort_keyword_operands`). It should be named that way.
2. Circularity is real but partial. Its true negatives come almost entirely from the benchmark's PRESERVING categories that are pure layout or comment edits. It does not cover parameter synonyms, DD reordering, default-DISP spellings or step renames, which is mild evidence against deliberate tailoring. Any circularity biases the comparison against RELIC, not for it.
3. The only Holm-significant "trivial rule beats RELIC" result on SemBench (B vs RELIC V2, Holm p = 0.020) rests on one rule. B differs from A on exactly 7 cases, all 7:0 for B, all in the two keyword-order subcategories that `sort_keyword_operands` targets. Against A the result is not Holm-significant (0.172). "RELIC shows no advantage over text rules" is robust; "the best trivial rule is significantly better" depends on that one rule.
4. `textdiff_ignore_job_parameters` is explicitly post hoc and built from the benchmark's negative operators (its own docstring). Its external F1 of 0.9978 is not independent evidence about detector quality. The external run reuses the same two negative operators.
5. The freeze evidence is self-reported flags plus a SHA-256. It does not prove blindness to the SemBench taxonomy.
6. The benchmark has no adversarial case for the normaliser: no CHANGING case is confined to comments, JOB parameters or letter case. Its documented semantic-loss modes are never exercised, so its recall is untested where it should fail.
7. Literature: bibliographic metadata of all 46 DOIs in the two bibs resolve in Crossref and match. Real problems: two foundational semantic-diff and AST-diff omissions (Horwitz 1990, GumTree), a missing closest analogue (TCE), a stale preprint venue (ReCode), a surname-only author (Jackson and Ladd), and a duplicated Sneed key. No literature method was reimplemented or run in this repo.

## A. Baseline fairness

### A1. What the normaliser does (read from `relic_eval/text_baselines.py`)

Rules in order: `preserve_instream_data`, `strip_comment_lines`, `drop_blank_lines`, `truncate_col71`, `rstrip_whitespace`, `join_continuations`, `strip_trailing_comment_field`, `collapse_whitespace`, `uppercase_outside_quotes`, `ignore_job_parameters`. Version B adds `sort_keyword_operands` (top-level KEY=VALUE operands of EXEC/DD/PROC/OUTPUT, after the positional prefix, not inside parentheses).

- Comments: all `//*` lines and trailing comment fields are removed.
- Whitespace and layout: blank lines, columns 72-80, trailing blanks, blank runs, case outside quotes, continuation line breaks are all removed.
- Keyword order: only in B, only top-level keywords.
- JOB statement: reduced to `//NAME JOB`. The file's own docs say this causes real semantic loss for COND=, TYPRUN=, REGION=, TIME=, RESTART= and CLASS=.
- Not done: no DD or statement reordering, no DSN/DSNAME synonym mapping, no DISP default expansion (`DISP=SHR` vs `DISP=(SHR,KEEP)`), no step-name canonicalisation, no PROC or symbol expansion.
- Information RELIC lacks: none beyond RELIC's own inputs. Both see only the pair of texts. The normaliser has no execution model, no dependency graph. It does discard information RELIC may also discard (JOB parameters, comments); that equivalence of ignorance is not itself unfair.

### A2. Was it frozen before the results were seen?

Evidence for: `results/sembench/BASELINE_FREEZE.json` records the rule list, `sembench_cases_jsonl_present_at_freeze: false`, `sembench_cases_loaded_by_agent4_before_freeze: false` and a SHA-256. I re-hashed: `shasum -a 256 relic_eval/text_baselines.py` returns `1ff51f34ad5cf11c28dd9afba0cbd13c205749b75de5ce30cfc015ac976213c6`, identical to the freeze. `pytest tests/sembench -q` passes (39 tests).

Limits:
- The flags are self-reported by the agent that wrote the baseline. All files in this tree have identical birth times (copied tree), and I cannot run git, so no timeline can be reconstructed.
- "No case loaded" is not "taxonomy unknown". `reports/v2/SEMBENCH_DESIGN.md` lists six PRESERVING categories (comment edit, whitespace and continuation, syntax representation, job card refactor, independent reorder, step rename) and says in its comparison table that they include "continuation reflow, parameter synonyms, DD reordering". Other docs say agents received sprint briefs describing SemBench. Rule-to-category correspondence (comments -> comment_edit; col71/continuation/whitespace/case -> whitespace_and_continuation; JOB parameters -> job_card_refactor; keyword order -> syntax_representation) is one-to-one for four of six categories **(inference: consistent with either deliberate tailoring or with the rules simply being the standard JCL-cosmetic set)**.
- The benchmark changed from 179 to 180 cases after the freeze (`BASELINE_AND_STATISTICAL_ANALYSIS.md` s8). `SEMBENCH_DESIGN.md` is dated "March 2025", which conflicts with the repo's other dates; do not rely on it for chronology.
- Pre-freeze exposure that is disclosed: a smoke run of the pipeline on the old 566-mutant benchmark (`NORMALIZED_TEXT_BASELINE.md`, "Honest interpretation"). Its negatives are only INSERT_COMMENT and CHANGE_MSGCLASS, which two of the ten rules (`strip_comment_lines`, `ignore_job_parameters`) remove completely (leave-one-out table: specificity 0.98 with both, 0.37 without comment stripping, 0.61 without JOB stripping).

Verdict: the freeze is a real precommitment of the rule text (hash), not a proof of blindness. Describe it as "rules fixed before SemBench cases were loaded by the baseline author, who knew the category design".

### A3. How much of the normaliser's advantage is circular? (computed from `results/sembench/predictions.jsonl`)

False positives of A / B on the 87 PRESERVING cases, by subcategory (RELIC V2 in last column):

| PRESERVING group | n | A FP | B FP | RELIC V2 FP |
|---|---|---|---|---|
| comment_edit (all) | 17 | 0 | 0 | 0 |
| job_card_refactor (all; 10 are job_class_change) | 12 | 0 | 0 | 0 |
| whitespace_and_continuation | 17 | 2 | 2 | 0 |
| dd_keyword_order + keyword_operand_order | 7 | 7 | 0 | 0 |
| dsn_dsname_synonym | 5 | 5 | 5 | 0 |
| disp_explicit_keep_default | 4 | 4 | 4 | 0 |
| independent_statement_reorder | 14 | 11 | 11 | 0 |
| other syntax_representation (parens, parm quoting, cond parens) | 5 | 4 | 4 | 0 |
| unreferenced_step_rename | 6 | 2 | 2 | 2 |

Reading, both directions:
- About 51 of B's 59 true negatives are comments, JOB parameters, layout, and (for B only) keyword order. These are exactly the cosmetic classes the rules strip. So B's specificity on those classes is by construction.
- B fails on DSN/DSNAME synonyms (5/5), explicit-default DISP (4/4), DD reorder (11/14) and renames. A `DSN`->`DSNAME` rule is one line; its absence is mild evidence against tailoring to the benchmark.
- The one benchmark-specific step with a measurable effect is `sort_keyword_operands`: 7 cases, 7:0, drives the only Holm-significant loss for RELIC.
- Ten of the 87 PRESERVING cases are byte-identical pairs (counted by `SEMBENCH_DESIGN.md` s5), trivially negative for every textual detector.
- Where the normaliser is not circular: its recall. Every CHANGING pair with a textual difference is flagged by any detector that flags non-cosmetic text changes. All 15 of B's false negatives are the byte-identical no-op label errors (`SEMBENCH_DESIGN.md` s5 says 15 CHANGING pairs are byte-identical). So B's recall of 0.84 on ALL is a property of the benchmark, not of the method.
- Converse circularity: the benchmark contains no CHANGING case confined to a comment, a JOB parameter (e.g. TYPRUN, COND on JOB) or case. The normaliser's own documented failure modes (`RULE_DOCS`) are therefore never tested, so its recall is unchallenged exactly where it would fail. An honest benchmark would include such cases; their absence flatters the normaliser.

Net: the comparison "RELIC vs normalised text" answers "does RELIC beat a cosmetic-noise filter plus raw diff on this benchmark". It does not answer "does RELIC beat plain text diff". Report the whole ladder (raw -> textdiff -> ignore-JOB -> A -> B), not one number. It is fair to the claim "RELIC is not more accurate than text rules" and unfair to nothing in RELIC's favour; it should not be called trivial.

### A4. `textdiff_ignore_job_parameters`

- `relic_eval/v2_eval.py` docstring: "DIAGNOSTIC ONLY (post hoc, not a competing detector) ... both negative operators edit only comments or JOB parameters." It was designed from the old benchmark's negative operators, i.e. from the data's construction.
- It predates the external run (`EXTERNAL_VALIDATION_PROTOCOL.md` already cites it), but the external pairs reuse the same ten operators, and the only negatives are again INSERT_COMMENT and CHANGE_MSGCLASS (`EXTERNAL_VALIDATION_RESULTS.md`, per-operator line). The comparator is therefore the exact complement of the negative generator on both the old and external corpora. External F1 0.9978 equals the old-benchmark F1 0.9978 for the same reason.
- Justification independent of the data: it is a reasonable "textdiff plus cosmetic-field filter" in general, but nothing in the repo justifies the JOB-parameter exemption other than the operator set. It is a legitimate diagnostic that exposes benchmark weakness. It is not independent evidence that RELIC V2 is worse in general.
- The normalised A/B detectors were never run on the external set (grep of `EXTERNAL_VALIDATION_RESULTS.md` finds none). `PREREGISTRATION.md` lists `textdiff_ignore_job_parameters` as the external comparator; keep that, state that A/B are not available externally.

### A5. Recommended actions (baseline)

1. Rename in text and tables: "JCL-syntax-normalised diff (rules frozen before SemBench cases were loaded)". Drop "trivial".
2. State the freeze limits from A2 verbatim in the limitations.
3. Report B and A together, and report the B-minus-sort result (= A) as the primary robust comparison. Note that the Holm-significant B result is a 7-case effect.
4. State that no benchmark case exercises the normaliser's semantic-loss modes; if cheap, add pre-registered adversarial CHANGING cases (JOB TYPRUN/COND edits, scheduler control comments, unquoted case-significant tokens) as labelled-new exploratory data, not as post-hoc relabelling.
5. Do not present the external F1 gap as independent replication of the SemBench finding.
6. If a Type-1-clone framing is used, verify the definition in Roy, Cordy, Koschke (2009) first; I have only its title and Crossref metadata.

## B. Literature audit

Method and limits. Bibliographic metadata: Crossref `api.crossref.org/works/<doi>` for every DOI in `paper/v2/references.bib` and `research/v2/final_verified_references.bib` (46 distinct DOIs; all returned a record whose title, authors, year and venue match the bib), arXiv API for 6 preprints, plus targeted Crossref title searches for omitted works. Abstract-level checks were done for four items through a fetch tool that returns a paraphrase (Semantic Scholar summaries for Kintis 2018, Menzies 2016, GumTree 2014) and a web-search digest (TCE 2015); these are labelled "abstract paraphrased", not "abstract read". ReCode's venue and Jackson and Ladd's first names come from search snippets only. Publisher pages were not fetched. doi.org returned HTTP 403 for the four DOIs I tried to resolve there. No full text was read for any entry.

### B1. Comparison matrix (full detail in `LITERATURE_MATRIX_V2.csv`, 90 rows)

| Type | Contents | Status |
|---|---|---|
| 1. Direct head-to-head in this repo | `raw_text`, `textdiff`, `textdiff_ignore_job_parameters`, `normalized_text_A/B`, `relic_v1_0/v1_1/V2`; `llm_C/D` on the old benchmark only | LLM rows are selection-biased and partial (`EVALUATION_SUMMARY.md` s4) and must not be reported as a fair comparison. A/B not run externally. |
| 2. Reimplemented methods | none | Empty set. No literature method (TCE, GumTree, SymDiff, RTS, clone detectors, equivalence checkers, Statfier) was reimplemented. |
| 3. Results reported in prior publications | none compared | TCE's reported ~30% equivalent-mutant detection exists in the literature but is a different task, dataset and metric; it must never be set beside SemBench true-negative counts. |
| 4. Qualitative capability comparisons | semantic-diff and regression-verification tools (Jackson and Ladd 1994, SymDiff, differential assertion checking, differential symbolic execution, Godlin and Strichman), AST differencing (GumTree, ChangeDistiller), RTS (Rothermel and Harrold), equivalence checking (Churchill 2019), analysers for adjacent artefacts (Rehearsal, Licker and Rice), LLM mainframe work, commercial JCL tools | These need a formal program model or target other languages; none was run on JCL here. Commercial tools are snippet-level only. |

### B2. Entries checked (title, authors, year, venue, DOI all match Crossref unless stated)

Correct as recorded: just2014, jia2011, madeyski2014, papadakis2015 (TCE), kintis2018, barr2015, hamlet1977, demillo1978, lahiri2012 (SymDiff), lahiri2013, person2008, felsing2014, rothermel1996, ernst2007, ammons2002, lorenzoli2008, deknop2022, le2014 (EMI), chen2018, statfier 2023, godlin2012, allamanis2019, kapoor2023.

Relevance checks that matter:
- `rothermel1996analyzing` is an RTS evaluation framework, not an RTS technique; paper s"Semantic differencing" cites it as RTS. The technique paper (Rothermel and Harrold 1997, TOSEM) is missing.
- `just2014mutants` / `andrews2005mutation` support "mutation validity" only; they say nothing about change detectors. Fine as used.
- `lahiri2012symdiff`, `person2008`, `felsing2014`, `godlin2012` are semantic-equivalence tools with formal models; the paper's own text correctly calls RELIC "far weaker". Qualitative only.
- `meyer1992`, `ernst2007daikon`, `ammons2002`: terminology and spec-mining background; no empirical comparison is implied.

### B3. Corrections needed (nothing fixed in place)

1. `jackson1994semantic` (paper bib) and `jackson1994semanticdiff` (research bib): authors are recorded as "Jackson and Ladd", which BibTeX treats as two surname-only authors. A web-search snippet gives Daniel Jackson and David A. Ladd, pages 243-252. Correct to full names after checking the PDF.
2. `wang2022recode` (research bib): listed as a preprint. A web search of the ACL Anthology shows ACL 2023 (Long), pp. 13818-13843, DOI 10.18653/v1/2023.acl-long.773, with 14 authors including Dan Roth and Bing Xiang. Snippet level; confirm via `aclanthology.org/2023.acl-long.773.bib`.
3. `andrews2005mutation`: Crossref spells the second author "L.C. Brand"; the paper bib has Briand, which is correct. Keep, and leave the existing comment.
4. `papadakis2019advances`: Crossref has no authors; the author list came from OpenAlex only. Also issued 2019 vs online 2018. Check the publisher page.
5. Same Sneed paper under two keys (`sneed2010cobol`, `sneed2010migrating`); unify.
6. `dau2026cobolcoder` (arXiv 2604.03986, published 2026-04-05 per arXiv API) and `wei2025equibench`: preprints, no peer-review venue verified. Mark as such wherever cited.
7. Entries verified but never cited in the paper: godlin2012, vangeet2009, schnappinger2021, gopinath2014/2017, offutt1992, avizienis1985, knight1986, wei2025, shambaugh2016, licker2019, li2012. Either cite or drop; Godlin and Strichman, Rehearsal and Licker and Rice are the useful ones.
8. `paper/v2/related_work.tex` says "We found no work ... that evaluates JCL-level behavioural checking". This is supported only by targeted queries. My additional searches found only patents (US 8326867 job-network generation; US 10409573 batch decomposition) and vendor tools (IBM Z JCL Expert; Micro Focus Enterprise Analyzer), no peer-reviewed JCL change-detection work. Keep it as an incomplete-search statement and mention the industrial tools.
9. `research/v2/FINAL_NOVELTY_ASSESSMENT.md` admits "No SemBench file exists in the repository at the time of writing"; its SemBench statements were made unseen and should not be reused as findings.
10. `final_verified_references.bib` carries entries "CARRIED ... without re-querying". All of them re-resolved in Crossref in this audit, so they can be re-labelled as re-verified (metadata only).

### B4. Missing work (all metadata_crossref-only unless noted; none content-verified)

| Topic | Entry | Why it matters |
|---|---|---|
| Semantic vs textual diff | Horwitz 1990, PLDI, doi 10.1145/93542.93574 | The founding statement of RELIC's central distinction. Most important omission. Two DOIs exist (a SIGPLAN Notices copy 10.1145/93548.93574). |
| AST differencing | Falleri et al. 2014 (GumTree), ASE, 10.1145/2642937.2642982 (abstract paraphrased); Falleri and Martinez 2024, ICSE; Fluri et al. 2007, TSE; Chawathe et al. 1996, SIGMOD | Text diff vs structural diff is the same axis as textdiff vs RELIC. The earlier assessment lists GumTree as "Not queried". |
| Regression test selection | Rothermel and Harrold 1997 TOSEM 10.1145/248233.248262; Yoo and Harman 2012 STVR (Crossref returned both 10.1002/stv.430 and 10.1002/stvr.430, doi.org 403 for both: resolve before use); Gligoric et al. 2015 (file-level selection that works in practice) | Safe-but-imprecise vs precise-but-unsafe framing. |
| Equivalent-mutant detection and normalisation baselines | TCE (Papadakis et al. 2015; in research bib, absent from paper bib), Kintis et al. 2018, Schuler and Zeller 2012, Offutt and Pan 1997, Kintis and Malevris 2013 | TCE is the closest literature precedent for "cheap normalise-and-compare filter used as equivalence detector"; it reports finding roughly 30% of equivalent mutants (abstract paraphrase). Cite it for the normaliser's role. Never compare its numbers with SemBench. |
| Clone detection | Kamiya et al. 2002 (CCFinder); Roy, Cordy, Koschke 2009; Svajlenko et al. 2014; Krinke and Ragkhitwetsagul 2022 (title-level only) | Token/comment/whitespace normalisation lineage; benchmark-validity critiques. |
| Program equivalence | Churchill et al. 2019 PLDI 10.1145/3314221.3314596 | Equivalence of transformed programs; formal. |
| Negative-result and simple-baseline norms | Menzies et al. 2016, EMSE, 10.1007/s10664-016-9472-2 (abstract paraphrased: nothing beat the original procedure); Fu and Menzies 2017 (already in bib, under-used); Ralph et al. empirical standards (not read in full) | Precedent for publishing a result where simple methods win. Verify the empirical-standards text for any quoted rule on negative results. |
| Legacy / mainframe | no peer-reviewed JCL work found | See B3 item 8. |

Not searched or not resolved: GumTree-style tools applied to non-code configuration formats; LLM-based change-impact surveys (the paper's own TODO ii); Semantic Scholar and DBLP are blocked or rate-limited in earlier sessions, so coverage of 2023-2026 LLM-for-code-review work is not established.

## Tests run

- `shasum -a 256 relic_eval/text_baselines.py` equals the frozen hash `1ff51f34...976213c6`.
- `pytest tests/sembench -q -p no:cacheprovider`: 39 passed.
- Per-subcategory FP table recomputed from `results/sembench/predictions.jsonl`.
- Crossref lookups for 46 DOIs (all resolved, metadata matched) and 30 title searches for omitted works; arXiv API for 6 ids.

## Remaining uncertainty

- Whether rules were tuned to the SemBench taxonomy cannot be settled without version-control history, which I cannot read.
- No full text of any reference was read; TCE and GumTree content comes from paraphrased abstracts, Jackson and Ladd and ReCode details from search snippets.
- The Type-1 clone definition and the empirical-standards wording on negative results remain unverified.
- Which Yoo and Harman DOI and which Chawathe DOI is canonical is unresolved (doi.org returned 403).
