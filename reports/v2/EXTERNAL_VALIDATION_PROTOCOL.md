# RELIC V2 — External dataset survey and validation protocol

Author: Agent 3 (external dataset / validation researcher). Retrieval date (system clock): **2026-11-20**.
Scope: research only; nothing in this repository other than this file was modified. Scratch work was in `/tmp/relic_ext`.

**Verification convention.** "Verified" means I fetched it over HTTP in this session (GitHub REST API via `web_fetch`/`curl`,
`raw.githubusercontent.com` at a pinned commit). Anything else is marked **UNVERIFIED**. The unauthenticated GitHub API
rate limit (60/h) was exhausted mid-session, so some API-only checks (`/license` endpoint for several repos, per-file `git log`) were not completed;
license text was instead verified by reading the first lines of the `LICENSE` file at the pinned commit.

## 1. Summary

* The **public, permissively licensed, realistic multi-step JCL pool is small.** After scanning 11 repositories, I could verify only
  **four** that combine (a) a license I could read and (b) more than ~5 multi-step `.jcl` files and (c) independence from the three development subjects:
  `cschneid-the-elder/mapa` (MIT; but its JCL is *synthetic parser-stress test data*), `yetacp/mvs_sysgen` (MIT on the fork; upstream provenance UNVERIFIED),
  `IBM/zopeneditor-sample` (Apache-2.0; 10 files, 7 multi-step, 7 with `COND=`), and `zowe/zowe-install-packaging` (EPL-2.0; 14 files, 2 multi-step).
  `MVS-sysgen/sysgen` is the richest in COND (71/99 files) but **has no license file** (GitHub `/license` → none; README has no license text) → **excluded until a license is confirmed**.
* None of the candidates appears in `datasets/`, `relic_eval/subjects.py`, or the evaluated results. Three were **named** in archived docs, never acquired or evaluated:
  `IBM/zopeneditor-sample`, `cicsdev/cics-banking-sample-application` (CBSA), and "Zowe/IBM samples" as a future-work sentence (see §3).
* A held-out set built only from these sources would have **~7 usable repositories and a few hundred files** — so a split *by repository* gives very few clusters.
  Confidence intervals must be cluster-aware and honest about this; negative results are expected and must be reportable.
* The existing benchmark cannot show an advantage over a trivial rule (`textdiff_ignore_job_parameters` F1 0.9978 > RELIC V2 0.980; `reports/v2/EVALUATION_SUMMARY.md` §2).
  The protocol in §5 therefore adds stronger negative classes and a normalised-text-diff baseline, and states hypotheses that can **fail**.
* Independent ground truth is feasible only partially: independent human relabelling (days–weeks) and git-history mining (weeks) are realistic;
  real z/OS execution needs an external partner or a licensed/emulated environment, and Hercules/TK4- (MVS 3.8j) can plausibly execute only the `COND=` subset (UNVERIFIED — see §4.4).

## 2. Candidate sources table (verified fields only)

All SHAs are the default-branch HEAD at retrieval (2026-11-20), verified via `GET /repos/{r}/commits/{branch}`. `.jcl` counts come from
`GET /git/trees/{branch}?recursive=1` (`truncated: false` for all). No `.proc/.prc/.cntl/.job` files were found in any of these trees (extension scan only — **extensionless members, if any, are not counted**).
Content prevalence = number of **files** (of those fetched at the pinned SHA) matching a quick regex over `//` statements — an approximation, not RELIC's lexer. "Multi-step" = ≥2 `EXEC` statements; "JOB" = file contains a JOB card (the evaluation-unit rule in `relic_eval/subjects.py`).

| # | Repo (URL) | HTTP verified | License (from LICENSE file at SHA) | Pinned SHA | `.jcl` files / with JOB / multi-step | Files with `COND=` / `IF…THEN` / `INCLUDE` / symbolic `&X` | Provenance | Used in RELIC dev? | Contamination risk |
|---|---|---|---|---|---|---|---|---|---|
| 1 | [IBM/zopeneditor-sample](https://github.com/IBM/zopeneditor-sample) | yes (API, raw) | Apache-2.0 (Apache License 2.0 text read). Note: sample file headers say "LICENSED MATERIALS – PROPERTY OF IBM"; consistent with Apache grant is **UNVERIFIED** | `8f9835308de6159eb54f226041d5f81a780cb8eb` | 10 / 8 / 7 | 7 / 0 / 1 / 9 (25 EXEC steps) | IBM sample project for Z Open Editor (build/run/alloc JCL for COBOL/PL/I/ASM) | **Named only**: `docs/archive/.../secondary_system_selection.md` lists it as "cannot acquire / structurally too simple (prior assessment)"; not in `datasets/` | Medium: IBM public repo, LLM training exposure plausible (UNVERIFIED) |
| 2 | [zowe/zowe-install-packaging](https://github.com/zowe/zowe-install-packaging) (branch `v3.x/staging`) | yes | EPL-2.0 (text read) | `07c2f91fdbb0811f235fb281da8b14350b8ed75d` | 14 / 8 / 2 | 4 / 1 / 0 / 12 (15 EXEC steps) | Zowe SMP/E build and install JCL (`smpe/bld/*.jcl`), test jobs | No | Medium–high (large, popular OSS; UNVERIFIED) |
| 3 | [zowe/zowe-cli](https://github.com/zowe/zowe-cli) | yes (`web_fetch` API) | EPL-2.0 (text read) | `8d0561c2c2c9f2ebc56600cae2d19b6624201870` | 7 / 7 / 2 | 0 / 0 / 0 / 4 (12 EXEC steps) | Test fixtures for `zosjobs` (job submission tests) | No (only the sentence "e.g. Zowe/IBM samples" in `docs/limitations.md`) | Medium–high; fixtures are tiny, test-oriented, not realistic batch streams |
| 4 | [IBM/dbb](https://github.com/IBM/dbb) | yes (`web_fetch` API) | Apache-2.0 (text read) | `251b47505d19601feba13a5a99f8f537bbea4f25` | 3 / 3 / 2 | 2 / 0 / 0 / 1 (7 EXEC steps) | IBM DBB samples (Git ISPF client, jclToZBuilder sample) | No | Medium; **too small** to matter alone |
| 5 | [IBM/IBM-Z-zOS](https://github.com/IBM/IBM-Z-zOS) | yes | Apache-2.0 (`LICENSE.md` text read) | `bc3b0470f7ccaab0de5f2bc6802534af660b146e` | 5 / 3 / 0 | 0 / 0 / 0 / 3 | IBM z/OS tool collection (SMF, print exits, msglg) | No | Medium; **too small / no multi-step** |
| 6 | [cschneid-the-elder/mapa](https://github.com/cschneid-the-elder/mapa) (`jcl/testdata`) | yes (API, raw) | MIT (text read; © Craig Schneiderwent) | `d05705af310730c3e9aa848e824755e652618512` | 216 / 199 / 77 (1,212 EXEC steps) | 20 / 4 / 3 / 117 | Parser regression/stress data authored for an ANTLR JCL grammar. Sampled `test0100.jcl`: 15 lines of `STORCLAS=` syntax variants, not a realistic job. Origin of the other 215 files **UNVERIFIED** (README says the parser was also run on Hercules SYS1/SYS2.PROCLIB; whether any is copied into testdata is UNVERIFIED) | No | Low–medium (obscure repo) — but **low realism**; useful for parser robustness, not for behavioural-contract validation |
| 7 | [yetacp/mvs_sysgen](https://github.com/yetacp/mvs_sysgen) (`sysgen/jcl`, 2022 snapshot) | yes | MIT (text read; © Yet Another Crazy Programmer). The README states it is "heavily based on Jay Moseley sysgen"; **upstream license/redistribution status UNVERIFIED** → MIT on a derivative may not cover the upstream text | `91a532a87892057557ad2a234250cd9ea1764ca4` | 106 / 103 / 67 (1,072 EXEC steps) | 24 / 0 / 0 / 60 | MVS 3.8j system-generation, SMP/E and install jobs for Hercules; JCL is **system-programmer, MVS-3.8-dialect** (no IF/PROC-heavy modern constructs) | No | Low–medium; very old, niche. `git log` for `sysgen/jcl` has 3 commit pages ⇒ history is short |
| 8 | [MVS-sysgen/sysgen](https://github.com/MVS-sysgen/sysgen) | yes | **None found** (API `/license` → null; no LICENSE file in tree; README grep for license/public-domain/copyright returned nothing) → **UNLICENSED for our purposes** | `4746195d33d9810bb9dfb0e8a3064a33efbb0559` | 99 / 92 / 84 (652 EXEC steps) | **71** / 0 / 0 / 34 | Maintained successor of Jay Moseley's sysgen for MVS/CE; **43 commit-pages touch `jcl/`** (real history; depth UNVERIFIED) | No | Low–medium |

**Probed and rejected (verified):**

| Repo | Reason |
|---|---|
| IBM/dbb-zappbuild (`796f48dd…`) | 0 `.jcl` files (7 `.cbl`); not a JCL source. |
| ansible-collections/ibm_zos_core (`46ec35e4…`, branch `dev`) | 0 `.jcl` by extension; GitHub API reports no detected license (real license UNVERIFIED); JCL, if any, is embedded in Python tests. |
| spgennard/vscode_cobol (MIT) | 0 `.jcl`. |
| grossvater/jcl-parser (Apache-2.0, last push 2019) | 1 `.jcl`. |
| cicsdev/cics-banking-sample-application-cbsa | archived pointer repo (1 file); the real CBSA location was not resolved → UNVERIFIED. |
| cicsdev/cics-banking-sample-application | `GET /repos` returned no repo (renamed/moved; UNVERIFIED). Already named in archived dev docs. |
| ozgurhepsag/Basic-z-OS-Utilities-and-Practices, phanikiran99/myMainframe, other small search hits | no license (`none`) → cannot be redistributed/used for a paper without permission. |
| skunklabz/tk4-hercules (6 files), joergschultzelutter/tk5-hercules, TK4-/TK5 distributions | Docker wrappers or binary distributions; **TK4-/MVS 3.8j "public domain" status is a common claim but UNVERIFIED here.** |
| WPTK/ibm-jcl-metar-decoder (MIT) | 1 `.jcl`. |

Search coverage caveat: GitHub repository search (`topic:jcl`, text queries) only. **Code search (`extension:jcl`) needs authentication and was not used**, so repositories that hold JCL without mentioning it in name/description/topics were *not* discovered. The candidate list is therefore a lower bound on what exists.

## 3. Development-use check

* `relic_eval/subjects.py` lists exactly three subjects: `carddemo` (aws-samples, Apache-2.0), `omp_course` (openmainframeproject, CC-BY-4.0/Apache-2.0), `genapp` (cicsdev, EPL-2.0, pinned `f6f3f4b2…`).
  `datasets/` contains only `carddemo`, `genapp`, `public_cobol`. `DATASET_VERSION.txt` for CardDemo and OMP records `git_commit: unknown` (zip of a branch, downloaded 2026-08-14) — **the development subjects are not pinned to a commit**, which matters for later de-duplication against a held-out pool.
* `grep -rIil` over the repo (excluding `.git`, `.venv`, vendored `extracted/` and `source/`) for the names: `IBM-Z-zOS`, `IBM/dbb`, `zappbuild`, `mapa`, `MVS-sysgen`, `sysgen`, `yetacp`, `Moseley`, `TK4`, `hercules`, `cschneid`, `ibm_zos_core`, `vscode_cobol`, `mainframe-dev` → **no hits**.
* Hits:
  * `zowe` → `docs/limitations.md` line 11 (future-work sentence "e.g. Zowe/IBM samples") and one archived HTML report. Not used as data.
  * `zopeneditor` → `docs/archive/2026-08_pre_remediation/docs/secondary_system_selection.md`, `.../evidence_ledger.md`, `results/legacy/secondary_system_candidates.json`: listed as a rejected candidate ("cannot acquire; prior assessment: structurally too simple"). My scan (§2 row 1: 7/10 files multi-step, 7 with `COND=`) **contradicts the "too simple" remark for the TEMPORAL/CONTROL_FLOW families**; the earlier remark's basis is UNVERIFIED.
  * `cbsa` / "CICS Banking Sample" → same archived docs; rejected, never acquired.
  * `jcl-parser` → archived superseded evaluation doc (a different meaning; unrelated to `grossvater/jcl-parser` as far as I could verify — UNVERIFIED).
* **Disclosure for the protocol:** by writing this document I have seen aggregate statistics (file counts, COND counts) for every repo in §2 and sampled the text of 2 files (`mapa/jcl/testdata/test0100.jcl`, `zopeneditor-sample/JCL/ALLOCATE.jcl` head). These repos are therefore **"screened by aggregate"**, not blind. The sealed split in §5 must record this; it does not affect labels (no label or detector output was seen) but it removes the strictest notion of "never looked at".
* **Contamination (who could have seen it):**
  * *RELIC authors*: the dev subjects, plus named-but-unused candidates (zopeneditor, CBSA) — authors knew the names, not the content (per docs).
  * *LLM baselines* (`gpt-oss-20b/120b`): any public GitHub repo may be in pre-training data; I could not verify for any candidate (**UNVERIFIED**). Stars/popularity ordering is a weak proxy. Detector (non-LLM) is unaffected; only LLM baselines C/D are.

## 4. Ground-truth strategies

### 4.1 Real version histories (mine commits that change JCL)
* **Idea:** use `git log -p -- '*.jcl'`, keep commits where the diff touches step order, DD/DSN, `COND=`/`IF`; label by human reading and/or by CI/commit evidence (message says "fix", linked issue, revert).
* **Verified yield indicators** (path-scoped commit pages via `Link: rel=last`, `per_page=1`, i.e. page count = commit count): `MVS-sysgen/sysgen` `jcl/` = 43 commits; `zowe/zowe-install-packaging` `smpe/bld` = 398 commits (directory includes non-JCL); `IBM/zopeneditor-sample` whole repo = 49; `yetacp/mvs_sysgen` `sysgen/jcl` = 3; `zowe-cli` JCL fixtures dir = 2; `mapa` `jcl/testdata`, `IBM/dbb IDE`, `IBM/IBM-Z-zOS zOS-Print` = ≤1. *How many of those commits change JCL semantics (vs whitespace/comments/data) is UNVERIFIED.* Expect most to be cosmetic or content changes (inline data) rather than behavioural contract changes.
* **Pros:** natural change distribution (answers the "mutation realism unmeasured" gap in `REPOSITORY_AUDIT.md` §4); independent of RELIC authors.
* **Cons:** no execution truth; commit message ≠ behavioural equivalence; positives (a real contract break) are rare and mostly repaired in later commits — label = "changed behaviour" not "broke production"; selection of commits can leak the detector. Sysgen is system-programmer JCL for MVS 3.8, far from modern batch.
* **Feasibility:** mining script ≈ 1–2 days; labelling ≈ 1–3 weeks; expected evaluable positives likely **tens, not hundreds** (UNVERIFIED estimate).

### 4.2 Independent reviewer relabelling of a random sample of oracle labels
* Draw a stratified random sample (by operator, subject/repo and oracle label) from the existing 566 evaluable mutants and, later, the held-out set; two or more mainframe-qualified reviewers who have **never seen oracle output or detector output** label DIFFERENT/EQUIVALENT with an evidence line.
* Compute agreement oracle↔reviewer(s) and reviewer↔reviewer (§4.4). Required to move from "single-author oracle" to any independence claim (`REPOSITORY_AUDIT.md` §3: "No claim of independent validation can be made").
* Sample size (rule of thumb, approximate): n≈100 labels yields a kappa 95 % CI of roughly ±0.1–0.15 for κ≈0.7–0.9 at 80 % prevalence; n≈200 halves that variance. Prevalence is skewed (81 % positive), so kappa is sensitive — report raw agreement, kappa and PABAK together; **oversample negatives** (all 106 negatives are cosmetic, so use the new strong negatives from §5).
* **Cost/feasibility:** reviewer time ~1–2 min per simple mutant, 5+ min for IF/PROC cases ⇒ ~4–10 h per reviewer for 100–200 items. Needs access to two qualified people (external partner, paid or volunteer). **Days to a couple of weeks once reviewers exist.** Reviewer availability: UNVERIFIED.

### 4.3 Execution on a real z/OS or emulator
| Option | What it gives | Limits | Feasibility |
|---|---|---|---|
| **Hercules + TK4-/TK5 (MVS 3.8j)** | Real JES2 + `COND=` evaluation, `IEFBR14`/`IDCAMS`/`IEBGENER`/`SORT`, real catalog semantics for utility-only jobs | MVS 3.8j is a 1980 dialect: `IF/THEN/ELSE`, `INCLUDE`, `JCLLIB`, `SET` are **not** present in its JCL (exact release that introduced them: UNVERIFIED from memory); no DB2/CICS; most dev subjects' programs (COBOL batch, DB2) cannot run. Free tooling; licensing status of the distributions **UNVERIFIED** | Days to build a harness for utility-only jobs; covers COND/order/dataset subset only |
| **IBM Z Development & Test Environment (ZD&T)** | Modern z/OS (IF/THEN/ELSE, PROC, symbolics) on x86 | Commercial IBM licence/entitlement; cost UNVERIFIED | Needs procurement ⇒ weeks, or a partner |
| **IBM Z Xplore / IBM Z trial / partner z/OS (via Zowe CLI)** | Real z/OS, job submission API (zosjobs) | Account/availability/time limits UNVERIFIED; programs available limited; Zowe is only a client | Short access windows; days if available |
| **Production z/OS at a partner (NDA)** | Real code + real behaviour | Legal/NDA; cannot publish data | External partner (weeks–months) |

*Return-code injection* (what the oracle models) would need explicit site-specific mechanism (e.g. an `IDCAMS` step with `SET MAXCC=n`); **not tested here (UNVERIFIED)**. Real execution can confirm or refute oracle labels for the executable subset only — a *calibration* sample, not the whole benchmark.

### 4.4 Differential labelling by two independent annotators with Cohen's kappa
* Two annotators label the same sample (blind to each other, to oracle labels, and to detector outputs), then adjudicate disagreements with a third reviewer; report κ (annotator↔annotator), κ (each↔oracle), and the confusion matrix of the oracle against the **adjudicated** label. Pre-register a threshold (e.g. oracle–adjudicated κ ≥ 0.8 is "substantial"; **threshold value is a proposal, not a field standard I verified**). Provide annotation guidelines + a calibration round on development items only (so held-out items stay unseen).
* If κ(annotators) < 0.6, the label definition (not RELIC) is the problem — that itself is a reportable result.
* **Feasibility:** needs two qualified annotators; same cost as §4.2 (it extends it). ~1–3 weeks including guideline writing.

## 5. Held-out evaluation protocol (pre-registration checklist)

Goal: a contamination-resistant, falsifiable evaluation. Nothing below has been run.

**Freeze (before the sealed set is opened)**
- [ ] Tag a commit that freezes detector (`src/legacy_contract/**`), oracle (`jcl_oracle/**`), mutator/negative-class generators (`relic_eval/**`), baselines, `requirements.lock`; record the full 40-char SHA and `sha256sum` of the working tree in the pre-registration file.
- [ ] After the freeze **only** infrastructure-neutral changes allowed (e.g. file-path adapters); any code change ⇒ the sealed set is burned for that version; record it and report it.
- [ ] Oracle fixed *before* detectors are tuned and tested only on development subjects (`REPOSITORY_AUDIT.md` §3: the oracle and fixes currently landed in one commit — do **not** repeat that).
- [ ] Document that oracle and mutator share `jcl_oracle.lexer` (common-mode risk); an independent lexer cross-check (e.g. `mapa`'s ANTLR grammar, MIT) is an optional mitigation — UNVERIFIED feasibility.

**Sealed set construction**
- [ ] Candidate pool = repos meeting §6 criteria; **split by repository, never by file**. With ~4–7 eligible repos, assign repos to sealed vs exploratory using a pre-announced random seed (e.g. the freeze SHA) to avoid hand picking; record the seed and the assignment *before* viewing contents.
- [ ] Record the pool's repo URL + pinned SHA + `git ls-tree` sha256 per repo; keep the manifest (hashes only) public; keep the downloaded content untouched until freeze. Disclose "screened by aggregate" status (§3).
- [ ] De-duplicate against the dev subjects and across the pool (SHA-256 of normalised text; near-duplicate threshold pre-set) — the dev datasets lack pinned commits, so compare by file hash.
- [ ] Evaluate the sealed set once per frozen version; no re-runs after peeking at failures (any re-run is reported as a deviation).

**Mutants and negative classes (all generated by frozen code, labelled by frozen oracle, then spot-checked by §4.2/4.4)**
- [ ] Keep the 10 existing operators; additionally add *behaviour-preserving* negatives so a text rule cannot separate classes:
  - **Benign reorders:** swap two adjacent steps with no shared dataset and no `COND=`/`IF` referencing either (oracle must say EQUIVALENT; need a *positive-control* check that the same swap with a shared dataset is DIFFERENT).
  - **Symbolic renames:** consistent step-name rename including every `COND=(…,stepname)`/`IF stepname.RC` reference; consistent DSN rename on producer and consumer; renaming a `SET`/`&SYM` and all uses.
  - **PROC-parameter changes:** change an irrelevant symbolic/override (`REGION`, `SPACE`, `PARM` text) vs a contract-relevant one (dataset-name symbol, `COND` override) — requires PROC support in the oracle (currently "noted, not parsed", `REPOSITORY_AUDIT.md` §5; if the oracle cannot judge them they must be reported as `OUT_OF_SCOPE`, not silently dropped).
  - **Whitespace/continuation reformatting:** re-wrap continuation lines, change column alignment, split/join parameter lists, change comment/sequence-number columns 73–80.
  - **Positive extensions:** COND *strengthening* (the missing direction), `REMOVE_IF_GUARD` once IF is parsed (0 evaluable today).
- [ ] Report the class mix (target ≥ 40 % negatives with ≥ 4 negative sub-classes, each with ≥ 30 mutants — *proposed sizes; adjust to what the pool can supply*).

**Baselines (all frozen with RELIC)**
- [ ] Existing: structural A, complexity B, text-change reference, `textdiff_ignore_job_parameters`, LLM C/D (only with a single documented model, invalid-output retry policy; otherwise omit — see `EVALUATION_SUMMARY.md` §4).
- [ ] **New normalised-text-diff baseline** (pre-specify exactly): strip comments; uppercase outside quotes; collapse whitespace and continuation; drop columns 73–80; drop JOB-card parameters; **canonicalise symbolic/step/DD names by first-occurrence order (alpha-renaming)**; compare statement sequence. Also a *sorted-statement* variant (order-insensitive) to show what an order rule adds. If the baseline matches RELIC on the strong negatives, the claim "RELIC > trivial rule" is **rejected**.

**Pre-registered hypotheses (proposals for the research lead to fix, with margins, before opening)**
- [ ] H1: RELIC specificity on the strong-negative classes ≥ normalised-text-diff specificity (one-sided, non-inferiority margin δ=0.05 pre-set).
- [ ] H2: RELIC recall on contract-breaking classes (ordering, dataset, COND) ≥ 0.85 pooled and ≥ 0.70 on the weakest repo (**thresholds are proposals; no data-driven basis**).
- [ ] H3: RELIC F1 on the sealed set does **not** exceed the best trivial baseline by a non-zero margin (null) — report whichever way it goes.
- [ ] H4: oracle↔adjudicated-human κ ≥ 0.8 on the §4.4 sample (validity of ground truth).

**Analysis plan (fix before unsealing)**
- [ ] Primary metrics: TP/FP/FN/TN, precision, recall, F1, specificity, **MCC**, balanced accuracy, per repo and per negative class; coverage/accounting statuses as in `docs/evaluation/BENCHMARK.md` §4 (including `OUT_OF_SCOPE` rate per repo — a high rate is a result).
- [ ] Uncertainty: file-level cluster bootstrap is inadequate with <10 repos; use **repo-level** leave-one-repo-out estimates and report each repo separately; use Wilson intervals only per class; no pooled p-values claiming repo-level generalisation with fewer than ~10 repos.
- [ ] Multiple-comparison control: a small, listed set of confirmatory tests (H1–H4); everything else exploratory and labelled so.
- [ ] Report negative results (H failures, repos with 0 evaluable mutants, parse failures, undetermined labels) in full; publish the registered plan, frozen SHAs and raw per-mutant records.
- [ ] Deviations log (any code change, any repo dropped after viewing, any label correction) appended and reported.

## 6. Inclusion / exclusion criteria

**Include** a repository/file when all hold:
1. Public, reachable by HTTPS at a pinned commit SHA; commit recorded.
2. License file present and readable, permitting redistribution/analysis (MIT, Apache-2.0, EPL-2.0, BSD, CC-BY, CC0, public-domain *with a verifiable statement*).
3. Not one of `carddemo`, `omp_course`, `genapp`, nor a fork/copy of them (file-hash de-dup), nor derived from the RELIC repo.
4. Contains JCL files with a JOB statement; evaluation units follow `relic_eval/subjects.py` (≥1 JOB, `.jcl`; extend to `.proc/.prc/.cntl/.job` only with a pre-announced rule).
5. Evaluable under existing operators: ≥ 2 EXEC steps in the file for ordering/splitting; at least one dataset produce/consume pair, or `COND=`, for the respective operators.
6. Authored by people independent of RELIC authors.

**Exclude** when any hold: no license or unclear/non-redistributable provenance (`MVS-sysgen/sysgen` until resolved; vendor demo licences that restrict use — e.g. the "Rocket/Micro Focus BankDemo" noted in `datasets/genapp/PROVENANCE.md`); Stack Overflow / forum snippets (licence); proprietary/NDA JCL in the public set (only in a separate partner track); files that are mostly inline data (e.g. `yetacp`/`sysgen` jobs with tens of thousands of data lines — exclude or cap lines so the oracle isn't dominated by data); generator/template output with unresolved `<PLACEHOLDER>` tokens beyond a stated cap; machine-translated or LLM-generated JCL (cannot verify here); files the lexer cannot parse; parser-stress fixtures (e.g. `mapa/jcl/testdata`) from the **behavioural** set (retain them for a separate *robustness/crash* track).

## 7. Feasibility timeline

| Horizon | What is realistic (given what I verified) | Not realistic |
|---|---|---|
| **Days (≈2–5)** | Pin the 4 verified-licence repos (rows 1, 2, 6, 7); write subject adapters; freeze and tag; add the normalised-text-diff baseline and the four negative-class generators; run the mutation benchmark once on the sealed pool; leave-one-repo-out reporting; confirm licenses for sysgen by contacting maintainers (response time UNVERIFIED) | Any independent-human claim |
| **Weeks (≈2–6)** | Independent relabelling / κ study (§4.2, §4.4) with 2 recruited annotators; git-history mining and labelling (§4.1) on `sysgen`/`zowe-install-packaging`/`zopeneditor-sample`; Hercules/TK4- harness for the utility-only/`COND` subset (§4.3); extend the oracle/detector to `IF/THEN/ELSE`, `PROC`, `INCLUDE` (large, and must happen **before** the freeze) | Statistical claims of generalisation across repositories (too few repos) |
| **Requires external partners** | Real z/OS execution (ZD&T licence, partner LPAR, IBM Z Xplore-type access — availability/cost UNVERIFIED); production JCL under NDA; qualified mainframe annotators; a broader code-search over GitHub (authenticated API) to enlarge the pool | — |

## 8. Risks

* **Tiny pool / few clusters:** 4 verified-licence repos (7 including tiny ones); repo-level inference is weak; one repo (`sysgen`, `mapa`) can dominate by file count. Mitigate with per-repo reporting and a cap on files/repo.
* **Realism:** `mapa` testdata is synthetic; `sysgen`/`yetacp` are MVS 3.8-era system jobs with heavy inline data; Zowe fixtures are test artefacts. None is representative of enterprise batch (common ground with the finding in `docs/archive/.../secondary_system_selection.md` that enterprise JCL is proprietary).
* **Oracle limitations carry over:** the oracle has not been validated against z/OS or by an independent expert; PROC/INCLUDE/IF not parsed; external repos lack COBOL sources, so `ORACLE_UNDETERMINED`/`OUT_OF_SCOPE` rates may be high — a high rate shrinks the evaluable set.
* **Common-mode lexer risk:** oracle and mutator share `jcl_oracle.lexer`.
* **Screened-by-aggregate:** this report exposed counts and two file fragments; strictest "blind" claim not available for the listed repos.
* **Search incompleteness:** only repo search was used (code search unauthenticated-unavailable); GitHub API rate-limited; candidate list is a lower bound. Several license `/license` API confirmations were not completed (read `LICENSE` text instead).
* **Licensing:** the sysgen lineage (Jay Moseley / IBM MVS 3.8j) licence is unverified; the `zopeneditor-sample` file headers ("LICENSED MATERIALS – PROPERTY OF IBM") conflict visually with the repo's Apache-2.0 LICENSE; both need legal reading before redistribution of derived files (analysis only, no redistribution, is the safer plan).
* **LLM contamination:** applies only to LLM baselines; a non-LLM detector is not affected, but any prompt tuning on the pool would be.
* **Time/priors:** all numeric thresholds (§5 H2, κ ≥ 0.8, ≥30 mutants/class) are proposals, not derived from data; the research lead must fix them before opening the sealed set.
* **Date caveat:** repo "HEAD" and "last push" dates come from GitHub's responses (2026); I did not independently check system clock vs. GitHub clock.
