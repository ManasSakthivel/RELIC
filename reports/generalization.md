# Generalization Report

**Date:** 2025

---

## In-Distribution (CardDemo)

| Metric | Value |
|--------|-------|
| JCL files | 38 CardDemo + 20 OMP-subset (used in GT construction) |
| Contracts extracted | 139 |
| GT positives | 139 |
| F1 | 1.0000 (circular — Level-2 GT) |

## Out-of-Distribution (OMP COBOL JCL — held-out)

| Metric | Value |
|--------|-------|
| JCL files | 43 |
| Contracts extracted | 34 |
| GT positives matching | 0 |
| FP | 34 |
| F1 | 0.0000 |

---

## Analysis

The F1=0.0 for OMP COBOL does NOT indicate the extractor fails on OMP JCL. It indicates the Level-2 ground truth does not include OMP JCL contracts in its positive set. The 34 contracts extracted from OMP JCL are real structural facts — they just weren't included in the GT because the GT was built from the 58 specific source files.

**This is a ground truth construction limitation, not an extractor generalization failure.**

To properly evaluate generalization:
1. Run the extractor on OMP JCL files
2. Build a separate Level-2 GT from OMP JCL
3. Evaluate in-distribution (CardDemo) vs out-of-distribution (OMP) with separate GTs
4. Report F1 degradation between the two datasets

**Expected result:** F1 should be near 1.0 on OMP as well (same deterministic extractor). Generalization of contract recovery at Level-2 is not the interesting question — it is Level-3 generalization (do human-labeled implicit contracts generalize?) that is scientifically meaningful.

---

## Verdict

**Generalization experiment is INCONCLUSIVE in current form.** The ground truth construction methodology needs to be fixed before generalization results can be reported.
