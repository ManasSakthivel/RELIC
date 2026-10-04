# Result Traceability — LEGACY-CONTRACT

Every empirical claim in the manuscript is traced from the text to the generating artifact.

---

## RQ1 — Contract Recovery

### Claim: "static BCG achieves precision=1.00, recall=1.00, F1=1.00 on 139 deterministic contracts"

```
MANUSCRIPT CLAIM
  paper/paper.md §11.1 (lines ~447–452)
    ↓
TABLE
  paper/tables/TABLE_4_rq1_recovery.md
    ↓
RESULT FILE
  results/rq1/rq1_summary.json
    → tp: 139, fp: 0, fn: 0, precision: 1.0, recall: 1.0, f1: 1.0
    ↓
EXPERIMENT
  experiments/rq1/config.yaml
    → baseline: StaticContractExtractor
    → ground_truth: benchmark/ground_truth/level2_deterministic.json
    → seed: 42
    ↓
DATASET
  datasets/carddemo/extracted/ (58 JCL files)
  datasets/public_jcl/ (OMP public JCL)
    ↓
CODE
  src/legacy_contract/static_analysis/extractor.py
  src/legacy_contract/evaluation/benchmark.py
  src/legacy_contract/evaluation/metrics.py
  src/legacy_contract/evaluation/runner.py
```

**⚠️ Tautology caveat:** Ground truth in `level2_deterministic.json` was annotated by
the `deterministic_extractor` — the same extraction family under evaluation. F1=1.0
confirms idempotence of the extractor, not that the extracted contracts correspond to
genuine behavioral obligations. Acknowledged in paper §11.1 and TABLE_4 caption.

---

## RQ2 — Risk Detection (Static Conditions)

### Claim: "static_bcg detects 109/109 mutations (F1=1.00) vs. structural baseline (F1=0.89, TP=87)"

```
MANUSCRIPT CLAIM
  paper/paper.md §11.2 (lines ~455–466)
    ↓
TABLE
  paper/tables/TABLE_5_baseline_comparison.md (rows: static_bcg, structural)
    ↓
RESULT FILE
  results/rq2/rq2_summary.json
    → static_bcg:   tp=109, fp=0, fn=0, f1=1.0000
    → structural:   tp=87,  fp=0, fn=22, f1=0.8878
    ↓
EXPERIMENT
  scripts/run_rq2.py
    → 440 mutations attempted, 109 evaluated (331 N/A for non-JCL operators)
    → operators: REORDER_JOBS, SWAP_DATASET, DROP_COND, ADD_REDUNDANT_STEP,
                 RENAME_DATASET, CHANGE_DISP, DROP_STEP, MODIFY_RC_THRESHOLD
    ↓
DATASET
  datasets/carddemo/extracted/ (CardDemo JCL corpus)
  benchmark/ground_truth/level2_deterministic.json
    ↓
CODE
  src/legacy_contract/mutations/engine.py      (8 operators)
  src/legacy_contract/risk/detector.py         (BCGDiff)
  src/legacy_contract/evaluation/runner.py     (experiment orchestration)
  baselines/structural/structural.py           (Baseline A)
```

### Claim: "4 of 8 operators are invisible to structural analysis (F3 and partial F2)"

```
MANUSCRIPT CLAIM
  paper/paper.md §12 (Abstract + §11.2 discussion)
    ↓
TABLE
  paper/tables/TABLE_6_per_operator.md
    → MODIFY_RC_THRESHOLD: structural F1=0.0, bcg F1=1.0
    → DROP_COND:           structural F1=0.0, bcg F1=1.0
    → RENAME_DATASET:      structural F1=0.0, bcg F1=1.0
    → CHANGE_DISP:         structural F1=0.0, bcg F1=1.0
    ↓
RESULT FILE
  results/rq2/rq2_summary.json → by_operator section
    ↓
CODE
  src/legacy_contract/mutations/engine.py
  baselines/structural/structural.py
```

---

## RQ1 — Pending (Level-3 Ground Truth)

### Claim: [RESULT_PENDING — Level-3 human annotation not yet available]

Non-circular evaluation requires Level-3 human-annotated ground truth. This
experiment cannot be traced until the annotation is complete.

**Status:** BLOCKED — future work.

---

## RQ2 — Pending (LLM Baselines C, D)

### Claim: [RESULT_PENDING — requires OPENAI_API_KEY]

```
MANUSCRIPT CLAIM
  paper/paper.md TABLE_5 rows: llm_only, dep_llm → [RESULT_PENDING]
    ↓
EXPERIMENT
  baselines/llm_only/llm_only.py   (Baseline C)
  baselines/dep_llm/dep_llm.py     (Baseline D)
    ↓
BLOCKER
  OPENAI_API_KEY not available in current environment
```

---

## RQ2 — Pending (BCG+Dynamic)

### Claim: [RESULT_PENDING — artifact_id mismatch blocks dynamic promotion]

```
MANUSCRIPT CLAIM
  paper/paper.md TABLE_5 row: bcg_dynamic → [RESULT_PENDING]
    ↓
EXPERIMENT
  scripts/run_dynamic_reconciliation.py
    → 0% promotion rate observed
    ↓
BLOCKER
  Artifact ID mismatch: traces generated with artifact_id=program_name,
  but contracts indexed by artifact_id=jcl_step_id.
  See: scripts/run_dynamic_reconciliation.py (artifact_id resolution section)
  Fix: Phase 7 blocker (map execution artifact_id → JCL step identifier)
```

---

## RQ3 — Pending (Dynamic Evidence Coverage)

### Claim: [RESULT_PENDING — no trace coverage experiment yet run]

```
MANUSCRIPT CLAIM
  paper/paper.md §11.3 → [RESULT_PENDING]
    ↓
EXPERIMENT
  experiments/rq3/config.yaml
    → coverage_levels: [0.10, 0.25, 0.50, 0.75, 1.00]
    ↓
BLOCKER
  CardDemo execution requires DB2/CICS/IMS — not available under GnuCOBOL alone.
  Simulated traces exist but artifact_id mismatch prevents contract promotion.
```

---

## Ablation — Static Conditions (E0–E6)

### Claim: "ablation conditions E0–E6 all achieve F1=1.00 (static only)"

```
MANUSCRIPT CLAIM
  paper/paper.md §12 (Ablation Study) → [RESULT_PENDING for full section]
  Note: static conditions are available
    ↓
RESULT FILE
  results/ablation/ablation_summary.json
    → E0 through E6: f1=1.0 for all static-only conditions
    ↓
EXPERIMENT
  experiments/ablation/config.yaml
    ↓
CODE
  src/legacy_contract/evaluation/runner.py (ablation sub-experiment)
```

**Note:** Ablation finds no differentiation among static conditions because the
deterministic extractor achieves perfect precision/recall on the Level-2 GT (which
it also generated). Meaningful ablation requires Level-3 GT or dynamic conditions.

---

## Statistical Claims

### Claim: "bootstrap confidence intervals at 95% level"

```
MANUSCRIPT CLAIM
  paper/paper.md §10.5 (Statistical methodology)
    ↓
RESULT FILE
  results/rq1/rq1_summary.json → bootstrap_ci section
  results/rq2/rq2_summary.json → bootstrap_ci section
    ↓
CODE
  src/legacy_contract/evaluation/metrics.py
    → MetricsCalculator.compute_with_ci()
    → n_bootstrap=10000, seed=42
```

### Claim: "Mann-Whitney U test with Bonferroni correction (α=0.01, n=5)"

```
MANUSCRIPT CLAIM
  paper/paper.md §10.5
    ↓
CODE
  src/legacy_contract/evaluation/metrics.py → mann_whitney_u()
  src/legacy_contract/evaluation/runner.py → n_comparisons=5 (fixed: was 15)
    ↓
STATUS
  [RESULT_PENDING] — per-mutation F1 list not yet populated by pipeline stubs;
  pairwise tests will execute when BCG+dynamic condition is unblocked.
```

---

## Figure Traceability

| Figure | Script | Data Source | Status |
|--------|--------|-------------|--------|
| Fig 1 — BCG Architecture | `figures/fig_architecture.py` | Design (no data) | Ready to generate |
| Fig 2 — BCG Formal Model | `figures/fig_bcg_formal.py` | Design (no data) | Ready to generate |
| Fig 3 — Reconciliation | `figures/fig_reconciliation.py` | Design (no data) | Ready to generate |
| Fig 4 — Baseline Comparison | `figures/fig_baseline_comparison.py` | `results/rq2/rq2_summary.json` | Partial (static conditions only) |
