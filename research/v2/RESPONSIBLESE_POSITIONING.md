# ResponsibleSE positioning for JCL-SemBench / RELIC (Agent 5)

Companion to [`FINAL_NOVELTY_ASSESSMENT.md`](FINAL_NOVELTY_ASSESSMENT.md); references in
[`final_verified_references.bib`](final_verified_references.bib) (cite keys in backticks). Status of the underlying
evidence is as in the assessment: RELIC V2 is development-set only, the oracle is author-written and unvalidated against z/OS,
the earlier benchmark's label ≈ "non-cosmetic text edit", independent review of SemBench labels is **PENDING**.
Nothing here asserts a result that the repository does not contain. Statements about what a cited paper says are from verified
metadata or an arXiv abstract I read, otherwise marked (bk, background knowledge).

---

## 1. Framing: what the responsible-SE problem actually is here

RELIC is meant to tell a modernisation team whether a change to a batch job stream preserves behaviour. The evaluation therefore
supports a *decision* ("is this migrated/edited job safe?"). The responsible-SE risks are risks to that decision, not abstract ethics:

| Risk | How it can arise in this project | Evidence in the repository |
|---|---|---|
| **False assurance** | A benchmark score (F1 0.98) is read as "RELIC detects broken contracts in production JCL"; absence of a flag is read as "safe". | V2 F1 0.980 vs trivial rule 0.998; 18 false negatives (13 GenApp swaps, 1 CardDemo swap, 4 renames); 104 of 106 negatives are comment/MSGCLASS edits; no production data. |
| **Automation bias** | Reviewers accept a "no violation" output without independent checking. Automation-bias and complacency effects with automated aids are documented in human-factors and clinical decision-support literature (`parasuraman2010complacency`, `goddard2012automation`; titles verified, findings bk). Whether they transfer to JCL reviewers is **unknown**; no study of RELIC users exists. | No user study. |
| **Hidden oracle dependence** | Labels, mutants and detector share author, period and (partly) lexer; "independent oracle" was overstated in earlier text (REVIEW_AND_REVISED_DRAFT C6). N-version independence assumptions are themselves contested (`avizienis1985nversion`, `knight1986independence`; titles verified, content bk). | ORACLE_SPECIFICATION §6. |
| **Benchmark construct invalidity** | A benchmark that cannot separate the method from a trivial rule produces misleading rankings (`liu2023evalplus`, `aleithan2024swebenchplus`, `raji2021everything`, `jacobs2021measurement`; abstracts read). | AGENT_1 §4: 564/566 agreement between label and text-edit predicate. |
| **Selective reporting** | CardDemo-only CI in abstract; "advantage = specificity" narrative; "random subsample" for a selection-biased LLM comparison (REVIEW_AND_REVISED_DRAFT C1–C5). | Documented by the paper review and the INTEGRATION_REPORT. |
| **Data / licensing and third-party exposure** | External repositories reused; the LLM baseline sends repository text to a third-party API; human reviewers' time and credit. | INTEGRATION_REPORT E, R-6; see §5. |

The project's strongest asset is that it already found and recorded several of these against itself. The positioning should keep that:
the paper should be *about* evaluating change-risk detectors without false assurance, with RELIC as the worked example.

---

## 2. Transparency about oracle dependence

Required statements in any manuscript (each is currently true and should be stated, not softened):

1. The oracle is a **model** of JCL execution semantics written by the same author as the mutator/transformer and the detector. It was not run against real z/OS or IBM Z D&T.
2. "Behaviour-preserving" in SemBench means **equivalent modulo the oracle's observables and scenario set** (execution, dataflow, final catalog, termination; single fault; listed RC values; SMS assumption). It does not mean semantically equivalent on a mainframe. (The analogy to "equivalence modulo inputs", `le2014emi`, is deliberate and should be named.)
3. Opaque programs yield UNDETERMINED and are excluded from scoring; report their count per transformation family so readers can judge selection effects.
4. Independence evidence is layered and its layer is named: import isolation (weakest) → shared-lexer ablation → second independently written semantic model on a sample → independent human review (strongest; **PENDING**). Never write "independent oracle" without the layer.
5. Until human review is complete, every table must carry the tag "labels author-only".

---

## 3. Uncertainty reporting and explainability

* Report CIs for every headline number (paired cluster bootstrap by source file; sensitivity by repository). With ≈4 external repositories, say explicitly that repository-level intervals are wide and that "inconclusive" is an acceptable, reportable outcome.
* Report **coverage**, not only accuracy: flagged / not flagged / abstained (unsupported construct, UNDETERMINED, invalid LLM output) per detector. A detector that silently scores unsupported constructs as "not flagged" produces false assurance (repository defects D-022: exceptions scored as "not flagged"; D-023: unsupported-construct diagnostics).
* Report per-family recall and specificity, not only pooled F1/MCC (pooling was dominated by two subjects, AGENT_1 §2).
* A detector output meant for engineers should say *which contract* is broken and *under what assumption*; the existing paper admits that "naming the violated contract" is **not measured** (REVIEW_AND_REVISED_DRAFT C4). Do not claim explainability benefits until measured.
* Seeds, scenario sets, `full` vs `no_abend` variants and the treatment of UNDETERMINED must be reported; conclusions should be shown robust (or not) to them.

---

## 4. Negative results and registered-reports practice

* Report the null/negative findings as results: normalised text diff ≥ RELIC on the old benchmark; V2's gain traceable to one fix on seven files; LLM comparison not interpretable.
* Pre-register hypotheses, metrics, thresholds and refutation criteria **before** the first look at the held-out/external data (see the RQ/H table in the assessment; thresholds there are proposed defaults, not literature-derived). Registered-report practice in SE is described by `ernst2023registered` (metadata verified; content bk).
* Freeze RELIC V2 and the SemBench generator/oracle versions (hash-tag) before running external corpora; any later change is labelled post-hoc.
* State the **kill condition** in the protocol: if the benchmark does not separate the detector from the surface baselines (H1) *and* labels fail review (H2), report as a negative-results/validity case study only.

---

## 5. Data, licensing and human-subject ethics (external repositories and reviewers)

Facts from INTEGRATION_REPORT (not independently re-checked by me): 4 candidate external repositories — `IBM/zopeneditor-sample` (Apache-2.0), `zowe/zowe-install-packaging` (EPL-2.0), `cschneid-the-elder/mapa` (MIT; synthetic parser-stress data only), `yetacp/mvs_sysgen` (MIT fork, **upstream licence unverified**); release-audit item R-6 says dataset licences are partly unverified; the screening saw aggregate counts and fragments, so the pool is "screened by aggregate", not blind.

Obligations (not legal advice; confirm with the institution):
1. **Licence audit before redistribution.** Record licence, commit hash and retrieval date per repository in a datasheet (`gebru2021datasheets`, verified; the datasheet practice is bk). Redistribute only what each licence permits (e.g., distribute transformation scripts + hashes and fetch instructions rather than third-party files where redistribution is unclear; EPL-2.0 and unknown-upstream items need explicit review).
2. **Do not use `yetacp/mvs_sysgen` as evidence until upstream licensing is resolved**, or list it as "excluded: provenance".
3. **No production or customer JCL** without written permission, anonymisation, and confirmation that the files contain no credentials, hostnames, customer-identifying dataset names or personal data. Scan for secrets before any LLM call.
4. **Third-party LLM APIs.** Sending external repository text to a hosted model is a disclosure to a third party; check provider terms and repository licences first; record model, provider, version, date and prompt version (the repo's earlier model/provider inconsistency — gpt-oss-20b/nvidia in records vs 120b/Groq in text — is the cautionary example). Treat training-data contamination as likely for public GitHub repositories and say so (`sallou2024breaking`; `kapoor2023leakage`; `allamanis2019duplication`).
5. **Human reviewers (mainframe practitioners).** Obtain informed consent, tell them how labels will be used, state compensation/acknowledgement, keep them blind to detector output, and check whether the institution requires ethics review for expert-annotation studies. The ACM Code of Ethics is the usual professional reference (the CACM article about it is verified, `gotterbarn2017acm`; the Code text page itself returned HTTP 403 and was **not** verified).
6. **Misuse.** A benchmark that characterises detector blind spots also shows what slips past a reviewer. Risk is low here (batch JCL, no security claim), but say the tool is a triage aid and not a security or compliance control.

---

## 6. Claims discipline — checklist authors must satisfy before submission

Tick each or record the reason it cannot be ticked.

**Evidence status**
- [ ] Every number is tagged: *development*, *frozen-held-out*, or *external*. V2 numbers on the 566 old mutants stay tagged *development*.
- [ ] RELIC and all baselines frozen (commit hash) before the first look at held-out/external data.
- [ ] Label provenance stated per pair: *oracle-only* / *oracle + reviewer(s)*; review status not left as PENDING in any table presented as a result.
- [ ] UNDETERMINED, invalid outputs, exceptions and out-of-scope candidates are counted and shown, not dropped.

**Baselines and metrics**
- [ ] Normalised text diff, step-multiset diff, template-fingerprint classifier and a documented LLM baseline are in the main results table, not an appendix (cf. `fu2017easy`).
- [ ] Primary metric (MCC) and CIs (cluster bootstrap) reported; per-family results shown.
- [ ] Hypotheses and refutation criteria quoted verbatim from the pre-registration with their outcome (supported / refuted / inconclusive).

**Oracle**
- [ ] The phrase "independent oracle" does not appear without the independence layer achieved.
- [ ] "Behaviour-preserving" is defined as "equivalent modulo the oracle model and scenario set"; real-z/OS validation status stated.
- [ ] Shared-lexer, same-author and single-fault assumptions stated in the main text, not only in the limitations file.

**Novelty and scope**
- [ ] "First", "novel", "no prior work" are not used. Use: "no prior art found in the sources searched (list), search incomplete" — with the caveats of assessment §2.
- [ ] No claim of superiority over text diff, LLMs or commercial tooling unless a pre-registered hypothesis supports it.
- [ ] No claim of real-defect representativeness (`just2014mutants`, `papadakis2018correlated` examine exactly that gap for mutants) or production readiness.
- [ ] Contribution list is exactly one primary + three supporting, matching the assessment.

**Reporting standards**
- [ ] The relevant SIGSOFT Empirical Standards (`ralph2020empirical`; standards content not fetched by me) and the benchmark requirements discussed by `hasselbring2021benchmarking` have been read and the checklist mapped.
- [ ] Threats to validity cover construct (label ≈ predicate; template shortcuts), internal (shared lexer, post-hoc fixes), external (≈4 repos, demonstration code) and conclusion validity (small n, clustering).
- [ ] Reproducibility: one command regenerates every table; known non-determinism (timestamps, LLM cache) documented; artefact licences stated.

**Responsible communication**
- [ ] Abstract and conclusion say the tool is a triage aid, give recall, and state that "not flagged" ≠ "safe".
- [ ] Abstract includes the trivial-baseline result from the old benchmark (F1 0.998 vs 0.980) or its SemBench equivalent.

---

## 7. Recommended venues and tracks (nothing below is verified as current)

I did not fetch any call for papers (one guessed track URL returned 404). Track names are from background knowledge; **check the current CFP for scope, page limits, dates, artefact and registered-report rules before deciding.** I make no claim about deadlines or acceptance criteria.

| Option | Why it fits | What to verify |
|---|---|---|
| Maintenance/evolution venues (ICSME, SANER) — negative-results/RENE-style, registered-reports, dataset/tool or industry tracks (bk) | Legacy/mainframe maintenance papers have appeared at ICSM/ICSME (verified metadata: `schnappinger2021platform`, `deknop2022semiparsing`, `sneed2010cobol`); the benchmark-validity/negative-result framing matches | Existence and scope of each track this cycle; whether benchmark papers are in scope |
| Mining/data venues (MSR data/showcase track) (bk) | Only if an external-corpus mining angle and a documented dataset (datasheet) are central | Track existence; licensing rules for redistributed code |
| Testing venues (ICST, ISSTA) (bk) | Mutation validity, metamorphic/EMI-style design and the oracle problem are native topics (`just2014mutants`, `le2014emi`, `barr2015oracle`) | Whether a JCL-domain benchmark is in scope; novelty bar vs `zhang2023statfier` |
| Empirical venues (ESEM; EMSE journal) (bk) | Benchmark validity as an empirical question; pre-registered design | Registered-report options and format |
| Industry/experience track (any) | Only if an industrial partner supplies production JCL or practitioner reviews (turns limitations into strengths) | Partner, data-sharing and ethics terms |

Do **not** target a main-track effectiveness paper on current evidence (consistent with Agent 2 §6).

---

## 8. Honest self-assessment (three dimensions)

Scale 1–5 (1 = would not survive review, 3 = acceptable at a specialist/negative-results venue, 5 = strong at a top venue). Scores are my judgement from repository evidence and the verified literature; they are not predictions of acceptance.

| Dimension | Score now | Evidence for the score | What would raise it (priority order) |
|---|---|---|---|
| **Rigour / validity** | **2** | **For:** arithmetic independently recomputed with 0 discrepancies across 12 detectors × 4 populations (AGENT_1); full accounting of 656 candidates; pinned-confusion tests; a self-audit that found the label≈predicate defect, the model/provider inconsistency and the "random subsample" error. **Against:** V2 tuned on its evaluation files; no held-out data; oracle author-only, shared lexer, unvalidated vs z/OS; SemBench review PENDING; ≈4 external repos, not blind; LLM comparison invalid; manuscript not compiled (INTEGRATION_REPORT). | (1) Completed independent blind label review with κ and per-family disagreement (H2). (2) Second independently written semantic model on a sample + shared-lexer ablation (H3). (3) Frozen, pre-registered external run with template-fingerprint baseline (H1, H4). (4) Fair multi-model LLM re-run, all pairs attempted (H5). Realistic ceiling with these: 3–4. |
| **Novelty** | **2** | **For:** no JCL benchmark / JCL semantic-equivalence / JCL static-analysis prior art found in Crossref, arXiv, OpenAlex (0 arXiv hits on three JCL/mainframe queries; Crossref/OpenAlex hits are books, 1970s language design, tooling). **Against:** matched-pair/metamorphic/EMI design, benchmark-validity critique, mutation-validity worries and trivial-baseline reporting are all established (`le2014emi`, `zhang2023statfier`, `liu2023evalplus`, `aleithan2024swebenchplus`, `fu2017easy`); the contract extractor is incremental; DBLP/Semantic Scholar were unavailable and grey literature unsearched, so absence is weak evidence. | (1) Complete the search (DBLP, Semantic Scholar, ACM DL, IEEE Xplore, vendor/IBM Z DevOps documentation, patents). (2) Show SemBench separates detectors that the old benchmark could not (H1 supported). (3) A transformation-family taxonomy grounded in real change histories (not yet evidenced). Realistic ceiling: 3 — the domain is new, the idea is not. |
| **Impact / relevance** | **2–3** | **For:** mainframe batch is a real modernisation setting (mainframe/COBOL migration work exists: `sneed2010cobol`, `schnappinger2021platform`, `dau2024xmainframe` [preprint]); a public benchmark with documented semantics would be reusable by tool and LLM evaluators; the audit story is useful to benchmark authors for other configuration-like languages. **Against:** no user study; no production JCL; no evidence that SemBench transformations resemble real migration defects; small community; small benchmark. | (1) Practitioner involvement (reviewers or partner JCL). (2) Evidence that SemBench failure modes match real defects (case analysis of real change histories). (3) Release of datasheet, generator, oracle and baselines under verified licences. (4) A usable "abstain" output so the tool can be used as triage without false assurance. |

**Overall:** a defensible, honest benchmark-and-methodology paper for a specialist or negative-results track *if* H2 (label validity) and the frozen external run are completed. Without them, the work remains a development-set report plus a validity case study. The ResponsibleSE value is that the claims-discipline checklist and refutation criteria make the outcome publishable *whichever way the hypotheses fall*.

---

## 9. Unverified items relevant to this file (do not cite until verified)

* ACM Code of Ethics text (HTTP 403); SIGSOFT Empirical Standards website/checklists (only the arXiv overview was verified); any RENE/registered-reports track description, dates or page limits (no CFP fetched).
* Feldt & Magazinius (validity-threats survey) — not found in Crossref; Kitchenham guidelines — not queried; Hamlet 1977, McKeeman 1998, Chen et al. 1998 — not queried.
* Findings of `parasuraman2010complacency`, `goddard2012automation`, `avizienis1985nversion`, `knight1986independence`, `gebru2021datasheets` as paraphrased here: metadata verified, content from background knowledge; abstracts not read.
* Venue claims for `liu2023evalplus`, `jimenez2023swebench`, `wang2022recode`, `raji2021everything`, `jacobs2021measurement` beyond what the bib states.
