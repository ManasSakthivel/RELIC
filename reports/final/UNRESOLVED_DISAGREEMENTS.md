# The 14 unresolved oracle cases (v1.1)

Classification by the author of this report, from the diffs and the oracle's own recorded evidence.
It is NOT an independent adjudication. No mainframe practitioner has reviewed these cases.
Original labels are unchanged. Nothing here was relabelled except C1 (see BENCHMARK_LABEL_AUDIT.md).

| Case | Expected | Oracle | Change in the artefact | Class | What would settle it |
|---|---|---|---|---|---|
| sembench_117, 120, 126, 129 | CHANGING | EQUIVALENT | DISP=SHR → DISP=OLD (input DD) | S1 scope: concurrency | Decide whether enqueue behaviour under contention is in the benchmark's observable set |
| sembench_118, 121, 124, 127, 130 | CHANGING | EQUIVALENT | DISP=(NEW,CATLG,…) → (NEW,KEEP,…) | S1 scope: catalog | Decide whether post-job catalogue state is in scope; check against the z/OS DISP reference |
| sembench_165 | CHANGING | EQUIVALENT | IDCAMS PRINT COUNT(100) → COUNT(10) | O oracle gap | The oracle does not model SYSPRINT record counts. Confirm the input dataset has more than 10 records (not in the artefact) |
| sembench_172 | CHANGING | UNDETERMINED (abstains) | Adds `SELECT MEMBER=NOTFOUND` to an IEBCOPY step | A undetermined | Needs an IEBCOPY return-code model; the opaque step is CPYPDS |
| sembench_078 | PRESERVING | DIFFERENT (25/25 scenarios) | Renames STEP10 → ST10X with internal references | S2 scope: step names | Decide whether step names are observable (job log text). Label is PRESERVING if they are not |
| sembench_079 | PRESERVING | DIFFERENT (46/46 scenarios) | Renames STEP1 → STP1REN, COND reference updated | S2 scope: step names | As above |
| sembench_036 | PRESERVING | DIFFERENT (10/15 scenarios) | PARM='NODECK,OBJECT,LIST' → PARM=(NODECK,OBJECT,LIST) | P JCL syntax | Check the IBM JCL reference: are the two PARM forms equivalent for IGYCRCTL? The oracle hashes the PARM text |

## Reading the table

- Nine of the fourteen (S1, 117–130) rest on out-of-model effects. Their CHANGING labels are defensible only if the benchmark's definition of behaviour includes enqueue or catalogue state. The oracle's EQUIVALENT verdict is correct *within its own model*. The published definition must settle this, and the label cannot be settled by the artefact alone.
- sembench_165 is the strongest candidate for a genuine oracle error, but it depends on a dataset fact outside the artefact.
- sembench_078/079 and 036 are PRESERVING labels that the oracle contradicts. Their correctness depends on scope and on a JCL syntax fact, respectively.
- No case here was resolved by inspection alone. Every class requires either a written scope decision or an external reference, and an independent reviewer.

## What this means for the headline

The sensitivity analysis (results/final/statistics/sensitivity_three_way.json) shows the sign of the RELIC V2 vs normalized-text-B gap is unchanged across all four label sets. Its size ranges from −0.17 (L3, oracle-relabelled) to −0.34 (L1). The headline must report this range, not a single number.
