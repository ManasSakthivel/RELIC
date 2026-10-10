# RELIC Final Research Readiness Report

*October 2026. Every number inside a generated block is rendered from
`results/final/metrics.json` by `relic_eval/report.py`; `make check` fails if any
of them disagrees with the raw records. Numbers outside generated blocks (test
counts, run times) are taken from the logged runs named in the text.*

## 1. Executive Summary

RELIC's earlier headline result is withdrawn; its benchmark was circular. It came
from a harness that edited RELIC's own contract graph and scored every applied
edit as a detected regression. The evaluation was rebuilt:

* source-level mutation of real JCL (10 operators, every applicable site);
* three public subject systems (multi-subject evaluation, **not** third-party
  external validation);
* ground truth from an independent JCL execution-semantics oracle (`jcl_oracle/`);
* complete accounting of every candidate mutant;
* RELIC v1.0.0 exactly as released as the primary, blind detector, with
  structural, complexity, static-BCG, trivial-reference and two LLM baselines.

<!-- BEGIN GENERATED:results-summary -->
- **Benchmark:** 656 candidate source-level mutants over 3 subject systems (566 evaluable, 86.3%); ground truth from an independent JCL execution-semantics oracle.
- **Primary result (CardDemo, RELIC v1.0.0 as released):** precision 1.000, recall 0.850, F1 0.919 (95% CI [0.88, 0.95]; TP 216, FP 0, FN 38, TN 61; n = 315).
- **RELIC v1.1** (spec-conformance fixes made *after* seeing these results): F1 0.982 on CardDemo.
- **Reference detector** that flags any non-comment text change: F1 0.943 (specificity 0.492); RELIC v1.0.0 − reference F1 difference 95% CI [-0.07, 0.02].
- **Structural baseline A:** F1 0.896.
- **All three subjects pooled:** RELIC v1.0.0 F1 0.905 (n = 566).
- **LLM baselines** (`openai/gpt-oss-20b`; scored only where both LLM baselines answered — 383 of 566 evaluable mutants (67.7%), all subjects): LLM-only F1 0.985 (P 1.000, R 0.970, specificity 1.000); dependency + LLM F1 0.967 (P 0.993, R 0.943, specificity 0.977); RELIC v1.0.0 on the same mutants F1 0.908 (RELIC v1.0.0 − LLM-only F1 difference 95% CI [-0.14, -0.03]; − dependency + LLM [-0.12, -0.01]). Coverage is limited by the provider quota of the API key used; the answered mutants are the first ones of a seeded random order, i.e. a random subsample. The earlier F1 0.0377 / 0.1091 figures were artifacts of rate-limited calls scored as negatives and are withdrawn.
<!-- END GENERATED:results-summary -->

**Assessment.** The repository supports a modest, honestly scoped research claim.
RELIC recovers JCL step-order and COND obligations and detects most
behaviour-changing edits on the primary subject without flagging harmless ones.
The released version misses whole change classes because of two implementation
defects. A trivial change detector matches its F1, so RELIC's value is
specificity and explanation rather than recall. The evaluation design, the oracle
and the raw data are the most reusable contribution. See §20.

## 2. Original Problems

Full audit with evidence: [remediation/PRE_REMEDIATION_AUDIT.md](remediation/PRE_REMEDIATION_AUDIT.md).

| # | Problem | Severity |
|---|---|---|
| P1 | RQ2 mutated RELIC's output (the BCG), not the source; detection was guaranteed | critical |
| P2 | Undetected mutants removed post hoc as "not applicable" | critical |
| P3 | Ground truth = "mutation applied"; precision fixed at 1 | critical |
| P4 | Negative benchmark edited nothing RELIC compares (no-ops) | critical |
| P5 | "Confidence-delta" finding produced by the harness lowering confidences by hand | high |
| P6 | LLM baselines: 245/248 and 241/248 calls failed (HTTP 429) and were scored; prompt leaked the operator name and contained no JCL | high |
| P7 | Complexity baseline read the mutation location (answer key) | high |
| P8 | RQ1 macro-F1 scored 0/0 files as 0; numbers inconsistent with the paper; oracle re-implemented the same rule | medium |
| P9 | RQ3 "dynamic validation" used traces generated from RELIC's own parser | high |
| P10 | Parser: continuation lines never merged (all 296 in CardDemo), columns 73–80 kept, COND bound to one step | high |
| P11 | Claimed dev/test split silently fell back to all files | medium |
| P12 | Secondary-subject analysis factually wrong | medium |
| P13 | ~80 files with contradictory headline numbers | medium |
| P14 | 8 of 36 citations and the failure-taxonomy sources unverifiable | medium |
| P15 | First version of the new oracle shared a same-named-step blind spot with RELIC | found and fixed before reporting |

## 3. Remediation Performed

* **Benchmark.** `relic_eval/mutate.py` mutates JCL text; `relic_eval/pipeline.py`
  runs every detector on (original, mutant) text only, labels each mutant with the
  oracle, and assigns exactly one status per candidate.
* **Oracle.** `jcl_oracle/` simulates both versions under return-code and abend
  scenarios and compares observable behaviour (§8).
* **RELIC versions.** `legacy_v1_0=True` switches in the parser, extractor and
  detector reproduce v1.0.0 exactly (primary). The default (v1.1) contains
  spec-conformance fixes made after the audit, reported separately as post hoc.
* **Baselines.** Complexity baseline made blind; trivial text-diff reference
  added; LLM baselines re-implemented and run (§9).
* **Metrics and reporting.** File-level cluster bootstrap CIs, Wilson intervals,
  sensitivity analyses; every table, LaTeX table, figure and documentation block
  generated from `metrics.json`; `make check` enforces it and scans active
  documentation for withdrawn numbers.
* **Repository.** Superseded reports archived under `docs/archive/` and
  `paper/archive/`; legacy results kept and labelled withdrawn; dependencies
  reduced to what the code imports; Makefile rewritten (`setup`, `test`,
  `reproduce`, `metrics`, `check`, `llm-baselines`).
* **Defects fixed during closure.** The generated-block regex never matched empty
  blocks, so the docs were never filled and `make check` accepted them; table
  row order depended on JSON key order. Both are fixed and covered by tests in
  `tests/evaluation/test_generated_blocks.py`.

## 4. Experimental Population

Unit of analysis: one JCL file with at least one JOB statement. Candidate mutants
are generated at every applicable site of every file and de-duplicated. A
candidate is scored only if it is EVALUABLE: a valid mutant, inside RELIC's
declared scope, with a DIFFERENT or EQUIVALENT oracle label. Behaviour-preserving
mutants (oracle EQUIVALENT, from both harmless and fault operators) are the
negatives.

<!-- BEGIN GENERATED:table-main-pooled -->
Population: all subjects, EVALUABLE mutants (n = 566: 460 behaviour-changing, 106 behaviour-preserving; 66 files)

| Detector | TP | FP | FN | TN | Precision | Recall | F1 | F1 95% CI (file bootstrap) | Specificity |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| **RELIC v1.0.0 (as released; primary)** | 380 | 0 | 80 | 106 | 1.000 | 0.826 | 0.905 | [0.84, 0.95] | 1.000 |
| RELIC v1.1 (post-hoc spec fixes) | 417 | 0 | 43 | 106 | 1.000 | 0.906 | 0.951 | [0.89, 0.99] | 1.000 |
| Baseline E: static BCG, broken-only | 380 | 0 | 80 | 106 | 1.000 | 0.826 | 0.905 | [0.84, 0.95] | 1.000 |
| Baseline A: structural edge diff | 368 | 0 | 92 | 106 | 1.000 | 0.800 | 0.889 | [0.81, 0.95] | 1.000 |
| Baseline B: complexity score | 162 | 33 | 298 | 73 | 0.831 | 0.352 | 0.495 | [0.21, 0.69] | 0.689 |
| Reference: any non-comment text change | 460 | 41 | 0 | 65 | 0.918 | 1.000 | 0.957 | [0.94, 0.97] | 0.613 |
<!-- END GENERATED:table-main-pooled -->

## 5. Mutation Accounting

Every candidate has exactly one status and a reason. No N/A category exists, and
no mutant is removed because of a detector's output (tested by
`tests/evaluation/test_results_integrity.py`).

<!-- BEGIN GENERATED:table-accounting -->
| Subject | Candidates | EVALUABLE | OUT_OF_SCOPE | INVALID_MUTATION | INFRASTRUCTURE_FAILURE | OTHER | % evaluable |
|---|---:|---:|---:|---:|---:|---:|---:|
| AWS CardDemo | 356 | 315 | 38 | 3 | 0 | 0 | 88.5% |
| Open Mainframe Project COBOL Programming Course | 84 | 35 | 26 | 23 | 0 | 0 | 41.7% |
| IBM CICS General Insurance Application (GenApp) | 216 | 216 | 0 | 0 | 0 | 0 | 100.0% |
| **All subjects** | 656 | 566 | 64 | 26 | 0 | 0 | 86.3% |
<!-- END GENERATED:table-accounting -->

<!-- BEGIN GENERATED:table-reasons -->
| Status / reason | CardDemo | OMP course | GenApp | All |
|---|---:|---:|---:|---:|
| INVALID_MUTATION | renamed DSN exceeds JCL length limits | 3 | 0 | 0 | 3 |
| INVALID_MUTATION | split point inside IF/THEN/ELSE | 0 | 23 | 0 | 23 |
| OUT_OF_SCOPE | IF/THEN/ELSE/ENDIF is outside RELIC's declared parser scope (jcl_parser.py: 'noted but not deeply parsed') | 0 | 23 | 0 | 23 |
| OUT_OF_SCOPE | no consumer of this dataset inside the analysed JCL file (cross-file effect only) | 38 | 3 | 0 | 41 |
<!-- END GENERATED:table-reasons -->

No candidate received an UNDETERMINED oracle label, and no infrastructure
failure occurred (both are checked by `make check`).

## 6. Contract Coverage

| Contract type | Implemented | Evaluated |
|---|---|---|
| TEMPORAL (step A precedes step B) | yes | yes: detection (step swap, job split) and recovery |
| RESOURCE (A produces a dataset before B consumes it) | yes | yes: detection (producer deletion, producer-side rename, consumer before producer) and recovery |
| CONTROL_FLOW (COND guards) | yes | yes: detection (COND removal, threshold change) and recovery |
| CONTROL_FLOW via IF/THEN/ELSE | no (outside the parser's declared scope) | reported as OUT_OF_SCOPE, plus a sensitivity analysis including them |
| DATA, STATE, ERROR | **no** (enum values only) | **no**. Future work. |

Recovery against oracle-derived facts (RQ1):

<!-- BEGIN GENERATED:table-contract-recovery -->
| Subject | Contract type | RELIC version | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| AWS CardDemo | TEMPORAL | relic_v1_0 | 79 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| AWS CardDemo | TEMPORAL | relic_v1_1 | 79 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| AWS CardDemo | RESOURCE | relic_v1_0 | 3 | 0 | 19 | 1.000 | 0.136 | 0.240 |
| AWS CardDemo | RESOURCE | relic_v1_1 | 9 | 9 | 13 | 0.500 | 0.409 | 0.450 |
| AWS CardDemo | CONTROL_FLOW | relic_v1_0 | 21 | 0 | 34 | 1.000 | 0.382 | 0.553 |
| AWS CardDemo | CONTROL_FLOW | relic_v1_1 | 55 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| AWS CardDemo | CONTROL_FLOW incl. IF/THEN (out of scope) | relic_v1_0 | 21 | 0 | 34 | 1.000 | 0.382 | 0.553 |
| AWS CardDemo | CONTROL_FLOW incl. IF/THEN (out of scope) | relic_v1_1 | 55 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Open Mainframe Project COBOL Programming Course | TEMPORAL | relic_v1_0 | 26 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Open Mainframe Project COBOL Programming Course | TEMPORAL | relic_v1_1 | 26 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Open Mainframe Project COBOL Programming Course | RESOURCE | relic_v1_0 | 0 | 0 | 23 | n/a | 0.000 | 0.000 |
| Open Mainframe Project COBOL Programming Course | RESOURCE | relic_v1_1 | 0 | 0 | 23 | n/a | 0.000 | 0.000 |
| Open Mainframe Project COBOL Programming Course | CONTROL_FLOW | relic_v1_0 | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Open Mainframe Project COBOL Programming Course | CONTROL_FLOW | relic_v1_1 | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Open Mainframe Project COBOL Programming Course | CONTROL_FLOW incl. IF/THEN (out of scope) | relic_v1_0 | 1 | 0 | 22 | 1.000 | 0.043 | 0.083 |
| Open Mainframe Project COBOL Programming Course | CONTROL_FLOW incl. IF/THEN (out of scope) | relic_v1_1 | 1 | 0 | 22 | 1.000 | 0.043 | 0.083 |
| IBM CICS General Insurance Application (GenApp) | TEMPORAL | relic_v1_0 | 68 | 4 | 0 | 0.944 | 1.000 | 0.971 |
| IBM CICS General Insurance Application (GenApp) | TEMPORAL | relic_v1_1 | 68 | 4 | 0 | 0.944 | 1.000 | 0.971 |
| IBM CICS General Insurance Application (GenApp) | RESOURCE | relic_v1_0 | 0 | 2 | 4 | 0.000 | 0.000 | 0.000 |
| IBM CICS General Insurance Application (GenApp) | RESOURCE | relic_v1_1 | 0 | 2 | 4 | 0.000 | 0.000 | 0.000 |
| IBM CICS General Insurance Application (GenApp) | CONTROL_FLOW | relic_v1_0 | 5 | 2 | 3 | 0.714 | 0.625 | 0.667 |
| IBM CICS General Insurance Application (GenApp) | CONTROL_FLOW | relic_v1_1 | 8 | 2 | 0 | 0.800 | 1.000 | 0.889 |
| IBM CICS General Insurance Application (GenApp) | CONTROL_FLOW incl. IF/THEN (out of scope) | relic_v1_0 | 5 | 2 | 3 | 0.714 | 0.625 | 0.667 |
| IBM CICS General Insurance Application (GenApp) | CONTROL_FLOW incl. IF/THEN (out of scope) | relic_v1_1 | 8 | 2 | 0 | 0.800 | 1.000 | 0.889 |
<!-- END GENERATED:table-contract-recovery -->

## 7. Subject-System Coverage

| Subject | Author | Role | License | Pinned |
|---|---|---|---|---|
| AWS CardDemo | AWS | primary | Apache-2.0 | vendored archive (`datasets/carddemo/`) |
| Open Mainframe Project COBOL Programming Course | Open Mainframe Project | secondary | CC-BY-4.0 / Apache-2.0 | vendored (`datasets/public_cobol/`) |
| IBM CICS General Insurance Application (GenApp) | IBM | secondary | EPL-2.0 | commit `f6f3f4b` (`datasets/genapp/PROVENANCE.md`) |

<!-- BEGIN GENERATED:table-subjects -->
| Detector | AWS CardDemo | Open Mainframe Project COBOL Programming Course | IBM CICS General Insurance Application (GenApp) | All subjects |
|---|---:|---:|---:|---:|
| n (pos/neg) | 315 (254/61) | 35 (10/25) | 216 (196/20) | 566 (460/106) |
| RELIC v1.0.0 (as released; primary) | F1 0.919 (P 1.000, R 0.850) | F1 0.947 (P 1.000, R 0.900) | F1 0.883 (P 1.000, R 0.791) | F1 0.905 (P 1.000, R 0.826) |
| RELIC v1.1 (post-hoc spec fixes) | F1 0.982 (P 1.000, R 0.965) | F1 1.000 (P 1.000, R 1.000) | F1 0.905 (P 1.000, R 0.827) | F1 0.951 (P 1.000, R 0.906) |
| Baseline E: static BCG, broken-only | F1 0.919 (P 1.000, R 0.850) | F1 0.947 (P 1.000, R 0.900) | F1 0.883 (P 1.000, R 0.791) | F1 0.905 (P 1.000, R 0.826) |
| Baseline A: structural edge diff | F1 0.896 (P 1.000, R 0.811) | F1 0.889 (P 1.000, R 0.800) | F1 0.880 (P 1.000, R 0.786) | F1 0.889 (P 1.000, R 0.800) |
| Baseline B: complexity score | F1 0.522 (P 0.912, R 0.366) | F1 0.439 (P 0.290, R 0.900) | F1 0.465 (P 0.968, R 0.306) | F1 0.495 (P 0.831, R 0.352) |
| Reference: any non-comment text change | F1 0.943 (P 0.891, R 1.000) | F1 1.000 (P 1.000, R 1.000) | F1 0.975 (P 0.952, R 1.000) | F1 0.957 (P 0.918, R 1.000) |
<!-- END GENERATED:table-subjects -->

This is a **multi-subject evaluation**. All three are demonstration or teaching
code, chosen and evaluated by the RELIC authors. **There is no third-party
external validation** and no production JCL.

## 8. Oracle Methodology

Specification: [evaluation/ORACLE_SPECIFICATION.md](evaluation/ORACLE_SPECIFICATION.md).

* **What it models:** JCL statements and continuation, procedures, COND (incl.
  EVEN/ONLY and step-qualified tests), IF/THEN/ELSE, abend propagation,
  allocation and dispositions, GDGs, IDCAMS catalog operations, common
  utilities and in-house COBOL file I/O. DB2/IMS/CICS/TSO programs are opaque.
* **Comparison:** both versions are simulated under a baseline scenario, each
  relevant return code per step and an abend per step. The comparison covers
  executed steps, return codes, the data version each read observes, the final
  catalog and job termination.
* **Independence:** `jcl_oracle` imports nothing from RELIC, the baselines or
  the harness, and receives only JCL text (enforced by
  `tests/oracle/test_oracle_independence.py`). Semantics are tested in
  `tests/oracle/test_oracle_semantics.py`, including the regression test for P15.
* **Sanity:** every original file of all three subjects simulates without a JCL
  error (`metrics.json` → `oracle_sanity`).
* **Limitations:**
  1. not validated against real z/OS execution;
  2. not reviewed by an independent mainframe practitioner;
  3. under abend semantics every step reorder is observable, so the no-abend
     sensitivity analysis is reported;
  4. step identity is name-based, with content hashes for duplicate names (see
     the specification, §6.7);
  5. the oracle and RELIC were written by the same project, so further shared
     blind spots may remain.

## 9. Baseline Methodology

Details: [evaluation/BASELINES.md](evaluation/BASELINES.md).

* **E: static BCG, broken contracts only.** It makes the same decisions as RELIC
  v1.0.0 on real source changes, because static confidences are always 1.0; this
  is verified by `make check`.
* **A: structural dependency-edge diff.**
* **B: corpus-normalised complexity score > 0.5.** It no longer reads the mutation
  location.
* **Reference: any non-comment text change.** It calibrates how easy the
  positives are.
* **C: LLM-only.** nvidia `openai/gpt-oss-20b`, temperature 0. It sees the
  original and modified JCL and a definition of behaviour.
* **D: dependency + LLM.** As C, plus an automatically extracted dependency
  summary of both versions.
* **Rules for C and D:**
  * no operator, site, file path or label in the prompt;
  * failed or unparseable answers are excluded, never scored;
  * every request/response is cached;
  * mutants are processed in a seeded random order.
* **Fair comparison:** the LLM table scores all detectors on the common population
  of mutants both LLM baselines answered.

## 10. Final RELIC Results

Primary: RELIC v1.0.0 as released, CardDemo, EVALUABLE mutants.

<!-- BEGIN GENERATED:table-main-carddemo -->
Population: AWS CardDemo, EVALUABLE mutants (n = 315: 254 behaviour-changing, 61 behaviour-preserving; 31 files)

| Detector | TP | FP | FN | TN | Precision | Recall | F1 | F1 95% CI (file bootstrap) | Specificity |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| **RELIC v1.0.0 (as released; primary)** | 216 | 0 | 38 | 61 | 1.000 | 0.850 | 0.919 | [0.88, 0.95] | 1.000 |
| RELIC v1.1 (post-hoc spec fixes) | 245 | 0 | 9 | 61 | 1.000 | 0.965 | 0.982 | [0.95, 1.00] | 1.000 |
| Baseline E: static BCG, broken-only | 216 | 0 | 38 | 61 | 1.000 | 0.850 | 0.919 | [0.88, 0.95] | 1.000 |
| Baseline A: structural edge diff | 206 | 0 | 48 | 61 | 1.000 | 0.811 | 0.896 | [0.84, 0.95] | 1.000 |
| Baseline B: complexity score | 93 | 9 | 161 | 52 | 0.912 | 0.366 | 0.522 | [0.19, 0.71] | 0.853 |
| Reference: any non-comment text change | 254 | 31 | 0 | 30 | 0.891 | 1.000 | 0.943 | [0.92, 0.96] | 0.492 |
<!-- END GENERATED:table-main-carddemo -->

Per operator, sensitivity analyses and figures:
[evaluation/RESULTS.md](evaluation/RESULTS.md). RELIC v1.1 is post hoc (its fixes
were designed after the defects were found) and is **not** the primary result.

## 11. LLM Baseline Results

## 12. Dependency+LLM Results

Sections 11 and 12 share one table, so that both LLM baselines and RELIC are
compared on the same mutants:

<!-- BEGIN GENERATED:table-llm -->
Model: `openai/gpt-oss-20b` via nvidia (prompt `source_diff_v4`, temperature 0, reasoning effort n/a, one sample per prompt). Failed or unparseable answers are excluded, never scored. All detectors below are scored on the same mutants: those for which both LLM baselines returned a valid answer.

| Population | Evaluable | Answered C / D | Common n (pos/neg) | Detector | TP | FP | FN | TN | Precision | Recall | F1 | F1 95% CI | Specificity |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| AWS CardDemo | 315 | 245 / 275 | 225 (174/51) | Baseline C: LLM-only | 170 | 0 | 4 | 51 | 1.000 | 0.977 | 0.988 | [0.98, 1.00] | 1.000 |
| | | | | Baseline D: dependency + LLM | 162 | 1 | 12 | 50 | 0.994 | 0.931 | 0.961 | [0.94, 0.98] | 0.980 |
| | | | | RELIC v1.0.0 (as released; primary) | 144 | 0 | 30 | 51 | 1.000 | 0.828 | 0.906 | [0.85, 0.95] | 1.000 |
| | | | | RELIC v1.1 (post-hoc spec fixes) | 165 | 0 | 9 | 51 | 1.000 | 0.948 | 0.974 | [0.93, 1.00] | 1.000 |
| | | | | Baseline A: structural edge diff | 143 | 0 | 31 | 51 | 1.000 | 0.822 | 0.902 | [0.84, 0.95] | 1.000 |
| | | | | Reference: any non-comment text change | 174 | 28 | 0 | 23 | 0.861 | 1.000 | 0.925 | [0.90, 0.94] | 0.451 |
| Open Mainframe Project COBOL Programming Course | 35 | 34 / 32 | 31 (8/23) | Baseline C: LLM-only | 7 | 0 | 1 | 23 | 1.000 | 0.875 | 0.933 | [0.86, 1.00] | 1.000 |
| | | | | Baseline D: dependency + LLM | 8 | 0 | 0 | 23 | 1.000 | 1.000 | 1.000 | [1.00, 1.00] | 1.000 |
| | | | | RELIC v1.0.0 (as released; primary) | 7 | 0 | 1 | 23 | 1.000 | 0.875 | 0.933 | [0.86, 1.00] | 1.000 |
| | | | | RELIC v1.1 (post-hoc spec fixes) | 8 | 0 | 0 | 23 | 1.000 | 1.000 | 1.000 | [1.00, 1.00] | 1.000 |
| | | | | Baseline A: structural edge diff | 6 | 0 | 2 | 23 | 1.000 | 0.750 | 0.857 | [0.67, 1.00] | 1.000 |
| | | | | Reference: any non-comment text change | 8 | 0 | 0 | 23 | 1.000 | 1.000 | 1.000 | [1.00, 1.00] | 1.000 |
| IBM CICS General Insurance Application (GenApp) | 216 | 139 / 156 | 127 (114/13) | Baseline C: LLM-only | 110 | 0 | 4 | 13 | 1.000 | 0.965 | 0.982 | [0.96, 1.00] | 1.000 |
| | | | | Baseline D: dependency + LLM | 109 | 1 | 5 | 12 | 0.991 | 0.956 | 0.973 | [0.95, 0.99] | 0.923 |
| | | | | RELIC v1.0.0 (as released; primary) | 95 | 0 | 19 | 13 | 1.000 | 0.833 | 0.909 | [0.65, 0.98] | 1.000 |
| | | | | RELIC v1.1 (post-hoc spec fixes) | 99 | 0 | 15 | 13 | 1.000 | 0.868 | 0.930 | [0.70, 0.99] | 1.000 |
| | | | | Baseline A: structural edge diff | 97 | 0 | 17 | 13 | 1.000 | 0.851 | 0.919 | [0.71, 0.98] | 1.000 |
| | | | | Reference: any non-comment text change | 114 | 7 | 0 | 6 | 0.942 | 1.000 | 0.970 | [0.93, 0.99] | 0.462 |
| All subjects | 566 | 418 / 463 | 383 (296/87) | Baseline C: LLM-only | 287 | 0 | 9 | 87 | 1.000 | 0.970 | 0.985 | [0.97, 0.99] | 1.000 |
| | | | | Baseline D: dependency + LLM | 279 | 2 | 17 | 85 | 0.993 | 0.943 | 0.967 | [0.95, 0.98] | 0.977 |
| | | | | RELIC v1.0.0 (as released; primary) | 246 | 0 | 50 | 87 | 1.000 | 0.831 | 0.908 | [0.84, 0.95] | 1.000 |
| | | | | RELIC v1.1 (post-hoc spec fixes) | 272 | 0 | 24 | 87 | 1.000 | 0.919 | 0.958 | [0.91, 0.99] | 1.000 |
| | | | | Baseline A: structural edge diff | 246 | 0 | 50 | 87 | 1.000 | 0.831 | 0.908 | [0.85, 0.95] | 1.000 |
| | | | | Reference: any non-comment text change | 296 | 35 | 0 | 52 | 0.894 | 1.000 | 0.944 | [0.92, 0.96] | 0.598 |
<!-- END GENERATED:table-llm -->

**Coverage.** The API key used allowed a limited token quota per rolling window.
The run stopped when quota was exhausted. Mutants were requested in a seeded random
order, and the answered set is exactly the first mutants of that order, i.e. a
random subsample. Answers that were not parseable (INVALID_OUTPUT: 148 for C,
103 for D) were excluded and not scored. No answered mutant was excluded.

Run status, coverage and configuration are in `results/final/raw/llm_status.json`.
Raw answers are in `results/final/raw/llm_records.jsonl`, and the full
request/response cache is in `results/final/raw/llm_cache/`. The withdrawn legacy
LLM results:

<!-- BEGIN GENERATED:table-legacy -->
| Quantity | Legacy harness (WITHDRAWN: BCG-level, circular) | Source-level benchmark (this version) |
|---|---|---|
| Mutants scored | 104 of 440 attempts | 315 of 356 candidates (CardDemo) |
| Ground truth | 'mutation was applied' (always positive) | independent JCL semantics oracle |
| Negatives | 144 BCG edits that touch no contract | oracle-equivalent mutants (incl. fault operators) |
| RELIC F1 | 1.000 | 0.919 (v1.0.0) / 0.982 (v1.1) |
| Baseline E F1 | 0.960 | 0.919 |
| Baseline A F1 | 0.899 | 0.896 |
| Baseline B F1 | 0.000 | 0.522 |
| Baseline C: LLM-only | F1 0.0377, but 245/248 calls failed (HTTP 429) and were scored as 'no regression'; 3/3 successful calls were correct | F1 0.985 on the 383 mutants (all subjects) both LLM baselines answered (of 566 evaluable; see LLM table) |
| Baseline D: dependency + LLM | F1 0.1091, but 241/248 calls failed (HTTP 429) and were scored as 'no regression'; 7/7 successful calls were correct | F1 0.967 on the 383 mutants (all subjects) both LLM baselines answered (of 566 evaluable; see LLM table) |
<!-- END GENERATED:table-legacy -->

## 13. Reproducibility

**Clean reproduction (fresh clone, fresh virtual environment, no API key).**

| | |
|---|---|
| Source | `git clone --branch relic/final-research-remediation` of the repository at commit `1cbcf06` |
| Environment | macOS 26.7, Darwin arm64, CPython 3.11.16 (uv-managed), new `.venv` from `requirements.lock`; `GROQ_API_KEY` unset |
| Commands | `make setup PY_BOOT=<python3.11>`, `make test`, `make reproduce`, `make check` |
| Time | 2026-10-04 06:53:52Z → 06:58:52Z: 300 s in total, of which `make reproduce` took 289 s |
| Exit status | setup 0, test 0 (391 passed), reproduce: every stage ran, but its final `make check` failed; check failed |
| Cause of the failure | one sentence in this report quoted the legacy test count without marking it legacy (a documentation issue, found by the stale-number scan). It was reworded in the follow-up commit; no code or result changed |
| Regenerated artifacts | every file under `results/final/` (raw records, LLM records and status, manifest, metrics, tables), `results/legacy/`, `paper/generated/`, `figures/final/`, `docs/assets/relic-results.svg` and all generated documentation blocks were **byte-identical** to the committed versions; the only changed file was `results/final/run_info.json` (commit hash, dirty flag, timestamp) |

**Repeat on the corrected commit `e5699fc`** (same procedure, fresh clone, no API
key), 2026-10-04 06:59:39Z → 07:21:31Z. `make setup` 0, `make test` 0 (391
passed), `make reproduce` 0, `make check` 0 ("Consistency check passed").
Again, every regenerated artifact was byte-identical to the commit apart from
`results/final/run_info.json`. `make reproduce` took 1,300 s on this run against
289 s on the first, on the same laptop; expect roughly 5–25 minutes.

**Determinism.** Two complete benchmark runs with different `PYTHONHASHSEED`
values produced byte-identical `evaluation_records.jsonl`,
`evaluation_manifest.csv`, `contract_recovery.json`,
`legacy_mutation_accounting.csv` and `metrics.json`. Figures are SVGs rendered
with a fixed hash salt and no date, and `make check` re-renders and compares
them. LLM answers come from the committed cache: a run without an API key
re-scores exactly the committed answers.

## 14. Test Results

`pytest tests/` (`make test`), 2026-10-04, CPython 3.11.16, macOS arm64:

| Total | Passed | Failed | Skipped | XFAIL |
|---:|---:|---:|---:|---:|
| 391 | 391 | 0 | 0 | 0 |

The legacy (pre-remediation) suite had 305 tests. Added: oracle independence,
semantics and determinism (`tests/oracle/`); mutation, metric, blindness,
results-integrity, generated-block and LLM-protocol tests (`tests/evaluation/`);
regression tests for the v1.1 fixes (`tests/remediation/`).

Defects found by running the tests and the clean reproduction, all fixed with
regression tests:
1. empty generated blocks were never matched (docs never filled, check vacuous);
2. table row order depended on JSON key order;
3. the oracle's evidence pairing depended on the per-process hash seed (labels
   were unaffected, records were not byte-identical; `test_oracle_determinism.py`
   fails on the old code).

The tests show that the implementation is consistent with its specification.
They are not evidence that the oracle's specification is a correct model of
z/OS.

## 15. Limitations

Full list with evidence and next steps: [limitations.md](limitations.md). In short:

1. Three small, non-production subjects; CardDemo dominates (L1, L2).
2. **No third-party external validation** (L13).
3. Oracle not validated against z/OS or by a practitioner (L3); abend semantics
   make every reorder observable (L4).
4. Single-file analysis; cross-job dependencies out of scope (L5).
5. Synthetic faults; the failure taxonomy's sources could not be verified (L6).
6. Positives are easy to flag; a trivial reference matches RELIC's F1 (L7).
7. RELIC v1.1 is post hoc (L8).
8. Contract coverage limited to TEMPORAL, RESOURCE and CONTROL_FLOW (L14).
9. LLM comparison: one model, one prompt, one sample; coverage limited by the
   provider quota (L10).
10. Dynamic-evidence reconciliation not validated (L11).
11. Small, clustered samples (L12).

## 16. Claims Supported by Evidence

* RELIC v1.0.0 has the precision, recall and F1 reported in §10, with the stated
  CIs, on CardDemo under the stated oracle.
* RELIC v1.0.0 flags none of the oracle-equivalent CardDemo mutants under the
  primary oracle. Without abend scenarios its specificity is lower (sensitivity
  table).
* RELIC v1.0.0 misses every COND-threshold change and most producer-side
  renames. The causes are traced to the diff ignoring guard parameters and to
  the continuation-line defect.
* A trivial non-comment change detector reaches similar or higher F1. RELIC's
  advantage is specificity.
* RELIC v1.0.0 and Baseline E make identical decisions on real source changes.
* The comparison with the LLM baselines on their common answered population is
  as reported in §11–12, for that model and prompt.
* The evaluation is reproducible from the repository (§13).

## 17. Claims Withdrawn or Weakened

| Earlier claim | Status |
|---|---|
| RQ2 F1 = 1.000 (104/104), zero false positives | **withdrawn**: circular harness (P1–P4) |
| Confidence-delta catches what structural analysis misses | **withdrawn**: harness artifact (P5) |
| LLM-only F1 0.0377, Dep+LLM F1 0.1091 | **withdrawn**: rate-limit failures scored as answers (P6) |
| RQ3 dynamic validation rate (legacy: 91.8%) | **withdrawn**: self-generated traces (P9) |
| RQ1 independent-oracle F1 on 33 held-out files | **withdrawn**: inconsistent with the artifacts, same-rule oracle (P8); replaced by recovery against oracle-derived facts |
| Mutation operators "empirically grounded" in documented failures | **weakened**: sources unverifiable (P14) |
| "305 tests pass" as evidence of correctness | **superseded**: see §14; tests show implementation consistency, not validity |
| Generalization to a second subject | **weakened**: now a multi-subject evaluation, not external validation |

## 18. Exact Reproduction Commands

```bash
git clone https://github.com/ManasSakthivel/RELIC.git && cd RELIC
git checkout relic/final-research-remediation
make setup        # .venv + requirements.lock (needs Python >= 3.11, or uv)
make test
make reproduce    # benchmark -> oracle -> detectors -> LLM scoring from cache -> metrics -> docs
make check
```

`make reproduce` re-scores the LLM baselines from the committed cache, so it needs
no API key. To re-query the model (new answers may differ):
`<PROVIDER_API_KEY>=... make llm-baselines` after deleting `results/final/raw/llm_cache/` (see `relic_eval/llm_baselines.py` for the expected environment variable name).

## 19. Remaining Work

1. Sample audit of oracle labels by an independent mainframe practitioner, and
   validation of a subset against real z/OS execution (L3).
2. Third-party replication on production or other public JCL (L13).
3. LLM comparison with several models and samples, and full coverage where the
   provider quota allowed only part (L10).
4. Cross-job (multi-file) analysis (L5).
5. DATA, STATE and ERROR contracts (L14).
6. Real execution evidence for the reconciliation component (L11).
7. Evaluate RELIC v1.1's fixes blind on new subjects (L8).

## 20. Final Research Readiness Assessment

**Ready for:** a workshop paper or a tool/artifact track as an honestly scoped
study. The contributions are: (1) an evaluation methodology for JCL behavioural
change detection (source-level mutation, an independent semantics oracle,
complete accounting, sensitivity analyses), released with all raw data;
(2) a characterisation of RELIC v1.0.0, including its two defects; (3) a
correction of the earlier, withdrawn results.

**Not ready for:** a claim that RELIC outperforms simple or LLM-based
alternatives. It does not on this benchmark: a trivial change detector matches
its F1, and on the LLM subsample the dependency-augmented LLM is at least as
accurate. Nor is it ready for a claim of external validity or real-world defect
detection.

**Blocking for a main-track submission:**
- independent validation of a sample of the oracle labels;
- third-party or production subjects;
- a full-coverage, multi-model LLM comparison. The current one covers a random
  subsample of the evaluable mutants (the free-tier API quota ran out; see §11).
  `make llm-baselines` resumes from the cache.

| Gate | Status |
|---|---|
| Circular evaluation removed, legacy results withdrawn | done |
| Every candidate mutant accounted for | done |
| Independent oracle, tested for independence and determinism | done (not externally validated) |
| Primary result blind (RELIC v1.0.0) | done |
| LLM-only and dependency+LLM baselines executed with a blind protocol | done, **partial coverage** |
| Numbers generated and machine-checked (`make check`) | done |
| Clean reproduction from a fresh clone | see §13 |
| Test suite | 391 / 391 pass |
| Third-party external validation | **not done** |
| DATA / STATE / ERROR contracts | **not implemented** |
