# RELIC — Final Closure Baseline Audit
<!-- Created: Final Closure Sprint (Phase 1) — 2026-08-30 -->

This document records the **exact starting state** of the repository at the beginning of the Final Closure Sprint.
It is a read-only snapshot and must not be modified.

---

## Git State

| Item | Value |
|---|---|
| Branch | main |
| HEAD commit | b78b385 |
| HEAD message | final-closure: fix FINAL_RESULTS.md stale RQ1 values (split-fix correction); update evidence ledger v3.0 with Stanford-level adversarial findings |
| Dirty files | `results/rq1/rq1_independent.json` (one-line timestamp change only — no data change) |
| Untracked | `.bob/` directory (IDE artifacts) |
| Stash | empty |

---

## Verified Experiment Results (Starting State)

### RQ1 — Contract Recovery

| Metric | Value | Source |
|---|---|---|
| micro-F1 | 1.0000 | rq1_independent.json (committed + dirty, data unchanged) |
| micro-precision | 1.0000 | rq1_independent.json |
| micro-recall | 1.0000 | rq1_independent.json |
| macro-F1 | 0.5455 | rq1_independent.json |
| 95% CI (macro-F1) | [0.2727, 0.8182] | rq1_independent.json |
| Total TP | 21 | rq1_independent.json |
| Total FP | 0 | rq1_independent.json |
| Total FN | 0 | rq1_independent.json |
| n_jcl_files | 11 (held_out split) | rq1_independent.json |
| h1_verdict | SUPPORTED | rq1_independent.json |

**FINAL_RESULTS.md consistency:** CONFIRMED — FINAL_RESULTS.md matches rq1_independent.json.

### RQ2 — Mutation Risk Detection

| Metric | Value | Source |
|---|---|---|
| BCG proposed F1 | 1.0000 | rq2_summary.json |
| BCG proposed TP | 104 | rq2_summary.json |
| Baseline A F1 | 0.8995 | rq2_summary.json |
| Baseline E F1 | 0.9600 | rq2_summary.json |
| Baseline B F1 | 0.0000 | rq2_summary.json |
| LLM-C F1 | 0.0377 (lower bound) | llm_c_results.json |
| LLM-D F1 | 0.1091 (lower bound) | llm_d_results.json |
| n_evaluated_mutations | 104 | rq2_summary.json |
| n_not_applicable | 336 | rq2_summary.json |
| n_attempted | 440 | rq2_summary.json |
| Negative TN | 144 | negative_summary.json |
| Negative FP | 0 | negative_summary.json |
| Negative FPR | 0.0000 | negative_summary.json |

### RQ3 — Dynamic Evidence

| Metric | Value | Source |
|---|---|---|
| STATIC_DYNAMIC_SUPPORTED | 56 | rq3_dynamic_results.json |
| STATIC_DYNAMIC_CONFLICT | 1 | rq3_dynamic_results.json |
| NOT_OBSERVED | 4 | rq3_dynamic_results.json |
| Dynamic validation rate | 0.918 | rq3_dynamic_results.json |
| Real execution validation rate | 0.000 | Derived (0/61) |
| n_contracts | 61 | rq3_dynamic_results.json |
| n_traces (real) | 2 | rq3_dynamic_results.json |
| n_traces (simulated) | 38 | rq3_dynamic_results.json |
| n_traces (synthetic excluded) | 3 | rq3_dynamic_results.json |

---

## Verified Manifest State

| Manifest | Version | Frozen | Hash/Status |
|---|---|---|---|
| FINAL_RESULTS_MANIFEST.json | v1.6 | true | All experiment entries verified |
| experiment_lock.json | v1.0 | LOCKED | config hashes present |
| ground_truth_manifest.json | v1.0 | false (locked field) | 463 items, 139 positive |
| dataset_manifest.json | — | — | 2 datasets, 161+50 artifacts |
| SPLITS_60_20_20.json (carddemo) | — | — | held_out=11 JCL, dev=33 JCL |

---

## Test State

```
305 passed, 1 warning in 0.32s
```

All 305 tests passing. 1 warning (unknown config option — benign pytest warning).

---

## File Inventory (Key Artifacts)

| Path | Status |
|---|---|
| results/rq1/rq1_independent.json | CURRENT (1-line timestamp drift — no data change) |
| results/rq2/rq2_summary.json | CURRENT |
| results/rq2/rq2.csv | CURRENT |
| results/rq2/llm_c_results.json | CURRENT |
| results/rq2/llm_d_results.json | CURRENT |
| results/rq2/negative_summary.json | CURRENT |
| results/rq3/rq3_dynamic_results.json | CURRENT |
| results/rq3/coverage_experiment.json | CURRENT |
| results/FINAL_RESULTS.md | CURRENT (corrected) |
| results/FINAL_RESULTS_MANIFEST.json | CURRENT (v1.6) |
| docs/evidence_ledger.md | v3.0 (to be updated) |
| docs/limitations.md | CURRENT |
| docs/final_hostile_review.md | CURRENT |
| datasets/carddemo/ | CURRENT (zip + extracted) |
| datasets/public_cobol/ | CURRENT (zip + extracted) |
| datasets/public_jcl/ | EMPTY |

---

## Identified Pre-Sprint Issues (Requiring Fix During Sprint)

1. **evidence_ledger.md worst-case F1 rounding error:** Reports 0.384; correct value is 0.382 (2×104/(2×104+336) = 0.3824). → WILL FIX
2. **Mann-Whitney U test incorrectly specified:** MWU assumes independence; mutations are paired observations. McNemar's test is correct. McNemar: b=19, c=0, χ²=17.05, p<0.0001, significant at Bonferroni α=0.01. → WILL DOCUMENT
3. **Second system search incomplete:** No exhaustive search documented from this sprint. → WILL COMPLETE
4. **No docs/final_failure_analysis.md exists yet.** → WILL CREATE
5. **No docs/FINAL_SCIENTIFIC_STATUS.md exists yet.** → WILL CREATE
6. **No docs/final_closure_baseline.md exists yet.** (this file) → CREATING NOW

---

## Stale Artifacts (None Found)

No stale numerical contradictions found between raw experiment outputs and documented results.
FINAL_RESULTS.md was previously corrected (commit b78b385) to match rq1_independent.json.
The dirty file (rq1_independent.json timestamp) contains no data-changing differences.

---

## Conclusion

The repository is in a clean, consistent starting state for the Final Closure Sprint.
All key metrics are verified against raw data. No contradictory artifacts exist.
The sprint will complete:
- Second-system search (→ SECOND SYSTEM NOT SCIENTIFICALLY VALIDATED)
- Statistical corrections (McNemar, F1 rounding)
- Failure analysis document
- Final scientific status document
- Three-panel adversarial review
- Final evidence ledger update (v4.0)

---

*Created: RELIC Final Closure Sprint Phase 1 | 2026-08-30*
