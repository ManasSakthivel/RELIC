# RQ1 Analysis: Precision and Recall of BCG Contract Extraction

**Research Question:** Does the BCG extractor achieve Precision ≥ 0.75 and F1 ≥ 0.70 on the
constructed benchmark?

**Hypothesis H1:** F1 ≥ 0.70 and Precision ≥ 0.75 → **HYPOTHESIS_SUPPORTED**

---

## 1. Executive Summary

The BCG contract extractor achieves perfect precision and recall (P = 1.0, R = 1.0, F1 = 1.0)
against the constructed benchmark across all three contract types: TEMPORAL, RESOURCE, and
CONTROL_FLOW. The bootstrap 95% confidence interval is [1.00, 1.00] (n = 10,000 iterations,
seed = 42).

**These results must be interpreted with significant caution.** The benchmark is a Level-2
DETERMINISTIC ground truth, constructed by the same extractor family whose outputs it evaluates.
Consequently, F1 = 1.0 is mathematically expected and constitutes an idempotency check, not a
proof of behavioral correctness. The result confirms that the extractor is internally consistent
and deterministic; it does not confirm that extracted contracts correspond to true semantic
obligations in the JCL artifacts. Section 5 addresses this threat at length.

---

## 2. Methodology

### 2.1 Benchmark Construction

| Parameter | Value |
|---|---|
| Source JCL files | 58 |
| Ground-truth positives (n_gt_positives) | 139 |
| Extraction run (n_extracted) | 139 |

Ground truth was constructed at **Level 2 — DETERMINISTIC**: the reference set was produced by
running the BCG static extractor in a canonical configuration and treating its output as the
reference. No human annotation was performed. No independent toolchain was consulted. This
classification is critical to interpreting all results in this section.

### 2.2 Evaluation Metrics

Standard binary information-retrieval metrics were computed at the contract instance level:

- **Precision** = TP / (TP + FP)
- **Recall** = TP / (TP + FN)
- **F1** = 2 × Precision × Recall / (Precision + Recall)
- **FNR** (False Negative Rate) = FN / (TP + FN)

False Positive Rate (FPR) is **undefined** for this benchmark. The benchmark is a closed set of
known positives; no ground-truth negatives were labeled. Any claim about FPR would require a
distinct corpus of JCL constructs that are semantically obligation-free — a corpus that does not
exist in this evaluation.

### 2.3 Bootstrap Confidence Interval

95% confidence intervals were computed via non-parametric bootstrap resampling:

- Resampling iterations: 10,000
- Random seed: 42
- Method: percentile bootstrap over per-file F1 values
- F1 CI: **[1.00, 1.00]**

The zero-width interval reflects the homogeneous nature of Level-2 GT, not measurement
stability across independent replications.

---

## 3. Results

### 3.1 Aggregate Results

| Metric | Value |
|---|---|
| TP | 139 |
| FP | 0 |
| FN | 0 |
| Precision | 1.000 |
| Recall | 1.000 |
| F1 | 1.000 |
| FNR | 0.000 |
| F1 95% CI (bootstrap, n=10k, seed=42) | [1.00, 1.00] |

### 3.2 Per-Type Breakdown

| Contract Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| TEMPORAL | 113 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| CONTROL_FLOW | 23 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| RESOURCE | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| **Total** | **139** | **0** | **0** | **1.000** | **1.000** | **1.000** |

**Note on RESOURCE type:** Only 3 positive instances were observed across 58 source files. While
F1 = 1.0 is recorded, this sample is insufficient to draw reliable conclusions about extractor
behavior on RESOURCE contracts. Any future evaluation must ensure substantially more RESOURCE
examples before type-level claims are made.

---

## 4. Hypothesis Verdict

**H1:** BCG extractor achieves F1 ≥ 0.70 and Precision ≥ 0.75 on the benchmark.

| Sub-criterion | Threshold | Observed | Status |
|---|---|---|---|
| F1 | ≥ 0.70 | 1.000 | ✓ MET |
| Precision | ≥ 0.75 | 1.000 | ✓ MET |

**Verdict: HYPOTHESIS_SUPPORTED**

**Reasoning:** Both thresholds are cleared with a wide margin. However, the support is
conditional on the Level-2 GT construction method (see Section 5). H1 is supported *within the
scope of this benchmark*. The hypothesis cannot be considered validated against independent,
human-labeled ground truth until Level-3 annotation is completed.

---

## 5. Threats to Validity

### 5.1 Ground-Truth Circularity (PRIMARY THREAT)

The dominant threat to this evaluation is **circular validation**. The Level-2 ground truth was
produced by the same extractor family being evaluated. This means:

1. The evaluation measures whether the extractor produces the same output on two runs of the
   same code — an **idempotency check**, not a correctness check.
2. Any systematic error in the extractor's extraction logic (e.g., missing an entire class of
   contract pattern, mis-scoping a TEMPORAL ordering rule) is invisible to this benchmark because
   the same error is present in both the reference and the system output.
3. F1 = 1.0 is the mathematically expected outcome under Level-2 GT given deterministic
   execution. A result below 1.0 would indicate a non-determinism bug, not a precision/recall
   deficiency.

This threat is not a weakness of the experimental design per se — Level-2 GT is a legitimate and
necessary milestone for confirming extractor stability. However, it **cannot substitute** for
external validation. All claims derived from this section must be scoped accordingly.

### 5.2 RESOURCE Type Under-Representation

Three positive RESOURCE instances are insufficient for any statistically meaningful statement
about extractor performance on that contract type. The RESOURCE row in the per-type table should
be treated as a tracking observation, not a result.

### 5.3 FPR Undefined / Open-Set Problem

No ground-truth negative set was constructed. The benchmark contains only known positives drawn
from 58 JCL files. Whether the extractor hallucinates contracts on obligation-free code is
entirely untested. FPR = undefined is a hard constraint, not a gap that bootstrap statistics
can address.

### 5.4 No Human Annotation

No domain expert reviewed extracted contracts to verify that they correspond to intended
semantic obligations in the source JCL. An extracted contract may be syntactically correct and
internally consistent while still failing to capture the true operational dependency it purports
to represent.

### 5.5 Dataset Scope

All 58 source files derive from a single benchmark codebase (CardDemo / related JCL corpus).
Generalizability to production JCL from other mainframe estates, tool versions, or coding
conventions is unestablished.

---

## 6. What This Result Proves vs. What It Does Not Prove

### This result PROVES:

- The BCG extractor is **deterministic and internally consistent**: running it twice on the same
  58 files produces identical output (139 contracts, identical structure).
- All three contract types (TEMPORAL, RESOURCE, CONTROL_FLOW) are **stably extracted** across
  the corpus; there are no random omissions or duplications between runs.
- The extractor is a viable foundation for downstream evaluation (RQ2, RQ3) because its outputs
  are reproducible.

### This result does NOT prove:

- That extracted contracts are **semantically correct** representations of true JCL obligations.
- That the extractor would achieve F1 ≥ 0.70 against a **human-annotated** reference set.
- That the extractor has **acceptable precision** on JCL that does not contain any behavioral
  contracts (the FPR question).
- That results **generalize** beyond the CardDemo JCL corpus.
- That **RESOURCE contract extraction** is reliable (n = 3 is insufficient).

---

## 7. Required Next Steps: Level-3 Human Annotation

To replace the Level-2 idempotency check with a meaningful correctness evaluation, the following
work must be completed:

1. **Recruit annotators.** A minimum of two independent annotators with JCL/mainframe domain
   expertise should label each of the 58 source files for behavioral contracts without reference
   to BCG extractor output.

2. **Define annotation schema.** The TEMPORAL / RESOURCE / CONTROL_FLOW taxonomy and the
   contract attribute schema (subject, predicate, object, confidence, scope) must be documented
   as an annotation guide with worked examples and adjudication rules for inter-annotator
   disagreement.

3. **Compute inter-annotator agreement.** Cohen's κ or Krippendorff's α should be reported
   before any system evaluation. A κ < 0.6 indicates the annotation task itself is underspecified.

4. **Re-run evaluation against Level-3 GT.** The same precision/recall/F1 pipeline can be
   reused; only the reference set changes.

5. **Construct a negative set.** Include JCL files known to contain no behavioral contracts (or
   sections of files with no obligations) to enable FPR measurement.

6. **Expand RESOURCE coverage.** Actively source JCL that exercises RESOURCE contracts to raise
   the per-type sample above a minimum of ~30 instances for statistical adequacy.

Until Level-3 annotation is complete, H1 should be reported as **HYPOTHESIS_SUPPORTED
(Level-2 GT only)** in any publication or technical report.

---

*Generated: 2026-08-15 | Corpus: CardDemo JCL (58 files) | Extractor: BCG static (deterministic) | Bootstrap: n=10,000, seed=42*
