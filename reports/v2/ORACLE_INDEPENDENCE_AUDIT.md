# Oracle independence and ground-truth validity audit (AGENT 2)

Repo `RELIC`, branch `research/relic-v2-final-sprint`. Read-only investigation: nothing outside
`reports/v2/ORACLE_INDEPENDENCE_AUDIT.md`, `reports/v2/INDEPENDENT_REVIEW_PACKAGE.md` and
`reports/v2/review_package/**` was created or edited, and no state-changing git command was run.
All numbers below were produced by scripts in `reports/v2/review_package/experiments/` (and by inline
read-only queries, listed in §7) against `results/final/raw/evaluation_records.jsonl`
(656 candidate mutants; 566 EVALUABLE = 460 oracle-DIFFERENT + 106 oracle-EQUIVALENT; 121 job files in 3 subjects).

**Headline.** The oracle is *code-independent* of RELIC (no import in either direction) but it is **not
independent of the mutation generator, of subject selection, or of the author**; it has not been compared with
real z/OS execution or with any human reviewer. Independent review is **PENDING** - nothing in this audit or in
the review package is a reviewer rating, and none was fabricated.

Severity: **High** = can change a headline conclusion or voids an independence claim; **Medium** = biases a
sub-result / limits generalisation; **Low** = documentation or hygiene.

---

## 1. Findings table

| ID | Sev. | Finding | Evidence (file:line / measurement) |
|---|---|---|---|
| F-01 | **High** | Oracle, mutation generator, subject selection and PROC library share one lexer/model. A lexer bug moves mutation sites *and* the labels of the resulting mutants identically, and the only mutant-validity gate (`INVALID`) is computed by the same lexer. | `relic_eval/mutate.py:39-40` imports `jcl_oracle.lexer.{Statement,lex,parse_operands,split_top,unparen}` and `jcl_oracle.model.substitute`; `relic_eval/subjects.py:18-19` imports `lex`, `ProcLibrary`, used at `:50` (which files are evaluation units), `:62-72` (PROC library), `:74-83` (COBOL sources handed to the oracle); `relic_eval/pipeline.py:131-133` labels with `compare_versions(original, mu.text, subject.proclib, subject.cobol_sources)`; `jcl_oracle/judge.py:150-151` returns `INVALID` only if `m2.errors` (IF/ELSE/ENDIF structure errors only: `model.py:269,278,319,329,385`). Also shared with contract-recovery ground truth: `relic_eval/contract_recovery.py:27`, `v2_eval.py:37`, `report.py:271-273`. **Mitigation measured (§3.3):** RELIC's *independent* tokenizer agrees with the shared lexer on the EXEC-name sequence of all 630 in-/out-of-scope mutants and on the expected structural effect of 607/607 checked mutants. |
| F-02 | **High** | Single author, same commit: oracle, mutator, oracle tests **and** the parser "spec-conformance" fixes that define RELIC v1.1 landed together; no practitioner review, no real-execution comparison. | `git log --format='%h %an %ad %s' -- jcl_oracle relic_eval/mutate.py src/legacy_contract/parsers/jcl_parser.py`: `1cbcf06 Manas Sakthivel 2026-10-04` adds all of `jcl_oracle/*` (2,090 lines), `relic_eval/mutate.py`, `tests/oracle/*` and edits `jcl_parser.py` (+91) in one commit; `997611d` (2026-11-20, same author) adds D-001..D-004; `db51c84` (2026-08-17) initial release; `git shortlog -sn` = 28 commits, 1 author. `docs/evaluation/ORACLE_SPECIFICATION.md:102-105,122-124` states the same limits. |
| F-03 | **High** | Three fault operators select sites with the *same DISP producer/consumer abstraction* the oracle uses to decide the label, so their positives follow by construction (60 positives = 13.0 % of 460). | Selection: `mutate.py:145-150,246-252` (status NEW/MOD => output, else input; omitted DISP => NEW). Label: `simulate.py:409-425` (OLD/SHR of a non-existent dataset, or NEW of an existing one => JCL error ends the job) with existence from `simulate.py:566-600` ("first access in the **original** creates it => absent initially"). DELETE_PRODUCER 33/33, MOVE_CONSUMER 14/14, RENAME_OUTPUT 13/13 evaluable mutants are DIFFERENT, all already in the no-failure baseline scenario (`mutant_crosscheck.py`). A wrong DISP default or "dataset pre-exists" assumption would be wrong for both site chooser and judge. |
| F-04 | **High** | `SPLIT_JOB` supplies 166/460 positives (36.1 %). Two oracle design choices make *every* split positive: (a) the termination observable embeds job names and job count; (b) split jobs may run in any serial order and a failure does not propagate between jobs. A human may call a split of independent steps behaviour-preserving under normal completion. | `simulate.py:310,316` (`terms.append((job.name,)+ctx.term_reason)`; `termination=tuple(sorted(terms))`): `(('CARDFILE','OK'),)` vs `(('CARDFIL2','OK'),('CARDFILE','OK'))` differs already in the *baseline* scenario (record `carddemo/app/jcl/CARDFILE.jcl/SPLIT_JOB/6`); `simulate.py:285-293` all serial orders (<= 4 jobs). Recomputed with job names and count removed from the termination observable (`split_job_sensitivity.py`): SPLIT_JOB stays 166/166 DIFFERENT, but only **72** differ at baseline, **21** need an injected RC, **73** need an abend. No split is EQUIVALENT, so the operator never tests whether the oracle can say "equivalent". |
| F-05 | **High** | The positive class is "differs under some hypothetical single fault", not "differs in the observed run": 159/460 positives (34.6 %) differ **only** under failure injection; 253/460 (55.0 %) once the job-name artefact of F-04 is removed. The injection domain is unconstrained (any step - including IEFBR14 - may end with any RC in {4,8,12,16}∪{c-1,c,c+1} or abend). | `judge.py:34-35,63-80` (scenario generator), `simulate.py:535-539` (injection applied to any step). Tiers of the 460 positives (official oracle, `mutant_crosscheck.py`): **T0 differs with no injection: 301**; **T1 injected non-abend RC only: 78**; **T2 abend only: 81** (= **38** whose `no_abend` label is EQUIVALENT + 43 whose `no_abend` label is UNDETERMINED; fields `oracle_result` / `oracle_result_no_abend`). Operators: all 81 T2 and 25 of the 78 T1 are SWAP_ADJACENT_STEPS; REMOVE_COND 33/34 and ALTER_COND 20/34 are T1. RELIC v1.0 recall by tier: T0 262/301 = 0.870, T1 45/78 = 0.577, T2 73/81 = 0.901. |
| F-06 | **High** | The negative class cannot test equivalence recognition: 104 of the 106 EQUIVALENT labels are comment insertions (65) or MSGCLASS changes (39), equivalent by definition; the other 2 are COND edits on the only step of a one-step job (`TXT2PDF1`, U-01). No reorder, split, delete, rename or move is ever EQUIVALENT in the primary scenario set. The reported specificity (RELIC 1.000 on 106; `textdiff` 0.49) therefore measures "ignores comments/MSGCLASS", not "recognises benign changes". | Records: `INSERT_COMMENT` 65, `CHANGE_MSGCLASS` 39, `ALTER_COND_THRESHOLD` 1, `REMOVE_COND` 1 (all EQUIVALENT). Benign swaps appear only under `no_abend` (38 EQUIVALENT) and are excluded from the primary label (`ORACLE_SPECIFICATION.md:117-121`). |
| F-07 | **Medium** | Oracle semantics are *unverified against IBM documentation or real z/OS* in this sprint (the IBM documentation index available to this agent has no z/OS JCL/MVS library - `list_ibm_doc_libraries`). Several unverified rules decide specific labels (§5). | `simulate.py:4-25` header ("semantics follow the IBM z/OS MVS JCL Reference" as read by the author); unit tests `tests/oracle/test_oracle_semantics.py:104` (first-step COND), `:154` (NEW => DELETE), `:141` (JCL error) are hand-derived by the same author. |
| F-08 | **Medium** | Opaque programs: 120 of 423 expanded steps (28.4 %) in 66 of 121 files (54.5 %) are opaque; 298/566 evaluable mutants (52.7 %) and 253/460 positives are in files with >=1 opaque step. For opaque steps the oracle's I/O model is the DD-disposition fallback (NEW/MOD write, OLD read+write, SHR read) - the same abstraction RELIC's parser uses (`jcl_parser.py:523-544`). The `UNDETERMINED` safeguard never fired in the primary run (0/656; 43 positives would be UNDETERMINED under `no_abend`). | `programs.py:311-328,331-375,378-386`; `judge.py:120-133,174-181`. Step counts by opaque reason: program source unavailable 37, TSO batch IKJEFT01/1A/1B 32, PROC `DFHLS2WS` unavailable 18, SDSF 10, CICS CSD utility 6, IMS `DFSRRC00` 5, IDCAMS SYSIN from dataset 4, referback program 3, DB2 utility 2, FTP 1, IEBCOPY 1, PROC `EYUJXBTP` 1. |
| F-09 | **Medium** | Measured oracle-lexer vs RELIC-parser disagreement (§3): RELIC never sees `stepname.ddname` DD statements (81 statements in 40 files) nor JOB cards with `<PLACEHOLDER>` names (2). On every statement both see, operation, name and operand field agree (1436/1436) once RELIC runs in default/V2 mode; v1.0 as released agrees on 1201/1436 operand fields (continuation rule, columns 73-80). The shared lexer is therefore *consistent with a second implementation* on this corpus, but the 40 files that exercise PROC DD overrides have no independent cross-check of the oracle's override semantics. | `jcl_parser.py:100-101` (`STATEMENT_PATTERN` name group `[A-Z@#$][A-Z0-9@#$]{0,7}` cannot contain `.`); §3 tables. |
| F-10 | **Medium** | Correlated *independently coded* assumptions (same reading of the manual, same author): omitted DISP status => NEW; MOD => producer; COND without step name tests **all** previous steps; step identity by name; unnamed DD = concatenation. A coincident misreading passes every cross-check available in the repo (§4). | `model.py:230` / `mutate.py:145-150` / `jcl_parser.py:486` (NEW default); `simulate.py:362-365` / `extractor.py:279-321` (COND all previous); `model.py:372-375` / `mutate.py:243-258` (unnamed DD). |
| F-11 | **Medium** | COND/IF semantics are exercised on a thin slice of the corpus: `COND=` on EXEC in 15/121 files; with step name 3; **no** `COND=EVEN/ONLY`, **no** multi-test `COND=((…),(…))`, **no** `COND.procstep`, **no** job-level `COND`, **no** `INCLUDE`; IF/THEN/ELSE in 22 files but `REMOVE_IF_GUARD` has 0 evaluable mutants. Those oracle paths are validated only by the author's unit tests. | `feature_census.py`; `simulate.py:93-119,163-260`. Unknown IF items evaluate to False (`simulate.py:258-260`); unparsable COND groups are silently skipped (`simulate.py:115-118`). |
| F-12 | **Medium** | Step identity across versions is by name; same-named steps by a content hash that excludes COND; step renames are never generated. 7 files have duplicate step names (64 positives). A mispairing flips a label either way. | `model.py:491-521`; `ORACLE_SPECIFICATION.md:110-113,125-131` (13 GenApp swaps were mislabelled EQUIVALENT before the fix). |
| F-13 | **Low** | The independence test checks only oracle -> RELIC imports; it does not test mutator <-> oracle coupling or shared assumptions. Grep confirms no `legacy_contract`/`baselines` import in `jcl_oracle/*` (only a docstring, `jcl_oracle/__init__.py:7`) and no `jcl_oracle` import in `src/` (comments only: `jcl_parser.py:153`, `mutations/engine.py:7`); `relic_eval/detectors.py:28-35` imports RELIC only. | `tests/oracle/test_oracle_independence.py:8-25`. |
| F-14 | **Low** | Final-catalog observable ignores CATLG/KEEP/UNCATLG distinctions and keeps a passed permanent dataset in the final catalog; GDG generations `X(+1)`/`X(0)` are opaque keys. `DISP` PASS appears in 7 files, GDG in 10, `&&` in 3. Effect on labels not measured. | `simulate.py:545-554`; `model.py:197-198`; `simulate.py:37-48`. |
| F-15 | Info | Independent review: **PENDING**. A 60-case blind package, rubric, adjudication procedure and agreement script (self-tested on synthetic data only) are in `reports/v2/review_package/`. | `INDEPENDENT_REVIEW_PACKAGE.md`. |

---

## 2. Feature-by-feature assumption table

"Shared" = one code object imported by several components. "Independent same assumption" = coded separately
in two or more components with the same assumption (correlated failure mode). Prevalence = files of the
121 evaluation units (`feature_census.py`). Line numbers are approximate to the quoted block.

| JCL feature (files) | Oracle `jcl_oracle` | RELIC parser/extractor `src/legacy_contract` | Mutator `relic_eval/mutate.py` | Shared code | Independent same assumption |
|---|---|---|---|---|---|
| **Continuation** (80) | operand ends with `,`; next `//` line needs a blank in col 3 and >=1 leading blank (any depth; IBM: cols 4-16): `lexer.py:155-174`; cols 1-71 `lexer.py:26,52`; comment lines interleaved | default `_merge_continuations_ibm` `jcl_parser.py:263-298`, `IBM_CONTINUATION_PATTERN` `^//\s+\S` `:111`; legacy v1.0 needs >=15 blanks `:108,227-242` (merged 0 CardDemo continuations, `:105-107`) | uses oracle `lex()` spans `mutate.py:162`; edits `lines[li][:71]` `:273-281` | **yes** (lexer): oracle + mutator | RELIC default = oracle rule (written in the same commit) |
| **DISP defaults / forms** (all) | omitted DISP => NEW; `(,CATLG)` => NEW; normal disp default DELETE if NEW else KEEP: `model.py:187-194,230`, `simulate.py:548` | v1.x omitted DISP => `OLD` (consumer) `jcl_parser.py:524`; v1.x regex reads `(,CATLG)` as `(`; V2 parses lists, omitted => NEW `:120,481-487` | `_dsn_of` default NEW `mutate.py:145-150` | `substitute` | omitted => NEW in oracle, mutator, RELIC V2; **disagreement** with RELIC v1.x (0 corpus DDs have DSN without DISP; 5 files have omitted status) |
| **DSN / DSNAME** (DSNAME 2) | `kw.get("DSN", kw.get("DSNAME"))` `model.py:221`; `*.` referback, `NULLFILE` `:224-227` | v1.x `DSN=([^\s,]+)` misses DSNAME `jcl_parser.py:474`; V2 `DSN(?:AME)?=` `:117,472` | same key lookup `mutate.py:144`; rename regex `DSN(?:AME)?=` `:374` | `parse_operands` (oracle+mutator) | - |
| **COND forms** (15; with step 3; EVEN/ONLY 0; multi-test 0) | `parse_cond` `(c,op[,step])`, lists, EVEN/ONLY `simulate.py:93-119`; step-less test applies to every earlier executed step `:362-365`; first-step COND ignored (`test_oracle_semantics.py:104`) | `COND_PATTERN_BALANCED` `jcl_parser.py:114,454-457`; extractor `COND_PATTERN` needs `\d+` `extractor.py:259-262`; step-less => all preceding (v1.1) `:317-321`, previous only (v1.0) `:318-319`; EVEN/ONLY dropped (D-009) | `_COND_RE` `mutate.py:284`; REMOVE_COND / ALTER first number x2 `:411-471` | none | step-less = all previous (oracle vs RELIC v1.1); COND syntax coded 3 times (oracle, extractor, mutator) |
| **Step names** (unnamed steps: 0) | as written, unnamed `#i`; identity name or name~hash `model.py:491-521` | name or `STEP_nnn`; v1.x entity id = hash(artifact, type, name) so duplicates merge; V2 `NAME#n` `jcl_parser.py:385-394` | block name or `#i` `mutate.py:238` | `lex` | name-based identity in all three |
| **DD concatenation** (17) | unnamed DD extends previous DD's `refs` `model.py:372-375` | each unnamed DD becomes `ANON_DD` entity `jcl_parser.py:494` | unnamed DD stays in block; only its DSN `mutate.py:243-258` | `lex` | - |
| **In-stream data** (77; DLM 1) | `DD *` ends at `/*` or any `//`; `DD DATA` at delimiter `lexer.py:96-107,177-195` | non-`//` lines go to `unparsed_lines`; a `//` data line would be parsed as a statement `jcl_parser.py:192-203` | via `lex` (`st.data`, `end_line`) `mutate.py:253-257` | **yes** | IDCAMS SYSIN parsed twice independently: `programs._idcams_commands` vs `mutate._idcams_names` |
| **PROC / IF / INCLUDE** (in-stream PROC 2; EXEC proc 51; IF 22; INCLUDE 0) | in-stream + cataloged PROCs expanded, overrides merged, symbols, IF evaluated: `model.py:287-299,392-487`, `simulate.py:163-260`; unknown PROC => opaque step | `PROC/PEND/IF/ENDIF/ELSE/SET/INCLUDE` ignored `jcl_parser.py:339-340`; PROC steps only `JCL_PROC` call targets (D-006) | IF only for REMOVE_IF_GUARD (OUT_OF_SCOPE) `mutate.py:493-505`; proc bodies skipped `:188-195` | `lex` | - |
| **Symbolic parameters** (`&NAME` 118; SET 9) | `substitute` (<= 4 passes), SET, PROC defaults/overrides `model.py:26-41,304-308,409-422`; unknown left as text | none (DSN compared as raw text) | `substitute` (same function) `mutate.py:140-150` | **yes** (`substitute`) | - |
| **MOD,DELETE** (8) | MOD creates if absent; DELETE applied at step end `simulate.py:418-421,548-554` | v1.x MOD => producer; V2 D-004 `(MOD,DELETE)` neither `jcl_parser.py:525-527` | MOD => output `mutate.py:248` | - | MOD => producer (mutator, RELIC v1.x). Two D-004 positives are DIFFERENT only through the final catalog |
| **Temp datasets `&&`** (3) | never pre-exist; removed at job end `simulate.py:308-309,412` | raw name `&&X` | `&&X` renamed by `+MG` `mutate.py:354-359,380` | - | - |
| **GDG (+1)/(0)** (10) | separate keys; `_GDG_RE` `simulate.py:38`, member-vs-GDG split `:43-48` | raw DSN string | rename keeps suffix `mutate.py:352-362,377-381` | - | no generation resolution anywhere |
| **Return-code semantics** | endogenous IDCAMS RCs (DELETE missing 8, DEFINE existing 12, SET MAXCC/LASTCC) `simulate.py:475-516`; injected RC/abend scenarios `judge.py:63-80`; IF `RC` = max RC so far `simulate.py:163-260` | contracts from COND text only | none | - | - |
| **Program models** (IDCAMS 27, IEFBR14 12, IEBGENER 8, SORT 5, IKJEFT 12) | IEFBR14, IEBGENER, SORT, IEBCOPY, IDCAMS, IGYCRCTL, IEWL modelled; COBOL by `SELECT/OPEN`; ~16 named programs + unknown programs opaque `programs.py:311-375` | `CALLS` program entity only | none | COBOL index `subjects.py:74-83` | opaque fallback == RELIC DD-disposition model (F-08) |

---

## 3. Experiments: oracle lexer vs RELIC parser (no code modified)

Scripts `experiments/lexer_disagreement.py`, `feature_census.py`, `mutant_crosscheck.py`,
`split_job_sensitivity.py`; raw outputs `experiments/*_results.json`. Unit of comparison = JOB/EXEC/DD
statement keyed by its first physical line on the **121** evaluation-unit files.

### 3.1 Statement-level agreement

| RELIC mode | Statements seen by either | Seen by both | Only oracle | Only RELIC | **Anchored agreement** | Operand field equal (both) | EXEC count equal per file | DD count equal per file | DSN set equal per file | DD role agree (398 DSN DDs) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `relic_v1_0` (legacy; primary detector) | 1519 | 1436 | 83 | 0 | **94.5 %** | 83.6 % (1201/1436) | 121/121 | 81/121 (66.9 %) | 65/121 (53.7 %) | 262/398 (65.8 %) |
| `relic_v1_1` (default) | 1519 | 1436 | 83 | 0 | **94.5 %** | **100 %** (1436/1436) | 121/121 | 81/121 | 90/121 (74.4 %) | 368/398 (92.5 %) |
| `relic_v2` (`v2_fixes`) | 1519 | 1436 | 83 | 0 | **94.5 %** | 100 % | 121/121 | 81/121 | 92/121 (76.0 %) | 371/398 (93.2 %) |

Operation code and name field agree on all 1436 common statements in every mode.

* **Headline agreement: 94.5 % (1436/1519) of JOB/EXEC/DD statements are identically recognised by the oracle lexer and by RELIC's parser; RELIC recognises no statement the oracle lexer misses (0); EXEC/step counts agree in 121/121 files.**
* The 83 oracle-only statements are fully explained: **81 `stepname.ddname` DD overrides in 40 files**
  (`PRC001.FILEIN`, `COBOL.SYSIN`, `LKED.SYSLMOD`, …) and **2 JOB cards named `<CMASAPPL>` / `<WUIAPPL>`** (GenApp
  templates). The 40 files whose DD count differs are exactly the 40 files with such overrides.
* v1.0's lower operand agreement is the documented continuation / columns 73-80 defect; v1.1/V2 fix it.
* Role disagreements on DSN DDs: v1.1 has 6 (omitted DISP status such as `DISP=(,CATLG,…)` / `(,PASS)`, D-002; 0 in V2).
  24 DDs (v1.1) / 27 (V2) get no PRODUCES/CONSUMES although the oracle sees a DSN: 5 precede the first step (JOBLIB),
  5 contain a symbolic DSN, 14 other (e.g. repeated `IMS.SDFSRESL` DDs in one step - probably relation
  de-duplication; **not root-caused**); the 3 extra in V2 are `(MOD,DELETE)` by design (D-004).
* RELIC STEP entities equal the EXEC count in 114/121 files (v1.x; duplicate names collapse, D-001) and 121/121 in V2.

### 3.2 Corpus feature census (files out of 121)

continuation 80 · in-stream data 77 · `&NAME` 118 · `stepname.ddname` overrides 40 · DD DUMMY/NULLFILE 39 · lowercase in
statements 33 · IF/THEN 22 (ELSE 22) · JCLLIB 17 · unnamed concatenation DDs 17 · COND on EXEC 15 · IKJEFT01/1B 12 · IEFBR14 12 ·
GDG 10 · SET 9 · MOD,DELETE 8 · text in cols 73-80 8 · duplicate step names 7 · DISP PASS 7 · omitted DISP status 5 ·
OLD,DELETE 4 · `&&` temps 3 · COND with step name 3 · in-stream PROC 2 · DSNAME 2 · DLM 1.
**Zero:** COND EVEN/ONLY, multi-test COND, `COND.procstep`, job COND, INCLUDE, DD with DSN but no DISP, unnamed steps,
multiple JOB cards, unknown operation codes (also over the 133 JCL/PROC files), tabs, non-blank column 72 on `//` lines.

### 3.3 Cross-check on mutants (630 EVALUABLE + OUT_OF_SCOPE mutants with text)

* Ordered EXEC-name sequence of the mutant, oracle lexer vs RELIC tokens: **630/630 equal**; JOB-card count 630/630; DD count 524/630 (all differences = `stepname.ddname`).
* Expected structural effect checked **with RELIC's tokens only** (swap = same multiset, two positions changed; delete = n-1 steps; split = +1 JOB card; comment/MSGCLASS/COND/rename/move = same step count and DD count): **607/607 pass**.
  Positive evidence that the shared lexer did not mis-locate edits on this corpus. It cannot see errors in text RELIC ignores (PROC DD overrides, IDCAMS SYSIN, in-stream data, symbolic substitution).

### 3.4 What a shared lexer bug would hide (and what was observed)

| Hypothetical lexer defect | Why shared code hides it | Observed |
|---|---|---|
| Continuation mis-merge / acceptance of any indent (`lexer.py:168`) | mutator cuts/moves/deletes at lexer spans; oracle re-lexes the damaged text with the same rule, so a non-JCL mutant gets a simulation label | RELIC agrees on all 1436 common statements and 630/630 mutant EXEC sequences; **not covered:** the 81 override DDs |
| In-stream data end rule (`lexer.py:186`: any `//` ends `DD *`) | swallowed/lost statements change both site list and label | EXEC counts equal 121/121; DLM used once; IDCAMS SYSIN content only checked by the author's two regexes |
| No support for text continued via column 72 (`STMT_COLS`, `lexer.py:26,52`) | truncated identically everywhere | 0 non-blank column-72 characters on `//` lines; 5 `//` lines carry non-numeric text in cols 73-80 (4 are `JOBnnnnn` tags) |
| Name/operation split on whitespace (`lexer.py _split_fields`) | accepts placeholders | 2 JOB cards (`<CMASAPPL>`, `<WUIAPPL>`) seen by oracle, not by RELIC |
| Unknown operation codes silently ignored (`model.py:377-381`) | OUTPUT/XMIT/CNTL carry no oracle semantics | 0 unknown ops in corpus |
| `substitute` bounded to 4 passes, `&&` untouched (`model.py:26-41`) | identical wrong DSN in mutator `_dsn_of` and oracle `make_dd` | 118/121 files contain `&NAME`; RELIC does not substitute, so no cross-check |

---

## 4. Correlated failure modes

1. **Lexer span / continuation bug** (F-01) - independent check only for the 94.5 % of statements RELIC parses.
2. **DISP abstraction** (F-03, F-10): NEW/MOD => producer, OLD/SHR => consumer coded in `mutate.py:246-252`, `programs.py:378-386`, `jcl_parser.py:523-544`. The 60 DELETE/MOVE/RENAME positives and every opaque-step I/O model rest on it.
3. **Initial-catalog rule** (`simulate.py:566-600`) makes producer removal and consumer-before-producer JCL errors by construction; never compared with a real catalog.
4. **COND/RC semantics read once** (first-step COND ignored, step-less test = all previously executed steps, bypassed steps not tested) - oracle `simulate.py:349-366`, RELIC v1.1 `extractor.py:279-321`, both from the same reading in commit `1cbcf06`. Affects every REMOVE_COND/ALTER_COND label and both EQUIVALENT COND labels (U-01).
5. **Scenario design vs operator design**: values `c-1,c,c+1` for every COND/IF constant of either version (`judge.py:69-73`) are what is needed to detect ALTER_COND_THRESHOLD (code x2) and any step may take any RC (`simulate.py:535-539`); ALTER_COND positives (34/35) are close to certain whenever the guarded step is not first.
6. **Reorder operators + abend flush** (`simulate.py:351-352`): after an abend later steps are flushed unless EVEN/ONLY, so *any* reorder is observable; 81 positives exist only because of this rule.
7. **Step identity by name** (oracle `model.py:491-521`, mutator `Block.name`, RELIC D-001): 7 duplicate-name files are the known weak spot (RELIC recall 0.391 -> 0.766, DEFECT_REGISTER D-001).
8. **Author dependence**: one author wrote oracle, mutator, parser fixes, tests and the analysis; there is no second reader of the IBM manual. This is the largest correlated cause and cannot be tested without people.

### 4b. Oracle limitations (consolidated)

* **Opaque programs:** 120/423 steps (28.4 %), 66/121 files; DISP fallback is a guess; PROCs `DFHLS2WS` (18 steps) and `EYUJXBTP` unavailable.
* **Unknown semantics:** DB2/CICS/IMS/MQ side effects, ICETOOL operators, IDCAMS commands beyond the listed set, dynamic allocation, VSAM catalog internals, SMS/space/volume errors, JES scheduling, restart, concurrent jobs (serial orders only, <= 4 jobs; > 4 jobs use document order, `simulate.py:289-293`).
* **Scenario set:** single fault only; RC domain {4,8,12,16}∪{c±1}; no allocation-failure injection; no operator cancel/time/region abends; abend may hit any step incl. IEFBR14.
* **Failure-injection-only positives:** 38 mutants are DIFFERENT only through abend scenarios (EQUIVALENT under `no_abend`) and 43 more become UNDETERMINED under `no_abend` (an opaque step moved) - 81 abend-only, all SWAP_ADJACENT_STEPS (GenApp 65, CardDemo 14, OMP 2). With 78 injected-RC-only positives: 159 (34.6 %).
* **Categories used:** execution 460/460 positives, dataflow 402, final_catalog 324, termination 268, job_orders 65. Positives whose *only* category is `execution`: SWAP 12, REMOVE_COND 5, ALTER_COND 4 (21). Never observed: output content, SYSOUT, messages, abend codes, step timing.
* **Mutant coverage:** 8 fault operators + 2 refactorings, exhaustively enumerated; 64 OUT_OF_SCOPE and 26 INVALID (23 in the OMP course) excluded; `REMOVE_IF_GUARD` 0 evaluable; no operator edits PROC/INCLUDE/symbolics/DISP/PARM/REGION; OMP has only 35 evaluable mutants.
* **No ground-truth validation:** no real z/OS or emulator run; no human labels.

## 5. Unresolved ambiguities (all **UNVERIFIED**)

| ID | Question | Where it matters | Status |
|---|---|---|---|
| U-01 | Does z/OS ignore `COND` on the first EXEC of a job? The oracle assumes yes (`test_oracle_semantics.py:104`). | `carddemo/app/jcl/TXT2PDF1.JCL` (single step `TXT2PDF EXEC PGM=IKJEFT1B … COND=(0,NE)`): `ALTER_COND_THRESHOLD/0` and `REMOVE_COND/0` are labelled **EQUIVALENT** - the only two non-trivial negatives (F-06). If the assumption is wrong both flip to DIFFERENT and the negative class has no non-trivial member. | UNVERIFIED; included as review cards R012 and R054 |
| U-02 | IBM default for omitted `DISP` status (NEW) and disposition (DELETE for NEW); `DISP=(,CATLG)` | oracle `model.py:230`, RELIC V2; RELIC v1.x treats omitted DISP as OLD (D-012). 0 corpus DDs have DSN without DISP; 5 files use `(,…)` | UNVERIFIED |
| U-03 | `DISP=NEW` of an existing dataset is a JCL error (spec: "SMS-managed assumption"); OLD/SHR of a non-existent dataset is a JCL error | drives DELETE/RENAME/MOVE positives (F-03) | UNVERIFIED, site-dependent |
| U-04 | `MOD` of a missing dataset = NEW; `(MOD,DELETE)` pre-delete idiom; `(OLD,DELETE)` | 8 D-004 files; 2 D-004 anchors R044, R048 | UNVERIFIED |
| U-05 | IF/THEN: `RC` = highest RC so far; `step.RC` false if step not run; `ABEND`/`RUN`; flushing after abend inside IF | IF in 22 files (baseline behaviour of guarded steps) | UNVERIFIED |
| U-06 | Program models: IEFBR14 no I/O; IEBGENER SYSUT1/2; SORT SORTIN/SORTOUT/OUTFIL; IEBCOPY INDD/OUTDD; IDCAMS RCs (DELETE missing 8, DEFINE existing 12); COBOL `SELECT … ASSIGN` DD-name derivation | IDCAMS 27 files, IEFBR14 12, IEBGENER 8, SORT 5 | UNVERIFIED |
| U-07 | `SPLIT_JOB`: separate jobs, any serial order, no failure propagation (F-04) | 166 positives | Design assumption, told to reviewers (rubric §3.3) so the review tests the oracle's implementation, not its definition |
| U-08 | "Behaviour-preserving" under normal completion vs under failure scenarios; abend flush makes every reorder observable | 81 abend-only + 78 RC-only positives | Rubric splits Q1/Q2 |
| U-09 | PASS of permanent datasets; CATLG/KEEP/UNCATLG; GDG relative generations | final-catalog observable (324 positives) | UNVERIFIED, effect unmeasured (F-14) |
| U-10 | 14 DD statements for which RELIC emits no relation (not root-caused) | RELIC parser statistics only | Open |

## 6. Recommended actions (not performed here)

1. Run the review package (60 cases, two independent mainframe-qualified reviewers, third for disagreements) and report oracle-vs-adjudicated agreement stratified by tier T0/T1/T2 and by the SPLIT / D-004 / duplicate-step flags **before** any "independent oracle" claim.
2. Report SPLIT_JOB, DELETE/MOVE/RENAME (construction-determined, F-03/F-04) and the 159 failure-injection-only positives as separate strata in headline metrics; add a baseline-only (no injection) label column to the records.
3. Make the termination observable job-name- and job-count-insensitive; add benign splits/reorders so the negative class contains non-trivial equivalences (F-04, F-06).
4. Add an independent third-party lexer as a cross-check of mutant well-formedness and of `stepname.ddname`/IDCAMS SYSIN; teach RELIC's `STATEMENT_PATTERN` the `procstep.ddname` name form.
5. Verify U-01..U-06 against the IBM *z/OS MVS JCL Reference* and, for the executable subset, a z/OS or Hercules/TK4- run (`EXTERNAL_VALIDATION_PROTOCOL.md` §4.3).

## 7. Reproduction

```
cd RELIC
for s in lexer_disagreement feature_census mutant_crosscheck split_job_sensitivity; do
  PYTHONPATH=$PWD/src:$PWD .venv/bin/python reports/v2/review_package/experiments/$s.py; done
```
Inline read-only queries not stored as scripts (outputs quoted above): opaque-step census over
`build_model` + `program_effect`; scan for col-72 / tab / unknown-op / cols 73-80 text over 133 `.jcl/.prc/.proc`
files; breakdown of the 24/27 "no relation" DDs; positive/negative counts per operator, subject, tier; RELIC recall by tier.
