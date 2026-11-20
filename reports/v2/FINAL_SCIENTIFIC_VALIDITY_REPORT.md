# RELIC V2 — Final Scientific Validity Report (final sprint)

Branch `research/relic-v2-final-sprint`, based on the integration checkpoint
`research/relic-v2-integration` @ `f435029` (preserved, not modified).
Everything here is derived from files in this repository; derived quantities that no
agent produced are marked *(derived)* with the script that regenerates them.

**One-sentence verdict.** RELIC is a high-precision, low-recall contract-based filter; on
every benchmark we built or ran, a transparent normalised-text rule beats it on recall,
F1 and MCC; the benchmark infrastructure, the oracle-independence audit and the
negative result are the defensible contributions; **independent validation has not
happened**.

## 1. Subagents launched and completed

Six agents ran in the final sprint; all completed and wrote files (no agent ran a
state-changing git command; the lead committed). All outputs were re-checked by the lead
against raw files (see §14 for corrections made).

| # | Agent | Deliverable | Lead audit result |
|---|---|---|---|
| 1 | JCL-SemBench | `benchmarks/sembench/` (180 pairs), `reports/v2/SEMBENCH_DESIGN.md` | **Defect found:** 25 byte-identical pairs; narrative and 3 table rows wrong → corrected |
| 2 | Oracle audit | `ORACLE_INDEPENDENCE_AUDIT.md`, `INDEPENDENT_REVIEW_PACKAGE.md`, `review_package/` | Consistent with raw experiments; review **PENDING** |
| 3 | External validation | `relic_eval/external_eval.py`, `results/external/`, `EXTERNAL_VALIDATION_RESULTS.md` | Confusion matrices **recomputed independently** from `predictions.jsonl`: match |
| 4 | Baselines/statistics | `relic_eval/text_baselines.py`, `sembench_eval.py`, `results/sembench/`, reports | SemBench confusion matrices recomputed: match |
| 5 | Novelty / ResponsibleSE | `research/v2/FINAL_NOVELTY_ASSESSMENT.md`, `RESPONSIBLESE_POSITIONING.md`, `final_verified_references.bib` | Search is incomplete (DBLP blocked, Semantic Scholar 429) → nothing may be called "first" |
| 6 | Paper | `paper/v2/FINAL_RESEARCH_DRAFT.md` | Reconciled with corrected SemBench tables (§14) |

Disclosure: Agent 3 used the user's `gh` login for read-only code search (minor deviation
from "local clone only"; no write action).

## 2. Independently validated benchmark pairs

**0.** All 180 SemBench pairs have `independent_review_status = PENDING`. What exists:

| Validation status (`oracle_validation.json`) | Pairs |
|---|---:|
| `VALIDATED_BY_ORACLE_AND_ARGUMENT` (author argument **and** project oracle agree) | 151 |
| `ORACLE_DISAGREES` | 28 (15 are byte-identical generator no-ops, 13 are real, unresolved) |
| `ORACLE_ABSTAINS` | 1 |

"Validated" means author + the **non-independent** oracle agree. A 60-case blind review
package (seed 20251120; 30 EQUIVALENT / 30 DIFFERENT; rubric, form, agreement script,
adjudication rule) is ready in `reports/v2/review_package/`; no ratings exist and none
were fabricated.

## 3. Harmless (behaviour-preserving) transformations

87 labelled PRESERVING, but **10 are byte-identical** (original = transformed), so
trivially equivalent and they inflate every detector's specificity. 77 are real edits.

## 4. Genuine behavioural modifications

93 labelled CHANGING, but **15 are byte-identical** (generator no-op; the oracle was
right to disagree), so **78 are genuine changes**. The frozen benchmark files were not
edited (rule: no label manipulation). A corrected benchmark version is
**[PENDING EXPERIMENT]**. Sensitivity analysis on the 155 real pairs:
`results/sembench/noop_sensitivity.json` (script `noop_sensitivity.py`, detector-independent
exclusion rule). The conclusions do not change.

## 5. Oracle independence evidence (summary of `ORACLE_INDEPENDENCE_AUDIT.md`)

* Code-independent by import check only. Oracle, mutator, subject selection and parser
  fixes share one lexer lineage and one author (commit `1cbcf06`); mutator, subjects and
  pipeline import `jcl_oracle`. No z/OS ground truth exists.
* Oracle lexer vs RELIC parser: 94.5% of statements agree (1436/1519, 121 files). The
  83 oracle-only statements are `stepname.ddname` overrides (81) and `<…>` job names (2).
  Operand fields 100% in v1.1/V2; DD-role agreement 92.5–93.2%; per-file DSN-set agreement 74–76%.
* SPLIT_JOB supplies 36.1% of positives; 34.6% of positives differ only under failure
  injection; 28.4% of steps (120/423) are opaque to the oracle.
* The trivial rule `textdiff_ignore_job_parameters` agrees with the label on 564/566 mutants
  of the old benchmark: label ≈ text predicate (D-025, D-014).
* Open: second tokenizer re-labelling, a second independently written semantic model, and
  the independent review (H2, H3 untested).

## 6. External repositories evaluated

11 licence-verified public repos at pinned SHAs (`results/external/SUBJECT_FREEZE.json`,
frozen at RELIC `f435029`): 10 effectiveness repos (182 `.jcl` files, 76 eligible) plus
`mapa` (robustness only). Excluded: `MVS-sysgen/sysgen` (no licence). Caveats:
`yetacp/mvs_sysgen` has an unverified upstream licence and supplies 589/824 (71.5%) mutants.
All were "screened by aggregate counts/fragments" — **none is blind**. Accounting:
1005 candidates → 824 evaluable, 163 out of scope, 17 invalid, 1 other; 0 oracle crashes, 0 detector errors.
Labels come from the **same non-independent oracle**: this tests generalisation of
parser+detector to unseen files, not agreement with independent ground truth.

## 7. Baseline results

**SemBench (n = 180; 93 changing / 87 preserving), recomputed from `predictions.jsonl`:**

| Detector | TP | FP | FN | TN | MCC |
|---|---:|---:|---:|---:|---:|
| relic_v1_0 | 15 | 2 | 78 | 85 | 0.2363 |
| relic_v1_1 = relic_v2 | 23 | 2 | 70 | 85 | 0.3241 |
| normalized_text_A | 78 | 35 | 15 | 52 | 0.4511 |
| normalized_text_B | 78 | 28 | 15 | 59 | 0.5249 |
| textdiff | 78 | 60 | 15 | 27 | — |
| textdiff_ignore_job_parameters | 78 | 49 | 15 | 38 | 0.302 |
| raw_text | 78 | 77 | 15 | 10 | −0.067 |

**External mutation run (n = 824), recomputed:**

| Detector | TP | FP | FN | TN |
|---|---:|---:|---:|---:|
| v1.0 | 612 | 0 | 79 | 133 |
| v1.1 | 643 | 0 | 48 | 133 |
| V2 | 658 | 0 | 33 | 133 |
| textdiff | 691 | 62 | 0 | 71 |
| textdiff_ignore_job_parameters | 691 | 3 | 0 | 130 |

V2 F1 0.9755 vs diagnostic 0.9978 (V2 − diagnostic CI [−0.042, −0.008]). Without the
`mvs_sysgen` subject V2 = v1.1 (F1 0.9897). `zowe-cli`: V2 F1 0.40 on 6 mutants (test
templates; not diagnosed, no tuning permitted).

**Old benchmark (n = 566, development set):** V2 TP 442 / FP 0 / FN 18 / TN 106, F1 0.9800; v1.1 0.951; v1.0 0.905; diagnostic text rule 0.9978.

**LLM baselines:** not re-run (no credentials). Committed records: `gpt-oss-20b`
(nvidia) on a selection-biased 383/566 subset; protocol for a fair re-run in
`LLM_EVALUATION_PROTOCOL.md`. **No LLM result exists for SemBench or the external set.**

## 8. Statistical results

* SemBench, V2 vs v1.1: 0 discordant cases. V2 vs `normalized_text_B`: discordant 26 vs 55,
  exact McNemar, Holm p = 0.020, ΔMCC = −0.20, 95% cluster-bootstrap CI [−0.30, −0.10]
  (16 clusters only).
* No-op sensitivity *(derived: `results/sembench/noop_sensitivity.py`)*: on the 155 real
  pairs, V2 MCC 0.366 vs `normalized_text_B` 0.684, ΔMCC CI [−0.43, −0.23], uncorrected
  p = 0.0017. Also excluding the 13 non-identical oracle-disagreement pairs and the 1
  abstaining pair (n = 141): V2 0.464 vs 0.694, CI [−0.37, −0.12], uncorrected p = 0.029.
  p-values in this script are **not** Holm-corrected.
* Oracle-contested subset (28): every detector has MCC < 0.
* Old benchmark: V2 beats v1.1 (27 vs 2 discordant) yet is significantly worse than the
  normalised and diagnostic rules.
* **Hypothesis H1 (RELIC beats a normalised text diff) is refuted** on SemBench, the old
  benchmark and the external run. H2–H5 are untested or pending.

## 9. Literature-supported novelty assessment

`research/v2/FINAL_NOVELTY_ASSESSMENT.md`: 54 verified BibTeX keys; unverified items
listed and must not be cited. No JCL behavioural-equivalence prior art was found in the
sources searched, but DBLP was blocked and Semantic Scholar rate-limited, so absence of
evidence is weak. Defensible framing: a benchmark and audit protocol for a niche
language, plus a negative result. **No claim of "first".**

## 10. Updated manuscript

`paper/v2/FINAL_RESEARCH_DRAFT.md` (claims register A1–A45, pending register P1–P14,
evidence index). LaTeX sources and `.bib` were **not** updated and LaTeX could not be
compiled here (no TeX). `paper/paper.md`: four hand-written LLM statements corrected,
plus an erratum next to the generated block (see §13).

## 11. Test and reproducibility results

Executed on the final tree (outputs summarised in the final message of the sprint):
`pytest tests -q`, `python -m relic_eval.check_consistency`, `python benchmarks/sembench/validate.py`
(manifest 360 passed, 0 failed), `python -m relic_eval.sembench_eval`. Commands:
`docs/reproducibility.md` ("Final-sprint additions"). The external run needs network access
to obtain the pinned clones and was not re-executed at the final step; its numbers were
recomputed from the committed `predictions.jsonl` instead.

## 12. Git

Branch `research/relic-v2-final-sprint`. Hashes are recorded in the final message and
verified with `git ls-remote`; a file cannot contain its own commit hash.

## 13. Remaining blockers

1. Independent review of the 60-case package (H2) — requires external human reviewers.
2. Corrected SemBench v2 (replace 15+10 no-op pairs; resolve 13 disagreements) — would be a
   new frozen version, not a mutation of the existing one.
3. A truly held-out, un-inspected external set and a second oracle (z/OS or independently
   written model) — none available.
4. Fair LLM re-run — credentials required.
5. Generator template wording ("random subsample") in `relic_eval/report.py` — changing it
   rewrites `results/final/tables/`; maintainer decision.
6. Version fields (pyproject/CITATION 1.1.0, package `__version__` and Dockerfile 0.1.0,
   tag v1.0.0) and stale Docker/compose — documented in `docs/reproducibility.md`, not altered.
7. LaTeX/`.bib` for the new draft; PROC/INCLUDE/IF-THEN-ELSE and production JCL
   compatibility remain unsupported/unevidenced.
8. Only 16 SemBench base programs (cluster-level power is low).

## 14. Corrections made by the lead during audit (transparency)

* SemBench: 25 byte-identical pairs found by hash comparison (not reported by Agent 1);
  `SEMBENCH_DESIGN.md` §5.1 and table rewritten from `cases.jsonl`
  (`unreferenced_step_rename` 4/2, `disp_change` 8/11, `return_code_effect` 10/2/1 abstain;
  preserving 84/3; changing 67/25/1). Frozen benchmark files untouched.
* Paper draft: "design report inconsistent" note changed to "resolved"; sensitivity CIs added;
  P6 closed, P14 narrowed.
* `paper/paper.md`: gpt-oss-120b/Groq/"quota-limited random subsample" statements replaced
  by the committed record (nvidia gpt-oss-20b, 383/566, selection-biased).

## 15. Honest revised scores (1–5)

| Dimension | Score | Reason |
|---|---:|---|
| Research rigour | **2** (ceiling 3–4 after independent review, second oracle, corrected SemBench, held-out set) | Labels author + non-independent oracle; development corpora inspected; 16 clusters; no independent validation; honest negative result and thorough audit trail lift it above 1 |
| Novelty | **2** (ceiling ≈3) | No prior JCL art found but search incomplete; contribution is infrastructure plus negative result, not a better detector |
| Impact / usefulness | **2–3** | Reusable benchmark/audit protocol and a clear warning against text-label-aligned oracles; RELIC itself is not shown to be useful beyond high-precision filtering |

## 16. Mapping to earlier-prompt deliverable names

| Earlier name | Delivered as |
|---|---|
| SEMANTICALLY_PRESERVING_TRANSFORMATIONS | `reports/v2/SEMBENCH_DESIGN.md`, `benchmarks/sembench/` |
| EXTERNAL_VALIDATION_EXECUTION | `reports/v2/EXTERNAL_VALIDATION_RESULTS.md` (+ `EXTERNAL_VALIDATION_PROTOCOL.md`) |
| ORACLE_AUDIT_PACKAGE | `reports/v2/ORACLE_INDEPENDENCE_AUDIT.md`, `INDEPENDENT_REVIEW_PACKAGE.md`, `review_package/` |
| REVISED_MANUSCRIPT | `paper/v2/FINAL_RESEARCH_DRAFT.md` |
| LLM re-evaluation | `reports/v2/LLM_EVALUATION_PROTOCOL.md` (protocol only) |
