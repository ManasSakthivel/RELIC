# Pre-Remediation Audit (snapshot of commit `024a3f2`)

Written **before** any code or result was changed during the final research
remediation (October 2026). It records the state of the repository as found,
so that every later change can be traced to a specific problem.

Environment used for the audit: macOS (Darwin 25.6, arm64), CPython 3.11.16
via `uv`, fresh virtual environment. No GnuCOBOL, no z/OS, no LLM API keys.

---

## A. Claims as found

| # | Claim (README / paper abstract) | Source of the number |
|---|---|---|
| C1 | RELIC F1 = 1.000 on CardDemo mutation benchmark (104/104 detected) | `results/rq2/rq2_summary.json` |
| C2 | Zero false positives on 144 semantics-preserving negatives (FPR = 0) | `results/rq2/negative_summary.json` |
| C3 | Static BCG without confidence-delta F1 = 0.960; structural F1 = 0.900; complexity F1 = 0.000 | `rq2_summary.json` |
| C4 | "Confidence-delta detection catches 8 ALTER_ERROR_BRANCH mutations invisible to structural analysis" (the paper's "discriminating finding") | `rq2_summary.json` by_operator |
| C5 | LLM-only F1 = 0.0377; Dependency+LLM F1 = 0.1091 ("lower bounds") | `results/rq2/llm_*_results.json` |
| C6 | RQ1 contract recovery micro-F1 = 1.000 on an 11-file held-out split (21 TP); paper abstract says "33 held-out files, 56 contracts, CI [0.39, 0.73]" | `results/rq1/rq1_independent.json` |
| C7 | RQ3 dynamic validation rate 91.8% (56/61 contracts) | `results/rq3/rq3_dynamic_results.json` |
| C8 | 305 tests pass; `make reproduce-paper1` reproduces all deterministic results | README |

## B. Verification of C8 (as found)

* `pytest tests/` → **305 passed** (verified).
* `make reproduce-paper1` fails as shipped: the Makefile hard-codes
  `python3.11`, which is not on PATH in a standard macOS environment. With a
  `python3.11` shim it runs and reproduces the committed numbers; output
  differs from the committed files only in timestamps and random `uuid4`
  identifiers (so CSVs are not byte-reproducible).
* `requirements.lock` contains an editable install pointing at another
  machine's directory (`/Users/.../untitled folder/legacy-contract`) and many
  unrelated packages (web3, eth-*, Flask). `pyproject.toml` declares many
  dependencies that no code imports (SQLAlchemy, alembic, lark, antlr4,
  pandas, seaborn, graphviz, …).

## C. Methodological problems found

### P1 — The RQ2 benchmark is circular (critical)

`scripts/run_rq2.py` never mutates source code. `MutationEngine`
(`src/legacy_contract/mutations/engine.py`) edits RELIC's *own output* — the
Behavioral Contract Graph — and then RELIC's detector diffs the original BCG
against the edited BCG:

* every F1/F2 operator explicitly **deletes contracts** from the mutated BCG
  (`mutated.contracts.pop(cid)`), with code comments stating this is done
  "to expose violation to BCGDiff";
* `ALTER_ERROR_BRANCH` **lowers `static_support` by 0.30** "to expose
  modification to BCGDiff", because the diff ignores the RC threshold;
* `SUPPRESS_RETURN_CODE_CHECK` deletes the contract directly.

The detector (`RiskDetector.detect`) flags any contract that is absent or has
lower confidence. Detection is therefore guaranteed by construction.

### P2 — Post-hoc exclusion of undetected mutants

`run_rq2.py` marks a mutant `NOT_APPLICABLE` when RELIC's own
`bcg.diff()` shows no broken/modified contract
(`error = mutation_no_contract_effect`, 2 rows). Mutants that the system
under test would miss are removed from the denominator before scoring.
`docs/mutation_na_criteria.md` states the N/A criteria were "determined
before experiment execution", which is not true for this criterion.

### P3 — The "ground truth" is "the mutation was applied"

`rq2_summary.json` notes: "Ground truth: any mutation that was successfully
applied is a positive test case" and "FP=0 by design". Precision is
hard-coded (`_metrics(tp, 0, fn)`). There is no oracle independent of RELIC.

### P4 — The negative benchmark is vacuous

`NegativeMutationEngine` operators never touch a contract:
`ADD_REDUNDANT_DEPENDENCY` is a no-op (the graph de-duplicates it),
`REORDER_INDEPENDENT_STEPS` only sets a flag attribute,
`RENAME_PROC_LABEL` renames an unreferenced entity. The 144 TNs include
3 seeds × identical no-ops. "Independent" steps are chosen without
transitivity (e.g., `STEP05`/`STEP15` in `TCATBALF.jcl` are called
independent although `STEP05 ≺ STEP10 ≺ STEP15`). FPR = 0 is guaranteed.

### P5 — The "confidence-delta" finding (C4) is a harness artifact

Static extraction always sets `static_support = 1.0`; a contract can only
become "modified" if something edits its confidence. On real source changes
RELIC (static) and Baseline E (static BCG, broken-only) are therefore
identical. The 8 ALTER_ERROR_BRANCH detections exist only because the
harness lowered the confidence by hand. Additionally, `BCG.diff()` compares
contracts by `(type, subject, predicate, object)` and ignores
`rc_threshold`/`operator`, so a real change of `COND=(4,LT)` to `COND=(8,LT)`
in source is invisible to RELIC.

### P6 — LLM baseline numbers (C5) measure rate limiting, not LLMs

* 245/248 (C) and 241/248 (D) calls failed with HTTP 429 (rate limit).
* Failed calls were **scored as "no regression"** — FN on positives and TN
  on negatives — rather than excluded.
* On the 10 calls that succeeded, the LLM was correct 10/10.
* The prompt never contained the JCL source or the change; it contained the
  file name, a one-line description, and the **operator name**, which leaks
  the label (`REORDER_INDEPENDENT_STEPS` vs `REORDER_JOBS`).

### P7 — The complexity baseline reads the answer key

`ComplexityBaseline.predict` uses `mutation.affected_entity_ids` (the
location of the mutation) — information no real detector would have.

### P8 — RQ1 metric bug and internal inconsistency

Five held-out files are single-step jobs with zero contracts in both oracle
and system (0/0). They are scored F1 = 0, giving macro-F1 = 0.5455 with a
bootstrap CI of [0.27, 0.82] next to micro-F1 = 1.000 with 0 FP / 0 FN.
The paper abstract reports different numbers (33 files, 56 contracts,
CI [0.39, 0.73]). The "independent oracle" re-implements the same rule
(consecutive EXEC statements are ordered) — independent code, same
specification, minimal discriminative power.

### P9 — RQ3 "dynamic validation" is self-confirmation

38 of the 40 traces are `EXECUTION_SIMULATED` traces produced by
`scripts/generate_execution_traces.py` from RELIC's own `JCLParser` step
order; they are then used to "validate" TEMPORAL contracts extracted from
that same step order. Real execution evidence: 2 GnuCOBOL runs of course
programs that do not correspond to CardDemo contracts.

### P10 — Parser defects that suppress whole contract categories

* `JCLParser.CONTINUATION_PATTERN = r"^//\s{15}"` merges a continuation line
  only when ≥ 15 blanks follow `//`. IBM JCL allows the continued operand to
  start anywhere in columns 4–16. **All 296 continuation lines in CardDemo
  have ≤ 13 blanks**, so none is merged; every `DISP=` on a continuation line
  is lost and the producing step defaults to a consumer. Result: only 3
  RESOURCE contracts in all of CardDemo, which the N/A document attributes
  to "a genuine characteristic of the CardDemo dataset".
* Columns 73–80 (sequence numbers) are not stripped.
* `COND=(code,op)` without a step name is bound only to the immediately
  preceding step; IBM semantics test every previous step.

### P11 — Split leakage / mislabeling

`_discover_dev_jcl()` claims "dev split only to avoid test-set leakage", but
the split paths never resolve and the script silently falls back to all
55 JCL files, including the held-out files used by RQ1.

### P12 — Secondary-subject analysis is factually wrong

`results/secondary_system_candidates.json` states that 40/43
`public_cobol` JCL files are single-step. Measured: 15 single-step,
24 two-step, 4 three-step. It also states no internet access was available;
GitHub access works in the current environment.

### P13 — Documentation sprawl and contradictions

≈ 80 tracked files contain headline metrics; many are superseded sprint
reports ("FINAL_*", "hostile review", "forensic audit", `.bob/` HTML). Numbers
disagree across README, paper, tables and JSON (see P8).

### P14 — Unverifiable citations and evidence sources

*Found during remediation, after the initial audit.* Eight of the 36 bibliography
entries could not be found anywhere (`docs/remediation/BIBLIOGRAPHY_VERIFICATION.md`).
The failure taxonomy's "evidence sources" could not be verified either: verbatim
AWS and IBM quotations, the "Knorr 2019" and "Gula 2020" postmortems, and
"CardDemo Issue #12", which is actually a PR renaming a data file. The claim that
the mutation operators are "empirically grounded" in documented migration failures
is therefore unsupported.

### P15 — Shared blind spot found in the new oracle (fixed before reporting)

The first version of the new oracle identified same-named steps by position. A
swap of two such steps then looked equivalent, and RELIC (whose entity IDs are
name-based) also missed it. Thirteen GenApp mutants were affected. The oracle now
uses content-based identities for duplicate names (test:
`test_swap_of_same_named_steps_is_not_hidden`).

## D. Pipeline as found

```
CardDemo JCL ──JCLParser──► IR ──Extractor──► BCG (original)
                                                 │
            MutationEngine edits BCG contracts ──┘──► BCG (mutated)
                                                 │
                       RiskDetector = BCG.diff ──┘──► detected? (always)
                                                 │
     label = "mutation applied" (always positive) ┘──► TP=104, FP≡0
```

## E. Mutation accounting as found (440 attempts)

| Status | Count | Reason |
|---|---:|---|
| EVALUATED (circular harness) | 104 | contract deleted/edited by the harness |
| NOT_APPLICABLE / zero_valid_contracts | 208 | 26 files × 8 operators: files with no contracts — 25 single-step files, plus `DEFCUST.jcl`, whose two steps are both named `STEP05` and collapse into one entity (entity IDs are name-based) |
| NOT_APPLICABLE / operator had no target | 126 | no MUST_PRECEDE / PRODUCES / COND element in an otherwise contract-bearing file (the RESOURCE cases are mostly caused by P10) |
| NOT_APPLICABLE / mutation_no_contract_effect | 2 | post-hoc exclusion (P2) |

The per-row legacy accounting is regenerated machine-readably in
`results/legacy/legacy_mutation_accounting.csv`.

## F. Remediation decisions (made before new results existed)

1. Replace the BCG-level benchmark with **source-level mutation**: mutate the
   JCL text, run the complete RELIC pipeline on the mutated text, diff.
2. Label every mutant with an **independent JCL execution-semantics oracle**
   (no imports from `legacy_contract`), which may say DIFFERENT, EQUIVALENT
   or UNDETERMINED. Equivalent mutants become negatives; undetermined ones
   are reported, not scored.
3. Enumerate **all** applicable mutation sites deterministically (no random
   site sampling, no seeds needed); de-duplicate identical mutants.
4. Score RELIC **as released (v1.0.0 behaviour)** as the primary, blind
   result. Spec-conformance fixes for P5/P10 are implemented afterwards and
   reported as a separately labelled, post-hoc variant.
5. Re-implement the LLM baselines so the model sees the actual original and
   mutated JCL; never score failed calls; report coverage.
6. Add two independently authored public JCL corpora as secondary subjects
   if the pipeline can process them without RELIC changes.
7. Generate every number in README / paper / tables from one pipeline and
   add an automated consistency check.
