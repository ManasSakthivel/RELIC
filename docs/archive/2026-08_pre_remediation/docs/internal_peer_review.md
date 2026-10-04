# Internal Peer Review
## LEGACY-CONTRACT — Hostile Reviewer Analysis

**Instructions:** Act as a hostile but fair program committee reviewer at ICSE/FSE. Identify every reason to reject this paper. For each, provide severity, rationale, evidence, fix, and status.

---

# TOP 15 REASONS THIS PAPER COULD BE REJECTED

---

## REJECTION REASON 1 — "This is just Daikon for COBOL"

**PROBLEM:** Daikon (Ernst et al. 2007) already mines behavioral properties (invariants) from execution traces. A reviewer may argue that applying this pattern to COBOL/JCL is an incremental engineering contribution, not a research contribution.

**SEVERITY:** High — this is the most likely first-round rejection reason.

**WHY IT MATTERS:** If the paper is perceived as "Daikon for mainframes," the novelty claim collapses.

**EVIDENCE:** Daikon mines data invariants from execution traces. This system mines temporal ordering and resource contracts from static AND dynamic evidence across heterogeneous artifacts. These are different problems. But a superficial read may not see the distinction.

**FIX:**
1. Explicitly acknowledge Daikon in Section 5 (Related Work) with a precise comparison table.
2. State clearly: Daikon mines DATA invariants (value-level properties) from OO execution. This system mines TEMPORAL and RESOURCE obligations (ordering and availability contracts) from cross-artifact LEGACY BATCH systems using both static and dynamic evidence. The problem, the artifacts, the contract semantics, and the use case are all different.
3. Show an example where Daikon would produce invariants that are irrelevant to modernization-risk detection, while BCG produces actionable temporal contracts.

**STATUS:** Mitigatable with careful framing. Must be addressed in paper draft.

---

## REJECTION REASON 2 — "The contribution is a combination of known techniques"

**PROBLEM:** Static analysis of COBOL exists (Sneed 2008, Pessoa et al. 2022). Dynamic invariant mining exists (Daikon). Static+dynamic combination exists (Naik et al. 2006). Graph representations exist. Provenance tracking exists. The reviewer may argue the paper combines known components without a novel idea.

**SEVERITY:** High.

**WHY IT MATTERS:** "Combination of existing techniques" is a common rejection in top venues unless the combination produces demonstrably better results than the sum of its parts.

**EVIDENCE:** Our novel axis: (1) the specific combination for the specific problem (cross-artifact behavioral contract recovery for modernization risk); (2) the explicit reconciliation of static/dynamic evidence with formal conflict taxonomy; (3) the formal provenance-aware IR that enables counterfactual analysis. None of these exist in combination.

**FIX:** The experimental results must DEMONSTRATE that the combination produces better outcomes than any individual component (ablation study E4). If the ablation shows each component contributes, the "just a combination" objection weakens substantially.

**STATUS:** Must be demonstrated empirically, not just argued.

---

## REJECTION REASON 3 — "CardDemo is too small / not representative"

**PROBLEM:** CardDemo is a sample application built for demonstration purposes, not a real enterprise application. A reviewer may argue that results on CardDemo have no ecological validity for real mainframe systems with millions of LOC.

**SEVERITY:** High.

**WHY IT MATTERS:** External validity is the primary threat for this type of evaluation.

**EVIDENCE:** We have no access to real enterprise mainframe systems due to confidentiality. This is documented as a limitation.

**FIX:**
1. Run generalization experiment on held-out public systems (even if small).
2. Be very explicit that claims are scoped to "batch COBOL+JCL systems comparable to CardDemo."
3. Document CardDemo's characteristics precisely: number of programs, JCL files, copybooks, LOC, job chains, contract density.
4. Motivate why CardDemo is the best available public benchmark, not just convenient.

**STATUS:** Partially mitigatable. External validity threat must be prominently disclosed. Cannot be fully resolved without enterprise data.

---

## REJECTION REASON 4 — "Dynamic evidence is not real mainframe execution"

**PROBLEM:** Using GnuCOBOL on Linux as "dynamic evidence" for a z/OS mainframe application is methodologically questionable. A reviewer will correctly note that GnuCOBOL ≠ z/OS.

**SEVERITY:** High.

**WHY IT MATTERS:** If the dynamic evidence is not representative of real mainframe execution, RQ3 ("does dynamic evidence help?") tests a different question than claimed.

**EVIDENCE:** GnuCOBOL implements COBOL-85/2002 with COBOL 2002 extensions but differs from IBM Enterprise COBOL in: COMP-3 handling in some edge cases, sort/merge behavior, external file I/O, runtime error codes, CICS/IMS interface (not present in batch).

**FIX:**
1. Label all dynamic evidence as "instrumented GnuCOBOL execution" throughout.
2. Explicitly enumerate the known differences and test whether they affect the contract types in scope (temporal, resource, control-flow).
3. Argue that for temporal and resource contracts (ordering and file availability), GnuCOBOL execution is semantically equivalent to z/OS for the batch programs in CardDemo (no CICS, no IMS, no vendor extensions).
4. Threat to validity section must address this prominently.

**STATUS:** Arguable but must be explicitly addressed. Not a showstopper if scoped properly.

---

## REJECTION REASON 5 — "Mutations are too simple / don't reflect real failures"

**PROBLEM:** Injecting single-operator mutations (reorder jobs, remove COND check) may be too simple to represent real modernization complexity. A reviewer may argue that real modernization failures are multi-component interactions.

**SEVERITY:** Medium-high.

**WHY IT MATTERS:** If mutations are not realistic, the evaluation measures the system's ability to detect simple artificial faults, not real modernization risks.

**EVIDENCE:** Our mutation taxonomy is empirically grounded (failure taxonomy docs). However, we acknowledge that compound failures are not represented in Paper 1.

**FIX:**
1. Emphasize the empirical grounding of each mutation operator (cite sources).
2. Show examples of real-world mutations that correspond to each operator.
3. Add compound mutations (2+ operators simultaneously) as an additional experiment, even if reported as exploratory.
4. Frame single-operator mutations as controlled conditions, not claims of full real-world coverage.

**STATUS:** Addressable.

---

## REJECTION REASON 6 — "No statistical significance or effect sizes"

**PROBLEM:** Reporting precision/recall/F1 numbers without confidence intervals, statistical tests, or effect sizes is insufficient at top venues.

**SEVERITY:** High.

**WHY IT MATTERS:** Without statistical rigor, reported differences between BCG and baselines may be noise.

**FIX:**
1. Bootstrap confidence intervals for all metrics.
2. Mann-Whitney U test for pairwise comparisons.
3. Cohen's d for effect sizes.
4. Bonferroni correction for multiple comparisons.
5. All implemented in `src/evaluation/statistics.py`.

**STATUS:** Must be implemented. Non-negotiable.

---

## REJECTION REASON 7 — "The BCG formalism is not formally evaluated"

**PROBLEM:** Claiming a "formal intermediate representation" without formally analyzing its properties (completeness, consistency, decidability) is a methodological gap.

**SEVERITY:** Medium.

**WHY IT MATTERS:** If the BCG is claimed as a formal contribution, its formal properties should be stated.

**FIX:**
1. State the formal properties that ARE claimed: typed vertex/edge sets, per-contract provenance, explicit validation states.
2. State the formal properties that are NOT claimed: completeness (cannot be claimed without LTL), decidability of satisfaction (not claimed for static-extracted contracts).
3. Frame BCG as a "formal intermediate representation" not a "formal verification framework."
4. Optional: prove a small soundness lemma for temporal contract extraction (e.g., if JCL grammar says STEP-A before STEP-B then ∀ executions satisfying preconditions: A ≺ B).

**STATUS:** Framing fix + small lemma where possible.

---

## REJECTION REASON 8 — "The confidence model is ad hoc"

**PROBLEM:** The multi-dimensional confidence model with weights is potentially arbitrary. Reviewers may argue the weights are tuned to maximize reported performance.

**SEVERITY:** Medium.

**WHY IT MATTERS:** Ad hoc confidence models undermine the scientific validity of confidence-based claims.

**FIX:**
1. Set confidence weights BEFORE seeing evaluation results (documented in research decisions).
2. Run sensitivity analysis on weights.
3. Report ablation: does changing weights significantly alter risk detection performance?
4. Never optimize weights to maximize reported metrics.
5. Alternatively: train weights on development set, report on held-out set.

**STATUS:** Protocol must be followed strictly.

---

## REJECTION REASON 9 — "Baselines are weak / unfairly implemented"

**PROBLEM:** If baselines are implemented poorly or without optimization, the proposed method will appear stronger than it actually is.

**SEVERITY:** High.

**WHY IT MATTERS:** Unfair baseline comparison is a major methodological flaw.

**FIX:**
1. Implement baselines to their best documented specifications.
2. For LLM baselines: use best-practice prompt engineering (chain-of-thought, few-shot examples).
3. Validate baseline implementations against published results on comparable tasks where possible.
4. Release baseline implementations for external validation.

**STATUS:** Must be verified during implementation.

---

## REJECTION REASON 10 — "Results are on a single dataset, no generalization"

**PROBLEM:** Single-dataset evaluation is insufficient for claims of generality.

**SEVERITY:** High.

**FIX:** Generalization experiment (E5) on held-out public COBOL repositories. Even if these are small, they demonstrate the system works on unseen artifacts. Report performance degradation explicitly.

**STATUS:** Addressed by Experiment E5. Must be executed.

---

## REJECTION REASON 11 — "Contract recovery precision is not high enough to be useful"

**PROBLEM:** If precision is low (many false-positive contracts), the BCG is noisy and engineers would not trust it.

**SEVERITY:** Medium-high.

**WHY IT MATTERS:** The practical usefulness argument depends on precision being high enough for engineers to act on the output.

**FIX:**
1. Report precision/recall trade-off curve.
2. Argue that even imperfect recovery is better than no behavioral contract representation (compare with Baseline A/B).
3. If precision is below 0.7, analyze why and discuss what additional evidence would improve it.

**STATUS:** Must be measured. Cannot be guaranteed in advance.

---

## REJECTION REASON 12 — "The provenance model is described but not experimentally evaluated"

**PROBLEM:** The paper describes a rich provenance model but may not show that provenance actually improves any outcome.

**SEVERITY:** Medium.

**FIX:** Ablation A4: remove provenance. Show whether provenance-unaware contract representation has different risk-detection performance. Also: human evaluation (if conducted) should ask whether provenance helps engineers trust and act on results.

**STATUS:** Ablation A4 is defined. Execute it.

---

## REJECTION REASON 13 — "The paper conflates static-contract inference with behavioral specification"

**PROBLEM:** Behavioral contracts that are inferred from source code are hypotheses about intended behavior, not verified specifications. Reviewers may object to calling inferred artifacts "contracts."

**SEVERITY:** Medium.

**WHY IT MATTERS:** Terminology matters. Using "contract" for unvalidated inferences may be seen as overclaiming.

**FIX:**
1. Distinguish clearly: STATIC_CANDIDATE contracts are "behavioral contract hypotheses." Only GROUND_TRUTH and HUMAN_VALIDATED contracts are "verified behavioral contracts."
2. Use consistent terminology throughout paper.
3. Never call a STATIC_CANDIDATE a "verified contract."

**STATUS:** Terminology fix. Must be consistent in paper.

---

## REJECTION REASON 14 — "No real engineer evaluation / practical usefulness not demonstrated"

**PROBLEM:** Without human evaluation showing engineers benefit from BCG output, the practical usefulness claim is unsubstantiated.

**SEVERITY:** Medium (for Paper 1; high for a systems paper).

**WHY IT MATTERS:** The claim is that BCG "helps engineers make better modernization decisions." Without measurement, this is an untested claim.

**FIX:**
1. Be explicit that Paper 1 does NOT include a human evaluation study. This is future work.
2. Frame Paper 1 as establishing: (a) that contracts can be recovered, (b) that BCG detects risks better than baselines. The practical usefulness hypothesis is a testable future question.
3. Do NOT claim practical usefulness in Paper 1 conclusions.

**STATUS:** Scope correctly.

---

## REJECTION REASON 15 — "The system is complex but the research question is narrow"

**PROBLEM:** The implementation is large (parsers, BCG, reconciliation, UI, baselines, experiments) but Paper 1 answers only 3 research questions. Reviewers at venues like ICSE may expect a tighter contribution-to-effort ratio.

**SEVERITY:** Medium.

**WHY IT MATTERS:** A complex system that answers simple questions suggests the complexity is not scientifically necessary.

**FIX:**
1. The complexity IS necessary because the problem requires it (cross-artifact parsing, evidence reconciliation, provenance). Make this argument explicit.
2. The research platform is designed for multiple papers (roadmap). Paper 1 is the focused first contribution.
3. Emphasize that each architectural component is necessary for the RQs (ablation study demonstrates this).

**STATUS:** Argument must be made explicitly in the paper's introduction and methodology sections.

---

# SUMMARY SEVERITY MATRIX

| # | Issue | Severity | Mitigatable? |
|---|-------|----------|-------------|
| R1 | "Just Daikon for COBOL" | High | Yes |
| R2 | Combination of known techniques | High | Empirically |
| R3 | CardDemo too small | High | Partially |
| R4 | GnuCOBOL ≠ z/OS | High | Yes (framing) |
| R5 | Mutations too simple | Medium-High | Yes |
| R6 | No statistical rigor | High | Yes (implement) |
| R7 | BCG not formally evaluated | Medium | Yes |
| R8 | Ad hoc confidence | Medium | Protocol |
| R9 | Weak baselines | High | Yes (implement) |
| R10 | Single dataset | High | Partially |
| R11 | Precision too low | Medium-High | Measured |
| R12 | Provenance not evaluated | Medium | Ablation |
| R13 | Conflating inference and specification | Medium | Terminology |
| R14 | No practical evaluation | Medium | Scope correctly |
| R15 | Complex for narrow question | Medium | Argument |

---

# FINAL ASSESSMENT

The paper is publishable if:
1. RQ2 and RQ3 show statistically significant improvements (R2, R6)
2. Daikon comparison is explicit and precise (R1)
3. CardDemo characteristics are fully documented and generalization experiment is run (R3, R10)
4. GnuCOBOL evidence is clearly labeled throughout (R4)
5. Ablation study demonstrates each BCG component contributes (R2, R12)
6. Baselines are fairly implemented (R9)

The paper is NOT publishable if:
- Results are fabricated or p-hacked
- Dynamic evidence is presented as mainframe production evidence
- Confidence scores are called probabilities
- Daikon overlap is not acknowledged
- Generalization experiment is skipped
