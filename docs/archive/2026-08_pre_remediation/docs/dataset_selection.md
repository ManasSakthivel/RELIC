# Dataset Selection and Execution Evidence Strategy
## LEGACY-CONTRACT Phase 0 — Public Datasets and Tracing Options

---

## DATASET POLICY (STRICT)

All datasets must be:
- Publicly available
- Legally usable (open-source license, research-permissive)
- Reproducible
- Documented with artifact types, size, license, version

**PROHIBITED:** IBM proprietary source, AD-Scan source, any customer data, internal IBM benchmarks.

---

## PRIMARY DATASET: AWS CardDemo

**Source:** https://github.com/aws-samples/aws-mainframe-modernization-carddemo  
**License:** Apache 2.0 (confirmed)  
**Version:** Commit tracked in datasets/carddemo/DATASET_VERSION.txt  
**Access date:** 2025

### Artifact inventory

| Artifact type | Count (approx.) | Notes |
|---------------|----------------|-------|
| COBOL programs (.cbl) | ~30 | Online + batch programs |
| JCL files (.jcl) | ~15 | Batch job streams |
| Copybooks (.cpy) | ~20 | Shared record structures |
| VSAM file definitions | ~10 | In JCL DD statements |
| BMS maps (.bms) | ~10 | CICS screen definitions (out of scope Paper 1) |
| README + documentation | Multiple | Architecture documentation |

### Executability
The CardDemo application can be run on:
1. z/OS with COBOL and JCL (requires mainframe access — not required for Paper 1)
2. IBM Z & Cloud Modernization Stack (requires subscription — not used)
3. **GnuCOBOL** (open-source COBOL compiler, free) for subset of batch programs
4. Simulated batch execution via instrumented GnuCOBOL + shell scripts

### Why CardDemo is suitable
- Contains realistic JCL job chains with file dependencies
- Contains COBOL programs with CALL chains, READ/WRITE, error paths
- Has copybooks shared across multiple programs
- Has documented batch job relationships (CBACT01C → CBACT02C dependencies)
- Has publicly documented migration use cases
- Legally unrestricted for research use

### Limitations (documented)
- CICS interactive programs not in Paper 1 scope
- VSAM semantics differ from UNIX file semantics (documented threat to validity)
- Not a production system — behavioral complexity may be lower than real enterprise applications
- No production execution logs available — traces must be generated from instrumented execution

---

## SECONDARY DATASET: Public COBOL Repositories

**Source:** GitHub search: language:COBOL stars:>20  
**Examples:**
- github.com/openmainframeproject/cobol-programming-course (Apache 2.0)
- github.com/openmainframeproject/COBOL-Sample-Programs (Apache 2.0)
- github.com/IBM/cobol-optimization-research (MIT)

**Use:** Additional COBOL programs for generalization testing (held-out set)  
**Limitation:** No accompanying JCL in most repositories — usable for COBOL-level contract analysis only

---

## TERTIARY DATASET: Public JCL Repositories

**Source:** GitHub search: language:JCL  
**Examples:**
- github.com/openmainframeproject/zorow (JCL samples, Apache 2.0)
- Sample JCL in IBM Z documentation (publicly available, non-proprietary)

**Use:** Additional JCL for JCL parser validation  
**Limitation:** Isolated JCL without matching COBOL — limited for cross-artifact analysis

---

## EXECUTION EVIDENCE STRATEGY

### Option 1 — GnuCOBOL Instrumented Execution (PRIMARY)

**Description:** Compile CardDemo COBOL programs with GnuCOBOL, add instrumentation wrappers around CALL, READ, WRITE, OPEN, CLOSE operations, execute with controlled input data, capture execution event stream.

**Implementation:**
1. GnuCOBOL compiler: `cobc -x` for batch programs
2. Instrumentation via GnuCOBOL `CALL "CBL_OC_GETOPT"` or pre/post-execution hooks
3. Execution event capture via modified COBOL COPY module that writes execution events to log
4. Normalize events into BCG ExecutionEvent schema

**Advantages:**
- Fully controlled
- Reproducible
- No proprietary tools
- Apache 2.0 compatible
- Generates real execution evidence (not simulated)

**Limitations:**
- GnuCOBOL is not z/OS — subtle semantic differences possible (documented as threat)
- JCL cannot be executed natively — batch job simulation required
- Must be explicitly labeled: "instrumented execution evidence, GnuCOBOL environment"

### Option 2 — Synthetic Trace Generation (SECONDARY FALLBACK)

**Description:** If GnuCOBOL execution is infeasible for a test case, generate synthetic traces from static analysis, explicitly labeled as synthetic.

**Implementation:** `src/dynamic_analysis/synthetic_trace_generator.py`

**Advantages:** Always available, reproducible

**Limitations:** Not execution evidence — must be clearly labeled `extraction_method = SYNTHETIC_STATIC`

**CRITICAL:** Synthetic traces must NEVER be presented as execution evidence. The system must refuse to set ValidationState = DYNAMICALLY_OBSERVED for contracts supported only by synthetic traces.

### Option 3 — JCL Batch Job Simulation

**Description:** Simulate JCL batch job execution order using shell scripts that mirror the JCL job step sequence, file dependency chain, and COND parameter logic.

**Implementation:** `src/dynamic_analysis/jcl_batch_simulator.py`

**Output:** Execution events capturing job start/end ordering, file access events

**Advantages:** Captures job-level temporal ordering evidence

**Limitations:** Does not capture COBOL-level internals — job-level only

---

## DYNAMIC EVIDENCE ADAPTER ARCHITECTURE

The system implements a `DynamicEvidenceAdapter` abstraction with multiple implementations:

```
DynamicEvidenceAdapter (abstract)
├── GnuCOBOLTraceAdapter       — GnuCOBOL execution logs
├── JCLSimulatorAdapter        — JCL batch simulation events
├── SyntheticAdapter           — Synthetic traces (clearly labeled)
└── [Future: SMFAdapter]       — z/OS SMF records (if publicly available data found)
```

All adapters normalize to the common `ExecutionEvent` schema before BCG ingestion.

---

## DATASET SPLITS

| Split | Systems | Traces | Use |
|-------|---------|--------|-----|
| Development | CardDemo batch programs (first 70%) | GnuCOBOL + JCL sim | System development + tuning |
| Validation | CardDemo batch programs (remaining 30%) | GnuCOBOL + JCL sim | Threshold tuning, hyperparam |
| Held-out | Public COBOL repos programs | Generated where possible | Generalization evaluation |

**Strict rule:** Held-out system artifacts and traces must not influence:
- Contract taxonomy
- Confidence thresholds
- Prompt design
- Mutation operators
- Model selection

---

## REPRODUCIBILITY REQUIREMENTS

For each dataset:
- `datasets/carddemo/DATASET_VERSION.txt` — git commit hash
- `datasets/carddemo/ARTIFACTS.json` — inventory of all artifacts with checksums
- `traces/dev/TRACE_GENERATION_LOG.txt` — exact commands used to generate traces
- `datasets/README.md` — full documentation of all datasets, licenses, limitations

Trace generation must be fully scriptable:
```
make generate-traces
```
This command must reproduce all development and validation traces from source.
