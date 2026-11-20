# RELIC V2 — Manuscript and reviewer audit (Agent 5)

Repository: `RELIC`, branch `research/relic-v2-integration`, HEAD `b690039`.
Scope of this file: review of `paper/paper.md`, `README.md`, `docs/*`, `reports/v2/*`
against `results/final/metrics.json`, `results/v2/v2_metrics.json` and
`results/final/raw/llm_records.jsonl`. Nothing outside `paper/v2/` was edited.
Companion files: `main.tex`, `abstract.tex`, `introduction.tex`, `related_work.tex`,
`methodology.tex`, `architecture.tex`, `results.tex`, `discussion.tex`,
`threats_to_validity.tex`, `conclusion.tex`, `references.bib`.
`research/v2/LITERATURE_AND_NOVELTY_ASSESSMENT.md` did **not** exist when this was
written; `reports/v2/AGENT_4_TECHNICAL_AUDIT.md` and `AGENT_6_RELEASE_AUDIT.md` did
exist and were consulted (they agree with the findings below, notably the
model/provider conflict, the LLM selection bias and the D-004 observation).

**Status of every V2 number: development set. External validation pending.**

---

## 1. Overall verdict

The existing manuscript is unusually candid about the withdrawn v1 result, but it
still (a) contradicts its own raw records on the LLM baseline (model, provider,
"random subsample"), (b) keeps an "advantage = specificity" narrative that the
post-hoc normalised text diagnostic (F1 0.9978 vs RELIC V2 0.9800) refutes,
(c) calls the oracle "independent" where only code-independence holds, and
(d) does not mention V2 at all. A reviewer who opens `results/v2/v2_metrics.json`
would find the main claims weaker than stated. The strongest defensible paper is a
**benchmark-and-oracle methodology with negative/diagnostic findings, a scoped
contract-extraction tool, and a validity-threat report** — not an effectiveness paper.

---

## 2. Unsupported or overstated claims (file:line, quote, verdict)

| # | Location | Quote | Problem | Action |
|---|---|---|---|---|
| C1 | `paper/paper.md:38` | "On a quota-limited random subsample, an LLM (`gpt-oss-120b`) given both versions…" | Three errors in one sentence: model (records: `openai/gpt-oss-20b`, `llm_status.json`), not quota-limited, not random (see N2). | Remove; replace with "183 of 566 mutants have no valid output; comparison not interpretable". |
| C2 | `paper/paper.md:29`, `README.md:102,129-130` | "Coverage is limited by the provider quota…; the answered mutants are the first ones of a seeded random order, i.e. a random subsample." | False per raw records: all 566 mutants were attempted for C and D (`order_index` 0–565 all present); 148 (C) and 103 (D) are `INVALID_OUTPUT` ("no JSON object in response"), scattered over indices 6–564; unscored mutants are 89.6 % positive vs 77.3 % for scored. | Remove "random subsample"/"quota". |
| C3 | `paper/paper.md:348-350, 424-425`; `README.md:129-132` | "the dependency-augmented LLM is at least as accurate as RELIC v1.0.0" | Holds only on the selection-biased 383 subset. Bounds on all 566 for llm_D are 0.8468 (invalid=not flagged) – 0.9536 (flagged); v1.0 is 0.9048 — i.e. undetermined. | Narrow to "no conclusion possible". |
| C4 | `paper/paper.md:335-338, 423-424`; `README.md:120-123`; `docs/limitations.md` L7 | "RELIC's advantage is specificity"; "Its advantage over trivial change detection is specificity rather than recall" | Refuted by D-014: text diff ignoring JOB-card parameters: P 0.9957, R 1.0, specificity 0.9811, **F1 0.9978** (> V2 0.9800, v1.1 0.9510, v1.0 0.9048). Negatives are 104/106 comment/MSGCLASS. "Naming the violated contract" is not measured (paper admits at :337-338). | Remove; state benchmark cannot separate RELIC from a trivial normalised rule. |
| C5 | `paper/paper.md:26` (abstract) | "RELIC v1.0.0 − reference F1 difference 95% CI [-0.07, 0.02]" | Selective: this is the CardDemo CI. The pooled CI in `results/final/metrics.json` (`results.pooled.bootstrap.diff_ci95["relic_v1_0-textdiff"]`) is **[-0.1183, -0.0048]**, i.e. the plain text rule is better than v1.0 pooled. | Report pooled and per-subject. |
| C6 | `paper/paper.md:1,18-19,59,69,420`; `README.md:3,39,96` | "independent execution-semantics oracle", "independent simulator" | Only code-independence (import-checked). Same author for oracle, mutator, detector; oracle and mutator share a lexer; written in one commit with fixes (D-013); no z/OS comparison, no reviewer (`docs/limitations.md` L3, L13). | Say "code-independent, same-team, not validated". |
| C7 | `paper/paper.md:5`; `README.md:139` | "Every number in this document is generated from `results/final/metrics.json`" | Contradicted by C1 (prose names a different model) and by V2 numbers living in `results/v2`. | Delete or restrict to generated blocks. |
| C8 | `paper/paper.md:33-34` | "two implementation defects" | V2 register lists D-001…D-012 (4 fixed, 8 open); D-001 alone accounts for 39 of 43 v1.1 false negatives. | Replace with the register. |
| C9 | `paper/paper.md:359-360` | "post-hoc fixes … remove most v1.0.0 misses" | Pooled FN 80 → 43 (v1.1), i.e. 46 %; "most" is true on CardDemo only (38 → 9). | Quote pooled numbers. |
| C10 | `paper/paper.md:94` (also :91-92) | "we are not aware of prior work that evaluates JCL-level contract checking against an execution-semantics oracle" | Absence claim without a systematic search. My Crossref probes found nothing relevant but are not a search. | Soften, TODO systematic search (§4). |
| C11 | `README.md:171` | "Mutants simulate documented failure classes" | Contradicts `paper/paper.md:399-400` and `docs/limitations.md` L6 (taxonomy sources unverifiable). | Use paper wording. |
| C12 | `README.md:79`, `paper/paper.md:131` | "ten source-level operators" | `REMOVE_IF_GUARD`: 23 candidates, 0 evaluable (D-015). Nine operators contribute. | "Ten defined, nine evaluable". |
| C13 | `paper/paper.md:156-157` and passim | "RELIC v1.0.0 as released (primary, blind)" | `relic_v1_0` is `legacy_v1_0=True` code in the current tree, not a checkout of release commit `db51c84` (D-018). "Blind" is also qualified: authors ran the benchmark and wrote the fixes. | Call it "v1.0 legacy-mode configuration". |
| C14 | `paper/paper.md:352-354` | "remaining advantages are determinism, cost, the absence of an external service" | Cost and determinism not measured. | Mark as untested. |
| C15 | `paper/paper.md:413-416`; `docs/reproducibility.md:69-71` | "regenerates every number…"; "no timestamps" | `run_info.json` has a timestamp (D-019); LLM numbers reproduce only from cache, not from a re-run (no key). | Qualify. |
| C16 | `README.md:219` | "391 passing tests" | After V2: 439 (391 + 48) per `reports/v2/EVALUATION_SUMMARY.md` §5. Stale if V2 is merged. | Update when merged. |
| C17 | `paper/paper.md:318-320` | "RELIC v1.0.0 flags no behaviour-preserving mutant" | True (FP 0) but uninformative: 104 of 106 negatives are comment/MSGCLASS edits; this composition is never disclosed in the paper's main text (only in `v2_metrics.json → benchmark_adequacy`). | Disclose. |

---

## 3. Numerical and factual inconsistencies (complete list)

| # | Item | Evidence |
|---|---|---|
| N1 | **LLM model/provider** | Raw: `results/final/raw/llm_status.json` → `provider: nvidia`, `model: openai/gpt-oss-20b`, `prompt_version: source_diff_v4`, seed/order seed 20261004. Says 20b/nvidia: `paper.md:29,286`, `README.md:102,151`, readiness report. Says **Groq gpt-oss-120b**: `paper.md:38,162`, `docs/limitations.md:62` (L10). `docs/evaluation/BASELINES.md:34` still has a Groq `llama-3.3-70b-versatile` row; code default is groq/`gpt-oss-120b`; 93 of 1225 cache files are orphaned Groq-120b entries (`reports/v2/REPOSITORY_AUDIT.md`). `llm_last_run.json`: `api_calls_made 189` for 1132 committed records (rest from cache). |
| N2 | **"Random subsample"/"quota"** | See C2. Both baselines have 566 records, `order_index` 0–565; non-OK: C 148 (min 6, max 564), D 103 (17–564). Not-scored (either baseline): 183 = 566 − 383; by subject CardDemo 90, GenApp 89, OMP 4; by operator SWAP 71, SPLIT 52, REMOVE_COND 19, ALTER_COND 17, INSERT_COMMENT 13, CHANGE_MSGCLASS 5, DELETE_PRODUCER 3, MOVE 2, RENAME 1. |
| N3 | **"Ten operators"** | `v2_metrics.json → benchmark_adequacy.operators_with_zero_evaluable_mutants = [REMOVE_IF_GUARD]`; positives span 7 operators, negatives 4 (INSERT_COMMENT 65, CHANGE_MSGCLASS 39, REMOVE_COND 1, ALTER_COND_THRESHOLD 1). |
| N4 | **"Advantage = specificity"** | Pooled: RELIC v1.0 spec 1.0000, V2 1.0000, text-change 0.6132, **diagnostic 0.9811** (2 FP / 106). F1: V2 0.9800 < diagnostic 0.9978. GenApp: plain text-change F1 0.9751 > V2 0.9657 (paired CI V2−text [−0.0574, 0.0199]). Sensitivity row "Without cosmetic negative operators" (`paper.md:249`) has only **2 negatives**, hence "specificity 0.000" for the reference is a 2-sample statement. |
| N5 | **Pooled v1.0 − text diff** | `results/final/metrics.json`: CI [−0.1183, −0.0048]; the manuscript abstract cites only the CardDemo CI. |
| N6 | Pooled counts (consistent, for the record) | 656 candidates / 566 evaluable (86.3 %) / 64 out-of-scope / 26 invalid; 460 positive, 106 negative, 66 files (31+25+10). v1.0 380/0/80/106 F1 0.9048; v1.1 417/0/43/106 F1 0.9510; V2 442/0/18/106 F1 0.9800 — match `paper.md` table and `EVALUATION_SUMMARY.md`. |
| N7 | `paper.md` table of LLM (§5.6) vs `v2_metrics.json` | Consistent: C 0.9846, D 0.9671, v1.0 0.9077, v1.1 0.9577, text 0.9442 on 383 (V2 0.9793 additionally). |
| N8 | **D-004 direction** | `relic_v2_wo_D004` F1 0.9823 (FN 16) > V2 0.9800 (FN 18): the "fix" lowers recall; any text calling D-004 an improvement is wrong (Agent 6 R-8). |
| N9 | Evaluable-file share | Paper describes 55/37/29 job files (121); only 66 files contribute evaluable mutants. CardDemo 31/55. |
| N10 | "Two implementation defects" vs register | See C8. |
| N11 | RESOURCE recovery on GenApp | V2: 2 TP / 3 FP / 2 FN vs v1.1 0/2/4 — one additional FP not analysed (`EVALUATION_SUMMARY.md` §3). |
| N12 | Test counts | 391 (README) vs 439 after V2. |

No arithmetic error was found in the generated tables of `paper.md` versus `results/final/metrics.json` for the quantities spot-checked (accounting, pooled/CardDemo detector rows, CardDemo CI, LLM summary).

---

## 4. Missing related work

**Added to `paper/v2/references.bib`** (each with a `verified via Crossref <DOI>` comment, fetched during this review): Hamlet 1977 (mutation origin); DeMillo–Lipton–Sayward 1978; Just et al. FSE 2014 (mutants vs real faults); Madeyski et al. TSE 2014 (equivalent mutants); Barr et al. TSE 2015 (oracle problem); Ammons–Bodík–Larus POPL 2002 (spec mining); Rothermel–Harrold TSE 1996 (regression test selection); Jackson–Ladd ICSM 1994 (Semantic Diff; Crossref lists family names only); Lahiri et al. FSE 2013 (differential assertion checking); Person et al. FSE 2008 (differential symbolic execution); Sneed ICSM 2010 (COBOL→Java). Existing entries re-verified: Meyer, Daikon, Lorenzoli, SymDiff, Felsing, Jia–Harman, Andrews et al. (Crossref spells "Brand"; kept "Briand", check against the PDF), Deknop et al., Leucker–Schallhart, Houdini.
Dropped from the old bib in v2: Naik (race detection), Fan et al. LLM survey, Mens–Tourwé (no longer cited in the revised text; they remain in `paper/references.bib`).

**TODO — not verified, therefore NOT in `references.bib`:**
1. A systematic search (DBLP, ACM DL, IEEE Xplore, arXiv, Google Scholar) for prior work on JCL / mainframe-batch analysis, job-stream dependency extraction, batch-to-workflow migration. Crossref free-text probes ("JCL job control language analysis", "mainframe batch modernization behavioral equivalence") returned only handbook entries and practitioner/SSRN-style items; this is **not** evidence of absence.
2. Papadakis et al., "Mutation Testing Advances: An Analysis and Survey" (Advances in Computers, 2019; DOI 10.1016/bs.adcom.2018.03.015 resolves in Crossref but the record has no author list — add after author check).
3. LLM literature: code-change/code-review analysis, LLM-based legacy (COBOL/JCL) translation and equivalence judgement; any survey must be located and verified (the existing `fan2023llm` entry in `paper/references.bib` is Crossref-verified but was not reused because it is a general survey).
4. Behavioural equivalence / translation validation / equivalence checking for migrations.
5. Infrastructure-as-code, build-system and workflow-DAG change checking (structurally closest to job-stream checking).
6. Benchmark validity: shortcut features, trivial-baseline sanity checks, construct validity of synthetic-fault benchmarks.
7. Process/log mining of batch schedules (dynamic evidence; the repository's reconciliation component is unvalidated).

---

## 5. Novelty assessment (honest)

* **Algorithmic novelty: none established.** Extraction is rule-based over JCL syntax; diff is signature comparison; "weakened" is a threshold comparison. Each ingredient (contracts, spec mining, semantic diff, mutation analysis) is established.
* **Application novelty: plausible but unproven.** JCL-level contract diff with an execution-semantics oracle may be new; the claim rests on an unsystematic search (§4 TODO 1).
* **Methodological contribution: the most defensible.** Complete accounting of every candidate mutant, oracle labels independent of the operator, replay with SHA-256 checks, ablations, paired cluster bootstrap, and diagnostics that expose the benchmark's weakness.
* **Empirical contribution: weak.** Development-set only; trivial rule parity/superiority; LLM comparison invalid; no held-out data.
* **Versus Daikon/spec mining/mutation testing:** see Q&A 6 below.

---

## 6. Recommended narrative

Use (a) benchmark+oracle methodology with negative and diagnostic findings (primary), (b) behavioural-contract extraction for JCL with explicit scope limits (secondary), (c) a validity-threat report plus the experiments that would settle open questions (tertiary). Present V2 as a development-set revision whose gain is traceable to one fix (D-001; F1 0.9534 without it). Do **not** claim: superiority over text diff or LLMs; independent validation; production compatibility; real-fault representativeness; generalisation; novelty beyond "to our knowledge, subject to a pending literature search".

---

## 7. Claims to remove or narrow

| Existing claim | Decision | Replacement |
|---|---|---|
| "advantage is specificity" (paper:335,423; README:122) | **Remove** | "benchmark does not separate RELIC from a normalised text rule (F1 0.9978 vs 0.9800)" |
| "random subsample", "quota-limited" (paper:29,38,355,424; README:102,129) | **Remove** | "183 of 566 mutants have no valid output (89.6 % positive); not interpretable" |
| "gpt-oss-120b / Groq" (paper:38,162; limitations L10) | **Correct** | `openai/gpt-oss-20b`, nvidia, `source_diff_v4` |
| "independent oracle" | **Narrow** | "code-independent, same-team, not validated against z/OS" |
| "LLM at least as accurate as v1.0.0" | **Narrow** | "no conclusion on committed records; bounds 0.8468–0.9536 for D" |
| "Every number generated from metrics.json" | **Remove** | restrict to generated blocks |
| "ten operators" | **Narrow** | "ten defined, nine evaluable" |
| "documented failure classes" (README:171) | **Remove** | "synthetic; taxonomy unverified" |
| "v1.0.0 as released, blind" | **Narrow** | "v1.0 legacy-mode configuration; pre-fix" |
| "two implementation defects" | **Replace** | defect register D-001…D-012 |
| "we are not aware of prior work…" | **Soften** | "to our knowledge, based on a non-systematic search" |
| Any V2 headline (0.980) without caveat | **Narrow** | always "development set; probably optimistic" |
| Production compatibility / independent validation | **Never claim** | — |

---

## 8. Revised abstract (same text as `abstract.tex`)

Mainframe batch jobs written in JCL encode behavioural rules (step order, dataset allocation and disposition, return-code guards) that are rarely written down and must be re-implemented by hand when a job stream is migrated. We describe RELIC, a static extractor of such rules as explicit *behavioural contracts* (temporal, resource, control-flow) with a contract-level diff between two versions of a job, and we report what a carefully accounted evaluation of it does and does not show. The evaluation uses source-level mutation of three public JCL corpora (656 candidate mutants, 566 evaluable, 66 files) and labels mutants with a JCL execution-semantics simulator that shares no code with RELIC but was written by the same team and has not been validated against z/OS. On this benchmark the pooled F1 of the baseline configuration (v1.0, fixed before the defects were analysed) is 0.905, of a version with post-hoc fixes (v1.1) 0.951, and of a further revision (V2) 0.980. All three corpora were inspected while the defects were found and fixed, so these are *development-set* figures and are probably optimistic. A post-hoc diagnostic rule that flags any text change except to JOB-card parameters reaches F1 0.998 on the same benchmark, because 104 of the 106 behaviour-preserving mutants are comment or MSGCLASS edits; the benchmark therefore does not separate RELIC from a trivial normalised text rule. A comparison with a language model cannot be interpreted: 183 of 566 mutants have no valid output from at least one model, and these are 89.6 % positive. We contribute (i) the benchmark, the accounting scheme and the oracle-based labelling methodology, together with the negative and diagnostic findings above; (ii) behavioural-contract extraction for JCL with explicit scope limits (no PROC/INCLUDE/IF-THEN-ELSE, single-file analysis); and (iii) a catalogue of validity threats. Held-out validation, a fair language-model comparison and independent oracle validation are **[PENDING EXPERIMENT]**. No claim of production compatibility is made.

## 9. Revised introduction (same content as `introduction.tex`)

Re-implementing a JCL job stream on another platform is risky in a specific way: the new job usually runs, but it behaves differently in situations the migration did not consider. A step that used to be bypassed after a failure now runs, a consumer reads a dataset before its producer has rewritten it, or a renamed output is no longer found downstream. These rules are implicit in the semantics of JCL (IBM, *z/OS MVS JCL Reference*). Structural dependency tools record which step uses which dataset, but not the obligations ("step B must not run if step A ends with RC > 4") that the new implementation must preserve.

RELIC extracts such obligations from JCL as explicit behavioural contracts (design by contract, Meyer 1992) and reports the contracts that a changed version of a job breaks or weakens. This paper reports a development-stage evaluation of RELIC and of the evaluation instrument built around it. It does *not* report an independent validation.

**Research questions.** RQ1 (recovery): how well do the contracts RELIC extracts match facts derived from an execution-semantics simulator of JCL? RQ2 (detection): given an original and a mutated job, how well does a contract-level diff separate behaviour-changing from behaviour-preserving mutants, compared with structural, text-based and language-model baselines? RQ3 (benchmark validity): does the benchmark discriminate a contract-aware detector from trivial change detectors?

**Contributions.** (1) A mutation benchmark for JCL change checking with complete accounting of every candidate mutant (656 candidates; 566 evaluable; 90 excluded with stated reasons) and labels from an execution-semantics simulator that is code-independent of the detector (but not author-independent). (2) Diagnostic and negative findings: a text diff ignoring JOB-card parameters scores F1 0.9978, above every RELIC variant (0.9048, 0.9510, 0.9800); evaluable negatives are almost entirely cosmetic; the committed language-model comparison is selection-biased and not interpretable. (3) Behavioural-contract extraction and differencing for JCL (TEMPORAL, RESOURCE, CONTROL_FLOW) with documented scope limits and an ablation of four post-hoc fixes. (4) A catalogue of threats to validity and the experiments needed before any claim of effectiveness.

**What we do not claim.** That RELIC outperforms a normalised text diff or a language model; that the mutants represent real migration defects; that the oracle matches z/OS; that V2 figures generalise beyond the three corpora; or that RELIC is compatible with production JCL. Each is **[PENDING EXPERIMENT]** where it would need new evidence.

---

## 10. Anticipated reviewer objections and responses

| # | Objection | Response (what can honestly be said) | Status |
|---|---|---|---|
| Q1 | **"A trivial text rule scores 0.998."** | Agreed and reported (pooled F1 0.9978, P 0.9957, spec 0.9811; GenApp 1.0000). The rule was built post hoc after inspecting the benchmark and 104/106 negatives are cosmetic, so the benchmark cannot separate it from RELIC. We therefore make no superiority claim. What the rule cannot do — name the broken contract, ignore benign reorderings, handle semantics-preserving renames — is not measured. | **[PENDING EXPERIMENT]**: benchmark with benign reorder/split/rename/symbol-change negatives, then rerun the normalised-text baseline; explanation-correctness study. |
| Q2 | **"The oracle was co-designed with the detector."** | Partly true. Code-independent (import-checked, never sees operator or detector output), but same team, shared lexer with the mutator, one author, same IBM reference, shared blind spot already found (same-named steps). Labels are not tuned on detector output; V2 replay left all labels and statuses unchanged (SHA-256 checked). No independence claim is made. | **[PENDING EXPERIMENT]**: blinded audit of a stratified label sample by an external mainframe engineer; z/OS execution of a sample; inter-annotator agreement. |
| Q3 | **"There is no held-out set."** | Correct. All 3 corpora were inspected during diagnosis. V2 (0.980) is a development result and probably optimistic; the bootstrap covers sampling variation over files only. | **[PENDING EXPERIMENT]**: freeze V2 and the metric, evaluate on a corpus never opened (e.g. additional public JCL), report per-subject. |
| Q4 | **"The LLM baseline is unfair."** | Agreed. 183 of 566 mutants lack a valid output from at least one model (89.6 % positive vs 77.3 % scored); one model, one prompt, one sample; documentation inconsistent across files (now corrected: `openai/gpt-oss-20b`, nvidia). Bounds on all 566: C 0.8083–0.9717, D 0.8468–0.9536. We draw no conclusion. | **[PENDING EXPERIMENT]**: credentialed re-run with a single documented model/provider, invalid-output retries, several models/prompts/samples, full coverage. |
| Q5 | **"Fixes were tuned on the test data."** | Correct. D-001…D-004 were found on the same files used to score them; ablations and paired CIs measure sampling noise, not selection. D-001 carries most of the gain (F1 0.9534 without it) and D-004 slightly lowers F1 (kept on semantic grounds). Only v1.0 predates the fixes (but see D-018). | **[PENDING EXPERIMENT]**: frozen-detector evaluation on unseen corpora. |
| Q6 | **"What is novel vs Daikon / spec mining / mutation testing?"** | Daikon/spec mining infer likely specifications from *executions*; RELIC extracts syntactic obligations from *job definitions* and diffs them — it learns nothing and is much weaker than inference. Mutation testing assesses test suites; here mutation generates change pairs for a change detector, with an oracle supplying labels. Semantic diffing/regression verification (SymDiff, differential symbolic execution) is stronger but needs formal program models unavailable for JCL here. Novelty is at most the combination for JCL plus the benchmark methodology; no algorithmic novelty is claimed; literature search incomplete. | **[PENDING EXPERIMENT]** (literature): systematic search, §4 TODO list. |
| Q7 | "Synthetic mutants may not represent real migration defects." | Agreed; taxonomy sources were unverifiable; guard strengthening never exercised (D-010). | **[PENDING EXPERIMENT]**: mutants mined from real change histories / practitioner-reported defects. |
| Q8 | "Three small teaching corpora; production unknown." | Agreed; no production JCL; single-file; PROC/INCLUDE/IF unsupported (D-006). No production compatibility is claimed. | **[PENDING EXPERIMENT]**: production-like or additional public corpora. |
| Q9 | "Precision 1.0 is an artefact of abend semantics and cosmetic negatives." | Both true (abend makes every reorder observable; 104/106 cosmetic). Reported with the no-abend sensitivity analysis. | **[PENDING EXPERIMENT]**: benign-reorder negatives. |
| Q10 | "Why trust RESOURCE recovery numbers?" | They are not extraction accuracy on JCL-visible facts: oracle facts include program/utility I/O (D-007); OMP recovery is 0/23. | — |
| Q11 | "Intervals / clustering?" | File-level bootstrap (66 clusters, 10 000 reps); small cells (OMP 10 positives); no significance tests. | — |
| Q12 | "Is the v1.0 'as released' number reproducible?" | It is the legacy-mode code path (D-018), reproduced byte-identically by the pipeline, but not a checkout of the release commit. | — |

---

## 11. Pending experiments (consolidated)

1. Frozen-detector evaluation on a held-out corpus — **[PENDING EXPERIMENT]**
2. Benign reorder/split/rename/symbol-change negatives; normalised-text baseline on that benchmark — **[PENDING EXPERIMENT]**
3. Independent oracle validation (z/OS execution or external blinded audit) — **[PENDING EXPERIMENT]**
4. Inter-annotator agreement on oracle labels — **[PENDING EXPERIMENT]**
5. Fair, full-coverage, multi-model LLM re-run with documented provider and retry policy — **[PENDING EXPERIMENT]**
6. Explanation-correctness study ("names the violated contract") — **[PENDING EXPERIMENT]**
7. Real-defect / change-history mutants — **[PENDING EXPERIMENT]**
8. Systematic literature search (JCL/mainframe batch, LLM code-change analysis, IaC change checking) — **[PENDING EXPERIMENT]**
9. Production-like JCL (NDA or additional public corpora) — **[PENDING EXPERIMENT]**

---

## 12. Reproducibility of this draft and LaTeX status

* **LaTeX was NOT compiled.** `which pdflatex latexmk tectonic xelatex lualatex` returned nothing on this machine. Static checks only: balanced braces and `\begin/\end` in all `.tex` files; every `\cite` key exists in `references.bib` and every bib entry is cited; every `\ref` has a `\label`. Compile with `pdflatex main && bibtex main && pdflatex main && pdflatex main` (packages: `natbib`, `booktabs`, `lmodern`, `hyperref`, `geometry`, `amsmath`, `amssymb`).
* All numbers in `results.tex` were copied from `results/v2/v2_metrics.json` and `results/final/metrics.json` (accounting counts: `results/final/metrics.json → accounting`). The author-list entry for Jackson–Ladd lists family names only, because that is what Crossref returns.
* Bibliography: citations were verified by fetching `https://api.crossref.org/works/<DOI>` (via the shell, not an IBM or search tool); the `verified via` comments in `references.bib` name the DOI.
