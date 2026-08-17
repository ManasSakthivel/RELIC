# Novelty Analysis v2
## LEGACY-CONTRACT — Audited and Revised Novelty Claims

**Version:** 0.2.0  
**Status:** Revised after 8-subagent hostile audit  
**Principle:** No claim uses "first" or "no prior work" without the qualifier "to our knowledge, in the reviewed literature"

---

## PART 1: SYNTHESIS OF AUDIT FINDINGS

The literature audit (subagent 1) identified 8 missing works and found that 2/7 original novelty claims required downgrading. The hostile reviewer subagent identified the "combination of known techniques" objection as the most damaging. This revision addresses both.

**Resolution of subagent conflict:**  
Subagent 1 ranked "fault-grounded mutations" as the third strongest claim. Subagent 7 (hostile reviewer) rated it as a CRITICAL vulnerability because the literature search for "mutation testing + mainframe/legacy" was never conducted. Resolution: **the mutation claim is conditionally retained but must be verified before submission via systematic search.** This document marks it accordingly.

---

## PART 2: PRIOR ART CAPABILITY MATRIX (UPDATED)

Added 8 works from literature audit. Rows added: Lo 2006, Ammons 2002, Lorenzoli 2008 (GIST), Lahiri 2012.

| Capability | Daikon | Klaedtke | Lo 2006 | GIST | Naik | Sneed | Pessoa | **BCG** |
|---|---|---|---|---|---|---|---|---|
| Behavioral contracts | ~ invariants | ✓ DFA | ~ specs | ~ FSM | ✗ | ✗ | ~ diff | **✓** |
| Temporal ordering obligations | ✗ | ✓ | ✓ | ~ | ✗ | ✗ | ✗ | **✓** |
| Resource dependency contracts | ✗ | ✗ | ✗ | ✗ | ✗ | ~ | ✗ | **✓** |
| Control-flow obligation contracts | ✗ | ~ | ~ | ~ | ✗ | ✗ | ~ | **✓** |
| Cross-artifact (multi-language) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| JCL+COBOL simultaneously | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Explicit static/dynamic reconciliation | ~ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | **✓** |
| Explicit conflict taxonomy | ✗ | ✗ | ✗ | ✗ | ~ | ✗ | ✗ | **✓** |
| Per-contract provenance | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Validation state machine | ✗ | ✗ | ✗ | ~ | ✗ | ✗ | ✗ | **✓** |
| Modernization-risk use case | ✗ | ✗ | ✗ | ✗ | ✗ | ~ | ✓ | **✓** |
| Empirically grounded fault model | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** [†] |
| Formal BCG intermediate representation | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |

[†] = Conditional on mutation testing literature search confirming no prior mainframe-specific work.

**Key finding from GIST audit:** GIST (Lorenzoli et al. 2008) infers FSM behavioral models from execution traces and has validation-related states, but:
1. It targets OO programs, not legacy batch
2. It does not have a multi-source cross-artifact representation  
3. It does not explicitly model provenance per constraint
4. It does not have a modernization-risk detection use case

GIST is a precursor, not a competitor to the primary novelty claim.

---

## PART 3: NOVELTY CLAIMS — REVISED AND RANKED

### CLAIM 1 (RANK 1 — STRONGEST): Cross-Artifact BCG for JCL+COBOL Batch Systems

**Revised statement:**
> "To our knowledge in the reviewed literature, no published work has produced a formal intermediate representation that jointly encodes temporal, resource, and control-flow behavioral obligations across heterogeneous legacy batch artifacts — specifically JCL job streams, COBOL programs, and copybook record definitions — with explicit per-contract provenance, validation states, and static/dynamic evidence reconciliation."

**Defensibility: 9/10**

**What makes it defensible:**
- Every prior tool is siloed: COBOL analyzers ignore JCL; JCL analyzers ignore COBOL behavioral semantics
- No prior IR combines {JCL + COBOL + temporal + resource + control-flow + provenance + reconciliation}
- The combination is non-trivial: JCL and COBOL have different execution models (batch scheduler vs. procedural program)

**Potential reviewer objection:** "This is just applying known techniques to a new domain."

**Rebuttal:** The domain itself imposes novel technical challenges. JCL step ordering is not equivalent to method invocation order. Dataset DISP semantics (NEW/OLD/SHR/MOD) have no counterpart in OO systems. The extraction mechanisms, the reconciliation semantics, and the validation state machine are all domain-specific and non-trivial adaptations.

**What NOT to claim:**
- Not "first behavioral contract system" — Meyer 1992, Daikon 2007 predate
- Not "first to analyze COBOL" — Sneed 2008, Pessoa 2022 predate
- Not "first JCL analysis" — IBM tools predate

---

### CLAIM 2 (RANK 2): Static/Dynamic Reconciliation with Explicit Conflict Taxonomy

**Revised statement:**
> "To our knowledge, no prior work applies a formal static/dynamic reconciliation procedure with an explicit conflict taxonomy — distinguishing SUPPORTED, CONTRADICTED, NOT_OBSERVED, PARTIALLY_SUPPORTED, AMBIGUOUS, INSUFFICIENT_EVIDENCE, and ENVIRONMENT_DEPENDENT outcomes — to behavioral contracts in legacy batch systems."

**Defensibility: 8/10**

**What makes it defensible:**
- Naik et al. (2006) reconciles for race detection but has no explicit conflict taxonomy and is not applied to behavioral contracts
- GIST (Lorenzoli 2008) infers FSM models but has no static/dynamic reconciliation mechanism
- The conflict taxonomy is specifically designed for legacy batch semantics (GnuCOBOL vs z/OS differences; ENVIRONMENT_DEPENDENT state)

**Potential reviewer objection:** "Static+dynamic analysis is well-known; the taxonomy is obvious."

**Rebuttal:** The taxonomy's specific states — particularly NOT_OBSERVED (which must never become CONTRADICTED), ENVIRONMENT_DEPENDENT (GnuCOBOL behavior not equivalent to z/OS), and INSUFFICIENT_EVIDENCE (granularity mismatch between events and contracts) — arise from domain-specific constraints that are not obvious from general static/dynamic analysis literature. The scientific contribution is demonstrating which distinctions are necessary and empirically investigating whether they reduce false positives (RQ3).

---

### CLAIM 3 (RANK 3): Execution-Grounded Contract Validation for Mainframe Batch

**Revised statement:**
> "To our knowledge, no prior work provides execution-grounded validation of behavioral contracts extracted from mainframe batch systems using instrumented open-source execution (GnuCOBOL), with explicit labeling of evidence quality (real execution vs. simulated vs. synthetic) and environment validity (portable vs. representative vs. environment-dependent)."

**Defensibility: 8/10**

**What makes it defensible:**
- Daikon provides execution-grounded invariant validation, but for OO programs with a fundamentally different execution model
- Mainframe batch execution has unique semantics: JCL step ordering, dataset DISP, return-code-based conditional execution — none of which Daikon addresses
- The explicit environment validity labeling (ENVIRONMENT_DEPENDENT state for VSAM, return codes) is a new dimension absent in prior work

**Important limitation to disclose:** Dynamic evidence uses GnuCOBOL (open-source), not z/OS. Results are labeled "GnuCOBOL instrumented execution" throughout. GnuCOBOL/z/OS semantic equivalence is formally characterized per contract type in docs/mainframe_realism_audit.md.

---

### CLAIM 4 (RANK 4 — CONDITIONAL): Empirically Grounded Fault Model for Mainframe Modernization

**Revised statement:**
> "To our knowledge [†pending systematic search], no published mutation testing framework derives fault operators specifically from documented real-world mainframe-to-cloud modernization failures, with each operator traceable to at least two independent empirical evidence sources."

**Defensibility: 8/10 CONDITIONAL**

**[†] Verification required before submission:**
```
Systematic literature search required:
  - IEEE Xplore: "mutation testing" + ("mainframe" OR "COBOL" OR "legacy")
  - ACM DL: same terms
  - Google Scholar: "COBOL mutation operators" + "modernization"
  - Reference: Offutt mutation testing bibliography
```

**If search finds related work:** Revise claim to compare against that work explicitly.  
**If search finds nothing:** Claim is defensible as stated with "to our knowledge" qualifier.

**What already makes it defensible regardless:**
- General mutation testing frameworks (PIT, Offutt operators) target Java/C program semantics
- No general mutation framework addresses: COND parameter semantics, JCL DISP semantics, dataset dependency ordering
- Empirical grounding from AWS CardDemo issues, IBM migration guides, Stack Overflow (all cited) is itself a contribution to reproducible failure modeling

---

### CLAIM 5 (RANK 5): Provenance-Aware Contract IR

**Revised statement:**
> "Unlike Daikon's single-dimensional statistical confidence for invariants, our BCG maintains a multi-dimensional evidence provenance per contract: source artifact, source location, extraction method (deterministic/LLM/human/execution), confidence vector (static_support, dynamic_support, cross_artifact_support, provenance_quality, human_validation, execution_frequency), and validation state (8-state machine). This enables systematic audit of why the system believes each contract exists."

**Defensibility: 7/10**

**What makes it defensible:**
- Daikon tracks confidence (single dimension: statistical support count)
- No behavioral contract system tracks the combination {source, method, multi-dim confidence, 8-state validation}
- The audit trail is essential for the modernization risk use case (engineers must trust and trace each risk finding)

**Potential reviewer objection:** "Daikon has confidence; your multi-dimensional version is just more dimensions."

**Rebuttal:** Daikon's confidence is a statistical property of a single evidence type (execution traces). BCG's confidence vector synthesizes four fundamentally different evidence types (static, dynamic, human, execution oracle), each with different reliability properties. The architecture supports audit and challenge of each dimension independently — which is not possible in Daikon's single-score model.

---

### CLAIM 6 (DOWNGRADED TO MOTIVATION): Counterfactual Contract Preservation

**Original status:** Listed as novelty claim.

**Revised status:** Motivation for experimental design, NOT a primary novelty claim.

**Rationale:** The framing of modernization as "which behavioral contracts are preserved?" is a useful perspective but is not a technical contribution on its own. It is the experimental framing that enables RQ2. Its scientific value lies in the empirical result, not in the framing itself.

**Correct usage in paper:**
> "We frame modernization verification as a contract preservation problem: a modernized system is behaviorally equivalent to the original if and only if it preserves the set of validated behavioral contracts. This framing motivates our experimental design (RQ2) and enables systematic comparison of what each approach detects."

---

### CLAIM 7 (DO NOT CLAIM — EMPIRICAL RESULT): Dynamic Evidence Reduces False Positives

**Status:** RQ3 hypothesis, NOT a novelty claim.

**Correct treatment:** Present as a testable hypothesis (H3). The finding — whether dynamic evidence reduces false positives — is the experimental contribution. If H3 is confirmed, it is an empirical finding, not a claimed innovation. If H3 is not confirmed, it is a negative result worth reporting.

---

## PART 4: GAPS IN THE LITERATURE REVIEW REQUIRING ADDITION

The following 8 works must be added before paper submission:

| # | Work | Venue | Why Required |
|---|------|-------|--------------|
| W29 | Lo et al. 2006 — "Mining Temporal Specifications" | ICSE | Canonical temporal-spec-mining; foundational for Claim 2 |
| W30 | Ammons et al. 2002 — "Mining Specifications" (IODINE) | ICSE | Behavioral model inference from traces; precursor |
| W31 | Lorenzoli et al. 2008 — GIST/GKTail | ICSE | FSM behavioral mining; closest competitor to dynamic evidence |
| W32 | Angluin 1987 — L* algorithm | Information & Computation | Foundation for automata learning cited in W1 |
| W33 | Leucker & Schallhart 2009 — Runtime Verification survey | JSS | RV foundations; context for dynamic evidence |
| W34 | Mariani & Pezzé 2012 — Spec mining + RV | ICSE | Connects behavioral mining to runtime monitoring |
| W35 | Lahiri et al. 2012 — Semantic Differencing | PLDI | Related work for modernization context |
| W36 | Felsing et al. 2014 — Regression Verification | ICSE | Conceptually adjacent to contract preservation |

---

## PART 5: RECOMMENDED PAPER NOVELTY FRAMING

### Primary Novelty Sentence (for abstract and introduction)

> "We present the Behavioral Contract Graph (BCG), a formal intermediate representation that jointly encodes temporal, resource, and control-flow obligations extracted from heterogeneous legacy batch artifacts (JCL + COBOL), reconciles static and dynamic evidence with an explicit eight-state validation taxonomy and per-contract provenance, and demonstrates—to our knowledge for the first time—execution-grounded behavioral contract validation for mainframe batch systems. We evaluate the BCG against five baselines on modernization fault detection and investigate whether execution evidence reduces false positives relative to static-only analysis."

### Secondary Claims (for contributions list)

1. A formal BCG for JCL+COBOL with typed entities, structural relations, behavioral contracts, provenance, dynamic observations, and validation metadata.
2. A static/dynamic reconciliation procedure with explicit conflict taxonomy including ENVIRONMENT_DEPENDENT and INSUFFICIENT_EVIDENCE states.
3. An empirically grounded mutation framework (F1–F3) deriving fault operators from documented mainframe-to-cloud modernization failures.
4. A multi-dimensional provenance model tracking extraction method, evidence type, confidence vector, and validation state per contract.
5. Experimental investigation of three research questions using a public executable legacy benchmark (AWS CardDemo).

---

## PART 6: WHAT MUST NOT BE CLAIMED

Do NOT use these phrasings:

| Prohibited phrase | Reason |
|---|---|
| "First behavioral contract system" | Meyer 1992, Daikon 2007 predate |
| "First to mine contracts from execution" | Lo 2006, Ammons 2002, Lorenzoli 2008 predate |
| "Novel algorithm" | No new algorithm is introduced; methods are combinations |
| "Novel BCG formalization" | Use "We present a BCG formalization" |
| "Dynamic evidence improves accuracy" | This is RQ3 hypothesis, not a claimed fact |
| "Our approach is superior" | Say "Our approach achieves higher F1 than baselines A–E" |
| "No prior work analyzes legacy systems" | Sneed, Pessoa, Ulrich+Newcomb, Comella-Dorda predate |

---

## PART 7: VERIFICATION CHECKLIST

Before final submission:

- [ ] Systematic mutation testing literature search completed (W37+)
- [ ] All "no prior work" changed to "to our knowledge"
- [ ] GIST (Lorenzoli 2008) checked: does it have explicit conflict states?
- [ ] 8 new literature works added to references.bib
- [ ] Claim 6 (counterfactual) moved from novelty to motivation in paper
- [ ] Claim 7 (dynamic evidence) labeled as RQ3 hypothesis, not innovation
- [ ] Primary novelty sentence verified by independent reviewer
