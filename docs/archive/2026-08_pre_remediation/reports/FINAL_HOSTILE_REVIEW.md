# FINAL HOSTILE REVIEW SUMMARY
# LEGACY-CONTRACT Research Platform
# Generated: 2026-08-17 (post LLM baseline completion)

Six independent reviewer agents evaluated the paper against the verified experimental state.

---

## REVIEW PANEL

- Reviewer 1: ICSE Empirical Software Engineering
- Reviewer 2: Static Analysis / Programming Languages
- Reviewer 3: Mainframe / Legacy Systems
- Reviewer 4: AI / LLM Systems
- Reviewer 5: Reproducibility / Open Science
- Reviewer 6: Hostile (maximally critical)

---

## AGGREGATE ISSUE COUNT

| Priority | Count | Issues |
|---|---|---|
| P0 (blocking) | 4 | LLM baselines validity, single-system eval gap, "execution-grounded" overstatement, F2/F3 n=1 |
| P1 (major) | 8 | LLM baseline framing, GnuCOBOL/z/OS scope, oracle independence, N/A rate buried, macro-F1 lead result, BCGDiff fix disclosure |
| P2 (minor) | 8 | CI gaps, NOT_OBSERVED framing, confidence calibration, Daikon comparison |

---

## P0 ISSUES (Must address for submission)

### P0-1: LLM Baselines — Invalid Due to 97–98% API Error Rate
**Issue:** F1=0.0377 (Baseline C) and F1=0.1091 (Baseline D) are computed from 3 and 7 successful calls out of 248. This is not a valid empirical comparison.  
**Status:** ACKNOWLEDGED IN PAPER — paper discloses API error counts and uses "lower bound" language, but reviewers 1, 4, and 6 judge this insufficient.  
**Resolution path:** 
- OPTION A: Re-run with reliable API endpoint (local model or higher quota) before submission
- OPTION B: Remove LLM F1 scores from the comparative table entirely; report only as "preliminary lower bound" in text
- OPTION C (minimum acceptable): Add explicit language in abstract: "Due to API infrastructure constraints (245–241/248 API errors), the LLM baseline F1 scores represent lower bounds derived from 3–7 successful responses and cannot be used for quantitative comparison."  
**Current paper status:** DISCLOSED but not sufficiently foregrounded. Needs stronger caveat.  
**Recommended fix for this submission:** Apply OPTION C minimum language plus add TABLE NOTE in baseline comparison table.

### P0-2: "Execution-Grounded" Title vs. 95% Simulated Traces
**Issue:** 38/40 traces are EXECUTION_SIMULATED. The paper title and framing claim execution grounding.  
**Status:** DISCLOSED in paper (trace composition stated clearly). Title uses "Execution-Grounded" accurately if EXECUTION_SIMULATED is a form of execution grounding.  
**Resolution path:** Add 1-sentence clarification in abstract that "execution grounding" includes both real and simulated JCL traces.  
**Recommended fix:** Add to abstract: "Execution evidence includes JCL step-ordering simulation (EXECUTION_SIMULATED) and GnuCOBOL real-execution traces; the GnuCOBOL execution environment is explicitly not z/OS."

### P0-3: F2/F3 Operator Sample Sizes of n=1
**Issue:** REMOVE_DATASET_INIT, CHANGE_DATASET_NAME, ALTER_FILE_DEPENDENCY_ORDER each have n=1 evaluated case. F1 scores from n=1 are statistically meaningless.  
**Status:** DISCLOSED in TABLE_7 and error analysis. But these n=1 results appear in aggregate F1=1.000 without per-category confidence.  
**Resolution path:** (a) Explicitly label F2 results as "preliminary, n=1" in Table 5 and text; (b) Remove them from aggregate F1=1.000 computation footnote; OR (c) Report separately.  
**Recommended fix:** Add TABLE_5 note: "F2 operators evaluated on n=1 instance each; these results are illustrative and not sufficient for per-operator statistical claims."

### P0-4: Benchmark Circularity / Closed-Set Design
**Issue:** FP=0 is by design (closed-set benchmark, all mutations are known violators). Presenting it as empirical evidence of low false-alarm rate is misleading.  
**Status:** PARTIALLY DISCLOSED — paper says "FP=0 by design: all mutations are applied to valid BCGs." But this is buried.  
**Resolution path:** Add sentence in abstract and Section 11: "FP=0 is a consequence of the closed-set benchmark design; open-world false-positive rate on unseen real-world changes remains unmeasured."  
**Recommended fix:** Already substantially disclosed. Strengthen abstract once sentence.

---

## P1 ISSUES (Major — should address)

### P1-1: Single-Dataset External Validity  
All results on CardDemo only. Enterprise generalization unverified.  
**Status:** DISCLOSED (L1 limitation, stated throughout). Cannot be fixed without new experiments.  
**Acceptable handling:** Explicitly scope contribution to "CardDemo-scale COBOL/JCL systems" in abstract.

### P1-2: Macro-F1 = 0.576 Should Lead RQ1  
Current framing leads with micro-F1=1.000, buries macro.  
**Status:** Both are reported. The explanation (zero-contract files) is in the text.  
**Fix:** Reorder RQ1 table reporting: lead with macro-F1 + CI, explain why micro is 1.000.

### P1-3: Daikon Comparison Missing  
No comparison against Daikon for TEMPORAL/RESOURCE contracts.  
**Status:** Not implemented. Would require additional experiment.  
**Acceptable handling:** Add to future work / limitations. Cannot add before this submission.

### P1-4: CONTROL_FLOW and RESOURCE Independent Validation Absent  
**Status:** DISCLOSED. Oracle covers TEMPORAL only. Cannot fix without human annotation.  
**Acceptable handling:** Current disclosure is adequate; strengthen scope statement.

### P1-5: BCGDiff Fix Disclosure  
Engine fix applied before evaluation. Critics question whether this is tuning.  
**Status:** DISCLOSED in §10.6, with explicit note that fix was a correction to evaluation logic, not to core algorithm.  
**Fix:** Add one sentence: "The engine fix was a correction to the evaluation harness; the core BCG representation and confidence model were not modified." Already substantially addressed.

### P1-6: "Not Observed" Semantics Ambiguity  
NOT_OBSERVED has three possible interpretations not formally distinguished.  
**Status:** Paper defines NOT_OBSERVED ≠ CONTRADICTED and describes reconciliation algorithm.  
**Fix:** Add clarifying sentence: NOT_OBSERVED means "no relevant dynamic observations retrieved from D" — it does not assert vacuous satisfaction.

---

## P2 ISSUES (Minor — fixable with text edits)

- P2-1: Add bootstrap CIs for all RQ2 operator-level F1 scores (currently only RQ1 has CI)
- P2-2: Analyze the 1 STATIC_DYNAMIC_CONFLICT case in more detail (already in §14 but could be expanded)
- P2-3: FPR=0 in combined benchmark table needs explicit "closed-set design" footnote
- P2-4: "SYNTHETIC_STATIC excluded by guard SI-01" — what is SI-01? Define in text.
- P2-5: Precision=1.000 for LLM baselines needs caveat (near-degenerate prediction set)
- P2-6: Model version stability for LLM reproducibility — note that model weights may drift

---

## ISSUES ALREADY WELL-ADDRESSED IN CURRENT PAPER

- ✅ LLM v1 discarded (semantics-preserving leak) — disclosed in §10.5
- ✅ NOT_OBSERVED ≠ CONTRADICTED — stated formally in §6.3, confirmed empirically in RQ3
- ✅ GnuCOBOL ≠ z/OS — explicit in abstract, §10.1, §16.4, §17 L2
- ✅ FP=0 by design — disclosed in §9.5 and results
- ✅ CardDemo single-dataset — explicit in §17 L1
- ✅ TEMPORAL-only oracle — explicit throughout
- ✅ Engine fix before evaluation — disclosed in §10.6
- ✅ LLM API error counts — disclosed in results table footnote
- ✅ Confidence not calibrated probability — §6.4, §17 L6
- ✅ No human validation — never claimed
- ✅ No enterprise generalization — never claimed
- ✅ No z/OS execution — never claimed

---

## PRIORITY FIXES REQUIRED BEFORE SUBMISSION

The following are the minimum changes to resolve P0 issues:

1. **Strengthen LLM caveat in abstract and Table 5**: Add "lower bound" language more prominently; add table footnote about API error rate. (30-minute edit)

2. **Add trace composition clarification to abstract**: One sentence about EXECUTION_SIMULATED being JCL step-ordering simulation. (10-minute edit)

3. **Label F2 n=1 results clearly in Table 7**: Add "n=1, illustrative" label. (10-minute edit)

4. **Strengthen "FP=0 by design" framing**: Add one sentence in abstract and Section 11 opening. (15-minute edit)

---

## REVIEWERS' OVERALL RECOMMENDATIONS

| Reviewer | Recommendation | Priority |
|---|---|---|
| R1 (ICSE Empirical SE) | WEAK REJECT | P1 |
| R2 (Static Analysis/PL) | WEAK REJECT | P1 |
| R3 (Legacy/Mainframe) | WEAK REJECT | P1 |
| R4 (AI/LLM) | WEAK REJECT | P0 |
| R5 (Reproducibility) | WEAK ACCEPT | P1 |
| R6 (Hostile) | REJECT | P0 |

---

## ASSESSMENT

The paper is at the threshold of "major revision" rather than outright rejection. The core contribution (confidence-delta detection for behavioral contract violations) is technically sound and the finding is specific enough to be credible. The main issues are:

1. **LLM baseline validity** — addressable by re-running OR by honest restructuring of claims (OPTION C minimum)
2. **External validity** — not fixable before this submission; requires explicit scope limitation in abstract
3. **F2 operator sample sizes** — addressable by text labeling
4. **Execution-grounded framing** — addressable by abstract clarification

None of these require new experiments for the minimum-fix path. The paper can be submitted with the changes listed in "Priority Fixes Required" above, with realistic expectation of major revision rather than outright rejection, and strong chance of acceptance at revision.

P0 COUNT: 4  
P1 COUNT: 8  
P2 COUNT: 8  
BLOCKING P0s REQUIRING EXPERIMENT: 0 (all addressable by text/table edits)  
