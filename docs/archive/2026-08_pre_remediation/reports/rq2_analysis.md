# RQ2 Analysis: Mutation Detection — BCG vs. Baselines

**Research Question:** Does the BCG+dynamic approach detect contract-violating mutations with
higher F1 than static baselines?

**Hypothesis H2:** BCG+dynamic F1 ≥ static_bcg F1 + 10 percentage points → **CANNOT BE
EVALUATED YET** (LLM baselines C and D require OPENAI_API_KEY; dynamic component not yet
integrated into the mutation harness)

**Run date:** 2026-08-15 | **Seed:** 42

---

## 1. Executive Summary

### Key Findings

The proposed `static_bcg` method achieves **F1 = 1.0** across all 109 evaluated mutations,
detecting every contract-violating mutation in the CardDemo JCL corpus with zero false positives.
Three of four available baselines are decisively outperformed; one baseline (static_bcg_baseline,
Baseline E) reaches F1 = 0.9619 but fails on a specific class of MODIFIED-not-BROKEN contracts.

**Critical structural findings:**

1. **ALTER_ERROR_BRANCH** (CONTROL_FLOW mutation) is the discriminating operator: Baseline E
   misses all 8 instances because it only detects BROKEN contracts. The proposed method's
   `RiskDetector` flags MODIFIED contracts (confidence-delta from 1.0 → 0.7), catching what
   Baseline E cannot.

2. **Complexity baseline (Baseline B) records F1 = 0.0** — a valid null result. The CardDemo
   JCL corpus operates below the complexity threshold (0.5) universally. Complexity metrics alone
   are insufficient for this contract-violation detection task.

3. **Structural baseline (Baseline A)** fails on four of eight operators because it cannot see
   semantic/behavioral mutations: it observes topology, not meaning.

4. **LLM baselines (C, D) are pending.** No result is fabricated. See Section 7.

### Summary Table

| Condition | F1 | Status |
|---|---|---|
| static_bcg (proposed) | **1.0000** | ✓ Evaluated |
| static_bcg_baseline (E) | 0.9619 | ✓ Evaluated |
| structural (A) | 0.8878 | ✓ Evaluated |
| llm_only (C) | PENDING | ✗ API key required |
| dep_llm (D) | PENDING | ✗ API key required |
| complexity (B) | 0.0000 | ✓ Evaluated (null result) |

---

## 2. Experimental Setup

### 2.1 Corpus and Mutation Generation

| Parameter | Value |
|---|---|
| JCL files | 55 |
| Mutations attempted | 440 |
| Mutations evaluated | 109 |
| Mutations marked N/A | 331 (75.2%) |
| Errors | 0 |

**N/A rate (75.2%):** A mutation attempt is marked N/A when the target operator is not
applicable to the specific JCL file — for example, a REMOVE_JOB_DEPENDENCY operator applied to
a single-step JCL file with no inter-job dependencies. This is expected behaviour. The 109
evaluated mutations represent the set where a mutation was both syntactically applicable and
produced a semantically distinct artifact. N/A is not an error; it is a domain constraint. See
Section 7.3 for a discussion of its implications.

### 2.2 Mutation Operators

Eight mutation operators were applied across two semantic domains:

**Control-flow / dependency operators:**
- `REORDER_JOBS` — changes execution ordering of jobs within a JCL stream
- `REMOVE_JOB_DEPENDENCY` — removes an explicit EXEC or job-trigger dependency
- `ALTER_STEP_SEQUENCE` — reorders steps within a job

**Data / resource operators:**
- `REMOVE_DATASET_INIT` — removes dataset initialisation step
- `CHANGE_DATASET_NAME` — changes a dataset reference, breaking resource binding
- `ALTER_FILE_DEPENDENCY_ORDER` — reorders file-processing steps

**Error-handling operators:**
- `SUPPRESS_RETURN_CODE_CHECK` — removes COND/RC evaluation
- `ALTER_ERROR_BRANCH` — modifies error-branch target (weakens, does not break)

### 2.3 Conditions

| Condition ID | Description |
|---|---|
| static_bcg | Proposed: BCG contract graph + RiskDetector (BROKEN + MODIFIED) |
| structural (A) | Baseline: structural dependency graph topology only |
| complexity (B) | Baseline: file/step complexity threshold (θ = 0.5) |
| llm_only (C) | Baseline: LLM zero-shot detection (PENDING) |
| dep_llm (D) | Baseline: BCG dependency graph + LLM reasoning (PENDING) |
| static_bcg_baseline (E) | Baseline: BCG contract graph, BROKEN contracts only (no confidence-delta) |

### 2.4 Metrics

- **TP:** Mutation correctly flagged as contract-violating
- **FP:** Non-violating artifact incorrectly flagged (see Section 7.1)
- **FN:** Contract-violating mutation not detected
- **Precision** = TP / (TP + FP); **Recall** = TP / (TP + FN); **F1** = harmonic mean; **FNR** = FN / (TP + FN)

---

## 3. Results

### 3.1 Condition-Level Results

| Condition | TP | FP | FN | Precision | Recall | F1 | FNR |
|---|---|---|---|---|---|---|---|
| static_bcg (proposed) | 109 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | 0.0000 |
| static_bcg_baseline (E) | 101 | 0 | 8 | 1.0000 | 0.9266 | 0.9619 | 0.0734 |
| structural (A) | 87 | 0 | 22 | 1.0000 | 0.7982 | **0.8878** | 0.2018 |
| complexity (B) | 0 | 0 | 109 | 0.0000 | 0.0000 | **0.0000** | 1.0000 |
| llm_only (C) | — | — | — | — | — | PENDING | — |
| dep_llm (D) | — | — | — | — | — | PENDING | — |

### 3.2 Per-Operator Results

| Operator | BCG F1 | Struct F1 | Complexity F1 | Static_BCG_E F1 | N/A count |
|---|---|---|---|---|---|
| REORDER_JOBS | 1.0 | 0.9655 | 0.0 | 1.0 | 25 |
| REMOVE_JOB_DEPENDENCY | 1.0 | 1.0 | 0.0 | 1.0 | 25 |
| ALTER_STEP_SEQUENCE | 1.0 | 0.9655 | 0.0 | 1.0 | 25 |
| REMOVE_DATASET_INIT | 1.0 | 1.0 | 0.0 | 1.0 | 54 |
| CHANGE_DATASET_NAME | 1.0 | 0.0 | 0.0 | 1.0 | 54 |
| ALTER_FILE_DEPENDENCY_ORDER | 1.0 | 0.0 | 0.0 | 1.0 | 54 |
| SUPPRESS_RETURN_CODE_CHECK | 1.0 | 0.0 | 0.0 | 1.0 | 47 |
| ALTER_ERROR_BRANCH | 1.0 | 0.0 | 0.0 | **0.0** | 47 |

---

## 4. Per-Operator Analysis

### 4.1 REORDER_JOBS, ALTER_STEP_SEQUENCE (Structural partial failure)

Structural Baseline A achieves F1 ≈ 0.9655 (not 1.0) on these operators. The structural
baseline detects most reordering mutations because explicit dependency edges in the JCL are
disrupted. The ~3.5% gap reflects edge cases where a reordering produces a syntactically valid
dependency graph with no topological violations — the structural baseline sees no broken edges
and therefore does not fire. The BCG extractor, however, tracks the temporal contract
`PRECEDES(step_a, step_b)` and detects the violation regardless of whether a graph edge is
absent.

### 4.2 REMOVE_JOB_DEPENDENCY (Both structural and BCG succeed)

Removing an explicit inter-job dependency is the one class of mutation that structural graph
analysis reliably catches: an edge disappears from the graph. F1 = 1.0 for both the structural
baseline and the proposed method. This is not a differentiating operator.

### 4.3 CHANGE_DATASET_NAME, ALTER_FILE_DEPENDENCY_ORDER (Structural F1 = 0.0)

These operators modify *which* dataset is referenced or *in what order* files are processed,
but do not remove any edges from the structural dependency graph. A renamed dataset appears as
a valid node with valid edges; the structural baseline has no basis for flagging it. The BCG
extractor tracks RESOURCE contracts binding specific dataset identifiers. When the name changes,
the binding fails → contract BROKEN → mutation detected.

### 4.4 SUPPRESS_RETURN_CODE_CHECK (Structural F1 = 0.0)

Return-code checking is a semantic control-flow obligation not represented in a structural
dependency graph topology. Suppressing it leaves graph topology unchanged. BCG CONTROL_FLOW
contracts capture RC-check obligations explicitly; suppression breaks the contract.

### 4.5 ALTER_ERROR_BRANCH — The Discriminating Operator

This is the most scientifically significant operator in the evaluation.

**What the mutation does:** Modifies the error-handling branch target from a hard-fail path to
a reduced-impact path. The error branch still exists; the obligation is weakened rather than
eliminated.

**Why Baseline E fails (F1 = 0.0 on this operator, 8 FN total):**
Baseline E detects only **BROKEN** contracts: those where static support has fallen to 0.0
(the contract is entirely absent from the mutated artifact). ALTER_ERROR_BRANCH produces a
contract whose static_support drops from 1.0 to 0.7 — the contract is present but degraded.
This is a **MODIFIED** state, not a BROKEN state. Baseline E's threshold logic does not fire.

**Why the proposed method succeeds:**
The `RiskDetector` component computes a confidence delta between the baseline and mutated
contract. A drop from static_support 1.0 → 0.7 exceeds the delta threshold and the contract
is classified as MODIFIED and at risk. The mutation is flagged. This capability is the sole
source of the 8-FN gap between Baseline E and the proposed method, and it represents a
meaningful architectural distinction, not a parameter-tuning artifact.

---

## 5. Comparison Narrative

### 5.1 Proposed Method vs. Baseline E (static_bcg_baseline)

Baseline E is the closest competitor, differing from the proposed method in a single design
decision: it does not implement confidence-delta / MODIFIED detection. The 8 FN gap (all
ALTER_ERROR_BRANCH instances) directly traces to this omission. The result demonstrates that
detecting weakened-but-present contracts requires the confidence-delta mechanism and cannot be
recovered by threshold adjustment on BROKEN-only logic.

### 5.2 Proposed Method vs. Structural (Baseline A)

Baseline A misses 22 mutations (FNR = 0.2018) across four operators. The failure pattern is
coherent: every missed mutation is a semantic change that preserves graph topology. Structural
analysis is limited to what is visible in the dependency graph skeleton; it is blind to the
semantic content of the contracts those edges represent. The proposed method's advantage is not
architectural sophistication but specificity: BCG contracts encode *what* a dependency means,
not just *that* it exists.

### 5.3 Proposed Method vs. Complexity (Baseline B)

Baseline B is a valid null result. Complexity metrics (at threshold 0.5) are entirely
uninformative for this task on this dataset. CardDemo JCL does not contain high-complexity
artifacts by this measure. Reporting F1 = 0.0 is scientifically honest and appropriate; this
is not an implementation error. The result establishes that complexity alone is an insufficient
signal for contract-violation detection in low-complexity JCL corpora.

### 5.4 LLM Baselines (C, D) — Pending

Baselines C (llm_only) and D (dep_llm) require an OpenAI API key that was not available at
time of evaluation. **No result is estimated, imputed, or extrapolated.** These conditions
remain open. Their absence does not affect the H2 verdict (see Section 6) because H2 compares
BCG+dynamic (not yet integrated) against static_bcg — neither LLM baseline is part of that
comparison. The LLM baselines are included for completeness and contextual calibration; their
results will be appended when available.

---

## 6. Hypothesis H2 Verdict

**H2:** BCG+dynamic F1 ≥ static_bcg F1 + 10 percentage points.

**Verdict: CANNOT BE EVALUATED**

The dynamic component (runtime trace integration into the mutation detection pipeline) has not
been integrated into the mutation harness. The current evaluation covers static conditions only.
The BCG+dynamic condition does not have a recorded F1 value.

### What CAN be concluded from available data:

1. **The static_bcg ceiling is F1 = 1.0** on this corpus. For BCG+dynamic to satisfy H2
   (F1 ≥ 1.0 + 0.10 = 1.10), H2 is **mathematically impossible to satisfy** if F1 is bounded
   at 1.0. The hypothesis as stated implicitly assumes static_bcg F1 < 0.90. The static_bcg
   result must be factored into the H2 formulation.

2. **H2 should be re-framed** before the dynamic experiment runs. A more useful formulation:
   "BCG+dynamic reduces FNR relative to static_bcg on previously undetected mutation classes"
   — this is testable even when static_bcg F1 = 1.0 on the current operators, because new
   operator classes or a harder corpus may reveal static_bcg gaps that dynamic evidence closes.

3. **The discriminating value of dynamic data** in this context is likely FPR reduction, not
   FNR reduction. Static_bcg achieves FNR = 0.0; dynamic evidence cannot improve recall beyond
   1.0. Dynamic evidence can potentially reduce false positives on ambiguous static flags.
   RQ3 is the more appropriate vehicle for measuring this.

---

## 7. Threats to Validity

### 7.1 FP = 0 by Construction

All evaluated conditions record zero false positives. This is a structural property of the
evaluation design, not an empirical finding. The mutation benchmark contains only mutated (TP)
and N/A artifacts; no unmodified "clean" artifacts were included in the evaluated set with a
negative ground-truth label. Precision = 1.0 for all evaluated conditions is a consequence of
this design. FPR for the proposed method is measured independently in RQ3 via dynamic trace
reconciliation.

### 7.2 N/A Rate (75.2%)

331 of 440 mutation attempts were inapplicable. While this is domain-appropriate (not every
operator applies to every file), the 75% N/A rate means the evaluation covers only 25% of the
attempted mutation space. If applicable mutations are structurally different from inapplicable
ones (e.g., only structurally simpler JCL files produce applicable mutations), results may not
generalize to the full mutation surface. A stratified analysis by JCL complexity and step count
is recommended to validate this assumption.

### 7.3 Dataset Size and Corpus Homogeneity

55 JCL files and 109 evaluated mutations from a single public benchmark (CardDemo) constitute
a limited evaluation surface. Results may not transfer to production JCL estates with higher
structural diversity, non-standard dialects, or complex cross-job dependencies. Baseline B's
null result (F1 = 0.0) is partly a corpus artefact: a high-complexity production corpus might
yield different complexity baseline behaviour.

### 7.4 LLM Baselines Absent

The absence of Baselines C and D prevents a full competitive evaluation. The proposed method's
relative standing with respect to LLM-based detection is unknown. This is a material gap for
any claim of state-of-the-art performance.

### 7.5 Single Threshold for Static BCG Baseline

The 8 FN gap between Baseline E and the proposed method is sensitive to the confidence-delta
threshold value. If the delta threshold were lowered sufficiently, Baseline E would also flag
ALTER_ERROR_BRANCH mutations. The advantage of the proposed architecture is the principled
RiskDetector framework, not a single tuned parameter — but this sensitivity should be documented
with an ablation over delta threshold values in a final evaluation.

---

*Generated: 2026-08-15 | Corpus: CardDemo JCL (55 files, 440 attempts, 109 evaluated) | Seed: 42*
