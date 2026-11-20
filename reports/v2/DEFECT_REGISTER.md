# RELIC V2 — Technical defect register

Baseline: `aee2309`. All evidence is reproducible from this repository
(`results/final`, `results/v2`, `tests/v2`). "Dev" = measured on the development
corpora (CardDemo, OMP course, GenApp) which were all inspected during diagnosis;
none is held-out, so **no V2 figure is external validation**.

Status values: **Fixed (opt-in)** — implemented behind `v2_fixes`, regression
tested, v1.x behaviour and `results/final` preserved · **Open** — not changed ·
**Doc** — documentation/validity issue, no code change in this sprint.

## Summary

| ID | Area | Severity | Status |
|---|---|---|---|
| D-001 | Same-named step identity | High | Fixed (opt-in) |
| D-002 | DD parsing (`DSNAME=`, `DISP=(,PASS)`) | Medium | Fixed (opt-in) |
| D-003 | RESOURCE contract ignores step order | Medium | Fixed (opt-in) |
| D-004 | `DISP=(MOD,DELETE)` treated as producer | Medium | Fixed (opt-in), **with measured trade-off** |
| D-005 | Swapped identically-named steps invisible | Medium | Open (characterised) |
| D-006 | PROC / INCLUDE / IF-THEN-ELSE not parsed | High (scope) | Open |
| D-007 | RESOURCE truth includes program/utility I/O | Medium | Open (scope mismatch) |
| D-008 | No cross-file RESOURCE contracts | Medium | Open |
| D-009 | `COND=EVEN/ONLY` silently dropped | Low | Open |
| D-010 | COND strengthening never exercised (mutator/detector co-design) | Medium | Open (documented) |
| D-011 | Symbolic DSNs, `&&` temporaries, unnamed concatenations | Medium | Open |
| D-012 | DD with DSN but no DISP defaults to consumer | Low | Open (unverified) |
| D-013 | Oracle independence | High (validity) | Doc |
| D-014 | Benchmark adequacy — cosmetic negatives, trivial rule matches RELIC | High (validity) | Doc |
| D-015 | `REMOVE_IF_GUARD` has 0 evaluable mutants | Low | Doc |
| D-016 | LLM model/provider inconsistencies | Medium | Doc |
| D-017 | LLM coverage claim wrong; selection bias | High (validity) | Doc |
| D-018 | "v1.0.0 as released" provenance | Medium | Doc |
| D-019 | Reproducibility wording; errors scored as "not flagged" | Low | Doc |

---

## D-001 Same-named step identity — High — Fixed (opt-in)
* **Evidence.** `genapp db2cre.jcl` has 10 `EXEC` statements but 4 STEP entities.
  39 of the 43 v1.1 false negatives are in files with repeated step names. v1.1
  recall: 0.990 (392/396) on files without repeated names, **0.391 (25/64)** on
  files with them (6 files).
* **Root cause.** `IREntity.entity_id = sha256(artifact::TYPE::name)`; equal step
  names therefore merge into one entity, so deleting, moving or un-guarding a
  duplicate is invisible and the step chain loses nodes.
* **Fix.** With `v2_fixes`, the n-th occurrence of a name in a file becomes
  `NAME#n` (first keeps `NAME`); `base_name` and file-wide `order` are recorded;
  `COND=(rc,op,stepname)` resolves to the nearest *preceding* same-named step.
* **Before/after (dev, pooled n=566).** Recall on files with repeated names
  0.391 → 0.766; without 0.990 → 0.992. Ablation without D-001: TP 419 vs 442
  (F1 0.953 vs 0.980). Paired bootstrap F1 diff (V2 − V2 without D-001) 95 % CI
  [0.0035, 0.0654].
* **Tests.** `tests/v2/test_v2_fixes.py::test_d001_*`, corpus-equivalence guard.
* **Scope limits.** Identity is by name + occurrence index within one file;
  steps within a PROC are not expanded (D-006); occurrence numbers shift if a
  same-named step is inserted earlier (names carry no content).

## D-002 DD parsing — Medium — Fixed (opt-in)
* **Evidence.** `DISP=(,PASS)` was captured as `(` and treated as a consumer;
  `DSNAME=` (35 DDs in the corpus) was invisible. 5 evaluated files affected;
  3 `RENAME_OUTPUT_DATASET` v1.1 false negatives (GenApp `asmmap` ×2, CardDemo
  `IMSMQCMP`). The oracle already handles both forms.
* **Root cause.** Regexes `DSN=([^\s,]+)` and `DISP=\(?([^,)]+)` do not model the
  `DSNAME` alias or an omitted first sub-parameter.
* **Fix.** `DSN(?:AME)?=` with a left boundary; `DISP` parsed as a parenthesised
  list, omitted status ⇒ `NEW` (IBM JCL default).
* **Before/after (dev).** V2 without D-002: TP 441 vs 442; RESOURCE recovery on
  CardDemo without D-002 P 0.69 / R 0.41 (9 TP, 4 FP) vs 11 TP, 0 FP with it.
* **Tests.** `test_d002_*` (status-role table, alias, boundary, absent-DISP default unchanged).
* **Scope limits.** Positional `DISP` only; `DSN` inside symbolic substitution
  is not resolved (D-011); `DD DUMMY`/`SYSOUT` unchanged.

## D-003 RESOURCE contract ignores step order — Medium — Fixed (opt-in)
* **Evidence.** CardDemo `UNLDPADB`: `STEP01 → STEP0` emitted though `STEP0`
  (consumer) is declared before `STEP01` (producer). Present among the 9 v1.1
  CardDemo recovery false positives.
* **Root cause.** `ResourceContractExtractor` pairs every producer with every
  consumer of a dataset regardless of declaration order.
* **Fix.** `v2_resource_order`: same-artifact pair kept only when producer
  `order` < consumer `order`.
* **Before/after (dev).** No detection change (TP 442 with and without D-003).
  CardDemo RESOURCE recovery FP: with D-003+D-004 0; with only one of them 3;
  with neither 8. TP unchanged (11).
* **Tests.** `test_d003_*`, UNLDPADB pin, corpus guard
  (V2 RESOURCE ⊆ v1.1 RESOURCE; TEMPORAL/CONTROL_FLOW identical on unaffected files).
* **Scope limits.** In-file order only. Because entity ids include the artifact
  path, cross-file contracts are never formed anyway (D-008). Loops/`GOTO`-like
  flow does not exist in JCL, so declaration order = execution order absent
  `IF`/`COND` (see D-006).

## D-004 `DISP=(MOD,DELETE[,…])` treated as producer — Medium — Fixed (opt-in), trade-off
* **Evidence.** The IEFBR14 pre-delete idiom created bogus contracts such as
  `ESDSRRDS PREDEL → STEP03`.
* **Root cause.** Any `MOD` status was classified as PRODUCES.
* **Fix.** With D-002 parsing, `MOD` + normal-termination `DELETE` produces
  neither PRODUCES nor CONSUMES. `MOD` with `CATLG/PASS/KEEP/none` still produces.
* **Before/after (dev) — TRADE-OFF.** Removes bogus RESOURCE contracts (see D-003
  numbers) but **loses 2 true positives** (CardDemo `DUSRSECJ` and `ESDSRRDS`
  `RENAME_OUTPUT_DATASET/0`, pooled TP 444 → 442, F1 0.9823 → 0.9800; paired
  bootstrap CI of the difference [-0.0060, 0.0]). v1.1 flagged these renames only
  *because* it mistook the delete for a producer; the oracle labels them DIFFERENT
  (final catalog changes). RELIC has no `deletes` contract, so V2 no longer sees
  them. Zero false positives gained.
* **Decision.** Kept in `relic_v2` on semantic grounds (a pre-delete is not a
  producer), **not** because it scores better — it scores slightly worse.
  `relic_v2_wo_D004` is reported alongside. Adding a "deletes" relation would be
  a new contract family and was out of scope.
* **Tests.** `test_d004_*`, including `test_documented_tradeoff_d004_…`.
* **Scope limits.** Only the exact `(MOD,DELETE…)` form; `(OLD,DELETE)` stays a
  consumer (correct: it reads then deletes).

## D-005 Swapped same-named steps invisible — Medium — Open
* **Evidence.** The 18 residual false negatives of `relic_v2` (all `RENAME_OUTPUT_DATASET`
  or `SWAP_ADJACENT_STEPS`): 13 are swaps in GenApp files whose steps share names
  (`db2cre` 6, `wsaap01` 3, `wsaup01` 3, `wsaip01` 1) — the sequence of step names is
  unchanged, so a name-based identity cannot see them. 1 is CardDemo `DEFCUST`
  (swap of IDCAMS in-stream `SYSIN` blocks: content opaque to the JCL parser).
  The remaining 4 are `RENAME_OUTPUT_DATASET`: 2 are the D-004 trade-off,
  2 are PROC-internal DD overrides (`TRANREPT`, `PRTCATBL`; D-006).
* **Root cause.** Identity is name-based (D-001 scope). A content fingerprint would
  distinguish them, but the benchmark has no step-content negatives, so its
  false-positive cost cannot be measured; shipping it would be unverifiable.
* **Status.** Characterised by
  `test_documented_limitation_swapped_identically_named_steps_not_detected`.

## D-006 PROC / INCLUDE / IF-THEN-ELSE not parsed — High (scope) — Open
* **Evidence.** PROC/INCLUDE are "noted, not parsed"; 27 corpus files contain
  `IF`, 0 contain `INCLUDE`; 64 candidate mutants are `OUT_OF_SCOPE`
  (all 23 `REMOVE_IF_GUARD`). Residual misses: CardDemo `TRANREPT`
  (`STEP05R.PRC001.FILEOUT`) and `PRTCATBL` (`STEP05R` calls `PROC=REPROC`): DD overrides on
  procedure-internal steps.
* **Why not fixed.** Needs PROC expansion with symbolic/override semantics and
  IF-condition modelling — a new contract family. Not attempted without a
  validated design; documented as blocker.

## D-007 RESOURCE truth includes program/utility I/O — Medium — Open
* **Evidence.** Oracle-only dataflow pairs come from COBOL program I/O (`COBRUN`)
  and IDCAMS `REPRO`/`DEFINE`; JCL-level extraction cannot see them. CardDemo
  RESOURCE recovery: v1.1 P 0.50 / R 0.41 → V2 P 1.00 / R 0.50. OMP course:
  0 / 23 recovered in all versions.
* **Assessment.** Scope/truth-definition mismatch, not a parser bug. RESOURCE
  recovery scores must not be read as extraction accuracy on JCL-visible facts.

## D-008 No cross-file RESOURCE contracts — Medium — Open
Entity ids hash the artifact path, so one dataset in two files is two entities;
the extractor docstring (“cross-artifact contract”) overstates capability.
Characterised by `test_documented_limitation_no_cross_file_resource_contracts`.

## D-009 `COND=EVEN/ONLY` — Low — Open
`COND_PATTERN` captures `EVEN`/`ONLY` as a bare word that no extractor branch
uses, so no contract results although the docstring promises one. 0 corpus instances.

## D-010 COND strengthening never exercised — Medium — Open (documented)
`ALTER_COND_THRESHOLD` always doubles the threshold (0 → 4: weakens the guard);
`guard_weakened` flags only weakening, and tests encode that a *stronger* guard is
not flagged (contract-satisfaction semantics) whereas the oracle uses behavioural
equivalence. Mutator and detector are co-designed, so this direction is neither
measured nor a known weakness. Not changed.

## D-011 Symbolic DSNs, temporary datasets, concatenations — Medium — Open
130 DDs use `&SYM`; 124 DDs are unnamed concatenations; `&&TEMP` datasets are
scoped to a job but treated as artifact-wide names. Effect on accuracy unmeasured.

## D-012 DD with DSN but no DISP — Low — Open (unverified)
Defaults to consumer. The single corpus case names a PDS member, where the IBM
default was not verified, so left unchanged (stated, not guessed).

## D-013 Oracle independence — High (validity) — Doc
Code-independent (import-checked), but: mutator and subjects share the oracle's
lexer (common-mode risk); one author for oracle, mutator and detector; oracle,
parser fixes and v1.1 fixes in one commit `1cbcf06`; no comparison with real
z/OS, no independent reviewer. **Independent validation is not claimed.**

## D-014 Benchmark adequacy — High (validity) — Doc
104 of 106 negatives are comment/MSGCLASS edits; the post-hoc
`textdiff_ignore_job_parameters` rule reaches pooled **F1 0.9978** (RELIC V2 0.980,
v1.1 0.951) and is a diagnostic only. No benign reorder/split negatives; 38 positives
need failure injection. Consequence: the benchmark shows RELIC beats a *naïve*
text diff on cosmetic edits, **not** that it beats a trivial normalised rule or
that it reasons about equivalence. The README phrase "advantage = specificity on
harmless edits" should be qualified accordingly (not edited here).

## D-015 `REMOVE_IF_GUARD` — Low — Doc
23 candidates, 0 evaluable (IF unsupported, D-006). README says ten operators;
nine contribute evaluable mutants.

## D-016 LLM model/provider inconsistencies — Medium — Doc
Committed records: nvidia `openai/gpt-oss-20b`, prompt `source_diff_v4`.
`paper/paper.md` and `docs/limitations.md` say Groq `gpt-oss-120b`; code default
is groq/`gpt-oss-120b`; BASELINES.md retains a llama-3.3 row; 93 of 1225 cache
files are orphaned Groq 120b entries. `paper/` is owned by the research lead and
was not edited; this register is the hand-off.

## D-017 LLM coverage and selection bias — High (validity) — Doc
README: "limited by the provider quota; a random subsample". Records: all 566
attempted; 183 unscored are `INVALID_OUTPUT` ("no JSON object in response":
148 llm_C, 103 llm_D). Unscored are 89.6 % positive (scored 77.3 %), concentrated in
`SWAP_ADJACENT_STEPS` (71) and `SPLIT_JOB` (52). On the 383-mutant common subset
(selection-biased): llm_C F1 0.985, llm_D 0.967, RELIC v1.0 0.908, v1.1 0.958,
**V2 0.979**; bounds over all 566 for invalid=not-flagged / flagged:
llm_C 0.808 / 0.972, llm_D 0.847 / 0.954. A fair LLM comparison needs a re-run
with credentials and output-format retries — **not performed**.

## D-018 "v1.0.0 as released" — Medium — Doc
`relic_v1_0` is `legacy_v1_0=True` code in the current tree (comment cites
`024a3f2`), not a checkout of release commit `db51c84` (2026-08-17).

## D-019 Reproducibility wording — Low — Doc
`docs/reproducibility.md` says outputs contain no timestamps; `run_info.json` does.
Detector exceptions are recorded as `ERROR` and scored as "not flagged" (none
occurred in V2 runs: 0 missing predictions).
