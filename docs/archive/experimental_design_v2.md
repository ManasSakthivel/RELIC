# Experimental Design v2
## Audited and Strengthened Experimental Framework

**Version:** 0.2.0  
**Basis:** Empirical methods audit (subagent 4) + hostile reviewer audit (subagent 7)

---

## PART 1: CRITICAL ISSUES IDENTIFIED AND RESOLVED

| Issue | Severity | Resolution |
|---|---|---|
| Benchmark construction timeline undocumented | CRITICAL | Protocol in Part 3 |
| Mutation oracle may not be independent of BCG | CRITICAL | Independent oracle defined in Part 4 |
| Conjunctive H2 underreports partial victories | HIGH | Multi-part H2 in Part 2 |
| RQ3 uses independent tests (Mann-Whitney) instead of paired | HIGH | Paired Wilcoxon specified in Part 2 |
| TEMPORAL contracts untestable on public repos | HIGH | Explicitly stated in generalization scope |
| Confidence weights sum to 1.10 | MEDIUM | Fixed in bcg_formalization_v2.md |
| No effect size thresholds | MEDIUM | Cohen's d ≥ 0.3 required in Part 2 |

---

## PART 2: REVISED RESEARCH QUESTIONS AND HYPOTHESES

### RQ1 — Contract Recovery

**Precise question:** Does the BCG static extraction pipeline recover behavioral contracts from JCL+COBOL with sufficient precision and recall for modernization analysis, where ground truth is independently constructed DETERMINISTIC structural facts?

**H1 (multi-part):**
```
H1a (TEMPORAL):
  F1(BCG, TEMPORAL, level2_deterministic) ≥ 0.70
  with 95% bootstrap CI lower bound ≥ 0.60
  [bootstrap n=10000, seed=42]

H1b (RESOURCE):
  F1(BCG, RESOURCE, level2_deterministic) ≥ 0.70
  with 95% bootstrap CI lower bound ≥ 0.60

H1c (CONTROL_FLOW):
  F1(BCG, CONTROL_FLOW, level2_deterministic) ≥ 0.70
  with 95% bootstrap CI lower bound ≥ 0.60
```

**Decision rule:**
- H1 FULLY SUPPORTED: H1a ∧ H1b ∧ H1c
- H1 PARTIALLY SUPPORTED: exactly 2 of {H1a, H1b, H1c}
- H1 NOT SUPPORTED: fewer than 2 supported
- H1 FALSIFIED: macro-average F1 < 0.50

**Unit of analysis:** A behavioral contract instance (type, subject, predicate, object) extracted from CardDemo.

**Ground truth:** `benchmark/ground_truth/level2_deterministic.json` — independently constructed by domain expert(s) from CardDemo syntactic/structural analysis before BCG system is built. See Part 3.

**What counts as a true positive:** A contract extracted by BCG that matches a contract in the ground truth by (contract_type, subject_name, predicate, object_name). Matching uses name-based comparison, not entity_id (since IDs are artifact-path-dependent).

**What counts as a false positive:** A contract extracted by BCG with no corresponding entry in the ground truth.

**What counts as a false negative:** A ground truth contract not extracted by BCG.

---

### RQ2 — BCG vs. Baselines for Risk Detection

**Precise question:** Does execution-grounded BCG achieve higher F1 for modernization-risk detection (mutation detection) than five baselines, given that ground truth is defined as observable behavioral change verified by an independent execution oracle?

**H2 (multi-part):**
```
H2a (PRIMARY — most important):
  F1(BCG+dynamic) > F1(Baseline_E: static_BCG)
  with p < 0.01 (Bonferroni-corrected, n=5)
  AND Cohen's d ≥ 0.3
  [Tests: "Does dynamic evidence help beyond static BCG?"]

H2b (SECONDARY):
  F1(BCG+dynamic) > F1(Baseline_D: dep+LLM)
  with p < 0.01 (Bonferroni)
  AND Cohen's d ≥ 0.3
  [Tests: "Does formal BCG help beyond informal LLM+dependencies?"]

H2c (SUPPLEMENTARY):
  F1(BCG+dynamic) > F1(Baseline_A: structural)
  F1(BCG+dynamic) > F1(Baseline_B: complexity)
  F1(BCG+dynamic) > F1(Baseline_C: LLM-only)
  [Each with p < 0.01, Bonferroni-corrected]
```

**Decision rule:**
- H2 SUPPORTED: H2a ∧ H2b
- H2 PARTIALLY SUPPORTED: H2a XOR H2b
- H2 NOT SUPPORTED: ¬H2a
- H2 FALSIFIED: Baseline_D significantly outperforms BCG+dynamic

**Unit of analysis:** A mutation evaluation event. For each injected mutation (N=150: 50 per category F1/F2/F3), each system labels the mutation as RISKY or NOT_RISKY.

**Ground truth for mutations:** An independent execution oracle — see Part 4.

**False positive definition:** System predicts RISKY but oracle says NOT_RISKY (execution produces identical output before and after mutation).

**Null hypothesis for H2a:**
```
H0(H2a): F1(BCG+dynamic) ≤ F1(Baseline_E: static_BCG)
Alternative: F1(BCG+dynamic) > F1(Baseline_E)
```

---

### RQ3 — Dynamic Evidence Value

**Precise question:** Does dynamic execution evidence (varying from 0% to 100% coverage) reduce false-positive rate compared with static-only behavioral contract analysis, and how does the reduction vary with coverage level?

**H3 (two-part):**
```
H3a (PRIMARY — endpoint comparison):
  FPR(BCG, coverage=100%) < FPR(BCG, coverage=0%)
  Tested with: PAIRED Wilcoxon signed-rank test (NOT Mann-Whitney U)
  with p < 0.05
  AND absolute FPR reduction ≥ 5 percentage points
  
  [Coverage=0% is equivalent to Baseline E: no dynamic evidence]
  [Coverage=100% is the proposed system with full traces]

H3b (SECONDARY):
  F1(BCG, coverage=100%) ≥ F1(BCG, coverage=0%)
  [System does not regress overall when dynamic evidence is added]
```

**Unit of analysis:** A contract evaluated at a specific coverage level. Each contract contributes 6 paired observations (one per coverage level: 0%, 10%, 25%, 50%, 75%, 100%).

**Why paired test (NOT Mann-Whitney U):**
The same contracts are evaluated at each coverage level. This is a repeated-measures design. Paired Wilcoxon signed-rank test is more powerful (controls within-contract variance) and more appropriate.

**Statistical method (CORRECTED from v0.1):**
```python
# CORRECT: paired Wilcoxon signed-rank test
from scipy.stats import wilcoxon

fpr_at_0 = [evaluate_contract(c, coverage=0.0, oracle) for c in contracts]
fpr_at_100 = [evaluate_contract(c, coverage=1.0, oracle) for c in contracts]

statistic, p_value = wilcoxon(fpr_at_0, fpr_at_100)
fpr_reduction = mean(fpr_at_0) - mean(fpr_at_100)

# Report: FPR(0%) = X.XX, FPR(100%) = X.XX, reduction = X.XX pp, p = X.XXXX, d = X.XX
```

**Falsification condition:**
- H3a falsified if: FPR(100%) ≥ FPR(0%) with p > 0.05, or FPR reduction < 3 percentage points
- Negative finding is reportable: "dynamic evidence did not significantly reduce false positives; H3 not supported"

---

## PART 3: GROUND TRUTH CONSTRUCTION PROTOCOL

This protocol prevents the circular validation risk identified by the empirical methods audit.

### Phase 1: Independent Benchmark Construction (BEFORE system development)

```
Week 1-2: Benchmark construction (NO access to BCG system)
  
  Step 1: Define DETERMINISTIC operationally:
    DETERMINISTIC := contracts verifiable using ONLY:
      - JCL source code (syntax, tokens)
      - COBOL source code (syntax, tokens)
      - Copybook definitions
      - Basic control-flow analysis
      - ZERO human semantic judgment
    
    Examples (DETERMINISTIC):
      ✓ "JCL step B is declared after step A in job MYJOB" (syntactic)
      ✓ "COBOL program CBACT01C contains CALL 'CBACT02C'" (syntactic)
      ✓ "Step STEP01 declares DD ACCTFILE with DISP=NEW (producer)" (structural)
    
    Non-examples (NOT deterministic):
      ✗ "File A must exist before step B reads it" (semantic inference)
      ✗ "This program likely produces a report" (human interpretation)
  
  Step 2: Annotator A independently parses CardDemo with standard parser
    - Extracts all DETERMINISTIC contracts
    - Records: (contract_type, subject_name, predicate, object_name, location)
    - Does NOT use BCG system
  
  Step 3: Annotator B independently validates Annotator A's items
    - Computes Cohen's κ
    - If κ < 0.70: adjudicate (both annotators discuss)
    - Result: agreed-upon level2_deterministic.json

Week 3: Lock benchmark
  benchmark.lock()
  git commit -m "Lock level2_deterministic.json (κ=X.XX, N=YY items)"
  git tag v1.0-benchmark-frozen

Week 4+: BCG system development begins
  - Developers cannot modify locked benchmark
  - Benchmark.load() verifies lock before use
```

### Phase 2: Chain of Custody Documentation

```json
{
  "benchmark_metadata": {
    "dataset": "aws-carddemo",
    "dataset_version": "[git commit hash]",
    "annotator_a": "[role, not name required for review]",
    "annotator_b": "[role]",
    "annotation_date_range": "YYYY-MM-DD to YYYY-MM-DD",
    "locked_date": "YYYY-MM-DD",
    "inter_rater_kappa": "[computed value]",
    "kappa_per_type": {
      "TEMPORAL": "[value]",
      "RESOURCE": "[value]",
      "CONTROL_FLOW": "[value]"
    },
    "adjudicated_items": "[count]",
    "definition_used": "DETERMINISTIC: syntactic+structural, zero semantic inference",
    "independence_note": "Annotators had no knowledge of BCG system design or capabilities"
  }
}
```

---

## PART 4: INDEPENDENT EXECUTION ORACLE

The execution oracle must be **independent of BCG's dynamic analysis engine** to avoid the tautology risk.

### Oracle Definition

```
Oracle(mutation M) = RISKY iff:
  run_original(CardDemo, inputs) → output_original
  run_mutated(mutate(CardDemo, M), inputs) → output_mutated
  output_original ≠ output_mutated

Oracle(mutation M) = NOT_RISKY iff:
  output_original = output_mutated

Oracle inputs: 20 diverse business scenarios (documented in docs/test_scenarios.md)
Oracle environment: GnuCOBOL 3.1.2, same for all systems
Independence: Oracle uses execution comparison, NOT contract analysis
```

**Why this is independent:**  
The oracle compares program outputs directly. It does not use the BCG, does not extract contracts, and does not use the reconciliation engine. The BCG may internally use execution traces to validate contracts, but the oracle's judgment is based on observable output differences — a different mechanism.

**Potential issue with oracle completeness:**  
Some mutations may change internal behavior without changing observed outputs for the 20 test inputs (latent violations). This is a known limitation; the 20-input oracle is a conservative ground truth (may undercount risky mutations). This undercounting affects all systems equally, so comparative results are valid.

---

## PART 5: GENERALIZATION EXPERIMENT SCOPE

The held-out generalization experiment uses public COBOL repositories (no JCL).

**Explicitly stated limitation:**
```
Contract types testable on public COBOL repos:
  ✓ RESOURCE (file operations present in COBOL programs)
  ✓ CONTROL_FLOW (COBOL conditional logic present)

Contract types NOT testable on public repos:
  ✗ TEMPORAL (requires JCL job scheduling context; public repos are COBOL-only)

Generalization claims are therefore restricted to:
  "RESOURCE and CONTROL_FLOW contracts generalize to [outcome] on public COBOL programs.
   TEMPORAL contract generalization cannot be evaluated on available public datasets."
```

This must be explicitly stated in:
1. Paper Section 11 (Results) — generalization table
2. Paper Section 16 (Threats to Validity) — external validity threat
3. Experiment config: `experiments/generalization/config.yaml`

---

## PART 6: STATISTICAL METHODS SUMMARY

| RQ | Primary Test | Correction | Effect Size | Threshold |
|---|---|---|---|---|
| RQ1 (F1 ≥ 0.70) | Bootstrap CI (n=10000) | N/A (single estimate) | N/A | CI_lower ≥ 0.60 |
| RQ2 (baseline comparison) | Mann-Whitney U (independent groups) | Bonferroni n=5 | Cohen's d | d ≥ 0.3, p < 0.01 |
| RQ3 (coverage experiment) | Paired Wilcoxon signed-rank | Bonferroni n=15 | Cohen's d | d ≥ 0.3, p < 0.05 |
| Ablation | Mann-Whitney U | Bonferroni per ablation set | Cohen's d | d ≥ 0.2, p < 0.05 |

**Why Bonferroni for RQ3:** 5 coverage level comparisons × 3 contract types = 15 comparisons. Bonferroni α = 0.05/15 = 0.0033.

**Why paired for RQ3:** Same contracts evaluated at each coverage level (repeated measures). Paired test removes within-contract variance and is more powerful.

**Effect size requirement:** p-value alone is never sufficient. Cohen's d ≥ 0.3 required for any positive claim. This prevents "statistically significant but practically negligible" findings.

---

## PART 7: CONFOUNDING FACTOR MITIGATIONS

| Factor | Risk | Mitigation | Status |
|---|---|---|---|
| Benchmark construction bias | Benchmark built with knowledge of BCG | Annotators independent; benchmark locked before BCG built | Protocol defined |
| Mutation design bias | Mutations designed to favor BCG | Failure taxonomy created before BCG design; git timestamps verifiable | Must verify |
| Baseline implementation unfairness | LLM baseline uses suboptimal prompts | Best-practice prompting; chain-of-thought; 5-run variance | Protocol defined |
| Threshold tuning on test data | Confidence thresholds tuned post-hoc | Thresholds locked in config before experiments run | Enforced |
| Dynamic oracle contamination | BCG dynamic analysis and execution oracle use same traces | Oracle uses output comparison, not contract analysis | Protocol defined |
| Leakage from held-out set | Held-out system design influences system development | Held-out set never examined during development; strict partition | Protocol defined |

---

## PART 8: EXPERIMENT CONFIGURATION REQUIREMENTS

Each experiment config YAML must include:

```yaml
# Required fields for reproducibility
experiment_id: [string]
research_question: [RQ1|RQ2|RQ3|ablation|generalization]
hypothesis: [H1|H2|H3|ablation_An]
dataset: [path]
dataset_version: [git commit hash or checksum]
ground_truth: [path]
ground_truth_version: [git commit hash]
random_seed: 42
bootstrap_n: 10000
statistical_method: [paired_wilcoxon|mann_whitney_u|bootstrap_ci]
significance_threshold: 0.05
bonferroni_n: [integer]
effect_size_threshold: 0.3
output_dir: [path]

# Reproducibility tracking
created_date: [ISO8601]
configuration_locked: false  # set to true before running
locked_date: null
```
