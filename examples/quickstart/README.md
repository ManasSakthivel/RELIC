# Quickstart Example

This example walks through the core LEGACY-CONTRACT pipeline on a minimal
two-step JCL job. It demonstrates:

1. Parsing JCL artifacts
2. Extracting TEMPORAL behavioral contracts
3. Building a Behavioral Contract Graph (BCG)
4. Applying a mutation
5. Detecting the contract violation with BCGDiff

**No GnuCOBOL required.** This example uses static analysis only.

---

## Prerequisites

```bash
# From the repository root
pip install poetry
poetry install
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
cd examples/quickstart
python3.11 run_quickstart.py
```

---

## Expected Output

```
=== LEGACY-CONTRACT Quickstart ===

Step 1: Parsing SAMPLEJOB.jcl...
  Found job: SAMPLEJOB
  Found 2 steps: INITFILE, PROCESS

Step 2: Building BCG...
  Entities (V): 4 (1 JOB, 2 STEPs, 1 DATASET)
  Contracts (C): 2
    [TEMPORAL]      INITFILE --MUST_PRECEDE--> PROCESS
                    provenance: SAMPLEJOB.jcl:8, extraction=DETERMINISTIC, confidence=1.000
    [CONTROL_FLOW]  PROCESS --CONDITIONAL_ON--> INITFILE  (threshold RC=4, op=GT)
                    provenance: SAMPLEJOB.jcl:8, extraction=DETERMINISTIC, confidence=1.000

Step 3: Applying ALTER_ERROR_BRANCH mutation...
  Original:  COND=(4,GT,INITFILE)   [static_support=1.000]
  Mutated:   COND=(16,GT,INITFILE)  [static_support=0.700]

Step 4: Running BCGDiff...
  BROKEN contracts:    0
  MODIFIED contracts:  1
    CONTRACT: PROCESS --CONDITIONAL_ON--> INITFILE
    ORIGINAL confidence:  1.000
    MUTATED  confidence:  0.700
    DELTA:                0.300  > threshold 0.050
    RISK LEVEL:           HIGH (confidence-delta exceeded threshold)

=== RISK DETECTED ===
The ALTER_ERROR_BRANCH mutation weakened a CONTROL_FLOW contract.
PROCESS will now execute even when INITFILE returns a soft error (RC 5–16).
This mutation is invisible to structural dependency analysis.
```

---

## What This Shows

- **Structural analysis** sees the same dependency graph in both versions
  (PROCESS still follows INITFILE; both reference the same DATASET).
  It would produce 0 risk items.

- **BCG with confidence-delta** detects the weakening because the
  `static_support` of the CONTROL_FLOW contract dropped from 1.000 to 0.700.
  The `BCGDiff.modified` list contains this contract; `RiskDetector` fires.

This is the discriminating finding of the paper: confidence-delta detection
catches behavioral weakening that structural analysis misses.

---

## Files in This Directory

```
examples/quickstart/
├── README.md               This file
├── SAMPLEJOB.jcl           Minimal example JCL artifact
└── run_quickstart.py       End-to-end demonstration script
```
