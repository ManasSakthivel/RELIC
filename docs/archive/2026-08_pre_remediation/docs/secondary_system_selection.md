# RELIC — Secondary System Selection Report

**Sprint:** Final Closure Sprint  
**Date:** 2026-08-30  
**Decision:** SECOND SYSTEM NOT SCIENTIFICALLY VALIDATED  

---

## Candidates Considered

### Candidate 1: public_cobol (COBOL Programming Course — Open Mainframe Project)

**Source:** https://github.com/openmainframeproject/cobol-programming-course  
**License:** Apache 2.0  
**JCL files:** 43 | **Multi-step JCL:** ~3 | **COBOL programs:** 7  
**Status:** Already in repository at `datasets/public_cobol/`

**Strengths:**
- Available, licensed for academic use
- Independent from CardDemo (different organization, purpose)
- Some COBOL programs are standalone-executable (EMPPAY, DEPTPAY)

**Weaknesses:**
- 40/43 JCL files are 1-step pedagogical exercises (no TEMPORAL contracts)
- The 3 multi-step files are COMPILE-LINK-GO patterns (no behavioral COND= guards)
- Zero meaningful TEMPORAL contracts available for independent evaluation
- No independent oracle constructable — the structural ordering is trivially deterministic with no interesting behavioral variation
- Already used as OOD dataset in this study — not independent

**Verdict:** REJECTED

---

### Candidate 2: public_jcl (empty repository directory)

**Status:** Directory exists at `datasets/public_jcl/` but is empty.  
**Verdict:** REJECTED — no data present.

---

### Candidate 3: IBM/zopeneditor-sample

**Source:** https://github.com/IBM/zopeneditor-sample  
**Status:** Cannot acquire — no internet/GitHub access from execution environment.

**Documented prior assessment (from FINAL_RESULTS_MANIFEST.json gap_B_second_system):**
> "structurally too simple for independent TEMPORAL evaluation"

**Verdict:** REJECTED — cannot acquire; prior assessment negative.

---

### Candidate 4: IBM CBSA / CICS Banking Sample Application

**Source:** https://github.com/cicsdev/cics-banking-sample-application  
**Status:** Cannot acquire — no internet/GitHub access from execution environment.

**Assessment (based on CICS architecture):**
- CICS applications use CICS API for behavioral contracts (START TASK, EXEC CICS READ/WRITE), not JCL COND= guards
- JCL in CICS systems is typically compile/link/deploy scripts rather than production batch streams
- RELIC's extraction is JCL-focused; CICS control flow would require extending parser scope
- Even if available, the CICS contract types would not match RELIC's TEMPORAL/PRECEDES contract definition

**Verdict:** REJECTED — outside RELIC's JCL-focused scope even if acquired.

---

## Selection Gate

**HARD STOP: No candidate can support a defensible independent evaluation.**

Selection criteria were applied in priority order:

| Criterion | public_cobol | zopeneditor | CBSA |
|---|---|---|---|
| Oracle independence | HIGH | UNKNOWN | N/A |
| JCL evaluation feasibility | NONE | UNKNOWN | LOW |
| Multi-step JCL count | 3 | UNKNOWN | LOW |
| System independence | HIGH | HIGH | HIGH |
| Reproducibility | YES | UNKNOWN | LOW |
| Licensing | OK | OK | OK |
| Integration cost | LOW | HIGH | VERY HIGH |
| **Overall verdict** | **REJECTED** | **CANNOT ACQUIRE** | **OUT OF SCOPE** |

---

## Decision

**SECOND SYSTEM NOT SCIENTIFICALLY VALIDATED**

This is the correct scientific conclusion, not a failure of effort:

1. The publicly available COBOL+JCL universe is extremely limited. CardDemo is among the only multi-step, behaviorally rich JCL systems publicly available.
2. Enterprise mainframe JCL (the natural evaluation target) is universally proprietary.
3. Academic datasets for this domain do not exist — there is no "COBOL/JCL benchmark suite" in the research community, which is part of what makes RELIC's contribution meaningful (it defines one).
4. Constructing a second system benchmark from scratch requires qualified JCL/COBOL domain experts to manually annotate ground truth — an external human dependency that cannot be resolved in this sprint.

---

## Impact on Paper

**This limitation must be prominently disclosed:**
- All results are on a single subject system (CardDemo, a demonstration-scale application)
- Cross-system generalization is an open research question
- The paper is scoped as: "proof-of-concept methodology + reproducible benchmark on CardDemo"
- Generalization claims beyond CardDemo are not supported by current evidence

**The limitation does NOT invalidate the research contribution:**
- CardDemo is the only publicly available realistic COBOL/JCL application suitable for this research
- The benchmark, methodology, and system are fully reproducible
- The findings — particularly ALTER_ERROR_BRANCH detection — represent real, demonstrable improvements over structural approaches
- Creating a reusable evaluation methodology (even on one system) is a contribution that future researchers can build on

---

## Cross-System Generalization Verdict

Per the evaluation framework's required verdicts:

**INSUFFICIENT EVIDENCE**

| Metric | CardDemo | Second System |
|---|---|---|
| Files | 55 JCL | N/A |
| Jobs | 55 | N/A |
| Steps | ~180 | N/A |
| Contracts | 63 | N/A |
| Micro-F1 | 1.0000 | N/A |
| Macro-F1 | 0.5455 | N/A |
| Mutation F1 | 1.0000 | N/A |
| Simulation | 91.8% | N/A |
| Real execution | 0% | N/A |

Generalization conclusion: **INSUFFICIENT EVIDENCE** — single system only.

---

*Generated: RELIC Final Closure Sprint | 2026-08-30*
