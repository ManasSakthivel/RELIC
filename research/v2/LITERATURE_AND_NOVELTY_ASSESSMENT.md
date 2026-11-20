# RELIC V2 — Literature and novelty assessment (Agent 2)

Scope: literature position of RELIC V2 (static behavioural-contract extraction from z/OS JCL,
broken-contract detection between job versions, mutation-based evaluation against an executable
oracle). Written against the repository state read on the day of the search (README.md,
docs/limitations.md, reports/v2/EVALUATION_SUMMARY.md, reports/v2/DEFECT_REGISTER.md,
paper/references.bib). No repository file other than this one and `literature_candidates.bib` was touched.

**Evidence status of RELIC used throughout this document:** V2 is development-set only
(pooled n = 566; V2 F1 0.980, v1.1 0.951, v1.0.0 0.905). A text diff that ignores JOB-card
parameters scores F1 0.998 (post-hoc diagnostic). The plain "any non-comment change" rule
scores 0.957. There is no held-out data and no independent reviewer. The oracle is a model
written by the same team and has not been checked against z/OS. The LLM comparison is
selection-biased and not fair. Nothing below assumes otherwise.

---

## 1. Method and queries

### 1.1 Verification policy
A reference is "verified" only if title, authors, year, venue and DOI/arXiv id were returned
by a primary bibliographic source during this session (Crossref REST API, or the arXiv API for
preprints). Where the source omitted a field (e.g. Crossref has only family names for
Jackson & Ladd 1994; no authors for the Papadakis chapter), the item is flagged in the table.

**Important limitation of the verification.** Verification covers *bibliographic metadata only*.
I did not open full texts. My one-line characterisations of what each paper does come from
background knowledge, except for the three arXiv papers (XMainframe, COBOL-Coder, EquiBench),
whose abstracts I read in the API response. Claims about paper content should be re-checked
against the full text before they are used in a related-work section.

### 1.2 Source availability
| Source | Result |
|---|---|
| Crossref `api.crossref.org/works?query.bibliographic=…` | Worked when called one request at a time. Parallel calls returned HTTP 429. Those queries were repeated sequentially. |
| arXiv API `export.arxiv.org/api/query` | Worked (one call timed out at 30 s and was not repeated in that form). |
| DBLP search API | **Blocked** (bot-protection page, no JSON). Not used. |
| Semantic Scholar Graph API | **HTTP 429** on the one call made. Not used. |
| ACM DL / IEEE / Springer landing pages | Not fetched (time budget; Crossref gives the DOI of record). |

Consequence: recall of the search is weaker than it would have been with DBLP/Semantic Scholar.
The "no prior art found" statements in §4 and §7 must be read with that in mind.

### 1.3 Queries actually run (in order, abbreviated; all returned HTTP 200 unless noted)
Crossref `query.bibliographic` / `query.title`:
1. `Mining specifications Ammons Bodik Larus` (429 once, then repeated with `… 2002`)
2. `The program dependence graph and its use in optimization Ferrante Ottenstein Warren`
3. `Are mutants a valid substitute for real faults in software testing Just` (429 once, repeated)
4. `Measuring code quality to improve specification mining Le Goues Weimer` (429 once, repeated)
5. `Applying Design by Contract Meyer 1992`
6. `Daikon system dynamic detection likely invariants Ernst` (429 once, repeated)
7. `Regression verification proving the equivalence of similar programs Godlin Strichman` (429 once, repeated)
8. `SYMDIFF language-agnostic semantic diff tool imperative programs Lahiri` (429 once, repeated)
9. `An Analysis and Survey of the Development of Mutation Testing Jia Harman`
10. `Job Control Language JCL analysis mainframe batch`
11. `query.title: "JCL" job control language z/OS step dataset`
12. `Sallou Durieux Panichella Breaking the Silence threats of using LLMs in software engineering`
13. `Generating Customised Control Flow Graphs for Legacy Languages with Semi-Parsing`
14. `Detecting incorrect build rules Licker Rice`
15. `The Seven Sins Security Smells in Infrastructure as Code Scripts Rahman`
16. `A systematic mapping study of infrastructure as code research Rahman Mahdavi-Hezaveh Williams`
17. `Data flow validation in workflow modelling Sadiq Orlowska` (429 once; repeated; **target not found**)
18. `Mutation Testing Advances An Analysis and Survey Papadakis` (found; authors absent in Crossref record)
19. `Semantic Diff tool for summarizing the effects of modifications Jackson Ladd`
20. `Differential testing a new approach to change detection Evans Savoia`
21. `Mining temporal rules for software maintenance Lo Khoo Liu`
22. `Build systems a la carte Mokhov Mitchell Peyton Jones`
23. `legacy COBOL mainframe migration industrial experience software maintenance`
24. `Rehearsal a configuration verification tool for Puppet Shambaugh Weiss Guha`
25. `Easy over hard a case study on deep learning Fu Menzies`
26. `automated inference of dependencies between batch jobs scheduling workload mainframe modernization` (no relevant hit)
27. `Investigations of the software testing coupling effect Offutt`
28. `Automatic Security Assessment of GitHub Actions Workflows Benedetti` (found; judged peripheral, not carried forward)

arXiv API:
29. `all:"job control language" OR all:JCL AND all:mainframe` → 0 results
30. `all:mainframe AND all:COBOL AND all:LLM` → 3 results (XMainframe, COBOL-Coder, COBOLAssist)
31. `abs:JCL AND abs:z/OS` → 0 results
32. `abs:Terraform AND abs:semantic AND abs:diff` → 0 results
33. `abs:"infrastructure as code" AND abs:"change impact"` → 0 results
34. `abs:Airflow AND abs:DAG AND abs:static…` → 2 results, both irrelevant (LLM DAG generation)
35. `all:"job control language"` (exact phrase) → 0 results
36. `ti:EquiBench` → 1 result (used)
37. `abs:"infrastructure as code" AND abs:LLM AND abs:semantic` → 9 results; top 5 inspected, all IaC *generation*/policy, none about semantic diff of IaC versions
38. (timed out, not repeated) `ti:equivalence AND abs:"large language models" AND abs:program`

DBLP and Semantic Scholar queries for "JCL", "Airflow DAG", "Terraform semantic diff" and
"LLM change risk" were **attempted or planned but not completed**, see §1.2.

### 1.4 Topics searched but not found / not completed
* Peer-reviewed static analysis of JCL: nothing returned (queries 10, 11, 26, 29, 31, 35).
* Semantic diff / change impact for Terraform/Ansible/Airflow: nothing returned in arXiv and
  nothing specific in Crossref (queries 32–34, 37). **Not searched in Crossref** with
  Terraform/Ansible/Airflow-specific title queries; this is a recall gap.
* Data-contamination / benchmark-validity literature beyond Sallou et al.: not searched in depth.
* LLM-based code change risk assessment: only the EquiBench result was retrieved; a dedicated
  search (e.g. "LLM regression detection code change", "semantic merge conflict") was not completed.

---

## 2. Verified references

All rows below were returned by the stated source. "Meta" = what was checked
(T = title, A = authors, Y = year, V = venue, D = DOI/arXiv id).

| # | Reference (title; authors; year; venue) | DOI / id | Source | Meta |
|---|---|---|---|---|
| R1 | Applying "Design by Contract"; B. Meyer; 1992 (Oct); *Computer* | 10.1109/2.161279 | Crossref | T,A(initial only),Y,V,D |
| R2 | The Daikon system for dynamic detection of likely invariants; M. D. Ernst, J. H. Perkins, P. J. Guo, S. McCamant, C. Pacheco, M. S. Tschantz, C. Xiao; 2007 (Dec); *Science of Computer Programming* | 10.1016/j.scico.2007.01.015 | Crossref | T,A,Y,V,D |
| R3 | Mining specifications; G. Ammons, R. Bodík, J. R. Larus; 2002; Proc. 29th ACM SIGPLAN-SIGACT POPL (Crossref also lists the SIGPLAN Notices copy 10.1145/565816.503275) | 10.1145/503272.503275 | Crossref | T,A,Y,V,D |
| R4 | Measuring Code Quality to Improve Specification Mining; C. Le Goues, W. Weimer; 2012; *IEEE TSE* | 10.1109/tse.2011.5 | Crossref | T,A,Y,V,D |
| R5 | Mining temporal rules for software maintenance; D. Lo, S.-C. Khoo, C. Liu; 2008 (Jul); *J. Software Maintenance and Evolution* | 10.1002/smr.375 | Crossref | T,A,Y,V,D |
| R6 | The program dependence graph and its use in optimization; J. Ferrante, K. J. Ottenstein, J. D. Warren; 1987 (Jul); *ACM TOPLAS* | 10.1145/24039.24041 | Crossref | T,A,Y,V,D |
| R7 | Semantic Diff: a tool for summarizing the effects of modifications; Jackson, Ladd; 1994; Proc. ICSM-94 | 10.1109/icsm.1994.336770 | Crossref | T,Y,V,D; **given names absent in Crossref** |
| R8 | Regression verification: proving the equivalence of similar programs; B. Godlin, O. Strichman; 2012; *Software Testing, Verification and Reliability* | 10.1002/stvr.1472 | Crossref | T,A,Y,V,D |
| R9 | SYMDIFF: A Language-Agnostic Semantic Diff Tool for Imperative Programs; S. K. Lahiri, C. Hawblitzel, M. Kawaguchi, H. Rebêlo; 2012; CAV (LNCS) | 10.1007/978-3-642-31424-7_54 | Crossref | T,A,Y,V,D |
| R10 | Differential testing; R. B. Evans, A. Savoia; 2007; Proc. ESEC/FSE 2007 (companion-papers version: 10.1145/1295014.1295038; the "a new approach to change detection" subtitle is not in the Crossref title) | 10.1145/1287624.1287707 | Crossref | T,A,Y,V,D |
| R11 | Are mutants a valid substitute for real faults in software testing?; R. Just, D. Jalali, L. Inozemtseva, M. D. Ernst, R. Holmes, G. Fraser; 2014; Proc. 22nd ACM SIGSOFT FSE | 10.1145/2635868.2635929 | Crossref | T,A,Y,V,D |
| R12 | An Analysis and Survey of the Development of Mutation Testing; Y. Jia, M. Harman; 2011 (Sep); *IEEE TSE* | 10.1109/tse.2010.62 | Crossref | T,A,Y,V,D |
| R13 | Investigations of the software testing coupling effect; A. J. Offutt; 1992; *ACM TOSEM* | 10.1145/125489.125473 | Crossref | T,A,Y,V,D |
| R14 | Rehearsal: a configuration verification tool for Puppet; R. Shambaugh, A. Weiss, A. Guha; 2016; Proc. 37th ACM SIGPLAN PLDI | 10.1145/2908080.2908083 | Crossref | T,A,Y,V,D |
| R15 | Detecting Incorrect Build Rules; N. Licker, A. Rice; 2019; Proc. ICSE 2019 (IEEE/ACM 41st) | 10.1109/icse.2019.00125 | Crossref | T,A,Y,V,D |
| R16 | Build systems à la carte: Theory and practice; A. Mokhov, N. Mitchell, S. Peyton Jones; 2020; *Journal of Functional Programming* (ICFP 2018 artifact record: 10.1145/3235047) | 10.1017/s0956796820000088 | Crossref | T,A,Y,V,D |
| R17 | A systematic mapping study of infrastructure as code research; A. Rahman, R. Mahdavi-Hezaveh, L. Williams; 2019 (Apr); *Information and Software Technology* | 10.1016/j.infsof.2018.12.004 | Crossref | T,A,Y,V,D |
| R18 | Efficient Platform Migration of a Mainframe Legacy System Using Custom Transpilation; M. Schnappinger, J. Streit; 2021; Proc. ICSME 2021 | 10.1109/icsme52107.2021.00055 | Crossref | T,A,Y,V,D |
| R19 | Generating Customised Control Flow Graphs for Legacy Languages with Semi-Parsing; C. Deknop, J. Fabry, K. Mens, V. Zaytsev; 2022 (Oct); Proc. ICSME 2022 | 10.1109/icsme55016.2022.00072 | Crossref | T,A,Y,V,D |
| R20 | XMainframe: A Large Language Model for Mainframe Modernization; A. T. V. Dau, H. T. Dao, A. T. Nguyen, H. T. Tran, P. X. Nguyen, N. D. Q. Bui; 2024 | arXiv:2408.04660 (preprint; **no peer-reviewed venue verified**) | arXiv API (abstract read) | T,A,Y,id |
| R21 | EquiBench: Benchmarking Large Language Models' Reasoning about Program Semantics via Equivalence Checking; A. Wei et al. (11 authors, ending A. Aiken); 2025 | arXiv:2502.12466 (preprint; **no peer-reviewed venue verified**) | arXiv API (abstract read) | T,A,Y,id |
| R22 | Breaking the Silence: the Threats of Using LLMs in Software Engineering; J. Sallou, T. Durieux, A. Panichella; 2024; ICSE 2024 NIER | 10.1145/3639476.3639764 | Crossref | T,A,Y,V,D |
| R23 | Easy over hard: a case study on deep learning; W. Fu, T. Menzies; 2017; Proc. ESEC/FSE 2017 | 10.1145/3106237.3106256 | Crossref | T,A,Y,V,D |
| R24 | COBOL-Coder: Domain-Adapted Large Language Models for COBOL Code Generation and Translation; A. T. V. Dau, S. H. Tan, J. Yang, N. D. Q. Bui, A. T. Nguyen; 2026 | arXiv:2604.03986 (preprint; no peer-reviewed venue verified) | arXiv API (abstract read) | T,A,Y,id |
| R25 | The Seven Sins: Security Smells in Infrastructure as Code Scripts; A. Rahman, C. Parnin, L. Williams; 2019; Proc. ICSE 2019 | 10.1109/icse.2019.00033 | Crossref | T,A,Y,V,D (peripheral) |

Items cited in `paper/references.bib` that I did **not** re-verify here (Lorenzoli 2008, Leucker 2009,
Flanagan 2001, Felsing 2014, Naik 2006, Fan 2023, Mens 2004, Andrews 2005): the repository
states they were checked against Crossref; I take no position. R1, R2, R9, R12 and R19 also appear in
the repo bib and were independently re-confirmed above.

---

## 3. Comparison with RELIC

RELIC contributions used as columns: **C1** JCL-specific contract extraction (TEMPORAL / RESOURCE /
CONTROL_FLOW) into a graph; **C2** version-to-version broken/weakened-contract detection;
**C3** mutation benchmark with an independent executable oracle and full mutant accounting;
**C4** honest negative findings (trivial-rule baseline, post-hoc fixes, LLM comparison invalid).
Characterisations of the cited work are from background knowledge unless marked (abs) — see §1.1.

| Ref | What it does | Overlap with RELIC | Where RELIC differs / does not differ |
|---|---|---|---|
| R14 Rehearsal (Puppet) | Static verification of configuration scripts: models resource ordering/dependencies, checks determinacy and idempotence via a filesystem model | **Closest conceptual neighbour** to C1/C2: ordering + resource-dependency analysis of a declarative operations language | Rehearsal checks one version for determinism with a formal model and SMT; RELIC compares two versions on a lightweight extracted contract set. Rehearsal is far more rigorous; RELIC adds a different language and a change-oriented framing. |
| R15 Licker & Rice | Detects missing/superfluous dependencies in build rules from observed file accesses | Same *class* of bug as RESOURCE contracts (read-before-produce) in a pipeline language | Dynamic (trace-based) and single-version; RELIC is static and version-differential. |
| R16 Mokhov et al. | Formal taxonomy of build systems (scheduler, rebuilder, dependency kinds) | Frames dependency ordering in build/workflow systems; useful vocabulary for TEMPORAL/RESOURCE | Theory of build semantics, no change-risk detection. |
| R7 Jackson & Ladd; R9 SymDiff; R8 Godlin & Strichman | Semantic diff / regression verification: summarise or prove equivalence of behavioural effect of a change | Same goal as C2 (does the change preserve behaviour?) | These work on imperative code with formal semantics; RELIC trades soundness for a small contract vocabulary on a language with no existing semantic-diff tool. RELIC offers no equivalence proof. |
| R10 Evans & Savoia | Differential testing for change detection | Oracle idea: compare two versions by executing them | RELIC's oracle executes a *model* of JCL, not the real system; independence is argued, not shown. |
| R2 Daikon; R3 Ammons; R4 Le Goues–Weimer; R5 Lo–Khoo–Liu | Dynamic/trace-based specification mining; temporal rules (R5) and FSM specs (R3) | Same notion: implicit ordering rules made explicit | RELIC mines **statically** from declarative text, with fixed templates, no trace evidence (dynamic evidence component is unvalidated). Technically much simpler than mining; no precision/recall of mined rules vs. human-verified specs. |
| R1 Meyer | Design by Contract | Terminology only | RELIC "contracts" are inferred observations, not programmer-asserted obligations. |
| R6 Ferrante et al. | Program dependence graph | RESOURCE contracts are def-use edges across steps; BCG is a coarse PDG for job steps | Established; not a novelty. |
| R11 Just et al.; R12 Jia–Harman; R13 Offutt | Mutation validity and the coupling effect | C3 relies on mutants as stand-ins for real defects | RELIC's mutants are *operators designed from expected failure classes*, and the repo itself says the taxonomy is unverified (L6). Just et al. warn that mutant detection correlates with real-fault detection only partially; this applies directly. Coupling-effect arguments are for small faults in code, not for hand-designed migration-defect classes. |
| R23 Fu & Menzies | Simple baselines can match complex methods | Directly analogous to RELIC's 0.998 text-rule result | Supports reporting the trivial baseline prominently. |
| R18 Schnappinger & Streit; R19 Deknop et al. | Mainframe/COBOL migration and legacy-language analysis (transpilation; control-flow graphs via semi-parsing) | Same industrial problem area (COBOL, mainframe); R19 is about semi-parsing legacy languages — RELIC's parser is also approximate | Neither covers JCL or behavioural-change detection to my search. |
| R20 XMainframe; R24 COBOL-Coder | LLMs for mainframe/COBOL (abstracts read) | Context for the LLM baseline; both target COBOL not JCL | Not change detection. RELIC's LLM baseline used one general model and is invalid as evidence. |
| R21 EquiBench | Benchmark of LLM equivalence checking; finds LLMs lean on syntactic similarity (abstract read) | The LLM baseline task is equivalence/non-equivalence of two versions | Different language; suggests that LLM results on mutation pairs should be tested for syntactic-similarity shortcuts. |
| R22 Sallou et al. | Threats of using LLMs in SE: data leakage, non-determinism, reproducibility | Relevant to C4 and to any LLM baseline on public GitHub repositories (CardDemo, GenApp, OMP) that are likely in training data | RELIC's three subjects are public; contamination was not assessed. |
| R17 Rahman et al.; R25 | IaC research mapping; IaC smells | Context for positioning JCL as a legacy IaC-like language | No semantic-diff/ordering contract work in those items. |

---

## 4. The research gap

**Strongest defensible gap (methodological, not algorithmic):**
In the sources I could reach, I found *no* publicly documented benchmark or executable behavioural
oracle for **version-to-version behavioural change in z/OS JCL batch jobs** (step order, dataset
producer/consumer ordering, COND/IF guards), and no evaluation of change-risk detectors for that language
that accounts for every mutant and reports the trivial-baseline result. The repository's reusable
asset is therefore the **benchmark + oracle + accounting protocol + a documented negative result** (a text rule
saturates the benchmark), not a new detection technique.

**Weaker gaps I would not claim:**
* "First static contract extraction for JCL" — absence of evidence from a limited search (§7).
* "Contracts outperform LLMs" — the committed data neither show nor refute this.
* "Contracts outperform a text rule" — the repo's own diagnostic shows the opposite on this benchmark.

---

## 5. Novelty matrix

| Element | Rating | Basis |
|---|---|---|
| Static extraction of temporal/RESOURCE/COND relations from job-step text | **Incremental** | Producer/consumer and ordering relations are def-use/dependency analysis (R6, R15, R16 family). Applying it to JCL is new in my search, but conceptually standard. |
| Calling the result a "Behavioural Contract Graph" | **Established (re-labelling)** | Specification-mining/contract vocabulary (R1–R5). The contracts are template-instantiated, not mined or asserted. |
| Version-to-version contract differencing for JCL | **Incremental / unknown** | Semantic diff exists for other languages (R7–R9). For JCL: no prior art found, search incomplete. |
| COND/return-code guard contracts | **Unknown** | Not found in any reference I checked; could be novel in framing or simply too narrow to have been written up. |
| Mutation benchmark of JCL with executable-semantics oracle and full mutant accounting | **Novel (in my search)** | No JCL benchmark found (queries 10, 11, 26, 29, 31, 35). Strongest claim, but depends on oracle validity (L3, D-013), which is unvalidated. |
| Using mutation analysis as evaluation of a change detector | **Established** | R11–R13. Validity concerns apply (L6). |
| Exposing a trivial baseline that matches the tool (0.998 vs 0.980) | **Established practice, valuable reporting** | R23 supports the practice; the finding itself is specific to this benchmark and counts as a result about the *benchmark*. |
| Finding and fixing same-step-name identity / DD-parsing defects with ablations | **Incremental engineering** | Useful reproducibility evidence; dev-set only. |
| Superiority over LLM baselines | **Unknown** | Current evidence invalid (selection bias, one model; EVALUATION_SUMMARY §4). |
| Generalisation to production JCL | **Unknown** | No production data. |
| Dynamic-evidence reconciliation | **Unknown / unsupported** | Unvalidated (L11); excluded from the evaluated path. |

---

## 6. Publication positioning recommendation

**Do not target a full ICSE/ASE/FSE technical paper.** The evidence is development-set only, the
oracle is untested against real z/OS, the headline detector does not beat a trivial text rule, the
LLM comparison is invalid, and the three corpora are demonstration code. A reviewer at a top venue
will find these in the repository's own documents.

Recommended framing, in order of fit:

1. **Benchmark + oracle + negative-result / reproducibility paper** at a maintenance/evolution venue
   (ICSME or SANER, e.g. a reproducibility/negative-results or tool/dataset track; MSR data/showcase if
   a mining angle is added). Verify track names and page limits against the current call for papers —
   I did not fetch any CFP. Contribution statement: "an oracle-labelled mutation benchmark for JCL
   change risk, an audit of circular evaluation, and evidence that cosmetic-heavy benchmarks are
   saturated by trivial rules."
2. **Industry/experience short paper** (ICSME industry track or similar) only if an industrial partner
   supplies production JCL or practitioner review of oracle labels. This is the single cheapest way
   to turn limitations L1/L3/L13 into strengths.
3. **ESEM-style empirical paper on benchmark validity** — the interesting empirical question is
   "how much do mutation benchmarks for configuration-like languages overstate detector quality",
   using the V2 flips, the 0.998 diagnostic and the specificity-at-fixed-recall analysis.

Required before submission under any framing:
* A **frozen, held-out** subject set (new JCL corpora; V2 frozen before first look). Without it,
  report V2 only as "post-hoc development result".
* **Independent audit of oracle labels** by a mainframe practitioner (blind to detector output),
  or execution of a sample on z/OS/IBM Z D&T.
* **Realistic harmless changes** in the benchmark, so specificity is measurable (EVALUATION_SUMMARY: 106 negatives,
  mostly cosmetic).
* A **fair LLM re-run** (several models, retry policy, all 566 mutants, contamination caveat per R22; consider
  R21's finding that LLMs may exploit syntactic similarity).
* Report the 0.998 text-diff result in the abstract, not just in limitations.

Honest contribution sentence supported by the current evidence: *"We release an executable-oracle
benchmark for JCL behavioural-change detection and show, on development data, that a contract-based
detector reaches F1 0.98 while a normalised text rule reaches 0.998; the benchmark therefore does not
yet separate the two."*

---

## 7. Where no prior art was found, and where my search may have missed it

**No prior art found (with the queries in §1.3):**
* Academic or arXiv work on static analysis, contract extraction or change-risk detection for JCL (queries 10, 11, 26, 29, 31, 35; Crossref returned only encyclopaedia entries, a 1972 Soviet paper, a 1981 *Computer Languages* item, and dictionary entries).
* Semantic-diff or change-impact papers for Terraform/Ansible/Airflow via arXiv (32–34, 37).

**Where I may have missed prior art:**
* **Industry/grey literature** (IBM Z DevOps tools, vendor products such as batch-scheduler dependency analysers, patents, white papers) — not searched at all. Commercial "JCL impact analysis" tools almost certainly exist.
* **DBLP and Semantic Scholar** — both unavailable; a title-keyword search of DBLP for "JCL" is the first thing to repeat.
* **Crossref `query.bibliographic` is relevance-ranked fuzzy search**; exact-phrase absence is not proof of absence.
* Workflow/Petri-net/process-mining literature on data-flow and ordering verification of workflows (e.g. Sadiq & Orlowska style data-flow validation; DECLARE-style temporal constraint languages). My one attempt to verify a data-flow-in-workflow paper failed; the area is probably relevant to TEMPORAL/RESOURCE contracts and I could not review it.
* Job-scheduler/ETL literature (Control-M, Airflow, Oozie dependency validation).
* Program-slicing/change-impact analysis literature (not queried).
* LLM change-risk / code-review literature 2023–2026 (query 38 timed out; no replacement run).
* Data-contamination/benchmark-validity literature beyond R22.
* Spec-mining literature beyond R2–R5 (e.g. Pradel & Gross-style object-usage mining, Lorenzoli et al.) — not re-verified here.

---

## 8. Unverified — do not cite

| Item | Why it is here |
|---|---|
| Sadiq & Orlowska, "Data flow validation in workflow modelling" (circa 2004) | Query 17 returned two other Sadiq/Orlowska papers (BIS 1999/2000), not the target. Possibly misremembered title/year. |
| Papadakis et al., *Mutation Testing Advances: An Analysis and Survey*, Advances in Computers, 2019 | Crossref returned title, year 2019 and DOI 10.1016/bs.adcom.2018.03.015, but **no author list**. Cite only after checking the publisher page. |
| Fluri et al., "Change distilling"; Falleri et al., GumTree | Not queried. |
| DeMillo, Lipton, Sayward 1978, "Hints on test data selection" | Not queried. |
| McKeeman 1998, "Differential testing for software" | Not queried (likely no DOI). |
| Pesic & van der Aalst, DECLARE | Not queried. |
| Trivial Compiler Equivalence (Papadakis et al., ICSE 2015) | Not queried; relevant to equivalent-mutant handling. |
| Hou et al. LLM4SE survey; SWE-bench-style contamination critiques | Not queried. |
| Any statement in §3 about the internal content of a reference other than R20, R21, R24 | Titles, authors, years, venues verified; content comes from background knowledge. |
| The 8 repo-bib items listed at the end of §2 | Not re-verified by me. |
| ICSME/SANER/MSR/ESEM track names in §6 | From background knowledge; no current CFP was fetched. |
