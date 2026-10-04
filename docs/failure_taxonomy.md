# Failure Classes Simulated by the Mutation Operators

## Status of the evidence (read first)

An earlier version of this document presented the failure categories as
"empirically grounded", citing verbatim quotations from AWS and IBM
documentation, "Knorr 2019" and "Gula 2020" postmortems, a chapter count from
Ulrich & Newcomb (2010), and "CardDemo Issue #12". During the October 2026
remediation these sources could not be verified. CardDemo #12 is a pull request
that renames a data file; it does not describe a job-ordering failure. The
quotations could not be found. That version is archived as
`docs/archive/2026-08_pre_remediation/docs/failure_taxonomy_v1_unverified_sources.md`
and **must not be cited**.

What remains is a weaker, honest claim. The three failure classes below are the
ways a re-implementation can break the rules that JCL enforces *by its semantics*
(IBM *z/OS MVS JCL Reference*). These rules are what a migration has to carry
over explicitly: step sequence, dataset allocation and disposition, and
return-code guards. Whether and how often these failures occur in real
migrations has **not** been established by this project. The mutants are
synthetic. Mutation analysis is a standard way to approximate faults
(Jia & Harman 2011; Andrews, Briand & Labiche 2005), but how well synthetic
mutants represent real migration defects is an open question here.

## F1 — Ordering

JCL runs the steps of a job in order. A later step may depend on an earlier one
through data (it reads what the earlier one wrote), control (its COND or IF
tests the earlier step's return code), or failure semantics (it is bypassed if
the earlier step abends). If a migrated job reorders steps, splits them into
separately scheduled units, or drops a dependency edge, any of these can
change.

Operators: `SWAP_ADJACENT_STEPS`, `SPLIT_JOB`.

## F2 — Dataset availability and identity

A step that allocates a dataset with `DISP=OLD/SHR` fails if the dataset does
not exist. A step reads whatever version the last writer produced. A migration
that drops a producing step, schedules a consumer first, or renames one side of
a producer–consumer pair changes what is read or fails allocation.

Operators: `DELETE_PRODUCER_STEP`, `MOVE_CONSUMER_BEFORE_PRODUCER`, `RENAME_OUTPUT_DATASET`.

## F3 — Return-code guards

`COND=` and `IF/THEN/ELSE` decide whether a step runs, based on earlier return
codes and abends. A migration that drops a guard, or re-implements it with a
different threshold or operator, changes which steps run after a failure.

Operators: `REMOVE_COND`, `ALTER_COND_THRESHOLD`, `REMOVE_IF_GUARD`.

## Expected-harmless refactorings

`INSERT_COMMENT`, `CHANGE_MSGCLASS` (output class only). These are included so
that the benchmark contains changes a precise detector should not flag.

## Out of scope

Record-format changes in copybooks, initialisation of program state,
transaction/commit boundaries and scheduler calendars are plausible failure
classes. RELIC does not model them and they are not evaluated.

Operator definitions and site rules: [evaluation/BENCHMARK.md](evaluation/BENCHMARK.md).
