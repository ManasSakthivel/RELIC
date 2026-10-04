# Research Methodology
## RELIC — Paper 1 Scope, RQs, Hypotheses, Baselines, Experimental Design

---

## PAPER 1 TITLE (Candidate)

**"Execution-Grounded Behavioral Contract Recovery for Legacy Batch Modernization Risk Detection"**

---

## PAPER 1 SCOPE (FROZEN)

| Component | In Scope | Out of Scope |
|-----------|----------|--------------|
| Artifact types | JCL, COBOL, Copybooks | BMS maps, PL/I, Assembler, CICS online |
| Contract types | Temporal, Resource, Control-flow | Data, State, Error contracts |
| Mutation categories | F1 (ordering), F2 (file availability), F3 (return code) | F4–F7 |
| Datasets | CardDemo + public COBOL repos | Enterprise/proprietary systems |
| Dynamic evidence | GnuCOBOL traces + JCL simulation | Production SMF traces |
| BCG features | V, E, C, P, D, Γ with reconciliation | LTL model checking |
| Evaluation | Automated metrics + ablations | Full human evaluation study |

---

## RESEARCH QUESTIONS AND HYPOTHESES

### RQ1 — Contract Recovery

**Question:** Can temporal, resource, and control-flow behavioral contracts be automatically recovered from JCL+COBOL legacy artifacts with sufficient precision and recall for modernization analysis?

**Hypothesis H1:** Static analysis of JCL+COBOL artifacts using the BCG extraction pipeline will recover ≥ 70% of deterministically verifiable contracts (F1 ≥ 0.70 against Level 2 ground truth).

**Operationalization:**
- Run static extraction on CardDemo development set
- Compare against Level 2 (deterministic) ground truth
- Measure precision, recall, F1 per contract type
- Measure extraction against Level 3 human-annotated ground truth

**Falsification condition:** F1 < 0.50 on deterministic contracts would suggest the extraction approach is fundamentally inadequate.

---

### RQ2 — BCG vs. Baselines for Risk Detection

**Question:** Does execution-grounded BCG analysis improve modernization-risk detection compared with structural dependency analysis, static complexity metrics, LLM-only analysis, and dependency+LLM analysis?

**Hypothesis H2:** The execution-grounded BCG achieves higher F1 for modernization-risk detection than all baselines (A–E).

**Operationalization:**
- Apply all 6 approaches (Baselines A–E + Proposed) to CardDemo with injected mutations
- Measure precision, recall, F1 per mutation category
- Measure false-positive rate

**Falsification condition:** Baseline D (dependency graph + LLM) achieves comparable or better F1 than BCG, suggesting the formal representation is not needed.

---

### RQ3 — Dynamic Evidence Value

**Question:** Does execution evidence reduce false positives compared with static-only behavioral contract analysis?

**Hypothesis H3:** BCG with dynamic evidence achieves lower false-positive rate and higher precision than BCG without dynamic evidence (Baseline E: static BCG).

**Operationalization:**
- Compare Baseline E (static BCG) vs. Proposed (static + dynamic BCG)
- Measure false-positive rate, precision, recall, F1 per contract type
- Vary dynamic coverage: 10%, 25%, 50%, 75%, 100%

**Falsification condition:** False-positive rate for static-only ≈ static+dynamic would suggest dynamic evidence does not contribute, challenging a core premise of the work.

---

## BASELINES

### Baseline A — Structural Dependency Analysis
**Description:** Extract structural dependencies (call graph, data flow, file dependencies) from JCL+COBOL using static analysis. Flag mutations that alter dependency structure.
**Implementation:** Program slicing + call graph construction. No behavioral contract abstraction.
**Reference:** Tip 1995 (slicing), standard program analysis.

### Baseline B — Static Complexity/Risk Metrics
**Description:** Compute McCabe cyclomatic complexity, coupling, cohesion, file-dependency count for each affected artifact. Risk score = weighted combination of metrics. Flag high-delta as risky.
**Implementation:** Standard complexity metrics on COBOL + JCL.
**Reference:** McCabe 1976, Halstead 1977.

### Baseline C — LLM-Only Semantic Analysis
**Description:** Provide LLM with artifact source code and mutation description. Ask: "Does this change introduce a semantic regression?" No structural analysis.
**Implementation:** GPT-4o (or equivalent) with structured prompt.
**Reference:** Fan et al. 2023, Hou et al. 2024.

### Baseline D — Dependency Graph + LLM
**Description:** Provide LLM with artifact source + structural dependency graph + mutation description.
**Implementation:** Baseline A output + Baseline C prompt augmented with dependency context.
**Reference:** Combination of structural and LLM-based approaches.

### Baseline E — Static BCG (No Dynamic Evidence)
**Description:** Full BCG with static extraction, provenance, and contract representation, but WITHOUT dynamic evidence or reconciliation. All contracts remain STATIC_CANDIDATE.
**Implementation:** This work's static pipeline, reconciliation disabled.
**Note:** This is the most important ablation baseline. It directly tests whether dynamic evidence contributes.

### Proposed — Execution-Grounded BCG
**Description:** Full BCG with static extraction + dynamic evidence from GnuCOBOL traces + JCL simulation + reconciliation + confidence update.

---

## EXPERIMENTAL DESIGN

### Experiment E1 — Contract Recovery (RQ1)

| Variable | Value |
|----------|-------|
| Dataset | CardDemo development set |
| Ground truth | Level 2 (deterministic) + Level 3 (human annotated) |
| Metrics | Precision, Recall, F1 per contract type |
| Analysis | Per-type breakdown, error analysis |
| Output | `results/rq1/contract_recovery.csv` |

### Experiment E2 — Risk Detection Comparison (RQ2)

| Variable | Value |
|----------|-------|
| Dataset | CardDemo development + validation set |
| Mutations | F1+F2+F3 operators, N=50 mutations per category |
| Ground truth | Execution oracle where possible; deterministic otherwise |
| Metrics | Precision, Recall, F1, FPR, FNR per baseline per mutation type |
| Analysis | Statistical: Mann-Whitney U test, effect size (Cohen's d) |
| Output | `results/rq2/risk_detection.csv` |

### Experiment E3 — Dynamic Evidence Value (RQ3)

| Variable | Value |
|----------|-------|
| Independent variable | Dynamic evidence presence (0/1) and coverage level (10/25/50/75/100%) |
| Dependent variable | False-positive rate, Precision, Recall, F1 |
| Dataset | CardDemo development set |
| Analysis | ANOVA on coverage levels; Tukey HSD post-hoc |
| Output | `results/rq3/dynamic_coverage.csv` |

### Experiment E4 — Ablation Study

Evidence dimensions removed one at a time:

| Ablation | Removed Component |
|----------|------------------|
| A1 | No provenance tracking |
| A2 | No dynamic evidence |
| A3 | No cross-artifact (single-artifact extraction only) |
| A4 | No confidence model (binary valid/invalid) |
| A5 | No reconciliation (all contracts kept as STATIC_CANDIDATE) |

### Experiment E5 — Generalization (Held-Out)

| Variable | Value |
|----------|-------|
| Dataset | Held-out public COBOL repos (unseen during development) |
| Metrics | Same as E2 |
| Analysis | Compare in-distribution vs. out-of-distribution performance |
| Output | `results/generalization/` |

---

## STATISTICAL METHODOLOGY

- All experiments: 5 independent random seeds for any randomized component
- Effect sizes: Cohen's d for continuous metrics
- Significance: p < 0.05 threshold (Bonferroni corrected for multiple comparisons)
- Confidence intervals: 95% bootstrap CI (10,000 resamples)
- Never interpret p-value alone without effect size

---

## EXPERIMENTAL METHODOLOGY TEMPLATE

Every experiment defines:
```yaml
# experiments/rq1/config.yaml
research_question: RQ1
hypothesis: H1
dataset: datasets/carddemo/
ground_truth: benchmark/ground_truth/level2_deterministic.json
independent_variables: [extraction_method]
dependent_variables: [precision, recall, f1, contract_type_accuracy]
baselines: []
random_seed: 42
metrics: [precision, recall, f1, fpr, fnr]
statistical_method: bootstrap_ci
significance_threshold: 0.05
```
