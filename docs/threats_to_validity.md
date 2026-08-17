# Threats to Validity
## LEGACY-CONTRACT — Comprehensive Validity Analysis

---

## 1. INTERNAL VALIDITY

### 1.1 Parser Errors
**Threat:** JCL and COBOL parsers may miss syntactic constructs, producing incomplete IRs and therefore missing contracts.
**Mitigation:** Parser test suite with known-good artifacts. Report parser coverage rate. Flag unparsed elements.
**Residual risk:** Medium. JCL has many dialects; COBOL has many vendor extensions not in public datasets.

### 1.2 Dynamic Instrumentation Errors
**Threat:** GnuCOBOL instrumentation hooks may fail to capture all execution events. JCL simulation may not accurately reflect real job execution.
**Mitigation:** Compare instrumented vs. reference output for validation. Document all missed event types.
**Residual risk:** Medium.

### 1.3 Annotation Errors
**Threat:** Human annotators may misinterpret implicit contracts, especially in legacy code with limited documentation.
**Mitigation:** Inter-annotator agreement measurement (Cohen's κ). Adjudication protocol. Annotation guidelines.
**Residual risk:** Low-medium (depends on κ value — reported in paper).

### 1.4 Mutation Bias
**Threat:** If mutations are designed with knowledge of the BCG's detection capabilities, the evaluation is biased.
**Mitigation:** Mutations derived from external empirical sources (failure taxonomy) BEFORE BCG is finalized. Mutation operators not modified after seeing evaluation results.
**Residual risk:** Low if the protocol is followed (documented in reproducibility log).

### 1.5 Benchmark Leakage
**Threat:** Information from benchmark systems could influence system design if not properly isolated.
**Mitigation:** Strict train/validation/held-out split. Held-out systems not examined during development. Split defined before system is built.
**Residual risk:** Low.

### 1.6 LLM Nondeterminism
**Threat:** LLM-based contract enrichment produces different outputs across runs even with same input.
**Mitigation:** Fixed temperature=0, fixed seed where supported. All LLM outputs logged with model version, prompt version, timestamp. Report variance across 5 runs for LLM-involving components.
**Residual risk:** Low-medium for LLM components (deterministic components unaffected).

### 1.7 Implementation Bias
**Threat:** Baselines implemented with less care than the proposed method.
**Mitigation:** Baselines implemented to their reference specifications. Baseline performance validated against known results where possible. Baselines documented and released for external validation.
**Residual risk:** Low.

---

## 2. EXTERNAL VALIDITY

### 2.1 Limited Legacy Systems
**Threat:** Results on CardDemo + public COBOL samples may not generalize to real enterprise mainframe systems with millions of lines of COBOL.
**Mitigation:** Generalization experiment on held-out systems. Explicit reporting of performance degradation. Limit claims to "batch COBOL+JCL systems of comparable complexity to CardDemo."
**Residual risk:** High. This is the primary external validity threat and must be prominently disclosed.

### 2.2 COBOL/JCL Focus
**Threat:** BCG may not generalize to other legacy languages (PL/I, RPG, Natural, Assembler).
**Mitigation:** Architecture designed for extension. Parser abstraction allows new language support.
**Residual risk:** Medium. Paper 1 claims explicitly scoped to COBOL+JCL.

### 2.3 Public Dataset Limitations
**Threat:** Public datasets are simpler and better-documented than real enterprise systems. Implicit contracts are more common and harder to detect in real systems.
**Mitigation:** CardDemo is specifically chosen because it has realistic batch structure. Limitation is disclosed.
**Residual risk:** High. Cannot be fully mitigated without access to enterprise data.

### 2.4 Execution Environment Differences
**Threat:** GnuCOBOL execution differs from z/OS execution (memory model, file I/O semantics, COMP-3 handling, etc.).
**Mitigation:** Differences documented. Results labeled with environment. z/OS-specific features handled conservatively in parser.
**Residual risk:** Medium.

---

## 3. CONSTRUCT VALIDITY

### 3.1 Do Contracts Correspond to Genuine Behavior?
**Threat:** Contracts extracted from static analysis may not correspond to actual behavioral obligations — they may be structural artifacts.
**Mitigation:** Execution oracle validation. Human expert annotation. Contract type definitions require semantic justification.
**Residual risk:** Medium-high for implicit contracts.

### 3.2 Do Mutations Reflect Real Modernization Failures?
**Threat:** Even empirically derived mutations may not match the specific types of failures relevant to the target domain.
**Mitigation:** Failure taxonomy derived from multiple independent evidence sources. Each mutation category has ≥2 documented sources.
**Residual risk:** Medium.

### 3.3 Does Risk Detection Metric Reflect Practical Usefulness?
**Threat:** Precision/recall on contract violation detection may not correlate with whether engineers would actually benefit from the output.
**Mitigation:** Human evaluation experiment (Phase 17) to assess practical usefulness. Not mandatory for Paper 1 but planned.
**Residual risk:** Medium. Practical usefulness is harder to measure than technical metrics.

---

## 4. DYNAMIC VALIDITY (NEW — SPECIFIC TO THIS WORK)

### 4.1 Incomplete Execution Coverage
**Threat:** Execution traces cover only executed paths. Unexecuted paths have no dynamic evidence. Contracts on unexecuted paths get NOT_OBSERVED status.
**Mitigation:** Explicit NOT_OBSERVED status. Coverage reporting. Dynamic coverage experiment measures sensitivity.
**Residual risk:** Medium. Fundamental limitation of dynamic analysis.

### 4.2 Hidden Environment State
**Threat:** Some contracts depend on environment configuration (JES parameters, RACF settings, z/OS system values) that cannot be captured in a non-mainframe environment.
**Mitigation:** Environment-dependent contracts flagged. Not claimed as fully validated.
**Residual risk:** High for environment-dependent contracts.

### 4.3 Nondeterministic Execution
**Threat:** Some COBOL programs have execution paths that depend on input data. Different inputs may exercise different contracts.
**Mitigation:** Multiple input scenarios for controlled execution. Execution frequency tracked per contract.
**Residual risk:** Low-medium with adequate test inputs.

### 4.4 Trace Fidelity
**Threat:** Instrumentation hooks may add overhead that alters execution timing (relevant for temporal contracts).
**Mitigation:** Instrumentation uses append-only logging. Event timestamps from monotonic clock. Overhead documented.
**Residual risk:** Low for ordering contracts (relative order preserved even with overhead). Higher for absolute timing.

### 4.5 Instrumentation Overhead Bias
**Threat:** Instrumentation may cause the system to behave differently, making some execution paths unreachable.
**Mitigation:** Instrumentation is non-branching (append-only logging). Validation: compare program output with and without instrumentation.
**Residual risk:** Low.

---

## 5. CRITICAL THREATS (Added: Ground Truth Circularity)

### 5.1 Ground Truth Circularity in RQ1 (PRIMARY VALIDITY THREAT)

**Threat:** The Level-2 DETERMINISTIC ground truth was produced by the same BCG static extractor
family under evaluation. Evaluating the extractor against its own output is not an independent
measurement of extraction accuracy — it is a self-consistency check.

**Consequence:** F1 = 1.00 in the current RQ1 evaluation is mathematically guaranteed regardless
of whether the extractor produces semantically correct or incorrect contracts. Any systematic
error in the extraction logic (e.g., missing an entire class of COND contract pattern) is
invisible to this benchmark because the same error appears in both the reference and the system
output. F1 below 1.00 would indicate a non-determinism bug, not a precision/recall deficiency.

**Correct characterization:** The Level-2 evaluation is an engineering self-consistency check,
not a scientific evaluation of contract recovery accuracy. It confirms the system is deterministic
and idempotent. It does not confirm that contracts correspond to true semantic obligations.

**Mitigation:** Level-3 independent human annotation (see `docs/annotation_protocol_final.md`).
This requires qualified annotators who have not seen the extractor's output to label
JCL artifacts for behavioral contracts independently.

**Current status:** Level-3 annotation has NOT been conducted.
RQ1 is marked BLOCKED_FOR_INDEPENDENT_VALIDATION.

**Required action before claiming RQ1:** Conduct Level-3 annotation (minimum 120 items per
`docs/annotation_protocol_final.md`), compute inter-annotator agreement (κ ≥ 0.60 required),
adjudicate disagreements, re-run the evaluation pipeline against `level3_human.json`.

### 5.2 LLM Baselines Blocked (RQ2 Incomplete)

**Threat:** Baselines C (LLM-only) and D (Dep+LLM) cannot be evaluated without an LLM API key.
The RQ2 full comparison is therefore incomplete.

**Current status:** Both conditions are marked BLOCKED_EXTERNAL_DEPENDENCY.
The static conditions (A, B, E, and proposed static_bcg) are complete and valid.

**Required action:** LLM API access with documented model version, prompt, temperature, seed.
Do not fabricate LLM results. If API is unavailable, report these conditions as BLOCKED.

### 5.3 Dynamic Pipeline Partial (RQ2 Dynamic Condition + RQ3)

**Threat:** The BCG+dynamic RQ2 condition and the full RQ3 coverage experiment cannot be
completed because CardDemo COBOL programs require DB2/CICS/IMS stubs not available in
the GnuCOBOL environment.

**Current status:** RQ3 has partial results (49.2% validation rate) from JCL simulation
traces and standalone COBOL programs. The full hypothesis (H3: FPR reduction at 50%
coverage) cannot be evaluated with the available trace set.

**Required action:** Either (a) obtain DB2/CICS/IMS stubs for GnuCOBOL, or (b) obtain
real z/OS execution traces from a production or sandbox mainframe environment.
