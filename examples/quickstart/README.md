# RELIC Quickstart Example

This example walks through the core RELIC pipeline on a minimal
two-step JCL job. It demonstrates:

1. Parsing JCL artifacts
2. Extracting TEMPORAL behavioral contracts
3. Building a Behavioral Contract Graph (BCG)
4. Editing the JCL source (a migration that weakens a COND guard)
5. Detecting the weakened contract by diffing the two BCGs
6. Checking the verdict against the independent oracle (`jcl_oracle`)

**No GnuCOBOL required.** This example uses static analysis only.

---

## Prerequisites

```bash
# From the repository root
make setup
```

---

## The Artifact

File: `examples/quickstart/SAMPLEJOB.jcl`

```jcl
//SAMPLEJOB JOB (ACCT),'QUICKSTART',CLASS=A,MSGCLASS=X
//*
//* Step 1: Initialize the output file
//INITFILE EXEC PGM=IEFBR14
//OUTFILE  DD  DSN=MY.OUTPUT.FILE,DISP=(NEW,CATLG),
//             SPACE=(CYL,(1,1)),UNIT=SYSDA
//*
//* Step 2: Process transactions (depends on OUTFILE being ready)
//PROCESS  EXEC PGM=CBACT01C,COND=(4,GT,INITFILE)
//INPUT    DD  DSN=MY.INPUT.FILE,DISP=SHR
//OUTPUT   DD  DSN=MY.OUTPUT.FILE,DISP=OLD
```

This JCL encodes two implicit behavioral obligations:
1. **TEMPORAL**: INITFILE must execute before PROCESS (`INITFILE ≺ PROCESS`)
2. **CONTROL_FLOW**: PROCESS is conditional on INITFILE returning RC ≤ 4

---

## Running the Example

```bash
.venv/bin/python examples/quickstart/run_quickstart.py
```

## Expected Output (abridged)

```
Change under review:  COND=(4,GT,INITFILE)  ->  COND=(2,GT,INITFILE)

--- RELIC v1.0.0 (as released)
  contracts in original BCG: 3
    [TEMPORAL    ] INITFILE --PRECEDES--> PROCESS
    [RESOURCE    ] INITFILE --PRODUCES_BEFORE_CONSUMES--> PROCESS
    [CONTROL_FLOW] INITFILE --MUST_NOT_FOLLOW_ON_ERROR--> PROCESS  (RC test: 4,GT)
  diff: broken=0 modified=0 preserved=3
  verdict: no risk reported

--- RELIC v1.1 (post-hoc fixes)
  ...
  diff: broken=0 modified=1 preserved=2
  verdict: RISK — 1 contract(s) broken or weakened

--- Independent oracle (jcl_oracle)
  label: DIFFERENT  (differing scenarios: 2 of 19)
    [INITFILE=2] execution: [('PROCESS', 'BYPASS', None), ('PROCESS', 'RUN', 0)]
```

---

## What This Shows

- Under IBM COND semantics a step is *bypassed* when its test is true.
  `COND=(4,GT,INITFILE)` bypasses PROCESS when INITFILE ends with RC < 4;
  `COND=(2,GT,INITFILE)` only when RC < 2, so PROCESS now also runs after RC 2 or 3.
  The oracle confirms the behaviour change.
- **RELIC v1.0.0** (as released) misses it: its BCG diff compared contracts only by
  (type, subject, predicate, object) and ignored the COND threshold. This is the
  defect behind its 0% recall on COND-threshold changes in the benchmark.
- **RELIC v1.1** compares guard parameters and reports the contract as weakened.
  v1.1 was written after this defect was found, so its benchmark results are post hoc.
  It reports only *weakened* guards: a change that makes a guard stricter (e.g.
  `COND=(4,GT)` → `COND=(16,GT)`) also changes behaviour but is not reported.

There is no "confidence-delta" mechanism in this example. The earlier version of
this quickstart showed one, but it came from a harness that edited RELIC's own
contract graph by hand, and it is withdrawn.

---

## Files in This Directory

```
examples/quickstart/
├── README.md               This file
├── SAMPLEJOB.jcl           Minimal example JCL artifact
└── run_quickstart.py       End-to-end demonstration script
```
