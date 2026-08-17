# Hostile Reviewer Attack v2
## LEGACY-CONTRACT — 15 ICSE/FSE/ASE Rejection Arguments with Mitigations

**Version:** 0.2.0  
**Auditor:** Hostile reviewer subagent (subagent 7) + lead researcher synthesis  
**Standard:** ICSE/FSE/ASE strong-accept bar

---

## PREAMBLE

This document is for internal use. Every argument listed here must be prepared for in the paper's related work, threats to validity, and limitations sections. Arguments marked HIGH severity must have explicit rebuttals in the paper draft.

---

## ATTACK 1 — NOVELTY: "This is just Daikon for COBOL"

**Rejection argument:**  
Daikon (Ernst et al. 2007) already infers behavioral properties from execution traces with confidence scores. Applying this to COBOL programs is incremental domain transfer, not a research contribution. The main "novelty" — adding JCL — is a straightforward extension.

**Severity: HIGH**

**Is this valid?** Partially. The surface similarity is real. The structural differences are also real but must be argued explicitly.

**Evidence from documents:**  
Novelty analysis.md correctly distinguishes BCG from Daikon (data invariants vs. temporal/resource/control-flow obligations; OO programs vs. cross-artifact legacy batch). But this argument is not yet made with sufficient force in the paper draft.

**Mitigation:**

1. Add a side-by-side comparison table in Related Work:

| Dimension | Daikon | BCG |
|---|---|---|
| Evidence type | Program execution traces | JCL execution + COBOL execution |
| Property type | Data invariants (x > 0, y = f(x)) | Temporal ordering (A ≺ B), resource availability (produces before consumes), error propagation |
| Artifact type | Single OO program | Cross-artifact (JCL + COBOL + copybook) |
| Execution model | Method invocations | Batch job steps, file I/O, return codes |
| Use case | Bug detection in OO code | Modernization risk detection for legacy batch |
| Provenance model | Statistical confidence | 8-state validation, multi-dimensional evidence, per-contract audit trail |

2. Show a concrete example where Daikon would fail: Daikon cannot express "JCL step CBACT01C must complete and successfully produce ACCTFILE before CBACT02C reads it" because this is not a data invariant — it is a temporal ordering obligation between heterogeneous artifacts.

---

## ATTACK 2 — NOVELTY: "Combination of known techniques"

**Rejection argument:**  
Static analysis of COBOL exists. Dynamic trace analysis exists. Graph representations exist. Provenance tracking exists. The paper combines existing components without any novel underlying mechanism.

**Severity: HIGH**

**Is this valid?** The critique is real. The response must not be defensive.

**Mitigation:**

The counter-argument has two parts:

1. **The combination produces a non-obvious emergent capability:** The static/dynamic reconciliation with explicit conflict taxonomy (SUPPORTED/CONTRADICTED/NOT_OBSERVED/ENVIRONMENT_DEPENDENT) for cross-artifact behavioral contracts does not exist as a combination in prior work. Naik et al. reconcile for race detection but have no conflict taxonomy. GIST mines behavioral models but has no static/dynamic reconciliation.

2. **The empirical question is independent of the novelty question:** Whether dynamic evidence actually reduces false positives in this domain is an empirical hypothesis (RQ3). If H3 is confirmed, the combination produces a demonstrably better outcome. If H3 is not confirmed, that is also a finding worth reporting. The combination's value is determined empirically, not asserted.

---

## ATTACK 3 — DYNAMIC VALIDITY: "GnuCOBOL ≠ z/OS"

**Rejection argument:**  
The paper claims to study "mainframe batch systems" but uses GnuCOBOL on Linux for all dynamic evidence. GnuCOBOL is not IBM Enterprise COBOL. Results cannot be extrapolated to z/OS.

**Severity: HIGH** (Most technically concrete objection; cannot be waved away)

**Is this valid?** VALID for some behaviors. PARTIALLY VALID for Paper 1's specific contract types.

**Mitigation:**

1. Formally characterize GnuCOBOL/z/OS equivalence per contract type (docs/dynamic_evidence_v2.md, Part 2). For Paper 1's contracts (temporal ordering, sequential file I/O, COND parameters on RC 0-4), GnuCOBOL provides representative behavioral evidence.

2. Explicitly exclude non-equivalent scenarios: VSAM-dependent contracts, ABEND-based error handling, RC > 4. Mark these `ENVIRONMENT_DEPENDENT` in the BCG.

3. Label all dynamic evidence as "GnuCOBOL instrumented execution (not z/OS)" throughout the paper.

4. Frame this honestly: "We use GnuCOBOL as the best available open-source proxy for mainframe execution. For the contract types in Paper 1's scope (temporal ordering, sequential file I/O), GnuCOBOL provides representative behavioral evidence. z/OS-specific features are explicitly excluded."

**What this objection cannot say:** It cannot say that no dynamic evidence is better than GnuCOBOL evidence for Paper 1's contract types. The temporal ordering of batch job steps is the same in both environments. This is the key rebuttal.

---

## ATTACK 4 — DATASET: "CardDemo is a sample application"

**Rejection argument:**  
AWS CardDemo is a demonstration system with ~30 COBOL programs, ~15 JCL files, and ~15K LOC. Real enterprise mainframe systems have hundreds of COBOL programs, thousands of JCL jobs, and millions of LOC. Results on CardDemo have zero ecological validity.

**Severity: HIGH**

**Is this valid?** Valid as an external validity concern. Cannot be fully mitigated without enterprise data (which is unavailable).

**Mitigation:**

1. **Clearly scope all claims:** "Results apply to batch COBOL+JCL systems comparable in structure to AWS CardDemo (~30 programs, ~15 JCL files, inter-job file dependencies)."

2. **Run generalization experiment:** Show the system works on held-out public COBOL programs. Even if these are smaller, cross-system validation strengthens the argument.

3. **Characterize CardDemo precisely:** LOC, number of programs, JCL complexity, number of cross-artifact contracts, number of inter-job dependencies. This is Table 2 in the paper.

4. **Argue why scale does not invalidate findings:** The extraction mechanisms (parsing JCL/COBOL, building IR, extracting contracts) scale linearly. The contract types (temporal, resource, control-flow) are present in real enterprise systems. The finding that "dynamic evidence reduces false positives" would be expected to hold at scale (more evidence = better validation).

5. **Do not overclaim:** Never say "our approach scales to enterprise systems." Say "our approach was evaluated on CardDemo-scale systems; enterprise-scale evaluation is future work."

---

## ATTACK 5 — GROUND TRUTH: "Ground truth is circular"

**Rejection argument:**  
The benchmark (level2_deterministic.json) may have been constructed knowing the system's extraction capabilities. If the annotators built the benchmark after observing what the system extracts, precision/recall measurements are circular.

**Severity: CRITICAL** (This would invalidate RQ1 entirely)

**Is this valid?** POTENTIALLY VALID if the protocol is not followed. Documents do not currently prove the protocol was followed (no dates, no version control evidence).

**Mitigation:**

1. **Follow the benchmark construction protocol exactly** (docs/experimental_design_v2.md, Part 3): benchmark constructed independently by annotators who have not seen the BCG system; benchmark locked before BCG development begins.

2. **Provide version control evidence:** The git commit date of `level2_deterministic.json` must predate the git commit date of the BCG extraction code. This is verifiable by reviewers.

3. **Use multiple annotators with κ:** Report inter-annotator agreement per contract type. κ ≥ 0.70 indicates agreement is not driven by system knowledge.

4. **Separate DETERMINISTIC from HUMAN_ANNOTATED evaluation:** DETERMINISTIC items (syntactic facts from parser) are verifiable by any independent parser. Their correctness does not depend on annotator judgment.

---

## ATTACK 6 — MUTATION BIAS: "Mutations are designed to favor BCG"

**Rejection argument:**  
The mutation categories (F1: job ordering, F2: file availability, F3: return code) exactly match the three contract types in BCG scope (TEMPORAL, RESOURCE, CONTROL_FLOW). BCG will trivially detect its own contract types being violated. The evaluation is circular.

**Severity: HIGH**

**Is this valid?** The concern is legitimate. The categories DO match. The response requires demonstrating this was NOT designed post-hoc.

**Mitigation:**

1. **Provide temporal evidence of independence:** The failure taxonomy (docs/failure_taxonomy.md) documents that F1-F3 were derived from empirical evidence (AWS MM docs, CardDemo issues, IBM migration guides). The git commit date of failure_taxonomy.md should predate BCG extraction design.

2. **Show baselines also detect some mutations:** If structural baseline (Baseline A) detects F1 mutations with similar performance, then mutation F1 is not "designed for BCG" — it is detectable by structural analysis too. BCG's advantage should be on subtler mutations.

3. **Evaluate per-mutation-category:** Separately report which categories BCG detects better than baselines. If BCG only beats baselines on the mutation types that trivially violate its contracts, that is a weaker finding than beating all categories.

4. **Note:** This objection motivates adding F4-F7 mutations (record format, state initialization) to demonstrate BCG also helps on types where it has no a priori advantage. However, F4-F7 are Paper 2 scope — this is an acknowledged limitation.

---

## ATTACK 7 — BASELINES: "Baselines use less information than BCG"

**Rejection argument:**  
BCG+dynamic has access to execution traces. Baselines A (structural), B (complexity), and C (LLM-only) do not have execution traces. The comparison is unfair — BCG wins because it has more evidence, not because its representation is better.

**Severity: HIGH**

**Is this valid?** Valid concern for Baselines A, B, C. NOT valid for Baseline E (static BCG uses same artifacts, no traces) and Baseline D (dep+LLM has same structural information).

**Mitigation:**

1. **RQ3 directly addresses this:** Baseline E (static BCG) uses the same representation without dynamic evidence. If BCG+dynamic beats Baseline E, the advantage comes from dynamic evidence — and the research question is whether that evidence helps. RQ3 is specifically designed to isolate this.

2. **Baselines A, B, C represent genuine alternatives:** A structural dependency analyzer, a complexity metric tool, and an LLM-based analyzer are the actual alternatives that modernization engineers use today. They do not use execution traces. BCG's advantage over them includes both the formal representation AND the execution evidence — which is the right comparison for practical adoption.

3. **Add Baseline D (dep+LLM) as the strongest alternative:** Baseline D has the same structural information AND LLM enrichment. BCG must beat Baseline D to claim formal representation adds value beyond LLM augmentation.

---

## ATTACK 8 — STATISTICAL: "Results not yet collected"

**Rejection argument:**  
All experiments show [RESULT_PENDING]. A paper with no experimental results cannot be submitted to ICSE/FSE. This is a tool paper without evaluation.

**Severity: CRITICAL (for submission) — MEDIUM for current phase**

**Is this valid?** Completely valid for submission. The system is in development; experiments have not run.

**Mitigation:**

This is not a defect of the research design; it is the current stage of the project. Before submission:
1. All experiments must be completed: RQ1, RQ2, RQ3, ablation, generalization
2. All [RESULT_PENDING] replaced with actual values
3. All tables filled with actual data (not placeholder data)

The experimental design is ready. The implementation is functionally complete. Running the experiments is the remaining step.

---

## ATTACK 9 — GENERALIZATION: "Temporal contracts can't be tested held-out"

**Rejection argument:**  
The held-out generalization uses public COBOL repos that have no JCL. Therefore, the most interesting contract type — TEMPORAL ordering across jobs — cannot be evaluated on the generalization set. The generalization claim is limited to RESOURCE and CONTROL_FLOW only, covering 2/3 of the claimed contribution.

**Severity: MEDIUM**

**Is this valid?** VALID. This is a real gap.

**Mitigation:**

1. **Disclose explicitly in paper:** "Held-out generalization evaluates RESOURCE and CONTROL_FLOW contracts only, as public COBOL repositories lack accompanying JCL. Temporal contract generalization remains unevaluated on unseen systems."

2. **Find public JCL sources:** Search GitHub for JCL repositories accompanying COBOL programs (e.g., OpenMainframe Project zorow JCL samples). Even a few JCL jobs with COBOL programs would allow temporal contract generalization testing.

3. **Frame appropriately:** "We demonstrate cross-system generalization for RESOURCE and CONTROL_FLOW contracts. Temporal contract generalization is evaluated on CardDemo only. Both types generalize within the CardDemo development/held-out split."

---

## ATTACK 10 — LLM: "Is the system actually deterministic?"

**Rejection argument:**  
Baseline C and E7 use LLMs. If LLM enrichment is part of the proposed system's evidence, then results are not reproducible (LLM outputs change with model versions) and claims of formal rigor are undermined.

**Severity: MEDIUM**

**Is this valid?** PARTIALLY VALID for E7/Baseline C. NOT valid for the core BCG system.

**Mitigation:**

The system is designed to operate without LLM (docs/research_decisions.md, D-005). LLM is an optional enrichment layer tested as a separate ablation level (E7). The deterministic BCG (E0-E6) is fully reproducible. LLM-involving components (Baseline C, Baseline D, E7) are explicitly labeled and run with fixed temperature=0, 5 repetitions, and variance reporting.

---

## ATTACK 11 — TERMINOLOGY: "'Behavioral contract' conflates specification and inference"

**Rejection argument:**  
A "behavioral contract" (in the tradition of Meyer 1992, Liskov+Wing 1994) is a specification written by a developer. What BCG infers from static analysis is a hypothesis, not a contract. Calling an inferred pattern a "contract" conflates specification with observation.

**Severity: MEDIUM**

**Is this valid?** Technically valid. The terminology should be precise.

**Mitigation:**

1. Introduce explicit terminology: "**Behavioral contract hypothesis**" for STATIC_CANDIDATE status. "**Validated behavioral contract**" for HUMAN_VALIDATED, GROUND_TRUTH, or STATIC_DYNAMIC_SUPPORTED status.

2. Add clarifying paragraph in Section 6 (Behavioral Contract Model): "We use 'behavioral contract' to refer to an implicit obligation that must hold for the system to preserve intended behavior — in contrast to explicit specifications (Meyer 1992). Our contracts are hypotheses extracted from artifacts and evidence; they gain confidence through validation but are never certified as ground truth unless verified by execution oracle or domain expert."

3. The 8-state validation machine already enforces this distinction at the code level. Make it explicit in the paper's terminology.

---

## ATTACK 12 — OVERCLAIMING: "Formal model lacks formal proofs"

**Rejection argument:**  
The paper claims a "formal BCG" but provides no formal proofs: no soundness theorem, no completeness theorem, no decidability result. The word "formal" is being used decoratively.

**Severity: MEDIUM**

**Is this valid?** PARTIALLY VALID. The formalization is more rigorous than typical software engineering papers but less than formal methods papers.

**Mitigation:**

1. Provide one lightweight formal result: **Soundness lemma for temporal contract extraction:**
> Lemma 1 (Temporal Extraction Soundness): For any JCL file F containing steps S₁ declared before S₂ in the same JOB, the static extractor produces a TEMPORAL contract (S₁, PRECEDES, S₂). Proof: By construction from the JCL grammar (rule: EXEC statements in order).

2. Clearly scope the formalism: "We present a formal model in the software engineering tradition — typed entities, well-defined relations, specified semantics, formal invariants — rather than the formal verification tradition (no proofs of correctness against implementation). The formalism enables precise communication and supports the experimental evaluation."

3. Remove the word "formal" from claims about proofs. Use "structured," "specified," or "precisely defined" where appropriate.

---

## ATTACK 13 — ENGINEERING: "This is a tool paper, not a research paper"

**Rejection argument:**  
The contribution is a system that parses COBOL/JCL, builds a graph, and flags changes. This is software engineering work, not research. The research questions are empirical but could be answered without the BCG — just by running a test suite.

**Severity: MEDIUM**

**Is this valid?** PARTIALLY VALID. The system IS a research contribution; the question is whether it investigates a genuine hypothesis.

**Mitigation:**

The paper tests three non-obvious hypotheses:
1. (H1) Static analysis of JCL+COBOL can recover behavioral contracts with F1 ≥ 0.70 — this is not guaranteed; parsers fail, COND semantics are complex, cross-artifact contracts are hard to discover.
2. (H2) The formal BCG representation improves risk detection over structural analysis, LLM-only, and dependency+LLM — this is not obvious; LLMs may already subsume the BCG's contribution.
3. (H3) Dynamic evidence reduces false positives — this is a hypothesis, not a given; it is possible that static analysis is already precise enough and execution evidence adds noise.

The system is the instrument for testing these hypotheses. The research contribution is the findings, not the system.

---

## ATTACK 14 — MISSING COMPARISON: "No Daikon baseline"

**Rejection argument:**  
The paper claims BCG is better than existing behavioral analysis approaches but never directly compares against Daikon. Since the paper repeatedly distinguishes itself from Daikon, a direct comparison is expected.

**Severity: MEDIUM**

**Is this valid?** Valid experimental design criticism.

**Mitigation:**

Add a **Baseline F: Daikon-on-COBOL** experiment in the ablation/generalization section. Apply Daikon to GnuCOBOL-compiled CardDemo programs, observe which "likely invariants" are inferred, evaluate whether those invariants correspond to temporal/resource/control-flow contracts, measure precision and recall against level2_deterministic.json.

Expected result: Daikon will produce data invariants (x > 0, x < 999) but not temporal ordering contracts (A ≺ B). This directly demonstrates the distinction.

**Note:** This requires compiling CardDemo with GnuCOBOL and running Daikon. Feasible with public tools.

---

## ATTACK 15 — REPRODUCIBILITY: "LLM results not reproducible"

**Rejection argument:**  
LLM results are non-deterministic. Model versions change, backend sampling changes, and results from 2024 cannot be reproduced in 2026. Any finding involving LLM baselines lacks reproducibility.

**Severity: LOW for core findings; MEDIUM for LLM baselines**

**Is this valid?** Valid for LLM-involving components. NOT valid for core BCG (fully deterministic).

**Mitigation:**

1. Clearly separate deterministic and LLM components in all reported results.
2. Report LLM results as mean ± std over 5 runs.
3. Specify model version, temperature, prompt hash in all LLM-related result tables.
4. Archive prompts and model-version specifications.
5. Note in reproducibility section: "Core BCG results (E0-E6) are fully reproducible. LLM-involving results (Baseline C, D, E7) are reproducible given the same model version but may differ with newer model versions. Results are reported with variance across 5 runs."

---

## TOP 5 KILLER OBJECTIONS

Ranked by likelihood to cause rejection at a top venue:

### Killer 1: Circular ground truth (Attack 5)

**Why it kills:** If the benchmark was built knowing the system's capabilities, all precision/recall numbers are meaningless. This makes RQ1 unfalsifiable.

**Preparation required:** Version control evidence that benchmark predates BCG; inter-annotator agreement κ ≥ 0.70; explicit independence statement.

### Killer 2: GnuCOBOL ≠ z/OS (Attack 3)

**Why it kills:** The research claims to study "mainframe legacy systems" but has no mainframe evidence. The entire dynamic evidence contribution is based on a non-mainframe environment.

**Preparation required:** Formal equivalence characterization (docs/dynamic_evidence_v2.md Part 2); explicit scoping to sequential-file batch programs; clear labeling throughout.

### Killer 3: Mutation bias (Attack 6)

**Why it kills:** If F1/F2/F3 mutations were designed knowing BCG detects TEMPORAL/RESOURCE/CONTROL_FLOW contracts, the evaluation is tautological.

**Preparation required:** Version control evidence; empirical sources for all mutations; per-category baseline comparison showing some categories are detected by structural baselines too.

### Killer 4: CardDemo is a demo (Attack 4)

**Why it kills:** The main system has ~30 programs. Reviewers at FSE/ICSE expect at least 5-10 independent systems for evaluation.

**Preparation required:** Generalization experiment; precise characterization of CardDemo; explicit scoping of all claims; discuss what would be needed for enterprise-scale evaluation.

### Killer 5: Baseline D (dep+LLM) might be sufficient (Attack 7)

**Why it kills:** If LLM + structural dependencies already achieves BCG-level performance, the formal representation is unnecessary. This directly falsifies the paper's thesis.

**Preparation required:** This is RQ2 primary hypothesis H2b. If BCG does not beat Baseline D significantly, the paper must honestly report this as a negative finding. Do not adjust the system post-hoc to beat this baseline.

---

## STATUS TRACKING

| Attack | Severity | Addressed in Docs? | Addressed in Code? | Requires Paper Section? |
|---|---|---|---|---|
| A1 (Daikon) | HIGH | ✓ novelty_analysis_v2.md | — | Related Work |
| A2 (combination) | HIGH | ✓ novelty_analysis_v2.md | — | Related Work + Intro |
| A3 (GnuCOBOL) | HIGH | ✓ dynamic_evidence_v2.md | ✓ ENVIRONMENT_DEPENDENT state | Threats + Methods |
| A4 (CardDemo) | HIGH | ✓ dataset_selection.md | — | Threats + Limitations |
| A5 (circular) | CRITICAL | ✓ experimental_design_v2.md | ✓ Benchmark.lock() | Methods + Chain of custody |
| A6 (mutation bias) | HIGH | ✓ mutation_validity | — | Methods + Threats |
| A7 (baseline info) | HIGH | ✓ experimental_design_v2.md | — | Methods + Baselines |
| A8 (no results) | CRITICAL (submit) | — | ✓ [RESULT_PENDING] discipline | Results (pending) |
| A9 (generalization) | MEDIUM | ✓ experimental_design_v2.md | — | Generalization section |
| A10 (LLM) | MEDIUM | ✓ research_decisions.md | ✓ LLM optional | Methods + Reproducibility |
| A11 (terminology) | MEDIUM | ✓ bcg_formalization_v2.md | ✓ STATIC_CANDIDATE naming | Section 6 |
| A12 (formal proofs) | MEDIUM | ✓ bcg_formalization_v2.md | — | Section 6 |
| A13 (tool paper) | MEDIUM | ✓ methodology.md | — | Intro + RQ framing |
| A14 (no Daikon) | MEDIUM | New: add Baseline F | ✓ GnuCOBOL available | Related Work + Baselines |
| A15 (LLM repro) | MEDIUM | ✓ reproducibility.md | ✓ 5-run variance | Reproducibility |
