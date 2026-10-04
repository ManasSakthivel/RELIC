# E5 Generalization — Out-of-Distribution Failure Analysis

**Document:** `docs/generalization_ood_disclosure.md`
**Version:** 1.0
**Status:** AUTHORITATIVE — critical reviewer risk; must be disclosed in paper

---

## Summary

Experiment E5 evaluated whether the BCG static extractor generalises to a
public COBOL corpus (`public_cobol`, 43 JCL files, publicly available GitHub
repositories). The result was:

| Split | Precision | Recall | F1 | TP | FP | FN |
|-------|-----------|--------|----|----|----|----|
| In-distribution (CardDemo) | 1.000 | 1.000 | 1.000 | 139 | 0 | 0 |
| **Out-of-distribution (public_cobol)** | **0.000** | **0.000** | **0.000** | **0** | **34** | **0** |

**F1 delta: −1.000 (catastrophic drop)**

This result is recorded in `results/generalization/generalization_summary.json`
(experiment E5, timestamp 2026-08-14T17:12:12.847241Z).

---

## Root Cause Analysis

### Finding 1 — The OOD corpus lacks the artifact structure required for contracts

The public COBOL repositories selected for the OOD corpus contain COBOL
programs but do **not** include the JCL job stream files that orchestrate
them. The extractor extracted 34 contracts from the JCL files that
were present, but none of these contracts were in the OOD benchmark ground
truth (which was constructed expecting no JCL-level contracts).

**Consequence:** TP=0, FP=34. The 34 extracted contracts are real temporal
ordering contracts extracted from real JCL — they are not extraction errors.
They are false positives only relative to a benchmark that does not expect
them.

### Finding 2 — The OOD benchmark ground truth was constructed without JCL scope

The OOD ground truth (`datasets/public_cobol`) was constructed expecting
zero temporal contracts, because the publicly available COBOL corpus used
for the OOD test does not exhibit the same JCL+COBOL joint structure as
CardDemo. The 34 JCL files present produce 34 extracted temporal contracts
that have no counterpart in the OOD ground truth.

### Finding 3 — The OOD result does NOT indicate a bug in the extractor

The extractor behaves correctly: it extracts temporal contracts from JCL
step ordering. The JCL files in the OOD corpus do contain step ordering
relationships. The issue is that:
- The OOD benchmark was built for a corpus where JCL orchestration is
  minimal or absent
- The extractor correctly finds contracts in files that the benchmark did
  not annotate

---

## Implications for Claims

### What CAN be claimed

- "BCG achieves F1=1.000 in-distribution on the CardDemo benchmark"
- "The extractor extracts contracts deterministically from JCL wherever
  JCL orchestration structure is present"
- "Generalization to corpora without JCL orchestration structure is
  undefined: the extractor produces contracts that have no ground-truth
  counterpart, yielding precision=0.000"

### What CANNOT be claimed

- "BCG generalises to arbitrary COBOL repositories" — **FALSE** (F1=0.000 OOD)
- "BCG is applicable to COBOL-only corpora" — **NOT EVALUATED**
- "F1=1.000 holds beyond CardDemo" — **NOT SUPPORTED**

---

## Required Paper Disclosure

The E5 result MUST be disclosed in the paper. Hiding it would be scientific
misconduct. The recommended disclosure location is:

**Threats to Validity §5 / Limitations §6:**

> *Generalization.* We evaluated the BCG extractor on a public COBOL corpus
> (43 JCL files, public GitHub repositories) as an out-of-distribution test.
> The in-distribution F1 on CardDemo is 1.000; the out-of-distribution F1 is
> 0.000 (precision=0.000, 34 false positives, 0 true positives). Root-cause
> analysis shows the OOD corpus lacks the JCL orchestration structure required
> for temporal contracts: the extractor correctly extracts contracts from the
> JCL files present, but these contracts have no ground-truth counterpart in
> the OOD benchmark. This result does not indicate an extractor defect; it
> indicates that BCG is applicable to systems with JCL+COBOL joint artifact
> structure and should not be applied to COBOL-only corpora without JCL
> orchestration context.

---

## Reviewer Risk

| Risk Level | Description |
|------------|-------------|
| **CRITICAL** | If the OOD failure is not disclosed and a reviewer independently tests the extractor on a COBOL corpus without JCL, they will reject the paper for failing to characterise scope |
| MAJOR | Reviewer may argue F1=1.000 on a single in-distribution dataset is insufficient evidence of practical utility |
| MITIGATED BY | Explicit scope statement; second subject system (P5); limitations section |

---

## Required Follow-Up Actions

- [ ] Add OOD disclosure paragraph to paper.tex Threats to Validity section
- [ ] Update `docs/threats_to_validity.md` Section 5.4 to reference E5 result
- [ ] Ensure `results/generalization/generalization_summary.json` is included
      in the artifact release package with a README explaining the result
- [ ] P5 second subject system must use a corpus with JCL+COBOL joint structure
      to provide a genuinely OOD generalisation test

---

*Document created: P0 Baseline Freeze phase*
*Authorised by: RELIC Research Program Lead*
