# Reviewer rubric - JCL behaviour-preservation review

You are given pairs of z/OS JCL jobs: an **original** and a **modified** version (a unified diff and the
two full texts are on each card). For each case decide whether the modification **preserves the
observable behaviour of the job**. Work alone, from the card only. Do not run any analysis tool on the
cases and do not discuss cases with other reviewers until the study coordinator says all reviews are in.
Use your own knowledge of z/OS JCL and the IBM *MVS JCL Reference* (you may look things up; note it in
`evidence` when a reading of the manual decided the case).

## 1. What "behaviour-preserving" means here

Two versions are **EQUIVALENT** if no observable below differs in **any** of the scenarios in section 2.
They are **DIFFERENT** if at least one observable differs in at least one scenario.

Observables (the only things that count):

| # | Observable | Examples of a difference |
|---|---|---|
| O1 | **Execution** - for every step: runs / is bypassed (COND, IF) / is not reached / is flushed after an abend; and the return code it ends with | a step that used to be skipped after RC 8 now runs; a step runs after an abend that used to flush it |
| O2 | **Data read** - for each step, *which version* of each dataset it reads (i.e. which earlier step wrote it, or whether it is the pre-existing copy) | a consumer now runs before its producer; a producer was deleted/renamed so the consumer reads something else or nothing |
| O3 | **Final catalog** - which permanent datasets / members exist after the job and which version they hold | a dataset is no longer kept, or is created under a different name |
| O4 | **Termination** - normal end vs. JCL error (e.g. dataset not found, `NEW` dataset already exists) | the job now fails allocation |

Not observable (never a reason for DIFFERENT): comments, blank/sequence columns, `MSGCLASS` / SYSOUT print class,
job-log destination, changes to text that is never executed or never read.

## 2. The two questions you must answer

**Q1 - normal completion.** Assume every step ends with return code 0 and nothing abends. Assume every
dataset that a step references with `OLD`/`SHR` exists before the job *unless* this job (in the original
version) creates it earlier; datasets the original job creates (`DISP=NEW`, IDCAMS `DEFINE`) do not exist
before the job; `&&` temporary datasets never pre-exist and vanish at job end. Is O1-O4 identical?
Answer `SAME`, `DIFFERENT` or `CANNOT_DETERMINE`.

**Q2 - failure scenarios (single fault).** Consider each situation in which exactly **one** step ends with a
non-zero return code (any value, in particular values around the constants appearing in `COND=` / `IF`
tests, and 4, 8, 12, 16) **or abends**; all other steps behave normally. Is O1-O4 identical in **every**
such situation? Answer `SAME`, `DIFFERENT` or `CANNOT_DETERMINE`.
*A job can be SAME under Q1 and DIFFERENT under Q2 (typical: swapping two independent steps changes which
step is flushed after an abend).*

**overall_label** = `DIFFERENT` if Q1 or Q2 is DIFFERENT; `EQUIVALENT` if both are SAME; otherwise
`CANNOT_DETERMINE`. (Do not answer `CANNOT_DETERMINE` merely because a case is hard: use it only if the
JCL text genuinely does not allow a decision, and say what is missing in `evidence`.)

## 3. Ground rules

1. **Unknown programs.** If you cannot see what a program does, assume it reads datasets coded `SHR`/`OLD`
   and writes datasets coded `NEW`/`MOD`/`OLD` in its DD statements, and has no other effect. If the case
   can only be decided by assuming more (DB2 tables, CICS, queues, FTP targets), answer `CANNOT_DETERMINE`
   for that question and write which side effect matters.
2. **Return codes of utilities.** You may assume any step *can* fail with any return code in the Q2 scenario
   (you are asked about the JCL's logic, not about whether a given utility realistically produces that code).
   If you think this is unreasonable for a particular case, still answer the question as asked and add
   `definition_disagrees` plus a sentence in `evidence`.
3. **Several JOB cards in one file.** Each JOB card is a separately scheduled job. Assume nothing about
   relative order or failure propagation *between* jobs: any serial order of the jobs may occur and a
   failure in one job does not stop another. Compare the *set* of possible behaviours.
4. **Procedures and overrides.** If a step invokes a procedure, the procedure text is on the card when it
   was available in the corpus; apply symbolic parameters, `COND.procstep`, and `procstep.ddname`
   overrides yourself. If the procedure is not on the card, treat that step as an unknown program (rule 1).
5. **Same-named steps.** Distinguish steps by position and content when names repeat.
6. **IBM defaults you rely on** (first-step `COND` is ignored, default `DISP` status/disposition, `MOD` of
   a missing dataset, `IF RC` semantics): if the outcome depends on one, say which in `evidence`.
7. **Disagree with the question, not with yourself.** Record what you believe is true of real z/OS
   behaviour; do not try to guess what any tool would say.

## 4. Filling the form

One row per case in `responses_<yourID>.csv` (columns as in `responses_template.csv`):

| column | allowed values |
|---|---|
| `reviewer_id` | your assigned id (e.g. `REV-A`) - same on every row |
| `q1_normal_completion`, `q2_failure_scenarios` | `SAME`, `DIFFERENT`, `CANNOT_DETERMINE` |
| `overall_label` | `EQUIVALENT`, `DIFFERENT`, `CANNOT_DETERMINE` |
| `confidence` | `1` guessing, `2` fairly sure, `3` certain |
| `evidence` | 1-2 sentences naming the step / DD / line that decides it (mandatory for DIFFERENT and for CANNOT_DETERMINE) |
| `minutes_spent` | integer |

Do not edit `case_id`. Do not leave `overall_label` blank - a blank row is treated as "not reviewed".
