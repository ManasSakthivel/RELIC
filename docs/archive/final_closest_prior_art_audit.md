# Final Closest Prior Art Audit — LEGACY-CONTRACT

**Auditor:** Lead Research Engineer (Phase 4/5)  
**Purpose:** Definitive comparison against closest prior art systems; final novelty classification  
**Date:** 2025 (pre-experiment, pre-submission)  
**Policy:** All claims hedged with "to our knowledge". Any claim not surviving this audit must be narrowed.

---

## Prior Art Comparison Table

| Dimension | GIST (Lorenzoli 2008) | Daikon (Ernst 2007) | Ammons 2002 (POPL) | Lo 2006 (FSE) | RV (Leucker 2009) | SYMDIFF (Lahiri 2012) | Pessoa 2022 (ICSME) | **BCG (Ours)** |
|-----------|----------------------|---------------------|-------------------|----------------|-------------------|----------------------|---------------------|--------------|
| **Contract type** | Behavioral FSM (event sequences) | Data invariants (pre/postconditions) | Temporal safety properties (API call order) | Control-flow patterns | LTL/temporal monitors | Semantic equivalence (semantic diff) | Behavioral semantic diff | Temporal + Resource + Control-flow obligations |
| **Static evidence** | NO | NO | NO | NO | PARTIAL (model-based) | YES (symbolic) | PARTIAL (dataflow) | **YES** (deterministic structural) |
| **Dynamic evidence** | YES (execution traces) | YES (execution traces) | YES (execution traces) | YES (execution traces) | YES (runtime) | YES (symbolic execution) | YES (execution) | **YES** (instrumented execution) |
| **Static+dynamic reconciliation** | NO | NO | NO | NO | NO | NO | NO | **YES** (with explicit conflict taxonomy) |
| **Provenance per contract** | NO | NO | NO | NO | NO | NO | NO | **YES** (extraction_method, source_artifact, location, evidence items) |
| **Confidence model** | NO | NO | NO | NO | NO | NO | NO | **YES** (6-dimension evidence-strength score) |
| **JCL support** | NO | NO | NO | NO | NO | NO | NO | **YES** |
| **COBOL support** | NO | NO | NO | NO | NO | NO | YES (partial) | **YES** |
| **Batch orchestration contracts** | NO | NO | NO | NO | NO | NO | NO | **YES** (job-step ordering, dataset chaining) |
| **Cross-artifact contracts** | NO (single-program FSM) | NO (single-program) | NO (single API) | NO (single-program) | NO | PARTIAL (two versions of same program) | PARTIAL (two COBOL programs) | **YES** (JCL + COBOL + copybook) |
| **Modernization context** | NO | NO | NO | NO | NO | YES (regression) | YES (migration) | **YES** |
| **Fault-grounded mutations** | NO | NO | NO | NO | NO | NO | NO | **YES** (F1–F3 from empirical sources) |
| **Modernization risk explanation** | NO | NO | NO | NO | NO | NO | NO | **YES** (CHANGE→CONTRACT→EVIDENCE→CONSEQUENCE chain) |
| **Evidence-gap handling** | NO (silence = absence) | NO (silence = absence) | NO | NO | NO | NO | NO | **YES** (NOT_OBSERVED ≠ CONTRADICTED; INSUFFICIENT_EVIDENCE state) |

---

## Per-System Detailed Analysis

### GIST (Lorenzoli, Mariani, Pezzè — ICSE 2008)

**What it does:** GIST (Generation of Invariant Software Tests) infers behavioral models from execution traces using the k-tail FSM inference algorithm. From a set of execution traces, it builds an FSM that accepts the observed behavior. The FSM can be used to check whether new executions conform to previously-observed behavior.

**Similarities to BCG:**
- Both use execution traces as evidence for behavioral models
- Both produce a representation of "what the program is expected to do"
- Both can identify deviations from expected behavior

**Differences from BCG:**
1. **Single-artifact scope:** GIST constructs one FSM per program. BCG constructs a graph spanning JCL jobs, COBOL steps, and the datasets they share — i.e., contracts across artifacts, not within one.
2. **No static evidence:** GIST is purely dynamic. BCG extracts static structural facts first, then reconciles with dynamic evidence. The reconciliation mechanism (SUPPORTED/CONTRADICTED/NOT_OBSERVED) does not exist in GIST.
3. **No provenance:** GIST FSMs have no link back to source locations, artifact paths, or extraction methods. BCG contracts carry full ProvenanceRecord.
4. **No modernization application:** GIST does not target modernization risk detection. It produces conformance monitors, not modernization contracts.
5. **No batch domain:** GIST is designed for OOP Java programs with method-call event traces. It has no concept of JCL step ordering, dataset production/consumption, or COND return-code semantics.
6. **No fault-grounded evaluation:** GIST was not evaluated with empirically-sourced modernization mutation operators.

**Verdict:** GIST is the closest uncited predecessor. The BCG dynamic evidence layer is conceptually related to GIST's trace-based inference. The key differentiators are (1) static+dynamic reconciliation, (2) provenance, (3) cross-artifact batch domain, (4) modernization context. These differences are substantive, not cosmetic. The paper must cite GIST prominently and compare against it in Table 1.

---

### Daikon (Ernst et al. — Science of Computer Programming 2007)

**What it does:** Daikon detects likely program invariants from execution traces: pre/post-conditions on data values (e.g., x > 0 after method foo()). It is the canonical system for dynamic invariant inference.

**Differences from BCG:**
1. **Data invariants vs. behavioral contracts:** Daikon focuses on data-value relationships. BCG focuses on temporal ordering and resource dependency obligations — a different contract space.
2. **No temporal/resource contracts:** Daikon does not infer "A must execute before B" or "A must produce file X before B consumes it."
3. **Single-program scope:** Daikon runs on one program's execution. BCG spans JCL + COBOL + datasets.
4. **No static evidence:** Daikon is purely dynamic.
5. **Not applicable to JCL:** Daikon has no JCL parser, no step-ordering semantics, no dataset dependency model.

**Verdict:** DOMAIN_ADAPTATION at most for the dynamic evidence layer. The contracts BCG targets (temporal/resource/control-flow) are orthogonal to Daikon's data invariants. The paper should cite Daikon as the canonical dynamic inference baseline, but the claim "BCG recovers different contract types than Daikon" is defensible and does not require hedging beyond "to our knowledge."

---

### Ammons, Bodík, Larus (POPL 2002) — Mining Specifications

**What it does:** Mines temporal safety properties from execution traces of C API calls. Produces FSM-based specifications (e.g., "malloc must be followed by free"). These specifications are in the same family as BCG's temporal contracts.

**Similarities:** Temporal contract inference from execution traces.

**Differences from BCG:**
1. **Single-language, single-artifact:** Ammons targets C API call sequences within one program. BCG targets cross-artifact JCL+COBOL batch orchestration.
2. **No static evidence:** Ammons is purely dynamic.
3. **No provenance:** No source artifact traceability.
4. **API-call semantics, not batch-job semantics:** CALL (malloc/free) ≠ JCL STEP/EXEC semantics.
5. **No modernization context:** Ammons was not applied to software modernization or migration risk.

**Verdict:** Closest theoretical predecessor for temporal contract mining. BCG's contribution relative to Ammons is (1) static+dynamic reconciliation, (2) cross-artifact JCL/COBOL scope, (3) provenance, (4) modernization application. Cite explicitly; position BCG as building on this direction.

---

### Lo, Khoo, Han (FSE 2006) — Mining Control-Flow Patterns

**What it does:** Mines iterative-convergent control-flow patterns from OOP execution traces.

**Differences from BCG:**
- OOP Java, not legacy batch
- Control-flow patterns within one program, not cross-artifact
- No static evidence
- No batch domain relevance

**Verdict:** DOMAIN_ADAPTATION (mining patterns from traces). Cite for completeness; not a direct competitor.

---

### Runtime Verification (Leucker & Schallhart 2009; Barnett & Schulte 2003)

**What it does:** Generates runtime monitors that check LTL/temporal specifications against live execution.

**Key difference:** RV is *prospective* (monitors future execution online). BCG is *retrospective* (recovers contracts from existing legacy code for modernization analysis). This is a fundamental distinction.

BCG does not generate executable monitors. It is not RV. The paper should clarify this in the related work section to preempt reviewer confusion.

---

### SYMDIFF (Lahiri et al. — CAV 2012)

**What it does:** Semantic differencing of two program versions using symbolic execution to identify behavioral differences.

**Similarities:** BCGDiff is conceptually related — both identify behavioral changes between program versions.

**Differences from BCG:**
1. **Statement-level symbolic execution vs. contract-level graph diff:** SYMDIFF works at the instruction level with formal verification. BCG works at the job/step/artifact level with execution-grounded contracts.
2. **Requires decompilable or analyzable code:** SYMDIFF requires SMT-solvable code. JCL is not amenable to symbolic execution.
3. **No cross-artifact scope:** SYMDIFF compares two versions of the same program; BCG compares behavioral obligations across JCL + COBOL + copybooks.
4. **No provenance:** No extraction method tracking.

**Verdict:** Related in spirit (behavioral comparison between program versions) but a different technique for a different abstraction level. Position BCG as complementary: SYMDIFF for fine-grained code-level semantics; BCG for coarse-grained batch-orchestration contracts.

---

### Pessoa et al. (ICSME 2022) — Behavioral Semantic Differencing of COBOL Programs

**What it does:** Compares two versions of a COBOL program using static/dynamic behavioral analysis to identify semantic differences introduced by migration.

**Similarities:**
- Applied to COBOL programs
- Targets modernization context
- Uses execution evidence

**Differences from BCG:**
1. **Single COBOL program, not cross-artifact:** Pessoa does not cover JCL job orchestration, batch step ordering, or dataset chaining.
2. **No formal contract abstraction:** Pessoa identifies behavioral differences but does not represent them as a typed contract IR with provenance.
3. **No resource/temporal contracts at batch level:** COBOL-level data differences ≠ JCL-level job ordering obligations.
4. **No reconciliation mechanism:** No explicit SUPPORTED/CONTRADICTED/NOT_OBSERVED states.
5. **No mutation framework:** Pessoa does not use fault-grounded mutations for evaluation.

**Verdict:** Most directly domain-related prior work. The paper must compare against Pessoa in Table 1 and clearly differentiate at the granularity level (program-level behavioral diff vs. batch-orchestration contract recovery). Cite prominently in the COBOL-related work paragraph.

---

## Novelty Classification Matrix

| Claimed BCG Contribution | Classification | Justification |
|--------------------------|----------------|---------------|
| 1. Cross-artifact behavioral contracts spanning JCL + COBOL | **GENUINELY_NOVEL** | No prior system constructs contracts across both JCL (job/step/COND) and COBOL (CALL/READ/WRITE) artifacts in a unified graph. |
| 2. Formal BCG IR (V, E, C, P, D, Γ) | **NOVEL_COMBINATION** | Individual components (graph IR, contract model, provenance) exist separately. The integration for legacy batch artifacts is new. |
| 3. Static/dynamic reconciliation with conflict taxonomy | **NOVEL_COMBINATION** | Static analysis and dynamic trace analysis are used separately in prior work. No prior system explicitly reconciles them per-contract with a typed conflict taxonomy (STATIC_FALSE_POSITIVE, DYNAMIC_INCOMPLETE, HIDDEN_STATE). |
| 4. Provenance-aware contract representation | **ENGINEERING_CONTRIBUTION** | Provenance in static analysis is not new. Applying it per-contract in a legacy batch context with ExtractionMethod tagging is a good engineering practice; not a novel algorithm. |
| 5. Evidence-strength confidence model (not probability) | **ENGINEERING_CONTRIBUTION** | Weighted confidence scores exist throughout program analysis. The specific 6-dimension model is novel only in its application domain. |
| 6. Fault-grounded mutation operators from empirical sources | **NOVEL_COMBINATION + EVALUATION_CONTRIBUTION** | Mutation testing for mainframe/legacy batch with empirically sourced failure patterns has not been previously done. The methodology of grounding mutations in published modernization postmortems is an evaluation contribution. |
| 7. BCGDiff for contract-level modernization impact | **DOMAIN_ADAPTATION** | Semantic differencing (SYMDIFF, Pessoa) exists. BCGDiff applies a graph-diff concept to a typed contract IR at the batch-orchestration level. |
| 8. Execution-grounded risk detection with explanation chain | **DOMAIN_ADAPTATION + ENGINEERING_CONTRIBUTION** | Risk detection from static analysis exists. The novelty is the CHANGE→CONTRACT→EVIDENCE→CONSEQUENCE explanation chain applied to BCG-based risk, not the concept of risk detection itself. |

---

## Contributions That Must Be Narrowed

1. **Contribution 4 (Provenance):** Must be positioned as an engineering contribution, not a scientific novelty. Change "novel provenance model" to "provenance-aware implementation that enables reproducibility and audit traceability."

2. **Contribution 5 (Confidence model):** Must not be called "novel." Frame as "a domain-specific evidence-strength model whose calibration is empirically evaluated." The calibration evaluation is the contribution.

3. **Contribution 8 (Explanation chain):** Must acknowledge that explainable risk detection exists in program analysis. Frame as "applying explanation chains to contract-based batch-orchestration risk, making the evidence path auditable."

---

## Final Defensible Novelty Statement

> To our knowledge, LEGACY-CONTRACT is the first system to jointly represent temporal, resource, and control-flow behavioral contracts across heterogeneous legacy batch artifacts (JCL job orchestration and COBOL program execution) as a formal intermediate representation, and to evaluate these contracts against both static structural evidence and dynamic instrumented execution with explicit reconciliation of conflicting evidence. Unlike prior contract inference systems (GIST, Ammons, Lo) which operate on single-program execution traces without static evidence, and unlike prior COBOL analysis work (Pessoa) which focuses on program-level behavioral differences without batch orchestration semantics, the BCG addresses the cross-artifact contract recovery problem specifically relevant to mainframe batch modernization, with fault-grounded evaluation using mutation operators derived from documented real-world migration failures.

---

## Recommended Paper Changes

1. **Section 6 (Related Work):** Add dedicated subsections for GIST and Ammons/POPL-2002, with explicit per-dimension comparison. Do not merely cite them in passing.

2. **Table 1 (Prior Art Comparison):** Must include GIST, Daikon, Ammons, Lo, Pessoa, SYMDIFF as rows. The columns must match the comparison table above. Complete this table before submission.

3. **Contribution list:** Remove "novel provenance model" and "novel confidence model" from the list of scientific contributions. Keep them as design choices with empirical evaluation (calibration).

4. **Abstract:** The phrase "execution-grounded" is the key differentiator from GIST/Ammons. Make this explicit: "Unlike prior behavioral model inference systems that rely solely on execution traces, BCG explicitly reconciles static structural evidence with dynamic observations."

5. **Section 2 (Background):** Add a paragraph on k-tail FSM inference (Angluin, Lo, Ammons) to establish the intellectual lineage.

6. **Threats to Validity:** Add a paragraph: "The GnuCOBOL execution environment does not reproduce z/OS-specific behavior (VSAM, mainframe I/O, ABEND codes). All dynamic evidence is labeled 'GnuCOBOL instrumented execution' throughout this paper. Claims about execution-grounded validation are bounded by this environment."

---

*End of docs/final_closest_prior_art_audit.md*
