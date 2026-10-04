# Ground-Truth Oracle Specification (`jcl_oracle`)

The ground truth for the mutation benchmark is produced by `jcl_oracle/`, an
execution-semantics simulator for z/OS JCL written for this evaluation. This
document states what the oracle computes, what it does not model, and why it
is independent of RELIC.

## 1. Source of ground truth

For a JCL file `O` and a mutant `M`, the label is

* **VIOLATION** (`DIFFERENT`) if some scenario yields a different observable
  behaviour for `O` and `M`;
* **NO VIOLATION** (`EQUIVALENT`) if no scenario does and no opaque step is affected;
* **not scored** (`UNDETERMINED`) if no modelled observable differs but a step
  whose program the oracle cannot model changed position, presence, job or DD set.

The operator that produced `M` plays no role in the label. A "fault" operator can
produce an equivalent mutant (labelled NO VIOLATION) and a "refactoring" operator
could produce a behaviour change (labelled VIOLATION).

## 2. Semantics implemented (IBM z/OS MVS JCL Reference)

| Construct | Modelled behaviour |
|---|---|
| Statement format | columns 1–71; 73–80 ignored; `//*` comments; `/*` delimiters; null statement; continuation when the operand field ends with `,` and the next `//` line has a blank in column 3 (columns 4–16; deeper indentation accepted) |
| In-stream data | `DD *` (ends at `/*` or any `//`), `DD DATA` (ends at `/*`), `DLM=` |
| Step order | document order within a job |
| `EXEC COND=` | step bypassed if any test `code op RC` is true; test without step name applies to every previously executed step; tests naming a step that did not run are ignored; `EVEN` / `ONLY` |
| `JOB COND=` | once a test is true, remaining steps are bypassed |
| Abend | after an abend, steps run only with `COND=EVEN/ONLY` or inside an `IF` that tests `ABEND`/`RUN` |
| `IF/THEN/ELSE/ENDIF` | `RC` = highest RC of executed steps; `step.RC` false if the step did not run; `ABEND`, `step.ABEND`, `step.RUN`; `NOT/AND/OR` |
| Symbols | `SET`, PROC defaults, EXEC overrides; `&&` temporary names untouched |
| Procedures | in-stream PROCs and cataloged PROCs found in the subject corpus are expanded (procedure steps, `COND.procstep`, DD overrides, DD additions); a procedure not in the corpus is an opaque step |
| Allocation | `DISP=OLD/SHR` of a non-existent dataset → JCL error, job ends; `DISP=NEW` of an existing dataset → JCL error (SMS-managed assumption); `MOD` creates if absent |
| Disposition | `NEW` defaults to `DELETE`, existing datasets to `KEEP`; abnormal disposition on abend; `DELETE` removes the whole dataset (all PDS members); temporaries deleted at end of job |
| GDG | relative generations are distinct keys (`X(+1)`, `X(0)`) as resolved at job start |
| IDCAMS | `DELETE` (RC 8 if absent), `DEFINE CLUSTER/GDG/AIX/PATH` (RC 12 if present), `REPRO`, `BLDINDEX`, `PRINT`, `VERIFY`, `LISTCAT`, `ALTER [NEWNAME]`, `SET MAXCC/LASTCC`, and the form `IF LASTCC/MAXCC op n THEN SET … = m`; any other command → opaque |
| Utilities | `IEFBR14`, `IEBGENER/ICEGENER`, `SORT/ICEMAN/DFSORT/SYNCSORT` (incl. `OUTFIL FNAMES=`), `IEBCOPY` (`COPY OUTDD=/INDD=`), COBOL compiler (`IGYCRCTL`), binder (`IEWL/IEWBLINK/HEWL`) |
| In-house COBOL programs | file access from `SELECT … ASSIGN TO dd` and `OPEN INPUT/OUTPUT/I-O/EXTEND`; programs containing `EXEC SQL/CICS/DLI`, IMS or MQ calls are marked opaque |
| Program library | a step reads member `LIB(PGM)` of its STEPLIB/JOBLIB, so a compile/link step that writes that member is a data dependency |
| Opaque programs | TSO batch (`IKJEFT01/1A/1B`), SDSF, IMS (`DFSRRC00`), FTP, CICS/DB2 utilities, unknown programs: access from DISP (`NEW/MOD` write, `OLD` read+write, `SHR` read) and the step is flagged opaque |

Return codes are partly **endogenous** (IDCAMS condition codes) and partly
**injected** by the scenario.

## 3. Scenarios and observables

Scenario set (primary, `full`): the baseline (no injected failure); for every step
of either version and every RC value in {4, 8, 12, 16} ∪ {c−1, c, c+1 for every
COND/IF constant c of either version} (1 ≤ v ≤ 4095), the step ending with that RC;
and every step abending. The sensitivity set `no_abend` omits the abend scenarios.

Observables compared per scenario:

1. **execution** — for every step: ran / bypassed / not reached / JCL error / abend, and its RC;
2. **dataflow** — for every read: which version of which dataset (versions are content
   hashes of the writer's identity and of everything the writer read, so a changed
   upstream input propagates);
3. **final catalog** — existence and version of every permanent dataset at end of job;
4. **termination** — normal end or JCL error (step, reason).

Files containing several JOB statements (only produced by the `SPLIT_JOB` operator)
are simulated in every serial job order; the label compares the *sets* of behaviours.

Steps are identified by name. Steps that share a name are identified by name plus
a hash of their content (program, PARM, DDs, in-stream data — not COND), so a swap
of two same-named steps is not hidden by positional numbering.

**Initial catalog.** A dataset exists before the job unless its first access in the
**original** job creates it (`DISP=NEW`, IDCAMS `DEFINE`); temporaries never exist.
Both versions run against this same initial catalog. Sanity check
(`metrics.json → oracle_sanity`): every original file of every subject runs to
normal completion in the baseline scenario.

## 4. What RELIC sees and what the oracle sees

| | RELIC (system under test) | Oracle |
|---|---|---|
| Input | original JCL text, mutated JCL text, artifact path | the same two texts, plus the subject's PROC library and COBOL sources |
| Mutation operator / site / intent | never | never |
| Code | `src/legacy_contract` (parser, extractor, BCG, diff, risk detector) | `jcl_oracle` (own lexer, model, simulator, judge) |
| Notion of behaviour | contract graph: step order, DD-based producer/consumer pairs, COND guards | simulated execution under scenarios |
| Output used | flagged / not flagged | DIFFERENT / EQUIVALENT / UNDETERMINED |

## 5. Why the evaluation is independent

* `jcl_oracle` imports nothing from `legacy_contract`, `baselines`, `relic_eval` or
  `scripts` (enforced by `tests/oracle/test_oracle_independence.py`).
* The oracle never reads RELIC output, and the detectors never receive the
  operator, site, intent or label (enforced by `tests/evaluation/test_blindness.py`;
  the placeholder record RELIC's API requires does not affect its decision).
* Labels are derived from execution semantics, not from contracts. The oracle
  models constructs RELIC ignores (IF/THEN/ELSE, procedures, IDCAMS catalog
  operations, program file I/O, dispositions, abend propagation), so RELIC can be
  wrong in both directions.
* The oracle's semantics were checked against hand-derived expectations
  (`tests/oracle/test_oracle_semantics.py`, 24 cases).

## 6. Limits of independence (stated, not hidden)

1. **Same author, same period.** The oracle was written by the same remediation
   effort that evaluates RELIC; it has not been reviewed by a JCL practitioner and
   has not been validated against real z/OS execution. Its semantics follow the
   IBM reference as read by the author.
2. **Shared JCL reading of the mutation generator.** The generator
   (`relic_eval/mutate.py`) uses the oracle's lexer to locate sites. This affects
   *which* mutants exist, not their labels: labels come from simulating the actual
   mutant text.
3. **A defect was found and fixed during evaluation.** The first version identified
   same-named steps positionally, which made 13 GenApp swaps look equivalent — a
   blind spot shared with RELIC. It was fixed (§3) before the reported run, and the
   fix is covered by a test. Other shared blind spots may remain.
4. **Modelling assumptions.** Single-fault scenarios only; SMS-managed allocation;
   RC domain limited to the values above; IDCAMS beyond the listed commands, ICETOOL,
   DB2/CICS/IMS/TSO side effects and dynamic allocation are not modelled (opaque).
5. **Strict observability.** Under abend propagation, *any* reorder of two steps is
   observable (the step that originally followed an abending step is bypassed;
   after the swap it has already run). This is correct JCL semantics but makes
   reorderings positive by default. The `no_abend` sensitivity analysis reports
   results when only normal completion is observable.
6. **Not a human-annotated ground truth.** No independent human labelling was
   performed. A sample audit by a mainframe engineer is listed as the next
   validation step in `docs/FINAL_RESEARCH_READINESS_REPORT.md`.
7. **Remaining step-identity assumptions.** Uniquely named steps are matched across
   versions by name, so renaming a step is seen as removing one step and adding
   another (no operator renames steps). Same-named steps are matched by a content
   hash that excludes COND; truly identical same-named steps are matched by
   occurrence order, which is harmless because exchanging identical steps changes
   nothing observable. Same-named steps whose content *and* position both change
   in one mutant could be paired differently from a human reading.
