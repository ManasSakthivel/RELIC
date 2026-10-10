# Checking Behavioral Contracts of JCL Batch Jobs Under Modernization: An Evaluation Against an Independent Execution-Semantics Oracle

*Manuscript draft (October 2026), not peer reviewed. Replaces the v1 manuscript
(`paper/archive/v1/`), whose central result came from a circular evaluation and
is withdrawn. Every number in this document is generated from
`results/final/metrics.json`.*

## Abstract

Mainframe batch jobs encode behavioural rules in JCL — step order, dataset
allocation and disposition, return-code guards — that must be carried over by
hand when a job is re-implemented on another platform. RELIC recovers these rules
as explicit *behavioral contracts* (TEMPORAL, RESOURCE, CONTROL_FLOW) in a
Behavioral Contract Graph, and reports contracts that a changed job breaks or
weakens. We evaluate RELIC with a source-level mutation benchmark over three
independently authored public JCL corpora (AWS CardDemo as the primary subject,
the Open Mainframe Project COBOL course, IBM CICS GenApp). Each mutant is labelled
by an independent simulator of JCL execution semantics that shares no code with
RELIC and never sees the mutation operator. Every candidate mutant is accounted
for. The results and their uncertainty are:

<!-- BEGIN GENERATED:results-summary -->
- **Benchmark:** 656 candidate source-level mutants over 3 subject systems (566 evaluable, 86.3%); ground truth from an independent JCL execution-semantics oracle.
- **Primary result (CardDemo, RELIC v1.0.0 as released):** precision 1.000, recall 0.850, F1 0.919 (95% CI [0.88, 0.95]; TP 216, FP 0, FN 38, TN 61; n = 315).
- **RELIC v1.1** (spec-conformance fixes made *after* seeing these results): F1 0.982 on CardDemo.
- **Reference detector** that flags any non-comment text change: F1 0.943 (specificity 0.492); RELIC v1.0.0 − reference F1 difference 95% CI [-0.07, 0.02].
- **Structural baseline A:** F1 0.896.
- **All three subjects pooled:** RELIC v1.0.0 F1 0.905 (n = 566).
- **LLM baselines** (`openai/gpt-oss-20b`; scored only where both LLM baselines answered — 383 of 566 evaluable mutants (67.7%), all subjects): LLM-only F1 0.985 (P 1.000, R 0.970, specificity 1.000); dependency + LLM F1 0.967 (P 0.993, R 0.943, specificity 0.977); RELIC v1.0.0 on the same mutants F1 0.908 (RELIC v1.0.0 − LLM-only F1 difference 95% CI [-0.14, -0.03]; − dependency + LLM [-0.12, -0.01]). Coverage is limited by the provider quota of the API key used; the answered mutants are the first ones of a seeded random order, i.e. a random subsample. The earlier F1 0.0377 / 0.1091 figures were artifacts of rate-limited calls scored as negatives and are withdrawn.
<!-- END GENERATED:results-summary -->

The released version misses every COND-threshold change and most producer-side
dataset renames because of two implementation defects (a diff that ignores guard
parameters; a continuation-line rule that drops most dataset dispositions). Fixes
made after the audit recover them, but that result is not blind. A trivial
detector that flags any non-comment edit reaches comparable F1, so most of
RELIC's measurable value lies in specificity and in naming the violated contract,
not in recall. On a quota-limited random subsample, an LLM (`gpt-oss-120b`) given
both versions of the job, with or without a dependency summary, was at least as
accurate as RELIC v1.0.0. We also report that the previous version of this work overstated
its evidence: the withdrawn F1 = 1.000 result came from mutating RELIC's own
output, and its LLM-baseline numbers reflected rate-limit failures (withdrawn).

## 1. Introduction

Re-implementing a JCL job stream on another platform is risky in a specific way.
The new job usually runs; it just behaves differently in situations the migration
did not consider: a step that used to be skipped after a failure now runs, a
consumer reads a dataset before its producer has rewritten it, a renamed output is
no longer found downstream. These rules are implicit in JCL semantics (IBM *z/OS
MVS JCL Reference*). Structural dependency tools record which step uses which
dataset, but not the obligations ("B must not run if A ends with RC > 4") that the
new implementation must preserve.

RELIC makes such obligations explicit and checks them across versions. This paper
asks:

* **RQ1 (recovery).** How accurately does RELIC recover TEMPORAL, RESOURCE and
  CONTROL_FLOW obligations, compared with facts derived independently from JCL
  semantics?
* **RQ2 (detection).** Given an original and a changed job, how well does RELIC
  separate behaviour-changing changes from behaviour-preserving ones, compared
  with structural and trivial baselines?

Contributions:

1. the Behavioral Contract Graph for JCL and contract differencing (RELIC);
2. an evaluation design for this class of tool — source-level mutation, an
   independent execution-semantics oracle (`jcl_oracle`), complete accounting of
   every candidate mutant, and sensitivity analyses — released with all raw data;
3. an honest assessment of RELIC, including two implementation defects the
   evaluation exposed, and a correction of the previously published results.

## 2. Background

A JCL **job** is a sequence of **steps** (`EXEC`), each running a program or
procedure with **DD** statements that allocate datasets (`DSN`) with a
**disposition** (`DISP=NEW|OLD|SHR|MOD`, plus what to do at normal and abnormal
end). `COND=(code,op[,step])` bypasses a step when a test against earlier return
codes is true; `IF/THEN/ELSE` selects steps by return codes and abends; after an
abend, later steps are bypassed unless they explicitly request otherwise. These
semantics are the implicit contract of a job.

Behavioural contracts follow Design by Contract (Meyer 1992). Unlike
specification mining from traces (Daikon, Ernst et al. 2007; GIST, Lorenzoli et
al. 2008), RELIC extracts contracts statically from job definitions. Unlike
statement-level semantic differencing (SymDiff, Lahiri et al. 2012) and
regression verification (Felsing et al. 2014), it works at the level of job
steps, datasets and guards, without a formal program model. Control-flow
extraction for COBOL in migration settings is an active topic (e.g. Deknop et al.
2022); we are not aware of prior work that evaluates JCL-level contract checking
against an execution-semantics oracle.

## 3. RELIC

**Behavioral Contract Graph.** `BCG = (V, E, C, P, D, Γ)`: entities (jobs, steps,
programs, datasets, DDs), structural relations, contracts, provenance, optional
dynamic observations and validation metadata. Contract types:

| Type | Form | Extracted from |
|---|---|---|
| TEMPORAL | `A ≺ B` | consecutive EXEC statements |
| RESOURCE | `produces(A, D) ≺ consumes(B, D)` | DD statements sharing a DSN, DISP NEW/CATLG/PASS/MOD vs OLD/SHR |
| CONTROL_FLOW | `RC(A) op t → ¬run(B)` | `COND=` tests |

**Differencing.** Both versions are parsed and their contracts compared by
signature `(type, subject, predicate, object)`. Contracts present only in the
original are *broken*; contracts with the same signature but lower confidence are
*weakened*. Any broken or weakened contract becomes a risk item with an
explanation chain. RELIC v1.1 (§6) also compares COND thresholds/operators and
reports a contract as weakened when the new guard lets the step run at a return
code where the original bypassed it.

**Dynamic reconciliation.** RELIC can attach execution events to contracts and
update their validation state. This component was not validated with real
execution evidence and is not used in the evaluation below (§8).

## 4. Evaluation design

**Subjects.** Three public corpora by different authors (AWS, the Open Mainframe
Project, IBM). This is a multi-subject evaluation run by the RELIC authors, not a
third-party external validation. The unit of analysis is one JCL file with at
least one JOB statement.

| Subject | Role | Job files | License |
|---|---|---:|---|
| AWS CardDemo | primary | 55 | Apache-2.0 |
| OMP COBOL Programming Course | secondary | 37 | CC-BY-4.0 / Apache-2.0 |
| IBM CICS GenApp (commit f6f3f4b) | secondary | 29 | EPL-2.0 |

**Mutation operators.** Ten source-level operators, applied at every applicable
site (no sampling): `SWAP_ADJACENT_STEPS` and `SPLIT_JOB` (ordering);
`DELETE_PRODUCER_STEP`, `RENAME_OUTPUT_DATASET` and
`MOVE_CONSUMER_BEFORE_PRODUCER` (datasets); `REMOVE_COND`,
`ALTER_COND_THRESHOLD` and `REMOVE_IF_GUARD` (return-code guards); plus two
expected-harmless refactorings (`INSERT_COMMENT`, `CHANGE_MSGCLASS`). Mutation
analysis is a standard proxy for real faults (Andrews et al. 2005; Jia & Harman
2011). Whether these operators match real migration defects has not been
established (§8).

**Oracle.** `jcl_oracle` simulates the original and the mutant under a baseline
scenario, every step ending with each relevant return code, and every step
abending. It compares executed steps and return codes, the data version each
read observes, the final dataset catalog, and job termination. It models COND,
IF/THEN/ELSE, abend propagation, allocation and disposition, GDGs, procedures,
IDCAMS catalog operations, common utilities and in-house COBOL file I/O. Programs
it cannot model (DB2/IMS/CICS/TSO) are *opaque*. A mutant whose only possible
difference involves an opaque step is labelled UNDETERMINED and not scored. The
oracle imports nothing from RELIC and receives only the two texts (enforced by
tests). Full specification: `docs/evaluation/ORACLE_SPECIFICATION.md`.

**Scope and accounting.** Every candidate mutant receives exactly one status:
EVALUABLE, OUT_OF_SCOPE (IF/THEN/ELSE guards, which RELIC does not parse; renames
whose only consequence is in other files), INVALID_MUTATION, INFRASTRUCTURE_FAILURE,
or OTHER (undetermined, duplicate).

**Detectors.** All receive only the original text, the mutated text and the
file path: RELIC v1.0.0 as released (primary, blind), RELIC v1.1 (post-hoc
fixes), Baseline E (static contract diff, broken contracts only), Baseline A
(structural dependency-edge diff), Baseline B (corpus-normalised complexity score
> 0.5), and a reference that flags any non-comment text change. Two LLM baselines
(Groq `openai/gpt-oss-120b`, temperature 0) receive the original and modified JCL
(C) or the same plus an automatically extracted dependency summary (D). Their
prompt contains no operator, site or label; calls that fail or do not parse are
excluded, never scored; and all detectors are compared with them on the common
population of mutants both LLM baselines answered
(`docs/evaluation/BASELINES.md`).

**Metrics.** Precision, recall, F1, specificity with Wilson intervals, and F1
intervals from a file-level cluster bootstrap (10,000 resamples).

## 5. Results

### 5.1 Accounting

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

### 5.2 RQ2 — detection (primary subject)

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

Per operator (TP/FN/FP/TN):

<!-- BEGIN GENERATED:table-operators-carddemo -->
| Operator | Contract type | n | violating | RELIC v1.0.0 TP/FN/FP/TN | RELIC v1.1 TP/FN/FP/TN | Baseline A TP/FN/FP/TN | Reference TP/FN/FP/TN |
|---|---|---:|---:|---|---|---|---|
| SWAP_ADJACENT_STEPS | TEMPORAL | 81 | 81 | 78/3/0/0 | 78/3/0/0 | 79/2/0/0 | 81/0/0/0 |
| SPLIT_JOB | TEMPORAL | 81 | 81 | 79/2/0/0 | 79/2/0/0 | 81/0/0/0 | 81/0/0/0 |
| DELETE_PRODUCER_STEP | RESOURCE | 28 | 28 | 26/2/0/0 | 27/1/0/0 | 28/0/0/0 | 28/0/0/0 |
| RENAME_OUTPUT_DATASET | RESOURCE | 11 | 11 | 1/10/0/0 | 8/3/0/0 | 7/4/0/0 | 11/0/0/0 |
| MOVE_CONSUMER_BEFORE_PRODUCER | RESOURCE | 11 | 11 | 11/0/0/0 | 11/0/0/0 | 11/0/0/0 | 11/0/0/0 |
| REMOVE_COND | CONTROL_FLOW | 22 | 21 | 21/0/0/1 | 21/0/0/1 | 0/21/0/1 | 21/0/1/0 |
| ALTER_COND_THRESHOLD | CONTROL_FLOW | 22 | 21 | 0/21/0/1 | 21/0/0/1 | 0/21/0/1 | 21/0/1/0 |
| INSERT_COMMENT | NONE | 30 | 0 | 0/0/0/30 | 0/0/0/30 | 0/0/0/30 | 0/0/0/30 |
| CHANGE_MSGCLASS | NONE | 29 | 0 | 0/0/0/29 | 0/0/0/29 | 0/0/0/29 | 0/0/29/0 |
<!-- END GENERATED:table-operators-carddemo -->

### 5.3 RQ2 — all subjects

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

### 5.4 Sensitivity

<!-- BEGIN GENERATED:table-sensitivity-carddemo -->
| Variant | n | RELIC v1.0.0 F1 / Spec. | RELIC v1.1 F1 / Spec. | Baseline A: structural edge diff F1 / Spec. | Reference: any non-comment text change F1 / Spec. |
|---|---:|---|---|---|---|
| Primary (EVALUABLE, full oracle) | 315 | 0.919 / 1.000 | 0.982 / 1.000 | 0.896 / 1.000 | 0.943 / 0.492 |
| Labels without abend scenarios | 306 | 0.908 / 0.939 | 0.975 / 0.939 | 0.883 / 0.939 | 0.930 / 0.455 |
| + OUT_OF_SCOPE mutants (labelled) | 353 | 0.850 / 1.000 | 0.924 / 1.000 | 0.862 / 1.000 | 0.950 / 0.492 |
| UNDETERMINED counted as violating | 315 | 0.919 / 1.000 | 0.982 / 1.000 | 0.896 / 1.000 | 0.943 / 0.492 |
| UNDETERMINED counted as preserving | 315 | 0.919 / 1.000 | 0.982 / 1.000 | 0.896 / 1.000 | 0.943 / 0.492 |
| Without cosmetic negative operators | 256 | 0.919 / 1.000 | 0.982 / 1.000 | 0.896 / 1.000 | 0.996 / 0.000 |
<!-- END GENERATED:table-sensitivity-carddemo -->

### 5.5 RQ1 — contract recovery against oracle-derived facts

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

### 5.6 LLM baselines (common population)

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

## 6. Analysis

**Observation.** RELIC v1.0.0 flags no behaviour-preserving mutant under the
primary oracle. It misses all COND-threshold changes, most producer-side renames,
and changes involving same-named steps or procedure overrides.
**Interpretation.** The threshold misses come from the diff ignoring guard
parameters (the legacy evaluation hid this by lowering contract confidence by
hand). The rename misses come from a continuation-line rule that merged none of
CardDemo's continuation lines, so most `DISP=` parameters were lost and RESOURCE
contracts were rarely extracted. The RQ1 table shows the same defects
independently of the mutation benchmark.

**Observation.** RELIC v1.0.0 and Baseline E make identical decisions on every
mutant. **Interpretation.** With static evidence only, every contract has the
same confidence, so the "confidence-delta" mechanism cannot fire; the legacy
claim that it distinguishes RELIC from Baseline E does not hold for real source
changes.

**Observation.** The text-difference reference has perfect recall and comparable
F1; RELIC's advantage is specificity. **Interpretation.** Most fault mutants
change behaviour, so recall is cheap on this benchmark. The useful comparison is
RELIC's ability to stay silent on harmless edits and to name the violated
contract — the second is not measured here.

**Observation.** Precision depends on observability. Under the primary oracle
every reorder is behaviour-changing because of abend propagation. Under
normal-completion semantics, some reorders are harmless and RELIC flags them
(TEMPORAL contracts exist between *all* consecutive steps).
**Interpretation.** RELIC's TEMPORAL contracts are conservative. Whether that is
a feature (failure behaviour matters) or noise (order of independent steps does
not) depends on the migration's acceptance criteria.

**LLM baselines.** On the mutants both LLM baselines answered (§5.6), the
dependency-augmented LLM is at least as accurate as RELIC v1.0.0, and the
LLM-only baseline is comparable. **Interpretation.** A capable general model that
sees both versions of a short JCL job can judge most of these changes. RELIC
v1.0.0 has no measurable accuracy advantage over it here, and its remaining
advantages are determinism, cost, the absence of an external service, and an
explicit contract-level explanation. The evidence is weak: coverage is a small
random subsample limited by the API quota, the intervals are wide, there is one
model and one prompt, and the prompt's definition of behaviour makes the harmless
operators easy.

**RELIC v1.1.** The post-hoc fixes (IBM continuation rule, columns 73–80
ignored, COND tests without a step name bound to every earlier step,
parameter-aware diff that flags weakened guards) remove most v1.0.0 misses. They
were designed after the defects were found, so the v1.1 numbers are an upper
estimate and need confirmation on new subjects.

## 7. Correction of earlier results

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

The legacy harness applied mutations to RELIC's own contract graph (deleting or
weakening contracts) and labelled every applied mutation as positive. Detection
was guaranteed, precision was fixed at 1 by construction, and mutants RELIC's
diff could not see were excluded as "not applicable". Its negatives edited
nothing RELIC compares. The legacy LLM prompt contained neither the JCL nor the
change, and failed calls were scored as negatives. The legacy RQ3 "dynamic
validation" used traces derived from RELIC's own parser. All are withdrawn. The
raw legacy outputs are preserved, and every legacy row is classified in
`results/legacy/legacy_mutation_accounting.csv`.

## 8. Threats to validity and limitations

* **Oracle validity.** The oracle models JCL semantics from the reference manual.
  It was not run against z/OS and was not reviewed by an independent practitioner.
  One blind spot shared with RELIC (same-named steps) was found and fixed during
  the evaluation; others may exist.
* **Subjects.** Three small, non-production corpora; CardDemo dominates;
  single-file analysis excludes cross-job dependencies.
* **Faults.** Mutants are synthetic. The earlier claim that they are grounded in
  documented migration failures relied on sources that could not be verified.
* **Post hoc.** Only v1.0.0 is blind.
* **LLM baselines.** One model, one prompt, one sample per mutant; see §5.6 for
  coverage. No validated dynamic evidence.
* **Contract types.** Only TEMPORAL, RESOURCE and CONTROL_FLOW are implemented and
  evaluated; DATA, STATE and ERROR contracts are future work.
* **Statistics.** Mutants are clustered in files; per-operator and secondary-subject
  cells are small.

Details, evidence and next validation steps: `docs/limitations.md`.

## 9. Reproducibility

`make setup && make test && make reproduce && make check` regenerates every
number, table and figure in 5–25 minutes on a laptop. No mainframe,
GnuCOBOL or API key is needed. Raw per-mutant records include the unified diff,
the oracle's evidence and every detector's decision.

## 10. Conclusion

On a source-level benchmark labelled by an independent JCL semantics oracle,
the released RELIC detects most behaviour-changing edits to CardDemo jobs, does
not flag harmless edits under the primary oracle, and misses whole classes of
changes because of two implementation defects. Its advantage over trivial change
detection is specificity rather than recall, and on a random subsample a
general-purpose LLM given both versions of the job was at least as accurate. The evaluation design, the oracle
and the complete raw data are the most reusable outcome of this work. External
validity, oracle validity against real execution, and a full-coverage,
multi-model comparison with LLM-based review remain open.

## References

- Andrews, J. H., Briand, L. C., Labiche, Y. Is mutation an appropriate tool for testing experiments? ICSE 2005. doi:10.1109/ICSE.2005.1553583
- Deknop, C., Fabry, J., Mens, K., Zaytsev, V. Generating customised control flow graphs for legacy languages with semi-parsing. ICSME 2022. doi:10.1109/ICSME55016.2022.00072
- Ernst, M. D., et al. The Daikon system for dynamic detection of likely invariants. Science of Computer Programming 69, 2007. doi:10.1016/j.scico.2007.01.015
- Felsing, D., Grebing, S., Klebanov, V., Rümmer, P., Ulbrich, M. Automating regression verification. ASE 2014. doi:10.1145/2642937.2642987
- IBM. z/OS MVS JCL Reference (SA23-1385).
- Jia, Y., Harman, M. An analysis and survey of the development of mutation testing. IEEE TSE 37(5), 2011. doi:10.1109/TSE.2010.62
- Lahiri, S. K., Hawblitzel, C., Kawaguchi, M., Rebêlo, H. SYMDIFF: A language-agnostic semantic diff tool for imperative programs. CAV 2012. doi:10.1007/978-3-642-31424-7_54
- Lorenzoli, D., Mariani, L., Pezzè, M. Automatic generation of software behavioral models. ICSE 2008. doi:10.1145/1368088.1368157
- Meyer, B. Applying "Design by Contract". Computer 25(10), 1992. doi:10.1109/2.161279
- Subject systems: AWS CardDemo; Open Mainframe Project COBOL Programming Course; IBM CICS GenApp (URLs in `paper/references.bib`).
