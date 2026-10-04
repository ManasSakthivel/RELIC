# Final Hostile Review — LEGACY-CONTRACT
**Reviewer:** Subagent H (Hostile Reviewer)
**Standard:** ICSE/FSE/ASE strong-accept bar
**Status of paper:** Pre-experiment manuscript skeleton. All results `[RESULT_PENDING]`.
**Date:** 2025

---

## Executive Summary

This manuscript presents a well-motivated, carefully documented research platform for behavioral contract recovery from legacy batch (JCL+COBOL) systems. The formalism is precise, the scientific integrity disciplines are genuine, and the threat-awareness is unusually thorough for a pre-experiment paper. However, the work faces **five potentially fatal problems** that must be resolved before experiments begin, and **eleven major problems** that will cause mandatory major revisions at any top venue. The gravest issues are: (1) a ground-truth circularity that renders RQ1 trivially true for Level-2 contracts, (2) a 150-item mutation benchmark drawn from a single ~30-program application — too small for statistically meaningful claims, (3) three incomplete baselines (B, D, E) that mean RQ2 cannot currently run, (4) a confidence-weight sum of 1.10 that is documented but not yet corrected in the paper (it is corrected in bcg_formalization_v2.md but not in paper.md §6.4, which still shows weights summing to 1.10), and (5) the `10pp F1 improvement` and `15pp FPR reduction` thresholds stated in the final report's RQ2/RQ3 hypotheses are not reproducibly justified. If these five issues are not resolved before experiments run, the numbers collected will not support the stated claims. The work is **not yet rejectable on novelty grounds**, but it will be rejected on evaluation soundness unless the issues below are addressed.

---

## Dimension 1: Novelty (N1–N5)

### N1 — "This is Daikon for COBOL"

**Criticism:** The surface-level elevator pitch — infer behavioral properties from execution traces with confidence scores and use them for verification — is structurally identical to Daikon (Ernst et al. 2007). The paper's rebuttal (temporal vs. data invariants; cross-artifact vs. single-program) is valid but is buried in `novelty_analysis_v2.md` and does not appear with sufficient force in `paper.md §5.1`. A reviewer who reads only the paper will not see the side-by-side Daikon vs. BCG capability table that `reviewer_attack_v2.md` recommends.

**Severity:** MAJOR

**Evidence:** `paper.md §5.1` says "We acknowledge Daikon as the methodological ancestor" but provides no table comparing capability dimensions. `reviewer_attack_v2.md A1` explicitly requires a side-by-side comparison table in Related Work — this table is absent from the paper draft.

**Proposed response:** Add the Daikon vs. BCG capability table (as specified in `reviewer_attack_v2.md A1`) to `paper.md §5.1`. Include a concrete worked example showing a contract that Daikon cannot express (e.g., "JCL step CBACT01C must complete and produce ACCTFILE before CBACT02C reads it").

**Pre-experiment fix needed?** YES — paper text fix; no code required.

---

### N2 — "This is specification mining applied to legacy batch"

**Criticism:** Lo et al. 2006 (W29) and Ammons et al. 2002 (W30) mine temporal specifications from execution traces. Both are listed in `novelty_analysis_v2.md` as required additions to the literature but are **not yet cited in `paper.md §5.1`**. A reviewer familiar with specification mining will raise this immediately. The paper's Related Work section (§5.1) does not cite W29, W30, W31 (GIST), W32–W36 anywhere.

**Severity:** MAJOR

**Evidence:** `paper.md §5.1` cites W1 (Klaedtke), W4 (Daikon), W5 (Flanagan), W6 (Xie) — but not Lo 2006, Ammons 2002, or GIST (Lorenzoli 2008). `novelty_analysis_v2.md Part 4` explicitly lists these 8 works as "must be added before paper submission" and they are absent.

**Proposed response:** Add W29–W36 to `paper.md §5.1`. Explicitly address GIST with the five-axis differentiation documented in `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §3`.

**Pre-experiment fix needed?** YES — paper text fix.

---

### N3 — "Cross-artifact is just engineering work"

**Criticism:** The claim that combining JCL and COBOL analysis is non-trivially novel can be challenged as "two existing parsers glued together." The rebuttal requires demonstrating that the *semantic* mismatch between JCL batch scheduling semantics and COBOL procedural semantics creates non-trivial challenges. This argument is not yet made concretely in the paper.

**Severity:** MINOR

**Evidence:** `paper.md §7.1` describes the three-stage pipeline mechanically but does not articulate *why* combining JCL and COBOL is technically hard. The `novelty_analysis_v2.md CLAIM 1` rebuttal (JCL DISP semantics, step ordering vs. method invocations) is not in the paper.

**Proposed response:** Add a paragraph to §7.1 or §2.1 articulating the specific semantic challenges of cross-artifact integration (DISP semantics, JCL step ordering ≠ method call ordering, dataset lifecycle across step boundaries).

**Pre-experiment fix needed?** YES — paper text fix.

---

### N4 — "ConfidenceVector is a weighted sum with unjustified weights"

**Criticism:** The six confidence weights (0.25, 0.30, 0.15, 0.10, 0.20, 0.10 in the paper; corrected to 0.25, 0.30, 0.10, 0.10, 0.20, 0.05 in v2 doc) are not justified by any theoretical or empirical argument. A reviewer will ask: why is dynamic_support weighted twice as much as static_support? Why does human_validation outweigh cross_artifact_support? The paper offers no answer.

**Severity:** MAJOR

**Evidence:** `paper.md §6.4` states the weights without justification. `bcg_formalization_v2.md §4` notes "Confidence is an evidence-strength score, NOT a probability" and "Calibration study required before probabilistic interpretation" — but gives no argument for the specific weight magnitudes. Compounding this, `paper.md §6.4` still shows the *old* weights summing to 1.10 (`cross_artifact_support: 0.15`, `execution_frequency: 0.10`), contradicting the v2 correction in `bcg_formalization_v2.md`.

**Proposed response:** (a) Correct `paper.md §6.4` to show the v2 weights (sum = 1.00). (b) Add a sensitivity analysis to the ablation study: report results with equal weights, with the proposed weights, and with a learned weight vector (if feasible). (c) State explicitly that the weights are heuristic and subject to calibration.

**Pre-experiment fix needed?** YES — paper.md weight correction needed before experiments to avoid running experiments with a paper that contradicts the implementation.

---

### N5 — "Provenance tracking is a solved problem"

**Criticism:** Provenance in program analysis systems (e.g., in abstract interpretation frameworks, taint analysis tools) is not novel. The novelty claim for per-contract provenance in `novelty_analysis_v2.md CLAIM 5` is the weakest of the five claims and will attract "this is obvious bookkeeping" objections.

**Severity:** MINOR

**Evidence:** `novelty_analysis_v2.md CLAIM 5` rates provenance defensibility at 7/10 and notes the Daikon objection ("Daikon has confidence; your multi-dimensional version is just more dimensions"). The paper does not preempt this objection.

**Proposed response:** Frame provenance not as a novelty claim but as an *enabler* of the modernization audit trail use case. Move it from the contributions list to the discussion of practical utility. Reserve novelty claims for N1–N3 and the reconciliation taxonomy.

**Pre-experiment fix needed?** NO — framing fix only.

---

## Dimension 2: Evaluation Validity (E1–E5)

### E1 — Dataset is a single demonstration application

**Criticism:** AWS CardDemo has approximately 30 COBOL programs and 15 JCL files. FSE/ICSE reviewers routinely expect 5–10 independent systems for evaluation claims. The held-out set (OMP COBOL, ~50 programs, 0 JCL files) cannot evaluate TEMPORAL contracts at all. Effectively, the paper's primary contribution — cross-artifact temporal contracts — is evaluated on exactly one system.

**Severity:** CRITICAL

**Evidence:** `paper.md §10.1` states "Approximately 30 COBOL programs, 15 JCL files." `limitations.md L1` acknowledges "Real enterprise mainframe systems may have thousands of programs." `reviewer_attack_v2.md A4` rates this HIGH and notes "Reviewers at FSE/ICSE expect at least 5-10 independent systems." `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §13 R7` rates this MEDIUM but does not resolve it.

**Proposed response:** Before submission, search for and incorporate additional public JCL+COBOL repositories (OpenMainframe Project zorow samples; IBM public samples; additional GitHub repositories with JCL). Even 2–3 additional JCL-bearing systems would materially strengthen the cross-system generalization claim. Clearly scope all claims to "CardDemo-scale systems" if no additional systems are found.

**Pre-experiment fix needed?** YES — dataset expansion should be attempted before experiments begin; if unsuccessful, scope all claims accordingly.

---

### E2 — 150 mutations from one application is not a sufficient benchmark

**Criticism:** The RQ2 benchmark comprises 50 mutations × 3 categories = 150 mutation instances, all drawn from CardDemo's ~30 programs and ~15 JCL files. With this benchmark size, the statistical power of the Mann-Whitney U test is extremely limited. If BCG achieves F1 = 0.70 and Baseline A achieves F1 = 0.62 on 150 binary classification items, the effect may not be statistically significant after Bonferroni correction (α = 0.01 for 5 comparisons). The paper does not report a power calculation.

**Severity:** CRITICAL

**Evidence:** `experiments/rq2/config.yaml` specifies `n_mutations_per_category: 50` (total 150). `methodology.md` specifies `Mann-Whitney U test` with `Bonferroni corrected` α. No power analysis appears in any document. Statistical tests on 150 binary outcomes with α = 0.01 require a large effect size (Cohen's d ≥ 0.5) to achieve 80% power.

**Proposed response:** Conduct a power analysis *before* experiments run. If 150 mutations are insufficient for the stated α = 0.01 with expected effect sizes, increase N. A minimum of 50 mutations *per baseline comparison cell* (i.e., per contract type per baseline) would be more defensible — requiring 750 mutations minimum.

**Pre-experiment fix needed?** YES — N must be determined before experiments run.

---

### E3 — GnuCOBOL is the only source of "execution" evidence

**Criticism:** The paper's title contains "Execution-Grounded" as a key claim. But the execution environment is GnuCOBOL on Linux — not a mainframe. The `rq3/config.yaml` explicitly sets `trace_source_type: EXECUTION_SIMULATED`. The "execution-grounded" claim in the title and abstract is therefore partially misleading: it is open-source-simulator-grounded, not mainframe-execution-grounded.

**Severity:** MAJOR

**Evidence:** `experiments/rq3/config.yaml` line: `trace_source_type: EXECUTION_SIMULATED`. `limitations.md L2` acknowledges "GnuCOBOL implements COBOL-85/2002 but may differ from IBM Enterprise COBOL." `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §10` provides GnuCOBOL equivalence estimates: TEMPORAL ~90%, RESOURCE (sequential files) ~80%, CONTROL_FLOW (RC 0–4) ~75%.

**Proposed response:** Rename "Execution-Grounded" in the title to "Execution-Evidence-Grounded" or replace with "Dynamically-Validated." In the paper, formally quantify what fraction of RQ3 evidence is `EXECUTION` vs. `EXECUTION_SIMULATED` and report results separately for each source type.

**Pre-experiment fix needed?** YES — paper framing fix before submission; source-type breakdown should be added to RQ3 output variables.

---

### E4 — Oracle problem: mutations designed by detector's builders

**Criticism:** The mutation operators (F1–F3) were designed by the same research team that built the BCG detector. Even though the failure taxonomy predates the BCG design and references empirical sources, the fact remains that the team building the detector also decides which failures count as ground truth. An independent adversarial mutation set (designed by someone who has NOT seen the BCG) would be a stronger evaluation.

**Severity:** MAJOR

**Evidence:** `threats_to_validity.md §1.4` acknowledges "if mutations are designed with knowledge of the BCG's detection capabilities, the evaluation is biased." The mitigation ("mutations derived from external empirical sources BEFORE BCG is finalized") requires version-control evidence that mutation design predates BCG implementation — and this evidence is not yet documented. `reviewer_attack_v2.md A6` rates this HIGH.

**Proposed response:** (a) Document the git timeline: commit date of `failure_taxonomy.md` must predate commits to `static_analysis/extractor.py` and `reconciliation/engine.py`. Publish this timeline in the paper. (b) Consider adding a "blind mutation" condition: ask a colleague unfamiliar with the BCG to construct 10–20 additional mutations from the same empirical sources, then evaluate BCG on these blind mutations.

**Pre-experiment fix needed?** YES — version control audit needed before submission.

---

### E5 — CardDemo is a designed-to-be-migrated showcase, not a real production system

**Criticism:** CardDemo was created by AWS specifically to demonstrate mainframe modernization. It is designed with clear, clean, well-documented batch structure — precisely the kind of system where automated analysis is easiest. A real enterprise mainframe system has undocumented shortcuts, implicit initialization sequences, decades-old workarounds, and COBOL copybooks shared across hundreds of programs. CardDemo's implicit contracts are almost certainly more discoverable than real-world contracts.

**Severity:** MAJOR

**Evidence:** `literature_review.md W17` describes CardDemo as "a fully public, executable COBOL/JCL mainframe application provided by AWS for modernization research." `limitations.md L1` and `reviewer_attack_v2.md A4` acknowledge this limitation. However, the paper does not quantify how "clean" CardDemo is relative to real enterprise systems.

**Proposed response:** Add a "Dataset Complexity Assessment" subsection to §10.1 that characterizes CardDemo's structural properties (average COND parameter complexity, depth of inter-job dependency chains, fraction of implicit vs. explicit contracts) and explicitly compares these to published statistics on enterprise mainframe systems where available.

**Pre-experiment fix needed?** NO — characterization can be done alongside experiments.

---

## Dimension 3: Baseline Fairness (B1–B3)

### B1 — Three baselines (B, D, E) are not yet implemented

**Criticism:** `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §5` explicitly states: "Baselines B, D, E — Not yet [implemented]." Without Baseline E (Static BCG without dynamic evidence), RQ3 cannot be evaluated. Without Baseline D (Dep+LLM), the strongest alternative hypothesis for RQ2 cannot be tested. The paper skeleton already includes these baselines in §10.4 as if they exist. This is the single largest practical blocker.

**Severity:** CRITICAL

**Evidence:** `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §5 table`: Baselines B, D, E marked "⚠ Not yet." `methodology.md §BASELINES` describes all five baselines but they are not all implemented. `rq2/config.yaml` lists all five baselines as required independent variables.

**Proposed response:** Implement Baselines B, D, E before running any RQ2 or RQ3 experiment. Do not run experiments with placeholder baselines and fill in results later. Implementation must be validated against known behavior before the experiment clock starts.

**Pre-experiment fix needed?** YES — blocking.

---

### B2 — Baseline E (Static BCG) may trivially equal the proposed method on RQ1

**Criticism:** RQ1 evaluates contract recovery against Level-2 DETERMINISTIC ground truth. Baseline E (Static BCG, no dynamic evidence) uses the same static extractor. By construction, Baseline E must produce identical recovery metrics to the proposed method on RQ1's Level-2 ground truth (since Level-2 is derived from the same static parser). If RQ1 is evaluated against Level-2 only, adding dynamic evidence cannot change the score. This means RQ1 results tell us nothing about the value of dynamic evidence.

**Severity:** MAJOR

**Evidence:** `rq1/config.yaml` states: "All ground truth items in level2_deterministic.json are Level-2 DETERMINISTIC (mechanically verifiable structural facts). Do not use Level-3 human-annotated items in the RQ1 headline metric." This means dynamic evidence contributes zero to RQ1 performance by construction.

**Proposed response:** RQ1 should use Level-3 (human-annotated, implicit contracts) as a secondary evaluation target and report results separately. The dynamic evidence contribution should be measured at Level-3 where it has a chance to affect the outcome. If only Level-2 is available, RQ1 tests parser completeness, not behavioral contract recovery — and should be reframed accordingly.

**Pre-experiment fix needed?** YES — Level-3 ground truth must be annotated before RQ1 has meaningful content.

---

### B3 — LLM baseline may receive less context than the proposed method

**Criticism:** Baseline C (LLM-only) is given "artifact source code and mutation description." Baseline D (Dep+LLM) is given "artifact source + structural dependency graph + mutation description." Neither baseline is given the BCG's formal contract set as context — yet the proposed method uses contracts as the primary detection signal. The comparison is information-asymmetric: BCG uses a pre-computed formal contract set while LLM baselines are given raw source. This is a fair comparison only if we accept that the BCG's effort to extract contracts has no cost — but it does.

**Severity:** MINOR

**Evidence:** `methodology.md §Baseline C/D` descriptions. No document discusses equalizing the information available to LLM baselines by providing them with the BCG's extracted contracts.

**Proposed response:** Add a "Baseline F: LLM + BCG contracts" condition in the ablation study: provide the LLM with the full BCG contract set plus mutation description. If BCG+LLM beats BCG alone (without LLM), that demonstrates the formal representation and the LLM are complementary. If BCG+LLM does not beat Baseline C + BCG contracts, the formal representation's value is in the contract extraction, not in the formal structure per se.

**Pre-experiment fix needed?** NO — addition to ablation study.

---

## Dimension 4: RQ Operationalization (R1–R4)

### R1 — The "≥10pp F1" threshold in RQ2 has no principled justification

**Criticism:** `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §2` states H2 as "BCG + dynamic evidence will improve F1 by ≥10pp over the best static baseline." This specific threshold (10 percentage points) appears nowhere in the methodology, experimental design, or paper skeleton. It is not derived from effect size analysis, power calculation, or domain requirements. A reviewer will ask: why is 9pp insufficient and 11pp sufficient?

**Severity:** MAJOR

**Evidence:** `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §2 RQ2 hypothesis`: "F1 by ≥10pp." `paper.md §4 RQ2` states the hypothesis as "achieves higher F1 score... than the best baseline" with no specific threshold. The two documents contradict each other on what constitutes a confirmatory result.

**Proposed response:** Remove the ≥10pp threshold from H2 in the final report and use it only as a "practically meaningful" effect size benchmark in the discussion. The formal hypothesis should be "BCG+dynamic > best baseline (statistically significant, Bonferroni-corrected)" with effect size reported as a secondary measure. If a threshold is desired, derive it from a domain argument ("10pp is the minimum improvement an engineer would notice given current baseline FPR").

**Pre-experiment fix needed?** YES — hypothesis wording must be consistent across all documents before experiments.

---

### R2 — RQ3's "coverage threshold" operationalization conflates two distinct questions

**Criticism:** RQ3 asks two questions in one: (a) "does dynamic evidence reduce false positives?" and (b) "is there a coverage threshold beyond which additional traces provide diminishing returns?" These are separate scientific questions. The first requires a simple binary comparison (0% vs. ≥1% coverage). The second requires monotonicity analysis across coverage levels. Conflating them means a non-monotonic result (medium coverage helps, full coverage degrades) would be scientifically surprising but the RQ framing would make it hard to report clearly.

**Severity:** MINOR

**Evidence:** `experiments/rq3/config.yaml` simultaneously tests `coverage_level` from 0.0 to 1.0 and asks whether coverage "reduces FPR." The hypothesis H3 in `paper.md §4 RQ3` is "Adding dynamic execution evidence (E5 vs. E3) reduces the false-positive rate by at least 10 percentage points" — a binary hypothesis — while the config tests six coverage levels.

**Proposed response:** Split RQ3 into two formally stated sub-questions: RQ3a (does any dynamic evidence reduce FPR vs. static-only?) and RQ3b (at what coverage level does the benefit plateau?). Report H3a as the primary hypothesis and coverage analysis as secondary exploratory analysis.

**Pre-experiment fix needed?** YES — RQ framing fix before experiments begin to avoid post-hoc narrative adjustment.

---

### R3 — RQ1 tests parser completeness, not behavioral contract recovery

**Criticism:** RQ1 evaluates static extraction against Level-2 DETERMINISTIC ground truth. Level-2 ground truth consists of "mechanically verifiable structural facts" from the JCL grammar. But mechanically verifiable structural facts are exactly what the static parser extracts — so precision and recall against Level-2 measure *parser correctness*, not *behavioral contract recovery capability*. The interesting scientific question is whether the extracted facts constitute meaningful behavioral contracts, which requires Level-3 human annotation.

**Severity:** MAJOR

**Evidence:** `rq1/config.yaml` notes: "All ground truth items in level2_deterministic.json are Level-2 DETERMINISTIC. Do not use Level-3 human-annotated items in the RQ1 headline metric." `bcg_formalization_v2.md §3` notes "execution oracle → GROUND_TRUTH" and "deterministic structural fact → Level 2." Level-2 facts are precisely what the deterministic static extractor produces.

**Proposed response:** The paper must collect Level-3 (human-annotated) ground truth for at least a representative subset of contracts before RQ1 can claim to evaluate behavioral contract recovery. Level-2 evaluation should be labeled "parser completeness evaluation" and Level-3 evaluation labeled "behavioral contract recovery evaluation." The F1 ≥ 0.80 threshold applies to the Level-3 evaluation, not Level-2.

**Pre-experiment fix needed?** YES — human annotation must be collected before RQ1 results are meaningful.

---

### R4 — The "≥15pp FPR reduction" in RQ3 is also unjustified

**Criticism:** `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §2 RQ3` states H3 as "reduce false-positive rate by ≥15pp." `paper.md §4 RQ3` states H3 as "reduces the false-positive rate by at least 10 percentage points." These are contradictory: the final report says 15pp, the paper says 10pp. Neither document justifies *why* this threshold is appropriate.

**Severity:** MAJOR

**Evidence:** `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §2`: "reduce false-positive rate by ≥15pp compared to static-only BCG at ≥50% execution coverage." `paper.md §4 RQ3`: "reduces the false-positive rate by at least 10 percentage points." These are different thresholds in the same research design.

**Proposed response:** Reconcile the threshold to a single value across all documents. Derive the threshold from a domain argument or power calculation. Document the derivation in `docs/methodology.md` before freezing the experimental design.

**Pre-experiment fix needed?** YES — must be consistent before experiments run.

---

## Dimension 5: Technical Claims (T1–T3)

### T1 — The reconciliation engine has 3 predicate implementations; CONTROL_FLOW validation is weak

**Criticism:** The CONTROL_FLOW reconciliation logic (§8.2) requires `return_code ≠ None` in subject events. In `rq3/config.yaml`, the trace source is `EXECUTION_SIMULATED` — a JCL simulator, not a COBOL executor. JCL simulators may not produce accurate return codes, meaning CONTROL_FLOW contracts will be systematically `NOT_OBSERVED` (not captured → return_code = None). This would mean RQ3's benefit from dynamic evidence is artificially low for CONTROL_FLOW contracts.

**Severity:** MAJOR

**Evidence:** `bcg_formalization_v2.md §5 CONTROL_FLOW`: "NOT_OBSERVED for CONTROL_FLOW: Error condition never triggered in observed traces." `paper.md §8.2`: "Identify return events with `return_code ≠ None` in E_subject." `rq3/config.yaml`: `trace_source_type: EXECUTION_SIMULATED`. Return codes from JCL simulation are not guaranteed to match real execution.

**Proposed response:** Characterize explicitly which fraction of CONTROL_FLOW contracts will be `NOT_OBSERVED` under GnuCOBOL+JCL simulation conditions. If this fraction is high (>50%), report CONTROL_FLOW results separately with a caveat that dynamic evidence provides limited signal for this contract type under available execution conditions. Consider whether a "happy path" test suite that specifically exercises error conditions is needed.

**Pre-experiment fix needed?** YES — test suite design must account for error-path coverage.

---

### T2 — The ConfidenceVector aggregate is not validated against any calibration data

**Criticism:** `bcg_formalization_v2.md §4` explicitly states "aggregate(cv, w) is a normalized evidence-strength score, NOT a probability. Calibration study required before probabilistic interpretation is possible." Yet the RQ2 evaluation uses the confidence threshold to determine `semantic_regression_candidates` (only validated, high-confidence contracts flagged as regressions). If confidence is not calibrated, the threshold choice is arbitrary and results will vary with threshold.

**Severity:** MAJOR

**Evidence:** `bcg_formalization_v2.md §6`: "semantic_regression_candidates = {c ∈ broken | c.is_validated()}" and "potential_regressions = {c ∈ broken | Γ(c).confidence.aggregate() ≥ confidence_threshold}." The `confidence_threshold` value is not specified in any configuration file. `limitations.md L4` acknowledges this limitation but the experimental design does not explain how results are sensitive to threshold choice.

**Proposed response:** Add a threshold sensitivity analysis to the ablation study. Report RQ2 results at three confidence thresholds (low, medium, high) and show which threshold was selected and why. Label the selected threshold as a hyperparameter tuned on the validation set.

**Pre-experiment fix needed?** YES — threshold must be locked before experiments run.

---

### T3 — Impact radius computation is not evaluated

**Criticism:** The `compute_impact_radius()` function in `risk/detector.py` computes transitive entity-sharing impact analysis. This is listed as a Phase 3 addition and as a contribution in the implementation status. However, there is no RQ, no experimental evaluation, and no baseline comparison for impact radius. It appears as an unvalidated feature.

**Severity:** MINOR

**Evidence:** `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §5 Phase 3 additions`: "compute_impact_radius(), ImpactRadius dataclass — Transitive entity-sharing impact analysis." No corresponding experiment in `experiments/`. No RQ addresses impact radius accuracy or utility.

**Proposed response:** Either (a) add impact radius to the ablation study as a component that can be enabled/disabled, and measure whether it changes risk detection precision; or (b) explicitly scope it as "future work" and remove it from the contributions list in the paper.

**Pre-experiment fix needed?** NO — scoping decision only.

---

## Dimension 6: GnuCOBOL Limitation (G1–G2)

### G1 — The "execution-grounded" framing does not survive the GnuCOBOL limitation

**Criticism:** The paper's title and first contribution claim ("execution-grounded BCG") assert that dynamic execution is a defining feature of the work. The execution environment is GnuCOBOL on Linux, which `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §10` estimates provides ~75% behavioral equivalence for CONTROL_FLOW contracts and less for VSAM-dependent operations. For 25% of control-flow behaviors, the execution evidence may be incorrect — meaning the reconciliation engine may produce `STATIC_DYNAMIC_SUPPORTED` for contracts that would actually be violated on z/OS.

**Severity:** MAJOR

**Evidence:** `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §10`: CONTROL_FLOW equivalence ~75%, RESOURCE (sequential files) ~80%. `reviewer_attack_v2.md A3` rates this as the most technically concrete objection and notes it "cannot be waved away." `paper.md §16.4` mentions this as a threat but does not quantify the 25% gap or its effect on results.

**Proposed response:** Add a formal "GnuCOBOL/z/OS Behavioral Equivalence" table to §10.1 or §7.2, specifying which contract types are reliably observable in GnuCOBOL vs. which require z/OS. Explicitly exclude z/OS-specific contracts from the evaluation and report the fraction of total contracts that are excluded. This makes the limitation concrete and shows the authors understand its scope.

**Pre-experiment fix needed?** YES — the exclusion criteria must be defined before experiments run to avoid post-hoc filtering.

---

### G2 — The paper does not disclose GnuCOBOL limitations prominently enough

**Criticism:** `limitations.md L2` correctly identifies the GnuCOBOL limitation. However, in `paper.md`, this limitation appears only in §17 (Limitations) and §16.4 (Threats to Validity — Dynamic Validity). The Abstract, Introduction, and §7.2 (Dynamic Evidence Architecture) do not mention that all execution evidence comes from a non-mainframe environment. A reviewer who skims the paper will believe the system was evaluated on real mainframe execution.

**Severity:** MAJOR

**Evidence:** `paper.md §10.1` says "Execution traces collected via GnuCOBOL instrumentation on Linux" — this is in the correct place. But `paper.md §1 Introduction` says "execution-grounded" three times without mentioning GnuCOBOL. The abstract (when written) will need to include this disclosure.

**Proposed response:** Add a one-sentence disclosure to the Introduction: "All dynamic evidence in this paper is collected from GnuCOBOL execution on Linux — not from IBM z/OS — and is labeled accordingly throughout." This is not a weakness; it is intellectual honesty that strengthens the paper.

**Pre-experiment fix needed?** YES — paper text fix; should be in introduction before any results are claimed.

---

## Dimension 7: Ground Truth Circularity (GT1–GT2)

### GT1 — Level-2 DETERMINISTIC ground truth is produced by the same parser that extracts contracts

**Criticism:** This is the most severe scientific integrity risk in the entire design. Level-2 ground truth is described as "mechanically verifiable structural facts" from the JCL grammar. The JCL parser that produces Level-2 ground truth is the same parser used in the BCG extraction pipeline. This means: if the extractor finds contract C from JCL grammar rule R, and the ground truth benchmark says contract C is a valid contract because rule R implies it, then precision on Level-2 is trivially 1.0 by construction. The evaluation is circular for all Level-2 items.

**Severity:** CRITICAL

**Evidence:** `rq1/config.yaml`: `ground_truth: benchmark/ground_truth/level2_deterministic.json` and description "Level-2 DETERMINISTIC (mechanically verifiable structural facts)." `threats_to_validity.md §1.1` acknowledges parser errors but does not address the circularity. `reviewer_attack_v2.md A5` identifies this as "CRITICAL (This would invalidate RQ1 entirely)" — but the proposed mitigation (benchmark construction before BCG development, version control evidence) has not been implemented or documented yet.

**Proposed response:** Level-2 ground truth must be constructed by an independent parser or by manual inspection of the JCL grammar specification, not by running the BCG extraction pipeline. At minimum: have a second researcher independently verify each Level-2 ground truth item by reading the JCL source without using the tool. Document this process in the paper. Alternatively, re-define Level-2 as "independently verifiable" and use an external JCL reference parser as the verification oracle.

**Pre-experiment fix needed?** YES — blocking. If Level-2 ground truth is circular, RQ1 F1 numbers are meaningless.

---

### GT2 — There is currently no Level-3 (human-annotated) ground truth

**Criticism:** The most scientifically interesting contracts are the *implicit* cross-artifact behavioral obligations that require human interpretation (e.g., "CBTRN02C must not run until CBACT04C has written the transaction master file — this is not stated anywhere in the JCL but is implied by the data flow"). Level-3 ground truth for these implicit contracts is the only evaluation that tests real recovery capability. The paper has a protocol for collecting Level-3 (annotation_protocol.md, IAA measurement) but the annotations do not yet exist.

**Severity:** CRITICAL

**Evidence:** `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §14`: "Ground-truth annotation of a representative benchmark sample — required for all RQs" is listed under "Must complete." No Level-3 ground truth JSON file is present. `limitations.md L6` acknowledges "Level-3 ground truth for implicit contracts depends on annotator interpretation."

**Proposed response:** Collect Level-3 annotations for at least 50–100 contracts (representing all three types) before running experiments. Measure Cohen's κ between two annotators. Report Level-3 results as the primary evaluation in RQ1 (parser completeness is secondary). This is non-trivially expensive in human time but is mandatory for the paper to claim "behavioral contract recovery" rather than "parser completeness."

**Pre-experiment fix needed?** YES — blocking for meaningful RQ1 results.

---

## Dimension 8: Sample Size (S1–S2)

### S1 — CardDemo has ~15 JCL files; the number of extractable temporal contracts is very small

**Criticism:** With ~15 JCL files, the maximum number of inter-job temporal contracts is bounded by O(J²) where J = number of distinct jobs. If CardDemo has ~10 distinct JCL jobs with inter-job dependencies, the total number of temporal contracts extractable from JCL step ordering is likely 20–50. The Level-2 DETERMINISTIC ground truth for TEMPORAL contracts may consist of as few as 20–50 items. Reporting F1 on 20 binary classification items is not statistically meaningful.

**Severity:** CRITICAL

**Evidence:** `paper.md §10.1`: "approximately 30 COBOL programs, 15 JCL files, 20 copybooks." No document characterizes the number of contracts actually extractable from CardDemo. `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §14`: "CardDemo dataset preparation + split documentation — required for RQ1/RQ2/RQ3" is listed as not yet complete.

**Proposed response:** Characterize the number of contracts per type in CardDemo *before* committing to the experimental design. If the total number of temporal contracts is <50, the evaluation of TEMPORAL contract recovery is underpowered. Consider whether augmenting CardDemo with synthetic JCL files (generated from the same grammar with known temporal contracts) would increase statistical power without compromising validity.

**Pre-experiment fix needed?** YES — characterization must be done before the experimental design is finalized.

---

### S2 — The generalization set has 0 JCL files; TEMPORAL contract generalization cannot be evaluated

**Criticism:** `reviewer_attack_v2.md A9` identifies this as MEDIUM severity: "The generalization claim is limited to RESOURCE and CONTROL_FLOW only, covering 2/3 of the claimed contribution." The most distinctive contribution of the work (cross-artifact JCL+COBOL temporal contracts) cannot be evaluated on any held-out system. Any generalization claim for temporal contracts is unsupported.

**Severity:** MAJOR

**Evidence:** `paper.md §10.1`: "Held-out dataset: Public COBOL repositories from the Open Mainframe Project (OMP) GitHub. Approximately 50 COBOL programs, 0 JCL files." `reviewer_attack_v2.md A9`: "The held-out generalization uses public COBOL repos that have no JCL." `FINAL_RESEARCH_DEVELOPMENT_REPORT.md §7 open issues`: "Generalization limited for TEMPORAL (no JCL in public COBOL repos) — High."

**Proposed response:** Search for JCL-bearing public repositories before finalizing the generalization split. The OpenMainframe Project `zorow` repository, IBM public code samples, and mainframe-related GitHub repositories may contain JCL. Even 2–3 JCL-bearing programs would allow a limited temporal contract generalization experiment. If no JCL is found, the paper must explicitly state that temporal contract generalization is unevaluated and this is a limitation.

**Pre-experiment fix needed?** YES — dataset search should be done before experiments begin.

---

## Dimension 9: Reproducibility (RP1)

### RP1 — GnuCOBOL installation is non-trivial and z/OS-specific behaviors are not reproducible

**Criticism:** The reproducibility claim ("clone the repository, run `make reproduce-paper1`") depends on GnuCOBOL 3.1.2 being installable in the Docker container. GnuCOBOL compilation on modern Linux requires specific build dependencies that may not be stable across Docker base image versions. More critically, any results that depend on JCL simulation (which is not GnuCOBOL) depend on a JCL simulator whose behavior, accuracy, and availability are not documented in any config or README.

**Severity:** MINOR

**Evidence:** `paper.md §18`: "GnuCOBOL 3.1.2; Docker 24.x." `dynamic_analysis/gnucobol_adapter.py` (listed as complete) parses "GnuCOBOL + JCL simulation logs" — but the JCL simulator is never identified by name or version in any document reviewed.

**Proposed response:** Document the JCL simulation tool used: its name, version, source, and behavioral fidelity relative to IBM JES. If an in-house JCL simulator was built, it must be released with the research artifact. If a third-party tool is used, its license and availability must be documented.

**Pre-experiment fix needed?** YES — the JCL simulator identity must be documented before experiments run to ensure reproducibility.

---

## Dimension 10: Framing (F1–F2)

### F1 — Abstract and title make "execution-grounded" a central claim without qualification

**Criticism:** The paper title "Execution-Grounded Behavioral Contract Recovery" puts execution evidence at the center. But (a) execution evidence is `EXECUTION_SIMULATED` for JCL, (b) the execution is GnuCOBOL not z/OS, and (c) execution evidence is the *input* to an experiment testing whether it helps (RQ3) — it is not a proven feature. Framing execution grounding as the paper's identity before the experiment has confirmed it helps is premature.

**Severity:** MINOR

**Evidence:** `paper.md §1 title`. The paper's central contribution list (§1) places "Dynamic Evidence Adapter" as contribution #3 but RQ3 is explicitly testing whether this contributes value. The framing assumes the answer before the experiment.

**Proposed response:** The title is acceptable if the paper is honest about the scope. Add "with GnuCOBOL-Based Dynamic Evidence" to the subtitle or abstract to be specific about the execution environment.

**Pre-experiment fix needed?** NO — can be revised after experiments.

---

### F2 — The 8 required literature additions (W29–W36) are absent from the paper

**Criticism:** `novelty_analysis_v2.md Part 4` lists 8 works that "must be added before paper submission" (Lo 2006, Ammons 2002, GIST/Lorenzoli 2008, Angluin 1987, Leucker 2009, Mariani 2012, Lahiri 2012, Felsing 2014). Not one of these works is cited in `paper.md`. The paper's Related Work (§5) therefore fails to engage with the specification mining tradition and the closest competitor (GIST), which constitutes a clear gap that any informed reviewer would identify.

**Severity:** MAJOR

**Evidence:** `paper.md §5` references list: W1–W28 only. `novelty_analysis_v2.md Part 4` explicitly states "These 8 works must be added before paper submission." The references section of `paper.md` shows W1–W28 and does not include W29–W36.

**Proposed response:** Immediately add W29–W36 to `paper.md §5` and the references list. GIST (W31) requires a dedicated paragraph in §5.1 with the five-axis differentiation. This is a text change that can and should be made before experiments begin.

**Pre-experiment fix needed?** YES — paper text fix; will affect how RQs are framed relative to prior work.

---

## Summary Table

| ID | Dimension | Criticism Summary | Severity | Pre-experiment fix? |
|----|-----------|-------------------|----------|---------------------|
| N1 | Novelty | Daikon comparison table missing from paper | MAJOR | YES |
| N2 | Novelty | W29–W36 spec-mining works not cited in paper | MAJOR | YES |
| N3 | Novelty | Cross-artifact semantic challenge not articulated | MINOR | YES |
| N4 | Novelty | Confidence weights unjustified; paper still shows 1.10-sum | MAJOR | YES |
| N5 | Novelty | Provenance tracking not novel enough as standalone claim | MINOR | NO |
| E1 | Evaluation | Single application (~30 programs) for entire evaluation | CRITICAL | YES |
| E2 | Evaluation | 150 mutations insufficient for stated statistical tests | CRITICAL | YES |
| E3 | Evaluation | "Execution-grounded" uses EXECUTION_SIMULATED traces | MAJOR | YES |
| E4 | Evaluation | Oracle problem: mutations designed by detector's builders | MAJOR | YES |
| E5 | Evaluation | CardDemo is a showcase app, not representative of real enterprise | MAJOR | NO |
| B1 | Baselines | Baselines B, D, E not implemented; RQ2/RQ3 blocked | CRITICAL | YES |
| B2 | Baselines | Baseline E trivially equals proposed method on RQ1 Level-2 | MAJOR | YES |
| B3 | Baselines | LLM baseline has information asymmetry vs. BCG | MINOR | NO |
| R1 | RQ ops | ≥10pp F1 threshold unjustified; contradicts paper.md | MAJOR | YES |
| R2 | RQ ops | RQ3 conflates two distinct scientific questions | MINOR | YES |
| R3 | RQ ops | RQ1 measures parser completeness, not contract recovery | MAJOR | YES |
| R4 | RQ ops | ≥15pp vs. ≥10pp FPR threshold inconsistency | MAJOR | YES |
| T1 | Technical | CONTROL_FLOW reconciliation weak under EXECUTION_SIMULATED | MAJOR | YES |
| T2 | Technical | Confidence threshold not locked; sensitivity analysis absent | MAJOR | YES |
| T3 | Technical | Impact radius not evaluated by any RQ | MINOR | NO |
| G1 | GnuCOBOL | 25% CONTROL_FLOW equivalence gap not quantified in evaluation | MAJOR | YES |
| G2 | GnuCOBOL | GnuCOBOL limitation not disclosed in Introduction | MAJOR | YES |
| GT1 | Ground truth | Level-2 ground truth is circular (same parser) | CRITICAL | YES |
| GT2 | Ground truth | No Level-3 (human-annotated) ground truth exists | CRITICAL | YES |
| S1 | Sample size | ~15 JCL files → <50 temporal contracts → underpowered | CRITICAL | YES |
| S2 | Sample size | 0 JCL in generalization set; temporal contracts unevaluated | MAJOR | YES |
| RP1 | Repro | JCL simulator unidentified; GnuCOBOL build chain undocumented | MINOR | YES |
| F1 | Framing | Title assumes execution grounding is proven, not hypothesis | MINOR | NO |
| F2 | Framing | 8 required literature works absent from paper | MAJOR | YES |

---

## CRITICAL Issues That Would Cause Rejection If Not Addressed

### CRITICAL-1: E1 — Single Application Dataset
A manuscript claiming to improve modernization risk detection, evaluated entirely on one ~30-program demonstration application with no JCL in the generalization set, will be desk-rejected or borderline-rejected at FSE/ICSE. **Minimum bar:** find at least 2 additional JCL-bearing public systems. If unavailable, scope all claims to "proof-of-concept on CardDemo" and target a workshop or tool track.

### CRITICAL-2: E2 — Insufficient Mutation Benchmark Size
150 binary outcomes with Bonferroni-corrected α = 0.01 is statistically underpowered for the claimed effect sizes. If the actual F1 difference is 8–12pp (a plausible range), the result will be non-significant. **Before experiments:** conduct a power analysis and set N accordingly (likely 300–500+ mutations needed).

### CRITICAL-3: B1 — Three Baselines Not Implemented
RQ2 and RQ3 cannot be run without Baselines B, D, and E. Running experiments with missing baselines and then saying "we could not complete RQ2" is a fatal flaw. **Must be implemented before any experiment runs.**

### CRITICAL-4: GT1 — Level-2 Ground Truth Circularity
If Level-2 ground truth is produced by running the same parser that populates the BCG, RQ1 F1 = 1.0 by construction. This makes RQ1 meaningless and, if not disclosed, scientifically fraudulent. **Must be addressed by independent verification of ground truth items before experiments begin.**

### CRITICAL-5: GT2 — No Level-3 (Human-Annotated) Ground Truth
The paper's core claim is recovery of *implicit* behavioral contracts — contracts that are not mechanically derivable from the grammar. Without human-annotated ground truth for implicit contracts, the paper cannot evaluate its primary contribution. The Level-3 annotation process is the single most important pre-experiment task.

### CRITICAL-6: S1 — Estimated <50 Temporal Contracts from ~15 JCL Files
If the total Level-2 temporal contract count from CardDemo is <50, F1 confidence intervals will be so wide as to be uninformative. **Characterize the contract population size before committing to the experimental design.**

---

## Things the Paper Does WELL (What Would Survive Reviewer Scrutiny)

### STRENGTH-1: Scientific Integrity Infrastructure Is Genuinely Impressive
The combination of 234 passing tests including 48 scientific integrity tests, benchmark lock mechanisms, confidence weight lock, `NOT_OBSERVED ≠ CONTRADICTED` enforcement in code, and the `SYNTHETIC_STATIC` contamination guard is more rigorous than the vast majority of software engineering empirical papers. A reviewer who reads the test suite and sees `SI-06: NOT_OBSERVED ≠ CONTRADICTED` enforced across all contract types will recognize unusual care. This infrastructure also means that when experiments do run, the results will be trustworthy.

### STRENGTH-2: Failure Taxonomy Is Empirically Grounded and Well-Documented
`failure_taxonomy.md` provides F1–F7 with named empirical sources for each category (AWS MM docs, IBM migration guides, specific GitHub issues, published postmortems). Each mutation operator can be challenged for realism, and the paper has a concrete, cited answer. This is a significant advantage over papers that invent mutations based on intuition. The citation of `aws-mainframe-modernization-carddemo Issue #12` as evidence for F1 is exactly the kind of specific, verifiable grounding reviewers respect.

### STRENGTH-3: Honest Pre-Registration of All Hypotheses With Falsification Conditions
`paper.md §4` states all three hypotheses with explicit null hypotheses and falsification conditions, and `methodology.md` states "A negative result (BCG not better) is a valid finding and must be reported without modification." The explicit statement "If H3 is not confirmed, that is also a finding worth reporting" in `reviewer_attack_v2.md` demonstrates research honesty that very few SE papers articulate. Pre-registering hypotheses with falsification conditions is a strong answer to p-hacking concerns.

---

## Final Count

| Severity | Count |
|----------|-------|
| CRITICAL | 6 (E1, E2, B1, GT1, GT2, S1) |
| MAJOR | 17 (N1, N2, N4, E3, E4, E5, B2, R1, R3, R4, T1, T2, G1, G2, S2, F2, and one additional on RQ3 threshold inconsistency R4) |
| MINOR | 7 (N3, N5, B3, R2, T3, RP1, F1) |
| **Total** | **30** |

**CRITICAL issues (must fix before experiments run):**
1. **E1** — Expand beyond single CardDemo application or restrict all claims to proof-of-concept scope
2. **E2** — Conduct power analysis; increase N before freezing experimental design
3. **B1** — Implement Baselines B, D, E before running RQ2 or RQ3
4. **GT1** — Reconstruct Level-2 ground truth using an independent parser or manual verification
5. **GT2** — Collect Level-3 human-annotated ground truth for implicit contracts
6. **S1** — Characterize the contract population size in CardDemo; if <50 temporal contracts, expand dataset or revise the experimental design

**3 strongest "accept as is" points:**
1. Scientific integrity infrastructure (test suite SI-01 through SI-12, lock mechanisms) is publication-ready and demonstrates research rigor beyond the norm for SE empirical papers.
2. Failure taxonomy (F1–F3) is empirically grounded with named, verifiable sources — a rare quality in mutation-based evaluation.
3. All hypotheses are pre-registered with explicit falsification conditions and negative results are explicitly accepted as valid findings.

**Confirmation:** `docs/final_hostile_review.md` has been written.
