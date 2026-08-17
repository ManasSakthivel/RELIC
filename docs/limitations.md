# Limitations
## LEGACY-CONTRACT — Honest Limitations of the Research System

---

## L1 — Single Primary Dataset

**Description:** Paper 1 uses AWS CardDemo as the primary evaluation dataset. This is a publicly available, realistic, but relatively small mainframe application (~30 COBOL programs, ~15 JCL files). Real enterprise mainframe systems may have thousands of programs and hundreds of JCL job streams.

**Impact:** Generalization claims are limited. Performance on systems of this scale may not predict performance on enterprise-scale systems.

**Disclosure:** All performance numbers must be reported as "on CardDemo-scale systems." Cross-system generalization is evaluated on held-out public systems but these are also small.

---

## L2 — Non-Mainframe Execution Environment

**Description:** Dynamic evidence is collected via GnuCOBOL on Linux/macOS, not z/OS. GnuCOBOL implements COBOL-85/2002 but may differ from IBM Enterprise COBOL in subtle ways (COMP-3 handling, file I/O semantics, SORT behavior, runtime error codes).

**Impact:** Dynamic evidence may not perfectly reflect mainframe execution. z/OS-specific behaviors (SMF records, JES job scheduling, RACF interactions) are not captured.

**Disclosure:** All dynamic evidence labeled `EXECUTION (GnuCOBOL environment, NOT z/OS)`. Results described as "evidence from GnuCOBOL execution" throughout.

---

## L3 — Paper 1 Contract Scope

**Description:** Paper 1 covers only temporal, resource, and control-flow contracts. Data contracts (field-level compatibility), state contracts (initialization sequences), and error contracts (exception propagation chains) are not addressed.

**Impact:** The BCG is incomplete for data-intensive modernization scenarios where field-level changes are the primary risk.

**Disclosure:** Explicitly stated as future work. Paper 2 extends to data and state contracts.

---

## L4 — Confidence Is Not Probability

**Description:** The confidence model produces a normalized evidence-strength score in [0,1], not a calibrated probability. Without a calibration study with sufficient ground-truth contracts, interpreting the score as P(contract is valid) is scientifically unsupported.

**Impact:** Cannot make probabilistic risk claims. All claims must be framed as "evidence-weighted confidence" not "probability of violation."

**Disclosure:** Explicitly stated in paper Section 6 (BCG model) and Section 10 (methodology). Future work: calibration study.

---

## L5 — LLM Nondeterminism

**Description:** LLM-based enrichment components (Baseline C, Baseline D, E7 evidence level) produce different outputs across runs even with temperature=0 due to model version changes, backend sampling, and context window variations.

**Impact:** LLM-involving results have inherent variance. Reproducibility of exact numbers for LLM baselines cannot be guaranteed across model updates.

**Disclosure:** All LLM results reported with model version, temperature, and variance across 5 runs. Core results (non-LLM BCG) are fully deterministic and reproducible.

---

## L6 — Annotation Subjectivity

**Description:** Level-3 (human-annotated) ground truth for implicit contracts depends on annotator interpretation. Inter-annotator agreement may be imperfect, especially for complex cross-artifact contracts.

**Impact:** Benchmark quality for implicit contracts depends on Cohen's κ value. Low κ regions have lower ground-truth reliability.

**Disclosure:** κ reported per contract type. Results for low-κ contract categories clearly distinguished.

---

## L7 — Mutation Realism

**Description:** Even empirically derived mutations are simplified versions of real modernization failures. Real modernization involves complex interactions between multiple system components that are difficult to represent as isolated mutation operators.

**Impact:** The evaluation may overestimate detection performance for real-world scenarios where multiple interacting changes occur simultaneously.

**Disclosure:** Compound mutations (multiple simultaneous operators) are noted as future work.

---

## L8 — Counterfactual Restoration Is Structural, Not Executable

**Description:** The counterfactual restoration module proposes structural changes to restore violated contracts but does NOT produce executable modified code. Restoration suggestions are structural recommendations only.

**Impact:** The system cannot claim "automated program repair." Restoration is a decision-support tool, not an automated repair tool.

**Disclosure:** All restoration output labeled as "structural restoration suggestion." Engineers must implement and verify the suggested changes.

---

## L9 — No Production Execution Data

**Description:** The research uses generated execution evidence (GnuCOBOL + JCL simulation), not production execution logs. Production systems have more complex behavioral patterns, more execution paths, and more edge cases.

**Impact:** Dynamic evidence quality may be lower than what production traces would provide.

**Disclosure:** Explicitly labeled throughout. This is simultaneously a limitation and a research contribution: the system provides value even when only instrumented evidence is available.

---

## L10 — JCL Dialect Coverage

**Description:** JCL has many vendor-specific extensions and dialects. The JCL parser is written against standard IBM JCL syntax as documented in the JCL Reference Manual. Non-standard extensions may not parse correctly.

**Impact:** Parse failures on non-standard JCL produce warnings and partial IR, not hard failures. Contracts from unparsed regions are missed.

**Disclosure:** Parser coverage rate reported in results. Unparsed regions documented.
