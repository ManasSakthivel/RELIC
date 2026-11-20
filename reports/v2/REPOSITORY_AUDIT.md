# RELIC V2 — Repository audit

Audit of `aee2309` (baseline) performed in a fresh clone. Findings that are
defects are tracked, with IDs, in [`DEFECT_REGISTER.md`](DEFECT_REGISTER.md).
Nothing here relies on code outside this repository.

## 1. Layout (what matters for the evaluation)

| Path | Role |
|---|---|
| `src/legacy_contract/parsers/jcl_parser.py` | JCL tokenizer/IR builder (steps, DDs, DISP, COND) |
| `src/legacy_contract/static_analysis/extractor.py` | TEMPORAL / RESOURCE / CONTROL_FLOW contract extraction |
| `src/legacy_contract/bcg`, `risk/detector.py` | behavioural-contract graph and the broken-contract detector |
| `jcl_oracle/` | behavioural oracle (lexer, simulator, judge) — labels mutants |
| `relic_eval/` | mutation generator, subjects, detectors, baselines, metrics, pipeline, consistency check |
| `results/final/` | **historical evidence** (raw records, metrics, tables, LLM cache) — never modified in V2 |
| `results/v2/` | new V2 development-set outputs |
| `datasets/` | CardDemo (primary), OMP COBOL course, GenApp (secondary) |

## 2. Pipeline and detectors

`mutate.generate` produces 656 mutants (10 operators). The oracle labels each
mutant `DIFFERENT` / `EQUIVALENT` or marks it non-evaluable (26 invalid,
64 out of scope). RELIC, structural baselines A/E, complexity B and the
text-change reference predict per mutant; LLM baselines C/D come from committed
records. `relic_v1_0` ("as released") is `legacy_v1_0=True` code in the current
tree; `relic_v1_1` is the post-hoc corrected current code.

## 3. Oracle semantics and independence

* **Semantics:** behavioural equivalence over a scenario set (return-code
  injection per step, program models, dataset catalog). It is not "does the
  mutated JCL still satisfy RELIC's contracts".
* **Code-level independence (verified):** `jcl_oracle` imports nothing from
  RELIC, enforced by `tests/oracle/test_oracle_independence.py`.
* **Common-mode risk (found):** `relic_eval/mutate.py` and `relic_eval/subjects.py`
  import `jcl_oracle.lexer`, `jcl_oracle.model` and `ProcLibrary`. The mutator
  and the oracle therefore share a lexer; a lexer bug would affect both
  consistently.
* **Not independent in the human sense:** one author wrote oracle, mutator and
  detector; the oracle, the parser fixes and the v1.1 fixes landed in one commit
  (`1cbcf06`, 2026-10-04), so there is no temporal evidence that the oracle was
  fixed before the detector was tuned. The oracle has not been validated against
  z/OS or by an independent mainframe engineer.
  **No claim of independent validation can be made.**
* **38 positives** are observable only under failure injection (return-code
  scenarios); they are not "plain run" differences.

## 4. Benchmark adequacy

* Subjects: 66 evaluable files (CardDemo 31, GenApp 10, OMP 25). All three were
  inspected during diagnosis, so none is held-out for V2.
* **Negatives are almost all cosmetic:** of 106 behaviour-preserving mutants,
  65 are comment insertions, 39 are `MSGCLASS` edits, 2 are COND edits.
  A one-line rule "text diff that ignores JOB-card parameters and comments"
  (`textdiff_ignore_job_parameters`, post-hoc diagnostic) scores pooled
  **F1 0.9978 (FP 2, FN 0)** — higher than RELIC v1.1 (0.951) and V2 (0.980).
  The benchmark therefore cannot demonstrate an advantage of contract reasoning
  over a trivial rule; the README sentence "advantage = specificity on harmless
  edits" is reproduced by that rule.
* **No benign reorder/split negatives:** every `SWAP_ADJACENT_STEPS` and
  `SPLIT_JOB` mutant is labelled DIFFERENT (166 each).
* **`REMOVE_IF_GUARD`:** 23 candidates, **0 evaluable** (all `OUT_OF_SCOPE`,
  `IF/THEN/ELSE` is not parsed). README says ten operators; nine contribute.
* **Mutation realism:** operators are single, synthetic edits (rename a DSN,
  double a COND threshold, swap two adjacent steps, …). `ALTER_COND_THRESHOLD`
  always doubles the threshold (0 → 4), i.e. always *weakens* the guard.
  The detector flags only weakening, so the *strengthening* direction is never
  exercised. Realism relative to production change histories is unmeasured.
* **Corpus coverage:** 27 files contain `IF` statements; 0 contain `INCLUDE`;
  130 DDs use unresolved `&SYMBOL` DSNs; 124 DDs are unnamed concatenations.

## 5. Contract extraction audit (summary; details in the register)

* TEMPORAL and CONTROL_FLOW recover the oracle's facts at P/R 1.0 on CardDemo
  (79 and 55 pairs). RESOURCE is the weak family: v1.1 recovery on CardDemo was
  P 0.50 / R 0.41 (9 TP, 9 FP, 13 FN).
* Remaining RESOURCE misses are mostly **program/utility I/O** (COBOL `COBRUN`,
  IDCAMS `REPRO`/`DEFINE`) that is invisible at JCL level — a scope/truth-definition
  mismatch, not a parser bug.
* `PROC` and `INCLUDE` are "noted, not parsed". `COND=EVEN/ONLY` is silently
  dropped (0 corpus instances).
* Entity ids hash `artifact_path::TYPE::name`, so a dataset in two files is two
  entities: **no cross-file RESOURCE contract can be formed**, although the
  extractor docstring describes one.

## 6. LLM baselines: model/provider and coverage audit

* **Committed LLM records:** all `openai/gpt-oss-20b` via nvidia, prompt
  `source_diff_v4`. The cache holds 1225 files: 1132 nvidia/20b and **93 Groq
  `gpt-oss-120b`, unreferenced (orphaned)**.
* **Documentation conflicts:** `paper/paper.md` (≈ lines 38, 162) and
  `docs/limitations.md` say Groq `gpt-oss-120b`; README, `docs/evaluation/BASELINES.md`
  and the readiness report say nvidia `gpt-oss-20b`; BASELINES.md still contains
  a legacy llama-3.3 row; `relic_eval/llm_baselines.py` defaults to
  groq / `gpt-oss-120b`. (The `paper/` files belong to the research lead and were
  **not** edited.)
* **Coverage claim is inaccurate:** README says coverage is "limited by the
  provider quota; a random subsample". Raw records show all 566 evaluable mutants
  were attempted; 183 are unscored because the model returned **no parseable JSON**
  (`INVALID_OUTPUT`: 148 for llm_C, 103 for llm_D).
* **Selection bias:** unscored mutants are 89.6 % positive vs 77.3 % for the
  scored ones, concentrated in `SWAP_ADJACENT_STEPS` (71) and `SPLIT_JOB` (52).
  LLM figures on the 383-mutant common subset are not comparable to RELIC on 566.
  Bounds if invalid outputs count as not-flagged / flagged: llm_C F1 0.808 / 0.972,
  llm_D F1 0.847 / 0.954 (`results/v2/v2_metrics.json`).

## 7. Documentation vs raw metrics

* Numbers in generated README/doc blocks agree with `results/final` (consistency
  check passes). The discrepancies are *narrative* claims listed in §4 and §6.
* `docs/reproducibility.md` did not mention V2 (updated in this sprint).

## 8. Hygiene

* 2420 tracked files at baseline; secret scan of the V2 commits found nothing.
  `.venv` is git-ignored.
* `results/final/run_info.json` changes on every reproduction; detector exceptions
  are recorded as `ERROR` and scored as "not flagged" (none observed in V2 runs).
