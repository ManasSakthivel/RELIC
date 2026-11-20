# Normalised-text baseline (RELIC final sprint, Agent 4)

Status: **FROZEN** before any JCL-SemBench case was loaded by this agent (`results/sembench/BASELINE_FREEZE.json`, `relic_eval/text_baselines.py` sha256 `1ff51f34ad5cf11c28dd9afba0cbd13c205749b75de5ce30cfc015ac976213c6`). No rule was added, removed or modified after SemBench results were seen; the harness (`relic_eval/sembench_eval.py`) refuses to run if the hash or rule list differs from the freeze.

## Purpose

A *trivial* comparator that is as strong as plain text processing can reasonably be made, so that any apparent RELIC advantage is measured against something other than `any byte differs`. It has **no knowledge of JCL semantics**: it never builds a dependency graph, never resolves PROCs/symbols and never decides which statement is a step. It only removes differences that are textual noise by JCL's own syntax rules. Everything it removes is listed below together with what that removal costs.

## Baselines (`relic_eval/text_baselines.py`)

| name | definition | origin |
|---|---|---|
| `raw_text` | any difference between the two texts | new |
| `textdiff` | any change outside `//*` comment lines (columns >71 ignored on `//` lines, trailing blanks ignored) | existing `relic_eval.detectors.TextDiffDetector` (reused) |
| `textdiff_ignore_job_parameters` | `textdiff` that also reduces every JOB statement to `//NAME JOB` | existing `relic_eval.v2_eval.TextDiffIgnoreJobCard` (reused) |
| `normalized_text_A` | the 10-rule pipeline below, **no operand reordering** | new |
| `normalized_text_B` | version A + `sort_keyword_operands` | new |

All five see only `(original, mutated, path)`; none receives an operator, label or oracle verdict. A detector exception is returned as `Prediction(None, 'ERROR')` (never as 'not flagged').

## Structure model (infrastructure, not a rule)

Every rule operates on a small structural parse that is always on:
* statements start with `//` (not `//*`) or `/*`; `//*` lines are comments;
* structure is decided on columns 1-71 only;
* a statement continues if its operand field ends in a comma (a trailing comma in a comment field is not a continuation) or a quote is open at column 71 with a non-blank column 72; comment lines between continuation lines belong to the statement; a continuation line is a `//` line with a blank in column 3;
* in-stream data follows `DD *` / `DD DATA[,DLM=xx]` and ends at `/*` (or `xx`); `DD *` data also ends at any `//` line.
This model is heuristic: it does **not** expand PROCs, INCLUDEs or symbols, and it can mis-segment unusual input (see limitations per rule).

## Rules (frozen order)

Each rule is a switch in `RULES` / `RULE_DOCS`; `normalize(text, rules, sort_operands)` applies exactly the enabled ones. Unit tests: `tests/sembench/test_text_baselines.py` (one test group per rule, each showing the rule ON equates the variants and OFF distinguishes them).

### 1. `preserve_instream_data`

* **Rationale:** Data between 'DD *'/'DD DATA' and its delimiter is program input, not JCL: it must not be re-formatted by any other rule. When ON, data lines are compared byte-for-byte; when OFF they are treated like ordinary text lines (and so subject to whitespace/case rules).
* **Excluded from comparison:** nothing is excluded; this rule PROTECTS in-stream data from the rules below
* **Known limitation / potential semantic loss:** Data-region detection is heuristic (DD * / DD DATA, DLM=xx, '//' ends DD * data). Mis-detection (e.g. PROC-internal SYSIN, symbolic-driven DD) makes the rule protect the wrong lines or normalise real data.

### 2. `strip_comment_lines`

* **Rationale:** '//*' statements are ignored by the system; changing them cannot change behaviour.
* **Excluded from comparison:** whole comment statements (outside in-stream data)
* **Known limitation / potential semantic loss:** Comments may carry out-of-band meaning (operator instructions, scheduler directives embedded as comments, '//*%OPC' style control comments); such changes ARE behavioural for those tools.

### 3. `drop_blank_lines`

* **Rationale:** Empty lines outside in-stream data carry no JCL content.
* **Excluded from comparison:** empty / blank-only lines outside in-stream data
* **Known limitation / potential semantic loss:** z/OS treatment of a blank record is not asserted here; a blank record can be an error or terminate the job stream in some contexts.

### 4. `truncate_col71`

* **Rationale:** Columns 73-80 are sequence numbers and column 72 is the continuation column; the system does not use text beyond column 71 as statement text.
* **Excluded from comparison:** columns 72-80 of statement lines (outside in-stream data)
* **Known limitation / potential semantic loss:** Column 72 of a continued quoted string is semantically a continuation flag; it is consulted by the (always-on) structure detector only. Source lines >80 columns or in non-fixed-record files lose real text.

### 5. `rstrip_whitespace`

* **Rationale:** Trailing blanks on a record are not significant in JCL statements.
* **Excluded from comparison:** trailing whitespace of non-data lines
* **Known limitation / potential semantic loss:** Inside a quoted string continued at column 71 trailing blanks ARE significant; they are kept only when join_continuations handles that case.

### 6. `join_continuations`

* **Rationale:** Re-flowing a statement over different physical lines (or splitting a long operand field differently) does not change the logical statement.
* **Excluded from comparison:** line-break positions within a logical statement (and the '//' + blank prefix of continuation lines)
* **Known limitation / potential semantic loss:** Continuation detection is textual; a comma that ends a comment field or a statement with no operand field but trailing text is mis-read. strip_trailing_comment_field and sort_keyword_operands need this rule (they are no-ops without it).

### 7. `strip_trailing_comment_field`

* **Rationale:** Text after the operand field of a logical statement (separated by blanks) is the JCL comment field and has no effect.
* **Excluded from comparison:** the comment field after the operand field (not for IF/ELSE/ENDIF/SET, whose operands may contain blanks)
* **Known limitation / potential semantic loss:** Re-serialises the kept fields with single blanks (so it also hides blank-count differences even if collapse_whitespace is off). A statement without operands but with trailing text, or an operand containing an unquoted blank (e.g. arithmetic in SET, IF expressions in continued form), is mis-split; the exemption list is explicit and incomplete.

### 8. `collapse_whitespace`

* **Rationale:** Runs of blanks between fields are not significant (fields are blank delimited).
* **Excluded from comparison:** number/amount of blanks between fields and around the statement
* **Known limitation / potential semantic loss:** Blank-vs-nonblank in column 3 (name present or not) is preserved as a single blank after '//'; blanks INSIDE quotes are never collapsed. Wrong for in-stream data (hence preserve_instream_data).

### 9. `uppercase_outside_quotes`

* **Rationale:** JCL keywords, ddnames and stepnames are upper-case by convention and lower case in them is not distinguished by writers reformatting code.
* **Excluded from comparison:** letter case of all text outside apostrophes in statements
* **Known limitation / potential semantic loss:** Real semantic loss for case-sensitive content that is not quoted (z/OS UNIX paths in PATH= are quoted by rule, but unquoted symbolic or member names in some dialects are case-significant); wrong for in-stream data (hence preserve_instream_data).

### 10. `ignore_job_parameters`

* **Rationale:** A JOB statement's name identifies the job; its parameters (CLASS, MSGCLASS, NOTIFY, accounting ...) are largely scheduling/reporting attributes. Mirrors the pre-existing trivial reference textdiff_ignore_job_parameters.
* **Excluded from comparison:** operand field and continuations of every JOB statement (name and existence kept)
* **Known limitation / potential semantic loss:** REAL semantic loss: JOB parameters such as COND=, TYPRUN=HOLD/SCAN, REGION=, TIME=, RESTART= and CLASS can change whether/how the job runs. A genuine behavioural change confined to JOB parameters becomes invisible.

### 11. `sort_keyword_operands` *(version B only)*

* **Rationale:** VERSION B ONLY. Keyword operands of EXEC/DD/PROC/OUTPUT may be coded in any order; sorting them makes pure operand reordering invisible.
* **Excluded from comparison:** order of top-level KEY=VALUE operands after the positional prefix (sub-parameters inside parentheses are never reordered)
* **Known limitation / potential semantic loss:** Changes positional meaning if a positional operand follows a keyword (then the statement is left unsorted, by design). Order IS significant inside parenthesised sub-parameter lists (not touched) and for duplicate keywords (invalid JCL). Requires join_continuations; skips JOB/IF/SET.

## Cumulative semantic-loss summary

Version A can wrongly report *no change* (false negative) when a genuine behavioural change is confined to: a JOB-statement parameter (`COND=`, `TYPRUN=`, `REGION=`, `TIME=`, `RESTART=`, `CLASS=` ...), a comment that a scheduler/tool interprets, a case-only edit of unquoted, case-significant text, or a mis-detected in-stream-data region. Version B additionally ignores the order of top-level keyword operands (safe for EXEC/DD/PROC/OUTPUT keyword operands in valid JCL; positional operands are never moved and statements with a positional operand after a keyword are left unsorted). Conversely both versions can wrongly report a change (false positive) for harmless edits they do not model: equivalent re-ordering of steps/DDs that does not alter data flow, symbolic/PROC refactorings, renamed-but-consistent step or dataset names, `COND`/`IF` restructurings that are equivalent, and re-flow inside quoted strings. These are precisely the cases a semantic detector is expected to win on.

## Old-benchmark ablation (report only)

Population: the old benchmark's 566 evaluable mutants (460 behaviour-changing, 106 preserving; labels from `results/v2/v2_predictions.jsonl`, mutants regenerated with `relic_eval.v2_eval.iter_mutants`, SHA-verified). Reproduce: `python -m relic_eval.sembench_eval --old-benchmark-ablation` → `results/sembench/old_benchmark_ablation.json`.

**Caveat that limits what this ablation can show:** the old benchmark's only harmless operators are `INSERT_COMMENT` and `CHANGE_MSGCLASS`; nothing in it exercises whitespace, case, continuation, blank-line, trailing-comment-field, in-stream-data or operand-order noise. Rules 3-9 and `sort_keyword_operands` are therefore *untestable here* and show no effect by construction, **not** because they are useless or harmless. Their behaviour is covered by unit tests instead. Recall is 460/460 for every variant (every behaviour-changing mutant alters the text).

### Reference detectors

| variant | TP | FP | FN | TN | specificity | F1 |
|---|---|---|---|---|---|---|
| `normalized_text_A` | 460 | 2 | 0 | 104 | 0.9811 | 0.9978 |
| `normalized_text_B` | 460 | 2 | 0 | 104 | 0.9811 | 0.9978 |
| `raw_text` | 460 | 106 | 0 | 0 | 0.0 | 0.8967 |
| `textdiff` | 460 | 41 | 0 | 65 | 0.6132 | 0.9573 |
| `textdiff_ignore_job_parameters` | 460 | 2 | 0 | 104 | 0.9811 | 0.9978 |

### Leave-one-out (version A minus one rule)

| variant | TP | FP | FN | TN | specificity | F1 |
|---|---|---|---|---|---|---|
| A − `collapse_whitespace` | 460 | 2 | 0 | 104 | 0.9811 | 0.9978 |
| A − `drop_blank_lines` | 460 | 2 | 0 | 104 | 0.9811 | 0.9978 |
| A − `ignore_job_parameters` | 460 | 41 | 0 | 65 | 0.6132 | 0.9573 |
| A − `join_continuations` | 460 | 2 | 0 | 104 | 0.9811 | 0.9978 |
| A − `preserve_instream_data` | 460 | 2 | 0 | 104 | 0.9811 | 0.9978 |
| A − `rstrip_whitespace` | 460 | 2 | 0 | 104 | 0.9811 | 0.9978 |
| A (= B − sort) | 460 | 2 | 0 | 104 | 0.9811 | 0.9978 |
| A − `strip_comment_lines` | 460 | 67 | 0 | 39 | 0.3679 | 0.9321 |
| A − `strip_trailing_comment_field` | 460 | 2 | 0 | 104 | 0.9811 | 0.9978 |
| A − `truncate_col71` | 460 | 2 | 0 | 104 | 0.9811 | 0.9978 |
| A − `uppercase_outside_quotes` | 460 | 2 | 0 | 104 | 0.9811 | 0.9978 |

### Add-one-in (no other rule enabled)

| variant | TP | FP | FN | TN | specificity | F1 |
|---|---|---|---|---|---|---|
| (no rule = raw lines) | 460 | 106 | 0 | 0 | 0.0 | 0.8967 |
| only `collapse_whitespace` | 460 | 106 | 0 | 0 | 0.0 | 0.8967 |
| only `drop_blank_lines` | 460 | 106 | 0 | 0 | 0.0 | 0.8967 |
| only `ignore_job_parameters` | 460 | 67 | 0 | 39 | 0.3679 | 0.9321 |
| only `join_continuations` | 460 | 106 | 0 | 0 | 0.0 | 0.8967 |
| only `preserve_instream_data` | 460 | 106 | 0 | 0 | 0.0 | 0.8967 |
| only `rstrip_whitespace` | 460 | 106 | 0 | 0 | 0.0 | 0.8967 |
| only `strip_comment_lines` | 460 | 41 | 0 | 65 | 0.6132 | 0.9573 |
| only `strip_trailing_comment_field` | 460 | 106 | 0 | 0 | 0.0 | 0.8967 |
| only `truncate_col71` | 460 | 106 | 0 | 0 | 0.0 | 0.8967 |
| only `uppercase_outside_quotes` | 460 | 106 | 0 | 0 | 0.0 | 0.8967 |

The 2 residual false positives of A and B on the old benchmark are `carddemo/app/jcl/TXT2PDF1.JCL/REMOVE_COND/0`, `carddemo/app/jcl/TXT2PDF1.JCL/ALTER_COND_THRESHOLD/0` (COND edits that the oracle labels behaviour-preserving). They are not noise a text rule can remove: the text really changed. The old benchmark's entire negative population is thus separated by two rules (`strip_comment_lines`, `ignore_job_parameters`) - the same observation already recorded for `textdiff_ignore_job_parameters`.

## Honest interpretation

* `normalized_text_A/B` are **not** claimed to be sound change detectors; they are an upper-bound-ish *trivial* comparator. On the old benchmark they already equal `textdiff_ignore_job_parameters`, so the old benchmark cannot separate RELIC from trivial rules on specificity.
* Rules were chosen from JCL syntax (and from what *kinds* of edits are typically cosmetic), before any SemBench case was loaded. Disclosure: a smoke run of the full pipeline on the old benchmark (460 TP / 2 FP / 0 FN / 104 TN) was made while debugging, before the freeze; the only pre-freeze changes were parser bug fixes found by unit tests (continuation lines need only a blank in column 3, quoted-string continuation expectations), none driven by any SemBench data. The per-rule ablation was also produced before the freeze and changed no rule.
* Rule defaults (all on) are a single pre-specified configuration; no per-rule tuning, and no configuration search, was performed.
